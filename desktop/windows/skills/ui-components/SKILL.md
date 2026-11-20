---
name: ui-components
description: Use when writing WinUI XAML (pages, user controls, x:Bind, DataTemplates, virtualized lists, InfoBar, ContentDialog). Triggers "build this screen". Not for state ownership (architecture).
disable-model-invocation: true
---

# Windows — UI Components (WinUI XAML)

How pages and controls are written: **`x:Bind` to a view model, thin code-behind, `DataTemplate`s with `x:DataType`, virtualized lists, a three-state region with an `InfoBar` for failure, restrained `ContentDialog`, production-channel controls only.** Audit rows: section D of `desktop-windows:standards-audit`. Design facts: `design/ui-ux-pro-max --stack winui`.

## Version lane

| Concern | WinUI on WinAppSDK 2.6 (primary) | Other |
|---|---|---|
| Binding | `x:Bind` (compiled, typed, AOT-safe) | WPF: `{Binding}` is the norm there → `desktop-windows:wpf` |
| `Window` | `Window.AppWindow`, `TitleBar` control → `desktop-windows:windows-and-navigation` | — |
| Production controls | Stable channel: `ListView`, `GridView`, `ItemsRepeater`, `NavigationView`, `TabView`, `InfoBar`, `NumberBox`, `TeachingTip`, `ContentDialog`, `Expander`, `BreadcrumbBar`, `Pager`… | — |
| **Experimental only** | `TableView` (2.5.4-exp; not a DataGrid replacement), `Chart` (line/area/bar, closed source), `InkCanvas` / `InkToolbar` (2.4.1-exp) | **Never in a production build or recipe.** For tables use `ListView` with a header row, or the Windows Community Toolkit `DataGrid` only if the project already ships it |
| XAML Designer | Not available for WinUI in Visual Studio (no date) — use Hot Reload and `winapp ui inspect` | — |

## When to use

- Writing or refactoring a page, a user control, a template or a list
- "Why is the list slow?", "`x:Bind` or `{Binding}`?", "where does the error show?", "dialog or `InfoBar`?"
- Choosing a control

## When NOT to use

- View-model shape, state types, DI → [`architecture`](../architecture/SKILL.md)
- Theme, colour, type ramp, Mica, motion → [`styling`](../styling/SKILL.md)
- Windows, titlebar, `NavigationView` + `Frame`, commands, access keys → `desktop-windows:windows-and-navigation`
- Text input, validation, `NumberBox`, focus order → `desktop-windows:forms`
- UI Automation labels → `desktop-windows:accessibility`; automation ids → `desktop-windows:test-ids`
- WPF / WinForms controls → `desktop-windows:wpf`, `:winforms`

---

## A page

```xml
<Page x:Class="OrdersApp.Views.OrdersPage"
      xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
      xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
      xmlns:vm="using:OrdersApp.ViewModels"
      xmlns:m="using:OrdersApp.Models">
  <Grid Padding="24">
    <Grid.RowDefinitions>
      <RowDefinition Height="Auto" />
      <RowDefinition Height="Auto" />
      <RowDefinition Height="*" />
    </Grid.RowDefinitions>
    <TextBlock Style="{StaticResource TitleTextBlockStyle}" x:Uid="OrdersTitle" />
    <InfoBar Grid.Row="1" IsOpen="{x:Bind ViewModel.HasBanner, Mode=OneWay}"
             Severity="Error" IsClosable="True"
             Title="{x:Bind ViewModel.BannerTitle, Mode=OneWay}"
             AutomationProperties.AutomationId="Orders.ErrorBanner" />
    <ListView Grid.Row="2" ItemsSource="{x:Bind ViewModel.Orders, Mode=OneWay}"
              SelectionMode="Single" IsItemClickEnabled="True"
              AutomationProperties.AutomationId="Orders.List">
      <ListView.ItemTemplate>
        <DataTemplate x:DataType="m:Order">
          <TextBlock Text="{x:Bind Title}" />
        </DataTemplate>
      </ListView.ItemTemplate>
    </ListView>
  </Grid>
</Page>
```

