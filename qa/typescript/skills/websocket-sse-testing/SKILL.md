---
name: qa-websocket-sse-testing-typescript
description: Test real-time **WebSocket** and **Server-Sent-Events (SSE)** streams in Node 20 + TypeScript (Vitest / Playwright). Triggers: "test our WebSocket chat endpoint with ws", "assert the server pushes N SSE events then closes", "wait for a websocket frame without a setTimeout".
---

# WebSocket & SSE Testing (Node 20 + TypeScript) — **ported from the canonical `qa-websocket-sse-testing-dotnet`**

> **Ported from the canonical `qa-websocket-sse-testing-dotnet`.** The four ideas and the section order are
> identical; only the protocol-client library (the **`ws`** lib / native `WebSocket` instead of
> `ClientWebSocket`) and the await primitive (a promise-with-timeout + Vitest `vi.waitFor` instead of a
> `Channel` + `CancellationTokenSource`) change. See the .NET file for the family rationale; this is the
> TypeScript expression of the same discipline. **.NET leads the family by judgment** (richest *native*
> real-time story); in TS the protocol clients are libraries (`ws`/`eventsource`) but the disciplines port
> directly, and the **Playwright browser surface is near-identical**.

Real-time tests assert one of two things about a **continuously-open stream** — a connection with no single
synchronous return you can `await` and assert on the next line:

- **A WebSocket** — a *bidirectional*, full-duplex channel (text **or** binary), no built-in reconnect. Used
  for chat, collaboration, live trading. You assert frames **in both directions** plus the open/close lifecycle.
- **An SSE stream** — a *server→client-only*, text/UTF-8 channel over **plain HTTP** (no upgrade handshake),
  with **auto-reconnect + `Last-Event-ID`** built into the protocol. Used for notification feeds, progress,
  server-pushed dashboards. You assert the event sequence and that the client resumes from `Last-Event-ID`.

> **The discipline this skill encodes — four ideas, identical across all three stacks:**
>
> 1. **Real-time = await a message on a CONDITION, never a sleep.** A stream delivers "soon", on the server's
>    schedule. Drain frames into a queue and **await the expected frame / count with a bounded timeout** (a
>    promise that rejects on a timer, or Vitest `vi.waitFor(() => expect(received).toHaveLength(n))`) — never
>    `await new Promise(r => setTimeout(r, 2000))` standing in for "it probably arrived". The *exact*
>    eventual-consistency lineage of `qa-messaging-testing-typescript` (a stream frame is a
>    message that arrives later).
> 2. **Drain BEFORE you act.** Attach the `'message'` handler / arm `page.waitForEvent('websocket')` **before**
>    the action that triggers the first frames, or you race the server and lose them.
> 3. **Assert the whole lifecycle, not just a payload.** The open handshake (HTTP **101 Switching Protocols**
>    for WS — the `'open'` event), the frames, **and** the clean close (close code **1000**, or the contract's
>    documented close code, on the `'close'` event). "Server emits N then closes" = await `length === N`, *then*
>    assert the close — never assert count inside a sleep-bounded window.
> 4. **Two transports × two surfaces — choose deliberately.** **Transport:** WebSocket (bidirectional) vs SSE
>    (server→client, auto-reconnect). **Surface:** protocol-client (connect from test code, no browser —
>    backend/contract verification) vs browser (the app's UI opens the socket — Playwright `OBSERVE` or
>    `MOCK`). Pick the narrowest surface that proves the behaviour.

## Decision matrix — which transport, which surface, which tool

| Situation | Transport | Surface / Tool |
|-----------|-----------|----------------|
| Backend WS endpoint, no browser involved (chat, trading feed) | WebSocket | **protocol-client** — `ws` lib / native `WebSocket` |
| Server pushes a one-way feed (notifications, progress, live dashboard) | SSE | **protocol-client** — native `EventSource` / the `eventsource` package |
| The app's **UI** opens a WS and you assert what crosses the wire | WebSocket | **browser** — Playwright `waitForEvent('websocket')` + `on('framereceived')` (OBSERVE) |
| The UI opens a WS and you want **deterministic** frames (no real server) | WebSocket | **browser** — Playwright `routeWebSocket` (MOCK) |
| The UI consumes an SSE feed and you want it deterministic | SSE | **browser** — `page.route` returning a chunked `text/event-stream` body |
| Async **queue/topic** (OrderPlaced lands on a queue, a consumer reacts) | — | **not this skill** → `qa-messaging-testing-typescript` etc. |
| A plain request/response **HTTP** dependency to fake | — | **not this skill** → `qa-api-mocking-typescript` / `qa-network-monitoring-typescript` |

