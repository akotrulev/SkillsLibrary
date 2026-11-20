---
name: concepts
description: Use when writing or reviewing Windows desktop C# and XAML (lane detection, packaged identity, UI thread, DPI, nullable). Triggers "which Windows framework". Not for a diff review (code-review).
disable-model-invocation: true
---

# Windows — The C# and XAML Coding Standard

How a Windows desktop app is written in this library: **WinUI on Windows App SDK 2.x, C# on .NET 10**, packaged MSIX, with WPF, WinForms and C++/WinRT as lanes for codebases that already use them. It is the Windows half of CLAUDE.md § Desktop code rules; the audit rows are sections A and B of `desktop-windows:standards-audit`. Design facts come from `design/ui-ux-pro-max` (`--stack winui`; `--stack wpf` for the WPF lane); where it and this skill disagree, the corpus wins.

## Version lane — detect first, key every recipe to it

Read the `.csproj` / `Directory.Build.props` (`TargetFramework`, `UseWinUI`, `UseWPF`, `UseWindowsForms`, `WindowsPackageType`, `LangVersion`), `global.json` and the `Microsoft.WindowsAppSDK` version **before** writing. Never up-level the TFM, Windows App SDK major, C# language version or the UI framework as a side effect.

| Concern | Primary | Supported | Flag, never target |
|---|---|---|---|
| .NET | **10 LTS** (EOS 2028-11-14) | **11 STS** (GA 2026-11-10) | **8 and 9: out of support since 2026-11-10** — a migration finding (`desktop-windows:migration`) |
| C# | 14 (ships with .NET 10) | 15 with .NET 11 | below the SDK's default only when the project pins it |
| Windows App SDK | **2.6.x** (SemVer since 2.0.1; 2.0 line serviced to 2027-04-29) | — | 1.x: out of support, a migration finding |
| TFM | `net10.0-windows10.0.26100.0` | `net11.0-windows10.0.26100.0` (unverified: release notes do not list .NET 11 TFMs) | a TFM with no `-windows` OS part |
| API floor | Windows 10 1809 (17763) | — | — |

**Conflict, recorded (plan 012 Q2, D2).** CLAUDE.md § Stack defaults and § Version policy still say ".NET 10 primary / 8–9 supported". This plugin follows the vendor: 8 and 9 are out of support. It does not edit the Version policy; the library-wide update is the user's decision.

A down-level project is not flagged for lacking a newer feature, except an out-of-support runtime or SDK, which is always a finding.

## When to use

- Writing C# or XAML for a Windows desktop app, or choosing a UI framework for one
- "WinUI, WPF or WinForms?", "is this project packaged?", "why does this crash off the UI thread?"
- Detecting what a brownfield repo is before any other skill runs

## When NOT to use

- Project, TFM, packaging, analyzers → [`project-setup`](../project-setup/SKILL.md)
- ViewModels, DI, services → [`architecture`](../architecture/SKILL.md)
- Controls and pages → [`ui-components`](../ui-components/SKILL.md); theme and Fluent → [`styling`](../styling/SKILL.md)
- Windows, titlebar, navigation, commands → `desktop-windows:windows-and-navigation`
- WPF, WinForms, C++/WinRT specifics → `desktop-windows:wpf`, `:winforms`, `:cpp-winrt`
- macOS → `desktop-macos:concepts`; an ASP.NET or library project with no UI → `be-dotnet`

---

## The lane table

| Lane | Role | Skill | Never |
|---|---|---|---|
| **WinUI** (Windows App SDK) + C# | Primary for new apps. Microsoft: "the recommended native UI framework for new Windows desktop apps" | this plugin's skills | Experimental-channel controls (`TableView`, `Chart`, Ink) in a production build |
| **WPF** on .NET 10/11 | Brownfield; fully supported; Fluent theme opt-in and "still in progress" | `wpf` | Adding WinUI to a WPF app as a side effect |
| **WinForms** on .NET 10/11 | Brownfield; dark mode and `ShowAsync` stable since .NET 10 | `winforms` | Adding WinUI or WPF to a WinForms app as a side effect |
| **C++/WinRT** WinUI | Native lane for `.vcxproj` projects | `cpp-winrt` | Raw `new` / `delete`, ownerless coroutines |

**Detected, not taught (D5).** .NET MAUI, Avalonia and Uno Platform are named, never guided; the agent says so and stops. Electron, Tauri, Qt and React Native for Windows are the same.

## Detection markers

Run from the repo root. A grep hit is a lead, not a finding.

| Marker | Means |
|---|---|
| `<UseWinUI>true</UseWinUI>` or `Microsoft.WindowsAppSDK` package reference, `.xaml` using `Microsoft.UI.Xaml` | WinUI |
| `<UseWPF>true</UseWPF>`; `.xaml` using `System.Windows` | WPF |
| `<UseWindowsForms>true</UseWindowsForms>`; `*.Designer.cs` | WinForms |
| `*.vcxproj` + `Microsoft.Windows.CppWinRT`, `*.idl` | C++/WinRT |
| `<UseMaui>true</UseMaui>`, `Microsoft.Maui.Controls` | MAUI — detected, not taught |
| `Avalonia` package, `*.axaml` | Avalonia — detected, not taught |
| `Uno.Sdk` in `global.json`, `Uno.WinUI` | Uno — detected, not taught |
| `Package.appxmanifest` or `Package.wapproj` / `<WindowsPackageType>None` | packaged / unpackaged |
| `<TargetFramework>net(4\|core\|5\|6\|7\|8\|9)` | out-of-support or .NET Framework: migration |

