---
name: fe-blazor-performance
description: Use when a Blazor app (.NET 8/9/10) is slow or you want to keep it fast — render performance (`@key`, `ShouldRender`, `Virtualize`, parameter-churn, `CascadingValue IsFixed`), WASM startup (trimming, lazy loading, the AOT decision, Brotli/CDN, net10 asset fingerprinting + `<LinkPreload>`), interactive-Server scale (circuit memory, SignalR, Azure SignalR), diagnostics via the net10 component OTel meters, and explicit budgets. Triggers: "my grid re-renders too much", "the WASM app takes forever to load", "should I AOT-compile", "how many circuits can one server hold", "add a Virtualize", "set performance budgets". Do NOT use for CSS/asset styling (use `frontend/blazor/skills/styling`), SignalR live-data *functionality* (use `frontend/blazor/skills/realtime`), server-side DB query tuning (use `data/*`), or load-testing the app (use `qa/dotnet/skills/performance/nbomber`, a peer).
---

# Blazor — Performance

Owns making a Blazor app fast and keeping it fast across three cost centers that behave differently per render mode: **render throughput** (how often and how cheaply components re-render), **WASM startup** (download + init before first interactivity), and **interactive-Server scale** (circuit memory + SignalR under concurrent users). Plus the **diagnostics** to measure them and the **budgets** to hold the line.

**Version rule:** detect the `TargetFramework` first. `@key`/`ShouldRender`/`Virtualize`/`CascadingValue IsFixed` and lazy-loading behave the same across net8/net9/net10. The **net10** deltas are asset-side: fingerprinted + precompressed `blazor.web.js` (~76% smaller), WASM asset fingerprinting (`<OverrideHtmlAssetPlaceholders>`), `<LinkPreload>`, and the three component OTel meters. Never emit a net10-only knob into a down-level project — the down-level equivalents are tagged below.

## When to use

- A component re-renders more than it should; a parent update repaints a whole subtree
- A list/grid renders thousands of rows; scrolling janks
- The WASM app's first paint / first interactivity is slow
- Deciding trimming / lazy-loading / AOT for WASM
- Interactive Server memory grows with users; sizing circuits
- Wiring perf diagnostics (OTel meters) and setting budgets

## When NOT to use

- Writing the CSS / bundling static assets → [`styling`](../styling/SKILL.md) (its static-asset note points *here* for the perf side)
- SignalR as a *feature* (live push, hubs, streams) → [`realtime`](../realtime/SKILL.md); this skill owns SignalR only as a *scale* concern
- Server-side query/DB tuning → `data/*`, the `backend/dotnet` dev stack's persistence skill if installed
- Caching read-heavy fetches (`HybridCache`) → [`data-access`](../data-access/SKILL.md)
- Load/stress/soak testing the deployed app → `qa/dotnet/skills/performance/nbomber` (peer)

## Cost-center routing — where is my slowness?

```
Is first paint / first interactivity slow, and it's a WASM/Auto app?
  YES → WASM startup      → §"WASM startup"
Is the app interactive but a specific interaction / scroll janks?
  YES → render throughput → §"Render performance"
Is memory/CPU on the server climbing with concurrent users (interactive Server)?
  YES → Server scale      → §"Interactive-Server scale"
Don't know which?      → wire the diagnostics first → §"Diagnostics"
```

| Symptom | Cost center | Section |
|---|---|---|
| "Blank screen for seconds, then it works" (WASM) | download + init | WASM startup |
| "Clicking a row re-renders the whole page" | render throughput | Render performance |
| "10k-row grid freezes the tab" | render throughput | Render performance (`Virtualize`) |
| "Server RAM climbs ~250 KB/user, OOMs at N users" | circuit memory | Interactive-Server scale |
| "Fine locally, slow on the deployed CDN" | asset delivery | WASM startup (Brotli/fingerprint) |

---

## Render performance

Blazor re-renders a component when: its `[Parameter]` values change (by reference for objects), a `StateHasChanged` fires, or an `EventCallback` it owns runs. The cost is the **diff**, not the paint — a cheap component rendered 1000×/sec still burns CPU. Four levers:

### `@key` — stable identity in lists

