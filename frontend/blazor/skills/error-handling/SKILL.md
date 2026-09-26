---
name: fe-blazor-error-handling
description: Use when a Blazor app (.NET 8/9/10) must fail safely and recover — `ErrorBoundary` placement, `OnErrorAsync` logging, interactive-Server reconnection UX (net10 `ReconnectModal`, circuit pause/resume), Polly on `HttpClient`, three-state data regions with retry, actionable empty states. Triggers: "an unhandled exception blanks my app", "add error boundaries", "show a reconnect UI when the circuit drops". Do NOT use to PRODUCE the categorized error (`data-fetching` — this RENDERS it).
---

# Blazor — Error Resilience

Owns everything about **failing safely and recovering**: catching exceptions before they blank the app, keeping an interactive-Server circuit reconnectable, retrying transient HTTP faults, and — the half most teams miss — **rendering failure and emptiness correctly in the UI** so a broken section never looks like an empty-but-fine section.

Division of labor with [`data-fetching`](../data-fetching/SKILL.md): data-fetching **produces** a categorized `Result` (ProblemDetails → friendly message + correlation id, raw detail logged server-side). This skill **renders** that result — the three-state region, the retry, the inline grid error. Two skills, one seam.

**Version rule:** detect the `TargetFramework` first. `ErrorBoundary`, `OnErrorAsync`, and Polly are net8+. The **net10** deltas are reconnection-side: the customizable `ReconnectModal` component (source shipped in the template), `Blazor.pauseCircuit()`/`resumeCircuit()`, and circuit-eviction state persistence. net8/net9 fallbacks (the default reconnect UI + JS reconnection handlers) are tagged below.

## When to use

- Placing `ErrorBoundary` so an exception degrades one region, not the app
- Logging caught render exceptions with a correlation id
- Reconnection UX for interactive Server (drop → reconnecting → resumed / failed)
- Retry/timeout/circuit-breaker on outbound `HttpClient` calls
- Shipping WASM client errors to the server log
- Rendering the three states of a data region (loading / loaded / failed) + actionable empty states

## When NOT to use

- Producing the categorized error `Result` from an API call → [`data-fetching`](../data-fetching/SKILL.md)
- Per-field form validation messages → [`forms`](../forms/SKILL.md)
- The SignalR live-data client + its reconnect handlers as a *feature* → [`realtime`](../realtime/SKILL.md) (this skill owns the *UX* of a dropped circuit; realtime owns the hub connection)
- Circuit/SignalR *scale* (memory, backplane) → [`performance`](../performance/SKILL.md)
- Auth token-expiry mid-session → `auth/auth0-blazor` (session lifecycle)

## The three failure surfaces

```
Unhandled EXCEPTION during render/lifecycle  → ErrorBoundary (catch, degrade the region)
Interactive-Server CIRCUIT dropped (network) → Reconnection UX (ReconnectModal, pause/resume)
Outbound HTTP call FAILED (transient/4xx/5xx) → Resilience handler + categorized Result → three-state render
```

Each surface has its own mechanism; wire all three. A boundary won't save a dropped circuit; a retry won't catch a render NRE.

---

## ErrorBoundary — catch exceptions, degrade the region

An unhandled exception in a component's render or lifecycle **tears down the whole render tree** (interactive Server: the circuit becomes unrecoverable; WASM: the app is dead). `ErrorBoundary` catches it and swaps in error content for **just that subtree**.

**Placement — two tiers:**

1. **Global**, in the layout, around `@Body` — the last line of defense so any uncaught error shows a friendly page-level message instead of a white screen:

   ```razor
   @* MainLayout.razor *@
   <ErrorBoundary>
       <ChildContent>@Body</ChildContent>
       <ErrorContent>
           <AppErrorPanel />   @* friendly message + "reload" + correlation id — never the exception *@
       </ErrorContent>
   </ErrorBoundary>
   ```

2. **Per-feature**, around independently-failing regions (a dashboard tile, a grid, a side panel) so one widget's failure doesn't blank the page around it.

**Derive a boundary to log + bound errors.** The base `ErrorBoundary` swallows silently; a derived one logs with context and caps repeats:

```csharp
public sealed class LoggingErrorBoundary : ErrorBoundary
{
    [Inject] private ILogger<LoggingErrorBoundary> Logger { get; set; } = default!;

    protected override async Task OnErrorAsync(Exception ex)
    {
        Logger.LogError(ex, "Unhandled UI error in {Boundary}", GetType().Name);  // structured — never string-interpolate
        await base.OnErrorAsync(ex);
    }
}
```

