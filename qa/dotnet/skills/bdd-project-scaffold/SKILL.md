---
name: qa-bdd-project-setup-dotnet
description: Use when adding the Reqnroll (SpecFlow successor) BDD layer onto a .NET 10 (8-9) UI/mobile test project, or standing up a Reqnroll + NUnit project from zero. Triggers "set up Reqnroll", "add a BDD layer to our Playwright/Appium tests in C#", "wire Reqnroll DI and hooks". Not for writing feature files (`feature-file-writer`), step definitions (`gherkin-step-code`), or page objects (`page-object-design`).
---

# Reqnroll BDD Project Scaffold (C# / .NET 10)

Wires **Reqnroll** (the maintained SpecFlow successor) into a .NET test project: packages under Central Package
Management, `reqnroll.json`, the `Features/` folder, the DI container (`[ScenarioDependencies]` via
`Reqnroll.Microsoft.Extensions.DependencyInjection`), the per-scenario browser/driver lifecycle **with failure
evidence**, and the shared scenario state that step definitions inject. It produces the **empty rig** — no
feature files, no step logic; those come from `feature-file-writer` and `gherkin-step-code`.

**Version rule:** this layer is added onto an existing UI/mobile project — **match that project's
`TargetFramework`**. For a from-zero rig, target **net10.0** (the library primary); net8 (LTS) / net9 (STS) are
supported fallbacks. Never up-level the host project.

This is the BDD analogue of `ui-project-setup`; it reuses the Playwright UI project
(`qa/dotnet/skills/ui-test-author/playwright` — `UiTests`, its page objects, its runsettings) or the Appium
project built by `qa-mobile-dotnet`.

## Stack

