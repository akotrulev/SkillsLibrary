---
name: data-fetching
description: Use when a React component fetches or writes data (Server Component fetch, TanStack Query, Server Actions, Suspense). Triggers "how should this load data". Not for pushed data (realtime).
disable-model-invocation: true
---

# React — Data Access (request/response lane)

Owns the **request/response transport lane**: a component asks for data and gets an answer, or writes and gets an outcome. The **live/push lane** — server-originated updates, streams, presence — is [`realtime`](../realtime/SKILL.md)'s. Both skills open with the same routing decision, so you land in the right one.

The standards are the fe-react rule files `react-data.md` and `react.md` (`.claude/rules/fe-react/` in the project, or `frontend/react/skills/rules/` until `/fe-react:rules` installs them); where this skill disagrees with a rule file, the rule file wins.

## Transport routing — which lane am I in?

Data the component pulls (it asks, the server answers once) is this skill's; data the server pushes is `realtime`'s.

| Signal | Lane | Skill |
|---|---|---|
| Load a page's list/detail; submit a form; paginate; search | request/response | **data-fetching** (here) |
| Dashboard tile updates itself; chat; presence; progress; server events | live/push | [`realtime`](../realtime/SKILL.md) |
| Slow query you want to *stream in* below a shell | request/response + `<Suspense>` | **data-fetching** (here) |

A surface often uses both: fetch the initial state here, then hand off to `realtime` for updates (it owns the seam).

**Version rule:** detect React/Next major first. **Next 15 changed the `fetch` default to uncached** (`cache: 'no-store'`): you opt *into* caching, where Next 14 cached by default. Server Actions + `useActionState` are React-19/Next-15 primary; the Vite SPA lane has no RSC or Server Actions and uses TanStack Query throughout.

## The core decision: fetch on the server by default

Where the component runs fixes how it should reach data:

| Component | Runs where | Reach data how |
|---|---|---|
| **Server Component** (default) | server | **`await` directly** in the body — `fetch` an API, or query the DB/service in-process. Pass the result down as props. |
| **Client Component** (`'use client'`) | browser | a **client hook** — TanStack Query against an API — only when the client genuinely owns fetching (caching, refetch, optimistic, infinite, polling) |
| **Server Action** (`'use server'`) | server, on invocation | write to the DB/API, then `revalidatePath`/`revalidateTag` — the mutation counterpart of a Server Component read |

The server default runs once, ships no fetching JS, keeps secrets server-side and avoids a client waterfall. The *client* owns the request lifecycle only for a filter that refetches without a navigation, infinite scroll, polling, an optimistic mutation, or a Vite SPA (no server to fetch on). Fetch logic lives in a **data module** (`features/orders/data.ts` server functions · `features/orders/useOrders.ts` client hooks), so the component names the data function, not the transport.

### Server lane — fetch or query directly in the RSC

```tsx
import 'server-only';
import { cache } from 'react';

export const getOrders = cache(async (): Promise<OrderDto[]> => {
  const res = await fetch(`${env.API_URL}/orders`, {
    headers: { authorization: `Bearer ${await getServerToken()}` },
    next: { revalidate: 60, tags: ['orders'] },
  });
  if (!res.ok) throw await problemError(res);
  return res.json();
});
```

```tsx
import { getOrders } from '@/features/orders/data';

export default async function OrdersPage() {
  const orders = await getOrders();
  return <OrderTable orders={orders} />;
}
```

`features/orders/data.ts` is a `server-only` module imported by Server Components and Actions, never by a client file. React `cache()` dedupes identical calls within one render pass. The token comes from the auth layer, `revalidate` opts into caching (Next 15 defaults to no-store), and `problemError` throws a categorized error to the nearest error boundary.

- **`fetch` caching (Next):** `next: { revalidate: n }` for time-based ISR, `next: { tags: [...] }` for on-demand `revalidateTag`, `cache: 'force-cache'` for build-time static, `cache: 'no-store'` for always-dynamic. State what you cache; in Next 15 uncached is the default.
- **Direct DB/service access** is allowed and encouraged in Server Components/Actions (no HTTP hop to your own API) — but that module is **`server-only`**; a Client Component importing it is a build error, and rightly so (it would ship your DB creds).
- **Base URLs and the token come from config/the auth layer**, never a hardcoded/`localhost` literal ([`project-setup`](../project-setup/SKILL.md) env hygiene; token is IdP-neutral — Auth0 *or* Cognito).

### Client lane — TanStack Query (when the client owns fetching)

```tsx
'use client';
import { useQuery } from '@tanstack/react-query';

export function useOrders(customerId: string) {
  return useQuery({
    queryKey: ['orders', customerId],
    queryFn: ({ signal }) => api.get<OrderDto[]>(`/orders?customerId=${customerId}`, { signal }),
    staleTime: 30_000,
  });
}
```

