---
name: mobile-android-basics
description: Use when writing or reviewing Kotlin — conventions, null safety, val and data classes, sealed interfaces for state, structured concurrency, injected dispatchers, Flow vs StateFlow vs SharedFlow, context parameters. Triggers "idiomatic Kotlin?", "can I use !!", "StateFlow or SharedFlow", "which dispatcher", "GlobalScope". Also the Expo native-module Kotlin standard. Do NOT use for project setup, Compose screens, or networking (`mobile-android-project-setup`, `-ui-components`, `-networking`).
---

# Android — The Kotlin Coding Standard

How Kotlin is written in this library: official conventions, null safety with no `!!`, immutability, sealed state, structured concurrency with injected dispatchers, and Flow used for what each type is for. It is the Kotlin half of CLAUDE.md § Mobile code rules; the audit rows are sections A and B of `mobile-android-standards-audit`.

**Reads without an app.** `mobile-react-native` loads this skill for Expo Modules and config-plugin Kotlin. Nothing here needs Compose, Hilt or a Gradle app module: apply it to a module's `.kt` files as they stand. App-level skills (`mobile-android-project-setup`, `-architecture`, `-ui-components`, `-networking`) are named for hand-off only — never required to apply this one.

## Version lane — detect first, key every recipe to it

Read the Kotlin version (`libs.versions.toml` / `kotlin` plugin), `languageVersion`, `-X` flags and the JDK toolchain **before** writing. Never up-level Kotlin, `languageVersion` or an API level as a side effect.

| Concern | Kotlin 2.4 (primary) | Kotlin 2.0–2.3 (brownfield) |
|---|---|---|
| Compiler | K2 only | K2 (2.0+) |
| Context parameters (`context(...)`) | **Stable** (explicit context arguments still experimental) | Preview in 2.2–2.3 behind `-Xcontext-parameters`; **do not use** in a project that has not opted in |
| Explicit backing fields (`val x: A field = B`) | **Stable** | Experimental — keep the `_x` / `x` pair |
| Compose compiler | Plugin `org.jetbrains.kotlin.plugin.compose`; strong skipping default | Same plugin since 2.0 |
| `kapt` | Never — KSP | Never — KSP; kapt in brownfield is a migration finding |
| Context receivers | Removed | Removed in 2.2 — migrate to context parameters |

A down-level project is not flagged for lacking a 2.4 feature. Kotlin 2.0–2.3 modules migrate through `mobile-android-migration`.

## When to use

- Writing Kotlin in an app, a library module or an Expo native module
- "Is `!!` OK here?", "data class or class?", "StateFlow or SharedFlow?", "which dispatcher?"
- Choosing how a coroutine is launched and cancelled; fixing a swallowed `CancellationException`

## When NOT to use

- Gradle, AGP, version catalog, detekt / ktlint → `mobile-android-project-setup`
- Screen ViewModel shape and DI → `mobile-android-architecture`
- Composables → `mobile-android-ui-components`
- Retrofit / Ktor clients → `mobile-android-networking`
- Tests → `mobile-android-unit-testing`
- Swift → `mobile-ios-basics`

---

## Conventions

The official Kotlin coding conventions are the floor; ktlint enforces the formatting, so this list is what formatting cannot.

- **Names**: `UpperCamelCase` types, `lowerCamelCase` functions and properties, `SCREAMING_SNAKE_CASE` only for `const val` and immutable top-level or `object` values. A `@Composable` that returns Unit is `UpperCamelCase`. Acronyms of two letters stay upper (`IO`), longer ones capitalise the first letter (`Url`, `Json`).
- **Packages by feature, lowercase, no underscores**; one top-level class per file named after it; a file of several related small declarations is named for what they share.
- **Expression bodies** for one-expression functions; `when` as an expression with an exhaustive result; `if` as an expression. Named arguments when a call has more than two arguments of the same type or any boolean literal.
- **Scope functions sparingly.** `let` for a null-checked transformation, `apply` for configuring an object being built, `also` for a side effect in a chain. Never nest scope functions — an inner `it` / `this` shadowing the outer is the tell.
- **Extension functions for behaviour that belongs to a type you do not own**; private extensions for file-local helpers. Not a dumping ground — a `StringUtils.kt` of unrelated extensions is a smell.
- **Trailing commas** in multi-line parameter and argument lists.
- **Visibility: `private` first.** `internal` for module-wide, public only for a library module's API. Explicit API mode (`explicitApi()`) in a library module that publishes.
- **No Java-isms**: no `get`/`set` method pairs, no `static` holder classes (`object` or top-level), no `Optional`, no builder where named and default arguments serve.
- **`const val` for compile-time constants; `object` for stateless singletons only.** A singleton that holds mutable state is the static mutable state CLAUDE.md forbids — inject it.

