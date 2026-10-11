using NUnit.Framework;
using OpenQA.Selenium.Appium;

namespace AppiumTests.Pages;

public sealed class OrdersPage : BaseAppiumPage
{
    private const string ListId = "Orders.List";

    public OrdersPage(AppiumDriver driver) : base(driver)
    {
    }

    public override void VerifyPageLoaded() =>
        Assert.That(IsTestIdVisible(ListId), Is.True, "Expected OrdersPage to be visible but the orders list was not found");

    public OrderRow Row(string orderNumber) => new(Driver, orderNumber);
}
