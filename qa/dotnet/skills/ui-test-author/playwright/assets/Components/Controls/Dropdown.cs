using Microsoft.Playwright;

namespace Example.UiTests.Components.Controls;

public sealed class Dropdown
{
    private readonly ILocator _select;

    public Dropdown(ILocator select)
    {
        _select = select;
        SelectedOption = select.Locator("option:checked").Describe("Selected option");
    }

    public ILocator SelectedOption { get; }

    public async Task SelectAsync(string option) =>
        await _select.SelectOptionAsync(new SelectOptionValue { Label = option });
}
