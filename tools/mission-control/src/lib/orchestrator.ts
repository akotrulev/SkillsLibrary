import { abortRun, dispatchTask } from "./dispatcher";
import { eventBus } from "./events";
import { isExecutionEnabled } from "./projects";
import { loadRun, updateRun } from "./store";
import type { Run, Task } from "./types";

/** Runs currently being driven by this process. */
const active = new Set<string>();

export function isRunning(runId: string): boolean {
  return active.has(runId);
}

async function publishRun(runId: string): Promise<void> {
  const run = await loadRun(runId);
  if (run) eventBus.publish(runId, { type: "run:updated", run });
}

async function setTask(
  runId: string,
  taskId: string,
  mutate: (task: Task) => void,
): Promise<void> {
  const run = await updateRun(runId, (r) => {
    const task = r.tasks.find((t) => t.id === taskId);
    if (task) mutate(task);
  });
  const task = run?.tasks.find((t) => t.id === taskId);
  if (task) eventBus.publish(runId, { type: "task:updated", task });
}

/** Questions that block this task and have not been answered yet. */
function blockingQuestions(run: Run, taskId: string): string[] {
  return run.openQuestions
    .filter((q) => !q.answer && q.blocksTaskIds.includes(taskId))
    .map((q) => q.question);
}

/**
 * A task is dispatchable when every dependency is done and nothing unanswered
 * blocks it. Dependencies that ended `skipped` count as satisfied so one
 * skipped task does not strand the rest of the graph.
 */
function isDispatchable(run: Run, task: Task): boolean {
  if (task.status !== "ready") return false;
  if (blockingQuestions(run, task.id).length > 0) return false;
  return task.dependsOn.every((depId) => {
    const dep = run.tasks.find((t) => t.id === depId);
    return !dep || dep.status === "done" || dep.status === "skipped";
  });
}

/**
 * Second line of defence behind the planner's parallel-safety call: never run
 * two tasks concurrently that declare overlapping files.
 */
function conflictsWithRunning(task: Task, running: Task[]): boolean {
  if (task.files.length === 0) return false;
  const claimed = new Set(running.flatMap((t) => t.files));
  return task.files.some((f) => claimed.has(f));
}

/**
 * Drive a run to completion: phases strictly in order, tasks within a phase
 * either sequential or bounded-parallel depending on the phase's safety call.
 *
 * Returns once the run reaches a terminal state, or pauses on a blocking
 * unanswered question.
 */
