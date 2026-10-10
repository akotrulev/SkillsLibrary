---
name: mobile-ios-migration
description: Use when an iOS project changes lane — Swift 5 → 6 per module, ObservableObject → @Observable, Combine → async / Observations, UIKit → SwiftUI screen by screen, Objective-C → Swift, CocoaPods → SPM before the 2026-12-02 trunk freeze, the iOS 27 SDK's forced changes, a deployment-target raise. Triggers "move us to Swift 6", "drop CocoaPods", "we link iOS 27 next month". Do NOT use for feature work, a fresh app (`mobile-ios-project-setup`) or a minor dependency bump.
---

# iOS — Migration

Owns changing the **language mode, framework, dependency manager, SDK or deployment target** of an existing project. Every other iOS skill applies what is already there; this one is the only skill that moves the lane, and it does so as **its own change** — never inside feature work, never two moves at once, never past one module or one screen per commit series.

## Version lane

| Lane | Value | Migration consequence |
|---|---|---|
| **Primary** | Xcode 27.0 · Swift 6.4 · iOS 27 SDK · deployment target iOS 17 · Swift 6 mode | The target unless the project names another |
| Supported | Xcode 26.x · Swift 6.2–6.3 · deployment target iOS 16 · Swift 5-mode modules | Each module moves on its own; never raise the whole project to reach a feature |
| Dated | **CocoaPods trunk read-only 2026-12-02** · uploads need the **iOS 27 SDK from April 2027** (the Xcode 26 SDK until then) | Both are deadlines, not preferences — [`cocoapods-to-spm`](references/cocoapods-to-spm.md) and [`ios27-sdk-and-targets`](references/ios27-sdk-and-targets.md) |
| Below iOS 16 | — | The UIKit lane only ([`uikit`](../uikit/SKILL.md)); a finding plus a deployment-target run, never a SwiftUI migration |

## When to use

- The user names a move: Swift 6, `@Observable`, async, SwiftUI, Swift, SPM, a deployment target, the iOS 27 SDK
- The audit reports A1, A5, A8, A9, A10 or A11 ([`standards-audit`](../standards-audit/SKILL.md) section A)
- A post-migration break: a runtime isolation crash, a view that lost its state, a `pod install` that no longer resolves

## When NOT to use

- New app → [`project-setup`](../project-setup/SKILL.md)
- Feature work, a bug fix → the agent's FIX / EXTEND modes; they never up-level a lane
- A patch / minor dependency bump, or a package major with no lane change — dependency hygiene
- An Expo project's native side → `mobile-react-native-migration`; this skill covers only the Swift an Expo module contains
- Android → `mobile-android-migration`

## Inputs needed

1. **The move** — one of the seven below. A request for two is two runs, in the order the table gives
2. **Current state** — Xcode and Swift versions, `SWIFT_VERSION` per target and package, deployment target, `Podfile` or `Package.swift`, UIKit / SwiftUI / Objective-C share (counts of `*.m`, `UIViewController` subclasses, `ObservableObject` types)
3. **The unit** — one module, one screen or one pod per commit; the order is leaves first (modules nothing else imports, screens nothing else pushes to)
4. **Whether the project ships to the store this quarter** — it decides whether the dated rows are urgent

## The gate — before any lane moves

1. **Clean tree, green baseline.** Record `xcodebuild … build`, `xcodebuild … test`, `xcrun swift-format lint` and `swiftlint` results *before* touching anything, or no later failure is attributable. Outside a `Gate: none` plan task, run them; inside one, say they were not run.
2. **One module, one change.** Commit the move per module (or screen, or pod) so a failure bisects to one unit. Work in the checkout you are given — never create a branch or worktree.
3. **Inventory the blast radius first** — count the warnings the strict mode reports, the `ObservableObject` types, the pods, the Objective-C files. That number is the real size of the job; a number you cannot bound is a reason to ask.
4. **Read the source of the move**, not memory: swift.org/migration for language modes, Apple's Technical Notes (TN3187) for the scene lifecycle, the Xcode 27 release notes for the SDK. Names of build settings and flags move between toolchains — read the installed toolchain's `-help` and the build settings reference.
5. **Never combine** two moves. Swift 6 plus `@Observable` plus a SwiftUI port in one PR leaves no way to tell which one broke a screen.

## The seven moves

