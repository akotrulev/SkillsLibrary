using System.Globalization;
using Microsoft.Playwright;

namespace Example.UiTests.Components.Controls;

public sealed class DatePicker
{
    private const string InputFormat = "yyyy-MM-dd";

    private readonly ILocator _input;

    public DatePicker(ILocator root)
    {
        _input = root.GetByRole(AriaRole.Textbox);
    }

    public async Task SelectAsync(DateOnly date)
    {
        await _input.FillAsync(date.ToString(InputFormat, CultureInfo.InvariantCulture));
        await _input.PressAsync("Enter");
    }

    public async Task ClearAsync() => await _input.ClearAsync();
}
