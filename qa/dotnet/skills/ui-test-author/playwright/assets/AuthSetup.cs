using Example.UiTests.Pages;
using Example.UiTests.Support;
using Microsoft.Playwright;
using Microsoft.Playwright.TestAdapter;
using NUnit.Framework;
using static Microsoft.Playwright.Assertions;

namespace Example.UiTests;

[SetUpFixture]
public class AuthSetup
{
    public static string UserState => Path.Combine(TestContext.CurrentContext.WorkDirectory, "auth-user.json");

    [OneTimeSetUp]
    public async Task SaveSignedInState()
    {
        using var playwright = await Playwright.CreateAsync();
        await using var browser = await playwright[PlaywrightSettingsProvider.BrowserName].LaunchAsync(PlaywrightSettingsProvider.LaunchOptions);
        var context = await browser.NewContextAsync(new() { BaseURL = BaseTest.RequiredEnv("BASE_URL") });
        var page = await context.NewPageAsync();

        await new LoginPage(page).SignInAsync(new LoginPage.Credentials(BaseTest.RequiredEnv("E2E_USER"), BaseTest.RequiredEnv("E2E_PASSWORD")));
        await Expect(new HomePage(page).Greeting, "greeting before saving the signed-in state").ToBeVisibleAsync();

        await context.StorageStateAsync(new() { Path = UserState });
    }
}
