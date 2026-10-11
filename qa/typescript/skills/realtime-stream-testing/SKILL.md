---
name: qa-realtime-stream-testing-typescript
description: Use when testing real-time **WebSocket** and **Server-Sent-Events (SSE)** streams in Node 24 (22 supported) + TypeScript (Vitest / Playwright). Triggers: "test our WebSocket chat endpoint with ws", "assert the server pushes N SSE events then closes", "wait for a websocket frame without a setTimeout". Do NOT use for request/response HTTP (`qa-api-test-writer-typescript`) or broker messages (`qa-messaging-testing-typescript`).
---

# WebSocket & SSE Testing (Node 24 + TypeScript) — **ported from the canonical `qa-realtime-stream-testing-dotnet`**

> The four ideas and the section order match the .NET file; only the client library (`ws` / native
> `WebSocket`) and the await primitive (a promise-with-timeout, Vitest `vi.waitFor`) change.

Real-time tests assert one of two things about a **continuously-open stream** — a connection with no single
synchronous return you can `await` and assert on the next line:

- **A WebSocket** — a *bidirectional*, full-duplex channel (text **or** binary), no built-in reconnect. Used
  for chat, collaboration, live trading. You assert frames **in both directions** plus the open/close lifecycle.
- **An SSE stream** — a *server→client-only*, text/UTF-8 channel over **plain HTTP** (no upgrade handshake),
  with **auto-reconnect + `Last-Event-ID`** built into the protocol. Used for notification feeds, progress,
  server-pushed dashboards. You assert the event sequence and that the client resumes from `Last-Event-ID`.

**This skill owns every stream in the browser too:** observing and **mocking WebSockets**
(`routeWebSocket`) and serving SSE to the page. `qa/typescript/skills/network-mocking` sends both here, because
`route.fulfill` answers with one whole body and cannot stand in for a stream. Plain request/response HTTP
mocking stays in `network-mocking` (`references/playwright-routes.md`).

This skill pins nothing. The Playwright version is the **Versions** table of
`qa/typescript/skills/ui-test-author/playwright/SKILL.md`.

> **The discipline this skill encodes — four ideas, identical across all three stacks:**
>
> 1. **Real-time = await a message on a CONDITION, never a sleep.** A stream delivers "soon", on the server's
>    schedule. Drain frames into a queue and **await the expected frame / count with a bounded timeout** (a
>    promise that rejects on a timer, or Vitest `vi.waitFor(() => expect(received).toHaveLength(n))`) — never
>    `await new Promise(r => setTimeout(r, 2000))` standing in for "it probably arrived".
> 2. **Drain BEFORE you act.** Attach the `'message'` handler / arm `page.waitForEvent('websocket')` **before**
>    the action that triggers the first frames, or you race the server and lose them.
> 3. **Assert the whole lifecycle, not just a payload.** The open handshake (HTTP **101 Switching Protocols**
>    for WS — the `'open'` event), the frames, **and** the clean close (close code **1000**, or the contract's
>    documented close code, on the `'close'` event). "Server emits N then closes" = await `length === N`, *then*
>    assert the close — never assert count inside a sleep-bounded window.
> 4. **Two transports × two surfaces — choose deliberately.** **Transport:** WebSocket (bidirectional) vs SSE
>    (server→client, auto-reconnect). **Surface:** protocol-client (connect from test code, no browser —
>    backend/contract verification) vs browser (the app's UI opens the stream — Playwright `OBSERVE` or
>    `MOCK`). Pick the narrowest surface that proves the behaviour.

## Decision matrix — which transport, which surface, which tool

