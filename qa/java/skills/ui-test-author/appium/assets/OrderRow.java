package com.example.mobiletests.pages;

import io.appium.java_client.AppiumDriver;
import org.openqa.selenium.StaleElementReferenceException;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.WebDriverWait;

public final class OrderRow {
    private static final String ROW_ID = "OrderRow";
    private static final String NUMBER_ID = "OrderRow.Number";
    private static final String TITLE_ID = "OrderRow.Title";
    private static final String STATUS_ID = "OrderRow.Status";

    private final AppiumDriver driver;
    private final String orderNumber;

    OrderRow(AppiumDriver driver, String orderNumber) {
        this.driver = driver;
        this.orderNumber = orderNumber;
    }

    public String title() {
        return textOf(TITLE_ID);
    }

    public String status() {
        return textOf(STATUS_ID);
    }

    public void open() {
        root().click();
    }

    private String textOf(String id) {
        return root().findElement(BaseAppiumPage.testId(driver, id)).getText();
    }

    private WebElement root() {
        return new WebDriverWait(driver, BaseAppiumPage.TIMEOUT)
                .ignoring(StaleElementReferenceException.class)
                .withMessage("No " + ROW_ID + " shows order " + orderNumber)
                .until(d -> d.findElements(BaseAppiumPage.testId(d, ROW_ID)).stream()
                        .filter(row -> orderNumber.equals(row.findElement(BaseAppiumPage.testId(d, NUMBER_ID)).getText()))
                        .findFirst()
                        .orElse(null));
    }
}
