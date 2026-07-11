# Radzen Blazor

Free (MIT) library, **145+ components** including the strongest free **DataGrid**, Scheduler, Charts, TreeView. Pick this when a rich free DataGrid is the deciding factor. (Radzen *Studio* and some premium themes are paid; the component package is free.)

**Version:** pin `Radzen.Blazor` to your TFM line. Recent majors ship Material 3 and Fluent themes and improved static-SSR rendering — verify interactive-service behavior against your pinned version.

## Setup

```bash
dotnet add package Radzen.Blazor
```

```razor
@* _Imports.razor *@
@using Radzen
@using Radzen.Blazor
```

Theme CSS + JS in `App.razor` `<head>`/`<body>` — pick one theme stylesheet (they're mutually exclusive):

```html
<link rel="stylesheet" href="_content/Radzen.Blazor/css/material-base.css" />   <!-- or fluent-base, standard-base, etc. -->
<script src="_content/Radzen.Blazor/Radzen.Blazor.js"></script>
```

```csharp
// Program.cs (Server AND .Client for Auto/WASM)
builder.Services.AddRadzenComponents();   // registers DialogService, NotificationService, TooltipService, ContextMenuService
```

## Providers — once, at the interactive layout root

Radzen's services need their host components mounted under an **interactive** render mode:

```razor
@* MainLayout.razor *@
<RadzenComponents />   @* mounts dialog/notification/tooltip/contextmenu hosts in one tag (recent versions) *@
<RadzenLayout>
    <RadzenBody>@Body</RadzenBody>
</RadzenLayout>
```

(Older versions use explicit `<RadzenDialog />`, `<RadzenNotification />`, `<RadzenTooltip />`, `<RadzenContextMenu />` — same rule: interactive root, once.)

## Theming + dark mode

Radzen themes are CSS-file-based (Material, Material 3, Fluent, Standard, Humanistic, Software — each with a `-dark` variant). Switch the stylesheet or use `ThemeService` for runtime switching:

```csharp
// Program.cs
builder.Services.AddRadzenComponents();   // includes ThemeService
```

```razor
@inject ThemeService ThemeService
<RadzenAppearanceToggle />   @* built-in light/dark toggle (recent versions) *@
@* or programmatically: *@
@code { void Dark() => ThemeService.SetTheme("material-dark", saveThemeToLocalStorage: true); }
```

Feed brand colors by referencing the theme's CSS custom properties and overriding them in your own isolated CSS ([`styling`](../styling/SKILL.md) owns the token mapping from `design/theme-factory`). Radzen themes expose `--rz-*` variables — override those, don't fork the theme file.

## DataGrid — server-side by default

`RadzenDataGrid` is the flagship. Use `LoadData` + `Count` for server-side paging/sort/filter:

```razor
<RadzenDataGrid @ref="_grid" Data="@_orders" Count="@_total" LoadData="@LoadAsync"
                AllowPaging="true" AllowSorting="true" AllowFiltering="true"
                PageSize="25" data-testid="Orders.Grid">
    <Columns>
        <RadzenDataGridColumn Property="Number" Title="Order #" />
        <RadzenDataGridColumn Property="Total" Title="Total" FormatString="{0:C}" TextAlign="TextAlign.Right" />
    </Columns>
</RadzenDataGrid>

@code {
    async Task LoadAsync(LoadDataArgs args)
    {
        var page = await Data.GetOrdersAsync(args.Skip, args.Top, args.OrderBy, args.Filter);
        _orders = page.Items; _total = page.Total;
    }
}
```

`LoadDataArgs` gives you `Skip`/`Top`/`OrderBy`/`Filter` strings ready to translate to your query. Radzen's grid also supports an `IQueryable` for EF-friendly auto server-side execution — but going through a [`data-access`](../../data-access/SKILL.md) interface keeps the grid render-mode-agnostic.

## Dialog + notification services

```csharp
@inject DialogService DialogService
@inject NotificationService NotificationService

async Task Delete(OrderDto o)
{
    var ok = await DialogService.Confirm(
        $"Delete order {o.Number}? This cannot be undone.", "Delete order",   // name the object — ui-conventions
        new ConfirmOptions { OkButtonText = "Delete", CancelButtonText = "Cancel" });
    if (ok == true)
    {
        await Data.DeleteAsync(o.Id);
        NotificationService.Notify(NotificationSeverity.Success, "Deleted", $"Order {o.Number} deleted");
    }
}
```

## Render-mode gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `DialogService.Open`/`Confirm` or `NotificationService.Notify` no-ops | Host components not in an interactive layout, or called from static SSR | `<RadzenComponents />` under an interactive render mode; caller interactive |
| `RadzenButton` `@onclick`/grid interactions dead | Component on a static-SSR page | Make the island interactive |
| Grid renders but never pages/sorts on the server | `LoadData`/`Count` not wired (bound to a full in-memory list) | Wire `LoadData` + `Count` and translate `LoadDataArgs` to a server query |
| Theme not applied | Theme CSS `<link>` missing or two theme stylesheets included | Exactly one theme base stylesheet |
| Services missing in `.Client` under Auto | `AddRadzenComponents()` only in Server | Register in both `Program.cs` |

**`data-testid` on Radzen controls:** inline `data-testid="..."` forwards via `Attributes` (`RadzenComponent`, `CaptureUnmatchedValues`) to the rendered root. Full rules in [`testability`](../../testability/SKILL.md).

## Validation

- `<RadzenComponents />` mounted interactively; `AddRadzenComponents()` in both `Program.cs` for Auto/WASM.
- `RadzenDataGrid` pages/sorts/filters via `LoadData` (server-side; Network shows one page).
- A `Confirm` dialog and a `Notify` toast fire from an interactive island.
- Dark theme toggles at runtime.
