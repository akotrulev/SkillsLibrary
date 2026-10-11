package com.example.mobiletests.pages;

import io.appium.java_client.AppiumDriver;
import org.openqa.selenium.WebElement;

import static org.assertj.core.api.Assertions.assertThat;

public final class LoginPage extends BaseAppiumPage {
    private static final String EMAIL_ID = "Login.Email";
    private static final String PASSWORD_ID = "Login.Password";
    private static final String SUBMIT_ID = "Login.Submit";

    public LoginPage(AppiumDriver driver) {
        super(driver);
    }

    @Override
    public void verifyPageLoaded() {
        assertThat(isTestIdVisible(EMAIL_ID))
                .as("Expected LoginPage to be visible but the email field was not found")
                .isTrue();
    }

    public OrdersPage signIn(String email, String password) {
        type(byTestId(EMAIL_ID), email);
        type(byTestId(PASSWORD_ID), password);
        byTestId(SUBMIT_ID).click();
        return new OrdersPage(driver);
    }

    private static void type(WebElement field, String text) {
        field.clear();
        field.sendKeys(text);
    }
}
