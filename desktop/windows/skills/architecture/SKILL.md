---
name: architecture
description: Use when deciding where state and logic live in a WinUI app (CommunityToolkit.Mvvm, Generic Host DI, services, view-model state). Triggers "ViewModel or code-behind". Not for API calls (networking).
---

# Windows — Architecture (MVVM with CommunityToolkit.Mvvm)

Where state and logic live: **MVVM with CommunityToolkit.Mvvm source generators, one view model per screen, constructor-injected services from a Generic Host, one sealed state per data region, no service locator.** Audit rows: section C of `desktop-windows:standards-audit`.

## Version lane

| Concern | Primary | Older / brownfield |
|---|---|---|
| CommunityToolkit.Mvvm | **8.4.2**; `[ObservableProperty]` on **partial properties** works on C# 14 without a preview language version | 8.2–8.3: `[ObservableProperty]` on a field (`_name` → `Name`). Do not mix styles in one project |
| DI / host | `Microsoft.Extensions.Hosting` at the runtime major (10.x on .NET 10) | Same; a WPF or WinForms app may use `ServiceCollection` alone |
| Messenger | `WeakReferenceMessenger` — only when earned | Same |
| `winui-mvvm` template | Uses CommunityToolkit.Mvvm. **Whether it registers a host is not documented** (re-checked 2026-11-15): read `App.xaml.cs` before adding one | — |

A project on a field-style `[ObservableProperty]` is not flagged for lacking partial properties.

## When to use

- Creating a screen's view model, a service, or the composition root
- "Where does this logic go?", "how does a view model get its service?", "do I need a messenger?"
- Modelling loading / loaded / failed state

## When NOT to use

- Controls, templates, `x:Bind` syntax → [`ui-components`](../ui-components/SKILL.md)
- HTTP clients, retries → `desktop-windows:networking`
- Local storage → `desktop-windows:offline-and-storage`
- Windows and navigation → `desktop-windows:windows-and-navigation`
- Validation → `desktop-windows:forms`
- Tests for view models → `desktop-windows:unit-testing`

---

## The layers (flat)

| Layer | Holds | Knows about |
|---|---|---|
| **View** (`*.xaml` + thin `*.xaml.cs`) | Layout, bindings, focus, animation | Its view model, nothing else |
| **ViewModel** | State, commands, orchestration of services | Services, models. **Never a control, a `Window`, a `Frame` or a `DispatcherQueue`** |
| **Service** | One capability: orders API, settings, clock | Models, `HttpClient`, storage |
| **Model** | Records | Nothing |

- **Two layers earn their keep, three do not by default.** A service that only forwards one call to a repository that only forwards to EF Core is one layer. A repository exists only for a real abstraction need (CLAUDE.md § Pattern application).
- **View models and services live in the Core class library** (`net10.0`, no `-windows`) so a control cannot be referenced from them ([`project-setup`](../project-setup/SKILL.md)).
- **One view model per screen or user control that has behaviour.** A control that only displays takes its data by `x:Bind` and has no view model.

## View model

```csharp
public sealed partial class OrdersViewModel : ObservableObject
{
    private readonly IOrdersService _orders;
    private CancellationTokenSource? _load;

    public OrdersViewModel(IOrdersService orders) => _orders = orders;

    [ObservableProperty]
    public partial OrdersState State { get; private set; } = OrdersState.Loading.Instance;

    [RelayCommand]
    private async Task LoadAsync(CancellationToken cancellationToken)
    {
        State = OrdersState.Loading.Instance;
        try
        {
            State = new OrdersState.Loaded(await _orders.ListAsync(cancellationToken));
        }
        catch (OrdersException ex)
        {
            State = new OrdersState.Failed(ex.Reason);
        }
    }
}
```

- **`partial` class, `sealed`**; `[ObservableProperty]` on a partial property (field form on older toolkits); `[RelayCommand]` on a method generates `LoadCommand`, an `IAsyncRelayCommand` with `IsRunning` and cancellation.
- **`[RelayCommand]` on an `async Task` method takes a `CancellationToken`** and the generated command cancels the previous run on re-execution when `IncludeCancelCommand = true`; wire the window's close to `Cancel`.
- **`async void` is not a command.** Never `.Result` / `.Wait()` in a view model.
- **`[NotifyPropertyChangedFor]`, `[NotifyCanExecuteChangedFor]`** over manual `OnPropertyChanged(nameof(...))` calls.
- **Property and collection changes that reach `x:Bind` happen on the UI thread.** A command awaited from the UI continues there, so no dispatcher is needed. Where a background source pushes (a socket), a small adapter in the app project (not the Core library) enqueues **once per batch** with `DispatcherQueue.TryEnqueue`, never once per item.

## State: one sealed type per data region