- **`MaximumErrorCount`** (default 100) — after N errors the boundary stops recovering and stays in the error state. Lower it for a region that shouldn't retry a poisoned render forever.
- After a handled error, call **`Recover()`** on navigation or an explicit "try again" so the region can re-render once the cause is gone.
- The `ErrorContent` **never renders `ex.Message`** — friendly text + a correlation id only (same rule as the API invoker below).

---

## Reconnection UX (interactive Server)

An interactive-Server app runs over a SignalR circuit. Drop the network and the UI freezes until reconnect. Blazor ships a default reconnection UI; make it deliberate:

- **net10:** the template includes a customizable **`ReconnectModal`** component (Razor + collocated JS) — own it, brand it, and make the three states legible: *reconnecting* (retrying, spinner), *reconnected* (brief confirmation), *failed* (offer a full reload). Use **`Blazor.pauseCircuit()` / `resumeCircuit()`** to pause the circuit when the tab is hidden and resume on focus (saves server work; avoids a spurious "disconnected" on a backgrounded tab).
- **net8/net9:** style the built-in `components-reconnect-modal` element via its documented CSS classes (`components-reconnect-show/hide/failed/rejected`); hook the JS reconnection handlers for custom retry backoff.
- **Eviction persistence:** a disconnected circuit is retained briefly then evicted (bounded by `DisconnectedCircuitMaxRetained` / retention timeout — [`performance`](../performance/SKILL.md) owns the sizing). On net10, circuit-eviction **state persistence** (+ `HybridCache` distributed restore) lets a reconnecting user land on their prior state instead of a cold reload — persist the state a user would hate to lose.
- **Pairs with [`realtime`](../realtime/SKILL.md):** its `HubConnection` reconnect handlers (Closed/Reconnecting/Reconnected) drive the *live-data* connection-status affordance; this skill owns the *circuit-level* modal. Same disconnect event, two layers — keep them consistent (don't show "connected" data over a "reconnecting" modal).

---

## HTTP resilience (WASM / outbound calls)

Transient faults (a blip, a cold-start 503, a throttled 429) should be absorbed, not surfaced:

```csharp
builder.Services.AddHttpClient<HttpOrderData>(c => c.BaseAddress = new Uri(baseUrl))
    .AddStandardResilienceHandler();   // Microsoft.Extensions.Http.Resilience (Polly v8): retry + timeout + circuit breaker + rate limiter
```

- Prefer **`AddStandardResilienceHandler()`** (the batteries-included Polly v8 pipeline) over hand-rolled retries; customize the pipeline options only when the defaults don't fit.
- **Only retry idempotent operations** (GET/PUT/DELETE) — retrying a non-idempotent POST can double-charge/double-create. Gate retries by method.
- The **circuit breaker** stops hammering a downed dependency; when it's open, the call fails fast → your categorized `Result` → the three-state region shows "temporarily unavailable, retry". (This `HttpClient` circuit breaker is Polly's, unrelated to a Blazor Server *circuit*.)

**WASM → server log shipping:** WASM exceptions land in the browser console where no one sees them. Ship them: a global handler (`Blazor.start` `internalError` hook / a top-level try-catch in interop-heavy code) POSTs to a lightweight server log endpoint, so client faults reach the same structured logs/OTel as the server (`observability/opentelemetry-node`-style bridge on the .NET client, external skill). Rate-limit the endpoint.

---

## UI-correctness: rendering failure & emptiness (ui-rules seed §3–4)

The rules below are the most-missed part of resilience — the app *handles* the error but *renders* it as an ambiguous blank. Each is a real defect class.

### One shared API invoker; never leak raw errors

Route every call through the invoker [`data-fetching`](../data-fetching/SKILL.md) defines — it categorizes (ProblemDetails → friendly message; unknown → generic message + correlation id) and logs raw detail server-side. **This skill's rule: never render `ex.Message` or a raw response body to the user** (bodies may be JSON, stack traces, or PII). The invoker's output is a `Result<T>` carrying `IsSuccess` / friendly `Error` / `CorrelationId` — render *that*.

### Three-state data regions — loading / loaded / failed

Every data region has **three** states, not two. The classic bug: `try { … } catch { }` leaves the region empty, so an **outage is indistinguishable from "no data"**. Render the failed state **inline, with retry** — never only a toast (a toast disappears; the empty region stays and lies):

