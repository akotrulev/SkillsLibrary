---
name: fe-react-error-handling
description: Use when a failure must not blank the screen — error boundary placement, retry on idempotent calls only, timeout budgets, loading/loaded/failed/stale data regions, the persistent error notification, mid-session 401 recovery. Triggers "an unhandled error blanks my app", "add error boundaries", "the grid shows empty when the API 500s", "the spinner never stops", "the session expired and my form was gone". Not for PRODUCING the categorized error (`data-fetching` — this RENDERS it).
---

# React — Error Resilience

Owns everything about **failing safely and recovering**: catching exceptions before they blank the app, retrying transient network faults, keeping live connections/offline states legible, and — the half most teams miss — **rendering failure and emptiness correctly in the UI** so a broken section never looks like an empty-but-fine section.

Division of labor with [`data-fetching`](../data-fetching/SKILL.md): data-fetching **produces** a categorized error (RFC-7807 `ProblemDetails` → friendly message + correlation id, raw detail logged server-side, via one `problemError` helper). This skill **renders** that error — the three-state region, the retry, the inline grid error. Two skills, one seam.

**Version rule:** detect the React/Next major first. Error boundaries, `react-error-boundary`, and TanStack Query retry are 18+. The **App Router** deltas are file conventions: `error.tsx` (per-segment boundary, must be a Client Component), `global-error.tsx` (wraps the root layout, its own `<html>`/`<body>`), and `not-found.tsx`. **React 19** adds root-level `onCaughtError`/`onUncaughtError` hooks for centralized reporting. The **Vite SPA** lane has no `error.tsx` — use `react-error-boundary` at the router/route level throughout (tagged below).

## When to use

- Placing error boundaries so an exception degrades one region, not the app
- Reporting caught render exceptions with a correlation id (not console-only)
- Retry/backoff on transient fetch faults; TanStack Query retry config
- Live-connection-drop / offline UX (kept consistent with the live-data status)
- Rendering the states of a data region (loading / loaded / failed / stale) + actionable empty states
- Setting request timeout budgets so a hung call fails instead of spinning; the slow-request affordance
- Deciding what a *refetch* failure does to data already on screen (keep it, mark it stale)
- Recovering from a mid-session 401 without discarding the user's unsaved work
- Surviving a deploy in an open tab (`ChunkLoadError`, RSC payload skew, the reload prompt)
- Write-failure semantics — double-submit, idempotency keys, optimistic rollback, 409 conflicts, partial bulk failure
- Keeping an outage from becoming a wall of toasts (rate-limit backoff, retry circuit, notification roll-up)
- Scoping a failure so only the response-dependent part degrades (rows fail, search/filters keep working)
- The app-wide persistent error notification (top-right, close-button-only) and what raises it

## When NOT to use

- Producing the categorized error from a fetch/Server Action → [`data-fetching`](../data-fetching/SKILL.md)
- Per-field form validation messages → [`forms`](../forms/SKILL.md)
- The live WS/SSE client + its reconnect handlers as a *feature* → [`realtime`](../realtime/SKILL.md) (this skill owns the *UX* of a dropped connection; realtime owns the socket)
- Render/bundle *performance* → [`performance`](../performance/SKILL.md)
- The token/refresh *mechanics* (SDK config, rotation, reuse detection) → `auth/auth0-react` — **this skill owns what the UI does when a call comes back 401** ([`references/session-and-deploy.md`](references/session-and-deploy.md))

## The failure surfaces

```
Unhandled EXCEPTION during render/lifecycle  → Error boundary (catch, degrade the region)
Async data FETCH failed (transient/4xx/5xx)  → retry/backoff + categorized error → state render
Async data FETCH never answers (hung)        → timeout budget turns "loading forever" INTO a failure
SESSION expired mid-work (401)               → refresh → replay → re-auth in place (never discard work)
The BUILD changed under an open tab          → version-skew detection + one guarded reload
Live CONNECTION dropped (WS/SSE) / OFFLINE   → connection-status UX (realtime owns the socket; consistency here)
```