```bash
rg -n "UseWinUI|UseWPF|UseWindowsForms|UseMaui|WindowsPackageType|TargetFramework|WindowsAppSDK" -g '*.csproj' -g '*.props'
rg -ln "Avalonia|Uno\.Sdk|Uno\.WinUI" -g '*.csproj' -g 'global.json'
```

A solution may hold more than one lane (a WPF shell hosting WinUI through interop). Detect per project, record it, and follow each project's own lane.

## The Windows mental model

- **Packaged identity.** A packaged (MSIX) app has an identity that unlocks notifications, background tasks, file and protocol activation, share targets and clean uninstall. An unpackaged app (`WindowsPackageType=None`) has none of these; it needs a recorded reason. ClickOnce does not support WinUI.
- **Activation.** The OS starts the app with an activation kind (launch, file, protocol, toast). WinUI apps are multi-instance by default; single instancing is `AppInstance`, never a hand-rolled mutex (`desktop-windows:activation-and-notifications`).
- **The UI thread (STA).** Every control belongs to the thread that created it. Work off it reaches controls only through `DispatcherQueue.TryEnqueue`, **batched** (one enqueue per update, not per item). Never `.Result`, `.Wait()` or `GetAwaiter().GetResult()` on it: that deadlocks.
- **DPI.** Per-monitor DPI v2. Sizes are in effective pixels; a window moved between monitors rescales. Never hard-code a pixel size from a screenshot; test at 100 %, 150 % and 200 %.
- **Elevation.** Never require admin. An elevated app cannot send app notifications and cannot receive drag-drop from a non-elevated one.
- **Lifetime.** A window closing cancels the work it started. A `CancellationTokenSource` lives with the view model that owns the work.

## C# standard

Formatting is the `.editorconfig`'s; this list is what formatting cannot.

- **Nullable reference types on, warnings as errors.** No `!` null-forgiving operator outside tests; no `#nullable disable`.
- **Names:** `PascalCase` types, members and constants; `_camelCase` private fields; `Async` suffix on every `Task`-returning method except event handlers; `I` prefix on interfaces. A file holds one top-level type named after it.
- **Records** for immutable data (models, DTOs, state); `init` / `required` properties over constructors with six parameters. **`sealed` by default**; inheritance only for a designed hierarchy — composition over inheritance.
- **`async void` only for an event handler**, and its whole body is a `try`/`catch` that routes to the error path (`desktop-windows:error-handling`). Everywhere else `async Task`.
- **`CancellationToken` is the last parameter** of every async method that does I/O and is passed down, never dropped.
- **`TimeProvider` over `DateTime.Now`**, so tests control time.
- **Structured logging only** through `ILogger<T>` with message templates; never `$""` in a log call; no tokens, paths of user data or personal data in a message.
- **Interfaces on the second implementer** (CLAUDE.md § Simplicity). A service interface with one implementation and no test fake is an unearned abstraction; a fake in the unit tests is a second implementation and earns it.
- **No static mutable state.** `static` holds constants and pure functions; the one exception is the `App` instance WinUI itself creates, and nothing reaches it through `App.Current` to find a service (a service locator).
- **No inline comments;** a doc comment only when the name cannot carry the contract (CLAUDE.md § Comments).

## XAML standard

- **`x:Bind` over `{Binding}`.** Compiled, typed, AOT-safe. `{Binding}` is reflection: it breaks under Native AOT and trimming, and it is a finding in a WinUI app. Default mode for `x:Bind` is `OneTime`; say `Mode=OneWay` for anything that changes.
- **Code-behind holds view concerns only:** focus, animation triggers, a `Loaded` hook that calls a view-model command. Business logic in `*.xaml.cs` is a finding.
- **Theme resources** (`{ThemeResource}`) for brushes, never a hex literal; styles in resource dictionaries, never copied per page ([`styling`](../styling/SKILL.md)).
- **Every interactive element and list container carries `AutomationProperties.AutomationId`** and every one an accessible name (`desktop-windows:test-ids`, `:accessibility`).
- **No `Thread.Sleep` and no `Task.Delay` to wait for UI;** wait on the condition.

## Common gotchas

- **Calling a control from a worker thread** — `COMException` (0x8001010E). Marshal with `DispatcherQueue.TryEnqueue`.
- **Treating a packaged and an unpackaged run as the same** — `ApplicationData.Current` throws without identity; see `desktop-windows:offline-and-storage`.
- **Adding a Windows App SDK package to a WPF or WinForms app** pulls WinUI in transitively — a side-effect lane change; reference only the component needed and say so.
- **`.NET 8` / `9` left in a `global.json`** — the SDK is out of support: raise to 10, never silently.
- **Reading `Window.Content.XamlRoot` before the window is activated** — null; use it from `Loaded`.

## Handoffs

- Project files, TFM, packaging, analyzer, ARM64 → [`project-setup`](../project-setup/SKILL.md)
- MVVM, DI, services → [`architecture`](../architecture/SKILL.md)
- Pages, controls, dialogs → [`ui-components`](../ui-components/SKILL.md); Fluent, theme, motion → [`styling`](../styling/SKILL.md)
- Windows, navigation, commands → `desktop-windows:windows-and-navigation`
- Secrets, WebView2, signing → `desktop/_shared/security`, `desktop/_shared/distribution`
- .NET 8/9 → 10, WinAppSDK 1.x → 2.x, WPF → WinUI → `desktop-windows:migration`
- Mac counterpart → `desktop-macos:concepts`
