using AppiumTests.Pages;
using AppiumTests.Support;
using Allure.NUnit.Attributes;
using NUnit.Framework;

namespace AppiumTests.Tests;

[AllureFeature("Orders")]
public class OrdersTests : BaseMobileTest
{
    [Test]
    [Category("Smoke")]
    public void Should_ShowOrderTitle_When_OrderIsInHistory()
    {
        var login = new LoginPage(Driver);
        login.VerifyPageLoaded();
        var orders = login.SignIn(Env.Required("E2E_USER"), Env.Required("E2E_PASSWORD"));
        orders.VerifyPageLoaded();
        var orderNumber = Env.Required("E2E_ORDER_NUMBER");

        var title = orders.Row(orderNumber).Title();

        Assert.That(title, Is.EqualTo(Env.Required("E2E_ORDER_TITLE")), $"title of order {orderNumber}");
    }
}
