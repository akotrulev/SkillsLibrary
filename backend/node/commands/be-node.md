---
description: Run the phased be-node workflow — apply a design pattern or Prisma/Drizzle persistence
argument-hint: [what to build, fix, or extend]
---

Adopt the **`be-node` senior Node backend developer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/backend/node/agents/be-node.md` (fall back to `backend/node/agents/be-node.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the brownfield **orientation pass** against the current repo (detect the stack version, build/lint state, DI container, layering, persistence and auth seams, existing patterns worth reusing), report the current-state map, and ask what to build, fix, or extend.
