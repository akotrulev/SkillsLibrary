---
name: ui-tests-playwright
description: Use when the user asks to scaffold Playwright UI tests in C# / .NET — NUnit test classes, page objects, BaseTest, .runsettings, signed-in state, locator scoping, web-first assertions, or device emulation. Triggers "write a Playwright test for X in C#", "add a Playwright .NET page object for screen Y", "set up Playwright with NUnit". Do NOT use for Selenium (`qa-dotnet:ui-tests-selenium`), Appium (`qa-dotnet:ui-tests-appium`) or reviewing tests (`qa-dotnet:ui-tests-review`).
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

### Lifecycle

- **Every test class derives from the one `BaseTest`.** No test or specialised skill calls
  `Playwright.CreateAsync()` or declares a second base class; a role, a device or a locale is an override
  of `ContextOptions()` on the fixture that needs it. The one other `Playwright.CreateAsync()` is
  `AuthSetup`'s `[OneTimeSetUp]`.
- **`ContextOptions()` amends `base.ContextOptions()`**, never returns `new()` — that drops `BaseURL`, the
  video folder and the defaults.
- **Parallelism is `ParallelScope.Self` only**, declared once on `BaseTest`. Never `All`, `Children` or
  `Fixtures`: tests of one fixture share one instance and its `Page`.
- **Launch options live in the `.runsettings`** (`BrowserName`, `LaunchOptions`, `ExpectTimeout`,
  `TestIdAttribute` — the only keys the adapter reads). The browser is per worker, so a suite that needs
  other launch arguments gets its own `.runsettings` and run.
- `BASE_URL` is required: `GotoAsync("/login")` and `Page.APIRequest` resolve against it. `HEADED=1` runs
  headed (the adapter reads it); `BROWSER=firefox` switches the browser.
- Failure evidence is `BaseTest`'s: trace, full-page screenshot and video kept only on failure, in
  `<WorkDirectory>/playwright-artifacts/<Class>.<Test>.{zip,png,webm}`. Its `[TearDown]` closes the context
  itself — `PageTest` does so only after a pass — then saves the video. The video API is `PathAsync()`; the
  docs' `GetPathAsync()` does not exist.

### Locators

1. **The ladder:** `GetByTestId` → `GetByRole` → `GetByLabel` → `GetByPlaceholder` → `GetByText` →
   `GetByAltText` / `GetByTitle` → CSS. The first rung the element supports wins.
2. **Test ids are PascalCase dot-separated and static** — `Login.Submit`, `OrderRow`, `OrderRow.Title` — the
   format `fe-react` and `fe-blazor` generate. A row is picked by its content, never by an id that embeds a
   key, an index or a state.
3. **A fallback carries no marker in the code.** Record it in `missing-testids.md` (page, element,
   suggested id, fallback in use). The report is the contract; no `TODO`, no comment on the locator.
4. **Scope instead of picking.** A locator that matches many is narrowed by its component root,
   `parent.Locator(child)`, or `Filter(new() { Has = ... })` / `Filter(new() { HasText = ... })`. `Nth()` /
   `First` only where order is the behaviour, and then the member name says so.
5. The `Visible` property (1.63) instead of `:visible`; `FrameLocator` / `ContentFrame` for iframes;
   `AddLocatorHandlerAsync` for overlays that may appear; `Describe()` on every locator a test asserts on.
6. **Never assert on an `Or()` locator** — it passes on either state.

### Page objects

- Locators are built once, in the constructor: `private readonly ILocator` fields, and get-only properties
  for the ones tests assert on (`Error`). Not expression-bodied properties: a lazy locator is no slower
  there, but the definitions scatter.
- A page takes `(IPage page)`. A **component** (a region reused across pages — a form, a row, a menu) takes
  its root `ILocator` and builds its children from it, as `SignInForm` does.
- Methods are `async Task`, named for user intent (`SignInAsync`, `AddToCartAsync`), never the widget
  (`ClickButtonAsync`). An action that always lands on another page may return that page object.
- The page owns its URL in `GoToAsync()`. Test classes never call `Page.GotoAsync`, `Page.Locator` or any
  other raw `Page` method.
- **No assertions in page objects.** They expose locators; tests assert. An optional `ExpectLoadedAsync()`
  that asserts one landmark is the only exception.
