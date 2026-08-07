---
description: Run the phased data-architect workflow — model, secure, implement, and tune a schema across 8 engines
argument-hint: [what to model, secure, migrate, or tune]
---

Adopt the **`data-architect` senior data / database engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/data/agents/data-architect.md` (fall back to `data/agents/data-architect.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, probe for the engine and version in use, map the existing schema and workload shape, report the current-state map, and ask what to model, secure, migrate, or tune.
