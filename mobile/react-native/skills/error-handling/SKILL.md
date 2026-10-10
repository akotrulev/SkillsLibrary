---
name: mobile-react-native-error-handling
description: Use when a failure must not blank an Expo SDK 57 screen — expo-router ErrorBoundary, loading/loaded/failed/stale/offline regions, the safe-area error banner, timeouts rendered, 401 re-auth in place, OTA-update skew, app resume, mutation and third-party failures, storage-full degradation. Triggers "app goes white on error", "list empty when API fails", "session expired mid-form". Do NOT use for producing the AppError or retries (`mobile-react-native-networking`).
---

# React Native — Error Resilience

Owns **failing safely and recovering** on a phone: catching render exceptions before the screen goes white, **rendering** failure, staleness and offline correctly so a broken region never looks like an empty one, and recovering in place from a dead session, a stale OTA bundle, a backgrounded write or a full disk. Web analog: [`fe-react-error-handling`](../../../../frontend/react/skills/error-handling/SKILL.md) — every rule carries over with the mobile delta below; `error.tsx`, `global-error.tsx`, hydration, multi-tab and `ChunkLoadError` do not exist here.

Division of labour with [`networking`](../networking/SKILL.md): it **produces** the categorised `AppError` (`kind`, `status`, `correlationId`, `retryAfterMs`, `retryable` — `networking/references/request-policy.md`), applies the timeout budget and bounded retries. This skill **renders** it. Two skills, one seam.

## Version lane

| Concern | Primary (SDK 57 · RN 0.86) | Notes |
|---|---|---|
| Route boundary | `export function ErrorBoundary({ error, retry })` from a route or layout file | `expo-router` renders it in place of that route; `retry` re-renders the route |
| Region boundary | `react-error-boundary` | Works unchanged in RN |
| Root reporting | `reportError` / `ErrorUtils.setGlobalHandler` → the crash reporter | One reporter — [`mobile-shared-observability`](../../../_shared/observability/SKILL.md); `expo-observe`'s `ObserveErrorBoundary` is **preview** (JS only, no native crashes) |
| OTA | `expo-updates` — `useUpdates()`, `Updates.reloadAsync()` | Not in Expo Go; skew detail in [`references/session-and-resume.md`](references/session-and-resume.md) |
| Offline signal | TanStack Query `onlineManager` (NetInfo) | Mounted by `networking` |
| `[SDK58]` | no change to these rules | Router core is reworked — re-read the `ErrorBoundary` export docs on upgrade |
| Floor 54 | same | Detect `expo-updates` before using its hook |

Detect first: `expo-updates`, the wired crash reporter, TanStack Query, and any existing banner or toast provider — extend it, never add a second.

## When to use

- Placing boundaries; rendering a region's loading / loaded / failed / stale / offline states and empty kinds
- The persistent banner, a timeout, a 401 mid-session, OTA skew, app resume, a failed write or SDK, a full disk

## When NOT to use

- Producing the error, retries, `Retry-After`, token refresh mechanics → [`networking`](../networking/SKILL.md)
- Persisting data, the mutation queue, conflicts → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Field validation messages → [`forms`](../forms/SKILL.md)
- Crash-reporter setup, symbols → [`mobile-shared-observability`](../../../_shared/observability/SKILL.md)
- Native Swift / Kotlin → `mobile-ios-error-handling` / `mobile-android-error-handling`

## The failure surfaces

```
Render EXCEPTION                   → ErrorBoundary (route export, region boundary)
Fetch FAILED / never answers       → AppError → region state (timeout is its own body)
SESSION expired (401)              → refresh → replay → re-auth in place (modal)
OTA update changed the JS bundle   → detect, prompt, one guarded reload
App BACKGROUNDED / device OFFLINE  → resume revalidates; offline told apart from a server error
Write interrupted                  → indeterminate outcome, reconcile
```

A boundary does not recover a failed fetch, and **no state machine saves a request with no deadline** — that is fixed at the transport (`networking`).

## Error boundaries — the route export, then the region

An exception during render unmounts up to the nearest boundary; with none, the app is a white or red screen.

```tsx
import { type ErrorBoundaryProps } from 'expo-router';
import { Pressable, Text, View } from 'react-native';
import { reportError } from '@/lib/reporting';

export function ErrorBoundary({ error, retry }: ErrorBoundaryProps) {
  const reference = reportError(error);
  return (
    <View accessibilityRole="alert" testID="Orders.Error">
      <Text>We couldn’t show this screen.</Text>
      <Text>Ref: {reference}</Text>
      <Pressable accessibilityRole="button" onPress={retry} testID="Orders.Retry">
        <Text>Try again</Text>
      </Pressable>
    </View>
  );
}
```

