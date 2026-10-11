---
name: conventions-review
description: Use when reviewing a Swift / SwiftUI / UIKit diff — force unwraps, blocking the main thread, Swift 6 isolation escape hatches, work in `body`, missing timeouts and failed states, secrets outside the Keychain, unvalidated links and push payloads, untagged elements — plus a simulator screenshot pass. Triggers "review this screen", "review this PR", "is this Swift ok". Do NOT use for a whole-repo audit (`mobile-ios:standards-audit`), explanations (`-basics`) or writing code.
---

# iOS — Code Review

A **hostile review of one diff** against the conformance checklist's rows and CLAUDE.md § Mobile code rules, then a **screenshot pass** on the running app. Findings go in the standard severity table; the review **does not rewrite** — it points, and the `mobile-ios` agent (or the author) fixes. A whole-repo sweep with a saved report is [`standards-audit`](../standards-audit/SKILL.md), which reuses these checks at repo scale.

## Version lane

Detect before flagging: Xcode and Swift (`xcodebuild -version`, `swift-tools-version`), `SWIFT_VERSION` and default isolation **per target**, the deployment target, SwiftUI vs UIKit for the files in the diff, SwiftData / Core Data / GRDB, SPM vs CocoaPods vs Tuist.

| Lane | Review consequence |
|---|---|
| **Xcode 27 · Swift 6 · iOS 17** | The rows as written |
| Swift 5-mode module | The Swift 6 rows (`[Swift6]`) are advice for the module's own migration run, not findings on a feature diff; a *new* module in Swift 5 mode is A1 / A6 |
| iOS 16 target | `[iOS17+]` rows (`@Observable`, SwiftData, `@Bindable`) are findings only when the diff adds them without an `#available` gate; `ObservableObject` is correct |
| `[UIKit]` file | The UIKit rows (D12–D20) apply; a SwiftUI rule is not flagged on a UIKit screen, and a UIKit codebase is not asked to convert |
| Below iOS 16 | One finding (A8) plus a [`migration`](../migration/SKILL.md) run |

`@Observable` on iOS 16, `Observations` below iOS 26, and a Swift 6.4-only construct on a 6.2 toolchain are **findings** (A4); a `PreviewProvider` in new code is a minor (A11).

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

1. **Map the diff to checklist sections** with the table below; open [`conformance-checklist.md`](../standards-audit/references/conformance-checklist.md) at only those sections and run each row's *Find it with* recipe **over the changed files**.
2. **Read the code at every hit.** A grep hit is a lead, not a finding.
3. **Verify the rule's owner** when a row is ambiguous — load the owning skill; the skill wins over the checklist, and the disagreement is reported.
4. **Run the screenshot pass** (below) if a simulator is available; otherwise say it was not run.
5. **Write the table**; one row per defect family with a count, not per site.

| The diff touches | Sections |
|---|---|
| Build settings, `Package.swift`, `Podfile`, xcconfig | A, B, K, L, T |
| SwiftUI views, components, lists | C, D, E, M, N, R |
| UIKit controllers, hosting seams | D (UIKit rows), M, N |
| Routes, links, notifications, AASA | F, J, K |
| Forms, inputs | G, M |
| API client, sockets | H, O, K |
| SwiftData / Core Data / Keychain / files | I, K |
| Permissions, camera, location, widgets, intents, background | J, K, L |
| Animation, gestures | Q, N, M |
| Strings, formats | P |
| Models, services, injection | B, C, V |
| Tests | S, R |
| Purchases | X |

## The rules every diff is held to (§5, in review form)

