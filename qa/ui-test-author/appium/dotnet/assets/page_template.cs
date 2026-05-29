using NUnit.Framework;
using OpenQA.Selenium;
using AppiumTests.Pages;

namespace AppiumTests.Pages;

/// <summary>
/// Page object for the [ScreenName] screen.
/// Replace all TODO comments with real locators from the app.
/// </summary>
public class ScreenNamePage : BaseAppiumPage
{
    // ── Locator constants ─────────────────────────────────────────────────────
    // Priority: AccessibilityId → Id → XPath (XPath is last resort)

    // TODO: replace placeholder values with real testID / resource-id values
    private const string LandmarkElementId = "screen-landmark-accessibility-id";
    private const string PrimaryActionButtonId = "primary-action-button";
    private const string InputFieldId = "input-field";

    // ── Constructor ───────────────────────────────────────────────────────────

    public ScreenNamePage(IWebDriver driver) : base(driver) { }

    // ── Page verification ─────────────────────────────────────────────────────

    /// <summary>Asserts this screen is currently visible.</summary>
    public void VerifyPageLoaded()
    {
        var landmark = FindByAccessibilityId(LandmarkElementId);
        Assert.That(landmark.IsDisplayed(), Is.True,
            $"Expected {nameof(ScreenNamePage)} to be visible but landmark element was not found.");
    }

    // ── Actions ───────────────────────────────────────────────────────────────

    /// <summary>Types text into the primary input field.</summary>
    public void EnterText(string text)
    {
        var field = FindByAccessibilityId(InputFieldId);
        field.Clear();
        field.SendKeys(text);
    }

    /// <summary>Taps the primary action button and returns the next screen's page object.</summary>
    /// <returns>The next page object, or <c>void</c> if navigation does not leave this screen.</returns>
    public NextScreenPage TapPrimaryAction()
    {
        FindByAccessibilityId(PrimaryActionButtonId).Click();
        return new NextScreenPage(Driver);
    }

    // ── Queries ───────────────────────────────────────────────────────────────

    /// <summary>Returns the visible text of a result element.</summary>
    public string GetResultText()
    {
        // TODO: replace with real locator
        return FindByAccessibilityId("result-label").GetText();
    }
}
