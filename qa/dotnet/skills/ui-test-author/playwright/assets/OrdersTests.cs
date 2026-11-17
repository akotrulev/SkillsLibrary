using System.Globalization;
using Allure.NUnit.Attributes;
using Example.UiTests.Pages;
using Example.UiTests.Support;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[AllureFeature("Orders")]
public class OrdersTests : BaseTest
{
    private static readonly DateOnly PlacedOn = new(2026, 11, 2);

    private OrdersPage _ordersPage = null!;
    private string _orderTitle = null!;
    private string _orderLocation = null!;

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.StorageStatePath = AuthSetup.UserState;
        return options;
    }

    [SetUp]
    public async Task SeedOrderAndOpenOrders()
    {
        _orderTitle = $"Order {Guid.NewGuid():N}";
        var created = await Page.APIRequest.PostAsync("/api/orders", new()
        {
            DataObject = new { Title = _orderTitle, PlacedOn = PlacedOn.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) },
        });
        Assert.That(created.Status, Is.EqualTo(201), await created.TextAsync());
        _orderLocation = created.Headers["location"];

        _ordersPage = new OrdersPage(Page);
        await _ordersPage.GoToAsync();
    }

    [TearDown]
    public async Task DeleteOrder()
    {
        var deleted = await Page.APIRequest.DeleteAsync(_orderLocation);
        Assert.That(deleted.Status, Is.EqualTo(204), await deleted.TextAsync());
    }

    [Test]
    [Category("orders")]
    [Category("smoke")]
    public async Task Should_ListOrderAsPending_When_FilteredByItsPlacedDateAndPendingStatus()
    {
        await _ordersPage.FilterAsync(PlacedOn, "Pending");

        var status = await _ordersPage.Orders.Row(_orderTitle).CellAsync("Status");
        await Expect(status, $"status of {_orderTitle}").ToHaveTextAsync("Pending");
    }

    [Test]
    [Category("orders")]
    [Category("regression")]
    public async Task Should_ListOnlyPendingOrders_When_FilteredByPendingStatus()
    {
        await _ordersPage.FilterAsync(PlacedOn, "Pending");

        await Expect(_ordersPage.Orders.DataRows, "orders listed").Not.ToHaveCountAsync(0);
        IReadOnlyList<string> statuses = await _ordersPage.Orders.ColumnValuesAsync("Status");
        Assert.That(statuses, Is.All.EqualTo("Pending"), "status of every listed order");
    }

    [Test]
    [Category("orders")]
    [Category("regression")]
    public async Task Should_ShowOrderAsCancelled_When_CancelledFromItsRow()
    {
        await _ordersPage.Orders.Row(_orderTitle).ChooseActionAsync("Cancel");

        var status = await _ordersPage.Orders.Row(_orderTitle).CellAsync("Status");
        await Expect(status, $"status of {_orderTitle}").ToHaveTextAsync("Cancelled");
    }
}
