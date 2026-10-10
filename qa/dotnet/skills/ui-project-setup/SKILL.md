---
name: qa-ui-project-setup-dotnet
description: Use when starting a web-UI test-automation project from zero in C# / .NET 10 (8-9) — solution layout, exact package versions, browser/local setup, and run commands for a standalone Playwright (default) or Selenium NUnit suite. Composable with the api/mobile/performance dotnet scaffolds. Triggers "scaffold a UI test project", "set up a .NET Playwright suite from scratch", "create the solution structure for UI tests". Not for authoring pages or tests (`ui-test-author/playwright`).
---

# UI Test Project Scaffold (C# / .NET 10)

This skill stands up a **complete, runnable web-UI test solution from zero**: directory layout, exact tool/library versions, the local setup (including browser binaries), a container image, and the commands to create and run it. It is **standalone** and **composable** — one project in a flat solution sharing a `TestCore` library with the api / mobile / performance modules (see *Expanding into a multi-module solution*).

**Version rule:** new projects target **net10.0** (the library primary); net8 (LTS) / net9 (STS) are supported fallbacks — target them only to match an existing solution's `TargetFramework`, never up-level a down-level repo. Substitute your chosen TFM for `net10.0` everywhere below.

Default driver is **Playwright** (auto-waiting, trace viewer, fastest to stand up); use **Selenium** only when the project mandates it or needs a Grid/browser Playwright doesn't support. The structure follows the dotnet layout: **flat projects at the solution root**, **per-project config** so each suite is independently configurable/dockerizable, a shared **`TestCore`**, and **Central Package Management (CPM)**. This skill owns the **project shell**. The Playwright project files themselves — `Directory.Packages.props`, `UiTests.csproj`, `ui.runsettings`, `BaseTest.cs`, `AuthSetup.cs` and a sample page and test — are the assets of [`ui-test-author/playwright`](../ui-test-author/playwright/SKILL.md); copy them, never re-type them here.

## When to use

- A fresh repo with no .NET UI test solution, and the user wants web-UI coverage.
- The user asks which versions / structure / setup a C# UI test framework should use.

## When NOT to use

- The solution already exists → author into it with the `qa-ui-dotnet` skills.
- API / mobile / performance scaffolding → use the matching `*-project-setup-dotnet` skill.

## Tooling & versions

Versions are pinned **once** in `Directory.Packages.props` (CPM); csprojs reference packages **without** a `Version` attribute (an inline version under CPM fails restore with `NU1008`). The Playwright rows below are the ones in `ui-test-author/playwright/assets/Directory.Packages.props`.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| SDK | .NET SDK | **10.0 (LTS)** | `global.json`, C# 14. On a down-level repo pin 8.0/9.0 to match. |
| Test runner | `NUnit` | **4.6.1** | Stay on 4.x (NUnit 5 changes `Assert.ThrowsAsync`). Use `Assert.That`; classic asserts are in `NUnit.Framework.Legacy`. |
| Test adapter | `NUnit3TestAdapter` | **6.3.1** | Runs NUnit 4; needs net8+. |
| Test host | `Microsoft.NET.Test.Sdk` | **18.10.1** | |
| Browser driver (default) | `Microsoft.Playwright.NUnit` | **1.63.0** | Pulls in `Microsoft.Playwright` and its test adapter, and provides `PageTest`. Reference it alone — never `Microsoft.Playwright` beside it. |
| Browser driver (alt) | `Selenium.WebDriver` + `Selenium.Support` | **4.51.0** | Only when mandated; Selenium Manager resolves the drivers. Add their `PackageVersion` lines when you choose it. |
| Assertions (opt) | `FluentAssertions` | **6.12.1** | Only if the solution already uses it — **deliberately pinned to 6.12.x** (last pre-commercial-license line). UI state is asserted with Playwright's `Expect(...)`, values with `Assert.That`. |
| Reporting | `Allure.NUnit` | **2.15.0** | `[AllureNUnit]` sits on `BaseTest`; report wiring is owned by `qa-reporting-dotnet`. |
| Accessibility (opt) | `Deque.AxeCore.Playwright` | **4.13.0** | Only if a11y is in scope. |
| Visual (opt) | `PercyIO.Playwright` / `Eyes.Playwright` | **1.0.4** / **1.37.49** | Hosted visual regression. The Applitools package is `Eyes.Playwright`; there is no `Applitools.Playwright` on NuGet. |
| Container | `mcr.microsoft.com/playwright/dotnet` | **v1.63.0-noble** | .NET SDK 10 with the browsers preinstalled. The tag always equals the package version; no `-jammy` image since 1.60. |

## Prerequisites & local setup

```bash
dotnet --version
pwsh --version
```

