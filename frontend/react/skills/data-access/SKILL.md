---
name: fe-react-data-access
description: Use when the user asks how a React component should FETCH or WRITE request/response data (Next.js App Router primary, Vite SPA fallback) — Server Component `fetch`/DB reads with `cache`/`revalidate` vs client TanStack Query, Server Actions for mutations with `revalidatePath`/`revalidateTag`, ProblemDetails→UI error mapping, streaming with `<Suspense>`, the RSC "no double-fetch" story, and cancellation with `AbortSignal`. Triggers "how should this component load data", "fetch in a Server Component or with TanStack Query", "call my API from React", "Server Action to create/update X", "revalidate after a mutation", "stream slow data", "map ProblemDetails to a friendly error". Do NOT use for live/server-pushed data (use `frontend/react/skills/realtime`), forms/validation UX (use `frontend/react/skills/forms`), auth token wiring itself (use `auth/auth0-react`), or where fetched state lives (use `frontend/react/skills/state-management`).
---

# React — Data Access (request/response lane)

Owns the **request/response transport lane**: a component asks for data and gets an answer, or writes and gets an outcome. The **live/push lane** — server-originated updates, streams, presence — is [`realtime`](../realtime/SKILL.md)'s. Both skills open with the same routing decision so you land in the right one.

## Transport routing — which lane am I in?

```
Is the data pulled by the component (it asks, the server answers once per request)?
  YES → request/response      → THIS skill (data-access)
Is the data pushed by the server (it arrives without the component asking)?
  YES → live / push / stream  → `realtime`
```

| Signal | Lane | Skill |
|---|---|---|
| Load a page's list/detail; submit a form; paginate; search | request/response | **data-access** (here) |
| Dashboard tile updates itself; chat; presence; progress; server events | live/push | [`realtime`](../realtime/SKILL.md) |
| Slow query you want to *stream in* below a shell | request/response + `<Suspense>` | **data-access** (here) |
| Third-party feed over WS/SSE | live/push | [`realtime`](../realtime/SKILL.md) |

A surface often uses both: fetch the initial state here, then hand off to `realtime` for updates (the snapshot→live handoff — [`realtime`](../realtime/SKILL.md) owns the seam).

**Version rule:** detect React/Next major first. **Next 15 changed the `fetch` default to uncached** (`cache: 'no-store'`) — you opt *into* caching; Next 14 cached by default and you opted out. Server Actions + `useActionState` are React-19/Next-15 primary; the Vite SPA lane has no RSC or Server Actions and uses TanStack Query throughout.

## When to use

- Deciding how a route/component loads or writes data
- Fetching in a Server Component (with caching/revalidation) vs a client TanStack Query hook
- Writing a Server Action mutation and revalidating the affected data
- Mapping API errors (ProblemDetails) to UI without leaking raw detail
- Streaming a slow query below a shell; cancelling an in-flight request

## When NOT to use

- Live/server-pushed data → [`realtime`](../realtime/SKILL.md)
- Form submit UX, validation, field errors → [`forms`](../forms/SKILL.md)
- The token-attaching auth layer itself → `auth/auth0-react` (this skill *consumes* it)
- Where state should live after fetch → [`state-management`](../state-management/SKILL.md)
- Three-state loading/failed regions + retry UX → [`error-resilience`](../error-resilience/SKILL.md)
- Writing the API/DTOs or contract tests → `qa/typescript/skills/{api-dto-writer,contract-testing-pact}` (peers)

## The core decision: fetch on the server by default

Where the component runs fixes how it should reach data:

| Component | Runs where | Reach data how |
|---|---|---|
| **Server Component** (default) | server | **`await` directly** in the body — `fetch` an API, or query the DB/service in-process. Pass the result down as props. |
| **Client Component** (`'use client'`) | browser | a **client hook** — TanStack Query against an API — only when the client genuinely owns fetching (caching, refetch, optimistic, infinite, polling) |
| **Server Action** (`'use server'`) | server, on invocation | write to the DB/API, then `revalidatePath`/`revalidateTag` — the mutation counterpart of a Server Component read |

**Default to fetching in the Server Component and passing props.** It runs once, ships no fetching JS, keeps secrets server-side, and avoids a client waterfall. Reach for a client hook (TanStack Query) only when the *client* must own the request lifecycle — a filter that refetches without a navigation, infinite scroll, polling, optimistic mutation, or a Vite SPA (no server to fetch on). Keep fetch logic in a **data module** (`features/orders/data.ts` server functions · `features/orders/useOrders.ts` client hooks), never inline in the component — the component names the data function, not the transport.

### Server lane — fetch or query directly in the RSC

