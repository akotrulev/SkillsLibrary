---
description: Design — turn one feature with clear requirements into an approved technical design/spec in docs/specs/ before any code is written (next: /dev-plan-feature). For a loose or multi-capability ask use /dev-refine instead.
argument-hint: [the feature to design]
---

Load and follow the **`ep-brainstorming`** skill for this task.

1. `Read` the skill at `${CLAUDE_PLUGIN_ROOT}/engineering-practices/brainstorming/SKILL.md` (fall back to `engineering-practices/brainstorming/SKILL.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — do not improvise past what it specifies.

**The task:**

$ARGUMENTS

If no task was given above, ask which feature to design. If the answer is several capabilities, or its requirements are still open, route to `/dev-refine` instead.