**Rule of thumb:** *bidirectional, interactive?* → WebSocket. *Server-push-only feed?* → SSE. *Testing the
protocol contract?* → protocol-client. *Testing the UI's use of the stream?* → browser (observe if the real
server is fine, mock if you need determinism). *A discrete message on a queue, not an open stream?* → that's
`messaging-testing`.

## Stack

- Node 20 + TypeScript (strict), Vitest 1.x (protocol-client) + Playwright (browser)
- **`ws`** (`import WebSocket from 'ws'`) — the standard Node WS client (also used to stand up a test server)
- Native global **`WebSocket`** — available since **Node 22** (undici impl). **The Node-20 boundary:** on Node
  20 it is *not* global → either use `ws`, or polyfill `globalThis.WebSocket = (await import('undici')).WebSocket`.
  **Call this out explicitly** — the CLAUDE.md default is Node 20, so prefer `ws` (or the undici polyfill) and
  note the Node-22 native path.
- Native **`EventSource`** (Node 22+) / the **`eventsource`** npm package for SSE on Node 20
- Vitest **`vi.waitFor`** is the condition-poll; a reusable client harness with a `waitForNextMessage()` queue
  is the recommended pattern (ad-hoc promise wrappers are the known pain point)
- Browser surface: `@playwright/test` (≥ **1.48** for `routeWebSocket`), built on the page-object model from
  `qa-ui-test-author-playwright-typescript`
- The SUT's stream client is **injected** with its URL — never a hard-coded URL read inside an `it()`

```
tests/realtime/
├── ws-harness.ts            ← test-side WS client: queues frames, exposes waitForNextMessage()/takeMessages()
├── sse-harness.ts           ← test-side SSE client: queues events, exposes waitForEvents()
├── chat.ws.test.ts          ← protocol-client WS (Vitest)
├── notifications.sse.test.ts← protocol-client SSE (Vitest)
└── specs/
    └── live-feed.spec.ts    ← Playwright observe + mock (browser surface)
```

## WebSocket vs SSE — when each, and what changes in the test

| | **WebSocket** | **SSE (Server-Sent Events)** |
|---|---|---|
| Direction | Bidirectional (client ↔ server) | Server → client only |
| Payload | Text **or** binary | Text/UTF-8 only (`data:` lines) |
| Transport | HTTP **upgrade** (101 Switching Protocols) | Plain HTTP streaming `text/event-stream` |
| Reconnect | **None built-in** — you implement/assert it | **Built-in** — `EventSource` auto-reconnects honoring `retry:` + `Last-Event-ID` |
| Browser API | `WebSocket` (Playwright can observe **and** mock) | `EventSource` (just HTTP — observe/mock via `page.route`) |
| Test focus | Full-duplex frames + open/close lifecycle | Event sequence + resume-from-`Last-Event-ID` |
| Pick it for | Chat, collaboration, interactive/trading | Notification feeds, progress, server-pushed dashboards |

## The bounded condition-wait — the heart of every real-time test

A frame arrives whenever the server sends it. The test must **await the condition** with a **timeout**,
returning the instant it holds and *failing* if it never does. A **client harness** queues incoming frames and
exposes a sequential `waitForNextMessage()` (a promise raced against a timer) plus `takeMessages(n)` — this is
the WS/SSE analogue of `qa-messaging-testing-typescript`'s `receiveMessages` long-poll + `expect.poll`.

```ts
// tests/realtime/ws-harness.ts
import WebSocket from 'ws';

export class WsHarness {
  private readonly socket: WebSocket;
  private readonly queue: string[] = [];
  private waiter?: (frame: string) => void;
  readonly opened: Promise<void>;
  closeCode?: number;            // assert the close code
  closeReason?: string;

  constructor(url: string, options?: WebSocket.ClientOptions) {
    this.socket = new WebSocket(url, options);   // options carry auth headers / subprotocol
    // 'open' fires after the 101 upgrade; the handler is attached BEFORE any send → no race.
    this.opened = new Promise((resolve, reject) => {
      this.socket.once('open', () => resolve());
      this.socket.once('error', reject);
    });
    this.socket.on('message', (data) => {
      const frame = data.toString();             // 'ws' delivers a reassembled message, not raw frames
      const w = this.waiter; this.waiter = undefined;
      if (w) w(frame); else this.queue.push(frame);
    });
    this.socket.on('close', (code, reason) => { this.closeCode = code; this.closeReason = reason.toString(); });
  }

  send(text: string): void { this.socket.send(text); }

  /** Await the next frame, or reject on timeout — the only sanctioned wait. */
  waitForNextMessage(timeoutMs = 5000): Promise<string> {
    const queued = this.queue.shift();
    if (queued !== undefined) return Promise.resolve(queued);
    return new Promise((resolve, reject) => {
      const t = setTimeout(() => { this.waiter = undefined; reject(new Error('ws message timeout')); }, timeoutMs);
      this.waiter = (frame) => { clearTimeout(t); resolve(frame); };
    });
  }

  async takeMessages(count: number, timeoutMs = 5000): Promise<string[]> {
    const frames: string[] = [];
    while (frames.length < count) frames.push(await this.waitForNextMessage(timeoutMs));
    return frames;
  }

  close(): void { this.socket.close(1000, 'bye'); }   // clean close, code 1000
}
```

