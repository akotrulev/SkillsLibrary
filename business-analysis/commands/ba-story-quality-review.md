---
description: Use when stories or epics were authored by someone else (client, another team, a PO) and need a review-only readiness audit before refinement or test design — INVEST, AC quality, testability, dependency hygiene; never rewrites.
argument-hint: [the stories/epics to review, and the purpose: sprint readiness, refinement intake, or pre-test-design]
---

Load and follow the **`ba-story-quality-review`** skill for this task.

1. `Read` the skill at `${CLAUDE_PLUGIN_ROOT}/business-analysis/skills/ba-story-quality-review/SKILL.md` (fall back to `business-analysis/skills/ba-story-quality-review/SKILL.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — do not improvise past what it specifies. Review only: point to the fix and name the skill that applies it.

**The task:**

$ARGUMENTS

If no task was given above, ask for the stories or epics to review and the purpose of the review.
