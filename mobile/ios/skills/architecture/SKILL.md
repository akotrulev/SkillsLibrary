---
name: architecture
description: Use when deciding where state and logic live in a SwiftUI app — MV by default with @Observable models and services, a view model only when logic needs a test apart from the view, @State / @Binding / @Bindable / @Environment ownership, initializer injection with no container. Triggers "MVVM or not", "where does this state go". Do NOT use for fetch mechanics (`mobile-ios:networking`), persistence (`-offline-and-storage`) or routes (`-navigation`). TCA is an existing-codebase lane.
---

# iOS — Architecture and State

SwiftUI is already a state-driven view layer: a view is a function of its state, and `@Observable` models plus value-type state cover what MVVM was invented for. House order: **local `@State` first, `@Binding` to a child, an `@Observable` model when state is shared or has behaviour, `@Environment` for app-wide services, a view model only where logic must be tested apart from its view.** No DI container, no coordinator layer, no protocol per class.

## Version lane

| Concern | iOS 17+ (primary) | `[iOS16]` | `[UIKit]` |
|---|---|---|---|
| Observation | `@Observable` macro; `@State` owns it, `@Bindable` binds it | `ObservableObject` + `@Published` + `@StateObject` / `@ObservedObject` is correct for the target | UIKit Observation tracking, or the codebase's existing binding style ([`uikit`](../uikit/SKILL.md)) |
| `@State` | The iOS 27 SDK's `@State` macro fix applies | Same property wrapper | — |
| Environment | `@Environment(Type.self)` for an `@Observable`; `.environment(model)` | `@EnvironmentObject` | Initializer injection |
| Observation outside views | `withObservationTracking`; `Observations` async sequence on iOS 26+ **[Swift 6.2]** | Combine publishers are correct | — |
| TCA / Factory / swift-dependencies | **Lane only where the codebase already uses it** — [`references/tca.md`](references/tca.md) | Same | Same |

An iOS 16 project is not flagged for lacking `@Observable`; migration is [`mobile-ios:migration`](../migration/SKILL.md)'s. Swift and isolation rules (`@MainActor` default in an app module, `nonisolated` in packages) are [`basics`](../basics/SKILL.md).

## When to use

- A feature must share state across views or screens
- "Do I need a view model?", "where does this service live?"
- Injecting a client, clock or store into a view
- Choosing `@State` vs `@Bindable` vs `@Environment`

## When NOT to use

- `URLSession` clients, retries, token refresh → `mobile-ios:networking`
- SwiftData / Keychain / `UserDefaults` → `mobile-ios:offline-and-storage`
- Route paths and sheets → [`navigation`](../navigation/SKILL.md)
- Form state and validation → `mobile-ios:forms`
- Concurrency and isolation rules → [`basics`](../basics/SKILL.md)
- Existing UIKit view controllers → [`uikit`](../uikit/SKILL.md)
- Another stack → `mobile-react-native:architecture`, `mobile-android:architecture`

## Inputs needed

- Deployment target (17 vs 16) and whether the codebase already has a view-model or TCA convention
- What the state is: view-local, shared across screens, or server data
- What needs a test apart from the view

## Decision tree

```
Is it purely presentational, owned by one view (a toggle, a text field, a sheet flag)?
  yes -> @State in that view.
  no  ->
Does a child only read it or write one value?
  yes -> pass the value, or @Binding for write.
  no  ->
Is it a model with behaviour used by one screen's subtree?
  yes -> @Observable model, @State in the owning view, passed down by property / @Bindable.
  no  ->
Is it app-wide (session, settings, a client)?
  yes -> @Observable model or service built at the composition root, passed by @Environment.
```

## MV by default

An **`@Observable` model is the domain object with its behaviour** — `Order`, `Cart`, `Session` — and a view reads it directly. There is no per-screen `OrdersViewModel` mirroring it.

```swift
@Observable
final class Cart {
    private(set) var lines: [CartLine] = []
    var total: Decimal { lines.reduce(0) { $0 + $1.subtotal } }

    func add(_ item: Item, quantity: Int = 1) {
        lines.append(CartLine(item: item, quantity: quantity))
    }
}

struct CartView: View {
    @Environment(Cart.self) private var cart

    var body: some View {
        List(cart.lines) { line in
            CartLineRow(line: line)
        }
        .safeAreaInset(edge: .bottom) {
            Text(cart.total, format: .currency(code: "EUR"))
        }
    }
}
```

In an app module with default `MainActor` isolation the models need no annotation; in a package they are `@MainActor` deliberately (`basics`). **Value types for data, `@Observable final class` only where identity or shared mutable state is the point.**

## A view model is earned

Introduce `@Observable final class <Screen>Model` **only when** at least one is true:

- The screen has **logic that needs a test apart from the view**: async loading with a `loading / loaded / failed` state, validation, sorting / filtering rules, a multi-step flow.
- State is **derived from several sources** and a view would otherwise compute it in `body`.
- The same behaviour is **reused by two views** (a second real need, not an expected one).

Otherwise the view holds `@State` and calls a service. A view model is a plain model with a screen's shape — it takes its dependencies in `init`, has no reference to a view or to SwiftUI types, and is tested without a renderer.

```swift
@Observable
final class OrdersModel {
    private(set) var state: LoadState<[Order]> = .loading
    private let client: OrdersClient
    init(client: OrdersClient) { self.client = client }

    func load() async {
        state = .loading
        do { state = .loaded(try await client.orders()) }
        catch is CancellationError { return }
        catch { state = .failed(error) }
    }
}

struct OrdersView: View {
    @State private var model: OrdersModel
    init(client: OrdersClient) { _model = State(initialValue: OrdersModel(client: client)) }

    var body: some View {
        OrdersContent(state: model.state)
            .task { await model.load() }
    }
}
```

