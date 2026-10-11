---
name: inhouse-framework-conventions
description: Use when working in the C# / .NET 10 (8-9 supported) Accelerator test automation framework (NUnit + RestSharp + Playwright + Appium, JSON-driven screens) or any consumer of it. Triggers: "add a test to the .NET Accelerator", "scaffold a screen for the C# Appium suite", "create a Playwright page object for X in Accelerator". Not for a suite outside the Accelerator (`page-object-design`, `ui-test-author/playwright`).
---

# Accelerator Conventions

The Accelerator is a C# / .NET 10 test automation framework (8/9 supported — match the repo's TFM) with separate projects for `AppiumTests`, `PlaywrightTests`, `ApiTests`, and `TestCore`. It uses a JSON-driven screen pattern, NUnit, Allure for reporting, BrowserStack for cloud execution, and a two-agent Claude Code workflow (Opus planner + Sonnet implementer). Its Playwright version is the one in the **Versions** table of `qa/dotnet/skills/ui-test-author/playwright/SKILL.md`; this skill pins nothing.

This skill encodes the conventions that distinguish "Accelerator code" from generic test automation.

## When to use

- The user is adding or modifying code inside the Accelerator repo
- The user is consuming Accelerator from another project and asks how to wire it up
- The user wants to know whether a piece of code follows Accelerator conventions

## When NOT to use

- The user wants generic Playwright / Appium / RestSharp tutorials → use the generic skills
- The user is starting a brand-new automation framework from scratch (Accelerator might be the wrong choice)

## Project layout

```
Accelerator/
├── TestCore/                  # shared abstractions, helpers, base classes
│   ├── Configuration/         # env config, BrowserStack creds, run options
│   ├── Reporting/             # Allure attachments, step decorators
│   ├── Screens/               # JSON loader, screen base class
│   └── Waits/                 # explicit wait helpers
├── ApiTests/                  # RestSharp-based API tests
│   ├── Clients/               # typed API clients (one per service)
│   ├── Builders/              # test data builders
│   └── Tests/                 # grouped by service / feature
├── PlaywrightTests/           # Web UI tests
│   ├── Pages/                 # page objects, one per screen, JSON-driven
│   ├── ScreenDefinitions/     # *.screen.json files — selectors + metadata
│   └── Tests/                 # grouped by feature
├── AppiumTests/               # Mobile tests
│   ├── Screens/               # screen objects, JSON-driven
│   ├── ScreenDefinitions/     # *.screen.json files
│   └── Tests/                 # grouped by feature
└── .claude/
    ├── commands/              # planner + implementer slash commands
    └── settings.json
```

## Conventions

### Screen / Page object pattern

Page and screen objects are **JSON-driven**. Selectors live in `*.screen.json` files, not in code. The C# class reads its selectors from the JSON at construction time.

Why: changing a selector doesn't recompile. The same JSON can drive both Playwright (web) and Appium (mobile) when the screen exists in both contexts.

**Screen JSON example** (`LoginScreen.screen.json`):

```json
{
  "name": "LoginScreen",
  "platforms": {
    "web": {
      "emailInput": "[data-testid='Login.Email']",
      "passwordInput": "[data-testid='Login.Password']",
      "signInButton": "[data-testid='Login.Submit']",
      "errorMessage": "[data-testid='Login.Error']"
    },
    "ios": {
      "emailInput": "//XCUIElementTypeTextField[@name='email']",
      "passwordInput": "//XCUIElementTypeSecureTextField[@name='password']",
      "signInButton": "//XCUIElementTypeButton[@name='Sign in']"
    },
    "android": {
      "emailInput": "//*[@resource-id='com.app:id/email']",
      "passwordInput": "//*[@resource-id='com.app:id/password']",
      "signInButton": "//*[@resource-id='com.app:id/sign_in']"
    }
  }
}
```

**Page class example** (web, Playwright). `PageBase.Locator(key)` turns the JSON key into
`Page.Locator(Selector(key))` and throws, naming the screen and the key, when the key is missing. Every action
goes through an `ILocator`, so it auto-waits and is strict; the page-level selector methods
(`Page.FillAsync(selector)`, `Page.ClickAsync(selector)`, `Page.InnerTextAsync(selector)`) are discouraged by
Playwright and are not used. State a test asserts on is exposed as an `ILocator`, never a `string` read once.

