---
name: mobile-ios-uikit
description: Use when the iOS codebase is UIKit or mixes UIKit and SwiftUI — view controllers, Auto Layout, diffable data sources, UIKit Observation tracking, UIHostingController / UIHostingConfiguration / UIViewRepresentable seams both ways, and the UIScene lifecycle move (TN3187). Triggers "add a screen to this UIKit app", "embed SwiftUI", "wrap a UIKit view", "scene delegate". Do NOT use for new SwiftUI screens (`mobile-ios-ui-components`) or rewrites (`-migration`).
---

# iOS — UIKit

The lane for apps where UIKit **is** the codebase. **A UIKit codebase is not a defect.** This skill extends it in its own idiom, bridges to SwiftUI where a screen earns it, and never proposes a rewrite — screen-by-screen UIKit → SwiftUI is [`mobile-ios-migration`](../migration/SKILL.md)'s, and only on request. Design facts: `design/ui-ux-pro-max` `--stack swiftui` for platform conventions; a UIKit screen follows the same HIG.

## Version lane

| Concern | Primary | Supported / notes |
|---|---|---|
| Scene lifecycle | **Required by the iOS 27 SDK** (TN3187): `UIApplicationSceneManifest`, a `UIWindowSceneDelegate` — [`references/uiscene-migration.md`](references/uiscene-migration.md) | An app still on `UIApplicationDelegate.window` builds on the iOS 26 SDK; planning the move is the finding, not the build |
| Observation in UIKit | iOS 26: `updateProperties()` + automatic tracking of `@Observable` reads, on by default | iOS 18: automatic tracking with `UIObservationTrackingEnabled = YES`; below 18: `withObservationTracking` by hand, or the codebase's own binding (Combine, KVO) |
| SwiftUI in UIKit cells | `UIHostingConfiguration` (iOS 16+) | Below 16: `UIHostingController` as a child |
| Layout | Auto Layout / layout anchors; compositional layout for collections | Storyboards and XIBs are present in many codebases — extend them, do not strip them |
| Lists | `UICollectionViewDiffableDataSource` + `CellRegistration` | `UITableViewDiffableDataSource`; classic data sources are present in older code — match them in files you do not own |
| Deployment target | Detected, never raised | Below iOS 16 is the UIKit lane, flagged (§ project-setup) |

Detect first: storyboards, `AppDelegate`/`SceneDelegate`, Objective-C, third-party layout or binding libraries, the existing navigation owner (coordinator, router, plain `UINavigationController`). **Match what is there.**

## When to use

- Adding or changing a screen in a UIKit app
- Embedding a SwiftUI view in UIKit, or a UIKit view in SwiftUI
- A collection view or table view with diffable data
- "Migrate to scenes", a missing `SceneDelegate`, a launch crash on the iOS 27 SDK
- Auto Layout breakage, a screen that does not rotate or resize on iPad

## When NOT to use

- A new SwiftUI screen in an app that is mostly SwiftUI → [`ui-components`](../ui-components/SKILL.md)
- Rewriting UIKit to SwiftUI, Objective-C → Swift, storyboard removal → [`migration`](../migration/SKILL.md)
- State ownership of `@Observable` models → [`architecture`](../architecture/SKILL.md)
- Routes and universal links → [`navigation`](../navigation/SKILL.md), `mobile-ios-notifications-and-links`
- Colour, type, Liquid Glass → [`styling`](../styling/SKILL.md)
- Another stack → `mobile-react-native-native-modules`, `mobile-android-views-interop`

## View controllers — small, owned, cancelled

```swift
final class OrdersViewController: UIViewController {
    private let client: APIClient
    private var loadTask: Task<Void, Never>?
    private var dataSource: UICollectionViewDiffableDataSource<Section, Order.ID>!

    init(client: APIClient) {
        self.client = client
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }

    override func viewDidLoad() {
        super.viewDidLoad()
        configureCollection()
        collectionView.accessibilityIdentifier = "Orders.List"
    }

    override func viewIsAppearing(_ animated: Bool) {
        super.viewIsAppearing(animated)
        reload()
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        loadTask?.cancel()
    }

    private func reload() {
        loadTask?.cancel()
        loadTask = Task { [weak self] in
            guard let self else { return }
            do { apply(try await client.send(.orders)) }
            catch is CancellationError { return }
            catch { showFailure(error) }
        }
    }
}
```

- **Initializer injection**, even when a storyboard instantiates the controller (`@IBSegueAction` / `instantiateViewController(identifier:creator:)` pass the dependencies); no singleton reach-ins and no property-injected optionals set later.
- **A `Task` the controller starts is cancelled when the screen goes** — store the handle, cancel in `viewDidDisappear` / `deinit`. Loading in `viewIsAppearing` (iOS 13+, with correct geometry) beats `viewWillAppear`.
- **The main thread never blocks**: no `Data(contentsOf:)`, Keychain loops, Core Data fetches on `viewContext` of thousands of rows, or image decoding in `cellForItemAt`.
- `[weak self]` in a stored closure or long-lived `Task`; **no retain cycle through a delegate** — delegate properties are `weak`.
- Three data states plus stale and offline — render them in the region (`UIContentUnavailableConfiguration` on iOS 17+ for empty and failed; a status view above that) while the search bar and header keep working; `mobile-ios-error-handling` owns the banner.
- Every interactive view and every list container sets `accessibilityIdentifier` — static PascalCase dot-separated ([`mobile-ios-test-ids`](../test-ids/SKILL.md)).