- `dotnet --version` should print 10.0.x (or the repo's pinned 8.0.x / 9.0.x).
- Playwright's CLI is `playwright.ps1`, generated under the project's `bin/` by the first build; it needs PowerShell 7. When `pwsh --version` fails, run `dotnet tool install --global PowerShell`. The old `Microsoft.Playwright.CLI` dotnet tool is legacy (stuck at 1.2.3) and no longer documented.
- **Browsers are required after the first build** — without them every test errors with "Executable doesn't exist". On CI use `install --with-deps chromium` (it installs OS packages, so it needs root or sudo), or run inside the container image, where the browsers are already present.
- Selenium needs no browser-binary step (Selenium Manager handles drivers) but needs the real browser on the runner.

## Project layout (standalone)

```
<Product>/                              # git repo root = solution root (flat projects)
├── <Product>.sln
├── global.json                         ┐
├── Directory.Build.props               │ solution-scoped, shared by every project
├── Directory.Packages.props            │ (CPM version table — from the writer's assets)
├── nuget.config · .editorconfig        │
├── .gitignore · .dockerignore          ┘
├── TestCore/                           # ← shared library (composition seam)
│   ├── Configuration/
│   ├── Builders/
│   ├── GlobalUsings.cs
│   └── TestCore.csproj
└── UiTests/                            # this discipline's project
    ├── UiTests.csproj                  # versionless, references TestCore, picks up ui.runsettings
    ├── ui.runsettings                  # browser, headless, expect timeout, test-id attribute
    ├── AuthSetup.cs                    # root namespace — signed-in state, once per run
    ├── Support/BaseTest.cs             # the one lifecycle: BASE_URL, evidence on failure
    ├── Pages/                          # page objects — intent, not selectors
    ├── Tests/                          # grouped by feature
    ├── Dockerfile                      # per-project, independently runnable
    └── README.md
```

Namespaces follow the folders under one root (`<Product>.UiTests`). `AuthSetup.cs` must stay in that root namespace: NUnit runs a `[SetUpFixture]` only for the namespace it is declared in.

## Create from zero

```bash
mkdir <Product> && cd <Product>
git init
dotnet new globaljson --sdk-version 10.0.100 --roll-forward latestFeature
dotnet new sln -n <Product>
dotnet new classlib -o TestCore -f net10.0
mkdir -p UiTests/Support UiTests/Pages UiTests/Tests
```

Then copy the writer's assets from `qa/dotnet/skills/ui-test-author/playwright/assets/`:

| Asset | Goes to |
|---|---|
| `Directory.Packages.props` | the solution root (it turns CPM on for every project) |
| `UiTests.csproj`, `ui.runsettings`, `AuthSetup.cs` | `UiTests/` |
| `BaseTest.cs` | `UiTests/Support/` |
| `LoginPage.cs`, `HomePage.cs` | `UiTests/Pages/` |
| `LoginTests.cs` | `UiTests/Tests/` |

Rename the root namespace `Example.UiTests` to `<Product>.UiTests` in every `.cs` file, then:

```bash
dotnet sln add TestCore UiTests
dotnet add UiTests reference TestCore
dotnet build
pwsh UiTests/bin/Debug/net10.0/playwright.ps1 install chromium
BASE_URL=https://staging.example.test E2E_USER=qa@example.test E2E_PASSWORD="$E2E_PASSWORD" dotnet test
```

`dotnet test` against a reachable app is the exit gate: green. The sample login tests and `AuthSetup` need a real account; a project with no signed-in tests deletes `AuthSetup.cs`. Do not start from `dotnet new nunit` — its csproj carries inline versions that break restore under CPM.

For **Selenium** instead: add `PackageVersion` lines for `Selenium.WebDriver` and `Selenium.Support`, reference them versionlessly, and follow `qa/dotnet/skills/ui-test-author/selenium`; there is no browser-binary step. `Directory.Build.props` carries settings only, exactly as in `qa-api-project-setup-dotnet`.

## The `.runsettings`

`UiTests.csproj` points `dotnet test` at `ui.runsettings` through `<RunSettingsFilePath>`. The Playwright adapter reads exactly four keys under `<Playwright>` — `BrowserName`, `LaunchOptions` (with `Headless`, `Channel`, `Args` inside it), `ExpectTimeout`, `TestIdAttribute` — and prints "not implemented" for any other. Override one for a run after `--`: `dotnet test -- Playwright.BrowserName=firefox`. Worker count is NUnit's: `-- NUnit.NumberOfTestWorkers=4`. Details: `ui-test-author/playwright/references/lifecycle.md` §5.

## The base fixture

`Support/BaseTest.cs` derives from `PageTest` and is the only Playwright lifecycle in the project:

- `ContextOptions()` amends `base.ContextOptions()` with `BaseURL` from `BASE_URL` (required) and a video folder; every override in a test class amends it again, never returns `new()`.
- Tracing starts in its `[SetUp]`; its `[TearDown]` keeps the trace, a full-page screenshot and the video **only for a failed test**, in `bin/<cfg>/net10.0/playwright-artifacts/`, and attaches them to the TRX and to Allure. It closes the context itself, because `PageTest` closes it only after a pass.
- `[Parallelizable(ParallelScope.Self)]` — the only scope Playwright supports.

CI uploads `UiTests/bin/<cfg>/net10.0/playwright-artifacts/` when the job fails (`qa/cicd/dotnet/skills/ci-pipelines`).

## Container

`UiTests/Dockerfile`, built from the solution root so it sees `Directory.Packages.props` and `TestCore`:

```dockerfile
FROM mcr.microsoft.com/playwright/dotnet:v1.63.0-noble
WORKDIR /src
COPY . .
RUN dotnet build UiTests/UiTests.csproj -c Release
ENTRYPOINT ["dotnet", "test", "UiTests/UiTests.csproj", "-c", "Release", "--no-build"]
```

```bash
docker build -f UiTests/Dockerfile -t ui-tests .
docker run --rm --ipc=host -e BASE_URL -e E2E_USER -e E2E_PASSWORD \
  -v "$PWD/artifacts:/src/UiTests/bin/Release/net10.0/playwright-artifacts" ui-tests
```

- The image already holds the browsers for 1.63.0, so there is no install step; bump the tag whenever the package version moves, or the run fails with "Executable doesn't exist".
- `--ipc=host` keeps Chromium from running out of shared memory. The image runs as root, which is fine for the team's own app; use `--user pwuser` when the tests visit untrusted sites.
- `.dockerignore` excludes `**/bin` and `**/obj`, so the host's build output never enters the image.

## Run

```bash
dotnet test
HEADED=1 dotnet test
dotnet test -- Playwright.LaunchOptions.Headless=false
PWDEBUG=1 dotnet test
dotnet test --filter "FullyQualifiedName~Checkout"
dotnet test --filter "TestCategory=smoke"
```

- `HEADED=1` is read by the Playwright adapter itself; `PWDEBUG=1` opens the Inspector with no timeouts.
- Debugging a failure: open the kept trace with `pwsh UiTests/bin/Debug/net10.0/playwright.ps1 show-trace <path-to-zip>`, or drop the zip on trace.playwright.dev (it loads in the browser, nothing is uploaded). `npx playwright show-trace` needs Node.
- The Allure report CLI and its pin are owned by `qa/reporting/dotnet/skills/test-reports`.

## Conventions (the shell only)

- **No `Thread.Sleep` / `Task.Delay` / `WaitForTimeoutAsync`.** Use Playwright auto-waiting and `Expect(...).ToBeVisibleAsync()`; for Selenium use explicit `WebDriverWait` helpers.
- **Page objects expose intent, not selectors**; one page object per screen; no assertions inside them.
- **One base fixture** (`Support/BaseTest.cs`) owns the context options and failure evidence; launch settings live in `ui.runsettings`.
- **Config / auth / secrets**: environment variables (`BASE_URL`, `E2E_USER`, `E2E_PASSWORD`), no secrets committed; the signed-in state file is written under `bin/` at run time.

Page-object architecture, selector strategy (`data-testid`-first), and test bodies are owned by the `qa-ui-dotnet` skills (`page-object-design`, `page-objects-from-url`, `ui-test-author/*`). Defer to them.

## Expanding into a multi-module solution

Flat solution + shared `TestCore` + CPM make this purely additive. To add a sibling (e.g. **ui + api**):

1. Install the sibling plugin and run its scaffold **inside this repo**, skipping `global.json`, `Directory.Build.props`, `Directory.Packages.props`, the `.sln`, and `TestCore` (already present).
2. Add only its project, `dotnet sln add ApiTests`, `dotnet add ApiTests reference TestCore`, then its packages (which append `<PackageVersion>` to the shared table). The sibling keeps its **own** configuration and `Dockerfile` — nothing to merge.
3. Promote shared config/auth helpers up into `TestCore`; keep `BaseTest` in `UiTests` and the RestClient factory in `ApiTests`.
4. `dotnet test` runs both projects; `dotnet test UiTests` runs one. Add `.slnf` filters per discipline for focused load / CI sharding. Mobile (`AppiumTests`) and performance (`PerfTests`, NBomber console) fold in the same way.

## Setup checklist

- [ ] `global.json` pins SDK 10.0 (or the repo's 8.0/9.0); `Directory.Packages.props` (CPM) is the only version source; csprojs versionless
- [ ] `Microsoft.Playwright.NUnit` 1.63.0 referenced alone; NUnit 4.x
- [ ] `Directory.Build.props` carries settings only
- [ ] `TestCore` is a shared library; `UiTests` references it
- [ ] Driver chosen deliberately (Playwright default; Selenium only if mandated)
- [ ] `ui.runsettings` picked up through `RunSettingsFilePath`; only the four Playwright keys
- [ ] `BaseTest` sets `BaseURL` from `BASE_URL` and keeps trace, screenshot and video on failure; `AuthSetup` in the root namespace
- [ ] Browsers installed (`playwright.ps1 install`) — or the run uses `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble`
- [ ] No secrets in the repo
- [ ] `dotnet build` clean; `dotnet test` green. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
