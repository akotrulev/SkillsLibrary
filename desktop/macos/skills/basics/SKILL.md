---
name: concepts
description: Use when writing or reviewing Swift for a Mac app (Swift 6 concurrency, optionals, errors, os.Logger, the Mac model). Triggers "is this Swift idiomatic". Not for reviewing a diff (code-review).
disable-model-invocation: true
---

# macOS — The Swift Coding Standard and the Mac Model

How Swift is written for a Mac app in this library, and what makes a Mac app a Mac app: scenes and windows instead of screens, a menu bar that holds every command, keyboard first, pointer plus touch, density, the sandbox. The Swift half is adapted from `mobile-ios` (the folder `basics`); the Mac half is new. Audit rows are sections A and B of `desktop-macos:standards-audit`.

**Reads without an app.** Nothing here needs a SwiftUI app: apply it to a package's `.swift` files as they stand. App-level skills (`project-setup`, `architecture`, `ui-components`) are named for hand-off only.

## Version lane — detect first, key every recipe to it

Read `SWIFT_VERSION` / `swiftLanguageModes`, `swift --version`, `MACOSX_DEPLOYMENT_TARGET`, `ARCHS` and the isolation settings **before** writing. Never up-level a toolchain, language mode, deployment target or architecture list as a side effect.

| Item | Primary | Supported | Floor / rule |
|---|---|---|---|
| Xcode / Swift / SDK | **Xcode 27.x, Swift 6.4, macOS 27 SDK** | Xcode 26.x, Swift 6.2–6.3, macOS 26 SDK | Xcode 27 installs only on Apple silicon, on Tahoe 26.6+ |
| Deployment target, new app | **macOS 15** (`UtilityWindow`, `defaultWindowPlacement`, `restorationBehavior`) | **macOS 14** (`@Observable`, SwiftData, `inspector`, `onKeyPress`, `openSettings`) | — |
| Deployment target, existing app | keep it | macOS 13 (`NavigationSplitView`, `Window`, `MenuBarExtra`, `SMAppService`) | **macOS 12 is Xcode 27's hard floor**; below 13 is the AppKit lane only, flagged |
| Architectures | arm64 only at a target ≥ 27 | Universal while the target is < 27 and Intel Macs on Tahoe are in scope | Intel software stops running on macOS 28 |
| Language mode | Swift 6 + Approachable Concurrency, new modules | Swift 5-mode modules, migrated one at a time | As `mobile-ios` |

**The deployment-target lanes are a recommendation (D4), not an Apple rule.** They come from which APIs each target unlocks; a project's own target wins, and a down-level project is never flagged for lacking an up-level API.

Three **separate** Swift switches, as on iOS: language mode (`SWIFT_VERSION = 6`, errors for data races), default actor isolation (`MainActor`, Swift 6.2 compiler) and Approachable Concurrency (`SWIFT_APPROACHABLE_CONCURRENCY`). The Xcode 27 template is still `SWIFT_VERSION = 5.0`. Never assume one implies another. `await` in `defer`, `weak let` and `~Sendable` are **[Swift 6.4]**; a 6.2–6.3 project is not flagged for lacking them. Depth: [`references/concurrency.md`](references/concurrency.md).

## When to use

- Writing Swift in a Mac app, a local package or a helper
- "Struct or class?", "may I force-unwrap?", "which error type?", "which isolation for this module?"
- Deciding whether something is a window, a menu command or a screen
- Fixing a `Sendable` diagnostic

## When NOT to use

- Creating the project, entitlements, xcconfig, lint → `project-setup`
- State ownership and injection → `architecture`
- SwiftUI views, `Table`, inspectors → `ui-components`
- Windows and scenes, menus → `windows-and-scenes`, `menus-and-commands`
- Reviewing a diff → `code-review`
- iOS-only Swift → `mobile-ios:concepts`; Windows → `desktop-windows:concepts`

---

## The Mac model — what is different from a phone

| Phone habit | On the Mac |
|---|---|
| One screen at a time, a navigation stack | **Several windows** on the same data, each with its own selection; a sidebar-detail window is the default shape. Scenes (`WindowGroup`, `Window`, `Settings`, `MenuBarExtra`, `DocumentGroup`, `UtilityWindow`) are declared once; the UI says "window", never "scene" |
| Actions in buttons and sheets | **Every command lives in the menu bar**, in the standard order (App, File, Edit, Format, View, app-specific, Window, Help). A command that is unavailable is **disabled, never hidden** |
| Touch only | **Keyboard first**: standard shortcuts kept, full Full Keyboard Access, a complete key-view loop. **Pointer plus touch**: touch-screen Macs ship since 2026-11-06, so a hover-only control also gets a click or context-menu path |
| Large controls (44 pt) | Density: control default **28 × 28 pt**, minimum **20 × 20 pt**; text default **13 pt**, minimum **10 pt** (HIG Accessibility) |
| A modal sheet for input | Less modality, more nesting-free layout: inspectors, popovers, panes. A background failure never raises a modal alert |
| Process lives until the OS ends it | The user quits, closes the last window (or not), restores state at relaunch; quitting with unsaved work asks first |
| Files are the app's | **The App Sandbox** decides: access to the user's files goes through open/save panels and security-scoped bookmarks; Full Disk Access is never assumed (`sandbox-and-permissions`) |

Design facts (menu order, window states, touch targets) come from `design/ui-ux-pro-max`: `search.py "<query>" --stack swiftui` and the HIG pages "The menu bar", "Windows", "Designing for macOS". Where this skill and the corpus disagree, the corpus wins.

## Naming — the API Design Guidelines

