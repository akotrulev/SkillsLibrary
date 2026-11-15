# desktop-windows Conformance Checklist — the 21 sections

The audit's spine. Section letters and check numbers are **permanent** — a finding is `<letter><n>` (`B3`, `M1`) and keeps that ID across every round, forever. Never renumber; append new checks at the end of a section with the next free number. The letters are identical on both desktop platforms (`macos`, `windows`) and keep their meaning from the mobile checklists: `M` is Accessibility everywhere. `Q` (motion) and `T` (release) are unused: motion is in E, release in L.

**How to read a row.** *Check* = the invariant. *Violation looks like* = what disqualifies it. *Find it with* = a mechanical lead (a grep hit is never a finding — read the code). *Sev* = the default severity; adjust for real impact and say why.

**Recipes** use `rg` (ripgrep), which honours `.gitignore` — so `bin/`, `obj/` and `x64/` when ignored are skipped without flags. Without ripgrep, `grep -rn --include='*.cs' --include='*.xaml' --include='*.cpp' --include='*.h' --exclude-dir=bin --exclude-dir=obj` is equivalent. Set the source roots once:

```bash
SRC=$(ls -d src Source App *App* 2>/dev/null | tr '\n' ' ')   # adjust to the repo layout
rg -n "<pattern>" $SRC -g '*.cs'   # the shape every recipe below uses
```

If the repo gitignores generated sources (`*.g.cs`, `*.g.i.cs`, `Generated Files/`) you still need to read, add `--no-ignore` and exclude it explicitly — and say so in the report's coverage line.

**The version lane gates everything.** Before flagging, confirm the check applies to the detected target framework and Windows App SDK major (2.x primary), the UI framework (WinUI, WPF, WinForms) and whether the app is packaged. Rows tagged **[WinUI]**, **[WPF]**, **[WinForms]**, **[C++]**, **[packaged]** and **[unpackaged]** apply only in that lane.

**Fragment sections.** K, L and U carry no rows here: their rows live in `desktop/_shared/<skill>/references/audit-checks.md` and are filtered by the `Platforms` column. X is owned by `interop` and `cpp-winrt` and is not applicable without P/Invoke, COM or C++ projects. Every other section is filled by the task that writes its skill — an empty section means that skill is not written yet, not that the code passes.

**Severity.** blocker — ships a crash, a store or notarization rejection, or a hard security rule break. major — a rule in CLAUDE.md § Desktop code rules broken where it will hurt soon. minor — style, naming, a single missing label. nit — preference.

---

