---
name: qa-bdd-project-setup-dotnet
description: Use when adding the Reqnroll (SpecFlow successor) BDD layer onto a .NET 10 (8-9) UI/mobile test project, or standing up a Reqnroll + NUnit project from zero. Triggers "set up Reqnroll", "add a BDD layer to our Playwright/Appium tests in C#", "wire Reqnroll DI and hooks". Not for writing feature files (`feature-file-writer`), step definitions (`gherkin-step-code`), or page objects (`page-object-design`).
---

# Reqnroll BDD Project Scaffold (C# / .NET 10)

Wires **Reqnroll** (the maintained SpecFlow successor) into a .NET test project: packages, `reqnroll.json`, the `Features/` folder, the DI container (`[ScenarioDependencies]` via `Reqnroll.Microsoft.Extensions.DependencyInjection`), the per-scenario browser/driver lifecycle hooks, and the shared scenario-context object that step definitions inject. It produces the **empty rig** — no feature files, no step logic; those come from `feature-file-writer` and `gherkin-step-code`.

**Version rule:** this layer is added onto an existing UI/mobile project — **match that project's `TargetFramework`**. For a from-zero rig, target **net10.0** (the library primary); net8 (LTS) / net9 (STS) are supported fallbacks. Never up-level the host project.

This is the BDD analogue of `ui-project-setup`; it assumes a Playwright (web) or Appium (mobile) page-object project either exists or will be built by `qa-ui-dotnet` / `qa-mobile-dotnet`.

## Stack (pinned, verify latest at author time)

