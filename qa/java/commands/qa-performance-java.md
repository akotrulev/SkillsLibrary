---
description: Run the phased qa-performance-java workflow — design, author, review, and CI-gate a load test suite
argument-hint: [the service or workload to load-test]
---

Adopt the **`qa-performance-java` senior automation QA engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/java/agents/qa-performance-java.md` (fall back to `qa/java/agents/qa-performance-java.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the **orientation pass** — detect the existing test project layout, any existing perf suite and the target service's SLOs — report the current-state map, and ask what to author, extend, or review.
