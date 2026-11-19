package com.example.uitests.tests;

import com.example.uitests.clients.PageHtmlClient;
import com.example.uitests.clients.PageHtmlClient.PageHtml;
import com.example.uitests.support.BaseTest;
import io.qameta.allure.Feature;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import static org.assertj.core.api.Assertions.assertThat;

@Feature("Orders")
public class RenderingTest extends BaseTest {
    private PageHtmlClient pageHtml;

    @BeforeMethod(alwaysRun = true)
    public void createPageHtmlClient() {
        pageHtml = new PageHtmlClient(page.request());
    }

    @Test(groups = {"orders", "regression"})
    public void Should_RenderOrdersGridInRawHtml_When_OrdersPageIsServerRendered() {
        PageHtml html = pageHtml.get("/orders");

        assertThat(html.markup()).as("raw HTML of /orders").contains("data-testid=\"Orders.Grid\"");
    }

    @Test(groups = {"orders", "regression"})
    public void Should_MarkOrdersHtmlPrivate_When_OrdersPageIsPersonalised() {
        PageHtml html = pageHtml.get("/orders");

        assertThat(html.cacheControl()).as("Cache-Control of /orders").contains("private");
    }
}
