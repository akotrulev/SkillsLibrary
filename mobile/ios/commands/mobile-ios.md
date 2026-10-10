---
description: Run the step-by-step mobile-ios workflow — build, fix, or extend an iOS app (Swift, SwiftUI, UIKit)
argument-hint: [what to build, fix, or extend]
---

Adopt the **`mobile-ios` senior iOS developer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/mobile/ios/agents/mobile-ios.md` (fall back to `mobile/ios/agents/mobile-ios.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the brownfield **orientation pass** against the current repo (detect Xcode and Swift versions, the language mode and default isolation per module, the deployment target, SwiftUI vs UIKit share, the persistence and dependency-manager lanes, extensions, `accessibilityIdentifier` coverage), report the current-state map, and ask what to build, fix, or extend.
