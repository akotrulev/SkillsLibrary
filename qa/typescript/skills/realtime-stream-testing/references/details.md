# Deep-dive details — `qa-realtime-stream-testing-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## The harness — `tests/realtime/ws-harness.ts`

`'open'` fires after the 101 upgrade; `ws` delivers a reassembled message, not raw frames; every handler is
attached in the constructor, before the test can send.

```ts
import WebSocket from 'ws';

export class WsHarness {
  private readonly socket: WebSocket;
  private readonly queue: string[] = [];
  private waiter?: (frame: string) => void;
  readonly opened: Promise<void>;
  closeCode?: number;
  closeReason?: string;

  constructor(url: string, options?: WebSocket.ClientOptions) {
    this.socket = new WebSocket(url, options);
    this.opened = new Promise((resolve, reject) => {
      this.socket.once('open', () => resolve());
      this.socket.once('error', reject);
    });
    this.socket.on('message', (data) => {
      const frame = data.toString();
      const waiter = this.waiter;
      this.waiter = undefined;
      if (waiter) waiter(frame);
      else this.queue.push(frame);
    });
    this.socket.on('close', (code, reason) => {
      this.closeCode = code;
      this.closeReason = reason.toString();
    });
  }

  send(text: string): void {
    this.socket.send(text);
  }

  waitForNextMessage(timeoutMs = 5000): Promise<string> {
    const queued = this.queue.shift();
    if (queued !== undefined) return Promise.resolve(queued);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.waiter = undefined;
        reject(new Error(`no WebSocket message within ${timeoutMs}ms`));
      }, timeoutMs);
      this.waiter = (frame) => {
        clearTimeout(timer);
        resolve(frame);
      };
    });
  }

  async takeMessages(count: number, timeoutMs = 5000): Promise<string[]> {
    const frames: string[] = [];
    while (frames.length < count) frames.push(await this.waitForNextMessage(timeoutMs));
    return frames;
  }

  close(): void {
    this.socket.close(1000, 'bye');
  }
}
```

## Browser fixtures — `specs/stream.fixtures.ts`

A page object that opens a socket arms `waitForEvent('websocket')` **before** it navigates and returns the
socket. `MockStreams.serveNotifications` registers the `204` route first and the one-time event body second:
routes run in reverse registration order, so the first request gets the events (`{ times: 1 }`) and every
reconnect gets the `204` that stops `EventSource`.

```ts
import type { Locator, Page, WebSocket } from '@playwright/test';
import { test as base } from '../fixtures';

export type NotificationEvent = { readonly id: string; readonly type: string; readonly text: string };

export class DashboardPage {
  readonly acmePrice: Locator;

  constructor(private readonly page: Page) {
    this.acmePrice = page.getByTestId('Prices.Acme');
  }

  async openWatchingPrices(): Promise<WebSocket> {
    const socket = this.page.waitForEvent('websocket', (ws) => ws.url().endsWith('/ws/prices'));
    await this.page.goto('/dashboard');
    return socket;
  }
}

export class StatusPage {
  readonly alert: Locator;
  readonly notifications: Locator;

  constructor(private readonly page: Page) {
    this.alert = page.getByRole('alert');
    this.notifications = page.getByTestId('Notifications.Item');
  }

  async open(): Promise<void> {
    await this.page.goto('/status');
  }
}

export class MockStreams {
  constructor(private readonly page: Page) {}

  async pushOutageOnSubscribe(region: string): Promise<void> {
    await this.page.routeWebSocket('**/ws/alerts', (ws) => {
      ws.onMessage(() => ws.send(JSON.stringify({ type: 'outage', region })));
    });
  }

  async serveNotifications(events: readonly NotificationEvent[]): Promise<void> {
    const body = events.map((event) => `id: ${event.id}\nevent: ${event.type}\ndata: ${event.text}\n\n`).join('');
    await this.page.route('**/api/notifications/stream', (route) => route.fulfill({ status: 204 }));
    await this.page.route(
      '**/api/notifications/stream',
      (route) => route.fulfill({ status: 200, contentType: 'text/event-stream', body }),
      { times: 1 },
    );
  }
}

export const test = base.extend<{ dashboardPage: DashboardPage; statusPage: StatusPage; mockStreams: MockStreams }>({
  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },
  statusPage: async ({ page }, use) => {
    await use(new StatusPage(page));
  },
  mockStreams: async ({ page }, use) => {
    await use(new MockStreams(page));
  },
});

export { expect } from '../fixtures';
```

