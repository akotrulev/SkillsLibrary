# Navigation Compose → Navigation 3

Source: developer.android.com/guide/navigation/navigation-3/migration-guide. Navigation 3 1.2 is stable; Navigation Compose 2.10 stays correct for an existing app. **Compose-only** — a Fragment-based app finishes [`views-to-compose`](views-to-compose.md) first. The guide describes a **single atomic migration**, not a mixed Nav2 / Nav3 app; do it as one change on one navigation graph.

## Steps

1. **Dependencies** (`compileSdk` 36+, `minSdk` 23+): `androidx.navigation3:navigation3-runtime`, `navigation3-ui` (1.2.0), and `androidx.lifecycle:lifecycle-viewmodel-navigation3` for entry-scoped ViewModels.
2. **Routes become `NavKey`s** — already `@Serializable`: `@Serializable data object Home : NavKey`; a route with arguments is a data class carrying them.
3. **State holder replaces `NavController`:** one back stack per top-level route, persisted with `rememberNavBackStack` / `rememberSerializable`; a small `Navigator` class owns `navigate(route)` and `goBack()`.
4. **`NavHost` → `NavDisplay`** with `entries`, `onBack`, and decorators: `rememberSaveableStateHolderNavEntryDecorator()` per stack and `rememberViewModelStoreNavEntryDecorator()` for entry-scoped ViewModels.
5. **Destinations → `entryProvider { entry<Route> { key -> Screen(key) } }`** — arguments come from `key`, not `toRoute()`. `dialog<T>` becomes `entry<T>(metadata = DialogSceneStrategy.dialog())`. `navigation<Base>` graphs are **deleted** — their children move to the top level; bottom sheets follow the recipe (the strategy is not in core).
6. **Results:** `rememberResultEventBusNavEntryDecorator()`; sender `resultBus.sendResult(...)`, receiver `ResultEffect<T>`. **The bus is in memory** — it does not survive process death; persist what matters in `SavedStateHandle` or the key.
7. **Deep links:** declared per destination in Nav2; in Nav3, matchers (`UriDeepLinkMatcher`) resolve the intent to a back stack in the Activity — in `onCreate` **and `onNewIntent`**. The intent is untrusted input: validate before building the stack ([`notifications-and-links`](../../notifications-and-links/SKILL.md)).
8. Remove all Navigation 2 imports and dependencies.

## Mapping

| Nav2 | Nav3 |
|---|---|
| `navigate(route)` | `navigator.navigate(route)` |
| `popBackStack()` | `navigator.goBack()` |
| `currentBackStackEntryAsState()` | The stack's last key |
| `hiltViewModel()` per destination | `hiltViewModel()` inside the entry with the ViewModel-store decorator |
| `LocalLifecycleOwner` from the back-stack entry | `LocalLifecycleOwner.current` inside the destination |

## Traps

- `popUpTo` / `launchSingleTop` semantics are state-holder logic now, written once in the `Navigator`; test it with a plain unit test.
- A selected bottom-bar item is `key == state.topLevelRoute`, not a hierarchy check.
- Without the ViewModel decorator, ViewModels are scoped to the Activity and survive entries they should not.
- Back handling for predictive back is `onBack` in `NavDisplay`; custom `BackHandler`s inside entries still win.
- `NavType` / `typeMap` custom types need a serializer for the key and a `DeepLinkSerializer` for links.

## Verify

- `rg -n "androidx.navigation\.|NavHost|NavController|toRoute" -g '*.kt' -g '*.kts'` is empty.
- Back stack survives rotation and process kill; a deep link opens the right stack from a cold start and from `onNewIntent`.