| Situation | Transport | Surface / Tool |
|-----------|-----------|----------------|
| Backend WS endpoint, no browser involved (chat, trading feed) | WebSocket | **protocol-client** — `ws` lib / native `WebSocket` |
| Server pushes a one-way feed (notifications, progress, live dashboard) | SSE | **protocol-client** — native `EventSource` / the `eventsource` package |
| The app's **UI** opens a WS and you assert what crosses the wire | WebSocket | **browser** — `waitForEvent('websocket')` + `framereceived` (OBSERVE) |
| The UI opens a WS and you want **deterministic** frames (no real server) | WebSocket | **browser** — `routeWebSocket` (MOCK) |
| The UI renders a **fixed set** of SSE events | SSE | **browser** — one fulfilled `text/event-stream` body, then `204` (§ Browser surface 3) |
| The UI must handle events **over time**, reconnect or resume from `Last-Event-ID` | SSE | a real test SSE server — protocol-client for the server, or the browser against it; **not** `page.route` |
| Async **queue/topic** (OrderPlaced lands on a queue, a consumer reacts) | — | **not this skill** → `qa-messaging-testing-typescript` |

## Stack

- Node 24 (22 maintenance) + TypeScript (strict), Vitest (protocol-client) + Playwright (browser)
- **`ws`** (`import WebSocket from 'ws'`) — the standard Node WS client (also used to stand up a test server)
- Native global **`WebSocket`** and **`EventSource`** — available on Node 22 and 24. A project detected on
  Node 20 (EOL since Apr 2026 — flag it) has neither → use `ws` and the `eventsource` package
- Vitest **`vi.waitFor`** is the condition-poll; a client harness with a `waitForNextMessage()` queue is the
  recommended pattern; cleanup is registered with `onTestFinished`, never inlined at the end of a test
- Browser surface: `@playwright/test` (`routeWebSocket` needs ≥ 1.48), on the writer's fixtures
  (`qa/typescript/skills/ui-test-author/playwright/assets/fixtures.ts`) — specs reach the page through page
  objects and fixtures, never raw `page.` calls
- The SUT's stream client is **injected** with its URL — never a hard-coded URL read inside an `it()`

```
tests/realtime/
├── ws-harness.ts             test-side WS client: queues frames, exposes waitForNextMessage()/takeMessages()
├── sse-harness.ts            test-side SSE client: queues events
├── chat.ws.test.ts           protocol-client WS (Vitest)
├── notifications.sse.test.ts protocol-client SSE (Vitest)
└── specs/
    ├── stream.fixtures.ts    page objects + MockStreams
    └── live-feed.spec.ts     Playwright observe + mock (browser surface)
```

## WebSocket vs SSE — when each, and what changes in the test

| | **WebSocket** | **SSE (Server-Sent Events)** |
|---|---|---|
| Direction | Bidirectional (client ↔ server) | Server → client only |
| Payload | Text **or** binary | Text/UTF-8 only (`data:` lines) |
| Transport | HTTP **upgrade** (101 Switching Protocols) | Plain HTTP streaming `text/event-stream` |
| Reconnect | **None built-in** — you implement/assert it | **Built-in** — `EventSource` auto-reconnects honoring `retry:` + `Last-Event-ID` |
| Browser API | `WebSocket` (Playwright can observe **and** mock) | `EventSource` (just HTTP — no stream API in Playwright) |
| Test focus | Full-duplex frames + open/close lifecycle | Event sequence + resume-from-`Last-Event-ID` |

## The bounded condition-wait — the heart of every real-time test

A frame arrives whenever the server sends it. The test must **await the condition** with a **timeout**,
returning the instant it holds and *failing* if it never does. A **client harness** (`WsHarness`, in
`references/details.md` § The harness) queues incoming frames and exposes a sequential `waitForNextMessage()`
— a promise raced against a timer — plus `takeMessages(n)`. Its handlers are attached in the constructor,
before any send, so no frame is lost. **The `setTimeout` inside it is a timeout *guard*, not a wait** — the
promise resolves the instant a frame arrives and *rejects* if none does within the window. No
`setTimeout`-as-wait, no `page.waitForTimeout`, anywhere.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **The harness
(`WsHarness`)**; **Browser fixtures (`stream.fixtures.ts`)**; **Protocol-client 1 — raw WebSocket**;
**Protocol-client 2 — socket.io / SignalR-JS**; **Protocol-client 3 — SSE (`EventSource`)**; **Disciplines & gotchas** (lifecycle, reconnect,
fragmentation, socket auth, heartbeat, the real-server rule) — every real-time test applies them.

