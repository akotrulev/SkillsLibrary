---
name: ui-tests-selenium
description: Use when scaffolding a .NET Selenium 4 page object or NUnit UI test (BasePage pattern). Triggers "create a Selenium page object for X". Not for Playwright projects (ui-tests-playwright).
---

# QA — Selenium .NET Page Object & Test Generator

Scaffolds Selenium 4 page objects and NUnit UI tests in C# / .NET 8, mirroring the Java sibling skill's structure. Uses a thin `BasePage` with `WebDriverWait`, element accessors that return `IWebElement`, and a `DriverFactory` that manages an `AsyncLocal<IWebDriver>` for parallel-safe runs.

## Stack

- .NET 8, C# 12, nullable reference types enabled
- **Selenium.WebDriver** 4.x — uses built-in **Selenium Manager** (no third-party driver manager needed since 4.6+)
- **NUnit** 4.x with parallel execution at fixture level
- **Allure NUnit** for reporting
- Constructor injection only — no static service locator

## When to use

- New page object under `Pages/`
- Component-level page object scoped to a parent `IWebElement`
- New NUnit UI test under `Tests/`

## When NOT to use

- Selenium Java → `qa/java/skills/ui-test-author/selenium`
- Selenium TypeScript → `qa/typescript/skills/ui-test-author/selenium`
- Playwright .NET → `qa/dotnet/skills/ui-test-author/playwright`
- Appium .NET → `qa/dotnet/skills/ui-test-author/appium`
- Reviewing a page object → `qa/dotnet/skills/ui-test-author/review`
- POM architecture → `qa/dotnet/skills/page-object-design`

## Inputs needed

1. **Page name** (PascalCase, e.g. `Login`, `Product`, `Cart`)
2. **Elements** — name + locator. Prefer `data-test` attributes; fall back to `Id`, then `CssSelector`, then `XPath`.
3. **Actions** — what the test will do on the page and whether it navigates
4. **Landmark element** — used in `IsElementVisible` to confirm the page is loaded
5. **Next pages** — for navigation actions, the destination page class

## Patterns

### `BasePage` (already in the project)

```csharp
public abstract class BasePage
{
    protected readonly IWebDriver Driver;
    private readonly WebDriverWait wait;

    protected BasePage(IWebDriver driver)
    {
        Driver = driver;
        wait = new WebDriverWait(driver, TimeSpan.FromSeconds(10));
    }

    public bool IsElementVisible(By locator) =>
        wait.Until(d => d.FindElements(locator).Any(e => e.Displayed));

    protected IWebElement FindElement(By locator) =>
        wait.Until(d => d.FindElement(locator));

    protected IWebElement FindElement(By locator, IWebElement parent) =>
        wait.Until(_ => parent.FindElement(locator));

    protected IReadOnlyList<IWebElement> FindElements(By locator) =>
        Driver.FindElements(locator);

    protected IReadOnlyList<IWebElement> FindElements(By locator, IWebElement parent) =>
        parent.FindElements(locator);
}
```

Every page inherits `BasePage` and uses its `FindElement(...)` / `FindElements(...)` overloads — never `Driver.FindElement` directly outside `BasePage`.

### Page object — `Pages/{Name}Page.cs`

```csharp
namespace UiTests.Pages;

using OpenQA.Selenium;
using UiTests.Utility;

public sealed class LoginPage : BasePage
{
    public LoginPage(IWebDriver driver) : base(driver) { }

    public void GoToPage() => Driver.Navigate().GoToUrl(EnvConfig.BaseUiUrl);

    public IWebElement Username    => FindElement(By.Id("user-name"));
    public IWebElement Password    => FindElement(By.Id("password"));
    public IWebElement LoginButton => FindElement(By.CssSelector("[data-test='login-button']"));
    public IWebElement ErrorBox    => FindElement(By.ClassName("error-message-container"));

    public ProductPage SuccessfulLogin(string user, string pwd)
    {
        GoToPage();
        Username.SendKeys(user);
        Password.SendKeys(pwd);
        LoginButton.Click();
        return new ProductPage(Driver);
    }
}
```

### Component page object — scoped to a parent `IWebElement`

