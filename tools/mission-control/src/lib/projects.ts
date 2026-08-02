import fs from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { DATA_DIR } from "./config";
import { ensureWorkspace, gitTokenFromEnv, repoName, WORKSPACES_DIR } from "./git";
import {
  decryptSecret,
  encryptSecret,
  secretsEnabled,
  tokenHint,
  type SecretRecord,
} from "./secrets";

/**
 * A configured working directory. Mission Control can hold many projects at
 * once; `enabled` is the execution switch — a disabled project's runs stay on
 * the board and keep their state, but dispatch nothing.
 */
export interface Project {
  id: string;
  name: string;
  /**
   * Directory the agents work in. For `local` projects this is the path you
   * supplied; for `git` projects it is the managed clone under
   * `.data/workspaces/<id>` and is filled in on first prepare.
   */
  targetDir: string;
  /** When false, the orchestrator refuses to dispatch tasks for this project. */
  enabled: boolean;
  source: ProjectSource;
  /** Git-backed projects only. */
  repoUrl?: string;
  baseBranch?: string;
  workBranch?: string;
  /**
   * Encrypted GitHub credential for this project. Never serialised to a client;
   * see `tokenDescriptor`. Absent means "fall back to the environment token".
   */
  tokenCipher?: SecretRecord;
  /** Non-reversible label for the stored token, safe to display. */
  tokenHint?: string;
  createdAt: string;
}

export type ProjectSource = "local" | "git";

const FILE = path.join(DATA_DIR, "projects.json");

let chain: Promise<unknown> = Promise.resolve();

/** Serialise writes so concurrent toggles cannot lose each other. */
function serialise<T>(fn: () => Promise<T>): Promise<T> {
  const next = chain.then(fn, fn);
  chain = next.catch(() => undefined);
  return next;
}

async function readAll(): Promise<Project[]> {
  try {
    const projects = JSON.parse(await fs.readFile(FILE, "utf8")) as Project[];
    return projects.map((p) => {
      // Projects written before git support had no `source`.
      const source = p.source ?? "local";
      // A git project's workspace is always `<DATA_DIR>/workspaces/<id>`, so it
      // is derived rather than trusted: a stored absolute path goes stale the
      // moment the app directory moves.
      const targetDir =
        source === "git" ? path.join(WORKSPACES_DIR, p.id) : p.targetDir;
      return { ...p, source, targetDir };
    });
  } catch {
    return [];
  }
}

async function writeAll(projects: Project[]): Promise<void> {
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.writeFile(FILE, JSON.stringify(projects, null, 2), "utf8");
}

export async function listProjects(): Promise<Project[]> {
  const projects = await readAll();
  return projects.sort((a, b) => a.name.localeCompare(b.name));
}

export async function getProject(id: string): Promise<Project | null> {
  return (await readAll()).find((p) => p.id === id) ?? null;
}

export async function getProjectByDir(targetDir: string): Promise<Project | null> {
  const resolved = path.resolve(targetDir);
  return (await readAll()).find((p) => p.targetDir === resolved) ?? null;
}

/**
 * Register a project, or return the existing one for that directory. The
 * directory is the identity — two projects cannot share a working directory.
 */
export async function upsertProject(input: {
  name?: string;
  targetDir: string;
}): Promise<Project> {
  return serialise(async () => {
    const targetDir = path.resolve(input.targetDir);
    const projects = await readAll();
    const existing = projects.find((p) => p.targetDir === targetDir);
    if (existing) {
      if (input.name?.trim()) existing.name = input.name.trim();
      await writeAll(projects);
      return existing;
    }
    const project: Project = {
      id: randomUUID(),
      name: input.name?.trim() || path.basename(targetDir),
      targetDir,
      enabled: true,
      source: "local",
      createdAt: new Date().toISOString(),
    };
    projects.push(project);
    await writeAll(projects);
    return project;
  });
}

/**
 * Register a project backed by a git remote. Nothing is cloned here — the
 * clone happens on `prepareProject`, so adding a project stays fast and a bad
 * URL surfaces when you start a run rather than while typing.
 */
export async function createGitProject(input: {
  repoUrl: string;
  name?: string;
  baseBranch?: string;
  workBranch?: string;
}): Promise<Project> {
  return serialise(async () => {
    const repoUrl = input.repoUrl.trim();
    const projects = await readAll();
    const existing = projects.find((p) => p.source === "git" && p.repoUrl === repoUrl);
    if (existing) return existing;

    const id = randomUUID();
    const project: Project = {
      id,
      name: input.name?.trim() || repoName(repoUrl),
      // Filled in by prepareProject once the clone exists.
      targetDir: path.join(WORKSPACES_DIR, id),
      enabled: true,
      source: "git",
      repoUrl,
      baseBranch: input.baseBranch?.trim() || undefined,
      workBranch:
        input.workBranch?.trim() || `mission-control/${new Date().toISOString().slice(0, 10)}`,
      createdAt: new Date().toISOString(),
    };
    projects.push(project);
    await writeAll(projects);
    return project;
  });
}