## The browser fixtures

Browser-surface specs import `test` and `expect` from `specs/stream.fixtures.ts` (`references/details.md`
§ Browser fixtures), which extends the writer's fixtures with page objects and one `MockStreams` fixture:

| Fixture | Gives the test |
|---|---|
| `dashboardPage.openWatchingPrices()` | navigates and returns the Playwright `WebSocket` it armed **before** navigating |
| `statusPage.alert` / `statusPage.notifications` | the locators the stream drives |
| `mockStreams.pushOutageOnSubscribe(region)` | a `routeWebSocket` mock answering the page's subscribe message |
| `mockStreams.serveNotifications(events)` | a one-time `text/event-stream` body, then `204` for every reconnect |

## Browser surface 1 — OBSERVE WebSocket frames

When the **app's UI** opens the socket and the real backend is fine, **observe** the frames. The page object
arms `waitForEvent('websocket')` before it navigates; the test awaits a frame on a predicate, never a sleep.

```ts
import { expect, test } from './stream.fixtures';

test('Should_ShowAcmePrice_When_SocketPushesAcmeUpdate', async ({ dashboardPage }) => {
  const socket = await dashboardPage.openWatchingPrices();

  const frame = await socket.waitForEvent('framereceived', (f) => String(f.payload).includes('"symbol":"ACME"'));

  const update: { price: number } = JSON.parse(String(frame.payload));
  await expect(dashboardPage.acmePrice).toContainText(String(update.price));
});
```

`WebSocket` exposes `'framesent'` / `'framereceived'` (`frame.payload` is `string | Buffer`), `'close'`, and
`isClosed()`. Since 1.61 a trace and a HAR also record WebSocket traffic, so a failed observe test's trace
shows the frames (`qa/typescript/skills/evidence-capture`).

## Browser surface 2 — MOCK WebSocket frames (`routeWebSocket`, ≥ 1.48)

When you need **deterministic** frames, **mock** the socket. By default the routed socket does **not** connect
to the real server — `MockStreams.pushOutageOnSubscribe` answers the page's subscribe message with a canned
outage frame. Register it **before** the page opens the socket.

```ts
import { expect, test } from './stream.fixtures';

test('Should_ShowOutageAlert_When_AlertSocketPushesOutage', async ({ mockStreams, statusPage }) => {
  await mockStreams.pushOutageOnSubscribe('EU');

  await statusPage.open();

  await expect(statusPage.alert).toContainText('EU outage');
});
```

- **Pass-through / intercept-and-modify:** `ws.connectToServer()` inside the handler returns the *server-side*
  route — forward most frames to the real backend and rewrite only the one under test.
- `webSocketRoute.protocols()` [1.60] returns the subprotocols the page asked for, for a mock that must echo
  the negotiated one.
- **Caveat (Playwright #33370):** driving server-initiated frames *on demand* from the route (outside a message
  handler) has had quirks — for "server spontaneously emits" scenarios, observe a real test server instead.

## Browser surface 3 — SSE in the browser

Playwright has **no stream API for SSE** — `EventSource` is a streaming HTTP `GET`, and `route.fulfill` answers
it with **one whole body, then ends the response**. The page's `EventSource` reads every event in that body at
once, fires `error`, and **reconnects** after `retry:` ms — fetching the same events again. A fulfilled body
therefore cannot model events arriving over time, a slow stream or a mid-stream drop. What it can model is
"the UI renders this fixed set of events": `MockStreams.serveNotifications` answers the first request with the
events (`{ times: 1 }`), and every reconnect with **`204`**, which tells `EventSource` to stop reconnecting.

