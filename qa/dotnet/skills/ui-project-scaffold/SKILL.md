---
name: qa-ui-project-scaffold-dotnet
description: Use when starting a web-UI test-automation project from zero in C# / .NET 10 (8-9) — solution layout, exact package versions, browser/local setup, and run commands for a standalone Playwright (default) or Selenium NUnit suite. Composable with the api/mobile/performance dotnet scaffolds. Triggers "scaffold a UI test project", "set up a .NET Playwright suite from scratch", "create the solution structure for UI tests". Not for authoring pages or tests (`ui-test-author/playwright`).
---

# UI Test Project Scaffold (C# / .NET 10)

This skill stands up a **complete, runnable web-UI test solution from zero**: directory layout, exact tool/library versions, the local setup (including browser binaries), and the commands to create and run it. It is **standalone** and **composable** — one project in a flat solution sharing a `TestCore` library with the api / mobile / performance modules (see *Expanding into a multi-module solution*).

**Version rule:** new projects target **net10.0** (the library primary); net8 (LTS) / net9 (STS) are supported fallbacks — target them only to match an existing solution's `TargetFramework`, never up-level a down-level repo. Substitute your chosen TFM for `net10.0` everywhere below.

Default driver is **Playwright** (auto-waiting, trace viewer, fastest to stand up); use **Selenium** only when the project mandates it or needs a Grid/browser Playwright doesn't support. The structure follows the dotnet layout: **flat projects at the solution root**, **per-project config** so each suite is independently configurable/dockerizable, a shared **`TestCore`**, and **Central Package Management (CPM)**. Page-object and test-authoring conventions are owned by the `qa-ui-dotnet` skills — this skill owns the **project shell**.

## When to use

- A fresh repo with no .NET UI test solution, and the user wants web-UI coverage.
- The user asks which versions / structure / setup a C# UI test framework should use.

## When NOT to use

- The solution already exists → author into it with the `qa-ui-dotnet` skills.
- API / mobile / performance scaffolding → use the matching `*-project-scaffold-dotnet` skill.

## Tooling & versions

Versions are pinned **once** in `Directory.Packages.props` (CPM); csprojs reference packages **without** a `Version` attribute (inline versions trigger `NU1008`).

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| SDK | .NET SDK | **10.0 (LTS)** | `global.json`, C# 14. On a down-level repo pin 8.0/9.0 to match. |
| Test runner | `NUnit` | **4.3.2** | Use `Assert.That`; classic asserts in `NUnit.Framework.Legacy`. |
| Test adapter | `NUnit3TestAdapter` | **5.0.0** | |
| Test host | `Microsoft.NET.Test.Sdk` | **17.14.1** | |
| Browser driver (default) | `Microsoft.Playwright.NUnit` | **1.55.0** | Pulls `Microsoft.Playwright`; provides `PageTest` base + fixtures. |
| Browser driver (alt) | `Selenium.WebDriver` + `Selenium.Support` | **4.44.0** | Use only when mandated; Selenium Manager auto-resolves drivers. |
| Assertions | `FluentAssertions` | **6.12.1** | **Deliberately pinned to 6.12.x** (last pre-commercial-license line). Prefer Playwright web-first `Expect(...)` for UI state. |
| Reporting | `Allure.NUnit` | **2.12.1** | Wiring owned by `qa-reporting-dotnet`. |
| Accessibility (opt) | `Deque.AxeCore.Playwright` | **4.*** | Only if a11y is in scope. |

Optional: `PercyIO.Playwright` 1.* / `Applitools.Playwright` 3.* (visual regression), cloud-grid wiring.

## Prerequisites & local setup

```bash
dotnet --version            # expect 10.0.x (or the repo's pinned 8.0.x / 9.0.x)

# Playwright browsers — REQUIRED after first build (downloads Chromium/Firefox/WebKit).
# playwright.ps1 appears under the project's bin/ after a build (path uses your TFM):
pwsh PlaywrightTests/bin/Debug/net10.0/playwright.ps1 install
# (no pwsh? dotnet tool install Microsoft.Playwright.CLI && playwright install)
```

CI must run `playwright install` after restore, or every test errors with "browser not found". Selenium needs no browser-binary step (Selenium Manager handles drivers) but needs the real browser on the runner.

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
│   ├── Waits/                          # explicit wait helpers (esp. for Selenium)
│   ├── Builders/
│   ├── GlobalUsings.cs
│   └── TestCore.csproj
└── PlaywrightTests/                    # this discipline's project (UiTests if you prefer)
    ├── Pages/                          # page objects — intent, not selectors
    ├── ScreenDefinitions/              # optional *.screen.json selector files
    ├── Fixtures/                       # base test: browser/context, trace+screenshot on fail
    ├── TestData/                       # builders
    ├── Tests/                          # grouped by feature
    ├── allureConfig.json               # ┐ per-project config — independently
    ├── appsettings.json                # │ configurable + dockerizable
    ├── appsettings.test.json           # │
    ├── Dockerfile                      # │
    ├── GlobalUsings.cs                 # │
    ├── README.md                       # ┘
    └── PlaywrightTests.csproj          # references TestCore
