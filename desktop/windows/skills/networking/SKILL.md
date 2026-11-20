---
name: networking
description: Use when a Windows desktop app calls an API (typed HttpClient, timeouts, retries, ProblemDetails, token refresh, ClientWebSocket). Triggers "call the API". Not for the form UI (forms).
disable-model-invocation: true
---

# Windows — Networking and Realtime

How a Windows desktop app talks to a server: **`IHttpClientFactory` typed clients, a timeout budget on every request, cancellation tied to the window, `Retry-After` honoured, ProblemDetails read into a typed failure, one token refresh in flight, and a reconnecting `ClientWebSocket`.** Audit rows: section H of `desktop-windows:standards-audit`. Applies to WinUI, WPF and WinForms alike.

## Version lane

| Concern | Primary | Note |
|---|---|---|
| Runtime | .NET 10 LTS (.NET 11 STS supported) | .NET 8 and 9 are out of support since 2026-11-10: flag, never target |
| HTTP | `Microsoft.Extensions.Http` 10.x, `HttpClient` through `IHttpClientFactory` | Same API on WinUI, WPF and WinForms |
| Resilience | `Microsoft.Extensions.Http.Resilience` (Polly v8 based) | Standard handler: rate limiter, total timeout, retry, circuit breaker, attempt timeout |
| Realtime | `System.Net.WebSockets.ClientWebSocket`; SignalR client `Microsoft.AspNetCore.SignalR.Client` when the server is SignalR | |
| Host | `Microsoft.Extensions.Hosting` composes it (WinUI: `architecture`; WPF: `wpf`; WinForms: `winforms`) | |

## When to use

- A view model needs data from, or sends data to, a server
- "Add a retry", "the call hangs", "refresh the token", "show the server's field errors", "keep a socket open"

## When NOT to use

- The form, the field errors, the banner → `desktop-windows:forms`, [`ui-components`](../ui-components/SKILL.md)
- Where the token and cache are stored → `desktop-windows:offline-and-storage`
- Sign-in flow itself → `auth0-winui` / `auth0-wpf` (S3)
- Server-side API design → the `be-*` plugins

---

## The typed client

One class per remote capability, constructor-injected `HttpClient`, registered once in the host. No `new HttpClient()` anywhere (it leaks sockets or pins DNS).

```csharp
public sealed class OrdersClient(HttpClient http)
{
    public async Task<Result<OrderDto>> GetAsync(Guid id, CancellationToken ct)
    {
        using var response = await http.GetAsync($"orders/{id}", ct);
        return await response.ToResultAsync<OrderDto>(ct);
    }
}
```

```csharp
services.AddHttpClient<OrdersClient>(client =>
{
    client.BaseAddress = new Uri(options.ApiBaseUrl);
    client.Timeout = Timeout.InfiniteTimeSpan;
})
.AddHttpMessageHandler<BearerTokenHandler>()
.AddStandardResilienceHandler();
```

- **One client per capability, not per screen.** The view model depends on `OrdersClient`; there is no `IOrdersClient` unless a test fake is needed (`V5`).
- **`BaseAddress` and every URL come from configuration**, never a literal in a view model. TLS only: an `http://` base address needs a recorded reason.
- **`Result<T>`** is a sealed type with `Ok(T)` and `Failed(Failure)`; the view model switches on it exhaustively (`architecture`). A method never returns `null` for a failure and never throws for an expected one.
- **`ToResultAsync`** is one extension that maps the response; it is the only place status codes are read.

## Timeouts — a budget, not a default

`HttpClient.Timeout` defaults to 100 seconds, which a user experiences as a frozen window. Set it to `InfiniteTimeSpan` and let the resilience handler own the budget:

| Layer | Setting | Typical |
|---|---|---|
| Total request | `TotalRequestTimeout` | 15 s read, 60 s upload |
| One attempt | `AttemptTimeout` | 5 s read |
| Retries | `Retry.MaxRetryAttempts` | 2, GET and other idempotent verbs only |
| Circuit breaker | `CircuitBreaker` | opens after repeated failure; the UI shows offline, not a spinner |

- **Never retry a non-idempotent `POST`** without an idempotency key the server honours. The standard handler retries everything by default: set `ShouldHandle` for writes.
- **A timeout is a typed failure** (`Failure.Timeout`), shown as a retry banner, never a raw `TaskCanceledException` message.

## Cancellation is part of the call

- Every client method takes a `CancellationToken` and passes it to every awaited call.
- A view-model command that loads data receives the token from `[RelayCommand]`; the window's close cancels it (`windows-and-navigation`).
- **Distinguish the two cancellations:** the caller's token cancelled → stop quietly, no banner; the timeout fired → `Failure.Timeout`. `OperationCanceledException` with `ct.IsCancellationRequested` false is a timeout.
- Stale responses: a search box cancels the previous request when the text changes; the last request wins.

## ProblemDetails into a typed failure

Servers answer RFC 9457 `application/problem+json`. Read it once, in `ToResultAsync`:

| Status | `Failure` | UI |
|---|---|---|
| 400 / 422 with `errors` | `Validation(fields)` | mapped to fields (`forms`) |
| 401 | `Unauthorized` | one refresh, then sign-in |
| 403 | `Forbidden` | banner: no permission |
| 404 | `NotFound` | empty/not-found state |
| 409 | `Conflict` | banner, input kept |
| 429 / 503 | `Throttled(RetryAfter)` | wait, then retry once |
| 5xx | `Server` | banner with retry |
| no response | `Offline` | offline state, not an error |

