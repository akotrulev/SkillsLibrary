using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public sealed class HomePage
{
    public HomePage(IPage page)
    {
        Greeting = page.GetByTestId("Home.Greeting").Describe("Home greeting");
    }

    public ILocator Greeting { get; }
}
