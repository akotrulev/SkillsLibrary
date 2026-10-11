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
