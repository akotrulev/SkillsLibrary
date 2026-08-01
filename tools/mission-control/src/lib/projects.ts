import fs from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { DATA_DIR } from "./config";

/**
 * A configured working directory. Mission Control can hold many projects at
 * once; `enabled` is the execution switch — a disabled project's runs stay on
 * the board and keep their state, but dispatch nothing.
 */
export interface Project {
  id: string;
  name: string;
  targetDir: string;
  /** When false, the orchestrator refuses to dispatch tasks for this project. */
  enabled: boolean;
  createdAt: string;
}

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
    return JSON.parse(await fs.readFile(FILE, "utf8")) as Project[];
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
      createdAt: new Date().toISOString(),
    };
    projects.push(project);
    await writeAll(projects);
    return project;
  });
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
 * Whether a run targeting `targetDir` may dispatch. Directories with no
 * registered project are allowed — registration is a convenience, not a gate.
 */
export async function isExecutionEnabled(targetDir: string): Promise<boolean> {
  const project = await getProjectByDir(targetDir);
  return project ? project.enabled : true;
}
