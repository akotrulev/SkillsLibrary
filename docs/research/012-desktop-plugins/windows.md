# Native Windows 11 apps — research for the `desktop-windows` plugin

**Date:** 2026-11-15 · **Scope:** what a coding standard, a skill set and a dev agent for native Windows 11 apps should teach today, verified on the web on this date. Feeds plan 012 (desktop plugins). Every row carries its source; claims the sources did not settle are in the closing **Not verified** list.

## Overview

Microsoft's own documentation is unusually direct right now. **WinUI on the Windows App SDK is the recommended native UI framework for new Windows desktop apps**, the 2.x line moved to semantic versioning in April 2026, and Microsoft now ships an official **Claude Code plugin** (`winui@win-dev-skills`) plus a terminal-first toolchain (`winapp` CLI) built for agents. WPF and WinForms stay fully supported on .NET 10/11 and keep getting features, so they are brownfield lanes, not dead ends. Two facts change the house version policy: **.NET 8 and .NET 9 reached end of support on 2026-11-10**, and **.NET 11 (STS) shipped the same day** — .NET 10 LTS is the only sensible primary.

---

## 1. Which UI stack is primary

### What Microsoft recommends now

| Statement | Source (date) |
|---|---|
| "WinUI 3 is the recommended native UI framework for building new Windows desktop applications" — C# and C++, runs on Windows 10 1809 (17763) and later | [WinUI 3 overview](https://learn.microsoft.com/en-us/windows/apps/winui/winui3/) (2026-10-02) |
| "The Windows App SDK is the recommended development platform for building new Windows desktop applications" and is also usable from WPF, WinForms, Win32 | [Windows App SDK overview](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/) (2026-09-10) |
| .NET 11 announcement: "WinUI 3: recommended for new Windows desktop apps" | [Announcing .NET 11](https://devblogs.microsoft.com/dotnet/?p=61205) (2026-11-10) |
| "You don't have to migrate to WinUI 3. WPF and WinForms are fully supported on modern .NET and continue to receive feature updates." | [Migration decision guide](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/migrate-to-windows-app-sdk/migration-decision-guide) (2026-10-13) |
| Microsoft dropped the "3" from the WinUI name at Build 2026 to signal no further framework is coming; acknowledged "a ton of feature gaps" (DataGrid, charting "up and coming") | [Windows Latest](https://www.windowslatest.com/2026/10/31/one-reason-windows-11-has-so-many-web-apps-winui-still-lacked-basic-features-and-thats-finally-changing/) (2026-10-31, secondary) |

### Windows App SDK / WinUI — current state

| Fact | Value | Source |
|---|---|---|
| Latest stable | **2.6.5**, 2026-11-02 (NuGet `Microsoft.WindowsAppSDK` 2.6.5, 2026-11-03) | [Release channels](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/release-channels) (2026-11-06); [NuGet](https://www.nuget.org/packages/Microsoft.WindowsAppSDK) |
| Latest experimental | 2.6.6-experimental, 2026-11-06 | same |
| 2.0 GA | 2.0.1, 2026-04-29 — first SemVer release; NuGet version = SDK version; breaking changes only on majors (next side-by-side = 3.0.0) | [2.x release notes](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/release-notes/windows-app-sdk-2-0) |
| Stable minors in 2026 | 2.1.3 (05-21), 2.2.0 (06-09), 2.3.1 (07-16), 2.4.0 (08-13), 2.5.1 (09-16), 2.6.4 (10-27), 2.6.5 (11-02) | same; NuGet |
| Cadence | Stable: "major releases no more than every six months (plus minor/patch servicing updates as needed)"; in practice a minor ~monthly | Release channels |
| Servicing | 2.0 line **Current**, end of servicing 2027-04-29; 1.8 **Maintenance**, ended 2026-09-24; 1.7 and older out of support | Release channels |
| Metapackage | `Microsoft.WindowsAppSDK` → Base, Runtime, AI, DWrite, Foundation, InteractiveExperiences, ML, Search, Widgets, WinUI (reference only what you need) | NuGet |
| OS floor | APIs run on Windows 10 1809 and later; *supported* only on Windows versions still in support | Release channels |
| Open source | Repo MIT; phase 3 done May 2026; **mainline development moved to GitHub Aug 2026 (phase 4)**; outside PRs not yet accepted; XAML compiler partly closed; Chart control closed-source | [microsoft-ui-xaml](https://github.com/microsoft/microsoft-ui-xaml) (pushed 2026-11-15); [Windows Latest](https://www.windowslatest.com/2026/10/31/one-reason-windows-11-has-so-many-web-apps-winui-still-lacked-basic-features-and-thats-finally-changing/) |
| Experimental-only controls | `TableView` (2.5.4-exp, not a DataGrid replacement), `Chart` (line/area/bar), `InkCanvas`/`InkToolbar` (2.4.1-exp), `Window.Width/Height` (2.3.2-exp) | 2.x release notes |
| Experimental C#-only UI | "Reactor" templates (`reactor`, `reactor-mvu`, …) on prerelease `Microsoft.UI.Reactor` — WinUI without XAML | [winapp CLI with WinUI](https://learn.microsoft.com/en-us/windows/apps/dev-tools/winapp-cli/guides/winui) (2026-11-09) |
| Designer | Visual Studio XAML Designer "not yet available for WinUI 3" | Migration decision guide |

### WPF on .NET 10 / 11

| Fact | Source |
|---|---|
| .NET 9 added the Fluent theme, `ThemeMode`, accent colour | [What's new in WPF](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/whats-new/) (2026-09-17) |
| .NET 10: Fluent styles added for DatePicker, GridSplitter, GridView, GroupBox, Hyperlink, Label, NavigationWindow, RichTextBox, TextBox; HighContrast crash fixes; "Fluent UI style support is still in progress"; `Grid` short-form `ColumnDefinitions="1*, Auto"`; new `MessageBoxButton`s | [WPF .NET 10](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/whats-new/net100) |
| .NET 11 (RC1 notes): bug fixes only — Fluent backdrop on Windows 10, DWM-failure crashes, `WeakEventTable.Purge`, `ijwhost.dll` in self-contained publish | [WPF .NET 11](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/whats-new/net110) |

### WinForms on .NET 10 / 11

| Fact | Source |
|---|---|
| .NET 10: dark mode `Application.SetColorMode(SystemColorMode)` **no longer experimental** (WFO5001 gone); `Form.ShowAsync`, `Form.ShowDialogAsync`, `TaskDialog.ShowDialogAsync` **no longer experimental** (WFO5002 gone); `Form.ScreenCaptureMode`; clipboard shared with WPF, `GetData` obsoleted for `TryGetData<T>` (WFDEV005) | [WinForms .NET 10](https://learn.microsoft.com/en-us/dotnet/desktop/winforms/whats-new/net100) |
| .NET 11: opt-in `Application.SetDefaultVisualStylesMode(VisualStylesMode.Net11)` modern renderer, `KioskModeManager`, `Application.SystemVisualSettingsChanged`, `FormRevealMode.Deferred`, `SuspendPainting()` scopes, `Appearance.ToggleSwitch`, more dark-mode fixes. RC1 notes warned the visual-styles rendering "isn't final" | [WinForms .NET 11](https://learn.microsoft.com/en-us/dotnet/desktop/winforms/whats-new/net110); [.NET 11 announcement](https://devblogs.microsoft.com/dotnet/?p=61205) |

### Other stacks

| Stack | Current | Role | Source |
|---|---|---|---|
| C++/WinRT WinUI | `Microsoft.Windows.CppWinRT` 3.0.260818.1; `winapp run/pack` build `.vcxproj` | Native lane | [NuGet](https://www.nuget.org/packages/microsoft.windows.cppwinrt); [winapp WinUI guide](https://learn.microsoft.com/en-us/windows/apps/dev-tools/winapp-cli/guides/winui) |
| .NET MAUI | `Microsoft.Maui.Controls` 11.0.10; on Windows it renders through WinUI; .NET 11 made CoreCLR default, dropped `Controls.Compatibility` | Cross-platform; owned by mobile plugins, not this one | NuGet API; [.NET 11 announcement](https://devblogs.microsoft.com/dotnet/?p=61205) |
| Uno Platform | `Uno.Sdk` 7.0.22 | WinUI-API cross-platform | NuGet API |
| Avalonia | 12.1.6 | WPF-like cross-platform | NuGet API |

**Recommendation.** Primary: **WinUI (Windows App SDK 2.x) + C# on .NET 10 LTS, packaged (MSIX), MVVM with CommunityToolkit.Mvvm.** Lanes: **WPF on .NET 10/11** (brownfield, Fluent theme opt-in), **WinForms on .NET 10/11** (brownfield, dark mode + async forms), **C++/WinRT WinUI** (detect `.vcxproj`, light coverage). MAUI, Uno, Avalonia: detected and handed off, not taught here.

---

## 2. Toolchain lanes

| Item | Primary | Supported | Floor / note | Source |
|---|---|---|---|---|
| .NET | **10 LTS** (10.0.15, 2026-11-10; EOS 2028-11-14) | **11 STS** (11.0.0, 2026-11-10; EOS 2028-11-14) | **.NET 8 and 9 out of support since 2026-11-10** — flag, never target | [.NET support policy](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core) |
| Windows App SDK | **2.6.x** (Current, EOS 2027-04-29) | — | 1.8 left maintenance 2026-09-24; 1.x is a migration finding | Release channels |
| TFM | `net10.0-windows10.0.26100.0` (used across Microsoft's winapp docs) | `net11.0-windows10.0.26100.0`; 28000-series SDK | Windows SDK 10.0.26100.9457 (Sep 2026) and 10.0.28000.2957 (Sep 2026, the 26H1 series) both current | [winapp WinUI guide](https://learn.microsoft.com/en-us/windows/apps/dev-tools/winapp-cli/guides/winui); [Windows SDK notes](https://learn.microsoft.com/en-us/windows/apps/windows-sdk/release-notes) |
| Min OS | Windows 10 1809 (17763) is the WinAppSDK API floor | — | Windows 10 EOS 2025-10-14; consumer ESU now runs to **2027-10-12**, so the 1809 floor stays meaningful; Win11 24H2 Home/Pro EOS 2026-10-13; 26H2 GA Sep 2026 | [BleepingComputer](https://bleepingcomputer.com/news/microsoft/microsoft-quietly-extends-free-windows-10-esu-support-to-october-2027); [BleepingComputer 24H2](https://www.bleepingcomputer.com/news/microsoft/microsoft-windows-11-24h2-home-and-pro-reached-end-of-support/) |
| IDE | **Visual Studio 2026** + "WinUI application development" workload; `winget configure -f https://aka.ms/winui-config` | — | VS 2026 18.12 shipped 2026-11-10 (secondary source) | [Build your first WinUI app](https://learn.microsoft.com/en-us/windows/apps/get-started/start-here) (2026-11-13); [Eleven Forum](https://www.elevenforum.com/t/visual-studio-2026-version-18-12-0-released.50763/) |
| CLI | **winapp CLI 0.8.0** (2026-11-07, public preview): `winapp new --template winui|winui-navview|winui-tabview|winui-mvvm|winui-lib|winui-unittest`, `winapp run` (builds, installs runtime, registers identity), `--debug-output` (stowed-exception triage), `find-ui`, `find-api`, `ui inspect/search/invoke/screenshot`, `cert generate`, `pack`, `az-sign` | — | Templates pack `Microsoft.WindowsAppSDK.WinUI.CSharp.Templates`; `Microsoft.Windows.SDK.BuildTools.WinApp` hooks `dotnet run`; Developer Mode required | [winapp WinUI guide](https://learn.microsoft.com/en-us/windows/apps/dev-tools/winapp-cli/guides/winui); [WinAppCli releases](https://github.com/microsoft/WinAppCli/releases) |
| Analyzer | `Microsoft.Windows.SDK.BuildTools.WinUIAnalyzer` added per app project | — | Microsoft's agent plugin adds it on every project | [winui-dev-workflow SKILL.md](https://github.com/microsoft/winappCli/tree/main/plugins/winui) |
| Projection | CsWinRT **2.3.1** stable | 3.0.0-preview.261104.1 (rewrite on .NET 10, AOT-first, breaking: no embedded mode, no netstandard2.0) | Do not adopt 3.0 until stable | NuGet API; [CsWinRT releases (mirror)](https://github.yxlr123.workers.dev/microsoft/CsWinRT/releases) |
| Packaging | **Packaged MSIX, framework-dependent** (template default, "WinUI 3 apps are packaged by default") | Packaged with external location; unpackaged (`WindowsPackageType=None`); WinAppSDK self-contained | `PublishSingleFile` only for unpackaged + self-contained; ClickOnce **not supported** for WinUI 3 | [Choose a distribution path](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path) (2026-10-07) |
| Native AOT | Supported since WinAppSDK 1.6 (`PublishAot`); `winapp run --aot` validates it; needs MSVC C++ build tools; `{Binding}` reflection paths break — `x:Bind` only | — | Windows Community Toolkit 8.2 is AOT-ready | [1.6 notes](https://learn.microsoft.com/en-my/WINDOWS/APPS/windows-app-sdk/release-notes/windows-app-sdk-1-6); [winui-dev-workflow SKILL.md](https://github.com/microsoft/winappCli/tree/main/plugins/winui); [InfoQ WCT 8.2](https://www.infoq.com/news/2025/05/wct-8-2-native-aot) |
| Architectures | x64, ARM64 (`winapp run --arch arm64`; `msixbundle` for multi-arch); .NET 11 requires x86-64-v2 / Arm64 LSE | x86 | — | winapp guide; [Start Debugging](https://startdebugging.net/2026/11/dotnet-11-is-generally-available-what-to-change-in-your-project/) (secondary) |

---

## 3. Architecture conventions

| Topic | Convention | Source |
|---|---|---|
| MVVM | **CommunityToolkit.Mvvm 8.4.2** (2026-03-25): `[ObservableProperty]` on **partial properties** works without preview language version on C# 14 (Roslyn 5.0 generators); `[RelayCommand]`, `ObservableObject`, `Messenger` | [NuGet](https://www.nuget.org/packages/CommunityToolkit.Mvvm); [InfoQ 8.4](https://www.infoq.com/news/2024/12/dotnet-community-toolkit-84) |
| Project split | ViewModels and services in a separate class library "for improved testability"; DI manages view models and services | [MVVM Toolkit tutorial](https://learn.microsoft.com/en-us/windows/apps/tutorials/winui-mvvm-toolkit/intro) (2026-09-10); [Testing WinUI](https://learn.microsoft.com/en-us/windows/apps/develop/testing/) |
| Template | `winui-mvvm` template uses CommunityToolkit.Mvvm; `winui-navview` gives a `NavigationView` shell | winapp WinUI guide |
| DI | `Microsoft.Extensions.Hosting` / `DependencyInjection` (11.0.0 current) composed in `App`; constructor injection into view models | NuGet API; MVVM tutorial |
| Navigation | `NavigationView` + `Frame`; 2.5.1 fixed NavigationView pane/flyout crashes | 2.x release notes |
| Lifecycle | `Microsoft.Windows.AppLifecycle.AppInstance`: `GetCurrent().GetActivatedEventArgs()`, `FindOrRegisterForKey`, `RedirectActivationToAsync` (must be awaited off the STA), `Activated` event; WinUI apps multi-instance by default; redirection is not terminal (guard circular redirects) | [App instancing](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/applifecycle/applifecycle-instancing) (2026-11-10) |
| Custom `Main` | `DISABLE_XAML_GENERATED_MAIN` now *renames* the generated main (`XamlGeneratedProgram.XamlGeneratedMain()`) instead of removing it (2.3.1) | 2.x release notes |
| Windowing | `Window.AppWindow` for title bar/presenter; WinUI `TitleBar` control (since 1.7; drag regions automatic since 2.1.3: `IsDragRegion`, `AutoRefreshDragRegions`); `ExtendsContentIntoTitleBar` must be true before `PreferredHeightOption = Tall` | [Title bar customization](https://learn.microsoft.com/en-us/windows/apps/develop/title-bar) (2026-10-13) |
| Threading | Background → UI only through `DispatcherQueue.TryEnqueue`, batched (one enqueue per update, not per item); never `.Result`/`.Wait()` on the UI thread | [Microsoft winui-code-review quality rules](https://github.com/microsoft/winappCli/tree/main/plugins/winui) |
| Settings | Packaged: `ApplicationData`; unpackaged: `Microsoft.Windows.Storage.ApplicationData.GetForUnpackaged()` (2.2.0; registry path corrected in 2.4.0) | 2.x release notes |
| Windows Community Toolkit | `CommunityToolkit.WinUI.*` **8.2.251219** stable (2025-12-20); 8.3.260402-preview2 (2026-04-02) | [NuGet](https://www.nuget.org/packages/CommunityToolkit.WinUI.Controls.SettingsControls) |

---

## 4. Fluent 2 / Windows 11 design

| Topic | Rule | Source |
|---|---|---|
| Mica | Base layer of long-lived windows, applied once, visible in the title bar; content layer uses `LayerFillColorDefaultBrush`; falls back to solid colour when transparency is off, on battery saver, on low-end hardware, when inactive, below build 22000 | [Mica](https://learn.microsoft.com/en-us/windows/apps/design/style/mica) (2026-07-22) |
| Mica Alt | For tabbed title bars; commanding layer `LayerOnMicaBaseAltFillColorDefaultBrush` | same |
| Backdrops in WinUI | `Window.SystemBackdrop` (`MicaBackdrop`, `DesktopAcrylicBackdrop`); new `SystemBackdropElement` hosts Mica/Acrylic inside a `CornerRadius` (2.0) | 2.x release notes; [System backdrops](https://learn.microsoft.com/en-us/windows/apps/develop/ui/system-backdrops) |
| Title bar | Extend content, keep caption buttons system-drawn; `Tall` when the bar holds interactive content | Title bar customization |
| High contrast | Mica shows the user's chosen colour; test every screen in High Contrast | Mica; Microsoft quality rules |
| Theme resources | `{ThemeResource}` brushes; experimental `FrameworkElement.SetThemeResourceBinding` (2.5.4-exp) | 2.x release notes |
| Corners, typography, icons, DPI, snap layouts | See Not verified — standard Fluent guidance (Segoe UI Variable, Segoe Fluent Icons, 4/8 px corner radii, per-monitor DPI v2) was not re-fetched this session | — |

---

## 5. Platform integration

| Capability | Current API / rule | Source |
|---|---|---|
| App notifications | Windows App SDK `AppNotificationManager` + `AppNotificationBuilder`; works for WinUI, WPF, WinForms, console; **elevated (admin) apps cannot send or receive app notifications** | [App notifications](https://learn.microsoft.com/en-us/windows/apps/develop/notifications/app-notifications/) (2026-10-13) |
| Push | WNS via Windows App SDK push notifications | same; [Windows App SDK overview](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/) |
| File/folder pickers | **`Microsoft.Windows.Storage.Pickers`** (WinAppSDK 1.8+): `new FileOpenPicker(this.AppWindow.Id)`, returns `PickFileResult.Path`; no `InitializeWithWindow`. Legacy `Windows.Storage.Pickers` needs `WinRT.Interop.InitializeWithWindow.Initialize(picker, hwnd)` | [Pickers](https://learn.microsoft.com/en-us/windows/apps/develop/files/using-file-folder-pickers) (2026-11-10) |
| Rich activation | File, protocol, restart, startup via AppLifecycle; file/protocol associations need package identity (manifest) | [Windows App SDK overview](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/); distribution path page |
| Package identity unlocks | Notifications, background tasks, file type associations, protocol handlers, share target | [Choose a distribution path](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path) |
| Widgets | Windows App SDK widget providers | [Widget providers](https://learn.microsoft.com/en-us/windows/apps/develop/widgets/widget-providers) |
| Windows AI APIs | Phi Silica (NPU; GPU on RTX 30+/RX 9060+ with Developer Mode), Text Recognition, Image Super Resolution/Description/Segmentation, Object Erase, Image Generation, Video Super Resolution (NPU/CPU), Speech Recognition (experimental). Check `GetReadyState`, consent before `EnsureReadyAsync` download. **Phi Silica is being replaced by "Aion Instruct"** (Insider Nov 2026, retail Jan 2027, then Phi Silica removed). Phi Silica is a Limited Access Feature (2.0); not available in China | [Windows AI APIs](https://learn.microsoft.com/en-us/windows/ai/apis/) (2026-11-13); 2.x release notes |
| Windows ML | `Microsoft.Windows.AI.MachineLearning` (ONNX Runtime 1.24.x), Windows 10 1903+; ARM64EC in 2.3.1 | 2.x release notes |
| App Content Search | Stable since 2.5.1 as a Limited Access Feature (token required) | Release channels |
| Crash reporting hook | WER via `windows.diagnosticServiceModule` manifest extension (2.5.1) | 2.x release notes |
| Credentials | `PasswordVault` (Credential Locker) for tokens; `DataProtectionProvider("LOCAL=user")` for data at rest | [Microsoft quality rules](https://github.com/microsoft/winappCli/tree/main/plugins/winui) |
| WebView2 | `Microsoft.Web.WebView2` 1.0.4314.35; lock down `CoreWebView2.Settings`, cancel `NavigationStarting` off-allowlist, devtools off in release | NuGet API; Microsoft quality rules |

---

## 6. Distribution and security

| Topic | Fact | Source |
|---|---|---|
| Recommended path | "For most developers, the Microsoft Store is the recommended path." MSIX submissions are re-signed by Microsoft (free signing), Store-managed updates | [Choose a distribution path](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path) |
| Store accounts | Individual registration free since Sep 2025 (ID + selfie, no card); **company accounts free since 2026-05-07** (Entra ID sign-up) | [Windows blog, individuals](https://blogs.windows.com/windowsdeveloper/2025/09/10/free-developer-registration-for-individual-developers-on-microsoft-store/); [Windows blog, companies](https://blogs.windows.com/windowsdeveloper/2026/05/07/publish-to-microsoft-store-as-a-company-now-with-free-registration-and-faster-onboarding/) |
| Store MSI/EXE path | Allowed; installer and all PE files signed with a Microsoft Trusted Root Program cert; no Store-managed updates | Distribution path |
| Direct MSIX | CA-trusted cert; `.appinstaller` for auto-update; `ms-appinstaller:` one-click URI **disabled by default since Dec 2023** | same |
| Code signing | **Azure Artifact Signing** (formerly Trusted Signing): Basic $9.99/mo (5,000 signatures, 1 profile), Premium $99.99/mo (100,000, 10 profiles); GA in US, Canada, Europe; individuals in US/Canada, organisations in US/Canada/EU/UK; 24-hour certs, timestamped; billing starts on account creation; `winapp az-sign` | [DevClass](https://www.devclass.com/security/2026/01/14/code-signing-windows-apps-may-be-easier-and-more-secure-with-new-azure-artifact-service/4079554) (2026-01-14); [pricing page](https://azure.microsoft.com/en-us/pricing/details/artifact-signing/); [SmartScreen](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation) |
| SmartScreen | Store apps never warn; **EV certs no longer bypass SmartScreen**; reputation builds per file hash and per publisher cert over weeks; keep one signing identity; never modify signed files | [SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation) |
| Smart App Control | On Windows 11 may supersede SmartScreen; blocks unsigned executables without positive reputation, for all executables, not only downloads | same |
| winget | Add a manifest to `microsoft/winget-pkgs` on top of any path | Distribution path |
| Unpackaged auto-update | **Velopack 1.2.161** (2026-09-29; avoid deprecated 1.2.158; 1.3 in preview) | [NuGet](https://www.nuget.org/packages/velopack) |
| ClickOnce | WPF/WinForms only; not for WinUI 3 | Distribution path |
| Least privilege | Minimal manifest capabilities; never require elevation (elevated apps lose notifications); HTTPS only, never override cert validation; never log tokens/PII | Microsoft quality rules; App notifications |
| Dev cert | `winapp cert generate` is test-only with a default password | winapp WinUI guide |

---

## 7. Accessibility

| Rule | Source |
|---|---|
| Every interactive control has `AutomationProperties.Name` (or `LabeledBy`); decorative images `AccessibilityView="Raw"` | [Microsoft quality rules](https://github.com/microsoft/winappCli/tree/main/plugins/winui) |
| Stable, unique `AutomationProperties.AutomationId` on every interactive control — Microsoft's own agent rule; it is what `winapp ui`, Appium `accessibility id` and FlaUI target | same; [AI-assisted testing](https://learn.microsoft.com/en-us/windows/apps/develop/ai-assisted/testing) (2026-10-02); [appium-windows-driver](https://github.com/appium/appium-windows-driver) |
| Semantic controls (`Button`, `HyperlinkButton`, `ListView`) over clickable `Border`/`Grid` | Microsoft quality rules |
| Keyboard: logical `TabIndex`, `AccessKey`, `KeyboardAccelerator`; every core scenario completable without a mouse | same; [Test before you ship](https://learn.microsoft.com/en-us/windows/apps/develop/test-before-you-ship) (2026-11-10) |
| Narrator (and NVDA) announce each control; never hide content with `Collapsed` for screen readers | same |
| High Contrast tested; 4.5:1 / 3:1 contrast; no colour-only state | Microsoft quality rules; Mica |
| **Accessibility Insights for Windows** to find missing names and inspect the UIA tree | [Test before you ship](https://learn.microsoft.com/en-us/windows/apps/develop/test-before-you-ship); [Testing WinUI](https://learn.microsoft.com/en-us/windows/apps/develop/testing/) |
| WinForms .NET 11 exposes `TextScaleFactor` via `SystemVisualSettings` | [WinForms .NET 11](https://learn.microsoft.com/en-us/dotnet/desktop/winforms/whats-new/net110) |

---

## 8. Testing

| Layer | Tool / version | Notes | Source |
|---|---|---|---|
| UI-thread unit tests | **WinUI Unit Test App** (MSTest, `[UITestMethod]`); `winapp new --template winui-unittest` | Required for anything touching `Microsoft.UI.Xaml` types | [Testing WinUI](https://learn.microsoft.com/en-us/windows/apps/develop/testing/) (2026-09-10) |
| Plain unit tests | MSTest (4.5.3) / NUnit / xUnit project; must match the app's Windows TFM, set `RuntimeIdentifiers`, `<WindowsAppSdkBootstrapInitialize>true</…>` when it loads WinAppSDK types | View models in a separate library need none of that | same |
| Agent/inner-loop UI checks | `winapp ui inspect|search|click|invoke|set-value|screenshot` over UI Automation; `--on sandbox` | Microsoft's `winui-ui-testing` skill; needs a graphical session in CI | [AI-assisted testing](https://learn.microsoft.com/en-us/windows/apps/develop/ai-assisted/testing) |
| Appium (Appium 3) | `appium-windows-driver` **6.3.1** (2026-10-08) — wraps WinAppDriver; Appium 3 only since 5.0 | Microsoft's testing page still names it | npm registry; [Testing WinUI](https://learn.microsoft.com/en-us/windows/apps/develop/testing/) |
| Appium (Appium 3) | **NovaWindows** `appium-novawindows-driver` **1.5.0** (2026-10-24; 2.0.0-preview.2 on `develop`) — recommended drop-in replacement in the Appium driver README | Community (Automate The Planet) | npm registry; [repo](https://github.com/AutomateThePlanet/appium-novawindows-driver) |
| Appium (Appium 4) | **`appium-wincore-driver` 4.1.1** (2026-11-13; repo `appium/appium-wincore-driver`, published by verisoft-ai, created 2026-09-02) — real UIA, WebView2 via CDP, `automationName: Wincore`; **v4 needs Appium 4 (4.0.0-beta.8); use 3.3.x on Appium 3** (3.9.1 stable) | Named by the Appium Windows driver README as the official replacement for Appium 3 and 4 | npm registry; [appium-windows-driver](https://github.com/appium/appium-windows-driver) |
| WinAppDriver | v1.2.1 (2020); "not maintained by Microsoft for years"; legacy JSONWP only — incompatible with Appium 4 | Do not start new suites on it | [appium-windows-driver](https://github.com/appium/appium-windows-driver); [Testing WinUI](https://learn.microsoft.com/en-us/windows/apps/develop/testing/) |
| FlaUI | `FlaUI.UIA3` **5.0.0** (2025-02-25), targets net6/net8-windows, net48 | In-process .NET UIA library; no newer release | [NuGet](https://www.nuget.org/packages/FlaUI.UIA3) |
| .NET Appium client | `Appium.WebDriver` 9.0.0 | — | NuGet API |
| WebView2 content | Playwright connects to WebView2 | — | [Testing WinUI](https://learn.microsoft.com/en-us/windows/apps/develop/testing/) |
| Store pre-check | Windows App Certification Kit; clean-device install of the release package | — | [Test before you ship](https://learn.microsoft.com/en-us/windows/apps/develop/test-before-you-ship) |
| Locator | All of the above read **`AutomationId`** (Appium `accessibility id`) | — | appium-windows-driver README; AI-assisted testing |

---

## 9. Performance and observability

| Topic | Rule | Source |
|---|---|---|
| Bindings | `x:Bind` (compiled, default `OneTime`) over `{Binding}`; `{Binding}` only where `x:Bind` cannot reach; required for Native AOT | [Microsoft quality rules](https://github.com/microsoft/winappCli/tree/main/plugins/winui) |
| Deferred UI | `x:Load` for subtrees not shown at start; `x:Phase` in item templates | same |
| Lists | `ListView`/`GridView`/`ItemsRepeater` past ~20 items; `ISupportIncrementalLoading` for paging | same |
| XAML perf | 2.3.1 added many opt-in XAML optimisations via XamlChangeIds; 2.5.4-exp fixed WinUI resource-tracking memory growth and orphaned native objects in .NET apps | 2.x release notes |
| Crash triage | `winapp run --debug-output [--symbols]` decodes stowed exceptions | winapp WinUI guide |
| Telemetry | Microsoft's testing page recommends **OpenTelemetry** for new projects (`OpenTelemetry` 1.21.0); App Insights for Azure-only | [Testing WinUI](https://learn.microsoft.com/en-us/windows/apps/develop/testing/); NuGet API |
| Crashes | WER; Partner Center health reports for Store MSIX; local dump collection for LOB; Sentry .NET 7.0.0 | [Testing WinUI](https://learn.microsoft.com/en-us/windows/apps/develop/testing/); NuGet API |
| Logging | Structured logging, never tokens/PII | Microsoft quality rules |

---

## 10. Migration paths

| From | Path | Source |
|---|---|---|
| .NET Framework WPF/WinForms | **Upgrade in place** to .NET 10 LTS first (GitHub Copilot upgrade / modernization agent, VS 2026, paid Copilot; VB not fully supported); C# WinUI cannot target .NET Framework | [Migration decision guide](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/migrate-to-windows-app-sdk/migration-decision-guide); [Copilot upgrade](https://learn.microsoft.com/en-us/dotnet/core/porting/github-copilot-upgrade/how-to-upgrade-with-github-copilot) |
| WPF/WinForms on modern .NET | **Modernize in place** (Windows App SDK NuGet, WinRT APIs, MSIX, XAML Islands) or **move to WinUI** view by view; blockers: WCF server, ASMX, `System.Configuration`, COM, third-party control vendors | same |
| WPF → WinUI | Microsoft guide `wpf-patterns-winui3`; Microsoft agent skill `winui-wpf-migration` | same; [WinUI agent plugin](https://learn.microsoft.com/en-us/windows/apps/develop/ai-assisted/winui-agent-plugin) |
| UWP → WinUI | Migrate-from-UWP guide (app model, `CoreWindow` gone, pickers need HWND or new pickers) | same; Pickers |
| Windows App SDK 1.x → 2.x | 1.8 out of maintenance 2026-09-24; 2.0 is SemVer; watch `DISABLE_XAML_GENERATED_MAIN` rename and `GetForUnpackaged` registry fix | Release channels; 2.x release notes |
| Xamarin.Forms/MAUI | Out of scope here (mobile plugins) | — |

---

## 11. What Microsoft ships for AI agents

| Thing | Facts | Source |
|---|---|---|
| **WinUI agent plugin** | Claude Code: `claude plugin marketplace add microsoft/win-dev-skills` → `claude plugin install winui@win-dev-skills` (Copilot CLI: `winui@awesome-copilot`); agent `winui-dev`; 8 skills: `winui-setup`, `winui-dev-workflow`, `winui-design`, `winui-code-review`, `winui-ui-testing`, `winui-packaging`, `winui-wpf-migration`, `winui-session-report`; plugin v0.7.1, MIT | [WinUI agent plugin](https://learn.microsoft.com/en-us/windows/apps/develop/ai-assisted/winui-agent-plugin) (2026-07-05); [marketplace.json](https://github.com/microsoft/win-dev-skills) (pushed 2026-11-08) |
| Same marketplace | `winappcli` plugin (packaging/signing/identity for Electron, .NET, C++, Rust, Flutter, Tauri); `windbg` plugin | same |
| winapp CLI | Agent-oriented: `--json` everywhere, `find-ui`/`find-api` grounded lookups, `ui` automation, `--detach --json` | winapp WinUI guide |
| Docs entry point | "Build an app with an AI agent" is the first card on the WinUI getting-started hub | [Getting started with WinUI](https://learn.microsoft.com/en-us/windows/apps/get-started/) (2026-11-04) |
| Modernization | GitHub Copilot upgrade / modernization agent for .NET Framework → .NET 10 (WPF, WinForms) | Migration decision guide |
| Third-party MCP | `wincore-mcp` (verisoft-ai) drives WinCore sessions over WebDriver | appium-wincore-driver README (npm) |
| .NET 11 SDK | Ships an MCP server template | [Start Debugging](https://startdebugging.net/2026/11/dotnet-11-is-generally-available-what-to-change-in-your-project/) (secondary) |

**Implication for the plugin:** our skills should *complement*, not duplicate, `winui@win-dev-skills`: we own the house rules (KISS, test ids, three-state regions, telemetry, ≥ 80% branch coverage, the plan/gate format) and the WPF/WinForms lanes; we can tell the agent to use `winapp find-ui`/`find-api` for grounded control lookups.

---

## Not verified

- Whether Windows App SDK 2.6 officially lists .NET 11 TFMs (`net11.0-windows…`) as supported; release notes say nothing about .NET TFMs.
- The template's default `TargetPlatformMinVersion` (assumed `10.0.17763.0` from the 1809 floor) and whether 2.x templates now default to the 28000-series SDK.
- Whether the `winui-mvvm` template wires `Microsoft.Extensions.Hosting` DI or a simpler container.
- WinUI XAML Designer: only the migration guide's "not yet available" — no date.
- Fluent design specifics not re-fetched: Segoe UI Variable type ramp, Segoe Fluent Icons, corner-radius tokens, snap layouts, per-monitor DPI v2 behaviour.
- Exact Visual Studio 2026 build (18.12, 2026-11-10) comes from Eleven Forum, not Microsoft's notes.
- Startup tasks, background tasks and share target APIs in Windows App SDK 2.x — not re-read; only "requires package identity" is verified.
- Windows Hello / passkey APIs for desktop apps; `PasswordVault` availability for unpackaged apps.
- PerfView / WPR / ETW current versions; OpenTelemetry desktop exporter guidance beyond Microsoft's two-line sample.
- Sentry's WinUI-specific integration status (only the `Sentry` 7.0.0 package version was checked).
- Relationship between NovaWindows and WinCore drivers (both target real UIA; WinCore is under the `appium` GitHub org but published by verisoft-ai).
- Artifact Signing individual eligibility outside the US/Canada and any minimum organisation history.
- WinUI open-source phase-4 date comes from one secondary source (Windows Latest); the repo's discussion thread was not read.
- .NET 11 x86-64-v2 / Arm64 LSE CPU floor comes from secondary coverage.