```ts
import { expect, test } from './stream.fixtures';

test('Should_ListThreeNotifications_When_StreamDeliversThreeEvents', async ({ mockStreams, statusPage }) => {
  await mockStreams.serveNotifications([
    { id: '1', type: 'notification', text: 'Build passed' },
    { id: '2', type: 'notification', text: 'Deploy started' },
    { id: '3', type: 'notification', text: 'Deploy finished' },
  ]);

  await statusPage.open();

  await expect(statusPage.notifications).toHaveText(['Build passed', 'Deploy started', 'Deploy finished']);
});
```

For timing, reconnect and `Last-Event-ID` resume, run a real SSE endpoint (the app's, or a small test server)
and assert through the protocol client (`references/details.md`), or drive the browser against it.

## Anti-patterns

- **`await new Promise(r => setTimeout(r, 2000))` then read one frame.** Races the server. *Fix:*
  `waitForNextMessage(timeout)` — resolves the instant the frame arrives, rejects if it never does.
- **`route.fulfill` with a "chunked" `text/event-stream` body to simulate a live feed.** The body arrives at
  once, the response ends, and `EventSource` reconnects and replays it. *Fix:* fixed events plus `204` for
  rendering; a real SSE server for timing and resume.
- **A finite read timeout on an open-ended stream.** Aborts the stream mid-flight. *Fix:* let `EventSource`
  own the long-lived connection; bound the *wait for an event*, not the connection.
- **Attaching the `'message'` handler *after* the send.** The first frames fire before you're listening.
  *Fix:* attach in the harness constructor / arm `waitForEvent('websocket')` **before** the trigger.
- **Closing the socket as the last line of the test.** A failing assertion skips it and the connection leaks.
  *Fix:* `onTestFinished(() => ws.close())` or fixture teardown; assert `closeCode` where it matters.
- **Assuming the native global `WebSocket`/`EventSource` exists on every Node.** Absent on Node 20 (EOL — flag
  it). *Fix:* `ws` / `eventsource`, or the Node 22/24 globals.

## Rules (hard constraints)

- **Real-time = await a condition, never a sleep.** A `setTimeout` is allowed only as the *reject* guard
  inside a bounded wait.
- **Drain before you act** — attach the `'message'` handler / arm `waitForEvent('websocket')` **before** the
  trigger.
- **Assert the whole lifecycle** — the 101 upgrade (`'open'`), the frames, **and** the clean close (code
  **1000** / the contract's code). "N then close" = take N, *then* assert close.
- **Use the right client** — `ws` (raw), socket.io/SignalR clients for those protocols,
  `EventSource`/`eventsource` for SSE.
- **This skill owns WebSocket mocking (`routeWebSocket`) and SSE in the browser.** SSE in the browser is a
  fixed event set plus `204` — never a fulfilled body posing as a live stream. Plain HTTP mocking is
  `qa/typescript/skills/network-mocking`.
- **Auth tokens from env, read lazily, never logged.** WS upgrade tests need the SUT on a **real server**.
- Test names `Should_X_When_Y`; one logical assertion per test; cleanup in teardown; no inline comments;
  builders for 4+-field payloads; `strict: true`.

## Cross-references

- `qa-realtime-stream-testing-dotnet` (**the canonical file**) · `qa-realtime-stream-testing-java` — the
  sibling stacks; same four ideas.
- `qa-messaging-testing-typescript` — the **eventual-consistency lineage** and the **boundary**: messaging =
  discrete queue/topic messages; this skill = an open WS/SSE stream.
- `qa-network-mocking-typescript` — **plain HTTP** mocking (`route.fulfill`, HAR, offline) and the "register
  before the action" rule; it routes WebSocket and SSE here.
- `qa-ui-test-writer-playwright-typescript` — the page-object fixtures the **browser-surface** tests extend.
- `qa-evidence-capture-typescript` — reading a failed browser test's trace, which carries WebSocket frames.
- `qa-test-login-tokens-typescript` — tokens for an authenticated socket, read from env, never logged.
