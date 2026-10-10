---
name: mobile-android-navigation
description: Use when adding screens, tabs or deep links in Compose — Navigation 3 (NavDisplay, back stack you own, typed NavKey routes) for new apps; Navigation Compose 2.10 type-safe routes for existing ones; adaptive scenes, App Links mapped to a route, predictive back. Triggers "add a screen", "navigate after save", "deep link into a detail". Do NOT use for assetlinks.json and push links (`mobile-android-notifications-and-links`) or ViewModel state (`-architecture`).
---

# Android — Navigation

**Navigation 3 for new apps**: you own the back stack as a list of typed keys, `NavDisplay` renders it, and entries scope their own ViewModels. **Navigation Compose 2.10 stays the lane for existing apps** — Google's own migration page still names it, which is the existing-app lane, not a contradiction. One pattern per app; never both in one graph.

## Version lane

| Concern | Navigation 3 1.2 (new apps) | Navigation Compose 2.10 `[NavCompose]` (existing) |
|---|---|---|
| Back stack | **A list you own** — `rememberNavBackStack(Home)`; navigate = `add` / `removeLastOrNull` | `NavController` owns it; `navigate(route)` / `popBackStack()` |
| Routes | `@Serializable` types implementing `NavKey` | `@Serializable` objects / data classes (type-safe), no string routes |
| Host | `NavDisplay(backStack, entryProvider, …)` | `NavHost(navController, startDestination)` + `composable<Route> { }` |
| Per-screen ViewModel | `rememberViewModelStoreNavEntryDecorator()` + `rememberSaveableStateHolderNavEntryDecorator()` | Built in (`hiltViewModel()` / `viewModel()` per destination) |
| Adaptive (list-detail) | Scene strategies (`ListDetailSceneStrategy` in `material3-adaptive-navigation3`) | Manual, or the adaptive scaffolds with a state-driven pane |
| Deep links | Parse the URI to a key list yourself, validate, `backStack` = result | `navDeepLink<Route>(basePath = …)` |
| Predictive back | `NavDisplay` animates it; target 36 on | `NavHost` animates it; `enableOnBackInvokedCallback` |
| Views / Fragments `[Views]` | n/a — see [`views-interop`](../views-interop/SKILL.md) | Fragment Navigation component |

Check the exact artifacts and versions (`androidx.navigation3:navigation3-runtime` / `-ui`, `androidx.lifecycle:lifecycle-viewmodel-navigation3`) against developer.android.com/jetpack/androidx/releases/navigation3 when writing. **An existing Navigation Compose app is not flagged for lacking Navigation 3**; migration is [`mobile-android-migration`](../migration/SKILL.md)'s and is incremental per graph.

## When to use

- Adding a screen, a detail, a dialog or a tab; navigating from code after an action
- Mapping an App Link / intent URI to a screen
- Two-pane layouts on tablets and foldables; handling back

## When NOT to use

- `assetlinks.json`, link verification, push payload routing, `PendingIntent` → `mobile-android-notifications-and-links`
- Where a screen's state lives → [`architecture`](../architecture/SKILL.md)
- Composable structure → [`ui-components`](../ui-components/SKILL.md); window size classes → [`styling`](../styling/SKILL.md)
- Transition and back animations → [`animation`](../animation/SKILL.md)
- XML nav graphs and Fragments → [`views-interop`](../views-interop/SKILL.md)
- iOS / RN → `mobile-ios-navigation`, `mobile-react-native-navigation`

## Inputs needed

- New app or existing (which navigation library is in the build file)
- Top-level areas (tabs), whether tablets / foldables are in scope, deep-link hosts

## Navigation 3 — keys, back stack, display

```kotlin
@Serializable data object OrdersList : NavKey
@Serializable data class OrderDetail(val id: String) : NavKey

@Composable
fun AppNavigation(modifier: Modifier = Modifier) {
    val backStack = rememberNavBackStack(OrdersList)
    NavDisplay(
        backStack = backStack,
        onBack = { backStack.removeLastOrNull() },
        entryDecorators = listOf(
            rememberSaveableStateHolderNavEntryDecorator(),
            rememberViewModelStoreNavEntryDecorator(),
        ),
        entryProvider = entryProvider {
            entry<OrdersList> {
                OrdersScreen(onOpenOrder = { backStack.add(OrderDetail(it.value)) })
            }
            entry<OrderDetail> { key ->
                OrderDetailScreen(orderId = key.id, onDone = { backStack.removeLastOrNull() })
            }
        },
        modifier = modifier,
    )
}
```

