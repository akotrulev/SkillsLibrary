---
name: fe-blazor-data-fetching
description: Use when a Blazor component must FETCH or WRITE data (.NET 8/9/10) — typed `HttpClient` for WASM vs server-direct services/`IDbContextFactory` for interactive SSR behind one render-mode-agnostic interface, ProblemDetails→UI mapping, `[PersistentState]` to kill the prerender double-fetch. Triggers: "how should this component load data", "avoid the double fetch on prerender", "one data interface for Server and WASM". Do NOT use for live data (`realtime`) or auth wiring (`auth/auth0-blazor`).
---

# Blazor — Data Access (request/response lane)

Owns the **request/response transport lane**: a component asks for data and gets an answer. The **live/push lane** — server-originated updates, streams, presence — is [`realtime`](../realtime/SKILL.md)'s. Both skills open with the same routing decision so you land in the right one.

## Transport routing — which lane am I in?

```
Is the data pulled by the component (it asks, the server answers once per request)?
  YES → request/response      → THIS skill (data-fetching)
Is the data pushed by the server (it arrives without the component asking)?
  YES → live / push / stream  → `realtime`
```

| Signal | Lane | Skill |
|---|---|---|
| Load a page's list/detail; submit a form; paginate; search | request/response | **data-fetching** (here) |
| Dashboard tile updates itself; chat; presence; progress; server events | live/push | [`realtime`](../realtime/SKILL.md) |
| Long-running query you want to *stream in chunks* to the first paint | request/response + **streaming rendering** | **data-fetching** (here) |
| Third-party feed over WS/SSE | live/push | [`realtime`](../realtime/SKILL.md) |

A surface often uses both: fetch the initial state here, then hand off to `realtime` for updates (the prerender-snapshot handoff below is the seam).

**Version rule:** detect the `TargetFramework` first. `[PersistentState]`, `HybridCache`, and streaming-rendering ergonomics are net10 primary; net8/net9 fallbacks are tagged. Never emit a net10-only API into a down-level project.

## When to use

- Deciding how a component loads/writes data under its render mode
- Building the render-mode-agnostic data interface + its two implementations
- Killing the prerender double-fetch (`[PersistentState]`)
- Mapping API errors (ProblemDetails) to UI without leaking raw detail
- Streaming a slow query into the first paint; caching with `HybridCache`; cancelling on navigation

## When NOT to use

- Live/server-pushed data → [`realtime`](../realtime/SKILL.md)
- Forms + validation + submit UX → [`forms`](../forms/SKILL.md)
- The token-attaching auth handler itself → `auth/auth0-blazor` (this skill *consumes* it)
- Where state should live after fetch → [`state-management`](../state-management/SKILL.md)
- Three-state loading/failed regions + retry UX → [`error-handling`](../error-handling/SKILL.md)
- Writing the API, its DTOs, or contract tests → `qa/dotnet/skills/{api-models,api-contract-testing}` (peers)

## The core decision: one interface, two implementations

The render mode fixes *where the component runs*, which fixes *how it can reach data*:

| Render mode | Runs where | Data reach | Implementation |
|---|---|---|---|
| **Static SSR / InteractiveServer** | server | in-process — your services, DB, caches | **server-direct**: inject the application service; `IDbContextFactory` for EF Core |
| **InteractiveWebAssembly** | browser | HTTP only — no server process | **typed `HttpClient`** to an API |
| **InteractiveAuto** | server *then* browser | **both**, over the component's lifetime | **both**, chosen at DI registration per project |

So define **one render-mode-agnostic interface** the component depends on, and register the right implementation per project. This is the price of Auto mode ([`project-setup`](../project-setup/SKILL.md) names it) — paid deliberately, here.

```csharp
// Shared contract (in .Client so both projects see it) — the component depends only on this.
public interface IOrderData
{
    Task<IReadOnlyList<OrderDto>> GetOrdersAsync(CancellationToken ct = default);
    Task<OrderDto?> GetOrderAsync(Guid id, CancellationToken ct = default);
}
```

### Server lane — inject the service, factory the DbContext