## Protocol-client 1 — raw WebSocket (`ws` lib / native `WebSocket`)

The test **is** a WebSocket client. The `'open'` event fires after the **101 upgrade**; `'message'` delivers a
**reassembled** logical message (the `ws` lib handles fragmentation, unlike .NET's raw `ReceiveAsync`); `'close'`
carries the close code. Drain into the harness queue, await on a condition. `baseWsUrl()` points at the SUT
booted on a real port.

```ts
import { describe, expect, it, onTestFinished, vi } from 'vitest';
import { baseWsUrl } from './app-fixture';
import { WsHarness } from './ws-harness';

function connect(path: string): WsHarness {
  const ws = new WsHarness(`${baseWsUrl()}${path}`);
  onTestFinished(() => ws.close());
  return ws;
}

describe('chat websocket', () => {
  it('Should_BroadcastMessage_When_ClientSays', async () => {
    const ws = connect('/ws/chat');
    await ws.opened;

    ws.send(JSON.stringify({ type: 'say', text: 'hello' }));

    expect(JSON.parse(await ws.waitForNextMessage())).toMatchObject({ text: 'hello' });
  });

  it('Should_EmitThreeTicks_When_TickerCountIsThree', async () => {
    const ws = connect('/ws/ticker?count=3');
    await ws.opened;

    const ticks = await ws.takeMessages(3);

    expect(ticks).toHaveLength(3);
  });

  it('Should_CloseWithCode1000_When_ClientClosesCleanly', async () => {
    const ws = connect('/ws/echo');
    await ws.opened;

    ws.close();

    await vi.waitFor(() => expect(ws.closeCode).toBe(1000));
  });
});
```

- `connect` registers the close with `onTestFinished`, so a failed assertion never leaks a socket; the close
  test calls `close()` itself because the close **is** its action — the second close is a no-op.
- The harness uses the **`ws`** lib so it runs on any Node line unchanged. On Node 22 and 24 the global
  `WebSocket` works too; a project detected on Node 20 (EOL — flag it) has no global, so keep `ws`.

## Protocol-client 2 — a higher-level client (socket.io / SignalR-JS)

When the endpoint is a **socket.io** server or a **SignalR** hub, use its **real client** rather than raw `ws`
— it reassembles, heartbeats and reconnects, so you assert at the higher level. The await is still a promise
raced against a timeout, and the handler is registered **before** the action.

```ts
import { io, type Socket } from 'socket.io-client';
import { expect, it, onTestFinished } from 'vitest';
import { baseUrl } from './app-fixture';

function nextEvent<T>(socket: Socket, event: string, timeoutMs = 5000): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`no '${event}' event within ${timeoutMs}ms`)), timeoutMs);
    socket.once(event, (payload: T) => {
      clearTimeout(timer);
      resolve(payload);
    });
  });
}

it('Should_DeliverMessageToRoom_When_ClientSendsToGroup', async () => {
  const socket = io(baseUrl(), { transports: ['websocket'] });
  onTestFinished(() => socket.close());
  await nextEvent(socket, 'connect');
  const received = nextEvent<string>(socket, 'receiveMessage');

  socket.emit('sendToGroup', { room: 'general', text: 'hi' });

  expect(await received).toContain('hi');
});
```

socket.io reconnects natively (`io(url, { reconnection: true })`); assert reconnect behaviour by stopping the
server and awaiting `nextEvent(socket.io, 'reconnect')` — never a sleep to "let it reconnect".

## Protocol-client 3 — SSE (native `EventSource` / the `eventsource` package)

SSE is **plain HTTP** — a `GET` whose body streams `text/event-stream`. `EventSource` (global on Node 22 and
24, the `eventsource` package on any line) handles the streaming, parsing and reconnect; subscribe with
`onmessage` / `addEventListener(type)` and drain into the harness queue. A browser `EventSource` **can't set
headers**, but the `eventsource` package accepts a `fetch` override, so a server-side test can send one.

```ts
import { EventSource } from 'eventsource';

export type SseEvent = { readonly type: string; readonly data: string; readonly lastEventId: string };

export class SseHarness {
  private readonly source: EventSource;
  private readonly received: SseEvent[] = [];

  constructor(url: string, types: readonly string[], headers?: Record<string, string>) {
    this.source = new EventSource(url, headers ? { fetch: (input, init) => fetch(input, { ...init, headers }) } : undefined);
    const keep = (event: MessageEvent<string>, type: string) =>
      this.received.push({ type, data: event.data, lastEventId: event.lastEventId });
    this.source.onmessage = (event) => keep(event, 'message');
    types.forEach((type) => this.source.addEventListener(type, (event) => keep(event, type)));
  }

  get events(): readonly SseEvent[] {
    return this.received;
  }

  close(): void {
    this.source.close();
  }
}
```

`tests/realtime/sse-harness.ts`.

```ts
import { expect, it, onTestFinished, vi } from 'vitest';
import { baseUrl } from './app-fixture';
import { SseHarness } from './sse-harness';

it('Should_StreamThreeProgressEventsThenDone_When_JobRuns', async () => {
  const sse = new SseHarness(`${baseUrl()}/sse/progress?job=42`, ['progress', 'done']);
  onTestFinished(() => sse.close());

  await vi.waitFor(() => expect(sse.events).toHaveLength(4), { timeout: 5000 });

  expect(sse.events.map((event) => event.type)).toEqual(['progress', 'progress', 'progress', 'done']);
});
```

`vi.waitFor` is the arrange step's completion condition — the four events arrived — and the sequence is the one
asserted behaviour.

**Reconnect / `Last-Event-ID`:** `EventSource` reconnects automatically honoring the server's `retry:` and
resends the last `id:` as `Last-Event-ID`, so the server resumes. Assert it against a real SSE server: drop the
connection server-side after event 2, then wait for the stream to finish and assert the ids are `1…n` with no
gap and no duplicate. This is free with SSE and is the main reason to choose it over WS for one-way feeds — and
it is exactly what a mocked `page.route` body cannot reproduce (SKILL.md § Browser surface 3).

## Disciplines & gotchas (apply to every real-time test)

- **Await a condition, never a sleep** — `waitForNextMessage(timeout)` / Vitest `vi.waitFor(...)` /
  Playwright `waitForEvent('framereceived', predicate)`.
- **Lifecycle:** the `'open'` event = the 101 upgrade succeeded (`'error'` before it = a failed handshake);
  close with `close(1000, …)` in teardown (`onTestFinished`, or the fixture's teardown) and assert the close
  code where the contract specifies one.
- **Server emits N then closes:** `takeMessages(N)` then assert the `'close'` code.
- **Reconnection / backoff:** drop the server (or `ws.close()` the route) and assert the client reconnects
  (socket.io `'reconnect'`; SSE reconnects natively, honoring `retry:` and resending `Last-Event-ID` — assert
  missed events replay from that id). Raw `ws` doesn't auto-reconnect; if the SUT wraps reconnect logic,
  assert *that*.
- **Fragmentation / backpressure:** `ws`'s `'message'` delivers a *reassembled* message; still send a large
  message and assert it arrives whole. Set `maxPayload` if testing limits.
- **Auth on the socket** — token in the **query string** (`?access_token=…`), via **subprotocol**
  (`new WebSocket(url, [token])` → `Sec-WebSocket-Protocol`), or in the **first frame**; `ws` also accepts
  `{ headers: { Authorization: … } }`. Read the token from **env, lazily, never logged**
  (`qa-test-login-tokens-typescript`). A browser `EventSource` **cannot set headers** → query-param or cookie
  auth.
- **Heartbeat (ping/pong):** `ws` exposes `'ping'`/`'pong'`; assert the app-level heartbeat / that a missed
  pong triggers the SUT's reconnect.
- **WS upgrade in tests** needs the SUT booted on a **real HTTP server** — boot it in `beforeAll` / via
  Testcontainers.
