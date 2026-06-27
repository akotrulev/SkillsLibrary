---
name: qa-accelerator-conventions-dotnet
description: Use when working in the C# / .NET 8 Accelerator test automation framework (NUnit + RestSharp + Playwright + Appium, JSON-driven screens) or any consumer of it. Triggers: "add a test to the .NET Accelerator", "scaffold a screen for the C# Appium suite", "create a Playwright page object for X in Accelerator".
---

# Accelerator Conventions

The Accelerator is a C# / .NET 8 test automation framework with separate projects for `AppiumTests`, `PlaywrightTests`, `ApiTests`, and `TestCore`. It uses a JSON-driven screen pattern, NUnit, Allure for reporting, BrowserStack for cloud execution, and a two-agent Claude Code workflow (Opus planner + Sonnet implementer).

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
      "emailInput": "[data-testid='email']",
      "passwordInput": "[data-testid='password']",
      "signInButton": "[data-testid='sign-in']",
      "errorMessage": "[data-testid='login-error']"
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

**Page class example**:

```csharp
public sealed class LoginPage : PageBase
{
    public LoginPage(IPage page) : base(page, "LoginScreen") { }

    public async Task SignInAsync(string email, string password)
    {
        await Page.FillAsync(Selector("emailInput"), email);
        await Page.FillAsync(Selector("passwordInput"), password);
        await Page.ClickAsync(Selector("signInButton"));
    }

    public Task<string> GetErrorMessageAsync() =>
        Page.InnerTextAsync(Selector("errorMessage"));
}
```

Rules:
- **No literal selectors in page methods.** Always go through `Selector("key")`.
- **Method names describe user intent**, not mechanics. `SignInAsync`, not `ClickSignInButton`.
- **One page object per screen.** Composite flows live in test code or in flow helpers, not in page objects.
- **No assertions inside page objects.** They expose state; tests assert.

### Test structure

```csharp
[TestFixture]
[AllureSuite("Authentication")]
public sealed class LoginTests : PlaywrightTestBase
{
    [Test]
    [AllureFeature("Login")]
    [AllureStory("Successful login")]
    public async Task Should_Redirect_To_Dashboard_When_Credentials_Valid()
    {
        var user = UserBuilder.AValidUser().Build();
        var login = new LoginPage(Page);

        await login.GoToAsync();
        await login.SignInAsync(user.Email, user.Password);

        await Expect(Page).ToHaveURLAsync("**/dashboard");
    }
}
```

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
- Are immutable internally — each `With*` method returns a new builder

```csharp
public sealed class UserBuilder
{
    private string _email = $"user-{Guid.NewGuid():N}@test.local";
    private string _password = "Valid123!";
    private int _yearsActive = 1;

    public static UserBuilder AValidUser() => new();
    public UserBuilder WithEmail(string email) { _email = email; return this; }
    public UserBuilder WithYearsActive(int years) { _yearsActive = years; return this; }
    public User Build() => new(_email, _password, _yearsActive);
}
```

### Waits

- **Never** use `Thread.Sleep`, `Task.Delay`, or `await page.WaitForTimeoutAsync(...)` in test code
- Use Playwright's auto-waiting (`ClickAsync`, `FillAsync`, `Expect(...).ToBeVisibleAsync()`)
- For Appium, use the helpers in `TestCore.Waits` — `WaitUntilVisible`, `WaitUntilStable`
- If you need a wait that doesn't exist, add it to `TestCore.Waits`, don't inline it

### Allure reporting

- Decorate every test with at least `[AllureSuite]`, `[AllureFeature]`, `[AllureStory]`
- Attach evidence on failure: screenshot, page source, network HAR
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

```csharp
// BAD: literal selector in page object
public async Task SignInAsync() {
    await Page.ClickAsync("button.signin-btn");  // ❌ selector in code
}

// BAD: sleep
await Task.Delay(2000);  // ❌

// BAD: implementation-named test
public async Task Test_ClickLoginButton() { ... }  // ❌

// BAD: inline test data
await login.SignInAsync("user@test.com", "Password1!");  // ❌ use a builder

// BAD: conditional in test
if (env == "staging") { ... } else { ... }  // ❌ use parameterized tests or fixtures
```
