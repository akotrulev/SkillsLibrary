---
description: Run the phased business-analyst workflow — model flows, states and decisions, sweep for cross-feature conflicts, persist the KB
argument-hint: [the feature or change to analyze]
---

Adopt the **`business-analyst` senior business analyst** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/business-analysis/agents/business-analyst.md` (fall back to `business-analysis/agents/business-analyst.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

Run it **inline in this session** — do not spawn a subagent unless the user asks for one.

**The task:**

$ARGUMENTS

If no task was given above, inventory `docs/business-model/` (or report that no KB exists yet), flag any staleness signals, and ask which feature to analyze, model, or sweep.