```csharp
public sealed class LoginPage : PageBase
{
    private readonly ILocator _email;
    private readonly ILocator _password;
    private readonly ILocator _signIn;

    public LoginPage(IPage page) : base(page, "LoginScreen")
    {
        _email = Locator("emailInput");
        _password = Locator("passwordInput");
        _signIn = Locator("signInButton");
        ErrorMessage = Locator("errorMessage").Describe("Sign-in error");
    }

    public ILocator ErrorMessage { get; }

    public async Task GoToAsync() => await Page.GotoAsync("/login");

    [AllureStep("Sign in")]
    public async Task SignInAsync(User user)
    {
        await _email.FillAsync(user.Email);
        await _password.FillAsync(user.Password);
        await _signIn.ClickAsync();
    }
}
```

Rules:
- **No literal selectors in page methods.** Always go through `Locator("key")`; locators are built once, in
  the constructor.
- **Actions run on an `ILocator`**, never on the page-level selector API; anything a test asserts is returned as
  an `ILocator` so the assertion is web-first.
- **Method names describe user intent**, not mechanics. `SignInAsync`, not `ClickSignInButton`.
- **One page object per screen.** Composite flows live in test code or in flow helpers, not in page objects.
- **No assertions inside page objects.** They expose state; tests assert.
- **Locators in JSON are `data-testid`-first for web**, PascalCase dot-separated (`Login.Submit`) — the format
  the dev team's `fe-*` agents generate.

### Test structure

```csharp
[AllureSuite("Authentication")]
[AllureFeature("Login")]
public sealed class LoginTests : BaseTest
{
    private LoginPage _loginPage = null!;

    [SetUp]
    public void CreatePages() => _loginPage = new LoginPage(Page);

    [Test]
    [AllureStory("Successful login")]
    public async Task Should_RedirectToTheDashboard_When_CredentialsAreValid()
    {
        var user = UserBuilder.AValidUser().Build();

        await _loginPage.GoToAsync();
        await _loginPage.SignInAsync(user);

        await Expect(Page).ToHaveURLAsync(new Regex("/dashboard$"));
    }

    [Test]
    [AllureStory("Rejected login")]
    public async Task Should_ShowAnError_When_ThePasswordIsWrong()
    {
        var user = UserBuilder.AValidUser().WithPassword($"Wrong-{Guid.NewGuid():N}").Build();

        await _loginPage.GoToAsync();
        await _loginPage.SignInAsync(user);

        await Expect(_loginPage.ErrorMessage).ToHaveTextAsync("Invalid email or password");
    }
}
```

- **`TestCore`'s Playwright base is `BaseTest`** from `qa/dotnet/skills/ui-test-author/playwright`
  (`assets/BaseTest.cs`): `BASE_URL`, failure evidence, `ParallelScope.Self`. Page objects are built in the
  test class's own `[SetUp]`; tests never call a `Page` method directly.
- **`ToHaveURLAsync(string)` is an exact match** of the whole URL after `BaseURL` resolution, so a glob such as
  `"**/dashboard"` never matches. Match part of the URL with a `Regex` (`new Regex("/dashboard$")`); a glob
  belongs in `WaitForURLAsync`.

Rules:
- Test class per feature or screen, not per AC
- Test name reads `Should_<outcome>_When_<condition>`
- Three-section body: Arrange / Act / Assert — single blank line between, no comments needed
- Test data via builders (`UserBuilder.AValidUser().Build()`), never inline literals
- One logical assertion per test

### Test data builders

Every domain object gets a builder. Builders:

- Live in `*Tests/Builders/`
- Use the `A<Name>` / `An<Name>` naming for the fluent entry: `UserBuilder.AValidUser()`, `OrderBuilder.AnOrderWith(...)`
- Provide sensible defaults — calling `.Build()` with no chained methods produces a valid object
- Return `this` from each `With*` method for fluent chaining; `Build()` returns an immutable record

```csharp
public sealed class UserBuilder
{
    private string _email = $"user-{Guid.NewGuid():N}@test.local";
    private string _password = "Valid123!";
    private int _yearsActive = 1;

    public static UserBuilder AValidUser() => new();

    public UserBuilder WithEmail(string email)
    {
        _email = email;
        return this;
    }

    public UserBuilder WithPassword(string password)
    {
        _password = password;
        return this;
    }

    public UserBuilder WithYearsActive(int years)
    {
        _yearsActive = years;
        return this;
    }

    public User Build() => new(_email, _password, _yearsActive);
}
```

