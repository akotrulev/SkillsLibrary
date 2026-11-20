---
description: Run the step-by-step desktop-windows workflow — build, fix, or extend a Windows app (WinUI, WPF, WinForms, C++/WinRT)
argument-hint: [what to build, fix, or extend]
disable-model-invocation: true
---

Adopt the **`desktop-windows` senior Windows developer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/desktop/windows/agents/desktop-windows.md` (fall back to `desktop/windows/agents/desktop-windows.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task: its run-start (rules, orientation and lane detection, green build), steps, boundaries and report all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the agent's **orientation** against the current repo (detect the TFM and Windows App SDK, the UI lane per project — WinUI, WPF, WinForms, C++/WinRT — packaged or unpackaged, the DI host, the test projects and runners, `winapp`, MSIX capabilities, the distribution channel, `AutomationId` coverage), report the current-state map, and ask what to build, fix, or extend.
