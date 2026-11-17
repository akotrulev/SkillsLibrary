---
name: ui-tests-selenium
description: Use when scaffolding a .NET Selenium 4 page object or NUnit UI test (BasePage pattern). Triggers "create a Selenium page object for X". Not for Playwright projects (ui-tests-playwright).
---

# QA — Selenium .NET Page Object & Test Generator

Scaffolds Selenium 4 page objects, components and NUnit UI tests in C#, mirroring the Java sibling skill's structure. A thin `BasePage` owns the one `WebDriverWait` and the finders; pages expose intent methods and queries that return values, never an `IWebElement`; repeating rows and design-system widgets are components; a `DriverFactory` keeps an `AsyncLocal<IWebDriver>` for parallel-safe runs.

## Stack

- .NET 10 primary, 8/9 supported: match the project's TFM, never up-level it; nullable reference types enabled
- **Selenium.WebDriver** and **Selenium.Support** 4.x (Selenium Manager resolves drivers since 4.6; `SelectElement` and `WebDriverWait` come from `Selenium.Support`)
- **NUnit** 4.x, `ParallelScope.Self` once on `BaseTest`
- **Allure NUnit** for reporting
- Constructor injection only, no static service locator

## When to use

- A new page object under `Pages/`, a region component (row, card, form) or a control component (dropdown, date picker, grid) under `Components/`
- A new NUnit UI test under `Tests/`

## When NOT to use

- Selenium Java → `qa/java/skills/ui-test-author/selenium`
- Selenium TypeScript → `qa/typescript/skills/ui-test-author/selenium`
- Playwright .NET → `qa/dotnet/skills/ui-test-author/playwright`
- Appium .NET → `qa/dotnet/skills/ui-test-author/appium`
- Reviewing a page object → `qa/dotnet/skills/ui-test-author/review`
- POM architecture → `qa/dotnet/skills/page-object-design`

## Inputs needed

1. **Page name** (PascalCase, e.g. `Login`, `Products`, `Cart`)
2. **Elements**: name and locator, the test id first, then `Id`, `CssSelector`, XPath last
3. **Actions**: what the user does on the page and whether it always lands on another page
4. **Landmark element**: the one element `VerifyPageLoaded()` checks
5. **Widgets and repeating rows**: which elements are design-system controls or rows, and the visible key that identifies a row

## Patterns

### `BasePage` (already in the project)

```csharp
using OpenQA.Selenium;
using OpenQA.Selenium.Support.UI;

namespace UiTests.Pages;

public abstract class BasePage
{
    private static readonly TimeSpan Timeout = TimeSpan.FromSeconds(10);

    protected BasePage(IWebDriver driver) => Driver = driver;

    protected IWebDriver Driver { get; }

    public abstract void VerifyPageLoaded();

    internal static WebDriverWait Wait(IWebDriver driver, string message)
    {
        var wait = new WebDriverWait(driver, Timeout) { Message = message };
        wait.IgnoreExceptionTypes(typeof(NoSuchElementException), typeof(StaleElementReferenceException));
        return wait;
    }

    internal static By TestId(string id) => By.CssSelector($"[data-testid='{id}']");

    protected IWebElement Find(By locator) =>
        Wait(Driver, $"No element found for {locator}").Until(driver => driver.FindElement(locator));

    protected bool IsDisplayed(By locator)
    {
        try
        {
            return Wait(Driver, $"{locator} is not displayed").Until(driver => driver.FindElements(locator).Any(element => element.Displayed));
        }
        catch (WebDriverTimeoutException)
        {
            return false;
        }
    }
}
```

Pages inherit `BasePage` and find through it, never `Driver.FindElement` directly. Components do not inherit it: they use its `Wait` and `TestId` and find inside their own root. `IsDisplayed` is the probe that turns one named exception into `false`; it is the only `catch` a page object holds.

A wait for the app's own busy signal (the loading bar gone, the snackbar gone) is a named wait condition on `BasePage` or the shell component, such as `WaitUntilLoaded()` built on `Wait(...).Until(driver => driver.FindElements(LoadingBar).Count == 0)`, and the action that triggers the load calls it before returning. A test never calls it.

### Page object: `Pages/{Name}Page.cs`

