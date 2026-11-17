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
        Map<?, ?> tool = productPage.registeredTool(ADD_TO_CART, TIMEOUT_MS);

        Assertions.assertThat(tool.get("inputSchema"))
                .as("%s inputSchema", ADD_TO_CART)
                .asInstanceOf(InstanceOfAssertFactories.MAP)
                .containsEntry("type", "object")
                .containsEntry("required", List.of("sku", "quantity"));
    }

    @Test(groups = {"webmcp", "regression"})
    public void Should_MarkAddToCartConsequential_When_AddToCartIsRegistered() {
        Map<?, ?> tool = productPage.registeredTool(ADD_TO_CART, TIMEOUT_MS);

        Assertions.assertThat(tool.get("annotations"))
                .as("%s annotations", ADD_TO_CART)
                .asInstanceOf(InstanceOfAssertFactories.MAP)
                .containsEntry("consequentialHint", true);
    }

    @Test(groups = {"webmcp", "regression"})
    public void Should_UpdateCartBadge_When_AddToCartIsCalledWithValidInput() {
        productPage.callTool(ADD_TO_CART, Map.of("sku", SKU, "quantity", 2), TIMEOUT_MS);

        assertThat(productPage.cartBadge()).hasText("2");
    }

    @Test(groups = {"webmcp", "regression"})
    public void Should_ReturnIsError_When_QuantityIsNegative() {
        Object result = productPage.callTool(ADD_TO_CART, Map.of("sku", SKU, "quantity", -1), TIMEOUT_MS);

        Assertions.assertThat(result)
                .as("%s result for quantity -1", ADD_TO_CART)
                .asInstanceOf(InstanceOfAssertFactories.MAP)
                .containsEntry("isError", true);
    }

    @Test(groups = {"webmcp", "regression"})
    public void Should_DropAddToCart_When_UserLeavesTheProductPage() {
        productPage.registeredTool(ADD_TO_CART, TIMEOUT_MS);
        loginPage.goTo();

        Assertions.assertThat(productPage.toolNamesAfterRemoval(ADD_TO_CART, TIMEOUT_MS))
                .as("tools after leaving the product page")
                .doesNotContain(ADD_TO_CART);
    }
}
