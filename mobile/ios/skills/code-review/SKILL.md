---
name: conventions-review
description: Use when reviewing a Swift, SwiftUI or UIKit diff against plugin conventions, plus a simulator screenshot pass. Triggers "review this PR". Not for a whole-repo audit (standards-audit).
---

# iOS — Code Review

A **hostile review of one diff** against the mobile-ios rule files, then a **screenshot pass** on the running app. Findings go in the standard severity table; the review **does not rewrite** — it points, and the `mobile-ios` agent (or the author) fixes. A whole-repo sweep with a saved report is [`standards-audit`](../standards-audit/SKILL.md).

## The checklist is the rule files

Every check, and the severity it reports, lives in one place: the mobile-ios rule files — `swift.md` (core), `swiftui.md`, `ios-accessibility.md`, `ios-styling.md`, `ios-localization.md`, `uikit.md`, `swift-networking.md`, `swift-persistence.md`, `swift-tests.md` and `xcode-config.md`.

1. **The project's copies first**: `.claude/rules/mobile-ios/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `mobile/ios/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/mobile-ios:rules` installs them.

Read `swift.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. A view in a folder no glob covers still gets `swiftui.md`, `ios-accessibility.md`, `ios-styling.md` and `ios-localization.md`; judge by what the file is, not by whether its path matched. A rule loaded on its own by the session is not enough: a review needs every file that applies, not just the ones the session happened to open. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

## Version lane

Detect before flagging: Xcode and Swift (`xcodebuild -version`, `swift-tools-version`), `SWIFT_VERSION` and default isolation **per target**, the deployment target, SwiftUI vs UIKit for the files in the diff, SwiftData / Core Data / GRDB, SPM vs CocoaPods vs Tuist. The rule files' "the codebase wins" line applies: a convention the project follows consistently is not a finding.

| Lane | Review consequence |
|---|---|
| **Xcode 27 · Swift 6 · iOS 17** | The rules as written |
| Swift 5-mode module | Swift 6 concurrency rules are advice for the module's own migration run, not findings on a feature diff; a *new* module in Swift 5 mode is a finding |
| iOS 16 target | `@Observable`, SwiftData and `@Bindable` are findings only when the diff adds them without an `#available` gate; `ObservableObject` is correct |
| UIKit file | `uikit.md` applies; a SwiftUI rule is not flagged on a UIKit screen, and a UIKit codebase is not asked to convert |
| Below iOS 16 | One finding plus a [`migration`](../migration/SKILL.md) run |

`@Observable` on iOS 16, `Observations` below iOS 26, and a Swift 6.4-only construct on a 6.2 toolchain are **findings**; a `PreviewProvider` in new code is a minor.

## When to use

- A `.swift` / `Info.plist` / `.xcconfig` / `Package.swift` / `.xcprivacy` / `.entitlements` / `.xcstrings` diff, before merge
- Step 5 of the agent: the whole change set, after the quality layers
- "Why does this hang / crash on resume / lose its state?"

## When NOT to use

- Whole codebase, saved re-runnable report → [`standards-audit`](../standards-audit/SKILL.md)
- Explaining a concept → [`basics`](../basics/SKILL.md); writing code → the owning feature skill
- Reviewing **E2E test code** (XCUITest / Appium / Maestro) → peer `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript`
- Pen-test or runtime security → peer `qa-security` (`mobile-app-scan`, `mobile-runtime-testing`)
- A spec-versus-code audit → `code-auditor`

## Inputs needed

1. **The diff** (files or `git diff` range) and the screens it touches
2. **Lane facts** above, from the project and the module's settings
3. **Whether a simulator is available** for the screenshot pass

## Procedure

1. **Read the rule files** that apply (above), then each changed file end to end. Over a large diff, the *Find it with* recipes in [`conformance-checklist.md`](../standards-audit/references/conformance-checklist.md) are useful search leads; its rows are not extra checks.
2. **Walk the rules in this order**: safety and concurrency (`swift.md`), secrets, TLS and link validation, persistence migrations, then the rest. Most blockers live there.
3. **Read the code at every hit.** A grep hit is a lead, not a finding. Load the owning feature skill when a rule's application is ambiguous.
4. **Per finding**: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment. One row per defect family with a count, not per site.
5. **Run the screenshot pass** (below) if a simulator is available; otherwise say it was not run.
6. **Do not rewrite.** Hand off (below).

## The screenshot pass (Step 5)

Only when a simulator is available and the app builds; otherwise report "screenshot pass not run" and why.

```bash
xcrun simctl io booted screenshot ios-<screen>.png
```

`Read` each image. Capture the changed screens in **light and dark**, at **an accessibility text size** (Settings → Larger Text, or `xcrun simctl ui booted content_size accessibility-extra-extra-large`) and on iPad where the target is universal, in each of loading, loaded, failed and empty where the diff changes them. Check against the diff, not against taste: safe-area clipping under the Dynamic Island and home indicator, text truncation at large sizes, contrast, touch-target size, the error banner position, system chrome left to Liquid Glass (no custom bar backgrounds), platform-native controls (no Material or web look). Cite the `design/ux-review` heuristic and the corpus row (`design/ui-ux-pro-max --stack swiftui`) behind each visual finding. Save images only under a scratch folder inside the worktree and delete them before committing.

## Output format

```
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| blocker  | Sources/Profile/ProfileView.swift:41 | `user.avatarURL!` force unwrap on a server value — crashes on a missing avatar | Optional-bind or show the placeholder per `basics` |
| major    | Sources/Orders/OrdersClient.swift:18 | `URLSession.shared` with no timeout budget | Per-endpoint-class timeouts per `networking` |
```

Close with the lane line (`Xcode 27 · Swift 6 mode · iOS 17 · SwiftUI · SPM`), the screenshot-pass status, the finding counts by severity, and one line: `Rules: project .claude/rules/mobile-ios/ | plugin copy (not installed)`.

## Handoffs

- Fix → the `mobile-ios` agent (FIX or EXTEND), or the owning feature skill
- Repo-wide → [`standards-audit`](../standards-audit/SKILL.md); version moves → [`migration`](../migration/SKILL.md)
- Lock the fix with a test → [`unit-testing`](../unit-testing/SKILL.md)
- A rule is missing or wrong → edit the project's `.claude/rules/mobile-ios/`; for every project, the plugin's `mobile/ios/skills/rules/`
- Missing ids → [`test-ids`](../test-ids/SKILL.md); E2E review → peer `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript`
- Security proof → peer `qa-security`
