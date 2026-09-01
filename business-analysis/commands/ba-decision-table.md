---
description: Model one business decision point (pricing, eligibility, access, fees, routing) as ONE merged DMN-style decision table with a declared hit policy, run the completeness and overlap checks, and persist it to the business-model KB.
argument-hint: [what to apply this skill to]
---

Load and follow the **`ba-decision-table`** skill for this task.

1. `Read` the skill at `${CLAUDE_PLUGIN_ROOT}/business-analysis/skills/ba-decision-table/SKILL.md` (fall back to `business-analysis/skills/ba-decision-table/SKILL.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — do not improvise past what it specifies.

**The task:**

$ARGUMENTS

If no task was given above, ask what to apply this skill to.
