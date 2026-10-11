---
name: mobile-project-setup
description: Use when starting a mobile (iOS/Android) test-automation project from zero in C# / .NET 10 (8-9) — solution layout, exact package versions, Appium 3 server + drivers + emulator setup, run commands for a standalone Appium NUnit suite. Composable with the api/ui/performance dotnet scaffolds. Triggers "scaffold a mobile test project", "set up a .NET Appium suite from scratch". Not for authoring screens or tests (`ui-test-author/appium`).
---

# Mobile Test Project Scaffold (C# / .NET 10)

This skill stands up a **complete, runnable mobile test solution from zero**: directory layout, exact tool/library versions, the local Appium 3 + driver + emulator setup, and the commands to create and run it. It is **standalone** and **composable** — one project in a flat solution sharing a `TestCore` library with the api / ui / performance modules (see *Expanding into a multi-module solution*).

**Version rule:** new projects target **net10.0** (the library primary); net8 (LTS) / net9 (STS) are supported fallbacks — target them only to match an existing solution's `TargetFramework`, never up-level a down-level repo. Substitute your chosen TFM for `net10.0` everywhere below.

Mobile has the heaviest local setup of any module (Appium server, platform drivers, an emulator/simulator or real device). The structure follows the dotnet layout: **flat projects at the solution root**, a shared **`TestCore`**, and **Central Package Management (CPM)**. Screen-object and test-authoring conventions are owned by the `qa-mobile-dotnet` skills — this skill owns the **project shell** and the **environment**. The compilable project that drops into `AppiumTests/` is `qa/dotnet/skills/ui-test-author/appium/assets/`; this skill does not copy it.

## When to use

- A fresh repo with no .NET mobile test solution, and the user wants iOS/Android coverage.
- The user asks which versions / structure / Appium setup a C# mobile framework should use.

## When NOT to use

- The solution already exists → author into it with the `qa-mobile-dotnet` skills.
- Web-UI / API / performance scaffolding → use the matching `*-project-setup-dotnet` skill.

## Tooling & versions

Versions are pinned **once** in `Directory.Packages.props` (CPM); csprojs reference packages **without** a `Version` attribute. The table is the **Versions** table of `ui-test-author/appium/SKILL.md`, and `assets/Directory.Packages.props` there holds the same pins.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| SDK | .NET SDK | **10.0 (LTS)** | `global.json`, C# 14. On a down-level repo pin 8.0/9.0 to match. |
| Test runner | `NUnit` | **4.6.1** | `Assert.That`. Stay on 4.x: NUnit 5 changes `Assert.ThrowsAsync` to return a `Task` (D18). |
| Test adapter | `NUnit3TestAdapter` | **6.3.1** | |
| Test host | `Microsoft.NET.Test.Sdk` | **18.10.1** | |
| Appium client | `Appium.WebDriver` | **9.0.0** | W3C `AppiumOptions`; strong-named, so a project moving from 8.x rebuilds everything. 8.x is the supported lane. The major does not track Selenium's. |
| Selenium | `Selenium.WebDriver` / `Selenium.Support` | **4.51.0** | The client needs ≥ 4.46. `Selenium.Support` is not transitive since client 6.0, so declare it for `WebDriverWait`. |
| Reporting | `Allure.NUnit` | **2.15.0** | Wiring owned by `qa-reporting-dotnet`. |
| Appium server | `appium` (npm) | **3.8.0** | Node `^20.19 \|\| ^22.12 \|\| ≥ 24`; use **Node 24** (22 supported; 20 is EOL). Drivers are installed separately. |
| Android driver | `appium-uiautomator2-driver` | **8.x** | `appium driver install uiautomator2`. 4.x is the Appium 2 lane. |
| iOS driver | `appium-xcuitest-driver` | **12.x** | `appium driver install xcuitest` (macOS + Xcode only). 9.x is the Appium 2 lane. |