`LoadState` is one enum — never three booleans. Rendering all of its cases, including stale and offline, is [`ui-components`](../ui-components/SKILL.md) and `mobile-ios:error-handling`.

## Ownership — who creates, who borrows

| Wrapper | Meaning | Use |
|---|---|---|
| `@State` | **This view owns it.** Created once per view identity | A value, or an `@Observable` the view creates |
| `@Binding` | Read-write reference to someone else's value | A child editing a parent's value |
| `@Bindable` | Makes `$model.field` bindings from an `@Observable` | `TextField("Name", text: $model.name)` on a model passed in |
| `@Environment(Type.self)` | Read something injected above | An app-wide model or service; a system value (`\.dismiss`, `\.scenePhase`) |
| plain `let` / `var` property | Borrowed, read-only | An `@Observable` handed down; reading tracks only the properties `body` touches |

- **Create an `@Observable` with `@State`, never in a plain property** — a plain property is recreated on every parent render and loses state.
- **Never `@State` a model that was passed in** — that makes a second owner. `@State` the owner; pass the rest by property.
- `@Binding` is for values; do not pass `@Binding` to an `@Observable` — use `@Bindable`.
- `@ObservationIgnored` on what a view must not track (a `Task` handle, a logger).

## Dependencies — initializer injection, no container

- **Every dependency is a parameter of `init`.** A view receives what it needs; a model receives its client. No singleton (`Client.shared`), no service locator, no property injection.
- **The composition root is the `App` struct.** It builds the real client, store and session once, and injects them: initializer into the first view, `.environment(model)` for the few app-wide models.
- **`@Environment` is for app-wide, read-mostly things**, not a back door for every dependency. If only one subtree uses a service, pass it by `init`.
- **No DI container library.** `init` parameters and the `App` struct are the container. A protocol is introduced on the **second** implementation (a fake counts when a test needs it and the real one is not injectable otherwise); until then the concrete type is injected.
- Seams that tests replace — clock, UUID, random, config, outbound I/O — are `init` parameters or a small closure (`var now: @Sendable () -> Date`). Test usage: [`unit-testing`](../unit-testing/SKILL.md).

```swift
@main
struct MyApp: App {
    @State private var session = Session()
    private let ordersClient = OrdersClient(baseURL: AppConfig.apiBaseURL)

    var body: some Scene {
        WindowGroup {
            RootView(ordersClient: ordersClient)
                .environment(session)
        }
    }
}
```

## Server data, local data, navigation

- **Server data is fetched by a model or a `.task`, held in a `LoadState`, and refetched when the scene returns to active** (`scenePhase`). There is no client-side cache layer to add until a requirement names one; SwiftData is the persistence default ([`offline-and-storage`](../offline-and-storage/SKILL.md)).
- **Route state is a typed path owned by the navigation container** — not a property on every model ([`navigation`](../navigation/SKILL.md)).
- Sharing a model across a sheet and its presenter is by passing it down, not by a global.

## Modules

Features live in local packages with dependency direction `App → Features → Core` ([`project-setup`](../project-setup/SKILL.md)). A feature's public API is one entry view plus the types its `init` needs; its models stay `internal`.

## Rules

- `@State` owns, `@Bindable` binds, `@Environment` reads app-wide; never two owners.
- An `@Observable` is created with `@State` in the view that owns it.
- A view model exists only for logic that needs a test apart from the view.
- Initializer injection; the `App` struct is the composition root; no container, no `shared`, no locator.
- A protocol arrives with its second implementation.
- State that is a mode is one enum, not several booleans.
- iOS 17+ uses `@Observable`; `ObservableObject` stays only on iOS 16 targets or existing code awaiting migration.
- TCA is used only where the codebase already is on it.

## What NOT to do

- Add `XViewModel` for every `XView` by reflex, or a model whose properties mirror a struct one for one.
- Put a network call, `UserDefaults` read or formatter setup in `body`.
- Keep an `@Observable` in a plain `let` created inside `body`.
- Pass `@Environment` everything; inject a service no view reads.
- Introduce a coordinator, router object or "AppState" god-model alongside `NavigationStack(path:)`.
- Use `@MainActor` on every type of a module already defaulting to `MainActor`.
- Add TCA, Factory or swift-dependencies to a project that did not choose them.

## Validation (exit gate)

- [ ] Every `@Observable` is owned by exactly one `@State`; borrowed everywhere else
- [ ] Each view model has a stated reason (a test, a derivation, a second user)
- [ ] All dependencies arrive via `init` or `@Environment` from the `App` composition root; no `.shared`
- [ ] No protocol with one implementation; no container library
- [ ] Loading states are one enum covering loading, loaded, failed

## Handoffs

- Views, previews, `.task` → [`ui-components`](../ui-components/SKILL.md)
- Routes → [`navigation`](../navigation/SKILL.md)
- Clients and retries → `mobile-ios:networking`
- Persistence → `mobile-ios:offline-and-storage`
- Failure, stale, offline UI → `mobile-ios:error-handling`
- Tests for models → `mobile-ios:unit-testing`
- `ObservableObject` → `@Observable` → `mobile-ios:migration`
- Concurrency and isolation → [`basics`](../basics/SKILL.md)
