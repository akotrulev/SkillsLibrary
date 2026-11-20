---
name: project-setup
description: Use when creating or hardening a Windows desktop project (WinUI template, TFM, MSIX, Directory.Build.props, analyzers, ARM64). Triggers "new WinUI app". Not for signing and CI (distribution).
disable-model-invocation: true
---

# Windows — Project Setup

How a Windows desktop solution is created and kept strict: **a template, an explicit TFM and OS floor, packaged MSIX, one `Directory.Build.props`, nullable and warnings as errors, the WinUI analyzer, x64 + ARM64.** Audit rows: sections A and B of `desktop-windows:standards-audit`. Design facts: `design/ui-ux-pro-max --stack winui`.

## Version lane

| Concern | Primary | Supported | Rule |
|---|---|---|---|
| .NET SDK | **10 LTS** | **11 STS** | 8 / 9 out of support since 2026-11-10: flag, never target (Q2, D2) |
| Windows App SDK | `Microsoft.WindowsAppSDK` **2.6.x** | — | Stable channel only in a production build; `*-experimental` never. 1.x is a migration finding |
| TFM | `net10.0-windows10.0.26100.0` | `net11.0-windows10.0.26100.0` (unverified for WinAppSDK 2.6); the 28000-series SDK | Write the OS part explicitly |
| `TargetPlatformMinVersion` | `10.0.17763.0` (Windows 10 1809, the API floor) | raise only for a feature needing it, with a recorded reason | **Written explicitly.** The official template page does not state its default (re-checked 2026-11-15), so never rely on it |
| Packaging | **Packaged MSIX, framework-dependent** | packaged with external location; unpackaged (`WindowsPackageType=None`); self-contained | Unpackaged needs a recorded reason. ClickOnce is not supported for WinUI |
| Architectures | x64, ARM64 | x86 | Ship both; `msixbundle` for multi-arch |
| Tooling | Visual Studio 2026 ("WinUI application development" workload) | `winapp` CLI **0.8.0** (public preview) | Every `winapp` recipe below has a `dotnet` / Visual Studio fallback (D10) |

Never raise the TFM, the Windows App SDK major, the C# version or `TargetPlatformMinVersion` as a side effect of other work.

## Create the project

**Visual Studio 2026** (fallback that always works): *Create a new project* → "WinUI Blank App (Packaged)" (or the NavigationView / MVVM variants the installed workload offers).

**`dotnet` CLI** (the pack `winapp new` wraps):

```powershell
dotnet new install Microsoft.WindowsAppSDK.WinUI.CSharp.Templates
dotnet new winui-mvvm -n OrdersApp
```

**`winapp` CLI 0.8.0** (preview; needs Developer Mode for `run`):

```powershell
winapp new --list
winapp new --name OrdersApp --template winui-mvvm --use-defaults
```

| Template | Use |
|---|---|
| `winui` | Minimal blank app |
| `winui-navview` | A `NavigationView` shell — the default for a multi-area app |
| `winui-tabview` | A `TabView` shell — document-like apps |
| `winui-mvvm` | CommunityToolkit.Mvvm wired in |
| `winui-lib` | Class library for view models and services |
| `winui-unittest` | Packaged MSTest app — only for tests that need XAML types (D8) |
| `reactor*` | **Experimental, never** — prerelease `Microsoft.UI.Reactor`, no XAML |

**What the templates do not tell you (re-checked 2026-11-15).** The official pack page states `net10.0` as the default and that generated projects target `net{N}.0-windows10.0.26100.0`. It does **not** say whether `winui-mvvm` registers `Microsoft.Extensions.Hosting`, nor the `TargetPlatformMinVersion` default. After scaffolding, **read the generated `.csproj` and `App.xaml.cs`**: if no host exists, add it per [`architecture`](../architecture/SKILL.md); write `TargetPlatformMinVersion` yourself.

## Solution layout

```
OrdersApp.sln
Directory.Build.props        Directory.Packages.props        global.json        .editorconfig
src/OrdersApp/               WinUI app: App, Views, Resources, Package.appxmanifest
src/OrdersApp.Core/          class library: view models, services, models  (net10.0, no -windows)
tests/OrdersApp.Core.Tests/  NUnit
```

- **View models and services live in a class library** that targets plain `net10.0`: it is testable without a UI runner and cannot reference a control by mistake. The app project holds XAML, code-behind, resources and the manifest.
- **A second library only on a real second consumer** (CLAUDE.md § Simplicity). A solution of one app and one core library is the default.
- `global.json` pins the SDK (`"version": "10.0.x"`, `"rollForward": "latestFeature"`).

## `Directory.Build.props` and central packages

```xml
<Project>
  <PropertyGroup>
    <LangVersion>latest</LangVersion>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <AnalysisMode>Recommended</AnalysisMode>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <Deterministic>true</Deterministic>
  </PropertyGroup>
</Project>
```

