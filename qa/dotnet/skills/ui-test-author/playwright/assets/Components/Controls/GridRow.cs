using Microsoft.Playwright;

namespace Example.UiTests.Components.Controls;

public sealed class GridRow
{
    private readonly ILocator _row;
    private readonly ILocator _grid;

    internal GridRow(ILocator row, ILocator grid)
    {
        _row = row;
        _grid = grid;
    }

    public async Task<ILocator> CellAsync(string column)
    {
        var header = _grid.GetByRole(AriaRole.Columnheader, new() { Name = column, Exact = true });
        var position = await header.GetAttributeAsync("aria-colindex");
        return _row.Locator($"[role=gridcell][aria-colindex=\"{position}\"]").Describe($"{column} cell");
    }

    public async Task ChooseActionAsync(string action) =>
        await _row.GetByRole(AriaRole.Button, new() { Name = action, Exact = true }).ClickAsync();

    public async Task SelectAsync() => await _row.GetByRole(AriaRole.Checkbox).CheckAsync();
}
