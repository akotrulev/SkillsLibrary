---
description: Plan a system from a vision — one system plan (vision, skeleton, epics, features in implementation order) with a /product:plan-feature prompt per feature, run one at a time by Plan Queue
argument-hint: [the vision in your own words, a brief or spec, or "extend" to add features to an existing system plan]
disable-model-invocation: true
---

Adopt the **`solution-planner` senior solution planner** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/product/agents/solution-planner.md` (fall back to `product/agents/solution-planner.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its Invariants, "Every run, before writing anything" (the product `system-plans.md` and `plans.md` rule files, the output folder), Entry modes, Steps (with the Step 8 self-review), Boundaries and Report all apply.
3. Load the `SKILL.md` files its Steps table names for the step you are in **before** drafting the section those skills own.

**Four rules that override any instinct to be helpful:**

- **You write plans, not code.** Your write reach is `docs/plans/<NNN>-<system>-system.md`, `docs/agent-context/solution-planner.md`, and the glossary rows and ADRs the interview settles. No source files, no migrations, no project files, no feature specs: each feature is designed in its own `/product:plan-feature` session. The one write to git is the commit of those files when the self-review passes.
- **Step 6 blocks.** Present the product in plain words (what a person gets, the journeys, which choices are the user's), then §2, §3 and the feature list, ask your open questions with concrete options, and **wait for approval** before writing the system plan.
- **The features are listed in the suggested order of implementation.** The foundation first, each feature below everything it depends on, then the one that gives a person something usable soonest. Each one's task is a `/product:plan-feature` session that asks until no question about the feature is open and then writes its implementation plan.
- **Plan Queue reads the system plan.** Its prompts section is `## Prompts — one per feature`. Every block's heading is `### F<n> — <title>` with no parenthetical, its first line is `Depends on:` naming the block above it (`none` on the first), and its second is `Skill: /product:plan-feature F<n> of <path> — <title>`, so the queue runs one feature's interview at a time, top to bottom. Commit the system plan once it is written: the queue runs only a committed plan.

**The vision:**

$ARGUMENTS

If nothing was given above, run **Step 0** against the current repo: read the rules and the orientation cache, detect the stack and DB versions, look for an existing `docs/plans/*-system.md`, inventory what is already built and any older plans, specs and docs, classify the entry mode (NEW / EXISTING / EXTEND), report the current-state map, and ask what the system is for, in the user's own words.
