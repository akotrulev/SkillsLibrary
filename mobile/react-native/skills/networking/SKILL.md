---
name: networking
description: Use when an Expo SDK 57 app must call an API — fetch + TanStack Query 5, focusManager on AppState, onlineManager on NetInfo, AbortSignal timeout budgets, bounded retries with Retry-After, no retry offline, ProblemDetails, token refresh, WebSocket / SSE paused on background. Triggers "request hangs on cell", "retry storm", "refresh token race". Do NOT use for the failure UI (`mobile-react-native:error-handling`), forms, or persisted caches (`-offline-and-storage`).
---

# React Native — Networking

Owns the **request-level half** of resilience: how a call is made, cancelled, timed out, retried, authenticated, and categorised, and how realtime connections live and die with the app. The **UI half** (failed region, banner, stale marker, retry button) is [`error-handling`](../error-handling/SKILL.md)'s; this skill produces the categorised error it renders. Web analog: [`fe-react:data-fetching`](../../../../frontend/react/skills/data-fetching/SKILL.md) — the timeout, ordering and critical-vs-optional rules carry over; RSC, Server Actions and `revalidateTag` do not.

## Version lane

| Concern | Primary (SDK 57 · RN 0.86) | Notes |
|---|---|---|
| Transport | global `fetch` (WHATWG, Hermes) | `expo/fetch` for streaming bodies and SSE; no Axios needed |
| `AbortSignal.timeout` / `AbortSignal.any` | available on RN 0.86 / Hermes V1 | Detect before use on a lower lane; the fallback is an `AbortController` + timer that is cleared on settle |
| TanStack Query | 5 | `focusManager` ← `AppState`; `onlineManager` ← NetInfo or `expo-network` |
| Reachability | `@react-native-community/netinfo` or `expo-network` | Pick the one already installed |
| `[SDK58]` | no networking change | Same rules |
| Floor SDK 54 | `AbortSignal.timeout` present on Hermes; verify | Same recipes |

Detect `@tanstack/react-query` major and whether a client (`ky`, Axios, a generated SDK) already exists — match it; do not add a second HTTP layer.

## When to use

- Writing the API client, a query or mutation hook, an upload
- A request hangs on a bad cell link; a retry storm; a duplicate write
- Token attach, 401 refresh, replay
- Refetch on foreground and on reconnect
- A WebSocket or SSE connection that must pause in the background

## When NOT to use

- Rendering failure, the banner, offline indicator, OTA-skew prompt → [`error-handling`](../error-handling/SKILL.md)
- Persisting the cache, the offline mutation queue, sync and conflicts → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Where server vs client state lives → [`architecture`](../architecture/SKILL.md)
- Form submit UX and `setError` → [`forms`](../forms/SKILL.md)
- Auth provider setup → `auth0-react-native`; token storage → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Push registration with the server → [`notifications-and-links`](../notifications-and-links/SKILL.md)
- Next.js fetch / caching → `fe-react:data-fetching`

## The client — one module, one place for the budget

```ts
import { getAccessToken, refreshAccessToken } from '@/features/auth/tokens';
import { AppError, problemError } from '@/lib/appError';

const TIMEOUT_MS = { read: 15_000, write: 30_000, upload: 120_000 } as const;
type EndpointClass = keyof typeof TIMEOUT_MS;

type RequestOptions = { signal?: AbortSignal; endpointClass?: EndpointClass; idempotencyKey?: string };

export async function api<T>(
  path: string,
  init: RequestInit,
  { signal, endpointClass = 'read', idempotencyKey }: RequestOptions = {},
  schema: { parse: (value: unknown) => T },
): Promise<T> {
  const budget = AbortSignal.timeout(TIMEOUT_MS[endpointClass]);
  const combined = signal ? AbortSignal.any([signal, budget]) : budget;

  const response = await send(path, init, combined, idempotencyKey);
  if (!response.ok) throw await problemError(response);
  return schema.parse(await response.json());
}
```

