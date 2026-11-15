---
name: conventions-review
description: Use when reviewing a Swift, SwiftUI or AppKit Mac diff against plugin conventions, plus a window screenshot pass. Triggers "review this PR". Not for a whole-repo audit (standards-audit).
---

# macOS — Code Review

A **hostile review of one diff** against the desktop-macos rule files, then a **screenshot pass** on the running app. Findings go in the standard severity table; the review **does not rewrite**: it points, and the `desktop-macos` agent (or the author) fixes. A whole-repo sweep with a saved report is [`standards-audit`](../standards-audit/SKILL.md).

## The checklist is the rule files

Every check, and the severity it reports, lives in one place: the desktop-macos rule files: `swift.md` (core), `swiftui-mac.md`, `appkit.md`, `mac-accessibility.md`, `mac-styling.md`, `mac-localization.md`, `swift-networking.md`, `swift-persistence.md`, `swift-tests.md` and `xcode-config.md`.

1. **The project's copies first**: `.claude/rules/desktop-macos/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `desktop/macos/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/desktop-macos:rules` installs them.

Read `swift.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. A view in a folder no glob covers still gets `swiftui-mac.md`, `mac-accessibility.md`, `mac-styling.md` and `mac-localization.md`; judge by what the file is, not by whether its path matched. A rule loaded on its own by the session is not enough: a review needs every file that applies. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

## Version lane

Detect before flagging: Xcode and Swift (`xcodebuild -version`, `swift-tools-version`), `SWIFT_VERSION` and default isolation **per target**, `MACOSX_DEPLOYMENT_TARGET` and `ARCHS`, SwiftUI vs AppKit for the files in the diff, SwiftData / Core Data / GRDB, SPM vs CocoaPods vs Tuist, and the distribution channel (Developer ID, Mac App Store, both). The rule files' "the codebase wins" line applies: a convention the project follows consistently is not a finding.

| Lane | Review consequence |
|---|---|
| **Xcode 27 · Swift 6 · macOS 15** | The rules as written |
| macOS 14 target | `@Observable`, SwiftData, `inspector`, `onKeyPress` and `openSettings` are available; `UtilityWindow` and `defaultWindowPlacement` need an `#available` gate |
| macOS 13 target | `NavigationSplitView`, `Window`, `MenuBarExtra` and `SMAppService` are the floor; `@Observable` is a finding only when added without a gate, and `ObservableObject` is correct |
| Swift 5-mode module | Swift 6 concurrency rules are advice for the module's own migration run, not findings on a feature diff; a *new* module in Swift 5 mode is a finding |
| AppKit file | `appkit.md` applies; a SwiftUI rule is not flagged on an AppKit window, and an AppKit codebase is not asked to convert |
| **[mac27SDK]** | A 27-SDK-only API in a diff that builds on 26 is a finding; `FileDocument` in new code on the 27 SDK is a minor |
| **[MAS]** / **[DevID]** | Mac App Store builds: no updater, no licence keys, sandboxed; Developer ID: Hardened Runtime, notarization, a Sparkle EdDSA feed |
| Below macOS 13 | One finding plus a [`migration`](../migration/SKILL.md) run |

## When to use

- A `.swift` / `Info.plist` / `.entitlements` / `.xcconfig` / `Package.swift` / `.xcprivacy` / `.xcstrings` diff, before merge
- Step 5 of the agent: the whole change set, after the quality layers
- "Why does this hang on wake / lose its window / get rejected by notarization?"

## When NOT to use

- Whole codebase, saved re-runnable report → [`standards-audit`](../standards-audit/SKILL.md)
- Explaining a concept → [`basics`](../basics/SKILL.md); writing code → the owning feature skill
- Reviewing **E2E test code** (Mac2, XCUITest) → peer `qa-desktop-java` / `qa-desktop-dotnet` / `qa-desktop-typescript`
- Pen-test or runtime security → peer `qa-security`
- A spec-versus-code audit → `code-auditor`

## Inputs needed

1. **The diff** (files or `git diff` range) and the windows and commands it touches
2. **Lane facts** above, from the project and the module's settings
3. **Whether the app can be built and launched** for the screenshot pass

## Procedure

1. **Read the rule files** that apply (above), then each changed file end to end. Over a large diff, the *Find it with* recipes in [`conformance-checklist.md`](../standards-audit/references/conformance-checklist.md) are useful search leads; its rows are not extra checks.
2. **Walk the rules in this order**: safety and concurrency (`swift.md`), secrets, entitlements and sandbox, unvalidated URL, XPC or pasteboard input, persistence migrations, then the rest. Most blockers live there.
3. **Read the code at every hit.** A grep hit is a lead, not a finding. Load the owning feature skill when a rule's application is ambiguous.
4. **Per finding**: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment. One row per defect family with a count, not per site.
5. **Run the screenshot pass** (below) if the app builds and launches; otherwise say it was not run.
6. **Do not rewrite.** Hand off (below).

## The screenshot pass (Step 5)

Only when the app builds and launches; otherwise report "screenshot pass not run" and why.

```bash
screencapture -l <windowid> mac-<window>.png
```

`-l` takes a CGWindowID, not an AppleScript window id: read it from `CGWindowListCopyWindowInfo` (`kCGWindowNumber`, filtered by `kCGWindowOwnerName`) in a short Swift script kept in the scratch folder, or use a window-listing tool the project already has. Screen Recording permission must be granted to the terminal; without it the capture is blank, which is "screenshot pass not run", not a pass. `Read` each image. Capture the changed windows in **light and dark**, at the **smallest supported window size** and a large one, with **Increase Contrast** and **Reduce Transparency** on where the diff touches surfaces, in each of loading, loaded, failed and empty where the diff changes them. Check against the diff, not against taste: the toolbar and sidebar left to Liquid Glass (no custom bar backgrounds), text truncation at small sizes and with longer translations, contrast, control sizes and density, the inline error banner position inside the window content, menu-bar commands present and disabled rather than hidden, platform-native controls (no web or iOS look). Cite the `design/ux-review` heuristic and the corpus row (`design/ui-ux-pro-max --stack swiftui`) behind each visual finding. Save images only under a scratch folder inside the worktree and delete them before committing.

## Output format

```
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| blocker  | Sources/Library/ImportService.swift:41 | `URL(string: payload.path)!` on a value from an XPC message, then read through the sandbox with no validation | Validate the bookmark and the scheme per `sandbox-and-permissions`; no force unwrap |
| major    | Sources/Library/LibraryCommands.swift:18 | `if model.hasSelection { Button("Archive") … }` hides the command | `.disabled(!model.hasSelection)` per `menus-and-commands` |
```

Close with the lane line (`Xcode 27 · Swift 6 mode · macOS 15 · SwiftUI · SPM · Developer ID`), the screenshot-pass status, the finding counts by severity, and one line: `Rules: project .claude/rules/desktop-macos/ | plugin copy (not installed)`.

## Handoffs

- Fix → the `desktop-macos` agent (FIX or EXTEND), or the owning feature skill
- Repo-wide → [`standards-audit`](../standards-audit/SKILL.md); version moves → [`migration`](../migration/SKILL.md)
- Lock the fix with a test → [`unit-testing`](../unit-testing/SKILL.md)
- A rule is missing or wrong → edit the project's `.claude/rules/desktop-macos/`; for every project, the plugin's `desktop/macos/skills/rules/`
- Missing ids → [`test-ids`](../test-ids/SKILL.md); E2E review → peer `qa-desktop-java` / `qa-desktop-dotnet` / `qa-desktop-typescript`
- Security proof → peer `qa-security`