Give every item in a rendered loop a stable `@key` so the diff matches old→new by identity, not by position. Without it, inserting/reordering rows makes Blazor tear down and rebuild every subsequent element (and lose focus/state):

```razor
@foreach (var row in Rows)
{
    <OrderRow @key="row.Id" Order="row" />   @* key on the STABLE domain id, never the loop index *@
}
```

`@key` on the loop **index** is worse than none — it defeats the match on exactly the reorder case it's meant to help. Key on the entity id.

### `ShouldRender` — veto needless re-renders

Override `ShouldRender` on a hot component to skip the diff when nothing it displays changed. Pairs with cached-parameter comparison:

```csharp
private OrderDto? _last;
protected override bool ShouldRender()
{
    if (ReferenceEquals(_last, Order)) return false;   // parent re-rendered but our data is identical
    _last = Order;
    return true;
}
```

Use sparingly and only on measured hot paths — a wrong `ShouldRender` that returns `false` too aggressively drops real updates. Measure before and after.

### `Virtualize` — render only what's visible

For any list past ~100 rows, `<Virtualize>` renders only the rows in (and near) the viewport, not the whole set:

```razor
<Virtualize Items="Orders" Context="o" OverscanCount="3">
    <OrderRow @key="o.Id" Order="o" />
</Virtualize>
```

For large/remote datasets use the **`ItemsProvider`** overload so you fetch a window per scroll instead of loading everything client-side (pairs with server-side paging — [`ui-conventions`](../ui-conventions/SKILL.md) table ergonomics). Set `ItemSize` to the real row height to avoid scroll-jump.

### Parameter churn & `CascadingValue IsFixed`

- **Don't allocate a new reference every render** for an object/collection/lambda parameter — a fresh `new[]{…}` or inline `() =>` each render looks "changed" and re-renders the child every time. Hoist it to a field, or memoize.
- **`<CascadingValue IsFixed="true">`** when the cascaded value never changes (a service, a fixed config). Without `IsFixed`, every consumer subscribes to change notifications and re-renders on any cascade update — `IsFixed` drops the subscription entirely. Default it to `true` for anything immutable.

### Render anti-patterns

| Anti-pattern | Cost | Fix |
|---|---|---|
| `@key="i"` (loop index) or no key on a mutable list | full teardown on reorder/insert | `@key` on the entity id |
| New object/lambda param allocated each render | child re-renders every parent render | hoist to a field / memoize |
| `CascadingValue` without `IsFixed` for an immutable value | every consumer re-renders on any change | `IsFixed="true"` |
| `StateHasChanged()` in a tight loop / per stream item | render storm | batch; render on a throttled tick |
| Heavy work in `OnParametersSet`/`BuildRenderTree` | runs every render | move to `OnInitialized`/`OnParametersSetAsync` guarded by change |
| A 10k-row `@foreach` | whole set diffed each render | `<Virtualize>` |
| `async void` event handler | unobserved exceptions, no re-render await | `async Task` |

---

## WASM startup

The WASM cost is **before** first interactivity: download the runtime + your assemblies, init the runtime, load. Levers, in order of leverage:

### 1. Trimming (on by default in Release)

The linker strips unused IL. Keep it on; guard reflection-used types with `[DynamicDependency]` or a trimmer roots file, and test the **published** app (trimming only runs on publish) — a reflection path that works in Debug can NRE trimmed.

### 2. Lazy-load assemblies not needed at startup

Defer feature assemblies until their route is hit, so they're off the startup critical path:

```xml
<ItemGroup>
  <BlazorWebAssemblyLazyLoad Include="Reporting.dll" />
</ItemGroup>
```

```csharp
// Router: load the assembly on navigation to its area
protected override async Task OnNavigateAsync(NavigationContext ctx)
{
    if (ctx.Path.StartsWith("reporting"))
        _lazy = await AssemblyLoader.LoadAssembliesAsync(["Reporting.dll"]);
}
```

Best for large, rarely-visited areas (admin, reporting, charts).

### 3. The AOT decision (weigh it — don't default to yes)