1. **Root layout** — export `ErrorBoundary` from `app/_layout.tsx`: the backstop for every route without its own.
2. **Per route** — export it from the route file that can fail independently; it replaces only that route.
3. **Per region** — below the route, wrap an independently failing widget (a map, a chart, a feed card) in `react-error-boundary`'s `<ErrorBoundary FallbackComponent onError={report} resetKeys>`.

Rules for every boundary: report with context and a correlation id (`reportError` returns it); **never render `error.message` or a stack** — friendly text plus the reference; always a real recovery action; the fallback carries `testID`s. Boundaries **do not** catch event handlers, effects, timers or rejected promises — those go through `try/catch` into the region states below, and `ErrorUtils` / the crash reporter catches the rest.

## Data regions — loading / loaded / failed, plus stale and offline

Every region has **three** states, then a fourth once it holds data, and offline is told apart from a server error. A `catch {}` that leaves a region empty makes an outage look like "no data".

```tsx
function OrdersRegion({ search, filters }: { search: string; filters: Filters }) {
  const query = useOrders(search, filters);
  const online = useOnlineStatus();

  if (query.isPending) return <RegionSkeleton testID="Orders.Loading" />;
  if (query.isError && query.data === undefined) {
    return <RegionFailure error={toAppError(query.error)} offline={!online} onRetry={query.refetch} testID="Orders.Error" />;
  }
  return (
    <>
      {query.isError ? <StaleMarker asOf={query.dataUpdatedAt} onRetry={query.refetch} testID="Orders.Stale" /> : null}
      <OrdersList rows={query.data} refreshing={query.isRefetching} onRefresh={query.refetch} />
    </>
  );
}
```

- **A response the app can't read is a failure, not an empty list.** A drifted body fails the Zod parse (`networking`) and lands in the failed state — never `data = []`.
- **Render only `{ message, correlationId }`.** `toAppError` maps an unknown thrown value to a generic `AppError`; the UI never prints the exception.
- **Offline is its own body** ("You're offline — showing what we have"), driven by `onlineManager`, not by a failed request. Offline with cached data is *stale*, not failed. No retry button spins while offline — it waits for reconnect, which refetches.
- **Stale (refetch failed, data held):** keep the rows, mark them with their age ("as of 14:02"), keep the retry, notify once. **Pull-to-refresh is the canonical refetch**; a failed pull keeps the list and shows the stale marker — it never swaps the list for the failed body. Disable actions that are unsafe on stale data (a price, a balance, availability) with the reason shown.
- `placeholderData: keepPreviousData` on filter and page changes; a new key's first load is *loading*, not stale.
- **Timeout** renders its own body: "This is taking longer than expected" with retry leading, and a soft "still loading…" tier at about 6 s inside the budget. `TimeoutError` is a failure; `AbortError` (the user left the screen) is not — no failed state, no banner.
- **Gone, not broken.** A `404` on a record renders "This order no longer exists" with a way back, removes actions bound to it, and the list invalidates on delete. Never a retry button.
- **Empty is three states**: no records yet (offer *create*), no filter yet (focus the filter), filter matched nothing (offer *clear filters*) — each in the data area, each with its own `testID` suffix.

### Scope the failure to the response-dependent subtree

The failure replaces only the part that needs the response. A list whose header holds search and filters loses them to an early `return <Error/>`; render the chrome unconditionally and put the state branch where the rows go.

```tsx
<FlashList
  data={query.data ?? []}
  ListHeaderComponent={<OrdersSearchAndFilters value={filters} onChange={setFilters} />}
  ListEmptyComponent={<OrdersListBody state={state} error={error} onRetry={query.refetch} />}
  renderItem={renderOrder}
  testID="Orders.List"
/>
```

Filter state lives above the failing region (or in route params), so "fix the filter and retry" works; independent tiles are independent states; a failed body is never identical to the empty one.

## The error banner — persistent, safe-area, user-dismissed

The inline region says *this data is missing*; the banner says *why, and how to report it*. Both, always.

| Property | Value |
|---|---|
| Position | **top-anchored inside the safe area** — below the status bar, notch and translucent header; one stack, above content, below modals; never under the keyboard |
| Dismissal | **close control only**, ≥ 44 pt × 44 pt; **no auto-dismiss for an error**, ever |
| Content | friendly message + correlation id (copyable) + optional retry — never `error.message`, a stack or a body |
| Semantics | `accessibilityRole="alert"`, `accessibilityLiveRegion="assertive"` (Android), announced with `AccessibilityInfo.announceForAccessibility` (iOS); focus is not stolen from the field |
| Dedupe | key `correlationId ?? code + region`; a repeat updates the entry with a count |
| Mount | one provider at the root layout, read through one hook; features never mount their own |
| Ids | `Notifications.Banner`, `Notifications.Banner.Close`, `Notifications.Banner.CorrelationId` |

