import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);

/**
 * What the host machine already provides, so Mission Control can be dropped on
 * a laptop that is already set up and just work.
 *
 * Two rules govern everything in this file:
 *
 * 1. **Detection reports presence, never value.** Nothing here returns a token,
 *    a key, or a file's contents — only where a credential was found and what
 *    it is called. A detected credential is used by the child process that
 *    needs it (git, or the Agent SDK) through the environment it already reads;
 *    it never travels through this app's API.
 * 2. **Detection is a lead, not a guarantee.** `gh` being installed does not
 *    mean it is logged in; a credential helper being configured does not mean
 *    it has an entry for the remote you care about. Where a cheap authoritative
 *    check exists (`gh auth status`) it is run; where it does not, the status
 *    says `likely` rather than claiming more than was observed.
 */

/** How sure we are that the host can supply this credential unaided. */
export type DetectionStatus =
  | "found" // observed directly, or an authoritative check passed
  | "likely" // the machinery is present but not verified end to end
  | "absent";

export interface Detection {
  status: DetectionStatus;
  /** Human-readable provenance, e.g. "gh CLI (logged in as akotrulev)". */
  label: string;
  /** Which mechanism answered, for the UI to group by. */
  via?: "env" | "file" | "cli" | "helper";
}

export interface HostConfig {
  anthropic: Detection;
  github: Detection;
  /** Set when git has an identity, so agent commits are not authored by nobody. */
  gitIdentity: Detection;
  platform: string;
  homeDir: string;
  detectedAt: string;
}

const ABSENT: Detection = { status: "absent", label: "Not configured on this machine" };

async function fileExists(file: string): Promise<boolean> {
  try {
    await fs.access(file);
    return true;
  } catch {
    return false;
  }
}

/** Run a command purely to learn whether it succeeds. Output is not returned. */
async function succeeds(
  command: string,
  args: string[],
): Promise<{ ok: boolean; stdout: string }> {
  try {
    const { stdout, stderr } = await run(command, args, {
      timeout: 5_000,
      maxBuffer: 1024 * 1024,
    });
    // `gh auth status` writes its useful half to stderr.
    return { ok: true, stdout: `${stdout}${stderr}` };
  } catch {
    return { ok: false, stdout: "" };
  }
}

/**
 * A Claude credential the Agent SDK can resolve on its own.
 *
 * The SDK's own order is `ANTHROPIC_API_KEY` → a stored login → the platform
 * keychain. The keychain is the case that cannot be probed cheaply, and it is
 * the normal case on macOS — so a Mac with a working `claude` login and no
 * credentials file reports `likely`, which is exactly the honest answer.
 */
async function detectAnthropic(home: string): Promise<Detection> {
  if (process.env.ANTHROPIC_API_KEY?.trim()) {
    return { status: "found", label: "ANTHROPIC_API_KEY in the environment", via: "env" };
  }
  if (process.env.CLAUDE_CODE_OAUTH_TOKEN?.trim()) {
    return {
      status: "found",
      label: "CLAUDE_CODE_OAUTH_TOKEN in the environment",
      via: "env",
    };
  }
  if (process.env.ANTHROPIC_AUTH_TOKEN?.trim()) {
    return { status: "found", label: "ANTHROPIC_AUTH_TOKEN in the environment", via: "env" };
  }

  if (await fileExists(path.join(home, ".claude", ".credentials.json"))) {
    return { status: "found", label: "Claude Code login (~/.claude)", via: "file" };
  }

  // No file and no variable. On macOS the login lives in the keychain, which a
  // server process cannot inspect without prompting, so presence of the CLI is
  // the most that can be claimed.
  const claude = await succeeds("which", ["claude"]);
  if (claude.ok && process.platform === "darwin") {
    return {
      status: "likely",
      label: "Claude Code CLI present — login may be in the macOS keychain",
      via: "cli",
    };
  }

  return ABSENT;
}

/** A GitHub credential git can use without being handed a token. */
async function detectGitHub(): Promise<Detection> {
  for (const name of ["MISSION_CONTROL_GIT_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"]) {
    if (process.env[name]?.trim()) {
      return { status: "found", label: `${name} in the environment`, via: "env" };
    }
  }

  const status = await succeeds("gh", ["auth", "status"]);
  if (status.ok) {
    const account = status.stdout.match(/account\s+(\S+)/i)?.[1];
    return {
      status: "found",
      label: account ? `gh CLI (logged in as ${account})` : "gh CLI (logged in)",
      via: "cli",
    };
  }

  const helper = await succeeds("git", ["config", "--get-all", "credential.helper"]);
  if (helper.ok && helper.stdout.trim()) {
    const first = helper.stdout.trim().split("\n").filter(Boolean).pop() ?? "";
    return {
      status: "likely",
      // The helper name can embed a path; keep it short and non-revealing.
      label: `git credential helper configured (${first.split(/\s+/)[0].slice(0, 40)})`,
      via: "helper",
    };
  }

  return ABSENT;
}

/** Whether commits an agent makes will have an author. */
async function detectGitIdentity(): Promise<Detection> {
  const name = await succeeds("git", ["config", "--get", "user.name"]);
  const email = await succeeds("git", ["config", "--get", "user.email"]);
  if (name.ok && email.ok && name.stdout.trim() && email.stdout.trim()) {
    return {
      status: "found",
      label: `${name.stdout.trim()} <${email.stdout.trim()}>`,
      via: "helper",
    };
  }
  return { status: "absent", label: "git user.name / user.email are not set" };
}

/**
 * Probe the host. Cheap enough to run per request (a few `execFile`s with a
 * 5s ceiling), and deliberately not cached: the answer changes when you run
 * `gh auth login` in another terminal, and a stale "absent" is confusing in a
 * way a stale "found" is not.
 */
export async function detectHostConfig(): Promise<HostConfig> {
  const home = os.homedir();
  const [anthropic, github, gitIdentity] = await Promise.all([
    detectAnthropic(home),
    detectGitHub(),
    detectGitIdentity(),
  ]);

  return {
    anthropic,
    github,
    gitIdentity,
    platform: `${os.type()} ${os.release()}`,
    homeDir: home,
    detectedAt: new Date().toISOString(),
  };
}
