---
name: qa-websocket-sse-testing-dotnet
description: >-
  Test real-time **WebSocket** and **Server-Sent-Events (SSE)** streams in .NET 8 / NUnit — from test code
  directly (protocol-client) and through the browser (Playwright). Covers raw `ClientWebSocket`
  (`ConnectAsync` / `SendAsync` / the `ReceiveAsync` reassembly loop / `CloseAsync` with a close code),
  SignalR `HubConnection` (`On<T>` + `InvokeAsync`, `WithAutomaticReconnect`, keep-alive), SSE via
  `System.Net.ServerSentEvents` `SseParser` (or manual `data:`/`event:`/`id:` line parsing of a streamed
  `HttpClient` response), **draining frames into a `Channel<T>` and awaiting a message on a CONDITION with a
  `CancellationTokenSource` timeout — never `Task.Delay`/`Thread.Sleep`**, asserting the full lifecycle (101
  handshake → frames → clean close code), reconnection/backoff, message fragmentation/backpressure, auth on
  the socket (token in query string / `Sec-WebSocket-Protocol` subprotocol / first frame), ping/pong
  heartbeat, and the **browser surface** — Playwright `Page.WaitForWebSocketAsync` + `IWebSocket.FrameReceived`
  to OBSERVE frames and `Page.RouteWebSocketAsync` (Playwright ≥ 1.48) to MOCK them. Triggers: "test our
  WebSocket chat endpoint", "assert the server pushes N SSE events then closes", "wait for a websocket frame
  without a sleep", "test SignalR hub reconnection", "mock the websocket the UI opens in Playwright", "verify
  the live-feed stream over SSE". Do NOT use for: the Java stack (use qa-websocket-sse-testing-java), the
  TypeScript stack (use qa-websocket-sse-testing-typescript), async **broker** messaging — queues/topics
  (use qa-messaging-testing-service-bus-dotnet / -sqs / -kafka / -rabbitmq), mocking a plain request/response
  **HTTP** dependency (use qa-api-mocking-wiremock-dotnet or qa-network-monitoring-playwright-routes-dotnet),
  or authoring the page objects the browser tests reuse (use qa-ui-test-author-playwright-dotnet).
---

# WebSocket & SSE Testing (.NET 8 / NUnit) — **canonical stack**