The banner container is positioned with `useSafeAreaInsets().top` and renders at most three entries.

Raise it from **one place per failure path** — `QueryCache.onError` / `MutationCache.onError`, a boundary's `onError`, or the OTA prompt — never at the call site *and* globally (double fire). A phone fits one or two banners, so:

1. **Cap the stack at 3**; the rest collapse into "+N more issues".
2. **Roll up by cause, not by call** — six regions on one 503 is one message; the inline regions say which.
3. **Let the retry circuit quiet it** — after *k* consecutive failures a region stops auto-retrying and stops re-notifying; one entry with a count.

**No banner** for field validation, an expected empty result, an aborted request, a failure absorbed by retry, or a failed analytics call.

## Situational surfaces — read the file when it applies

| Situation | Where |
|---|---|
| **401 mid-session** — refresh → replay → biometric / in-place re-auth; 403 is not 401 | [`references/session-and-resume.md`](references/session-and-resume.md) |
| **OTA update skew** — detect, prompt, one guarded `Updates.reloadAsync()`; forced-update note for native | [`references/session-and-resume.md`](references/session-and-resume.md) |
| **App resume** — foreground + reconnect revalidate; stale-open-app | [`references/session-and-resume.md`](references/session-and-resume.md) |
| **A write fails** — double submit, idempotency, rollback, 409, 422, bulk, indeterminate after background | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |
| **A third party fails** — maps, payments, push, analytics, a native module that won't link | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |
| **Storage is full** — write fails typed, memory fallback, one notice | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |

## Rules

- Root `ErrorBoundary` export, one per independently failing route, `react-error-boundary` per independent widget; each reports a reference id and offers retry. Never render `error.message`, a stack or a body.
- Three-state regions plus stale and offline; a drifted response is *failed*; a failed refetch keeps the data and shows the stale marker.
- Scope the failure to the response-dependent subtree; chrome and filter state survive.
- Every surfaced failure also raises the persistent banner — safe-area top, no auto-dismiss, 44 pt close, deduped, one provider, one raise-point per path, ≤ 3 visible, rolled up by cause.
- `TimeoutError` has its own body; `AbortError` renders nothing; offline is not a server error and never retries.
- A 401 runs the ladder with in-place re-auth; 403 is permission-denied. OTA skew prompts and reloads once, never over unsaved work.
- An unknown write outcome is reconciled, not reported as failed; third parties fail in their own boundary; storage failures degrade to memory with one notice.
- 404 on a record is "gone"; empty is three kinds; every state and the banner carry a `testID`.

## What NOT to do

- No app without a root `ErrorBoundary`; no console-only report; no two-state region; no failure only inline or only in a banner.
- No early `return <Error/>` from a container that owns search and filters; no failed body over data the user is reading.
- No auto-dismissing banner, none behind the notch or keyboard, none with a close target under 44 pt; no banner per retry, none uncapped.
- No request without a deadline; no failed state for `AbortError`; no retry button while offline.
- No unguarded `Updates.reloadAsync()`; no sign-out straight off a 401 or from a 403 / third-party 401.
- No generic "No data"; no retry on a 404 record.

## Generation steps

1. Read the existing boundaries, banner or toast provider, query config and crash reporter; match them.
2. Add the root and route `ErrorBoundary` exports and region boundaries; build the region body once and bind it where rows render.
3. Mount the banner at the root, raise from `QueryCache` / `MutationCache` `onError` only; add the ladder, resume and OTA prompt from the references; tag every state.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Throw in a region → its boundary shows friendly content with a reference; the rest of the screen works; no `error.message` on screen.
- Fail the list query with search and filters filled → both stay interactive; only the rows carry the error; the banner sits below the notch until its close control is pressed.
- Fail a pull-to-refresh after a load → rows remain, stale marker with an age, one banner.
- Airplane mode → offline or stale, never "failed", no retry attempts; hang the endpoint → the timeout body at the deadline.
- Dev-side tests: [`component-testing`](../component-testing/SKILL.md); device journeys → `qa-mobile-typescript` (peer).

## Handoffs

- The categorised error, timeouts, retries, token refresh → [`networking`](../networking/SKILL.md)
- Persistence and the mutation queue → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Field errors → [`forms`](../forms/SKILL.md) · list slots → [`ui-components`](../ui-components/SKILL.md)
- Ids → [`test-ids`](../test-ids/SKILL.md) · roles, announcements → [`accessibility`](../accessibility/SKILL.md)
- Crash reporter, symbols → [`mobile-shared-observability`](../../../_shared/observability/SKILL.md) · OTA release channels → `mobile-shared-release`
- Auth provider / credentials manager → `auth0-react-native`
