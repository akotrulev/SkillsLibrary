package com.example.mobiletests.pages;

import io.appium.java_client.AppiumDriver;

import static org.assertj.core.api.Assertions.assertThat;

public final class OrdersPage extends BaseAppiumPage {
    private static final String LIST_ID = "Orders.List";

    public OrdersPage(AppiumDriver driver) {
        super(driver);
    }

    @Override
    public void verifyPageLoaded() {
        assertThat(isTestIdVisible(LIST_ID))
                .as("Expected OrdersPage to be visible but the orders list was not found")
                .isTrue();
    }

    public OrderRow row(String orderNumber) {
        return new OrderRow(driver, orderNumber);
    }
}
