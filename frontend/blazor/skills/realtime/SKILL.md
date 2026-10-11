---
name: realtime
description: Use when a Blazor surface (.NET 8/9/10) needs LIVE / server-pushed data — interactive-Server circuit push (`InvokeAsync(StateHasChanged)`), the WASM SignalR client (`HubConnection`, `WithStatefulReconnect`), raw WebSocket/SSE feeds, the prerender-snapshot→live-channel handoff. Triggers: "push updates to the UI", "SignalR in Blazor", "live dashboard/chat", "background job updates a component". Do NOT use for request/response fetching (`data-fetching`) or the reconnect modal UI (`error-handling`).
---

# Blazor — Realtime (live / push lane)

Owns the **live/push transport lane**: data arrives at the component *without it asking*. The **request/response lane** — the component asks, the server answers once — is [`data-fetching`](../data-fetching/SKILL.md)'s. Both skills open with the same routing decision.

## Transport routing — which lane am I in?

```
Is the data pushed by the server (it arrives without the component asking)?
  YES → live / push / stream  → THIS skill (realtime)
Is the data pulled by the component (it asks, the server answers once per request)?
  YES → request/response      → `data-fetching`
```

| Signal | Lane | Skill |
|---|---|---|
| Dashboard tile updates itself; ticker; chat; presence; progress; server notifications | live/push | **realtime** (here) |
| Load a list/detail; submit a form; paginate; search | request/response | [`data-fetching`](../data-fetching/SKILL.md) |
| Long query streamed in chunks to first paint (`[StreamRendering]`) | request/response | [`data-fetching`](../data-fetching/SKILL.md) |
| Third-party feed over WebSocket/SSE | live/push | **realtime** (here) |

Most live surfaces do **both**: [`data-fetching`](../data-fetching/SKILL.md) fetches the initial state, then this skill's live channel takes over. The **prerender-snapshot handoff** (below) is the seam.

**Version rule:** detect the `TargetFramework` first. `WithStatefulReconnect`, the `ReconnectModal`, and circuit pause/resume are net8+/net10 as noted; net8/net9 fallbacks are tagged. Never emit a net10-only API into a down-level project.

## The push mechanism differs by render mode

| Render mode | Push channel | Client needed? |
|---|---|---|
| **InteractiveServer** | **the circuit itself is already a WebSocket** | **No SignalR client** — subscribe to a server broker, marshal to UI via `InvokeAsync(StateHasChanged)` |
| **InteractiveWebAssembly** | a SignalR **`HubConnection`** the browser opens to a hub | Yes — the WASM client lane below |
| **InteractiveAuto** | Server push while server-side → SignalR client once WASM takes over | Both, behind one subscription abstraction |
| **Static SSR** | none — no live channel on a static page | promote the surface to an interactive island first |

## Interactive Server — the circuit is the channel

A Server component already holds a live WebSocket (the circuit). Server-originated updates reach it through a **broker → scoped subscription → `InvokeAsync(StateHasChanged)`**. No `HubConnection`, no SignalR client.

```csharp
// A singleton/BackgroundService broker raises events (e.g. from a queue, DB change feed, domain event).
public sealed class PriceBroker
{
    public event Action<PriceTick>? Ticked;
    public void Publish(PriceTick tick) => Ticked?.Invoke(tick);   // called from background work
}
// Program.cs: builder.Services.AddSingleton<PriceBroker>();
```

```razor
@implements IDisposable
@inject PriceBroker Broker

<span data-testid="Ticker.Price">@_price</span>

@code {
    private decimal _price;

    protected override void OnInitialized() => Broker.Ticked += OnTick;

    private void OnTick(PriceTick tick) =>
        InvokeAsync(() => { _price = tick.Price; StateHasChanged(); });   // hop onto the circuit's sync context

    public void Dispose() => Broker.Ticked -= OnTick;   // always unsubscribe — the broker is a singleton
}
```

**The two non-negotiables:**
1. **A background thread must never touch component state directly.** The broker event fires on a thread-pool thread; the component lives on the circuit's synchronization context. Marshal *every* UI mutation through `InvokeAsync(...)` — a direct `_price = ...; StateHasChanged();` from the event races the renderer and corrupts state.
2. **Always unsubscribe in `Dispose`.** The broker is a singleton; the component is scoped. A missed unsubscribe leaks the component (and its whole render tree) for the life of the app, and fires `StateHasChanged` on a disposed component.

