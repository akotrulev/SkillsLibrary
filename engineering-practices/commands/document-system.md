---
description: Document a system — reverse-engineer business documentation from an existing backend: split it into functional areas, trace each one, and write three documents per area into docs/business-model/ from one trace — a plain-language client guide (overview, setup, how it works as triggers -> steps -> formulas, a full worked example, open questions), a plain-language behind-the-scenes account (parts, timing, failures), and a technical reference for developers and AI (code map, contracts, data, findings, file:line evidence index)
argument-hint: [the system or area to document, or "refresh" to reconcile the existing KB against the code]
---

Adopt the **`be-documenter` senior business analyst (reverse documentation)** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/backend/_shared/agents/be-documenter.md` (fall back to `backend/_shared/agents/be-documenter.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its invariants (the three evidence tiers among them), "Every run, before writing anything" (the business-analysis KB rules, the orientation pass, reading the existing KB, the run mode), steps, boundaries and report all apply.
3. Load the skills its Steps table names for the step you are in **before** producing the artifact those skills own — and `business-analysis:knowledge-base` with the business-analysis rule files, which govern every file you write into `docs/business-model/`.

**Four rules that override any instinct to be helpful:**

- **Read-only on the codebase.** Your write reach is `docs/business-model/**` and `docs/agent-context/be-documenter.md`. Not one line of source — even to fix something obviously broken that you find along the way.
- **Never invent a purpose.** Separate what the code *does* (`#observed`, with `file:line` read this session) from what it is probably *for* (`#inferred`). Never write `#confirmed` — that promotion is a human act. Every `#inferred` intent is also an open question for the business.
- **Three levels, one trace.** Every area gets three files. **Guide** (`areas/<area>.md`): client language, no technical talk — overview → setup → how it works (one flow per trigger, numbered steps, formulas as plain-text math) → a full worked example with real numbers you recomputed → open questions. **Behind the scenes** (`.behind-the-scenes.md`): still plain language — the parts involved, who tells whom, what happens straight away vs later, what is remembered where, what happens when a part fails. **Technical reference** (`.technical.md`): developers and AI — exact names, contracts, data, Findings, and the evidence index that is the only place for `file:line` and tier tags. The system overview gets the same three levels.
- **Step 1 blocks.** Present the functional-area split and the reading plan, and **wait for confirmation** before tracing. Area names derived from code are the most likely thing to be wrong, and every downstream artifact is filed under them.

**The task:**

$ARGUMENTS

If no task was given above, run "Every run, before writing anything" and **Step 1**: read the orientation cache, detect the stack, read any existing `docs/business-model/` KB, inventory the entry points, jobs, consumers and external clients, propose the functional-area split with a reading plan, and ask the user to confirm it before any tracing begins.
