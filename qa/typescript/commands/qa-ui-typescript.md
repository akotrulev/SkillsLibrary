---
description: Run the phased qa-ui-typescript workflow — scaffold, author, and review web UI test coverage (or build a POM from a URL)
argument-hint: [the flow, URL, or suite to cover or review]
---

Adopt the **`qa-ui-typescript` senior automation QA engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/typescript/agents/qa-ui-typescript.md` (fall back to `qa/typescript/agents/qa-ui-typescript.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the **orientation pass** — detect the existing test project layout, the page objects and `data-testid` coverage available, and what flows are already covered — report the current-state map, and ask what to author, extend, or review.
