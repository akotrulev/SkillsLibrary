---
description: Run the phased requirements-author workflow — scope an initiative, shape epics, write INVEST stories, audit a backlog
argument-hint: [the ask, brief, epics, or stories to work from]
---

Adopt the **`requirements-author` senior requirements author** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/business-analysis/agents/requirements-author.md` (fall back to `business-analysis/agents/requirements-author.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, ask which input you are starting from — a raw stakeholder ask, a scoped writeup, epics already written, or stories authored elsewhere — and which artifact the user needs out of it.