```csharp
using NUnit.Framework;
using OpenQA.Selenium;
using UiTests.Support;

namespace UiTests.Pages;

public sealed class LoginPage : BasePage
{
    private static readonly By Username = TestId("Login.Username");
    private static readonly By Password = TestId("Login.Password");
    private static readonly By Submit = TestId("Login.Submit");
    private static readonly By Error = TestId("Login.Error");

    public LoginPage(IWebDriver driver) : base(driver)
    {
    }

    public override void VerifyPageLoaded() =>
        Assert.That(IsDisplayed(Username), Is.True, "Expected LoginPage but the username field is not displayed");

    public void GoTo() => Driver.Navigate().GoToUrl(new Uri(Env.BaseUrl, "/login"));

    public void SignIn(string user, string password)
    {
        Find(Username).SendKeys(user);
        Find(Password).SendKeys(password);
        Find(Submit).Click();
    }

    public string ErrorText() => Find(Error).Text;
}
```

`SignIn` returns `void` because it does not always land on another page (a wrong password stays here); an action that always navigates returns the destination's page object. Element locators are `private static readonly By`; the page exposes intent methods and queries that return text, a count or a bool.

### Region component: a row picked by its content

```csharp
using OpenQA.Selenium;
using UiTests.Pages;

namespace UiTests.Components;

public sealed class ProductCard
{
    private static readonly By Card = BasePage.TestId("Inventory.Item");
    private static readonly By Name = BasePage.TestId("Inventory.Item.Name");
    private static readonly By Price = BasePage.TestId("Inventory.Item.Price");
    private static readonly By AddToCartButton = BasePage.TestId("Inventory.Item.AddToCart");

    private readonly IWebDriver _driver;
    private readonly string _productName;

    internal ProductCard(IWebDriver driver, string productName)
    {
        _driver = driver;
        _productName = productName;
    }

    public string PriceText() => Root().FindElement(Price).Text;

    public void AddToCart() => Root().FindElement(AddToCartButton).Click();

    private IWebElement Root() =>
        BasePage.Wait(_driver, $"No product card shows {_productName}").Until(driver =>
            driver.FindElements(Card).FirstOrDefault(card => card.FindElement(Name).Text == _productName))!;
}
```

The component holds the row key, never an element, and finds its root again on every call, so a re-rendered list cannot leave it stale. Every child is found inside the root with a static test id; nothing is built from the row's text.

To assert on every row of a result, the grid or list exposes a query returning one column's values (`ColumnValues("Status")` → `IReadOnlyList<string>`); the test asserts `Is.Not.Empty`, then `Is.All.EqualTo(...)` on the whole collection. Never `rows[0]` standing for the result set, never a loop over rows in a test. Where the app's ids embed the row index, the component resolves it from the row's content; the test never passes an index.

### Control component: a `Dropdown` over a native `<select>`

```csharp
using OpenQA.Selenium;
using OpenQA.Selenium.Support.UI;
using UiTests.Pages;

namespace UiTests.Components.Controls;

public sealed class Dropdown
{
    private readonly IWebDriver _driver;
    private readonly By _select;

    public Dropdown(IWebDriver driver, By select)
    {
        _driver = driver;
        _select = select;
    }

    public void Select(string option) => Element().SelectByText(option);

    public string SelectedOption() => Element().SelectedOption.Text;

    private SelectElement Element() =>
        new(BasePage.Wait(_driver, $"No dropdown found for {_select}").Until(driver => driver.FindElement(_select)));
}
```

A custom listbox that only looks like a dropdown is a second class (`Combobox`), never a branch in this one. The Playwright lane's catalogue (`qa/dotnet/skills/ui-test-author/playwright/references/components.md`) lists the other controls and their intent methods; the Selenium form follows the same shape.

### The page that hands them out

```csharp
using NUnit.Framework;
using OpenQA.Selenium;
using UiTests.Components;
using UiTests.Components.Controls;

namespace UiTests.Pages;

public sealed class ProductsPage : BasePage
{
    private static readonly By Heading = TestId("Products.Heading");

    public ProductsPage(IWebDriver driver) : base(driver)
    {
        SortOrder = new Dropdown(driver, TestId("Products.Sort"));
    }

    public Dropdown SortOrder { get; }

    public override void VerifyPageLoaded() =>
        Assert.That(IsDisplayed(Heading), Is.True, "Expected ProductsPage but the heading is not displayed");

    public string HeadingText() => Find(Heading).Text;

    public ProductCard Product(string name) => new(Driver, name);
}
```