| | IL (default) | AOT (`RunAOTCompilation`) |
|---|---|---|
| Download size | smaller | **2–3× larger** (native WASM) |
| CPU-bound runtime speed | baseline | up to ~2× faster |
| Startup | faster (less to download) | slower (more to download) |
| Build time | seconds | **minutes** |

**Default: no AOT.** AOT trades a bigger download (worse startup — the usual complaint) for faster steady-state CPU. Only choose it for genuinely **CPU-bound** WASM (client-side crypto, image processing, sims) where compute dominates and the larger download is acceptable. For typical CRUD/data UIs, IL + trimming + Brotli beats AOT on the metric users feel. Consider **partial AOT** (hot assemblies only) before whole-app.

### 4. Compression + CDN + fingerprinting

- **Brotli** the published `_framework` assets; serve with `Content-Encoding: br` (the .NET host does this; a CDN/reverse proxy must be configured to, and to send the right `Cache-Control`).
- Serve `_framework/*` from a **CDN** with long-lived immutable caching — the filenames are content-hashed, so cache-bust is free.
- **net10:** `blazor.web.js` ships fingerprinted + precompressed (~76% smaller) and WASM assets fingerprint via `<OverrideHtmlAssetPlaceholders>true</OverrideHtmlAssetPlaceholders>`; add **`<LinkPreload />`** in `<head>` to start fetching the runtime before the parser reaches the script. This is where [`styling`](../styling/SKILL.md)'s static-asset note points.
  - net8/net9 fallback: manual `<link rel="preload">` for the key `_framework` assets; content-hash query strings via the publish pipeline.

### 5. Prerender the shell

Prerender (static SSR) the first paint so the user sees content while WASM downloads — pair with `[PersistentState]` so the interactive run doesn't refetch ([`data-access`](../data-access/SKILL.md)). Prerender improves *perceived* startup, not actual download.

---

## Interactive-Server scale

Interactive Server holds a **circuit** (server-side component state + a SignalR connection) per connected user. Memory and SignalR are the ceilings:

- **Circuit memory** is roughly the component tree + captured state per user. Keep component state lean; **`IDisposable`/`IAsyncDisposable`** everything that holds resources (see [`realtime`](../realtime/SKILL.md), [`error-resilience`](../error-resilience/SKILL.md)) — a leaked subscription or `DbContext` (never inject one — [`data-access`](../data-access/SKILL.md)) multiplies by user count.
- **`DisconnectedCircuitMaxRetained`** / retention timeout bound how many evicted circuits stay in memory for reconnection — lower them under memory pressure.
- **SignalR scale-out needs sticky sessions** (a circuit is stateful, pinned to one server) and a backplane: **Azure SignalR Service** (offloads connections from your app servers — the default at scale) or a **Redis backplane**. Without one, a load-balanced deployment drops circuits on the wrong node.
- **Right-size before scaling out:** transfer size per interaction, render batch size, and `MaxBufferedUnacknowledgedRenderBatches` affect throughput. Measure circuits/CPU/RAM under real concurrency with `qa/dotnet/skills/performance/nbomber` (peer) before adding servers.

WASM has **no** server circuit — it scales like static files + your API. That's the trade against Server's zero-download interactivity.

---

## Diagnostics

Measure before optimizing. Wire the **net10 component OTel meters** into the observability stack (documented in [`reference`](../reference/SKILL.md)):

| Meter source | Watches |
|---|---|
| `Microsoft.AspNetCore.Components` | component render counts + durations |
| `Microsoft.AspNetCore.Components.Lifecycle` | lifecycle timing (init/parameters/render) |
| `Microsoft.AspNetCore.Components.Server.Circuits` | active/disconnected circuit counts (Server scale) |

```csharp
builder.Services.AddOpenTelemetry().WithMetrics(m => m
    .AddMeter("Microsoft.AspNetCore.Components",
              "Microsoft.AspNetCore.Components.Lifecycle",
              "Microsoft.AspNetCore.Components.Server.Circuits"));
```

Feed them into the Grafana stack (`observability/opentelemetry-dotnet` + `observability/grafana-dashboards`, external skills). net8/net9: no built-in component meters — use the **`<CascadingValue>`-free** render-count trick (`Interlocked.Increment` in `OnAfterRender`) on suspect components, browser DevTools **Performance**, and the WASM startup trace in the browser console.

