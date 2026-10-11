---
description: Document one feature and write its e2e-only test-case suite from a single trace
argument-hint: [feature sentence + entry points | #<inventory row>]
---

Adopt the **`qa-feature-spec-writer`** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/manual/agents/qa-feature-spec-writer.md` (fall back to `qa/manual/agents/qa-feature-spec-writer.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, step table, e2e rule, and report all apply.
3. Read the sections of `be-feature-documenter.md` and `qa-test-case-designer.md` that definition cites **before** the step that follows them. Do not improvise what they own.

**The task:**

$ARGUMENTS

If no task was given above, ask for the feature: a sentence plus its entry points, or a `docs/features/INVENTORY.md` row number such as `#57`.
