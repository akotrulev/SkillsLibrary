# Kotlin coroutines — scopes, cancellation, `runCatching`, test seams

Depth for [`../SKILL.md`](../SKILL.md). Applies to an app and to a library or Expo native module alike: a library takes its dispatcher and scope as constructor parameters and never creates a global one.

## 1. Scopes — every coroutine has an owner

A coroutine is a child of a scope; the scope's lifetime is the work's lifetime.

| Owner | Scope | Cancelled when |
|---|---|---|
| Screen ViewModel | `viewModelScope` | The ViewModel is cleared (not on rotation) |
| Activity / Fragment / Compose lifecycle | `lifecycleScope`, `rememberCoroutineScope()`, `LaunchedEffect(key)` | The lifecycle is destroyed / the composable leaves composition / the key changes |
| Application-wide fire-and-forget (a sync kick, analytics flush) | An **injected** `CoroutineScope(SupervisorJob() + defaultDispatcher)` provided once by the application | The process dies — use sparingly |
| Work that must survive the process | **WorkManager**, not a scope | Per its constraints |
| A library or module | A scope **passed in**, or `coroutineScope { }` inside a `suspend` function | The caller's scope |

- **`GlobalScope` is banned.** It has no owner, so its work cannot be cancelled and leaks past the screen; it fails the "work a screen starts is cancelled when the screen goes" rule.
- **Prefer `suspend` functions over functions that take a scope and launch.** The caller decides concurrency; a function that launches internally hides work the caller cannot await or cancel.
- **`coroutineScope { }`** for structured fan-out inside a `suspend` function — it returns when all children finish and cancels all of them if one fails.
- **`supervisorScope { }`** only when one child failing must not cancel its siblings (independent prefetches); each child then handles its own failure.
- **`launch` for fire-and-forget inside a scope; `async` only when a result is awaited.** An `async` whose `await` is skipped swallows its exception until the scope ends.
- **A `Job` stored in a property** is for "restart on a new request": `job?.cancel(); job = scope.launch { … }`. Prefer `flatMapLatest` / `collectLatest` where the trigger is a flow.
- **Never create a `CoroutineScope(...)` in a class body without a `cancel()` path** — an uncancelled scope is the same leak as `GlobalScope`.

## 2. Dispatchers — injected, main-safe

```kotlin
@Qualifier
annotation class IoDispatcher
```