## Null safety — no `!!` outside tests

**`!!` does not appear outside test code.** It converts a type-system guarantee back into a crash.

| Instead of | Write |
|---|---|
| `value!!` | `value ?: return` / `value ?: error("…")` where absence is a bug, with the evidence in the message |
| `map[key]!!` | `getValue(key)` (throws a descriptive `NoSuchElementException`) or `map[key] ?: return` |
| `x as Foo` | `x as? Foo ?: return`, or `when (x) { is Foo -> … }` |
| `lateinit var` for a dependency | Constructor injection — `lateinit` only for a framework-created view or a test fixture |
| `requireNotNull(x)` | Acceptable at a boundary for a precondition that is a programmer error — with a message |

- **Make the type non-null if absence cannot happen.** A nullable that every caller immediately unwraps is the wrong type.
- **Never nullable collections** — an empty list means none. A platform type from Java (`String!`) is declared nullable or non-null explicitly at the boundary and checked once.
- **Elvis with `return` / `continue` / `throw`** is the early-exit idiom; `?.let { }` for a scoped use.
- **`error()` and `check()` / `require()`** state invariants and argument contracts; they are for programmer error, never user input or I/O.

## Immutability — `val`, data classes, read-only collections

- **`val` over `var`**; a `var` that is never reassigned is a defect. Function parameters are values.
- **`data class` for plain data** — models, DTOs, UI state. All properties `val`; change with `copy()`. A data class with a mutable property or a `ByteArray` field is a trap (equality, hashing).
- **`value class` for a typed id** (`@JvmInline value class OrderId(val value: String)`) so ids do not mix; do not wrap everything.
- **`List` / `Set` / `Map` in signatures**, never `MutableList`; build with `buildList { }` / `toList()`. Expose a read-only view of a private mutable collection.
- **`enum class` for a closed set of simple constants; a sealed interface the moment a case carries data.**
- **`class` (final by default) for identity or a service**; `open` and `abstract` only for a designed hierarchy — composition over inheritance.
- **Records of behaviour are interfaces only on the second implementer** (CLAUDE.md § KISS). A repository interface with one implementation is an unearned abstraction — except where a fake in tests is the second implementation, which is the justification the architecture skill records.

## State as sealed interfaces

A screen's load is **one sealed type**, never three booleans:

```kotlin
sealed interface OrdersState {
    data object Loading : OrdersState
    data class Loaded(val orders: List<Order>, val isStale: Boolean = false) : OrdersState
    data class Failed(val reason: FailureReason) : OrdersState
}

enum class FailureReason { Offline, Timeout, Server, Unknown }
```

- **`sealed interface` over `sealed class`** unless the cases share state or a constructor; interfaces compose (a case can implement two).
- **`data object`** for stateless cases; `when` over the type is **exhaustive with no `else`** — adding a case then breaks the build where it must be handled. An `else` branch on a sealed type is a finding.
- **The failed case carries the typed reason, never `Throwable.message`** — the UI maps a reason to a string resource (and never leaks an exception message).
- **Results and errors**: functions throw typed exceptions at an I/O boundary or return a sealed result; they do not return `null` to mean failure. `kotlin.Result` is not a return type for domain functions.

## Structured concurrency

Detail in [`references/concurrency.md`](references/concurrency.md); the rules every file obeys:

| Rule | Why |
|---|---|
| **No `GlobalScope`.** Launch in a scope with a lifetime: `viewModelScope`, `lifecycleScope`, a `CoroutineScope` the owner creates and cancels | Work a screen starts is cancelled when the screen goes |
| **Dispatchers are injected**, never `Dispatchers.IO` written in a class body | The test replaces them; the production default is one named binding |
| **`suspend` functions are main-safe**: a function that does blocking I/O moves itself with `withContext(ioDispatcher)` | A caller never has to know which thread to call from |
| **Never `runBlocking` in production code**; never `.join()` / `.await()` on the main thread | CLAUDE.md § async all the way down |
| **Never swallow `CancellationException`** — rethrow it | `catch (e: Exception)` and `runCatching` both catch it and break cancellation |
| **`coroutineScope { }` / `async` for parallel children**, `supervisorScope` only when one child failing must not cancel siblings | Failure and cancellation propagate by design |
| **Collect flows lifecycle-aware** — `collectAsStateWithLifecycle` in Compose, `repeatOnLifecycle(STARTED)` in Views | A background collector wastes work and can crash on a destroyed UI |

