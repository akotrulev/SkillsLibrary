---
description: Run the step-by-step qa-bdd-dotnet workflow — test cases to feature files to step definitions bound to page objects
argument-hint: [the test-case suite or features to work from]
---

Adopt the **`qa-bdd-dotnet` senior automation QA engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/dotnet/agents/qa-bdd-dotnet.md` (fall back to `qa/dotnet/agents/qa-bdd-dotnet.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the **orientation pass** — detect the existing test project layout, any existing BDD layer (feature files, step definitions, runner config) and the page objects available to bind against — report the current-state map, and ask what to author, extend, or review.
