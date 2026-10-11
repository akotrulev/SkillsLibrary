---
name: navigation
description: Use when adding routes or containers in SwiftUI — NavigationStack(path:) with typed routes, NavigationSplitView, sheets and full-screen covers, TabView with the Tab API, and onOpenURL mapped to a route. Triggers "add a screen", "navigate programmatically", "deep link into a detail", "tabs on iPad". Do NOT use for push and universal-link setup (`mobile-ios:push-and-deep-links`), state ownership (`-architecture`) or view structure (`-ui-components`).
---

# iOS — Navigation

SwiftUI navigation is **data-driven**: the path is a value, destinations are registered by type, and a link is a value pushed onto the path. House rules: `NavigationStack(path:)` with typed routes, `NavigationSplitView` for sidebar layouts, `TabView` for top-level areas, sheets for self-contained tasks, and one function that turns a URL into a route. Design facts: `design/ui-ux-pro-max` swiftui rows 21–23 and `app-interface.csv`.

## Version lane

| Concern | iOS 17+ (primary) | `[iOS16]` |
|---|---|---|
| Stack | `NavigationStack(path:)` (iOS 16+) | Same — `NavigationStack` is the iOS 16 floor |
| `NavigationView`, `NavigationLink(destination:)` | Deprecated — flag in new code | Below 16: UIKit lane only, flagged |
| Tabs | **`Tab` API** (`TabView { Tab("Orders", systemImage: "shippingbox") { … } }`, iOS 18+) with Liquid Glass tab bar on the iOS 27 SDK | `TabView { … .tabItem { Label(…) } }` — correct below iOS 18 |
| Programmatic path state | `NavigationPath` or a typed array | Same |
| Split view | `NavigationSplitView` | Same |
| Sheets | `.sheet(item:)`, `.presentationDetents` | Same (iOS 16+) |
| `[UIKit]` | `UINavigationController`, `UITabBarController`, `UISplitViewController` | [`uikit`](../uikit/SKILL.md) |

Use the `Tab` API where the deployment target is iOS 18+; `.tabItem` remains right for 17 and 16. Liquid Glass tab bars, minimise-on-scroll (`tabBarMinimizeBehavior`) and bottom accessories are system chrome — confirm availability in the SDK docs, and never rebuild them by hand ([`styling`](../styling/SKILL.md)).

## When to use

- Adding a screen, a detail, a modal or a tab
- Navigating from code (after a save, from a notification)
- Mapping a URL to a screen
- Laying out iPad / large-screen navigation

## When NOT to use

- APNs, universal-link entitlements and AASA, scheme validation → `mobile-ios:push-and-deep-links`
- Model ownership, the composition root → [`architecture`](../architecture/SKILL.md)
- View internals → [`ui-components`](../ui-components/SKILL.md)
- Not-found and failure screens → `mobile-ios:error-handling`
- RN / Compose routing → `mobile-react-native:navigation`, `mobile-android:navigation`

## Inputs needed

- The screen graph: tabs, stacks, modals
- Which links reach the app (URLs, notifications) and which screens they open
- Deployment target; iPhone only or iPad

## Typed routes and `NavigationStack(path:)`

A route is a `Hashable` enum or struct carrying **ids, not models** — a path must survive state restoration and a link must be constructible from a URL.

```swift
enum OrdersRoute: Hashable {
    case detail(Order.ID)
    case receipt(Order.ID)
}

struct OrdersTab: View {
    @State private var path: [OrdersRoute] = []
    let client: OrdersClient

    var body: some View {
        NavigationStack(path: $path) {
            OrdersList(client: client)
                .navigationTitle("Orders")
                .navigationDestination(for: OrdersRoute.self) { route in
                    switch route {
                    case .detail(let id): OrderDetail(id: id, client: client)
                    case .receipt(let id): ReceiptView(id: id, client: client)
                    }
                }
        }
    }
}
```

- **In-app navigation is `NavigationLink(value:)`** — a real link — never a `Button` that mutates the path to navigate (the button form is for logic results, e.g. after a save: `path.append(.detail(id))`).
- **`navigationDestination(for:)` is declared once per route type, on the stack's root content**, not inside lazy rows (a destination in a `List` row may not be registered). Never `NavigationLink(destination: View())`: it builds the destination eagerly and cannot be restored.
- **One path per stack, owned with `@State` by the view that owns the stack**, or a small `@Observable` router **only when several distant views must push** (a second real need). Do not build a coordinator layer; the path is the coordinator.
- **A heterogeneous stack** uses `NavigationPath` with several `navigationDestination(for:)` registrations; a single-route-type stack uses a typed array (inspectable, testable).
- `@Environment(\.dismiss)` closes the current screen; never `presentationMode`. Pop to root is `path.removeAll()`.
- **The destination loads its own data from the id**, in `.task` ([`ui-components`](../ui-components/SKILL.md)); it does not rely on a model its predecessor happened to hold, so a deep link and a tap behave identically.
- Navigation titles use `navigationTitle` + `navigationBarTitleDisplayMode`; toolbars use `.toolbar` with `ToolbarItem` / `ToolbarSpacer` — system chrome, no custom header views.

## Tabs

```swift
struct RootView: View {
    @State private var selection: AppTab = .orders

    var body: some View {
        TabView(selection: $selection) {
            Tab("Orders", systemImage: "shippingbox", value: .orders) {
                OrdersTab(client: ordersClient)
            }
            .accessibilityIdentifier("Root.OrdersTab")
            Tab("Account", systemImage: "person.crop.circle", value: .account) {
                AccountTab()
            }
            .accessibilityIdentifier("Root.AccountTab")
        }
    }
}

enum AppTab: Hashable { case orders, account }
```

