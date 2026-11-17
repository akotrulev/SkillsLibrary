using AppiumTests.Pages;
using AppiumTests.Seeders;
using AppiumTests.Support;
using Allure.NUnit.Attributes;
using NUnit.Framework;

namespace AppiumTests.Tests;

[AllureFeature("Orders")]
public class OrdersTests : BaseMobileTest
{
    private OrderSeeder _seeder = null!;
    private SeededOrder _order = null!;
    private OrdersPage _orders = null!;

    [OneTimeSetUp]
    public void CreateSeeder() => _seeder = new OrderSeeder(new Uri(Env.Required("API_URL")), Env.Required("API_TOKEN"));

    [OneTimeTearDown]
    public void DisposeSeeder() => _seeder.Dispose();

    [SetUp]
    public async Task SeedOrderAndSignIn()
    {
        _order = await _seeder.CreateAsync($"Order {Guid.NewGuid():N}");
        var login = new LoginPage(Driver);
        login.VerifyPageLoaded();
        _orders = login.SignIn(Env.Required("E2E_USER"), Env.Required("E2E_PASSWORD"));
        _orders.VerifyPageLoaded();
    }

    [TearDown]
    public async Task DeleteOrder() => await _seeder.DeleteAsync(_order);

    [Test]
    [Category("Smoke")]
    public void Should_ShowOrderTitle_When_OrderIsInHistory()
    {
        var title = _orders.Row(_order.Number).Title();

        Assert.That(title, Is.EqualTo(_order.Title), $"title of order {_order.Number}");
    }
}
