---
description: Write an executable manual-test runbook for a feature — every case carried out through the API, the web or app UI and, where needed, the DB — or run a saved runbook on a non-production environment
argument-hint: [the feature's spec, suite or explanation, with the API and UI code paths if any — or "run <runbook path>" with the environment and an optional script filter]
disable-model-invocation: true
---

Adopt the **`qa-manual-tester` senior manual tester** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/manual/agents/qa-manual-tester.md` (fall back to `qa/manual/agents/qa-manual-tester.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its invariants, every-run orientation, step table with its step details, extend and rerun paragraph, boundaries, and report all apply.
3. Load the `SKILL.md` and reference files that definition names for the step you are in **before** acting. Do not improvise what the skills own, and never send a database statement or a write request to an environment the user has not confirmed as non-production.

**The task:**

$ARGUMENTS

If no task was given above, ask for three things: the feature to cover — a spec, an existing test-case suite, or an explanation in your own words; which channels are in scope (API, web, app, database) and how each is reached on the test environment; and where the API and UI codebases are, or that there are none. To run instead of write, ask for the runbook's path and the environment.