- .NET 10 (or the host project's TFM — 8/9 supported), C# (nullable enabled), NUnit 4.x
- `Reqnroll.NUnit` (core + NUnit integration; latest line **3.3.x**)
- `Reqnroll.Microsoft.Extensions.DependencyInjection` (MS DI plugin; needs `Microsoft.Extensions.DependencyInjection` ≥ 6)
- Web: `Microsoft.Playwright` (≥ 1.49) — there is **no** first-party Reqnroll+Playwright package; wire it by hand
- Mobile: `Appium.WebDriver` 8.x (Selenium 4)
- `Reqnroll.Allure` when the project reports through Allure (the library default)
- Features under `Features/`, step definitions under `StepDefinitions/`, hooks + context + DI under `Support/`

## When to use

- A .NET UI/mobile project needs Reqnroll added (packages, config, hooks, DI).
- Starting a Reqnroll suite from zero.

## When NOT to use

- Writing `.feature` files → `qa/_shared/bdd/feature-file-writer`
- Generating `[Binding]` step classes → `qa/dotnet/skills/gherkin-step-code`
- Building page objects → `qa/dotnet/skills/page-object-design` / `page-objects-from-url`
- Reqnroll in Java/TS → `qa/{java,typescript}/skills/bdd-project-scaffold` (those use Cucumber-JVM / playwright-bdd)

## Inputs needed

Confirm at most 2–3.

1. **Target project path** and whether a Playwright/Appium page-object project already exists (reuse it; don't duplicate page objects).
2. **Platform** — web (Playwright), mobile (Appium), or both (two hook/context pairs).
3. **Reporting** — native Reqnroll HTML formatter (default) or Allure (the library standard).

## Procedure

1. Read 2–3 existing files (the `.csproj`, an existing page object, `BaseTest`) to match namespaces and conventions.
2. Add the Reqnroll packages to the test `.csproj` (or a new `Bdd.Tests.csproj`). Reqnroll generates feature code-behind via a build-time source generator — no MSBuild generator config needed.
3. Create `reqnroll.json` with the report formatter and (optionally) the Cucumber-Expression behavior.
4. Create `Support/` : the DI registration (`[ScenarioDependencies]`), the scenario-context object, and the lifecycle hooks (`[BeforeScenario]`/`[AfterScenario]` that own the Playwright page or Appium driver — **with teardown**).
5. Create the empty `Features/` folder and one throwaway smoke `.feature` to prove the rig parses and runs.
6. `dotnet build` (the source generator must produce code-behind) and run the smoke scenario. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
7. Report files created and hand off to `feature-file-writer` (features) + `gherkin-step-code` (steps).

## Templates

### `Bdd.Tests.csproj`

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>   <!-- match the host UI/mobile project (net8.0 / net9.0 / net10.0) -->
    <Nullable>enable</Nullable>
    <LangVersion>latest</LangVersion>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Reqnroll.NUnit" Version="3.3.4" />
    <PackageReference Include="Reqnroll.Microsoft.Extensions.DependencyInjection" Version="3.3.4" />
    <PackageReference Include="Microsoft.Playwright" Version="1.49.0" />
    <PackageReference Include="NUnit" Version="4.2.2" />
    <PackageReference Include="NUnit3TestAdapter" Version="4.6.0" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />
    <!-- Allure (library default reporting): -->
    <!-- <PackageReference Include="Reqnroll.Allure" Version="..." /> -->
  </ItemGroup>
  <ItemGroup>
    <!-- Reuse the existing page-object project rather than copying pages -->
    <ProjectReference Include="..\UiTests\UiTests.csproj" />
  </ItemGroup>
</Project>
```

### `reqnroll.json`

```json
{
  "$schema": "https://schemas.reqnroll.net/reqnroll-config-latest.json",
  "language": { "feature": "en" },
  "formatters": {
    "html": { "outputFilePath": "TestResults/bdd-report.html" }
  }
}
```

> Living documentation: Reqnroll's native HTML formatter (shipped since v3.0) replaces the discontinued SpecFlow+LivingDoc. For CI dashboards, prefer Allure via `Reqnroll.Allure` — `qa-reporting-dotnet` owns that wiring.

### `Support/TestDependencies.cs` — DI container

```csharp
using Microsoft.Extensions.DependencyInjection;
using Reqnroll.Microsoft.Extensions.DependencyInjection;

namespace Bdd.Tests.Support;

public static class TestDependencies
{
    // Must be static and return IServiceCollection. [Binding] classes are auto-registered.
    [ScenarioDependencies]
    public static IServiceCollection CreateServices()
    {
        var services = new ServiceCollection();
        // Scoped == one instance per scenario. Page objects are created in the hook
        // from the scenario's IPage, so register the context as scoped here.
        services.AddScoped<ScenarioState>();
        return services;
    }
}
```

### `Support/ScenarioState.cs` — shared per-scenario state (web)

```csharp
using Microsoft.Playwright;
using Bdd.Tests.Pages; // the existing page-object project

namespace Bdd.Tests.Support;

// One per scenario (scoped). Holds the page + lazily-built page objects so every
// step definition shares the same IPage. No assertions, no logic — just state.
public sealed class ScenarioState
{
    public IPage Page { get; set; } = default!;
    public LoginPage Login => new(Page);
    public DashboardPage Dashboard => new(Page);
}
```

### `Support/BrowserHooks.cs` — per-scenario lifecycle (web, async, with teardown)

```csharp
using Microsoft.Playwright;
using Reqnroll;

namespace Bdd.Tests.Support;

[Binding]
public sealed class BrowserHooks
{
    private readonly ScenarioState _state;
    private IPlaywright? _pw;
    private IBrowser? _browser;
    private IBrowserContext? _context;

    public BrowserHooks(ScenarioState state) => _state = state;

    [BeforeScenario(Order = 0)]
    public async Task StartBrowserAsync()
    {
        _pw = await Playwright.CreateAsync();
        _browser = await _pw.Chromium.LaunchAsync(new() { Headless = true });
        _context = await _browser.NewContextAsync();
        _state.Page = await _context.NewPageAsync();
    }

    [AfterScenario]
    public async Task StopBrowserAsync()
    {
        if (_context is not null) await _context.CloseAsync();
        if (_browser is not null) await _browser.DisposeAsync();
        _pw?.Dispose();
    }
}
```

> The widely-cited Reqnroll+Playwright blog example **leaks the browser** (no teardown). Always dispose context → browser → playwright in `[AfterScenario]`. Prefer one browser per test run (`[BeforeTestRun]`, static/async) and a fresh context+page per scenario for speed + isolation when the suite grows; the per-scenario form above is the simplest correct baseline.

### Mobile variant (`ScenarioState` + hook)

For Appium, `ScenarioState` holds an `AppiumDriver` (sync API) built in `[BeforeScenario]` via the existing `AppiumDriverFactory`, and disposed with `Driver.Quit()` in `[AfterScenario]`. Page objects extend the existing `BaseAppiumPage`.

## Anti-patterns to flag

- Putting browser/driver lifecycle in step-definition constructors instead of hooks.
- Static mutable state for the page/driver — use the scoped `ScenarioState` via DI (library rule: no static mutable state).
- Missing `[AfterScenario]` teardown — leaks browsers/drivers.
- Re-declaring page objects in the BDD project instead of `ProjectReference`-ing the existing UI project.
- Manual registration of `[Binding]` classes in the DI method — Reqnroll auto-registers them.
- Using the `ScenarioContext` string-bag for state that should be typed DI.

## Handoffs

- Feature files → `qa/_shared/bdd/feature-file-writer`
- Step definitions + POM wiring → `qa/dotnet/skills/gherkin-step-code`
- Page objects → `qa/dotnet/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- Allure reporting → `qa/reporting/dotnet/skills/test-reports`
- CI (feature shard, publish report) → `qa/cicd/dotnet/skills/ci-pipelines`
