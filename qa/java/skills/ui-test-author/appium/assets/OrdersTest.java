package com.example.mobiletests.tests;

import com.example.mobiletests.pages.LoginPage;
import com.example.mobiletests.pages.OrdersPage;
import com.example.mobiletests.support.BaseMobileTest;
import com.example.mobiletests.support.Env;
import io.qameta.allure.Feature;
import org.testng.annotations.Test;

import static org.assertj.core.api.Assertions.assertThat;

@Feature("Orders")
public class OrdersTest extends BaseMobileTest {

    @Test(groups = {"orders", "smoke"})
    public void Should_ShowOrderTitle_When_OrderIsInHistory() {
        LoginPage login = new LoginPage(driver);
        login.verifyPageLoaded();
        OrdersPage orders = login.signIn(Env.required("E2E_USER"), Env.required("E2E_PASSWORD"));
        orders.verifyPageLoaded();
        String orderNumber = Env.required("E2E_ORDER_NUMBER");

        String title = orders.row(orderNumber).title();

        assertThat(title)
                .as("title of order %s", orderNumber)
                .isEqualTo(Env.required("E2E_ORDER_TITLE"));
    }
}
