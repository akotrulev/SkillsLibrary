---
description: Refine — turn a loose description of something to build into requirements.md, epics.md and stories.md in a new initiative folder; the front door to the delivery lane (next: /dev:plan-system)
argument-hint: [a description of what you want built, or a brief/backlog to work from]
---

Adopt the **`requirements-author`** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/business-analysis/agents/requirements-author.md` (fall back to `business-analysis/agents/requirements-author.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, orientation pass, mode table, steps, id scheme and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

Write into a **new initiative folder** at `docs/plans/<NNN>-<initiative>/` under the current project's root — `requirements.md`, then `epics.md` (`E1..En`), then `stories.md` (`US1..USn`) — and hand off to `/dev:plan-system` with that path.

**The ask:**

$ARGUMENTS

If nothing was given above, ask what the user wants built, in their own words — a paragraph is enough. Then run Step 1's question batch against it.
