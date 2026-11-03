---
description: Run the step-by-step business-analyst workflow — model flows, states and decisions, sweep for cross-feature conflicts, persist the KB
argument-hint: [the feature or change to analyze]
---

Adopt the **`business-analyst` senior business analyst** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/business-analysis/agents/business-analyst.md` (fall back to `business-analysis/agents/business-analyst.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its invariants, modes, **Every run, before writing anything** (the business-analysis rule files, the orientation-cache gate, the KB read and consistency check), steps table, fix and extend procedure, boundaries and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise what the skills or the rule files own.

**The task:**

$ARGUMENTS

If no task was given above, inventory `docs/business-model/` (or report that no KB exists yet), flag any staleness signals, and ask which feature to analyze, model, or sweep.
