# Deep-dive details — `qa-realtime-stream-testing-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Protocol-client 1 — raw WebSocket (`ws` lib / native `WebSocket`)

The test **is** a WebSocket client. The `'open'` event fires after the **101 upgrade**; `'message'` delivers a
**reassembled** logical message (the `ws` lib handles fragmentation, unlike .NET's raw `ReceiveAsync`); `'close'`
carries the close code. Drain into the harness queue, await on a condition.

```ts
// tests/realtime/chat.ws.test.ts
import { describe, it, expect } from 'vitest';
import { WsHarness } from './ws-harness';
import { baseWsUrl } from './app-fixture';   // points at the booted SUT on a real port

describe('chat websocket', () => {
  it('should broadcast a message to a connected client', async () => {
    const ws = new WsHarness(`${baseWsUrl()}/ws/chat`);
    await ws.opened;                                            // condition: the 101 upgrade

    ws.send(JSON.stringify({ type: 'say', text: 'hello' }));

    const frame = await ws.waitForNextMessage();               // await the broadcast on a condition
    expect(frame).toContain('"text":"hello"');                 // one logical assertion: the broadcast fact
    ws.close();
  });

  it('should emit three ticks then close cleanly', async () => {
    const ws = new WsHarness(`${baseWsUrl()}/ws/ticker?count=3`);
    await ws.opened;

    const ticks = await ws.takeMessages(3);                    // the N frames…
    expect(ticks).toHaveLength(3);

    ws.close();                                                // …then the close handshake
    await vi.waitFor(() => expect(ws.closeCode).toBe(1000));   // …and the clean close (code 1000)
  });
});
```

> **The Node-22 boundary:** the harness uses the **`ws`** lib so it runs on any Node line unchanged. On Node 22
> and 24 you can drop `ws` and `new globalThis.WebSocket(url)`; a project detected on Node 20 (EOL — flag it) has
> no native global — either keep `ws` (recommended) or polyfill
> `globalThis.WebSocket = (await import('undici')).WebSocket` once in setup.

## Protocol-client 3 — SSE (native `EventSource` / the `eventsource` package)

SSE is **plain HTTP** — a `GET` whose body streams `text/event-stream`. `EventSource` (native on Node 22+, the
`eventsource` package on any line) handles the streaming, parsing, and reconnect; subscribe with `onmessage` /
`addEventListener(type)` and drain into the harness queue. Auth note: a browser `EventSource` **can't set
headers**, but the Node `eventsource` package accepts a `fetch` override / headers for server-side tests.

```ts
// tests/realtime/sse-harness.ts
import { EventSource } from 'eventsource';   // any Node line; Node 22+ also has a global EventSource

export interface SseEvent { type: string; data: string; lastEventId: string; }

export class SseHarness {
  private readonly es: EventSource;
  private readonly queue: SseEvent[] = [];

  constructor(url: string, headers?: Record<string, string>) {
    this.es = new EventSource(url, headers ? { fetch: (u, init) => fetch(u, { ...init, headers }) } : undefined);
    const push = (e: MessageEvent, type: string) =>
      this.queue.push({ type, data: e.data as string, lastEventId: (e as any).lastEventId });
    this.es.onmessage = (e) => push(e, 'message');
    for (const t of ['progress', 'done']) this.es.addEventListener(t, (e) => push(e as MessageEvent, t));
  }

  get events(): readonly SseEvent[] { return this.queue; }
  close(): void { this.es.close(); }
}
```

```ts
import { vi } from 'vitest';

it('should stream three progress events then a done event', async () => {
  const sse = new SseHarness(`${baseUrl()}/sse/progress?job=42`);

  await vi.waitFor(() => expect(sse.events).toHaveLength(4), { timeout: 5000 });   // condition, not a sleep

  expect(sse.events.map((e) => e.type)).toEqual(['progress', 'progress', 'progress', 'done']);   // the sequence
  sse.close();
});
```

> **Reconnect / `Last-Event-ID`:** `EventSource` reconnects automatically honoring the server's `retry:` and
> resends the last `id:` as `Last-Event-ID` so the server resumes — assert that missed events replay from that
> id after a drop. This is free with SSE and is the main reason to choose it over WS for one-way feeds.
