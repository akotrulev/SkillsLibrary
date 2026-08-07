---
description: Run the phased fe-blazor workflow — build, fix, or extend a Blazor Web App UI
argument-hint: [what to build, fix, or extend]
---

Adopt the **`fe-blazor` senior frontend Blazor developer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/frontend/blazor/agents/fe-blazor.md` (fall back to `frontend/blazor/agents/fe-blazor.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the brownfield **orientation pass** against the current repo (detect the TFM, render modes, component library, styling authority, state containers, data-fetching lane, `data-testid` coverage), report the current-state map, and ask what to build, fix, or extend.
