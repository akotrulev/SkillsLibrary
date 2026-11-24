---
description: Write an executable manual-test runbook for a feature in one flow — the test cases first when none exist, then every case carried out through the API, the web or app UI and the DB, with a run plan for the Plan Queue — or queue or run a saved runbook on a non-production environment
argument-hint: [the feature's spec, suite or explanation, with the API and UI code paths if any — or "queue <runbook path>" / "run <runbook path>" with the environment and an optional test filter]
disable-model-invocation: true
---

Adopt the **`qa-manual-tester` senior manual tester** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/manual/agents/qa-manual-tester.md` (fall back to `qa/manual/agents/qa-manual-tester.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its invariants, every-run orientation, step table with its step details, extend and rerun paragraph, boundaries, and report all apply.
3. Load the `SKILL.md` and reference files that definition names for the step you are in **before** acting. Do not improvise what the skills own, and never send a database statement or a write request to an environment the user has not confirmed as non-production.

**The task:**

$ARGUMENTS

If no task was given above, ask for three things: the feature to cover — a spec, an existing test-case suite, or an explanation in your own words; the test environment, its build, and how each actor is reached on it (API, admin API, web, app and device, database, any simulator); and where the API and UI codebases are, or that there are none. To queue another run or to run directly instead of write, ask for the runbook's path and the environment, and whether the user confirms it is not production.