```csharp
// Server project
public sealed class ServerOrderData(IDbContextFactory<AppDbContext> dbFactory) : IOrderData
{
    public async Task<IReadOnlyList<OrderDto>> GetOrdersAsync(CancellationToken ct = default)
    {
        await using var db = await dbFactory.CreateDbContextAsync(ct);   // one context per unit of work
        return await db.Orders.Select(o => o.ToDto()).ToListAsync(ct);
    }

    public async Task<OrderDto?> GetOrderAsync(Guid id, CancellationToken ct = default)
    {
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        return await db.Orders.Where(o => o.Id == id).Select(o => o.ToDto()).FirstOrDefaultAsync(ct);
    }
}

// Program.cs (server)
builder.Services.AddDbContextFactory<AppDbContext>(o => o.UseNpgsql(cfg.GetConnectionString("Db")));
builder.Services.AddScoped<IOrderData, ServerOrderData>();
```

**Never inject a `DbContext` directly into a Blazor component or a circuit-scoped service.** A component's DI scope is the **circuit** (interactive Server) — it outlives a single request, so a captured `DbContext` lives for the whole session: connection held open, change-tracker growing, and concurrent renders racing on one non-thread-safe context. `IDbContextFactory` hands out a short-lived context per operation. No HTTP hop to your own API from the server lane — call the service in-process.

### WASM lane — typed `HttpClient`, auth handler, resilience

```csharp
// .Client project
public sealed class HttpOrderData(HttpClient http) : IOrderData
{
    public async Task<IReadOnlyList<OrderDto>> GetOrdersAsync(CancellationToken ct = default) =>
        await http.GetFromJsonAsync<IReadOnlyList<OrderDto>>("api/orders", ct) ?? [];

    public async Task<OrderDto?> GetOrderAsync(Guid id, CancellationToken ct = default) =>
        await http.GetFromJsonAsync<OrderDto>($"api/orders/{id}", ct);
}

// Program.cs (.Client)
builder.Services.AddScoped<IOrderData, HttpOrderData>();
builder.Services.AddHttpClient<HttpOrderData>(c => c.BaseAddress = new Uri(baseUrl))
    .AddHttpMessageHandler<AccessTokenHandler>()   // attaches the bearer token — see auth skill
    .AddStandardResilienceHandler();               // Microsoft.Extensions.Http.Resilience: retry + timeout + circuit breaker
```

The **token-attaching `DelegatingHandler` is auth's, not this skill's** — and it's **IdP-agnostic**: it attaches whatever access token the auth layer produced, whether that's **Auth0** or **AWS Cognito** (both are OIDC). This skill just registers it on the client. Get the handler from `auth/auth0-blazor` (`CustomAuthorizationMessageHandler`) or the Cognito equivalent; the base address comes from **configuration**, never a hardcoded/`localhost` literal ([`project-setup`](../project-setup/SKILL.md) config hygiene).

### Consumer — identical regardless of lane

```razor
@page "/orders"
@inject IOrderData Data

<PageTitle>Orders</PageTitle>

@if (_orders is null) { <p data-testid="Orders.Loading">Loading…</p> }
else { /* render _orders — see error-handling for the three-state region */ }

@code {
    [PersistentState] public IReadOnlyList<OrderDto>? _orders { get; set; }

    protected override async Task OnInitializedAsync() =>
        _orders ??= await Data.GetOrdersAsync();
}
```

The component names only `IOrderData`. It never knows whether it's talking to a DB or an API — that's what lets the same component run under Server, WASM, or Auto.

## Kill the prerender double-fetch — `[PersistentState]`

Under Auto/prerender, `OnInitializedAsync` runs **twice** — once server-side (prerender) and once when the component goes interactive — so a naive fetch hits the backend twice. `[PersistentState]` (net10) persists the prerendered result into the page and the interactive run rehydrates it (`??=` guards the refetch):

```csharp
[PersistentState] public IReadOnlyList<OrderDto>? _orders { get; set; }
protected override async Task OnInitializedAsync() => _orders ??= await Data.GetOrdersAsync();
```