```

## Create from zero

```bash
mkdir <Product> && cd <Product>
git init
dotnet new globaljson --sdk-version 10.0.100 --roll-forward latestFeature
dotnet new sln -n <Product>

dotnet new classlib -o TestCore -f net10.0
dotnet new nunit    -o PlaywrightTests -f net10.0
dotnet sln add TestCore PlaywrightTests
dotnet add PlaywrightTests reference TestCore

dotnet new tool-manifest
dotnet tool install allure

# Create Directory.Packages.props (CPM on) FIRST, then add packages versionlessly:
dotnet add PlaywrightTests package Microsoft.Playwright.NUnit
dotnet add PlaywrightTests package FluentAssertions
dotnet add PlaywrightTests package Allure.NUnit

dotnet build                                            # generates playwright.ps1 under bin/
pwsh PlaywrightTests/bin/Debug/net10.0/playwright.ps1 install   # download browsers
dotnet test                                             # exit gate: green
```

For **Selenium** instead: `dotnet add PlaywrightTests package Selenium.WebDriver Selenium.Support` (and name the project `UiTests`); no browser-binary install step. The `Directory.Packages.props` + `Directory.Build.props` files are exactly as in `qa-api-project-scaffold-dotnet` (CPM version table + settings-only props) — add the Playwright/Selenium `<PackageVersion>` lines.

## Run

```bash
dotnet test
HEADED=1 dotnet test                          # if your fixture reads HEADED for a visible browser
dotnet test --filter "FullyQualifiedName~Checkout"
allure serve allure-results
```

Debugging a failure: open the Playwright trace from the run's artifacts (`npx playwright show-trace trace.zip`) — the base fixture should attach traces/screenshots on failure.

## Conventions (the shell only)

- **No `Thread.Sleep` / `Task.Delay` / `WaitForTimeoutAsync`.** Use Playwright auto-waiting and `Expect(...).ToBeVisibleAsync()`; for Selenium use explicit `WebDriverWait` helpers in `TestCore/Waits`.
- **Page objects expose intent, not selectors**; one page object per screen; no assertions inside them.
- **Base fixture** (in `Fixtures/`) owns browser/context lifecycle and attaches trace + screenshot on failure.
- **Config / auth / secrets**: per-project `appsettings.<env>.json`, env vars, no secrets committed.

Page-object architecture, selector strategy (`data-testid`-first), and test bodies are owned by the `qa-ui-dotnet` skills (`page-object-architect`, `pom-builder`, `ui-test-author/*`). Defer to them.

## Expanding into a multi-module solution

Flat solution + shared `TestCore` + CPM make this purely additive. To add a sibling (e.g. **ui + api**):

1. Install the sibling plugin and run its scaffold **inside this repo**, skipping `global.json`, `Directory.Build.props`, `Directory.Packages.props`, `.config`, the `.sln`, and `TestCore` (already present).
2. Add only its project: `dotnet new nunit -o ApiTests`, `dotnet sln add ApiTests`, `dotnet add ApiTests reference TestCore`, then its packages (which append `<PackageVersion>` to the shared table). The sibling keeps its **own** `appsettings`/`allureConfig`/`Dockerfile` — nothing to merge.
3. Promote shared config/auth/Allure helpers up into `TestCore`; keep the page-object base in the UI project and the RestClient factory in `ApiTests`.
4. `dotnet test` runs both projects; `dotnet test PlaywrightTests` runs one. Add `.slnf` filters per discipline for focused load / CI sharding. Mobile (`AppiumTests`) and performance (`PerfTests`, NBomber console) fold in the same way.

## Setup checklist

- [ ] `global.json` pins SDK 10.0 (or the repo's 8.0/9.0); `Directory.Packages.props` (CPM) is the only version source; csprojs versionless
- [ ] `Directory.Build.props` carries settings only
- [ ] `TestCore` is a shared library; the UI project references it
- [ ] Driver chosen deliberately (Playwright default; Selenium only if mandated)
- [ ] Playwright browsers installed (`playwright.ps1 install`) — and the step is in CI
- [ ] Base fixture attaches trace + screenshot on failure
- [ ] Per-project `appsettings`/`allureConfig`/`Dockerfile`/`README` present; allure local tool installed
- [ ] No secrets in `appsettings*.json`
- [ ] `dotnet build` clean; `dotnet test` green
