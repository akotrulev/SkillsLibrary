using Allure.NUnit.Attributes;
using Example.UiTests.Pages;
using Example.UiTests.Support;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[AllureFeature("WebMCP")]
[Category("webmcp")]
public class WebMcpTests : BaseTest
{
    private const string AddToCart = "add_to_cart";
    private const string Sku = "sku-123";
    private const int TimeoutMs = 10_000;

    private ProductPage _productPage = null!;
    private LoginPage _loginPage = null!;

    [SetUp]
    public async Task OpenProductPage()
    {
        _productPage = new ProductPage(Page);
        _loginPage = new LoginPage(Page);
        await _productPage.GoToAsync(Sku);
    }

    [Test]
    public async Task Should_DeclareAnObjectSchema_When_AddToCartIsRegistered()
    {
        var tool = await _productPage.RegisteredToolAsync(AddToCart, TimeoutMs);

        Assert.That(tool.GetProperty("inputSchema").GetProperty("type").GetString(), Is.EqualTo("object"), $"{AddToCart} inputSchema in {tool}");
    }

    [Test]
    public async Task Should_MarkAddToCartConsequential_When_AddToCartIsRegistered()
    {
        var tool = await _productPage.RegisteredToolAsync(AddToCart, TimeoutMs);

        Assert.That(tool.GetProperty("annotations").GetProperty("consequentialHint").GetBoolean(), Is.True, $"{AddToCart} annotations in {tool}");
    }

    [Test]
    public async Task Should_UpdateCartBadge_When_AddToCartIsCalledWithValidInput()
    {
        await _productPage.CallToolAsync(AddToCart, new { sku = Sku, quantity = 2 }, TimeoutMs);

        await Expect(_productPage.CartBadge, $"cart badge after {AddToCart}").ToHaveTextAsync("2");
    }

    [Test]
    public async Task Should_ReturnIsError_When_QuantityIsNegative()
    {
        var result = await _productPage.CallToolAsync(AddToCart, new { sku = Sku, quantity = -1 }, TimeoutMs);

        Assert.That(result.GetProperty("isError").GetBoolean(), Is.True, $"{AddToCart} result for quantity -1: {result}");
    }

    [Test]
    public async Task Should_DropAddToCart_When_UserLeavesTheProductPage()
    {
        await _productPage.RegisteredToolAsync(AddToCart, TimeoutMs);
        await _loginPage.GoToAsync();

        var names = await _productPage.ToolNamesAfterRemovalAsync(AddToCart, TimeoutMs);

        Assert.That(names, Does.Not.Contain(AddToCart), "tools after leaving the product page");
    }
}
