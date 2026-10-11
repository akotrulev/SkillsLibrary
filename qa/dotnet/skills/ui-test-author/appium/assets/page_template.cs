using NUnit.Framework;
using OpenQA.Selenium.Appium;

namespace AppiumTests.Pages;

public sealed class ScreenNamePage : BaseAppiumPage
{
    private const string LandmarkId = "ScreenName.Landmark";
    private const string InputId = "ScreenName.Input";
    private const string PrimaryActionId = "ScreenName.PrimaryAction";
    private const string ResultId = "ScreenName.Result";

    public ScreenNamePage(AppiumDriver driver) : base(driver)
    {
    }

    public override void VerifyPageLoaded() =>
        Assert.That(IsTestIdVisible(LandmarkId), Is.True, "Expected ScreenNamePage to be visible but the landmark was not found");

    public void EnterText(string text)
    {
        var field = ByTestId(InputId);
        field.Clear();
        field.SendKeys(text);
    }

    public void TapPrimaryAction() => ByTestId(PrimaryActionId).Click();

    public string ResultText() => ByTestId(ResultId).Text;
}
