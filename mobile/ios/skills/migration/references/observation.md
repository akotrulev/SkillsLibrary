# `ObservableObject` → `@Observable` — per model, iOS 17+

Needs a **deployment target of iOS 17**. On iOS 16 the model stays `ObservableObject` (a finding is reported, not a rewrite) until the target moves — [`ios27-sdk-and-targets`](ios27-sdk-and-targets.md).

The iOS 27 SDK makes the `@State` macro behaviour mandatory: an `@State` property's initial value is evaluated once, not on every view re-init. Code that relied on the old re-run (an initializer with a side effect, a model built from a parameter) must be read before the SDK is linked.

## Map

| Before | After |
|---|---|
| `class M: ObservableObject` + `@Published var x` | `@Observable final class M` + `var x` |
| `@StateObject var m = M()` | `@State private var m = M()` |
| `@ObservedObject var m: M` (passed in) | `var m: M` — a plain property; `@Bindable var m: M` only when the view needs `$m.x` bindings |
| `@EnvironmentObject var m: M` / `.environmentObject(m)` | `@Environment(M.self) private var m` / `.environment(m)` |
| `$m.x` publisher | gone — [`combine-to-async`](combine-to-async.md) |
| `objectWillChange.send()` | delete; mutation notifies by itself |
| A property that must not trigger updates | `@ObservationIgnored` |

Observation tracks **the properties a view's `body` reads**, so a model with fifty properties re-renders only what reads the one that changed — the reason to migrate, and the reason a model with computed properties over other properties needs no `@Published` boilerplate.

## Steps (one model per commit)

1. List the models: `rg -n "ObservableObject|@Published|@StateObject|@ObservedObject|@EnvironmentObject" -g '*.swift'`. Start with a model no other model references.
2. Convert the class; keep it `final`; keep its isolation (`@MainActor` default in an app module, or the annotation it already had).
3. Convert **every** site that owns or receives it, in the same commit — a half-converted pair (`@StateObject` over an `@Observable`) compiles and silently owns the model twice.
4. Ownership check: **one `@State` owner per model**, created where the model's lifetime starts (the app, a scene, a screen); children receive it by parameter or `@Environment`. Two `@State` creating "the same" model is two models (C2).
5. Tests: the model's tests are unchanged; a test that observed `$x` through Combine becomes an assertion on the property after the call.
6. Previews: `#Preview` builds the model with `@State` or passes a value; no `PreviewProvider`.

## UIKit hosts

An `@Observable` read inside a `UIViewController` is tracked only where UIKit observation tracking is on (iOS 18 `updateProperties()`, `UIObservationTrackingEnabled`); on earlier targets keep the codebase's own binding ([`uikit`](../../uikit/SKILL.md), D19).

## Traps

- **`@Published` left on an `@Observable`** — no error, no effect.
- **A model created in `body`** (`let m = M()`) — recreated on every pass; own it with `@State`.
- **`@Bindable` over a `let` model passed through five views** — pass the model as a plain parameter and make a `@Bindable` only in the view that binds.
- **An `ObservableObject` kept for a Combine pipeline** — move the pipeline first, then the model.

## Done

Audit rows A4, A5, C1, C2, C3 pass for the converted models.
