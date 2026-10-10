# LiveData / RxJava → Flow

LiveData and RxJava are never in new code ([`architecture`](../../architecture/SKILL.md)). Move **from the data layer outward**: a repository that returns `Flow` can be consumed by a LiveData-based ViewModel through `asLiveData()` while the ViewModel is still waiting its turn.

## Order

1. **Data sources and repositories** — return `Flow` / `suspend`. Room 2.8 DAOs return `Flow<T>` directly; the Rx / LiveData integrations are built in on Room 2.8 and become separate converter artifacts on Room 3 ([`room2-to-3`](room2-to-3.md)).
2. **ViewModel** — expose one `uiState: StateFlow` built with `stateIn(viewModelScope, WhileSubscribed(5_000), initial)`; remove `MutableLiveData`.
3. **UI** — Compose `collectAsStateWithLifecycle()`; Views `repeatOnLifecycle(STARTED)` with `launch { flow.collect { … } }` in the view's lifecycle scope.
4. Remove `androidx.lifecycle:lifecycle-livedata-ktx` / `rxjava3` dependencies last.

## Mapping

| Before | After |
|---|---|
| `LiveData<T>` + `MutableLiveData` | `StateFlow<T>` + private `MutableStateFlow`, `update { }` |
| `MediatorLiveData` | `combine(a, b) { … }` |
| `Transformations.map / switchMap` | `map` / `flatMapLatest` |
| `SingleLiveEvent` / `Event<T>` wrapper | **State** the UI consumes and clears — no event channel ([`architecture`](../../architecture/SKILL.md)) |
| `Observable` / `Flowable` | `Flow` (`kotlinx-coroutines-rx3` `asFlow()` as the bridge) |
| `Single` / `Maybe` / `Completable` | `suspend` function (`await()` as the bridge) |
| `Schedulers.io()` / `observeOn(mainThread)` | Injected dispatcher + `flowOn`; collectors on `Main` |
| `CompositeDisposable` | The ViewModel / lifecycle scope — structured cancellation |
| `observe(viewLifecycleOwner)` in a Fragment | `repeatOnLifecycle(STARTED)` in `viewLifecycleOwner.lifecycleScope` |

## Traps

- **`LiveData` is conflated and sticky; `SharedFlow` is neither.** A migrated "event" must become state, or it fires twice / not at all after rotation.
- `asLiveData()` is a bridge for the in-between state; it is a finding in a finished migration.
- `collectAsState()` instead of `collectAsStateWithLifecycle()` keeps collecting in the background.
- `flow.collect` launched in `init` to push into another flow — use `stateIn`.
- Do not swallow `CancellationException` in a replacement for an Rx `onErrorReturn`.
- Tests: a LiveData test needed `InstantTaskExecutorRule`; the Flow test uses `runTest`, `StandardTestDispatcher` and Turbine ([`unit-testing`](../../unit-testing/SKILL.md)).

## Verify

- `rg -n "LiveData|MutableLiveData|io.reactivex|SingleLiveEvent" -g '*.kt'` is empty for the migrated modules.
- A rotation and a process kill restore the screen without a double snackbar.
