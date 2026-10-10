---
name: mobile-android-error-handling
description: Use when a failure must not blank a Compose screen — loading/loaded/failed/stale/offline regions, failure scoped below search and filters, the safe-area error banner, timeouts rendered, 401 re-auth in place, forced update on version skew, lifecycle resume, process-death restore, write failures, third-party failures, full-disk degradation. Triggers "list empty when API fails", "session expired mid-form". Do NOT use for producing the ApiError or retries (`mobile-android-networking`).
---

# Android — Error Resilience

Owns **failing safely and recovering**: **rendering** failure, staleness and offline so a broken region never looks like an empty one, and recovering in place from a dead session, a version the server no longer supports, a killed process, a backgrounded write or a full disk. Web analog: [`fe-react-error-handling`](../../../../frontend/react/skills/error-handling/SKILL.md) — every rule carries over with the mobile delta below; `error.tsx`, hydration, multi-tab and chunk-load errors do not exist here. Siblings: [`mobile-ios-error-handling`](../../../ios/skills/error-handling/SKILL.md), [`mobile-react-native-error-handling`](../../../react-native/skills/error-handling/SKILL.md) (OTA skew is RN-only).

Division of labour with [`networking`](../networking/SKILL.md): it **produces** the categorised `ApiError` (`Offline`, `TimedOut`, `Unauthorized`, `NotFound`, `Conflict`, `RateLimited`, `Validation`, `Server`, `Drifted` — `networking/references/request-policy.md`), applies the timeout budget and bounded retries. This skill **renders** it.

## Version lane

