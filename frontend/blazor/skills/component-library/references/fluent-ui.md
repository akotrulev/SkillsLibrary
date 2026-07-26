# Fluent UI Blazor

Free (MIT), Microsoft-maintained (`Microsoft.FluentUI.AspNetCore.Components`). Native Fluent design — the Microsoft 365 / Teams look. Pick this when the product must *look* like a Microsoft product and you want design-token theming.

**Version:** built on **Fluent UI Web Components** (JS custom elements underneath). Major versions track the underlying web-components rewrite closely — pin `Microsoft.FluentUI.AspNetCore.Components` to your TFM line and check the migration notes when bumping majors (the token API and component names have shifted between majors). net8/net9/net10 all supported on recent majors.

## Setup

```bash
dotnet add package Microsoft.FluentUI.AspNetCore.Components
```

```csharp
// Program.cs (Server AND .Client for Auto/WASM)
builder.Services.AddFluentUIComponents();
```

```razor
@* _Imports.razor *@
@using Microsoft.FluentUI.AspNetCore.Components
```

The library's static web assets (JS for the web components) are included via the package; the web-components loader initializes on the client — this matters for static SSR (see gotchas).

## Providers — once, at the interactive layout root

Fluent UI's overlay services (dialog, toast, tooltip, menu) need their providers mounted under an **interactive** render mode:

```razor
@* MainLayout.razor *@
<FluentLayout>
    <FluentBodyContent>@Body</FluentBodyContent>
</FluentLayout>

@* provider hosts — interactive root, once *@
<FluentToastProvider />
<FluentDialogProvider />
<FluentTooltipProvider />
<FluentMenuProvider />
```

## Theming + dark mode — design tokens

Fluent UI theming is **token-first**: you set a few global tokens (accent base color, neutral base, density, corner radius) and the system derives the rest. `<FluentDesignTheme>` at the root drives light/dark and accent:

```razor
@* App root / MainLayout *@
<FluentDesignTheme @bind-Mode="_mode" @bind-OfficeColor="_accent" StorageName="theme" />

@code {
    private DesignThemeModes _mode = DesignThemeModes.System;   // System follows OS preference
    private OfficeColor? _accent = OfficeColor.Default;
}
```

`DesignThemeModes.System` follows the OS light/dark automatically; `StorageName` persists the user's choice to localStorage. Map your `design/theme-presets` accent to `OfficeColor`/a custom accent base; [`styling`](../../styling/SKILL.md) owns any further CSS-variable overrides on top of the derived tokens. **Don't hand-set component colors** — set the token, let the system derive.

## DataGrid — server-side by default

`<FluentDataGrid>` binds `Items` (IQueryable, auto server-side when EF-backed) or a `ItemsProvider` for explicit virtualized/paged server loads:

```razor
<FluentDataGrid ItemsProvider="_provider" Pagination="_pagination" TGridItem="OrderDto" data-testid="Orders.Grid">
    <PropertyColumn Property="@(o => o.Number)" Title="Order #" Sortable="true" />
    <PropertyColumn Property="@(o => o.Total)" Format="C" Title="Total" Align="Align.End" />
</FluentDataGrid>
<FluentPaginator State="_pagination" />

@code {
    GridItemsProvider<OrderDto> _provider = default!;
    readonly PaginationState _pagination = new() { ItemsPerPage = 25 };
    protected override void OnInitialized() =>
        _provider = async req =>
        {
            var page = await Data.GetOrdersAsync(req.StartIndex, req.Count ?? 25, req.SortByColumn, req.SortByAscending);
            return GridItemsProviderResult.From(page.Items, page.Total);
        };
}
```

The `ItemsProvider` calls a [`data-fetching`](../../data-fetching/SKILL.md) method — server-side paging, render-mode-agnostic.

## Dialog + toast services

```csharp
@inject IDialogService DialogService
@inject IToastService ToastService

async Task Delete(OrderDto o)
{
    var dialog = await DialogService.ShowConfirmationAsync(
        $"Delete order {o.Number}? This cannot be undone.", "Delete", "Cancel", "Delete order");  // name the object
    var result = await dialog.Result;
    if (!result.Cancelled)
    {
        await Data.DeleteAsync(o.Id);
        ToastService.ShowSuccess($"Order {o.Number} deleted");
    }
}
```

## Render-mode gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Components render as unstyled/empty custom elements on first paint under static SSR | Fluent web-components JS hasn't loaded/upgraded the elements yet | Expected hydration order; make interactive surfaces `@rendermode`; don't rely on JS-driven behavior in a pure static-SSR island |
| `DialogService`/`ToastService` no-ops | Provider host not in an interactive layout, or called from static SSR | Providers under an interactive render mode; caller interactive |
| Tokens/theme not applied | `<FluentDesignTheme>` missing at root, or web-components loader not present | `<FluentDesignTheme>` at the app root; ensure package static assets load |
| Services missing in `.Client` under Auto | `AddFluentUIComponents()` only in Server | Register in both `Program.cs` |
| Icons/emoji packages huge in WASM payload | Full icon/emoji assemblies pulled in | Reference only the icon sizes/sets you use; trim (see `performance`, Session D) |

**`data-testid` on Fluent controls:** inline `data-testid="..."` forwards via `AdditionalAttributes` (`FluentComponentBase`) to the rendered root/host element. Full rules in [`test-ids`](../../test-ids/SKILL.md).

## Validation

- `AddFluentUIComponents()` in both `Program.cs` for Auto/WASM; providers mounted interactively.
- `<FluentDesignTheme Mode="System">` follows OS light/dark and persists the user's toggle.
- `<FluentDataGrid>` pages server-side via `ItemsProvider`.
- A confirmation dialog and a toast fire from an interactive island.
