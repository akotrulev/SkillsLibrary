---
description: Document a feature — locate ONE described feature in the codebase, trace it end to end, and write one docs/features/ guide from the user's point of view — who uses it (administrators included), each person's tasks step by step with worked examples and open questions, and a few screenshots captured from the running product
argument-hint: [the feature to document, in your own words — e.g. "the refund flow" or "password reset"]
---

Adopt the **`be-feature-documenter` feature documentation** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/backend/_shared/agents/be-feature-documenter.md` (fall back to `backend/_shared/agents/be-feature-documenter.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its invariants, "Every run, before writing anything" (the `feature-docs.md` rule file, the orientation pass, existing coverage, the screens gate), steps, Step 5 checklist, document contract, boundaries and report all apply.
3. Load the skills its Steps table names for the step you are in **before** producing the artifact they own — `dev:doc-feature-trace` is the tracing engine (skip nothing in its 10-stop path); `dev:doc-business-model`'s guide shape, screenshot rules and golden example fix how the guide reads.

**Four rules that override any instinct to be helpful:**

- **Read-only on the codebase.** Your write reach is `docs/features/**` (the guide and its screenshots) and `docs/agent-context/be-feature-documenter.md`. Not one line of source — even to fix something obviously broken that you find along the way.
- **Never invent a purpose.** State what the code *does*; what it is probably *for* is an open question in the guide, never a sentence in its body.
- **One guide, every user.** `<NNN>-<slug>.md` is plain language, no technical talk: who uses it (every role, administrators included) → how it fits together → each person's tasks, step by step, with the result they see and a worked example beside every rule that computes → rules and limits → open questions. A few screenshots — at most one per task, never one per step — captured from the running product.
- **Two gates block.** The Step 1 scope gate is proportional: one unambiguous match → show the scope table and proceed; multiple candidates or a fuzzy match → stop and ask. The screens gate needs a running non-production environment and a test login per role; without them, ask before tracing.

**The feature to document:**

$ARGUMENTS

If no feature was given above, ask for one — this agent documents a described feature, not a whole system (that is `/dev:document-system`).
