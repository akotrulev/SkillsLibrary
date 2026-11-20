---
name: concepts
description: Use when explaining how Blazor works (render modes, lifecycle, state containers, PersistentState, cascading). Triggers "when to use RenderMode X". Not for scaffolding (component-writer).
disable-model-invocation: true
---

# Blazor Design Patterns — Reference

Conceptual reference for design patterns in Blazor on .NET 8, 9, and 10 — Static SSR, Server, WebAssembly, and Interactive Auto. Covers component composition, render-mode trade-offs, state containers, parameter cascading, JS interop, and the "wait, am I a SignalR connection or a SPA right now?" surprises that come with Interactive Auto.

## Version applicability

.NET 10 idioms are the primary recipes; .NET 8/9 equivalents are kept as explicitly tagged fallbacks — a `net8/net9` pattern is not obsolete, it's the correct pattern for that TFM. Key guidance to the project's `TargetFramework`.

| Concern | net10 (primary) | net8 / net9 (fallback) |
|---|---|---|
| Prerender state hand-off | `[PersistentState]` attribute on a property | Manual `PersistentComponentState` register/take/dispose |
| 404 handling | `NotFoundPage` on `<Router>` + `NavigationManager.NotFound()` | `<NotFound>` router template / manual redirect |
| Navigation | Enhanced navigation on by default; `NavLink` ignores query strings + fragments by default | Enhanced nav per-element opt-in; `NavLink` matches the full URI |
| Nested form validation | `AddValidation()` + `[ValidatableType]` | FluentValidation (house default on all TFMs) |
| Reconnect UX | Template `ReconnectModal` component; `Blazor.pauseCircuit()` / `resumeCircuit()` | Hand-rolled `components-reconnect-modal` markup + CSS state classes |
| Diagnostics | Built-in OTel meters (`Microsoft.AspNetCore.Components`, `.Lifecycle`, `.Server.Circuits`) | Custom `ActivitySource` / `Meter` instrumentation |

## Render modes (.NET 8+)

Since .NET 8, components render Static (server-rendered HTML, no interactivity), Interactive Server (SignalR-backed), Interactive WebAssembly (downloaded to the browser), or **Interactive Auto** (Server first, then transparently swap to WASM once the runtime downloads).

| Mode | Where the C# runs | When |
|---|---|---|
| **Static (SSR)** | Server, once | Content pages, marketing, anything not needing event handlers |
| **InteractiveServer** | Server over SignalR | Interactive UI, low-latency network, secrets stay server-side, small payload |
| **InteractiveWebAssembly** | Browser | Offline-capable, no server round-trip on interaction, but downloads the runtime |
| **InteractiveAuto** | Server first, then WASM | Best of both: instant interactivity (Server) and offline-capable (WASM) once downloaded |

Rules:
- **Static SSR is the default; interactivity is opt-in per component** ("islands"). The render-mode decision is per surface, not per app.
- Components stay **render-mode-agnostic** — the consumer sets `@rendermode` at the top; a component never hardcodes its own render mode, so the same component runs under Server, WASM, or Auto.
- Auto has a real cost: data access must be abstracted behind an interface with a server-direct and an HTTP implementation. Pay it deliberately, not by default.
- Live/push-heavy surfaces favor Interactive Server (the circuit is already a WebSocket); API-consuming surfaces favor WASM or static SSR.
- **Interactive Server holds a SignalR circuit per user**, so it suits internal tools with modest concurrency. Public traffic takes InteractiveWebAssembly or InteractiveAuto.
- Which mode a route gets is a planning decision: the plan's `rendering_plan`, mapped to these modes by [`rendering-strategy.md`](../../../../backend/_shared/experience-plan/references/rendering-strategy.md).

## Component composition

Blazor's component model is closer to React's than to ASP.NET MVC's. Patterns map:

- **Props** = `[Parameter]`
- **Two-way binding** = `@bind-Value` (sugar for `Value` + `ValueChanged` EventCallback)
- **Children** = `[Parameter] public RenderFragment? ChildContent { get; set; }`
- **Compound components** = parent state held in the parent component, children read via `[CascadingParameter]`

### Component contract: `EventCallback` vs `Action`

| Use | When |
|---|---|
| **`EventCallback` / `EventCallback<T>`** | Always for component-to-parent events. Awaitable, triggers re-render of the parent automatically. |
| **`Action` / `Action<T>`** | Never as a `[Parameter]` for events. Bypasses the auto-render. |
| **`Func<T, Task>`** | Rarely; use EventCallback instead. |

EventCallback is to Blazor what `onChange` is to React — non-negotiable for event props.

### CascadingValue / CascadingParameter

The Blazor equivalent of React Context. One parent provides; descendants consume.

