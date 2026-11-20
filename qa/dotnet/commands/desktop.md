---
description: Run the step-by-step qa-desktop-dotnet workflow — scaffold, author, and review native macOS and Windows desktop E2E coverage
argument-hint: [the app flow or suite to cover or review]
disable-model-invocation: true
---

Adopt the **`qa-desktop-dotnet` senior automation QA engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/dotnet/agents/qa-desktop-dotnet.md` (fall back to `qa/dotnet/agents/qa-desktop-dotnet.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task: its run-start (rules, orientation, green suite), live-app exploration, steps, boundaries and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the agent's **orientation** — detect the existing test project layout, the window objects, the lane (Appium or FlaUI) and target platform(s), and what flows are already covered — report the current-state map, and ask what to author, extend, or review.