Each surface has its own mechanism; wire all six. A boundary won't recover a failed fetch's UX; a retry won't catch a render `undefined.map`; and **no state machine saves you from a request that never resolves** — that one is only fixed at the transport, with a deadline.

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
- **Honour `Retry-After` on a 429/503.** The server has told you when to come back; backing off less than it asked is how a throttle becomes a ban. Read the header (delta-seconds *or* an HTTP-date), wait at least that long, cap the attempts, and tell the user rather than looping silently: *"Too many requests — retrying in 30s."* Absent the header, fall back to the exponential schedule.
- **Stop retrying at some point, and say so.** After *k* consecutive failures for the same key (3 is a reasonable default), **stop the automatic retries** and switch that region to manual-only: *"We've stopped retrying automatically."* with a Retry button. A polling query left auto-retrying through a 20-minute outage burns battery, fills logs, and hammers a service that is already down — the client is part of the incident.
- **Server-side / RSC / Server Actions:** wrap the outbound call in a small retry-with-backoff helper for idempotent reads; let a failure throw a categorized error to the nearest `error.tsx`, or return a typed error result a Server Action surfaces. Consider a circuit-breaker (fail fast when a dependency is down) for hot paths.
- The retry pairs with [`data-fetching`](../data-fetching/SKILL.md)'s `problemError`: once retries are exhausted, the categorized error flows to the three-state region below.

**Hydration mismatches are reportable, not cosmetic.** React recovers from most by re-rendering on the client (logging a recoverable error), and a severe one throws and blanks the route — either way it means the server and client disagreed about what to draw, usually from a browser read during render or locale/time formatting ([`basics`](../basics/SKILL.md) owns the causes). Capture recoverable errors too — React 19's root `onRecoverableError` — so they reach the same logs instead of dying in a console nobody has open.

**Client-error reporting:** an unhandled client error that only lands in the browser console is invisible. Wire **Sentry** (or a lightweight `POST /api/client-errors`, rate-limited) from `global-error.tsx`/boundary `onError` and a top-level `window.onerror`/`onunhandledrejection` handler, so client faults reach the same structured logs/OTel as the server (`observability/opentelemetry-node`, external). Include the correlation id.

---

## Situational surfaces — deep dives

Four failures need more than a rule and are kept out of the main flow. **Read the file when the situation applies:**

| Situation | Where |
|---|---|
| A **write** fails — double-submit, idempotency keys, optimistic rollback, 409 conflicts, partial bulk failure, unconfirmable outcomes | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |
| A **third-party** fails — maps, payment iframes, analytics, feature flags (and which failures the user should *not* hear about) | [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md) |
| The **session expires** mid-work — the refresh → replay → re-auth-in-place ladder that keeps unsaved work | [`references/session-and-deploy.md`](references/session-and-deploy.md) |
| A **deploy** lands under an open tab — `ChunkLoadError`, RSC payload skew, the guarded once-only reload | [`references/session-and-deploy.md`](references/session-and-deploy.md) |

## Live-connection & offline UX

React has **no persistent server circuit** (unlike Blazor) — so there's no circuit-reconnect modal. The analogous surfaces are the **live-data socket** and **network offline**:

- **Live WS/SSE drop:** [`realtime`](../realtime/SKILL.md) owns the socket, its backoff reconnection, and exposes a connection status (`connecting`/`open`/`reconnecting`/`closed`). This skill owns making that status **legible and consistent** — a "reconnecting…" affordance on the live region, and **never showing stale live data as current** while the socket is down (dim it / mark it stale). Same disconnect event, two layers — keep them consistent.
- **Offline:** gate optimistic actions on `navigator.onLine` + the `online`/`offline` events; show an offline banner; queue or block writes rather than failing them silently. TanStack Query pauses and resumes queries/mutations across offline→online — lean on it rather than hand-rolling.

---

## UI-correctness: rendering failure & emptiness

The rules below are the most-missed part of resilience — the app *handles* the error but *renders* it as an ambiguous blank. Each is a real defect class.

