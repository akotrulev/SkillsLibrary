# Deep-dive details — `qa-java:realtime-stream-testing`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Protocol-client 1 — raw WebSocket (OkHttp `WebSocket`)

The test **is** a WebSocket client. OkHttp's `WebSocketListener` delivers `onOpen` / `onMessage` /
`onClosing` / `onClosed` / `onFailure` callbacks — push each message into a `BlockingQueue` so the test can
await on a condition. The listener is wired at `newWebSocket`, so it is registered before anything is sent, and
OkHttp **reassembles fragments for you** — `onMessage(String)` gives a whole logical message (unlike .NET's raw
`ReceiveAsync`). `onOpen` completes with the 101 check; `onClosing` records the close code and echoes the close
handshake so both ends close cleanly. `configure` adds auth headers or the `Sec-WebSocket-Protocol` subprotocol.

```java
import okhttp3.*;
import okio.ByteString;

import java.time.Duration;
import java.util.concurrent.*;
import java.util.function.Consumer;

public final class WebSocketProbe implements AutoCloseable {

    private final OkHttpClient client = new OkHttpClient.Builder().pingInterval(Duration.ofSeconds(20)).build();
    private final BlockingQueue<String> frames = new LinkedBlockingQueue<>();
    private final CompletableFuture<Boolean> opened = new CompletableFuture<>();
    private volatile int closeCode = -1;
    private WebSocket socket;

    public BlockingQueue<String> frames() { return frames; }
    public int closeCode() { return closeCode; }

    public void connect(String url, Consumer<Request.Builder> configure) {
        Request.Builder builder = new Request.Builder().url(url);
        configure.accept(builder);
        socket = client.newWebSocket(builder.build(), new WebSocketListener() {
            @Override public void onOpen(WebSocket ws, Response response) { opened.complete(response.code() == 101); }
            @Override public void onMessage(WebSocket ws, String text) { frames.add(text); }
            @Override public void onMessage(WebSocket ws, ByteString bytes) { frames.add(bytes.utf8()); }
            @Override public void onClosing(WebSocket ws, int code, String reason) {
                closeCode = code;
                ws.close(1000, "ack");
            }
            @Override public void onFailure(WebSocket ws, Throwable t, Response r) { opened.completeExceptionally(t); }
        });
    }

    public void awaitOpen(Duration timeout) throws Exception {
        if (!opened.get(timeout.toMillis(), TimeUnit.MILLISECONDS)) {
            throw new AssertionError("WebSocket did not upgrade (101)");
        }
    }

    public void send(String text) { socket.send(text); }

    public void closeNormally() { socket.close(1000, "bye"); }

    @Override public void close() {
        if (socket != null) {
            socket.close(1000, "bye");
        }
        client.dispatcher().executorService().shutdown();
    }
}
```

The probe is created in `@BeforeMethod` and closed in `@AfterMethod(alwaysRun = true)` — never a
try-with-resources inside the test.

```java
import org.testng.annotations.*;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

public class ChatWebSocketTest extends AppFixture {
    private static final Duration FRAME_TIMEOUT = Duration.ofSeconds(5);
    private WebSocketProbe probe;

    @BeforeMethod(alwaysRun = true)
    public void openProbe() {
        probe = new WebSocketProbe();
    }

    @AfterMethod(alwaysRun = true)
    public void closeProbe() {
        probe.close();
    }

    @Test
    public void Should_BroadcastMessage_When_ClientSays() throws Exception {
        probe.connect(baseWsUri() + "/ws/chat", request -> { });
        probe.awaitOpen(FRAME_TIMEOUT);

        probe.send("{ \"type\": \"say\", \"text\": \"hello\" }");

        assertThat(AwaitFrame.next(probe.frames(), FRAME_TIMEOUT)).contains("\"text\":\"hello\"");
    }

    @Test
    public void Should_CloseWithCode1000_When_TickerHasEmittedThreeTicks() throws Exception {
        probe.connect(baseWsUri() + "/ws/ticker?count=3", request -> { });
        probe.awaitOpen(FRAME_TIMEOUT);
        AwaitFrame.untilCount(probe.frames(), 3, FRAME_TIMEOUT);

        probe.closeNormally();

        await("close code").atMost(Duration.ofSeconds(2))
                .untilAsserted(() -> assertThat(probe.closeCode()).isEqualTo(1000));
    }
}
```

`AppFixture` is the `@SpringBootTest(webEnvironment = RANDOM_PORT)` base that exposes `baseWsUri()` on a real
port. `untilAsserted` fails with the last value it saw, which a bare `until(() -> code == 1000)` would not print.

## Protocol-client 2 — STOMP-over-WebSocket (Spring `WebSocketStompClient`)

