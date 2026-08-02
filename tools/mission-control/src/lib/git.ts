import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import { DATA_DIR } from "./config";

const run = promisify(execFile);

/** Where cloned repositories live. One directory per project. */
export const WORKSPACES_DIR = path.join(DATA_DIR, "workspaces");

export interface GitResult {
  stdout: string;
  stderr: string;
}

async function git(cwd: string, args: string[]): Promise<GitResult> {
  try {
    const { stdout, stderr } = await run("git", args, {
      cwd,
      maxBuffer: 32 * 1024 * 1024,
      env: {
        ...process.env,
        // Never let git block waiting for credentials on a background dispatch.
        GIT_TERMINAL_PROMPT: "0",
        GIT_ASKPASS: "echo",
      },
    });
    return { stdout, stderr };
  } catch (error) {
    const e = error as { stderr?: string; stdout?: string; message?: string };
    throw new Error(redact(e.stderr || e.stdout || e.message || "git failed"));
  }
}

/**
 * Strip any embedded credential before an error reaches a log or the UI.
 * Tokens are injected into the remote URL, so git errors can echo them back.
 */
export function redact(text: string): string {
  return text.replace(/\/\/[^@/\s]+@/g, "//***@");
}

/**
 * The process-wide token, used when a project has none of its own.
 * Per-project tokens are resolved in `projects.ts` and passed in explicitly.
 */
export function gitTokenFromEnv(): string | undefined {
  return (
    process.env.MISSION_CONTROL_GIT_TOKEN ||
    process.env.GITHUB_TOKEN ||
    process.env.GH_TOKEN ||
    undefined
  );
}

/**
 * Build an authenticated remote URL. The token is injected at call time and
 * kept out of the stored git config (see `authenticatedRemote` usage below).
 */
export function withToken(repoUrl: string, token = gitTokenFromEnv()): string {
  if (!token) return repoUrl;
  try {
    const url = new URL(repoUrl);
    if (url.protocol !== "https:") return repoUrl; // SSH handles its own auth.
    url.username = token;
    url.password = "";
    return url.toString().replace(/:@/, "@");
  } catch {
    return repoUrl;
  }
}

/** Derive a readable default project name from a repo URL. */
export function repoName(repoUrl: string): string {
  const cleaned = repoUrl.replace(/\.git$/, "").replace(/\/+$/, "");
  const parts = cleaned.split(/[/:]/).filter(Boolean);
  return parts.slice(-2).join("/") || cleaned;
}

async function exists(target: string): Promise<boolean> {
  try {
    await fs.access(target);
    return true;
  } catch {
    return false;
  }
}

export interface EnsureWorkspaceInput {
  projectId: string;
  repoUrl: string;
  /** Branch to base work on. Defaults to the remote's HEAD. */
  baseBranch?: string;
  /** Branch the agents commit to. Created from baseBranch if absent. */
  workBranch: string;
  /** Resolved credential for this project; falls back to the env token. */
  token?: string;
}

export interface WorkspaceState {
  dir: string;
  baseBranch: string;
  workBranch: string;
  headSha: string;
}

/**
 * Clone the repo if this project has no workspace yet, otherwise fetch and
 * reset onto the requested branch. Safe to call before every run.
 *
 * The remote is stored WITHOUT the token; the token is supplied per-command so
 * it never lands in `.git/config` inside a workspace agents can read.
 */
