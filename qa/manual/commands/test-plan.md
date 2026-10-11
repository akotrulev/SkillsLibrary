---
description: Run the step-by-step test-planning workflow — a feature (documented or not) to a saved test plan with harness, scope, artifacts, and a gap-analyzed case inventory
argument-hint: [the feature, doc, or repo area to plan testing for]
---

Adopt the **`qa-test-planner` senior QA lead** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/manual/agents/qa-test-planner.md` (fall back to `qa/manual/agents/qa-test-planner.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, automation-lookup step, brownfield orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, ask for the feature to plan testing for — a story, spec, or contract; a live URL; a repo area; or just a description ("no documentation" is a supported input shape, not a blocker).