| Concern | Primary (Compose BOM 2026.09 · lifecycle 2.9+) | Notes |
|---|---|---|
| Region state | A sealed `LoadState` in the screen's one `uiState: StateFlow`, collected with `collectAsStateWithLifecycle` | One type, not four booleans; no ViewModel-to-UI events ([`architecture`](../architecture/SKILL.md)) |
| Failed / empty body | A composable with icon, text and action in the data area | `[Views]` a `ViewStub` / included layout with the same content |
| Pull to refresh | Material 3 `PullToRefreshBox` | The canonical refetch |
| Resume | `LifecycleResumeEffect` / `repeatOnLifecycle(STARTED)` | `[Views]` `Lifecycle.Event.ON_START` observer |
| Offline signal | `ConnectivityManager` default-network callback → `Flow` (`networking`'s `Connectivity`) | Never a ping |
| Process death | `SavedStateHandle` + `rememberSaveable`, then a reload | [`references/session-and-resume.md`](references/session-and-resume.md) |
| Crash / ANR reporting | One reporter + Android vitals — [`mobile-shared-observability`](../../../_shared/observability/SKILL.md) | A `!!`, an unchecked index or a `lateinit` read is **not** a recoverable error — prevent it |
| Forced update | Server minimum version → blocking screen (MASVS-CODE-2); Play In-App Updates is the store half | [`references/session-and-resume.md`](references/session-and-resume.md) |

Detect first: the existing banner / snackbar host, the `LoadState` / `ApiError` types, the wired crash reporter — extend them, never add a second.

## When to use

- Rendering a region's loading / loaded / failed / stale / offline states and the three empty kinds
- The persistent banner, a timeout, a `401` mid-session, a forced update, app resume, a killed process, a failed write or SDK, a full disk

## When NOT to use

- Producing the error, retries, `Retry-After`, token-refresh mechanics → [`networking`](../networking/SKILL.md)
- Persisting data, the write queue, conflicts → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Field validation messages → [`forms`](../forms/SKILL.md)
- Crash-reporter setup, mapping upload → [`mobile-shared-observability`](../../../_shared/observability/SKILL.md)
- Other stacks → `mobile-react-native-error-handling`, `mobile-ios-error-handling`

## The failure surfaces

```
Programmer error (NPE, !!, index)   → prevented: no !!, no unchecked index, no lateinit read before set
Fetch FAILED / never answers        → ApiError → LoadState.Failed (timeout is its own body)
SESSION expired (401)               → refresh → replay → re-auth in place (dialog / biometric)
Server REJECTS this app version     → forced-update screen, one action
PROCESS KILLED / app backgrounded   → restore small state, reload the rest; offline ≠ server error
Write interrupted                   → indeterminate outcome, reconcile
```

Compose has **no error boundary**: an exception thrown in composition crashes the process. Every `suspend` call in a ViewModel sits in a `try` / `Result` that lands in `LoadState`, and a composable never throws for a recoverable condition. **Rethrow `CancellationException`** — leaving a screen is not a failure ([`networking`](../networking/SKILL.md)).

## Data regions — loading / loaded / failed, plus stale and offline

```kotlin
sealed interface LoadState<out T> {
    data object Loading : LoadState<Nothing>
    data class Loaded<T>(val value: T) : LoadState<T>
    data class Failed(val error: ApiError) : LoadState<Nothing>
    data class Stale<T>(val value: T, val error: ApiError, val asOf: Instant) : LoadState<T>
}
```

```kotlin
@Composable
fun OrdersRegion(
    state: LoadState<List<Order>>,
    isOnline: Boolean,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    when (state) {
        LoadState.Loading -> CircularProgressIndicator(modifier.testTag("Orders.Loading"))
        is LoadState.Failed -> RegionFailure(state.error, isOffline = !isOnline, onRetry, modifier.testTag("Orders.Error"))
        is LoadState.Loaded -> OrdersList(state.value, modifier)
        is LoadState.Stale -> Column(modifier) {
            StaleMarker(state.asOf, onRetry, Modifier.testTag("Orders.Stale"))
            OrdersList(state.value)
        }
    }
}
```

- **A response the app can't read is a failure, not an empty list.** `ApiError.Drifted` lands in `Failed` — never `runCatching { … }.getOrDefault(emptyList())`.
- **Render only a friendly message and the correlation id**, from a `when` over `ApiError` to string resources; never `Throwable.message`, a stack or a body.
- **Offline is its own body** ("You're offline — showing what we have"), driven by `Connectivity`, not by a failed request. Offline with cached data is `Stale`, not `Failed`; no retry control spins while offline — reconnect refetches.
- **Stale (refetch failed, data held)**: keep the rows, show their age ("as of 14:02"), keep the retry, notify once. **A failed pull-to-refresh keeps the list and becomes `Stale`** — it never swaps the list for the failed body. Disable actions unsafe on stale data (a price, a balance) with the reason shown.
- **Timeout renders its own body** — "This is taking longer than expected", retry leading — with a soft "still loading…" tier at about 6 s inside the budget. `TimedOut` is a failure; `CancellationException` is **not**: no state change, no banner.
- **Gone, not broken.** `NotFound` on a record renders "This order no longer exists" with a way back and removes actions bound to it; never a retry button.
- **Empty is three states**: no records yet (offer *create*), no filter yet (focus the filter), filter matched nothing (offer *clear filters*) — each in the data area, each with a test-tag suffix.

### Scope the failure to the response-dependent subtree

The failure replaces only the part that needs the response. A `LazyColumn` whose search and filters sit in its header loses them to an early `if (state is Failed) { Error(); return }` at the top of the screen; render the chrome unconditionally and put the `when` where the rows go.

```kotlin
@Composable
fun OrdersScreen(state: OrdersUiState, actions: OrdersActions) {
    PullToRefreshBox(isRefreshing = state.isRefreshing, onRefresh = actions::refresh) {
        LazyColumn(Modifier.testTag("Orders.List")) {
            stickyHeader(key = "filters") {
                OrdersSearchAndFilters(state.query, actions::onQueryChange)
            }
            item(key = "region", contentType = "region") {
                OrdersRegion(state.load, state.isOnline, actions::refresh)
            }
        }
    }
}
```

Filter state lives in the ViewModel's `SavedStateHandle` above the failing region, so "fix the filter and retry" works; independent tiles are independent `LoadState`s; a failed body is never identical to the empty one. When the loaded region is itself the `items(…)`, the failed / empty slot replaces those items, not the header.

## The error banner — persistent, safe-area, user-dismissed

The inline region says *this data is missing*; the banner says *why, and how to report it*. Both, always.

| Property | Value |
|---|---|
| Position | **Top-anchored inside the safe area** — a root `Box` overlay with `Modifier.windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Top + WindowInsetsSides.Horizontal))`, below the status bar and display cutout, clear of a translucent app bar; above content, below dialogs; never under the IME |
| Dismissal | **A close control only**, ≥ 48 × 48 dp; **no auto-dismiss for an error**, ever — which rules out `Snackbar` with a duration for errors (`SnackbarDuration.Indefinite` still sits at the bottom and under the IME) |
| Content | Friendly message + copyable correlation id + optional retry |
| Semantics | A polite live region, announced on appearance; focus is not stolen from the field ([`accessibility`](../accessibility/SKILL.md)) |
| Dedupe | Key `correlationId ?: code + region`; a repeat updates the entry with a count |
| Host | One `NotificationsHost` (a Hilt singleton holding `StateFlow<List<Banner>>`) rendered once at the root; features raise through it and never mount their own. It is **state, not an event stream** — the banner stays until closed ([`architecture`](../architecture/SKILL.md)) |
| Ids | `Notifications.Banner`, `Notifications.Banner.Close`, `Notifications.Banner.CorrelationId` |

Raise it from **one place per failure path** — the repository or ViewModel that owns the load, a mutation's `catch`, the forced-update gate — never at the call site *and* globally. A phone fits one or two banners, so:

1. **Cap the stack at 3**; the rest collapse into "+N more issues".
2. **Roll up by cause, not by call** — six regions on one 503 is one message; the inline regions say which.
3. **Let the retry circuit quiet it** — after *k* consecutive failures a region stops auto-retrying and stops re-notifying; one entry with a count.

**No banner** for field validation, an expected empty result, a cancelled request, a failure absorbed by retry, or a failed analytics call.

## Situational surfaces — read the file when it applies

| Situation | Where |
|---|---|
| **401 mid-session** — refresh → replay → biometric / dialog re-auth; 403 is not 401 | [`references/session-and-resume.md`](references/session-and-resume.md) |
| **Version skew** — the server's minimum version, the forced-update screen; a degraded API contract | [`references/session-and-resume.md`](references/session-and-resume.md) |
| **App resume** — lifecycle + reconnect revalidate; stale-open-app | [`references/session-and-resume.md`](references/session-and-resume.md) |
| **Process death** — what `SavedStateHandle` restores, what reloads, what renders stale | [`references/session-and-resume.md`](references/session-and-resume.md) |
| **A write fails** — double submit, idempotency, rollback, 409, 422, bulk, indeterminate after background | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |
| **A third party fails** — maps, payments, push, analytics, an SDK that throws at launch | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |
| **Storage is full** — typed write failure, memory fallback, one notice | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |

## Rules

- Every thrown error is caught where it is thrown and becomes state; `CancellationException` is rethrown; no `!!`, no `error()` for a recoverable condition.
- Regions are one sealed `LoadState` with failed, stale and offline; a drifted response is *failed*; a failed refetch keeps the data and shows the stale marker.
- Scope the failure to the response-dependent subtree; chrome and filter state survive.
- Every surfaced failure also raises the persistent banner — safe-area top, no auto-dismiss, 48 dp close, deduped, one host, one raise-point per path, ≤ 3 visible, rolled up by cause.
- `TimedOut` has its own body; cancellation renders nothing; offline is not a server error and never retries.
- A `401` runs the ladder with in-place re-auth; `403` is permission-denied; an unsupported app version shows the forced-update screen.
- A killed process restores small state and reloads the rest; a restored region renders stale until it revalidates.
- An unknown write outcome is reconciled, not reported as failed; third parties fail in their own region; storage failures degrade to memory with one notice.
- `NotFound` on a record is "gone"; empty is three kinds; every state and the banner carry a `testTag`.

## What NOT to do

- No two-state region; no failure only inline or only in a banner; no `catch { }` that leaves the region empty.
- No early return from a screen that owns search and filters; no failed body over data the user is reading.
- No auto-dismissing banner or error `Snackbar`, none behind the cutout or the IME, none with a close target under 48 dp; no banner per retry, none uncapped.
- No request without a deadline; no failed state for a cancelled request; no retry button while offline.
- No sign-out straight off a `401` or from a `403` / third-party `401`; no blocking update screen for a version the server still supports.
- No ViewModel `SharedFlow` / `Channel` of error events — the banner is state.
- No generic "No data"; no retry on a `NotFound` record; no `Throwable.message` on screen.

## Generation steps

1. Read the existing `LoadState` / `ApiError`, banner host, `Connectivity` and crash reporter; match them.
2. Give each region one `LoadState` and one body bound where its rows render; keep chrome outside it.
3. Mount the `NotificationsHost` at the root and raise from the owning repository or ViewModel only; add the ladder, resume, restore and forced-update gate from the references; tag every state.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Fail the list load with search and filters filled → both stay interactive; only the rows carry the error; the banner sits below the status bar and cutout until its close control is pressed.
- Fail a pull-to-refresh after a load → rows remain, stale marker with an age, one banner.
- Airplane mode → offline or stale, never "failed", no retry attempts; emulator network at 100 % loss → the timeout body at the deadline.
- `adb shell am kill <package>` from the home screen, then reopen → the filter and the open record are back, the data reloads, no blank screen.
- Return from background after an expired token → one refresh, the screen current or the dialog shown, not a wall of failed regions.
- Dev-side tests of the state transitions: [`unit-testing`](../unit-testing/SKILL.md); device journeys → `qa-mobile-android` (peer).

## Handoffs

- The categorised error, timeouts, retries, token refresh → [`networking`](../networking/SKILL.md)
- Persistence and the write queue → [`offline-and-storage`](../offline-and-storage/SKILL.md) · field errors → [`forms`](../forms/SKILL.md)
- Ids → [`test-ids`](../test-ids/SKILL.md) · announcements → [`accessibility`](../accessibility/SKILL.md)
- Crash reporter, mapping upload → [`mobile-shared-observability`](../../../_shared/observability/SKILL.md) · min-version policy → [`mobile-shared-release`](../../../_shared/release/SKILL.md)
- Auth provider / Credential Manager → `auth-auth0-android`