```razor
<CascadingValue Value="@theme" Name="Theme">
    <App />
</CascadingValue>

@code {
    private Theme theme = new Theme(...);
}
```

```razor
@code {
    [CascadingParameter(Name = "Theme")] public Theme? Theme { get; set; }
}
```

Rules:
- Don't cascade unbounded objects (a "page model" with 30 fields) — split by concern
- Use `IsFixed = true` when the cascaded value never changes — avoids unnecessary re-renders
- For app-wide state (user, theme, feature flags), one cascading parameter per concern beats one fat one

## Component architecture — the layering taxonomy

A new component, a decision about where its state or data lives, or a parameter chain growing past two layers → read [`references/component-layering.md`](references/component-layering.md): the levels (atom → page) and what each may own, naming, prop-drilling limits, when a molecule owns state, composition over configuration.

## State containers

For state shared across multiple components on different routes, three viable patterns:

| Pattern | Scope | Use when |
|---|---|---|
| **Service registered in DI** | Singleton / Scoped / Transient | Most cases. State is just a class injected into components. |
| **CascadingValue** | Render-tree scope | Theme, current user, feature flags |
| **Fluxor / Blazor-State / Stargazer.Blazor.StateManagement** | Whole app | Redux-style global store; rarely the right answer |

The default — **a scoped service** (`AddScoped<CartState>()` in Server, `AddScoped<CartState>()` in WASM) — covers most needs. The service raises an event on change; components subscribe in `OnInitialized`, unsubscribe in `Dispose`.

```csharp
public class CartState
{
    private readonly List<CartItem> _items = new();
    public IReadOnlyList<CartItem> Items => _items;
    public event Action? Changed;
    public void Add(CartItem item) { _items.Add(item); Changed?.Invoke(); }
    public void Remove(string id) { _items.RemoveAll(i => i.Id == id); Changed?.Invoke(); }
}
```

```razor
@implements IDisposable
@inject CartState Cart

<p>@Cart.Items.Count items</p>

@code {
    protected override void OnInitialized() => Cart.Changed += StateHasChanged;
    public void Dispose() => Cart.Changed -= StateHasChanged;
}
```

Avoid Fluxor unless you've adopted Redux conventions intentionally — it's overkill for most Blazor apps.

## Lifecycle

`SetParametersAsync` → `OnInitialized` / `OnInitializedAsync` → `OnParametersSet` / `OnParametersSetAsync` → `ShouldRender` → render → `OnAfterRender` / `OnAfterRenderAsync(firstRender)`

Rules:
- Async data loads in `OnInitializedAsync` — but in InteractiveServer, this runs **twice** (prerender + interactive connection). Use `[PersistentState]` (net10) or the `PersistentComponentState` API (net8/net9) to avoid duplicate fetches.
- DOM-touching JS interop in `OnAfterRenderAsync(firstRender: true)` — earlier and the DOM isn't ready
- Don't override `ShouldRender` without measurement; auto-rerender is almost always correct
- `IDisposable` / `IAsyncDisposable` is mandatory when subscribing to events or timers

## JS interop

`IJSRuntime.InvokeAsync<T>("name", args)` calls JS from C#. The reverse direction uses `[JSInvokable]` on a static method or via a `DotNetObjectReference<T>`.

Rules:
- Use ES modules: `await js.InvokeAsync<IJSObjectReference>("import", "./Components/Map.razor.js")` so each component's JS lives next to the .razor file
- **net10:** call JS constructors (`InvokeNewAsync`) and get/set JS object properties (`GetValueAsync` / `SetValueAsync`) directly from C# — no wrapper JS functions needed for simple object construction/property access. net8/net9 fallback: a small exported wrapper function in the collocated module.
- Dispose `IJSObjectReference` / `DotNetObjectReference` in `IAsyncDisposable.DisposeAsync`
- Don't `InvokeAsync` from a server-prerender path — the JS runtime isn't there yet; gate with `OnAfterRenderAsync`
- Keep payloads small; large object marshalling is expensive

## Pre-rendering & state persistence

Server prerender produces HTML; the interactive connection takes over and re-runs `OnInitializedAsync` — bad UX (loading spinners + flashes).

### `[PersistentState]` (net10 — primary)

One attribute replaces the manual register/take/dispose dance. The framework persists the property on prerender and restores it on the interactive run:

```razor
@page "/orders"
@inject HttpClient Http

@code {
    [PersistentState]
    public List<Order>? Orders { get; set; }

    protected override async Task OnInitializedAsync()
    {
        Orders ??= await Http.GetFromJsonAsync<List<Order>>("/api/orders");
    }
}
```