`staleTime: 30_000` keeps the data fresh for 30s, so no refetch storm. The `signal` TanStack Query passes is an `AbortSignal`: thread it into `fetch` so navigating away **cancels** the in-flight request.

**Every call also carries a deadline** composed with that cancel signal: the `budget()` helper and the per-endpoint budgets are in [`error-handling`](../error-handling/SKILL.md) (Timeouts). `problemError`/`toAppError` keeps `TimeoutError` (a surfaced failure) apart from `AbortError` (not a failure, never rendered or notified), and server-side reads (RSC, Server Actions) take the same budget.

Set up one `QueryClient` in a `'use client'` provider mounted from the root layout; on the App Router, **hydrate** server-prefetched queries so the client doesn't refetch what the server already has.

### Writes — Server Actions (App Router primary)

```tsx
'use server';
import { revalidateTag } from 'next/cache';

export async function createOrder(input: CreateOrderInput) {
  const created = await db.orders.create(input);
  revalidateTag('orders');
  return created;
}
```

A Server Action is an `async` server function callable from a Client Component (or a `<form action>`); the write is a DB call or a POST to the API, and `revalidateTag` invalidates the cached read so the next render is fresh, with no client cache to invalidate and no API route to hand-roll. **Form** submission through actions (`useActionState`, field errors, pending) is [`forms`](../forms/SKILL.md)'s; this skill owns the imperative read/write mechanics. **Vite SPA lane:** no Server Actions — writes go through a TanStack Query `useMutation` that POSTs and `invalidateQueries` on success.

## No double-fetch — RSC fetches once

React's classic prerender double-fetch mostly **doesn't exist on the App Router**: a Server Component runs on the server, its result is serialized into the payload, and the client **never re-runs that fetch**. Two things keep it that way:

- **`cache()`** (React) memoizes identical data calls within a single render pass, so `getOrders()` called from both the page and its metadata runs once.
- When a **Client Component** needs server-fetched data, **prefetch on the server and hydrate** (TanStack Query `HydrationBoundary` / passing a resolved promise to `use()`), rather than refetching in a client `useEffect`. Reading data in a client `useEffect` that the server already had is the double-fetch — avoid it.

## Streaming slow data with `<Suspense>`

When one region is slow but the shell can paint now, wrap the slow async Server Component in `<Suspense>` — Next streams the fallback first, then the resolved content :

```tsx
export default function ReportPage() {
  return (
    <>
      <ReportHeader />
      <Suspense fallback={<TableSkeleton data-testid="Report.Loading" />}>
        <SlowReport />
      </Suspense>
    </>
  );
}
```

`SlowReport` is an async Server Component that awaits `getSlowReport()`. A route-level `loading.tsx` is the implicit `<Suspense>` for the whole segment. Streaming is still request/response; live updates after paint are [`realtime`](../realtime/SKILL.md).

## Composing several calls — critical vs optional, and dependent chains

A page rarely makes one request. How the calls **compose** decides whether one weak dependency can take the page down — and this is not derivable from the per-region state rules, because it's a decision made before any region renders.

