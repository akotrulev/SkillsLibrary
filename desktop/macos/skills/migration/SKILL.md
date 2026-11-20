---
name: migration
description: Use when a Mac project changes lane (Swift 6, @Observable, AppKit to SwiftUI, Catalyst, Apple silicon only, Document). Triggers "move us to Swift 6". Not for a new app (project-setup).
disable-model-invocation: true
---

# macOS — Migration

Owns changing the **language mode, framework, dependency manager, SDK, deployment target or architecture list** of an existing Mac project. Every other macOS skill applies what is already there; this one is the only skill that moves the lane, and it does so as **its own change**: never inside feature work, never two moves at once, never past one module or one window per commit series.

## Version lane

| Lane | Value | Migration consequence |
|---|---|---|
| **Primary** | Xcode 27.x · Swift 6.4 · macOS 27 SDK · deployment target macOS 15 for a new app · Swift 6 mode | The target unless the project names another |
| Supported | Xcode 26.x · Swift 6.2–6.3 · macOS 26 SDK · target macOS 14 (13 for an existing app) · Swift 5-mode modules | Each module moves on its own; never raise the whole project to reach a feature |
| Dated | **Developer ID CA expires 2027-02-01** (`.pkg` re-signed with a G2 certificate) · **CocoaPods trunk read-only 2026-12-02** · macOS 26 Tahoe is the last macOS for Intel; Intel software stops running on macOS 28 | Deadlines, not preferences: [`apple-silicon-and-developer-id`](references/apple-silicon-and-developer-id.md), [`sdk-and-targets`](references/sdk-and-targets.md) |
| Below macOS 13 | Xcode 27's hard floor is macOS 12 | The AppKit lane only ([`appkit`](../appkit/SKILL.md)); a finding plus a deployment-target run, never a SwiftUI migration |

## Inputs needed

1. **The move**: one of the eight below. A request for two is two runs, in the order the table gives
2. **Current state**: Xcode and Swift versions, `SWIFT_VERSION` per target and package, `MACOSX_DEPLOYMENT_TARGET`, `ARCHS`, `Podfile` or `Package.swift`, SwiftUI / AppKit / Objective-C share (counts of `*.m`, `NSViewController` subclasses, `ObservableObject` types), Catalyst yes or no, Developer ID / Mac App Store
3. **The unit**: one module, one window or one pod per commit; the order is leaves first (modules nothing else imports, windows nothing else opens)
4. **Whether the app ships this quarter**: it decides whether the dated rows are urgent

## The gate — before any lane moves

1. **Clean tree, green baseline.** Record `xcodebuild -scheme <Scheme> -destination 'platform=macOS' build`, the `… test` run, `xcrun swift-format lint --recursive <dirs>` and `swiftlint` results *before* touching anything, or no later failure is attributable. Run them.
2. **One module, one change.** Commit the move per module (window, pod) so a failure bisects to one unit. Work in the checkout you are given; never create a branch or worktree.
3. **Inventory the blast radius first**: count the warnings strict mode reports, the `ObservableObject` types, the pods, the Objective-C files, the AppKit controllers. That number is the real size of the job; a number you cannot bound is a reason to ask.
4. **Read the source of the move**, not memory: swift.org/migration for language modes, the Xcode 27 release notes for the SDK, developer.apple.com/news for dates. Build-setting and flag names move between toolchains: read the installed toolchain's `-help` and the build settings reference.
5. **Never combine** two moves. Swift 6 plus `@Observable` plus a SwiftUI port in one change leaves no way to tell which one broke a window.

## The eight moves

| Move | Reference | One-line shape | Order |
|---|---|---|---|
| Swift 5 → 6, per module | [`swift6-modules`](references/swift6-modules.md) | Complete checking as warnings in Swift 5 mode, fix, flip the mode; leaves first; **find dynamic isolation crashes before shipping** | 1 |
| `ObservableObject` → `@Observable`, Combine → async | [`observation-and-async`](references/observation-and-async.md) | Per model; `@State` owns it, `@Bindable` binds it; needs macOS 14 | 2 |
| AppKit → SwiftUI | [`appkit-to-swiftui`](references/appkit-to-swiftui.md) | App lifecycle first, then one window or view at a time, host with `NSHostingView` / `NSHostingController`, root last | 3 |
| Catalyst → native | [`catalyst-to-native`](references/catalyst-to-native.md) | A native macOS target beside the Catalyst one; share packages; move scene by scene; delete Catalyst last | 4 |
| Objective-C → Swift | [`objc-to-swift`](references/objc-to-swift.md) | Annotate the header, then convert a leaf file; never convert and redesign | 5 |
| `FileDocument` → `Document` | [`filedocument-to-document`](references/filedocument-to-document.md) | **[mac27SDK]** one document type per commit; read and write become `async`, off the main actor | 6 |
| Intel → Apple silicon only, and the Developer ID CA | [`apple-silicon-and-developer-id`](references/apple-silicon-and-developer-id.md) | **Dated.** State the architecture decision, set `ARCHS` by hand, re-sign `.pkg` with a G2 certificate before 2027-02-01 | 0 — dated |
| macOS 27 SDK changes, CocoaPods → SPM, deployment target | [`sdk-and-targets`](references/sdk-and-targets.md) | Glass and hidden menu icons, `FileDocument` deprecation; pods replaced one by one before 2026-12-02; one macOS version per raise | 0 — dated |

