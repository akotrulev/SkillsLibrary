---
name: desktop-project-setup
description: Use when starting a desktop E2E project in .NET (NUnit + Appium 3, Mac2, WinCore, or FlaUI 5 on Windows). Triggers "scaffold a desktop test project". Not for writing tests (desktop-window-objects).
disable-model-invocation: true
---

# Desktop Test Project Scaffold (C# / .NET 10)

Stands up a **runnable native-desktop test solution from zero**: layout, exact versions, the Appium 3 server and pinned drivers (or the in-process FlaUI lane), OS prerequisites, env-driven options and a first smoke run. It owns the **project shell and the environment**. The shared rules (drivers, the test-id contract, CI hosts) are `qa/_shared/desktop-testing`; load it first. The mobile twin is `qa/dotnet/skills/mobile-project-setup`, whose CPM table, `Env.cs`, `BaseMobileTest.cs` and `mobile.runsettings` (in `qa/dotnet/skills/ui-test-author/appium/assets/`) this skill reuses rather than copies.

**Version rule:** net10.0 primary; net8/9 only to match an existing solution's TFM, never up-levelled. FlaUI 5.0.0 targets `net8.0-windows`, `net6.0-windows` and `net48`, so a FlaUI suite targets `net10.0-windows` or the repo's `-windows` TFM. Electron and Tauri apps are out of scope.

## When to use

- A fresh repo with no .NET desktop test project and a native macOS or Windows app to cover.
- The user asks which versions, drivers or OS setup a C# desktop suite needs, or whether to use FlaUI.

## When NOT to use

- The project exists → `qa/dotnet/skills/desktop-window-objects`, and `qa/dotnet/skills/ui-test-author/appium` for the NUnit conventions.
- Mobile → `qa/dotnet/skills/mobile-project-setup`. Browser UI → `qa/dotnet/skills/ui-project-setup`.
- A device cloud for desktop: none exists, see `qa/_shared/desktop-testing`.
- Java / TypeScript → `qa/java/skills/desktop-project-setup` / `qa/typescript/skills/desktop-project-setup`.

## Which lane

| | Appium lane (default) | FlaUI lane |
|---|---|---|
| Platforms | macOS (Mac2) and Windows (WinCore) | Windows only |
| Server | Appium 3.8.0 (Node 24) | none: UIA3 in the test process |
| Locator | `accessibility id` | `ByAutomationId` |
| Choose when | one locator contract across macOS, Windows and the Java/TypeScript lanes | a Windows-only suite beside a WPF or WinUI codebase that wants no Node or Appium |

**Choose per suite and never mix:** one suite uses Appium or FlaUI, not both, because the window objects, waits and evidence hook differ. The rest of the skill covers the Appium lane first, then FlaUI.

## Versions

Verified 2026-11-15. Pins are those of `mobile-project-setup`; `Directory.Packages.props` (CPM) is the only version source.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| SDK | .NET SDK | **10.0** | `global.json`; C# 14 |
| Runner | `NUnit` · `NUnit3TestAdapter` · `Microsoft.NET.Test.Sdk` | **4.6.1** · **6.3.1** · **18.10.1** | Stay on NUnit 4.x |
| Appium client | `Appium.WebDriver` | **9.0.0** | `MacDriver` and `WindowsDriver` take `AppiumOptions`. Strong-named |
| Selenium | `Selenium.WebDriver` · `Selenium.Support` | **4.51.0** | `Selenium.Support` for `WebDriverWait` |
| Reporting | `Allure.NUnit` | **2.15.0** | |
| Appium server | `appium` (npm) | **3.8.0** | Latest is 3.9.1; not moved here. Node 24 |
| macOS driver | `appium-mac2-driver` | **4.6.1** | Peer `appium ^3.0.0-rc.2`. 5.x needs Appium 4 |
| Windows driver | `appium-wincore-driver` | **3.3.2** | Peer `appium ^3.0.0-rc.2`. 4.x needs Appium 4 |
| Windows fallback | `appium-novawindows-driver` | **1.5.0** | Same `AutomationId` contract |
| FlaUI | `FlaUI.Core` · `FlaUI.UIA3` | **5.0.0** | 2025-02-25; no release in 21 months, but mature. UIA3, not UIA2 (WPF-only legacy) |
| WebView2 content | `Microsoft.Playwright` | **1.63.0** | The library pin; `ConnectOverCDPAsync`. Never a 1.64-only API |

**From 4.0 GA:** Appium 4 with Mac2 5.x and WinCore 4.x. Do not scaffold on it. `Appium.WebDriver` 9 has no `Mac2Driver` class: the macOS driver class is `MacDriver` with `automationName` set to `mac2` (not verified against a live Mac2 session: the smoke is the proof).

