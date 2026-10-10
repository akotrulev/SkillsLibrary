---
description: Run the step-by-step mobile-android workflow — build, fix, or extend an Android app (Kotlin, Jetpack Compose, Views, KMP)
argument-hint: [what to build, fix, or extend]
---

Adopt the **`mobile-android` senior Android developer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/mobile/android/agents/mobile-android.md` (fall back to `mobile/android/agents/mobile-android.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the brownfield **orientation pass** against the current repo (detect Kotlin, AGP and Gradle versions, compile / target / min SDK, Compose vs Views share, KSP vs kapt, the DI and persistence lanes, Kotlin Multiplatform modules, `testTag` coverage), report the current-state map, and ask what to build, fix, or extend.