```kotlin
class OrdersRepository(
    private val api: OrdersApi,
    private val ioDispatcher: CoroutineDispatcher,
) {
    suspend fun orders(): List<Order> = withContext(ioDispatcher) {
        api.orders().map(OrderDto::toDomain)
    }
}
```

## `Flow`, `StateFlow`, `SharedFlow`

| Type | Is | Use for | Never for |
|---|---|---|---|
| `Flow<T>` | Cold, per-collector stream | A repository's observable query (Room, DataStore), one-shot sequences | Holding the latest UI state |
| `StateFlow<T>` | Hot, always has a value, conflates equal values | **A screen's one `uiState`** (CLAUDE.md § Mobile code rules); a latest-value cache | Events that must each be handled |
| `SharedFlow<T>` | Hot, no initial value, optional replay | Fan-out between components (a process-wide invalidation signal) | Delivering events from a ViewModel to its UI |

- **One `uiState: StateFlow` per screen ViewModel**, built with `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initial)` from the repository's flows, collected with `collectAsStateWithLifecycle`. **No ViewModel-to-UI events** — a one-off outcome (a snackbar, a navigation) is a field in the state that the UI consumes and the ViewModel clears.
- **Expose read-only, keep the mutable one private.** Kotlin 2.4: an explicit backing field (`val uiState: StateFlow<S> field = MutableStateFlow(S())`); before 2.4: `private val _uiState` + `val uiState = _uiState.asStateFlow()`.
- **Update `StateFlow` with `update { it.copy(…) }`** — an atomic read-modify-write; `value = value.copy(…)` races.
- **Operators**: `map`, `combine`, `flatMapLatest` (restart on a new key — search), `distinctUntilChanged` (already in `StateFlow`), `debounce` for input. `catch { }` handles upstream failures and **does not catch downstream or `CancellationException`**.
- **`flowOn(ioDispatcher)` changes the upstream context only**; never `withContext` around `emit`.
- **Do not collect inside `init` with a bare `launch` to feed another flow** — derive with operators and `stateIn`.

## Context parameters — only when earned

**[Kotlin 2.4, stable]** `context(logger: Logger) fun sync() { … }` makes a dependency implicit in a call chain. Use one **only** when the same dependency would otherwise be threaded through a long chain of internal calls and it is genuinely ambient (a transaction scope, a `CoroutineScope`-like receiver, a DSL's builder).

- **Not a service locator.** A context parameter resolves at the call site from the caller's scope; it is not a lookup by type at runtime. Dependencies of a class are still constructor-injected.
- **Not for business dependencies** — a repository is a constructor parameter, never a `context(...)`.
- **Not in a project below 2.4** that has not enabled the preview flag.
- Context receivers are gone; migrate them to context parameters when raising Kotlin.

## Common gotchas

- **`catch (e: Exception)` / `runCatching` around a `suspend` call** — swallows `CancellationException`; rethrow it (reference).
- **`Dispatchers.Main` hard-coded in a ViewModel** — untestable; inject or use `viewModelScope`.
- **`GlobalScope.launch`** to "outlive" a screen — use WorkManager for work that must survive, an application-scoped scope injected for fire-and-forget app work.
- **A `StateFlow` of a mutable object** — equal-by-reference mutation never emits; the state is an immutable data class.
- **`SharedFlow` for UI events** — dropped when nothing collects; model it as state.
- **`!!` on `findViewById` / `getSystemService`** — use ViewBinding or the typed `getSystemService<T>()` and handle null.
- **Logging with string templates** — `Log.d("tag", "$token")`: log through the project's logger with no sensitive values; telemetry is `mobile-shared-observability`'s.

## Handoffs

- Scopes, cancellation, `runCatching`, test seams → [`references/concurrency.md`](references/concurrency.md)
- Gradle, AGP 9, lint → `mobile-android-project-setup`
- Screen ViewModel, DI → `mobile-android-architecture`
- LiveData / RxJava → Flow, kapt → KSP → `mobile-android-migration`
- Telemetry → `mobile-shared-observability`
- Swift counterpart → `mobile-ios-basics`