Cloud device farms (BrowserStack / Sauce) replace the local server/emulator — see `device-cloud` + `browser-cloud-setup`; confirm the farm runs Appium 3 first.

## Prerequisites & local setup

```bash
dotnet --version
node --version                         # 24 (22 supported)
npm install -g appium@3
appium setup                           # mobile preset: uiautomator2, xcuitest (macOS), espresso, images and inspector plugins
appium driver list --installed
appium driver doctor uiautomator2      # verify the Android toolchain
appium driver doctor xcuitest          # macOS only
appium                                 # start the server (default :4723)
adb devices                            # an Android emulator/device must be listed
xcrun simctl list                      # iOS (macOS only): Xcode + simulators
```

A booted emulator/simulator (or a connected device) and a running `appium` server are required before `dotnet test` — there is no auto-start. A local `appium-mcp` session needs no server, but a test run does. Keep the `.app`/`.apk`/`.ipa` build artifact path in an environment variable, not in code. Recording a screen needs `ffmpeg` on the Appium host (always on iOS; on Android only above 180 s) — see `evidence-capture/references/appium.md`.

## Project layout (standalone)

```
<Product>/                              # git repo root = solution root (flat projects)
├── <Product>.sln
├── global.json                         ┐
├── Directory.Build.props               │ solution-scoped, shared by every project
├── Directory.Packages.props            │ (CPM version table)
├── nuget.config · .editorconfig        ┘
├── .gitignore
├── TestCore/                           # ← shared library (composition seam)
│   ├── Configuration/
│   ├── Reporting/
│   ├── Builders/
│   ├── GlobalUsings.cs
│   └── TestCore.csproj
└── AppiumTests/                        # this discipline's project
    ├── Pages/                          # screen objects, components, sub-flows
    ├── Support/
    │   ├── AppiumDriverFactory.cs      # builds AndroidDriver/IOSDriver from env
    │   ├── BaseMobileTest.cs           # driver per fixture + failure evidence
    │   ├── Env.cs                      # the one required-variable reader
    │   ├── GestureExtensions.cs
    │   ├── Native/                     # permissions, deep links, push helpers
    │   └── Farm/                       # only when a device cloud is used
    ├── Tests/
    ├── allureConfig.json               # per-project config
    ├── mobile.runsettings              # NumberOfTestWorkers
    ├── .env.example                    # PLATFORM, DEVICE_NAME, APP_PATH, PLATFORM_VERSION, APPIUM_URL
    ├── README.md
    └── AppiumTests.csproj              # references TestCore
```

The screen objects live in `Pages/`, not `Screens/`: every skill and the agent's backlog check glob `AppiumTests/Pages/`. Waits sit in `BaseAppiumPage` (`Wait`), not in a separate folder.

## Create from zero

```bash
mkdir <Product> && cd <Product>
git init
dotnet new globaljson --sdk-version 10.0.100 --roll-forward latestFeature
dotnet new sln -n <Product>

dotnet new classlib -o TestCore -f net10.0
dotnet new nunit    -o AppiumTests -f net10.0
dotnet sln add TestCore AppiumTests
dotnet add AppiumTests reference TestCore

cp <skills>/qa/dotnet/skills/ui-test-author/appium/assets/Directory.Packages.props .
cp <skills>/qa/dotnet/skills/ui-test-author/appium/assets/*.cs <skills>/qa/dotnet/skills/ui-test-author/appium/assets/mobile.runsettings AppiumTests/

dotnet build                            # exit gate: 0 errors, 0 warnings
# start appium + boot an emulator, then:
PLATFORM=android dotnet test AppiumTests
```

Create `Directory.Packages.props` (CPM on) **before** adding packages, then add them versionless (`dotnet add AppiumTests package Appium.WebDriver`, `Selenium.WebDriver`, `Selenium.Support`, `Allure.NUnit`). Sort the copied `.cs` files into `Support/`, `Pages/` and `Tests/` to match their namespaces. `Directory.Build.props` (settings only) is exactly as in `qa-dotnet:api-project-setup`. The Allure CLI that turns `allure-results/` into a report is installed and run as `qa/reporting/dotnet/skills/test-reports` says; there is no `allure` package on NuGet to install as a dotnet tool.

