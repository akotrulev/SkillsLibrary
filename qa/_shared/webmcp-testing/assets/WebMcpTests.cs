using System.Text.Json;
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
        var tool = await RegisteredToolAsync(AddToCart);

        Assert.That(tool.GetProperty("inputSchema").GetProperty("type").GetString(), Is.EqualTo("object"), $"{AddToCart} inputSchema in {tool}");
    }

    [Test]
    public async Task Should_MarkAddToCartConsequential_When_AddToCartIsRegistered()
    {
        var tool = await RegisteredToolAsync(AddToCart);

        Assert.That(tool.GetProperty("annotations").GetProperty("consequentialHint").GetBoolean(), Is.True, $"{AddToCart} annotations in {tool}");
    }

    [Test]
    public async Task Should_UpdateCartBadge_When_AddToCartIsCalledWithValidInput()
    {
        await CallAddToCartAsync(2);

        await Expect(_productPage.CartBadge, $"cart badge after {AddToCart}").ToHaveTextAsync("2");
    }

    [Test]
    public async Task Should_ReturnIsError_When_QuantityIsNegative()
    {
        var result = await CallAddToCartAsync(-1);

        Assert.That(result.GetProperty("isError").GetBoolean(), Is.True, $"{AddToCart} result for quantity -1: {result}");
    }

    [Test]
    public async Task Should_DropAddToCart_When_UserLeavesTheProductPage()
    {
        await RegisteredToolAsync(AddToCart);
        await _loginPage.GoToAsync();

        var tools = await _productPage.SettledToolsAsync(AddToCart, present: false, TimeoutMs);

        Assert.That(Names(tools), Does.Not.Contain(AddToCart), "tools after leaving the product page");
    }

    private async Task<JsonElement> RegisteredToolAsync(string name)
    {
        var tools = await _productPage.SettledToolsAsync(name, present: true, TimeoutMs);
        var tool = tools.EnumerateArray().FirstOrDefault(candidate => candidate.GetProperty("name").GetString() == name);
        return tool.ValueKind == JsonValueKind.Object
            ? tool
            : throw new AssertionException($"WebMCP tool {name} not registered within {TimeoutMs} ms; tools: {string.Join(", ", Names(tools))}");
    }

    private async Task<JsonElement> CallAddToCartAsync(int quantity)
    {
        await RegisteredToolAsync(AddToCart);
        return await _productPage.CallToolAsync(AddToCart, new { sku = Sku, quantity }, TimeoutMs);
    }

    private static string?[] Names(JsonElement tools) =>
        tools.EnumerateArray().Select(tool => tool.GetProperty("name").GetString()).ToArray();
}