Order 0 moves first when its date is near; the numbered ones follow by dependency: `@Observable` needs macOS 14, the SwiftUI port wants Swift 6 modules underneath, `Document` needs a 27 SDK build.

## Cross-move rules

- **Never up-level as a side effect.** A feature task that finds Swift 5 mode, a Podfile, a macOS 13 target or a universal binary reports it and offers this skill; it does not start it (CLAUDE.md § Desktop code rules).
- **A deployment-target raise is its own move**, and the only one that may delete `#available` branches. The target moves one macOS version per change and the architecture list is decided in the same run, because a 27 target drops x86_64 without a warning.
- **Generated projects.** A project owned by Tuist or XcodeGen changes in its manifest; a hand edit to the `.pbxproj` is erased by the next generation ([`project-setup`](../project-setup/SKILL.md), B-section rows).
- **Warnings are the work list.** `SWIFT_TREAT_WARNINGS_AS_ERRORS` goes on at the end of a module's move, not before; never silence a concurrency warning with `@unchecked Sendable` or `nonisolated(unsafe)` to finish faster: each is a written justification ([`basics`](../basics/SKILL.md), concurrency reference).
- **Tests move with the code.** A moved module keeps its Swift Testing / XCTest split; a migration with no test that fails on the old behaviour has proved nothing ([`unit-testing`](../unit-testing/SKILL.md)).
- **Dynamic isolation checks only show at runtime.** Swift 6 mode turns a thread assumption into a crash when a callback arrives on another queue; the compiler cannot see through Objective-C and unannotated closures. [`swift6-modules`](references/swift6-modules.md) § "Finding dynamic isolation checks" is part of that move's gate.
- **Entitlements and signing are part of every move that changes the build.** A move that changes the signing identity or the sandbox state re-checks the Keychain access group and the entitlements file ([`sandbox-and-permissions`](../sandbox-and-permissions/SKILL.md)).

## Verification (every move, non-negotiable)

1. Build is clean with warnings as errors for the unit just moved; `xcrun swift-format lint` and `swiftlint` match or beat the baseline.
2. The test plan matches or beats the baseline; a test exists that exercises the moved seam.
3. The app launches and the primary flow runs end to end; `screencapture -l <windowid> <file>` for the record on a UI move, read back as an image.
4. For Swift 6, a debug build runs the full UI path of every module moved **with Thread Sanitizer and the Main Thread Checker on**, once per callback seam.
5. A release-configuration archive builds and launches: optimisation breaks what Debug hides, and Debug is often unsandboxed.
6. For an architecture or signing move, `lipo -archs` on the binary and `codesign -dvv` / `spctl -a -vv` on the product agree with the stated decision.
7. Re-run the conformance audit's section A ([`standards-audit`](../standards-audit/SKILL.md)).

## Anti-patterns

- **Flipping `SWIFT_VERSION` to 6 on the whole project** and fixing what the compiler lists: the list is thousands long and hides the runtime ones.
- **`@preconcurrency import` or `@unchecked Sendable` as the migration**, rather than as a dated, justified bridge.
- **Converting every `ObservableObject` in one commit**, or leaving a `@StateObject` on an `@Observable`.
- **Rewriting AppKit windows as SwiftUI while also redesigning them**: the diff cannot be reviewed.
- **Raising the deployment target to 27 and finding out later that Intel Macs dropped.** `ARCHS` is part of the decision.
- **Deleting `Pods/` before every pod has an SPM replacement** or a vendored xcframework.
- **Raising the deployment target to use one API**: gate it with `#available` instead, until the target move is its own run.
- **Re-signing the app and forgetting the installer**: the `.pkg` certificate is the one the 2027-02-01 expiry stops.
- **Bundling a feature into the migration commit.**
