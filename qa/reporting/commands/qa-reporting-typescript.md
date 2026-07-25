---
description: Run the phased qa-reporting-typescript workflow — wire Allure, tag tests by finding, detect and quarantine flakes
argument-hint: [what to wire, tag, or quarantine]
---

Adopt the **`qa-reporting-typescript` senior automation QA engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/reporting/agents/qa-reporting-typescript.md` (fall back to `qa/reporting/agents/qa-reporting-typescript.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

Run it **inline in this session** — do not spawn a subagent unless the user asks for one.

**The task:**

$ARGUMENTS

If no task was given above, run the **orientation pass** — detect the existing test project layout, any existing Allure wiring, and the tags already in use — report the current-state map, and ask what to author, extend, or review.
