---
name: qa-realtime-stream-testing-java
description: Use when testing WebSocket or SSE streams in Java 21 / TestNG — protocol clients (OkHttp WebSocket/SSE, Spring STOMP, WebClient + StepVerifier) draining frames into a queue and asserting on conditions (Awaitility, never sleeps), plus Playwright for in-browser frames. Triggers: "test our WebSocket endpoint", "assert the SSE stream emits X", "real-time updates test". Do NOT use for request/response HTTP (`qa-api-test-writer-java`).
---

# WebSocket & SSE Testing (Java 21 / TestNG / Playwright 1.63)

The Java expression of the family the .NET sibling leads (`qa-realtime-stream-testing-dotnet`): the four ideas
and the section order are the same; the protocol clients are OkHttp / Spring, the await primitive is Awaitility /
`BlockingQueue.poll`, and the browser surface is Playwright for Java on J1's `BaseTest`.

Real-time tests assert one of two things about a **continuously-open stream** — a connection with no single
synchronous return you can assert on the next line:

- **A WebSocket** — a *bidirectional*, full-duplex channel (text **or** binary), no built-in reconnect. Used
  for chat, collaboration, live trading. You assert frames **in both directions** plus the open/close lifecycle.
- **An SSE stream** — a *server→client-only*, text/UTF-8 channel over **plain HTTP** (no upgrade handshake),
  with **auto-reconnect + `Last-Event-ID`** built into the protocol. Used for notification feeds, progress,
  server-pushed dashboards. You assert the event sequence and that the client resumes from `Last-Event-ID`.

