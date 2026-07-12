---
name: fe-blazor-reference
description: Use when the user asks to explain a Blazor pattern (.NET 8/9/10 — Static SSR / Server / WASM / Interactive Auto) — component lifecycle, render modes, state containers, `[PersistentState]` / PersistentComponentState, parameter cascading, JS interop, EventCallback vs Action, CascadingValue, and the component-architecture / atomic-design taxonomy (atom/molecule/organism naming, prop-drilling limits, when a component should own state). Triggers: "what's the right Blazor state container pattern", "when to use `RenderMode` X", "EventCallback vs Action", "CascadingValue vs DI", "what does [PersistentState] do", "atom or organism / how should I layer components", "how deep is too deep to prop-drill", "should this component own its state". Do NOT use for scaffolding (use `frontend/blazor/skills/generator`), reviewing (use `frontend/blazor/skills/reviewer`), where component files go on disk (use `frontend/blazor/skills/project-scaffold`), or non-Blazor .NET patterns (use the `backend/dotnet` dev stack's reference, if installed).
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

## When to use

- "What's the right state pattern for X in Blazor?"
- "When should I use `@rendermode InteractiveServer` vs `InteractiveAuto`?"
- "How do I share state without coupling components?"
- Comparing two Blazor approaches conceptually

## When NOT to use

- Scaffolding → `frontend/blazor/skills/generator`
- Reviewing → `frontend/blazor/skills/reviewer`
- Plain .NET back-end patterns → the `backend/dotnet` dev stack's reference, if installed
- React → `frontend/react/skills/reference`
- Auth0 in Blazor → `auth/auth0-blazor`

---

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

The atomic-design vocabulary (**atom → molecule → organism → template → page**) is the conceptual reasoning behind Blazor component structure. [`project-scaffold`](../project-scaffold/SKILL.md) owns the **placement heuristic** — which reuse level lives in shared `Components/` vs a feature folder, and the "promote on the second reuse" rule. Read its layering table for *where files go*; this section is *why the levels differ* and the design rules for each. Don't build a global `Atoms/`/`Molecules/` folder tree — the taxonomy is a placement heuristic, not a directory structure ([`project-scaffold`](../project-scaffold/SKILL.md) says so and shows the folder layout).

### The levels, and what changes as you go up

| Level | Domain awareness | Owns state? | Data reach | Render mode |
|---|---|---|---|---|
| **Atom** | None | No — fully controlled | None | Agnostic (runs anywhere) |
| **Molecule** | None (generic) | **Only ephemeral UI state** (see below) | None | Agnostic |
| **Organism** | Yes — knows a model slice | Local view state OK; domain state via injection/params | Via an injected [`data-access`](../data-access/SKILL.md) interface or parameters | Agnostic |
| **Template** | None (layout only) | No | None | Usually Static |
| **Page** | Yes — orchestrates | Owns the fetch + page-level state | Owns the data fetch | **Sets** the render mode at `@page` |

The through-line: **domain knowledge and data ownership climb as you go up; render-mode-agnosticism holds until the page.** An atom that injects a data service or names a domain type has skipped two levels — it's a mislabeled organism and won't be reusable.

### Naming

- **Atom/molecule names describe the control, not the domain**: `InputCurrency`, `SearchBox`, `Pagination`, `Badge` — never `OrderSearchBox` (that domain-coupling makes it a one-use organism).
- **Organism names name the domain concept**: `OrderTable`, `CustomerCard`, `CheckoutSummary`.
- **Page names match the route/capability**; templates name the arrangement (`TwoPaneLayout`, `MainLayout`).
- One name → one concept across the app (the IA rule [`ui-conventions`](../ui-conventions/SKILL.md) enforces app-wide).

### Prop-drilling limits — when to stop passing parameters down

Passing a value through 1–2 layers is fine. Past that, or when many siblings need it, the parameter chain is a smell:

| Depth / shape | Use |
|---|---|
| 1–2 levels, one value | `[Parameter]` passing (plain, explicit, testable) |
| Deep subtree, cross-cutting (theme, current user, edit context) | `CascadingValue` / `[CascadingParameter]` (Blazor's Context) with `IsFixed` when static |
| Shared across routes / unrelated subtrees | A **scoped service** (state container below) — not cascading, not drilling |
| A callback drilled 3+ levels to bubble an event | Reconsider structure, or a scoped service raising an event; never `Action` params (use `EventCallback`) |

Rule of thumb: **drill parameters, cascade cross-cutting context, service-inject shared state.** If you're drilling the same value past three organisms, promote it to a cascade or a service. If you're drilling a *callback* up through layers, the event probably belongs on a scoped state container that the interested components subscribe to directly.

### When a molecule (or any component) owns state

Default: components are **controlled** — value in via `[Parameter]`, changes out via `EventCallback`. A component may own state only when the state is **ephemeral and purely presentational** and would be noise to hoist:

- ✅ **Own it:** a dropdown's open/closed flag, a "show password" toggle, hover/focus visual state, an accordion's expanded section, an in-progress (not-yet-submitted) inline edit buffer. None of this outlives the component or matters to anyone else.
- ❌ **Don't own it — lift it (or put it in a container):** the selected value of a picker (the parent needs it), form field values that must round-trip to a submit ([`forms`](../forms/SKILL.md) owns the `EditContext`), anything two components must agree on, anything that must survive navigation or prerender (`[PersistentState]`), any domain data (that's [`data-access`](../data-access/SKILL.md)/[`state-management`](../state-management/SKILL.md)).

Test: *if another component or the server needs to know this value, it isn't the molecule's to own.* Ephemeral UI toggles stay local; everything else lifts to a parameter, a cascade, or a scoped service.

### Composition over configuration

Prefer composing small components (pass `RenderFragment` slots) over one component with 20 `[Parameter]`s and mode flags. A `Card` with `Header`/`Body`/`Footer` `RenderFragment`s beats a `Card` with `ShowHeader`/`HeaderText`/`ShowFooter`/... booleans — the global "composition over inheritance/configuration" rule, applied to the render tree. This is also what keeps atoms/molecules domain-free: they expose slots, the organism fills them with domain content.

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

## Handoffs

- Scaffolding Blazor components / patterns → `frontend/blazor/skills/generator`
- Reviewing Blazor code → `frontend/blazor/skills/reviewer`
- Non-Blazor .NET patterns → the `backend/dotnet` dev stack's reference, if installed
- Auth0 wiring in Blazor → `auth/auth0-blazor`
