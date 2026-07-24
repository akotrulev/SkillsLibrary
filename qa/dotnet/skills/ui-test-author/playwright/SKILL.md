---
name: qa-ui-test-author-playwright-dotnet
description: Use when the user asks to scaffold Playwright UI tests in C# / .NET. Triggers: "write a Playwright test for X in C#", "add a Playwright .NET page object for screen Y", "scaffold a Playwright C# spec". For end-to-end suite work prefer the phased agent `qa-ui-dotnet` / `qa-bdd-dotnet` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Playwright Test & Page Object Generator (C# / .NET)

Scaffolds Playwright tests and page objects in **.NET 10 + NUnit** (net8/9 supported — match the project's TFM) using `Microsoft.Playwright` and `Microsoft.Playwright.NUnit`. Uses a **base-test class pattern**: tests inherit from `PageTest` (which Microsoft's package ships) and a project-local `BaseTest` that exposes page objects via `[SetUp]`. Tests do not instantiate browsers themselves. Locators use `GetByTestId` first (`data-testid` is the standing contract with the dev team — see `qa/dotnet/skills/pom-builder` for extraction and the missing-testid report), falling back to role/label semantics — never raw CSS where anything better exists.

## Stack

- .NET 10 (net8/9 supported — match the project's TFM), C# (nullable reference types enabled)
- NUnit 4.x
- `Microsoft.Playwright` + `Microsoft.Playwright.NUnit`
- Page objects under `Tests/Pages/`, test classes under `Tests/Specs/`
- Base class under `Tests/Support/`
- `Allure.NUnit` where the project uses Allure

## When to use

- New `*Tests.cs` under `Tests/Specs/`
- New page object under `Tests/Pages/`
- New base class or helper under `Tests/Support/`
- Adding a scenario to an existing test class

## When NOT to use

- Playwright TypeScript → `qa/typescript/skills/ui-test-author/playwright`
- Playwright Java → `qa/java/skills/ui-test-author/playwright`
- Mobile / Appium → `qa/dotnet/skills/ui-test-author/appium`
- Selenium C# → `qa/dotnet/skills/ui-test-author/selenium`
- Java Selenium → `qa/java/skills/ui-test-author/selenium`
- Reviewing existing Playwright code → `qa/dotnet/skills/ui-test-author/reviewer`
- Designing the overall page-object hierarchy → `qa/dotnet/skills/page-object-architect`

## Inputs needed

1. **Feature / page** under test (e.g. `Login`, `CheckoutCart`)
2. **User journey** — concrete steps + the user-visible outcome to assert
3. **Locators** — for each element: `GetByTestId` whenever the element has a `data-testid`; otherwise `GetByRole` / `GetByLabel`, then `GetByText`; CSS only as last resort. Missing testids are reported via `qa/dotnet/skills/pom-builder`'s `missing-testids.md`
4. **Auth requirement** — anonymous, or signed-in (which user role + how the session is established)
5. **Test data** — seeded by API, by helper, or inline

## Patterns

### `Tests.csproj`

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>   <!-- or net8.0 / net9.0 to match the project -->
    <Nullable>enable</Nullable>
    <LangVersion>latest</LangVersion>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Playwright" Version="1.49.0" />
    <PackageReference Include="Microsoft.Playwright.NUnit" Version="1.49.0" />
    <PackageReference Include="NUnit" Version="4.2.2" />
    <PackageReference Include="NUnit3TestAdapter" Version="4.6.0" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />
  </ItemGroup>
</Project>
```

### Base test — `Tests/Support/BaseTest.cs`

`PageTest` (from `Microsoft.Playwright.NUnit`) handles browser/context/page lifecycle per test. The project base only wires up page objects:

```csharp
using Microsoft.Playwright.NUnit;
using NUnit.Framework;
using Example.Tests.Pages;

namespace Example.Tests.Support;

public abstract class BaseTest : PageTest
{
    protected LoginPage LoginPage { get; private set; } = default!;
    protected HomePage HomePage { get; private set; } = default!;

    [SetUp]
    public void InitPages()
    {
        LoginPage = new LoginPage(Page);
        HomePage = new HomePage(Page);
    }
}
```

### Page object — `Tests/Pages/LoginPage.cs`

```csharp
using Microsoft.Playwright;
using static Microsoft.Playwright.Assertions;

namespace Example.Tests.Pages;

public sealed class LoginPage
{
    private readonly IPage _page;
    private readonly ILocator _email;
    private readonly ILocator _password;
    private readonly ILocator _submit;

    public ILocator ErrorBanner { get; }

    public LoginPage(IPage page)
    {
        _page = page;
        _email = page.GetByLabel("Email");
        _password = page.GetByLabel("Password");
        _submit = page.GetByRole(AriaRole.Button, new() { Name = "Sign in" });
        ErrorBanner = page.GetByTestId("login-error");
    }

    public Task GoToAsync() => _page.GotoAsync("/login");

    public async Task SignInAsync(string email, string password)
    {
        await _email.FillAsync(email);
        await _password.FillAsync(password);
        await _submit.ClickAsync();
    }

    public Task ExpectLoadedAsync() => Expect(_email).ToBeVisibleAsync();
}
```

### Test — `Tests/Specs/LoginTests.cs`

```csharp
using Microsoft.Playwright.NUnit;
using NUnit.Framework;
using Example.Tests.Support;
using static Microsoft.Playwright.Assertions;

namespace Example.Tests.Specs;

[Parallelizable(ParallelScope.Self)]
[TestFixture]
public class LoginTests : BaseTest
{
    [Test, Category("smoke")]
    public async Task Signs_In_With_Valid_Credentials()
    {
        await LoginPage.GoToAsync();
        await LoginPage.SignInAsync(
            Environment.GetEnvironmentVariable("E2E_USER")!,
            Environment.GetEnvironmentVariable("E2E_PASSWORD")!);

        await HomePage.ExpectLoadedAsync();
        await Expect(HomePage.Greeting).ToContainTextAsync("Welcome");
    }

    [Test]
    public async Task Shows_Error_For_Invalid_Password()
    {
        await LoginPage.GoToAsync();
        await LoginPage.SignInAsync(
            Environment.GetEnvironmentVariable("E2E_USER")!,
            "wrong");

        await Expect(LoginPage.ErrorBanner).ToBeVisibleAsync();
        await Expect(LoginPage.ErrorBanner)
            .ToHaveTextAsync(new System.Text.RegularExpressions.Regex("invalid credentials", System.Text.RegularExpressions.RegexOptions.IgnoreCase));
    }
}
```

### Authenticated state via `StorageState`

Sign in once via a `[OneTimeSetUp]` in a dedicated setup fixture, persist to a JSON file, and have `PageTest` consume it by overriding `ContextOptions()`:

```csharp
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.Tests.Support;

[SetUpFixture]
public class AuthSetup
{
    public const string StatePath = "playwright/.auth/user.json";

    [OneTimeSetUp]
    public async Task Authenticate()
    {
        using var pw = await Playwright.CreateAsync();
        var browser = await pw.Chromium.LaunchAsync();
        var ctx = await browser.NewContextAsync();
        var page = await ctx.NewPageAsync();
        var login = new Pages.LoginPage(page);
        await login.GoToAsync();
        await login.SignInAsync(
            Environment.GetEnvironmentVariable("E2E_USER")!,
            Environment.GetEnvironmentVariable("E2E_PASSWORD")!);
        await ctx.StorageStateAsync(new() { Path = StatePath });
        await browser.CloseAsync();
    }
}

public abstract class AuthenticatedBaseTest : BaseTest
{
    public override BrowserNewContextOptions ContextOptions() =>
        new() { StorageStatePath = AuthSetup.StatePath };
}
```

### API-seeded data

```csharp
[SetUp]
public async Task SeedOrder()
{
    var res = await Page.APIRequest.PostAsync("/api/orders",
        new() { DataObject = new { Sku = "ABC", Qty = 1 } });
    Assert.That(res.Ok, Is.True);
    _seededOrderId = (await res.JsonAsync())!.Value.GetProperty("id").GetString();
}
```

## Rules

### Locator preference order (strict)

1. `page.GetByTestId("...")` — **preferred whenever the element carries a `data-testid`**; the attribute is the agreed contract with the app team. Elements missing it go in the `missing-testids.md` dev-team report (extraction workflow: `qa/dotnet/skills/pom-builder`) and use a fallback below with `// TODO: missing data-testid '<suggested>'`
2. `page.GetByRole(AriaRole.X, new() { Name = "..." })` — best fallback
3. `page.GetByLabel("...")` — for form inputs
4. `page.GetByPlaceholder("...")` — only when there is no label
5. `page.GetByText("...", new() { Exact = true })` — for assertions on visible text
6. CSS / XPath via `page.Locator("...")` — **last resort**; add `// TODO: replace with data-testid locator` and a brief reason

### Page object rules

- Locators are `readonly ILocator` fields initialized in the constructor — **not** properties that re-query the DOM
- Constructor signature is `(IPage page)` — never take strings or config
- Action methods are `async Task` for same-page actions; for navigation return the next page object (e.g. `Task<HomePage>`)
- An `ExpectLoadedAsync()` method must exist and assert one landmark locator is visible
- **No assertions inside actions** — actions perform; tests and `ExpectLoadedAsync` assert
- **No `page.Locator("css selector")` in test classes** — wrap inside a page object
- Nullable reference types enabled — no `!`-bang in page objects beyond constructor initialization

### Test rules

- One test fixture per feature; group scenarios with NUnit `[Category("...")]`
- Test method names describe behavior: `Signs_In_With_Valid_Credentials`, `Shows_Error_For_Invalid_Password`
- One logical behavior per `[Test]`. Multiple `Expect(...)` calls are fine if they verify one behavior; otherwise split.
- **Every test asserts something.** A test that ends after an action with no assertion is not a test.
- Use web-first assertions: `Expect(locator).ToBeVisibleAsync() / .ToHaveTextAsync(...) / .ToHaveCountAsync(n) / .ToBeEnabledAsync()`. They retry until timeout. Never `await locator.IsVisibleAsync()` then `Assert.That(result, Is.True)` — one-shot checks lose auto-waiting.
- Prefer positive assertions over negated ones: `ToBeHiddenAsync()` over `Not.ToBeVisibleAsync()`, `ToBeDisabledAsync()` over `Not.ToBeEnabledAsync()`.
- **No `page.WaitForTimeoutAsync(ms)`** — use a web-first assertion with a `Timeout` option for conditional waits.
- **Do not pass `WaitUntil = WaitUntilState.NetworkIdle` to `GotoAsync`.** Brittle on SPAs with long-polling / WebSockets. Navigate, then assert a user-visible landmark.
- **Do not pre-wait before auto-waiting actions.** `ClickAsync` / `FillAsync` / `CheckAsync` already wait for actionability — `locator.WaitForAsync()` immediately before `locator.ClickAsync()` is redundant.
- **Do not use `Force = true`.** It skips actionability checks and hides real bugs. Fix the flow — close the overlay, scroll into view — instead of forcing.
- **`WaitForNavigationAsync` is deprecated.** Use `page.WaitForURLAsync("**/path")` or a web-first URL/landmark assertion.
- **`RunAndWaitForResponseAsync` ordering** — wrap the trigger in the action delegate so the listener is set up before the click:
  ```csharp
  var response = await page.RunAndWaitForResponseAsync(
      async () => await submit.ClickAsync(),
      r => r.Url.Contains("/api/data") && r.Status == 200);
  ```
  Never call `WaitForResponseAsync` after the action — the response can arrive first.
- **Retry loops:** never hand-roll `while (retries-- > 0) { ... Task.Delay ... }`. Raise the assertion timeout via the `Timeout` option, or for non-DOM polling use `Assert.That(() => ..., Is.EqualTo(...).After(timeout).PollEvery(interval))`.
- Prefer web-first assertions over `page.WaitForFunctionAsync(...)` for UI state.
- Pass `Exact = true` to `GetByText` / `GetByRole` `Name` when the expected text is a substring of other labels — otherwise a future label change causes a strict-mode violation.
- Tag tests with NUnit `[Category("smoke")]` so projects can filter.
- Async all the way down — never `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()`.

### Auth & storage state

- Sign in **once** per run via `[SetUpFixture]`, persist `StorageState` to a file, and consume it by overriding `ContextOptions()` on a base class; do not log in inside every test
- For tests that need a different role, create a separate `[SetUpFixture]` per role with its own state file
- Anonymous tests inherit from the plain `BaseTest`

### What NOT to do

- No `page.WaitForTimeoutAsync(ms)` — every wait must be conditional on a Locator or response
- No `WaitUntil = WaitUntilState.NetworkIdle` — assert a landmark instead
- No `Force = true` on `ClickAsync` / `FillAsync` / `CheckAsync` — fix the underlying flow
- No `locator.WaitForAsync(...)` immediately before an auto-waiting action — it is redundant
- No `WaitForNavigationAsync` (deprecated) — use `WaitForURLAsync` or a URL assertion
- No hand-rolled retry loops with `Task.Delay` — extend the assertion timeout
- No `page.WaitForFunctionAsync` for state covered by a web-first assertion
- No `Not.ToBeVisibleAsync()` when `ToBeHiddenAsync()` exists; no `Not.ToBeEnabledAsync()` when `ToBeDisabledAsync()` exists
- No `page.Locator("div.foo > span:nth-child(3)")` in test classes — promote to a page object with a semantic locator
- No `page.GotoAsync(...)` directly in test classes — put it in the page object's `GoToAsync()` so it owns its URL
- No `Console.WriteLine` for debugging in committed tests — use NUnit progress or the trace viewer instead
- No assertions in action methods — `ExpectLoadedAsync()` is the only assertion that belongs on a page object
- No `if`/`for` driving assertions — use NUnit `[TestCase(...)]` / `[TestCaseSource]` for parameterization
- No shared mutable state between tests — each test gets a fresh context (via `PageTest`) and fresh page objects
- No hardcoded credentials, base URLs, or environment hostnames — read from env vars / `appsettings.Test.json`
- No test without at least one assertion — actions without assertions verify nothing
- No NUnit `[Order]` chains across `[Test]` methods to model multi-step flows. Each test sets up its own state. For one journey, put the whole flow in a single test and use Allure `[AllureStep]` for the phases.

## Generation steps

1. Confirm **feature**, **scenarios**, **locators**, **auth requirement**, and **data source** with the user.
2. For each new screen, generate or extend `Tests/Pages/{Name}Page.cs`:
   - One `readonly ILocator` per element, initialized in the constructor with the best-available semantic locator
   - `GoToAsync()` method that owns the URL
   - `ExpectLoadedAsync()` that asserts one landmark
   - One action method per user-intent action
3. Add the page object as a property on `BaseTest` and initialize it in `[SetUp]`.
4. Generate `Tests/Specs/{Feature}Tests.cs` inheriting from `BaseTest` (or `AuthenticatedBaseTest`):
   - `[TestFixture]` per feature
   - One `[Test]` per scenario
5. For authenticated flows, ensure an `AuthSetup` `[SetUpFixture]` exists and the test inherits `AuthenticatedBaseTest`.
6. Install Playwright browsers once via `pwsh bin/Debug/net10.0/playwright.ps1 install` (use the project's TFM in the path; or the project's bootstrap script).
7. Run `dotnet test` — expect 0 failures. Run with `HEADED=1` (via `LaunchOptions`) to debug visually.

## Handoffs

- Designing the page-object hierarchy → `qa/dotnet/skills/page-object-architect`
- Reviewing existing Playwright tests → `qa/dotnet/skills/ui-test-author/reviewer`
- Test data builders → `qa/dotnet/skills/test-data-builder`
- Allure reporter setup → `qa/reporting/dotnet/skills/allure-reporting`
