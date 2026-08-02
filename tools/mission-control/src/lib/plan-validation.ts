/**
 * Structural checks on a parsed plan.
 *
 * The zod schema proves each object has the right *shape*; these checks prove
 * the objects are consistent with each other. Both failure modes they catch are
 * silent at runtime rather than loud:
 *
 * - a task pointing at a phase that does not exist is never promoted, never
 *   dispatched, and the run still reports `completed`;
 * - a duplicate task id makes every `tasks.find(t => t.id === …)` resolve to the
 *   first match, so status lands on the wrong task.
 *
 * Kept free of SDK imports so it can be unit tested on its own.
 */

export interface ValidatablePlan {
  phases: { id: string; name: string }[];
  tasks: { id: string; phaseId: string; dependsOn: string[] }[];
  openQuestions: { id: string; blocksTaskIds: string[] }[];
}

/** Ids appearing more than once, in first-seen order. */
function duplicates(ids: string[]): string[] {
  const seen = new Set<string>();
  const dupes = new Set<string>();
  for (const id of ids) {
    if (seen.has(id)) dupes.add(id);
    seen.add(id);
  }
  return [...dupes];
}

/**
 * Returns a list of human-readable problems. An empty list means the plan is
 * internally consistent; it says nothing about whether the plan is any good.
 */
export function validatePlan(plan: ValidatablePlan): string[] {
  const problems: string[] = [];

  const duplicatePhases = duplicates(plan.phases.map((p) => p.id));
  if (duplicatePhases.length > 0) {
    problems.push(`Duplicate phase ids: ${duplicatePhases.join(", ")}.`);
  }

  const duplicateTasks = duplicates(plan.tasks.map((t) => t.id));
  if (duplicateTasks.length > 0) {
    problems.push(`Duplicate task ids: ${duplicateTasks.join(", ")}.`);
  }

  const phaseIndex = new Map(plan.phases.map((p, i) => [p.id, i]));
  const taskIds = new Set(plan.tasks.map((t) => t.id));

  const orphans = plan.tasks.filter((t) => !phaseIndex.has(t.phaseId));
  if (orphans.length > 0) {
    problems.push(
      `Task(s) assigned to an unknown phase: ${orphans
        .map((t) => `${t.id} → ${t.phaseId}`)
        .join(", ")}.`,
    );
  }

  for (const task of plan.tasks) {
    if (task.dependsOn.includes(task.id)) {
      problems.push(`Task ${task.id} depends on itself.`);
    }

    const unknownDeps = task.dependsOn.filter((d) => d !== task.id && !taskIds.has(d));
    if (unknownDeps.length > 0) {
      problems.push(
        `Task ${task.id} depends on unknown task(s): ${unknownDeps.join(", ")}.`,
      );
    }

    // Phases run strictly in order, so a dependency on later work can never be
    // satisfied — the phase would stall and fail at runtime instead of now.
    const own = phaseIndex.get(task.phaseId);
    if (own === undefined) continue;
    for (const depId of task.dependsOn) {
      const dep = plan.tasks.find((t) => t.id === depId);
      const depPhase = dep ? phaseIndex.get(dep.phaseId) : undefined;
      if (depPhase !== undefined && depPhase > own) {
        problems.push(
          `Task ${task.id} (phase ${task.phaseId}) depends on ${depId}, which runs in a later phase (${dep!.phaseId}).`,
        );
      }
    }
  }

  for (const question of plan.openQuestions) {
    const unknown = question.blocksTaskIds.filter((id) => !taskIds.has(id));
    if (unknown.length > 0) {
      problems.push(
        `Open question ${question.id} blocks unknown task(s): ${unknown.join(", ")}.`,
      );
    }
  }

  return problems;
}