When the endpoint speaks **STOMP** (Spring's messaging convention over WS), use `WebSocketStompClient` with a
`StompSessionHandler` and a `BlockingQueue`-backed `StompFrameHandler` — the canonical Spring integration-test
pattern, and the Java analogue of the .NET SignalR section. `connectAsync(...).get(timeout)` is the
condition-wait for the connection; `subscribe` runs before the `send` that triggers the server push.

```java
WebSocketStompClient stomp = new WebSocketStompClient(new StandardWebSocketClient());
stomp.setMessageConverter(new MappingJackson2MessageConverter());
BlockingQueue<ChatMessage> received = new LinkedBlockingQueue<>();

StompSession session = stomp.connectAsync(baseWsUri() + "/stomp", new StompSessionHandlerAdapter() { })
        .get(5, TimeUnit.SECONDS);
session.subscribe("/topic/general", new StompFrameHandler() {
    @Override public Type getPayloadType(StompHeaders h) { return ChatMessage.class; }
    @Override public void handleFrame(StompHeaders h, Object payload) { received.add((ChatMessage) payload); }
});
session.send("/app/say", new ChatMessage("alice", "hi"));

assertThat(AwaitFrame.next(received, Duration.ofSeconds(5)).text()).isEqualTo("hi");
```

Configure heartbeats via `stomp.setDefaultHeartbeat(...)` + a `TaskScheduler` and assert reconnect behaviour by
closing the session and re-subscribing — the STOMP layer absorbs the protocol so you assert *behaviour*. The
session is disconnected in `@AfterMethod(alwaysRun = true)`.

## Protocol-client 3 — SSE (OkHttp-SSE / `WebClient` `Flux`)

SSE is **plain HTTP** — a `GET` whose body streams `text/event-stream`. With **OkHttp-SSE**, an
`EventSourceListener` delivers `onEvent(id, type, data)`; push each into a `BlockingQueue` and await. The client
has no read timeout, because the stream is open-ended.

```java
import okhttp3.sse.*;

public final class SseProbe implements AutoCloseable {
    private final OkHttpClient client = new OkHttpClient.Builder().readTimeout(Duration.ZERO).build();
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

    @Override public void close() {
        if (source != null) {
            source.cancel();
        }
    }
}
```

```java
@Test
public void Should_StreamThreeProgressEventsThenDone_When_JobRuns() {
    sseProbe.subscribe(baseUri() + "/sse/progress?job=42");

    AwaitFrame.untilCount(sseProbe.events(), 4, Duration.ofSeconds(5));

    assertThat(sseProbe.events().stream().map(SseProbe.Sse::type).toList())
            .containsExactly("progress", "progress", "progress", "done");
}
```

`sseProbe` is built in `@BeforeMethod` and closed in `@AfterMethod(alwaysRun = true)`. **`Last-Event-ID` resume**
is asserted against a real server: subscribe, take two events, drop the connection, resubscribe with the header
set to the last id, and assert the next event follows it with nothing replayed.

> **Reactive SUT alternative:** a Spring `WebClient` returning `Flux<ServerSentEvent<String>>` is asserted
> with **reactor-test** `StepVerifier` — `.expectNextCount(3).expectNextMatches(e -> e.event().equals("done")).thenCancel().verify(Duration.ofSeconds(5))`.
> Both express "N events then done" as a *condition*, never a sleep.

## Browser page objects and `MockStreams`

Browser tests extend J1's `BaseTest` (`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`) and build
these in their own `@BeforeMethod`, after `BaseTest` has opened the page:

```java
@BeforeMethod(alwaysRun = true)
public void createPages() {
    dashboardPage = new DashboardPage(page);
    statusPage = new StatusPage(page);
    mockStreams = new MockStreams(page);
}
```

A page object that opens a socket arms `waitForWebSocket` **before** it navigates and returns the socket.

```java
public final class DashboardPage {
    private final Page page;
    private final Locator acmePrice;

    public DashboardPage(Page page) {
        this.page = page;
        this.acmePrice = page.getByTestId("Prices.Acme").describe("ACME price");
    }

    public WebSocket openWatchingPrices() {
        return page.waitForWebSocket(
                new Page.WaitForWebSocketOptions().setPredicate(ws -> ws.url().endsWith("/ws/prices")),
                () -> page.navigate("/dashboard"));
    }

    public Locator acmePrice() {
        return acmePrice;
    }
}
```

```java
public final class StatusPage {
    private final Page page;
    private final Locator alert;
    private final Locator notifications;

    public StatusPage(Page page) {
        this.page = page;
        this.alert = page.getByRole(AriaRole.ALERT);
        this.notifications = page.getByTestId("Notifications.Item");
    }

    public void open() {
        page.navigate("/status");
    }

    public Locator alert() {
        return alert;
    }

    public Locator notifications() {
        return notifications;
    }
}
```

`MockStreams` owns every stream route. `serveNotifications` registers the `204` route first and the one-time
event body second: routes run in reverse registration order, so the first request gets the events
(`setTimes(1)`) and every reconnect gets the `204` that stops `EventSource`.

```java
public final class MockStreams {
    private static final Pattern ALERT_SOCKET = Pattern.compile(".*/ws/alerts$");
    private static final String NOTIFICATION_STREAM = "**/api/notifications/stream";

    private final Page page;

    public MockStreams(Page page) {
        this.page = page;
    }

    public void pushOutageOnSubscribe(String region) {
        String outage = "{\"type\":\"outage\",\"region\":\"" + region + "\"}";
        page.routeWebSocket(ALERT_SOCKET, ws -> ws.onMessage(frame -> {
            if (frame.text().contains("subscribe")) {
                ws.send(outage);
            }
        }));
    }

    public void serveNotifications(List<NotificationEvent> events) {
        String body = events.stream()
                .map(event -> "id: " + event.id() + "\nevent: " + event.type() + "\ndata: " + event.text() + "\n\n")
                .collect(Collectors.joining());
        page.route(NOTIFICATION_STREAM, route -> route.fulfill(new Route.FulfillOptions().setStatus(204)));
        page.route(NOTIFICATION_STREAM,
                route -> route.fulfill(new Route.FulfillOptions()
                        .setStatus(200)
                        .setContentType("text/event-stream")
                        .setBody(body)),
                new Page.RouteOptions().setTimes(1));
    }

    public record NotificationEvent(String id, String type, String text) {}
}
```

- The `WebSocketRoute.onMessage` handler is a `Consumer<WebSocketFrame>`; `frame.text()` is the page's message
  (`frame.binary()` for a binary frame).
- That `EventSource` stops on a routed `204` in Chromium is the SSE specification's behaviour, carried from the TS
  lane (plan D64); it is not yet run in this library from Java.
- A route handler never sleeps: Java runs it on Playwright's dispatch loop, so a sleep there stalls every event.

## Disciplines & gotchas (apply to every real-time test)

- **Await a condition, never a sleep** — `BlockingQueue.poll(timeout)` / Awaitility `await().until(...)` /
  `waitForFrameReceived(predicate)`. No `Thread.sleep`-as-wait, no `page.waitForTimeout`.
- **Lifecycle:** `onOpen` with `response.code() == 101` is the handshake assertion (a failed upgrade hits
  `onFailure`); close with code 1000 in teardown and assert the close code where the contract specifies one.
- **Server emits N then closes:** `AwaitFrame.untilCount(queue, N, timeout)` then assert the close.
- **Reconnection / backoff:** drop the server (or `ws.close()` the route) and assert the client reconnects with
  increasing intervals (STOMP session re-subscribe; SSE reconnects natively, honoring `retry:` and resending
  `Last-Event-ID` so the server resumes). OkHttp doesn't auto-reconnect a raw WS; if the SUT wraps reconnect
  logic, assert *that*.
- **Fragmentation / backpressure:** OkHttp's `onMessage(String)` delivers a *reassembled* logical message; still
  send a large message and assert it arrives whole.
- **Auth on the socket** — token in the **query string** (`?access_token=…`), via **subprotocol**
  (`builder.header("Sec-WebSocket-Protocol", token)`), or in the **first frame** after connect. Read the token
  from **env, lazily, never logged** (`qa-java:test-login-tokens`). A *browser* `EventSource` **cannot set
  headers** → query-param or cookie auth.
- **Heartbeat (ping/pong):** OkHttp's `pingInterval(...)` drives client pings; assert the app-level heartbeat /
  that a missed pong triggers the SUT's reconnect. STOMP heartbeats via `setDefaultHeartbeat`.
- **WS upgrade in integration tests** needs a **real port** — `@SpringBootTest(webEnvironment = RANDOM_PORT)`.

## Examples

**Auth via subprotocol (token on the handshake, read from env, never logged):**

```java
probe.connect(baseWsUri() + "/ws/secure",
        request -> request.header("Sec-WebSocket-Protocol", TestTokens.accessToken()));
```

**A 4+-field frame payload comes from a builder (`qa-java:test-data-builder`):**

```java
ChatMessage payload = ChatMessages.standard().withText("hello").withRoom("general").build();
probe.send(json.writeValueAsString(payload));
```

`json` is the test class's one `ObjectMapper` field.