- Pages are built in the test class's `[SetUp]`, never as properties of `BaseTest`. No shared `BasePage`
  until three pages share real behaviour (`page-object-design`).

### Tests

- **Names are `Should_X_When_Y`** (`Should_ShowInvalidCredentialsError_When_PasswordIsWrong`), one test class
  per feature.
- **Categories tag the area and the tier:** `[Category("login")]`, `[Category("smoke")]`;
  `[AllureFeature("Login")]` on the class.
- One logical behaviour per test; every test asserts. Several assertions are fine when they check one
  behaviour.
- **Web-first assertions only** (`references/assertions.md`). No one-shot read compared later
  (`Assert.That(await loc.IsVisibleAsync(), Is.True)`, `TextContentAsync()`); `ILocator` has no `.Text`
  (that is Selenium's `IWebElement`).
- **One expected condition per assertion — never an `OR`**: no `.Or.`, no `Is.AnyOf(...)`, no `||` in
  `Assert.That`, no `Regex("a|b")` in a text or URL assertion. Split the outcomes, or use `[TestCase]`.
- **Failures name the subject:** `Describe()` on the locator, and `Expect(locator, "message")` (1.60) where
  the record or user matters; NUnit value assertions carry the evidence as the message.
- **No `try` / `catch` / `finally` in a test or a hook.** An expected exception from async code is
  `Assert.ThrowsAsync<T>` — never `Assert.Throws<T>` around a `Task`, which reports that nothing was thrown.
  Cleanup is the class's `[TearDown]`.
- No `if` or `for` driving assertions; `[TestCase]` / `[TestCaseSource]` instead. Tests are independent:
  no `[Order]` chains, no shared mutable state. One long journey is one test with `[AllureStep]` methods.
- API responses assert the exact status with the body:
  `Assert.That(created.Status, Is.EqualTo(201), await created.TextAsync())` — never
  `Assert.That(res.Ok, Is.True)` or `ToBeOKAsync()`.
- Async all the way: never `.Result`, `.Wait()` or `.GetAwaiter().GetResult()`. No hardcoded credentials,
  URLs or hostnames — `BASE_URL`, `E2E_USER`, `E2E_PASSWORD`. No `Console.WriteLine`; use the trace.

### Waiting

- No `WaitForTimeoutAsync` and no `Task.Delay` for UI state; raise the matcher's timeout
  (`ToBeVisibleAsync(new() { Timeout = 15_000 })`), or set `ExpectTimeout` once in the runsettings.
- No `WaitUntil = WaitUntilState.NetworkIdle`; navigate, then assert a landmark.
- No `WaitForAsync()` before an action that already auto-waits; no `Force = true` (close the overlay with
  `AddLocatorHandlerAsync`, scroll, wait for the state).
- No `WaitForNavigationAsync` (deprecated); `WaitForURLAsync` or `Expect(Page).ToHaveURLAsync(...)`, whose
  string is an exact match — a glob needs `WaitForURLAsync` or a `Regex`. No page-level selector APIs
  (`Page.ClickAsync(selector)`, `Page.InnerTextAsync(selector)`).
- `RunAndWaitForResponseAsync(action, predicate)` starts the wait with the action. No hand-rolled retry
  loops.

### Auth and data

- Sign in **once per run per role** in `AuthSetup` (root namespace), save the state, and point signed-in
  fixtures at it in `ContextOptions()`. Never sign in inside every test.
- Records a test needs are created through `Page.APIRequest` in the class's `[SetUp]`, with a unique value
  per test, and deleted in its `[TearDown]`. Never seed in `[OneTimeSetUp]`.
- Builders for any record with four or more fields (`qa/dotnet/skills/test-data-builder`).

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
   `dotnet test` (0 failures); debug with `HEADED=1` or `PWDEBUG=1`. In a `Gate: none` plan task, run none
   of this; report the files as "written, not run".

## Handoffs

Besides the skills under "When NOT to use":

- Test data builders → `qa/dotnet/skills/test-data-builder`
- Breakpoint matrices → `qa/dotnet/skills/responsive-testing`
- Real-device mobile web → `qa/dotnet/skills/device-cloud`
- Allure reporting and CI → `qa/reporting/dotnet/skills/test-reports`, `qa/cicd/dotnet/skills/ci-pipelines`
