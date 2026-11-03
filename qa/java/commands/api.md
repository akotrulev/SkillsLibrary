---
description: Run the step-by-step qa-api-java workflow — scaffold, author, and review API test coverage
argument-hint: [the endpoints or suite to cover or review]
---

Adopt the **`qa-api-java` senior automation QA engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/java/agents/qa-api-java.md` (fall back to `qa/java/agents/qa-api-java.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task: its run-start (rules, orientation, green build), steps, boundaries and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the agent's **orientation** — detect the existing test project layout, the API surface under test, and what coverage already exists — report the current-state map, and ask what to author, extend, or review.