- .NET 10 (or the host project's TFM — 8/9 supported), C# (nullable enabled), NUnit 4 — the pins of the UI
  project's `Directory.Packages.props` (`ui-test-author/playwright/assets/`)
- `Reqnroll.NUnit` and `Reqnroll.Microsoft.Extensions.DependencyInjection` **3.3.4**
- Web: **`Microsoft.Playwright.NUnit` 1.63.0** — already pinned in that props file; it brings `Microsoft.Playwright`
  and the `PlaywrightSettingsProvider` the hooks read the runsettings through. There is **no** first-party
  Reqnroll+Playwright package; the hooks are wired by hand
- Mobile: Appium.WebDriver at the pin in `qa/dotnet/skills/ui-test-author/appium`
- `Allure.Reqnroll` **2.15.0** (the same release line as `Allure.NUnit`) when the project reports through Allure,
  the library default
- Features under `Features/`, step definitions under `StepDefinitions/`, hooks + state + DI under `Support/`

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
2. **Platform** — web (Playwright), mobile (Appium), or both (two hook/state pairs).
3. **Reporting** — Allure (the library standard) and/or the native Reqnroll HTML formatter.

## Procedure

1. Read 2–3 existing files (the `.csproj`, `Directory.Packages.props`, an existing page object, `BaseTest`) to
   match namespaces and conventions.
2. Add the Reqnroll and Allure `PackageVersion` entries to the solution's `Directory.Packages.props`, and a
   versionless `Bdd.Tests.csproj` beside `UiTests`. Reqnroll generates feature code-behind with a build-time
   source generator — no MSBuild generator config.
3. Create `reqnroll.json`.
4. Create `Support/`: the DI registration (`[ScenarioDependencies]`), `ScenarioState`, and `BrowserHooks`
   (`references/hooks.md`) — the browser per scenario, failure evidence, teardown.
5. Create the empty `Features/` folder and one throwaway smoke `.feature` to prove the rig parses and runs.
6. `dotnet build` (the source generator must produce code-behind) and run the smoke scenario with `BASE_URL`
   set. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
7. Report files created and hand off to `feature-file-writer` (features) + `gherkin-step-code` (steps).

## Templates

### `Directory.Packages.props` — the additions

The UI project's props file already pins `Microsoft.Playwright.NUnit` 1.63.0, NUnit 4.6.1, the adapter, the Test
SDK and `Allure.NUnit`. The BDD project adds:

```xml
<ItemGroup>
  <PackageVersion Include="Reqnroll.NUnit" Version="3.3.4" />
  <PackageVersion Include="Reqnroll.Microsoft.Extensions.DependencyInjection" Version="3.3.4" />
  <PackageVersion Include="Allure.Reqnroll" Version="2.15.0" />
</ItemGroup>
```

A project that references `Microsoft.Playwright` directly instead of `.NUnit` adds
`<PackageVersion Include="Microsoft.Playwright" Version="1.63.0" />` — never both packages in one project.

### `Bdd.Tests.csproj`

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <IsPackable>false</IsPackable>
    <RunSettingsFilePath>$(MSBuildProjectDirectory)/../UiTests/ui.runsettings</RunSettingsFilePath>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" />
    <PackageReference Include="NUnit" />
    <PackageReference Include="NUnit3TestAdapter" />
    <PackageReference Include="Reqnroll.NUnit" />
    <PackageReference Include="Reqnroll.Microsoft.Extensions.DependencyInjection" />
    <PackageReference Include="Microsoft.Playwright.NUnit" />
    <PackageReference Include="Allure.Reqnroll" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\UiTests\UiTests.csproj" />
  </ItemGroup>
</Project>
```

- `TargetFramework` matches the host UI/mobile project; no `Version=` on a `PackageReference` under CPM (NU1008).
- The `ProjectReference` reuses `UiTests`' page objects and `BaseTest.RequiredEnv`; the runsettings path reuses
  its browser, headless and expect-timeout settings, so a scenario and a fixture run the same browser.

### `reqnroll.json`

```json
{
  "$schema": "https://schemas.reqnroll.net/reqnroll-config-latest.json",
  "language": { "feature": "en" },
  "bindingAssemblies": [ { "assembly": "Allure.ReqnrollPlugin" } ],
  "formatters": {
    "html": { "outputFilePath": "TestResults/bdd-report.html" }
  }
}
```

`bindingAssemblies` loads the Allure plugin's bindings; drop it when the project does not report through Allure.
Reqnroll's native HTML formatter (since v3.0) is the living documentation; the Allure mapping itself (history,
categories, publish) is `qa/reporting/dotnet/skills/test-reports`'.

### `Support/TestDependencies.cs` — DI container

```csharp
using Microsoft.Extensions.DependencyInjection;
using Reqnroll.Microsoft.Extensions.DependencyInjection;

namespace Example.BddTests.Support;

public static class TestDependencies
{
    [ScenarioDependencies]
    public static IServiceCollection CreateServices()
    {
        var services = new ServiceCollection();
        services.AddScoped<ScenarioState>();
        return services;
    }
}
```

The method is static and returns `IServiceCollection`; scoped means one instance per scenario. `[Binding]`
classes are registered by Reqnroll — never add them here.

### `Support/ScenarioState.cs` — shared per-scenario state (web)

```csharp
using Example.UiTests.Pages;
using Microsoft.Playwright;

namespace Example.BddTests.Support;

public sealed class ScenarioState
{
    public IPage Page { get; private set; } = null!;

    public LoginPage Login { get; private set; } = null!;

    public HomePage Home { get; private set; } = null!;

    public void Open(IPage page)
    {
        Page = page;
        Login = new LoginPage(page);
        Home = new HomePage(page);
    }
}
```

The hook opens the page and builds the page objects once per scenario; steps reach them through the state,
never `new` them. No assertions, no logic — just state.

### `Support/BrowserHooks.cs` — per-scenario lifecycle and failure evidence

The code is in [`references/hooks.md`](references/hooks.md). Its contract, fixed by
`qa/dotnet/skills/evidence-capture` ("Reqnroll scenarios"):

| Step | Hook | Does |
|---|---|---|
| Open | `[BeforeScenario(Order = 0)]` | `Playwright.CreateAsync()`; the runsettings browser via `PlaywrightSettingsProvider`; a context with `BaseURL` from `BASE_URL`, `RecordVideoDir` = `<WorkDirectory>/playwright-videos`, `Locale` en-US, `ColorScheme` Light; tracing with screenshots, snapshots and sources; `ScenarioState.Open(page)` |
| Keep | `[AfterScenario(Order = 20_000)]` — after every other hook | When `ScenarioContext.TestError` is set: stop the trace to a path, full-page screenshot, close the context, `SaveAsAsync` the video; always `DeleteAsync` the raw video. No catch |
| Name | — | `<Feature>.<Scenario>`, every character outside `[A-Za-z0-9._-]` replaced by `_`, in `<WorkDirectory>/playwright-artifacts/` |
| Attach | — | `TestContext.AddTestAttachment` + `AllureApi.AddAttachment(name, type, path)`; the trace as `application/vnd.allure.playwright-trace` |

> The widely-cited Reqnroll+Playwright blog example **leaks the browser** (no teardown) and keeps no evidence.
> The hook closes the driver and the browser on the way out with `using` / `await using`, even when an evidence
> step throws.

### Mobile variant (`ScenarioState` + hook)

For Appium, `ScenarioState` holds an `AppiumDriver` (sync API) built in `[BeforeScenario]` via the existing
driver factory and quit in `[AfterScenario]`; page objects extend the existing base page. Appium failure
evidence follows `qa/dotnet/skills/evidence-capture`'s Appium reference.

## Anti-patterns to flag

- Browser/driver lifecycle in step-definition constructors instead of hooks.
- Static mutable state for the page/driver — use the scoped `ScenarioState` via DI.
- Missing `[AfterScenario]` teardown — leaks browsers/drivers; a teardown that keeps **no trace, screenshot or
  video** on a failed scenario.
- A hardcoded browser or `Headless = true` in the hook, or a context with no `BaseURL` — read the runsettings and
  `BASE_URL`.
- `Version=` on a `PackageReference` under CPM, or a floating / pre-1.63 Playwright pin.
- A `catch` in a hook to "save the video anyway".
- Re-declaring page objects in the BDD project instead of `ProjectReference`-ing the existing UI project.
- Manual registration of `[Binding]` classes in the DI method — Reqnroll auto-registers them.
- Using the `ScenarioContext` string-bag for state that should be typed DI.

## Handoffs

- Feature files → `qa/_shared/bdd/feature-file-writer`
- Step definitions + POM wiring → `qa/dotnet/skills/gherkin-step-code`
- Page objects → `qa/dotnet/skills/page-object-design` / `page-objects-from-url` / `mobile-screen-objects`
- Evidence rules and reading a failed scenario's trace → `qa/dotnet/skills/evidence-capture`
- Allure reporting → `qa/reporting/dotnet/skills/test-reports`
- CI (feature shard, publish report, upload `playwright-artifacts/`) → `qa/cicd/dotnet/skills/ci-pipelines`
