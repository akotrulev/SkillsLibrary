---
name: qa-mobile-project-scaffold-dotnet
description: Use when starting a mobile (iOS/Android) test-automation project from zero in C# / .NET 8 — solution layout, exact package versions, Appium server + driver + emulator setup, and run commands for a standalone Appium NUnit suite. Triggers: "scaffold a mobile test project", "set up a .NET Appium suite from scratch", "what versions for a C# mobile test framework", "create the solution structure for mobile tests". Composable: explains how to fold in api/ui/performance dotnet modules later.
---

# Mobile Test Project Scaffold (C# / .NET 8)

This skill stands up a **complete, runnable mobile test solution from zero**: directory layout, exact tool/library versions, the local Appium + driver + emulator setup, and the commands to create and run it. It is **standalone** and **composable** — one project in a flat solution sharing a `TestCore` library with the api / ui / performance modules (see *Expanding into a multi-module solution*).

Mobile has the heaviest local setup of any module (Appium server, platform drivers, an emulator/simulator or real device). The structure follows the dotnet layout: **flat projects at the solution root**, **per-project config** so each suite is independently configurable/dockerizable, a shared **`TestCore`**, and **Central Package Management (CPM)**. Screen-object and test-authoring conventions are owned by the `qa-mobile-dotnet` skills — this skill owns the **project shell** and the **environment**.

## When to use

- A fresh repo with no .NET mobile test solution, and the user wants iOS/Android coverage.
- The user asks which versions / structure / Appium setup a C# mobile framework should use.

## When NOT to use

- The solution already exists → author into it with the `qa-mobile-dotnet` skills.
- Web-UI / API / performance scaffolding → use the matching `*-project-scaffold-dotnet` skill.

## Tooling & versions

Versions are pinned **once** in `Directory.Packages.props` (CPM); csprojs reference packages **without** a `Version` attribute.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| SDK | .NET SDK | **8.0 (LTS)** | `global.json`, C# 12. |
| Test runner | `NUnit` | **4.2.2** | `Assert.That`. |
| Test adapter | `NUnit3TestAdapter` | **4.6.0** | |
| Test host | `Microsoft.NET.Test.Sdk` | **17.11.1** | |
| Appium client | `Appium.WebDriver` | **8.0.0** | W3C `AppiumOptions`; depends on Selenium ≥4.36 (pulled transitively). |
| Selenium base | `Selenium.WebDriver` / `Selenium.Support` | **4.44.0** | Transitive via Appium; pin explicitly to control wait helpers. |
| Assertions | `FluentAssertions` | **6.12.1** | Pinned to 6.12.x (pre-commercial-license). |
| Reporting | `Allure.NUnit` | **2.12.1** | Wiring owned by `qa-reporting-dotnet`. |
| Appium server | `appium` (npm) | **2.x** | `npm i -g appium`; v2 needs drivers installed separately. |
| Android driver | `appium-uiautomator2-driver` | **latest 2.x** | `appium driver install uiautomator2`. |
| iOS driver | `appium-xcuitest-driver` | **latest** | `appium driver install xcuitest` (macOS + Xcode only). |

Cloud device farms (BrowserStack / Sauce / Device Farm) replace the local server/emulator — see `mobile-device-farm` + `cloud-grid-config`.

## Prerequisites & local setup

```bash
dotnet --version
node --version                  # 18+ recommended
npm install -g appium
appium driver install uiautomator2     # Android
appium driver install xcuitest         # iOS (macOS + Xcode only)
appium driver doctor uiautomator2      # verify Android toolchain
appium                                  # start the server (default :4723)
adb devices                             # Android emulator/device must be listed
# iOS (macOS only): Xcode + simulators; xcrun simctl list
```

A booted emulator/simulator (or a connected device) and a running `appium` server are required before `dotnet test` — there is no auto-start. Keep the `.app`/`.apk`/`.ipa` build artifact path in config, not in code.

## Project layout (standalone)

```
<Product>/                              # git repo root = solution root (flat projects)
├── <Product>.sln
├── global.json                         ┐
├── Directory.Build.props               │ solution-scoped, shared by every project
├── Directory.Packages.props            │ (CPM version table)
├── nuget.config · .editorconfig        │
├── .config/dotnet-tools.json           ┘ allure local tool
├── .gitignore
├── TestCore/                           # ← shared library (composition seam)
│   ├── Configuration/
│   ├── Reporting/
│   ├── Builders/
│   ├── GlobalUsings.cs
│   └── TestCore.csproj
└── AppiumTests/                        # this discipline's project (MobileTests if you prefer)
    ├── Screens/                        # screen objects — accessibility-id-first
    ├── ScreenDefinitions/              # optional *.screen.json (ios/android locators)
    ├── Support/
    │   ├── AppiumDriverFactory.cs      # builds AndroidDriver/IOSDriver from caps
    │   ├── Waits/                      # explicit wait helpers (no Thread.Sleep)
    │   └── Native/                     # permissions, deep links, push helpers
    ├── TestData/
    ├── Tests/
    ├── allureConfig.json               # ┐ per-project config — independently
    ├── appsettings.json                # │ configurable + dockerizable
    ├── appsettings.android.json        # │
    ├── appsettings.ios.json            # │
    ├── Dockerfile                      # │
    ├── GlobalUsings.cs                 # │
    ├── README.md                       # ┘
    └── AppiumTests.csproj              # references TestCore
```

