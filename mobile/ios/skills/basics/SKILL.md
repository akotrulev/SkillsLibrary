---
name: concepts
description: Use when writing or reviewing Swift — API Design Guidelines naming, value vs reference types, optionals, errors, access control, the Swift 6 concurrency standard (default isolation, Sendable, cancellation), Observation, os.Logger. Triggers "is this Swift idiomatic", "@MainActor by default or not", "can I use !", "Sendable error". Also the Expo native-module Swift standard. Do NOT use for project setup, SwiftUI screens, or networking (`mobile-ios:project-setup`, `-ui-components`, `-networking`).
---

# iOS — The Swift Coding Standard

How Swift is written in this library: names that read as English at the call site, value types by default, no force unwrap, typed errors, the narrowest access control, the Swift 6 concurrency standard, `@Observable` and `os.Logger`. The audit rows are sections A and B of `mobile-ios:standards-audit`.

**Reads without an app.** This skill is also loaded by `mobile-react-native` for Expo Modules and config-plugin Swift. Nothing here needs a SwiftUI app or an Xcode project: apply it to a module's `.swift` files as they stand. Where a rule depends on the module kind, it says so. App-level skills (`mobile-ios:project-setup`, `-architecture`, `-ui-components`, `-networking`) are named for hand-off only — never required to apply this one.

## Version lane — detect first, key every recipe to it

Read `SWIFT_VERSION` / `swiftLanguageModes`, the toolchain (`swift --version`), the deployment target and the existing isolation settings **before** writing. Never up-level a project's language mode, toolchain or deployment target as a side effect.

| Switch | What it is | Needs | Default in an Xcode 27 template |
|---|---|---|---|
| **Swift language mode** (`SWIFT_VERSION` = 6, `swiftLanguageModes: [.v6]`) | Data-race safety diagnostics are **errors** | Swift 6 compiler | **Still Swift 5** (`SWIFT_VERSION = 5.0`) — new modules set 6 |
| **Default actor isolation** (`MainActor`, SE-0466) | Unannotated declarations in the module are `@MainActor` | Swift **6.2** compiler; works in either language mode | `nonisolated`; the app template may set `MainActor` |
| **Approachable Concurrency** (`SWIFT_APPROACHABLE_CONCURRENCY`) | The bundle of upcoming features behind SE-0461 (`nonisolated(nonsending)` by default) and SE-0470 (isolated conformances inferred) | Swift **6.2** compiler; works in either language mode | Off unless the template turns it on |

These are **three separate switches**; a rule below that needs one says which. Swift 6 mode without the other two is common in packages; Swift 5 mode with default `MainActor` isolation is common mid-migration. Never assume one implies another.

| Concern | Xcode 27 / Swift 6.4 (primary) | Xcode 26 / Swift 6.2–6.3 (supported) |
|---|---|---|
| Default isolation, `@concurrent`, `nonisolated(nonsending)`, isolated conformances | Available | Available (introduced in 6.2) |
| `await` in `defer`, `weak let`, `~Sendable` | Available **[Swift 6.4]** | Not available — use the 6.2 pattern in the right-hand cells below |
| `@Observable` | iOS 17+ | iOS 17+; on iOS 16 `ObservableObject` is correct |
| `Observations` async sequence | iOS 26+ **[Swift 6.2]** | iOS 26+ |

Swift 5-mode modules are migrated **one module at a time** (`mobile-ios:migration`). Below Swift 6.2, `@MainActor` is annotated explicitly and `@concurrent` does not exist — a down-level project is not flagged for lacking them.

## When to use

- Writing Swift in an app, a local package or an Expo native module
- "Should this be a struct or a class?", "may I force-unwrap here?", "which error type?"
- Choosing isolation for a new module; fixing a `Sendable` diagnostic

## When NOT to use

- Creating the project, targets, xcconfig, SwiftLint → `mobile-ios:project-setup`
- Choosing app architecture or state ownership → `mobile-ios:architecture`
- SwiftUI views and previews → `mobile-ios:ui-components`
- `URLSession` clients and retries → `mobile-ios:networking`
- Tests → `mobile-ios:unit-testing`
- Kotlin → `mobile-android:concepts`

---

## Naming — the API Design Guidelines

The call site is the unit of design. A name is right when the line reading `cart.add(item, quantity: 2)` is a sentence.

- **Clarity at the point of use**, not brevity. Include every word needed to remove ambiguity; omit words the types already say. `remove(_ member: Element)`, not `removeElement(_ member: Element)`.
- **Name by role, not by type.** `var greeting: String`, not `var string: String`.
- **Methods that do something read as imperative verbs; their non-mutating partner reads as a noun or `-ed`/`-ing`**: `sort()` / `sorted()`, `append(_:)` / `appending(_:)`.
- **Boolean properties read as assertions**: `isEmpty`, `hasUnreadMessages`, `canRetry`.
- **Argument labels**: the first label drops only when it cannot be mistaken for part of the base name; prepositions start a label (`move(from:to:)`); defaulted arguments come last.
- **Types and cases are `UpperCamelCase`; everything else `lowerCamelCase`**; acronyms uniform in case (`URLSession`, `userID`). No type-name prefixes — modules are the namespace.

