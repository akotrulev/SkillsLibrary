using OpenQA.Selenium;
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Support.UI;

namespace AppiumTests.Pages;

/// <summary>
/// Base class for every Appium page object. Owns the driver and a 10s
/// <see cref="WebDriverWait"/>, and funnels all element access through
/// accessibility-id-first finders so locators never leak into actions.
/// </summary>
public abstract class BaseAppiumPage
{
    protected AppiumDriver Driver { get; }
    private readonly WebDriverWait _wait;

    protected BaseAppiumPage(AppiumDriver driver)
    {
        Driver = driver;
        _wait = new WebDriverWait(driver, TimeSpan.FromSeconds(10));
    }

    /// <summary>Asserts this screen is currently visible via its landmark element.</summary>
    public abstract void VerifyPageLoaded();

    // ── Finders (priority: AccessibilityId → Id → XPath) ─────────────────────

    protected AppiumElement FindByAccessibilityId(string id) =>
        WaitVisible(AppiumBy.AccessibilityId(id));

    protected AppiumElement FindById(string id) =>
        WaitVisible(By.Id(id));

    protected AppiumElement FindByXPath(string xpath) =>
        WaitVisible(By.XPath(xpath));

    protected IReadOnlyList<AppiumElement> FindAllByAccessibilityId(string id) =>
        Driver.FindElements(AppiumBy.AccessibilityId(id)).Cast<AppiumElement>().ToList();

    /// <summary>True if the element becomes visible within the wait window; false on timeout.</summary>
    protected bool IsElementVisible(By locator)
    {
        try { return WaitVisible(locator).Displayed; }
        catch (WebDriverTimeoutException) { return false; }
    }

    // ── Internal wait (no DotNetSeleniumExtras dependency) ───────────────────

    private AppiumElement WaitVisible(By locator) =>
        _wait.Until(d =>
        {
            try
            {
                var el = d.FindElement(locator);
                return el.Displayed ? (AppiumElement)el : null;
            }
            catch (NoSuchElementException) { return null; }
            catch (StaleElementReferenceException) { return null; }
        })!;
}