## Prerequisites

| Host | Need |
|---|---|
| Both | .NET 10 SDK, Node 24 and npm (Appium lane) |
| macOS | macOS 11.3+, **Xcode 13+** with command-line tools, the app built and installed; **Xcode Helper** granted Accessibility; `sudo automationmodetool enable-automationmode-without-authentication`. `WebDriverAgentRunner-Runner.app` needs Accessibility only for moving or resizing windows. All human steps: report them, never skip them |
| Windows | The app built or installed (exe path or UWP AUMID), an **interactive session with autologon**: the runner is a process, not a service (see `qa/_shared/desktop-testing` § CI and hosts). Applies to FlaUI too |

## Appium 3 server and drivers

```bash
npm install -g appium@3.8.0
appium driver install mac2@4.6.1
appium driver install --source=npm appium-wincore-driver@3.3.2
appium driver list --installed
appium driver doctor mac2
appium
```

Run the second command on a Mac, the third on Windows. **Never an unpinned `appium driver install mac2`** (it may resolve to a major that needs Appium 4) and never `appium driver update` (it can cross a major). `appium driver list --installed` must show `mac2@4.6.1` or `wincore@3.3.2`. The server must be running before `dotnet test`: there is no auto-start. The legacy Appium Windows driver and WinAppDriver are never installed (D9). Fallback for a legacy app: `appium-novawindows-driver@1.5.0` and `automationName` `NovaWindows`; locators do not change.

## Project layout

```
<Product>/                              # solution root (flat projects)
├── <Product>.sln · global.json · Directory.Build.props · Directory.Packages.props
├── TestCore/                           # shared library, as in mobile-project-setup
└── DesktopTests/
    ├── Windows/                        # BaseWindow, window objects
    ├── Components/                     # region components (rows); Controls/ holds native controls
    ├── Support/
    │   ├── Env.cs                      # the one required-variable reader
    │   ├── AppiumDriverFactory.cs      # Appium lane: MacDriver / WindowsDriver from env
    │   ├── AppLauncher.cs              # FlaUI lane: Application.Launch from env
    │   └── BaseDesktopTest.cs          # session per fixture + failure evidence
    ├── Tests/
    ├── allureConfig.json
    ├── desktop.runsettings             # NumberOfTestWorkers = 1
    ├── .env.example
    └── DesktopTests.csproj
```

The window objects live in `Windows/`: every skill and the agent's backlog check glob `DesktopTests/Windows/`. Create it as `dotnet new nunit -o DesktopTests -f net10.0` (`net10.0-windows` for FlaUI), add it to the sln, reference `TestCore`, copy `Directory.Packages.props` from `ui-test-author/appium/assets/` and add the lane's packages versionless. `Env.cs` and `mobile.runsettings` (renamed `desktop.runsettings`) copy over unchanged. For the FlaUI lane delete `Appium.WebDriver`, `Selenium.*` and add `FlaUI.Core`, `FlaUI.UIA3`.

## Options and configuration

**One mechanism:** environment variables through `Env.Required`. `PLATFORM` (`macos` or `windows`) picks the driver; a test never branches on platform, the window object's locator map does.

| Variable | Used for |
|---|---|
| `PLATFORM` | `macos` or `windows`; anything else fails naming the value (the FlaUI lane is `windows` only) |
| `APP_ID` | macOS: the bundle id. Windows: the exe path or UWP AUMID |
| `APP_ARGUMENTS` | Optional launch arguments |
| `APPIUM_URL` | Appium lane; default `http://127.0.0.1:4723` |
| `E2E_USER`, `E2E_PASSWORD` | The test account the example flow signs in with |

```csharp
public static class AppiumDriverFactory
{
    private static readonly TimeSpan CommandTimeout = TimeSpan.FromSeconds(180);

    public static AppiumDriver Create()
    {
        var server = new Uri(Env.AppiumUrl);
        var platform = Env.Required("PLATFORM");
        return platform switch
        {
            "macos" => new MacDriver(server, MacOptions(), CommandTimeout),
            "windows" => new WindowsDriver(server, WindowsOptions(), CommandTimeout),
            _ => throw new ArgumentException($"PLATFORM must be macos or windows, got {platform}"),
        };
    }

    private static AppiumOptions MacOptions()
    {
        var options = new AppiumOptions { PlatformName = "mac", AutomationName = "mac2" };
        options.AddAdditionalAppiumOption("bundleId", Env.Required("APP_ID"));
        return options;
    }

    private static AppiumOptions WindowsOptions()
    {
        var options = new AppiumOptions { PlatformName = "Windows", AutomationName = "Wincore" };
        options.App = Env.Required("APP_ID");
        options.AddAdditionalAppiumOption("ms:waitForAppLaunch", 30);
        return options;
    }
}
```

