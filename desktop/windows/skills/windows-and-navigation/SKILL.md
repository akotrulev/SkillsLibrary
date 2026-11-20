---
name: windows-and-navigation
description: Use when writing WinUI windows, title bar, multi-window, NavigationView + Frame, TabView, commands, access keys. Triggers "add a window". Not for single instancing (activation-and-notifications).
disable-model-invocation: true
---

# Windows — Windows, Navigation and Commands

How a WinUI app opens, sizes, remembers and navigates its windows: **`Window.AppWindow`, the `TitleBar` control, one shared source of truth across windows, `NavigationView` + `Frame`, and every command reachable from the keyboard.** Audit rows: section F of `desktop-windows:standards-audit`. Design facts: `design/ui-ux-pro-max --stack winui`.

## Version lane

| Concern | WinUI on WinAppSDK 2.6 (primary) | Note |
|---|---|---|
| Title bar | `TitleBar` control (since 1.7; drag regions automatic since 2.1.3: `IsDragRegion`, `AutoRefreshDragRegions`) | `ExtendsContentIntoTitleBar` must be `true` before `PreferredHeightOption = Tall` |
| Window API | `Window.AppWindow` (`Presenter`, `Size`, `Move`, `Closing`, `Changed`, `Id`) | Win32 `HWND` only through `WinRT.Interop` → `desktop-windows:interop` |
| Backdrop | `Window.SystemBackdrop`, one per window → [`styling`](../styling/SKILL.md) | — |
| Navigation | `NavigationView` + `Frame` (2.5.1 fixed pane and flyout crashes) | `Pivot` is not used in new code |
| WPF / WinForms | `Window` / `Form` with their own APIs | → `desktop-windows:wpf`, `:winforms`; never add WinUI to them |

Detect the lane from `basics` (`desktop-windows:concepts`) first. A TFM, SDK or framework change is never a side effect of this work.

## The window rules (CLAUDE.md § Desktop code rules)

1. **Resizable, with a stated minimum.** Set the minimum through `OverlappedPresenter.PreferredMinimumWidth` / `PreferredMinimumHeight` (effective pixels), never by a fixed page `Width`.
2. **Restores size and position.** Save `AppWindow.Position`, `Size` and `Presenter` state on `Closing` and apply them on launch. Validate against `DisplayArea.GetFromPoint` / `DisplayArea.FindAll()` — a saved position on a monitor that is gone must land on a live one.
3. **Survives a DPI or monitor change.** Per-monitor DPI v2; layout in effective pixels; never cache `RasterizationScale`. Test 100 %, 150 %, 200 % and a window dragged between monitors.
4. **Several windows share one source of truth.** Each window's view model takes the same singleton service; none loads its own copy.
5. **Work a window starts is cancelled when it closes.** The view model owns a `CancellationTokenSource`; `Closed` cancels it and unsubscribes.
6. **Quitting with unsaved work asks first,** and relaunch restores state.
7. **No `Thread.Sleep`, no blocking on the UI thread;** results return through `DispatcherQueue.TryEnqueue`, batched.

### Create, remember, restore

```csharp
public sealed partial class MainWindow : Window
{
    private readonly WindowPlacementStore _placement;

    public MainWindow(MainViewModel viewModel, WindowPlacementStore placement)
    {
        ViewModel = viewModel;
        _placement = placement;
        InitializeComponent();
        ExtendsContentIntoTitleBar = true;
        AppWindow.Closing += OnClosing;
        _placement.Restore(AppWindow);
    }

    public MainViewModel ViewModel { get; }

    private void OnClosing(AppWindow sender, AppWindowClosingEventArgs args)
    {
        if (ViewModel.HasUnsavedChanges)
        {
            args.Cancel = true;
            _ = ConfirmCloseAsync();
            return;
        }
        _placement.Save(sender);
        ViewModel.Cancel();
    }
}
```

`WindowPlacementStore` writes through the storage the project already has (`desktop-windows:offline-and-storage`); it is a class, not an interface, until a second implementer exists.

### Unsaved-work prompt

The decision is a `ContentDialog` with `XamlRoot = Content.XamlRoot`, a non-destructive default, and labels that name the action ("Save", "Discard", "Cancel"), never "OK". `Window.Closed` cannot be cancelled; `AppWindow.Closing` can — use it.

### Multi-window

```csharp
public sealed class WindowFactory(IServiceProvider services)
{
    public Window OpenDetail(Guid documentId)
    {
        var window = ActivatorUtilities.CreateInstance<DetailWindow>(services, documentId);
        window.Activate();
        return window;
    }
}
```

Each window has its own `DispatcherQueue` only when created on another thread; a second window on the UI thread shares it. Track open windows in a service so a re-open of the same document activates the existing window instead of opening a copy.

## The title bar

- Use the **`TitleBar` control** and `Window.SetTitleBar(titleBar)`. Keep caption buttons system-drawn.
- `Tall` height only when the bar holds interactive content (search, tabs) and only after `ExtendsContentIntoTitleBar = true`.
- Interactive content in the bar is a real control with `AutomationProperties.Name` and `AutomationId`. A back button goes in the `TitleBar`'s `IsBackButtonVisible`, not hand-drawn.
- Mica shows through the bar; never paint it opaque ([`styling`](../styling/SKILL.md)).

