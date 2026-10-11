---
name: architecture
description: Use when deciding where state and logic live in a Compose app — repositories, one screen ViewModel with one uiState StateFlow, no ViewModel-to-UI events, use cases only in big apps, Hilt or manual DI, SavedStateHandle for process death, modules only when earned. Triggers "ViewModel or not", "how do I show a snackbar from the ViewModel". Do NOT use for Retrofit (`mobile-android:networking`), Room (`-offline-and-storage`) or routes (`-navigation`).
---

# Android — Architecture and State

Google's recommended architecture (2026-10-05), applied with the house rules: a **data layer of repositories**, a **screen ViewModel that exposes exactly one `uiState: StateFlow`**, a UI that renders it and sends plain function calls back, **no ViewModel-to-UI events**, a domain layer only when the app earns it, Hilt for a complex app and manual DI for a simple one, and **fakes over mocks**. It is the Android half of CLAUDE.md § Mobile code rules; audit rows are section C of `mobile-android:standards-audit`.

## Version lane

| Concern | Primary (AGP 9, Kotlin 2.4) | Brownfield |
|---|---|---|
| ViewModel / state | `androidx.lifecycle` ViewModel, `StateFlow`, `collectAsStateWithLifecycle` | Same |
| Backing field | Explicit backing field `val uiState: StateFlow<S> field = MutableStateFlow(S())` (Kotlin 2.4 stable) | `_uiState` + `asStateFlow()` — correct below 2.4 |
| DI | Hilt (Gradle plugin 2.59+ needs AGP 9) or manual | Hilt ≤ 2.58 on AGP 8; Dagger; Koin if already chosen |
| Per-entry ViewModels | Navigation 3 `rememberViewModelStoreNavEntryDecorator()` ([`navigation`](../navigation/SKILL.md)) | `hiltViewModel()` / `viewModel()` per Navigation Compose destination |
| LiveData / RxJava / `kapt` | Never in new code | A migration finding — `mobile-android:migration` |
| Kotlin Multiplatform | KMP ViewModel; Koin or Metro — Hilt is Android-only | [`kotlin-multiplatform`](../kotlin-multiplatform/SKILL.md) |

A down-level project is not flagged for lacking 2.4's backing field. Kotlin standard and Flow rules are [`basics`](../basics/SKILL.md).

## When to use

- A feature must hold state, survive rotation or process death, or share state across screens
- "Do I need a ViewModel?", "where does this repository live?", "how do I show a snackbar?"
- Choosing Hilt vs manual DI; deciding whether a module or use case is earned

## When NOT to use

- Retrofit / Ktor clients, retries, token refresh → `mobile-android:networking`
- Room / DataStore / Keystore → `mobile-android:offline-and-storage`
- Route types and back stack → [`navigation`](../navigation/SKILL.md)
- Composable structure → [`ui-components`](../ui-components/SKILL.md)
- Form state and validation → `mobile-android:forms`
- Gradle and modules' build files → [`project-setup`](../project-setup/SKILL.md)
- Another stack → `mobile-ios:architecture`, `mobile-react-native:architecture`

## Inputs needed

- Compose or Views (Views → [`views-interop`](../views-interop/SKILL.md)); Hilt / Koin / manual already in place
- What the state is: composable-local, screen state, or app-wide
- What must survive process death

## The layers

```
UI (composables)  ──state down, calls up──  ViewModel (one per screen)
                                               │
                                  [use case — only when earned]
                                               │
                              Repository (one per data type) ── data sources (network, Room, DataStore)
```

- **Data layer:** a repository per kind of data (`OrdersRepository`), the single source of truth for it, owning its data sources and conflict policy. It exposes `Flow` for observed data and `suspend` functions for one-shot work, **main-safe** (injected dispatcher, [`basics`](../basics/SKILL.md)). Repositories hold no UI types.
- **UI layer:** composables render state; the **screen ViewModel** holds screen state and calls repositories. A composable never calls a repository.
- **Domain layer / use cases: only in a big app** — when logic is reused by two ViewModels or is a real business rule worth testing alone. A use case that forwards one repository call is a layer that only forwards: delete it.
- **Interfaces on repositories** appear with the second implementation — a **fake** a test needs counts ([`unit-testing`](../unit-testing/SKILL.md)); until then the concrete class is injected.