> **`setTimeout` here is a timeout *guard*, not a wait.** The promise resolves the instant a frame arrives and
> *rejects* if none does within the window — the opposite of `await sleep(2000)` which races the server. No
> bare `setTimeout`-as-wait, no `page.waitForTimeout`, anywhere.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Protocol-client 1 — raw WebSocket (`ws` lib / native `WebSocket`)**; **Protocol-client 3 — SSE (native `EventSource` / the `eventsource` package)**.

## Protocol-client 2 — a higher-level client (socket.io / SignalR-JS)

When the endpoint is a **socket.io** server or a **SignalR** hub, use its **real client** rather than raw `ws`
— it reassembles, heartbeats, and reconnects, so you assert at the higher level (the TS analogue of the .NET
SignalR section). The message-await is still a promise raced against a timeout; **register the handler before
the action**.

```ts
import { io } from 'socket.io-client';

const socket = io(baseUrl(), { transports: ['websocket'] });
const received = new Promise<string>((resolve, reject) => {
  const t = setTimeout(() => reject(new Error('no push')), 5000);
  socket.on('receiveMessage', (msg: string) => { clearTimeout(t); resolve(msg); });   // arm BEFORE emit
});
await new Promise<void>((r) => socket.on('connect', () => r()));   // connect = the condition-wait, not a sleep
socket.emit('sendToGroup', { room: 'general', text: 'hi' });

expect(await received).toContain('hi');
socket.close();
```

> socket.io reconnects natively (`io(url, { reconnection: true })`); assert reconnect behaviour by killing the
> server and awaiting the `'reconnect'` event — never `sleep` to "let it reconnect".

## Browser surface 1 — OBSERVE WebSocket frames (Playwright)

When the **app's UI** opens the socket and the real backend is fine, **observe** the frames. Arm
`page.waitForEvent('websocket')` **before** the action that opens it; layer this on the page-object model from
`qa-ui-test-author-playwright-typescript`.

```ts
import { test, expect } from '@playwright/test';

test('should push a price update over the dashboard socket', async ({ page }) => {
  // Arm the WS wait BEFORE navigating — the socket opens on load.
  const wsPromise = page.waitForEvent('websocket');
  await page.goto('/dashboard');

  const ws = await wsPromise;
  expect(ws.url()).toContain('/ws/prices');

  // Await a frame on a condition (the predicate), not a sleep.
  const frame = await ws.waitForEvent('framereceived',
    (f) => (f.payload as string).includes('"symbol":"ACME"'));

  expect(frame.payload).toContain('"price"');
  await expect(page.getByTestId('acme-price')).not.toBeEmpty();   // the user-visible effect of the frame
});
```

`WebSocket` exposes `'framesent'` / `'framereceived'` (`frame.payload` is `string | Buffer`), `'close'`, and
`isClosed()` — enough to assert direction, payload, and lifecycle of what the page actually sends/receives.

## Browser surface 2 — MOCK WebSocket frames (Playwright `routeWebSocket`, ≥ 1.48)

When you need **deterministic** frames, **mock** the socket with `page.routeWebSocket` (Playwright **1.48**).
By default the routed socket does **not** connect to the real server — you script both directions. Register it
**before** the page opens the socket.

```ts
test('should render the alert banner when the socket pushes an outage', async ({ page }) => {
  // Mock the socket: when the page sends "subscribe", push a canned outage frame back.
  await page.routeWebSocket('**/ws/alerts', (ws) => {
    ws.onMessage((message) => {
      if (String(message).includes('subscribe'))
        ws.send(JSON.stringify({ type: 'outage', region: 'EU' }));   // server→page, fully deterministic
    });
  });

  await page.goto('/status');

  await expect(page.getByRole('alert')).toContainText('EU outage');
});
```

