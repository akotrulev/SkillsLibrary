---
name: qa-websocket-sse-testing-java
description: >-
  Test real-time **WebSocket** and **Server-Sent-Events (SSE)** streams in Java 21 / TestNG — from test code
  directly (protocol-client) and through the browser (Playwright). Covers **OkHttp `WebSocket`**
  (`newWebSocket` + a `WebSocketListener` draining frames into a `BlockingQueue`, `send`, `close(1000, …)`),
  Java-WebSocket (`WebSocketClient`) and Spring `WebSocketStompClient` when the endpoint speaks STOMP, SSE via
  **OkHttp-SSE** (`EventSources` + `EventSourceListener`) or Spring `WebClient` `Flux<ServerSentEvent<T>>` +
  reactor-test `StepVerifier`, **awaiting a message on a CONDITION with Awaitility (`await().atMost().until(...)`)
  or `queue.poll(timeout)` — never `Thread.sleep`**, asserting the full lifecycle (101 handshake → frames →
  clean close code), reconnection/backoff, message fragmentation/backpressure, auth on the socket (token in
  query string / `Sec-WebSocket-Protocol` subprotocol / first frame), ping/pong heartbeat, and the **browser
  surface** — Playwright `page.waitForWebSocket` + `ws.onFrameReceived` to OBSERVE frames and
  `page.routeWebSocket` (Playwright ≥ 1.48) to MOCK them. Triggers: "test our WebSocket chat endpoint",
  "assert the server pushes N SSE events then closes", "wait for a websocket frame without a sleep", "test
  STOMP-over-WebSocket reconnection", "mock the websocket the UI opens in Playwright", "verify the live-feed
  stream over SSE". Do NOT use for: the .NET stack (use qa-websocket-sse-testing-dotnet), the TypeScript stack
  (use qa-websocket-sse-testing-typescript), async **broker** messaging — queues/topics (use
  qa-messaging-testing-service-bus-java / -sqs / -kafka / -rabbitmq), mocking a plain request/response **HTTP**
  dependency (use qa-api-mocking-wiremock-java or qa-network-monitoring-playwright-routes-java), or authoring
  the page objects the browser tests reuse (use qa-ui-test-author-playwright-java).
---

# WebSocket & SSE Testing (Java 21 / TestNG) — **ported from the canonical `qa-websocket-sse-testing-dotnet`**

