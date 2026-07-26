# Deep-dive details — `qa-realtime-stream-testing-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

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
