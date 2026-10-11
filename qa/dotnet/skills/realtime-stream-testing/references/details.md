# Deep-dive details — `qa-dotnet:realtime-stream-testing`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Layout

```
IntegrationTests/                       UiTests/
├── Realtime/                           ├── Support/SocketWatch.cs   (OBSERVE)
│   ├── AwaitFrame.cs                   ├── Support/MockStreams.cs   (MOCK: WebSocket + the SSE event set)
│   ├── WebSocketProbe.cs               ├── Pages/DashboardPage.cs, StatusPage.cs, NotificationsPage.cs
│   └── SseProbe.cs                     └── Tests/LiveFeedBrowserTests.cs
├── Fixtures/AppFixture.cs
├── ChatWebSocketTests.cs
└── NotificationsSseTests.cs
```

`AppFixture` hosts the app with `WebApplicationFactory` on a **real Kestrel port** and exposes `BaseUri`,
`BaseWsUri` and `CreateClient()`; the in-memory `TestServer` cannot perform the WebSocket upgrade
(aspnetcore#31911). The `UiTests/` side is the Playwright project from `qa/dotnet/skills/ui-test-author/playwright`.

## 0. `AwaitFrame` — bounded reads off a frame channel

```csharp
using System.Threading.Channels;

namespace IntegrationTests.Realtime;

public static class AwaitFrame
{
    public static async Task<T> NextAsync<T>(ChannelReader<T> reader, TimeSpan timeout)
    {
        using var deadline = new CancellationTokenSource(timeout);
        try
        {
            return await reader.ReadAsync(deadline.Token);
        }
        catch (OperationCanceledException exception) when (deadline.IsCancellationRequested)
        {
            throw new TimeoutException($"No frame arrived within {timeout}.", exception);
        }
    }

    public static async Task<IReadOnlyList<T>> TakeAsync<T>(ChannelReader<T> reader, int count, TimeSpan timeout)
    {
        using var deadline = new CancellationTokenSource(timeout);
        var frames = new List<T>(count);
        try
        {
            while (frames.Count < count)
            {
                frames.Add(await reader.ReadAsync(deadline.Token));
            }
            return frames;
        }
        catch (OperationCanceledException exception) when (deadline.IsCancellationRequested)
        {
            throw new TimeoutException(
                $"Expected {count} frames, got {frames.Count} within {timeout}: {string.Join(" | ", frames)}", exception);
        }
    }
}
```

- The deadline lives **inside** the `CancellationTokenSource`; the read returns the moment a frame is queued.
- This helper is the one place a `catch` sits in the skill: it turns the deadline into a `TimeoutException`
  carrying what did arrive. The filter catches only the deadline's own cancellation; a channel completed with
  an error throws `ChannelClosedException`, which passes through with the probe's failure inside it.

## 1. Protocol client — raw WebSocket (`ClientWebSocket`)

The test **is** a WebSocket client. `ClientWebSocket` does **not** reassemble fragments — a logical message
can span several frames — so the pump loops on `ReceiveAsync` until `EndOfMessage`. The pump starts inside
`ConnectAsync`, before the caller sends anything, so the server's reply cannot arrive unheard.

```csharp
using System.Net.WebSockets;
using System.Text;
using System.Threading.Channels;

namespace IntegrationTests.Realtime;

public sealed class WebSocketProbe : IAsyncDisposable
{
    private readonly ClientWebSocket _socket = new();
    private readonly Channel<string> _frames = Channel.CreateUnbounded<string>();
    private Task _pump = Task.CompletedTask;

    public ChannelReader<string> Frames => _frames.Reader;

    public WebSocketCloseStatus? CloseStatus => _socket.CloseStatus;

    public async Task ConnectAsync(Uri uri, Action<ClientWebSocketOptions>? configure = null)
    {
        configure?.Invoke(_socket.Options);
        await _socket.ConnectAsync(uri, CancellationToken.None);
        _pump = PumpAsync().ContinueWith(
            pump => _frames.Writer.TryComplete(pump.Exception?.GetBaseException()), TaskScheduler.Default);
    }

    public Task SendAsync(string text) =>
        _socket.SendAsync(Encoding.UTF8.GetBytes(text), WebSocketMessageType.Text, endOfMessage: true, CancellationToken.None);

    public async Task CloseAsync()
    {
        if (_socket.State == WebSocketState.Open)
        {
            await _socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "done", CancellationToken.None);
        }
        await _pump;
    }

    public async ValueTask DisposeAsync()
    {
        await CloseAsync();
        _socket.Dispose();
    }

    private async Task PumpAsync()
    {
        var buffer = new byte[8 * 1024];
        using var message = new MemoryStream();
        while (_socket.State == WebSocketState.Open)
        {
            var result = await _socket.ReceiveAsync(buffer, CancellationToken.None);
            if (result.MessageType == WebSocketMessageType.Close)
            {
                await AcknowledgeServerCloseAsync();
                return;
            }
            message.Write(buffer, 0, result.Count);
            if (result.EndOfMessage)
            {
                _frames.Writer.TryWrite(Encoding.UTF8.GetString(message.ToArray()));
                message.SetLength(0);
            }
        }
    }

    private async Task AcknowledgeServerCloseAsync()
    {
        if (_socket.State == WebSocketState.CloseReceived)
        {
            await _socket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "ack", CancellationToken.None);
        }
    }
}
```

- **`ConnectAsync` throwing is the failed-handshake assertion** — a non-101 upgrade throws `WebSocketException`.
- **The pump's failure reaches the test.** `ContinueWith` completes the channel with the pump's exception, so
  the next `AwaitFrame` read throws `ChannelClosedException` wrapping it instead of timing out silently.
- **Only a server-initiated close is acknowledged.** When the test closes first, `CloseAsync` completes the
  handshake and the pump's pending receive returns the close; echoing it again would throw.

```csharp
using System.Net.WebSockets;
using NUnit.Framework;

namespace IntegrationTests;

public class ChatWebSocketTests : AppFixture
{
    private static readonly TimeSpan FrameTimeout = TimeSpan.FromSeconds(5);

    [Test]
    public async Task Should_BroadcastTheMessage_When_AClientSaysHello()
    {
        await using var probe = new WebSocketProbe();
        await probe.ConnectAsync(new Uri($"{BaseWsUri}/ws/chat"));

        await probe.SendAsync("""{ "type": "say", "text": "hello" }""");

        var frame = await AwaitFrame.NextAsync(probe.Frames, FrameTimeout);
        Assert.That(frame, Does.Contain("\"text\":\"hello\""), frame);
    }

    [Test]
    public async Task Should_EmitThreeTicksThenCloseNormally_When_ATickerOfThreeIsOpened()
    {
        await using var probe = new WebSocketProbe();
        await probe.ConnectAsync(new Uri($"{BaseWsUri}/ws/ticker?count=3"));

        var ticks = await AwaitFrame.TakeAsync(probe.Frames, 3, FrameTimeout);
        await probe.CloseAsync();

        Assert.Multiple(() =>
        {
            Assert.That(ticks, Has.Count.EqualTo(3));
            Assert.That(probe.CloseStatus, Is.EqualTo(WebSocketCloseStatus.NormalClosure));
        });
    }
}
```

## 2. Protocol client — SignalR hub (`HubConnection`)

When the endpoint is a **SignalR hub**, use the **real client**: `HubConnection` reassembles messages, handles
the heartbeat and, with `WithAutomaticReconnect`, reconnects, so you assert at the *hub* level. The await
primitive is a `TaskCompletionSource<T>` completed inside the `On<T>` handler — registered **before**
`StartAsync` — and awaited with `WaitAsync(timeout)`.

```csharp
using Microsoft.AspNetCore.SignalR.Client;
using NUnit.Framework;

namespace IntegrationTests;

public class ChatHubTests : AppFixture
{
    [Test]
    public async Task Should_ReceiveTheGroupMessage_When_APeerSendsToTheGroup()
    {
        await using var connection = new HubConnectionBuilder()
            .WithUrl($"{BaseUri}/hubs/chat")
            .WithAutomaticReconnect()
            .Build();
        var received = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
        connection.On<string, string>("ReceiveMessage", (user, text) => received.TrySetResult($"{user}:{text}"));
        await connection.StartAsync();

        await connection.InvokeAsync("SendToGroup", "general", "hi");

        Assert.That(await received.Task.WaitAsync(TimeSpan.FromSeconds(5)), Is.EqualTo("alice:hi"));
    }
}
```

`StartAsync()` *is* the condition-wait for "connected" — never sleep after it. Reconnect and keep-alive
(`KeepAliveInterval` / `ServerTimeout`) are asserted as behaviour (`connection.State`, the next message after a
drop), not re-implemented.

## 3. Protocol client — SSE (`SseProbe`)

SSE is **plain HTTP**: a `GET` whose body streams `text/event-stream`. `SseParser` (.NET 9+) parses it;
`SseItem<T>.EventId` is there from .NET 10. On .NET 8, read the stream line by line — accumulate `data:`, take
`event:` and `id:`, dispatch on a blank line — inside the probe. **`HttpCompletionOption.ResponseHeadersRead`**
is essential: without it `HttpClient` buffers the open-ended response and the test hangs.

```csharp
using System.Net;
using System.Net.ServerSentEvents;
using System.Threading.Channels;

namespace IntegrationTests.Realtime;

public sealed record SseEvent(string Type, string Data, string? Id);

public sealed class SseProbe(HttpClient http) : IAsyncDisposable
{
    private readonly Channel<SseEvent> _events = Channel.CreateUnbounded<SseEvent>();
    private readonly CancellationTokenSource _stop = new();
    private Task _pump = Task.CompletedTask;

    public ChannelReader<SseEvent> Events => _events.Reader;

    public async Task SubscribeAsync(string url)
    {
        var response = await http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, _stop.Token);
        var mediaType = response.Content.Headers.ContentType?.MediaType;
        if (response.StatusCode != HttpStatusCode.OK || mediaType != "text/event-stream")
        {
            throw new InvalidOperationException(
                $"GET {url} answered {(int)response.StatusCode} {mediaType}: {await response.Content.ReadAsStringAsync()}");
        }
        var stream = await response.Content.ReadAsStreamAsync(_stop.Token);
        _pump = PumpAsync(stream).ContinueWith(
            pump => _events.Writer.TryComplete(pump.IsCanceled ? null : pump.Exception?.GetBaseException()),
            TaskScheduler.Default);
    }

    public async ValueTask DisposeAsync()
    {
        await _stop.CancelAsync();
        await _pump;
        _stop.Dispose();
    }

    private async Task PumpAsync(Stream stream)
    {
        await foreach (var item in SseParser.Create(stream).EnumerateAsync(_stop.Token))
        {
            _events.Writer.TryWrite(new SseEvent(item.EventType, item.Data, item.EventId));
        }
    }
}
```

```csharp
[Test]
public async Task Should_StreamThreeProgressEventsThenDone_When_AJobRuns()
{
    await using var probe = new SseProbe(CreateClient());
    await probe.SubscribeAsync("/sse/progress?job=42");

    var events = await AwaitFrame.TakeAsync(probe.Events, 4, TimeSpan.FromSeconds(5));

    Assert.That(events.Select(e => e.Type), Is.EqualTo(new[] { "progress", "progress", "progress", "done" }));
}
```

- A wrong status or content type fails `SubscribeAsync` with the body, before any event is awaited.
- Dispose cancels the read; the continuation completes the channel and never throws, so teardown is quiet
  and an earlier stream failure has already reached the test through the channel.
- **Resume:** subscribe with `Last-Event-ID: <id>` on the request (`HttpRequestMessage` + `SendAsync`) and
  assert the first event after it is the next id — the protocol's replay contract.

## Browser page objects

The page objects `LiveFeedBrowserTests` builds in `[SetUp]` (SKILL.md, browser surfaces 1–3):

```csharp
using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public sealed class DashboardPage
{
    private readonly IPage _page;
    private readonly ILocator _signOut;

    public DashboardPage(IPage page)
    {
        _page = page;
        AcmePrice = page.GetByTestId("Ticker.AcmePrice").Describe("ACME price");
        _signOut = page.GetByTestId("Nav.SignOut");
    }

    public ILocator AcmePrice { get; }

    public async Task OpenAsync() => await _page.GotoAsync("/dashboard");

    public async Task SignOutAsync() => await _signOut.ClickAsync();
}

public sealed class StatusPage(IPage page)
{
    public ILocator AlertBanner { get; } = page.GetByRole(AriaRole.Alert).Describe("Status alert banner");

    public async Task OpenAsync() => await page.GotoAsync("/status");
}

public sealed class NotificationsPage(IPage page)
{
    public ILocator Items { get; } = page.GetByTestId("Notifications.Item").Describe("Notification items");

    public async Task OpenAsync() => await page.GotoAsync("/notifications");
}
```

One type per file in a project; they share a block here only to keep the reference short.

## Disciplines & gotchas

- **Lifecycle:** `ConnectAsync` throwing *is* the failed-handshake assertion; close in teardown (`await using`)
  and assert the close code where the contract specifies one.
- **Server emits N then closes:** `AwaitFrame.TakeAsync(reader, N, timeout)`, then assert the close.
- **Reconnection / backoff:** drop the server and assert the client reconnects with increasing intervals
  (SignalR `WithAutomaticReconnect`). SSE reconnects natively, honouring `retry:` and resending
  `Last-Event-ID` — assert the missed events are replayed from that id, against a real server.
- **Fragmentation:** raw `ClientWebSocket` delivers frames, not messages — the `EndOfMessage` loop is mandatory;
  send a message that spans frames and assert it reassembles. SignalR reassembles for you.
- **Auth on the socket** — whichever the contract uses: the **query string** (`?access_token=…`, what SignalR
  uses because browsers cannot set WS headers), a **subprotocol** (`options.AddSubProtocol(token)` →
  `Sec-WebSocket-Protocol`), or the **first frame**. Read the token from env, lazily, never logged
  (`qa-dotnet:test-login-tokens`). A server-side `HttpClient` can set `Authorization` on SSE; a browser
  `EventSource` cannot set headers — query or cookie auth.
- **Heartbeat (ping/pong):** control frames are handled below the pump; assert the application-level heartbeat
  if the app sends one, and SignalR's `KeepAliveInterval` / `ServerTimeout` behaviour.
- **WS upgrade in integration tests** needs a real Kestrel port (aspnetcore#31911).

## Anti-patterns (protocol client)

- **Reading `ReceiveAsync` once and assuming a whole message.** *Fix:* loop until `EndOfMessage`.
- **Buffering the SSE response** (`GetAsync` without `ResponseHeadersRead`). *Fix:* stream the body.
- **Never closing the socket**, or asserting only the payload. *Fix:* `await using`; assert `CloseStatus`.
- **`ClientWebSocket` against a SignalR hub.** *Fix:* the real `HubConnection`.
- **An empty `catch` in a probe's pump or dispose.** It hides why the stream died. *Fix:* complete the channel
  with the pump's exception, as `WebSocketProbe` and `SseProbe` do.

## Examples

**Auth via subprotocol (token on the handshake, from env, never logged):**

```csharp
var token = await Tokens.TestUser.GetAccessTokenAsync();
await probe.ConnectAsync(new Uri($"{BaseWsUri}/ws/secure"), options => options.AddSubProtocol(token));
```

**A builder for a 4+-field frame payload** (`qa-dotnet:test-data-builder`):

```csharp
var payload = ChatMessages.Standard().WithText("hello").WithRoom("general").Build();
await probe.SendAsync(JsonSerializer.Serialize(payload, JsonSerializerOptions.Web));
```
