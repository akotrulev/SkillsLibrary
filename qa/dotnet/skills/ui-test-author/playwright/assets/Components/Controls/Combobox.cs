using Microsoft.Playwright;

namespace Example.UiTests.Components.Controls;

public sealed class Combobox
{
    private readonly ILocator _input;
    private readonly ILocator _listbox;

    public Combobox(ILocator input, ILocator listbox)
    {
        _input = input;
        _listbox = listbox;
    }

    public async Task SelectAsync(string option)
    {
        await _input.FillAsync(option);
        await _listbox.GetByRole(AriaRole.Option, new() { Name = option, Exact = true }).ClickAsync();
    }

    public async Task ClearAsync() => await _input.ClearAsync();
}