```csharp
public sealed partial class OrdersPage : Page
{
    public OrdersViewModel ViewModel { get; }

    public OrdersPage(OrdersViewModel viewModel)
    {
        ViewModel = viewModel;
        InitializeComponent();
    }
}
```

- **The page exposes its view model as a get-only property** and binds with `x:Bind ViewModel.…`. Constructor-injected through the host ([`architecture`](../architecture/SKILL.md)); the page never `new`s it or locates it.
- **Code-behind is view code:** focus, animation hooks, a `Loaded` handler that invokes a command. No business logic, no HTTP, no storage.

## `x:Bind` rules

- **Mode is explicit for anything that changes:** default `OneTime` silently stops updating. `OneWay` for display, `TwoWay` for input. Add `UpdateSourceTrigger=PropertyChanged` only where live validation needs it.
- **Functions in `x:Bind`** (`Text="{x:Bind local:Fmt.Price(Total), Mode=OneWay}"`) replace converters for one-off formatting. `IValueConverter` only where a resource-level converter is reused.
- **Every `DataTemplate` declares `x:DataType`** — required for `x:Bind` in a template and what makes it compiled.
- **`x:Bind` events** (`Click="{x:Bind ViewModel.Save}"`) bind straight to a view-model method; prefer a `Command` binding for anything with `CanExecute`.
- **`{Binding}` is reflection** and is a finding in a WinUI app (breaks Native AOT and trimming). Allowed only where `x:Bind` cannot reach (some `ItemsPanel` / theme-dictionary scenarios), with the reason noted in the PR.
- **`x:Load`** defers realising rarely shown subtrees (a failed-state body, an empty state); `Visibility` only hides.

## Lists — always virtualized

- **`ListView` / `GridView` virtualize by default; `ItemsRepeater` with `StackLayout` / `UniformGridLayout` for custom layouts.** A list over about 20 items **must** virtualize. Putting a `ListView` inside a `ScrollViewer` or a `StackPanel` **disables** virtualization (infinite height) — a finding; give the list a bounded height (a `Grid` row with `*`).
- **Never `ItemsControl` in a `ScrollViewer` for data of unknown length;** never an `ItemsRepeater` without a `ScrollViewer` ancestor or `ItemsRepeaterScrollHost`.
- **A stable item identity:** bind to a collection of records with a domain id; do not rebuild the whole `ObservableCollection` per refresh — diff and `Add`/`Remove`/`Move`, or replace `ItemsSource` once.
- **Large or growing data:** `ISupportIncrementalLoading` / `IncrementalLoadingTrigger`, with the loading and failed states of the **tail** handled (a footer row with retry).
- **Fixed-size item templates and no nested layout depth** keep realisation cheap; use `x:Phase` for staged rendering of heavy `GridView` items.
- **Each row's container** carries an automation id that does not contain the row's id, value or index (`desktop-windows:test-ids`).

## The three-state region

A response-dependent region renders from the view model's sealed state ([`architecture`](../architecture/SKILL.md)); each state is a real subtree:

| State | Shows |
|---|---|
| Loading | `ProgressRing` (or skeleton rows) in place of the content, not over a blank page |
| Loaded | The list or content; `IsStale` adds a "last updated" text, never silence |
| Failed | A body in the region's own place: typed message, a **Retry** button, an offline variant told apart from a server error |
| Empty (a loaded state) | A message and the next action — never a blank list |

- **Scope the failure.** The title, search box, filters and toolbar keep rendering; only the region's body swaps. A drifted or unparseable response is *failed*, never empty.
- **Every surfaced failure also sets the one persistent `InfoBar`** at the top of the window content (`Severity="Error"`, `IsClosable="True"`) that only the user closes: no auto-dismiss, no `DispatcherTimer` closing it. A **background** failure never raises a `ContentDialog` or `MessageBox`.
- **Never leak `Exception.Message`.** Show a localised string mapped from the typed failure reason (`x:Uid` / `.resw` via `desktop-windows:languages`).
- **State switching:** bind visibility with a function (`x:Bind local:Vis.IsLoading(ViewModel.State), Mode=OneWay`) or a `VisualStateManager` with `StateTrigger`s. No three booleans on the view model.

## Dialogs and flyouts