### Waits

- **Never** use `Thread.Sleep`, `Task.Delay`, or `await page.WaitForTimeoutAsync(...)` in test code
- Use Playwright's auto-waiting (`ClickAsync`, `FillAsync`, `Expect(...).ToBeVisibleAsync()`)
- For Appium, use the helpers in `TestCore.Waits` — `WaitUntilVisible`, `WaitUntilStable`
- If you need a wait that doesn't exist, add it to `TestCore.Waits`, don't inline it

### Allure reporting

- Decorate every test with at least `[AllureSuite]`, `[AllureFeature]`, `[AllureStory]` (on the class or the test)
- Web failure evidence (trace, video, full-page screenshot) comes from `BaseTest`'s `[TearDown]` into
  `<WorkDirectory>/playwright-artifacts/`, attached to NUnit and Allure — no second hook for the same evidence
  (`qa/dotnet/skills/evidence-capture`)
- Use `[AllureStep]` on page object methods so steps appear in the Allure tree

### API tests

- One typed client per service in `ApiTests/Clients/`
- Clients return strongly typed responses, not `IRestResponse`
- Test data via builders, same convention as UI
- Contract tests (Pact) run before integration tests in the pipeline

### Configuration & environments

- All config lives in `appsettings.json` + per-env overrides (`appsettings.staging.json`)
- BrowserStack creds, base URLs, and feature flags come from env vars
- Never commit `.env` files; commit `.env.example` only

### Claude Code workflow

The Accelerator uses a two-agent pattern:

- **Planner** (Opus): reads the task, produces a numbered plan with files to create/modify and a verification step. Does not write code.
- **Implementer** (Sonnet): executes the plan, one step at a time. After each step, runs the relevant tests.

Slash commands:
- `/plan <task>` — invokes the planner
- `/implement` — invokes the implementer against the last plan
- `/review` — invokes a reviewer pass against the current branch

When rate-limited on one model, switch to another (Opus → Sonnet → Haiku) — the workflow is designed to degrade gracefully.

## Quality bar (reviewer checklist)

- [ ] No literal selectors in page/screen methods
- [ ] Page actions run on `Locator("key")`, never `Page.FillAsync/ClickAsync/InnerTextAsync(selector)`
- [ ] URL assertions use a `Regex`, never a glob string in `ToHaveURLAsync`
- [ ] No `Thread.Sleep` / `WaitForTimeout` / `Task.Delay` in tests
- [ ] Test name follows `Should_X_When_Y`
- [ ] Test data via a builder
- [ ] Allure decorators present
- [ ] One logical assertion per test
- [ ] Page object methods describe intent, not mechanics
- [ ] Builders provide valid defaults
- [ ] No conditional logic in tests (`if`, `for` driving assertions)
- [ ] Tests are independent and order-agnostic

## Anti-examples

| Anti-example | Why it's wrong | Instead |
|---|---|---|
| `await Page.ClickAsync("button.signin-btn")` in a page object | A selector in code, and a page-level selector method | `_signIn.ClickAsync()` built from `Locator("signInButton")`, the selector in `*.screen.json` |
| `Task<string> GetErrorMessageAsync()` returning `Page.InnerTextAsync(...)`, then `Assert.That(text, ...)` | A one-shot read races the page | expose `ILocator ErrorMessage`; `Expect(_loginPage.ErrorMessage).ToHaveTextAsync(...)` |
| `await Expect(Page).ToHaveURLAsync("**/dashboard")` | The string is an exact match after `BaseURL` resolution — it never passes | `ToHaveURLAsync(new Regex("/dashboard$"))` |
| `await Task.Delay(2000)` | A sleep | auto-wait, web-first assertions, `TestCore.Waits` |
| `public async Task Test_ClickLoginButton()` | Names the mechanics, not the behaviour | `Should_RedirectToTheDashboard_When_CredentialsAreValid` |
| `await _loginPage.SignInAsync(new User("user@test.com", "Password1!", 1))` | Inline test data | `UserBuilder.AValidUser().Build()` |
| `if (env == "staging") { … } else { … }` in a test | Conditional logic in a test | `[TestCase]` / `[TestCaseSource]` or a fixture per environment |
| A `LoginTests` class with its own `Playwright.CreateAsync()` | A second lifecycle beside `BaseTest` | derive from `BaseTest` |