## Auto Layout

- **Constraints are activated in `viewDidLoad` / `init`, once**; `translatesAutoresizingMaskIntoConstraints = false` on every programmatic view; never `frame` arithmetic for a layout that must adapt.
- Constrain to `safeAreaLayoutGuide` for edges the system draws over and to `keyboardLayoutGuide` for keyboard avoidance (iOS 15+) instead of keyboard notifications.
- Text uses `UIFont.preferredFont(forTextStyle:)` / `UIFontMetrics` with `adjustsFontForContentSizeCategory = true`; `numberOfLines = 0` where text may grow; a constant height on a label is a Dynamic Type bug.
- Touch targets ≥ 44 pt; a smaller visual with a larger hit area is a `point(inside:with:)` override or `UIButton.Configuration` padding, not a tiny control.
- iPad windows resize freely: lay out from `view.bounds` / trait collection, never `UIScreen.main.bounds` (deprecated) or an assumed orientation.

## Collections — diffable, registered, identifier-based

```swift
extension OrdersViewController {
    enum Section { case main }

    func configureCollection() {
        let registration = UICollectionView.CellRegistration<UICollectionViewListCell, Order> { cell, _, order in
            cell.contentConfiguration = UIHostingConfiguration { OrderRow(order: order) }
            cell.accessibilityIdentifier = "Orders.Row"
        }
        dataSource = UICollectionViewDiffableDataSource(collectionView: collectionView) { [weak self] view, indexPath, id in
            guard let order = self?.orders[id] else { return nil }
            return view.dequeueConfiguredReusableCell(using: registration, for: indexPath, item: order)
        }
    }

    func apply(_ orders: [Order]) {
        self.orders = Dictionary(uniqueKeysWithValues: orders.map { ($0.id, $0) })
        var snapshot = NSDiffableDataSourceSnapshot<Section, Order.ID>()
        snapshot.appendSections([.main])
        snapshot.appendItems(orders.map(\.id))
        dataSource.apply(snapshot, animatingDifferences: true)
    }
}
```

- **Snapshots carry stable domain ids, not model values** — items hashed by content make every edit a delete + insert; re-configure changed rows with `reconfigureItems`.
- `apply` is called on the main actor; a large diff may use `applySnapshotUsingReloadData` for the first load.
- Compositional layout (`UICollectionViewCompositionalLayout`, `UICollectionLayoutListConfiguration`) replaces `UICollectionViewFlowLayout` for new screens; an existing flow layout stays.
- Prefetching (`UICollectionViewDataSourcePrefetching`) cancels in `cancelPrefetchingForItemsAt`.

## UIKit Observation tracking

On iOS 26 UIKit tracks `@Observable` reads automatically inside `updateProperties()` (and `layoutSubviews`, `viewWillLayoutSubviews`, `draw`, …) and re-runs that method when a read property changes. On iOS 18, set `UIObservationTrackingEnabled` to `YES` in `Info.plist` to get the same for the existing methods.

```swift
final class CartBadgeViewController: UIViewController {
    private let cart: Cart
    private let badge = UILabel()

    init(cart: Cart) {
        self.cart = cart
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }

    override func updateProperties() {
        super.updateProperties()
        badge.text = cart.lines.count.formatted()
        badge.isHidden = cart.lines.isEmpty
    }
}
```

