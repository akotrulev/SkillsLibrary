# Deep-dive details — `qa-realtime-stream-testing-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

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