net8/net9 fallback: manual `PersistentComponentState` register/take/dispose (see [`state-management`](../state-management/SKILL.md) and [`component-writer`](../component-writer/SKILL.md) for the full down-level recipe). Add `AllowUpdates = true` (net10) when the value should refresh across enhanced navigation.

## Streaming rendering for slow paths (static SSR)

When a static-SSR page has a slow query, stream the shell first and the data when it resolves — no blank wait, no full interactivity cost:

```razor
@page "/report"
@attribute [StreamRendering]   @* net8+: renders a loading UI, then re-renders when the await completes *@

@if (_rows is null) { <p data-testid="Report.Loading">Crunching…</p> }
else { /* table */ }

@code {
    private IReadOnlyList<RowDto>? _rows;
    protected override async Task OnInitializedAsync() => _rows = await Data.GetSlowReportAsync();
}
```

Streaming rendering is request/response — it just splits the response. Live updates after first paint are [`realtime`](../realtime/SKILL.md).

## `HybridCache` (net9+)

Cache read-heavy, slow, or fan-out server-side reads with stampede protection + optional distributed (Redis) backing:

```csharp
public sealed class CachedOrderData(IOrderData inner, HybridCache cache) : IOrderData
{
    public async Task<OrderDto?> GetOrderAsync(Guid id, CancellationToken ct = default) =>
        await cache.GetOrCreateAsync($"order:{id}", inner,
            (i, c) => new ValueTask<OrderDto?>(i.GetOrderAsync(id, c)), cancellationToken: ct);
    // ...
}
```

Decorate the server implementation, not the component. On net8, fall back to `IMemoryCache` / `IDistributedCache` with your own stampede lock.

## Cancellation on navigation

A fetch outliving its component wastes work and can throw on a disposed scope. Tie the token to the component lifetime and pass it all the way to `HttpClient`/EF Core:

```csharp
private readonly CancellationTokenSource _cts = new();
protected override async Task OnInitializedAsync() => _orders = await Data.GetOrdersAsync(_cts.Token);
public void Dispose() { _cts.Cancel(); _cts.Dispose(); }   // @implements IDisposable
```

## Correctness rules folded from the field (ui-rules seed §1–2)

Each rule below is a real defect class in data-driven Blazor apps:

- **Never index a route/descriptor dictionary directly** (`routes["read"]`). Use `TryGetValue` and fail with a **diagnosable** message — a missing key must not surface as a bare `KeyNotFoundException` that crashes the page.

  ```csharp
  if (!routes.TryGetValue("read", out var template))
      throw new InvalidOperationException($"Descriptor '{name}' has no 'read' route. Known: {string.Join(", ", routes.Keys)}.");
  ```

- **URL-template building must throw on any unsubstituted `{placeholder}`.** Copy-pasted substitution (`template.Replace("{id}", id)` against a template that actually uses `{accountId}`) silently ships a literal `{accountId}` to the server = guaranteed 404. Substitute by name, then assert none remain:

  ```csharp
  var url = SubstituteAll(template, args);
  if (Regex.IsMatch(url, @"\{[^}]+\}"))
      throw new InvalidOperationException($"Unsubstituted placeholder in '{url}'.");
  ```

  Lookup/dropdown endpoints that take route params must substitute them from form context — a service that calls the parameterized URL verbatim and swallows the 404 yields **silently empty dropdowns**, the worst failure because nothing *looks* broken.

- **Match the deserialization type to the endpoint's actual shape.** Deserializing a **single-object** endpoint into `T[]` + `FirstOrDefault()` yields `null` and a **blank section**, not an error. `GetFromJsonAsync<OrderDto>` for one order; `GetFromJsonAsync<List<OrderDto>>` for a list. A `GET /{id}` returning one object is a **read**, not a **list** — don't array-wrap it.

- **Contract-test the UI's DTOs and routes against the API spec** (OpenAPI). Script-verify every route, DTO name, and field the UI binds — drift between a generated client and the spec is caught mechanically, in CI, not by a user staring at a blank pane. Hand off to `qa/dotnet/skills/api-contract-testing` (peer).

## ProblemDetails → UI error mapping

