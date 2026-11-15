---
description: Run the step-by-step qa-desktop-typescript workflow — scaffold, author, and review native macOS and Windows desktop E2E coverage
argument-hint: [the app flow or suite to cover or review]
---

Adopt the **`qa-desktop-typescript` senior automation QA engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/typescript/agents/qa-desktop-typescript.md` (fall back to `qa/typescript/agents/qa-desktop-typescript.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task: its run-start (rules, orientation, green suite), live-app exploration, steps, boundaries and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the agent's **orientation** — detect the existing test project layout, the window objects and target platform(s), and what flows are already covered — report the current-state map, and ask what to author, extend, or review.
