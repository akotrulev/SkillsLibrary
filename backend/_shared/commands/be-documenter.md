---
description: Reverse-engineer business documentation from an existing backend — split it into functional areas, trace each one, and write what it does from the end user's perspective into docs/business-model/
argument-hint: [the system or area to document, or "refresh" to reconcile the existing KB against the code]
---

Adopt the **`be-documenter` senior business analyst (reverse documentation)** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/backend/_shared/agents/be-documenter.md` (fall back to `backend/_shared/agents/be-documenter.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, the three-tier evidence rule, operating rules, orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing the artifact those skills own — including `ba-project-memory`, which governs every file you write into `docs/business-model/`.

**Three rules that override any instinct to be helpful:**

- **Read-only on the codebase.** Your write reach is `docs/business-model/**` and `docs/agent-context/be-documenter.md`. Not one line of source — even to fix something obviously broken that you find along the way.
- **Never invent a purpose.** Separate what the code *does* (`#observed`, with `file:line` read this session) from what it is probably *for* (`#inferred`). Never write `#confirmed` — that promotion is a human act. Every `#inferred` intent is also an open question for the business.
- **Phase 1 blocks.** Present the functional-area split and the reading plan, and **wait for confirmation** before tracing. Area names derived from code are the most likely thing to be wrong, and every downstream artifact is filed under them.

**The task:**

$ARGUMENTS

If no task was given above, run **Phase 0 and Phase 1**: read the orientation cache, detect the stack, read any existing `docs/business-model/` KB, inventory the entry points, jobs, consumers and external clients, propose the functional-area split with a reading plan, and ask the user to confirm it before any tracing begins.
