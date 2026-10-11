# Deep-dive details — `qa-dotnet:ui-tests-appium`

Sections moved out of SKILL.md for on-demand loading. Every block below is a copy of a file in `assets/`; when they differ, the asset wins.

## Patterns

### `BaseAppiumPage` — [`assets/BaseAppiumPage.cs`](../assets/BaseAppiumPage.cs)

Every page extends it and goes through the inherited finders, never `Driver.FindElement(...)`. `WebDriverWait` and its `IgnoreExceptionTypes` come from `Selenium.Support`, so the hand-rolled predicates need no `DotNetSeleniumExtras`.

```csharp
using OpenQA.Selenium;
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.iOS;
using OpenQA.Selenium.Support.UI;

namespace AppiumTests.Pages;

public abstract class BaseAppiumPage
{
    private static readonly TimeSpan Timeout = TimeSpan.FromSeconds(10);

    protected AppiumDriver Driver { get; }

    protected BaseAppiumPage(AppiumDriver driver) => Driver = driver;

    public abstract void VerifyPageLoaded();

    internal static By TestId(AppiumDriver driver, string id) =>
        driver is IOSDriver ? MobileBy.AccessibilityId(id) : MobileBy.Id(id);

    internal static WebDriverWait Wait(AppiumDriver driver, string message)
    {
        var wait = new WebDriverWait(driver, Timeout) { Message = message };
        wait.IgnoreExceptionTypes(typeof(NoSuchElementException), typeof(StaleElementReferenceException));
        return wait;
    }

    protected AppiumElement ByTestId(string id) => Present(TestId(Driver, id));

    protected AppiumElement ByContentDescription(string description) => Present(MobileBy.AccessibilityId(description));

    protected AppiumElement ByIosPredicate(string predicate) => Present(MobileBy.IosNSPredicate(predicate));

    protected AppiumElement ByIosClassChain(string classChain) => Present(MobileBy.IosClassChain(classChain));

    protected AppiumElement ByAndroidUiAutomator(string selector) => Present(MobileBy.AndroidUIAutomator(selector));

    protected AppiumElement ByXPath(string xpath) => Present(By.XPath(xpath));

    protected AppiumElement ByCss(string selector) => Present(By.CssSelector(selector));

    protected void InWebView(Action webActions)
    {
        var native = Driver.Context;
        var webView = Wait(Driver, "No WEBVIEW context appeared")
            .Until(_ => Driver.Contexts.FirstOrDefault(context => context.StartsWith("WEBVIEW")))!;
        Driver.Context = webView;
        try
        {
            webActions();
        }
        finally
        {
            Driver.Context = native;
        }
    }

    protected bool IsTestIdVisible(string id)
    {
        var locator = TestId(Driver, id);
        try
        {
            Wait(Driver, $"{locator} is not displayed").Until(_ => Driver.FindElements(locator).FirstOrDefault(e => e.Displayed));
            return true;
        }
        catch (WebDriverTimeoutException)
        {
            return false;
        }
    }

    private AppiumElement Present(By locator) =>
        Wait(Driver, $"No element found for {locator}").Until(_ => Driver.FindElements(locator).FirstOrDefault())!;
}
```

### Page object — [`assets/LoginPage.cs`](../assets/LoginPage.cs)

```csharp
using NUnit.Framework;
using OpenQA.Selenium.Appium;

namespace AppiumTests.Pages;

public sealed class LoginPage : BaseAppiumPage
{
    private const string EmailId = "Login.Email";
    private const string PasswordId = "Login.Password";
    private const string SubmitId = "Login.Submit";

    public LoginPage(AppiumDriver driver) : base(driver)
    {
    }

    public override void VerifyPageLoaded() =>
        Assert.That(IsTestIdVisible(EmailId), Is.True, "Expected LoginPage to be visible but the email field was not found");

    public OrdersPage SignIn(string email, string password)
    {
        Type(ByTestId(EmailId), email);
        Type(ByTestId(PasswordId), password);
        ByTestId(SubmitId).Click();
        return new OrdersPage(Driver);
    }

    private static void Type(AppiumElement field, string text)
    {
        field.Clear();
        field.SendKeys(text);
    }
}
```

`page_template.cs` is the same shape with placeholder ids; copy it for a new screen.

### Component — [`assets/OrderRow.cs`](../assets/OrderRow.cs)

The component keeps the row key and finds the row again on every call. The host page hands it out:

```csharp
using OpenQA.Selenium.Appium;

namespace AppiumTests.Pages;

public sealed class OrderRow
{
    private const string RowId = "OrderRow";
    private const string NumberId = "OrderRow.Number";
    private const string TitleId = "OrderRow.Title";
    private const string StatusId = "OrderRow.Status";

    private readonly AppiumDriver _driver;
    private readonly string _orderNumber;

    internal OrderRow(AppiumDriver driver, string orderNumber)
    {
        _driver = driver;
        _orderNumber = orderNumber;
    }

    public string Title() => TextOf(TitleId);

    public string Status() => TextOf(StatusId);

    public void Open() => Root().Click();

    private string TextOf(string id) => Root().FindElement(BaseAppiumPage.TestId(_driver, id)).Text;

    private AppiumElement Root() =>
        BaseAppiumPage.Wait(_driver, $"No {RowId} shows order {_orderNumber}").Until(_ =>
            _driver.FindElements(BaseAppiumPage.TestId(_driver, RowId))
                .FirstOrDefault(row => row.FindElement(BaseAppiumPage.TestId(_driver, NumberId)).Text == _orderNumber))!;
}
```

```csharp
using NUnit.Framework;
using OpenQA.Selenium.Appium;

namespace AppiumTests.Pages;

public sealed class OrdersPage : BaseAppiumPage
{
    private const string ListId = "Orders.List";

    public OrdersPage(AppiumDriver driver) : base(driver)
    {
    }

    public override void VerifyPageLoaded() =>
        Assert.That(IsTestIdVisible(ListId), Is.True, "Expected OrdersPage to be visible but the orders list was not found");

    public OrderRow Row(string orderNumber) => new(Driver, orderNumber);
}
```

### Sub-flow pages

Multi-step flows (onboarding, checkout) live under `AppiumTests/Pages/Onboarding/` with namespace `AppiumTests.Pages.Onboarding`. Each extends `BaseAppiumPage` and returns the next step's page object.

## Gestures — [`assets/GestureExtensions.cs`](../assets/GestureExtensions.cs)

```csharp
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Interactions;

namespace AppiumTests.Support;

public static class GestureExtensions
{
    public static bool ScrollGesture(this AppiumDriver driver, AppiumElement container, string direction = "down", double percent = 0.75) =>
        (bool)driver.ExecuteScript("mobile: scrollGesture", new Dictionary<string, object>
        {
            ["elementId"] = container.Id,
            ["direction"] = direction,
            ["percent"] = percent,
        });

    public static void LongPress(this AppiumDriver driver, AppiumElement element, int durationMs = 1500) =>
        driver.ExecuteScript("mobile: longClickGesture", new Dictionary<string, object>
        {
            ["elementId"] = element.Id,
            ["duration"] = durationMs,
        });

    public static void Swipe(this AppiumDriver driver, int startX, int startY, int endX, int endY)
    {
        var finger = new PointerInputDevice(PointerKind.Touch, "finger");
        var swipe = new ActionSequence(finger);
        swipe.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport, startX, startY, TimeSpan.Zero));
        swipe.AddAction(finger.CreatePointerDown(MouseButton.Touch));
        swipe.AddAction(finger.CreatePause(TimeSpan.FromMilliseconds(200)));
        swipe.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport, endX, endY, TimeSpan.FromMilliseconds(600)));
        swipe.AddAction(finger.CreatePointerUp(MouseButton.Touch));
        driver.PerformActions(new List<ActionSequence> { swipe });
    }

    public static void Tap(this AppiumDriver driver, AppiumElement element)
    {
        var area = element.Rect;
        var finger = new PointerInputDevice(PointerKind.Touch, "finger");
        var tap = new ActionSequence(finger);
        tap.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport, area.X + area.Width / 2, area.Y + area.Height / 2, TimeSpan.Zero));
        tap.AddAction(finger.CreatePointerDown(MouseButton.Touch));
        tap.AddAction(finger.CreatePointerUp(MouseButton.Touch));
        driver.PerformActions(new List<ActionSequence> { tap });
    }
}
```

- A page method wraps the gesture (`SwipeToNextPhoto`), and takes the geometry from `AppiumElement.Rect`. On iOS coordinates are points, not screenshot pixels.
- `mobile: scrollGesture` takes `elementId`, `direction` and `percent`, and returns `true` while more content can scroll. Wrap a repeat of it in `BaseAppiumPage.Wait(...)` to reach an element.

## WebView

A hybrid app exposes more than one context. `BaseAppiumPage.InWebView` (in the base page above) waits for the web context, switches, acts and always switches back in a `finally`, so a failed web step cannot leave the fixture's driver in `WEBVIEW`. A page action is:

```csharp
public void AcceptCookies() => InWebView(() => ByCss("#cookie-accept").Click());
```

- The helper and `ByCss` live in the base page, so a page never calls `Driver.FindElement(By.CssSelector(...))`.
- `Driver.Contexts` is not populated at once: the WebView is created asynchronously, hence the wait.
- UiAutomator2's `mobile: getContexts` lists each WebView with its pages' titles and URLs, for an app with more than one.
