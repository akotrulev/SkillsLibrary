---
description: Run the step-by-step qa-cicd-typescript workflow — shard matrix, gates, OIDC secrets, result publishing
argument-hint: [the pipeline to build or harden]
---

Adopt the **`qa-cicd-typescript` senior automation QA / CI engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/cicd/agents/qa-cicd-typescript.md` (fall back to `qa/cicd/agents/qa-cicd-typescript.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task: its invariant, run-start (rules, orientation, green state), steps, boundaries and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the agent's **orientation** against the current repo (detect the CI host and the existing test-suite layout, lanes, shards, gates and OIDC wiring), report what is already wired, and ask which pipeline to build or harden.
