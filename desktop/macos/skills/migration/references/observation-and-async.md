# `ObservableObject` → `@Observable`, and Combine → async

Two moves in this order, each its own commit series. `@Observable` needs **macOS 14**; below it, `ObservableObject` is correct and not a finding. Re-read the Observation documentation on the installed SDK before a run.

## A. `ObservableObject` → `@Observable` (macOS 14+)

Per model, leaves first (models no other model owns).

| Before | After |
|---|---|
| `final class Library: ObservableObject` with `@Published var albums` | `@Observable final class Library` with `var albums` |
| `@StateObject private var library = Library()` in the view that creates it | `@State private var library = Library()` |
| `@ObservedObject var library: Library` (passed in) | `var library: Library`; add `@Bindable var library` only where a binding (`$library.title`) is needed |
| `@EnvironmentObject var library: Library` | `@Environment(Library.self) var library`, injected with `.environment(library)` |
| `objectWillChange` observers | Delete; read the property where it is used |

Rules:

- **One owner per model.** `@State` owns an `@Observable` in the view that creates it; a model created in `body` or held in a plain `let` is rebuilt on every render. Window-scoped models are created per window; app-wide models once in the `App` ([`architecture`](../../architecture/SKILL.md)).
- **Mark properties that must not track** with `@ObservationIgnored` (a cache, a task handle).
- **`@MainActor` stays where the UI reads the model**; with default MainActor isolation in the app target there is no annotation to add.
- **Do not mix**: an `@Observable` under a `@StateObject` compiles and misbehaves. Convert the model and every use of it in one commit.
- **AppKit readers.** Reads of `@Observable` properties inside `draw(_:)`, `layout()`, `updateConstraints()` and the view-controller equivalents are tracked on the 2026 releases; back-deploying to macOS 15 needs `NSObservationTrackingEnabled` in `Info.plist`, and below 15 an AppKit view observes with `withObservationTracking` ([`appkit`](../../appkit/SKILL.md)).
- A model passed to a background actor still crosses by identifier or a `Sendable` value, never by reference.

Verify: the window that owned the model keeps its state across a re-render; two windows on one model both update; the test that failed on the old behaviour passes.

## B. Combine → async

A pipeline at a time, never the whole app.

| Before | After |
|---|---|
| `publisher.sink { … }.store(in: &bag)` driving UI | A `.task` in the view reading an `AsyncSequence`, or an `@Observable` property |
| `@Published` read by a view | An `@Observable` property (move A) |
| `NotificationCenter.default.publisher(for:)` | `NotificationCenter.default.notifications(named:)` in a `.task`; wake and activation arrive as an `AsyncStream` made at the root |
| `Timer.publish` | A `Task` with a clock `sleep`, cancelled with its owner |
| `debounce`, `removeDuplicates` | Algorithm in `swift-async-algorithms` only if the project already depends on it; otherwise a small `Task` with a clock |
| `URLSession.dataTaskPublisher` | `try await session.data(for:)` ([`networking`](../../networking/SKILL.md)) |

`Observations` (an `AsyncSequence` over `@Observable` state) needs macOS 26; below it, observe with `withObservationTracking` or read the property in the view. Convert the pipeline, not the surface: wrapping `.values` around every publisher moves the problem. Every unstructured `Task` is stored and cancelled when its owner (window, model) goes.

Verify: a test feeds the stream with a fake clock or a hand-made `AsyncStream` and asserts the state; no `Task.sleep` in the test.