- **Parse `type`, `title`, `status`, `errors`**; keep `traceId` for the log, never display it as the message.
- **A body that is not ProblemDetails** (an HTML proxy page, a truncated JSON) is `Failure.Malformed`, a *failed* state, never an empty list. Deserialize with `System.Text.Json` source generation (`JsonSerializerContext`), and on a `JsonException` log the property path and keep the raw body for the log, not the UI.
- **The user text comes from a table keyed by `Failure`**, never from `Exception.Message` or `detail` (`C6`).

## `Retry-After`

For `429` and `503`, read `Retry-After` (seconds or an HTTP date) and wait that long, capped at the remaining total budget. Never a tight loop. The standard handler exposes `DelayGenerator`; set it from the header. Foreground work shows "Retrying in 12 s" with a cancel; background sync just reschedules.

## Token handling

```csharp
public sealed class BearerTokenHandler(ITokenStore tokens, TokenRefresher refresher) : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
    {
        request.Headers.Authorization = new("Bearer", await tokens.GetAccessTokenAsync(ct));
        var response = await base.SendAsync(request, ct);
        if (response.StatusCode != HttpStatusCode.Unauthorized) return response;

        response.Dispose();
        request.Headers.Authorization = new("Bearer", await refresher.RefreshAsync(ct));
        return await base.SendAsync(request, ct);
    }
}
```

- **Single-flight refresh:** `TokenRefresher` holds one in-flight `Task` (a `SemaphoreSlim` or a shared `Lazy<Task<string>>`); ten concurrent `401`s cause one refresh.
- **A request body that was streamed cannot be replayed** — buffer small bodies, or fail the retry as `Unauthorized`.
- **One refresh per request.** A second `401` signs the user out and raises the sign-in state; no loop.
- **Tokens live in `PasswordVault` / DPAPI** (`offline-and-storage`), never in `appsettings.json`, settings, logs or a URL. The `Authorization` header is redacted from HTTP logging (`RedactLoggedHeaders`).

## Reachability and revalidation

- **Offline is not an error.** `NetworkInformation.NetworkStatusChanged` (WinRT, needs no package identity on desktop) or `NetworkChange.NetworkAvailabilityChanged` flips the offline state; the failed region shows "Offline" with cached data marked stale (`offline-and-storage`).
- **Revalidate** on window activation, resume from sleep (`SystemEvents.PowerModeChanged` / `PowerManager`), and connectivity restored (CLAUDE.md § Desktop code rules). Throttle: no more than once per 30 s per resource.
- Reachability is a hint; the request's own failure is the truth.

## Realtime — `ClientWebSocket`

```csharp
public sealed class FeedSocket(Uri endpoint, ILogger<FeedSocket> logger) : IAsyncDisposable
{
    public async IAsyncEnumerable<FeedMessage> ReadAsync([EnumeratorCancellation] CancellationToken ct)
    {
        var delay = TimeSpan.FromSeconds(1);
        while (!ct.IsCancellationRequested)
        {
            using var socket = new ClientWebSocket();
            await socket.ConnectAsync(endpoint, ct);
            delay = TimeSpan.FromSeconds(1);
            await foreach (var message in ReceiveAsync(socket, ct)) yield return message;
            await Task.Delay(delay, ct);
            delay = TimeSpan.FromSeconds(Math.Min(delay.TotalSeconds * 2, 30));
        }
    }
}
```

- **Reconnect with exponential backoff and jitter**, capped (30 s); a `Close` frame from the server and a dropped link both reconnect.
- **`wss://` only.** Send the token in the first message or a header, not the query string (it lands in logs).
- **Receive on a background task, deliver to the UI through `DispatcherQueue.TryEnqueue`** (WinUI), `Dispatcher.InvokeAsync` (WPF) or `Control.BeginInvoke` (WinForms), **batched**: coalesce a burst into one enqueue, never one per message (`windows-and-navigation`).
- **Close properly** on window close: `CloseAsync` with a timeout, then dispose; cancel the read loop with the window's token.
- **Messages are untrusted input:** validate the frame size, parse with the source-generated serializer, drop and count what does not parse.
- A socket is a **state of the region** (`Connecting`, `Live`, `Reconnecting`, `Failed`), shown as a quiet indicator; a reconnect loop never raises a modal.

## Telemetry

HTTP is instrumented by `OpenTelemetry.Instrumentation.Http` (span per call, `traceparent` propagated). Add a log at each failure decision (`Failure` kind, status, attempt), a `http.client.retries` metric, and a `net.reconnects` counter for sockets. Never log bodies, tokens or query strings that carry ids of people.

## Common gotchas

- **`new HttpClient()` per call** — socket exhaustion; use the factory.
- **Default 100 s timeout** — the window looks hung; own the budget.
- **Retrying a `POST`** — a double charge; retry idempotent verbs only.
- **`.Result` on the UI thread** — deadlock (`B8`).
- **Showing `ex.Message`** — leaks internals; map `Failure` to user text.
- **A blank list on a malformed body** — it is a failed state.
- **Ten parallel refreshes** — single-flight it.
- **Token in the WebSocket URL** — it is logged by proxies.
- **A reconnect loop with no backoff** — hammers a recovering server.

## Handoffs

- Field errors, banner, retry button → `desktop-windows:forms`, [`ui-components`](../ui-components/SKILL.md)
- State type and cancellation in view models → [`architecture`](../architecture/SKILL.md)
- Token and cache storage → `desktop-windows:offline-and-storage`
- Sign-in → `auth0-winui` / `auth0-wpf`; TLS and certificate pinning rules → `desktop-shared:security`
- Mac counterpart → `desktop-macos:networking`
