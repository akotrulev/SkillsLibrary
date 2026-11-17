using Example.UiTests.Components.Controls;
using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public sealed class OrdersPage
{
    private readonly IPage _page;

    public OrdersPage(IPage page)
    {
        _page = page;
        PlacedOn = new DatePicker(page.GetByTestId("Orders.PlacedOn"));
        Status = new Dropdown(page.GetByTestId("Orders.Status"));
        Orders = new DataGrid(page.GetByTestId("Orders.Grid"));
    }

    public DatePicker PlacedOn { get; }

    public Dropdown Status { get; }

    public DataGrid Orders { get; }

    public async Task GoToAsync() => await _page.GotoAsync("/orders");

    public async Task FilterAsync(DateOnly placedOn, string status)
    {
        await PlacedOn.SelectAsync(placedOn);
        await Status.SelectAsync(status);
    }
}