- **Keys are small `@Serializable` types carrying ids, never models or lambdas** — `rememberNavBackStack` saves them across process death. A key holding an object that cannot serialise crashes on restore.
- **Navigating is mutating the list**: `add(key)`, `removeLastOrNull()`, `removeAll { }` plus `add` to reset to a root. A single `Navigator` holder (`class Navigator(val backStack: NavBackStack)`) with `navigate` / `back` is acceptable once screens would otherwise receive the list; it is a holder, not a framework.
- **The screen composable receives callbacks (`onOpenOrder`, `onDone`), never the back stack** — so previews and tests need no navigation. Entries pass the key's id into the screen; the screen's ViewModel loads from it ([`architecture`](../architecture/SKILL.md)).
- **Entry decorators are not optional**: the state-holder decorator keeps `rememberSaveable` per entry; the ViewModel-store decorator scopes ViewModels to the entry and clears them on pop. Without them a ViewModel is the activity's.
- **A destination loads its own data from its key.** It never relies on state only the previous screen populated — a restored process lands directly on it.
- **Result back to the caller**: a result type through the Navigation 3 result pattern (docs: Return results), or a shared repository / state; never a global.
- **Dialogs and bottom sheets** are entries with scene metadata (`DialogSceneStrategy`, `BottomSheetSceneStrategy`), or a composable `AlertDialog` / `ModalBottomSheet` driven by screen state when it is not a route.
- **Modularity:** each feature exposes `fun EntryProviderScope<NavKey>.ordersEntries(navigator: Navigator)`; the app module composes them. Keys other features need to open live where the dependency direction allows ([`architecture`](../architecture/SKILL.md)).

## Tabs and top-level areas