(The qualifier is Hilt's; manual DI passes the dispatcher as a plain constructor parameter. The rule is the injection, not the container — the architecture skill owns the wiring.)

| Dispatcher | Use | Rule |
|---|---|---|
| `Dispatchers.Main` / `Main.immediate` | UI and state updates | `viewModelScope` and `lifecycleScope` already use it; never name it in a class |
| `Dispatchers.Default` | CPU work: sorting, parsing a big payload, diffing, image processing | Inject `defaultDispatcher` |
| `Dispatchers.IO` | Blocking I/O: files, databases that are not `suspend`-aware, legacy blocking SDKs | Inject `ioDispatcher`; Room, Retrofit and DataStore `suspend` APIs are already main-safe and need no `withContext` |
| `limitedParallelism(n)` | A serial or bounded resource | Created once, in the provider |

- **`withContext(dispatcher)` at the boundary that does the blocking work**, so every caller is main-safe. A ViewModel calling a repository function never wraps it in `withContext`.
- **Do not switch dispatchers to "fix" a race.** A shared mutable variable is protected by confining it to one coroutine, a `Mutex`, or an atomic update on a `StateFlow` — not by choosing a different dispatcher.
- **CPU-bound loops check `ensureActive()`** (or call a cancellable suspend function) so they stop on cancellation.

## 3. Cancellation — cooperative, and exceptions must not eat it

Cancelling a scope throws **`CancellationException`** at the next suspension point. Anything that catches it and carries on breaks cancellation, leaves the coroutine running, and can leave state half-updated.

- **Never `catch (e: Exception)` / `catch (e: Throwable)` around a suspension point without rethrowing `CancellationException`:**

```kotlin
suspend fun refresh(): Result<List<Order>> =
    try {
        Result.success(api.orders())
    } catch (e: CancellationException) {
        throw e
    } catch (e: IOException) {
        Result.failure(e)
    }
```

  Catch the **narrowest exception** the call can throw (`IOException`, `HttpException`, a typed domain error); a blanket `Exception` catch needs the rethrow above it.
- **`try` / `finally` for cleanup that must run on cancel**; a `suspend` call inside `finally` needs `withContext(NonCancellable)` — and only for short, essential cleanup.
- **Blocking code is not cancellable.** Wrap a cancellable callback API with `suspendCancellableCoroutine` and `invokeOnCancellation { … }` to cancel the underlying operation (a `Call`, a location request).
- **Timeouts**: `withTimeout(…)` throws `TimeoutCancellationException` (a `CancellationException`); use `withTimeoutOrNull(…)` where the timeout is an expected outcome, and map it to the *timeout* failure reason — not to a generic error. Every network request has a timeout budget (CLAUDE.md § Mobile code rules).
- **`CancellationException` is control flow, not a failure.** Never surface it as an error state or banner.

## 4. `runCatching` and coroutines

**`runCatching { suspendCall() }` catches `CancellationException`** and turns it into a `Result.failure`, so the coroutine continues after being cancelled. It is the most common way Kotlin code silently breaks cancellation.

| Situation | Do |
|---|---|
| A `suspend` call inside `runCatching` | Don't. Use the `try` / `catch` above, or a local helper that rethrows |
| Truly non-suspending code (parsing a string) | `runCatching` is fine |
| You want a `Result`-returning helper | Write it once with the rethrow, and use that everywhere |

```kotlin
suspend inline fun <T> suspendRunCatching(block: () -> T): Result<T> =
    try {
        Result.success(block())
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        Result.failure(e)
    }
```

- `Result` is acceptable as a **private** plumbing type between two functions in one file; a public domain function returns a value, throws a typed exception, or returns a sealed result — never `Result<T>`.
- **Do not `getOrNull()` a failure the user must see** — it discards the reason; map it to the `Failed` state.
- **An uncaught exception in `launch` crashes the app** (it goes to the scope's handler); an exception in `async` surfaces on `await`. A `CoroutineExceptionHandler` is a last-resort logger for a root scope, not a substitute for handling failures at the call.

## 5. Flow collection and lifecycle

- **Compose**: `val state by viewModel.uiState.collectAsStateWithLifecycle()` — collection stops below `STARTED`.
- **Views**: `viewLifecycleOwner.lifecycleScope.launch { viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) { flow.collect { … } } }` — one `repeatOnLifecycle` per `launch`, never `launchWhenStarted` (removed from use).
- **ViewModel**: `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initial)` — the 5-second window keeps upstream alive across a rotation and stops it when the UI is really gone. `Eagerly` only when the work must run with no UI; `Lazily` almost never.
- **`collectLatest` / `flatMapLatest`** cancel the in-flight work when a new value arrives (search, a changing id); `collect` does not.
- **A flow collecting in a `launch` inside `init` that feeds `MutableStateFlow`** is the pattern `stateIn` replaces — use it for new code.

## 6. Test seams

The seams are the **injected dispatcher and scope**, and a **fake** for each collaborator (fakes over mocks, CLAUDE.md § Test code rules).

- **Inject `CoroutineDispatcher`s** and pass `StandardTestDispatcher(testScheduler)` in tests; `runTest { }` supplies the scheduler and skips virtual delays. Tests that relied on `UnconfinedTestDispatcher` running eagerly are the exception, not the default; **Compose UI test v2 APIs run on `StandardTestDispatcher`**, so advance with `advanceUntilIdle()` / `waitForIdle()`, not by assuming immediacy.
- **`Dispatchers.setMain(testDispatcher)` in a test rule** for code that uses `viewModelScope`; reset it in teardown. A ViewModel that takes its dispatcher by constructor needs no `setMain` for the work it dispatches itself.
- **Time**: inject a `Clock` (or a `() -> Instant`) and use `delay` under the test scheduler; never `Thread.sleep` or a real wait in a test.
- **Assert flows with Turbine** (`test { awaitItem() }`) or `first()` / `toList()` on a `backgroundScope` collector; assert the **sequence of states** (`Loading` → `Loaded`), not just the last.
- **Cancellation is testable**: launch, `cancel()`, `advanceUntilIdle()`, then assert the fake saw no further work and no state changed.
- **The test body has no `try` / `catch`** (CLAUDE.md § Test code rules): an expected exception is `assertFailsWith<T> { … }`; an unexpected one reaches the runner.
- **A scope created in production code and not injected** is untestable — the seam is the constructor parameter, which is why `GlobalScope` and in-class `CoroutineScope(...)` are findings.
