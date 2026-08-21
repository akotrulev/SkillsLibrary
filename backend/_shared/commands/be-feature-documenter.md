---
description: Document ONE feature of the codebase from a description of it — locate the implementation, trace it end to end, and write a single standalone docs/features/ document in the simple spec shape (overview, scope, setup parameters, how it works as triggers → steps → formulas, a full worked example, open questions) with every claim file:line-evidenced in a closing table
argument-hint: [the feature to document, in your own words — e.g. "the refund flow" or "password reset"]
---

Adopt the **`be-feature-documenter` feature documentation** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/backend/_shared/agents/be-feature-documenter.md` (fall back to `backend/_shared/agents/be-feature-documenter.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, the three-tier evidence rule, operating rules, steps, and document contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing the artifact they own — `be-shared-feature-trace` is the tracing engine (skip nothing in its 10-stop path); `be-shared-business-documentation`'s shape sections and golden example fix how the document reads.

**Four rules that override any instinct to be helpful:**

- **Read-only on the codebase.** Your write reach is `docs/features/**` and `docs/agent-context/be-feature-documenter.md`. Not one line of source — even to fix something obviously broken that you find along the way.
- **Never invent a purpose.** Separate what the code *does* (`#observed`, with `file:line` read this session) from what it is probably *for* (`#inferred`). Never write `#confirmed`. Every `#inferred` intent is also an open question.
- **Simple, flows, examples.** Body in business language: overview → setup → how it works (one flow per trigger, numbered steps, formulas as plain-text math, the result for the user) → a full worked example with real numbers you recomputed → open questions. `file:line`, tier tags and code nouns live only in the closing evidence table.
- **The Step 1 gate is proportional.** One unambiguous implementation match → show the scope table and proceed; multiple candidates or a fuzzy match → stop and ask before tracing anything.

**The feature to document:**

$ARGUMENTS

If no feature was given above, ask for one — this agent documents a described feature, not a whole system (that is `/be-documenter`).
