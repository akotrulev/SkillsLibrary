# Combine → async / `Observations` — a pipeline at a time

Combine is not deprecated and a working pipeline is not a defect. This move exists for code the codebase is already touching, and for the places Combine fights Swift 6 isolation. **Convert the pipeline, never wrap it**: a `publisher.values` around an unchanged chain keeps Combine's threading and `Sendable` problems and adds an adapter.

## Version gates

| Need | Floor |
|---|---|
| `async` / `await`, `AsyncStream`, `Task` | iOS 13 with the back-deployed runtime; every supported target |
| `NotificationCenter.default.notifications(named:)`, `URLSession` async APIs | iOS 15 |
| `@Observable` change streams through `Observations { }` (SE-0475, Swift 6.2) | **iOS 26** — gate with `#available`, or use `withObservationTracking` on lower targets |
| `Publisher.values` (the adapter) | iOS 15 — a bridge for a boundary you do not own, not a destination |

## Map

| Combine | Replacement |
|---|---|
| `URLSession.dataTaskPublisher` + `decode` + `sink` | `try await session.data(for:)` + `Codable` ([`networking`](../../networking/SKILL.md)); a `Task` owned by `.task` / `.task(id:)` |
| `$property.sink` on an `ObservableObject` | An `@Observable` read in `body`; outside a view, `Observations { model.x }` (iOS 26) or `withObservationTracking` |
| `PassthroughSubject` / `CurrentValueSubject` as an event bus | `AsyncStream` with its continuation, or a method call — an event bus between two types is usually a missing parameter |
| `debounce`, `throttle`, `removeDuplicates` | `.task(id:)` with a `Task.sleep(for:)` at the top for debounce (cancelled when the key changes); `removeDuplicates` is `if new != old` before the work |
| `combineLatest`, `merge` | `async let` for independent loads; an `AsyncStream` merge only where two live streams must combine — rare |
| `NotificationCenter.publisher(for:)` | `for await _ in NotificationCenter.default.notifications(named:)` inside a `.task` |
| `Timer.publish` | A `.task` with `while !Task.isCancelled { try await Task.sleep(for:); … }` |
| `AnyCancellable` bag | Gone: the `Task` is cancelled with the view (`.task`) or by the owner's stored `Task` handle |

## Steps (one pipeline per commit)

1. `rg -n "import Combine|\.sink|\.assign\(|AnyCancellable|PassthroughSubject|CurrentValueSubject|\.eraseToAnyPublisher" -g '*.swift'`. Pick a pipeline with a test, or write the test first against the current behaviour ([`unit-testing`](../../unit-testing/SKILL.md)).
2. Decide the owner of the work: a view (`.task`) or a model (a stored `Task` cancelled in `deinit` / on sign-out). Work with no owner is the bug the migration removes.
3. Rewrite the pipeline as `async` code; preserve the cancellation behaviour — Combine cancelled on `AnyCancellable` deinit, the `Task` must be cancelled by the owner.
4. Keep `CancellationError` silent (B7); the failed state is for real failures.
5. Remove `import Combine` from the file only when nothing else in it uses it.

## Leave alone

- Combine inside a third-party SDK's public API you do not own — wrap at the boundary, once.
- A pipeline whose operators have no async equivalent worth writing (a ten-input `combineLatest` feeding a form) until it is being changed anyway.

## Done

Audit rows B8, B9, B11, D1, H3 pass for the converted code; no `AnyCancellable` remains where the pipeline was.