## Run

```bash
# Terminal 1: appium     (or point APPIUM_URL at a cloud grid)
# Terminal 2:
PLATFORM=android DEVICE_NAME=Pixel_7_API_34 APP_PATH=/abs/app.apk dotnet test AppiumTests
PLATFORM=ios DEVICE_NAME="iPhone 15" PLATFORM_VERSION=17.4 APP_PATH=/abs/App.app dotnet test AppiumTests   # macOS only
```

**One platform-selection mechanism:** the `PLATFORM` variable (`android` or `ios`), read by `AppiumDriverFactory`. There are no per-platform `appsettings.<platform>.json` files and no `--filter "Platform=…"`; a test never branches on platform, the finder does. Devices, the app path and the server URL come from the other variables, never from code.

## Conventions (the shell only)

- **No `Thread.Sleep` / `Task.Delay`.** Use `BaseAppiumPage.Wait` (a `WebDriverWait`); add new waits there, never inline.
- **Screen objects expose intent, not selectors**; the per-platform test id first; one screen object per screen. The only assertion in a screen object is `VerifyPageLoaded()`; the tests own every other one.
- **Driver lifecycle** lives in `AppiumDriverFactory` + `BaseMobileTest`; tests never new-up a driver.
- **Config / secrets**: app path, Appium URL and device from environment variables; no secrets committed.

Screen-object emission, locator strategy, device-farm wiring, and native-feature surfaces are owned by the `qa-mobile-dotnet` skills (`mobile-screen-explorer`, `mobile-screen-objects`, `ui-test-author/appium`, `device-cloud`, `mobile-native-features`). Defer to them.

## Expanding into a multi-module solution

Flat solution + shared `TestCore` + CPM make this purely additive. To add a sibling (e.g. **mobile + api** for backend setup/teardown of mobile test data):

1. Install the sibling plugin and run its scaffold **inside this repo**, skipping `global.json`, `Directory.Build.props`, `Directory.Packages.props`, the `.sln`, and `TestCore` (already present).
2. Add only its project (`dotnet new nunit -o ApiTests`, `dotnet sln add ApiTests`, `dotnet add ApiTests reference TestCore`) + its packages (which append `<PackageVersion>` to the shared table). The sibling keeps its **own** config files — nothing to merge.
3. Promote shared config/auth/Allure helpers up into `TestCore`; keep `AppiumDriverFactory` in `AppiumTests` and the RestClient factory in `ApiTests`.
4. `dotnet test` runs all projects; run one by its path (`dotnet test AppiumTests`). Add `.slnf` filters per discipline. Web-UI (`UiTests`) and performance (`PerfTests`, NBomber) fold in the same way.

## Setup checklist

- [ ] `global.json` pins SDK 10.0 (or the repo's 8.0/9.0); `Directory.Packages.props` (CPM) is the only version source; csprojs versionless
- [ ] `Directory.Build.props` carries settings only
- [ ] `TestCore` is a shared library; `AppiumTests` references it
- [ ] Node 24 (22 supported); Appium 3 server installed; uiautomator2 (and/or xcuitest) driver installed; `driver doctor` clean
- [ ] An emulator/simulator boots and `adb devices` (or `simctl`) lists it
- [ ] `AppiumDriverFactory` reads `PLATFORM`, `DEVICE_NAME`, `APP_PATH` from the environment — no hard-coded options
- [ ] No `Thread.Sleep`; waits in `BaseAppiumPage.Wait`
- [ ] Per-project `allureConfig.json`, `mobile.runsettings`, `.env.example`, `README`; secrets out of config
- [ ] `dotnet build` clean; `dotnet test` green against a booted device. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
