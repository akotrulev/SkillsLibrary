# Swift concurrency — isolation, `Sendable`, cancellation, escape hatches

Depth for [`../SKILL.md`](../SKILL.md). Every rule names the switch it needs: **Swift 6 language mode**, **default actor isolation** (Swift 6.2 compiler, SE-0466) or **Approachable Concurrency** (Swift 6.2 compiler, SE-0461 / SE-0470). They are independent — check which the module has (`SWIFT_VERSION`, `SWIFT_DEFAULT_ACTOR_ISOLATION`, `SWIFT_APPROACHABLE_CONCURRENCY`, or `swiftSettings` in `Package.swift`) before reasoning. The Xcode 27 app template is still Swift 5 mode.

## 1. Isolation by module kind

| Module | Default isolation | Why |
|---|---|---|
| **App target, UI-only local packages** | `MainActor` | Almost everything touches views or models views read. Setting it removes a wall of `@MainActor` and makes the single-threaded case the one with no ceremony |
| **Library package** (networking client, parsing, storage, domain logic, an Expo native module's pure logic) | `nonisolated` | A library must not force its callers onto the main actor, and must run from a background task |
| **Mixed** | Split into two modules | Do not annotate your way around one module doing both jobs |

```swift
// swift-tools-version: 6.2
let package = Package(
    name: "OrdersUI",
    targets: [
        .target(
            name: "OrdersUI",
            swiftSettings: [.defaultIsolation(MainActor.self)]
        ),
        .target(name: "OrdersCore")
    ]
)
```

`OrdersCore` takes no setting and stays `nonisolated`. In an Xcode project the same choice is the target's *Default Actor Isolation* build setting.

- A type in a `MainActor`-default module that must work off the main actor says **`nonisolated`** (or is an `actor`); a value type that is plain data is usually `nonisolated struct` so a background caller can use it.
- **`@MainActor` on a library type** is correct only for a type that is genuinely UI-facing (`UIViewRepresentable` bridge, a view-bound model). Never blanket a package.
- Below Swift 6.2 there is no default-isolation setting: annotate `@MainActor` explicitly on UI types. A pre-6.2 project is not flagged for lacking it.

## 2. Where async work runs

| Declaration | Runs on | Needs |
|---|---|---|
| `func f() async` in a `MainActor`-default module | The main actor | Default isolation |
| `nonisolated func f() async` | **Caller's actor** with Approachable Concurrency (`nonisolated(nonsending)` is the default, SE-0461); the **global concurrent executor** without it | Approachable Concurrency decides |
| `@concurrent func f() async` | Always the global concurrent executor — off the caller's actor | Swift 6.2 |
| `nonisolated(nonsending) func f() async` | Caller's actor, written explicitly | Swift 6.2 |

- **Put CPU work behind `@concurrent`**: image decode and resize, JSON for a large payload, sorting a large collection, compression. The function's *caller* stays simple (`await`), and the work cannot block the main actor.
- **A `@concurrent` function cannot touch actor-isolated state directly**; it takes `Sendable` values in and returns `Sendable` values out.
- **Do not reach for `Task.detached` to leave the main actor.** It drops priority, task-locals and cancellation propagation. `@concurrent` is the tool; `Task.detached` needs a written reason.
- **Without Approachable Concurrency, a plain `nonisolated async` function running on the global executor is a trap in library code that takes non-`Sendable` arguments** — turn the feature on for new modules, or mark the function `nonisolated(nonsending)` deliberately.

## 3. `Sendable` — what may cross an isolation boundary

A value crossing from one isolation domain to another (a task, an actor call, a `@concurrent` function) must be `Sendable`. **Swift 6 mode makes a violation an error; Swift 5 mode reports it as a warning or not at all** — the rule applies to both.

| Type | `Sendable`? |
|---|---|
| `struct` / `enum` whose stored properties are all `Sendable` | Yes — inferred for internal types; **declare it on `public` types** |
| `actor`, `@MainActor` class | Yes — isolation is the protection |
| `final class` with only immutable (`let`) `Sendable` properties | Yes — declare `: Sendable` |
| Class with mutable state | No — make it an `actor`, a `@MainActor` class, or a `struct` |
| A closure | `@Sendable` closure must capture only `Sendable` values; `sending` parameters transfer ownership of a value across the boundary (SE-0430) |

Fix a diagnostic in this order — stop at the first that works:

1. **Make the type a `struct`** (value type, `Sendable` for free).
2. **Make it an `actor`** if it owns shared mutable state.
3. **Isolate it to `MainActor`** if it is UI-bound.
4. **Pass a `sending` value** if ownership moves and the caller no longer uses it.
5. Escape hatch (section 6) — last, with a justification.

**[Swift 6.4]** `~Sendable` marks a type as deliberately not `Sendable`, so the compiler stops inferring it. Use it on a type whose design forbids crossing domains.

**Isolated conformances (SE-0470, Approachable Concurrency, Swift 6.2).** A `@MainActor` type may conform to a protocol with the conformance itself isolated: `extension Model: @MainActor Equatable`. The conformance is usable only from the main actor, which removes the old "nonisolated protocol requirement" workarounds.

## 4. Actors — when and how

An `actor` serialises access to its mutable state. Reach for one only for **shared mutable state used from several isolation domains** (a token-refresh coordinator, an in-memory cache with concurrent readers). A `MainActor`-isolated model needs no actor.

- Keep actor methods short and **never hold state across an `await` that another caller could interleave with** — reentrancy means state read before an `await` may have changed after it. Re-check or restructure so the critical section has no suspension.
- An actor is a reference type with identity; one concrete actor, no protocol until a second implementation exists.
- Do not make an actor "to be safe" around a value that is only ever touched by one task.

## 5. Cancellation — a screen's work dies with the screen

Cancellation in Swift is **cooperative**: cancelling a `Task` sets a flag; the code must look.

- **SwiftUI: `.task { await model.load() }`** — the system cancels it when the view disappears. `.task(id: query) { … }` restarts and cancels the previous run when `query` changes; this is the search-as-you-type pattern.
- **An unstructured `Task { }` is a stored handle**: keep it in a property, cancel it in `deinit` or on disappear, and replace-and-cancel when a new request supersedes it.
- **Children cancel with the parent.** `async let` and `withTaskGroup` children are cancelled when the enclosing scope is cancelled or throws; prefer them to `Task { }` for fan-out.
- **Check at suspension points that matter**: `try Task.checkCancellation()` before expensive work, `Task.isCancelled` in a long loop. `URLSession`'s async APIs, `Task.sleep` and `AsyncSequence` iteration already throw on cancel.
- **`CancellationError` is control flow, not a failure.** Catch it separately (`catch is CancellationError { return }`) and do not set a `failed` state or show an error banner for it.
- **Wrap blocking callbacks with `withTaskCancellationHandler`** when the underlying operation can be cancelled (`URLSessionTask`, a `CLLocationManager` request): the handler runs on cancel and tears the operation down.
- **`withCheckedThrowingContinuation` is resumed exactly once**, on every path including cancellation and failure — a leaked continuation hangs the task; a double resume traps.
- **Never `Task.sleep` to wait for a condition** — await the event, or poll with a bounded, cancellable loop.

```swift
.task(id: query) {
    do {
        results = try await search.run(query)
    } catch is CancellationError {
        return
    } catch {
        state = .failed(error)
    }
}
```

## 6. Escape hatches and the written-justification rule

| Escape hatch | What it tells the compiler | Allowed when |
|---|---|---|
| `@unchecked Sendable` | "Trust me, this is thread-safe" | A type that is made safe by something the compiler cannot see: a lock (`OSAllocatedUnfairLock`, `Mutex`), a serial queue, immutability behind an Objective-C API |
| `nonisolated(unsafe)` | "No isolation, no checking" on a variable | A write-once global or an Objective-C-owned singleton read after a happens-before the compiler cannot see |
| `@preconcurrency import` / `@preconcurrency` conformance | "This module predates concurrency checking" | A dependency you do not own that has not adopted `Sendable`; removed when it does |
| `assumeIsolated` / `MainActor.assumeIsolated` | "I am on this actor" — crashes if wrong | A callback documented to arrive on the main thread but not annotated |
| `Task.detached` | New task with no inherited context | The work must not inherit priority, actor or task-locals — and you can say why |

**The rule: an escape hatch carries a justification in the same declaration, and a reader can check it.** No `@unchecked Sendable` or `nonisolated(unsafe)` without one (CLAUDE.md § Mobile code rules). The audit finds the hatch and then reads for the justification.

- A justification states **the invariant that makes it safe and what enforces it** — "guarded by `lock` on every access", "assigned once in `application(_:didFinishLaunching:)` before any task starts", "the Objective-C header documents main-thread delivery".
- Where the project's lint supports it, put the reason in the directive's own justification field; otherwise it is the one place a short doc comment on the declaration is permitted, because a unsafe-by-construction contract is exactly what a name cannot carry (CLAUDE.md § Comments — a non-obvious invariant the code enforces but does not state).
- **A hatch used to silence a diagnostic you do not understand is a defect, not a justification.** Go back to section 3's ordered fixes.
- Prefer deleting the need: wrap the unsafe state in an `actor` or a `Mutex`-guarded `final class` once, and let everything else stay checked.

```swift
final class TokenCache: @unchecked Sendable {
    private let lock = OSAllocatedUnfairLock<String?>(initialState: nil)

    var token: String? {
        get { lock.withLock { $0 } }
        set { lock.withLock { $0 = newValue } }
    }
}
```

The justification for `TokenCache` is on its declaration: *"Every access to the stored token goes through `lock`; the class has no other mutable state."*

## 7. Bridging legacy code

- **Callbacks / delegates → `async`:** one `withChecked(Throwing)Continuation` per callback, in one adapter, resumed once; do not scatter continuations through feature code.
- **Delegates that deliver a stream → `AsyncStream`**; finish the stream in the delegate's teardown and set `onTermination` to cancel the source.
- **Combine → `async` / `Observations`** [Swift 6.2, iOS 26+] is `mobile-ios-migration`'s path; new code does not add Combine.
- **`DispatchQueue.main.async` → `@MainActor`** or `await MainActor.run { }`; GCD survives only in a legacy API that demands a queue.
- **Objective-C completion handlers** import as `async` automatically; a handler that can be called more than once does not, and gets an `AsyncStream` adapter.
