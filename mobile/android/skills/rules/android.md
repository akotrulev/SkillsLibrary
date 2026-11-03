---
paths:
  - "**/src/{main,debug,release}/**/*.kt"
  - "**/src/test*/**/*.kt"
  - "**/src/*{Main,Test}/**/*.kt"
---

<!-- mobile-android rules v1 (2026-11-03): core. Installed by /mobile-android:rules; edit the paths above to this project's Android modules, re-run to compare with the plugin's copy. -->

# Android / Kotlin code standards

Apply these to every Kotlin file you write, edit or review in an Android or Kotlin Multiplatform module. The tag after a rule is the severity a review reports: **blocker** ships a crash, a store rejection or a hard security break, **major** is a design or correctness problem, **minor** is style, **nit** is preference. Compose / Views UI, data, test, build, manifest and KMP rules are separate files that load with those files.

**The codebase wins.** Where this project consistently does something another way (Koin, Room 2.8, Navigation Compose, a Views screen), follow the project and do not flag it. Detect the lane before writing: Kotlin, AGP and Gradle, compile / target / min SDK, the Compose BOM, Compose vs Views, KSP vs kapt, the DI container, Room 2.8 vs 3, Navigation 3 vs Navigation Compose, any KMP module. Never use an API above the detected lane, and never flag a down-level project for lacking one. A Kotlin, AGP, SDK or BOM move is never made beside other work; it is a `migration` run of its own. *major*

## Simplicity

- Write the simplest thing that meets the requirement, then stop. No interface with one implementer (a test fake counts as the second), no use case that only forwards to a repository, no ViewModel that mirrors a model, no wrapper that only forwards, no configurability nothing uses. *major, fix by inlining*
- Modules and convention plugins only on their second user; no `:core:*` or `:domain` module in a one-screen app. *minor*
- No LiveData, RxJava or an MVI framework the codebase did not choose in new code. *minor*
- Cut structure, never correctness: the three-state region, cancellation, the denied path and the tests stay.

## Kotlin

- No `!!` outside tests: `?: return`, `getValue(key)`, `as?`, or a non-null type when absence cannot happen. *blocker*
- No `lateinit` for an injectable dependency. *major*
- UI state is an immutable `data class` (all `val`, changed with `copy()`); no `var` or `MutableList` field in it and no `StateFlow` of a mutable object. *major*
- `val` over `var`; read-only `List` / `Set` / `Map` in signatures. *minor*
- A load is one sealed interface, never booleans for loading / error / data; `when` over it is exhaustive with no `else`. *major*
- A failure carries a typed reason, never `Throwable.message`; no `null` return to mean failure. *major*
- No Java-isms: `get`/`set` pairs, `Optional`, static-holder classes, a builder where named and default arguments serve. *minor*
- A context parameter never carries a repository or service. *major*

## Coroutines and the main thread

- No `GlobalScope`; launch in `viewModelScope`, `lifecycleScope` or a scope the owner cancels; work that must outlive the screen is WorkManager. *blocker*
- No `runBlocking`, `Thread.sleep`, `.get()` on a future, or disk, network or database work on the main thread. *blocker*
- Dispatchers are injected, never `Dispatchers.IO` named in a class body; a `suspend` function that blocks moves itself with `withContext(ioDispatcher)`. *major*
- `CancellationException` is rethrown; no `catch (e: Exception)` or `runCatching` around a suspend call that swallows it. *major*
- Flows are collected with the lifecycle: `collectAsStateWithLifecycle`, or `repeatOnLifecycle(STARTED)` in Views; never `collectAsState()` on a ViewModel flow or `launchWhenStarted`. *major*
- `StateFlow` changes with `update { it.copy(…) }`, not `value = value.copy(…)`. *minor*
- Derive state with operators and `stateIn(viewModelScope, WhileSubscribed(5_000), …)`; no collect in `init` that pushes into another flow. *minor*

## Architecture and DI

- One screen ViewModel, one `uiState: StateFlow`, the mutable one private. No ViewModel-to-UI events: no `SharedFlow` or `Channel` of navigation, snackbar or error effects; a one-off outcome is a state field the UI consumes and the ViewModel clears. *major*
- A ViewModel holds no `Context`, `View`, `NavController` or composable. *major*
- Repositories own data and are main-safe; a composable never calls a repository, DAO or client. *major*
- Constructor injection only: no service locator, no `object` or `companion` holding a client or mutable state, no Hilt field injection outside an entry point. Manual DI first; Hilt on KSP once earned. *major*
- `SavedStateHandle` holds the small state that must survive process death, never a list or a model. *major*

## Errors, secrets and untrusted input

- An error is caught where it is thrown and becomes state; no `catch { }` that leaves a region empty, no `error()` for a recoverable condition. *major*
- No exception message, stack or response body on screen. *major*
- No secret in the APK: no token or key in `BuildConfig`, resources, `SharedPreferences`, plain DataStore, Room, files or `SavedStateHandle`. Tokens live only in Keystore-backed storage. *blocker*
- No token, body or personal data in a log line. *blocker*
- Links, push payloads and intents are untrusted: one pure, validated parse function maps them to a closed set of destinations; never a route, `Intent` or `Class.forName` built from unchecked `intent.data` or message data. *blocker*
- A `PendingIntent` is immutable, explicit and has its own request code. *blocker*

## Comments

- No comments inside a function body: no step markers, no restating the next line, no commented-out code, no `TODO` / `FIXME`. Extract and name the step instead. *minor; major when the comment exists because the code is unclear*
- KDoc only where the name cannot carry the meaning, stating a contract, never the signature; scaffolded template comments are removed. *minor*
