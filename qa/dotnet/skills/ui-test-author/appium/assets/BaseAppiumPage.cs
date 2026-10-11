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