> **Ported from the canonical `qa-websocket-sse-testing-dotnet`.** The four ideas and the section order are
> identical; only the protocol-client library (OkHttp `WebSocket` instead of `ClientWebSocket`) and the
> await primitive (Awaitility / `BlockingQueue.poll` instead of a `Channel` + `CancellationTokenSource`)
> change. See the .NET file for the rationale behind the family; this is the Java expression of the same
> discipline. **.NET leads the family by judgment** (richest *native* real-time story); the Java protocol
> clients are third-party (OkHttp / Spring) but the disciplines port directly, and the **Playwright browser
> surface is near-identical**.

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
>    `Thread.sleep(2000)` standing in for "it probably arrived". The *exact* eventual-consistency lineage of
>    `qa-messaging-testing-service-bus-java` (a stream frame is a message that arrives later).
> 2. **Drain BEFORE you act.** Register the `WebSocketListener` / arm `page.waitForWebSocket` **before** the
>    action that triggers the first frames, or you race the server and lose them.
> 3. **Assert the whole lifecycle, not just a payload.** The open handshake (HTTP **101 Switching Protocols**
>    for WS — surfaced in `onOpen`), the frames, **and** the clean close (close code **1000**, or the
>    contract's documented close code). "Server emits N then closes" = await `size == N`, *then* assert the
>    close — never assert count inside a sleep-bounded window.
> 4. **Two transports × two surfaces — choose deliberately.** **Transport:** WebSocket (bidirectional) vs SSE
>    (server→client, auto-reconnect). **Surface:** protocol-client (connect from test code, no browser —
>    backend/contract verification) vs browser (the app's UI opens the socket — Playwright `OBSERVE` or
>    `MOCK`). Pick the narrowest surface that proves the behaviour.

## Decision matrix — which transport, which surface, which tool

| Situation | Transport | Surface / Tool |
|-----------|-----------|----------------|
| Backend WS endpoint, no browser involved (chat, trading feed) | WebSocket | **protocol-client** — OkHttp `WebSocket` |
| The endpoint speaks **STOMP-over-WS** (Spring messaging) | WebSocket | **protocol-client** — Spring `WebSocketStompClient` |
| Server pushes a one-way feed (notifications, progress, live dashboard) | SSE | **protocol-client** — OkHttp-SSE / `WebClient` `Flux<ServerSentEvent>` |
| The app's **UI** opens a WS and you assert what crosses the wire | WebSocket | **browser** — Playwright `waitForWebSocket` + `onFrameReceived` (OBSERVE) |
| The UI opens a WS and you want **deterministic** frames (no real server) | WebSocket | **browser** — Playwright `routeWebSocket` (MOCK) |
| The UI consumes an SSE feed and you want it deterministic | SSE | **browser** — `page.route` returning a chunked `text/event-stream` body |
| Async **queue/topic** (OrderPlaced lands on a queue, a consumer reacts) | — | **not this skill** → `qa-messaging-testing-service-bus-java` (#28) etc. |
| A plain request/response **HTTP** dependency to fake | — | **not this skill** → `qa-api-mocking-wiremock-java` (#22) / `qa-network-monitoring-playwright-routes-java` (#8) |

**Rule of thumb:** *bidirectional, interactive?* → WebSocket. *Server-push-only feed?* → SSE. *Testing the
protocol contract?* → protocol-client. *Testing the UI's use of the stream?* → browser (observe if the real
server is fine, mock if you need determinism). *A discrete message on a queue, not an open stream?* → that's
`messaging-testing`.

## Stack

- Java 21, TestNG, Gradle (Kotlin DSL) — async handled via listeners + `BlockingQueue`; tests are synchronous
- `com.squareup.okhttp3:okhttp` — the raw WebSocket client (`newWebSocket` + `WebSocketListener`)
- `com.squareup.okhttp3:okhttp-sse` — the SSE client (`EventSources` + `EventSourceListener`); **or**
  `org.springframework:spring-webflux` `WebClient` returning `Flux<ServerSentEvent<T>>` + `reactor-test`
  `StepVerifier` when the SUT is reactive
- `org.springframework:spring-websocket` `WebSocketStompClient` only when the endpoint speaks **STOMP**
- `org.awaitility:awaitility` — `await().atMost(...).until(...)` is the **bounded condition-wait**; `BlockingQueue.poll(timeout)` is the simpler form
- `org.springframework.boot:spring-boot-starter-test` `@SpringBootTest(webEnvironment = RANDOM_PORT)` — a
  **real port** so the WS upgrade works (an in-memory mock servlet can't upgrade)
- Browser surface: `com.microsoft.playwright:playwright` (≥ **1.48** for `routeWebSocket`), built on the
  `BasePage`/`BaseTest` model from `qa-ui-test-author-playwright-java`
- The SUT's stream client is **constructor-injected** with its URL / an `OkHttpClient` — never a hard-coded
  URL read inside an `@Test`

```
src/test/java/realtime/
├── WebSocketProbe.java       ← test-side WS client: listener drains frames into a BlockingQueue, await on a condition
├── SseProbe.java             ← test-side SSE client: EventSourceListener drains events into a BlockingQueue
├── ChatWebSocketTest.java    ← protocol-client WS
├── NotificationsSseTest.java ← protocol-client SSE
└── specs/
    └── LiveFeedBrowserTest.java  ← Playwright observe + mock (browser surface)
```

## WebSocket vs SSE — when each, and what changes in the test

| | **WebSocket** | **SSE (Server-Sent Events)** |
|---|---|---|
| Direction | Bidirectional (client ↔ server) | Server → client only |
| Payload | Text **or** binary | Text/UTF-8 only (`data:` lines) |
| Transport | HTTP **upgrade** (101 Switching Protocols) | Plain HTTP streaming `text/event-stream` |
| Reconnect | **None built-in** — you implement/assert it | **Built-in** — auto-reconnect honoring `retry:` + `Last-Event-ID` |
| Browser API | `WebSocket` (Playwright can observe **and** mock) | `EventSource` (just HTTP — observe/mock via `page.route`) |
| Test focus | Full-duplex frames + open/close lifecycle | Event sequence + resume-from-`Last-Event-ID` |
| Pick it for | Chat, collaboration, interactive/trading | Notification feeds, progress, server-pushed dashboards |

## The bounded condition-wait — the heart of every real-time test

A frame arrives whenever the server sends it. The test must **await the condition** with a **timeout**. The
listener pushes frames into a `BlockingQueue`; the test either `poll(timeout)` for the next one or uses
**Awaitility** for the "until N frames / until subscribed" gate. This is the WS/SSE analogue of
`qa-messaging-testing-service-bus-java`'s long-poll receive + Awaitility side-effect wait.

```java
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;
import static org.awaitility.Awaitility.await;
import static java.time.Duration.ofSeconds;

public final class AwaitFrame {

    /** Await the next frame, or fail if none arrives within the timeout. */
    public static <T> T next(BlockingQueue<T> queue, int timeoutSeconds) throws InterruptedException {
        T frame = queue.poll(timeoutSeconds, TimeUnit.SECONDS);   // returns the instant a frame is queued
        if (frame == null) throw new AssertionError("No frame arrived within " + timeoutSeconds + "s.");
        return frame;
    }

    /** Block until the queue holds at least {@code count} frames, or fail on timeout. */
    public static void untilCount(BlockingQueue<?> queue, int count, int timeoutSeconds) {
        await().atMost(ofSeconds(timeoutSeconds))
               .pollInterval(ofSeconds(0).plusMillis(50))
               .until(() -> queue.size() >= count);               // condition, not a clock
    }
}
```

> **No `Thread.sleep` anywhere as a wait.** `poll(timeout)` and `await().until(...)` return the instant the
> condition holds and *fail* if it never does. A fixed sleep races the server — slow when the frame is fast,
> flaky when it's slow.

## Protocol-client 1 — raw WebSocket (OkHttp `WebSocket`)

The test **is** a WebSocket client. OkHttp's `WebSocketListener` delivers `onOpen` / `onMessage` /
`onClosing` / `onClosed` / `onFailure` callbacks — push each message into a `BlockingQueue` so the test can
await on a condition. **Register the listener before sending** (it's wired at `newWebSocket`, so this is
automatic), and OkHttp **reassembles fragments for you** — `onMessage(String)` gives a whole logical message
(unlike .NET's raw `ReceiveAsync`).

```java
import okhttp3.*;
import okio.ByteString;
import java.util.concurrent.*;

public final class WebSocketProbe implements AutoCloseable {

    private final OkHttpClient client = new OkHttpClient.Builder().pingInterval(java.time.Duration.ofSeconds(20)).build();
    private final BlockingQueue<String> frames = new LinkedBlockingQueue<>();
    private final CompletableFuture<Boolean> opened = new CompletableFuture<>();
    private volatile int closeCode = -1;
    private volatile String closeReason;
    private WebSocket socket;

    public BlockingQueue<String> frames() { return frames; }
    public int closeCode() { return closeCode; }            // assert the close code
    public String closeReason() { return closeReason; }

    /** Connect and start draining. {@code configure} can add auth headers / subprotocol to the request. */
    public void connect(String url, java.util.function.Consumer<Request.Builder> configure) {
        Request.Builder builder = new Request.Builder().url(url);
        if (configure != null) configure.accept(builder);   // auth: header / Sec-WebSocket-Protocol go here
        socket = client.newWebSocket(builder.build(), new WebSocketListener() {
            @Override public void onOpen(WebSocket ws, Response response) {
                opened.complete(response.code() == 101);     // 101 Switching Protocols = the upgrade succeeded
            }
            @Override public void onMessage(WebSocket ws, String text) { frames.add(text); }           // reassembled
            @Override public void onMessage(WebSocket ws, ByteString bytes) { frames.add(bytes.utf8()); }
            @Override public void onClosing(WebSocket ws, int code, String reason) {
                closeCode = code; closeReason = reason;
                ws.close(1000, "ack");                        // echo the close handshake — clean on both ends
            }
            @Override public void onFailure(WebSocket ws, Throwable t, Response r) { opened.completeExceptionally(t); }
        });
    }

    /** Await the 101 upgrade on a condition before the test sends. */
    public void awaitOpen(int timeoutSeconds) throws Exception {
        if (!opened.get(timeoutSeconds, TimeUnit.SECONDS)) throw new AssertionError("WS did not upgrade (101)");
    }

    public void send(String text) { socket.send(text); }

    @Override public void close() {
        if (socket != null) socket.close(1000, "bye");        // clean close, code 1000
        client.dispatcher().executorService().shutdown();
    }
}
```

```java
import org.testng.annotations.*;
import static org.assertj.core.api.Assertions.assertThat;

public class ChatWebSocketTest extends AppFixture {   // AppFixture exposes baseWsUri() on a real port

    @Test
    public void should_broadcast_a_message_to_a_connected_client() throws Exception {
        try (WebSocketProbe probe = new WebSocketProbe()) {
            probe.connect(baseWsUri() + "/ws/chat", null);
            probe.awaitOpen(5);                                       // condition: the 101 upgrade

            probe.send("{ \"type\": \"say\", \"text\": \"hello\" }");

            String frame = AwaitFrame.next(probe.frames(), 5);        // await the broadcast on a condition
            assertThat(frame).contains("\"text\":\"hello\"");          // one logical assertion: the broadcast fact
        }
    }

    @Test
    public void should_emit_three_ticks_then_close_cleanly() throws Exception {
        WebSocketProbe probe = new WebSocketProbe();
        probe.connect(baseWsUri() + "/ws/ticker?count=3", null);
        probe.awaitOpen(5);

        AwaitFrame.untilCount(probe.frames(), 3, 5);                  // the N frames…
        probe.close();                                               // …then the close handshake
        await().atMost(ofSeconds(2)).until(() -> probe.closeCode() == 1000);   // …and the clean close
    }
}
```

## Protocol-client 2 — STOMP-over-WebSocket (Spring `WebSocketStompClient`)

When the endpoint speaks **STOMP** (Spring's messaging convention over WS), use `WebSocketStompClient` with a
`StompSessionHandler` and a `BlockingQueue`-backed `StompFrameHandler` — the canonical Spring integration-test
pattern. This is the Java analogue of the .NET SignalR section (a higher-level hub/messaging layer over the
raw socket; the client reassembles, heartbeats, and can reconnect).

```java
WebSocketStompClient stomp = new WebSocketStompClient(new StandardWebSocketClient());
stomp.setMessageConverter(new MappingJackson2MessageConverter());
BlockingQueue<ChatMessage> received = new LinkedBlockingQueue<>();

StompSession session = stomp.connectAsync(baseWsUri() + "/stomp", new StompSessionHandlerAdapter() {})
        .get(5, TimeUnit.SECONDS);                                   // connect = the condition-wait, not a sleep
session.subscribe("/topic/general", new StompFrameHandler() {
    @Override public Type getPayloadType(StompHeaders h) { return ChatMessage.class; }
    @Override public void handleFrame(StompHeaders h, Object payload) { received.add((ChatMessage) payload); }
});                                                                  // subscribe BEFORE triggering the server push
session.send("/app/say", new ChatMessage("alice", "hi"));

ChatMessage message = AwaitFrame.next(received, 5);
assertThat(message.text()).isEqualTo("hi");
```

> Configure heartbeats via `stomp.setDefaultHeartbeat(...)` + a `TaskScheduler` and assert reconnect behaviour
> by closing the session and re-subscribing — the STOMP layer absorbs the protocol so you assert *behaviour*.

## Protocol-client 3 — SSE (OkHttp-SSE / `WebClient` `Flux`)

SSE is **plain HTTP** — a `GET` whose body streams `text/event-stream`. With **OkHttp-SSE**, an
`EventSourceListener` delivers `onEvent(id, type, data)`; push each into a `BlockingQueue` and await. (OkHttp
streams the body — there's no "buffer the whole response" trap to avoid, unlike a naive `HttpClient`.)

```java
import okhttp3.sse.*;

public final class SseProbe implements AutoCloseable {
    private final OkHttpClient client = new OkHttpClient.Builder()
            .readTimeout(java.time.Duration.ZERO).build();           // an open-ended stream: no read timeout
    private final BlockingQueue<Sse> events = new LinkedBlockingQueue<>();
    private EventSource source;

    public record Sse(String type, String data, String id) {}
    public BlockingQueue<Sse> events() { return events; }

    public void subscribe(String url) {
        Request request = new Request.Builder().url(url).header("Accept", "text/event-stream").build();
        source = EventSources.createFactory(client).newEventSource(request, new EventSourceListener() {
            @Override public void onEvent(EventSource es, String id, String type, String data) {
                events.add(new Sse(type == null ? "message" : type, data, id));
            }
        });
    }

    @Override public void close() { if (source != null) source.cancel(); }
}
```

```java
@Test
public void should_stream_three_progress_events_then_a_done_event() throws Exception {
    try (SseProbe probe = new SseProbe()) {
        probe.subscribe(baseUri() + "/sse/progress?job=42");

        AwaitFrame.untilCount(probe.events(), 4, 5);

        var types = probe.events().stream().map(SseProbe.Sse::type).toList();
        assertThat(types).containsExactly("progress", "progress", "progress", "done");   // the event sequence
    }
}
```

> **Reactive SUT alternative:** a Spring `WebClient` returning `Flux<ServerSentEvent<String>>` is asserted
> with **reactor-test** `StepVerifier` — `.expectNextCount(3).expectNextMatches(e -> e.event().equals("done")).thenCancel().verify(Duration.ofSeconds(5))`.
> Use whichever matches the SUT; both express "N events then done" as a *condition*, never a sleep.

## Browser surface 1 — OBSERVE WebSocket frames (Playwright-Java)

When the **app's UI** opens the socket and the real backend is fine, **observe** the frames. Arm
`page.waitForWebSocket(...)` **before** the action that opens it; layer this on the `BasePage`/`BaseTest`
model from `qa-ui-test-author-playwright-java`.

```java
@Test
public void should_push_a_price_update_over_the_dashboard_socket() {
    // Arm the WS wait BEFORE navigating — the socket opens on load.
    WebSocket ws = page.waitForWebSocket(() -> page.navigate("/dashboard"));
    assertThat(ws.url()).contains("/ws/prices");

    // Await a frame on a condition (the predicate), not a sleep.
    WebSocketFrame frame = ws.waitForFrameReceived(
            new WebSocket.WaitForFrameReceivedOptions().setPredicate(f -> f.text().contains("\"symbol\":\"ACME\"")),
            () -> {});

    assertThat(frame.text()).contains("\"price\"");
    assertThat(page.getByTestId("acme-price")).not().isEmpty();   // the user-visible effect of the frame
}
```

`WebSocket` exposes `onFrameSent` / `onFrameReceived` (`WebSocketFrame.text()` / `.binary()`), `onClose`, and
`isClosed()` — enough to assert direction, payload, and lifecycle of what the page actually sends/receives.

## Browser surface 2 — MOCK WebSocket frames (Playwright `routeWebSocket`, ≥ 1.48)

When you need **deterministic** frames, **mock** the socket with `page.routeWebSocket` (Playwright **1.48**).
By default the routed socket does **not** connect to the real server — you script both directions. Register it
**before** the page opens the socket.

```java
@Test
public void should_render_the_alert_banner_when_the_socket_pushes_an_outage() {
    // Mock the socket: when the page sends "subscribe", push a canned outage frame back.
    page.routeWebSocket(java.util.regex.Pattern.compile(".*/ws/alerts"), ws -> {
        ws.onMessage(message -> {
            if (message.contains("subscribe"))
                ws.send("{ \"type\": \"outage\", \"region\": \"EU\" }");   // server→page, fully deterministic
        });
    });

    page.navigate("/status");

    assertThat(page.getByRole(AriaRole.ALERT)).containsText("EU outage");
}
```

> **Pass-through / intercept-and-modify:** call `ws.connectToServer()` inside the handler to get the
> *server-side* route — forward most frames to the real backend and rewrite only the one under test. **Caveat
> (Playwright #33370):** driving server-initiated frames *on demand* from the route (outside a message
> handler) has had quirks — for "server spontaneously emits" scenarios, an observe test against a real test
> server is more reliable than a mock. **SSE has no dedicated Playwright API** — `EventSource` is just a
> streaming HTTP GET, so mock it with `page.route` returning a chunked `text/event-stream` body (or observe it
> via `page.onResponse`); a protocol-client SSE test is usually cleaner for asserting the server's sequence.

## Disciplines & gotchas (apply to every real-time test)

- **Await a condition, never a sleep** — `BlockingQueue.poll(timeout)` / Awaitility `await().until(...)` /
  `waitForFrameReceived(predicate)`. No `Thread.sleep`-as-wait, no `page.waitForTimeout`.
- **Lifecycle:** `onOpen` with `response.code() == 101` is the handshake assertion (a failed upgrade hits
  `onFailure`); always `close(1000, …)` in teardown and assert the close code where the contract specifies one.
  Wire the listener (drain) **before** sending to avoid a race on the first frames.
- **Server emits N then closes:** `AwaitFrame.untilCount(queue, N, timeout)` then assert the close — never
  assert the count inside a sleep-bounded window.
- **Reconnection / backoff:** drop the server (or `ws.close()` the route) and assert the client reconnects with
  increasing intervals (STOMP session re-subscribe; SSE reconnects natively, honoring `retry:` and resending
  `Last-Event-ID` so the server resumes — assert missed events are replayed from that id). OkHttp doesn't
  auto-reconnect a raw WS; if the SUT wraps reconnect logic, assert *that*.
- **Fragmentation / backpressure:** OkHttp's `onMessage(String)` delivers a *reassembled* logical message
  (one of the few places Java is simpler than the raw .NET loop); still send a large message and assert it
  arrives whole.
- **Auth on the socket** — cover all three patterns: token in the **query string** (`?access_token=…`), token
  via **subprotocol** (`builder.header("Sec-WebSocket-Protocol", token)`), or token in the **first frame**
  after connect. Read the token from **env, lazily, never logged** (cross-link `qa-auth0-test-tokens-java`).
  For SSE, an OkHttp request can set `Authorization`, but a *browser* `EventSource` **cannot set headers** →
  query-param or cookie auth.
- **Heartbeat (ping/pong):** OkHttp's `pingInterval(...)` drives client pings; assert the app-level heartbeat
  / that a missed pong triggers the SUT's reconnect. STOMP heartbeats via `setDefaultHeartbeat`.
- **WS upgrade in integration tests** needs a **real port** — `@SpringBootTest(webEnvironment = RANDOM_PORT)`,
  not a mock servlet (which can't upgrade).

## Anti-patterns

- **`Thread.sleep(2000)` then read one frame.** Races the server; slow when fast, flaky when slow. *Fix:*
  `AwaitFrame.next(queue, timeout)` — returns the instant the frame queues, fails if it never does.
- **Buffering the SSE response with a read timeout.** A finite `readTimeout` aborts an open-ended stream
  mid-flight. *Fix:* `readTimeout(Duration.ZERO)` on the OkHttp-SSE client (or `WebClient` + `StepVerifier`).
- **Wiring the listener / subscribing *after* the action.** The first frames fire before you're listening.
  *Fix:* `newWebSocket` (listener wired at construction) / `session.subscribe(...)` / `waitForWebSocket`
  **before** the trigger.
- **Never closing the socket** (or asserting only the payload). The connection leaks across tests and you
  never catch a bad close code. *Fix:* `close(1000, …)` in teardown (try-with-resources); assert `closeCode()`.
- **`Thread.sleep` to "let it reconnect".** *Fix:* assert the reconnected state on a condition (re-subscribe;
  await the next frame after the drop).
- **Using OkHttp raw `WebSocket` for a STOMP endpoint.** You'd re-implement STOMP framing. *Fix:*
  `WebSocketStompClient`.
- **Reaching for this skill for a queue/topic.** A discrete message on a broker is *not* an open stream. *Fix:*
  `qa-messaging-testing-service-bus-java` (#28) and siblings.
- **Token hard-coded or logged.** *Fix:* env, read lazily, never logged (`qa-auth0-test-tokens-java`).

## Examples

**End-to-end: a WebSocket request/response round-trip with a clean close, asserted lifecycle-first.**

```java
public class EchoSocketTest extends AppFixture {
    @Test
    public void should_echo_a_message_and_close_with_code_1000() throws Exception {
        WebSocketProbe probe = new WebSocketProbe();
        probe.connect(baseWsUri() + "/ws/echo", null);
        probe.awaitOpen(5);                                          // 101 upgrade

        probe.send("ping");
        assertThat(AwaitFrame.next(probe.frames(), 5)).isEqualTo("ping");

        probe.close();                                              // clean close handshake
        await().atMost(ofSeconds(2)).until(() -> probe.closeCode() == 1000);   // code 1000
    }
}
```

**Auth via subprotocol (token on the handshake, read from env, never logged):**

```java
probe.connect(baseWsUri() + "/ws/secure",
        builder -> builder.header("Sec-WebSocket-Protocol", TestTokens.accessToken()));   // env-sourced; see qa-auth0-test-tokens-java
```

**Composing with a test-data builder for the frame payload (4+ fields → builder, per the global rules):**

```java
var payload = ChatMessages.standard().withText("hello").withRoom("general").build();   // qa-test-data-builder-java
probe.send(new ObjectMapper().writeValueAsString(payload));
```

## Rules (hard constraints)

- **Real-time = await a condition, never a sleep.** Drain into a `BlockingQueue`, await with `poll(timeout)` /
  Awaitility `await().atMost().until(...)` / Playwright `waitForFrameReceived(predicate)`. **No `Thread.sleep`/
  `page.waitForTimeout` as a wait.**
- **Drain before you act** — wire the `WebSocketListener` / `subscribe` / arm `waitForWebSocket` **before** the
  trigger, or you race the first frames.
- **Assert the whole lifecycle** — the 101 upgrade (`onOpen` `response.code() == 101`; failed upgrade →
  `onFailure`), the frames, **and** the clean close (code **1000** / the contract's close code). "N then close"
  = await count N, *then* assert close.
- **Use the right client** — OkHttp `WebSocket` (raw, reassembles), `WebSocketStompClient` (STOMP), OkHttp-SSE
  / `WebClient` `Flux` (SSE, no read timeout). Don't hand-roll STOMP over a raw socket.
- **Pick the transport and surface deliberately** — WS (bidirectional) vs SSE (server-push, free reconnect);
  protocol-client (contract) vs browser (observe if the real server suffices, `routeWebSocket` to mock).
- **Auth tokens from env, read lazily, never logged** (query / subprotocol / first-frame; browser `EventSource`
  can't set headers — query/cookie). WS upgrade integration tests need a **real port** (`RANDOM_PORT`).
- Constructor injection for the SUT's stream client; test names `Should_X_When_Y` (`should_x_when_y`); one
  logical assertion per test; builders for 4+-field payloads; structured logging; no secrets in code.

## Cross-references

- `qa-websocket-sse-testing-dotnet` — **the canonical file**: same four ideas, raw `ClientWebSocket` (with the
  `EndOfMessage` fragment-reassembly loop), SignalR `HubConnection`, `SseParser`, a `Channel<T>` +
  `CancellationTokenSource` deadline as the condition-wait, Playwright-.NET observe/mock. Read it for the
  family rationale.
- `qa-websocket-sse-testing-typescript` — same four ideas, the **`ws`** lib / native `WebSocket` (the Node-22
  boundary), a promise-with-timeout + Vitest `vi.waitFor`, native `EventSource` / the `eventsource` package,
  Playwright-TS (`waitForEvent('websocket')`, `on('framereceived')`, `routeWebSocket`).
- `qa-messaging-testing-service-bus-java` (#28) — the **eventual-consistency lineage** (a stream frame is a
  message that arrives later) and the **boundary**: messaging = discrete queue/topic messages with a consumer;
  this skill = an open WS/SSE stream. (Plus `-sqs` #29 / `-kafka` #30 / `-rabbitmq` #31.)
- `qa-network-monitoring-playwright-routes-java` (#8) — the **HTTP** mock counterpart and the "register before
  the action" ordering rule; SSE-in-the-browser mocking reuses its `page.route`.
- `qa-api-mocking-wiremock-java` (#22) — fake a *synchronous* HTTP dependency; not a stream.
- `qa-ui-test-author-playwright-java` — the `BasePage`/`BaseTest` model the **browser-surface** tests layer on;
  the no-`waitForTimeout` discipline originates there.
- `qa-auth0-test-tokens-java` (#16) — tokens for an authenticated socket, read from env, never logged.
- `qa-test-environments-java` (#14) — booting the SUT on a real port with the readiness-wait discipline.
  `qa-allure-reporting-java` — attach captured frames / the event sequence. `qa-test-data-builder-java` —
  frame payloads with 4+ fields.
