using Allure.NUnit.Attributes;
using Example.UiTests.Pages;
using Example.UiTests.Support;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[AllureFeature("Login")]
public class LoginTests : BaseTest
{
    private LoginPage _loginPage = null!;
    private HomePage _homePage = null!;
    private LoginPage.Credentials _user = null!;

    [SetUp]
    public void CreatePages()
    {
        _loginPage = new LoginPage(Page);
        _homePage = new HomePage(Page);
        _user = new LoginPage.Credentials(RequiredEnv("E2E_USER"), RequiredEnv("E2E_PASSWORD"));
    }

    [Test]
    [Category("login")]
    [Category("smoke")]
    public async Task Should_GreetUser_When_CredentialsAreValid()
    {
        await _loginPage.SignInAsync(_user);

        await Expect(_homePage.Greeting, $"greeting for {_user.Email}").ToHaveTextAsync($"Welcome, {_user.Email}");
    }

    [Test]
    [Category("login")]
    [Category("regression")]
    public async Task Should_ShowInvalidCredentialsError_When_PasswordIsWrong()
    {
        await _loginPage.SignInAsync(_user with { Password = _user.Password + "-wrong" });

        await Expect(_loginPage.Error, $"sign-in error for {_user.Email}").ToHaveTextAsync("Invalid email or password");
    }
}
