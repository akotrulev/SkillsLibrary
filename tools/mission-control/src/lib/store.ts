import fs from "node:fs/promises";
import path from "node:path";
import { MAX_LOG_ENTRIES, RUNS_DIR } from "./config";
import type { Run, Task, TaskLogEntry } from "./types";

/**
 * File-backed run store. One JSON document per run.
 *
 * Writes are serialised through a per-run promise chain: the orchestrator can
 * finish several parallel tasks in the same tick, and a naive read-modify-write
 * would lose updates.
 */
const writeChains = new Map<string, Promise<unknown>>();
const memory = new Map<string, Run>();

function runFile(runId: string): string {
  return path.join(RUNS_DIR, `${runId}.json`);
}

async function ensureDir(): Promise<void> {
  await fs.mkdir(RUNS_DIR, { recursive: true });
}

/** Queue `fn` behind any in-flight write for this run. */
function serialise<T>(runId: string, fn: () => Promise<T>): Promise<T> {
  const prior = writeChains.get(runId) ?? Promise.resolve();
  const next = prior.then(fn, fn);
  // Keep the chain alive but never let a rejection poison later writes.
  writeChains.set(
    runId,
    next.catch(() => undefined),
  );
  return next;
}

export async function saveRun(run: Run): Promise<Run> {
  return serialise(run.id, async () => {
    await ensureDir();
    run.updatedAt = new Date().toISOString();
    memory.set(run.id, run);
    await fs.writeFile(runFile(run.id), JSON.stringify(run, null, 2), "utf8");
    return run;
  });
}

/**
 * Repair state that a previous process left mid-flight.
 *
 * Agent subprocesses do not survive a shutdown, so any task still marked
 * `in_progress` on disk is an orphan: nothing is driving it. Reset those to
 * `ready` so the work is picked up again on the next start, and demote a
 * `running` run to `paused` — restarting the tool must never silently resume
 * dispatching against a project.
 */
function reconcile(run: Run): boolean {
  let changed = false;
  for (const task of run.tasks) {
    if (task.status === "in_progress") {
      task.status = "ready";
      task.error = "Interrupted when Mission Control stopped; requeued.";
      task.startedAt = undefined;
      changed = true;
    }
  }
  if (run.status === "running") {
    run.status = "paused";
    changed = true;
  }
  return changed;
}

export async function loadRun(runId: string): Promise<Run | null> {
  const inMemory = memory.get(runId);
  if (inMemory) return inMemory;
  try {
    const run = JSON.parse(await fs.readFile(runFile(runId), "utf8")) as Run;
    // First load in this process: heal anything the last process left behind.
    if (reconcile(run)) {
      memory.set(run.id, run);
      await fs.writeFile(runFile(run.id), JSON.stringify(run, null, 2), "utf8");
    }
    memory.set(runId, run);
    return run;
  } catch {
    return null;
  }
}

export async function listRuns(): Promise<Run[]> {
  await ensureDir();
  let names: string[];
  try {
    names = await fs.readdir(RUNS_DIR);
  } catch {
    return [];
  }
  const runs: Run[] = [];
  for (const name of names) {
    if (!name.endsWith(".json")) continue;
    const run = await loadRun(name.replace(/\.json$/, ""));
    if (run) runs.push(run);
  }
  return runs.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export async function deleteRun(runId: string): Promise<void> {
  memory.delete(runId);
  try {
    await fs.unlink(runFile(runId));
  } catch {
    // Already gone.
  }
}

/**
 * Read-modify-write a run atomically with respect to other store writers.
 * Returns the updated run, or null if it no longer exists.
 */
export async function updateRun(
  runId: string,
  mutate: (run: Run) => void,
): Promise<Run | null> {
  return serialise(runId, async () => {
    const run = memory.get(runId) ?? (await loadRunUncached(runId));
    if (!run) return null;
    mutate(run);
    run.updatedAt = new Date().toISOString();
    memory.set(runId, run);
    await ensureDir();
    await fs.writeFile(runFile(runId), JSON.stringify(run, null, 2), "utf8");
    return run;
  });
}

async function loadRunUncached(runId: string): Promise<Run | null> {
  try {
    return JSON.parse(await fs.readFile(runFile(runId), "utf8")) as Run;
  } catch {
    return null;
  }
}

export function getTask(run: Run, taskId: string): Task | undefined {
  return run.tasks.find((t) => t.id === taskId);
}

/** Append a log entry, trimming the oldest so run files stay bounded. */
export function appendLog(task: Task, entry: TaskLogEntry): void {
  task.log.push(entry);
  if (task.log.length > MAX_LOG_ENTRIES) {
    task.log.splice(0, task.log.length - MAX_LOG_ENTRIES);
  }
}