- **`ContentDialog` is for a decision the user must make now,** not for errors, progress or information. One at a time (a second `ShowAsync` throws); set `XamlRoot` (`this.XamlRoot`) or it throws.
- **Defaults are the safe action;** the destructive button is never the default; `Escape` closes; the primary button label names the verb ("Delete order"), not "OK".
- **`ShowAsync()` is awaited,** and the result is read in the view, then forwarded to a command; the view model never shows a dialog (cannot be unit tested) — a confirmation service in the app project wraps it if several view models need it, on the second need (CLAUDE.md § Simplicity).
- **Quitting with unsaved work asks first** (`AppWindow.Closing` cancel + dialog), `desktop-windows:windows-and-navigation`.
- **`TeachingTip`** for one-time guidance; **`Flyout`** for contextual choices; **`InfoBar`** for status. A modal used for a toast-like message is a finding.

## Controls — choose the semantic one

| Need | Use | Not |
|---|---|---|
| Navigate in-app | `NavigationView` items / `HyperlinkButton` with `NavigateUri` | A `Button` whose `Click` calls `Frame.Navigate` where the destination is a link-like destination |
| Command | `Button`, `AppBarButton` in `CommandBar`, `MenuFlyoutItem` with `Command` | A `Grid` / `Border` with `Tapped` |
| Binary choice | `ToggleSwitch` (immediate), `CheckBox` (applied with a button) | A `Button` that toggles text |
| Select one of few | `RadioButtons`, `ComboBox` for many | A `ListView` for 3 options |
| Hierarchy | `TreeView`, `Expander`, `BreadcrumbBar` | Nested `StackPanel`s |
| Tabs | `TabView` (documents) / `SelectorBar` / `Pivot` (legacy: avoid in new code) | Hand-rolled `Button` rows |

- **In-app navigation that is a link is a `HyperlinkButton` / `NavigationView` item,** not a click handler on a panel.
- **Interactive containers are real controls** (focusable, keyboard-operable, announced); a `Border` with `PointerPressed` is invisible to keyboard and Narrator.
- **Access keys on commands** (`AccessKey="S"`) and accelerators come from `desktop-windows:windows-and-navigation`; every command reachable by keyboard.
- **Icon-only buttons** have `ToolTipService.ToolTip` **and** `AutomationProperties.Name`.
- **Content before chrome:** one primary action per region (`AccentButtonStyle`); the rest are standard buttons.

## Custom controls

- **`UserControl` for a reusable composition with its own view model** or `DependencyProperty`s; a `Page` per navigable destination.
- **`DependencyProperty` only for a property the XAML must bind to;** a plain property otherwise. Register with `DependencyProperty.Register` in a `static readonly` field (a constant, not static mutable state).
- **A templated control (`Control` + `Generic.xaml`) only on the second consumer.** One screen's repeated markup is a `DataTemplate` or a user control.
- **No custom control for what an existing control with a style already does.**

## Common gotchas

- **`ListView` inside `ScrollViewer` / `StackPanel`** — disables virtualization; give it a bounded row.
- **`x:Bind` with no `Mode`** — the UI never updates after load.
- **`ContentDialog` with no `XamlRoot`** — throws in a `Window`-hosted page.
- **Showing a second `ContentDialog`** while one is open — `COMException`; serialise.
- **`DataTemplate` with no `x:DataType`** — `x:Bind` does not compile in it.
- **Using `TableView` or `Chart`** — experimental channel; never ships.
- **A control manipulated from a worker thread** — dispatcher rule in [`basics`](../basics/SKILL.md).
- **Hex colours and `FontSize` literals** — [`styling`](../styling/SKILL.md).

## Handoffs

- State types, view models, host → [`architecture`](../architecture/SKILL.md)
- Theme, type ramp, Mica, icons, motion, DPI → [`styling`](../styling/SKILL.md)
- Navigation, `AppWindow`, titlebar, commands → `desktop-windows:windows-and-navigation`
- Forms and validation → `desktop-windows:forms`
- Labels, UIA, High Contrast, text scaling → `desktop-windows:accessibility`
- Automation ids → `desktop-windows:test-ids`
- Startup, virtualization measurement → `desktop-windows:performance`
- WPF / WinForms lanes → `desktop-windows:wpf`, `:winforms`
