# Swift concurrency on the Mac — isolation, `Sendable`, cancellation, escape hatches

Depth for [`../SKILL.md`](../SKILL.md). Adapted from `mobile-ios`. Every rule names its switch: **Swift 6 language mode**, **default actor isolation** (Swift 6.2 compiler, SE-0466) or **Approachable Concurrency** (SE-0461 / SE-0470). Check `SWIFT_VERSION`, `SWIFT_DEFAULT_ACTOR_ISOLATION`, `SWIFT_APPROACHABLE_CONCURRENCY` or `swiftSettings` first.

## 1. Isolation by module kind

| Module | Default isolation | Why |
|---|---|---|
| App target, UI-only local package | `MainActor` | Nearly everything touches views or models views read |
| Library package (networking, parsing, storage, domain logic, an XPC service's logic) | `nonisolated` | Must run from a background task and from a helper with no UI |
| Mixed | Split into two modules | Do not annotate around one module doing both jobs |

```swift
// swift-tools-version: 6.2
let package = Package(
    name: "LibraryUI",
    targets: [
        .target(name: "LibraryUI", swiftSettings: [.defaultIsolation(MainActor.self)]),
        .target(name: "LibraryCore")
    ]
)
```

A `nonisolated` type in a `MainActor` module is plain data or work for a background caller. Below Swift 6.2, annotate `@MainActor` explicitly; a pre-6.2 project is not flagged.

## 2. Where async work runs

| Declaration | Runs on |
|---|---|
| `func f() async` in a `MainActor`-default module | The main actor |
| `nonisolated func f() async` | The caller's actor with Approachable Concurrency; the global executor without it |
| `@concurrent func f() async` | Always the global executor (Swift 6.2) |

Put CPU work behind `@concurrent`: image decode, large JSON, sorting a large `Table` data set, hashing a file. It takes and returns `Sendable` values. `Task.detached` needs a written reason.

## 3. `Sendable`

A value crossing an isolation boundary is `Sendable`. Fix a diagnostic in order: make it a `struct`; make it an `actor`; isolate it to `MainActor`; pass a `sending` value; escape hatch last. Declare `Sendable` on `public` types. **[Swift 6.4]** `~Sendable` marks a type deliberately not `Sendable`. Isolated conformances (`extension Model: @MainActor Equatable`) need Approachable Concurrency.

## 4. Actors

Only for shared mutable state used from several domains (a token-refresh coordinator, a cache with concurrent readers). Keep methods short; state read before an `await` may have changed after it. One concrete actor, no protocol until a second implementation exists.

## 5. Cancellation

Cooperative: cancelling sets a flag and the code must look.

- `.task { }` cancels when the window's view goes; `.task(id:)` restarts on change.
- A stored `Task { }` is cancelled in `deinit` or on disappear, and replaced-and-cancelled when a newer request supersedes it.
- `async let` and task-group children cancel with the parent.
- `try Task.checkCancellation()` before expensive work; `URLSession`, `Task.sleep` and `AsyncSequence` already throw.
- `CancellationError` is caught separately and never becomes a `failed` state or a banner.
- `withTaskCancellationHandler` when the operation can be torn down; a continuation is resumed exactly once on every path.
- A **window that closes cancels the work it started**; work that must outlive it belongs to an app-wide model.

## 6. Escape hatches

`@unchecked Sendable` and `nonisolated(unsafe)` need a comment-free justification in the type's doc comment: what protects the state (a lock, a serial queue, immutability after init) and why a safer form does not fit. A framework callback that is not `Sendable` is wrapped once, at the edge, never spread through the module. `DispatchQueue.main.async` and `Task.detached` are not escape hatches; they are the code to replace.
