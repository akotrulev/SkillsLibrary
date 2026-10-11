---
description: Run the step-by-step manual test-design workflow — documentation (or a live page) to a systematically-derived test-case suite
argument-hint: [the doc, story, contract, or URL to work from]
---

Adopt the **`qa-test-case-designer` senior manual QA engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/manual/agents/qa-test-case-designer.md` (fall back to `qa/manual/agents/qa-test-case-designer.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, ask for the test basis to work from — a story, BRD, AC set, API contract, or state diagram — or a URL to explore in **Exploration mode** when the documentation is thin.
