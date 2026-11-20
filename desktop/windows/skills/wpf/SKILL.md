---
name: wpf
description: Use when working in a WPF app on .NET 10/11 (MVVM, Fluent theme opt-in, ThemeMode, dark mode, modernizing in place). Triggers "WPF". Not for moving to WinUI (migration) or WinUI apps (ui-components).
disable-model-invocation: true
---

# Windows — WPF Lane

How a WPF codebase is built and modernized **as WPF**: **MVVM with CommunityToolkit.Mvvm, the Fluent theme as an opt-in, `ThemeMode` for dark mode, the house rules applied to what WPF has, and modernization in place.** The lane stays itself. Moving to WinUI is a `desktop-windows:migration` run, never a side effect (`A6`). Audit rows: section D, tagged `[WPF]`.

## Version lane

| Concern | Primary | Note |
|---|---|---|
| Runtime | **.NET 10 LTS** (`net10.0-windows`); .NET 11 STS supported | .NET 8/9 out of support since 2026-11-10; .NET Framework 4.x is a `migration` finding |
| Fluent theme | Shipped since .NET 9; **.NET 10 added Fluent styles** for `DatePicker`, `GridSplitter`, `GridView`, `GroupBox`, `Hyperlink`, `Label`, `NavigationWindow`, `RichTextBox`, `TextBox` and fixed High Contrast crashes | **Microsoft says "Fluent UI style support is still in progress"** (What's new in WPF for .NET 10). .NET 11 brings bug fixes only (Fluent backdrop on Windows 10, DWM-failure crashes, `WeakEventTable.Purge`). Opt-in per app, never assumed complete |
| `ThemeMode` | `Application.ThemeMode` / `Window.ThemeMode`: `Light`, `Dark`, `System`, `None` | **Was experimental (`WPF0001`) when introduced in .NET 9; re-check the status on the SDK in use.** If the diagnostic still fires, suppress it with a stated reason in the project, never globally |
| MVVM | CommunityToolkit.Mvvm 8.4.2 | `[ObservableProperty]` partial properties on C# 14 |
| New in .NET 10 | `Grid ColumnDefinitions="1*, Auto"` short form; `MessageBox` buttons (`RetryCancel`, `AbortRetryIgnore`, `CancelTryContinue`); clipboard shared with WinForms (`GetData` obsolete for `TryGetData<T>`) | |
| Packaging | Unpackaged by default; MSIX optional | Package identity is needed only for APIs that require it |

## Stay in the lane

- **Detect first:** `UseWPF`, `System.Windows` in `.xaml`, `App.xaml` with `StartupUri`. Report the detected lane and TFM before changing anything.
- **Never add `UseWinUI`, `Microsoft.WindowsAppSDK`, `Microsoft.UI.Xaml` or a WinUI control** to fix a WPF problem. That is a lane change: it needs the owner's decision and the `migration` skill's guide (`A6`).
- **Modernization in place** is the default: .NET 10, nullable on, `Directory.Build.props`, compiled bindings where possible, MVVM Toolkit, Fluent opt-in, `HttpClientFactory`, MSIX packaging if wanted, **WinRT APIs through the TFM** (`net10.0-windows10.0.26100.0`) where a Windows 10/11 feature is needed. The decision guide lists blockers for a later move: WCF server, ASMX, `System.Configuration`, COM, third-party control suites.
- **Third-party control suites** (DevExpress, Telerik, Syncfusion) own their theme: their theme manager is the styling authority, and Fluent is not layered over it.

## Architecture — MVVM with the toolkit

```csharp
public sealed partial class OrdersViewModel(OrdersClient orders) : ObservableObject
{
    [ObservableProperty]
    public partial LoadState<IReadOnlyList<OrderRow>> State { get; private set; } = LoadState.Loading;

    [RelayCommand]
    private async Task LoadAsync(CancellationToken ct) => State = await orders.ListAsync(ct).ToStateAsync();
}
```

- **One view model per view, `sealed partial`**, no code-behind logic (`D3`); a view model has no `Window`, `Dispatcher` or `MessageBox` (`C2`). Dialogs go through a small `IDialogService` only when a view model must ask something and a test fake exists.
- **Host and DI:** `Host.CreateApplicationBuilder()` in `App`, started in `OnStartup`, stopped in `OnExit`; constructor injection, no `App.Current.Services` locator (`C3`). Remove `StartupUri` and resolve `MainWindow` from the container.
- **Bindings:** WPF has no `x:Bind`. Use `{Binding}` with `Mode` stated where it changes and `d:DataContext` / `d:DesignInstance` for the designer; `FallbackValue` and `TargetNullValue` for absent data. Binding errors are a defect: **fail the debug build on them** (`PresentationTraceSources`, a trace listener that throws on `BindingExpression path error`). `D1` and `D2` are `[WinUI]` rows; the WPF equivalent is `D12`.
- **Threading:** a background result reaches the UI through `Dispatcher.InvokeAsync` (batched), or an `await` that resumes on the captured context. Never `Dispatcher.Invoke` (blocks) from a loop, never `.Result` / `.Wait()` (`D17`, `B8`). Collections changed off-thread need `BindingOperations.EnableCollectionSynchronization` or marshalling.
- **Three-state regions** with a scoped failed body and one persistent banner (an `Border`+`TextBlock` + close `Button` strip or a themed `InfoBar`-like control) at the top of the window content (CLAUDE.md § Desktop code rules). Never a `MessageBox` for a background failure.

## Fluent theme — an opt-in

```xml
<Application x:Class="Contoso.Notes.App"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             ThemeMode="System">
```

- **`ThemeMode="System"`** follows the user's light/dark setting and applies the Fluent styles; `Light` / `Dark` force one; `None` is the classic Aero2 look. A window's `ThemeMode` overrides the application's.
- **Equivalent without `ThemeMode`:** merge the Fluent dictionary (`pack://application:,,,/PresentationFramework.Fluent;component/Themes/Fluent.xaml`, with `.Light` / `.Dark` variants) into `Application.Resources`.
- **The accent colour** follows the system accent; read it, never hard-code a brand colour into a control template that fights it.
- **Gaps are expected:** a control without Fluent styles (the .NET 10 list above is what was added; others may remain) keeps the classic look. Check each control used and note the gaps; do not rewrite templates to paper over a gap Microsoft is still closing.
- **High Contrast** must work: use `SystemColors` / `SystemParameters` brushes and `DynamicResource` for theme-varying colours, never a literal. Test every screen in a High Contrast theme (section M). The .NET 10 fixes cover crashes, not every control.
- **Backdrop (Mica):** the Fluent theme applies the system backdrop on Windows 11 (the .NET 11 notes list a Fluent-backdrop fix for Windows 10); not verified per window type, so check the screen. One backdrop per window.
- **One styling authority:** the Fluent theme plus `Application.Resources` token dictionaries (`Brushes.xaml`, `Spacing.xaml`); no per-control inline colours (`D15`).

## Dark mode

- `ThemeMode` for the managed content. The **title bar** follows when the Fluent theme is on; on `ThemeMode="None"` set the immersive dark-mode attribute (`DwmSetWindowAttribute` with `DWMWA_USE_IMMERSIVE_DARK_MODE`) from an `interop` helper keyed to the user's setting (`desktop-windows:interop`).
- **React to the system change** (`SystemEvents.UserPreferenceChanged`, with `ThemeMode="System"` WPF handles it). Unsubscribe static events on window close: `SystemEvents` is a classic leak source.
- **Images and icons** have dark variants or use a monochrome glyph recoloured from `Foreground`.

## Windows, commands and input in WPF

- **Commands:** `RoutedCommand`/`ICommand` bound to menu, toolbar and `InputBindings` from one definition (`F11`); `ApplicationCommands.*` for the standard ones so shortcuts keep their meaning (`F9`); disable, never collapse, an unavailable command (`F10`).
- **Access keys** with `_` in `Header`/`Content`; `Menu` items use `InputGestureText` for accelerators.
- **Window state** (`Left/Top/Width/Height/WindowState`) is saved on close and restored on launch, validated against `SystemParameters.VirtualScreen*` / per-monitor bounds; `Window.Closing` with `e.Cancel` asks about unsaved work (`F2`, `F3`).
- **DPI:** declare per-monitor v2 in `app.manifest` (`<dpiAwareness>PerMonitorV2</dpiAwareness>`), use device-independent units, `UseLayoutRounding="True"`, and snap images with `RenderOptions`.
- **Lists virtualize:** `ListView`/`DataGrid`/`ItemsControl` with `VirtualizingStackPanel.IsVirtualizing="True"` and `VirtualizationMode="Recycling"`; never an `ItemsControl` with a `StackPanel` over unbounded data, never a `ListBox` inside a `ScrollViewer` (`D13`).
- **Forms:** `Binding` with `ValidatesOnNotifyDataErrors=True` and `INotifyDataErrorInfo` (the toolkit's `ObservableValidator`), an error template that shows **text**, not only a red border (`G5`); `PasswordBox` for secrets (a `SecureString` is not needed; clear after use).
- **Accessibility:** `AutomationProperties.Name` / `LabeledBy` / `LiveSetting`, `AutomationProperties.AutomationId` on every interactive element and list container (`desktop-windows:test-ids`); custom controls override `OnCreateAutomationPeer`.

## Performance and leaks that bite WPF

- **Event handlers and `DispatcherTimer`s** attached to long-lived objects keep windows alive: unsubscribe on `Unloaded` / `Closed`; use `WeakEventManager` for cross-lifetime events.
- **`Freezable`s** (brushes, geometries) are frozen when shared; `BitmapImage` uses `CacheOption=OnLoad` and `DecodePixelWidth` for large images.
- **Startup:** no blocking work in `OnStartup`; show the window, then load behind a loading state. `ReadyToRun` helps; Native AOT is not supported for WPF.

## Telemetry

Same base as every desktop app (`desktop-shared:observability`): `ILogger` through the host, a span per command that does I/O, a metric per business event. WPF adds a **first-chance binding-error log** in Debug and an `AppDomain` / `Application.DispatcherUnhandledException` handler that logs and shows the failed state (`desktop-windows:error-handling`).

## Common gotchas

- **`UseWinUI` added "to get a control"** — a lane change; stop and run `migration`.
- **`ThemeMode` set, a control still classic** — Fluent support is in progress; note the gap (`D16`).
- **`WPF0001` suppressed globally** — suppress per project with a reason, or not at all.
- **Binding path typos fail silently** — turn binding errors into build/debug failures.
- **`ObservableCollection` mutated from a thread-pool thread** — marshal, or enable collection sync.
- **A `ScrollViewer` around a `ListView`** — virtualization is off; remove the wrapper.
- **`StartupUri` left in while DI builds the window** — two windows.
- **Static `SystemEvents` handlers not removed** — the window never collects.
- **Literal colours** — break High Contrast and dark.