**Never render a raw response body or `ex.Message` to the user** — bodies may be JSON or stack traces. Route every call through one invoker that reads RFC-7807 `ProblemDetails`, surfaces the `title`/`detail` as a friendly message (or a generic message + correlation id for unknowns), and logs the raw detail server-side:

```csharp
public async Task<Result<T>> SendAsync<T>(Func<Task<HttpResponseMessage>> call)
{
    var res = await call();
    if (res.IsSuccessStatusCode)
        return Result<T>.Ok(await res.Content.ReadFromJsonAsync<T>() ?? throw new(...));

    var problem = await res.Content.ReadFromJsonAsync<ProblemDetails>();   // may be null on non-PD errors
    var correlationId = res.Headers.TryGetValues("X-Correlation-Id", out var v) ? v.First() : null;
    _logger.LogWarning("API {Status} on {Path}: {Detail}", (int)res.StatusCode, res.RequestMessage?.RequestUri, problem?.Detail);
    return Result<T>.Fail(problem?.Title ?? "Something went wrong.", correlationId);
}
```

The **three-state region** that renders this failure inline (with retry) is [`error-handling`](../error-handling/SKILL.md)'s job — this skill produces the categorized `Result`; that skill renders it.

## Rules

- **Open every data feature with the transport routing decision** (above): pull → here; push → [`realtime`](../realtime/SKILL.md).
- **One render-mode-agnostic interface**; server-direct and `HttpClient` implementations registered per project. The component depends only on the interface.
- **`IDbContextFactory`, never a captured/injected `DbContext`** in the server lane (circuit scope outlives a request).
- **No HTTP hop to your own API from the server lane** — call the service in-process.
- **`[PersistentState]`** (net10) / `PersistentComponentState` (net8/9) on every prerendered fetch; `??=` guard.
- **`[StreamRendering]`** for slow static-SSR paths; **`HybridCache`** (net9+) on the server implementation for slow reads.
- **Thread a `CancellationToken`** from the component through the client/EF Core; cancel on dispose.
- **`TryGetValue` + diagnosable message; throw on unsubstituted `{placeholder}`; deserialize to the endpoint's real shape; contract-test against the spec.**
- **ProblemDetails mapped to friendly text + correlation id; raw detail logged server-side, never rendered.**
- **Base addresses + external hosts from configuration**; the **IdP-agnostic** token handler comes from the auth skill (Auth0 *or* Cognito).

## What NOT to do

- No render-mode-specific data code inside the component; no `@rendermode` deciding a fetch path — inject the interface.
- No injected/captured `DbContext`; no `.Result`/`.Wait()` on the data calls (async all the way — global rule).
- No double-fetch left unguarded on prerender.
- No raw `ex.Message`/response body rendered to users; no failure swallowed into a blank section (that's a three-state region, [`error-handling`](../error-handling/SKILL.md)).
- No direct dictionary indexing of routes; no template sent with an unsubstituted placeholder; no single-object endpoint deserialized as an array.
- No hardcoded/`localhost` base URLs; no token-attaching handler hand-rolled here (it's auth's, provider-neutral).
- No net10-only API (`[PersistentState]`, `HybridCache` net9+) emitted into a lower TFM.

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- `dotnet build` — 0 warnings.
- Prerender smoke: DevTools **Network** shows **one** fetch, not two, on an Auto/prerendered page.
- Server lane: no `DbContext` lives longer than one operation (no injected context in any component/circuit service).
- Kill a slow request by navigating away → the fetch cancels (no post-dispose exception).
- Contract test green against the OpenAPI spec.

## Handoffs

- Live/push updates after first paint → [`realtime`](../realtime/SKILL.md) (shares this routing matrix)
- Render the failed/loading states, retry UX → [`error-handling`](../error-handling/SKILL.md)
- Where fetched state lives → [`state-management`](../state-management/SKILL.md)
- Forms/submit → [`forms`](../forms/SKILL.md)
- Token handler (Auth0 / Cognito) → `auth/auth0-blazor` · `auth/cognito-blazor`
- DTOs + contract tests → `qa/dotnet/skills/{api-models,api-contract-testing}` (peers)