```xml
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Microsoft.WindowsAppSDK" Version="2.6.5" />
    <PackageVersion Include="Microsoft.Windows.SDK.BuildTools.WinUIAnalyzer" Version="(current on NuGet)" />
    <PackageVersion Include="CommunityToolkit.Mvvm" Version="8.4.2" />
    <PackageVersion Include="Microsoft.Extensions.Hosting" Version="10.0.0" />
  </ItemGroup>
</Project>
```

- **Every version lives in `Directory.Packages.props`;** a `Version=` in a `.csproj` is a finding. The analyzer's version is read from NuGet, not copied from this page.
- Pin the Extensions packages to the **runtime major** (10 on .NET 10).

## The WinUI app project

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net10.0-windows10.0.26100.0</TargetFramework>
    <TargetPlatformMinVersion>10.0.17763.0</TargetPlatformMinVersion>
    <RootNamespace>OrdersApp</RootNamespace>
    <UseWinUI>true</UseWinUI>
    <WindowsPackageType>MSIX</WindowsPackageType>
    <EnableMsixTooling>true</EnableMsixTooling>
    <Platforms>x64;ARM64</Platforms>
    <RuntimeIdentifiers>win-x64;win-arm64</RuntimeIdentifiers>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.WindowsAppSDK" />
    <PackageReference Include="Microsoft.Windows.SDK.BuildTools.WinUIAnalyzer" PrivateAssets="all" />
    <PackageReference Include="CommunityToolkit.Mvvm" />
    <ProjectReference Include="..\OrdersApp.Core\OrdersApp.Core.csproj" />
  </ItemGroup>
</Project>
```

- **`Microsoft.Windows.SDK.BuildTools.WinUIAnalyzer` goes on every WinUI app project** — it catches WinUI misuse at build time.
- **Reference only the Windows App SDK components the app uses** (`Microsoft.WindowsAppSDK.WinUI`, `.Foundation`, …) when trimming matters; the `Microsoft.WindowsAppSDK` metapackage pulls AI, ML and Widgets too.
- **`WindowsPackageType=None`** (unpackaged) needs its reason recorded in the project's decision log, and loses identity features (`desktop-windows:activation-and-notifications`).
- **Native AOT** (`PublishAot`) needs `x:Bind` only, MSVC C++ build tools and the WCT 8.2+ controls; validate with `winapp run --aot` or a `dotnet publish -p:PublishAot=true` in CI before promising it.
- **The manifest is requested capabilities, minimal.** `runFullTrust` stays (WinUI desktop apps need it); every other capability carries a recorded reason (`desktop/_shared/security`).

## Run, package, debug

| Goal | `winapp` (0.8.0, preview) | Fallback |
|---|---|---|
| Build and run with identity | `winapp run` (add `--arch arm64`, `--debug-output` for stowed exceptions) | Visual Studio F5 on the packaged project; `dotnet build -p:Platform=x64` then deploy from VS |
| Package a signed MSIX | `winapp cert generate --manifest .\Package.appxmanifest` then `winapp pack .\OrdersApp.csproj -c Release --arch x64 --cert .\devcert.pfx` | VS *Publish → Create App Packages*; `dotnet publish` with `-p:GenerateAppxPackageOnBuild=true` |
| Find a control or API | `winapp find-ui "tabbed layout"`, `winapp find-api NavigationView` | WinUI Gallery app; learn.microsoft.com |
| Inspect a running UI | `winapp ui inspect -a OrdersApp` | Accessibility Insights for Windows; Inspect |

The dev certificate is for local testing only; production signing is `desktop/_shared/distribution`. `winapp` is optional: a project that works with the fallback column is correct.

## WPF and WinForms projects

- **WPF:** `<UseWPF>true</UseWPF>`, `net10.0-windows`, `Directory.Build.props` and central packages as above. The Fluent theme is an opt-in (`desktop-windows:wpf`).
- **WinForms:** `<UseWindowsForms>true</UseWindowsForms>`, `<ApplicationHighDpiMode>PerMonitorV2</ApplicationHighDpiMode>`, `Application.SetColorMode` in `Main` (`desktop-windows:winforms`).
- **Never add `UseWinUI` or the Windows App SDK to either** as a side effect.

## Common gotchas

- **`dotnet run` starts the app with no identity** — add `Microsoft.Windows.SDK.BuildTools.WinApp` (templates from `winapp new` already reference it) or run from Visual Studio.
- **Developer Mode off** — `winapp run` and local MSIX registration fail until it is on.
- **A TFM without the OS part** (`net10.0`) on the app project — no WinUI; only the Core library takes it.
- **Mixed `Platforms`** — a `Any CPU` configuration on a packaged WinUI project; use `x64;ARM64`.
- **`PackageReference` with a `Version`** while central management is on — NU1008; remove the attribute.