Use `IHubContext<THub>` **only** when non-circuit clients (a mobile app, another service) consume the same hub — not to push to your own Server components.

**Scale-out:** the circuit is stateful, so **sticky sessions are mandatory** behind a load balancer, and a **backplane** (Azure SignalR Service or a Redis backplane) is required so a broker event on node A reaches a circuit pinned to node B.

## WASM — the SignalR client lane

A WASM component has no circuit, so it opens a `HubConnection` to a hub. Build it in `OnInitializedAsync`, implement `IAsyncDisposable`, and marshal received messages through `InvokeAsync(StateHasChanged)` (same sync-context rule).

```razor
@implements IAsyncDisposable
@inject NavigationManager Nav
@inject IAccessTokenProvider TokenProvider   @* auth — provider-neutral *@

<span data-testid="Notifications.Count">@_count</span>
<ConnectionBadge State="@_state" />   @* status affordance — see below *@

@code {
    private HubConnection? _hub;
    private int _count;
    private HubConnectionState _state = HubConnectionState.Disconnected;

    protected override async Task OnInitializedAsync()
    {
        _hub = new HubConnectionBuilder()
            .WithUrl(Nav.ToAbsoluteUri("/hubs/notifications"), options =>
                options.AccessTokenProvider = async () => (await TokenProvider.RequestAccessToken())
                    .TryGetToken(out var t) ? t.Value : null)
            .WithAutomaticReconnect()        // reconnect with backoff on transport blips
            .WithStatefulReconnect()         // net8+: buffer + ACK-replay so brief blips lose NO messages
            .Build();

        _hub.On<int>("CountChanged", n => InvokeAsync(() => { _count = n; StateHasChanged(); }));
        _hub.Reconnecting += _ => UpdateState();
        _hub.Reconnected  += _ => UpdateState();
        _hub.Closed       += _ => UpdateState();

        await _hub.StartAsync();
        UpdateState();
    }

    private Task UpdateState() =>
        InvokeAsync(() => { _state = _hub!.State; StateHasChanged(); });

    public async ValueTask DisposeAsync()
    {
        if (_hub is not null) await _hub.DisposeAsync();   // stops the connection AND unhooks handlers
    }
}
```

- **`WithAutomaticReconnect()`** retries on drop with a backoff schedule; **`WithStatefulReconnect()`** (net8+, and Azure SignalR SDK ≥ 1.26.1 server-side) buffers unacknowledged messages and replays them on reconnect so a short blip loses nothing. Without it, messages sent during the gap are gone.
- **Transport fallback** is automatic: WebSockets → Server-Sent Events → long polling. Prefer WebSockets (lower latency, reliable); only pin the transport when a proxy forces it.
- **Streaming** a server method: `await foreach (var item in _hub.StreamAsync<T>("Feed", ct)) { ... }` for continuous server output, distinct from one-shot invocations.
- **Hub auth is provider-neutral** — the `AccessTokenProvider` supplies whatever OIDC token the auth layer minted (**Auth0 or AWS Cognito**); wiring lives in `auth/auth0-blazor` · `auth/cognito-blazor`.
- **Connection-status affordance** is mandatory: surface `HubConnectionState` (Connected / Reconnecting / Disconnected) so the user knows the data may be stale. The full reconnection *modal* UX is [`error-handling`](../error-handling/SKILL.md)'s.

## Raw WebSocket / SSE — non-SignalR feeds

For third-party or non-SignalR backends, talk the protocol directly:

- **WebSocket:** `ClientWebSocket` (WASM: over the browser WS API) — connect, `ReceiveAsync` loop into a channel, buffer + apply backpressure, dispose on component teardown.
- **SSE:** consume the `text/event-stream` as a streaming `HttpResponseMessage` and parse events line by line.
- **Dedupe by message key** — at-least-once feeds redeliver; key each message and drop repeats so the UI doesn't double-apply.

Same disposal + `InvokeAsync` marshalling rules as the SignalR lane.