> **Pass-through / intercept-and-modify:** call `ws.connectToServer()` inside the handler to get the
> *server-side* route — forward most frames to the real backend and rewrite only the one under test. **Caveat
> (Playwright #33370):** driving server-initiated frames *on demand* from the route (outside a message handler)
> has had quirks — for "server spontaneously emits" scenarios, an observe test against a real test server is
> more reliable than a mock. **SSE has no dedicated Playwright API** — `EventSource` is just a streaming HTTP
> GET, so mock it with `page.route` returning a chunked `text/event-stream` body (or observe via `page.on('response')`);
> a protocol-client SSE test is usually cleaner for asserting the server's sequence.

## Disciplines & gotchas (apply to every real-time test)

- **Await a condition, never a sleep** — `waitForNextMessage(timeout)` / Vitest `vi.waitFor(...)` /
  Playwright `waitForEvent('framereceived', predicate)`. No bare `setTimeout`-as-wait, no `page.waitForTimeout`.
- **Lifecycle:** the `'open'` event = the 101 upgrade succeeded (`'error'` before it = a failed handshake);
  always `close(1000, …)` in teardown and assert the close code where the contract specifies one. Attach the
  `'message'` handler **before** sending (the harness does this in its constructor) to avoid a race.
- **Server emits N then closes:** `takeMessages(N)` then assert the `'close'` code — never assert the count
  inside a sleep-bounded window.
- **Reconnection / backoff:** drop the server (or `ws.close()` the route) and assert the client reconnects with
  increasing intervals (socket.io `'reconnect'`; SSE reconnects natively, honoring `retry:` and resending
  `Last-Event-ID` so the server resumes — assert missed events replay from that id). Raw `ws` doesn't
  auto-reconnect; if the SUT wraps reconnect logic, assert *that*.
- **Fragmentation / backpressure:** the `ws` lib's `'message'` delivers a *reassembled* message (simpler than
  raw .NET); still send a large message and assert it arrives whole. Set `maxPayload` if testing limits.
- **Auth on the socket** — cover all three patterns: token in the **query string** (`?access_token=…`), token
  via **subprotocol** (`new WebSocket(url, [token])` → `Sec-WebSocket-Protocol`), or token in the **first
  frame** after connect. With `ws` you can also pass `{ headers: { Authorization: … } }` (server-side only).
  Read the token from **env, lazily, never logged** (cross-link `qa-auth0-test-tokens-typescript`). A browser
  `EventSource` **cannot set headers** → query-param or cookie auth.
- **Heartbeat (ping/pong):** `ws` exposes `'ping'`/`'pong'` events; assert the app-level heartbeat / that a
  missed pong triggers the SUT's reconnect.
- **WS upgrade in tests** needs the SUT booted on a **real HTTP server** (the upgrade can't happen against an
  in-process mock) — boot it in `beforeAll` / via Testcontainers (`qa-test-environments-typescript`).

## Anti-patterns

- **`await new Promise(r => setTimeout(r, 2000))` then read one frame.** Races the server; slow when fast,
  flaky when slow. *Fix:* `waitForNextMessage(timeout)` — resolves the instant the frame arrives, rejects if
  it never does.
- **A finite `EventSource`/`fetch` read timeout on an open-ended stream.** Aborts the stream mid-flight. *Fix:*
  let `EventSource` own the long-lived connection; don't wrap it in a timeout.
- **Attaching the `'message'` handler *after* the send.** The first frames fire before you're listening. *Fix:*
  attach in the harness constructor / arm `waitForEvent('websocket')` **before** the trigger.
- **Never closing the socket** (or asserting only the payload). The connection leaks across tests and you
  never catch a bad close code. *Fix:* `close(1000, …)` in `afterEach`; assert `closeCode`.
- **`sleep` to "let it reconnect".** *Fix:* assert the reconnected state on a condition (`'reconnect'` event;
  await the next frame after the drop).
- **Assuming the native global `WebSocket` exists on Node 20.** It's `undefined` < Node 22. *Fix:* use the `ws`
  lib (recommended) or polyfill via `undici`.
- **Using raw `ws` for a socket.io / SignalR endpoint.** You'd re-implement their framing/heartbeat. *Fix:* use
  the real client.
- **Reaching for this skill for a queue/topic.** A discrete message on a broker is *not* an open stream. *Fix:*
  `qa-messaging-testing-typescript` and siblings.
- **Token hard-coded or logged.** *Fix:* env, read lazily, never logged (`qa-auth0-test-tokens-typescript`).

## Examples

**End-to-end: a WebSocket request/response round-trip with a clean close, asserted lifecycle-first.**

