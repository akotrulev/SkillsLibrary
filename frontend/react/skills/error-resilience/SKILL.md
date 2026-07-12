---
name: fe-react-error-resilience
description: Use when a React app (Next.js App Router primary / Vite SPA fallback; React 19 / 18) must fail safely and recover — error boundary placement (`error.tsx` per route + `global-error.tsx` root, `react-error-boundary` below), TanStack Query / fetch retry with backoff on idempotent calls only, live-connection-drop + offline UX (consistency with realtime's reconnect), client-error reporting to the server (Sentry/OTel, not console-only), plus the UI-correctness half: three-state (loading/loaded/failed) data regions with inline retry, inline grid error regions, and actionable empty states. Triggers "an unhandled error blanks my app", "add error boundaries", "retry failed requests", "the grid shows empty when the API 500s", "stop leaking error.message". Do NOT use to PRODUCE the categorized error from a fetch (that's `frontend/react/skills/data-access` — this skill RENDERS it), for form field-validation (use `frontend/react/skills/forms`), or for the live WS/SSE client itself (use `frontend/react/skills/realtime`).
---

# React — Error Resilience

Owns everything about **failing safely and recovering**: catching exceptions before they blank the app, retrying transient network faults, keeping live connections/offline states legible, and — the half most teams miss — **rendering failure and emptiness correctly in the UI** so a broken section never looks like an empty-but-fine section.

Division of labor with [`data-access`](../data-access/SKILL.md): data-access **produces** a categorized error (RFC-7807 `ProblemDetails` → friendly message + correlation id, raw detail logged server-side, via one `problemError` helper). This skill **renders** that error — the three-state region, the retry, the inline grid error. Two skills, one seam.

**Version rule:** detect the React/Next major first. Error boundaries, `react-error-boundary`, and TanStack Query retry are 18+. The **App Router** deltas are file conventions: `error.tsx` (per-segment boundary, must be a Client Component), `global-error.tsx` (wraps the root layout, its own `<html>`/`<body>`), and `not-found.tsx`. **React 19** adds root-level `onCaughtError`/`onUncaughtError` hooks for centralized reporting. The **Vite SPA** lane has no `error.tsx` — use `react-error-boundary` at the router/route level throughout (tagged below).

## When to use

- Placing error boundaries so an exception degrades one region, not the app
- Reporting caught render exceptions with a correlation id (not console-only)
- Retry/backoff on transient fetch faults; TanStack Query retry config
- Live-connection-drop / offline UX (kept consistent with the live-data status)
- Rendering the three states of a data region (loading / loaded / failed) + actionable empty states

## When NOT to use

- Producing the categorized error from a fetch/Server Action → [`data-access`](../data-access/SKILL.md)
- Per-field form validation messages → [`forms`](../forms/SKILL.md)
- The live WS/SSE client + its reconnect handlers as a *feature* → [`realtime`](../realtime/SKILL.md) (this skill owns the *UX* of a dropped connection; realtime owns the socket)
- Render/bundle *performance* → [`performance`](../performance/SKILL.md)
- Auth token-expiry mid-session → `auth/auth0-react` (session lifecycle)

## The three failure surfaces

```
Unhandled EXCEPTION during render/lifecycle  → Error boundary (catch, degrade the region)
Async data FETCH failed (transient/4xx/5xx)  → retry/backoff + categorized error → three-state render
Live CONNECTION dropped (WS/SSE) / OFFLINE   → connection-status UX (realtime owns the socket; consistency here)
```

Each surface has its own mechanism; wire all three. A boundary won't recover a failed fetch's UX; a retry won't catch a render `undefined.map`.

---

## Error boundaries — catch exceptions, degrade the region

An unhandled exception thrown during a component's render **unmounts the tree up to the nearest boundary**. Without one, the whole app (or route) goes blank. React error boundaries are still class components — but you almost never write one by hand: the App Router gives file conventions, and `react-error-boundary` gives a function-component API.

**Placement — three tiers (App Router):**

1. **`app/global-error.tsx`** — the last line of defense; wraps the **root layout** (so it must render its own `<html>`/`<body>`). Catches errors the layout itself throws. Friendly page-level message + reload — never a stack trace.

2. **`app/<segment>/error.tsx`** — a **per-route** boundary (a Client Component) that catches errors from that segment's page/children and offers `reset()` to re-render the segment:

   ```tsx
   'use client';
   import { useEffect } from 'react';

   export default function OrdersError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
     useEffect(() => { report(error); }, [error]);   // structured report, never console-only
     return (
       <div role="alert" data-testid="Orders.Error">
         <p>Couldn’t load orders.</p>
         {error.digest && <small>Ref: {error.digest}</small>}   {/* Next's server error digest — correlate, don't leak the message */}
         <button onClick={reset} data-testid="Orders.Error.Retry">Try again</button>
       </div>
     );
   }
   ```

