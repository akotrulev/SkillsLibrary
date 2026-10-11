---
name: error-handling
description: Use when a failure must not blank a SwiftUI screen — loading/loaded/failed/stale/offline regions, failure scoped below search and filters, the safe-area error banner, timeouts rendered, 401 re-auth in place, forced update on version skew, scenePhase resume, write failures, third-party failures, full-disk degradation. Triggers "list empty when API fails", "session expired mid-form". Do NOT use for producing the APIError or retries (`mobile-ios:networking`).
---

# iOS — Error Resilience

Owns **failing safely and recovering**: **rendering** failure, staleness and offline so a broken region never looks like an empty one, and recovering in place from a dead session, a version the server no longer supports, a backgrounded write or a full disk. Web analog: [`fe-react:error-handling`](../../../../frontend/react/skills/error-handling/SKILL.md) — every rule carries over with the mobile delta below; `error.tsx`, hydration, multi-tab and chunk-load errors do not exist here. Sibling: [`mobile-react-native:error-handling`](../../../react-native/skills/error-handling/SKILL.md) (the same deltas; OTA skew is RN-only).

Division of labour with [`networking`](../networking/SKILL.md): it **produces** the categorised `APIError` (kind, status, correlation id, `retryAfter`, retryable — `networking/references/request-policy.md`), applies the timeout budget and bounded retries. This skill **renders** it.

## Version lane

