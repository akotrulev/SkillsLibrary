# Swift 5 → 6 — one module at a time, leaves first

Sources: swift.org/migration (the Swift 6 migration guide) · the SE proposals named in [`basics/references/concurrency.md`](../../basics/references/concurrency.md). Re-read the guide on the installed toolchain before a run; build-setting and flag names move between Swift releases and were not re-confirmed against an Apple page for this file.

The language mode is a **per-module** setting (`SWIFT_VERSION` per target, `swiftLanguageModes` per package). A Swift 6 module can import a Swift 5 module, so the move runs from the modules nothing else imports towards the app target.

## 0. Order the modules

```bash
rg -n "dependencies:|\.target\(|\.package\(" -g 'Package.swift'
rg -n "SWIFT_VERSION" -g '*.pbxproj' -g '*.xcconfig'
```

Draw the import graph. The first module is a **leaf** — a package no other target imports, or the lowest library (models, parsing). The app target is last. Tests move with the module they test.

## 1. Per module: warnings first, mode second

1. **Baseline.** Build and test the module in Swift 5 mode; record the count of warnings.
2. **Turn on complete checking as warnings, still in Swift 5 mode** — the build setting `SWIFT_STRICT_CONCURRENCY = complete` (target), or `.enableExperimentalFeature("StrictConcurrency")` / `.strictConcurrency` in `swiftSettings` for a package. This reports what Swift 6 would reject without breaking the build.
3. **Fix by cause, one cause per commit:**

| Warning family | Fix |
|---|---|
| Non-`Sendable` type crosses an actor | Make the type a value type (`struct` / `enum` of `Sendable` fields) — the default; a `final class` with only `let` `Sendable` members is also `Sendable` |
| Mutable state read from several contexts | Move it behind an `actor`, or isolate it to `@MainActor` when it is UI state |
| Global or static `var` | Make it `let`, or isolate it; a mutable global is a design finding (B13), not a warning to silence |
| A closure sent across isolation captures a non-`Sendable` value | Capture a copy of the `Sendable` part; mark the closure `@Sendable` only after it is |
| A protocol conformance reaches isolated state | An isolated conformance (SE-0470) on the Swift 6.2+ toolchain, or move the state to a `nonisolated` helper |
| An Objective-C or pre-concurrency framework type | `@preconcurrency import` **as a dated bridge** with the reason beside the import, removed when the SDK annotates the type |

4. **Pick the module's default isolation** ([`basics`](../../basics/SKILL.md)): `MainActor` for the app target and UI-only packages, `nonisolated` for library packages. A library package with `MainActor` default isolation is finding A2 / B12.
5. **Flip the mode**: `SWIFT_VERSION = 6` on the target (or `swiftLanguageModes: [.v6]` and `swift-tools-version: 6.x` on the package). Any new diagnostics are the errors Swift 5 mode could not show; fix them.
6. **Set** `SWIFT_TREAT_WARNINGS_AS_ERRORS = YES` (`treatAllWarnings(as: .error)`) on the module ([`project-setup`](../../project-setup/SKILL.md)).
7. Run [**Finding dynamic isolation checks**](#finding-dynamic-isolation-checks-before-shipping) below, then commit and **stop**. The next module is a new commit series.

`swift package migrate` (SwiftPM, Swift 6.2+) applies the compiler's fix-its for a named upcoming feature across a package; run it per feature, review the diff, and read `swift package migrate --help` on the installed toolchain for the exact flag. It rewrites syntax; it does not decide isolation — steps 3–4 stay yours.

Approachable Concurrency (`SWIFT_APPROACHABLE_CONCURRENCY`, with `NonisolatedNonsendingByDefault`) is a **separate switch** from the language mode and changes where `nonisolated async` functions run. Turn it on in its own commit after the mode is 6, and re-run the test plan; A3 asks only that it be a stated choice.

## Finding dynamic isolation checks before shipping

The compiler proves isolation only for code it can see. Where it cannot — Objective-C callbacks, unannotated closures, protocol witnesses called by a framework — Swift 6 mode inserts **runtime** checks that stop the process if a `@MainActor` (or actor-isolated) function runs on the wrong executor. They do not show as warnings and a debug run that never exercises the seam will not trip them; a release user will.

Crash signatures to search crash logs and the Xcode console for: `dispatch_assert_queue_fail`, `Incorrect actor executor assumption`, `Fatal error: Incorrect actor executor assumption; Expected same executor as MainActor`, `_swift_task_checkIsolatedSwift`.

Find the seams **statically**, before running anything:

```bash
rg -n "@MainActor" -g '*.swift' --glob '!*Tests*'   # isolated types a callback may reach
rg -n "completionHandler|DispatchQueue\.(global|main)|NotificationCenter\.default\.addObserver|URLSessionDelegate|CLLocationManagerDelegate|AVCapture.*Delegate|NSItemProvider|MTKViewDelegate" -g '*.swift'
rg -n "@preconcurrency|assumeIsolated|MainActor\.assumeIsolated|nonisolated\(unsafe\)|@unchecked Sendable" -g '*.swift'
```

For each hit ask one question: **which queue or thread does the framework call this on, and does the code assume the main actor?** A delegate method on an `@MainActor` class that a framework calls on a background queue is the classic crash — the fix is a `nonisolated` delegate method that hops with `Task { @MainActor in … }` (or `await MainActor.run`), not `MainActor.assumeIsolated` (which is the same crash with a different name).

Then **exercise them at runtime** — debug build, Swift 6 mode, every module moved so far:

1. Run the whole test plan with **Thread Sanitizer** and the **Main Thread Checker** on (scheme → Diagnostics).
2. Drive each seam found above once on a device or simulator: grant and deny each permission, receive a push, finish a background `URLSession` transfer, foreground from the app switcher, rotate, open a link, finish a download, background and resume.
3. Search the console for the signatures above. A hit is a finding with the seam's file and line; fix it before the next module moves.

A flag that downgrades the dynamic checks exists for migrations (reported in the SE-0423 discussion as `-disable-dynamic-actor-isolation`); confirm it against the installed compiler before relying on it, record the reason, and remove it in the same run — shipping with it is hiding the crash, not fixing it.

## Done

- Every module of the run: `SWIFT_VERSION = 6`, warnings as errors, no new `@unchecked Sendable` / `nonisolated(unsafe)` without a justification beside it
- The seam list from the section above is in the PR description with the result of each
- Audit rows A1, A2, A3, A6, A7, B3, B10, B12 pass for the moved modules
