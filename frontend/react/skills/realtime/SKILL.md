---
name: realtime
description: Use when a surface needs LIVE / server-pushed data — SSE from a route handler + `EventSource` hook, a WebSocket hook with backoff reconnection, the snapshot→live-channel handoff, connection-status affordance, TanStack Query invalidate-on-message. Triggers: "push updates to the UI", "SSE / WebSocket in React", "live dashboard/chat", "reconnect UX", "the socket reconnects in a loop". Do NOT use for request/response fetching (`data-fetching`) or the error/reconnect UI itself (`error-handling`).
---

# React — Realtime (live / push lane)

Owns the **live/push transport lane**: data arrives at the component *without it asking*. The **request/response lane** — the component asks, the server answers once — is [`data-fetching`](../data-fetching/SKILL.md)'s. Both skills open with the same routing decision.

## Transport routing — which lane am I in?

```
Is the data pushed by the server (it arrives without the component asking)?
  YES → live / push / stream  → THIS skill (realtime)
Is the data pulled by the component (it asks, the server answers once per request)?
  YES → request/response      → `data-fetching`
```

| Signal | Lane | Skill |
|---|---|---|
| Dashboard tile updates itself; ticker; chat; presence; progress; notifications | live/push | **realtime** (here) |
| Load a list/detail; submit a form; paginate; search | request/response | [`data-fetching`](../data-fetching/SKILL.md) |
| Slow query streamed below a shell (`<Suspense>`) | request/response | [`data-fetching`](../data-fetching/SKILL.md) |
| Third-party feed over WebSocket/SSE | live/push | **realtime** (here) |

Most live surfaces do **both**: [`data-fetching`](../data-fetching/SKILL.md) fetches the initial state (server-side, once), then this skill's live channel takes over. The **snapshot→live handoff** (below) is the seam.

## Live data is always a Client Component

There is no server-push equivalent of Blazor's circuit here: a **Server Component renders once and is done** — it holds no open channel. Every live surface is a **`'use client'` island** that opens the channel (`EventSource` / `WebSocket`) in an effect and tears it down on unmount. The RSC parent fetches the initial snapshot and passes it as a prop; the client island subscribes for updates. Keep the island small — only the live-updating subtree is client; the rest of the page stays a Server Component.

**Choose the channel:**

| Need | Channel |
|---|---|
| Server → client only (dashboards, tickers, notifications, progress, streamed tokens) | **SSE** — simpler, auto-reconnects, rides plain HTTP, no extra infra |
| Bidirectional (chat, collaborative editing, games, client→server signalling) | **WebSocket** |
| A managed realtime backend already in play (Pusher, Ably, Supabase Realtime, socket.io) | its SDK — same client-island + cleanup rules apply |

Default to **SSE** for one-directional push — it's the lightest thing that works and survives proxies. Reach for WebSocket only when the client must send too.

## SSE — server → client push

### The server (App Router route handler)

```ts
// app/api/prices/route.ts — streams text/event-stream
export const dynamic = 'force-dynamic';           // never cache a live stream

export async function GET(req: Request) {
  const stream = new ReadableStream({
    start(controller) {
      const enc = new TextEncoder();
      const send = (tick: PriceTick) =>
        controller.enqueue(enc.encode(`data: ${JSON.stringify(tick)}\n\n`));
      const unsub = priceBus.subscribe(send);       // your broker / pub-sub
      req.signal.addEventListener('abort', () => { unsub(); controller.close(); }); // client left → clean up
    },
  });
  return new Response(stream, {
    headers: { 'content-type': 'text/event-stream', 'cache-control': 'no-store', connection: 'keep-alive' },
  });
}
```

### The client hook

```tsx
// features/prices/useSSE.ts
'use client';
import { useEffect, useRef, useState } from 'react';

type Status = 'connecting' | 'open' | 'closed';

export function useSSE<T>(url: string, onMessage: (data: T) => void) {
  const [status, setStatus] = useState<Status>('connecting');
  const cb = useRef(onMessage);
  cb.current = onMessage;                          // latest handler without re-subscribing

  useEffect(() => {
    const es = new EventSource(url, { withCredentials: true }); // sends the auth cookie
    es.onopen = () => setStatus('open');
    es.onmessage = (e) => cb.current(JSON.parse(e.data) as T);
    es.onerror = () => setStatus('closed');        // EventSource auto-reconnects with backoff
    return () => es.close();                        // always close on unmount
  }, [url]);

  return status;
}
```

```tsx
'use client';
export function PriceTicker({ initial }: { initial: PriceTick }) {   // initial = server snapshot (data-fetching)
  const [price, setPrice] = useState(initial.price);
  const status = useSSE<PriceTick>('/api/prices', (t) => setPrice(t.price));
  return (
    <div>
      <span data-testid="Ticker.Price">{price}</span>
      <ConnectionBadge status={status} />           {/* stale-data affordance — mandatory */}
    </div>
  );
}
```

- **`EventSource` reconnects automatically** with a growing backoff; `onerror` fires on each drop. Surface it as a **connection-status affordance** so the user knows the data may be stale.
- **The channel is a Client Component effect** — never open an `EventSource` during render or in a Server Component.
- **Auth is provider-neutral** — `withCredentials` sends the auth cookie; if the stream needs a bearer token instead, SSE can't set headers, so proxy through a same-origin route handler that attaches it server-side (token from the auth layer — Auth0 *or* Cognito, `auth/auth0-react`).

## WebSocket — bidirectional