export async function startRun(runId: string): Promise<void> {
  if (active.has(runId)) return;
  active.add(runId);

  try {
    await updateRun(runId, (run) => {
      run.status = "running";
      run.error = undefined;
    });
    await publishRun(runId);

    for (;;) {
      const run = await loadRun(runId);
      if (!run) return;
      if (run.status === "cancelled" || run.status === "paused") return;

      // Execution switch: a disabled project keeps all its state but dispatches
      // nothing. Checked every iteration so toggling it off stops the run at
      // the next task boundary rather than only at start.
      if (!(await isExecutionEnabled(run.targetDir))) {
        await updateRun(runId, (r) => {
          r.status = "paused";
          r.error = "Execution is turned off for this project.";
        });
        await publishRun(runId);
        return;
      }

      const phase = run.phases.find((p) =>
        run.tasks.some(
          (t) =>
            t.phaseId === p.id &&
            t.status !== "done" &&
            t.status !== "skipped" &&
            t.status !== "blocked",
        ),
      );

      if (!phase) {
        const anyBlocked = run.tasks.some((t) => t.status === "blocked");
        await updateRun(runId, (r) => {
          r.status = anyBlocked ? "failed" : "completed";
        });
        await publishRun(runId);
        return;
      }

      // Promote this phase's backlog tasks to ready.
      await updateRun(runId, (r) => {
        for (const t of r.tasks) {
          if (t.phaseId === phase.id && t.status === "backlog") t.status = "ready";
        }
      });
      await publishRun(runId);

      const current = await loadRun(runId);
      if (!current) return;

      const phaseTasks = current.tasks.filter((t) => t.phaseId === phase.id);
      const pending = phaseTasks.filter(
        (t) => t.status === "ready" || t.status === "in_progress",
      );

      if (pending.length === 0) {
        // The phase finder counts `review` as unfinished but nothing here can
        // dispatch it — it is waiting on a human. Looping would spin hot, so
        // stop and hand the run back.
        const awaiting = phaseTasks.filter((t) => t.status === "review");
        await updateRun(runId, (r) => {
          r.status = "paused";
          r.error =
            awaiting.length > 0
              ? `Phase "${phase.name}" is waiting on review of: ${awaiting.map((t) => t.id).join(", ")}.`
              : `Phase "${phase.name}" has no dispatchable work left.`;
        });
        await publishRun(runId);
        return;
      }

      const dispatchable = pending.filter((t) => isDispatchable(current, t));

      if (dispatchable.length === 0) {
        // Everything left in this phase is waiting on an unanswered question.
        const stuck = pending.filter(
          (t) => blockingQuestions(current, t.id).length > 0,
        );
        if (stuck.length === pending.length) {
          await updateRun(runId, (r) => {
            r.status = "paused";
            for (const t of r.tasks) {
              if (stuck.some((s) => s.id === t.id)) t.status = "blocked";
            }
          });
          await publishRun(runId);
          return;
        }
        // Dependencies inside the phase are unmet but resolvable — a
        // dependency cycle would spin here, so fail loudly instead.
        await updateRun(runId, (r) => {
          r.status = "failed";
          r.error = `Phase "${phase.name}" cannot progress: unmet dependencies or a cycle among ${pending
            .map((t) => t.id)
            .join(", ")}.`;
        });
        await publishRun(runId);
        return;
      }

      const batch = phase.parallelSafe
        ? selectParallelBatch(dispatchable, current.maxParallel)
        : [dispatchable[0]];

      await Promise.all(batch.map((task) => runTask(runId, task.id)));
    }
  } finally {
    active.delete(runId);
  }
}

/** Pick a conflict-free batch, up to the concurrency ceiling. */
function selectParallelBatch(candidates: Task[], maxParallel: number): Task[] {
  const batch: Task[] = [];
  for (const task of candidates) {
    if (batch.length >= Math.max(1, maxParallel)) break;
    if (conflictsWithRunning(task, batch)) continue;
    batch.push(task);
  }
  return batch.length > 0 ? batch : [candidates[0]];
}

async function runTask(runId: string, taskId: string): Promise<void> {
  await setTask(runId, taskId, (t) => {
    t.status = "in_progress";
    t.startedAt = new Date().toISOString();
    t.error = undefined;
  });

  const run = await loadRun(runId);
  const task = run?.tasks.find((t) => t.id === taskId);
  if (!run || !task) return;

  const result = await dispatchTask(run, task);

  await setTask(runId, taskId, (t) => {
    t.finishedAt = new Date().toISOString();
    t.costUsd = result.costUsd;
    if (result.ok) {
      t.status = "done";
      t.summary = result.summary;
    } else {
      t.status = "blocked";
      t.error = result.error;
    }
  });
  await publishRun(runId);
}

export async function pauseRun(runId: string): Promise<void> {
  await updateRun(runId, (run) => {
    if (run.status === "running") run.status = "paused";
  });
  abortRun(runId);
  await publishRun(runId);
}

export async function cancelRun(runId: string): Promise<void> {
  await updateRun(runId, (run) => {
    run.status = "cancelled";
    for (const t of run.tasks) {
      if (t.status === "in_progress" || t.status === "ready") t.status = "backlog";
    }
  });
  abortRun(runId);
  await publishRun(runId);
}

/** Reset a blocked task so the next run attempt picks it up again. */
export async function retryTask(runId: string, taskId: string): Promise<void> {
  await setTask(runId, taskId, (t) => {
    t.status = "ready";
    t.error = undefined;
  });
  await publishRun(runId);
}

export async function skipTask(runId: string, taskId: string): Promise<void> {
  await setTask(runId, taskId, (t) => {
    t.status = "skipped";
  });
  await publishRun(runId);
}