| Move | Reference | One-line shape | Order |
|---|---|---|---|
| Swift 5 → 6, per module | [`swift6-modules`](references/swift6-modules.md) | Complete checking as warnings in Swift 5 mode, fix, then flip the mode; leaves first; **find dynamic isolation crashes before shipping** | 1 |
| `ObservableObject` → `@Observable` | [`observation`](references/observation.md) | Per model; `@State` owns it, `@Bindable` binds it; needs iOS 17 | 2 |
| Combine → async / `Observations` | [`combine-to-async`](references/combine-to-async.md) | A pipeline at a time; `Observations` needs iOS 26 | 3 |
| UIKit → SwiftUI | [`uikit-to-swiftui`](references/uikit-to-swiftui.md) | Scene lifecycle first, then screens, host with `UIHostingController`, root last | 4 |
| Objective-C → Swift | [`objc-to-swift`](references/objc-to-swift.md) | Annotate the header, then convert a leaf file; never convert and redesign | 5 |
| CocoaPods → SPM | [`cocoapods-to-spm`](references/cocoapods-to-spm.md) | **Before 2026-12-02**; inventory pods, replace one by one, remove `Pods/` last | 0 — dated |
| iOS 27 SDK changes, deployment target | [`ios27-sdk-and-targets`](references/ios27-sdk-and-targets.md) | Scene lifecycle, launch screen, glass, `@State`; one iOS version per raise | 0 — dated |

Order 0 moves first when their date is near; the numbered ones follow by dependency — `@Observable` needs iOS 17, `Observations` needs iOS 26, the SwiftUI port wants Swift 6 modules underneath.

## Cross-move rules

- **Never up-level as a side effect.** A feature task that finds Swift 5 mode, a Podfile or an iOS 16 target reports it and offers this skill — it does not start it.
- **A deployment-target raise is its own move** — and the only one that may delete `#available` branches.
- **Generated projects.** A project owned by Tuist or XcodeGen changes in its manifest; a hand edit to the `.pbxproj` is erased by the next generation ([`project-setup`](../project-setup/SKILL.md), B24).
- **Warnings are the work list.** `SWIFT_TREAT_WARNINGS_AS_ERRORS` goes on at the end of a module's move, not before; never silence a concurrency warning with `@unchecked Sendable` or `nonisolated(unsafe)` to finish faster — each is a written justification ([`basics`](../basics/SKILL.md) concurrency reference).
- **Tests move with the code.** A moved module keeps its Swift Testing / XCTest split; a migration with no test that fails on the old behaviour has proved nothing ([`unit-testing`](../unit-testing/SKILL.md)).
- **Dynamic isolation checks only show at runtime.** Swift 6 mode (and any `@MainActor` annotation on a callback) turns a thread assumption into a crash when the callback arrives on another queue; the compiler cannot see through Objective-C and unannotated closures. [`swift6-modules`](references/swift6-modules.md) § "Finding dynamic isolation checks" is part of that move's gate.

## Verification (every move, non-negotiable)

1. Build is clean with warnings as errors for the unit just moved; `xcrun swift-format lint` and `swiftlint` match or beat the baseline.
2. The test plan matches or beats the baseline; a test exists that exercises the moved seam.
3. The app launches on a simulator and the primary flow runs end to end; `xcrun simctl io booted screenshot <file>` for the record on a UI move.
4. For Swift 6, a debug build runs the full UI path of every module moved **with Thread Sanitizer and the main-thread checker on**, once per callback seam ([`swift6-modules`](references/swift6-modules.md)).
5. A release-configuration archive builds — optimisation breaks what debug hides.
6. Re-run the conformance audit's section A ([`standards-audit`](../standards-audit/SKILL.md)).

## Anti-patterns

- **Flipping `SWIFT_VERSION` to 6 on the whole project** and fixing what the compiler lists — the list is thousands long and hides the runtime ones.
- **`@preconcurrency import` or `@unchecked Sendable` as the migration**, rather than as a dated, justified bridge.
- **Converting every `ObservableObject` in one commit**, or leaving a `@StateObject` on an `@Observable`.
- **Rewriting UIKit screens as SwiftUI while also redesigning them** — the diff cannot be reviewed.
- **Deleting `Pods/` before every pod has an SPM replacement** or a vendored xcframework.
- **Raising the deployment target to use one API** — gate it with `#available` instead, until the target move is its own run.
- **Combine → async by wrapping `values` around every publisher** — convert the pipeline, not the surface.
- **Bundling a feature into the migration commit.**

## Handoffs

- The Swift standard and the concurrency reference → [`basics`](../basics/SKILL.md)
- Project, package and xcconfig layout → [`project-setup`](../project-setup/SKILL.md)
- UIKit lane, scene lifecycle, interop seams → [`uikit`](../uikit/SKILL.md)
- State ownership after the move → [`architecture`](../architecture/SKILL.md)
- Store model migrations (SwiftData `VersionedSchema`) → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Privacy manifest, signing, SDK upload requirements → `mobile-shared-store-compliance`, `mobile-shared-release`
- Review the migration diff → [`code-review`](../code-review/SKILL.md); conformance after the move → [`standards-audit`](../standards-audit/SKILL.md)
- Tests that lock the move → [`unit-testing`](../unit-testing/SKILL.md); device journeys → peer `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript`