- **Each tab owns its own `NavigationStack`** and path, so switching tabs preserves each stack. Never one stack around a `TabView`.
- Top-level areas only, ≤ 5; more goes in `More` or a sidebar. Tab labels are nouns with an SF Symbol; badges via `.badge(_:)`.
- Selection is an enum — a URL can set it.
- **On iPad, `.tabViewStyle(.sidebarAdaptable)`** turns the tab bar into a sidebar from the same `Tab`s; do not maintain two navigation trees.

## Split view — iPad and large screens

`NavigationSplitView` (sidebar / content / detail) collapses to a stack on compact width by itself. Selection is a bound value; the detail column is driven by it.

```swift
NavigationSplitView {
    List(orders, selection: $selectedID) { OrderRow(order: $0) }
        .accessibilityIdentifier("Orders.List")
} detail: {
    if let selectedID {
        OrderDetail(id: selectedID, client: client)
    } else {
        ContentUnavailableView("Select an order", systemImage: "shippingbox")
    }
}
```

Never branch on `userInterfaceIdiom`; the container adapts to the window width ([`styling`](../styling/SKILL.md)). A detail column may host its own `NavigationStack` for deeper steps.

## Sheets and full-screen covers

- **A sheet is for a self-contained task or a peer view** (compose, filters, a picker) that has its own completion. Present with **`.sheet(item:)`** bound to optional `Identifiable` state — not a Bool plus a separate selection.
- **`.fullScreenCover`** only for immersive flows (a camera, onboarding); everything else is a sheet or a push.
- **Every sheet has a close affordance** (`Done` / `Cancel` in the toolbar) and the swipe-to-dismiss behaviour is kept or deliberately disabled with `interactiveDismissDisabled` only for unsaved input, with a confirmation.
- A sheet that navigates has **its own `NavigationStack`**. Sizes via `.presentationDetents([.medium, .large])` + `.presentationDragIndicator`.
- Sheets and alerts that must reflect a route are fed by the same path/state as links, so a deep link can open them.

## URL → route (`onOpenURL`)

One function maps an incoming URL to a route; **a URL is untrusted input** — parse it, validate every component, and ignore what does not match. Setup of universal links (entitlements, AASA) and URL schemes is [`notifications-and-links`](../notifications-and-links/SKILL.md); this skill owns where the URL lands.

```swift
enum DeepLink: Equatable {
    case order(Order.ID)

    init?(url: URL) {
        let parts = url.pathComponents.filter { $0 != "/" }
        guard parts.count == 2, parts[0] == "orders", let id = Order.ID(parts[1]) else { return nil }
        self = .order(id)
    }
}

.onOpenURL { url in
    guard let link = DeepLink(url: url) else { return }
    selection = .orders
    ordersPath = [.detail(link.orderID)]
}
```

- Parsing is a pure, unit-tested function on `URL`; unmatched, malformed or oversized input is **ignored, never crashes**, and the app opens normally.
- Setting `selection` and the tab's path together reaches the screen from cold start and from running.
- A link to a screen behind sign-in is held and replayed after authentication, not dropped; an auth gate is **client UX, never authorisation** — the server enforces it.
- Not found (a valid link to a missing id) is the destination's failed state, not a navigation failure.

## State restoration

Paths of `Codable` routes survive relaunch via `@SceneStorage` (store the encoded `[Route]`) — restore only what is cheap and valid; a stale id lands on the destination's failed state. Do not persist a path holding anything sensitive.

## Rules

- `NavigationStack(path:)` with typed `Hashable` routes carrying ids; `navigationDestination(for:)` at the stack root.
- In-app navigation is `NavigationLink(value:)`; code-driven navigation appends to the path.
- Each tab owns its stack; selection is an enum.
- `NavigationSplitView` for sidebar layouts; no idiom branching.
- `.sheet(item:)`, a close affordance, its own stack when it navigates.
- One pure, validated URL → route function; untrusted input ignored safely.
- Guards are client UX; the server authorises.
- No `NavigationView`, no `NavigationLink(destination:)`, no `presentationMode`.

## What NOT to do

- Pass a model object through a route, or rely on the previous screen's loaded data.
- Wrap a `TabView` in one `NavigationStack`, or share a path across tabs.
- Build a custom tab bar, navigation bar or back button.
- Register `navigationDestination` inside a `List` row or a lazily-created view.
- Add a router / coordinator class for one stack.
- Trust a URL's components or open a sheet for an unvalidated id.

## Validation (exit gate)

- [ ] Every route is a `Hashable` value of ids; each type has one `navigationDestination(for:)` at the stack root
- [ ] Tabs each own a `NavigationStack`; selection is an enum
- [ ] A URL maps to a route through one tested function; bad URLs are ignored
- [ ] Every sheet can be dismissed; `.sheet(item:)` used
- [ ] Links and tabs carry `accessibilityIdentifier`
- [ ] No `NavigationView` / `NavigationLink(destination:)` remains in new code

## Handoffs

- Push, universal links, schemes → `mobile-ios:push-and-deep-links`
- Models, injection → [`architecture`](../architecture/SKILL.md)
- Views, `.task` loads → [`ui-components`](../ui-components/SKILL.md)
- Tab bar and split-view look, iPad → [`styling`](../styling/SKILL.md)
- Not-found, failed states → `mobile-ios:error-handling`
- Test ids → `mobile-ios:test-ids`
- `NavigationView` → `NavigationStack` → `mobile-ios:migration`
