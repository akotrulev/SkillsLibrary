# Deep-dive details — `qa-ui-test-writer-appium-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Patterns

### `BaseAppiumPage` (already in the project)

See [`assets/BaseAppiumPage.cs`](assets/BaseAppiumPage.cs) for the full file. Every page extends it and goes through the inherited finders — never `Driver.FindElement(...)` directly.

```csharp
using OpenQA.Selenium;
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Support.UI;

namespace AppiumTests.Pages;

public abstract class BaseAppiumPage
{
    protected AppiumDriver Driver { get; }
    private readonly WebDriverWait _wait;

    protected BaseAppiumPage(AppiumDriver driver)
    {
        Driver = driver;
        _wait = new WebDriverWait(driver, TimeSpan.FromSeconds(10));
    }

    /// <summary>Asserts the landmark element resolves and is displayed.</summary>
    public abstract void VerifyPageLoaded();

    protected AppiumElement FindByAccessibilityId(string id) =>
        (AppiumElement)_wait.Until(ExpectedConditions.ElementIsVisible(AppiumBy.AccessibilityId(id)));

    protected AppiumElement FindById(string id) =>
        (AppiumElement)_wait.Until(ExpectedConditions.ElementIsVisible(By.Id(id)));

    protected AppiumElement FindByXPath(string xpath) =>
        (AppiumElement)_wait.Until(ExpectedConditions.ElementIsVisible(By.XPath(xpath)));

    protected IReadOnlyList<AppiumElement> FindAllByAccessibilityId(string id) =>
        Driver.FindElements(AppiumBy.AccessibilityId(id)).Cast<AppiumElement>().ToList();

    protected bool IsElementVisible(By locator)
    {
        try { return _wait.Until(ExpectedConditions.ElementIsVisible(locator)).Displayed; }
        catch (WebDriverTimeoutException) { return false; }
    }
}
```

> `ExpectedConditions` lives in `DotNetSeleniumExtras.WaitHelpers` (add the NuGet package) — or hand-roll the `Func<IWebDriver, T>` predicates if you prefer no extra dependency. The `DefaultWait<T>` variant (below, under **Explicit waits**) avoids the package entirely.

### Page object — `AppiumTests/Pages/{Name}Page.cs`

```csharp
using NUnit.Framework;
using OpenQA.Selenium.Appium;

namespace AppiumTests.Pages;

public class LoginPage : BaseAppiumPage
{
    private const string EmailFieldId = "login-email";
    private const string PasswordFieldId = "login-password";
    private const string SubmitButtonId = "login-submit";

    public LoginPage(AppiumDriver driver) : base(driver) { }

    public override void VerifyPageLoaded()
    {
        var emailField = FindByAccessibilityId(EmailFieldId);
        Assert.That(emailField.Displayed, Is.True,
            $"Expected {nameof(LoginPage)} to be visible but the email field was not found.");
    }

    public HomePage Login(string email, string password)
    {
        var emailField = FindByAccessibilityId(EmailFieldId);
        emailField.Clear();
        emailField.SendKeys(email);

        var passwordField = FindByAccessibilityId(PasswordFieldId);
        passwordField.Clear();
        passwordField.SendKeys(password);

        FindByAccessibilityId(SubmitButtonId).Click();
        return new HomePage(Driver);
    }
}
```

### Component page object — scoped to a parent `AppiumElement`

For repeating elements (list rows, cards, swipeable cells), create a component class that takes the parent `AppiumElement` in its constructor and queries inside it.

```csharp
public class OrderRow : BaseAppiumPage
{
    private readonly AppiumElement _parent;

    public OrderRow(AppiumDriver driver, AppiumElement parent) : base(driver)
    {
        _parent = parent;
    }

    public AppiumElement Title()  => (AppiumElement)_parent.FindElement(AppiumBy.AccessibilityId("order-title"));
    public AppiumElement Amount() => (AppiumElement)_parent.FindElement(AppiumBy.AccessibilityId("order-amount"));

    public override void VerifyPageLoaded() =>
        Assert.That(Title().Displayed, Is.True, "Order row title not visible.");

    public OrderDetailsPage Open()
    {
        _parent.Click();
        return new OrderDetailsPage(Driver);
    }
}
```

The container page exposes the rows:

```csharp
public IReadOnlyList<OrderRow> OrderRows() =>
    FindAllByAccessibilityId("order-row")
        .Select(el => new OrderRow(Driver, el))
        .ToList();
```

### Sub-flow pages — namespaced sub-namespace

Multi-step flows (onboarding, checkout) live under `AppiumTests/Pages/Onboarding/{WelcomePage,ConsentPage,ProfilePage}.cs` with namespace `AppiumTests.Pages.Onboarding`. Each extends `BaseAppiumPage` and returns the next step's page object.
