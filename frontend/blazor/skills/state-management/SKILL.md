---
name: fe-blazor-state-management
description: Use when managing state in Blazor (.NET 8/9/10 — Server / WASM / Auto) — scoped DI services, CascadingValue, `[PersistentState]`, circuit-eviction persistence, Fluxor for Redux-style, prerender → interactive hand-off. Triggers: "where should this state live in Blazor", "share state across components", "CascadingValue vs scoped service", "persist data across prerender". Do NOT use for component scaffolding (`component-writer`), forms (`forms`), or React (its sibling).
---

# Blazor State Management

The right place for state in Blazor (.NET 8/9/10) depends on lifetime + scope + render mode. The default: **scoped DI services with a `Changed` event**, `[PersistentState]` (net10) or `PersistentComponentState` (net8/net9) to bridge prerender → interactive, `CascadingValue` for cross-cutting concerns. Avoid Fluxor / Redux-style stores unless the team is genuinely committed to the pattern.

## When to use

- Multiple components need to share state
- Page lifecycle changes (navigate, refresh, prerender → interactive) lose data the user expects to survive
- App-wide concerns (current user, theme, feature flags, cart) need a home
- Migrating from prop-drilling / static fields to a sane pattern
- Picking between scoped service + event, CascadingValue, Fluxor

## When NOT to use

- Component scaffolding → `frontend/blazor/skills/component-writer`
- Forms specifically → `frontend/blazor/skills/forms`
- Render mode trade-offs → `frontend/blazor/skills/basics`
- React → `frontend/react/skills/state-management`
- Auth state from Auth0 → `auth/auth0-blazor`

## Lifetime / scope mental model

Blazor's DI scope behavior differs between Server and WASM. Pick the right lifetime for **what the state must outlive**.

| Scope | Blazor Server | Blazor WASM |
|---|---|---|
| **Transient** | Per resolution | Per resolution |
| **Scoped** | **Per SignalR connection** (per user session) | **Application lifetime** (only one user) |
| **Singleton** | Process-wide (**shared across all users — danger**) | Process-wide (single user — fine) |

The killer pitfall: a `Singleton` state container in Blazor Server is shared across every user's session. Always use **Scoped** for state containers in Server.

## Decision tree

```
Is this state used only by one component?
  ├─ yes  → component field (`@code private string _foo;`)
  └─ no   ↓
Is this state shared across the render tree (theme, user)?
  ├─ yes  → CascadingValue + CascadingParameter
  └─ no   ↓
Is this state shared across non-adjacent components?
  ├─ yes  → Scoped DI service with a `Changed` event (the default)
  └─ no   ↓
Is the state-change graph large with many actions and side effects?
  ├─ yes  → consider Fluxor / Blazor-State (only if the complexity justifies)
  └─ no   → scoped DI service still wins
```

## Scoped DI service with `Changed` event (the default)

```csharp
// State/CartState.cs
public sealed class CartState
{
    private readonly List<CartItem> _items = new();

    public IReadOnlyList<CartItem> Items => _items;

    public event Action? Changed;

    public void Add(CartItem item)    { _items.Add(item);                  Changed?.Invoke(); }
    public void Remove(string id)     { _items.RemoveAll(i => i.Id == id); Changed?.Invoke(); }
    public void Clear()               { _items.Clear();                    Changed?.Invoke(); }

    public long TotalMinor => _items.Sum(i => i.PriceMinor * i.Quantity);
}

// Program.cs
builder.Services.AddScoped<CartState>();
```

Consumer (every component that subscribes implements `IDisposable`):

```razor
@implements IDisposable
@inject CartState Cart

<p>Items: @Cart.Items.Count — Total: @(Cart.TotalMinor / 100m).ToString("F2") EUR</p>

@code {
    protected override void OnInitialized() => Cart.Changed += StateHasChanged;
    public void Dispose() => Cart.Changed -= StateHasChanged;
}
```

`IDisposable` is **mandatory** — without it the subscription leaks across navigations and you accumulate ghost handlers. Reviewers should flag any subscription without dispose.

For multi-event services, expose named events (`CountChanged`, `TotalChanged`) so components subscribe only to the ones they care about.

## Read-only access from the outside

The container exposes `IReadOnlyList<>` / `IReadOnlyDictionary<>` — never `List<>`. State mutations go through the container's methods, which raise events. A consumer that can `state.Items.Add(...)` will inevitably do so and bypass `Changed`.

## Per-route state (page-scoped)

For state that should reset on route change, instantiate it inside the page component:

```razor
@page "/checkout"
@code {
    private CheckoutFlow _flow = new();

    protected override void OnInitialized()
    {
        _flow.StepCompleted += StateHasChanged;
    }

    public void Dispose() => _flow.StepCompleted -= StateHasChanged;
}
```

Use this when a multi-step flow's state shouldn't persist across navigations.

## CascadingValue for cross-cutting

Theme, current user, locale, feature flags — read by many, written rarely. Provided at a root layout level:

```razor
@* MainLayout.razor *@
<CascadingValue Value="@_theme" Name="Theme" IsFixed="false">
    <CascadingValue Value="@_currentUser" Name="CurrentUser" IsFixed="false">
        @Body
    </CascadingValue>
</CascadingValue>
```

Consumer:

```razor
@code {
    [CascadingParameter(Name = "Theme")]       public Theme Theme { get; set; }
    [CascadingParameter(Name = "CurrentUser")] public User?  CurrentUser { get; set; }
}
```

Rules from `frontend/blazor/skills/basics`:
- Split by concern (no god `AppState` carrying everything)
- `IsFixed="true"` when the reference doesn't change — cheaper re-renders