### One error helper; never leak raw errors

Route every call through [`data-fetching`](../data-fetching/SKILL.md)'s `problemError` — it categorizes (ProblemDetails → friendly message; unknown → generic message + correlation id) and logs raw detail server-side. **This skill's rule: never render `error.message` or a raw response body to the user** (bodies may be JSON, stack traces, or PII). Render the categorized `{ message, correlationId }` — not the exception.

### Data-region states — loading / loaded / failed (+ stale)

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

**A response the app can't read is a failure, not an emptiness.** A 200 whose body drifted (a field renamed, an object where an array was expected) must fail the Zod parse at the boundary ([`data-fetching`](../data-fetching/SKILL.md)) and land in **this** failed state — never fall through to `data = []` and render as "no records". Transport failure, auth failure, shape failure and timeout all render the same failed state; only the message differs.

### The fourth state — stale, when a *refetch* fails

The three states above describe a region that has **no data yet**. Once a region *has* rendered data, a later failure is a different situation and the failed body is the **wrong** answer: replacing a dashboard the user is reading with an error panel — because one 5s poll blipped — destroys information they still had.

**Split the rule by whether data exists:**

| Situation | TanStack signal | Render |
|---|---|---|
| First load, in flight | `isPending` (no `data`) | **loading** skeleton |
| First load, failed | `isError` && `data === undefined` | **failed** body + retry (§ above) |
| Refresh in flight over existing data | `isFetching` && `data !== undefined` | **loaded**, with a subtle refreshing indicator — never a skeleton flash |
| Refresh failed, data still held | `isError` && `data !== undefined` | **stale**: keep rendering the data, mark it stale, notify |

```tsx
const q = useQuery({ queryKey: ['orders', filters], queryFn: getOrders,
  placeholderData: keepPreviousData });   // filter change keeps the old rows visible instead of flashing empty

if (q.isPending)              return <Skeleton data-testid="Orders.Loading" />;
if (q.isError && !q.data)     return <FailedBody error={toAppError(q.error)} onRetry={q.refetch} />;
return (
  <>
    {q.isError && (                       // ← the stale state: data is old, and we know it
      <StaleBanner data-testid="Orders.Stale" asOf={q.dataUpdatedAt} onRetry={q.refetch} />
    )}
    <OrdersTable rows={q.data} dimmed={q.isError} />
  </>
);
```

**Rules for the stale state**

