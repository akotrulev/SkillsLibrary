package com.example.uitests.tests;

import com.example.uitests.pages.LoginPage;
import com.example.uitests.pages.ProductPage;
import com.example.uitests.support.BaseTest;
import com.microsoft.playwright.BrowserType;
import io.qameta.allure.Feature;
import org.assertj.core.api.Assertions;
import org.assertj.core.api.InstanceOfAssertFactories;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.util.List;
import java.util.Map;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

@Feature("WebMCP")
public class WebMcpTest extends BaseTest {
    private static final String ADD_TO_CART = "add_to_cart";
    private static final String SKU = "sku-123";
    private static final int TIMEOUT_MS = 10_000;

    private ProductPage productPage;
    private LoginPage loginPage;

    @Override
    protected BrowserType.LaunchOptions launchOptions() {
        return new BrowserType.LaunchOptions().setArgs(List.of("--enable-features=WebMCP"));
    }

    @BeforeMethod(alwaysRun = true)
    public void openProductPage() {
        productPage = new ProductPage(page);
        loginPage = new LoginPage(page);
        productPage.goTo(SKU);
    }

    @Test(groups = {"webmcp", "regression"})
    public void Should_DeclareAnObjectSchema_When_AddToCartIsRegistered() {
        Map<?, ?> tool = registeredTool(ADD_TO_CART);

        Assertions.assertThat(tool.get("inputSchema"))
                .as("%s inputSchema", ADD_TO_CART)
                .asInstanceOf(InstanceOfAssertFactories.MAP)
                .containsEntry("type", "object")
                .containsEntry("required", List.of("sku", "quantity"));
    }

    @Test(groups = {"webmcp", "regression"})
    public void Should_MarkAddToCartConsequential_When_AddToCartIsRegistered() {
        Map<?, ?> tool = registeredTool(ADD_TO_CART);

        Assertions.assertThat(tool.get("annotations"))
                .as("%s annotations", ADD_TO_CART)
                .asInstanceOf(InstanceOfAssertFactories.MAP)
                .containsEntry("consequentialHint", true);
    }

    @Test(groups = {"webmcp", "regression"})
    public void Should_UpdateCartBadge_When_AddToCartIsCalledWithValidInput() {
        callAddToCart(2);

        assertThat(productPage.cartBadge()).hasText("2");
    }

    @Test(groups = {"webmcp", "regression"})
    public void Should_ReturnIsError_When_QuantityIsNegative() {
        Object result = callAddToCart(-1);

        Assertions.assertThat(result)
                .as("%s result for quantity -1", ADD_TO_CART)
                .asInstanceOf(InstanceOfAssertFactories.MAP)
                .containsEntry("isError", true);
    }

    @Test(groups = {"webmcp", "regression"})
    public void Should_DropAddToCart_When_UserLeavesTheProductPage() {
        registeredTool(ADD_TO_CART);
        loginPage.goTo();

        Assertions.assertThat(names(productPage.settledTools(ADD_TO_CART, false, TIMEOUT_MS)))
                .as("tools after leaving the product page")
                .doesNotContain(ADD_TO_CART);
    }

    private Map<?, ?> registeredTool(String name) {
        List<Map<?, ?>> tools = productPage.settledTools(name, true, TIMEOUT_MS);
        return tools.stream()
                .filter(tool -> name.equals(tool.get("name")))
                .findFirst()
                .orElseThrow(() -> new AssertionError(
                        "WebMCP tool " + name + " not registered within " + TIMEOUT_MS + " ms; tools: " + names(tools)));
    }

    private Object callAddToCart(int quantity) {
        registeredTool(ADD_TO_CART);
        return productPage.callTool(ADD_TO_CART, Map.of("sku", SKU, "quantity", quantity), TIMEOUT_MS);
    }

    private static List<Object> names(List<Map<?, ?>> tools) {
        return tools.stream().<Object>map(tool -> tool.get("name")).toList();
    }
}
