using Microsoft.Playwright;

namespace Example.UiTests.Components.Controls;

public sealed class DataGrid
{
    private readonly ILocator _root;
    private readonly ILocator _rows;

    public DataGrid(ILocator root)
    {
        _root = root;
        _rows = root.GetByRole(AriaRole.Row);
        DataRows = _rows.Filter(new() { Has = root.Page.GetByRole(AriaRole.Gridcell) }).Describe("Grid data rows");
    }

    public ILocator DataRows { get; }

    public GridRow Row(string key) =>
        new(_rows.Filter(new() { Has = _root.Page.GetByRole(AriaRole.Gridcell, new() { Name = key, Exact = true }) }), _root);

    public async Task<IReadOnlyList<string>> ColumnValuesAsync(string column)
    {
        var header = _root.GetByRole(AriaRole.Columnheader, new() { Name = column, Exact = true });
        var position = await header.GetAttributeAsync("aria-colindex");
        return await DataRows.Locator($"[role=gridcell][aria-colindex=\"{position}\"]").AllInnerTextsAsync();
    }

    public async Task SortByAsync(string column) =>
        await _root.GetByRole(AriaRole.Columnheader, new() { Name = column, Exact = true }).ClickAsync();
}
