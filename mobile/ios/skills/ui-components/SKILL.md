---
name: mobile-ios-ui-components
description: Use when writing SwiftUI views — small views, #Preview, .task for loads cancelled with the view, loading / loaded / failed / stale / offline regions, List and lazy stacks, SF Symbols, no work in body. Triggers "build this screen", "view is slow to render", "load data when it appears", "add a preview". Do NOT use for state ownership (`mobile-ios-architecture`), theming (`-styling`), routes (`-navigation`), forms (`-forms`) or UIKit (`-uikit`).
---

# iOS — SwiftUI Views

Writes SwiftUI views that are small, previewable, cancel their own work and render every state of their data. State and injection are [`architecture`](../architecture/SKILL.md); colour, type and Liquid Glass are [`styling`](../styling/SKILL.md); the Swift is [`basics`](../basics/SKILL.md). Design facts come from `design/ui-ux-pro-max` — `search.py "<query>" --stack swiftui` (rows 1–4 Views, 14 / 24–26 Lists, 30–31 Async, 36–38 Preview, 39–40 Performance).

## Version lane

| Concern | iOS 17+ (primary) | `[iOS16]` |
|---|---|---|
| Previews | `#Preview` macro; `PreviewProvider` is deprecated by the iOS 27 SDK | `#Preview` is a toolchain feature and works on any deployment target |
| Model in a view | `@State` / `@Bindable` / `@Environment(Type.self)` | `@StateObject` / `@ObservedObject` / `@EnvironmentObject` |
| `onChange` | Two-parameter / zero-parameter closure form | The one-parameter form is deprecated on 17+; fine on 16 |
| `ScrollView` position | `scrollPosition(id:)`, `scrollTargetBehavior` | Not available — do not recommend |
| Empty / failed states | `ContentUnavailableView` | A custom view with the same shape |
| `Observations` stream | iOS 26+ | n/a |

Do not flag an iOS 16 project for lacking an iOS 17 API; do not apply an iOS 17 recipe to it. `[UIKit]` codebases host SwiftUI through `UIHostingController` — [`uikit`](../uikit/SKILL.md).

## When to use

- Building a screen, a row, a reusable component or an empty / error state
- Loading data when a view appears; cancelling when it goes
- A view that re-renders too much or is slow
- Adding a `#Preview`

## When NOT to use

- Where the state lives; view-model decisions → [`architecture`](../architecture/SKILL.md)
- Colour, type, materials, Liquid Glass, iPad layout → [`styling`](../styling/SKILL.md)
- Routes, sheets, tabs → [`navigation`](../navigation/SKILL.md)
- Forms and text input → `mobile-ios-forms`
- VoiceOver detail → `mobile-ios-accessibility`; test ids → `mobile-ios-test-ids`
- Animation → `mobile-ios-animation`
- UIKit controllers → [`uikit`](../uikit/SKILL.md)
- RN / Compose screens → `mobile-react-native-ui-components`, `mobile-android-ui-components`

## Inputs needed

- The data the screen shows, and its states: loading, loaded, empty, failed, stale, offline
- Deployment target; SwiftUI vs UIKit host
- The closest existing view to copy the shape of

## Small views

- **A view is a `struct` with a `body` and nothing else heavy.** Rows, headers, sections and states are their own views; a `body` that scrolls past a screen is split.
- **Extract a subview, not a `@ViewBuilder` method on the parent**, once it has its own inputs — a separate struct gets its own identity and skips re-evaluation when its inputs are unchanged.
- **Inputs are values or bindings** — a row takes `Order`, not the whole list model. A view that only displays takes plain data and is previewable without a model.
- Modifiers apply **in order**; background after padding is a different result from before. Reusable modifier chains become a `ViewModifier` or a `ButtonStyle`, not a copy.
- Conditional content keeps view identity: prefer `.opacity`, `.disabled`, or an `if/else` of the same kind over wrapping a view in an `if` modifier extension that changes its identity.

```swift
struct OrderRow: View {
    let order: Order

    var body: some View {
        HStack {
            Label(order.title, systemImage: "shippingbox")
            Spacer()
            Text(order.total, format: .currency(code: order.currencyCode))
                .foregroundStyle(.secondary)
        }
    }
}
```

## `.task` — loads that cancel with the view

**`.task { }` is the only way a view starts async work.** SwiftUI cancels it when the view disappears or its identity changes; `Task { }` in `onAppear` is a leak ([`basics`](../basics/SKILL.md) B11).

```swift
.task { await model.load() }
.task(id: model.filter) { await model.reload() }
.refreshable { await model.load() }
```

- `.task(id:)` restarts — and cancels the previous run — when `id` changes; use it for search text and filters.
- A cancelled load is not a failure: `catch is CancellationError` returns without setting `failed`.
- **Returning to the foreground revalidates:** observe `@Environment(\.scenePhase)` and reload on `.active` — detail in `mobile-ios-error-handling`.
- Nothing in `body` or an `init` does I/O.

## Every data region has states

A region that depends on a response renders **loading, loaded, empty, failed**, and — where data is cached — **stale** and **offline**. The failure is scoped to that region: toolbar, search field and navigation title keep rendering.