/**
 * Make a project ready to be worked in, and return the directory to use as a
 * run's `targetDir`. Local projects are returned as-is; git projects are
 * cloned or fetched and put on their work branch.
 */
export async function prepareProject(project: Project): Promise<string> {
  if (project.source !== "git" || !project.repoUrl) return project.targetDir;

  const state = await ensureWorkspace({
    projectId: project.id,
    repoUrl: project.repoUrl,
    baseBranch: project.baseBranch,
    workBranch: project.workBranch ?? "mission-control/work",
    token: resolveGitToken(project).token,
  });

  // Record what the clone actually resolved to (e.g. the real default branch).
  await serialise(async () => {
    const projects = await readAll();
    const stored = projects.find((p) => p.id === project.id);
    if (stored) {
      stored.targetDir = state.dir;
      stored.baseBranch = state.baseBranch;
      stored.workBranch = state.workBranch;
      await writeAll(projects);
    }
  });

  return state.dir;
}

/** Flip the execution switch. Returns the updated project, or null. */
export async function setProjectEnabled(
  id: string,
  enabled: boolean,
): Promise<Project | null> {
  return serialise(async () => {
    const projects = await readAll();
    const project = projects.find((p) => p.id === id);
    if (!project) return null;
    project.enabled = enabled;
    await writeAll(projects);
    return project;
  });
}

export async function deleteProject(id: string): Promise<void> {
  await serialise(async () => {
    const projects = await readAll();
    await writeAll(projects.filter((p) => p.id !== id));
  });
}

/**
 * Store (or clear, with null) this project's GitHub credential.
 * Throws when no `MISSION_CONTROL_SECRET` is configured — a token is never
 * written unencrypted.
 */
export async function setProjectToken(
  id: string,
  token: string | null,
): Promise<Project | null> {
  return serialise(async () => {
    const projects = await readAll();
    const project = projects.find((p) => p.id === id);
    if (!project) return null;

    if (token === null) {
      delete project.tokenCipher;
      delete project.tokenHint;
    } else {
      const trimmed = token.trim();
      if (!trimmed) throw new Error("Token is empty.");
      project.tokenCipher = encryptSecret(trimmed);
      project.tokenHint = tokenHint(trimmed);
    }

    await writeAll(projects);
    return project;
  });
}

/** Where a project's credential comes from, and whether it can push at all. */
export interface GitTokenDescriptor {
  source: "project" | "env" | "none";
  /** Safe-to-display label, project-sourced tokens only. */
  hint?: string;
  canPush: boolean;
  /** True when a token is stored but the key can no longer decrypt it. */
  undecryptable: boolean;
  /** False when MISSION_CONTROL_SECRET is unset, so tokens cannot be stored. */
  storageAvailable: boolean;
}

/**
 * Resolve the credential for a project: its own token first, then the
 * process-wide environment token, then nothing.
 *
 * The returned token is for server-side git commands only — it must never be
 * put in an API response (see `tokenDescriptor`) or an agent's environment
 * (see `agent-env.ts`).
 */
export function resolveGitToken(project: Project): {
  token?: string;
  descriptor: GitTokenDescriptor;
} {
  const storageAvailable = secretsEnabled();
  const envToken = gitTokenFromEnv();

  if (project.tokenCipher) {
    const token = decryptSecret(project.tokenCipher);
    if (token) {
      return {
        token,
        descriptor: {
          source: "project",
          hint: project.tokenHint,
          canPush: true,
          undecryptable: false,
          storageAvailable,
        },
      };
    }
    // Stored but unreadable: fall back to env rather than failing outright,
    // and tell the UI the stored token needs re-entering.
    return {
      token: envToken,
      descriptor: {
        source: envToken ? "env" : "none",
        canPush: Boolean(envToken),
        undecryptable: true,
        storageAvailable,
      },
    };
  }

  return {
    token: envToken,
    descriptor: {
      source: envToken ? "env" : "none",
      canPush: Boolean(envToken),
      undecryptable: false,
      storageAvailable,
    },
  };
}

/** The client-safe half of `resolveGitToken`. Never contains the token. */
export function tokenDescriptor(project: Project): GitTokenDescriptor {
  return resolveGitToken(project).descriptor;
}

/**
 * Whether a run targeting `targetDir` may dispatch. Directories with no
 * registered project are allowed — registration is a convenience, not a gate.
 */
export async function isExecutionEnabled(targetDir: string): Promise<boolean> {
  const project = await getProjectByDir(targetDir);
  return project ? project.enabled : true;
}