This is the **canonical** stack of the `qa/dotnet/skills/websocket-sse-testing/` node — a **NEW family, not a port**. **.NET
leads here by judgment** (the "lead where the tool is most authentic" call #28/#30/#36 made): .NET has the
**richest *native* real-time story** of the three — raw `System.Net.WebSockets.ClientWebSocket` (the protocol
itself), the first-party `SignalR` `HubConnection` (the hub layer, with built-in reconnect/heartbeat/groups),
and built-in SSE parsing (`System.Net.ServerSentEvents.SseParser` on .NET 9+) — **all in the BCL, no
third-party client dependency**. That makes it the cleanest reference for every discipline; the `java`
(OkHttp `WebSocket` + Awaitility / OkHttp-SSE) and `typescript` (`ws` / native `WebSocket` + `eventsource` +
Vitest `vi.waitFor`) siblings **port the disciplines, not the code** — the protocol-client libraries and the
await primitive genuinely differ per stack, while the **Playwright browser surface is near-identical** across
all three.

Real-time tests assert one of two things about a **continuously-open stream** — a connection that has no
single synchronous return you can assert on the next line:

- **A WebSocket** — a *bidirectional*, full-duplex channel (text **or** binary), no built-in reconnect. Used
  for chat, collaboration, live trading, anything interactive. You assert frames **in both directions** plus
  the open/close lifecycle.
- **An SSE stream** — a *server→client-only*, text/UTF-8 channel over **plain HTTP** (no upgrade handshake),
  with **auto-reconnect + `Last-Event-ID`** built into the protocol. Used for notification feeds, progress
  streams, server-pushed dashboards. You assert the sequence of `data:`/`event:`/`id:` events and that the
  client resumes from `Last-Event-ID`.

> **The discipline this skill encodes — four ideas, identical across all three stacks:**
>
> 1. **Real-time = await a message on a CONDITION, never a sleep.** A stream delivers "soon", on the server's
>    schedule. Drain incoming frames into a buffer (`Channel<T>`) and **await the expected frame / count with
>    a bounded `CancellationTokenSource` timeout** — never `await Task.Delay(2000)` standing in for "it
>    probably arrived". This is the *exact* eventual-consistency lineage of `qa-messaging-testing-service-bus-dotnet`
>    (a stream frame is a message that arrives later).
> 2. **Drain BEFORE you act.** Start the receive loop / arm the `WaitForWebSocketAsync` promise **before** the
>    action that triggers the first frames, or you race the server and lose them. (The same ordering rule as
>    `qa-network-monitoring-playwright-routes-dotnet`'s "register routes before navigation".)
> 3. **Assert the whole lifecycle, not just a payload.** The open handshake (HTTP **101 Switching Protocols**
>    for WS), the frames, **and** the clean close (`WebSocketCloseStatus.NormalClosure` = code **1000**, or the
>    contract's documented close code). "Server emits N then closes" = await `count == N`, *then* assert the
>    close — never assert count inside a sleep-bounded window.
> 4. **Two transports × two surfaces — choose deliberately.** **Transport:** WebSocket (bidirectional) vs SSE
>    (server→client, auto-reconnect). **Surface:** protocol-client (connect from test code, no browser —
>    backend/contract verification) vs browser (the app's UI opens the socket — Playwright `OBSERVE` or
>    `MOCK`). Pick the narrowest surface that proves the behaviour.

## Decision matrix — which transport, which surface, which tool

| Situation | Transport | Surface / Tool |
|-----------|-----------|----------------|
| Backend WS endpoint, no browser involved (chat, trading feed) | WebSocket | **protocol-client** — `ClientWebSocket` |
| The endpoint is a **SignalR hub** (groups, reconnect, RPC-style) | WebSocket | **protocol-client** — SignalR `HubConnection` (real client) |
| Server pushes a one-way feed (notifications, progress, live dashboard) | SSE | **protocol-client** — `SseParser` / streamed `HttpClient` |
| The app's **UI** opens a WS and you assert what crosses the wire | WebSocket | **browser** — Playwright `WaitForWebSocketAsync` + `FrameReceived` (OBSERVE) |
| The UI opens a WS and you want **deterministic** frames (no real server) | WebSocket | **browser** — Playwright `RouteWebSocketAsync` (MOCK) |
| The UI consumes an SSE feed and you want it deterministic | SSE | **browser** — `Page.RouteAsync` returning a chunked `text/event-stream` body |
| Async **queue/topic** (OrderPlaced lands on a queue, a consumer reacts) | — | **not this skill** → `qa-messaging-testing-service-bus-dotnet` (#28) etc. |
| A plain request/response **HTTP** dependency to fake | — | **not this skill** → `qa-api-mocking-wiremock-dotnet` (#22) / `qa-network-monitoring-playwright-routes-dotnet` (#8) |

**Rule of thumb:** *bidirectional, interactive?* → WebSocket. *Server-push-only feed?* → SSE (cheaper, plain
HTTP, free reconnect). *Testing the protocol contract?* → protocol-client. *Testing the UI's use of the
stream?* → browser (observe if the real server is fine, mock if you need determinism). *A discrete message on
a queue, not an open stream?* → that's `messaging-testing`, not this skill.

## Stack

- .NET 8, C# (nullable reference types on), NUnit 4.x — **async all the way** (`ConnectAsync`, `ReceiveAsync`,
  `SendAsync`, `CloseAsync`; never `.Result` / `.Wait()` / `.GetAwaiter().GetResult()`)
- `System.Net.WebSockets.ClientWebSocket` (BCL) — the raw protocol client
- `Microsoft.AspNetCore.SignalR.Client` (`HubConnection`) — only when the endpoint is a SignalR hub
- `System.Net.ServerSentEvents` `SseParser` (.NET 9+) for SSE; on .NET 8, a hand-rolled line parser over a
  streamed `HttpClient` response (shown below)
- `System.Threading.Channels` (`Channel<T>`) — the frame buffer the test awaits on; `CancellationTokenSource`
  (`CancelAfter`) is the **bounded condition-wait** primitive
- `Microsoft.AspNetCore.Mvc.Testing` `WebApplicationFactory` **on a real Kestrel port** for in-process WS/SSE
  integration tests (the in-memory `TestServer` historically can't do the WS upgrade — aspnetcore#31911)
- Browser surface: `Microsoft.Playwright` + `Microsoft.Playwright.NUnit` (≥ **1.48** for `RouteWebSocketAsync`),
  built on the `PageTest` base from `qa-ui-test-author-playwright-dotnet`
- The SUT's stream client is **constructor-injected** with its URL / an `HttpClient` — never a hard-coded URL
  read inside a `[Test]`

```
IntegrationTests/
├── Realtime/
│   ├── WebSocketProbe.cs        ← test-side WS client: connect, drain frames into a Channel, await on a condition
│   ├── SseProbe.cs              ← test-side SSE client: stream + parse events into a Channel
│   └── AwaitFrame.cs            ← the bounded condition-wait helpers (no Task.Delay as a wait)
├── Fixtures/
│   └── AppFixture.cs            ← WebApplicationFactory on a real Kestrel port (WS upgrade needs it)
├── ChatWebSocketTests.cs        ← protocol-client WS
├── NotificationsSseTests.cs     ← protocol-client SSE
└── Specs/
    └── LiveFeedBrowserTests.cs  ← Playwright observe + mock (browser surface)
```

## WebSocket vs SSE — when each, and what changes in the test

| | **WebSocket** | **SSE (Server-Sent Events)** |
|---|---|---|
| Direction | Bidirectional (client ↔ server) | Server → client only |
| Payload | Text **or** binary | Text/UTF-8 only (`data:` lines) |
| Transport | HTTP **upgrade** (101 Switching Protocols) | Plain HTTP streaming `text/event-stream` |
| Reconnect | **None built-in** — you implement/assert it | **Built-in** — auto-reconnect honoring `retry:` + `Last-Event-ID` |
| Browser API | `WebSocket` (Playwright can observe **and** mock) | `EventSource` (just HTTP — observe/mock via `Page.RouteAsync`) |
| Test focus | Full-duplex frames + open/close lifecycle | Event sequence + resume-from-`Last-Event-ID` |
| Pick it for | Chat, collaboration, interactive/trading | Notification feeds, progress, server-pushed dashboards |

## The bounded condition-wait — the heart of every real-time test

A frame arrives whenever the server sends it. The test must **await the condition** (a frame, or the Nth
frame) with a **timeout**, returning the instant it holds and *failing* if it never does. Drain frames into a
`Channel<T>` and read with a `CancellationTokenSource` deadline — this is the WS/SSE analogue of
`qa-messaging-testing-service-bus-dotnet`'s `ReceiveMessageAsync(maxWaitTime)` long-poll and `WaitFor.Async`.

```csharp
namespace IntegrationTests.Realtime;

/// <summary>
/// Bounded reads off a frame Channel. A timeout is a deterministic FAILURE ("no frame arrived in the window"),
/// not a silent pass. This is the only sanctioned wait in the skill — there is no bare Task.Delay-as-wait.
/// </summary>
public static class AwaitFrame
{
    /// <summary>Await the next frame, or fail if none arrives within <paramref name="timeout"/>.</summary>
    public static async Task<T> NextAsync<T>(ChannelReader<T> reader, TimeSpan timeout)
    {
        using var cts = new CancellationTokenSource(timeout);
        try
        {
            return await reader.ReadAsync(cts.Token);   // returns the instant a frame is queued
        }
        catch (OperationCanceledException)
        {
            throw new TimeoutException($"No frame arrived within {timeout}.");
        }
    }

    /// <summary>Collect exactly <paramref name="count"/> frames, or fail on timeout.</summary>
    public static async Task<IReadOnlyList<T>> TakeAsync<T>(ChannelReader<T> reader, int count, TimeSpan timeout)
    {
        using var cts = new CancellationTokenSource(timeout);
        var frames = new List<T>(count);
        try
        {
            while (frames.Count < count)
                frames.Add(await reader.ReadAsync(cts.Token));
            return frames;
        }
        catch (OperationCanceledException)
        {
            throw new TimeoutException($"Expected {count} frames, got {frames.Count} within {timeout}.");
        }
    }
}
```

> **No bare `Task.Delay`/`Thread.Sleep` anywhere as a wait.** The deadline lives *inside* `CancellationTokenSource`;
> the read returns immediately when a frame is queued. A fixed sleep races the server — it's slow when the
> frame is fast and flaky when the frame is slow.

## Protocol-client 1 — raw WebSocket (`ClientWebSocket`)

The test **is** a WebSocket client. The critical detail: **`ClientWebSocket` does NOT reassemble fragments** —
a logical message can span several frames, so loop on `ReceiveAsync` accumulating until `result.EndOfMessage`.
A background pump drains complete messages into a `Channel`; the test awaits the channel. **Start the pump
before sending**, so the server's reply can't arrive before you're listening.

```csharp
using System.Net.WebSockets;
using System.Text;
using System.Threading.Channels;

namespace IntegrationTests.Realtime;

public sealed class WebSocketProbe : IAsyncDisposable
{
    private readonly ClientWebSocket _socket = new();
    private readonly Channel<string> _frames = Channel.CreateUnbounded<string>();
    private Task? _pump;

    public ChannelReader<string> Frames => _frames.Reader;
    public WebSocketCloseStatus? CloseStatus => _socket.CloseStatus;          // assert the close code
    public string? CloseDescription => _socket.CloseStatusDescription;

    /// <summary>Connect (asserts the 101 upgrade implicitly — ConnectAsync throws otherwise) and start draining.</summary>
    public async Task ConnectAsync(Uri uri, Action<ClientWebSocketOptions>? configure = null, CancellationToken ct = default)
    {
        configure?.Invoke(_socket.Options);                                   // auth: subprotocol / headers go here
        await _socket.ConnectAsync(uri, ct);                                  // throws on a non-101 / handshake failure
        _pump = Task.Run(() => PumpAsync(CancellationToken.None));            // DRAIN before the caller sends
    }

    public Task SendAsync(string text, CancellationToken ct = default) =>
        _socket.SendAsync(Encoding.UTF8.GetBytes(text), WebSocketMessageType.Text, endOfMessage: true, ct);

    /// <summary>Reassemble fragmented frames into one logical message, then queue it.</summary>
    private async Task PumpAsync(CancellationToken ct)
    {
        var buffer = new byte[8 * 1024];
        var message = new MemoryStream();
        try
        {
            while (_socket.State == WebSocketState.Open)
            {
                var result = await _socket.ReceiveAsync(buffer, ct);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    // Echo the close handshake back so the close is clean on both ends.
                    await _socket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "ack", ct);
                    break;
                }
                message.Write(buffer, 0, result.Count);
                if (result.EndOfMessage)                                      // a logical message may span many frames
                {
                    _frames.Writer.TryWrite(Encoding.UTF8.GetString(message.ToArray()));
                    message.SetLength(0);
                }
            }
        }
        catch (OperationCanceledException) { /* teardown */ }
        finally { _frames.Writer.TryComplete(); }
    }

    public async ValueTask DisposeAsync()
    {
        if (_socket.State == WebSocketState.Open)
            await _socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "bye", CancellationToken.None);  // clean close, code 1000
        if (_pump is not null) await _pump;
        _socket.Dispose();
    }
}
```

```csharp
[TestFixture]
public class ChatWebSocketTests : AppFixture                  // AppFixture exposes BaseUri on a real Kestrel port
{
    [Test]
    public async Task Should_broadcast_a_message_to_a_connected_client()
    {
        await using var probe = new WebSocketProbe();
        await probe.ConnectAsync(new Uri($"{BaseWsUri}/ws/chat"));   // pump is now draining

        await probe.SendAsync("""{ "type": "say", "text": "hello" }""");

        // Await the broadcast on a condition — never a sleep before reading.
        var frame = await AwaitFrame.NextAsync(probe.Frames, TimeSpan.FromSeconds(5));

        Assert.That(frame, Does.Contain("\"text\":\"hello\""));     // one logical assertion: the broadcast fact
    }

    [Test]
    public async Task Should_emit_three_ticks_then_close_cleanly()
    {
        await using var probe = new WebSocketProbe();
        await probe.ConnectAsync(new Uri($"{BaseWsUri}/ws/ticker?count=3"));

        var ticks = await AwaitFrame.TakeAsync(probe.Frames, count: 3, TimeSpan.FromSeconds(5));

        Assert.That(ticks, Has.Count.EqualTo(3));                   // the N frames…
        // …then the close handshake. Disposing awaits the pump; the close status is observable after.
        await probe.DisposeAsync();
        Assert.That(probe.CloseStatus, Is.EqualTo(WebSocketCloseStatus.NormalClosure));   // …and the clean close
    }
}
```

## Protocol-client 2 — SignalR hub (`HubConnection`)

When the endpoint is a **SignalR hub**, use the **real client** — `HubConnection` reassembles messages,
handles the heartbeat, and (with `WithAutomaticReconnect`) reconnects, so you assert at the *hub* level. The
message-await primitive is a `TaskCompletionSource<T>` completed inside the `On<T>` handler and awaited with a
timeout — register the handler **before** the action that triggers the server-to-client call.

```csharp
[Test]
public async Task Should_receive_a_ReceiveMessage_When_a_peer_sends_to_the_group()
{
    await using var connection = new HubConnectionBuilder()
        .WithUrl($"{BaseUri}/hubs/chat")
        .WithAutomaticReconnect()                  // exercise reconnect behaviour
        .Build();

    var received = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
    connection.On<string, string>("ReceiveMessage", (user, text) => received.TrySetResult($"{user}:{text}"));  // arm BEFORE start

    await connection.StartAsync();                 // awaits the negotiate + connect; no sleep needed
    await connection.InvokeAsync("SendToGroup", "general", "hi");

    // Await the server→client push on a condition: the TCS, raced against a timeout.
    var message = await received.Task.WaitAsync(TimeSpan.FromSeconds(5));

    Assert.That(message, Is.EqualTo("alice:hi"));
}
```

> SignalR's first-class **reconnect** (`WithAutomaticReconnect`) and **keep-alive** (`KeepAliveInterval` /
> `ServerTimeout`) mean you assert *behaviour* (did it reconnect, did it survive a dropped ping) rather than
> hand-rolling the protocol. `connection.StartAsync()` *is* the condition-wait for "connected" — never sleep
> after it. `received.Task.WaitAsync(timeout)` fails deterministically if the push never comes.

## Protocol-client 3 — SSE (`SseParser` / streamed `HttpClient`)

SSE is **plain HTTP** — a `GET` whose response body streams `text/event-stream`. On **.NET 9+**, `SseParser`
parses it for you; on **.NET 8**, read the stream line-by-line (`data:` lines, blank line dispatches an
event). Either way, pump events into a `Channel` and await on a condition. **`HttpCompletionOption.ResponseHeadersRead`**
is essential — without it `HttpClient` buffers the whole (infinite) response and the test hangs.

```csharp
using System.Net.ServerSentEvents;   // .NET 9+

public sealed class SseProbe : IAsyncDisposable
{
    private readonly Channel<(string Type, string Data, string? Id)> _events =
        Channel.CreateUnbounded<(string, string, string?)>();
    private readonly HttpClient _http;
    private Task? _pump;

    public ChannelReader<(string Type, string Data, string? Id)> Events => _events.Reader;

    public SseProbe(HttpClient http) => _http = http;   // constructor-injected client

    public async Task SubscribeAsync(string url, CancellationToken ct = default)
    {
        // ResponseHeadersRead: stream the body, don't buffer the (open-ended) response.
        var response = await _http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, ct);
        response.EnsureSuccessStatusCode();
        Assert.That(response.Content.Headers.ContentType?.MediaType, Is.EqualTo("text/event-stream"));

        var stream = await response.Content.ReadAsStreamAsync(ct);
        _pump = Task.Run(async () =>
        {
            await foreach (SseItem<string> item in SseParser.Create(stream).EnumerateAsync(ct))   // .NET 9+
                _events.Writer.TryWrite((item.EventType, item.Data, item.ReconnectionId));
            _events.Writer.TryComplete();
        }, ct);
    }

    public async ValueTask DisposeAsync()
    {
        _http.CancelPendingRequests();        // ends the stream read
        if (_pump is not null) { try { await _pump; } catch (OperationCanceledException) { } }
    }
}
```

```csharp
[Test]
public async Task Should_stream_three_progress_events_then_a_done_event()
{
    var http = AppFixture.CreateClient();      // points at the real Kestrel port
    await using var probe = new SseProbe(http);
    await probe.SubscribeAsync("/sse/progress?job=42");

    var events = await AwaitFrame.TakeAsync(probe.Events, count: 4, TimeSpan.FromSeconds(5));

    Assert.That(events.Select(e => e.Type),
        Is.EqualTo(new[] { "progress", "progress", "progress", "done" }));   // the event sequence
}
```

> **.NET 8 fallback (no `SseParser`):** read with a `StreamReader`, accumulate `data:` lines, and dispatch the
> accumulated event on a **blank line**; track `id:` for `Last-Event-ID` and `event:` for the type. Keep that
> parsing inside the probe so tests stay clean.

## Browser surface 1 — OBSERVE WebSocket frames (Playwright)

When the **app's UI** opens the socket and the real backend is fine, **observe** the frames Playwright sees.
Arm `WaitForWebSocketAsync` (or subscribe `Page.WebSocket`) **before** the action that opens it. Layer this on
the `PageTest` base from `qa-ui-test-author-playwright-dotnet` and wrap it in an intent-named helper, never raw
event wiring in a `[Test]`.

```csharp
[Test]
public async Task Should_push_a_price_update_over_the_dashboard_socket()
{
    // Arm the WS wait BEFORE navigating — the socket opens on load.
    var wsTask = Page.WaitForWebSocketAsync();
    await Page.GotoAsync("/dashboard");

    var ws = await wsTask;
    Assert.That(ws.Url, Does.Contain("/ws/prices"));

    // Await a frame on a condition (FrameReceived predicate), not a sleep.
    var frame = await ws.WaitForEventAsync("framereceived",
        new() { Predicate = f => f.Text.Contains("\"symbol\":\"ACME\"") });

    Assert.That(frame.Text, Does.Contain("\"price\""));
    await Expect(Page.GetByTestId("acme-price")).Not.ToBeEmptyAsync();   // the user-visible effect of the frame
}
```

`IWebSocket` exposes `FrameSent` / `FrameReceived` events (`IWebSocketFrame.Text` / `.Binary`), `Close`, and
`IsClosed()` — enough to assert direction, payload, and lifecycle of what the page actually sends/receives.

## Browser surface 2 — MOCK WebSocket frames (Playwright `RouteWebSocketAsync`, ≥ 1.48)

When you need **deterministic** frames (the real server is flaky, slow, or you're exercising an edge case),
**mock** the socket with `Page.RouteWebSocketAsync` (added in Playwright **1.48**). By default the routed
socket does **not** connect to the real server — you script both directions. Register it **before** the page
opens the socket.

```csharp
[Test]
public async Task Should_render_the_alert_banner_When_the_socket_pushes_an_outage()
{
    // Mock the socket: when the page sends "subscribe", push a canned outage frame back.
    await Page.RouteWebSocketAsync("**/ws/alerts", ws =>
    {
        ws.OnMessage(message =>
        {
            if (message.Contains("subscribe"))
                ws.Send("""{ "type": "outage", "region": "EU" }""");   // server→page, fully deterministic
        });
    });

    await Page.GotoAsync("/status");

    await Expect(Page.GetByRole(AriaRole.Alert)).ToContainTextAsync("EU outage");
}
```

> **Pass-through / intercept-and-modify:** call `ws.ConnectToServer()` inside the handler to get the
> *server-side* route — forward most frames to the real backend and rewrite only the one under test. **Caveat
> (Playwright #33370):** driving server-initiated frames *on demand* from the route (outside a message
> handler) has had quirks — for "server spontaneously emits" scenarios, an observe test against a real test
> server is more reliable than a mock. **SSE has no dedicated Playwright API** — `EventSource` is just a
> streaming HTTP GET, so mock it with `Page.RouteAsync` returning a chunked `text/event-stream` body (or
> observe it via `Page.Response`); a protocol-client SSE test is usually cleaner for asserting the server's
> event sequence.

## Disciplines & gotchas (apply to every real-time test)

- **Await a condition, never a sleep** — the `AwaitFrame` channel reads / `TaskCompletionSource.WaitAsync` /
  `WaitForEventAsync(predicate)`. No `Task.Delay`-as-wait, no `Thread.Sleep`, no `Page.WaitForTimeoutAsync`.
- **Lifecycle:** `ConnectAsync` throwing *is* the failed-handshake assertion (a non-101 upgrade throws); always
  `CloseAsync(NormalClosure, …)` in teardown and assert the close code where the contract specifies one. Build
  the drain channel **before** connecting to avoid a race on the first frames.
- **Server emits N then closes:** `AwaitFrame.TakeAsync(reader, N, timeout)` then assert the close event —
  never assert the count inside a sleep-bounded window.
- **Reconnection / backoff:** drop the server (or `ws.Close()` the route) and assert the client reconnects
  with increasing intervals (SignalR `WithAutomaticReconnect`; SSE reconnects natively, honoring `retry:` and
  resending `Last-Event-ID` so the server resumes — assert missed events are replayed from that id).
- **Fragmentation / backpressure:** raw `ClientWebSocket` delivers *frames*, not messages — the `EndOfMessage`
  reassembly loop above is mandatory; send a large message that spans multiple frames and assert it
  reassembles. SignalR reassembles for you.
- **Auth on the socket** — cover all three patterns the contract might use: token in the **query string**
  (`?access_token=…`, what SignalR uses because browsers can't set WS headers), token via **subprotocol**
  (`_socket.Options.AddSubProtocol(token)` → `Sec-WebSocket-Protocol`), or token in the **first frame** after
  connect. Read the token from **env, lazily, never logged** (cross-link `qa-auth0-test-tokens-dotnet`). For
  SSE, a server-side `HttpClient` can set `Authorization`, but a *browser* `EventSource` **cannot set headers**
  → query-param or cookie auth.
- **Heartbeat (ping/pong):** assert the server's keep-alive and that a missed pong triggers reconnect
  (SignalR `KeepAliveInterval` / `ServerTimeout`); the raw protocol's control frames are handled below your
  pump, so assert at the application-heartbeat level if the app sends one.
- **WS upgrade in integration tests** needs a **real Kestrel port** — the in-memory `TestServer` handler can't
  perform the upgrade (aspnetcore#31911). Boot `WebApplicationFactory` and host on a real port.

## Anti-patterns

- **`await Task.Delay(2000)` then read one frame.** Races the server; slow when fast, flaky when slow. *Fix:*
  `AwaitFrame.NextAsync(reader, timeout)` — returns the instant the frame queues, fails if it never does.
- **Reading `ReceiveAsync` once and assuming you got the whole message.** A logical message can span frames;
  you'll assert on a truncated payload. *Fix:* loop until `result.EndOfMessage`.
- **Buffering the SSE response** (`GetAsync` without `ResponseHeadersRead`). The test hangs waiting for an
  open-ended stream to "finish". *Fix:* `HttpCompletionOption.ResponseHeadersRead` + stream the body.
- **Subscribing/arming the listener *after* the action.** The first frames fire before you're listening and
  you miss them. *Fix:* start the pump / arm `WaitForWebSocketAsync` / register `On<T>` **before** the trigger.
- **Never closing the socket** (or asserting only the payload). The connection leaks across tests and you
  never catch a bad close code. *Fix:* `CloseAsync(NormalClosure, …)` in teardown; assert `CloseStatus`.
- **`Thread.Sleep` to "let it reconnect".** *Fix:* assert the reconnected state on a condition (SignalR
  exposes `State`; await the next frame after the drop).
- **Asserting on `ClientWebSocket` for a SignalR endpoint.** You'd re-implement negotiate/handshake/framing.
  *Fix:* use the real `HubConnection`.
- **Reaching for this skill for a queue/topic.** A discrete message landing on Service Bus/SQS/Kafka is *not*
  an open stream. *Fix:* `qa-messaging-testing-service-bus-dotnet` (#28) and its siblings.
- **Token hard-coded or logged.** *Fix:* env, read lazily, never logged (`qa-auth0-test-tokens-dotnet`).

## Examples

**End-to-end: a WebSocket request/response round-trip with a clean close, asserted lifecycle-first.**

```csharp
[TestFixture]
public class EchoSocketTests : AppFixture
{
    [Test]
    public async Task Should_echo_a_message_and_close_with_code_1000()
    {
        await using var probe = new WebSocketProbe();
        await probe.ConnectAsync(new Uri($"{BaseWsUri}/ws/echo"));   // 101 upgrade or ConnectAsync throws

        await probe.SendAsync("ping");
        var echoed = await AwaitFrame.NextAsync(probe.Frames, TimeSpan.FromSeconds(5));
        Assert.That(echoed, Is.EqualTo("ping"));

        await probe.DisposeAsync();                                  // clean close handshake
        Assert.That(probe.CloseStatus, Is.EqualTo(WebSocketCloseStatus.NormalClosure));  // code 1000
    }
}
```

**Auth via subprotocol (token on the handshake, read from env, never logged):**

```csharp
await probe.ConnectAsync(
    new Uri($"{BaseWsUri}/ws/secure"),
    configure: opts => opts.AddSubProtocol(TestTokens.AccessToken()));   // env-sourced; see qa-auth0-test-tokens-dotnet
```

**Composing with a test-data builder for the frame payload (4+ fields → builder, per the global rules):**

```csharp
var payload = ChatMessages.Standard().WithText("hello").WithRoom("general").Build();   // qa-test-data-builder-dotnet
await probe.SendAsync(JsonSerializer.Serialize(payload));
```

## Rules (hard constraints)

- **Real-time = await a condition, never a sleep.** Drain into a `Channel<T>`, await with a
  `CancellationTokenSource` deadline (`AwaitFrame`) / `TaskCompletionSource.WaitAsync(timeout)` /
  Playwright `WaitForEventAsync(predicate)`. **No `Task.Delay`/`Thread.Sleep`/`WaitForTimeoutAsync` as a wait.**
- **Drain before you act** — start the receive pump / arm `WaitForWebSocketAsync` / register `On<T>` **before**
  the trigger, or you race the first frames.
- **Assert the whole lifecycle** — the 101 upgrade (`ConnectAsync` throwing = the negative assertion), the
  frames, **and** the clean close (`WebSocketCloseStatus.NormalClosure` / the contract's close code). "N then
  close" = take N, *then* assert close.
- **Reassemble fragments** on raw `ClientWebSocket` (`EndOfMessage` loop); use `HubConnection` for SignalR
  (don't hand-roll the protocol); `HttpCompletionOption.ResponseHeadersRead` for SSE (never buffer the stream).
- **Pick the transport and surface deliberately** — WS (bidirectional) vs SSE (server-push, free reconnect);
  protocol-client (contract) vs browser (observe if the real server suffices, `RouteWebSocketAsync` to mock).
- **Auth tokens from env, read lazily, never logged** (query / subprotocol / first-frame; browser `EventSource`
  can't set headers — query/cookie). WS upgrade integration tests need a **real Kestrel port**.
- **Async all the way** (`await` every call; `await using` the probes; never `.Result`/`.Wait()`); the SUT's
  stream client is **constructor-injected** with its URL/`HttpClient`; test names `Should_X_When_Y`; one
  logical assertion per test; builders for 4+-field payloads; structured logging; no secrets in code.

## Cross-references

- `qa-websocket-sse-testing-java` — same skill, Java 21 / TestNG: **OkHttp `WebSocket`** (`newWebSocket` +
  `WebSocketListener` draining into a `BlockingQueue`) / Java-WebSocket, **Awaitility** (`await().atMost().until(...)`)
  as the condition-wait, **OkHttp-SSE** (`EventSources` + `EventSourceListener`) or Spring `WebClient`
  `Flux<ServerSentEvent>` + `StepVerifier` for SSE, Playwright-Java (`page.waitForWebSocket`,
  `ws.onFrameReceived`, `page.routeWebSocket`). Structure ported, not code.
- `qa-websocket-sse-testing-typescript` — same skill, Node 20 + TS: the **`ws`** lib / native global
  `WebSocket` (the **Node-22** boundary — polyfill via `undici` on Node 20), a promise-with-timeout +
  Vitest **`vi.waitFor`** as the condition-wait, native `EventSource` / the **`eventsource`** package for SSE,
  Playwright-TS (`page.waitForEvent('websocket')`, `ws.on('framereceived')`, `page.routeWebSocket`).
- `qa-messaging-testing-service-bus-dotnet` (#28) — the **eventual-consistency lineage** this skill leans on:
  a stream frame is a message that arrives later. The **boundary**: messaging = discrete messages on a
  queue/topic with a consumer; this skill = an open, continuous WS/SSE stream. Same condition-wait discipline,
  different shape. (Plus `-sqs` #29 / `-kafka` #30 / `-rabbitmq` #31.)
- `qa-network-monitoring-playwright-routes-dotnet` (#8) — the **HTTP** request/mock counterpart and the
  source of the "register before the action" ordering rule; use it for plain request/response, this skill for
  the open socket. (SSE-in-the-browser mocking reuses its `Page.RouteAsync`.)
- `qa-api-mocking-wiremock-dotnet` (#22) — fake a *synchronous* HTTP dependency; not a stream.
- `qa-ui-test-author-playwright-dotnet` — the `PageTest` base / page objects the **browser-surface** tests
  layer on; the no-`WaitForTimeoutAsync` discipline originates there.
- `qa-auth0-test-tokens-dotnet` (#16) — tokens for an authenticated socket (query / subprotocol / first-frame),
  read from env, never logged.
- `qa-test-environments-dotnet` (#14) — booting the SUT (`WebApplicationFactory` on a real Kestrel port, or a
  containerised stream server) with the readiness-wait discipline. `qa-allure-reporting-dotnet` — attach the
  captured frames / event sequence to the result. `qa-test-data-builder-dotnet` — frame payloads with 4+ fields.