### Test: `Tests/{Name}Tests.cs`

```csharp
using Allure.NUnit.Attributes;
using NUnit.Framework;
using UiTests.Pages;
using UiTests.Support;

namespace UiTests.Tests;

[AllureFeature("Login")]
public sealed class LoginTests : BaseTest
{
    private LoginPage _login = null!;
    private ProductsPage _products = null!;

    [SetUp]
    public void OpenLogin()
    {
        _login = new LoginPage(Driver);
        _products = new ProductsPage(Driver);
        _login.GoTo();
        _login.VerifyPageLoaded();
    }

    [Test, Category("smoke")]
    public void Should_ShowProducts_When_CredentialsAreValid()
    {
        _login.SignIn(Env.Required("E2E_USER"), Env.Required("E2E_PASSWORD"));

        Assert.That(_products.HeadingText(), Is.EqualTo("Products"), "heading after sign-in");
    }

    [Test, Category("regression")]
    public void Should_ShowInvalidCredentialsError_When_PasswordIsWrong()
    {
        _login.SignIn(Env.Required("E2E_USER"), "wrong-password");

        Assert.That(_login.ErrorText(), Is.EqualTo("Invalid username or password"), "sign-in error");
    }
}
```

`BaseTest` carries `[Parallelizable(ParallelScope.Self)]`, starts the driver from `DriverFactory` in `[SetUp]`, keeps failure evidence and quits it in `[TearDown]`. Reaching the page happens in the class's `[SetUp]`; a record a test needs is created there through the API and deleted in `[TearDown]`.

## Rules

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `automation.md`, `page-objects.md` and `web-ui.md`. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Conventions

- Pages inherit `BasePage` and pass `driver` to `: base(driver)`; locators are `private static readonly By`; pages return values from queries and never expose an `IWebElement`.
- Locator order: test id → `Id` → `CssSelector` → `ClassName` → XPath. A fallback is a `missing-testids.md` row, never a code marker.
- Components live in `Components/` (region) and `Components/Controls/` (controls) and never inherit `BasePage`. A row component holds its key and re-resolves its root; a control takes its root locator.
- Multi-step journeys are pages in a sub-folder (`Pages/Checkout/`), each returning the next step; a setup that crosses pages is a `<Something>Flow` class taking its pages in the constructor.
- The one wait is `BasePage.Wait` (10 s `WebDriverWait`, implicit wait zero); no sleeps, no JavaScript `click()`.
- The driver goes through `DriverFactory.SetDriver()` / `GetDriver()` / `QuitDriver()`, one per test via `AsyncLocal<IWebDriver>`; the browser comes from `BROWSER`, the base URL from `BASE_URL` through `Env`. Add `WebDriverManager.Net` only for pinned driver versions.
- Selenium .NET is synchronous: page methods are sync; async work mixed in (an API seed) is awaited in an `async Task` setup.

## Generation steps

1. Confirm the page name, elements and locators, actions, landmark, widgets and rows with the user.
2. For each element without a test id, add a `missing-testids.md` row rather than silently using XPath.
3. Generate `Pages/{Name}Page.cs`: `: base(driver)`, one `private static readonly By` per element, `VerifyPageLoaded()` on the landmark, one intent method per user action and one query per value a test reads.
4. Map each design-system widget to a control in `Components/Controls/` (reuse the existing one; write a missing one in the `Dropdown` shape) and each repeating row or card to a region component keyed by its visible content. The page exposes controls as properties and hands out rows by key.
5. If a destination page does not exist yet, create a stub or generate it.
6. Generate the test class inheriting `BaseTest`: pages built and the page reached in `[SetUp]`, one linear `[Test]` per scenario asserting a returned value.
7. Run `dotnet test`: expect 0 failures.

## Handoffs

- POM architecture → `qa/dotnet/skills/page-object-design`
- Test data builders → `qa/dotnet/skills/test-data-builder`
- Reviewing a page object → `qa/dotnet/skills/ui-test-author/review`
- Allure reporting → `qa/reporting/dotnet/skills/test-reports`
