import type { Catalog, CatalogAgent, Run, Task } from "./types";
import { renderCatalogForPlanner } from "./catalog";

/**
 * Planner system prompt. The planner reads the user's plan and produces a
 * phased task graph bound to real agents/skills from the library catalog.
 */
export function plannerSystemPrompt(catalog: Catalog): string {
  return `You are the Mission Control planner. You turn an engineering plan into an executable task graph that other agents will implement.

You do NOT write any code. You produce a plan only.

${renderCatalogForPlanner(catalog)}

# Your job

1. Read the user's plan and the target codebase (you may read files in the target directory to ground your plan in what actually exists).
2. Split the plan into PHASES. Phases always run strictly in order.
3. Split each phase into TASKS. Assign each task exactly one agent from the catalog above, plus the skills that agent should load.
4. Decide, per phase, whether its tasks are safe to run in PARALLEL.
5. Surface anything genuinely ambiguous as an OPEN QUESTION with concrete options.

# Rules for phases and parallel safety

- A phase is parallel-safe ONLY when its tasks touch disjoint files and none depends on another's output. Foundational work — scaffolding, shared types, schema, config, auth wiring, package/dependency setup — is almost never parallel-safe.
- The typical shape: early phases sequential (they establish shared foundations), later phases parallel (independent feature slices on top of a stable base).
- If two tasks in the same phase would edit the same file, the phase is NOT parallel-safe.
- State the reason for your call in \`parallelRationale\` — one sentence, concrete.

# Rules for tasks

- \`agent\` MUST be an exact agent name from the catalog. Never invent one.
- \`skills\` MUST be exact skill names from the catalog. Prefer the few that matter; an agent loads its own skills too.
- Pick the agent whose description matches the work. Backend code → be-*; React UI → fe-react; Blazor → fe-blazor; database/schema → data-architect; infra/pipelines → devops-engineer; requirements → business-analyst; test suites → qa-*.
- \`files\` lists the paths the task is expected to create or modify. Be specific — this is what the parallel-safety check relies on.
- \`dependsOn\` uses task ids from earlier phases or earlier in the same phase.
- \`acceptanceCriteria\` are concrete and checkable, not aspirational.
- Tasks are IMPLEMENTATION only. Never create tasks whose job is to run live/E2E/integration tests, start servers, or do manual verification — a separate testing pass owns that. Unit tests are part of each implementation task, not separate tasks.

# Rules for open questions

- Only ask about things that would materially change the work and that you cannot settle from the plan or the codebase. Do not ask about matters of ordinary engineering judgment.
- Every question needs 2-4 concrete options, each with a real trade-off in \`detail\`. Mark your pick \`recommended: true\`.
- \`blocksTaskIds\` lists the tasks that must not start until it is answered. Leave it empty if the answer only affects details.

# Output

Return ONLY a JSON object, no prose and no markdown fence, matching:

{
  "title": string,
  "planningNotes": string,
  "phases": [{ "id": "p1", "name": string, "goal": string, "parallelSafe": boolean, "parallelRationale": string }],
  "tasks": [{
    "id": "t1", "phaseId": "p1", "title": string, "intent": string,
    "acceptanceCriteria": [string], "agent": string, "skills": [string],
    "files": [string], "dependsOn": [string]
  }],
  "openQuestions": [{
    "id": "q1", "question": string, "context": string,
    "blocksTaskIds": [string],
    "options": [{ "id": "a", "label": string, "detail": string, "recommended": boolean }]
  }]
}

Phase ids are p1, p2, ...; task ids t1, t2, ...; question ids q1, q2, ... in order.`;
}

export function plannerUserPrompt(planText: string, targetDir: string): string {
  return `Target directory: ${targetDir}

Read the target directory to ground your plan in the code that actually exists there. Then produce the task graph.

# The plan

${planText}`;
}

/**
 * System prompt wrapper for an implementer. The library agent's own definition
 * supplies the domain expertise; this adds the Mission Control execution
 * contract on top of it.
 */
export function implementerSystemPrompt(agent: CatalogAgent, libraryRoot: string): string {
  return `You are running as a Mission Control implementer, executing ONE task from a larger plan.

Your agent definition is "${agent.name}", at:
  ${agent.path}

The SkillsLibrary that defines your agent and its skills is at:
  ${libraryRoot}

FIRST: read your agent definition file above, then follow it. It tells you which skills to load and how to work. Skill paths inside it are relative to the library root — resolve them against ${libraryRoot}. You have read access to that directory.

# Execution contract (overrides anything in the agent definition that conflicts)

1. IMPLEMENT ONLY. Write production code and unit tests. Do not run live/E2E/integration tests, do not start dev servers, do not run the app, and do not perform manual verification. A separate testing pass owns all of that.
2. UNIT TESTS ARE REQUIRED. Every unit of behaviour you implement gets unit tests, in the project's existing test framework and conventions. Running unit tests IS allowed and expected — that is not a live test.
3. VERIFY TEST STRENGTH WITH MUTATION TESTING. After the unit tests pass, run the project's mutation testing tool over the code you wrote (Stryker.NET for .NET, StrykerJS for TypeScript/JS, PIT for Java). Surviving mutants mean missing assertions — strengthen the tests and re-run. If no mutation tool is configured, configure it minimally, scoped to the files you touched. If it genuinely cannot be run in this project, say so explicitly in your summary rather than skipping silently.
4. STAY IN SCOPE. Only touch the files this task calls for. Another agent may be working in the same repo concurrently — do not refactor, reorganise, or "fix" code outside your task.
5. MATCH THE CODEBASE. Read 2-3 nearby files first and follow their conventions over any default.

# Final output

End your final message with a summary block in exactly this form:

## Summary
<2-4 sentences: what you built, what you tested, and the mutation-testing result. Note anything you deliberately left out.>

Keep it short. The board shows this verbatim.`;
}

export function implementerUserPrompt(run: Run, task: Task): string {
  const answered = run.openQuestions.filter((q) => q.answer);
  const decisions =
    answered.length > 0
      ? `\n\n# Decisions already made\n\n${answered
          .map((q) => `- ${q.question}\n  → ${q.answer!.text}`)
          .join("\n")}`
      : "";

  const done = run.tasks.filter((t) => t.status === "done" && t.summary);
  const context =
    done.length > 0
      ? `\n\n# Already completed in this run\n\n${done
          .map((t) => `- [${t.id}] ${t.title}: ${t.summary}`)
          .join("\n")}`
      : "";

  const deps = task.dependsOn.length > 0 ? task.dependsOn.join(", ") : "none";

  return `# Task ${task.id}: ${task.title}

${task.intent}

## Acceptance criteria
${task.acceptanceCriteria.map((c) => `- ${c}`).join("\n")}

## Files you are expected to touch
${task.files.length > 0 ? task.files.map((f) => `- ${f}`).join("\n") : "- (determine from the task)"}

## Depends on
${deps}

## Skills to load
${task.skills.length > 0 ? task.skills.join(", ") : "(those your agent definition specifies)"}${decisions}${context}

Work in the current directory. Implement the task, write unit tests, verify them with mutation testing, then post your summary.`;
}