```swift
struct Cart {
    private(set) var lines: [CartLine] = []

    mutating func add(_ item: Item, quantity: Int = 1) {
        lines.append(CartLine(item: item, quantity: quantity))
    }

    func removing(_ item: Item) -> Cart {
        var copy = self
        copy.lines.removeAll { $0.item.id == item.id }
        return copy
    }

    var isEmpty: Bool { lines.isEmpty }
}
```

## Value types by default

**`struct` and `enum` first; `class` only when identity or shared mutable state is the point.** Value semantics make copies independent, make data races structurally impossible for plain data, and make `Sendable` free.

| Use | When |
|---|---|
| `struct` | Data with value semantics: models, DTOs, view state, configuration |
| `enum` with associated values | A closed set of cases — screen state, route, result, error. Model "loading / loaded / failed" as one enum, never three booleans |
| `final class` | Identity matters (a session, a connection, a cache), you need `deinit`, or an `@Observable` model that views share |
| `actor` | Shared mutable state accessed from several isolation domains — see [`references/concurrency.md`](references/concurrency.md) |
| `class` (non-final) | Only to subclass a framework type (`UIViewController`, `NSObject`); everything else is `final` |

- **Composition over inheritance.** A protocol with one conformer is an unearned abstraction — introduce it on the second real need.
- **`let` over `var`**; `private(set)` when callers read but must not write. A `var` that is never reassigned is a defect.
- **`Equatable` / `Hashable` / `Codable` by synthesis**; `Identifiable` with a stable domain id on anything listed.

## Optionals — no force unwrap outside tests

**`!`, `as!` and `try!` do not appear outside test code.** A crash on `nil` is a bug the type system offered to prevent.

| Instead of | Write |
|---|---|
| `value!` | `guard let value else { return }` / `if let value` / `value ?? fallback` |
| `dict[key]!` | `guard let x = dict[key] else { throw LookupError.missing(key) }` |
| `as! T` | `as? T` with a `guard` |
| `try! f()` | `do { try f() } catch { … }` or let it `throw` |
| `var x: T!` (implicitly unwrapped) | A non-optional with an initializer, or a real optional — the one framework-owned exception is an `@IBOutlet` in UIKit code |
| `fatalError("unreachable")` | An `enum` whose exhaustive `switch` makes the case unrepresentable |

- **`guard` for early exit** keeps the happy path unindented; `if let` for a scoped use. Shorthand `if let value` / `guard let value` is the house style.
- **Never optional-of-collection** — an empty array already means "none". Do not make a property optional to avoid initialising it; model genuine absence with an `enum` state.
- **`try?` discards the reason.** Use it only where the failure has no handler and no user consequence, and never to silence an error the user should see.

## Errors

- **Functions `throw`; they do not return a sentinel or `(value, error)`.** The caller decides whether a failure is recoverable.
- **One `Error` enum per failure domain**, cases named for what went wrong, with associated values carrying the evidence (the status code, the key, the underlying error). Conform to `LocalizedError` only at the layer that shows a message to a person.
- **Typed throws (`throws(NetworkError)`)** only where one domain's error type is closed and every caller handles it exhaustively; plain `throws` across module boundaries. Never retrofit it across an existing API as a side effect.
- **No empty `catch`.** A catch logs what it caught with `Logger` and either recovers, maps to a domain error, or rethrows.
- **A `CancellationError` is not a failure the user sees** — see the concurrency reference.

## Access control — narrowest that works

`private` → `fileprivate` → `internal` (the default) → `package` → `public` → `open`.

- Start `private`; widen on a real caller. **`internal` is the default and is right for app code.**
- **`public` is only the API of a local package or library module** — a public type has `public init`, public members, and a documented contract; a `public` symbol is a promise.
- **`package`** for cross-module access inside one SwiftPM package or Xcode workspace without publishing it.
- **`open` only when subclassing outside the module is designed.**
- `private(set)` for read-only state; `final` on every class not designed for subclassing.

## Concurrency — the standard

Structured, cancellable, isolation-explicit. The full treatment — isolation, `Sendable`, task cancellation, escape hatches — is [`references/concurrency.md`](references/concurrency.md); the rules every file obeys:

