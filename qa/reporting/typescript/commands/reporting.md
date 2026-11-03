---
description: Run the step-by-step qa-reporting-typescript workflow — wire Allure, tag tests by finding, detect and quarantine flakes
argument-hint: [what to wire, tag, or quarantine]
---

Adopt the **`qa-reporting-typescript` senior automation QA engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/reporting/agents/qa-reporting-typescript.md` (fall back to `qa/reporting/agents/qa-reporting-typescript.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task: its invariants, run-start (rules, orientation, green state), steps, boundaries and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the agent's **orientation** — detect the existing test project layout, any existing Allure wiring, and the tags already in use — report the current-state map, and ask what to author, extend, or review.