The call site is the unit of design: `cart.add(item, quantity: 2)` reads as a sentence.

- Clarity at the point of use; omit words the types already say; name by role, not type.
- Mutating verbs and non-mutating nouns/`-ed`: `sort()` / `sorted()`.
- Booleans read as assertions: `isEmpty`, `hasUnsavedChanges`, `canRevert`.
- Types and cases `UpperCamelCase`, the rest `lowerCamelCase`; acronyms uniform (`URLSession`, `userID`); no type prefixes.

## Value types by default

`struct` and `enum` first; `final class` only when identity or shared mutable state is the point.

| Use | When |
|---|---|
| `struct` | Models, DTOs, view state, configuration |
| `enum` with associated values | A closed set: route, result, error, `loading / loaded / failed` as one enum, never three booleans |
| `final class` | A session, a cache, a document model, an `@Observable` model several views share |
| `actor` | Shared mutable state used from several isolation domains |
| non-final `class` | Only to subclass a framework type (`NSViewController`, `NSObject`) |

Composition over inheritance. A `protocol` with one conformer is an unearned abstraction: add it on the second real need. `let` over `var`; `private(set)` when callers read but must not write. `Identifiable` with a stable domain id on anything listed.

## Optionals and errors

**No `!`, `as!` or `try!` outside tests.** `guard let value else { return }`, `value ?? fallback`, `as?` with a `guard`. The one framework-owned exception is an `@IBOutlet` in AppKit code. Never an optional collection. `try?` only where the failure has no handler and no user consequence.

- Functions `throw`; no sentinel returns. One `Error` enum per failure domain, associated values carrying the evidence. `LocalizedError` only where a message reaches a person.
- No empty `catch`: log with `Logger`, then recover, map to a domain error, or rethrow. `CancellationError` is control flow, not a failure the user sees.
- Typed throws only where one domain's error is closed and every caller handles it exhaustively.

## Access control — narrowest that works

`private` → `fileprivate` → `internal` (right for app code) → `package` → `public` → `open`. `public` is the API of a local package: a promise with a documented contract. `final` on every class not designed for subclassing.

## Concurrency — the rules every file obeys

| Rule | Needs |
|---|---|
| **Async all the way.** No `DispatchSemaphore`, `.wait()`, `RunLoop.run`, blocking on a `Task`. Callbacks wrap once in `withCheckedThrowingContinuation`, resumed exactly once | Any |
| **App and UI modules default to `MainActor`; library packages stay `nonisolated`** | Swift 6.2 compiler |
| **CPU-heavy work is `@concurrent`**, never `Task.detached` | Swift 6.2 |
| **A window's work is a child of its view**: `.task { }` cancels with the view; a stored `Task { }` is cancelled on `deinit` or disappear | Any |
| **Data crossing isolation is `Sendable`** | Swift 6 mode enforces |
| **No `@unchecked Sendable` or `nonisolated(unsafe)` without a written justification** | Any |
| **No `DispatchQueue.main.async`** in new code | Any |
| **The main actor never blocks**: no disk, network, database or heavy compute | Any |

```swift
@MainActor
@Observable
final class LibraryModel {
    private(set) var state: LoadState<[Album]> = .loading
    private let client: AlbumClient

    init(client: AlbumClient) { self.client = client }

    func load() async {
        state = .loading
        do {
            state = .loaded(try await client.albums())
        } catch is CancellationError {
            return
        } catch {
            state = .failed(error)
        }
    }
}
```

In an app module with default `MainActor` isolation the explicit `@MainActor` is redundant; it stays in a package or a pre-6.2 module.

## Observation — `@Observable`

`@Observable` replaces `ObservableObject` on macOS 14+. `@State` owns the model, `@Environment` / a property passes it, `@Bindable` binds it; ownership detail is `architecture`. `@ObservationIgnored` on a task handle or logger. An `@Observable` in a package is annotated deliberately. On macOS 13 `ObservableObject` is correct. No new Combine pipelines. AppKit views read `@Observable` properties in `draw(_:)` / `layout()` and are tracked (`appkit`).

## Logging — `os.Logger` only

`print`, `NSLog`, `debugPrint`, `dump` do not ship.

```swift
import os

extension Logger {
    static let sync = Logger(subsystem: "com.example.app", category: "sync")
}

Logger.sync.info("Synced \(count, privacy: .public) albums for \(accountID, privacy: .private)")
```

One `Logger` per category, a `static let`. Interpolate into the call so the system redacts; dynamic values are `.private` unless harmless. **Never log a token, password, email, file path of the user's documents or a URL with a query.** Levels: `debug`, `info`, `notice`, `error` (a handled failure), `fault` (a broken invariant); log once at the boundary that decides.

## Common gotchas

- **Treating the template as Swift 6**: it is `SWIFT_VERSION = 5.0`; the errors you expect are silent.
- **`MainActor` default isolation on a package**: forces every consumer onto the main actor.
- **A phone-shaped app**: one window, a tab bar, commands only in buttons. Move commands to the menu bar and the content to a sidebar-detail window.
- **A hover-only control**: add a click or context-menu path (touch Macs).
- **A `static var`**: mutable global state; make it `let`, an actor, or inject it.
- **Cross-platform shell** (Electron, Tauri): detected and named, never taught here; `migration` mentions the move to native.

## Handoffs

- Concurrency depth → [`references/concurrency.md`](references/concurrency.md)
- Project, sandbox, hardened runtime, lint → `project-setup`
- State and injection → `architecture`
- Windows, menus → `windows-and-scenes`, `menus-and-commands`
- Swift 5 → 6, AppKit → SwiftUI → `migration`
- iOS counterpart → `mobile-ios:concepts`
