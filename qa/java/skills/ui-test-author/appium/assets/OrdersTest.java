package com.example.mobiletests.tests;

import com.example.mobiletests.pages.LoginPage;
import com.example.mobiletests.pages.OrdersPage;
import com.example.mobiletests.support.BaseMobileTest;
import com.example.mobiletests.support.Env;
import com.example.mobiletests.support.OrderSeeder;
import io.qameta.allure.Feature;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@Feature("Orders")
public class OrdersTest extends BaseMobileTest {
    private static final String ORDER_TITLE = "Seeded order";

    private OrderSeeder seeder;
    private OrdersPage orders;
    private String orderNumber;
    private URI seededOrder;

    @BeforeClass(alwaysRun = true)
    public void createSeeder() {
        seeder = new OrderSeeder(HttpClient.newHttpClient(), URI.create(Env.required("API_URL")), Env.required("E2E_API_TOKEN"));
    }

    @BeforeMethod(alwaysRun = true)
    public void seedOrderAndSignIn() throws IOException, InterruptedException {
        orderNumber = "ORD-" + UUID.randomUUID();
        seededOrder = seeder.create(orderNumber, ORDER_TITLE);
        LoginPage login = new LoginPage(driver);
        login.verifyPageLoaded();
        orders = login.signIn(Env.required("E2E_USER"), Env.required("E2E_PASSWORD"));
        orders.verifyPageLoaded();
    }

    @AfterMethod(alwaysRun = true)
    public void deleteOrder() throws IOException, InterruptedException {
        seeder.delete(seededOrder);
    }

    @Test(groups = {"orders", "smoke"})
    public void Should_ShowOrderTitle_When_OrderIsInHistory() {
        String title = orders.row(orderNumber).title();

        assertThat(title).as("title of order %s", orderNumber).isEqualTo(ORDER_TITLE);
    }
}
