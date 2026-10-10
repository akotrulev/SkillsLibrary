---
name: mobile-android-ui-components
description: Use when writing Jetpack Compose UI — stateless composables with hoisted state, modifier as the first optional parameter, previews, lazy-list key and contentType, stability, side-effect APIs, Material 3 components, loading / loaded / failed regions. Triggers "build this screen", "why does it recompose", "LaunchedEffect keys". Do NOT use for ViewModels (`mobile-android-architecture`), theme tokens (`-styling`), routes (`-navigation`) or XML Views (`-views-interop`).
---

# Android — UI Components (Compose)

How composables are written here: **stateless by default, state hoisted, `modifier` first among the optional parameters**, lazy lists with stable keys, side effects through the right API, Material 3 components over hand-drawn ones, and every data region rendering loading / loaded / failed (plus stale and offline). It is the Compose half of CLAUDE.md § Mobile code rules; audit rows are section D of `mobile-android-standards-audit`.

## Version lane

| Concern | Compose BOM 2026.09.00 (primary) | Older BOM (brownfield) |
|---|---|---|
| Compiler | Kotlin plugin `org.jetbrains.kotlin.plugin.compose`; **strong skipping is default** — lambdas are remembered, unstable params can skip | Same plugin from Kotlin 2.0 |
| Material 3 | `material3` **1.4.0** stable | Older 1.x — same components |
| Material 3 Expressive `[M3-1.5]` | Stable only in material3 **1.5** (beta at the time of writing); in 1.4 it is `@ExperimentalMaterial3ExpressiveApi` — [`styling`](../styling/SKILL.md) | n/a |
| Adaptive | `material3-adaptive` + window size classes ([`styling`](../styling/SKILL.md)) | Manual `BoxWithConstraints` |
| Collecting state | `collectAsStateWithLifecycle` | Same |
| Views `[Views]` | Compose is the default; XML lane is [`views-interop`](../views-interop/SKILL.md) | Same |
| Test APIs | Compose UI test **v2** (`StandardTestDispatcher`) — [`unit-testing`](../unit-testing/SKILL.md) | v1 |

Views are in maintenance mode (I/O 2026): new screens are Compose. A Views codebase is extended in Views unless asked otherwise.

## When to use

- Writing or refactoring a composable, screen or list
- "Why does this recompose?", "what keys for `LaunchedEffect`?", "where does this state go?"
- Choosing a Material 3 component; building the loading / failed / empty views

## When NOT to use

- Screen ViewModel, `uiState` design, DI → [`architecture`](../architecture/SKILL.md)
- Theme, colour, typography, insets, window size classes → [`styling`](../styling/SKILL.md)
- Routes and back stack → [`navigation`](../navigation/SKILL.md)
- Text fields and validation → `mobile-android-forms`
- Animation APIs → [`animation`](../animation/SKILL.md); labels and TalkBack → [`accessibility`](../accessibility/SKILL.md)
- Test tags → [`test-ids`](../test-ids/SKILL.md)
- iOS / RN components → `mobile-ios-ui-components`, `mobile-react-native-ui-components`

## Inputs needed

- Compose BOM and Material 3 version; whether the app is Compose-only or has Views
- The data region's source (a `uiState`) and its failure shape
- Whether the composable is screen-level or reusable

## Stateless by default, state hoisted

Two shapes only:

```kotlin
@Composable
fun OrdersScreen(
    viewModel: OrdersViewModel,
    onOpenOrder: (OrderId) -> Unit,
    modifier: Modifier = Modifier,
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    OrdersContent(state = state, onOpenOrder = onOpenOrder, onRetry = viewModel::refresh, modifier = modifier)
}

@Composable
fun OrdersContent(
    state: OrdersUiState,
    onOpenOrder: (OrderId) -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    when (state) {
        OrdersUiState.Loading -> LoadingIndicator(modifier)
        is OrdersUiState.Loaded -> OrdersList(state.orders, onOpenOrder, modifier)
        is OrdersUiState.Failed -> FailureBody(state.reason, onRetry, modifier)
    }
}
```

