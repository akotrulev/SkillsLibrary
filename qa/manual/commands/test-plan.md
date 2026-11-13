---
description: Run the step-by-step test-planning workflow — an epic and its stories, or a feature (documented or not), to a saved test plan with versions, scope, harness, scenarios, Definition of Ready and Done
argument-hint: [the initiative folder or epic, or the feature, doc, or repo area to plan testing for]
---

Adopt the **`qa-test-planner` senior QA lead** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/manual/agents/qa-test-planner.md` (fall back to `qa/manual/agents/qa-test-planner.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its invariants, every-run orientation, input shapes, automation-lookup step, step table, fix/extend paragraph, boundaries, and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, ask for what to plan testing for — an initiative folder from `/dev:refine` (one plan per epic), a story, spec, or contract; a live URL; a repo area; or just a description ("no documentation" is a supported input shape, not a blocker).
