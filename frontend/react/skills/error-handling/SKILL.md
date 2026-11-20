---
name: error-handling
description: Use when a React failure must not blank the screen (error boundaries, safe retries, failed regions, 401 recovery). Triggers "an error blanks my app". Not for producing the error (data-fetching).
disable-model-invocation: true
---

# React — Error Resilience

Owns **failing safely and recovering**: catching exceptions before they blank the app, retrying transient network faults, and **rendering failure and emptiness correctly in the UI**, so a broken section never looks like an empty-but-fine one.

[`data-fetching`](../data-fetching/SKILL.md) **produces** a categorized error (RFC-7807 `ProblemDetails` → friendly message + correlation id, raw detail logged server-side, via one `problemError` helper). This skill **renders** it: the three-state region, the retry, the notification. The standards are the fe-react rule files `react.md` and `react-data.md` (`.claude/rules/fe-react/` in the project, or `frontend/react/skills/rules/` until `/fe-react:rules` installs them). Where this skill and a rule file disagree, the rule file wins.

**Version rule:** detect the React/Next major first. Boundaries and TanStack Query retry are 18+; **React 19** adds root-level `onCaughtError`/`onUncaughtError`. The **App Router** has the file conventions `error.tsx`, `global-error.tsx` and `not-found.tsx`; the **Vite SPA** lane places `react-error-boundary` at the app root and around each route element.

## The failure surfaces

```
Unhandled EXCEPTION during render/lifecycle  → Error boundary (catch, degrade the region)
Async data FETCH failed (transient/4xx/5xx)  → retry/backoff + categorized error → state render
Async data FETCH never answers (hung)        → timeout budget turns "loading forever" INTO a failure
SESSION expired mid-work (401)               → refresh → replay → re-auth in place (never discard work)
The BUILD changed under an open tab          → version-skew detection + one guarded reload
Live CONNECTION dropped (WS/SSE) / OFFLINE   → connection-status UX (realtime owns the socket)
```

Wire all six: a boundary won't recover a failed fetch's UX, a retry won't catch a render `undefined.map`, and only a deadline at the transport fixes a request that never resolves.

## Situational surfaces

A task that contains the situation in the first column reads the file in the second.

| Situation | Where |
|---|---|
| A **write** fails (double-submit, idempotency keys, optimistic rollback, 409, partial bulk failure, unconfirmable outcome), or a **third party** fails (maps, payment iframes, analytics, feature flags) | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |
| The **session expires** mid-work (refresh → replay → re-auth in place), or a **deploy** lands under an open tab (`ChunkLoadError`, RSC payload skew) | [`references/session-and-deploy.md`](references/session-and-deploy.md) |
| A **WebSocket or SSE feed**, an **offline** requirement, a **data grid**, or a **detail page or region bound to a record** that can be deleted | [`references/live-connection-grids-and-gone.md`](references/live-connection-grids-and-gone.md) |
| The **notification** is wired for the project's component library, or several regions can fail at once | [`references/notifications.md`](references/notifications.md) |
| A change to error handling is **verified**: tests or a review pass | [`references/validation.md`](references/validation.md) |

---

## Error boundaries — catch exceptions, degrade the region

An unhandled exception thrown during render **unmounts the tree up to the nearest boundary**; without one, the whole app or route goes blank. You almost never write the class component: use the App Router file conventions or `react-error-boundary`.

**Placement — three tiers (App Router):**

1. **`app/global-error.tsx`** wraps the **root layout**, so it renders its own `<html>`/`<body>`, and shows a friendly page-level message with a reload.
2. **`app/<segment>/error.tsx`** is a **per-route** Client Component that catches errors from that segment's page and children, and offers `reset()` to re-render the segment:

   ```tsx
   'use client';
   import { useEffect } from 'react';

   export default function OrdersError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
     useEffect(() => { report(error); }, [error]);
     return (
       <div role="alert" data-testid="Orders.Error">
         <p>Couldn’t load orders.</p>
         {error.digest && <small>Ref: {error.digest}</small>}
         <button onClick={reset} data-testid="Orders.Error.Retry">Try again</button>
       </div>
     );
   }
   ```

   `report` sends a structured entry, and `error.digest` is Next's server error digest, which correlates it without leaking the message.
3. **Per feature**, below the route: wrap an independently failing region (a dashboard tile, a widget) in `react-error-boundary`'s `<ErrorBoundary FallbackComponent={…} onReset={…} onError={report}>`. Reset through `resetKeys` or an explicit "try again".

**Every boundary** reports with context (`onError`/`useEffect`), renders friendly text plus a correlation id instead of `error.message` or a stack, and offers a real recovery action (`reset`). React 19 centralizes the reporting in the root `onCaughtError`.

Error boundaries **do not** catch errors in event handlers, effect cleanup or async code (a rejected `fetch`): handle those with try/catch, then the three-state region below.