- **The screen composable** takes the ViewModel (or a route's arguments), collects `uiState`, and hands plain values and lambdas to the **content composable**. Only the screen knows the ViewModel; `OrdersContent` previews and tests with a literal state.
- **Everything below the screen is stateless**: state down, events up as lambdas (`onX`). A composable that reads a repository, `Context` services or a `NavController` is a finding.
- **Hoist to the lowest common parent** that reads or writes the state. UI-only state (expanded, focus, scroll) stays in `remember` / `rememberSaveable` in the composable that owns it; `rememberSaveable` where it must survive rotation.
- **Hoisting a controlled component:** value + `onValueChange`, optionally a `rememberXState()` holder class for a component with several related pieces of state.
- **`when` over a sealed state is exhaustive with no `else`** ([`basics`](../basics/SKILL.md)); a new case then breaks the build.

## The parameter list

`required parameters → modifier: Modifier = Modifier → optional parameters with defaults → trailing content lambda`.

- **`modifier` is the first optional parameter**, applied to the **root** emitted node only, and **passed once**. A composable that ignores or applies it to a child is a finding.
- **Event lambdas are `() -> Unit` / `(T) -> Unit`** named `onX`; not `MutableState`, not a `ViewModel`.
- **Slots over booleans**: `leadingIcon: @Composable (() -> Unit)? = null` beats `showIcon: Boolean`.
- **A composable returning Unit is `UpperCamelCase`; one returning a value is `lowerCamelCase`** (`rememberFoo`).
- **Order inside the modifier chain is meaning** (`padding` then `clickable` ≠ the reverse); `size`/`fillMax*` first, `clickable` before `padding` when the padding should be tappable.
- **Prefer `Modifier` to wrapper `Box`**; `Box` only for overlap; `LazyColumn` over `Column(verticalScroll)` for unbounded data; one scroll direction per axis; avoid `IntrinsicSize` unless needed; avoid `fillMaxSize` as a default.

## Lazy lists — keys and content types

```kotlin
LazyColumn(modifier = modifier, contentPadding = contentPadding) {
    items(items = orders, key = { it.id.value }, contentType = { "order" }) { order ->
        OrderRow(order = order, onClick = { onOpenOrder(order.id) }, modifier = Modifier.animateItem())
    }
}
```

- **`key` = a stable domain id** — never the index, never a value that changes on edit. Without keys, reorder and state (a scroll position, a text field) follow the position, not the item.
- **`contentType`** when a list mixes row kinds, so item composition is reused.
- **No lazy list inside a vertically scrolling parent of the same axis** (crash / infinite height); use one `LazyColumn` with several `item { }` / `items { }` blocks.
- **Hoist `rememberLazyListState()`** when a parent reads scroll position; derive "scrolled past first item" with `derivedStateOf` rather than reading the index in composition.

## Stability and recomposition

With strong skipping on, **stability is rarely the thing to fix** — measure first (recomposition counts, Compose compiler report, [`performance`](../performance/SKILL.md)).

- **State classes are immutable `data class`es with `val`s and `List`** ([`basics`](../basics/SKILL.md)). Strong skipping compares unstable params by instance, stable ones by `equals`; an `@Immutable` / `@Stable` annotation is a promise — add it only where a type from another module cannot be inferred and the promise is true.
- **Mutable collections as parameters are a finding**; `kotlinx.collections.immutable` is optional, not required.
- **Defer reads**: pass `() -> Float` (or use `Modifier.graphicsLayer { }`, `drawBehind`) for a value that changes every frame so only layout / draw reruns, not composition.
- **No work in composition**: sorting, filtering, formatting, `Regex`, object construction go in the ViewModel or in `remember(key) { }`; **`derivedStateOf`** only when a frequently changing input yields a rarely changing output.
- **Never write to state during composition**; never allocate listeners or `Handler`s in the body.

## Side effects — the right API

| Need | API | Rule |
|---|---|---|
| A suspend call tied to the composable's presence or a key | `LaunchedEffect(key)` | Keys are the values the effect reads; **`LaunchedEffect(Unit)` / `true` only for a true run-once** with a reason |
| A callback that must see the newest lambda inside a long effect | `rememberUpdatedState` | Avoids restarting the effect |
| Launch from an event handler (a click) | `rememberCoroutineScope()` | UI-scoped jobs only; long work belongs in the ViewModel |
| Register / unregister something | `DisposableEffect(key) { … onDispose { … } }` | Every registration has an `onDispose` |
| Publish Compose state to non-Compose code each successful recomposition | `SideEffect` | Rare |
| Turn a non-Compose source into state | `produceState`, `snapshotFlow` | Flow to state: prefer the ViewModel's `stateIn` |

A collector or listener started in a composable without lifecycle awareness is a leak. Show-a-snackbar and navigate-after-save follow the state-based pattern in [`architecture`](../architecture/SKILL.md), through `LaunchedEffect(state.message)`.

## Material 3 components

Use the component, not a hand-drawn look-alike: `Scaffold` with `topBar`, `snackbarHost`, `bottomBar`, content padding; `TopAppBar` family; `NavigationBar` / `NavigationRail` / `NavigationSuiteScaffold`; `Button` / `FilledTonalButton` / `OutlinedButton` / `TextButton`; `IconButton` with a label; `Card`; `ListItem`; `ModalBottomSheet`; `AlertDialog`; `SnackbarHost`; `PullToRefreshBox`; `OutlinedTextField`. **Never imitate iOS or the web** — no iOS-style switch, no segmented pill drawn by hand where `SingleChoiceSegmentedButtonRow` exists. Expressive components (`ButtonGroup`, `LoadingIndicator`, `FloatingToolbar`) are `[M3-1.5]` — experimental on 1.4 behind an opt-in; use them only where the project already opted in ([`styling`](../styling/SKILL.md)). Icons come from `Icons.Default` / the `material-icons-core` set or a project icon asset, with a `contentDescription` or `null` when decorative ([`accessibility`](../accessibility/SKILL.md)).

Design facts — spacing, touch targets (48 dp), component choice — are `design-ui-ux-pro-max --stack jetpack-compose`; where this skill and the corpus disagree on a design fact, the corpus wins (the one deliberate exception, ViewModel-to-UI events, is in [`architecture`](../architecture/SKILL.md)).

## Every data region: loading / loaded / failed / stale / offline

- **The region** is the response-dependent subtree: rows, canvas, pane. **Search, filters, the top bar and the header keep rendering** while the region shows `Loading` (a placeholder with a fixed height — no layout jump), `Failed` (a message from a string resource mapped from `FailureReason`, a Retry button, never `error.message`), or `Loaded`-empty (an empty state with the next action).
- **Stale**: data shown while a refresh runs or after a failed refresh carries a visible "last updated" cue; **offline** is told apart from a server error and keeps cached rows visible.
- **One persistent, user-dismissed error banner inside the safe area** accompanies every surfaced failure (a `Snackbar` with `SnackbarDuration.Indefinite` and a dismiss action, or an in-content banner) — never auto-dismissing. A drifted or undecodable response is `Failed`, not an empty list.
- Every request has a timeout budget — [`networking`](../networking/SKILL.md). Rendering detail and the restore flow: `mobile-android-error-handling`.

## Previews

`@Preview` on every reusable composable, covering its states (Loading, Loaded, Failed, empty, long text, large font via `fontScale`, dark via `uiMode`). A multipreview annotation (`@PreviewLightDark`, `@PreviewFontScale`, or a project `@PreviewStates`) once the same set repeats. **A preview never calls a real repository, network or database**; it renders the content composable with a literal state. A private preview function lives beside the composable.

## Rules

- Screen composable takes the ViewModel; every composable below it is stateless with `modifier` first among optional parameters, applied to the root.
- State down, events up; hoist to the lowest common parent.
- Lazy lists use `key` (stable id) and `contentType` for mixed rows.
- Effects use the API in the table; every `LaunchedEffect` has meaningful keys, every registration disposes.
- Material 3 components, not imitations; Expressive only on 1.5 or an existing opt-in.
- Each data region renders loading / loaded / failed / stale / offline, scoped to the region, with a persistent error banner.
- Previews for reusable composables, no live data.

## What NOT to do

- Pass a `ViewModel` or `NavController` down the tree.
- Use `remember` for business state, or `rememberSaveable` for a list.
- Use the list index as a key, or `LaunchedEffect(Unit)` as a default.
- Sort, format or parse in the composable body.
- Apply `modifier` to a child, or accept two modifiers.
- Show `error.message`, or collapse a failure into a blank list.
- Wrap a `LazyColumn` in `Column(verticalScroll)`.
- Add `@Stable` / `@Immutable` as a reflex.

## Validation (exit gate)

- [ ] Only the screen composable reads a ViewModel; content composables have a literal-state preview
- [ ] `modifier` first optional, applied once to the root
- [ ] Every `items { }` has a `key`; no `LaunchedEffect(Unit)` without a reason
- [ ] Failed region shows a retry and a persistent banner; offline separated; no raw exception text
- [ ] Previews cover the states and use no live data

## Handoffs

- ViewModel, `uiState` → [`architecture`](../architecture/SKILL.md)
- Theme and windows → [`styling`](../styling/SKILL.md); routes → [`navigation`](../navigation/SKILL.md)
- Forms → `mobile-android-forms`; labels → [`accessibility`](../accessibility/SKILL.md); test ids → [`test-ids`](../test-ids/SKILL.md)
- Recomposition profiling → [`performance`](../performance/SKILL.md)
- Compose UI tests → [`unit-testing`](../unit-testing/SKILL.md)
- Existing XML screens → [`views-interop`](../views-interop/SKILL.md)