## Create from zero

```bash
mkdir <Product> && cd <Product>
git init
dotnet new globaljson --sdk-version 8.0.100 --roll-forward latestFeature
dotnet new sln -n <Product>

dotnet new classlib -o TestCore -f net8.0
dotnet new nunit    -o AppiumTests -f net8.0
dotnet sln add TestCore AppiumTests
dotnet add AppiumTests reference TestCore

dotnet new tool-manifest
dotnet tool install allure

# Create Directory.Packages.props (CPM on) FIRST, then add packages versionlessly:
dotnet add AppiumTests package Appium.WebDriver
dotnet add AppiumTests package Selenium.Support
dotnet add AppiumTests package FluentAssertions
dotnet add AppiumTests package Allure.NUnit

dotnet build                            # exit gate: 0 errors, 0 warnings
# start appium + boot an emulator, then:
dotnet test --filter "Platform=Android"
```

`Directory.Packages.props` (CPM version table) + `Directory.Build.props` (settings only) are exactly as in `qa-api-project-scaffold-dotnet` — add the Appium/Selenium `<PackageVersion>` lines.

## Run

```bash
# Terminal 1: appium     (or point appsettings at a cloud grid)
# Terminal 2:
dotnet test --filter "Platform=Android"
dotnet test --filter "Platform=iOS"        # macOS only
allure serve allure-results
```

The platform is selected by config/category, not by code branching inside tests — the `AppiumDriverFactory` reads caps from `appsettings.<platform>.json`.

## Conventions (the shell only)

- **No `Thread.Sleep` / `Task.Delay`.** Use the explicit wait helpers in `Support/Waits` (`WaitUntilVisible`, `WaitUntilStable`); add new waits there, never inline.
- **Screen objects expose intent, not selectors**; accessibility-id-first locators; one screen object per screen; no assertions inside them.
- **Driver lifecycle** lives in `AppiumDriverFactory` + the base test; tests never new-up a driver.
- **Config / secrets**: app path, Appium URL, and caps from per-project `appsettings.<platform>.json` + env vars; no secrets committed.

Screen-object emission, locator strategy, device-farm wiring, and native-feature surfaces are owned by the `qa-mobile-dotnet` skills (`appium-explore`, `appium-page-object`, `ui-test-author/appium`, `mobile-device-farm`, `mobile-native-features`). Defer to them.

## Expanding into a multi-module solution

Flat solution + shared `TestCore` + CPM make this purely additive. To add a sibling (e.g. **mobile + api** for backend setup/teardown of mobile test data):

1. Install the sibling plugin and run its scaffold **inside this repo**, skipping `global.json`, `Directory.Build.props`, `Directory.Packages.props`, `.config`, the `.sln`, and `TestCore` (already present).
2. Add only its project (`dotnet new nunit -o ApiTests`, `dotnet sln add ApiTests`, `dotnet add ApiTests reference TestCore`) + its packages (which append `<PackageVersion>` to the shared table). The sibling keeps its **own** config files — nothing to merge.
3. Promote shared config/auth/Allure helpers up into `TestCore`; keep `AppiumDriverFactory` in `AppiumTests` and the RestClient factory in `ApiTests`.
4. `dotnet test` runs all projects; filter by project or category to run one. Add `.slnf` filters per discipline. Web-UI (`PlaywrightTests`) and performance (`PerfTests`, NBomber) fold in the same way.

## Setup checklist

- [ ] `global.json` pins SDK 8.0; `Directory.Packages.props` (CPM) is the only version source; csprojs versionless
- [ ] `Directory.Build.props` carries settings only
- [ ] `TestCore` is a shared library; `AppiumTests` references it
- [ ] Appium 2 server installed; uiautomator2 (and/or xcuitest) driver installed; `driver doctor` clean
- [ ] An emulator/simulator boots and `adb devices` (or `simctl`) lists it
- [ ] `AppiumDriverFactory` reads caps from per-project `appsettings.<platform>.json` — no hard-coded caps
- [ ] No `Thread.Sleep`; waits centralized in `Support/Waits`
- [ ] Per-project `appsettings`/`allureConfig`/`Dockerfile`/`README`; allure local tool installed; secrets out of config
- [ ] `dotnet build` clean; `dotnet test` green against a booted device
