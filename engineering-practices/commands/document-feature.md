---
description: Document a feature — locate ONE described feature in the codebase, trace it end to end, and write three docs/features/ documents from one trace — a plain-language client guide (overview, scope, setup, how it works as triggers -> steps -> formulas, a full worked example, open questions), a plain-language behind-the-scenes account of how the parts connect, and a technical reference for developers and AI with every claim file:line-evidenced
argument-hint: [the feature to document, in your own words — e.g. "the refund flow" or "password reset"]
---

Adopt the **`be-feature-documenter` feature documentation** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/backend/_shared/agents/be-feature-documenter.md` (fall back to `backend/_shared/agents/be-feature-documenter.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its invariants, "Every run, before writing anything" (the `feature-docs.md` rule file, the orientation pass, existing coverage), steps, Step 4 checklist, document contract, boundaries and report all apply.
3. Load the skills its Steps table names for the step you are in **before** producing the artifact they own — `dev:doc-feature-trace` is the tracing engine (skip nothing in its 10-stop path); `dev:doc-business-model`'s three level shapes and golden examples fix how the documents read.

**Four rules that override any instinct to be helpful:**

- **Read-only on the codebase.** Your write reach is `docs/features/**` and `docs/agent-context/be-feature-documenter.md`. Not one line of source — even to fix something obviously broken that you find along the way.
- **Never invent a purpose.** Separate what the code *does* (`#observed`, with `file:line` read this session) from what it is probably *for* (`#inferred`). Never write `#confirmed`. Every `#inferred` intent is also an open question.
- **Three levels, one trace.** `<NNN>-<slug>.md` is the client guide: plain language, no technical talk — overview → setup → how it works (one flow per trigger, numbered steps, formulas as plain-text math, the result for the user) → a full worked example with real numbers you recomputed → open questions. `.behind-the-scenes.md` is still plain language: the parts, who tells whom, straight away vs later, what is remembered where, what happens when a part fails. `.technical.md` is for developers and AI: exact names, contracts, data, Findings, and the evidence index — the only place for `file:line`, tier tags and code nouns.
- **The Step 1 gate is proportional.** One unambiguous implementation match → show the scope table and proceed; multiple candidates or a fuzzy match → stop and ask before tracing anything.

**The feature to document:**

$ARGUMENTS

If no feature was given above, ask for one — this agent documents a described feature, not a whole system (that is `/dev:document-system`).