```swift
struct OrdersContent: View {
    let state: LoadState<[Order]>
    let retry: () -> Void

    var body: some View {
        switch state {
        case .loading:
            ProgressView().accessibilityIdentifier("Orders.Loading")
        case .loaded(let orders) where orders.isEmpty:
            ContentUnavailableView("No orders yet", systemImage: "shippingbox")
        case .loaded(let orders):
            List(orders) { OrderRow(order: $0) }
                .accessibilityIdentifier("Orders.List")
        case .failed:
            ContentUnavailableView {
                Label("Couldn't load orders", systemImage: "exclamationmark.triangle")
            } actions: {
                Button("Try again", action: retry)
                    .accessibilityIdentifier("Orders.RetryButton")
            }
        }
    }
}
```

- **A drifted or undecodable response is `failed`, never empty.** The view never shows `error.localizedDescription` from a framework or server; it shows a message you wrote.
- **Every failure also raises the one persistent banner** inside the safe area, closed only by the user, and offline is told apart from a server error — the mechanics are `mobile-ios-error-handling`.
- A Dynamic-Type-safe `ProgressView` or a skeleton on first load; a spinner that blocks the screen is wrong when stale data can be shown.
- **Test ids** (`accessibilityIdentifier`, PascalCase, dot-separated, static) on every interactive element and container — never the label — are `mobile-ios-test-ids`' rule; samples carry them.

## Lists and long content

| Content | Use |
|---|---|
| Standard scrolling rows, swipe actions, selection, editing | **`List`** — cell reuse, system styling, `onDelete` / `swipeActions` |
| Custom layout, many rows | **`ScrollView` + `LazyVStack` / `LazyHStack`** (or `LazyVGrid`) |
| A handful of fixed items | `VStack` — a non-lazy stack of 100+ items is a defect |

- **`ForEach` / `List` take a stable domain id** (`Identifiable`, or `id: \.id`) — never an array index, never a value that changes.
- No `GeometryReader` for sizing a simple layout; reach for `Layout`, `containerRelativeFrame` or stack alignment first.
- Pagination triggers from the last row's `.onAppear` / `.task`, appends, and keeps the list identity.

## SF Symbols

**SF Symbols are the icon source** (`Image(systemName:)`, `Label`) — they scale with Dynamic Type, weight and Bold Text and adapt to Liquid Glass. A custom asset only for a brand mark with no symbol. Pick by `symbolRenderingMode` (`hierarchical`, `palette`) rather than a hand-tinted image; verify the symbol exists on the deployment target (the catalog lists the introduction version). Icon choices and names: `design/ui-ux-pro-max` icons.

## No work in `body`

`body` runs often and must be cheap and pure.

- No sorting, filtering, formatting-object creation, `DateFormatter()` / `NumberFormatter()` or JSON decoding — compute in the model, use `Text(value, format:)`, or cache outside `body`.
- No side effects, no state mutation in `body`, no `print`.
- Pass the smallest slice of an `@Observable` — a view re-renders only for the properties its `body` actually reads.
- Profile with Instruments' SwiftUI template before optimising; `Equatable` views and `drawingGroup` are fixes for a measured problem ([`performance`](../performance/SKILL.md)).

## Previews

Every reusable view ships `#Preview`s for its **states** — loading, loaded, empty, failed, and one at an accessibility Dynamic Type size — using static preview data, never production data or the network.

```swift
#Preview("Failed") { OrdersContent(state: .failed(PreviewError()), retry: {}) }
#Preview("Large type") {
    OrdersContent(state: .loaded(Order.previewList), retry: {})
        .dynamicTypeSize(.accessibility3)
}
```

`PreviewData` lives in the view's file or a `Preview Content` folder excluded from release.

## Rules

- Views are small structs; sub-regions are their own types.
- Async starts only in `.task`; cancellation is not failure.
- Every data region renders loading, loaded, empty, failed (plus stale / offline where cached), scoped to the region.
- `List` for standard rows, lazy stacks for custom, stable ids always.
- SF Symbols first; system controls and text styles — no imitation of Android or the web.
- No I/O, formatter construction or sorting in `body`.
- A `#Preview` per state; an accessibility size among them.
- Every interactive element and list carries a static `accessibilityIdentifier`.

## What NOT to do

- `Task { }` in `onAppear`, or a load in `init`.
- Index as id; `GeometryReader` as a default layout tool.
- Three booleans for loading / error / empty.
- A custom back button, tab bar or alert imitating a platform control.
- Use `AnyView` to erase types to dodge a compile error.
- Surface `error.localizedDescription` directly to the user.
- Hard-code a font size or colour — [`styling`](../styling/SKILL.md).

## Validation (exit gate)

- [ ] No view body exceeds one screen; each region is its own struct
- [ ] Every load is `.task` / `.task(id:)`; no `Task {}` in `onAppear`
- [ ] Each data region handles loading, loaded, empty, failed in its own subtree
- [ ] Lists use stable ids; long ones use `List` or a lazy stack
- [ ] `#Preview` per state exists; none uses live data
- [ ] Interactive elements and containers have `accessibilityIdentifier`

## Handoffs

- State ownership → [`architecture`](../architecture/SKILL.md)
- Colour, type, Liquid Glass → [`styling`](../styling/SKILL.md)
- Routes and sheets → [`navigation`](../navigation/SKILL.md)
- Forms → `mobile-ios-forms`; clients → `mobile-ios-networking`
- Banner, offline, resume → `mobile-ios-error-handling`
- Labels, traits, Dynamic Type sizes → `mobile-ios-accessibility`
- Test ids → `mobile-ios-test-ids`; render cost → `mobile-ios-performance`