## One screen ViewModel, one `uiState`

```kotlin
sealed interface OrdersUiState {
    data object Loading : OrdersUiState
    data class Loaded(
        val orders: List<Order>,
        val isStale: Boolean = false,
        val message: UserMessage? = null,
    ) : OrdersUiState
    data class Failed(val reason: FailureReason) : OrdersUiState
}

class OrdersViewModel(
    private val repository: OrdersRepository,
    private val savedStateHandle: SavedStateHandle,
) : ViewModel() {

    private val message = MutableStateFlow<UserMessage?>(null)

    val uiState: StateFlow<OrdersUiState> = combine(repository.observeOrders(), message) { orders, message ->
        OrdersUiState.Loaded(orders, message = message) as OrdersUiState
    }
        .catch { emit(OrdersUiState.Failed(it.toFailureReason())) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), OrdersUiState.Loading)

    fun onSave() {
        viewModelScope.launch {
            repository.save()
            message.value = UserMessage.Saved
        }
    }

    fun onMessageShown() {
        message.value = null
    }
}
```

- **`stateIn(viewModelScope, WhileSubscribed(5_000), initial)`** from the repository's flows: the 5 s survives a rotation without restarting the upstream and stops it when the app is backgrounded. Derive with operators (`combine`, `flatMapLatest`); **do not `launch { flow.collect { _state.value = … } }` inside `init`** to feed state.
- **A user action that changes state uses `MutableStateFlow.update { it.copy(…) }`** — atomic, never `value = value.copy`. Mutable stays private; the exposed type is `StateFlow`.
- **The state is the sealed type from [`basics`](../basics/SKILL.md)** — `Loading` / `Loaded` / `Failed`, with `isStale` and an offline `FailureReason`; never three booleans, never `Throwable.message`. Rendering all of them is [`ui-components`](../ui-components/SKILL.md) and `mobile-android:error-handling`.
- **The UI collects with `collectAsStateWithLifecycle()`** (`lifecycle-runtime-compose`) — never `collectAsState()`.
- **The ViewModel takes its dependencies in the constructor** and holds no `Context`, `View`, `NavController` or composable reference. `AndroidViewModel` / `Application` only for a reasoned need.
- **User actions are plain methods** (`refresh()`, `onDismissMessage()`); the screen passes them down as lambdas. No `onEvent(sealed class Event)` funnel unless the screen already has one.

### No ViewModel-to-UI events

A snackbar, a toast, a navigation: **the ViewModel does not emit it** (no `SharedFlow` / `Channel` of effects). The outcome is **part of state** (`message` above), the UI shows it and tells the ViewModel it was consumed:

```kotlin
LaunchedEffect(state.message) {
    state.message?.let {
        snackbarHostState.showSnackbar(context.getString(it.resId))
        viewModel.onMessageShown()
    }
}
```

Navigation after a save is the same: a `navigateTo: Route?` field the UI observes, calls the navigator for, then clears — or the composable reacts to the state (`if (state.saved) onDone()`) and the ViewModel's `onDone()` resets it. An event is dropped when nothing collects it and can fire twice after a rotation; state is neither. **`design:corpus` `--stack jetpack-compose` row 16 (Channel + `receiveAsFlow` for navigation) conflicts with Google's recommendation and this rule — recorded as a decision in plan 002; the house rule applies.**

## State ownership

| State | Lives in | Survives |
|---|---|---|
| Scroll position, animation, focus, a text field mid-typing | `remember` / `rememberSaveable` in the composable | `rememberSaveable`: rotation + process death |
| Screen data and what the user chose to see | Screen ViewModel `uiState` | Rotation (ViewModel) |
| What must outlive process death (selected id, draft, filter) | `SavedStateHandle` in the ViewModel (`savedStateHandle.getStateFlow("q", "")`) | Process death |
| Data the app owns | Repository → Room / DataStore ([`offline-and-storage`](../offline-and-storage/SKILL.md)) | Everything |
| App-wide session / settings | A repository exposing `StateFlow`, injected where needed | App process |