- **The base URL is `process.env.EXPO_PUBLIC_API_URL`** — public by design; no secret travels in it. `https` only; a cleartext or ATS exception carries a recorded reason ([`mobile-<stack>:security`](../../../_shared/security/SKILL.md)).
- **Every call has a timeout budget by endpoint class** — a request on a dying cell link otherwise waits minutes. Budgets are longer than on web; set them in one table, not at call sites.
- **Compose, never replace**: `AbortSignal.any([queryClientSignal, AbortSignal.timeout(ms)])`. The caller's signal is TanStack's, so leaving the screen cancels the request.
- **`TimeoutError` is a failure** (render the timeout body); **`AbortError` is not** (the user left) — never notify on it.
- **Parse the response to the endpoint's real shape with Zod**; a parse failure throws a categorised `AppError`, never an empty array. A single-object endpoint is not read as a list.
- **Checked route map, no unsubstituted `{placeholder}`** — build URLs by name and assert none remain; a swallowed 404 becomes a silently empty dropdown.
- The request body, URL and token never go to `console.log`; log the status, endpoint class and correlation id.

The categorised error, token attach, refresh queue and the retry policy in code are in [`references/request-policy.md`](references/request-policy.md).

## Retries — bounded, polite, never offline

| Situation | Rule |
|---|---|
| Idempotent read (`GET`) failing with network error, `408`, `429`, `502`, `503`, `504` | up to **2** retries, exponential backoff with jitter |
| `429` / `503` with `Retry-After` | wait **exactly that** (seconds or HTTP date), capped at a ceiling; do not retry sooner |
| Write (`POST` / `PATCH`) | retried **only** with an `Idempotency-Key` the server honours; otherwise never |
| `4xx` other than `408` / `429` | never retry; it is the caller's bug or the user's input |
| **Device offline** | **no retry at all** — queue or fail fast; retrying burns battery and data |
| Repeated failures on one endpoint | open a circuit: stop for a cool-down, then one probe; surface *failed*, not spinner |

TanStack's `retry` and `retryDelay` implement this once at the `QueryClient`; do not also retry inside `api()`:

```ts
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => error instanceof AppError && error.retryable && failureCount < 2,
      retryDelay: (attempt, error) =>
        error instanceof AppError && error.retryAfterMs !== undefined
          ? error.retryAfterMs
          : Math.min(1000 * 2 ** attempt, 30_000) + Math.random() * 500,
      networkMode: 'online',
    },
    mutations: { retry: false, networkMode: 'online' },
  },
});
```

Mutations never auto-retry from the query client; replay is the offline queue's decision ([`offline-and-storage`](../offline-and-storage/SKILL.md)).

## App focus and connectivity — React Native has no `window`

```tsx
import NetInfo from '@react-native-community/netinfo';
import { focusManager, onlineManager } from '@tanstack/react-query';
import { AppState, type AppStateStatus } from 'react-native';
import { useEffect } from 'react';

onlineManager.setEventListener((setOnline) =>
  NetInfo.addEventListener((state) => setOnline(state.isConnected === true && state.isInternetReachable !== false)),
);

export function useAppFocusRevalidation() {
  useEffect(() => {
    const subscription = AppState.addEventListener('change', (status: AppStateStatus) =>
      focusManager.setFocused(status === 'active'),
    );
    return () => subscription.remove();
  }, []);
}
```

Mount `useAppFocusRevalidation()` once in the root layout. Returning to the foreground then revalidates stale queries, and reconnecting refetches — **leave `refetchOnWindowFocus` and `refetchOnReconnect` on**; tune `staleTime` instead. A screen that is not focused (a lower stack entry) can be paused with `subscribed` from `useIsFocused`-style logic in navigation; do not poll behind it.

## Ordering and critical vs optional

- **Key every query by every parameter it depends on** (`['orders', search, filters, page]`) so a slow answer for a replaced query is discarded; a hand-rolled effect fetch has an abort in its cleanup.
- **Forward `signal`** from `queryFn: ({ signal }) => api(..., { signal })`.
- **Classify each call critical or optional**: `Promise.all` only for calls critical together, `allSettled` the moment one is optional; `enabled` gates a dependent query so it neither fires with `undefined` nor spins when its parent failed. Render partial success — the UI half is [`error-handling`](../error-handling/SKILL.md).
- **Pagination** with `useInfiniteQuery`; the list's `onEndReached` calls `fetchNextPage`; pull-to-refresh calls `refetch` ([`ui-components`](../ui-components/SKILL.md)).
- **Mutations** carry an idempotency key generated once per user intent (not per attempt), disable their control while pending, and invalidate precisely the keys they change.

