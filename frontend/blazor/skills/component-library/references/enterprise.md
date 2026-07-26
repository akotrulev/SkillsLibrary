# Telerik / Syncfusion (paid enterprise)

The two mature **paid** suites. Pick one only when a **support SLA** is a procurement requirement, you need the widest component set (Gantt, PivotGrid, document editors, reporting), or you need vendor-certified accessibility/compliance. Both have a licensing gate that must be wired before anything renders.

**License:**
- **Telerik UI for Blazor** — commercial only (trial available). License key required at build/runtime.
- **Syncfusion Blazor** — commercial, **plus a free Community License** for individuals and small companies (revenue/headcount thresholds apply — check current terms). License key registration required or components render a watermark / throw.

**Version:** both track the Blazor render model actively and support net8/net9/net10 on current releases; pin the suite version to your TFM and read the vendor's render-mode / static-SSR notes for that release.

## Setup — Telerik

```bash
# Requires the Telerik NuGet source configured with your account credentials
dotnet add package Telerik.UI.for.Blazor
```

```csharp
// Program.cs (Server AND .Client)
builder.Services.AddTelerikBlazor();
```

```razor
@* MainLayout.razor — root component, interactive *@
<TelerikRootComponent>
    @Body
</TelerikRootComponent>
```

License key: set the `TELERIK_LICENSE` (key contents) or `TELERIK_LICENSE_PATH` environment variable / add the license file per Telerik's current activation flow — **as an env var / secret, never committed** (global rule: no secrets in code).

## Setup — Syncfusion

```bash
dotnet add package Syncfusion.Blazor
```

```csharp
// Program.cs
using Syncfusion.Licensing;
SyncfusionLicenseProvider.RegisterLicense(builder.Configuration["Syncfusion:LicenseKey"]);  // from config/secret store
builder.Services.AddSyncfusionBlazor();
```

```razor
@* _Imports.razor *@
@using Syncfusion.Blazor
```

Register the license **before** the host builds; pull the key from configuration / secret store (env var, Key Vault) — never a literal.

## Theming + dark mode

- **Telerik:** swatch-based themes (Default, Material, Fluent, Bootstrap) each with dark swatches; use the ThemeBuilder for brand colors, or override the theme's CSS variables. Runtime light/dark = swap the theme stylesheet or toggle a root class the swatch keys off.
- **Syncfusion:** theme stylesheet per theme (Material 3, Fluent 2, Bootstrap 5, Tailwind — each with `-dark`); switch by swapping the `<link>` or using the theme-switching API. Brand via the Theme Studio output.

Map the `design/theme-presets` palette to the vendor theme's CSS custom properties; [`styling`](../../styling/SKILL.md) owns the variable mapping. Don't fork vendor theme files — override their exposed variables.

## DataGrid — server-side by default

Both grids are the suites' flagship and support server-side operations. Bind to an observable data source / `OnRead` (Telerik) or a `DataManager` with a custom adaptor (Syncfusion) that translates paging/sort/filter to a [`data-fetching`](../../data-fetching/SKILL.md) call:

```razor
@* Telerik *@
<TelerikGrid TItem="OrderDto" OnRead="@ReadAsync" Pageable="true" Sortable="true" FilterMode="GridFilterMode.FilterRow"
             PageSize="25" data-testid="Orders.Grid">
    <GridColumns>
        <GridColumn Field="@nameof(OrderDto.Number)" Title="Order #" />
        <GridColumn Field="@nameof(OrderDto.Total)" Title="Total" DisplayFormat="{0:C}" />
    </GridColumns>
</TelerikGrid>

@code {
    async Task ReadAsync(GridReadEventArgs args)
    {
        var page = await Data.GetOrdersAsync(args.Request);   // translate DataSourceRequest
        args.Data = page.Items; args.Total = page.Total;
    }
}
```

Syncfusion's equivalent uses a `SfDataManager` + `CustomAdaptor` that issues the server query. Either way the grid is a consumer of a data-fetching interface, not a data owner.

## Dialog + toast/notification services

- **Telerik:** `DialogFactory` (injected via `TelerikDialogs`) for `ConfirmAsync`/`AlertAsync`; `TelerikNotification` component + `@ref` for toasts.
- **Syncfusion:** `SfDialogService` for confirm/alert; `SfToast` component + `@ref` for toasts.

Both require their host/root component mounted under an interactive render mode (Telerik's `<TelerikRootComponent>`, Syncfusion's rendered providers). Name the object in destructive confirms (ui-rules).

## Render-mode gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Everything renders as a watermark / throws a license error | License key not registered / wrong env var | Register the key from config/secret before host build (both suites) |
| Dialog/toast services no-op | Root/provider component not interactive, or called from static SSR | `<TelerikRootComponent>` / Syncfusion providers under an interactive render mode |
| Components dead on a static-SSR page | Interactivity needs an interactive island | `@rendermode` on the island |
| Grid loads whole table then pages client-side | `OnRead`/`CustomAdaptor` not wired | Wire server-side read; translate the request to a data-fetching query |
| Services missing in `.Client` under Auto | Registration only in Server | Register (and license-register) in both `Program.cs` |
| Large WASM payload | Full suite assemblies pulled into WASM | Trim; reference only used component assemblies (see `performance`, Session D) |

**`data-testid`:** both suites expose per-component `HtmlAttributes` / attribute dictionaries; inline `data-testid` usually forwards to the rendered root — where it doesn't, tag the nearest owned wrapper element already in your markup. Verify in DOM. Full rules in [`test-ids`](../../test-ids/SKILL.md).

## Validation

- License registered from config/secret (no watermark, no license exception); **no key committed**.
- Root/provider component mounted interactively; services registered in both `Program.cs` for Auto/WASM.
- Grid pages/sorts/filters server-side via `OnRead`/`CustomAdaptor`.
- A confirm dialog and a toast fire from an interactive island; dark theme toggles.