---

## Fetch resilience — retry transient faults, only when safe

Absorb a blip, a cold-start 503 or a throttled 429 rather than surface it. The retry, idempotency and `Retry-After` rules are in `react-data.md`. With **TanStack Query**, retry 5xx and network errors with capped exponential backoff:

```ts
useQuery({
  queryKey: ['orders'],
  queryFn: getOrders,
  retry: (count, err) => count < 3 && isTransient(err),
  retryDelay: (i) => Math.min(1000 * 2 ** i, 30_000),
});
```

- **Say when a throttle sends you away.** On a 429/503 with `Retry-After` tell the user, "Too many requests — retrying in 30s", rather than looping silently.
- **Stop retrying at some point, and say so.** After *k* consecutive failures for one key (3 by default), switch that region to manual-only: *"We've stopped retrying automatically."* with a Retry button, and stop re-notifying. A polling query left retrying through an outage hammers a service that is already down.
- **Server-side / RSC / Server Actions:** wrap the outbound call in a small retry-with-backoff helper for idempotent reads, and let a failure throw a categorized error to the nearest `error.tsx` or return a typed error result a Server Action surfaces.

**Report what boundaries cannot see.** Capture a hydration mismatch ([`basics`](../basics/SKILL.md) owns the causes) with the root `onRecoverableError`. Send an unhandled client error to **Sentry** (or a rate-limited `POST /api/client-errors`) from `global-error.tsx`, the boundary `onError` and a top-level `window.onerror`/`onunhandledrejection` handler, with the correlation id, so it lands in the same logs and OTel as the server (`observability/opentelemetry-node`, external).

---

## UI-correctness: rendering failure & emptiness

### One error helper; never leak raw errors

Route every call through `data-fetching`'s `problemError` and render the categorized `{ message, correlationId }`, never the exception, `error.message` or a raw response body.

### Data-region states — loading / loaded / failed (+ stale)

Every data region has **three** states. The classic bug is a `try { … } catch {}` (or a swallowed `.then`) that leaves the region empty, so an **outage is indistinguishable from "no data"**. Render the failed state **inline, with retry**, because a toast alone disappears while the empty region stays and lies. With TanStack Query the states fall out of the hook, and the region is `failed` only when there is no data to show:

```tsx
function OrdersRegion() {
  const q = useQuery({ queryKey: ['orders'], queryFn: getOrders });

  if (q.isPending) return <Skeleton data-testid="Orders.Loading" />;
  if (q.data === undefined) {
    const failure = toAppError(q.error);
    return (
      <div role="alert" data-testid="Orders.Error">
        <p>{failure.message}</p>
        {failure.correlationId && <small>Ref: {failure.correlationId}</small>}
        <button onClick={() => q.refetch()} data-testid="Orders.Error.Retry">Try again</button>
      </div>
    );
  }
  if (q.data.length === 0) return <EmptyState kind="no-records" data-testid="Orders.Empty" />;
  return <OrdersTable orders={q.data} />;
}
```

In RSC, **loading** is the segment's `loading.tsx` (or a `<Suspense fallback>`) and **failed** is its `error.tsx`.

**A response the app can't read is a failure, not an emptiness.** A 200 whose body drifted fails the Zod parse at the boundary ([`data-fetching`](../data-fetching/SKILL.md)) and lands in **this** failed state, never in `data = []` rendered as "no records". Transport, auth, shape and timeout failures render the same failed state; only the message differs.

### The fourth state — stale, when a *refetch* fails

The three states describe a region with **no data yet**. Once a region has rendered data, replacing it with an error panel because one 5s poll blipped destroys information the user still had. Split the rule by whether data exists:

| Situation | TanStack signal | Render |
|---|---|---|
| First load, in flight | `isPending` (no `data`) | **loading** skeleton |
| First load, failed | `data === undefined` after `isPending` ends | **failed** body + retry |
| Refresh in flight over existing data | `isFetching` && `data !== undefined` | **loaded**, with a subtle refreshing indicator, never a skeleton flash |
| Refresh failed, data still held | `isError` && `data !== undefined` | **stale**: keep rendering the data, mark it stale, notify |

```tsx
const q = useQuery({ queryKey: ['orders', filters], queryFn: getOrders, placeholderData: keepPreviousData });

if (q.isPending) return <Skeleton data-testid="Orders.Loading" />;
if (q.data === undefined) return <FailedBody error={toAppError(q.error)} onRetry={q.refetch} />;
return (
  <>
    {q.isError && <StaleBanner data-testid="Orders.Stale" asOf={q.dataUpdatedAt} onRetry={q.refetch} />}
    <OrdersTable rows={q.data} dimmed={q.isError} />
  </>
);
```

`keepPreviousData` keeps the old rows visible while a filter change loads, instead of flashing empty.

