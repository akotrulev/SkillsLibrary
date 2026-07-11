---
name: fe-blazor-generator
description: Use when the user asks to scaffold a Blazor pattern in .NET 8/9/10 — Static SSR / Server / WASM / Interactive Auto — into the active repo. Triggers: "scaffold a Blazor component for X", "create a state container for Y", "wire a CascadingValue", "convert this to an interactive component", "add a [PersistentState] fetch", "compound component for tabs in Blazor", "add a NotFound page", "customize the reconnect modal", "add an external link that opens in a new tab". Do NOT use for explanations (use `frontend/blazor/skills/reference`), reviews (use `frontend/blazor/skills/reviewer`), or non-Blazor patterns (use `design-patterns/dotnet/generator`).
---

# Blazor Design Patterns — Generator

Scaffolds Blazor components, services, and patterns into the active repo (.NET 8/9/10). Picks the right render mode per surface, uses `EventCallback` for events, scopes state via DI services, persists across the prerender boundary with `[PersistentState]` (net10) or `PersistentComponentState` (net8/net9), and disposes subscriptions cleanly.

**Version rule:** detect the project's `TargetFramework` first. net10 idioms are the primary recipes; every net8/net9 fallback is tagged. Never emit a net10-only API into a net8/net9 project.

## When to use

- New page / route component
- Reusable component (form input, table, dialog, compound widget)
- Scoped state container for shared UI state
- `CascadingValue` for app-wide concerns (theme, current user, feature flags)
- JS interop for a small browser-side capability
- Switching a static page to interactive

## When NOT to use

- Explanation → `frontend/blazor/skills/reference`
- Review → `frontend/blazor/skills/reviewer`
- Plain .NET backend patterns → `design-patterns/dotnet/generator`
- React → `design-patterns/react/generator`
- Auth0 in Blazor → `auth/auth0-blazor`

## Inputs needed

0. **TargetFramework** — net8.0 / net9.0 / net10.0 (drives which recipe variant is emitted)
1. **Hosting model** — Blazor Web App (Server, WASM, or both); static SSR is the default, interactivity opt-in per surface
2. **Render mode** for this surface — Static, InteractiveServer, InteractiveWebAssembly, InteractiveAuto — set by the **consumer** at the call site, never inside the component
3. **Component name** + responsibilities
4. **Inputs (parameters) + outputs (EventCallbacks)**
5. **Shared state needed** (none / cascading value / DI service)
6. **JS interop** required (Y/N + what)
7. **Prerender behavior** — does the component fetch data on init?

## Recipes

### Page component with prerender state persistence — `[PersistentState]` (net10, primary)

```razor
@page "/orders"
@inject HttpClient Http

<PageTitle>Orders</PageTitle>

@if (Orders is null)
{
    <p data-testid="Orders.Loading">Loading…</p>
}
else
{
    <ul data-testid="Orders.List">
        @foreach (var o in Orders)
        {
            <li>@o.Reference — @o.Status</li>
        }
    </ul>
}

@code {
    [PersistentState]
    public List<OrderDto>? Orders { get; set; }

    protected override async Task OnInitializedAsync()
    {
        Orders ??= await Http.GetFromJsonAsync<List<OrderDto>>("/api/orders");
    }
}
```

One attribute cures "InteractiveAuto fetches twice" — the prerender's fetch persists into the page, the interactive run rehydrates without a second HTTP call. No subscription, no dispose. The same declaration backs circuit pause/resume state persistence. Note: no `@rendermode` in the page — the consumer sets it.

### net8/net9 fallback — manual `PersistentComponentState`

```razor
@page "/orders"
@implements IDisposable
@inject HttpClient Http
@inject PersistentComponentState ApplicationState

@code {
    private PersistingComponentStateSubscription _persistingSubscription;
    private List<OrderDto>? _orders;

    protected override async Task OnInitializedAsync()
    {
        if (!ApplicationState.TryTakeFromJson<List<OrderDto>>("orders", out _orders))
        {
            _orders = await Http.GetFromJsonAsync<List<OrderDto>>("/api/orders");
        }

        _persistingSubscription = ApplicationState.RegisterOnPersisting(() =>
        {
            ApplicationState.PersistAsJson("orders", _orders);
            return Task.CompletedTask;
        });
    }

    public void Dispose() => _persistingSubscription.Dispose();
}
```