```ts
it('should echo a message and close with code 1000', async () => {
  const ws = new WsHarness(`${baseWsUrl()}/ws/echo`);
  await ws.opened;                                          // 101 upgrade

  ws.send('ping');
  expect(await ws.waitForNextMessage()).toBe('ping');

  ws.close();                                               // clean close handshake
  await vi.waitFor(() => expect(ws.closeCode).toBe(1000));  // code 1000
});
```

**Auth via subprotocol (token on the handshake, read from env, never logged):**

```ts
const ws = new WsHarness(`${baseWsUrl()}/ws/secure`, { protocol: testTokens.accessToken() });  // env-sourced; see qa-auth0-test-tokens-typescript
```

**Composing with a test-data builder for the frame payload (4+ fields → builder, per the global rules):**

```ts
const payload = chatMessages.standard().withText('hello').withRoom('general').build();   // qa-test-data-builder-typescript
ws.send(JSON.stringify(payload));
```

## Rules (hard constraints)

- **Real-time = await a condition, never a sleep.** Drain into a harness queue, await with a
  promise-plus-timeout (`waitForNextMessage`) / Vitest `vi.waitFor` / Playwright `waitForEvent(..., predicate)`.
  **No bare `setTimeout`-as-wait, no `page.waitForTimeout`.** (A `setTimeout` is allowed only as the *reject*
  guard inside the bounded wait.)
- **Drain before you act** — attach the `'message'` handler / arm `waitForEvent('websocket')` **before** the
  trigger, or you race the first frames.
- **Assert the whole lifecycle** — the 101 upgrade (the `'open'` event; `'error'` first = failed handshake),
  the frames, **and** the clean close (code **1000** / the contract's close code, on `'close'`). "N then close"
  = take N, *then* assert close.
- **Use the right client** — the `ws` lib (raw, reassembles; works on Node 20), socket.io/SignalR clients for
  those protocols, `EventSource`/`eventsource` for SSE (free reconnect + `Last-Event-ID`). **Mind the Node-22
  boundary** for the native global `WebSocket`/`EventSource`.
- **Pick the transport and surface deliberately** — WS (bidirectional) vs SSE (server-push, free reconnect);
  protocol-client (contract) vs browser (observe if the real server suffices, `routeWebSocket` to mock).
- **Auth tokens from env, read lazily, never logged** (query / subprotocol / first-frame / `ws` headers;
  browser `EventSource` can't set headers — query/cookie). WS upgrade tests need the SUT on a **real server**.
- `strict: true`; the SUT's stream client is injected with its URL; test names `Should_X_When_Y`-style; one
  logical assertion per test; builders for 4+-field payloads; structured logging; no secrets in code.

## Cross-references

- `qa-websocket-sse-testing-dotnet` — **the canonical file**: same four ideas, raw `ClientWebSocket` (with the
  `EndOfMessage` fragment-reassembly loop), SignalR `HubConnection`, `SseParser`, a `Channel<T>` +
  `CancellationTokenSource` deadline as the condition-wait, Playwright-.NET observe/mock. Read it for the
  family rationale.
- `qa-websocket-sse-testing-java` — same four ideas, OkHttp `WebSocket` + a `WebSocketListener`/`BlockingQueue`,
  Awaitility as the condition-wait, OkHttp-SSE / `WebClient` `Flux<ServerSentEvent>` + `StepVerifier`,
  Spring `WebSocketStompClient` for STOMP, Playwright-Java (`waitForWebSocket`, `onFrameReceived`, `routeWebSocket`).
- `qa-messaging-testing-typescript` — the **eventual-consistency lineage** (a stream frame is
  a message that arrives later) and the **boundary**: messaging = discrete queue/topic messages with a consumer;
  this skill = an open WS/SSE stream. (Plus `-sqs` `sqs` / `-kafka` `kafka` / `-rabbitmq` `rabbitmq`.)
- `qa-network-monitoring-typescript` — the **HTTP** mock counterpart and the "register
  before the action" ordering rule; SSE-in-the-browser mocking reuses its `page.route`.
- `qa-api-mocking-typescript` — fake a *synchronous* HTTP dependency; not a stream. (MSW also has a
  WebSocket-mocking API for service-level interception — distinct from Playwright's browser-level `routeWebSocket`.)
- `qa-ui-test-author-playwright-typescript` — the page-object model the **browser-surface** tests layer on; the
  no-`waitForTimeout` discipline originates there.
- `qa-auth0-test-tokens-typescript` — tokens for an authenticated socket, read from env, never logged.
- `qa-test-environments-typescript` — booting the SUT on a real server (Testcontainers) with the
  readiness-wait discipline. `qa-allure-reporting-typescript` — attach captured frames / the event sequence.
  `qa-test-data-builder-typescript` — frame payloads with 4+ fields.