## Realtime — WebSocket and SSE live with the app state

Pull is TanStack Query above; push is a socket the app opens **only while foregrounded and the screen needs it**.

- Open on `AppState` `active`, close on `background` — the OS suspends and kills idle sockets anyway; reconnect with jittered backoff and **revalidate the queries the stream feeds** (messages may have been missed).
- Reconnect only when `onlineManager.isOnline()`; no reconnect loop while offline.
- SSE uses `expo/fetch` streaming with an abort in cleanup; a WebSocket is created in an effect and closed in its cleanup — never in render, never one per list row.
- A push socket's payload is parsed with Zod like any response; a malformed frame is dropped and counted, not thrown into the render.
- Background delivery is push notifications ([`notifications-and-links`](../notifications-and-links/SKILL.md)), not a held-open socket.

## Rules

- One API module; base URL from `EXPO_PUBLIC_*` config; https only.
- A timeout budget on every call, per endpoint class; compose with the caller's signal; `TimeoutError` ≠ `AbortError`.
- Retries bounded (≤ 2 for reads), jittered, honour `Retry-After`; none for writes without an idempotency key; **none while offline**.
- `focusManager` on `AppState` and `onlineManager` on NetInfo, mounted once.
- Responses parsed with Zod; a parse failure is an error, never empty.
- Query keys carry every dependency; `signal` forwarded; dependent queries `enabled`-gated.
- 401 triggers one shared refresh, then replay once, then re-auth in place.
- Sockets and SSE closed on background and on unmount.
- No token, body or PII in logs.

## What NOT to do

- No request without a timeout; no `setTimeout`-vs-`fetch` race where `AbortSignal.timeout` fits; no timeout signal that replaces the caller's.
- No retry loop inside `api()` on top of the query client's; no retry while offline; no retry of a non-idempotent write.
- No `Retry-After` ignored; no fixed-interval retry without jitter.
- No `fetch` inside `useEffect` without an abort; no `.then()` that swallows an error into a blank region.
- No `Promise.all` spanning a critical and an optional call.
- No server data copied into Zustand ([`architecture`](../architecture/SKILL.md)).
- No secret in `EXPO_PUBLIC_*`; no hardcoded `localhost` or LAN URL in a release build.
- No socket opened in render or left open in the background.
- No second HTTP client beside the one the project has.

## Generation steps

1. Read the existing client, `QueryClient` config and auth module; detect Query major and reachability library.
2. Define the endpoint classes and budgets; write or extend `api()` and `AppError`.
3. Configure the `QueryClient` retry policy once; mount `onlineManager` and focus revalidation in the root layout.
4. Write the query / mutation hooks per feature, with full keys, `signal`, Zod parse and idempotency keys.
5. Add token attach and the single-flight refresh ([`references/request-policy.md`](references/request-policy.md)).
6. Realtime: open and close the socket with `AppState`; revalidate on reconnect.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Typecheck and lint with the project's scripts clean.
- On a device with the network throttled: a request past its budget rejects at the deadline with `TimeoutError`; leaving the screen aborts silently.
- Airplane mode: no retry attempts appear in the network log; reconnect refetches stale queries.
- A `503` with `Retry-After: 5` is retried after 5 s, not sooner; an expired access token causes exactly one refresh for N concurrent calls.
- Dev-side tests (fake `fetch`, fake timers): `mobile-react-native:component-testing`.

## Handoffs

- Failed region, banner, stale, OTA skew → [`error-handling`](../error-handling/SKILL.md)
- Persisted cache, mutation queue, token storage → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- State ownership → [`architecture`](../architecture/SKILL.md) · field errors → [`forms`](../forms/SKILL.md)
- Cleartext, pinning, secrets → [`mobile-<stack>:security`](../../../_shared/security/SKILL.md)
- API contract tests → `qa-api-typescript` (peer)