> **The discipline this skill encodes — four ideas, identical across all three stacks:**
>
> 1. **Real-time = await a message on a CONDITION, never a sleep.** A stream delivers "soon", on the server's
>    schedule. Drain frames into a `BlockingQueue` and **await the expected frame / count with a bounded
>    timeout** (Awaitility `await().atMost(...).until(...)` or `queue.poll(5, SECONDS)`) — never
>    `Thread.sleep(2000)` standing in for "it probably arrived".
> 2. **Drain BEFORE you act.** Register the `WebSocketListener` / arm `page.waitForWebSocket` **before** the
>    action that triggers the first frames, or you race the server and lose them.
> 3. **Assert the whole lifecycle, not just a payload.** The open handshake (HTTP **101 Switching Protocols**
>    for WS — surfaced in `onOpen`), the frames, **and** the clean close (close code **1000**, or the
>    contract's documented close code). "Server emits N then closes" = await `size == N`, *then* assert the close.
> 4. **Two transports × two surfaces — choose deliberately.** **Transport:** WebSocket (bidirectional) vs SSE
>    (server→client, auto-reconnect). **Surface:** protocol-client (connect from test code, no browser —
>    backend/contract verification) vs browser (the app's UI opens the stream — Playwright **observe** or
>    **mock**). Pick the narrowest surface that proves the behaviour.

## Decision matrix — which transport, which surface, which tool

| Situation | Transport | Surface / Tool |
|-----------|-----------|----------------|
| Backend WS endpoint, no browser involved (chat, trading feed) | WebSocket | **protocol-client** — OkHttp `WebSocket` |
| The endpoint speaks **STOMP-over-WS** (Spring messaging) | WebSocket | **protocol-client** — Spring `WebSocketStompClient` |
| Server pushes a one-way feed (notifications, progress, live dashboard) | SSE | **protocol-client** — OkHttp-SSE / `WebClient` `Flux<ServerSentEvent>` |
| The app's **UI** opens a WS and you assert what crosses the wire | WebSocket | **browser** — `waitForWebSocket` + `waitForFrameReceived` (observe) |
| The UI opens a WS and you want **deterministic** frames (no real server) | WebSocket | **browser** — `routeWebSocket` (mock) |
| The UI **renders** a fixed set of SSE events | SSE | **browser** — a one-time `text/event-stream` route over a `204` route |
| SSE **timing**, reconnect or `Last-Event-ID` resume | SSE | a **real SSE server** — the protocol client, or the browser against it |
| Async **queue/topic** (OrderPlaced lands on a queue, a consumer reacts) | — | **not this skill** → `qa-messaging-testing-java` etc. |

## Stack

- Java 21, TestNG, Gradle (Kotlin DSL) — async handled via listeners + `BlockingQueue`; tests are synchronous
- `com.squareup.okhttp3:okhttp` — the raw WebSocket client (`newWebSocket` + `WebSocketListener`)
- `com.squareup.okhttp3:okhttp-sse` — the SSE client (`EventSources` + `EventSourceListener`); **or**
  `org.springframework:spring-webflux` `WebClient` returning `Flux<ServerSentEvent<T>>` + `reactor-test`
  `StepVerifier` when the SUT is reactive
- `org.springframework:spring-websocket` `WebSocketStompClient` only when the endpoint speaks **STOMP**
- `org.awaitility:awaitility` — `await().atMost(...).until(...)` is the **bounded condition-wait**;
  `BlockingQueue.poll(timeout)` is the simpler form
- `org.springframework.boot:spring-boot-starter-test` `@SpringBootTest(webEnvironment = RANDOM_PORT)` — a
  **real port** so the WS upgrade works (an in-memory mock servlet can't upgrade)
- Browser surface: Playwright for Java at the pin in the **Versions** table of
  `qa/java/skills/ui-test-author/playwright/SKILL.md` (this skill pins nothing; `routeWebSocket` needs ≥ 1.48).
  Browser classes **extend J1's `BaseTest`** and reach the page through page objects and one `MockStreams` helper
- The SUT's stream client is **constructor-injected** with its URL / an `OkHttpClient` — never a hard-coded
  URL read inside an `@Test`. Test-side clients: `WebSocketProbe`, `SseProbe` (`references/details.md`)

## WebSocket vs SSE — when each, and what changes in the test

| | **WebSocket** | **SSE (Server-Sent Events)** |
|---|---|---|
| Direction | Bidirectional (client ↔ server) | Server → client only |
| Payload | Text **or** binary | Text/UTF-8 only (`data:` lines) |
| Transport | HTTP **upgrade** (101 Switching Protocols) | Plain HTTP streaming `text/event-stream` |
| Reconnect | **None built-in** — you implement/assert it | **Built-in** — auto-reconnect honoring `retry:` + `Last-Event-ID` |
| Browser API | `WebSocket` (Playwright can observe **and** mock) | `EventSource` (just HTTP — no Playwright stream API) |
| Test focus | Full-duplex frames + open/close lifecycle | Event sequence + resume-from-`Last-Event-ID` |

## The bounded condition-wait — the heart of every real-time test

A frame arrives whenever the server sends it. The listener pushes frames into a `BlockingQueue`; the test either
`poll(timeout)`s for the next one or uses **Awaitility** for the "until N frames" gate.

```java
public final class AwaitFrame {

    public static <T> T next(BlockingQueue<T> queue, Duration timeout) throws InterruptedException {
        T frame = queue.poll(timeout.toMillis(), TimeUnit.MILLISECONDS);
        if (frame == null) {
            throw new AssertionError("No frame arrived within " + timeout);
        }
        return frame;
    }

    public static void untilCount(BlockingQueue<?> queue, int count, Duration timeout) {
        await("at least " + count + " frames").atMost(timeout).pollInterval(Duration.ofMillis(50))
                .until(() -> queue.size() >= count);
    }
}
```

`poll(timeout)` and `await().until(...)` return the instant the condition holds and *fail* if it never does. A
fixed sleep races the server — slow when the frame is fast, flaky when it's slow.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Protocol-client 1 —
raw WebSocket (OkHttp)**; **Protocol-client 2 — STOMP-over-WebSocket (Spring)**; **Protocol-client 3 — SSE
(OkHttp-SSE / `WebClient`)**; **Browser page objects and `MockStreams`**; **Disciplines & gotchas** (lifecycle,
reconnect, fragmentation, socket auth, heartbeat, the real-port rule) — every real-time test applies them.

## The browser helpers

Browser tests extend `BaseTest` and build these in their own `@BeforeMethod` (`references/details.md` §
Browser page objects and `MockStreams`):

| Helper | Gives the test |
|---|---|
| `dashboardPage.openWatchingPrices()` | navigates and returns the Playwright `WebSocket` it armed **before** navigating |
| `dashboardPage.acmePrice()` / `statusPage.alert()` / `statusPage.notifications()` | the locators the stream drives |
| `mockStreams.pushOutageOnSubscribe(region)` | a `routeWebSocket` mock answering the page's subscribe frame |
| `mockStreams.serveNotifications(events)` | a one-time `text/event-stream` body, then `204` for every reconnect |

## Browser surface 1 — OBSERVE WebSocket frames

When the **app's UI** opens the socket and the real backend is fine, **observe** the frames. The page object arms
`waitForWebSocket` before it navigates; the test awaits a frame on a predicate, never a sleep.

```java
@Test
public void Should_ShowAcmePrice_When_SocketPushesAcmeUpdate() {
    WebSocket socket = dashboardPage.openWatchingPrices();

    WebSocketFrame frame = socket.waitForFrameReceived(
            new WebSocket.WaitForFrameReceivedOptions().setPredicate(f -> f.text().contains("\"symbol\":\"ACME\"")),
            () -> { });

    PriceUpdate update = new Gson().fromJson(frame.text(), PriceUpdate.class);
    assertThat(dashboardPage.acmePrice()).containsText(update.price());
}
```

`PriceUpdate` is a `record (String symbol, String price)`; Gson is Playwright for Java's own dependency.

`WebSocket` exposes `onFrameSent` / `onFrameReceived` (`WebSocketFrame.text()` / `.binary()`), `onClose`,
`isClosed()` and the `waitForFrame…` methods — enough to assert direction, payload and lifecycle of what the page
actually sends and receives. A failed observe test's trace records the WebSocket traffic
(`qa/java/skills/evidence-capture`).

## Browser surface 2 — MOCK WebSocket frames (`routeWebSocket`, ≥ 1.48)

When you need **deterministic** frames, **mock** the socket. By default the routed socket does **not** connect
to the real server — `MockStreams.pushOutageOnSubscribe` answers the page's subscribe frame with a canned outage
frame. The route's handler is a `Consumer<WebSocketFrame>`: it reads the page's message with `frame.text()`.
Register it **before** the page opens the socket.

```java
@Test
public void Should_ShowOutageAlert_When_AlertSocketPushesOutage() {
    mockStreams.pushOutageOnSubscribe("EU");

    statusPage.open();

    assertThat(statusPage.alert()).containsText("EU outage");
}
```

- **Pass-through / intercept-and-modify:** `ws.connectToServer()` inside the handler returns the *server-side*
  route — forward most frames to the real backend and rewrite only the one under test.
- **Caveat (Playwright #33370):** driving server-initiated frames *on demand* from the route (outside a message
  handler) has had quirks — for "server spontaneously emits" scenarios, observe a real test server instead.

## Browser surface 3 — SSE in the browser

Playwright has **no stream API for SSE** — `EventSource` is a streaming HTTP `GET`, and `route.fulfill` answers it
with **one whole body, then ends the response**. The page's `EventSource` reads every event in that body at once,
fires `error`, and **reconnects** after `retry:` ms — fetching the same events again. A "chunked"
`text/event-stream` body is therefore not a stream: it cannot model events arriving over time, a slow stream or
a mid-stream drop, and it replays on every reconnect. What it can model is "the UI renders this fixed set of
events": `MockStreams.serveNotifications` answers the first request with the events (`setTimes(1)`) and every
reconnect with **`204`**, which tells `EventSource` to stop reconnecting.

```java
@Test
public void Should_ListThreeNotifications_When_StreamDeliversThreeEvents() {
    mockStreams.serveNotifications(List.of(
            new NotificationEvent("1", "notification", "Build passed"),
            new NotificationEvent("2", "notification", "Deploy started"),
            new NotificationEvent("3", "notification", "Deploy finished")));

    statusPage.open();

    assertThat(statusPage.notifications()).hasText(new String[] {"Build passed", "Deploy started", "Deploy finished"});
}
```

For timing, reconnect and `Last-Event-ID` resume, run a real SSE endpoint (the app's, or a small test server) and
assert through the protocol client (`references/details.md`), or drive the browser against it.

## Anti-patterns

- **`Thread.sleep(2000)` then read one frame.** Races the server. *Fix:* `AwaitFrame.next(queue, timeout)`.
- **Buffering the SSE response with a read timeout.** A finite `readTimeout` aborts an open-ended stream
  mid-flight. *Fix:* `readTimeout(Duration.ZERO)` on the OkHttp-SSE client (or `WebClient` + `StepVerifier`).
- **Wiring the listener / subscribing *after* the action.** *Fix:* `newWebSocket` / `session.subscribe(...)` /
  `waitForWebSocket` **before** the trigger.
- **Never closing the socket** (or asserting only the payload). *Fix:* close in `@AfterMethod(alwaysRun = true)`;
  assert `closeCode()`.
- **A `route.fulfill` "chunked" `text/event-stream` body as an SSE stream.** It arrives at once and replays on
  every reconnect. *Fix:* a fixed event set over a `204` route for rendering; a real SSE server for timing.
- **`ws.onMessage(message -> message.contains(...))` on a `WebSocketRoute`.** The handler receives a
  `WebSocketFrame`, not a `String`. *Fix:* `frame.text()`.
- **Raw `page.` calls in a browser test.** *Fix:* page objects and `MockStreams`.
- **Using OkHttp raw `WebSocket` for a STOMP endpoint.** *Fix:* `WebSocketStompClient`.

## Rules (hard constraints)

- **Real-time = await a condition, never a sleep.** `poll(timeout)` / Awaitility / Playwright
  `waitForFrameReceived(predicate)`. No `Thread.sleep` / `page.waitForTimeout` as a wait.
- **Drain before you act** — wire the listener / `subscribe` / arm `waitForWebSocket` **before** the trigger.
- **Assert the whole lifecycle** — the 101 upgrade, the frames, **and** the clean close (code **1000** / the
  contract's close code). "N then close" = await count N, *then* assert close.
- **Use the right client** — OkHttp `WebSocket` (raw, reassembles), `WebSocketStompClient` (STOMP), OkHttp-SSE /
  `WebClient` `Flux` (SSE, no read timeout).
- **Browser SSE is mocked only as a fixed event set followed by `204`**; anything about time goes to a real server.
- **Browser tests extend `BaseTest`** and reach the page through page objects and `MockStreams`; probes and
  sockets close in `@AfterMethod(alwaysRun = true)`, never in a `try` inside the test.
- **Auth tokens from env, read lazily, never logged**; a browser `EventSource` can't set headers — query/cookie.
- Constructor injection for the SUT's stream client; test names `Should_X_When_Y`; one logical assertion per
  test; builders for 4+-field payloads; no secrets in code.

## Cross-references

- `qa-realtime-stream-testing-dotnet` — the family lead: raw `ClientWebSocket`, SignalR `HubConnection`,
  `SseParser`, a `Channel<T>` deadline, Playwright-.NET observe/mock.
- `qa-realtime-stream-testing-typescript` — the `ws` lib / native `WebSocket`, `EventSource`, Playwright-TS; its
  `MockStreams` is the same fixed-event-set shape.
- `qa-messaging-testing-java` — the **eventual-consistency lineage** and the **boundary**: messaging = discrete
  queue/topic messages; this skill = an open WS/SSE stream.
- `qa-network-mocking-java` — the **HTTP** mock counterpart and the "register before the action" rule; this skill
  owns WebSocket mocking and browser SSE.
- `qa-ui-test-writer-playwright-java` — `BaseTest` and the page-object rules the browser surface layers on.
- `qa-test-login-tokens-java` — tokens for an authenticated socket, read from env, never logged.