## Prerender-snapshot → live-channel handoff

Fetch the initial state via [`data-fetching`](../data-fetching/SKILL.md) and persist it with `[PersistentState]` (net10) so prerender shows real data with no flash and no double-fetch; then start the live channel and let it take over:

```razor
@implements IAsyncDisposable
@inject IDashboardData Data   @* data-fetching: initial state *@

@code {
    [PersistentState] public DashboardSnapshot? Snapshot { get; set; }   // net10; net8/9 → PersistentComponentState

    protected override async Task OnInitializedAsync()
    {
        Snapshot ??= await Data.GetSnapshotAsync();   // request/response — fills first paint
        await StartLiveChannel();                     // realtime — takes over updates
    }
    // ... live handlers mutate Snapshot via InvokeAsync(StateHasChanged); IAsyncDisposable tears down.
}
```

This is the exact seam between the two lanes: **data-fetching owns the snapshot, realtime owns the stream.**

## Rules

- **Open every live feature with the transport routing decision**: push → here; pull → [`data-fetching`](../data-fetching/SKILL.md).
- **Interactive Server: no SignalR client** — subscribe to a server broker; the circuit is the channel.
- **Every background→UI update is marshalled through `InvokeAsync(StateHasChanged)`** — a background thread never touches component state directly (circuit *and* renderer sync context).
- **Every subscription/connection is torn down** — `IDisposable`/`IAsyncDisposable`, unsubscribe from singleton brokers, `DisposeAsync` the `HubConnection`.
- **WASM: build `HubConnection` in `OnInitializedAsync`**, `WithAutomaticReconnect()` + `WithStatefulReconnect()` (net8+), Reconnecting/Reconnected/Closed handlers, and a **connection-status affordance**.
- **Prefer WebSockets**; rely on automatic transport fallback rather than pinning.
- **Prerender a `[PersistentState]` snapshot** via [`data-fetching`](../data-fetching/SKILL.md), then hand off to the live channel — no flash, no double-fetch.
- **Hub auth token is IdP-agnostic** (Auth0 / Cognito), sourced from the auth skill.
- **Scale-out (Server): sticky sessions + Azure SignalR/Redis backplane.**
- **Every live element carries a `data-testid`** per [`test-ids`](../test-ids/SKILL.md); connection-status control included.

## What NOT to do

- No mutating component state from a broker/hub callback without `InvokeAsync` — it races the renderer.
- No subscription/`HubConnection` left undisposed; no missed unsubscribe from a singleton broker (leaks the whole render tree).
- No SignalR *client* in an interactive-Server component to reach its own UI — use the circuit + broker.
- No `HubConnection` built in `OnAfterRenderAsync` for the connection itself (auth/token timing) — build it in `OnInitializedAsync`.
- No live channel on a static-SSR page — promote to an interactive island first.
- No stale UI without a connection-status affordance during reconnect.
- No scale-out without sticky sessions + backplane (Server) — cross-node pushes silently vanish.
- No net10-only API (circuit pause/resume, `ReconnectModal`) emitted into net8/net9.

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- `dotnet build` — 0 warnings.
- Kill the connection (stop the hub / drop the network) → status affordance flips to Reconnecting; on restore, `WithStatefulReconnect` replays buffered messages (no gap).
- Navigate away from a live page → subscription unsubscribed / `HubConnection` disposed (no `StateHasChanged` on a disposed component in logs).
- Server scale-out smoke: a broker event on node A reaches a circuit on node B (backplane wired).
- No flash on prerendered live page — snapshot renders, then live updates continue.

## Handoffs

- Initial-state fetch + the shared routing matrix → [`data-fetching`](../data-fetching/SKILL.md)
- Reconnection modal, circuit pause/resume, three-state failure UX → [`error-handling`](../error-handling/SKILL.md)
- Hub auth token (Auth0 / Cognito) → `auth/auth0-blazor` · `auth/cognito-blazor`
- Testids on live elements → [`test-ids`](../test-ids/SKILL.md)
- **Testing** these streams → `qa/dotnet/skills/realtime-stream-testing` (peer); **connection-count load** → `qa-performance-dotnet` (peer)