**Client-side (both modes):** browser DevTools — **Network** (asset sizes, Brotli applied, one-not-two fetches on prerender), **Performance** (long tasks, layout thrash), Lighthouse for a startup score.

---

## Budgets

Set explicit budgets and fail CI when they regress — an unmeasured perf rule rots. Suggested starting budgets (tune per app):

| Metric | Budget (starting point) | Where enforced |
|---|---|---|
| WASM published `_framework` transfer (Brotli) | ≤ 2.5 MB initial, lazy-load the rest | build check on publish output size |
| First Contentful Paint (prerendered shell) | ≤ 1.5 s on mid-tier / throttled | Lighthouse CI |
| Time to Interactive (WASM) | ≤ 3.5 s on mid-tier / throttled | Lighthouse CI |
| Largest grid without `Virtualize` | ≤ 100 rows | `reviewer` rule |
| Circuit memory / active user (Server) | measured baseline; alert on +30% | OTel circuit meter + Grafana alert |
| Component render count on a key interaction | no unbounded growth per interaction | OTel component meter |

## Rules

- **`@key` on the entity id** in every rendered list; never the loop index.
- **`Virtualize`** past ~100 rows; `ItemsProvider` + server paging for large/remote sets.
- **`CascadingValue IsFixed="true"`** for anything immutable; never cascade a mutable value unfixed to a wide subtree.
- **No new object/lambda reference allocated per render** for a child parameter — hoist/memoize.
- **`ShouldRender` only on measured hot paths**, guarded by a real change comparison.
- **WASM: trimming on, lazy-load rarely-visited areas, Brotli + CDN + long-immutable cache**, prerender the shell, `[PersistentState]` to avoid the double-fetch.
- **AOT is opt-in for CPU-bound WASM only** — never a default (it worsens startup).
- **net10 asset knobs** (`<LinkPreload>`, WASM fingerprinting, precompressed `blazor.web.js`) on net10; tagged down-level fallbacks otherwise.
- **Interactive Server: dispose everything, sticky sessions + Azure SignalR/Redis backplane** for scale-out; bound retained disconnected circuits.
- **Wire the component OTel meters** (net10) and set **explicit budgets** enforced in CI.
- Measure first (diagnostics), optimize the proven hot path, measure again — never speculatively.

## What NOT to do

- No `@key="index"`; no unkeyed mutable lists.
- No un-virtualized large grids; no client-side load of an entire remote dataset.
- No `StateHasChanged()` per stream item / in a render loop (batch — [`realtime`](../realtime/SKILL.md)).
- No AOT "for speed" on a data/CRUD UI (bigger download, slower startup).
- No net10-only asset API emitted into a net8/net9 project.
- No injected/captured `DbContext` or leaked subscription inflating circuit memory ([`data-access`](../data-access/SKILL.md), [`realtime`](../realtime/SKILL.md)).
- No `async void` handlers; no heavy work in `OnParametersSet`/render.
- No "we optimized it" without a before/after measurement.

## Validation

- Published WASM `_framework` transfer size within budget; Brotli served (Network shows `content-encoding: br`).
- A key large grid uses `Virtualize`; scrolling stays smooth (no long tasks in DevTools Performance).
- Toggle `IsFixed`/`ShouldRender`/`@key` off→on and confirm the render-count meter drops on the target interaction.
- Under simulated concurrency (nbomber peer), circuit memory/CPU stay within the Server budget; no unbounded growth.
- Lighthouse FCP/TTI within budget on a throttled profile.

## Handoffs

- Static-asset bundling/serving mechanics → [`styling`](../styling/SKILL.md)
- SignalR as a live-data feature (not scale) → [`realtime`](../realtime/SKILL.md)
- Caching slow reads (`HybridCache`) → [`data-access`](../data-access/SKILL.md)
- Server-side query/DB tuning → `data/*`, the `backend/dotnet` dev stack's persistence skill if installed
- OTel meter export to Grafana → `observability/opentelemetry-dotnet`, `observability/grafana-dashboards`
- Load/stress/soak of the deployed app → `qa/dotnet/skills/performance/nbomber` (peer)
