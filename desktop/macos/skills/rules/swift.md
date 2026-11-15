---
paths:
  - "**/*.swift"
---

<!-- desktop-macos rules v1 (2026-11-15): core. Installed by /desktop-macos:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# Swift / macOS code standards

Apply these to every Swift file you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a crash, a notarization or store rejection or a security break, **major** is a design or correctness problem, **minor** is style, **nit** is preference. SwiftUI, AppKit, accessibility, styling, localization, networking, persistence, test and project-config rules are separate files that load with those files.

**The codebase wins.** Where this project consistently does something another way, follow the project and do not flag it. Detect the Xcode and Swift versions, `SWIFT_VERSION` and default isolation per target and package, the deployment target and `ARCHS`, SwiftUI vs AppKit, and the distribution channel before writing: never use an API newer than the target without `#available`, never flag a Swift 5-mode module for lacking Swift 6 or a macOS 13 target for using `ObservableObject`. An AppKit codebase is extended in AppKit.

## Simplicity and scope

- Write the simplest thing that meets the requirement, then stop. No `protocol` with one conformer, no view model that mirrors a struct, no wrapper that only forwards, no configurability nothing uses. An abstraction is earned on the second real need. *major, fix by inlining*
- Cut structure, never correctness: the region states, accessibility, cancellation, the denied path and the tests stay.
- No TCA, Factory, swift-dependencies or DI container where the codebase did not choose one. *major*
- Never raise the Swift language mode, SDK, toolchain, deployment target or architecture list as a side effect; that move is its own change. Gate a newer API with `#available` instead. *major*

## Safety and types

- No `!`, `as!` or `try!` outside tests; no `fatalError` for a recoverable condition. *blocker*
- No implicitly unwrapped optional outside an `@IBOutlet`. *major*
- `struct` and `enum` first; `final class` when identity matters; `actor` for shared mutable state. A mode is one enum, never several booleans. *minor*
- No mutable global state: no `static var`; make it `let`, an actor, or inject it. *major*
- Access control is the narrowest that works; `public` only on a package's API. *minor*

## Concurrency

- Nothing blocks the main actor: no `DispatchSemaphore`, `.wait()`, `Thread.sleep`, `DispatchQueue.main.sync`, synchronous `Data(contentsOf:)` on a URL, and no file, network or database work on it. *blocker*
- A callback-to-async continuation resumes exactly once. *major*
- App and UI modules default to `MainActor` (no redundant `@MainActor` on their types); packages stay `nonisolated` and never take `MainActor` by blanket. *major*
- CPU-heavy work is `@concurrent`; no `Task.detached` to leave the main actor without a written reason. *major*
- An unstructured `Task { }` is stored and cancelled when its owner (window, model) goes; window work is `.task`. *major*
- No `@unchecked Sendable`, `nonisolated(unsafe)` or `MainActor.assumeIsolated` without a written justification beside it. *major*
- No `DispatchQueue.main.async` or other GCD hop in new code; return to the main actor by isolation. *minor*

## State, architecture and dependencies

- macOS 14+: `@Observable`, not `ObservableObject` / `@Published` / `@StateObject`, in new code. *major*
- One owner per model: `@State` owns an `@Observable` in the view that creates it, `@Bindable` binds, `@Environment` reads app-wide; never an `@Observable` in a `let` built in `body`. *major*
- Several windows on the same data share one model created once in the `App`, never a copy per window; window-local state (selection, scroll, a draft) lives per window. *major*
- Dependencies arrive by initializer or `@Environment` from the `App` composition root; no `.shared` singleton or locator inside a view or model. *major*
- A view model exists only for logic that needs a test apart from the view. *major*
- No coordinator, router object or "AppState" god-model beside the scenes. *major*

## Errors, logging and secrets

- Functions `throw` one domain `Error` enum, never a sentinel; `LocalizedError` only where a person reads the message. *minor*
- No empty `catch`; no `try?` hiding a failure the user must see. A catch logs, recovers, maps or rethrows. *major*
- `CancellationError` is never shown as a failure. *major*
- `os.Logger` only: no `print`, `NSLog`, `debugPrint` or `dump`. *minor*
- Interpolate values into the `Logger` call with a privacy level; dynamic values `.private` by default. Never log a token, password, email, file path of a user document or URL with a query. Log once, where the failure is handled. *major*
- Tokens and secrets live only in the Keychain: never in the binary, `UserDefaults`, `@AppStorage`, a plist or an xcconfig. *blocker*
- URL scheme and universal-link URLs, Services and pasteboard input, drag and drop payloads, file-open requests, XPC messages and `WKWebView` bridge messages are untrusted: validate before they route, open, read or act. A client check is UX; the server authorises. *blocker*

## Permissions, files and lifecycle

- File access goes through open and save panels or security-scoped bookmarks; every `startAccessingSecurityScopedResource` has one `stopAccessing…` in a `defer`; Full Disk Access is never assumed. *major*
- A TCC permission is asked at the moment of use, after a pre-prompt, never at launch; the denied path is a working screen with a link to System Settings, rechecked on activation. *major*
- Work a window starts is cancelled when it closes; wake from sleep, a network change and reactivation revalidate; quitting with unsaved work asks first and relaunch restores state. *major*
- Login items and helpers use `SMAppService` and register only on the user's action; IPC uses XPC with a listener that checks the peer. *major*
- Launch does first-frame work only: SDK initialisation waits, except the crash reporter; nothing blocks the first window. *major*

## Comments

- No comments inside function bodies: no step markers, no restating the next line, no commented-out code, no `TODO`/`FIXME`. Extract and name the step instead. *minor; major when the comment is wrong or exists because the code is unclear*
- A `///` doc comment only where the name cannot carry the meaning: a business rule, an ordering or isolation constraint on callers, a deliberate deviation, or a public contract. Never one that restates the signature. *minor*
- Scaffolded template comments and file headers are removed. *minor*
