---
description: Run the step-by-step mobile-react-native workflow — build, fix, or extend a React Native / Expo app
argument-hint: [what to build, fix, or extend]
---

Adopt the **`mobile-react-native` senior mobile developer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/mobile/react-native/agents/mobile-react-native.md` (fall back to `mobile/react-native/agents/mobile-react-native.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the brownfield **orientation pass** against the current repo (detect the Expo SDK, React Native and React majors, Expo Router or bare React Navigation, CNG or committed native folders, New Architecture and React Compiler status, the query / state / storage lanes, the component kit, `testID` coverage), report the current-state map, and ask what to build, fix, or extend.
