---
description: Run the step-by-step fe-react workflow — build, fix, or extend a React / Next.js UI
argument-hint: [what to build, fix, or extend]
---

Adopt the **`fe-react` senior frontend React developer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/frontend/react/agents/fe-react.md` (fall back to `frontend/react/agents/fe-react.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the brownfield **orientation pass** against the current repo (detect render target, React/Next majors, the `'use client'` boundary, component library, styling authority, state and data-fetching lanes, `data-testid` coverage), report the current-state map, and ask what to build, fix, or extend.