**Classify every call on the page as critical or optional.** Critical = the page is meaningless without it (the order you're viewing). Optional = it enriches (a recommendations strip, a "3 related tickets" badge, an activity feed). Then:

```ts
const [order, recommendations] = await Promise.all([getOrder(id), getRecommendations(id)]);
```

Wrong, above: `Promise.all` rejects on the first failure, so a dead recommendations service 500s the whole order page. Right, below: the critical call decides the page, and the optional call degrades in place.

```ts
const order = await getOrder(id);
const [recs] = await Promise.allSettled([getRecommendations(id)]);
const recommendations = recs.status === 'fulfilled' ? recs.value : null;
```

A throw from `getOrder` is the page's failed state, correctly, and a `null` recommendations section renders its own failed body.

- **`Promise.all` is for calls that are critical *together*.** The moment one member is optional, it's `allSettled` — otherwise you've promoted a nice-to-have into a single point of failure. This is the composition-level form of the failure-scoping rule.
- **An optional failure is still reported** (logged, and notified once if the user would otherwise wonder why a section is missing), because a section that degrades silently and invisibly disappears for a month.
- **Dependent chains must not fire, and must not spin.** Gate query B on A's result (`enabled: !!a.data` in TanStack) so it doesn't fire with `undefined`, and resolve the gate to a **state**: if A failed, B is *unavailable because A failed*, never a skeleton left rendering forever.
- **Render partial success**: two of three sections resolving means two render their data and one its failed body, never a whole-page error.
- **Sequential `await`s that don't depend on each other are a waterfall**, not composition — parallelize them ([`performance`](../performance/SKILL.md)).

### Failure scoping in the RSC lane **[App]**

An uncaught throw in a Server Component escalates to the **segment's** `error.tsx`, which replaces the whole route, search bar and filters included. **The App Router default violates the failure-scoping rule by construction**, so scope it deliberately:

- Put the failable read in its **own async Server Component** wrapped in `<Suspense>` *and* a region-level boundary (`react-error-boundary` in a small client wrapper, since `error.tsx` exists only per segment), so fallback and failure land in that region.
- Or **don't throw**: have the data function return a typed `Result` and render the failed body inline. Prefer this when the region is one of several on a dashboard.
- **Server Actions return `{ ok: false, error }` for expected failures** and throw only for exceptional ones, because a thrown Action error reaches the client as a generic error with no field mapping or correlation id ([`forms`](../forms/SKILL.md) renders it).

## Correctness rules folded from the field

Each is a real defect class in data-driven React apps:

- **Never index a route/descriptor map unchecked** (`routes['read']`). A checked access **fails diagnosably**, so a missing key never surfaces as `undefined` flowing into a URL and 404-ing silently: `` if (!(name in routes)) throw new Error(`No '${name}' route. Known: ${Object.keys(routes)}`) ``.
- **Substitute URL templates by name, then assert none remain** (`if (/\{[^}]+\}/.test(url)) throw …`), because `t.replace('{id}', id)` against a template using `{accountId}` ships a literal `{accountId}`. An unsubstituted lookup route whose 404 is swallowed yields **silently empty dropdowns**, the worst failure, because nothing *looks* broken.
- **Parse the response to the endpoint's real shape** with the resource's Zod schema (`Schema.parse(await res.json())`), so a drifted field fails at the boundary, not three components deep. **A parse failure is an error, not an emptiness**: throw the categorized `AppError` (the `problemError` shape, with its own code) so the consumer renders the *failed* state and notifies, instead of a `catch` into `[]`/`null` that turns a broken contract into a silent "no records".
- **A tab that comes back from the dead must not render yesterday's data as current.** A reopened laptop, a bfcache restore or a refocused background tab never unmounted the component, so nothing refetched. Keep TanStack Query's `refetchOnWindowFocus`/`refetchOnReconnect` on and tune `staleTime` instead. Where a surface has no query library, refetch on `visibilitychange` + `online` and show the stale marker while it revalidates ([`error-handling`](../error-handling/SKILL.md)).
- **A response must never land out of order.** If the request for `"ac"` resolves after the one for `"acme"`, **the UI shows results for a query the user has already replaced**, with no error to notice. **Key the query by every parameter it depends on** (`queryKey: ['orders', search, filters, page]`) and TanStack discards the answer to a key you're no longer on. On a hand-rolled `useEffect` fetch, set an `ignore` flag (or abort) in the cleanup and check it before `setState`:

  ```ts
  useEffect(() => {
    let ignore = false;
    getOrders(search).then(r => { if (!ignore) setRows(r); });
    return () => { ignore = true; };
  }, [search]);
  ```

  The same cleanup kills the stale-closure variant. **A fetch in an effect without a cleanup guard is a data-correctness bug.**
- **Contract-test the UI's DTOs and routes against the API spec** (OpenAPI) — drift between a typed client and the spec is caught mechanically in CI, not by a user staring at a blank pane. Hand off to `qa/typescript/skills/api-contract-testing` (peer).

## ProblemDetails → UI error mapping

Route every call through one helper that reads RFC-7807 `ProblemDetails`, surfaces `title`/`detail` as a friendly message (or a generic message + correlation id for unknowns), and logs the raw detail server-side:

```tsx
export async function problemError(res: Response): Promise<AppError> {
  const problem = await res.json().catch(() => null) as ProblemDetails | null;
  const correlationId = res.headers.get('x-correlation-id') ?? undefined;
  logger.warn({ status: res.status, url: res.url, detail: problem?.detail }, 'api error');
  return new AppError(problem?.title ?? 'Something went wrong.', { correlationId, status: res.status });
}
```

Throwing this from a Server Component surfaces it at the nearest `error.tsx` boundary; a client hook exposes it as `query.error`. [`error-handling`](../error-handling/SKILL.md) renders it in the three-state region.

## Validation

Done when every line holds.

- The project's build and typecheck scripts run clean.
- A Server-Component route ships no fetching JS, and the Network panel shows one fetch, server-side.
- A Server Action that `revalidateTag`s updates the list without a manual refresh.
- Navigating away from a client query aborts the in-flight request, with no failed state and no notification.
- Typing fast with the slowest response served first leaves the rows matching the current input.
- Failing one optional endpoint shows that section's failed body and the rest of the page renders; failing the critical one shows the page's failed state; failing a parent in a dependent chain shows the child as unavailable, not an endless skeleton.
- Delaying an endpoint past its budget rejects with a `TimeoutError` at the deadline and renders the timeout failed state.
- The contract test is green against the OpenAPI spec.
