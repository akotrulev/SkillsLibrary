# MudBlazor (default)

Free (MIT) Material-Design component library, largest Blazor community, clean C#-first API. The library default unless a decision-matrix row fits better.

**Version:** pin the MudBlazor major to your TFM. MudBlazor 7.x targets net8/net9; MudBlazor 8.x adds net9/net10 and improved static-SSR behavior. Static-SSR support for interactive services matured across the 7→8 line — **verify against your pinned version** before assuming a dialog fires from an SSR page (it won't; see gotchas).

## Setup

```bash
dotnet add package MudBlazor
```

```csharp
// Program.cs (Server) AND Program.cs (.Client) — register in BOTH projects for Auto/WASM
builder.Services.AddMudServices();
```

```razor
@* _Imports.razor *@
@using MudBlazor
@using MudBlazor.Services
```

Static assets in `App.razor` `<head>`/`<body>` (net8+ auto-includes via the package's static web assets in recent versions; add manually if your version needs it):

```html
<link href="_content/MudBlazor/MudBlazor.min.css" rel="stylesheet" />
<script src="_content/MudBlazor/MudBlazor.min.js"></script>
<link href="https://fonts.googleapis.com/css?family=Roboto:300,400,500,700" rel="stylesheet" />
```

## Providers — once, at the interactive layout root

The providers must live under an **interactive** render mode (they run JS and hold service state). Put them in `MainLayout.razor` (or a dedicated `Providers.razor` rendered interactively), never per page:

```razor
@* MainLayout.razor *@
<MudThemeProvider @bind-IsDarkMode="_isDark" Theme="_theme" />
<MudPopoverProvider />
<MudDialogProvider />
<MudSnackbarProvider />

<MudLayout>
    <MudMainContent>@Body</MudMainContent>
</MudLayout>
```

## Theming + dark mode

One `MudTheme` object at the root; feed its palette from the `design/theme-presets` output (map palette hex → `PaletteLight`/`PaletteDark`).

```csharp
private readonly MudTheme _theme = new()
{
    PaletteLight = new PaletteLight { Primary = "#1867c0", Background = "#ffffff" },
    PaletteDark  = new PaletteDark  { Primary = "#4f9cff", Background = "#1a1a27" },
    Typography = new Typography { Default = new DefaultTypography { FontFamily = ["Roboto", "sans-serif"] } },
};
private bool _isDark;
```

**Dark mode:** `MudThemeProvider` exposes system-preference detection — bind `@ref` and call `GetSystemPreference()` / `WatchSystemPreference(cb)` (net8+ MudBlazor 7+) so the app follows the OS and updates live when the user flips their OS theme:

```razor
<MudThemeProvider @ref="_provider" @bind-IsDarkMode="_isDark" Theme="_theme" />
@code {
    private MudThemeProvider _provider = null!;
    protected override async Task OnAfterRenderAsync(bool first)
    {
        if (!first) return;
        _isDark = await _provider.GetSystemPreference();
        await _provider.WatchSystemPreference(v => { _isDark = v; StateHasChanged(); return Task.CompletedTask; });
        StateHasChanged();
    }
}
```

## DataGrid — server-side by default

`MudDataGrid<T>` with `ServerData` for server-side paging/sort/filter (never load a full table client-side):

```razor
<MudDataGrid T="OrderDto" ServerData="LoadAsync" SortMode="SortMode.Multiple" Filterable="true" data-testid="Orders.Grid">
    <Columns>
        <PropertyColumn Property="x => x.Number" Title="Order #" />
        <PropertyColumn Property="x => x.Total" Title="Total" Format="C" CellStyleFunc="@(_ => "text-align:right")" />
    </Columns>
    <PagerContent><MudDataGridPager T="OrderDto" /></PagerContent>
</MudDataGrid>

@code {
    private async Task<GridData<OrderDto>> LoadAsync(GridState<OrderDto> s)
    {
        var page = await Data.GetOrdersAsync(s.Page, s.PageSize, s.SortDefinitions, s.FilterDefinitions);
        return new GridData<OrderDto> { Items = page.Items, TotalItems = page.Total };
    }
}
```

The `LoadAsync` calls a [`data-fetching`](../../data-fetching/SKILL.md) interface method — the grid is a consumer, not a data owner.

## Dialog + snackbar services

```csharp
@inject IDialogService DialogService
@inject ISnackbar Snackbar

private async Task Delete(OrderDto o)
{
    var ok = await DialogService.ShowMessageBox("Delete order",
        $"Delete order {o.Number}? This cannot be undone.",   // name the specific object — ui-rules
        yesText: "Delete", cancelText: "Cancel");
    if (ok == true) { await Data.DeleteAsync(o.Id); Snackbar.Add($"Order {o.Number} deleted", Severity.Success); }
}
```

Both services require their provider alive under an interactive render mode (see gotchas).

## Render-mode gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `DialogService.Show` / `Snackbar.Add` throws or nothing appears | Called from static SSR, or providers not in an interactive layout | Providers under an interactive render mode; the calling island interactive |
| `MudButton` `@onclick` does nothing | Button on a static-SSR page (styled markup, no interactivity) | Make the island `@rendermode InteractiveServer/WebAssembly/Auto` |
| Popovers/menus mis-position | `MudPopoverProvider` missing | Add it alongside the other providers |
| `data-testid` on `MudTabPanel` doesn't land in DOM | `MudTabPanel` doesn't render captured `UserAttributes` | Tag an inner element — [`test-ids`](../../test-ids/SKILL.md) matrix caveat |
| Theme flashes light then dark on load | System-preference read only after first render | Read `GetSystemPreference()` in `OnAfterRenderAsync(firstRender)`; acceptable, or persist last choice server-side |
| Services not found in `.Client` under Auto | `AddMudServices()` only registered in Server | Register in **both** `Program.cs` files |

**`data-testid` on MudBlazor controls:** inline `data-testid="..."` forwards via `UserAttributes` (`MudComponentBase`) to the rendered root for most components — the `MudTabPanel` exception above is the one to remember. Full rules in [`test-ids`](../../test-ids/SKILL.md).

## Validation

- Providers resolve; `AddMudServices()` in both `Program.cs` for Auto/WASM.
- A `MudDialog` and a `Snackbar` fire from an interactive island (they no-op from static SSR).
- `MudDataGrid` pages/sorts/filters server-side.
- Dark mode toggles and follows OS preference live.
