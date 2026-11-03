---
name: ui-tests-playwright
description: Use when scaffolding Playwright UI tests in .NET/NUnit (specs, page objects, signed-in state, web-first assertions). Triggers "write a Playwright test for X". Not for Selenium (ui-tests-selenium).
---

# QA — Playwright Test & Page Object Generator (C# / .NET)

Scaffolds Playwright for .NET tests and page objects on **.NET 10 + NUnit 4** (net8/9 supported — match the
project's TFM). Every test class derives from **one `BaseTest : PageTest`**, which sets the base URL and
keeps failure evidence; the browser, headless mode, assertion timeout and test-id attribute come from one
**`.runsettings`**; locators climb **one ladder** with `data-testid` first; every check is a **web-first
assertion**. The code lives in `assets/`; the mechanics live in `references/`.

## Versions

These are the only Playwright pins in this skill. Every other file links here; `Directory.Packages.props`
in `assets/` carries the same values.

| Package | Version | Note |
|---|---|---|
| `Microsoft.Playwright.NUnit` | **1.63.0** | Pulls in `Microsoft.Playwright` and `Microsoft.Playwright.TestAdapter`; never reference them too. .NET 1.64 is not on NuGet yet |
| Docker image | `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` | .NET SDK 10, browsers preinstalled; the tag always equals the package version. No `-jammy` since 1.60 |
| `NUnit` | 4.6.1 | Stay on 4.x; NUnit 5 changes `Assert.ThrowsAsync` |
| `NUnit3TestAdapter` / `Microsoft.NET.Test.Sdk` | 6.3.1 / 18.10.1 | Both run NUnit 4 |
| `Allure.NUnit` | 2.15.0 | `[AllureNUnit]` on `BaseTest`; `AllureApi.AddAttachment(name, type, path)` |
| `Deque.AxeCore.Playwright` | 4.13.0 | Owned by `accessibility-testing` |
| `PercyIO.Playwright` / `Eyes.Playwright` | 1.0.4 / 1.37.49 | Owned by `visual-regression` |

**Version lane.** Detect the project's Playwright version and TFM and keep them — never up-level as a side
effect. A 1.64-only API does not compile on 1.63, though playwright.dev's .NET pages already list some; trust
the installed package. **From 1.64: `child.Within(parent)`** — on 1.63 write `parent.Locator(child)`;
`GetByRef`, `RecordVideoFps` and screencast style have no 1.63 form.

## Stack and layout

Nullable reference types on; Central Package Management, so no `Version=` in a `.csproj`.

```
UiTests/
├── UiTests.csproj        ui.runsettings          (Directory.Packages.props at the solution root)
├── AuthSetup.cs          root namespace Example.UiTests — signed-in state, once per run
├── Support/BaseTest.cs   the one lifecycle
├── Pages/                LoginPage.cs, HomePage.cs, components shared by several pages
└── Tests/                LoginTests.cs — one test class per feature
```

Namespaces follow the folders under one root (`Example.UiTests.Pages`). `AuthSetup` sits in the root
namespace itself, because NUnit runs a `[SetUpFixture]` only for the namespace it is declared in.

## When to use

- A new test class, page object, component object, or the `BaseTest` itself.
- A new or rewritten `UiTests.csproj`, `Directory.Packages.props`, `.runsettings` or signed-in state.
- Scoping or fixing locators, replacing one-shot reads with web-first assertions.
- Running a fixture per device, viewport, colour scheme, locale or time.

## When NOT to use

- Native mobile apps → `qa/dotnet/skills/ui-test-author/appium`
- Selenium → `qa/dotnet/skills/ui-test-author/selenium`
- Reviewing Playwright code → `qa/dotnet/skills/ui-test-author/review`
- Designing the page-object hierarchy → `qa/dotnet/skills/page-object-design`
- Extracting page objects and test ids from a live URL → `qa/dotnet/skills/page-objects-from-url`
- A new solution from zero (SDK, solution layout, Docker) → `qa/dotnet/skills/ui-project-setup`
- Screenshots, video, traces and HAR beyond the `BaseTest` defaults → `qa/dotnet/skills/evidence-capture`
- Visual regression, accessibility scans, network mocking → `visual-regression`, `accessibility-testing`,
  `network-mocking`
- Playwright TypeScript or Java → `qa/typescript/skills/ui-test-author/playwright`,
  `qa/java/skills/ui-test-author/playwright`

## Inputs needed

1. **Feature or page** under test (`Login`, `CheckoutCart`).
2. **User journey** — the steps and the one user-visible outcome to assert.
3. **Locators** — the test id for each element, or the fallback rung and a `missing-testids.md` row.
4. **Auth** — signed out, or signed in as which role.
5. **Test data** — seeded through the API in the class's `[SetUp]`, or a builder.
6. **Devices and media** — which fixtures run on which emulated device.

## What ships with this skill

| File | Holds |
|---|---|
| [`references/lifecycle.md`](references/lifecycle.md) | The four base classes, the SetUp/TearDown order, `ParallelScope.Self`, `ContextOptions()`, environment and runsettings keys, failure evidence, `AuthSetup`, API seeding, install / codegen / show-trace / headed commands |
| [`references/locators.md`](references/locators.md) | The ladder, `GetBy*`, `Filter` / `And` / `Or`, component roots, `parent.Locator(child)` and the 1.64 `Within()` line, `Visible`, frames, strictness, `Describe()`, overlays, the test-id attribute, agent-facing locators |
| [`references/assertions.md`](references/assertions.md) | The web-first set (accessible name, role, classes, URL, aria snapshots), one expected condition, no one-shot reads, timeouts, `Expect(locator, "message")`, `Assert.ThrowsAsync`, HTTP responses |
| [`references/emulation-and-mobile-web.md`](references/emulation-and-mobile-web.md) | `Playwright.Devices[...]`, touch, viewport, media features, locale, geolocation, `Page.Clock`, offline |
| [`assets/Directory.Packages.props`](assets/Directory.Packages.props), [`assets/UiTests.csproj`](assets/UiTests.csproj) | The pins in one place; a versionless project that picks up the runsettings |
| [`assets/ui.runsettings`](assets/ui.runsettings) | `BrowserName`, `LaunchOptions` / `Headless`, `ExpectTimeout`, `TestIdAttribute` |
| [`assets/BaseTest.cs`](assets/BaseTest.cs) | `BASE_URL`, `ContextOptions()` amending the base, tracing, failure evidence to NUnit and Allure |
| [`assets/AuthSetup.cs`](assets/AuthSetup.cs) | The root-namespace `[SetUpFixture]` that saves the signed-in state |
| [`assets/LoginPage.cs`](assets/LoginPage.cs), [`assets/HomePage.cs`](assets/HomePage.cs) | Intent methods, a `SignInForm` component, the error scoped with `parent.Locator(child)`; the landing page |
| [`assets/LoginTests.cs`](assets/LoginTests.cs) | `Should_X_When_Y` tests, categories, pages built per test |

Start from the assets: copy them, rename the root namespace, and keep their shape.

## Rules

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `automation.md` and `web-ui.md`. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Mechanics the rules rely on

- Launch options live in the `.runsettings` (`BrowserName`, `LaunchOptions`, `ExpectTimeout`, `TestIdAttribute`, the only keys the adapter reads). The browser is per worker, so a suite that needs other launch arguments gets its own `.runsettings` and run. `HEADED=1` runs headed; `BROWSER=firefox` switches the browser.
- `BaseTest`'s `[TearDown]` closes the context itself (`PageTest` does so only after a pass), then saves the video; evidence lands in `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.{zip,png,webm}`. The video API is `PathAsync()`; the docs' `GetPathAsync()` does not exist.
- Locators are `private readonly ILocator` fields built in the constructor, with get-only properties for the ones tests assert on (not expression-bodied, so the definitions stay together). A component takes its root `ILocator` and builds its children from it, as `SignInForm` does.
- The `Visible` property (1.63) instead of `:visible`; `FrameLocator` / `ContentFrame` for iframes; `AddLocatorHandlerAsync` for overlays that may appear; `Expect(locator, "message")` (1.60) where the record or user matters. `ILocator` has no `.Text`; that is Selenium's `IWebElement`.
- A slow state raises the matcher's timeout (`ToBeVisibleAsync(new() { Timeout = 15_000 })`) or sets `ExpectTimeout` once in the runsettings.
- Categories tag the area and the tier (`[Category("login")]`, `[Category("smoke")]`), `[AllureFeature]` on the class; a long journey is one test with `[AllureStep]` methods.
- An API call inside a UI test asserts the exact status with the body as the message: `Assert.That(created.Status, Is.EqualTo(201), await created.TextAsync())`, never `res.Ok` or `ToBeOKAsync()`.

## Generation steps

1. Detect the installed Playwright, NUnit and Allure versions, the TFM, CPM and the project layout; match
   them.
2. Confirm the feature, scenarios, locators, auth, data and devices with the user.
3. No `BaseTest` yet: add `assets/BaseTest.cs`, `ui.runsettings` and `RunSettingsFilePath`. One whose
   `ContextOptions()` returns `new()`, a `[SetUpFixture]` outside the root namespace, or inline `Version=`
   under CPM: fix that first.
4. For each screen, write or extend `Pages/<Name>Page.cs` from `assets/LoginPage.cs`: one locator per element
   on the highest ladder rung, components for reused regions, `GoToAsync()`, intent methods, `Describe()` on
   asserted locators. Add a `missing-testids.md` row for every fallback.
5. Write `Tests/<Feature>Tests.cs` from `assets/LoginTests.cs`: derives from `BaseTest`, pages built in a
   `[SetUp]`, one `[Test]` per scenario with a `Should_X_When_Y` name and categories.
6. For signed-in fixtures, keep `AuthSetup` in the root namespace and amend `ContextOptions()` with
   `StorageStatePath`; for devices, amend it from `Playwright.Devices[...]`.
7. Build, install the browser with `pwsh bin/Debug/net10.0/playwright.ps1 install chromium`, and run
   `dotnet test` (0 failures); debug with `HEADED=1` or `PWDEBUG=1`.

## Handoffs

Besides the skills under "When NOT to use":

- Test data builders → `qa/dotnet/skills/test-data-builder`
- Breakpoint matrices → `qa/dotnet/skills/responsive-testing`
- Real-device mobile web → `qa/dotnet/skills/device-cloud`
- Allure reporting and CI → `qa/reporting/dotnet/skills/test-reports`, `qa/cicd/dotnet/skills/ci-pipelines`
