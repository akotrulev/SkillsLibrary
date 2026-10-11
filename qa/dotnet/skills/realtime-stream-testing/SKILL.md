---
name: realtime-stream-testing
description: Use when testing WebSocket or SSE streams in .NET 10 (8-9) / NUnit — protocol clients (`ClientWebSocket`, SignalR `HubConnection`, SSE over `HttpClient`) draining frames into a channel and asserting on conditions (never sleeps), plus Playwright .NET for in-browser frames. Triggers "test our WebSocket endpoint", "assert the SSE stream emits X", "SignalR hub test". Not for request/response HTTP (`api-test-author/writer`).
---

# WebSocket & SSE Testing (.NET 10 / NUnit) — **canonical stack**

The **canonical** stack of the `realtime-stream-testing` family: .NET has the richest first-party real-time
story — `ClientWebSocket`, SignalR's `HubConnection`, `SseParser`. The siblings port the disciplines, not the
code; the Playwright browser surface is near-identical in all three. This skill owns **WebSocket
mocking and browser SSE**; plain HTTP mocking is `qa/dotnet/skills/network-mocking`. A real-time test
asserts on a **continuously-open stream** — a connection with no single synchronous return to assert on the
next line.

> **The discipline this skill encodes — four ideas, identical across all three stacks:**
>
> 1. **Real-time = await a message on a CONDITION, never a sleep.** Drain frames into a buffer (`Channel<T>`)
>    or complete a `TaskCompletionSource` from the frame event, and **await it with a bounded timeout** —
>    never `Task.Delay(2000)` standing in for "it probably arrived". The eventual-consistency lineage of
>    `qa-dotnet:messaging-testing`.
> 2. **Drain BEFORE you act.** Start the receive loop / subscribe the frame event **before** the action that
>    triggers the first frames, or you race the server and lose them.
> 3. **Assert the whole lifecycle, not just a payload.** The open handshake (HTTP **101** for WS), the frames,
>    **and** the clean close (`WebSocketCloseStatus.NormalClosure` = **1000**, or the contract's code). "Emits
>    N then closes" = await `count == N`, *then* assert the close.
> 4. **Two transports × two surfaces — choose deliberately.** WebSocket vs SSE; **protocol-client** (connect
>    from test code — backend/contract verification) vs **browser** (the app's UI opens the stream —
>    Playwright OBSERVE or MOCK). Pick the narrowest surface that proves the behaviour.

## Decision matrix — which transport, which surface, which tool

| Situation | Transport | Surface / Tool |
|-----------|-----------|----------------|
| Backend WS endpoint, no browser involved | WebSocket | **protocol-client** — `ClientWebSocket` |
| The endpoint is a **SignalR hub** | WebSocket | **protocol-client** — SignalR `HubConnection` |
| Server pushes a one-way feed (notifications, progress) | SSE | **protocol-client** — `SseParser` over a streamed `HttpClient` |
| The app's **UI** opens a WS; assert what crosses the wire | WebSocket | **browser** — `Page.WebSocket` + `FrameReceived` + `TaskCompletionSource` (OBSERVE) |
| The UI opens a WS and you want **deterministic** frames | WebSocket | **browser** — `Page.RouteWebSocketAsync` (MOCK) |
| The UI renders an SSE feed and you want it deterministic | SSE | **browser** — a fixed event set: a `Times = 1` route over a route answering `204` |
| SSE timing, reconnect or `Last-Event-ID` resume in the browser | SSE | **browser** against a **real SSE test server** — a route cannot stream |
| Async **queue/topic** (a message lands, a consumer reacts) | — | **not this skill** → `qa-dotnet:messaging-testing` |

## Stack

- .NET 10 (8/9 supported — match the TFM), C# with nullable on, NUnit 4 — **async all the way**
- `System.Net.WebSockets.ClientWebSocket` — the raw protocol client
- `Microsoft.AspNetCore.SignalR.Client` (`HubConnection`) — only when the endpoint is a SignalR hub
- `System.Net.ServerSentEvents` `SseParser` (.NET 9+; `SseItem<T>.EventId` from .NET 10); on .NET 8 a line
  parser over the streamed response
- `System.Threading.Channels` (`Channel<T>`) — the frame buffer; `CancellationTokenSource(timeout)` and
  `Task.WaitAsync(timeout)` — the bounded condition-waits
- `WebApplicationFactory` **on a real Kestrel port** for in-process WS/SSE integration tests (the in-memory
  `TestServer` cannot do the WS upgrade — aspnetcore#31911)
- Browser surface: **Microsoft.Playwright.NUnit** at the pins in the **Versions** table of
  `qa/dotnet/skills/ui-test-author/playwright/SKILL.md` (this skill pins nothing; `RouteWebSocketAsync` needs
  ≥ 1.48). Every browser fixture **derives from that skill's `BaseTest`**; tests reach the page through page
  objects and the `SocketWatch` / `MockStreams` helpers, never raw `Page` calls.
- The SUT's stream client is **constructor-injected** with its URL / `HttpClient`

## WebSocket vs SSE — what changes in the test

| | **WebSocket** | **SSE** |
|---|---|---|
| Shape | Bidirectional, text or binary, HTTP **upgrade** (101) | Server → client, UTF-8 `data:` lines over plain HTTP |
| Reconnect | **None built-in** — you implement/assert it | **Built-in** — `retry:`, `Last-Event-ID`; a `204` stops it |
| Browser | Playwright observes **and** mocks it | `EventSource`; a route answers it once |

## The bounded condition-wait — the heart of every real-time test

A frame arrives whenever the server sends it. The test **awaits the condition** with a **timeout**, returning
the instant it holds and *failing* when it never does — a failure that names what was missing, never a silent
pass. Two primitives, and nothing else:

| Surface | Primitive | Fails with |
|---|---|---|
| Protocol client | Frames drained into a `Channel<T>`; `AwaitFrame.NextAsync(reader, timeout)` / `TakeAsync(reader, n, timeout)` read under a `CancellationTokenSource` deadline | `TimeoutException` listing the frames that did arrive |
| Browser (Playwright) and SignalR | A `TaskCompletionSource` completed from the frame event or `On<T>` handler, awaited with `.WaitAsync(timeout)` | `TimeoutException` at the await |

## Deep-dive reference

[`references/details.md`](references/details.md) holds **0. `AwaitFrame`** (the channel reads, the one helper
with a `catch`) and the protocol-client surfaces — **1. raw WebSocket (`WebSocketProbe`)**, **2. SignalR hub
(`HubConnection`)**, **3. SSE (`SseProbe`)** — plus **Disciplines & gotchas** (auth on the socket,
reconnection, heartbeat, fragmentation, the Kestrel port), the project layout and **Examples**. Read it when
the task touches them.

## Browser surface 1 — OBSERVE WebSocket frames (Playwright)

When the **app's UI** opens the socket and the real backend is fine, observe the frames the page receives.
`IWebSocket` has events (`FrameReceived`, `FrameSent`, `Close`, `SocketError`) and two properties, `IsClosed`
and `Url` — **there is no `WaitForEventAsync` on it**. So `SocketWatch` subscribes `Page.WebSocket` **before**
the action, hooks each matching socket's `FrameReceived`, and completes a `TaskCompletionSource` when a frame
matches; the test awaits it with `WaitAsync(timeout)`.

```csharp
using System.Text.RegularExpressions;
using Microsoft.Playwright;

namespace Example.UiTests.Support;

public sealed class SocketWatch(IPage page)
{
    public Task<IWebSocketFrame> FrameAsync(Regex url, Func<string, bool> matches)
    {
        var frame = new TaskCompletionSource<IWebSocketFrame>(TaskCreationOptions.RunContinuationsAsynchronously);
        page.WebSocket += (_, socket) =>
        {
            if (url.IsMatch(socket.Url))
            {
                socket.FrameReceived += (_, received) =>
                {
                    if (received.Text is { } text && matches(text))
                    {
                        frame.TrySetResult(received);
                    }
                };
            }
        };
        return frame.Task;
    }

    public Task<IWebSocket> ClosedAsync(Regex url)
    {
        var closed = new TaskCompletionSource<IWebSocket>(TaskCreationOptions.RunContinuationsAsynchronously);
        page.WebSocket += (_, socket) =>
        {
            if (url.IsMatch(socket.Url))
            {
                socket.Close += (_, closedSocket) => closed.TrySetResult(closedSocket);
            }
        };
        return closed.Task;
    }
}
```

```csharp
using System.Text.RegularExpressions;
using Example.UiTests.Pages;
using Example.UiTests.Support;
using NUnit.Framework;

namespace Example.UiTests.Tests;

public class LiveFeedBrowserTests : BaseTest
{
    private static readonly Regex PricesSocket = new("/ws/prices$");
    private static readonly TimeSpan FrameTimeout = TimeSpan.FromSeconds(10);

    private SocketWatch _sockets = null!;
    private MockStreams _streams = null!;
    private DashboardPage _dashboard = null!;
    private StatusPage _status = null!;
    private NotificationsPage _notifications = null!;

    [SetUp]
    public void CreateHelpers()
    {
        _sockets = new SocketWatch(Page);
        _streams = new MockStreams(Page);
        _dashboard = new DashboardPage(Page);
        _status = new StatusPage(Page);
        _notifications = new NotificationsPage(Page);
    }

    [Test]
    public async Task Should_ShowTheAcmePrice_When_ThePriceSocketPushesAnAcmeFrame()
    {
        var acmeFrame = _sockets.FrameAsync(PricesSocket, text => text.Contains("\"symbol\":\"ACME\""));

        await _dashboard.OpenAsync();

        var frame = await acmeFrame.WaitAsync(FrameTimeout);
        await Expect(_dashboard.AcmePrice, $"ACME price after frame {frame.Text}").Not.ToBeEmptyAsync();
    }

    [Test]
    public async Task Should_CloseThePriceSocket_When_TheUserSignsOut()
    {
        var closed = _sockets.ClosedAsync(PricesSocket);
        await _dashboard.OpenAsync();

        await _dashboard.SignOutAsync();

        var socket = await closed.WaitAsync(FrameTimeout);
        Assert.That(socket.IsClosed, Is.True, $"{socket.Url} after sign-out");
    }
}
```

- `FrameAsync` and `ClosedAsync` are called **before** the action; the returned task is awaited after it.
- The frame's payload is `IWebSocketFrame.Text` (or `.Binary`), never the frame itself as a string;
  `IsClosed` is a property, not a method.
- A missed frame fails at the `WaitAsync` line; `BaseTest` keeps the trace.

## Browser surface 2 — MOCK WebSocket frames (`RouteWebSocketAsync`)

When you need **deterministic** frames, mock the socket with `Page.RouteWebSocketAsync` (≥ 1.48). By default
the routed socket does **not** connect to the server — you script both directions. Register it **before** the
page opens the socket.

```csharp
using System.Text.Json;
using Microsoft.Playwright;

namespace Example.UiTests.Support;

public sealed class MockStreams(IPage page)
{
    public Task PushOutageOnSubscribeAsync(string region) =>
        page.RouteWebSocketAsync("**/ws/alerts", socket =>
            socket.OnMessage(frame =>
            {
                if (frame.Text == "subscribe")
                {
                    socket.Send(JsonSerializer.Serialize(new { type = "outage", region }));
                }
            }));

    public async Task ServeNotificationsAsync(params string[] messages)
    {
        await page.RouteAsync("**/api/notifications/stream", route => route.FulfillAsync(new() { Status = 204 }));
        await page.RouteAsync("**/api/notifications/stream", route => route.FulfillAsync(new()
        {
            Status = 200,
            ContentType = "text/event-stream",
            Body = string.Concat(messages.Select((message, index) => $"id: {index + 1}\ndata: {message}\n\n")),
        }), new() { Times = 1 });
    }
}
```

```csharp
[Test]
public async Task Should_ShowTheOutageBanner_When_TheAlertSocketPushesAnOutage()
{
    await _streams.PushOutageOnSubscribeAsync("EU");

    await _status.OpenAsync();

    await Expect(_status.AlertBanner).ToContainTextAsync("EU outage");
}
```

- `OnMessage` receives an `IWebSocketFrame`; compare `frame.Text`, never the frame.
- **Pass-through / rewrite:** `socket.ConnectToServer()` inside the handler returns the server side — forward
  most frames, rewrite the one under test. For "the server spontaneously emits" scenarios, an OBSERVE test
  against a real test server is more reliable than driving the route on demand (Playwright #33370).

## Browser surface 3 — SSE in the browser: a fixed event set, then `204`

`EventSource` is a plain HTTP `GET`. A route **cannot stream**: `FulfillAsync` sends one body and ends the
response, so the page reads every event at once — and then `EventSource` **reconnects and fetches them again**.
A "chunked `text/event-stream`" route body is that defect. `MockStreams.ServeNotificationsAsync` serves the
events once (`Times = 1`) over a route answering `204`, which the SSE spec defines as "stop reconnecting";
routes match newest first, so the `Times = 1` route answers the first request and the `204` every one after.

```csharp
[Test]
public async Task Should_ListEveryPushedNotification_When_TheFeedDeliversThem()
{
    await _streams.ServeNotificationsAsync("Build 42 passed", "Deploy started");

    await _notifications.OpenAsync();

    await Expect(_notifications.Items).ToHaveTextAsync(["Build 42 passed", "Deploy started"]);
}
```

- This proves **rendering** only. Timing between events, the reconnect after a drop, `retry:` and the
  `Last-Event-ID` resume need a **real SSE test server** — or the protocol-client `SseProbe`
  (`references/details.md` §3) for the server's own sequence.
- That every browser stops on a routed `204` is the SSE spec's rule, not yet run here; if a browser keeps
  reconnecting, the duplicated list shows it at once.

## Anti-patterns

- **`await Task.Delay(2000)` then read one frame.** Races the server. *Fix:* `AwaitFrame.NextAsync` /
  `TaskCompletionSource` + `WaitAsync(timeout)`.
- **`ws.WaitForEventAsync(...)`, `ws.IsClosed()`, `OnMessage(message => message.Contains(...))`.** None compiles
  against `IWebSocket` / `IWebSocketRoute`. *Fix:* `FrameReceived` + a `TaskCompletionSource`; `IsClosed` is a
  property; `frame.Text`.
- **A "chunked" `text/event-stream` route body for browser SSE.** It arrives at once and replays on reconnect.
  *Fix:* the fixed event set + `204`; a real server for timing.
- **Subscribing after the action.** The first frames fire before you listen. *Fix:* arm first, act, then await.
- Protocol-client mistakes — one `ReceiveAsync` per message, a buffered SSE response, a socket never closed,
  `ClientWebSocket` against a SignalR hub — are listed in `references/details.md`.

## Rules (hard constraints)

- **Real-time = await a condition, never a sleep.** `AwaitFrame` channel reads,
  `TaskCompletionSource.WaitAsync(timeout)`; no `Task.Delay`/`Thread.Sleep`/`WaitForTimeoutAsync` as a wait.
- **Drain before you act** — start the pump / subscribe `Page.WebSocket` / register `On<T>` / route the socket
  **before** the trigger.
- **Assert the whole lifecycle** — the 101 upgrade (`ConnectAsync` throwing is the negative assertion), the
  frames, **and** the clean close. "N then close" = take N, *then* assert the close.
- **Browser SSE is a fixed event set + `204`**; timing, reconnect and `Last-Event-ID` go to a real server.
- **Browser fixtures derive from `BaseTest`** and reach the page through page objects and helpers built in
  `[SetUp]`; no `Playwright.CreateAsync()`, no `try`/`catch`/`finally` in a test.
- **Auth tokens from env, never logged**; async all the way; `Should_X_When_Y` names; PascalCase test ids.

## Cross-references

- `qa-java:realtime-stream-testing` · `qa-typescript:realtime-stream-testing` — the sibling stacks; same four
  ideas, their own protocol clients and await primitives.
- `qa-dotnet:messaging-testing` — discrete messages on a queue, not an open stream.
- `qa-dotnet:network-mocking` — plain HTTP mocking and the "register before the action" rule.
- `qa-dotnet:ui-tests-playwright` — `BaseTest` and page objects the browser surface builds on.
- `qa-dotnet:test-login-tokens` — tokens for an authenticated socket, read from env, never logged.