export async function ensureWorkspace(
  input: EnsureWorkspaceInput,
): Promise<WorkspaceState> {
  await fs.mkdir(WORKSPACES_DIR, { recursive: true });
  const dir = path.join(WORKSPACES_DIR, input.projectId);
  const authed = withToken(input.repoUrl, input.token ?? gitTokenFromEnv());

  if (!(await exists(path.join(dir, ".git")))) {
    await fs.rm(dir, { recursive: true, force: true });
    await git(WORKSPACES_DIR, ["clone", authed, dir]);
    // Replace the authenticated URL with the clean one.
    await git(dir, ["remote", "set-url", "origin", input.repoUrl]);
  } else {
    await git(dir, ["fetch", authed, "--prune", "+refs/heads/*:refs/remotes/origin/*"]);
  }

  const baseBranch =
    input.baseBranch?.trim() ||
    (await git(dir, ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"]))
      .stdout.trim()
      .replace(/^origin\//, "") ||
    "main";

  // Check out the work branch, creating it from the base branch if new.
  const branches = (await git(dir, ["branch", "--list", input.workBranch])).stdout.trim();
  if (branches) {
    await git(dir, ["checkout", input.workBranch]);
  } else {
    await git(dir, ["checkout", "-B", input.workBranch, `origin/${baseBranch}`]);
  }

  const headSha = (await git(dir, ["rev-parse", "HEAD"])).stdout.trim();
  return { dir, baseBranch, workBranch: input.workBranch, headSha };
}

/** Whether the workspace has uncommitted changes. */
export async function hasChanges(dir: string): Promise<boolean> {
  const { stdout } = await git(dir, ["status", "--porcelain"]);
  return stdout.trim().length > 0;
}

/** Stage and commit everything in the workspace. Returns the sha, or null. */
export async function commitAll(dir: string, message: string): Promise<string | null> {
  if (!(await hasChanges(dir))) return null;
  await git(dir, ["add", "-A"]);
  await git(dir, [
    "-c",
    "user.name=Mission Control",
    "-c",
    "user.email=mission-control@local",
    "commit",
    "-m",
    message,
  ]);
  return (await git(dir, ["rev-parse", "HEAD"])).stdout.trim();
}

/** Push the work branch to origin, setting upstream. */
export async function pushBranch(
  dir: string,
  repoUrl: string,
  workBranch: string,
  token = gitTokenFromEnv(),
): Promise<void> {
  if (!token && repoUrl.startsWith("https://")) {
    throw new Error(
      "No git token for this project. Add one under GitHub access, or set MISSION_CONTROL_GIT_TOKEN.",
    );
  }
  await git(dir, ["push", "-u", withToken(repoUrl, token), `${workBranch}:${workBranch}`]);
}

export type AccessCheck =
  | { ok: true; verified: "write" | "read" }
  | { ok: false; reason: string };

/**
 * Classify a git failure into something a human can act on, without ever
 * echoing the credential.
 *
 * "could not read Password" counts as rejection: prompts are disabled, so it
 * means git did not accept the supplied credential as complete.
 */
function classifyAccessFailure(raw: string): string {
  if (
    /authentication failed|invalid username or (password|token)|could not read password|terminal prompts disabled|403/i.test(
      raw,
    )
  ) {
    return "Token rejected, or it lacks access to this repo.";
  }
  if (/not found|repository does not exist|404/i.test(raw)) {
    return "Repository not found for this token.";
  }
  if (/permission|denied|protected branch|pre-receive/i.test(raw)) {
    return "Token reached the repo but cannot write to it (needs Contents: read and write).";
  }
  return raw.split("\n")[0].slice(0, 200);
}

/** Credential-bearing git invocation with prompts and helpers disabled. */
async function gitAuthed(args: string[], cwd?: string): Promise<void> {
  await run("git", ["-c", "credential.helper=", ...args], {
    cwd,
    // No credential helper: a cached OS-keychain entry must not mask a bad token.
    env: { ...process.env, GIT_TERMINAL_PROMPT: "0", GIT_ASKPASS: "echo" },
    timeout: 30_000,
    maxBuffer: 8 * 1024 * 1024,
  });
}

/**
 * Verify a credential against the real remote.
 *
 * Prefers a dry-run push from the workspace, because that is the operation the
 * token actually has to perform and it exercises the same authorization path.
 * `ls-remote` alone is not evidence: on a public repository it succeeds with no
 * credential at all, so a garbage token would look fine.
 *
 * Falls back to `ls-remote` only when there is no workspace yet, and says so
 * via `verified: "read"` rather than claiming more than it checked.
 */
export async function checkAccess(
  repoUrl: string,
  token = gitTokenFromEnv(),
  workspaceDir?: string,
): Promise<AccessCheck> {
  const authedUrl = withToken(repoUrl, token);
  const canDryRun = workspaceDir && (await exists(path.join(workspaceDir, ".git")));

  if (canDryRun) {
    try {
      // Pushes nothing; the server still authenticates and authorizes.
      await gitAuthed(
        ["push", "--dry-run", authedUrl, "HEAD:refs/heads/mission-control-access-check"],
        workspaceDir,
      );
      return { ok: true, verified: "write" };
    } catch (error) {
      const e = error as { stderr?: string; message?: string };
      return { ok: false, reason: classifyAccessFailure(redact(e.stderr || e.message || "git failed")) };
    }
  }

  try {
    await gitAuthed(["ls-remote", "--heads", authedUrl]);
    return { ok: true, verified: "read" };
  } catch (error) {
    const e = error as { stderr?: string; message?: string };
    return { ok: false, reason: classifyAccessFailure(redact(e.stderr || e.message || "git failed")) };
  }
}

/** Resolve a ref to a sha, or null when it does not exist. */
async function resolveRef(dir: string, ref: string): Promise<string | null> {
  try {
    const { stdout } = await git(dir, ["rev-parse", "--verify", "--quiet", `${ref}^{commit}`]);
    const sha = stdout.trim();
    return sha || null;
  } catch {
    return null;
  }
}

/** Short status summary for the UI. */
export async function workspaceStatus(
  dir: string,
  baseBranch?: string,
): Promise<{
  branch: string;
  changedFiles: number;
  ahead: number;
} | null> {
  if (!(await exists(path.join(dir, ".git")))) return null;
  const branch = (await git(dir, ["rev-parse", "--abbrev-ref", "HEAD"])).stdout.trim();
  const changed = (await git(dir, ["status", "--porcelain"])).stdout
    .split("\n")
    .filter((l) => l.trim()).length;

  // "Ahead" means unpushed work, so it is always counted against a remote ref:
  // the branch's own upstream when it has been pushed, otherwise the base
  // branch it was cut from. Counting HEAD alone would report the repo's whole
  // history as unpushed on a freshly cloned workspace.
  const candidates = [
    `origin/${branch}`,
    baseBranch ? `origin/${baseBranch}` : null,
    "origin/HEAD",
  ].filter((ref): ref is string => Boolean(ref));

  let base: string | null = null;
  for (const ref of candidates) {
    base = await resolveRef(dir, ref);
    if (base) break;
  }

  let ahead = 0;
  try {
    // No remote ref at all (a local-only repo): every commit is unpushed.
    const range = base ? `${base}..HEAD` : "HEAD";
    const { stdout } = await git(dir, ["rev-list", "--count", range]);
    ahead = Number(stdout.trim()) || 0;
  } catch {
    ahead = 0;
  }

  return { branch, changedFiles: changed, ahead };
}