Every data region has **loading / loaded / failed, plus stale and offline** (CLAUDE.md § Desktop code rules). One type, never three booleans:

```csharp
public abstract record OrdersState
{
    public sealed record Loading : OrdersState { public static readonly Loading Instance = new(); }
    public sealed record Loaded(IReadOnlyList<Order> Orders, bool IsStale = false) : OrdersState;
    public sealed record Failed(FailureReason Reason) : OrdersState;
}

public enum FailureReason { Offline, Timeout, Server, Unknown }
```

- **The failed case carries a typed reason, never `Exception.Message`.** The view maps it to a resource string ([`ui-components`](../ui-components/SKILL.md)).
- **A `switch` expression over the state has no `_` arm,** so a new case breaks the build where it must be handled; a discard arm on this type is a finding.
- **Stale** = the last loaded data kept while a refresh runs or after it failed with a cached copy; **offline** is a reason of its own, told apart from `Server`.
- **A failure is scoped to the response-dependent subtree** — toolbars, filters and the shell keep rendering — and also sets the one persistent `InfoBar` (below).

## Composition root: Generic Host

Constructor injection only; no `Ioc.Default.GetService<T>()` in a class, no `App.Current.Services` lookup (a service locator).

```csharp
public partial class App : Application
{
    private readonly IHost _host = Host.CreateDefaultBuilder()
        .ConfigureServices(services =>
        {
            services.AddSingleton<TimeProvider>(TimeProvider.System);
            services.AddSingleton<IOrdersService, OrdersService>();
            services.AddTransient<OrdersViewModel>();
            services.AddTransient<OrdersPage>();
            services.AddTransient<MainWindow>();
        })
        .Build();

    protected override async void OnLaunched(LaunchActivatedEventArgs args)
    {
        await _host.StartAsync();
        _host.Services.GetRequiredService<MainWindow>().Activate();
    }
}
```

- **The root is the only place that resolves from the container.** A page gets its view model through its constructor (the `Frame` creates pages with no arguments, so navigation resolves the page from the host — `desktop-windows:windows-and-navigation`); never `new OrdersViewModel(...)` in a page.
- **Lifetimes:** `AddSingleton` for stateless services and caches, `AddTransient` for view models and windows, `AddScoped` is meaningless without a request scope — do not use it.
- **`HttpClient` only through `IHttpClientFactory`** typed clients (`desktop-windows:networking`). **Configuration** from the `IConfiguration` the host builds; **no secret in `appsettings.json`** — tokens live in `PasswordVault` / DPAPI (`desktop-windows:offline-and-storage`).
- **Logging through `ILogger<T>`** with message templates; the OpenTelemetry wiring is `desktop/_shared/observability`.
- **Dispose the host on exit,** and cancel work when the window closes.
- **If the template already composes services another way,** keep the project's way (match conventions over this skill's defaults) and still forbid the locator.

## One banner for failures

A failed region raises **one persistent `InfoBar`** inside the window content (`IsOpen`, severity `Error`, `IsClosable=true`) that only the user closes; a background failure never raises a `ContentDialog` or message box. The view model owns an `ErrorBanner` state; the shell binds it.

## Messenger — only when earned

`WeakReferenceMessenger` is for two view models with **no other relationship** (a settings change that must refresh an unrelated open window). Not for parent→child (a property or constructor argument), not for a request/response (a service). A messenger used for everything is a hidden global; flag pattern stacking.

## Several windows, one source of truth

Two windows on the same data share **one service holding the state** (a singleton with `IObservable`/event or a shared `ObservableCollection` owned by it), never a copy per window.

## Common gotchas

- **View model holds a `Window`, `Page` or `DispatcherQueue`** — cannot be unit tested; move the UI call to the view.
- **`[ObservableProperty]` on a field in a 8.4 partial-property project** (or the reverse) — one style per project.
- **`Ioc.Default` in a constructor** — a service locator.
- **`async void` command handlers** — exceptions crash the app; use `[RelayCommand]` on `async Task`.
- **Singleton view model** — state leaks between navigations; view models are transient.
- **Reading a service's result before `StartAsync`** — hosted services start in `OnLaunched`, awaited.

## Handoffs

- Controls, `x:Bind`, templates, `InfoBar` markup → [`ui-components`](../ui-components/SKILL.md)
- Typed HTTP clients, timeouts → `desktop-windows:networking`
- Persistence, `PasswordVault` → `desktop-windows:offline-and-storage`
- Navigation and window lifetime → `desktop-windows:windows-and-navigation`
- Validation (`ObservableValidator`) → `desktop-windows:forms`
- View-model tests, `TimeProvider` seams → `desktop-windows:unit-testing`
- Telemetry → `desktop/_shared/observability`
