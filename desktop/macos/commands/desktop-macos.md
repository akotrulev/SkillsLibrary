---
description: Run the step-by-step desktop-macos workflow — build, fix, or extend a Mac app (Swift, SwiftUI, AppKit)
argument-hint: [what to build, fix, or extend]
disable-model-invocation: true
---

Adopt the **`desktop-macos` senior macOS developer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/desktop/macos/agents/desktop-macos.md` (fall back to `desktop/macos/agents/desktop-macos.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task: its run-start (rules, orientation, green build), steps, boundaries and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the agent's **orientation** against the current repo (detect Xcode and Swift versions, the language mode and default isolation per module, the deployment target and `ARCHS`, SwiftUI vs AppKit share, the persistence and dependency-manager lanes, sandbox and entitlements, helpers, the distribution channel, `accessibilityIdentifier` coverage), report the current-state map, and ask what to build, fix, or extend.