| Check | Bad sign | Severity |
|---|---|---|
| No force unwrap, `as!` or `try!` outside tests | `value!`, `try!` in app or package source | blocker |
| The main thread is never blocked | `DispatchSemaphore`, `.wait()`, `Thread.sleep`, `main.sync`, `Data(contentsOf:)` on a URL in UI code | blocker |
| Secrets live in the Keychain, never in the binary | A token in `UserDefaults` / `@AppStorage` / a plist / an xcconfig; `kSecAttrAccessibleAlways*` | blocker |
| TLS only | `NSAllowsArbitraryLoads` without a recorded reason; a `serverTrust` delegate accepting everything | blocker |
| Push and link payloads are validated | A route, `openURL` or path built from an unchecked `userInfo` / URL field | blocker |
| Every shipped store migrates | A `@Model` edited with no `VersionedSchema` stage; `eraseDatabaseOnSchemaChange` in a release path | blocker |
| Every protected resource has a usage string | A permission request with no `NS…UsageDescription` | blocker |
| Swift 6 escape hatches carry a justification | `@unchecked Sendable`, `nonisolated(unsafe)`, `MainActor.assumeIsolated` with no stated invariant; `Task.detached` to leave the main actor | major |
| No work in `body` | A network call, `DateFormatter()`, decode or large sort in `body` | major |
| Async work is owned by the view | `Task { }` in `onAppear` with no handle instead of `.task`; a controller `Task` never cancelled | major |
| Every request has a timeout budget | `URLSession.shared` defaults; a spinner that can run forever | major |
| Data regions have all states | No failed / stale / offline path; a failure that blanks the toolbar and the screen; `try?` turning a failure into empty | major |
| Failures surface in one persistent banner | A `print`-only catch, an alert that vanishes, `Text(error.localizedDescription)` | major |
| Unbounded lists are lazy, with stable ids | `VStack` in `ScrollView` over server data; `id: \.self`; `ForEach(0..<n)` | major |
| Permissions asked in context | A request in `App.init` / first `onAppear`; no denied-path screen | major |
| Every interactive element and list container has an `accessibilityIdentifier` | A `Button` / `TextField` / `List` with none; an id built from an index, GUID or state; the label used as an id | major |
| Accessible | An icon-only button with no label; `.onTapGesture` as a button; `.font(.system(size:))`; target < 44 pt | major |
| Dependencies arrive by initializer or `@Environment` | A `.shared` singleton or locator inside a view or model | major |
| `ObservableObject` is not new code on iOS 17+ | `@StateObject` / `@Published` in a new model | major |
| No unearned abstraction | A `protocol` with one conformer; a view model that only mirrors a struct; a wrapper that only forwards | major |
| Reduce Motion honoured | Custom animation with no `accessibilityReduceMotion` read | major |
| Liquid Glass not fought | A custom background behind a system bar; `UIDesignRequiresCompatibility` | major |
| Strings localized | A literal built by concatenation; a new `.strings` file | major |
| Swift Testing in new tests; no `do`/`catch`, `if`, `OR` or sleep in a test body | `XCTestCase` for pure logic; `#expect(a == x \|\| a == y)` | major |
| No inline comment, no commented-out code, no `TODO` | `//` inside a body | minor |
| A version, SDK or deployment-target move inside a feature diff | `SWIFT_VERSION` or `IPHONEOS_DEPLOYMENT_TARGET` changed beside a feature | major — reject; it is a [`migration`](../migration/SKILL.md) run |

## The screenshot pass (Step 5)

Only when a simulator is available and the app builds; otherwise report "screenshot pass not run" and why. Never build inside a `Gate: none` plan task.

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

Close with the lane line (`Xcode 27 · Swift 6 mode · iOS 17 · SwiftUI · SPM`), the screenshot-pass status, and the finding counts by severity. Severities follow the checklist: blocker ships a crash, a store rejection or a hard security rule break; major breaks a § Mobile code rule where it will hurt soon; minor is style; nit is preference.

## Anti-patterns to always flag

- A Swift 6, SwiftUI, SPM or deployment-target move inside a feature diff — reject it; it is a [`migration`](../migration/SKILL.md) run
- A comment that exists because a name is unclear (major — the fix is the rename)
- A test that asserts nothing, or an `OR` in an assertion (Test code rules)
- `try` / `catch` inside a test body
- A migration PR that changes behaviour beside the conversion

## Handoffs

- Fix → the `mobile-ios` agent (FIX or EXTEND), or the owning skill named per section
- Repo-wide → [`standards-audit`](../standards-audit/SKILL.md); version moves → [`migration`](../migration/SKILL.md)
- Lock the fix with a test → [`unit-testing`](../unit-testing/SKILL.md)
- Missing ids → [`test-ids`](../test-ids/SKILL.md); E2E review → peer `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript`
- Security proof → peer `qa-security`