- Top-level destinations are **`NavigationSuiteScaffold`** (bottom bar on compact, rail on medium, drawer on expanded — [`styling`](../styling/SKILL.md)) or `NavigationBar` + `NavigationRail` by window class; **never a hand-rolled tab bar**.
- **Each top-level area keeps its own back stack** (`Map<TopLevelKey, NavBackStack>`; the displayed list is the selected area's); switching tabs preserves each stack, and back from a tab's root returns to the start destination, then exits. Selection is an enum / sealed type held in the root state, not a string.
- Maximum five bottom destinations; badges via `BadgedBox` with a label for TalkBack.

## Adaptive navigation — scenes

On expanded windows a list and its detail show together; the same keys, no new routes. With Navigation 3 pass a `sceneStrategy` (list-detail / supporting-pane from `material3-adaptive-navigation3`) built on the window's `WindowAdaptiveInfo`, and mark entries with the strategy's metadata (`ListDetailSceneStrategy.listPane()` / `.detailPane()`). The back stack stays one list; the scene decides how many entries render. Size classes are [`styling`](../styling/SKILL.md). **Existing Navigation Compose `[NavCompose]`:** a state-driven `ListDetailPaneScaffold` over the same typed routes.

## Back — predictive, always handled

- **Target 36 turns predictive back on**; `android:enableOnBackInvokedCallback="true"` in the manifest ([`project-setup`](../project-setup/SKILL.md)). `NavDisplay` / `NavHost` already animate the system gesture.
- **Intercepting back**: `BackHandler(enabled = hasUnsavedChanges) { showDiscardDialog() }` for confirm-discard; `PredictiveBackHandler` only when the screen owns a custom back animation ([`animation`](../animation/SKILL.md)). Enabled **only while the condition holds** — a permanently enabled handler swallows the gesture.
- **Never override `onBackPressed()`, handle `KEYCODE_BACK`, or build a custom back arrow that does something other than pop** (`navigationIcon` calls the same `onBack`).
- A confirm-discard dialog has Keep editing / Discard; a back press never silently loses typed input.

## Deep links and App Links

A link is **untrusted input** (CLAUDE.md § Mobile code rules): validated before it routes.

```kotlin
fun parseLink(uri: Uri): List<NavKey>? {
    if (uri.host != "app.example.com") return null
    val segments = uri.pathSegments
    return when {
        segments.size == 2 && segments[0] == "orders" && segments[1].matches(OrderId.PATTERN) ->
            listOf(OrdersList, OrderDetail(segments[1]))
        else -> null
    }
}
```

- **One pure function maps a URI to keys** (a synthetic back stack, so back from the detail goes to the list); unknown shape → `null` → the start destination, no crash, nothing opened. Host allow-list; ids match a pattern; no `openURL` of a link parameter; no route chosen from an `extra` string without validation.
- **`<intent-filter android:autoVerify="true">` with `https` and a specific host + `pathPrefix`**, never `pathPattern=".*"`; verification and `assetlinks.json` are [`notifications-and-links`](../notifications-and-links/SKILL.md)'s. A custom scheme carries **no secret, code or token**.
- **Handle both entry points**: `intent` in `onCreate` and `onNewIntent` (`singleTop` activity) → the same parser → replace the stack. **Navigation Compose:** `composable<OrderDetail>(deepLinks = listOf(navDeepLink<OrderDetail>(basePath = "https://app.example.com/orders")))`.
- A sign-in gate on a route is **client UX, not authorisation** — the server enforces; auth-required links wait for sign-in, then resume the stored key list.

## Navigation Compose 2.10 — the existing-app lane

```kotlin
@Serializable object OrdersList
@Serializable data class OrderDetail(val id: String)

NavHost(navController, startDestination = OrdersList) {
    composable<OrdersList> { OrdersScreen(onOpenOrder = { navController.navigate(OrderDetail(it.value)) }) }
    composable<OrderDetail> { entry -> OrderDetailScreen(orderId = entry.toRoute<OrderDetail>().id) }
}
```

**Typed routes, never `"orders/{id}"` strings.** A `NavController` never leaves the nav-host composable — screens get callbacks. Tabs: `navigate(route) { popUpTo(start) { saveState = true }; launchSingleTop = true; restoreState = true }`. Nested graphs with `navigation<Graph>(startDestination = …)`. Do not add Navigation 3 to a graph piecemeal; move per [`migration`](../migration/SKILL.md).

## Rules

- New apps: Navigation 3; existing apps: Navigation Compose 2.10 with typed routes; never both mixed in one graph.
- Keys are `@Serializable`, id-carrying, small; the back stack is `rememberNavBackStack` (N3) / typed routes (2.10).
- Entry decorators on `NavDisplay`; ViewModels scoped to the entry.
- Screens take callbacks, not the back stack or `NavController`.
- A destination loads from its key; a restored process works.
- Top-level areas are a navigation suite with one back stack each — no hand-built tab bar.
- Back is predictive; `BackHandler` enabled only while it has a job; no `onBackPressed()` override.
- Links go through one validated parse function; bad input is ignored; no secret in a scheme.

## What NOT to do

- Navigate with string routes, or put a model object or lambda in a key.
- Pass `NavBackStack` / `NavController` into a leaf composable or a ViewModel.
- Navigate by emitting a ViewModel event — the state-based pattern is in [`architecture`](../architecture/SKILL.md).
- Leave `BackHandler(enabled = true)` permanently.
- Claim `pathPattern=".*"` or trust `intent.data` unchecked.
- Rewrite a working Navigation Compose graph to Navigation 3 as a side effect.
- Use `LaunchedEffect(Unit) { navigate(...) }` to drive a flow.

## Validation (exit gate)

- [ ] One navigation library in the build file; routes / keys are serializable types
- [ ] `NavDisplay` has both entry decorators; ViewModels clear on pop
- [ ] Kill the process on a detail screen, return: it restores and loads from its key
- [ ] Deep link `adb shell am start -a android.intent.action.VIEW -d <uri>` opens the right stack; a malformed one does not crash
- [ ] Back gesture previews and works on target 36; no `onBackPressed` override

## Handoffs

- Link verification, push → `mobile-android-notifications-and-links`
- Screen state, entry ViewModels → [`architecture`](../architecture/SKILL.md)
- Window classes, rails → [`styling`](../styling/SKILL.md)
- Back and transition animation → [`animation`](../animation/SKILL.md)
- Navigation Compose → Navigation 3 → [`migration`](../migration/SKILL.md)
- Test ids on bars and rows → [`test-ids`](../test-ids/SKILL.md)