```tsx
// features/chat/useWebSocket.ts
'use client';
import { useEffect, useRef, useState } from 'react';

export function useWebSocket(url: string, onMessage: (data: unknown) => void) {
  const [status, setStatus] = useState<'connecting' | 'open' | 'closed'>('connecting');
  const ws = useRef<WebSocket | null>(null);
  const cb = useRef(onMessage); cb.current = onMessage;

  useEffect(() => {
    let closed = false;
    let retry = 0;
    const connect = () => {
      const socket = new WebSocket(url);
      ws.current = socket;
      socket.onopen = () => { retry = 0; setStatus('open'); };
      socket.onmessage = (e) => cb.current(JSON.parse(e.data));
      socket.onclose = () => {
        setStatus('closed');
        if (!closed) setTimeout(connect, Math.min(1000 * 2 ** retry++, 30_000)); // capped exponential backoff
      };
    };
    connect();
    return () => { closed = true; ws.current?.close(); };  // stop retrying + close on unmount
  }, [url]);

  const send = (msg: unknown) => ws.current?.readyState === WebSocket.OPEN && ws.current.send(JSON.stringify(msg));
  return { status, send };
}
```

- **`WebSocket` does not auto-reconnect** — you own the backoff loop (capped exponential above), and you **must stop retrying on unmount** (the `closed` flag) or a navigated-away component reconnects forever.
- **Dedupe at-least-once feeds by message key** — redelivered messages must not double-apply; key each and drop repeats.
- **Backpressure:** on a high-rate feed, batch/throttle UI updates (coalesce ticks per animation frame) so you don't re-render on every frame.

## Snapshot → live handoff

Fetch the initial state server-side via [`data-fetching`](../data-fetching/SKILL.md) so first paint shows real data (no flash, no client waterfall), pass it as a prop, and let the client channel take over:

```tsx
// app/dashboard/page.tsx — Server Component
import { getSnapshot } from '@/features/dashboard/data';
export default async function DashboardPage() {
  const snapshot = await getSnapshot();             // request/response — fills first paint
  return <LiveDashboard initial={snapshot} />;       // client island — subscribes for updates
}
```

This is the exact seam between the lanes: **data-fetching owns the snapshot, realtime owns the stream.**

## Integrating with TanStack Query

If the surface already uses TanStack Query, don't hand-manage a parallel copy of the data — let the push **invalidate or patch** the cache: on a message, `queryClient.invalidateQueries({ queryKey })` (refetch the authoritative value) or `setQueryData` (patch it in for a hot feed). The query stays the source of truth; the socket is just a change signal.

## Scale-out

SSE and WebSocket connections are **stateful and pinned to one server instance**, so behind a load balancer you need **sticky sessions** *and* a **pub/sub backplane** (Redis, NATS, a managed realtime service) so an event produced on instance A reaches a client connected to instance B. On serverless/edge hosts, long-lived connections may be time-boxed or unsupported — use a managed realtime provider (Pusher/Ably/Supabase) there rather than a raw route-handler stream.

## Rules

- **Open every live feature with the transport routing decision**: push → here; pull → [`data-fetching`](../data-fetching/SKILL.md).
- **Live data is a small `'use client'` island** — the channel opens in an effect and is **always torn down on unmount** (`es.close()` / `ws.close()`, and stop the WS retry loop).
- **Default to SSE** for one-directional push; WebSocket only when the client must send.
- **The RSC fetches the initial snapshot**, passes it as a prop; the client island subscribes — no flash, no double-fetch (the [`data-fetching`](../data-fetching/SKILL.md) handoff).
- **Connection-status affordance is mandatory** — surface connecting/open/closed so the user knows data may be stale (the full reconnect UX is [`error-handling`](../error-handling/SKILL.md)'s).
- **Dedupe at-least-once feeds by key; throttle high-rate updates.**
- **If TanStack Query is in play, push invalidates/patches the cache** — don't keep a parallel copy.
- **Auth is IdP-neutral** — cookie via `withCredentials`, or a same-origin proxy route that attaches the bearer token server-side.
- **Scale-out: sticky sessions + a pub/sub backplane**; a managed provider on serverless/edge.
- **Every live element carries a `data-testid`** per [`test-ids`](../test-ids/SKILL.md); the connection-status control included.

## What NOT to do

- No opening `EventSource`/`WebSocket` during render or in a Server Component — effects only, in a client island.
- No channel left open on unmount; no WebSocket retry loop that keeps reconnecting after the component is gone.
- No live channel on a static page without promoting the live subtree to a `'use client'` island first.
- No re-subscribing every render because the message handler isn't held in a ref.
- No stale UI without a connection-status affordance during reconnect.
- No un-deduped at-least-once feed (double-applied updates); no unthrottled high-rate feed re-rendering per frame.
- No parallel hand-managed copy of data that TanStack Query already owns — invalidate/patch instead.
- No raw route-handler stream on a serverless/edge host that time-boxes connections — use a managed provider.

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- The project's own build and typecheck scripts (run with the package manager `packageManager` names) clean.
- Drop the connection (kill the server / go offline) → status affordance flips to closed; SSE auto-reconnects, the WS hook reconnects with backoff and stops when the component unmounts.
- Navigate away from a live page → the channel closes; no post-unmount `setState` warning, no lingering socket in DevTools.
- No flash on a snapshot→live page — the server snapshot renders, then live updates continue.
- Scale-out smoke: an event produced on instance A reaches a client on instance B (backplane wired).

## Handoffs

- Initial-state fetch + the shared routing matrix → [`data-fetching`](../data-fetching/SKILL.md)
- Reconnect UX, three-state failure region → [`error-handling`](../error-handling/SKILL.md)
- Channel auth token (Auth0 / Cognito) → `auth/auth0-react`
- Testids on live elements → [`test-ids`](../test-ids/SKILL.md)
- **Testing** these streams → `qa/typescript/skills/realtime-stream-testing` (peer); **connection-count load** → `qa-performance-typescript` (peer)