```csharp
public sealed class ProductCard : BasePage
{
    private readonly IWebElement parent;

    public ProductCard(IWebDriver driver, IWebElement parent) : base(driver)
    {
        this.parent = parent;
    }

    public IWebElement Name  => FindElement(By.CssSelector("[data-test='inventory-item-name']"), parent);
    public IWebElement Price => FindElement(By.CssSelector("[data-test='inventory-item-price']"), parent);
    public IWebElement AddToCart =>
        FindElement(By.CssSelector($"[data-test='add-to-cart-{ToSlug(Name.Text)}']"));

    private static string ToSlug(string s) => s.Replace(" ", "-").ToLowerInvariant();
}
```

The container page exposes the list:

```csharp
public IReadOnlyList<ProductCard> ProductCards =>
    FindElements(By.CssSelector("[data-test='inventory-item']"))
        .Select(el => new ProductCard(Driver, el))
        .ToList();
```

### Sub-flow pages — namespaced sub-folder

Multi-step flows live under `Pages/Checkout/CheckoutInformationPage.cs`, etc. Each step inherits `BasePage` and returns the next step's page object.

### Test — `Tests/{Name}Tests.cs`

```csharp
[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class AuthenticationTests : BaseTest
{
    [Test, Category("Smoke")]
    public void Should_ShowTheCart_When_CredentialsAreValid()
    {
        var login = new LoginPage(Driver);
        login.GoToPage();
        login.Username.SendKeys(TestUsers.First());
        login.Password.SendKeys(TestPassword);
        login.LoginButton.Click();

        var product = new ProductPage(Driver);
        Assert.That(product.NavigationMenu.Cart.Displayed, Is.True,
            "Cart button not visible after login attempt.");
    }
}
```

`BaseTest` owns `IWebDriver Driver` via `DriverFactory`, `[SetUp]` to start, `[TearDown]` to quit, and `[OneTimeSetUp]` to harvest seed data.

## Rules

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `automation.md` and `web-ui.md`. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Conventions

- Pages inherit `BasePage` and pass `driver` to `: base(driver)`; element accessors are expression-bodied properties returning `IWebElement` / `IReadOnlyList<IWebElement>`; page constants and helpers (`ToSlug`) are `private static`.
- Locator order: `data-testid` → `Id` → `CssSelector` → `ClassName` → `XPath`. An XPath fallback is a `missing-testids.md` row, never a code marker.
- Multi-step flows live in a sub-folder (`Pages/Checkout/`); repeating items are components scoped to a parent `IWebElement`.
- Tests inherit `BaseTest`, which provides the per-test `Driver` and shared seed data; `[Category("Smoke")]` enables selective runs.
- `BasePage` sets the default 10 s `WebDriverWait`; conditional waits use `IsElementVisible(By)` or a typed `wait.Until(...)`.
- The driver goes through `DriverFactory.SetDriver()` / `GetDriver()` / `QuitDriver()`, one per test via `AsyncLocal<IWebDriver>`, which is safe for `ParallelScope.Fixtures`; the browser comes from `BROWSER` (`EnvConfig.BrowserType`). Selenium Manager resolves drivers; add `WebDriverManager.Net` only for pinned driver versions.
- Selenium .NET is synchronous; async work mixed in is awaited properly.

## Generation steps

1. Confirm **page name**, **elements + locators**, **actions**, and **next pages** with the user.
2. For each element without `data-test`, flag whether the app team can add one — note as tech debt rather than silently using XPath.
3. Generate `Pages/{Name}Page.cs`:
   - Constructor calls `: base(driver)`
   - One expression-bodied property per element
   - One action method per user-intent action (`void` or next-page return)
   - For repeating items, an `IReadOnlyList<{Component}>` property wrapping each `IWebElement` in a component class
4. If a destination page doesn't exist yet, create a stub or recursively generate it.
5. Generate the test class inheriting `BaseTest`; one `[Test]` per scenario, assertions on user-visible outcomes.
6. Run `dotnet test` — expect 0 failures.

## Handoffs

- POM architecture → `qa/dotnet/skills/page-object-design`
- Test data builders → `qa/dotnet/skills/test-data-builder`
- Reviewing a page object → `qa/dotnet/skills/ui-test-author/review`
- Allure reporting → `qa/reporting/dotnet/skills/test-reports`
