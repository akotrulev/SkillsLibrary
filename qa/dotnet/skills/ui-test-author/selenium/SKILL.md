---
name: qa-ui-test-author-selenium-dotnet
description: Use when the user asks to scaffold a C# / .NET 8 + Selenium 4 page object or NUnit UI test, following the BasePage / DriverFactory / NUnit pattern. Triggers: "create a Selenium page object for X in C#", "add a .NET page for screen Y", "write a Selenium NUnit test for Z".
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
- Reviewing a page object → `qa/dotnet/skills/ui-test-author/reviewer`
- POM architecture → `qa/dotnet/skills/page-object-architect`

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
    public void SuccessfulLogin()
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

### Page object rules
- Inherit `BasePage`; pass `driver` to `: base(driver)`
- Element accessors are expression-bodied properties returning `IWebElement` / `IReadOnlyList<IWebElement>`
- **No `PageFactory` / `[FindsBy]` attributes** — explicit `FindElement(By)` calls only
- **Locator preference:** `data-test` → `Id` → `CssSelector` → `ClassName` → `XPath` (last resort, add a `// TODO`)
- One class per page; multi-step flows live in a sub-folder
- Reusable components take a parent `IWebElement` and use the parent-scoped overloads
- Navigation methods return the next page object; same-page actions return `void`
- Page constants and helpers (e.g. `ToSlug`) are `private static`

### Test rules
- Inherit `BaseTest` — provides the per-test `Driver` and shared seed data
- Test names: `SuccessfulLogin`, `CartShowsAddedProduct`, `LoginRejectsLockedUser`
- Use `[Category("Smoke")]` to enable selective runs
- Assertions live in the test, **never** inside page methods
- Use `Assert.That(value, Is.X, "message")` — every failure must explain itself
- Use `Assert.Multiple(() => { ... })` when verifying multiple fields after one user action

### Waits
- Default 10s wait set in `BasePage` via `WebDriverWait`
- For conditional waits, use `IsElementVisible(By)` or a typed `wait.Until(...)`
- **No `Thread.Sleep` / `Task.Delay` for synchronization** — only `WebDriverWait`

### Driver lifecycle
- Always go through `DriverFactory.SetDriver()` / `GetDriver()` / `QuitDriver()` — never `new ChromeDriver()` in a test
- Browser configured via env var `BROWSER` (or appsettings) — `EnvConfig.BrowserType`
- One driver per test via `AsyncLocal<IWebDriver>` — safe for NUnit `Parallelizable(ParallelScope.Fixtures)`
- Selenium Manager (built into Selenium 4.6+) auto-resolves browser drivers — do not add `WebDriverManager.Net` unless you need pinned versions

### What NOT to do

- No `Thread.Sleep` — use `WebDriverWait`
- No `Driver.FindElement(...)` in a page outside `BasePage`
- No assertions inside page methods
- No `PageFactory` / `[FindsBy]` attributes — explicit `FindElement(By)` only
- No raw XPath when a `data-test` attribute could be added to the app
- No shared mutable state on page objects
- No business logic in page objects (e.g. computing discounts)
- No hardcoded URLs or credentials — use `EnvConfig` / `IConfiguration`
- No `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` — Selenium .NET is sync; if you mix async work, use `await` properly

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

- POM architecture → `qa/dotnet/skills/page-object-architect`
- Test data builders → `qa/dotnet/skills/test-data-builder`
- Reviewing a page object → `qa/dotnet/skills/ui-test-author/reviewer`
- Allure reporting → `qa/reporting/dotnet/skills/allure-reporting`