Read **only what the UI shows** inside the tracked method — every property read becomes a dependency. Below iOS 18 (or where a codebase's convention is Combine / KVO / closures), keep that convention in code you extend; `withObservationTracking` with a re-arming `onChange` is the by-hand version. Do not introduce `@Observable` models into a codebase with no Observation consumers as a drive-by.

## The seams — SwiftUI in UIKit

| Need | Use |
|---|---|
| A whole SwiftUI screen pushed from UIKit | `UIHostingController(rootView:)` added through `navigationController?.pushViewController` |
| A SwiftUI view inside a layout | `addChild(host)`, add `host.view`, constrain, `host.didMove(toParent: self)` |
| A SwiftUI cell | `UIHostingConfiguration { … }` (iOS 16+) as `contentConfiguration` |
| Sizing | `host.sizingOptions = [.intrinsicContentSize]` (iOS 16+) for a self-sizing child |
| Environment into SwiftUI | `rootView: Screen().environment(model)` — built by the owning controller, initializer-injected |

```swift
func showOrder(_ order: Order) {
    let host = UIHostingController(rootView: OrderDetailView(order: order, client: client))
    host.title = order.number
    navigationController?.pushViewController(host, animated: true)
}
```

- **UIKit keeps owning navigation** in a UIKit-owned stack: a hosted SwiftUI screen does not own a second `NavigationStack` inside a `UINavigationController` push (two bars). Present SwiftUI sheets from the SwiftUI side only when the screen is wholly SwiftUI.
- The hosting controller is retained by its parent; do not hold the `rootView` struct in a property to "update" it — update the `@Observable` model it reads.
- **Safe area and keyboard**: a `UIHostingController` participates in both; `safeAreaRegions` / `.ignoresSafeArea` are decisions made in SwiftUI, not worked around with constraints.
- Previews: `#Preview { OrdersViewController(client: .preview) }` works for UIKit controllers on Xcode 15+.

## The seams — UIKit in SwiftUI

Wrap UIKit with `UIViewRepresentable` / `UIViewControllerRepresentable` only where SwiftUI has no equivalent (prefer `PhotosPicker`, `fileImporter`, `Link`, `Map` — [`device-features`](../device-features/SKILL.md)). **`makeUIView` builds once; `updateUIView` applies state and is idempotent**; delegates live in the `Coordinator`; cleanup is in `dismantleUIView`. The full wrapper and its rules are in [`references/interop-seams.md`](references/interop-seams.md).

## The scene lifecycle

The iOS 27 SDK makes the UIScene lifecycle mandatory; an app that builds against it without a scene manifest does not launch. The move is mechanical and does not change screens: add the scene manifest, a `SceneDelegate` that owns the window, move window and URL / activity handling out of the app delegate. The step-by-step, including `application(_:configurationForConnecting:options:)`, state restoration and multi-window, is in [`references/uiscene-migration.md`](references/uiscene-migration.md). **Do the move because the SDK requires it** — not as a vehicle for restructuring navigation.

## Rules

- Extend UIKit in UIKit; **never propose or start a rewrite** — [`migration`](../migration/SKILL.md) does that, on request.
- Initializer injection into controllers; weak delegates; cancelled `Task`s; no blocking the main thread.
- Diffable data sources with stable ids; compositional layout for new collections.
- Auto Layout with safe-area and keyboard guides; Dynamic Type via `UIFontMetrics`; ≥ 44 pt targets.
- `UIHostingConfiguration` for SwiftUI cells; a hosting controller added as a proper child.
- `makeUIView` once, `updateUIView` idempotent, delegates in the `Coordinator`, cleanup in `dismantleUIView`.
- One owner of navigation per stack; `accessibilityIdentifier` on every interactive view and container.
- A scene delegate owns the window on the iOS 27 SDK.

## What NOT to do

- No "this should be SwiftUI" finding; no storyboard-removal or Objective-C-bridging side quests.
- No `UIScreen.main.bounds`, no `frame` math for adaptive layout, no `UIWebView`.
- No `DispatchQueue.main.asyncAfter` to fix layout timing; no `layoutIfNeeded()` sprinkled to hide an ordering bug.
- No second navigation stack inside a pushed hosting controller.
- No SwiftUI state mutated from `updateUIView`; no `UIViewRepresentable` for something `TextField`, `Map` or `PhotosPicker` does.
- No `@Observable` introduced into a Combine / KVO codebase as a drive-by.
- No retain cycle through a stored closure, delegate or `Timer`.

## Generation steps

1. Detect UIKit vs SwiftUI share, storyboards, navigation owner, `Observation` use, target and SDK; read two controllers in the area.
2. Write the controller (initializer-injected, cancelled tasks), its layout and its diffable data source in the project's style.
3. Embed SwiftUI through `UIHostingConfiguration` / `UIHostingController` only where a screen or cell earns it.
4. Wrap UIKit for SwiftUI with `UIViewRepresentable` + `Coordinator` only where SwiftUI has no equivalent.
5. If the app has no scene manifest: apply [`references/uiscene-migration.md`](references/uiscene-migration.md).
6. Add test ids; add dev-side tests for presenters / models, not for view-controller internals.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Build with warnings as errors; the project's formatter and linter pass.
- Run on an iPad in a resized window and at the largest accessibility text size: no clipped or overlapped content.
- Leaving a screen mid-load cancels the request; Instruments (Leaks, Memory Graph) shows the controller deallocated after pop.
- A scene-based app launches, restores its state and handles a universal link in cold and warm start.
- Dev-side tests: logic extracted to models and tested with Swift Testing; view-controller journeys are `qa-mobile-<stack>`'s (peer).

## Handoffs

- Rewrites, Objective-C, storyboard removal → [`migration`](../migration/SKILL.md)
- Models, injection → [`architecture`](../architecture/SKILL.md) · views → [`ui-components`](../ui-components/SKILL.md)
- Links and push routing → [`navigation`](../navigation/SKILL.md), `mobile-ios-notifications-and-links`
- Test ids → [`mobile-ios-test-ids`](../test-ids/SKILL.md) · accessibility → `mobile-ios-accessibility`
- Pickers, camera, location → [`device-features`](../device-features/SKILL.md)