## Navigation

| Shape | Use |
|---|---|
| A handful of top-level sections | `NavigationView` (left pane) + one `Frame` |
| Many documents of one kind | `TabView` (tabbed `TitleBar`, Mica Alt) |
| A drill-down inside a section | `Frame.Navigate` + `BreadcrumbBar` or the back button |
| Detail on the same screen | a split view, not a new window |

- **Navigation items are real `NavigationViewItem`s** with `Tag` or `x:Name` mapped to a page type — never a `Border` with `Tapped` that calls `Frame.Navigate` (`D9`).
- **Back is wired.** `NavigationView.IsBackEnabled` follows `Frame.CanGoBack`; `Alt+Left`, the mouse back button and the title-bar back all call one handler.
- **Page parameters are untrusted when they come from activation** (deep link, file, toast). Parse and validate into a typed record before `Frame.Navigate` (`desktop-windows:activation-and-notifications`).
- **State survives navigation:** set `Page.NavigationCacheMode` only where re-creating the page loses user input; the view model, not the page, owns the data.
- Selecting a section announces it: the page's `Title` or a focus move to the page heading so Narrator reads the change.

```xml
<NavigationView x:Name="Nav" AutomationProperties.AutomationId="Shell.Navigation"
                IsBackEnabled="{x:Bind ContentFrame.CanGoBack, Mode=OneWay}"
                SelectionChanged="OnSelectionChanged" BackRequested="OnBackRequested">
    <NavigationView.MenuItems>
        <NavigationViewItem Content="Orders" Tag="Orders"
                            AutomationProperties.AutomationId="Shell.Navigation.Orders">
            <NavigationViewItem.Icon><FontIcon Glyph="&#xE7BF;"/></NavigationViewItem.Icon>
        </NavigationViewItem>
    </NavigationView.MenuItems>
    <Frame x:Name="ContentFrame" AutomationProperties.AutomationId="Shell.ContentFrame"/>
</NavigationView>
```

The handlers only forward to a navigation service or call `ContentFrame.Navigate`; the section-to-page map is data, not a `switch` of business rules.

## Commands

**Every command is reachable from the keyboard** and has one definition used everywhere it appears (menu, toolbar, context menu, accelerator).

- **`XamlUICommand` / `StandardUICommand`** bind label, icon, accelerator and `Command` once; use `StandardUICommand` (`Save`, `Delete`, `Open`, `Copy`, `Paste`, `Undo`) for the standard ones so the shortcut and text match the OS.
- **`KeyboardAccelerator`** on the control or a root `UIElement.KeyboardAccelerators`: `Ctrl+N`, `Ctrl+O`, `Ctrl+S`, `Ctrl+W`, `Ctrl+F`, `F5`, `Ctrl+Z`, `Ctrl+Y`, `Delete`. **Keep the standard shortcuts** and never rebind them to something else.
- **`AccessKey`** (`Alt` sequences) on menu bar items, tabs and dialog buttons; unique inside one scope.
- **`MenuBar`** for an app with many commands; **`CommandBar` / `AppBarButton`** for the page's actions; **`MenuFlyout`** for context menus, also opened by the `Menu` key and `Shift+F10`.
- **A disabled command stays visible and disabled.** Drive `CanExecute` from view-model state; do not collapse the item.
- **Destructive commands** confirm or are undoable; never an accelerator-only delete with no undo.
- Commands are `[RelayCommand]` on the view model ([`architecture`](../architecture/SKILL.md)); the XAML binds with `x:Bind ViewModel.SaveCommand`.
- **Focus order is complete and visible:** logical `TabIndex`, `IsTabStop` only on real stops, `FocusVisualPrimaryBrush` untouched, `TabFocusNavigation` set on composite regions.
- **Icon-only buttons** carry `ToolTipService.ToolTip` and `AutomationProperties.Name` (`D10`).

```xml
<CommandBar DefaultLabelPosition="Right" AutomationProperties.AutomationId="Orders.Toolbar">
    <AppBarButton Command="{x:Bind ViewModel.SaveCommand}" Label="Save" Icon="Save"
                  AutomationProperties.AutomationId="Orders.Toolbar.Save">
        <AppBarButton.KeyboardAccelerators>
            <KeyboardAccelerator Key="S" Modifiers="Control"/>
        </AppBarButton.KeyboardAccelerators>
    </AppBarButton>
</CommandBar>
```

## Common gotchas

- **`Closing` cancelled after `Closed` hooks ran** — do the unsaved check in `AppWindow.Closing`, not `Window.Closed`.
- **A saved position off-screen after a monitor is unplugged** — validate against current `DisplayArea`s on restore.
- **`ExtendsContentIntoTitleBar` set after `Tall`** — the height silently reverts; order matters.
- **`XamlRoot` null for a dialog** — a dialog from a window not yet loaded; open it from `Loaded` or after activation.
- **An accelerator on a collapsed element does not fire** — put global shortcuts on the root, not on a hidden flyout item.
- **A second window per document opened every time** — look it up first.
- **`NavigationView` selection set in code re-navigates** — guard `SelectionChanged` against the programmatic change.
