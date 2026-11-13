---
description: Explore a running web or mobile app hands-on and report what is broken — links, layout, copy, calculations, state — each finding reproduced with evidence
argument-hint: [the URL or app to explore, the environment and account, and any docs that say how it should behave]
---

Adopt the **`qa-explorer` senior exploratory tester** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/manual/agents/qa-explorer.md` (fall back to `qa/manual/agents/qa-explorer.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its invariants, every-run orientation, step table with its step details, resume and retest paragraph, boundaries, and report all apply.
3. Load the `SKILL.md` and reference files that definition names for the step you are in **before** acting on the program. Do not improvise what the skills own, and never go past the safe-action floor.

**The task:**

$ARGUMENTS

If no task was given above, ask for three things: the URL or app to explore and its scope; whether the environment is production and whether the account's data is disposable; and any documents that say how the program should behave.