- **Never downgrade rendered data to an error panel** on a refetch failure — keep the data, add the marker, keep the notification.
- **Say how old it is** (`dataUpdatedAt` → "as of 14:02") and offer retry. Stale-but-labeled is honest; stale-shown-as-current is the defect ([`realtime`](../realtime/SKILL.md) holds the same line for a dropped socket — one rule, two transports).
- **Data that is dangerous when stale is the exception** — a price, a balance, an availability count, anything the user is about to act on. Mark it stale *and* **disable the action that depends on it** ([`ui-rules`](../ui-rules/SKILL.md) disable-don't-hide, with the reason in the tooltip). Decide this per region; when in doubt, disable the write, keep the read.
- **A background refetch failure still notifies** (once, deduped) — silence would make the staleness invisible, which is how a user acts on ten-minute-old numbers.
- **A filter/param change is a first load for that key**, not a refresh — unless you opt into `keepPreviousData`, which is the right default for tables and pagination (no empty flash between pages).

### Timeouts — a request that never answers

The loading state is not a fourth failure surface, it is the **absence** of one: a request that never resolves leaves the region spinning **forever**. The browser will not save you — Chrome's own `fetch` deadline is ~300 seconds. A region with no deadline has a state the three-state rule can't express, and it reads to the user as "this app is broken" with nothing to click.

**Every call gets a budget**, expressed as a signal rather than a `setTimeout` race:

```ts
// one helper, one place — the budget is a property of the endpoint, not of the call site
export function budget(ms: number, external?: AbortSignal) {
  return external ? AbortSignal.any([external, AbortSignal.timeout(ms)]) : AbortSignal.timeout(ms);
}

queryFn: ({ signal }) => api.get('/orders', { signal: budget(10_000, signal) }),
//                                     ↑ TanStack's unmount/cancel signal, composed — not replaced
```

`AbortSignal.timeout()` rejects with a **`TimeoutError`** `DOMException` (distinguishable from a user/unmount abort, which is an `AbortError` — and an `AbortError` is **not** a failure: it must not render a failed state or notify). `AbortSignal.any()` composes them; both are Baseline since 2024.

- **Set the budget per endpoint class**, not one global number: interactive reads ~8–10s · autocomplete/typeahead ~2–3s · reports/exports/uploads much longer or none (a 90s export killed at 10s is a self-inflicted failure). Put the numbers in the API client config so they're visible in one place.
- **A timeout categorizes as its own error** — not a generic 5xx. It is the one failure where "try again" is genuinely likely to work, so the failed body leads with retry: *"This is taking longer than expected."*
- **Retry a timeout only if the call is idempotent** — a timed-out POST may well have succeeded on the server; retrying it double-charges. Same rule as the retry section, and timeouts are exactly where it gets violated.
- **Cross the soft threshold first.** At ~4s (well inside the budget) the skeleton should acknowledge itself — "still loading…", or a progress affordance — so the user knows the app is alive. A silent skeleton at second nine is why people double-click and submit twice.
- **Server-side too:** RSC fetches and Server Actions need the same budget (`AbortSignal.timeout` on the outbound `fetch`), or a slow upstream holds the whole streamed response open.

### Failure scope — degrade the smallest data-dependent subtree

**The failure replaces only the part that depends on the response. Everything the user can still act on keeps rendering.**

Take a list page: header, search bar, filter controls, column headers, toolbar, paging — none of those need the response to exist. Only the **rows** do. So a failed `GET /orders` leaves the whole page usable (the user can change filters and retry the query) with the error rendered **in the rows area**, exactly where the data would have been. The same rule holds for every such element: a chart's canvas but not its legend/range picker, a detail pane but not the master list beside it, a dependent `<select>`'s options but not the form around it, a tile in a dashboard but not the dashboard.

The defect this prevents is an early return in the container:

```tsx
// ✗ WRONG — one failed call unmounts the search bar, the filters, and the user's typed state with them
if (q.isError) return <ErrorPanel error={q.error} onRetry={q.refetch} />;
return (<><Filters …/><OrdersTable rows={q.data}/></>);

// ✓ RIGHT — chrome renders unconditionally; the state branch lives at the data-dependent boundary
return (
  <section data-testid="Orders">
    <OrdersSearchBar value={search} onChange={setSearch} />   {/* independent of the response */}
    <OrdersFilters value={filters} onChange={setFilters} />   {/* independent of the response */}
    <OrdersTable
      rows={q.data ?? []}
      state={q.isPending ? 'loading' : q.isError ? 'failed' : 'loaded'}
      error={q.isError ? toAppError(q.error) : undefined}
      onRetry={q.refetch}
    />                                                        {/* only the BODY swaps state */}
  </section>
);
```

**Scoping rules**

- The three-state branch sits at the **data-dependent boundary**, not at the container that also owns the chrome. If a component renders both, split it (container/presentation) rather than early-returning.
- **Filter/search/sort state survives the failure** — it lives above the failing region (or in the URL, per [`state-management`](../state-management/SKILL.md)), so "fix the filter and try again" actually works. Unmounting the controls destroys what the user typed and is the real cost of the early return.
- **Error boundaries follow the same scope:** wrap the data-dependent subtree, not the route, whenever the surrounding chrome is still meaningful. A route-level `error.tsx`/`global-error.tsx` remains the backstop for a chrome-level throw — not the first line of defense for a failed read.
- **Partial failure is per-region**: three tiles fetching independently means three independent states — one 500 degrades one tile, and the other two still render their data.
- **Never leave the failed region visually identical to its empty state** — the failed body carries the error text, the correlation id, and a retry; the empty body carries the actionable empty message (below).

### The error notification — persistent, top-right, user-dismissed

The inline region says *this data is missing*; the notification says *why, and how to report it*. Both, always — they are not alternatives.

**The contract:**

| Property | Value |
|---|---|
| Position | **top-right** of the viewport, one stack, above app chrome, below modals |
| Dismissal | **manual only** — an explicit close button (`aria-label="Close"`). **No auto-dismiss timeout, ever**, for an error |
| Content | the categorized friendly message + the correlation id (copyable) + optionally a retry action — **never** `error.message`, a stack, or a raw body |
| Semantics | container `aria-live="polite"` + `role="status"` for info, `role="alert"` for errors; the close button is keyboard-reachable and focus is not stolen from the user's current field |
| Dedupe | key by `correlationId ?? (code + region)` — a retried-then-failed call updates the existing entry (with a count) instead of stacking five copies |
| Scope | one provider mounted **once** at the root client island; features call a hook (`useNotify().error(appError)`), never mount their own portal |

Success/info notifications may auto-dismiss (~4–6s). **Errors may not** — the user must be able to read it, copy the reference, and screenshot it. This is the one place this skill's older "never a toast" rule is refined: a toast is wrong *as the only surface* for a persistent region, and correct *in addition to* the inline state.

Wire it with the project's component library rather than hand-rolling — [`component-library`](../component-library/SKILL.md) owns the mounting:

| Library | Persistent-error call |
|---|---|
| MUI (notistack) | `enqueueSnackbar(msg, { variant: 'error', persist: true, anchorOrigin: { vertical: 'top', horizontal: 'right' }, action: closeButton })` |
| Mantine | `notifications.show({ color: 'red', autoClose: false, withCloseButton: true })` + `<Notifications position="top-right" />` |
| Chakra v3 | `toaster.error({ duration: null, meta: { closable: true } })`, toaster created with `placement: 'top-end'` |
| **shadcn (sonner)** — default lane | `toast.error(msg, { duration: Infinity, closeButton: true })` + `<Toaster position="top-right" />` |
| none | a small `NotificationProvider` context + a fixed-position `<ul aria-live="polite">` portal; same contract |

Give the surface stable test ids ([`test-ids`](../test-ids/SKILL.md)): `Notifications.Region`, `Notifications.Error`, `Notifications.Error.Close`, `Notifications.Error.CorrelationId`.

**Where it is raised:** one place per failure path — the query/mutation error handler (a TanStack Query `QueryCache.onError` / `MutationCache.onError` global handler covers every query for one change), a boundary's `onError`, or the Server-Action result handler. Do not `notify()` at the call site *and* in the global handler — that double-fires.

**Volume control — an outage must not become a wall of toasts.** Dedupe-by-key handles the *same* error repeating; it does nothing about a backend outage failing six regions at once, each with its own correlation id. Three defenses, in order:

1. **Cap the stack.** Show at most ~3 notifications; collapse the rest into one "+4 more issues" entry that expands. A stack taller than the viewport hides its own close buttons.
2. **Roll up by cause, not by call.** Six regions failing on one 503 is **one** message ("Some data couldn't be loaded — the service is unavailable"), not six. Group on status/code + a short time window; the per-region inline states already say *which* regions are affected.
3. **Let the retry circuit quiet it.** Once a region stops auto-retrying (the *k*-consecutive-failures rule in the retry section), it stops re-notifying — one persistent entry with a count, not one per attempt.

**What does NOT get a notification:** field-level validation ([`forms`](../forms/SKILL.md) renders it on the field), an expected empty result, an aborted request (navigation cancels), and a transient fault absorbed by retry — only the final, surfaced failure notifies.

### Inline error region **inside** grids

A grid load failure renders its error **in the grid area**, not just a toast — an empty grid is indistinguishable from "no rows". Bind the loading + failed states on the **shared table/grid component** so every grid gets them for one change ([`ui-rules`](../ui-rules/SKILL.md) renderer unification) — don't reimplement per page.

### Gone, not broken — the deleted entity

A detail page whose record was deleted (or whose id was pasted wrong) comes back **404**, and rendering that as "something went wrong" sends the user retrying a thing that will never work. Treat it as its own outcome: *"This order no longer exists"*, with a way out — back to the list, or the search that found it. **[App]** the route-level form of this is `not-found.tsx` + `notFound()` ([`routing`](../routing/SKILL.md)); below the route, a region that lost its record renders the gone state in place, and any action bound to it is removed rather than left to fail. A list that still shows the deleted row until the next refetch is the paired defect — invalidate on delete.

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
- **Writes get their own discipline** ([details](references/writes-and-dependencies.md)) — pending disables the control (double-submit = duplicate charge), retryable writes carry an **idempotency key per intent**, a rolled-back optimistic update **always notifies** and never clears the user's input, a 409/412 conflict is handed back as a choice (never silently retried), 422 goes to the fields, bulk reports per item, and an unconfirmable write says so and refetches.
- **Honour `Retry-After`**, cap attempts, and **stop auto-retrying after k consecutive failures** — switch the region to manual retry and stop re-notifying.
- **Third-party dependencies fail in their own boundary, with their own timeout** ([details](references/writes-and-dependencies.md)) — analytics/flags fail silently to the user (defaults, logged); maps/embeds fail to their region; payment/auth iframes fail loudly with a fallback path. A flag provider never blocks first render.
- **Storage access is guarded and degrades to memory** ([`state-management`](../state-management/SKILL.md)) — a quota/private-mode throw must never break a render.
- **A 404 on a record is "gone", not "broken"** — its own message and a way out, with the deleted row invalidated from the list.
- **Report recoverable errors too** (hydration mismatches via `onRecoverableError`) — a console-only signal is no signal.
- **Cap and roll up notifications** — ≤ ~3 visible with a "+N more", grouped by cause rather than by call, so one outage is one message.
- **Handle deploy version skew** ([details](references/session-and-deploy.md)) — set `deploymentId`, catch `ChunkLoadError`/dynamic-import failures globally and reload **once** (sessionStorage-guarded), prompt rather than force-reload when work is unsaved, and share one "new version available" affordance with the service worker's.
- **A mid-session 401 runs the ladder** ([details](references/session-and-deploy.md)) — single-flight silent refresh → replay once → **re-auth in place** → redirect only from a surface with no unsaved work. 403 renders permission-denied (no retry, no re-auth); only your own API triggers it; warn before the deadline; `returnTo` the exact route.
- **Live-data status stays consistent** — show "reconnecting", never stale live data as current while the socket is down (coordinate with [`realtime`](../realtime/SKILL.md)); handle offline explicitly.
- **Three-state data regions** everywhere: loading / loaded / failed **inline with retry** — never swallow a failure into a blank section. An unreadable/drifted response is a **failed** state, not an empty one.
- **A failed *refetch* renders the stale state, not the failed body** — keep the data the user already has, label how old it is, offer retry, notify once; disable actions that are unsafe on stale data. The failed body is only for a region with no data yet.
- **Every request carries a timeout budget** (`AbortSignal.timeout` composed with the cancel signal via `AbortSignal.any`), set per endpoint class, categorized as its own `TimeoutError` — and a soft "still loading" tier before it. A user-initiated `AbortError` is not a failure: no failed state, no notification.
- **Scope the failure to the data-dependent subtree** — search, filters, toolbars, headers, and the user's typed filter state keep rendering; only the part fed by the response swaps to the failed body. No early `return <Error/>` from a container that also owns the chrome; boundaries wrap the region, not the route.
- **Every surfaced failure also raises a persistent notification** — top-right, **no auto-dismiss**, explicit close button, friendly message + correlation id, deduped by key, from one root-mounted provider and one raise-point per failure path.
- **Grid failures render inline in the grid**; loading + failed bound on the **shared grid component**.
- **Actionable empty states** — distinguish no-records / no-filter / filter-matched-nothing.

## What NOT to do

- No app without a root boundary (`global-error.tsx` / root `react-error-boundary`) — one uncaught render error = blank app.
- No `error.message` / raw response body / stack trace rendered to a user.
- No two-state region (loaded / not-loaded) — a failure then reads as "no data".
- No failure surfaced *only* as a toast for a persistent region (grid/detail/section) — and equally, no inline failure without the notification.
- **No auto-dismissing error notification** (a timed-out error the user was scrolling past is an unreported bug), no notification without a close button, no error notification anywhere but the top-right stack, no per-feature toast portal.
- No whole-page/whole-section unmount for one failed call — filters, search, and toolbars must not disappear with the rows; no early `return` that discards the user's filter state.
- No drifted/unparseable response falling through to `[]` and rendering as "no records"; no `catch` that turns a failed read into an empty one.
- **No request without a deadline** — no region that can spin forever, no reliance on the browser's ~300s default, no `setTimeout`-vs-`fetch` race where `AbortSignal.timeout` fits, and no timeout signal that *replaces* the library's cancel signal instead of composing with it.
- **No error panel replacing data the user was already reading** because a background refetch failed; no skeleton flash over existing rows on a refresh or a page change (`keepPreviousData`); no stale data shown as current, and no enabled write action on stale data that makes the write unsafe.
- No submit control left enabled while its mutation is pending; no retryable write without an idempotency key; **no silent optimistic rollback**; no form cleared on a failed submit; no 409/412 auto-retried or silently overwritten; no 422 shown as a toast instead of on the field; no blanket success/failure over a partially-failed bulk write; no timed-out write reported as a definite failure.
- No toast for a failed analytics beacon (nothing the user can act on); no flag provider gating first paint; no third-party widget crash reaching the route's boundary; no unguarded storage write; no 404-on-a-record rendered as a generic failure or left retryable; no hydration mismatch swallowed by the console.
- No ignoring `Retry-After`; no unbounded auto-retry through an outage (the client becomes part of the incident); no notification per retry attempt; no uncapped notification stack, and no six toasts for one 503.
- No `ChunkLoadError` left as a terminal error state (the recovery is a reload, not a message); **no unguarded auto-reload** (infinite loop on a broken build); no forced reload over unsaved work; no second, competing "new version" prompt beside the service worker's.
- **No `loginWithRedirect()` straight off a 401** — not before a single-flight refresh + one replay, and never from a page holding unsaved work; no per-request refresh (rotation stampede); no replayed request re-entering the ladder (refresh→401 loop); no logout triggered by a 403 or by a third-party host's 401; no redirect answer to a `fetch`/Server Action (return 401 JSON).
- No blind retry of a **timed-out** non-idempotent request (it may have succeeded server-side); no user-cancelled/unmounted request (`AbortError`) rendered as a failure or notified.
- No generic "No data" covering all three empty situations.
- No auto-retry on a non-idempotent mutation; no retry on a 4xx; no hand-rolled retry loop where TanStack Query's `retry` fits.
- No stale live data shown as current while the connection is down.
- No console-only client error (invisible = unlogged).
- No App-Router-only convention (`error.tsx`/`global-error.tsx`) emitted into a Vite SPA — use `react-error-boundary`.

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- Throw in a feature component → its boundary shows friendly content; the rest of the page still works; the report has the structured entry + correlation id; no `error.message` on screen.
- Make a fetch 500 → the region shows the **failed** state inline with a working retry, not a blank grid; the retry recovers on the next success; a transient 503 is absorbed by backoff without surfacing.
- With that 500 still failing: the **search bar, filters, and toolbar are still on screen and still interactive**, the filter text the user typed is intact, and only the rows area carries the error. Change a filter → the query re-runs.
- Simultaneously, **one** notification appears top-right with the friendly message + correlation id; it is **still there after 60s**; it closes only on the close button; failing the same call three times leaves one entry, not three.
- Mock a drifted response body (rename a field / return an object where an array is expected) → the region shows **failed** (not "no records") and notifies.
- **Hang the endpoint** (delay the response past the budget) → the region leaves loading at the deadline with a timeout-specific failed state and a working retry — it does **not** spin indefinitely; the soft "still loading" tier appeared first. Navigate away mid-request → it aborts silently (no failed state, no notification).
- **Load successfully, then fail the refetch** (poll or window-focus) → the rows are **still there**, marked stale with an "as of" time, one notification; the failed body never appears. Any action unsafe on stale data is disabled with a reason.
- Change a filter / page → no empty flash between results (`keepPreviousData`), and the new key's first load shows the loading state, not a stale marker.
- Fail two of three independent dashboard tiles → those two show failed states, the third still renders its data.
- **Fail a mutation** with an optimistic update in play → the row reverts **and** a notification says what didn't happen; the form still holds what was typed. Double-click submit → one request. Retry a timed-out write → the server dedupes on the idempotency key (one record, not two). Return 409 → a choice, not a retry. Return 422 → errors on the fields, no toast.
- **Break the backend entirely** (all endpoints 503) → the notification stack stays capped and rolled up (not one per region per attempt), auto-retry stops after k attempts with a manual Retry offered, and `Retry-After` is respected where sent.
- **Simulate a deploy across an open tab** (build, deploy, then navigate to a lazy route in the tab opened before it — or delete a chunk from the served build): the app recovers onto the new build with **one** reload, never loops, and a tab with unsaved work is prompted rather than reloaded.
- **Expire the session while a form is half-filled** (revoke the token / clock-skew the expiry), then trigger a save: the refresh fires **once** across all in-flight calls, the request replays, and the user sees nothing. Force the refresh to fail → the re-auth appears **in place**, the typed values are still there afterwards, and the original save completes. Confirm no second refresh loop on a repeated 401, and that a 403 shows permission-denied without touching the session.
- Drop the network → offline UX appears; the live region shows "reconnecting" (not stale-as-current); restore → it recovers.
- Empty each way (no records / no filter / filtered-out) → three distinct actionable messages.
- Force a client error → it reaches the server log / Sentry (not just the browser console); force a hydration mismatch → it is *reported*, not only logged to the console.
- Block the third-party hosts (flag provider, maps, analytics) at the network level → the app still renders, flags fall to their defaults, the map region shows its failed body, and **no** analytics toast appears.
- Fill `localStorage` to quota (or run in private mode) → the app renders and works with persistence degraded, no crash.
- Open the app in two tabs, sign out in one → the other stops rendering as signed-in.
- Leave a tab backgrounded past `staleTime` and return → it revalidates rather than showing yesterday's numbers as current.
- Delete a record in another tab, then act on its detail page → "no longer exists" with a way out, and the list no longer shows the row.

## Handoffs

- The categorized error this skill renders → [`data-fetching`](../data-fetching/SKILL.md) (produces it via `problemError`)
- Live WS/SSE socket + its reconnect/backoff + connection status → [`realtime`](../realtime/SKILL.md)
- Render/bundle performance → [`performance`](../performance/SKILL.md)
- Field-level validation errors → [`forms`](../forms/SKILL.md)
- Renderer unification (bind loading/failed once on the shared grid) → [`ui-rules`](../ui-rules/SKILL.md)
- Mounting the notification provider/portal in the library's idiom → [`component-library`](../component-library/SKILL.md)
- Test ids for the notification + failed regions → [`test-ids`](../test-ids/SKILL.md); E2E proof that the chrome survives → `qa-ui-typescript` (peer)
- Keeping filter/search state above the failing region (or in the URL) → [`state-management`](../state-management/SKILL.md)
- Token/refresh mechanics + the login surface the re-auth ladder calls into → `auth/auth0-react`
- Dirty-form state (`formState.isDirty`) that gates rung 4 of the ladder → [`forms`](../forms/SKILL.md)
- Client/server error export to Grafana → `observability/opentelemetry-node`
