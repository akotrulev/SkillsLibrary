package com.example.uitests.tests;

import com.example.uitests.pages.OrdersPage;
import com.example.uitests.support.BaseTest;
import com.microsoft.playwright.APIResponse;
import com.microsoft.playwright.options.RequestOptions;
import io.qameta.allure.Feature;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.time.LocalDate;
import java.util.Map;
import java.util.UUID;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.assertj.core.api.Assertions.assertThat;

@Feature("Orders")
public class OrdersTest extends BaseTest {
    private static final LocalDate PLACED_ON = LocalDate.of(2026, 3, 14);

    private OrdersPage ordersPage;
    private String orderNumber;
    private String orderLocation;

    @BeforeMethod(alwaysRun = true)
    public void seedOrderAndOpenOrders() {
        orderNumber = "ORD-" + UUID.randomUUID();
        APIResponse created = page.request().post("/api/orders", RequestOptions.create()
                .setData(Map.of("number", orderNumber, "placedOn", PLACED_ON.toString(), "status", "Pending")));
        assertThat(created.status()).as(created.text()).isEqualTo(201);
        orderLocation = created.headers().get("location");
        ordersPage = new OrdersPage(page);
        ordersPage.goTo();
    }

    @AfterMethod(alwaysRun = true)
    public void deleteOrder() {
        APIResponse deleted = page.request().delete(orderLocation);
        assertThat(deleted.status()).as(deleted.text()).isEqualTo(204);
    }

    @Test(groups = {"orders", "regression"})
    public void Should_ListOrder_When_FilteredByItsPlacedDate() {
        ordersPage.placedOn().select(PLACED_ON);

        assertThat(ordersPage.order(orderNumber).cell("Status")).hasText("Pending");
    }

    @Test(groups = {"orders", "regression"})
    public void Should_ListOnlyOrdersPlacedThatDay_When_FilteredByPlacedDate() {
        ordersPage.placedOn().select(PLACED_ON);

        assertThat(ordersPage.orderColumn("Placed on"))
                .as("Placed on of every listed order")
                .isNotEmpty()
                .allSatisfy(placedOn -> assertThat(placedOn).isEqualTo(PLACED_ON.toString()));
    }
}
