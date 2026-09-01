---
description: Read, initialise or refresh the project's business-model knowledge base (docs/business-model/) — the read-first / update-after protocol every reasoning-lane skill follows; inventory it, create it, or reconcile it against changed sources.
argument-hint: [inventory | init | refresh, or a question about what the KB already records]
---

Load and follow the **`ba-project-memory`** skill for this task.

1. `Read` the skill at `${CLAUDE_PLUGIN_ROOT}/business-analysis/skills/ba-project-memory/SKILL.md` (fall back to `business-analysis/skills/ba-project-memory/SKILL.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — do not improvise past what it specifies. Write only under `docs/business-model/` of the current project.

**The task:**

$ARGUMENTS

If no task was given above: report whether `docs/business-model/INDEX.md` exists; if it does, inventory the KB (artifact counts by type, ID ranges, staleness signals) and ask whether to refresh it; if it does not, offer to initialise it per the skill.