3. **Per-feature**, below the route — wrap an independently-failing region (a dashboard tile, a widget) in `react-error-boundary`'s `<ErrorBoundary FallbackComponent={…} onReset={…} onError={report}>` so one widget's crash doesn't blank the page around it. Reset via `resetKeys` (re-mount when the inputs change) or an explicit "try again".

**Rules for every boundary:** log/report with context (`onError`/`useEffect`), **never render `error.message`** or a stack trace (bodies may carry PII/JSON) — friendly text + a correlation id (`error.digest` on the server side) only, and offer a real recovery action (`reset`). React 19: centralize reporting via `onCaughtError` in the root instead of duplicating `onError` everywhere. **Vite SPA:** no `error.tsx`/`global-error.tsx` — place `react-error-boundary` at the app root and around each route element.

Error boundaries **do not** catch errors in event handlers, effects cleanup, or async code (a rejected `fetch`) — those you handle with try/catch → the three-state region below.

---

## Fetch resilience — retry transient faults, only when safe

Transient faults (a blip, a cold-start 503, a throttled 429) should be absorbed, not surfaced. **TanStack Query** does this on the client:

```ts
useQuery({
  queryKey: ['orders'],
  queryFn: getOrders,
  retry: (count, err) => count < 3 && isTransient(err),   // 5xx/network only — never 4xx
  retryDelay: (i) => Math.min(1000 * 2 ** i, 30_000),     // exponential backoff + cap
});
```

- **Only retry idempotent operations** (GET/PUT/DELETE). **Never auto-retry a non-idempotent POST/mutation** — a retried create/charge double-submits. Mutations retry only with an idempotency key the server dedupes on.
- **Don't retry 4xx** (except 408/429) — the request is wrong, retrying won't fix it.
- **Server-side / RSC / Server Actions:** wrap the outbound call in a small retry-with-backoff helper for idempotent reads; let a failure throw a categorized error to the nearest `error.tsx`, or return a typed error result a Server Action surfaces. Consider a circuit-breaker (fail fast when a dependency is down) for hot paths.
- The retry pairs with [`data-access`](../data-access/SKILL.md)'s `problemError`: once retries are exhausted, the categorized error flows to the three-state region below.

**Client-error reporting:** an unhandled client error that only lands in the browser console is invisible. Wire **Sentry** (or a lightweight `POST /api/client-errors`, rate-limited) from `global-error.tsx`/boundary `onError` and a top-level `window.onerror`/`onunhandledrejection` handler, so client faults reach the same structured logs/OTel as the server (`observability/opentelemetry-node`, external). Include the correlation id.

---

## Live-connection & offline UX

React has **no persistent server circuit** (unlike Blazor) — so there's no circuit-reconnect modal. The analogous surfaces are the **live-data socket** and **network offline**:

- **Live WS/SSE drop:** [`realtime`](../realtime/SKILL.md) owns the socket, its backoff reconnection, and exposes a connection status (`connecting`/`open`/`reconnecting`/`closed`). This skill owns making that status **legible and consistent** — a "reconnecting…" affordance on the live region, and **never showing stale live data as current** while the socket is down (dim it / mark it stale). Same disconnect event, two layers — keep them consistent.
- **Offline:** gate optimistic actions on `navigator.onLine` + the `online`/`offline` events; show an offline banner; queue or block writes rather than failing them silently. TanStack Query pauses and resumes queries/mutations across offline→online — lean on it rather than hand-rolling.

---

## UI-correctness: rendering failure & emptiness

The rules below are the most-missed part of resilience — the app *handles* the error but *renders* it as an ambiguous blank. Each is a real defect class.

### One error helper; never leak raw errors

Route every call through [`data-access`](../data-access/SKILL.md)'s `problemError` — it categorizes (ProblemDetails → friendly message; unknown → generic message + correlation id) and logs raw detail server-side. **This skill's rule: never render `error.message` or a raw response body to the user** (bodies may be JSON, stack traces, or PII). Render the categorized `{ message, correlationId }` — not the exception.

### Three-state data regions — loading / loaded / failed

Every data region has **three** states, not two. The classic bug: a `try { … } catch {}` (or a swallowed `.then`) leaves the region empty, so an **outage is indistinguishable from "no data"**. Render the failed state **inline, with retry** — never only a toast (a toast disappears; the empty region stays and lies). With TanStack Query the three states fall out of the hook:

```tsx
function OrdersRegion() {
  const q = useQuery({ queryKey: ['orders'], queryFn: getOrders });

  if (q.isPending) return <Skeleton data-testid="Orders.Loading" />;
  if (q.isError)
    return (
      <div role="alert" data-testid="Orders.Error">
        <p>{toAppError(q.error).message}</p>            {/* friendly — never q.error.message raw */}
        {toAppError(q.error).correlationId && <small>Ref: {toAppError(q.error).correlationId}</small>}
        <button onClick={() => q.refetch()} data-testid="Orders.Retry">Try again</button>
      </div>
    );
  if (q.data.length === 0) return <EmptyState kind="no-records" />;   // see below
  return <OrdersTable orders={q.data} />;
}
```

In RSC, the **loading** state is the segment's `loading.tsx` (or a `<Suspense fallback>`), and the **failed** state is the segment's `error.tsx` — the same three states, expressed through the file conventions. Either way: three states, always.

### Inline error region **inside** grids

A grid load failure renders its error **in the grid area**, not just a toast — an empty grid is indistinguishable from "no rows". Bind the loading + failed states on the **shared table/grid component** so every grid gets them for one change ([`ui-conventions`](../ui-conventions/SKILL.md) renderer unification) — don't reimplement per page.

### Actionable empty states — three kinds

"Empty" is three different situations; each needs a different message and a different action:

| Situation | Message (in the data area, not a toast) | Action |
|---|---|---|
| **No records exist yet** | "No orders yet." | offer the **create** action |
| **No filter applied yet** | "Enter a filter to begin." | focus the filter |
| **Filter matched nothing** | "No orders match these filters." | offer **clear filters** |

A single generic "No data" for all three is a defect — it tells the user nothing about what to do next.

---

## Rules

- **`global-error.tsx`** at the root + **`error.tsx` per route** + **per-feature `react-error-boundary`** around independently-failing regions (Vite: `react-error-boundary` at root + per route).
- **Report** caught errors (structured, with context/correlation id) via `onError`/`useEffect`/React 19 `onCaughtError`; **never render `error.message`/stack** — friendly text + correlation id only; always offer `reset`/retry.
- **Retry idempotent calls only**, with exponential backoff (TanStack Query `retry`/`retryDelay`); never auto-retry a POST/mutation without an idempotency key; don't retry 4xx.
- **Report client errors to the server** (Sentry/OTel/rate-limited endpoint) — never console-only; include the correlation id.
- **Live-data status stays consistent** — show "reconnecting", never stale live data as current while the socket is down (coordinate with [`realtime`](../realtime/SKILL.md)); handle offline explicitly.
- **Three-state data regions** everywhere: loading / loaded / failed **inline with retry** — never swallow a failure into a blank section.
- **Grid failures render inline in the grid**; loading + failed bound on the **shared grid component**.
- **Actionable empty states** — distinguish no-records / no-filter / filter-matched-nothing.

## What NOT to do

- No app without a root boundary (`global-error.tsx` / root `react-error-boundary`) — one uncaught render error = blank app.
- No `error.message` / raw response body / stack trace rendered to a user.
- No two-state region (loaded / not-loaded) — a failure then reads as "no data".
- No failure surfaced *only* as a toast for a persistent region (grid/detail/section).
- No generic "No data" covering all three empty situations.
- No auto-retry on a non-idempotent mutation; no retry on a 4xx; no hand-rolled retry loop where TanStack Query's `retry` fits.
- No stale live data shown as current while the connection is down.
- No console-only client error (invisible = unlogged).
- No App-Router-only convention (`error.tsx`/`global-error.tsx`) emitted into a Vite SPA — use `react-error-boundary`.

## Validation

- Throw in a feature component → its boundary shows friendly content; the rest of the page still works; the report has the structured entry + correlation id; no `error.message` on screen.
- Make a fetch 500 → the region shows the **failed** state inline with a working retry, not a blank grid; the retry recovers on the next success; a transient 503 is absorbed by backoff without surfacing.
- Drop the network → offline UX appears; the live region shows "reconnecting" (not stale-as-current); restore → it recovers.
- Empty each way (no records / no filter / filtered-out) → three distinct actionable messages.
- Force a client error → it reaches the server log / Sentry (not just the browser console).

## Handoffs

- The categorized error this skill renders → [`data-access`](../data-access/SKILL.md) (produces it via `problemError`)
- Live WS/SSE socket + its reconnect/backoff + connection status → [`realtime`](../realtime/SKILL.md)
- Render/bundle performance → [`performance`](../performance/SKILL.md)
- Field-level validation errors → [`forms`](../forms/SKILL.md)
- Renderer unification (bind loading/failed once on the shared grid) → [`ui-conventions`](../ui-conventions/SKILL.md)
- Auth token-expiry mid-session → `auth/auth0-react`
- Client/server error export to Grafana → `observability/opentelemetry-node`
