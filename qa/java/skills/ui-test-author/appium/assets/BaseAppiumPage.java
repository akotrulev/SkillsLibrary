package com.example.mobiletests.pages;

import io.appium.java_client.AppiumBy;
import io.appium.java_client.AppiumDriver;
import io.appium.java_client.ios.IOSDriver;
import org.openqa.selenium.By;
import org.openqa.selenium.TimeoutException;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;

public abstract class BaseAppiumPage {
    static final Duration TIMEOUT = Duration.ofSeconds(10);

    protected final AppiumDriver driver;
    private final WebDriverWait wait;

    protected BaseAppiumPage(AppiumDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, TIMEOUT);
    }

    static By testId(WebDriver driver, String id) {
        return driver instanceof IOSDriver ? AppiumBy.accessibilityId(id) : AppiumBy.id(id);
    }

    protected WebElement byTestId(String id) {
        return present(testId(driver, id));
    }

    protected WebElement byContentDescription(String description) {
        return present(AppiumBy.accessibilityId(description));
    }

    protected WebElement byIosPredicate(String predicate) {
        return present(AppiumBy.iOSNsPredicateString(predicate));
    }

    protected WebElement byIosClassChain(String classChain) {
        return present(AppiumBy.iOSClassChain(classChain));
    }

    protected WebElement byAndroidUiAutomator(String selector) {
        return present(AppiumBy.androidUIAutomator(selector));
    }

    protected WebElement byXPath(String xpath) {
        return present(By.xpath(xpath));
    }

    protected boolean isTestIdVisible(String id) {
        try {
            wait.until(ExpectedConditions.visibilityOfElementLocated(testId(driver, id)));
            return true;
        } catch (TimeoutException e) {
            return false;
        }
    }

    public abstract void verifyPageLoaded();

    private WebElement present(By locator) {
        return wait.until(ExpectedConditions.presenceOfElementLocated(locator));
    }
}