Same semantics, more ceremony — this is the correct pattern on net8/net9; do not backport `[PersistentState]`.

### NotFound page (net10)

`Routes.razor`:

```razor
<Router AppAssembly="@typeof(Program).Assembly"
        NotFoundPage="typeof(Pages.NotFound)">
    <Found Context="routeData">
        <RouteView RouteData="@routeData" DefaultLayout="@typeof(Layout.MainLayout)" />
        <FocusOnNavigate RouteData="@routeData" Selector="h1" />
    </Found>
</Router>
```

`Pages/NotFound.razor`:

```razor
@page "/not-found"
<PageTitle>Not found</PageTitle>
<h1>Page not found</h1>
<p>Sorry — there's nothing at this address. <a href="/">Go home</a>.</p>
```

Trigger programmatically with `NavigationManager.NotFound()` (e.g. entity lookup misses). The `<NotFound>` render-fragment section is **not supported on net10** — it is the net8/net9 fallback.

### Reconnect modal (net10, Blazor Server)

The Blazor Web App template ships `Components/Layout/ReconnectModal.razor` (+ collocated `.css`/`.js`) — customize that component rather than hand-rolling overlay markup; it handles the `components-reconnect-state-changed` event including the net10 `retrying` state. Pair with `Blazor.pauseCircuit()` on tab hide / `Blazor.resumeCircuit()` on return. net8/net9 fallback: style the `components-reconnect-modal` element and its state CSS classes.

### External link that opens in a new tab

Only for the deliberate exceptions (reference material used *while* on the current screen, a link that would destroy unsaved work, a PDF) — in-app navigation stays same-tab. When a new tab is warranted, emit the full accessible affordance, not a bare `target="_blank"`:

```razor
<a href="@href" target="_blank" rel="noopener"
   aria-label="@($"{label} (opens in new tab)")"
   data-testid="@ComposedTestId">
    @label
    <span class="external-icon" aria-hidden="true">↗</span>   @* visible cue; hidden from SR since the label already says it *@
</a>
```

