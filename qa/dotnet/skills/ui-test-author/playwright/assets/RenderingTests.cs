using Allure.NUnit.Attributes;
using Example.UiTests.Clients;
using Example.UiTests.Support;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[AllureFeature("Orders")]
public class RenderingTests : BaseTest
{
    private PageHtmlClient _pageHtml = null!;

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.StorageStatePath = AuthSetup.UserState;
        return options;
    }

    [SetUp]
    public void CreatePageHtmlClient()
    {
        _pageHtml = new PageHtmlClient(Page.APIRequest);
    }

    [Test]
    [Category("orders")]
    [Category("regression")]
    public async Task Should_RenderOrdersGridInRawHtml_When_OrdersPageIsServerRendered()
    {
        var html = await _pageHtml.GetAsync("/orders");

        Assert.That(html.Markup, Does.Contain("data-testid=\"Orders.Grid\""), "raw HTML of /orders");
    }

    [Test]
    [Category("orders")]
    [Category("regression")]
    public async Task Should_MarkOrdersHtmlPrivate_When_OrdersPageIsPersonalised()
    {
        var html = await _pageHtml.GetAsync("/orders");

        Assert.That(html.CacheControl, Does.Contain("private"), "Cache-Control of /orders");
    }
}