| Rule | Needs |
|---|---|
| **Async all the way.** No `DispatchSemaphore`, `.wait()`, `RunLoop.run` or blocking on a `Task`'s result. Callbacks wrap once with `withCheckedThrowingContinuation`, resumed exactly once | Any |
| **App and UI modules default to `@MainActor`.** Set the module's default isolation to `MainActor`; a type that must run elsewhere says `nonisolated` | Swift 6.2 compiler; either language mode |
| **Library packages are `nonisolated` by default.** A package must not assume a main-actor caller; annotate individual UI-facing types `@MainActor` | Any |
| **CPU-heavy work is `@concurrent`** (an `async` function that runs off the caller's actor). Never `Task.detached` to get off the main actor | Swift 6.2 |
| **Plain `async` functions stay on the caller's actor** — `nonisolated(nonsending)` is the default with Approachable Concurrency; without it, `nonisolated async` hops to the global executor | Approachable Concurrency (SE-0461) |
| **A screen's work is a child of the view** — `.task { }` cancels with the view. An unstructured `Task { }` is stored and cancelled in `deinit` / on disappear, or it is a bug | Any |
| **Data crossing isolation is `Sendable`.** Structs of `Sendable` fields are; mutable classes are not | Swift 6 mode makes it an error |
| **No `@unchecked Sendable` or `nonisolated(unsafe)` without a written justification** next to it | Any |
| **No `DispatchQueue.main.async` / GCD in new code** — `@MainActor` and `await MainActor.run` | Any |

```swift
@MainActor
@Observable
final class OrdersModel {
    private(set) var state: LoadState<[Order]> = .loading
    private let client: OrdersClient

    init(client: OrdersClient) { self.client = client }

    func load() async {
        state = .loading
        do {
            state = .loaded(try await client.orders())
        } catch is CancellationError {
            return
        } catch {
            state = .failed(error)
        }
    }
}
```

In an app module with default `MainActor` isolation the explicit `@MainActor` above is redundant and omitted; it stays in a package or a Swift 5-mode / pre-6.2 module.

**[Swift 6.4]** `await` is allowed in `defer`, `weak let` is a declaration form, and `~Sendable` lets a type say it is deliberately not `Sendable`. Use them where the toolchain is 6.4; they are not required, and a 6.2–6.3 project is not flagged for lacking them.

## Observation — `@Observable`

On iOS 17+ **`@Observable` replaces `ObservableObject`** — no `@Published`, no `objectWillChange`, no `@StateObject`. SwiftUI re-renders only the views that read a changed property.

- `@Observable final class` for a shared model; `@State` owns it in the view that creates it, `@Environment` / a plain property passes it down, `@Bindable` makes a binding to its properties. Ownership details are `mobile-ios:architecture`'s.
- **`@ObservationIgnored`** on properties a view must not track (a task handle, a logger).
- **`@Observable` inherits the module's default isolation** — in an app module that is `@MainActor`, which is what a UI model wants. A non-UI `@Observable` in a package is annotated deliberately.
- **Outside SwiftUI**, `withObservationTracking`, or on iOS 26+ the **`Observations`** async sequence **[Swift 6.2]**. No new Combine pipelines.
- **iOS 16:** `ObservableObject` + `@Published` is correct for that target; migration is `mobile-ios:migration`'s.

## Logging — `os.Logger` only

`print`, `NSLog`, `debugPrint` and `dump` do not ship. **`Logger` from `os`** is the only logging API: structured, level-filtered, privacy-aware, visible in Console and Instruments.

```swift
import os

extension Logger {
    static let sync = Logger(subsystem: "com.example.app", category: "sync")
}

Logger.sync.info("Synced \(count, privacy: .public) orders for \(accountID, privacy: .private)")
```

- **Subsystem = bundle id of the module, category = the component.** One `Logger` per category, a `static let` on an extension — a constant, not mutable state.
- **Message templates, never prebuilt strings.** Interpolate values into the `Logger` call so the system can redact them; `Logger.x.info("\(String(describing: v))")` defeats it.
- **Dynamic values are `.private` by default**; mark `.public` only for non-sensitive values (counts, enum cases, ids that are not personal). **Never log a token, password, email, card number or a URL with a query.**
- **Levels**: `debug`, `info`, `notice`, `error` (a handled failure), `fault` (a broken invariant). Log once at the boundary that decides, not at every layer a rethrow passes.

## Common gotchas

- **Setting `MainActor` default isolation on a package** — it forces every consumer onto the main actor and breaks background use. Packages stay `nonisolated`.
- **Treating the Xcode template as Swift 6** — it is still `SWIFT_VERSION = 5.0`; strict concurrency errors you expect will be silent warnings or nothing.
- **`nonisolated async` hopping to the global executor** in a module without Approachable Concurrency — the same function runs on the caller's actor with it on. State which the module has before reasoning.
- **A `static var`** — mutable global state; make it `let`, an actor, or inject it.
- **`try?` swallowing a failure the user must see** — surface it as the `failed` state.
- **`Task { }` in `onAppear`** with no cancellation — use `.task`.

## Handoffs

- Concurrency depth, escape-hatch justifications → [`references/concurrency.md`](references/concurrency.md)
- Project, targets, Swift 6 mode, lint → `mobile-ios:project-setup`
- State ownership and architecture → `mobile-ios:architecture`
- Swift 5 → 6, `ObservableObject` → `@Observable` → `mobile-ios:migration`
- Telemetry and crash export → `mobile-<stack>:observability`
- Kotlin counterpart → `mobile-android:concepts`