net10 also supports state persistence across **circuit eviction** (a paused/evicted circuit's declared state survives and restores on resume), with `HybridCache` as the distributed backing store on scale-out.

### `PersistentComponentState` (net8 / net9 — fallback)

The manual API, still correct on down-level TFMs:

```csharp
@implements IDisposable
@inject PersistentComponentState ApplicationState

@code {
    private PersistingComponentStateSubscription _sub;
    private List<Order>? _orders;

    protected override async Task OnInitializedAsync()
    {
        if (!ApplicationState.TryTakeFromJson<List<Order>>("orders", out _orders))
        {
            _orders = await Http.GetFromJsonAsync<List<Order>>("/api/orders");
        }
        _sub = ApplicationState.RegisterOnPersisting(() =>
        {
            ApplicationState.PersistAsJson("orders", _orders);
            return Task.CompletedTask;
        });
    }

    public void Dispose() => _sub.Dispose();
}
```

Prerender persists, interactive run rehydrates — no double fetch.

## Navigation & 404s

- **Enhanced navigation is on by default (net10):** same-app link clicks and form posts are intercepted and patched into the DOM without a full reload, even on static SSR. On net8/net9 the behavior exists but with per-element opt-outs (`data-enhance-nav="false"`) doing more work.
- **`NavLink` ignores query strings and fragments by default (net10)** when matching — a net8/net9 `NavLink` that relied on query-string matching needs review on upgrade.
- **404s (net10):** declare `NotFoundPage` on the `<Router>` in `Routes.razor` and trigger programmatically with `NavigationManager.NotFound()` — works under streaming rendering and enhanced nav. **net8/net9 fallback:** the `<NotFound>` router template section.
- In-app navigation renders as a **real anchor** (`<a href>`), never a click-handler-only button calling `NavigateTo` — real anchors get enhanced nav, middle-click, and crawlability for free.

## Reconnection UX (Blazor Server)

- **net10:** the Blazor Web App template ships a customizable `ReconnectModal` component (with its own `.razor.js`/`.css`) — edit it instead of hand-rolling overlay divs. `Blazor.pauseCircuit()` / `Blazor.resumeCircuit()` let you pause a circuit on tab hide and resume on return, pairing with circuit-eviction state persistence.
- **net8/net9 fallback:** style the `components-reconnect-modal` element and its state CSS classes by hand.

## Diagnostics (net10)

Three built-in OTel meter/activity sources: `Microsoft.AspNetCore.Components`, `Microsoft.AspNetCore.Components.Lifecycle`, and `Microsoft.AspNetCore.Components.Server.Circuits` (circuit count, duration, lifecycle events). Subscribe to them in the OpenTelemetry pipeline — no custom instrumentation needed for component/circuit basics. On net8/net9, instrument with your own `ActivitySource`/`Meter`.

## Form handling

`<EditForm>` + `DataAnnotationsValidator` + `ValidationSummary` is the standard. `<EditForm Model="@m" OnValidSubmit="HandleValid">`. On net10, `AddValidation()` + `[ValidatableType]` extend DataAnnotations to nested objects and collections, and class-level `ValidationAttribute`s cover cross-field rules. The house default for non-trivial validation remains **FluentValidation** on all TFMs — details in `frontend/blazor/skills/forms`.

Two-way binding: `@bind-Value` on `InputText`/`InputNumber`/`InputCheckbox` — these are wrappers around the cascading `EditContext`.

## Authentication & authorization

`<AuthorizeView>` and `[Authorize]` attributes work in Blazor — wired to `AuthenticationStateProvider`. Detailed wiring → `auth/auth0-blazor`.

## Common gotchas

- **Static prerender + InteractiveServer** runs `OnInitializedAsync` twice — use `[PersistentState]` (net10) / `PersistentComponentState` (net8/net9)
- **InteractiveAuto** runs once on Server, then again on WASM — the same trap
- **Capturing `this` in event handlers** across renders — Blazor handles it, but the `[Parameter]` reference equality semantics still bite (use `EventCallback`, not `Action`)
- **Forgetting `@implements IDisposable`** when subscribing to a state container — memory leak per page navigation
- **JS interop in prerender path** — `InvalidOperationException` because there's no JS runtime
- **`@bind` without `@bind:event="oninput"`** — updates only on `change` (blur), which surprises users used to React

## Comparison: Blazor vs React

| Concept | Blazor | React |
|---|---|---|
| Component | `.razor` file | `.tsx` function |
| Props | `[Parameter]` | function parameters |
| State | service / `CascadingValue` / `[Parameter]` | `useState` / context / Zustand |
| Event prop | `EventCallback<T>` | `(t: T) => void` |
| Side effect | `OnInitializedAsync` / `OnAfterRenderAsync` | `useEffect` |
| Memo | `ShouldRender` | `React.memo` / `useMemo` |
| Context | `CascadingValue` / `CascadingParameter` | `React.createContext` + provider/hook |