| Concern | Primary (Swift 6.2+, iOS 17+) | Notes |
|---|---|---|
| Region state | A `LoadState<Value>` enum in an `@Observable` model or `@State` | One enum, not four booleans |
| Failed / empty body | `ContentUnavailableView` (iOS 17+) | `[iOS16]` a plain `VStack` with the same content |
| Pull to refresh | `.refreshable { }` | The canonical refetch |
| Resume | `@Environment(\.scenePhase)` + `.onChange(of:)` | `[UIKit]` `UIScene` notifications / `sceneDidBecomeActive` |
| Offline signal | `NWPathMonitor` (`networking`'s `Connectivity`) | Never a ping |
| Crash reporting | One reporter + MetricKit — [`mobile-<stack>:observability`](../../../_shared/observability/SKILL.md) | A Swift trap (`try!`, `!`, array bounds) is **not catchable** — prevent it |
| Forced update | Server minimum version → blocking screen (MASVS-CODE-2) | [`references/session-and-resume.md`](references/session-and-resume.md) |

Detect first: the existing banner or toast host, the `LoadState` / `AppError` types, the wired crash reporter — extend them, never add a second.

## When to use

- Rendering a region's loading / loaded / failed / stale / offline states and the three empty kinds
- The persistent banner, a timeout, a 401 mid-session, a forced update, app resume, a failed write or SDK, a full disk

## When NOT to use

- Producing the error, retries, `Retry-After`, token-refresh mechanics → [`networking`](../networking/SKILL.md)
- Persisting data, the write queue, conflicts → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Field validation messages → [`forms`](../forms/SKILL.md)
- Crash-reporter setup, symbols → [`mobile-<stack>:observability`](../../../_shared/observability/SKILL.md)
- Other stacks → `mobile-react-native:error-handling`, `mobile-android:error-handling`

## The failure surfaces

```
Programmer error (trap)           → prevented: no try!, no force unwrap, no unchecked index
Fetch FAILED / never answers      → APIError → LoadState.failed (timeout is its own body)
SESSION expired (401)             → refresh → replay → re-auth in place (sheet)
Server REJECTS this app version   → forced-update screen, one action
App BACKGROUNDED / device OFFLINE → scenePhase resume revalidates; offline ≠ server error
Write interrupted                 → indeterminate outcome, reconcile
```

SwiftUI has **no error boundary**: a thrown error is caught where it is thrown and becomes state. Every `async throws` call in a view or model sits in a `do`/`catch` that lands in a `LoadState`; the view never lets an error escape `body`.

## Data regions — loading / loaded / failed, plus stale and offline

```swift
enum LoadState<Value: Sendable>: Sendable {
    case loading
    case loaded(Value)
    case failed(AppError)
    case stale(Value, AppError, asOf: Date)
}
```

```swift
struct OrdersRegion: View {
    let state: LoadState<[Order]>
    let isOnline: Bool
    let retry: () async -> Void

    var body: some View {
        switch state {
        case .loading:
            ProgressView().accessibilityIdentifier("Orders.Loading")
        case .failed(let error):
            RegionFailure(error: error, isOffline: !isOnline, retry: retry)
                .accessibilityIdentifier("Orders.Error")
        case .loaded(let rows):
            OrdersList(rows: rows)
        case .stale(let rows, _, let asOf):
            OrdersList(rows: rows).safeAreaInset(edge: .top) {
                StaleMarker(asOf: asOf, retry: retry).accessibilityIdentifier("Orders.Stale")
            }
        }
    }
}
```

- **A response the app can't read is a failure, not an empty list.** A drifted body throws `APIError.drifted` (`networking`) and lands in `.failed` — never `try?` into `[]`.
- **Render only a friendly message and the correlation id.** `AppError(error)` maps any thrown value to a generic one; the UI never prints `localizedDescription`, a stack or a body.
- **Offline is its own body** ("You're offline — showing what we have"), driven by `Connectivity`, not by a failed request. Offline with cached data is `.stale`, not `.failed`; no retry control spins while offline — reconnect refetches.
- **Stale (refetch failed, data held)**: keep the rows, show their age ("as of 14:02"), keep the retry, notify once. **A failed pull-to-refresh keeps the list and becomes `.stale`** — it never swaps the list for the failed body. Disable actions unsafe on stale data (a price, a balance) with the reason shown.
- **Timeout renders its own body** — "This is taking longer than expected", retry leading — with a soft "still loading…" tier at about 6 s inside the budget. `URLError.timedOut` is a failure; `CancellationError` / `URLError.cancelled` (the user left) is **not**: no state change, no banner.
- **Gone, not broken.** A `404` on a record renders "This order no longer exists" with a way back, removes actions bound to it, and the list reloads; never a retry button.
- **Empty is three states**: no records yet (offer *create*), no filter yet (focus the filter), filter matched nothing (offer *clear filters*) — each in the data area, each with an identifier suffix.

### Scope the failure to the response-dependent subtree

The failure replaces only the part that needs the response. A list whose search and filters sit above the rows loses them to an early `if case .failed = state { return … }` at the top of the screen; render the chrome unconditionally and put the `switch` where the rows go.

```swift
var body: some View {
    List {
        Section { OrdersSearchAndFilters(query: $query) }
        Section { OrdersRegion(state: model.state, isOnline: isOnline, retry: model.reload) }
    }
    .refreshable { await model.reload() }
    .accessibilityIdentifier("Orders.List")
}
```

Filter state lives above the failing region (in the model or the route), so "fix the filter and retry" works; independent tiles are independent `LoadState`s; a failed body is never identical to the empty one.

## The error banner — persistent, safe-area, user-dismissed

The inline region says *this data is missing*; the banner says *why, and how to report it*. Both, always.

| Property | Value |
|---|---|
| Position | **Top-anchored inside the safe area** — `.safeAreaInset(edge: .top)` on the root, below the status bar and Dynamic Island, clear of translucent bars; above content, below sheets; never under the keyboard |
| Dismissal | **A close control only**, ≥ 44 × 44 pt; **no auto-dismiss for an error**, ever |
| Content | Friendly message + copyable correlation id + optional retry — never `localizedDescription`, a stack or a body |
| Semantics | Announced with `AccessibilityNotification.Announcement(_:).post()` on appearance; focus is not stolen from the field |
| Dedupe | Key `correlationId ?? code + region`; a repeat updates the entry with a count |
| Host | One `@Observable` `Notifications` model injected through `@Environment` at the root; features never mount their own |
| Ids | `Notifications.Banner`, `Notifications.Banner.Close`, `Notifications.Banner.CorrelationId` |

Raise it from **one place per failure path** — the model that owns the load, a mutation's `catch`, the forced-update gate — never at the call site *and* globally. A phone fits one or two banners, so:

1. **Cap the stack at 3**; the rest collapse into "+N more issues".
2. **Roll up by cause, not by call** — six regions on one 503 is one message; the inline regions say which.
3. **Let the retry circuit quiet it** — after *k* consecutive failures a region stops auto-retrying and stops re-notifying; one entry with a count.

**No banner** for field validation, an expected empty result, a cancelled request, a failure absorbed by retry, or a failed analytics call.

## Situational surfaces — read the file when it applies

| Situation | Where |
|---|---|
| **401 mid-session** — refresh → replay → biometric / sheet re-auth; 403 is not 401 | [`references/session-and-resume.md`](references/session-and-resume.md) |
| **Version skew** — the server's minimum version, the forced-update screen; a degraded API contract | [`references/session-and-resume.md`](references/session-and-resume.md) |
| **App resume** — `scenePhase` + reconnect revalidate; stale-open-app | [`references/session-and-resume.md`](references/session-and-resume.md) |
| **A write fails** — double submit, idempotency, rollback, 409, 422, bulk, indeterminate after background | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |
| **A third party fails** — maps, payments, push, analytics, a framework that fails to load | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |
| **Storage is full** — typed write failure, memory fallback, one notice | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |

## Rules

- Every thrown error is caught where it is thrown and becomes state; no `try!`, no force unwrap, no `fatalError` for a recoverable condition.
- Regions are one `LoadState` enum with failed, stale and offline; a drifted response is *failed*; a failed refetch keeps the data and shows the stale marker.
- Scope the failure to the response-dependent subtree; chrome and filter state survive.
- Every surfaced failure also raises the persistent banner — safe-area top, no auto-dismiss, 44 pt close, deduped, one host, one raise-point per path, ≤ 3 visible, rolled up by cause.
- `timedOut` has its own body; cancellation renders nothing; offline is not a server error and never retries.
- A 401 runs the ladder with in-place re-auth; 403 is permission-denied; an unsupported app version shows the forced-update screen.
- An unknown write outcome is reconciled, not reported as failed; third parties fail in their own region; storage failures degrade to memory with one notice.
- 404 on a record is "gone"; empty is three kinds; every state and the banner carry an `accessibilityIdentifier`.

## What NOT to do

- No two-state region; no failure only inline or only in a banner; no `catch { }` that leaves the region empty.
- No early return from a screen that owns search and filters; no failed body over data the user is reading.
- No auto-dismissing banner, none behind the Dynamic Island or keyboard, none with a close target under 44 pt; no banner per retry, none uncapped.
- No request without a deadline; no failed state for a cancelled request; no retry button while offline.
- No sign-out straight off a 401 or from a 403 / third-party 401; no blocking update screen for a version the server still supports.
- No generic "No data"; no retry on a 404 record; no `localizedDescription` on screen.

## Generation steps

1. Read the existing `LoadState` / `AppError`, banner host, `Connectivity` and crash reporter; match them.
2. Give each region one `LoadState` and one body bound where its rows render; keep chrome outside it.
3. Mount the `Notifications` host at the root and raise from the owning model only; add the ladder, resume and forced-update gate from the references; tag every state.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Fail the list load with search and filters filled → both stay interactive; only the rows carry the error; the banner sits below the Dynamic Island until its close control is pressed.
- Fail a pull-to-refresh after a load → rows remain, stale marker with an age, one banner.
- Airplane mode → offline or stale, never "failed", no retry attempts; hang the endpoint (Network Link Conditioner, 100% loss) → the timeout body at the deadline.
- Return from background after an expired token → one refresh, the screen current or the sheet shown, not a wall of failed regions.
- Dev-side tests of the state transitions: [`unit-testing`](../unit-testing/SKILL.md); device journeys → `qa-mobile-<stack>` (peer).

## Handoffs

- The categorised error, timeouts, retries, token refresh → [`networking`](../networking/SKILL.md)
- Persistence and the write queue → [`offline-and-storage`](../offline-and-storage/SKILL.md) · field errors → [`forms`](../forms/SKILL.md)
- Ids → [`test-ids`](../test-ids/SKILL.md) · announcements → [`accessibility`](../accessibility/SKILL.md)
- Crash reporter, symbols → [`mobile-<stack>:observability`](../../../_shared/observability/SKILL.md) · min-version policy → [`mobile-<stack>:release`](../../../_shared/release/SKILL.md)
- Auth provider / credentials manager → `mobile-ios:auth0`