- **Process death is part of the requirement.** A ViewModel is **not** restored by the system; `SavedStateHandle` (small, serializable values — ids, query strings, never lists or models) plus a reload from the repository is. Restore is verified with "Don't keep activities" or `adb shell am kill`.
- **Never put business state in `remember`**; never a repository result in `rememberSaveable`.
- **No client store over server data.** The repository + Room is the cache; no second Flow-of-everything in a singleton.

## Dependency injection

- **Constructor injection only** — no service locator, no field injection, no `Context.getSystemService` for your own classes.
- **Manual DI (simple app):** an `AppContainer` built in `Application.onCreate` holding the client, database and repositories, with a ViewModel `factory` that reads it (`viewModelFactory { initializer { OrdersViewModel(appContainer.orders, createSavedStateHandle()) } }`). One file; no library.
- **Hilt (complex app):** `@HiltAndroidApp`, `@AndroidEntryPoint` on `MainActivity`, `@HiltViewModel` + `@Inject constructor`, `@Module @InstallIn(SingletonComponent::class)` for the client / database / dispatchers (`@IoDispatcher` qualifier), KSP for the compiler, **never kapt**. Hilt arrives when manual wiring across several features starts to hurt, not on day one. Detail: [`references/hilt-and-modules.md`](references/hilt-and-modules.md).
- **Scopes:** `@Singleton` only for what is genuinely process-wide (client, database, repositories with in-memory state); ViewModels get their own scope.
- **No static mutable state; no `object` singleton holding a client.** Test seams — clock, id, dispatcher, config — are constructor parameters.

## Modules — only when earned

One `:app` module until a boundary hurts: build time, a feature a second app reuses, or a dependency-direction violation the compiler cannot prevent. Then split **by feature** (`:feature:orders`) over shared `:core:data` / `:core:ui` only as a second consumer appears; direction is `app → feature → core`, and a feature never depends on another feature's internals (a small `api` module or the navigation key types is the contract). Convention plugins arrive with the second module ([`project-setup`](../project-setup/SKILL.md)). Splitting by layer (`:data`, `:domain`, `:ui` for one feature) is a smell.

## Rules

- One screen ViewModel, one `uiState: StateFlow`, collected with `collectAsStateWithLifecycle`.
- No ViewModel-to-UI events: no `SharedFlow` / `Channel` of effects exposed to the UI.
- Repositories own data; composables never call them.
- Use cases only when reused or a real rule; interfaces only on a second implementation (a fake counts).
- `SavedStateHandle` for the small state that must survive process death.
- Constructor injection; manual DI first, Hilt on KSP when earned; no locator, no static state.
- Modules and convention plugins only on a second consumer.
- LiveData and RxJava never in new code.

## What NOT to do

- Add a use case, mapper and interface for every ViewModel call.
- Expose `MutableStateFlow`, a `Channel` or a `SharedFlow` of one-off events.
- Hold a `Context`, `NavController` or composable in a ViewModel.
- Keep the whole state in `rememberSaveable`, or restore a list from `SavedStateHandle`.
- Collect a flow in `init` to push into another one; use `stateIn`.
- Introduce Hilt, a `:domain` module and `:core:*` modules in a one-screen app.
- Reach for MVI frameworks (Orbit, MVIKotlin) in a codebase that did not choose them.

## Validation (exit gate)

- [ ] Each screen ViewModel exposes one `StateFlow` and no other flow or channel
- [ ] State is a sealed interface with failed / stale cases; no `Throwable.message` reaches the UI
- [ ] `rg -n "collectAsState\(\)|SharedFlow|Channel<" -g '*.kt'` finds nothing in ViewModel-to-UI position
- [ ] Process-death restore tried: kill the process, return, state reloads
- [ ] No `lateinit` dependency, no `.shared`, no locator; Hilt (if any) uses `ksp`

## Handoffs

- Flow and coroutine rules → [`basics`](../basics/SKILL.md)
- Composables and state hoisting → [`ui-components`](../ui-components/SKILL.md)
- Routes, entry-scoped ViewModels → [`navigation`](../navigation/SKILL.md)
- Persistence and sync → `mobile-android:offline-and-storage`
- Failure rendering, process-death restore tests → `mobile-android:error-handling`
- Fakes and `runTest` → [`unit-testing`](../unit-testing/SKILL.md)
- LiveData → Flow, Dagger → Hilt → [`migration`](../migration/SKILL.md)