## The prerender hand-off — `[PersistentState]` (net10, primary)

Without persistence, an `OnInitializedAsync` fetch runs **twice** (once on prerender, once on the interactive connection). On net10, one attribute fixes it:

```razor
@page "/orders"
@inject HttpClient Http

@code {
    [PersistentState]
    public List<OrderDto>? Orders { get; set; }

    protected override async Task OnInitializedAsync()
    {
        Orders ??= await Http.GetFromJsonAsync<List<OrderDto>>("/api/orders");
    }
}
```

The framework persists the property on prerender and restores it on the interactive run — no subscription, no dispose. Add `AllowUpdates = true` when the value should refresh during enhanced navigation.

### Circuit-eviction persistence + `HybridCache` (net10, Blazor Server)

The same `[PersistentState]` declarations survive circuit pause/eviction: `Blazor.pauseCircuit()` (or server-side `Circuit.RequestCircuitPauseAsync`) disposes the circuit while persisting declared state, and `Blazor.resumeCircuit()` restores it — a hidden tab costs no server memory and the user loses nothing. On scale-out, back the persisted circuit state with `HybridCache` (Redis, etc.) so a resume can land on another node.

## `PersistentComponentState` (net8 / net9 — fallback)

The manual API — the correct, non-obsolete pattern on down-level TFMs. The prerender persists the data into the page; the interactive run reads it back.

```razor
@page "/orders"
@implements IDisposable
@inject HttpClient Http
@inject PersistentComponentState ApplicationState

@if (_orders is null) <p>Loading…</p>
else
{
    <ul>@foreach (var o in _orders) <li>@o.Reference</li></ul>
}

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

Apply on every component that fetches data **and** renders interactively — with `[PersistentState]` on net10, this manual form on net8/net9. The single biggest UX win either way.

## Persistence across navigations

| Where | Use |
|---|---|
| `localStorage` (WASM) | User-preference state surviving reloads (theme, recently viewed) |
| `sessionStorage` | Per-tab state (multi-step wizard mid-flow) |
| Cookies | When server-side reads matter (set via JS interop or a server-side controller) |
| `ProtectedSessionStorage` / `ProtectedLocalStorage` (Server) | Sensitive client-side state encrypted with the data protection keys |

Reach for `ProtectedBrowserStorage` patterns (`Microsoft.AspNetCore.Components.Server.ProtectedBrowserStorage`) on Blazor Server when storing anything user-specific.

## Fluxor / Blazor-State — when (rarely)

A Redux-style store with actions / reducers / effects. Use it when:

- The state-change graph is large + complex + async-heavy
- The team has internalized Redux mental model and wants the same in Blazor
- You need devtools-style time-travel debugging

For most apps in this library, a scoped DI service + `Changed` is simpler and equally correct. Fluxor adds boilerplate (action types, reducer methods, effect classes) that's worth it only when the alternative becomes worse.

## Server-side caching (not state, but related)

For "expensive computation we'd rather not redo per request":

- `IMemoryCache` (in-process)
- Distributed cache (`IDistributedCache`) backed by Redis (`data/redis`)

This isn't UI state; it's server-side memoization. Keep it out of the components.

## Anti-patterns

- **Singleton state container in Blazor Server** — shared across users
- **Subscribing without `IDisposable`** — handler leak
- **Mutable `List<>` exposed publicly** — bypasses event
- **God state container** carrying every app concern
- **`StateHasChanged()` in event handlers when the framework would already detect** — wastes renders
- **Server-only secrets in WASM-compiled state** (the WASM bundle ships to the browser)
- **`OnInitializedAsync` fetch without `PersistentComponentState`** on a prerendered + interactive page — double fetch
- **Cascading parameters carrying many fields** — re-renders descendants on every change

## Rules

- `AddScoped<TState>()` for shared state in Blazor Server; same scope in WASM is fine
- Subscriptions to events implement `IDisposable` / `IAsyncDisposable`, unsubscribe in `Dispose`
- Read-only collection types exposed publicly
- Split events by concern; consumers subscribe to specific events
- Prerendered fetches persisted: `[PersistentState]` (net10) / `PersistentComponentState` (net8/net9)
- `CascadingValue` for genuinely cross-cutting state, split by concern
- `ProtectedBrowserStorage` for sensitive client-side state
- No god `AppState`

## What NOT to do

- No `Singleton` state container in Blazor Server
- No subscriptions without `Dispose`
- No public `List<T>` on state containers
- No `Fluxor` for a CRUD app
- No `OnInitializedAsync` HTTP call without prerender persistence
- No `[CascadingParameter]` on bulky god objects
- No client-side state that includes secrets in WASM
- No `StateHasChanged` after every property setter — let events do it
- No bypassing the state container by mutating its private collections via tricks

## Generation steps

1. Identify the **lifetime** the state must outlive (component / route / session / app).
2. Pick the pattern from the decision tree.
3. Generate the state class with `IReadOnlyList<>`-exposing properties + `Changed` event(s).
4. Register lifetime (`AddScoped` default; document if Singleton/Transient).
5. Consumer pattern: inject + `Changed += StateHasChanged` + `IDisposable`.
6. For prerendered + interactive pages, persist initial fetches — `[PersistentState]` on net10, `PersistentComponentState` on net8/net9.
7. For app-wide concerns, add a `CascadingValue` at the root layout.

## Handoffs

- Component scaffolding using this state → `frontend/blazor/skills/component-writer`
- Render-mode and lifecycle background → `frontend/blazor/skills/basics`
- Forms specifically → `frontend/blazor/skills/forms`
- Auth state from Auth0 → `auth/auth0-blazor`
- React equivalent → `frontend/react/skills/state-management`