```razor
@if (_state == LoadState.Loading)
{
    <Skeleton data-testid="Orders.Loading" />
}
else if (_state == LoadState.Failed)
{
    <div class="data-error" role="alert" data-testid="Orders.Error">
        <p>@_error   @* friendly message from Result — never ex.Message *@</p>
        @if (_correlationId is not null) { <small>Ref: @_correlationId</small> }
        <button @onclick="LoadAsync" data-testid="Orders.Retry">Try again</button>
    </div>
}
else if (_orders is { Count: 0 })
{
    <EmptyState … />   @* see actionable empty states below *@
}
else
{
    @* the loaded grid *@
}

@code {
    private enum LoadState { Loading, Loaded, Failed }
    private LoadState _state = LoadState.Loading;
    private string? _error, _correlationId;
    private IReadOnlyList<OrderDto>? _orders;

    protected override Task OnInitializedAsync() => LoadAsync();

    private async Task LoadAsync()
    {
        _state = LoadState.Loading;
        var result = await Data.GetOrdersResultAsync();     // categorized Result from data-fetching
        if (result.IsSuccess) { _orders = result.Value; _state = LoadState.Loaded; }
        else { _error = result.Error; _correlationId = result.CorrelationId; _state = LoadState.Failed; }
    }
}
```

### Inline error region **inside** grids

A grid load failure needs its error rendered **in the grid area**, not just a toast — an empty grid is indistinguishable from "no rows". Bind the failed state on the **shared renderer** so every grid gets it for one change ([`ui-rules`](../ui-rules/SKILL.md) renderer unification), and bind the loading indicator there too (one `IsLoading` on the shared grid fixes every page).

### Actionable empty states — three kinds

"Empty" is three different situations; each needs a different message and a different action:

| Situation | Message (in the data area, not a toast) | Action |
|---|---|---|
| **No records exist yet** | "No orders yet." | offer the **create** action |
| **No filter applied yet** | "Enter a filter to begin." | focus the filter |
| **Filter matched nothing** | "No orders match these filters." | offer **clear filters** |

A single generic "No data" for all three is a defect — it tells the user nothing about what to do next.

---

## Rules

- **Global `ErrorBoundary`** around `@Body` in the layout + **per-feature boundaries** around independently-failing regions.
- **Derive the boundary** to log (structured, with context) via `OnErrorAsync`; set `MaximumErrorCount`; `Recover()` on navigation/retry; **never render `ex.Message`** in `ErrorContent`.
- **Own the reconnection UX**: net10 `ReconnectModal` (reconnecting/reconnected/failed states) + `pauseCircuit`/`resumeCircuit` on tab visibility; net8/9 style the built-in modal; persist eviction state a user would hate to lose.
- **`AddStandardResilienceHandler()`** on outbound `HttpClient`; retry idempotent methods only; let the breaker fail fast into a categorized `Result`.
- **Ship WASM client errors to the server log** (rate-limited endpoint).
- **Three-state data regions** everywhere: loading / loaded / failed **inline with retry** — never swallow a failure into a blank section.
- **Grid failures render inline in the grid**; loading + failed states bound on the **shared renderer**.
- **Actionable empty states** — distinguish no-records / no-filter / filter-matched-nothing.
- **Reconnection modal and live-data status stay consistent** (don't show live data over a reconnecting circuit — coordinate with [`realtime`](../realtime/SKILL.md)).

## What NOT to do

- No app without a global `ErrorBoundary` (one uncaught exception = white screen / dead circuit).
- No `ex.Message` / raw response body / stack trace rendered to a user.
- No two-state region (loaded / not-loaded) — a failure then reads as "no data".
- No failure surfaced *only* as a toast for a persistent region (grid/detail/section).
- No generic "No data" covering all three empty situations.
- No retry on a non-idempotent POST; no hand-rolled retry loop where `AddStandardResilienceHandler` fits.
- No net10-only reconnection API (`ReconnectModal` customization, `pauseCircuit`) emitted into net8/net9 — use the tagged fallback.
- No unlogged WASM client exception (console-only = invisible).

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- Force an exception in a feature component → its boundary shows friendly content; the rest of the page still works; the log has the structured entry + correlation id; no `ex.Message` on screen.
- Kill the network on an interactive-Server page → the reconnect modal appears; restore → it reconnects (net10: prior state restored, not a cold reload).
- Make an API call 500 → the region shows the **failed** state inline with a working retry, not a blank grid; the retry recovers on the next success.
- Empty each way (no records / no filter / filtered-out) → three distinct actionable messages.
- Throw in WASM → the error reaches the server log (not just the browser console).

## Handoffs

- The categorized `Result` this skill renders → [`data-fetching`](../data-fetching/SKILL.md) (produces it)
- Live-data hub reconnect handlers + connection-status affordance → [`realtime`](../realtime/SKILL.md)
- Circuit/SignalR memory + retained-circuit sizing → [`performance`](../performance/SKILL.md)
- Field-level validation errors → [`forms`](../forms/SKILL.md)
- Renderer unification (bind loading/failed once on the shared grid) → [`ui-rules`](../ui-rules/SKILL.md)
- Auth token-expiry mid-session → `auth/auth0-blazor`
- Client/server error export to Grafana → `observability/opentelemetry-dotnet`