- **Say how old it is** (`dataUpdatedAt` → "as of 14:02") and offer retry. Stale-but-labeled is honest; stale-shown-as-current is the defect ([`realtime`](../realtime/SKILL.md) holds the same line for a dropped socket).
- **Data that is dangerous when stale** (a price, a balance, an availability count) is marked stale *and* **disables the action that depends on it** ([`ui-rules`](../ui-rules/SKILL.md) disable-don't-hide, with the reason in the tooltip). When in doubt, disable the write and keep the read.
- **A background refetch failure still notifies** (once, deduped); silence hides the staleness.
- **A filter or param change is a first load for that key**, not a refresh, unless you opt into `keepPreviousData`, the right default for tables and pagination.

### Timeouts — a request that never answers

A request that never resolves leaves the region spinning **forever**, and Chrome's own `fetch` deadline is ~300 seconds. **Every call gets a budget**, from one helper, because the budget is a property of the endpoint and not of the call site:

```ts
export function budget(ms: number, external?: AbortSignal) {
  return external ? AbortSignal.any([external, AbortSignal.timeout(ms)]) : AbortSignal.timeout(ms);
}

queryFn: ({ signal }) => api.get('/orders', { signal: budget(10_000, signal) }),
```

Passing TanStack's unmount/cancel `signal` composes it with the timeout instead of replacing it. A timeout rejects with `TimeoutError`; a user or unmount abort is an `AbortError`, which renders no failed state and no notification.

- **Set the budget per endpoint class**, and keep the numbers in the API client config: interactive reads ~8–10s · autocomplete/typeahead ~2–3s · reports, exports and uploads much longer or none (a 90s export killed at 10s is a self-inflicted failure).
- **A timeout categorizes as its own error**, not a generic 5xx, and its failed body leads with retry: *"This is taking longer than expected."*
- **Cross a soft threshold first.** At ~4s the skeleton acknowledges itself ("still loading…"), so the user does not double-click and submit twice.
- **Server-side too:** RSC fetches and Server Actions take the same budget on the outbound `fetch`, or a slow upstream holds the whole streamed response open.

### Failure scope — degrade the smallest data-dependent subtree

**The failure replaces only the part that depends on the response, and everything the user can still act on keeps rendering.** On a list page only the **rows** need the response, so a failed `GET /orders` leaves the header, search, filters, toolbar and paging usable, with the error **in the rows area**. A chart's canvas fails without its range picker, and a dashboard tile without the dashboard.

Wrong: an early return in the container, where one failed call unmounts the search bar, the filters and the user's typed state with them.

```tsx
if (q.isError) return <ErrorPanel error={q.error} onRetry={q.refetch} />;
return (<><OrdersSearchBar value={search} onChange={setSearch} /><OrdersTable rows={q.data} /></>);
```

Right: the chrome renders unconditionally and the state branch lives at the data-dependent boundary, where only the table body swaps state.

```tsx
const state = q.isPending ? 'loading' : q.data === undefined ? 'failed' : 'loaded';

return (
  <section data-testid="Orders">
    <OrdersSearchBar value={search} onChange={setSearch} />
    <OrdersFilters value={filters} onChange={setFilters} />
    <OrdersTable
      rows={q.data ?? []}
      state={state}
      stale={q.isError && q.data !== undefined}
      error={q.error ? toAppError(q.error) : undefined}
      onRetry={q.refetch}
    />
  </section>
);
```

- **The three-state branch sits at the data-dependent boundary**, not at a container that also owns the chrome; split such a component (container/presentation) instead of early-returning.
- **Filter, search and sort state lives above the failing region**, or in the URL ([`state-management`](../state-management/SKILL.md)), so it survives the failure and "fix the filter and try again" works.
- **An error boundary wraps the data-dependent subtree, not the route**, whenever the surrounding chrome is still meaningful.
- **Partial failure is per region**: one 500 degrades one of three independent tiles.
- **The failed body differs from the empty body**: failed carries the error text, the correlation id and a retry; empty carries the actionable message below.

### The error notification

The inline region says *this data is missing*; the notification says *why*. Both, always: `react.md` states the contract (persistent, top-right, closed only by its close button). Raise it once per failure path, never for field-level validation ([`forms`](../forms/SKILL.md) renders that on the field), an expected empty result, an aborted request or a fault the retry absorbed. Wiring the provider, dedupe, the raise-point and the volume control for an outage → [`references/notifications.md`](references/notifications.md).

### Actionable empty states — three kinds

"Empty" is three situations, each with its own message in the data area (not a toast) and its own action:

| Situation | Message | Action |
|---|---|---|
| **No records exist yet** | "No orders yet." | offer the **create** action |
| **No filter applied yet** | "Enter a filter to begin." | focus the filter |
| **Filter matched nothing** | "No orders match these filters." | offer **clear filters** |

A generic "No data" for all three tells the user nothing about what to do next.