`rel="noopener"` closes the reverse-`window.opener` hole; the visible icon warns sighted users; the `aria-label` suffix warns screen-reader users (the icon is `aria-hidden` so it isn't announced twice). Never open a new tab the user didn't ask for, and never for internal routes.

### Reusable input component with two-way binding

```razor
@* Components/InputCurrency.razor *@
<input type="number" min="0" step="0.01"
       value="@DisplayValue"
       @oninput="OnInput"
       data-testid="@ComposedTestId"
       class="form-input" />

@code {
    [Parameter] public string? TestId { get; set; }
    [Parameter] public long ValueMinor { get; set; }
    [Parameter] public EventCallback<long> ValueMinorChanged { get; set; }
    [Parameter] public string Currency { get; set; } = "EUR";

    private string ComposedTestId => $"{TestId ?? ""}.CurrencyField";

    private string DisplayValue => (ValueMinor / 100m).ToString("F2");

    private async Task OnInput(ChangeEventArgs e)
    {
        if (decimal.TryParse((string?)e.Value, out var d))
            await ValueMinorChanged.InvokeAsync((long)(d * 100));
    }
}
```

Consumer uses `@bind-ValueMinor="totalMinor"` (the suffix matches the `ValueMinor` + `ValueMinorChanged` pair).

### Compound component via Cascading

```razor
@* Components/Tabs.razor *@
<CascadingValue Value="this" IsFixed="true">
    <div role="tablist">
        @ChildContent
    </div>
</CascadingValue>

@code {
    [Parameter] public string DefaultValue { get; set; } = "";
    [Parameter] public RenderFragment? ChildContent { get; set; }

    private string _active = "";
    private string _baseId = Guid.NewGuid().ToString("N")[..8];

    protected override void OnInitialized()
    {
        _active = DefaultValue;
    }

    internal string Active => _active;
    internal string BaseId => _baseId;
    internal void Activate(string value)
    {
        _active = value;
        StateHasChanged();
    }
}
```

```razor
@* Components/TabTrigger.razor *@
<button role="tab"
        id="@($"{Parent!.BaseId}-trigger-{Value}")"
        aria-selected="@(Parent.Active == Value)"
        aria-controls="@($"{Parent.BaseId}-panel-{Value}")"
        @onclick="() => Parent.Activate(Value)">
    @ChildContent
</button>

@code {
    [CascadingParameter] public Tabs? Parent { get; set; }
    [Parameter] public string Value { get; set; } = "";
    [Parameter] public RenderFragment? ChildContent { get; set; }
}
```

`IsFixed="true"` because the `Tabs` instance reference doesn't change between renders.

### Scoped state container service

```csharp
// State/CartState.cs
public sealed class CartState
{
    private readonly List<CartItem> _items = new();
    public IReadOnlyList<CartItem> Items => _items;

    public event Action? Changed;
    public void Add(CartItem item) { _items.Add(item); Changed?.Invoke(); }
    public void Remove(string id) { _items.RemoveAll(i => i.Id == id); Changed?.Invoke(); }
}

// Program.cs
builder.Services.AddScoped<CartState>();
```

Consumer:

```razor
@implements IDisposable
@inject CartState Cart

<p>Items in cart: @Cart.Items.Count</p>

@code {
    protected override void OnInitialized() => Cart.Changed += StateHasChanged;
    public void Dispose() => Cart.Changed -= StateHasChanged;
}
```

**Always dispose**. Subscriptions to a scoped state container leak across page navigations otherwise.

### Cascading value at the root

```razor
@* App.razor (Server) or App.razor (WASM) *@
<CascadingValue Value="@_theme" Name="Theme" IsFixed="false">
    <Router AppAssembly="@typeof(Program).Assembly">
        <Found Context="routeData">
            <RouteView RouteData="@routeData" />
        </Found>
    </Router>
</CascadingValue>

@code {
    private Theme _theme = Theme.System;
}
```

Children:

```razor
@code {
    [CascadingParameter(Name = "Theme")] public Theme Theme { get; set; }
}
```

### JS interop via collocated module

```javascript
// Components/Map.razor.js
export function init(elementRef, options) {
    return new Map(elementRef, options);
}

export function destroy(instance) {
    instance?.destroy();
}
```

```razor
@* Components/Map.razor *@
@implements IAsyncDisposable
@inject IJSRuntime JS

<div @ref="_el" class="map"></div>

@code {
    private ElementReference _el;
    private IJSObjectReference? _module;
    private IJSObjectReference? _map;

    protected override async Task OnAfterRenderAsync(bool firstRender)
    {
        if (firstRender)
        {
            _module = await JS.InvokeAsync<IJSObjectReference>("import", "./Components/Map.razor.js");
            _map = await _module.InvokeAsync<IJSObjectReference>("init", _el, new { /* options */ });
        }
    }

    public async ValueTask DisposeAsync()
    {
        if (_module is not null && _map is not null)
            await _module.InvokeVoidAsync("destroy", _map);
        if (_map is not null) await _map.DisposeAsync();
        if (_module is not null) await _module.DisposeAsync();
    }
}
```

ES modules collocated as `<Component>.razor.js` keep JS next to the consumer.

### Form with validation

```razor
<EditForm Model="@_model" OnValidSubmit="HandleSubmit">
    <DataAnnotationsValidator />
    <ValidationSummary />

    <InputText @bind-Value="_model.Email" />
    <ValidationMessage For="@(() => _model.Email)" />

    <button type="submit">Save</button>
</EditForm>

@code {
    private CreateUser _model = new();

    private async Task HandleSubmit() { /* call API */ }

    private sealed class CreateUser
    {
        [Required, EmailAddress]
        public string Email { get; set; } = "";
    }
}
```

For complex validation (cross-field, async): swap `DataAnnotationsValidator` for a `FluentValidationValidator` from the `Blazored.FluentValidation` package.

## Rules

- **EventCallback** (or `EventCallback<T>`) for every event parameter — never `Action` / `Func<T, Task>`
- Components that subscribe to state / events implement `IDisposable` (or `IAsyncDisposable`) and **always unsubscribe**
- `OnAfterRenderAsync(firstRender: true)` for any DOM-touching JS interop; never in `OnInitializedAsync`
- Persist any prerendered data fetch: `[PersistentState]` (net10) / `PersistentComponentState` (net8/net9)
- **Static SSR by default; interactivity opt-in per surface.** The `@rendermode` is set by the consumer at the call site — emitted components are **render-mode-agnostic** (no `@rendermode` inside a reusable component)
- **Every interactive element and list/grid container carries a `data-testid`** per the `frontend/blazor/skills/testability` convention (PascalCase dot-separated, static row locators, no ids/GUIDs/indexes) — zero locator collisions
- **In-app navigation is a real anchor** (`<a href="...">`, or `NavLink`) — never a click-handler-only button calling `NavigateTo`. **Default to the same tab** (new tabs break Back and disorient); emit `target="_blank"` only for the deliberate exceptions [`ui-conventions`](../ui-conventions/SKILL.md) §7 lists, and when you do, emit the full affordance: `rel="noopener"` **plus** a visible "opens in new tab" cue and an `aria-label` suffix — see the recipe below
- **Every page scaffold emits `<PageTitle>`**
- Cascading values split by concern; `IsFixed="true"` when the cascaded reference doesn't change
- State containers as **scoped** DI services; events with `Changed` (or specific event names) raised on mutation
- JS lives in `.razor.js` modules next to the component
- DI registrations in `Program.cs` (Server) and `Program.cs` of the WASM project — both for shared services
- Constructor / `@inject` field initialization for dependencies; never `Activator.CreateInstance`

## What NOT to do

- No `Action` / `Func` as `[Parameter]` for events — `EventCallback` forces correct re-render
- No subscriptions without `Dispose` cleanup
- No JS interop in `OnInitializedAsync`
- No double-fetch on prerender boundary — `[PersistentState]` (net10) / `PersistentComponentState` (net8/net9)
- No `@rendermode` hardcoded inside a reusable component — the consumer decides
- No click-handler-only navigation buttons; no page without `<PageTitle>`; no interactive element without a `data-testid`
- No `target="_blank"` on internal routes, and none anywhere without `rel="noopener"` + a visible "opens in new tab" cue + an `aria-label` suffix
- No net10-only APIs (`[PersistentState]`, `NotFoundPage`, `AddValidation()`) emitted into a net8/net9 project
- No mutable static fields holding component state
- No `StateHasChanged()` calls right after a state container update — the container's event already triggers it
- No `[CascadingParameter]` on bulky god objects — split by concern
- No mixing render modes on the same component without a clear reason
- No `@bind` without `@bind:event="oninput"` if you actually want input-time updates (default is `onchange`)
- No business logic in components — push into services / handlers; components render and dispatch
- No `IDisposable` skipped just because the page "feels short-lived" — leaks add up
- No `await` on Tasks without `ConfigureAwait(false)` in shared library code (Blazor app code is fine without)

## Generation outputs

For every component:

1. The `.razor` file under `Components/` or feature folder
2. A code-behind `.razor.cs` partial class when the component grows beyond ~50 lines of code
3. Collocated `.razor.js` for any JS interop
4. A bUnit test for non-trivial components (`*.Tests` project)

## Validation

- `dotnet build` — 0 warnings
- `dotnet test` — bUnit tests pass
- Smoke in browser: confirm no double fetch on prerender, confirm `Dispose` is invoked on navigation (DevTools network panel)

## Handoffs

- Conceptual lookup → `frontend/blazor/skills/reference`
- Reviewing the result → `frontend/blazor/skills/reviewer`
- Auth wiring → `auth/auth0-blazor`
- Non-component .NET patterns → `design-patterns/dotnet/generator`
- API DTOs the components consume → `qa/api-dto-writer/dotnet`