## A — Version lane, toolchain & migration hygiene
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`migration`](../../migration/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| A1 | The .NET and Windows App SDK lane is detected, and nothing above it is used | TFM, `Microsoft.WindowsAppSDK` major or C# version raised as a side effect of other work | `rg -n "TargetFramework\|WindowsAppSDK\|LangVersion" -g '*.csproj' -g '*.props'` | major |
| A2 | No out-of-support runtime or SDK is targeted | `net8.0-windows` / `net9.0-windows` (out of support since 2026-11-10), .NET Framework, or `global.json` pinning 8 / 9 — a migration finding, never silently raised | `rg -n "<TargetFramework>net(4\|core\|5\|6\|7\|8\|9)" -g '*.csproj' -g '*.props'`; `rg -n '"version": "(8\|9)\.' global.json` | major |
| A3 | Windows App SDK is on the 2.x stable channel `[WinUI]` | `Microsoft.WindowsAppSDK` 1.x, or any `*-experimental` / `-preview` version in a production build | `rg -n "Microsoft.WindowsAppSDK" -g '*.csproj' -g 'Directory.Packages.props'` | blocker |
| A4 | `TargetPlatformMinVersion` is written explicitly `[WinUI]` | Property absent on the app project (the template default is not documented), or raised with no recorded reason | `rg -n "TargetPlatformMinVersion\|TargetFramework>" -g '*.csproj'` | minor |
| A5 | The TFM carries the OS part on every UI project | `net10.0` on a project that uses `UseWinUI` / `UseWPF` / `UseWindowsForms` | `rg -n "<TargetFramework>net[0-9.]+<" -g '*.csproj'`; read each hit against its `Use*` property | major |
| A6 | The UI framework is not changed as a side effect `[WPF]` `[WinForms]` | `UseWinUI` or a `Microsoft.WindowsAppSDK` reference added to a WPF or WinForms project with no migration task | `rg -n "UseWinUI\|Microsoft.WindowsAppSDK" -g '*.csproj'`; read the lane per project | major |
| A7 | Detected-not-taught stacks are named, not guided | A MAUI, Avalonia or Uno project reviewed against WinUI rules, or the report is silent about it | `rg -ln "UseMaui\|Avalonia\|Uno\.Sdk" -g '*.csproj' -g 'global.json'` | minor |

---

## B — Project structure, strictness & language standard
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| B1 | Nullable reference types are on and warnings fail the build | `<Nullable>` absent or `disable`; `TreatWarningsAsErrors` absent or `false`; `#nullable disable` in source | `rg -n "<Nullable>\|TreatWarningsAsErrors" -g '*.csproj' -g '*.props'`; `rg -n "#nullable disable" -g '*.cs'` | major |
| B2 | One `Directory.Build.props` and central package versions | A `Version=` on a `PackageReference` in a `.csproj`; the same property repeated per project; no `Directory.Packages.props` | `rg -n "PackageReference.*Version=" -g '*.csproj'`; `rg -ln "ManagePackageVersionsCentrally" -g '*.props'` | minor |
| B3 | The WinUI analyzer is on every WinUI app project `[WinUI]` | `Microsoft.Windows.SDK.BuildTools.WinUIAnalyzer` absent from an app project | `rg -n "WinUIAnalyzer" -g '*.csproj' -g 'Directory.Packages.props'` | minor |
| B4 | Packaged MSIX unless a reason is recorded `[WinUI]` | `<WindowsPackageType>None</WindowsPackageType>` with no recorded reason; no `Package.appxmanifest`; ClickOnce on a WinUI app | `rg -n "WindowsPackageType\|ClickOnce\|PublishSingleFile" -g '*.csproj' -g '*.pubxml'`; `rg -ln "Package.appxmanifest" -g '*.csproj'` | major |
| B5 | View models and services sit in a library that cannot reference controls | A `ViewModels/` or `Services/` folder in the WinUI project that uses `Microsoft.UI.Xaml` types | `rg -n "using Microsoft.UI.Xaml" -g '*ViewModel*.cs' -g '*Service*.cs'` | major |
| B6 | Platforms are `x64;ARM64`, never `Any CPU`, on a packaged project `[packaged]` | `AnyCPU` platform on the app project; only x64 with no recorded reason | `rg -n "<Platforms>\|AnyCPU\|RuntimeIdentifiers" -g '*.csproj' -g '*.sln'` | minor |
| B7 | `async void` only on an event handler, with a `try`/`catch` body | `async void` on a non-handler; a handler with no `catch` | `rg -n "async void" -g '*.cs'`; read each hit | major |
| B8 | `.Result`, `.Wait()`, `GetAwaiter().GetResult()` are absent from production code | Any of them outside a test; on the UI thread this deadlocks | `rg -n "\.Result\b\|\.Wait\(\)\|GetAwaiter\(\)\.GetResult" -g '*.cs'` | blocker |
| B9 | Logging uses message templates, never interpolation | `LogInformation($"…")`, `string.Format` in a log call, a token or user data in a message | `rg -n "Log(Trace\|Debug\|Information\|Warning\|Error\|Critical)\(\$\"" -g '*.cs'` | major |
| B10 | No static mutable state, no `null!` suppressions | A `static` field assigned after load; `Ioc.Default` / `App.Current` used as a locator; `!` used to silence nullable outside tests | `rg -n "static (?!readonly)[A-Za-z<>\[\]?]+ _?[a-z]\w* *(=\|;)" -g '*.cs' --pcre2`; `rg -n "null!\|Ioc\.Default" -g '*.cs'` | major |
| B11 | Time comes from `TimeProvider`, not `DateTime.Now` / `UtcNow` | `DateTime.Now` or `DateTimeOffset.UtcNow` in logic a test must control | `rg -n "DateTime(Offset)?\.(Utc)?Now" -g '*.cs'` | minor |
| B12 | The C++ build is strict and the language is not raised `[C++]` | `/W4`, `/WX` or `/permissive-` missing on a project; `LanguageStandard` raised, or `WarningLevel` lowered, with no recorded decision; `#pragma warning(disable` in own code | `rg -n "WarningLevel\|TreatWarningAsError\|ConformanceMode\|LanguageStandard" -g '*.vcxproj' -g '*.props'`; `rg -n "pragma warning" -g '*.cpp' -g '*.h'` | major |

---

## C — Architecture, state & DI
*Owning skill: [`architecture`](../../architecture/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| C1 | One view model per screen, `sealed partial`, built on CommunityToolkit.Mvvm | Hand-written `INotifyPropertyChanged` and `ICommand` boilerplate; a view model that is not `sealed`; field-style and partial-property `[ObservableProperty]` mixed in one project | `rg -n "INotifyPropertyChanged\|: ICommand" -g '*.cs'`; `rg -n "\[ObservableProperty\]" -A1 -g '*.cs'` | minor |
| C2 | A view model never touches the UI | `Window`, `Page`, `Frame`, `DispatcherQueue`, `ContentDialog` or any `Microsoft.UI.Xaml` type inside a view model | `rg -n "Microsoft.UI.Xaml\|DispatcherQueue\|ContentDialog" -g '*ViewModel*.cs'` | major |
| C3 | Dependencies arrive through the constructor; there is no service locator | `Ioc.Default.GetService`, `App.Current.Services`, `IServiceProvider` injected into a view model, `new` of a service in a page | `rg -n "Ioc\.Default\|GetRequiredService\|GetService<\|IServiceProvider" -g '*.cs'`; allow only the composition root | major |
| C4 | One Generic Host composition root; lifetimes are right | Services registered in several places; a singleton view model; `AddScoped` with no scope; the host never disposed | `rg -n "AddSingleton\|AddTransient\|AddScoped\|Host\.CreateDefaultBuilder" -g '*.cs'` | major |
| C5 | A data region's state is one sealed type, switched exhaustively | Three booleans (`IsLoading`, `IsError`, `HasData`); a `_` arm on a state `switch` | `rg -n "bool (IsLoading\|IsBusy\|IsError\|HasError)" -g '*.cs'`; `rg -n "_ =>" -g '*ViewModel*.cs'` | major |
| C6 | A failure holds a typed reason, never `Exception.Message` | `State = new Failed(ex.Message)`; `ErrorText = ex.Message` bound to the UI | `rg -n "\.Message\b" -g '*ViewModel*.cs'` | major |
| C7 | An async command accepts and honours a `CancellationToken`; work stops when its window closes | `[RelayCommand]` on `async Task` with no token; a token created and never cancelled; a worker that outlives its window | `rg -n "\[RelayCommand" -A2 -g '*.cs'`; `rg -n "CancellationTokenSource" -g '*.cs'` | major |
| C8 | A failure also sets the one persistent banner | A failed region with no `InfoBar`; the banner auto-dismissed by a timer; a `ContentDialog` or message box for a background failure | `rg -n "InfoBar" -g '*.xaml'`; `rg -n "DispatcherTimer" -g '*.cs'`; `rg -n "MessageBox\|ContentDialog" -g '*ViewModel*.cs' -g '*Service*.cs'` | major |
| C9 | Several windows on the same data share one source of truth | Each window's view model loads and holds its own copy of the same data | read the services each multi-window view model takes | major |
| C10 | A messenger is used only between unrelated view models | `WeakReferenceMessenger` for parent→child or request/response calls | `rg -n "Messenger\.(Default\|Send\|Register)\|WeakReferenceMessenger" -g '*.cs'`; read each hit | minor |
| C11 | No interface with one implementer and no test fake | `IFooService` with a single `FooService` and no fake in the tests | `rg -n "^\s*(public \|internal )?interface I\w+Service" -g '*.cs'`; count implementers | major |
| C12 | C++ dependencies are constructor parameters; no static mutable state or locator `[C++]` | A namespace-scope or `static` non-const object holding a service; an `extern` global; a runtime class that fetches its client from a singleton | `rg -n "^(static\|inline) (?!constexpr\|const )[\w:<>]+ \w+ *(=\|;\|\{)" -g '*.cpp' -g '*.h' --pcre2`; `rg -n "^extern " -g '*.h'` | major |

---

## D — UI components & platform conventions
*Owning skills: [`ui-components`](../../ui-components/SKILL.md) · [`wpf`](../../wpf/SKILL.md) · [`winforms`](../../winforms/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| D1 | Compiled bindings: `x:Bind`, not `{Binding}` `[WinUI]` | `{Binding …}` in a WinUI page or template (reflection; breaks Native AOT and trimming) | `rg -n "\{Binding" -g '*.xaml'` | major |
| D2 | `x:Bind` states its `Mode` where the value changes; every `DataTemplate` has `x:DataType` `[WinUI]` | A changing value bound with the `OneTime` default; a `DataTemplate` with no `x:DataType` | `rg -n "x:Bind" -g '*.xaml'` (hits with no `Mode=`); `rg -n "<DataTemplate>" -g '*.xaml'` | major |
| D3 | Code-behind holds view concerns only | Business logic, HTTP, storage or navigation decisions in `*.xaml.cs` | `rg -n "HttpClient\|File\.\|SqliteConnection\|DbContext" -g '*.xaml.cs'`; read each `*.xaml.cs` over 80 lines | major |
| D4 | Long lists virtualize `[WinUI]` | A `ListView` / `GridView` inside a `ScrollViewer` or `StackPanel`; an `ItemsControl` over unbounded data; `ItemsRepeater` with no scroll host | `rg -n "<ScrollViewer\|<StackPanel" -A3 -g '*.xaml'` for a `ListView` child; `rg -n "<ItemsControl" -g '*.xaml'` | major |
| D5 | Every data region renders loading, loaded and failed from its state | A region with no failed body; a blank list for an empty result; a failure that blanks the toolbar or filters | read each page's region markup against its view-model state | major |
| D6 | The failed state is scoped, with one persistent `InfoBar` | An `InfoBar` with `IsClosable="False"` and no way out, or auto-closed; the failure replaces the whole page | `rg -n "<InfoBar" -A4 -g '*.xaml'` | major |
| D7 | `ContentDialog` is for a decision, set up correctly | A dialog used for an error, progress or information; no `XamlRoot`; a destructive default button; "OK" as the primary label | `rg -n "new ContentDialog\|ContentDialog" -A6 -g '*.cs' -g '*.xaml'` | major |
| D8 | Experimental-channel controls never ship `[WinUI]` | `TableView`, `Chart`, `InkCanvas`, `InkToolbar` or `SetThemeResourceBinding` in a production project | `rg -n "TableView\|<.*Chart\|InkCanvas\|InkToolbar\|SetThemeResourceBinding" -g '*.xaml' -g '*.cs' -g '*.csproj'` | blocker |
| D9 | In-app navigation is a real link or `NavigationView` item; interactive containers are real controls | A `Border` / `Grid` / `StackPanel` with `Tapped` or `PointerPressed` doing the work of a button or link | `rg -n "Tapped=\|PointerPressed=\|Frame\.Navigate" -g '*.xaml' -g '*.cs'` | major |
| D10 | An icon-only control has a tooltip and an accessible name | `AppBarButton` / `Button` with only an `Icon` and neither `ToolTipService.ToolTip` nor `AutomationProperties.Name` | `rg -n "<(AppBarButton\|Button)[^>]*Icon=" -g '*.xaml'`; read each hit | major |
| D11 | Every control comes from the semantic choice | A `Button` that toggles text instead of a `ToggleSwitch` / `CheckBox`; a `ListView` for three options; `Pivot` in new code | read the page against the control table in [`ui-components`](../../ui-components/SKILL.md) | minor |
| D12 | Binding errors are a defect, not silence `[WPF]` | No trace listener or test that fails on a binding path error; `{Binding}` with no `Mode`, `FallbackValue` or design-time type | `rg -n "PresentationTraceSources\|d:DesignInstance" -g '*.cs' -g '*.xaml'`; `rg -n "\{Binding" -g '*.xaml'` | minor |
| D13 | Long lists virtualize `[WPF]` | A `ListBox` / `ListView` inside a `ScrollViewer`; `VirtualizingStackPanel.IsVirtualizing="False"`; an `ItemsControl` + `StackPanel` over unbounded data | `rg -n "IsVirtualizing\|<ScrollViewer\|<ItemsControl" -g '*.xaml'` | major |
| D14 | A big `DataGridView` is virtual `[WinForms]` | Thousands of rows loaded into a bound `DataGridView` with `VirtualMode` off, or per-cell handlers that query a store | `rg -n "DataGridView\|VirtualMode\|CellFormatting" -g '*.cs'` | major |
| D15 | Colours come from theme or system resources, never literals `[WPF]` | A hex brush or `Colors.White` in a view; `StaticResource` on a colour that changes with `ThemeMode`; no High Contrast pass | `rg -n "#[0-9A-Fa-f]{6,8}\|Brushes\.\|StaticResource [A-Za-z]*Brush" -g '*.xaml'` | major |
| D16 | `ThemeMode` / Fluent is an explicit choice with its gaps noted `[WPF]` | `ThemeMode` or a Fluent dictionary added with no record of unstyled controls; `WPF0001` suppressed in every project; a template rewritten to paper over a gap | `rg -n "ThemeMode\|Fluent\.xaml\|WPF0001" -g '*.xaml' -g '*.csproj' -g '*.cs' -g '*.editorconfig'` | minor |
| D17 | Background results reach the UI through the dispatcher, batched; collections are synchronized `[WPF]` | `Dispatcher.Invoke` in a loop; an `ObservableCollection` changed from a thread-pool thread; `.Result` on the UI thread | `rg -n "Dispatcher\.Invoke\(\|EnableCollectionSynchronization\|\.Result\b" -g '*.cs'` | major |
| D18 | Long-lived subscriptions are removed on close `[WPF]` `[WinForms]` | `SystemEvents.*` or a static event subscribed with no unsubscribe; a `DispatcherTimer` or timer never stopped; a form shown and never disposed | `rg -n "SystemEvents\.\|DispatcherTimer\|new Timer\|\+= " -g '*.cs'` | major |
| D19 | Layout is anchored and scales; no absolute pixel positions `[WinForms]` | `Location` / `Size` set in pixels for new forms; `AutoScaleMode.None`; hard-coded `Font("Tahoma", 8)`; no per-monitor DPI setting | `rg -n "AutoScaleMode\|ApplicationHighDpiMode\|new Font\(\|Location = new" -g '*.cs' -g '*.csproj'` | major |
| D20 | Dark mode is set before the first form; colours are not literals `[WinForms]` | `Application.SetColorMode` missing, or called after a form exists; literal `BackColor` / `ForeColor`; owner-drawn controls that ignore the current colours | `rg -n "SetColorMode\|BackColor = Color\.\|ForeColor = Color\." -g '*.cs'` | major |
| D21 | Dialogs are awaited, never nested loops `[WinForms]` | `ShowDialog()` inside an async workflow; `Application.DoEvents()`; `Invoke` from a worker loop; `BackgroundWorker` in new code | `rg -n "\.ShowDialog\(\|DoEvents\|BackgroundWorker\|\.Invoke\(" -g '*.cs'` | major |
| D22 | `VisualStylesMode.Net11` is an explicit opt-in on a .NET 11 project `[WinForms]` | `SetDefaultVisualStylesMode(Net11)` added as a side effect or in a shared library; custom-painted controls untested | `rg -n "VisualStylesMode" -g '*.cs' -g '*.csproj'` | minor |
| D23 | The form is passive: binding to a view model, no logic in handlers `[WinForms]` | Business logic, HTTP or storage in a `*.cs` form handler; `*.Designer.cs` edited by hand for behaviour; a designer constructor that does real work | `rg -n "HttpClient\|File\.\|SqliteConnection" -g '*Form*.cs' -g '!*.Designer.cs'` | major |

---

## E — Styling, theming, motion & adaptive layout
*Owning skill: [`styling`](../../styling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| E1 | Colours come from theme resources, not literals | A hex colour or `Colors.White` / `Black` in a page; `Foreground="Black"` | `rg -n "#[0-9A-Fa-f]{6,8}\b\|Colors\.\(White\|Black\)\|=\"(Black\|White)\"" -g '*.xaml' -g '*.cs'` | major |
| E2 | `{ThemeResource}` for anything that changes with theme | `{StaticResource}` on a theme brush | `rg -n "StaticResource [A-Za-z]*(Brush\|Color)" -g '*.xaml'` | major |
| E3 | A custom brush has `Light`, `Dark` and `HighContrast` entries | A `ThemeDictionaries` brush missing the `HighContrast` key; a brush defined once outside `ThemeDictionaries` | `rg -n "ThemeDictionaries" -A12 -g '*.xaml'` | major |
| E4 | One backdrop per window, none stacked on an opaque root | A second `SystemBackdrop`; an opaque `Background` on the root `Grid` hiding Mica; Acrylic as a main-window backdrop | `rg -n "SystemBackdrop\|MicaBackdrop\|DesktopAcrylicBackdrop" -g '*.xaml' -g '*.cs'` | minor |
| E5 | Typography uses the type-ramp styles, Regular and Semibold only | A literal `FontSize`; `FontWeight="Bold"` or `FontStyle="Italic"` in UI text; a fixed font family over Segoe UI Variable | `rg -n "FontSize=\"[0-9]\|FontWeight=\"Bold\|FontStyle=\"Italic\|FontFamily=\"" -g '*.xaml'` | minor |
| E6 | Text scaling is never locked | `IsTextScaleFactorEnabled="False"` | `rg -n "IsTextScaleFactorEnabled" -g '*.xaml' -g '*.cs'` | major |
| E7 | Corner radius uses `ControlCornerRadius` / `OverlayCornerRadius`; spacing sits on the 4 px grid | A literal `CornerRadius="6"`; `Margin="7,3"` | `rg -n "CornerRadius=\"[0-9]\|Margin=\"[0-9, ]*[1235679]\b" -g '*.xaml'` | nit |
| E8 | Motion honours the animation-effects setting; no decorative loop | A custom `Storyboard` that never reads `UISettings.AnimationsEnabled`; a `RepeatBehavior="Forever"` decoration; layout properties animated | `rg -n "Storyboard\|RepeatBehavior=\"Forever\|AnimationsEnabled" -g '*.xaml' -g '*.cs'` | major |
| E9 | Windows are adaptive: no fixed page sizes, a stated minimum size | A fixed `Width` / `Height` on a page root; no `AdaptiveTrigger` for a layout that overflows narrow; a hand-multiplied `RasterizationScale` | `rg -n "<Page[^>]*(Width\|Height)=\|RasterizationScale" -g '*.xaml' -g '*.cs'` | minor |
| E10 | State is never shown by colour alone | A status brush with no icon or text beside it | read each status brush's use sites | major |
| E11 | Raster images ship at scale variants; icons come from Segoe Fluent Icons | A single bitmap used at all DPIs; a custom icon font where `FontIcon` serves | `rg -n "scale-(100\|200)" -g '*.png' --files`; `rg -n "FontIcon\|SymbolIcon\|ImageIcon" -g '*.xaml'` | nit |

---

## F — Windows, navigation & commands
*Owning skill: [`windows-and-navigation`](../../windows-and-navigation/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| F1 | A window states a minimum size and is resizable | A fixed page `Width`/`Height`; no `PreferredMinimumWidth`; `IsResizable=false` with no reason | `rg -n "PreferredMinimum\|IsResizable\|<Page[^>]*(Width\|Height)=" -g '*.cs' -g '*.xaml'` | minor |
| F2 | Size, position and presenter state are saved on close and restored on launch, validated against live displays | No `AppWindow.Closing` save; a restored position never checked against `DisplayArea` | `rg -n "AppWindow\.(Move\|Resize\|Position\|Size)\|DisplayArea" -g '*.cs'` | major |
| F3 | Closing with unsaved work asks first, in `AppWindow.Closing` | `Window.Closed` used for the check; no `args.Cancel`; the work lost on close | `rg -n "AppWindow\.Closing\|\.Closed \+=\|IsDirty\|HasUnsavedChanges" -g '*.cs'` | major |
| F4 | Several windows on the same data share one source of truth | Each window's view model loads its own copy; a second window opened per document every time | read the services each window's view model takes; `rg -n "new .*Window\(" -g '*.cs'` | major |
| F5 | Work a window starts is cancelled when it closes | A `CancellationTokenSource` never cancelled on close; an event subscription never removed | `rg -n "CancellationTokenSource\|\.Closed \+=\|Closing \+=" -g '*.cs'` | major |
| F6 | The title bar uses the `TitleBar` control; `ExtendsContentIntoTitleBar` precedes `Tall` `[WinUI]` | A hand-drawn drag region and caption buttons; `PreferredHeightOption = Tall` with no extend; an opaque title bar over Mica | `rg -n "SetTitleBar\|ExtendsContentIntoTitleBar\|PreferredHeightOption\|<TitleBar" -g '*.cs' -g '*.xaml'` | minor |
| F7 | Navigation uses `NavigationView` items and a `Frame`, wired for back `[WinUI]` | A `Border`/`Grid` with `Tapped` calling `Frame.Navigate`; `IsBackEnabled` not following `CanGoBack`; `Pivot` in new code | `rg -n "Frame\.Navigate\|IsBackEnabled\|CanGoBack\|<Pivot" -g '*.cs' -g '*.xaml'` | major |
| F8 | Every command is reachable from the keyboard | A command only in a click handler or a context menu; no accelerator for a frequent command; a drag-only action with no keyboard path | `rg -n "KeyboardAccelerator\|AccessKey\|StandardUICommand\|XamlUICommand" -g '*.xaml' -g '*.cs'`; read each command against the menu and toolbar | major |
| F9 | Standard shortcuts keep their meaning | `Ctrl+C/X/V/Z/Y/S/N/O/W/F` or `F5` bound to something else | `rg -n "KeyboardAccelerator" -A2 -g '*.xaml'` | major |
| F10 | An unavailable command is disabled, never hidden | `Visibility="Collapsed"` bound to command availability; `CanExecute` ignored | `rg -n "Visibility=\"\{x:Bind[^}]*Can\|CanExecute" -g '*.xaml' -g '*.cs'` | major |
| F11 | Menu and toolbar items share one command definition | The same action defined twice with different labels or shortcuts | `rg -n "<AppBarButton\|<MenuFlyoutItem\|<MenuBarItem" -A3 -g '*.xaml'` | minor |
| F12 | Focus order is complete and logical; the focus visual is not removed | `TabIndex` set on part of a form; `IsTabStop` on decoration; `FocusVisualPrimaryBrush` set transparent; `UseSystemFocusVisuals="False"` | `rg -n "TabIndex\|IsTabStop\|UseSystemFocusVisuals\|FocusVisual" -g '*.xaml'` | major |
| F13 | Page parameters from activation are validated before `Frame.Navigate` | A deep-link string cast or parsed inside the page; an id passed on unchecked | `rg -n "Navigate\(typeof" -g '*.cs'`; read how each parameter was produced | major |

---

## G — Forms & input
*Owning skill: [`forms`](../../forms/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| G1 | Each value uses its semantic input control | A `TextBox` parsed with `int.Parse`; a `ComboBox` for two options; a `ListView` as a form field; a free-text date | `rg -n "int\.Parse\|double\.Parse\|<TextBox" -g '*.cs' -g '*.xaml'`; read against the control table in [`forms`](../../forms/SKILL.md) | minor |
| G2 | Every input has a visible label and an accessible name | A placeholder used as the label; no `Header` and no `LabeledBy`; a required field marked by colour alone | `rg -n "<(TextBox\|PasswordBox\|NumberBox\|ComboBox\|CalendarDatePicker)" -g '*.xaml'`; read each hit for `Header` or `LabeledBy` | major |
| G3 | Validation lives on the view model (`ObservableValidator`), not in code-behind | `Validate`/regex in `*.xaml.cs`; error strings built in a click handler | `rg -n "ObservableValidator\|ValidateAllProperties\|\[Required\|\[Range" -g '*.cs'`; `rg -n "Regex\|IsNullOrWhiteSpace" -g '*.xaml.cs'` | major |
| G4 | Submit validates every field, shows all errors and focuses the first invalid one | `ValidateAllProperties()` never called; untouched required fields submit; focus stays on the button | `rg -n "ValidateAllProperties\|HasErrors\|TryFocusAsync\|\.Focus\(" -g '*.cs'` | major |
| G5 | An error shows at its field as text, not by colour alone, and is announced | A red border only; no live region; one summary string for the whole form | `rg -n "LiveSetting\|GetErrors\|HasErrors" -g '*.xaml' -g '*.cs'` | major |
| G6 | Errors appear on lost focus first, then live; never on an untouched field at load | Errors on page load; validation blocking typing with `BeforeTextChanging` outside a hard format | `rg -n "BeforeTextChanging\|UpdateSourceTrigger" -g '*.xaml' -g '*.cs'` | minor |
| G7 | `NumberBox` empty (`NaN`) is handled | `NumberBox.Value` saved without an `IsNaN` check | `rg -n "NumberBox" -g '*.xaml'`; `rg -n "double\.IsNaN" -g '*.cs'` | major |
| G8 | A server field error maps back to its field; an unknown key reaches the banner | `400` errors dropped; the raw server message shown; an unknown key ignored | `rg -n "ProblemDetails\|errors\[\|SetServerError" -g '*.cs'` | major |
| G9 | A failed submit keeps the user's input and shows one persistent `InfoBar` | The form cleared on failure; a `MessageBox` or `ContentDialog` for a `5xx`; the banner auto-dismissed | `rg -n "InfoBar\|ContentDialog\|MessageBox" -g '*.cs' -g '*.xaml'` | major |
| G10 | Double submit is prevented and the save is cancellable | No `CanExecute` on `IsSaving`; the save command has no `CancellationToken` | `rg -n "\[RelayCommand" -A3 -g '*.cs'` | major |
| G11 | A secret uses `PasswordBox` and is never logged, persisted or left in the view model | A `TextBox` for a password; a password in a log call; a secret kept after use | `rg -n "PasswordBox\|Password" -g '*.cs' -g '*.xaml'` | blocker |
| G12 | `InputScope` is set; spell check is off for ids, codes and emails | No `InputScope` on an email or number field; spell-check squiggles in an id | `rg -n "InputScope\|IsSpellCheckEnabled" -g '*.xaml'` | nit |
| G13 | A dirty form asks before it is left; a form that loads data has a failed state | Close or navigate loses edits; a failed load renders an empty editable form | `rg -n "IsDirty" -g '*.cs'`; read each edit page's load states | major |

---

## H — Networking & realtime
*Owning skill: [`networking`](../../networking/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| H1 | `HttpClient` only through `IHttpClientFactory` typed clients | `new HttpClient()` outside a test or the factory; a static shared client with no handler lifetime | `rg -n "new HttpClient\(" -g '*.cs'` | major |
| H2 | Every request sits inside a timeout budget | Default `HttpClient.Timeout` (100 s) with no total or attempt timeout; a retry with no cap | `rg -n "AddStandardResilienceHandler\|AddResilienceHandler\|Timeout =" -g '*.cs'` | major |
| H3 | Every client method takes and passes a `CancellationToken`; a closing window cancels it | A client method with no token; `CancellationToken.None` in a view-model path; stale search responses still applied | `rg -n "async Task.*\)" -g '*Client*.cs'`; `rg -n "CancellationToken\.None" -g '*.cs'` | major |
| H4 | ProblemDetails is read once into a typed failure; user text comes from the failure kind | `ex.Message` or `detail` shown to the user; status codes read in view models; a `400` body dropped | `rg -n "StatusCode\|ProblemDetails\|\.Message" -g '*.cs'` | major |
| H5 | Only idempotent requests retry; `Retry-After` is honoured | A `POST` retried with no idempotency key; a retry loop with no delay; `429` / `503` handled as a plain failure | `rg -n "Retry\|RetryAfter\|ShouldHandle" -g '*.cs'` | major |
| H6 | One token refresh is in flight; a second `401` signs out; tokens never reach URLs or logs | Concurrent refreshes; a refresh loop; a token in a query string, log call or `Debug.WriteLine` | `rg -n "Authorization\|access_token\|RefreshAsync" -g '*.cs'` | blocker |
| H7 | A malformed or unparseable body is a failed state, never an empty one | `catch (JsonException)` returning an empty list; a `?? new()` on a failed deserialize; reflection-based `JsonSerializer` calls in a trimmed or AOT app | `rg -n "JsonException\|JsonSerializer\." -g '*.cs'` | major |
| H8 | TLS only | An `http://` or `ws://` base address with no recorded reason; certificate validation disabled | `rg -n "http://\|ws://\|ServerCertificateCustomValidationCallback\|DangerousAcceptAnyServerCertificate" -g '*.cs' -g '*.json'` | blocker |
| H9 | Offline is told apart from a server error; the window revalidates on activation, resume and connectivity | One generic failure for no network and `5xx`; no reachability handling; revalidation on a timer loop | `rg -n "NetworkStatusChanged\|NetworkAvailabilityChanged\|PowerModeChanged" -g '*.cs'` | major |
| H10 | A socket reconnects with capped backoff, closes with the window, and delivers to the UI batched | A reconnect loop with no delay; no `CloseAsync`; one dispatcher enqueue per message; `ws://` | `rg -n "ClientWebSocket\|ConnectAsync\|CloseAsync" -g '*.cs'` | major |
| H11 | Socket and server messages are untrusted input | No frame-size limit; an unvalidated message routed to navigation or a file path; a token in the socket URL | `rg -n "ReceiveAsync\|ClientWebSocket" -g '*.cs'` | major |

---

## I — Storage, documents & sync
*Owning skill: [`offline-and-storage`](../../offline-and-storage/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| I1 | The store matches package identity `[packaged]` `[unpackaged]` | `ApplicationData.Current` in an unpackaged app; a hard-coded path; no recorded choice of `GetForUnpackaged` or `LocalApplicationData` | `rg -n "ApplicationData\.Current\|GetForUnpackaged\|SpecialFolder\." -g '*.cs'` | blocker |
| I2 | Settings are one typed service: versioned, atomic, no secrets | Settings read in many places; a half-written file after a crash; a corrupt file that crashes startup; a secret in settings or `appsettings.json` | `rg -n "LocalSettings\|settings\.json\|File\.WriteAll" -g '*.cs'` | major |
| I3 | Secrets live only in `PasswordVault` or DPAPI `CurrentUser` | A token or password in settings, a file, the database or a log; `DataProtectionScope.LocalMachine`; no recorded choice between vault and DPAPI for an unpackaged app `[unpackaged]` | `rg -n "PasswordVault\|ProtectedData\|LocalMachine" -g '*.cs'` | blocker |
| I4 | `PasswordVault` misses are handled, only after opt-in sign-in | `Retrieve` / `FindAllBy*` with no `COMException` handling; a credential saved before the user opted in; sign-out leaves it behind | `rg -n "\.Retrieve\(\|FindAllBy\|RetrievePassword\|vault\.Remove" -g '*.cs'` | major |
| I5 | Migrations run at startup behind a loading state with a failed body; the file is backed up first | `Database.Migrate()` in a view model or on the UI thread; a failed migration shows a blank window; no backup | `rg -n "Migrate\(Async\)?\|EnsureCreated" -g '*.cs'` | major |
| I6 | No `EnsureCreated` on an evolving database; no in-memory provider in tests | `EnsureCreated()` beside migrations; `UseInMemoryDatabase` or an SQLite in-memory substitute for a real-file integration test | `rg -n "EnsureCreated\|UseInMemoryDatabase\|Mode=Memory" -g '*.cs'` | major |
| I7 | A `DbContext` is short-lived and never held by a window | A singleton `DbContext`; a context stored in a view model; tracked reads for display data; I/O on the UI thread | `rg -n "AddDbContext\|IDbContextFactory\|AsNoTracking\|DbContext " -g '*.cs'` | major |
| I8 | No file, database or registry I/O on the UI thread | `File.ReadAllText`, `SaveChanges()` or `Registry.*` in a handler or command body | `rg -n "File\.(Read\|Write\|Open)\|SaveChanges\(\)\|Registry\." -g '*.cs'` | major |
| I9 | Cache and data folders are right; the cache has a size or age cap | A cache under `LocalFolder` / the data folder; no eviction; a fixed temp filename | `rg -n "LocalCacheFolder\|GetTempPath\|Cache" -g '*.cs'` | minor |
| I10 | Offline writes go to an idempotent outbox, drained in order | A write that fails offline and is lost; a retry that can double-apply; no "changes waiting" state | `rg -n "Outbox\|IdempotencyKey\|Idempotency-Key" -g '*.cs'` | major |
| I11 | Cached data is shown as stale and offline, with the persistent banner | A blank region offline; cached rows with no "last updated"; a modal for the offline state | read the state type; `rg -n "Stale\|Offline" -g '*.cs'` | major |
| I12 | A path that arrives from outside is validated before it is opened | A path from activation, drag-drop or a document used with no `GetFullPath` and root check | `rg -n "Path\.Combine\|GetFullPath" -g '*.cs'` | major |
| I13 | Unsaved work is autosaved or asked about; relaunch restores state | Quit loses a draft; no draft file; a secret persisted in a draft | `rg -n "Draft\|FormClosing\|Closing" -g '*.cs'` | major |

---

## J — Platform integration, permissions & background
*Owning skills: [`platform-integration`](../../platform-integration/SKILL.md) · [`activation-and-notifications`](../../activation-and-notifications/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| J1 | The Windows App SDK pickers are constructed with `AppWindow.Id` `[WinUI]` | `InitializeWithWindow` on the new pickers; a picker built with the wrong window; `Windows.Storage.Pickers` used where the new ones serve | `rg -n "FileOpenPicker\|FileSavePicker\|FolderPicker\|InitializeWithWindow" -g '*.cs'` | major |
| J2 | A picker's `null` is cancel, not an error; a picked path is opened read-only and validated | A cancel raising a banner; a picked file parsed with no size or type check | `rg -n "PickSingleFileAsync\|PickSaveFileAsync\|PickFolderAsync" -A4 -g '*.cs'` | minor |
| J3 | Single instancing uses `AppInstance`, never a mutex | `new Mutex(` / `Mutex` used to enforce one instance; the second launch's arguments dropped | `rg -n "new Mutex\|Mutex\(\|FindOrRegisterForKey\|RedirectActivationToAsync" -g '*.cs'` | major |
| J4 | Redirection is awaited before any UI starts and cannot loop | `RedirectActivationToAsync` not awaited; services started before the redirect; a redirected instance redirecting again | `rg -n "RedirectActivationToAsync\|GetActivatedEventArgs" -B2 -A6 -g '*.cs'` | major |
| J5 | The `Activated` handler marshals to the UI thread | A control or window touched directly from `AppInstance.Activated` or `NotificationInvoked` | `rg -n "\.Activated \+=\|NotificationInvoked" -A8 -g '*.cs'` | major |
| J6 | Protocol, file, command-line and toast arguments are validated before routing | A `Uri` or path passed to navigation unchecked; an action name used as a method name; a protocol verb that deletes or pays | `rg -n "ProtocolActivatedEventArgs\|IFileActivatedEventArgs\|AppNotificationActivatedEventArgs\|\.Argument\b\|ExtendedActivationKind" -g '*.cs'` | blocker |
| J7 | An unknown activation kind or a rejected payload falls back to the start screen | An exception or an error echoing the input; a rejected payload logged raw | read the activation router's default branch | major |
| J8 | File and protocol associations are declared narrowly and only for a packaged app `[packaged]` | Wildcard `FileTypeAssociation`; an association with no `DisplayName`; associations claimed by an unpackaged app with no recorded reason | `rg -n "FileTypeAssociation\|uap:Protocol\|SupportedFileTypes" -g '*.appxmanifest'` | minor |
| J9 | Launch at sign-in is the user's choice, off by default, and shows the real state | A startup task enabled at install with no UI; `DisabledByUser` retried instead of linked to Settings | `rg -n "StartupTask\|windows.startupTask\|RequestEnableAsync" -g '*.cs' -g '*.appxmanifest'` | major |
| J10 | `AppNotificationManager` is registered before the first activation and unregistered on exit | `Register()` called late; never unregistered; no handler for a toast that launched the app | `rg -n "AppNotificationManager" -g '*.cs'` | major |
| J11 | Toast text and arguments carry no secret or personal data; tags group and replace | A token or email in a toast; a notification per event with no tag; no way to turn the app's toasts off in-app | `rg -n "AppNotificationBuilder\|AddText\|AddArgument\|SetTag" -g '*.cs'` | major |
| J12 | The app never requires elevation | `requireAdministrator` in a manifest; `runFullTrust` plus `allowElevation` with no recorded reason | `rg -n "requireAdministrator\|allowElevation\|highestAvailable" -g '*.manifest' -g '*.appxmanifest' -g '*.csproj'` | blocker |
| J13 | A background task is MSIX, registered once, unique, resumable, and never shows a modal `[packaged]` | Registered at every launch; a long task that cannot resume; a `ContentDialog` from a task; a trigger unsupported for full trust | `rg -n "BackgroundTaskBuilder\|windows.comServer\|ExeServer" -g '*.cs' -g '*.appxmanifest'` | major |
| J14 | A dropped, pasted or shared item is validated; drag-drop has a keyboard alternative | `Drop` reading storage items with no type or size check; a drag-only reorder; `await` in `Drop` with no deferral | `rg -n "AllowDrop\|\bDrop=\|DataPackageView\|GetStorageItemsAsync\|GetDeferral" -g '*.cs' -g '*.xaml'` | major |
| J15 | The clipboard handles contention and never holds a secret | `COMException` unhandled on `GetContent`; a secret copied with history and roaming allowed | `rg -n "Clipboard\." -A3 -g '*.cs'` | minor |
| J16 | WebView2 is locked down: navigation allowlist, devtools and default menus off in release | No `NavigationStarting` handler; `AreDevToolsEnabled` true in release; `NewWindowRequested` unhandled | `rg -n "CoreWebView2\|NavigationStarting\|NewWindowRequested\|AreDevToolsEnabled\|AreDefaultContextMenusEnabled" -g '*.cs' -g '*.xaml'` | blocker |
| J17 | WebView2 bridge messages are validated, typed and source-checked | `WebMessageAsJson` used untyped; `args.Source` unchecked; `AddHostObjectToScript` of a broad object; `NavigateToString` with user HTML | `rg -n "WebMessageReceived\|AddHostObjectToScript\|NavigateToString\|WebMessageAsJson" -g '*.cs'` | blocker |
| J18 | WebView2 failure is a state; the user-data folder is app-private | A blank WebView on `ProcessFailed`; a user-data folder under a shared path | `rg -n "ProcessFailed\|NavigationCompleted\|UserDataFolder\|EnsureCoreWebView2Async" -g '*.cs'` | major |
| J19 | Every Windows AI call is behind `GetReadyState`; a model download follows consent | No readiness branch; `EnsureReadyAsync` with no consent; `NotSupportedOnCurrentSystem` ending in a crash or blank region | `rg -n "GetReadyState\|EnsureReadyAsync\|LanguageModel\|TextRecognizer" -g '*.cs'` | major |
| J20 | No dependency on Phi Silica by name; no LAF token in source; no experimental AI API in production | A hard-coded model name; `TryUnlockFeature` with a token literal; the speech-recognition experimental API in a release build | `rg -n "PhiSilica\|Phi Silica\|TryUnlockFeature\|LimitedAccessFeatures" -g '*.cs' -g '*.json' -g '*.config'` | major |
| J21 | Prompts and model output are not logged and are treated as untrusted text | A prompt or response in a log call; model output rendered as markup or run as a command | `rg -n "GenerateResponseAsync" -A6 -g '*.cs'` | major |
| J22 | A permission or capability is asked at the moment of use; the denied path is a working screen | A capability requested at startup; a denied toast or AI download leaving a dead control with no link to Settings | read each capability's first use and its denied branch | major |

---

## K — Security
*Owning fragment: [`desktop/_shared/security`](../../../../_shared/security/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `desktop/_shared/security/references/audit-checks.md` whose `Platforms` column names `windows`, and the ids are the fragment's — finding `K3` is row K3 of the security fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## L — Distribution & store compliance
*Owning fragment: [`desktop/_shared/distribution`](../../../../_shared/distribution/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `desktop/_shared/distribution/references/audit-checks.md` whose `Platforms` column names `windows`, and the ids are the fragment's — finding `L3` is row L3 of the distribution fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## M — Accessibility
*Owning skill: [`accessibility`](../../accessibility/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| M1 | Every interactive element has an accessible name | An icon-only `Button`, `AppBarButton` or `ToggleButton` with no text content and no `AutomationProperties.Name` or `LabeledBy`; a name that is the role (`Delete button`) or an id (`btnDelete`) | `rg -n "<(AppBarButton\|Button\|ToggleButton\|HyperlinkButton)\b[^>]*/>" -g '*.xaml'`; read each for `Content`, `Label` or `AutomationProperties.Name`; Accessibility Insights FastPass | major |
| M2 | Semantic controls, not clickable panels | `Tapped` or `PointerPressed` on a `Border`, `Grid`, `StackPanel`, `Image` or `TextBlock` that acts as a button or link | `rg -n "<(Border\|Grid\|StackPanel\|Image\|TextBlock)\b[^>]*(Tapped\|PointerPressed)=" -g '*.xaml'` | major |
| M3 | Every command is reachable from the keyboard and focus is visible | A command with only a pointer, hover or drag path; `UseSystemFocusVisuals="False"` with no replacement visual; a custom control with no key handling | `rg -n "UseSystemFocusVisuals=\"False\"\|PointerEntered\|DragStarting" -g '*.xaml' -g '*.cs'`; read each for a keyboard equivalent | major |
| M4 | Tab order is complete and follows reading order | `TabIndex` set on part of a group; `IsTabStop="False"` on a reachable control; a new page or window with no initial focus; focus lost after a dialog closes or a row is deleted | `rg -n "TabIndex\|IsTabStop\|\.Focus\(" -g '*.xaml' -g '*.cs'`; tab through each screen | minor |
| M5 | Text scales with the system setting and is never locked | `IsTextScaleFactorEnabled="False"`; a fixed `Height` on a text element; a layout that clips at 225% text or at the minimum window size | `rg -n "IsTextScaleFactorEnabled\|<TextBlock[^>]*\bHeight=" -g '*.xaml'`; run at 225% text | major |
| M6 | High Contrast is honoured | A hex colour literal in a `Foreground`, `Background`, `Fill`, `Stroke` or `BorderBrush`; a custom theme dictionary with no `HighContrast` key; an image that carries meaning with no contrast variant | `rg -n "(Foreground\|Background\|Fill\|Stroke\|BorderBrush)=\"#" -g '*.xaml'`; `rg -n "HighContrast" -g '*.xaml'`; run in Aquatic and Night sky | major |
| M7 | No state is shown by colour alone; contrast meets 4.5:1 text, 3:1 graphics and focus | An error shown only by a red border; a selected row shown only by a fill; low-contrast secondary text or focus visual. **requires dynamic test → `qa-security`**, reported as unverified | Read each state's template; Accessibility Insights colour-contrast check in both themes | major |
| M8 | A status or failure change is announced | A status `TextBlock` that changes with no `AutomationProperties.LiveSetting`; a hand-built failure panel with no live region in place of `InfoBar`; an announcement on every keystroke or tick | `rg -n "LiveSetting\|RaiseNotificationEvent" -g '*.xaml' -g '*.cs'`; read the status elements | major |
| M9 | A custom control exposes the right peer, pattern and change events | A `Control` that behaves as a button, slider or list with no `OnCreateAutomationPeer`; a peer with no pattern provider, or one that never calls `RaisePropertyChangedEvent` | `rg -n "OnCreateAutomationPeer\|AutomationPeer\|GetPatternCore\|RaisePropertyChangedEvent" -g '*.cs'`; list `: Control` classes and compare | major |
| M10 | Decorative elements are `Raw`; content is never `Collapsed` to hide it from readers | A divider or glyph read by Narrator; `Visibility="Collapsed"` used to hide a duplicate from a reader while keeping it on screen | `rg -n "AccessibilityView" -g '*.xaml'`; read the decorative images and glyphs | minor |
| M11 | Animation effects and transparency settings are honoured | A custom `Storyboard` or implicit animation that ignores `UISettings.AnimationsEnabled`; a custom translucent surface with no solid fallback when transparency is off; content flashing over three times a second | `rg -n "AnimationsEnabled\|AdvancedEffectsEnabled\|Storyboard\|Implicit(Show\|Hide)Animations" -g '*.xaml' -g '*.cs'` | minor |
| M12 | `[WinForms]` Interactive controls carry `AccessibleName` and `AccessibleRole` where the default is wrong | An icon-only `Button` or `ToolStripButton` with no `AccessibleName`; a custom-drawn control with no `AccessibleObject` | `rg -n "AccessibleName\|AccessibleRole\|CreateAccessibilityInstance" -g '*.cs' -g '*.Designer.cs'` | major |
| M13 | A Narrator and Accessibility Insights pass is recorded for each screen touched | No FastPass result and no Narrator walk in the report. **requires dynamic test → `qa-security`**, reported as unverified | The report's evidence; Accessibility Insights for Windows, Narrator `Win+Ctrl+Enter` | minor |

---

## N — Performance
*Owning skill: [`performance`](../../performance/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| N1 | Work leaves the UI thread once and returns once per result `[C++]` | Compute, file or network work in a handler before any `co_await winrt::resume_background()`; WinRT calls made before `resume_background` (extra hops); a `resume_foreground` per row | `rg -n "resume_background\|resume_foreground" -g '*.cpp'`; read each coroutine's order of awaits | major |
| N2 | Nothing costly runs before the first frame | File, database, settings-migration or network work in `App()`, `OnLaunched` or the first page's constructor, awaited before `Activate()`; a fixed-delay splash | `rg -n "OnLaunched\|Activate\(\)\|InitializeComponent" -g '*.cs'`; read what runs before the window shows | major |
| N3 | The UI thread never waits on a task | `.Result`, `.Wait()` or `.GetAwaiter().GetResult()` in production code; file or network work in a handler with no `await` | `rg -n "\.Result\b\|\.Wait\(\)\|GetAwaiter\(\)\.GetResult\(\)" -g '*.cs'` | major |
| N4 | `x:Bind` over `{Binding}` `[WinUI]` | A `{Binding}` with no recorded reason; an `x:Bind` to a changing value left on the default `OneTime`; a `DataTemplate` with no `x:DataType` | `rg -n "\{Binding " -g '*.xaml'`; `rg -n "<DataTemplate(?![^>]*x:DataType)" --pcre2 -g '*.xaml'` | major |
| N5 | Lists virtualize and have a bounded height | An `ItemsControl` or `StackPanel` in a `ScrollViewer` over about 20 items or more; a `ListView`, `GridView` or `ItemsRepeater` inside a vertical `ScrollViewer` or an `Auto` row | `rg -n "<ScrollViewer\|ItemsControl\|<StackPanel" -g '*.xaml'`; read each for a bound collection | major |
| N6 | Changes reach the UI thread batched | A `TryEnqueue` per row; hundreds of `Add` calls on a bound `ObservableCollection`; a bound property that recomputes a heavy value on every read | `rg -n "TryEnqueue\|\.Add\(" -g '*.cs'`; read each in a loop | minor |
| N7 | Handlers, timers, subscriptions and tokens are released when the page unloads | `+=` on a static or singleton event with no `-=`; a strong messenger subscription held by a page; a `CancellationTokenSource` never cancelled or disposed; a `WebView2` never closed | `rg -n "\+=\|StrongReferenceMessenger\|CancellationTokenSource\|Unloaded\|\.Close\(\)" -g '*.cs'`; navigate ten times and diff the heap | major |
| N8 | Thumbnails decode at display size | A `BitmapImage` in a row template with no `DecodePixelWidth` or `DecodePixelHeight`; a full-size image shown at 48 px | `rg -n "BitmapImage\|<Image\b" -g '*.xaml' -g '*.cs'` | minor |
| N9 | Native AOT and trimming are decisions with their warnings read `[WinUI]` | `PublishAot` with `{Binding}` or a reflection serializer; `IL2xxx` / `IL3xxx` in `NoWarn` with no reason; trimming turned on with no run of the published binary | `rg -n "PublishAot\|PublishTrimmed\|NoWarn\|JsonSerializerContext" -g '*.csproj' -g '*.props' -g '*.cs'` | major |
| N10 | Timers and polling match how fast the data changes | A `DispatcherTimer` under 100 ms that updates bindings; polling a server faster than its data changes; a timer or watcher left running for a closed window | `rg -n "DispatcherTimer\|PeriodicTimer\|FileSystemWatcher\|Interval" -g '*.cs'` | minor |
| N11 | A performance change carries a before and after number | A change described as faster with no trace, no median and no Release build on target hardware. **requires dynamic test**, reported as unverified | The report's evidence: WPR / PerfView / `dotnet-counters` output | minor |

---

## O — Error resilience
*Owning skill: [`error-handling`](../../error-handling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| O1 | Every data region has loading, loaded and failed states, plus stale and offline | A nullable list plus a boolean; a pane that goes blank on failure; no Failed body, no Retry; an empty result shown as nothing | `rg -n "Load<\|Failed\|IsLoading\|HasError" -g '*.cs' -g '*.xaml'`; read each data region | major |
| O2 | The failure is scoped to the response-dependent subtree | The whole page or `Frame` swaps to an error page; the toolbar, search or navigation disappears when the content fails | `rg -n "Navigate\(typeof\(\w*Error\|Content = .*Error" -g '*.cs'`; read each page's failed state | major |
| O3 | Every surfaced failure also opens one persistent `InfoBar` that only the user closes | A failure with no banner; `IsClosable="False"`; a `DispatcherTimer`, `Task.Delay` or code that sets `IsOpen=false` on a timer; several stacked banners | `rg -n "InfoBar\|IsClosable\|IsOpen" -g '*.xaml' -g '*.cs'` | major |
| O4 | A foreground failure is never a modal; a background failure never is | `MessageBox`, `MessageDialog` or `ContentDialog` for a failure; a dialog raised from a timer or background task; a toast for a foreground failure | `rg -n "MessageBox\|MessageDialog\|ShowAsync\(\|AppNotificationManager" -g '*.cs'`; read each for its trigger | major |
| O5 | A raw exception is never shown or bound to the UI | `ex.Message`, `ex.ToString()` or a status code alone in a `TextBlock`, `InfoBar` message or dialog | `rg -n "\.Message\b\|ToString\(\)" -g '*.cs'` in view models; `rg -n "Message=\"\{x:Bind [^\"]*Exception" -g '*.xaml'` | major |
| O6 | A drifted or unparseable response is Failed, never empty | A `catch` that returns an empty list; `?? []` on a required collection; deserialization with all properties optional | `rg -n "catch[^{]*\{[^}]*(Array\.Empty\|new List\|\[\])\|\?\? (\[\]\|new List)" --pcre2 -g '*.cs'` | major |
| O7 | Every request has a timeout, and work is cancelled when the page unloads | A `GetAsync`, `SendAsync` or `GetFromJsonAsync` with no token; no timeout budget; a token never cancelled in `Unloaded` | `rg -n "GetAsync\|SendAsync\|PostAsync\|GetFromJsonAsync\|CancelAfter\|Timeout" -g '*.cs'`; read each call for its token | major |
| O8 | Offline is told apart from a server error; a failed refresh behind data is Stale | One message for every failure; the list cleared when a refresh fails after a success; a 401 shown as a generic error | `rg -n "FailureKind\|Stale\|NetworkInformation\|HttpRequestException\|HttpStatusCode" -g '*.cs'` | major |
| O9 | Wake, window reactivation and a network change revalidate; windows share one model | No `Activated`, `SystemSuspendStatusChanged` or `NetworkStatusChanged` handler; two refreshes fired for one wake; each window holding its own copy of the data | `rg -n "WindowActivationState\|SystemSuspendStatusChanged\|NetworkStatusChanged\|NetworkAvailabilityChanged" -g '*.cs'` | major |
| O10 | Unhandled-exception handlers are registered, log, and do not swallow | No `Application.UnhandledException`, `AppDomain` or `TaskScheduler.UnobservedTaskException` handler; `e.Handled = true` unconditionally; a handler that shows UI after the process is ending | `rg -n "UnhandledException\|UnobservedTaskException\|DispatcherUnhandledException\|ThreadException\|Handled = true" -g '*.cs'` | major |
| O11 | No empty `catch`, and no `catch` that logs and continues without a state | `catch { }`; `catch (Exception)` that only logs and returns; a catch that ends with no state change and no rethrow | `rg -n "catch\s*(\(Exception[^)]*\))?\s*\{\s*\}" -g '*.cs'`; `rg -n -A3 "catch" -g '*.cs'`; read each | major |
| O12 | `async void` is only an event handler whose whole body is guarded | `async void` on a non-handler; an event handler with an `await` outside a `try` | `rg -n "async void" -g '*.cs'` | major |
| O13 | Closing with unsaved work asks, writes are atomic, and an indeterminate write is reconciled | No `AppWindow.Closing` handler on a window with editable state; a save written straight over the old file; a pending write dropped on relaunch; an update that restarts over unsaved work | `rg -n "Closing\|args\.Cancel\|File\.Replace\|File\.Move\(\|Idempotency\|pending" -g '*.cs'` | major |
| O14 | A storage failure is a recoverable, explained state | An `IOException` or `UnauthorizedAccessException` unhandled on save; a failure that loses the in-memory data; a path of user data in a message or span | `rg -n "IOException\|UnauthorizedAccessException\|FailureKind.Storage" -g '*.cs'`; read each file write | major |
| O15 | A dependency failure degrades to a scoped failed region | `EnsureCoreWebView2Async` with no handling of a missing runtime; no `CoreProcessFailed` handler; a COM object created with no `COMException` handling; an unbounded wait on a helper process | `rg -n "EnsureCoreWebView2Async\|CoreProcessFailed\|WebView2RuntimeNotFoundException\|COMException\|NamedPipeClientStream" -g '*.cs'` | major |
| O16 | Crash evidence is kept: symbols retained and stowed exceptions readable | Release PDBs discarded; a crash report with no HRESULT. **requires dynamic test**, reported as unverified | The build's symbol store; `winapp run --debug-output --symbols` on a forced failure | minor |

---

## P — Localization
*Owning skill: [`languages`](../../languages/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| P1 | No user-visible literal in XAML or C# | `Text="Orders"`, `Content="Save"`, `Title = "Error"` or a message string in markup or code, outside test ids, log templates and protocol tokens | `rg -n "(Text\|Content\|Header\|Title\|PlaceholderText\|Label\|ToolTipService.ToolTip)=\"[A-Za-z]" -g '*.xaml'`; `rg -n "(Text\|Content\|Title\|Message) = \"[A-Za-z]" -g '*.cs'` | major |
| P2 | Every `x:Uid` property exists on the element's type and no identifier collides | `Greeting.Text` for an `x:Uid` on a `Button`; a simple identifier and a property identifier on the same stem; an identifier renamed after translation | `rg -n "x:Uid=" -g '*.xaml'`, then each stem in `Strings/**/*.resw`; run the app and read each page | major |
| P3 | Strings reach code through one injected `ResourceLoader`, never by concatenation | `new ResourceLoader()` in a view model; `"You have " + n + " orders"`; a `Strings` wrapper that only forwards | `rg -n "ResourceLoader\|GetString\(" -g '*.cs'`; `rg -n "\" \+ \|\+ \"\|\$\"[^\"]*\{" -g '*.cs'` in UI-facing code | major |
| P4 | Every declared language has the full identifier set, and the manifest declares them `[packaged]` | `<Resource Language="x-generate"/>` left in the manifest; a `.resw` missing identifiers the default has; a language folder not declared | `rg -n "Resource Language" -g 'Package.appxmanifest'`; diff the identifier sets of each `Strings/*/Resources.resw` | major |
| P5 | Plurals are chosen by category, never by `== 1` | `count == 1 ? "item" : "items"`; one string for every count; `0 orders` shown where a zero message is needed | `rg -n "== 1 \?\|Count == 1\|Length == 1" -g '*.cs'` | major |
| P6 | Display formatting is culture-aware, wire formats are invariant | A hand-written `MM/dd/yyyy`; `ToString()` of a number or date shown in the UI with no culture; a hard-coded `$`; the UI culture used for JSON or a query string; `Parse` of typed text in the invariant culture | `rg -n "\"(MM\|dd\|yyyy)[/.-]\|\"\$\"\|CultureInfo\.InvariantCulture\|\.Parse\(" -g '*.cs'`; read each hit for display versus wire | major |
| P7 | Comparison and case change use the right culture mode | `ToLower()` or `ToUpper()` for comparison; culture-sensitive comparison of an id or key; `ToUpper()` on user text with no culture | `rg -n "ToLower\(\)\|ToUpper\(\)\|StringComparison\.\|StringComparer\." -g '*.cs'` | minor |
| P8 | The layout survives right-to-left and longer text | A fixed `Width` or `Height` on a text element; `HorizontalAlignment="Left"` where the layout carries meaning; a directional icon not mirrored; no `TextWrapping` or `TextTrimming` | `rg -n "<(TextBlock\|Button)[^>]*\b(Width\|Height)=\|HorizontalAlignment=\"(Left\|Right)\"\|MirroredWhenRightToLeft" -g '*.xaml'`; run a pseudo-localized and an RTL language | minor |
| P9 | Manifest strings are localized `[packaged]` | A literal `DisplayName` or `Description` in `Package.appxmanifest` instead of `ms-resource:` | `rg -n "DisplayName=\|Description=" -g 'Package.appxmanifest'` | minor |
| P10 | `[WPF]` `[WinForms]` use `.resx` and `CurrentUICulture`, and no `.resw` is added | A `.resw` or MRT Core reference added to a WPF or WinForms project; strings hard-coded in `.Designer.cs` | `rg -n "\.resw\|Microsoft.Windows.ApplicationModel.Resources" -g '*.csproj' -g '*.cs'` | minor |

---

## R — Testability & test ids
*Owning skill: [`test-ids`](../../test-ids/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| R1 | Every interactive element carries an `AutomationId` | A `Button`, `TextBox`, `PasswordBox`, `NumberBox`, `ComboBox`, `CheckBox`, `ToggleSwitch`, `HyperlinkButton`, `AppBarButton`, `MenuFlyoutItem`, `NavigationViewItem` or `TabViewItem` with no `AutomationProperties.AutomationId` | `rg -n "<(Button\|TextBox\|PasswordBox\|NumberBox\|ComboBox\|CheckBox\|ToggleSwitch\|HyperlinkButton\|ToggleButton\|AppBarButton\|MenuFlyoutItem\|NavigationViewItem\|TabViewItem)\b(?![^>]*AutomationId)" --pcre2 -g '*.xaml'`; read the multi-line hits | major |
| R2 | Every list and grid container carries its own id | A `ListView`, `GridView`, `ItemsRepeater` or `TreeView` with no `AutomationId`; the id on a panel above it instead | `rg -n "<(ListView\|GridView\|ItemsRepeater\|TreeView)\b(?![^>]*AutomationId)" --pcre2 -g '*.xaml'` | major |
| R3 | Ids follow `Screen.ElementType[.Qualifier]` | A space, underscore, hyphen, digit run, GUID, list index or state value; lowercase segments; a non-ASCII character | `rg -n "AutomationId=\"([^\"]*[ _-]\|[a-z][^\"]*\|[^\"]*\.[0-9]+)" -g '*.xaml'` | major |
| R4 | The id is never the accessibility name and never localized | An `AutomationId` equal to the visible text or to `AutomationProperties.Name`; an `AutomationId` property in a `.resw` or set from `x:Uid` | `rg -n "AutomationId" -g '*.resw'`; compare `AutomationId` and `AutomationProperties.Name` on the same element | major |
| R5 | Row ids are static, with no per-item data | `AutomationId="{x:Bind Id}"`, `Orders.Row.1234`, an id built from an index or a title | `rg -n "AutomationId=\"\{\|AutomationIdProperty.*\$\"" -g '*.xaml' -g '*.cs'` | major |
| R6 | Rows and the parts a test reads are tagged inside the `DataTemplate` | A `DataTemplate` root with no id; a title or status a test must read with no id of its own | `rg -n -A4 "<DataTemplate" -g '*.xaml'`; read each template | minor |
| R7 | Banners, failed and loading regions, empty states and dialogs carry ids | An `InfoBar`, a three-state region body, a `ContentDialog` or a `Flyout` content with no `AutomationId` | `rg -n "<(InfoBar\|ContentDialog\|Flyout\|ProgressRing\|TeachingTip)\b(?![^>]*AutomationId)" --pcre2 -g '*.xaml'` | major |
| R8 | `[WinForms]` controls are named deliberately | `button1`, `textBox2`, `label3` left as `Name` | `rg -n "Name = \"(button\|textBox\|label\|comboBox\|checkBox\|listView\|dataGridView)[0-9]+\"" -g '*.Designer.cs'` | major |
| R9 | An id is set inline, not through a wrapper control that only carries ids | An `AppButton` or helper class existing only to set `AutomationId`; ids set in code-behind where markup works | `rg -n "SetAutomationId\|AutomationIdProperty" -g '*.cs'` | minor |
| R10 | Ids reach the UI Automation tree, and are unique within each container, rows apart | An id absent from the live tree (wrong element, collapsed parent, template root not exposed); the same non-row id twice under one parent. **requires dynamic test → `qa-desktop-<lang>`**, reported as unverified | The explorer's page source, `missing-testids.md`, Accessibility Insights Live inspect, or `winapp ui inspect` where installed | major |

---

## S — Dev-side tests
*Owning skill: [`unit-testing`](../../unit-testing/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| S1 | C++ logic is tested with GoogleTest over a XAML-free core library, to the floor `[C++]` | No test project; tests that reference the app project or `Microsoft.UI.Xaml`; a loop or `if` driving an assertion instead of `TEST_P`; the changed files below 80% of lines (80% of branches where `llvm-cov` reports them) | `rg -ln "gtest\|CppUnitTest" -g '*.vcxproj' -g '*.cpp'`; `rg -n "TEST\(\|TEST_P\(" -g '*.cpp'`; the coverage report (`references/testing-and-coverage.md` of `cpp-winrt`) | major |
| S2 | Logic lives in a UI-free library and view models never touch the dispatcher | `DispatcherQueue`, `XamlRoot`, `Window` or `Microsoft.UI.Xaml` in a view model or service; tests that reference the app project | `rg -n "DispatcherQueue\|XamlRoot\|Microsoft\.UI\.Xaml" -g '*ViewModel*.cs' -g '*Service*.cs'`; `rg -n "ProjectReference" -g '*Tests*.csproj'` | major |
| S3 | The test project's TFM matches the project it references, and XAML types use `[UITestMethod]` | A plain `net10.0` test project referencing a WinUI project; `[TestMethod]` on a test that creates a `Grid` or `UserControl`; a `RuntimeIdentifiers` or `WindowsAppSdkBootstrapInitialize` missing where WinAppSDK types load | `rg -n "TargetFramework\|RuntimeIdentifiers\|WindowsAppSdkBootstrapInitialize" -g '*Tests*.csproj'`; `rg -n "UITestMethod" -g '*.cs'` | major |
| S4 | NUnit is the runner; MSTest only in the WinUI Unit Test App for XAML types (D8) | An MSTest or xUnit project for plain logic where NUnit is the house default (an existing suite is not migrated); the WinUI Unit Test App holding plain-logic tests | `rg -n "MSTest\|xunit\|NUnit" -g '*.csproj'` | minor |
| S5 | Test names describe behaviour | `Test1`, `WorksCorrectly`, a name that restates the method under test with no condition | `rg -n "public (async Task\|void) (Test\d*\|Works\|Should_?\(\|[A-Z]\w*Test)\b" -g '*Tests*.cs'`; read each name for `Should_X_When_Y` | minor |
| S6 | One logical assertion, with no `if` or loop driving it | An `if`, `for` or `foreach` in a test body; unrelated assertions in one test; an assertion that states two outcomes (`.Or.`) | `rg -n "\bif\s*\(\|\bfor(each)?\s*\(\|\.Or\." -g '*Tests*.cs'` | major |
| S7 | No `try`/`catch`, no `Thread.Sleep` or `Task.Delay`, no `async void` in a test | A `try` or `catch` in a body; `Thread.Sleep`, `Task.Delay` to wait; `async void` test | `rg -n "\btry\b\|\bcatch\b\|Thread\.Sleep\|Task\.Delay\|async void" -g '*Tests*.cs'` | major |
| S8 | Time goes through `TimeProvider` | `DateTime.Now`, `UtcNow` or `DateTimeOffset.UtcNow` in logic; a test that depends on the clock | `rg -n "DateTime(Offset)?\.(Now\|UtcNow)" -g '*.cs' -g '!*Tests*'` | major |
| S9 | Fakes over mocks, and no in-memory stand-in for a shipped database | `UseInMemoryDatabase`; SQLite standing in for another engine; a mocked `HttpClient`; a mock of a type the project owns where a fake serves | `rg -n "UseInMemoryDatabase\|Mock<\|Substitute\.For\|Mock\.Of" -g '*Tests*.cs'` | major |
| S10 | The changed files reach 80% of branches, designed branch by branch, with asserting tests | The changed files below 80% of branches in the coverage report; a test with no assertion; a branch (`catch`, guard return, `switch` default) with no test. **requires the coverage report**, reported as unverified without it | `dotnet test --collect:"XPlat Code Coverage"` and the Cobertura `branch-rate` of the changed files; `rg -L "Assert\|Throws" -g '*Tests*.cs'` | major |
| S11 | Coverage exclusions are listed by name and never hide behaviour | `[ExcludeFromCodeCoverage]` or `ExcludeByFile` on code with behaviour; an exclusion not listed in the report | `rg -n "ExcludeFromCodeCoverage\|ExcludeByFile\|Exclude>" -g '*.cs' -g '*.csproj' -g '*.runsettings'` | major |
| S12 | Test data uses builders from four fields, and tests are independent | The same inline object literal duplicated across tests; a `static` field mutated by a test; a test that needs another to run first | `rg -n "static (?!readonly)" --pcre2 -g '*Tests*.cs'`; read the fixtures | minor |

---

## U — Observability & logging
*Owning fragment: [`desktop/_shared/observability`](../../../../_shared/observability/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `desktop/_shared/observability/references/audit-checks.md` whose `Platforms` column names `windows`, and the ids are the fragment's — finding `U3` is row U3 of the observability fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## V — Comments & KISS
*Owning skills: [`engineering-practices/code-comments`](../../../../../engineering-practices/code-comments/SKILL.md) · CLAUDE.md § Comments and § Simplicity (KISS)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| V1 | No inline comments in a body | A `//` line inside a method body (C#, C++) — a step marker, a restatement of the next line, a section banner | `rg -n "^\s+//[^/]" $SRC -g '*.cs' -g '*.cpp' -g '*.h'` | minor |
| V2 | A doc comment states a contract, not the signature | An XML doc comment that restates the name or signature (`Gets the user id`) on a property, DTO, getter or single-expression method | `rg -n -A1 "^\s*/// <summary>" $SRC -g '*.cs'`; read each hit against the member it sits on | minor |
| V3 | No commented-out code, no `TODO` / `FIXME` left behind | A `//` line holding code, or a `TODO` / `FIXME` / `HACK` marker in committed source | `rg -n "^\s*//\s*(var\|await\|return\|if\|using\|auto\|co_await)\b" $SRC -g '*.cs' -g '*.cpp' -g '*.h'` · `rg -n "TODO\|FIXME\|HACK" $SRC -g '*.cs' -g '*.xaml' -g '*.cpp' -g '*.h'` | minor |
| V4 | A comment that exists because the code is unclear | A comment explaining what a badly named local or method does — the fix is the rename or extraction, not a reworded comment | Read the comment hits from V1; ask whether a name would carry it | major |
| V5 | No `interface` with one implementation | An abstraction introduced for one caller and one implementation, with no second real need | `rg -n "^\s*(public \|internal )?interface I\w+" $SRC -g '*.cs'`; then count implementers per hit | major |
| V6 | No wrapper that only forwards | A class or method whose whole body delegates one call to the next layer (service → repository → store as three layers) | `rg -n -A2 "\) =>\s*_\w+\.\w+\(" $SRC -g '*.cs'`; read each hit for a single delegated call | major |
| V7 | No configurability nothing uses | An options bag, flag, generic parameter or extension point that no caller passes or varies | `rg -n "Options\b\|Configuration\b\|\bconfig\b" $SRC -g '*.cs'`; then search for a call site that supplies it | major |
| V8 | A generated or scaffolded comment is removed | A template header, a framework placeholder comment (`// TODO: Add your code`) or a wizard banner left in a source file, with no tool depending on it | `rg -n "Generated by\|<auto-generated\|This file was\|Copyright \(c\)" $SRC -g '*.cs' -g '*.cpp' -g '*.h'` — skip generated sources | minor |

---

## X — Interop & native code
*Owning skills: [`interop`](../../interop/SKILL.md) · [`cpp-winrt`](../../cpp-winrt/SKILL.md)*

Not applicable without P/Invoke, COM or C++ projects.

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| X1 | P/Invoke uses `[LibraryImport]` on `static partial` methods | `[DllImport]` with no recorded reason; `AllowUnsafeBlocks` missing; `SYSLIB1054` suppressed | `rg -n "DllImport\|LibraryImport" -g '*.cs'` | major |
| X2 | Native strings are Unicode and named exactly | An ANSI entry point; `CharSet` instead of `StringMarshalling.Utf16`; no `W` entry point | `rg -n "CharSet\|StringMarshalling\|EntryPoint" -g '*.cs'` | major |
| X3 | A native failure is checked and thrown at the boundary | `SetLastError` absent and the return ignored; no `Win32Exception` or `ThrowExceptionForHR`; a bare `catch` around the call | `rg -n "SetLastError\|GetLastPInvokeError\|ThrowExceptionForHR" -g '*.cs'` | major |
| X4 | Owned native handles are `SafeHandle`s | An owned handle held as `nint` / `IntPtr` with a manual close; a handle leaked on an error path | `rg -n "nint \|IntPtr \|SafeHandle" -g '*.cs'` | major |
| X5 | A window handle comes from the owning window, never the foreground | `GetForegroundWindow()` or `Process.MainWindowHandle` as an owner; a view model holding an `HWND`; a handle cached past close | `rg -n "GetForegroundWindow\|MainWindowHandle\|GetWindowHandle\|WindowInteropHelper" -g '*.cs'` | major |
| X6 | CsWinRT 2.3.1 only; no 3.0 preview `[WinUI]` `[WPF]` `[WinForms]` | `Microsoft.Windows.CsWinRT` 3.x or a preview version, directly or transitively; two versions in the graph | `rg -n "CsWinRT" -g '*.csproj' -g '*.props' -g 'packages.lock.json'` | major |
| X7 | A packaged-only or newer-OS API is guarded `[unpackaged]` | A WinRT call needing package identity, or newer than `TargetPlatformMinVersion`, with no identity or OS check | `rg -n "IsWindowsVersionAtLeast\|HasPackageIdentity\|ApiInformation" -g '*.cs'` | major |
| X8 | Native libraries load by full path or system directory | `LoadLibrary` of a bare name; no `DefaultDllImportSearchPaths` on a P/Invoke class | `rg -n "LoadLibrary\|NativeLibrary\.Load\|DefaultDllImportSearchPaths" -g '*.cs'` | blocker |
| X9 | A delegate passed to native code is kept alive | `GetFunctionPointerForDelegate` on a local delegate; a callback stored nowhere | `rg -n "GetFunctionPointerForDelegate\|UnmanagedCallersOnly\|delegate\* " -g '*.cs'` | major |
| X10 | WinUI hosting in WPF or WinForms is a recorded decision `[WPF]` `[WinForms]` | `DesktopWindowXamlSource` or `Microsoft.WindowsAppSDK` added to a WPF or WinForms project with no decision; an island not disposed or sized | `rg -n "DesktopWindowXamlSource\|WindowsXamlManager\|WindowsXamlHost" -g '*.cs' -g '*.xaml'` | major |
| X11 | COM uses generated interop; registration or elevation is never required | `[ComImport]` with no reason in a trimmed or AOT app; `regsvr32` or registration-free COM needing admin; a raw pointer shared across apartments | `rg -n "ComImport\|GeneratedComInterface\|regsvr32" -g '*.cs' -g '*.csproj'` | major |
| X12 | `unsafe` is scoped and bounds-checked | `<AllowUnsafeBlocks>` used for convenience; a pointer loop with no length check; a COM or buffer size taken from outside unchecked | `rg -n "unsafe\|stackalloc\|fixed \(" -g '*.cs'` | major |
| X13 | Ownership uses projected values, `com_ptr` on implementation types and `winrt::make`; no raw `new` / `delete` `[C++]` | `new` or `delete` on a WinRT type; `com_ptr` of a projected type; an implementation type on the stack returned as a projected type; an owning raw pointer | `rg -n "\bnew [A-Za-z]\|\bdelete \|com_ptr<(winrt::)?(Windows\|Microsoft)::" -g '*.cpp' -g '*.h'` | major |
| X14 | A coroutine or handler that touches `this` after a suspension holds `get_strong()` or `get_weak()` taken before the first `co_await` `[C++]` | A member coroutine using members with no `get_strong` / `get_weak`; the lifetime taken after an await; a weak reference used without promoting it | `rg -n "fire_and_forget\|IAsync(Action\|Operation)(WithProgress)?<?.*::" -g '*.cpp'`; read each hit for `get_strong\|get_weak` above the first `co_await` | blocker |
| X15 | Coroutine parameters are owned: by value or handle, not `const&` read after an await `[C++]` | A `const&` or raw `HANDLE` parameter used after the first suspension point | `rg -n "(fire_and_forget\|IAsync\w+(<[^>]*>)?) +\w+::\w+\([^)]*(&\|HANDLE)" -g '*.cpp'`; read each hit | major |
| X16 | UI-affine objects are touched only after resuming on their dispatcher queue `[C++]` | A XAML property read or set after `resume_background` with no `resume_foreground(queue)`; the queue looked up from a background thread; `hresult_wrong_thread` in logs | `rg -n "resume_background\|resume_foreground\|apartment_context" -g '*.cpp'`; read the code after each background hop | blocker |
| X17 | The UI thread never waits on an async operation `[C++]` | `.get()` or `.wait_for(` on an `IAsync*` in a handler or page method | `rg -n "\.get\(\)\|wait_for\(" -g '*.cpp'`; read each hit for the thread it runs on | blocker |
| X18 | `hresult_error` is caught once at the boundary; expected failures are return values `[C++]` | An empty or logging-and-continuing `catch (...)`; exceptions thrown to signal an expected outcome; a `catch` in every inner function; an async handler returning `void` or `IAsyncAction` instead of `fire_and_forget` | `rg -n "catch \(\.\.\.\)\|catch \(winrt::hresult_error" -g '*.cpp'`; `rg -n "^(void\|IAsyncAction) \w+::\w+_(Click\|Changed\|Loaded)" -g '*.cpp'` | major |
| X19 | Win32 and COM returns are checked `[C++]` | An `HRESULT`, `BOOL` or `HANDLE` return ignored; a handle tested with a bare `if` and dropped; `GetLastError` read after another call | `rg -n "check_hresult\|check_bool\|check_win32\|SUCCEEDED\(\|FAILED\(" -g '*.cpp'`; read the Win32 calls with no check | major |
| X20 | XAML-referenced types are runtime classes in IDL; generated files are untouched `[C++]` | A page or view model bound from XAML with no `runtimeclass`; an edit under `Generated Files`; `Generated Files` committed | `rg -n "runtimeclass" -g '*.idl'`; `git ls-files \| rg "Generated Files"` | major |
| X21 | Event handlers capture a strong or weak reference, or the receiver owns the source; strong handlers are revoked `[C++]` | A `[this]` or `[&]` lambda registered on a source that outlives the object; a `get_strong` handler with no revoker or token revoked on unload | `rg -n "\[this\]\|\[&\]\|auto_revoke\|get_strong\(\), &" -g '*.cpp'`; read each registration | major |
| X22 | C++/WinRT build support is the NuGet package, current and not experimental `[C++]` | A `.vcxproj` with `<CppWinRTEnabled>` and no `Microsoft.Windows.CppWinRT`; a prerelease CppWinRT or Windows App SDK package; `CppWinRTOptimized` turned off | `rg -n "Microsoft.Windows.CppWinRT\|CppWinRTEnabled\|CppWinRTOptimized" -g '*.vcxproj' -g '*.props'` | minor |

---

## Section index

| § | Section | Rows | Owner |
|---|---|---|---|
| A | Version lane, toolchain & migration hygiene | A1–A7 | `project-setup`, `migration`, `basics` |
| B | Project structure, strictness & language standard | B1–B12 | `project-setup`, `basics` |
| C | Architecture, state & DI | C1–C12 | `architecture` |
| D | UI components & platform conventions | D1–D23 | `ui-components`, `wpf`, `winforms` |
| E | Styling, theming, motion & adaptive layout | E1–E11 | `styling` |
| F | Windows, navigation & commands | F1–F13 | `windows-and-navigation` |
| G | Forms & input | G1–G13 | `forms` |
| H | Networking & realtime | H1–H11 | `networking` |
| I | Storage, documents & sync | I1–I13 | `offline-and-storage` |
| J | Platform integration, permissions & background | J1–J22 | `platform-integration`, `activation-and-notifications` |
| K | Security | fragment | `desktop/_shared/security` |
| L | Distribution & store compliance | fragment | `desktop/_shared/distribution` |
| M | Accessibility | M1–M13 | `accessibility` |
| N | Performance | N1–N11 | `performance` |
| O | Error resilience | O1–O16 | `error-handling` |
| P | Localization | P1–P10 | `languages` |
| R | Testability & test ids | R1–R10 | `test-ids` |
| S | Dev-side tests | S1–S12 | `unit-testing` |
| U | Observability & logging | fragment | `desktop/_shared/observability` |
| V | Comments & KISS | V1–V8 | `engineering-practices/code-comments`, CLAUDE.md § Simplicity |
| X | Interop & native code | X1–X22 | `interop`, `cpp-winrt` (N/A without P/Invoke, COM or C++ projects) |

Sections Q (motion) and T (release) are unused: motion is in E, release in L. Fragment sections hold the rows of their `audit-checks.md` whose `Platforms` column names `windows`. **Lane tags:** the `[C++]` rows are B12, C12, N1, S1 and X13–X22 (14 rows); they are reported only against C++/WinRT projects, and every other row is reported against C# projects in its own idiom. `[WinUI]`, `[WPF]` and `[WinForms]` rows are reported only in their lane.