- `bundleId` is mandatory on Mac2 (the default app is Finder). `AppiumOptions` adds the `appium:` prefix to additional options. `WindowsOptions`-style typed helpers hard-set `automationName` to `Windows` in some clients: setting it on `AppiumOptions` as above is what reaches WinCore.
- **`NumberOfTestWorkers` is 1.** Mac2 runs one session at a time and Windows focus is exclusive. Parallelism is more machines, never more workers.
- A session starts a fresh app by default. Keep state only deliberately: `noReset` (Mac2) or `shouldCloseApp: false` (WinCore).
- Evidence on failure (screenshot, page source via `Driver.PageSource`) comes from `BaseDesktopTest.CaptureEvidence`, modelled on `BaseMobileTest.cs` with the device log and recording parts dropped.

## The FlaUI lane

No server, no driver install. The app launches inside the test process.

```csharp
public static class AppLauncher
{
    public static Application Start(UIA3Automation automation)
    {
        var app = Application.Launch(Env.Required("APP_ID"), Environment.GetEnvironmentVariable("APP_ARGUMENTS"));
        app.WaitWhileMainHandleIsMissing();
        return app;
    }
}
```

`BaseDesktopTest` owns one `UIA3Automation` and one `Application` per fixture (`[OneTimeSetUp]`) and disposes both in `[OneTimeTearDown]`: disposing the `Application` closes the app. Evidence is `Capture.Screen()` / `window.Capture()` saved from `[TearDown]`, and the element tree is not a page source, so a failure dumps the failing container's descendants' `AutomationId`, `Name` and `ControlType`. `maxInstances` does not exist: the runsettings worker count of 1 is the rule. FlaUI needs the same interactive session as Appium on Windows. API names above follow the FlaUI wiki and were not compiled here.

## Embedded WebView2 content

A WinUI, WPF or WinForms app hosting WebView2 exposes the page DOM outside the UIA tree. Launch the app with the environment variables the shared skill names (`WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=<port>`, a unique `WEBVIEW2_USER_DATA_FOLDER` per worker), then connect: `var browser = await playwright.Chromium.ConnectOverCDPAsync($"http://127.0.0.1:{port}"); var page = browser.Contexts[0].Pages[0];`. Locate by the page's `data-testid`. Reference `Microsoft.Playwright` 1.63.0 only when a suite covers WebView2; the Playwright browser download is not needed for CDP.

## First smoke

```csharp
[TestFixture]
public sealed class SmokeTests : BaseDesktopTest
{
    [Test]
    public void Should_ShowLibraryWindow_When_AppLaunches() => new LibraryWindow(Driver).VerifyWindowLoaded();
}
```

(`LibraryWindow(Application, Automation)` in the FlaUI lane.) Run with the app installed:

```bash
PLATFORM=macos APP_ID=com.example.Library dotnet test DesktopTests --settings DesktopTests/desktop.runsettings
PLATFORM=windows APP_ID='C:\Apps\Library\Library.exe' dotnet test DesktopTests --settings DesktopTests/desktop.runsettings
```

Exit gate: `dotnet build` is clean, the driver is listed at its pinned version, `appium driver doctor mac2` is clean (macOS), and the smoke is green on one host.

## CI

Owned hardware: a self-hosted Windows agent in an interactive autologon session (Microsoft-hosted Azure agents do not support visible UI tests) and a Mac with Xcode. No device cloud runs native desktop apps. The pipeline is `qa/cicd/dotnet/skills/ci-pipelines`; this skill does not write CI.

## Setup checklist

- [ ] One lane chosen (Appium or FlaUI), recorded in the README
- [ ] CPM pins as above; csprojs versionless; `global.json` pins the SDK
- [ ] Appium lane: `appium driver list --installed` shows `mac2@4.6.1` or `wincore@3.3.2`, no unpinned install
- [ ] `PLATFORM` and `APP_ID` come from the environment; `NumberOfTestWorkers` is 1; `.env.example` committed
- [ ] Interactive autologon session (Windows) or Xcode and both Accessibility grants (macOS)
- [ ] `dotnet build` clean; the smoke green on the host

## Handoffs

- Window discovery → `qa/dotnet/skills/desktop-screen-explorer`; window objects → `qa/dotnet/skills/desktop-window-objects`
- NUnit conventions → `qa/dotnet/skills/ui-test-author/appium`
- Shared rules and CI facts → `qa/_shared/desktop-testing`
- Java / TypeScript siblings → `qa/java/skills/desktop-project-setup` / `qa/typescript/skills/desktop-project-setup`
