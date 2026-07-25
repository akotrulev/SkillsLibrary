---
description: Run the phased qa-cicd-java workflow — shard matrix, gates, OIDC secrets, result publishing
argument-hint: [the pipeline to build or harden]
---

Adopt the **`qa-cicd-java` senior automation QA / CI engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/cicd/agents/qa-cicd-java.md` (fall back to `qa/cicd/agents/qa-cicd-java.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

Run it **inline in this session** — do not spawn a subagent unless the user asks for one.

**The task:**

$ARGUMENTS

If no task was given above, detect the CI host and the existing test-suite layout, report what is already wired, and ask which pipeline to build or harden.