```tsx
// features/orders/data.ts — server-only module; import into Server Components/Actions, never a client file
import 'server-only';
import { cache } from 'react';

// React cache() dedupes identical calls within one server render pass (request memoization).
export const getOrders = cache(async (): Promise<OrderDto[]> => {
  const res = await fetch(`${env.API_URL}/orders`, {
    headers: { authorization: `Bearer ${await getServerToken()}` }, // IdP-neutral token — from the auth layer
    next: { revalidate: 60, tags: ['orders'] },                     // opt into caching (Next 15 default is no-store)
  });
  if (!res.ok) throw await problemError(res);                       // categorized error → nearest error boundary
  return res.json();
});
```

```tsx
// app/orders/page.tsx — a Server Component: fetch once, render, ship no fetching JS
import { getOrders } from '@/features/orders/data';

export default async function OrdersPage() {
  const orders = await getOrders();
  return <OrderTable orders={orders} />; // pass data down as serializable props
}
```

- **`fetch` caching (Next):** `next: { revalidate: n }` for time-based ISR, `next: { tags: [...] }` for on-demand `revalidateTag`, `cache: 'force-cache'` for build-time static, `cache: 'no-store'` for always-dynamic. In **Next 15 uncached is the default** — be explicit about what you cache.
- **Direct DB/service access** is allowed and encouraged in Server Components/Actions (no HTTP hop to your own API) — but that module is **`server-only`**; a Client Component importing it is a build error, and rightly so (it would ship your DB creds).
- **Base URLs and the token come from config/the auth layer**, never a hardcoded/`localhost` literal ([`project-scaffold`](../project-scaffold/SKILL.md) env hygiene; token is IdP-neutral — Auth0 *or* Cognito).

### Client lane — TanStack Query (when the client owns fetching)

```tsx
'use client';
import { useQuery } from '@tanstack/react-query';

export function useOrders(customerId: string) {
  return useQuery({
    queryKey: ['orders', customerId],
    queryFn: ({ signal }) => api.get<OrderDto[]>(`/orders?customerId=${customerId}`, { signal }),
    staleTime: 30_000,          // fresh for 30s — no refetch storm
  });
}
```

The `signal` TanStack Query passes is an `AbortSignal` — thread it into `fetch` so navigating away **cancels** the in-flight request (the React analog of Blazor's cancel-on-dispose). Set up one `QueryClient` in a `'use client'` provider mounted from the root layout; on the App Router, **hydrate** server-prefetched queries so the client doesn't refetch what the server already has.

### Writes — Server Actions (App Router primary)

```tsx
// features/orders/actions.ts
'use server';
import { revalidateTag } from 'next/cache';

export async function createOrder(input: CreateOrderInput) {
  const created = await db.orders.create(input);   // or a POST to the API
  revalidateTag('orders');                         // invalidate the cached read → UI reflects the write
  return created;
}
```

A Server Action is an `async` server function callable from a Client Component (or a `<form action>`); after the write it **revalidates** the affected cache tag/path so the next render is fresh — no client cache to invalidate, no API route to hand-roll. **Form** submission through actions (`useActionState`, field errors, pending) is [`forms`](../forms/SKILL.md)'s; this skill owns the imperative read/write mechanics. **Vite SPA lane:** no Server Actions — writes go through a TanStack Query `useMutation` that POSTs and `invalidateQueries` on success.

## No double-fetch — RSC fetches once

React's classic prerender-double-fetch (Blazor's `[PersistentState]` problem) mostly **doesn't exist on the App Router**: a Server Component runs on the server, its result is serialized into the payload, and the client **never re-runs that fetch**. Two things keep it that way:

- **`cache()`** (React) memoizes identical data calls within a single render pass, so `getOrders()` called from both the page and its metadata runs once.
- When a **Client Component** needs server-fetched data, **prefetch on the server and hydrate** (TanStack Query `HydrationBoundary` / passing a resolved promise to `use()`), rather than refetching in a client `useEffect`. Reading data in a client `useEffect` that the server already had is the double-fetch — avoid it.

## Streaming slow data with `<Suspense>`

When one region is slow but the shell can paint now, wrap the slow async Server Component in `<Suspense>` — Next streams the fallback first, then the resolved content (the analog of Blazor `[StreamRendering]`):

```tsx
export default function ReportPage() {
  return (
    <>
      <ReportHeader />
      <Suspense fallback={<TableSkeleton data-testid="Report.Loading" />}>
        <SlowReport />        {/* async Server Component: await getSlowReport() */}
      </Suspense>
    </>
  );
}
```

A route-level `loading.tsx` is the implicit `<Suspense>` for the whole segment. Streaming is still request/response — it just splits the response; live updates after paint are [`realtime`](../realtime/SKILL.md).

## Correctness rules folded from the field

Each is a real defect class in data-driven React apps:

- **Never index a route/descriptor map unchecked** (`routes['read']`). Use a checked access that **fails diagnosably** — a missing key must not surface as `undefined` flowing into a URL and 404-ing silently: `` if (!(name in routes)) throw new Error(`No '${name}' route. Known: ${Object.keys(routes)}`) ``.
- **URL-template building must throw on any unsubstituted `{placeholder}`.** Copy-pasted substitution (`t.replace('{id}', id)` against a template that uses `{accountId}`) ships a literal `{accountId}` = guaranteed 404. Substitute by name, then assert none remain (`if (/\{[^}]+\}/.test(url)) throw …`). A lookup endpoint whose route param isn't substituted from context and whose 404 is swallowed yields **silently empty dropdowns** — the worst failure, nothing *looks* broken.
- **Parse the response to the endpoint's real shape** — validate with the resource's Zod schema (`Schema.parse(await res.json())`) so a single-object endpoint isn't read as an array (yielding `undefined` + a blank section) and a drifted field fails loudly at the boundary, not three components deep.
- **Contract-test the UI's DTOs and routes against the API spec** (OpenAPI) — drift between a typed client and the spec is caught mechanically in CI, not by a user staring at a blank pane. Hand off to `qa/typescript/skills/contract-testing-pact` (peer).

## ProblemDetails → UI error mapping

**Never render a raw response body or `error.message` to the user** — bodies may be JSON or stack traces. Route every call through one helper that reads RFC-7807 `ProblemDetails`, surfaces `title`/`detail` as a friendly message (or a generic message + correlation id for unknowns), and logs the raw detail server-side:

```tsx
export async function problemError(res: Response): Promise<AppError> {
  const problem = await res.json().catch(() => null) as ProblemDetails | null;
  const correlationId = res.headers.get('x-correlation-id') ?? undefined;
  logger.warn({ status: res.status, url: res.url, detail: problem?.detail }, 'api error'); // server-side only
  return new AppError(problem?.title ?? 'Something went wrong.', { correlationId, status: res.status });
}
```

Throwing this from a Server Component surfaces it at the nearest `error.tsx` boundary; a client hook exposes it as `query.error`. The **three-state region** that renders the failure inline with retry is [`error-resilience`](../error-resilience/SKILL.md)'s job — this skill produces the categorized error; that skill renders it.

## Rules

- **Open every data feature with the transport routing decision**: pull → here; push → [`realtime`](../realtime/SKILL.md).
- **Fetch on the server by default** (RSC `await` + props); reach for a client TanStack Query hook only when the client owns the request lifecycle or there's no server (Vite SPA).
- **Keep fetch logic in a data module** (`server-only` server functions · client hooks), never inline in the component; the component names the data function.
- **Be explicit about caching** — `revalidate`/`tags`/`force-cache`/`no-store` (Next 15 default is uncached); mutate with a **Server Action** that `revalidateTag`/`revalidatePath`.
- **No HTTP hop to your own API from a Server Component** — query the service/DB in-process; mark the module `server-only`.
- **Prefetch+hydrate** server data needed by a Client Component; never re-fetch in `useEffect` what the server already had.
- **Thread `AbortSignal`** into client fetches; cancel on unmount/navigation.
- **Checked map access; throw on unsubstituted `{placeholder}`; parse to the endpoint's real shape (Zod); contract-test against the spec.**
- **ProblemDetails → friendly text + correlation id; raw detail logged server-side, never rendered.**
- **Base URLs + external hosts from config**; the token is IdP-neutral, from the auth layer.

## What NOT to do

- No transport-specific fetch code inline in a component; no fetching in a client `useEffect` when the Server Component could fetch and pass props.
- No `server-only` module (DB creds, secrets) imported into a `'use client'` file.
- No `.then()`-swallowed error surfaced as a blank section (that's a three-state region — [`error-resilience`](../error-resilience/SKILL.md)); no raw `error.message`/response body rendered to users.
- No unchecked map indexing of routes; no template sent with an unsubstituted placeholder; no single-object endpoint parsed as an array.
- No hardcoded/`localhost` base URLs; no token-attaching layer hand-rolled here (it's auth's, provider-neutral).
- No client store holding server data (that's TanStack Query/RSC — [`state-management`](../state-management/SKILL.md)); no `await` in a Client Component body.
- No assuming `fetch` is cached on Next 15 (it isn't) — opt in explicitly.

## Validation

- `pnpm build` + typecheck clean.
- Prerender/network smoke: a Server-Component route ships **no fetching JS** and its data isn't re-fetched on the client (Network shows one fetch, server-side).
- A mutation via Server Action `revalidateTag`s and the list reflects the change without a manual refresh.
- Navigate away from a client query → the in-flight request **aborts** (no post-unmount state update warning).
- Contract test green against the OpenAPI spec.

## Handoffs

- Live/push updates after first paint → [`realtime`](../realtime/SKILL.md) (shares this routing matrix)
- Render the failed/loading states, retry UX → [`error-resilience`](../error-resilience/SKILL.md)
- Where fetched state lives → [`state-management`](../state-management/SKILL.md)
- Forms/submit UX → [`forms`](../forms/SKILL.md)
- Token layer (Auth0 / Cognito) → `auth/auth0-react`
- DTOs + contract tests → `qa/typescript/skills/{api-dto-writer,contract-testing-pact}` (peers)
