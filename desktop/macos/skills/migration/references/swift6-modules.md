# Swift 5 → 6 — one module at a time, leaves first

Sources: swift.org/migration (the Swift 6 migration guide) · the SE proposals named in [`basics/references/concurrency.md`](../../basics/references/concurrency.md). Re-read the guide on the installed toolchain before a run; build-setting and flag names move between Swift releases.

The language mode is a **per-module** setting (`SWIFT_VERSION` per target, `swiftLanguageModes` per package). A Swift 6 module can import a Swift 5 module, so the move runs from the modules nothing else imports towards the app target.

## 0. Order the modules

```bash
rg -n "dependencies:|\.target\(|\.package\(" -g 'Package.swift'
rg -n "SWIFT_VERSION" -g '*.pbxproj' -g '*.xcconfig'
```

Draw the import graph. The first module is a **leaf**: a package no other target imports, or the lowest library (models, parsing). The app target is last, then helpers and XPC services (each its own target with its own mode). Tests move with the module they test.

## 1. Per module: warnings first, mode second

1. **Baseline.** Build and test the module in Swift 5 mode; record the count of warnings.
2. **Turn on complete checking as warnings, still in Swift 5 mode**: `SWIFT_STRICT_CONCURRENCY = complete` on the target, or the strict-concurrency setting in the package's `swiftSettings`. This reports what Swift 6 would reject without breaking the build.
3. **Fix by cause, one cause per commit:**

| Warning family | Fix |
|---|---|
| Non-`Sendable` type crosses an actor | Make it a value type (`struct` / `enum` of `Sendable` fields); a `final class` with only `let` `Sendable` members is also `Sendable` |
| Mutable state read from several contexts | Behind an `actor`, or isolated to `@MainActor` when it is UI state |
| Global or static `var` | `let`, or isolated; a mutable global is a design finding, not a warning to silence |
| A closure sent across isolation captures a non-`Sendable` value | Capture a copy of the `Sendable` part; mark the closure `@Sendable` only after it is |
| A protocol conformance reaches isolated state | An isolated conformance on the Swift 6.2+ toolchain, or move the state to a `nonisolated` helper |
| An Objective-C or pre-concurrency framework type | `@preconcurrency import` **as a dated bridge** with the reason beside the import, removed when the SDK annotates the type |

4. **Pick the module's default isolation** ([`basics`](../../basics/SKILL.md)): `MainActor` for the app target and UI-only packages, `nonisolated` for library packages.
5. **Flip the mode**: `SWIFT_VERSION = 6` on the target (or `swiftLanguageModes: [.v6]` and a matching `swift-tools-version` on the package). Any new diagnostics are the errors Swift 5 mode could not show; fix them.
6. **Set** `SWIFT_TREAT_WARNINGS_AS_ERRORS = YES` on the module ([`project-setup`](../../project-setup/SKILL.md)).
7. Run [the dynamic isolation search](#finding-dynamic-isolation-checks-before-shipping) below, then commit and **stop**. The next module is a new commit series.

`swift package migrate` (SwiftPM, Swift 6.2+) applies the compiler's fix-its for a named upcoming feature across a package; run it per feature, review the diff, and read `swift package migrate --help` on the installed toolchain for the exact flag. It rewrites syntax; it does not decide isolation: steps 3 and 4 stay yours.

Approachable Concurrency (`SWIFT_APPROACHABLE_CONCURRENCY`, with `NonisolatedNonsendingByDefault`) is a **separate switch** from the language mode and changes where `nonisolated async` functions run. Turn it on in its own commit after the mode is 6, and re-run the test plan.

## Finding dynamic isolation checks before shipping

The compiler proves isolation only for code it can see. Where it cannot (Objective-C callbacks, unannotated closures, protocol witnesses a framework calls), Swift 6 mode inserts **runtime** checks that stop the process if a `@MainActor` or actor-isolated function runs on the wrong executor. They do not show as warnings, and a debug run that never exercises the seam will not trip them; a user will.

Crash signatures to search crash logs and the Xcode console for: `dispatch_assert_queue_fail`, `Incorrect actor executor assumption`, `Expected same executor as MainActor`, `_swift_task_checkIsolatedSwift`.

Find the seams **statically**:

```bash
rg -n "@MainActor" -g '*.swift' --glob '!*Tests*'
rg -n "completionHandler|DispatchQueue\.(global|main)|NotificationCenter\.default\.addObserver|NSWorkspace|NSApplicationDelegate|NSOpenSavePanelDelegate|NSMenuItemValidation|URLSessionDelegate|FSEventStream|NSXPCConnection|SPUUpdaterDelegate|IOKit" -g '*.swift'
rg -n "@preconcurrency|assumeIsolated|nonisolated\(unsafe\)|@unchecked Sendable" -g '*.swift'
```

For each hit ask one question: **which queue or thread does the framework call this on, and does the code assume the main actor?** A delegate method on an `@MainActor` class that a framework calls on a background queue is the classic crash. The fix is a `nonisolated` delegate method that hops with `Task { @MainActor in … }`, not `MainActor.assumeIsolated` (the same crash with a different name).

Mac seams that trip this most: workspace notifications (`NSWorkspace.didWakeNotification`, `didActivateApplicationNotification`), open and save panel completion handlers, `NSXPCConnection` handlers and `XPCSession` callbacks, file-system event callbacks, Sparkle delegate methods, IOKit power callbacks, `NSMenuItem` validation, and AppKit delegate methods in a module whose default isolation changed.

Then **exercise them at runtime**, debug build, Swift 6 mode, every module moved so far:

1. Run the whole test plan with **Thread Sanitizer** and the **Main Thread Checker** on (scheme → Diagnostics).
2. Drive each seam once on a Mac: grant and deny each permission, sleep and wake, open and save through the panels, connect and kill each helper, quit and relaunch, check for updates.
3. Search the console for the signatures above. A hit is a finding with the seam's file and line; fix it before the next module moves.
