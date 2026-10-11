package com.example.mobiletests.support;

import io.appium.java_client.AppiumDriver;
import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.android.options.UiAutomator2Options;
import io.appium.java_client.ios.IOSDriver;
import io.appium.java_client.ios.options.XCUITestOptions;

import java.net.MalformedURLException;
import java.net.URI;
import java.net.URL;

public final class AppiumDriverFactory {
    private static final String DEFAULT_SERVER_URL = "http://127.0.0.1:4723";

    private AppiumDriverFactory() {
    }

    public static AppiumDriver create() throws MalformedURLException {
        URL server = URI.create(System.getenv().getOrDefault("APPIUM_URL", DEFAULT_SERVER_URL)).toURL();
        String platform = Env.required("PLATFORM");
        return switch (platform) {
            case "android" -> new AndroidDriver(server, androidOptions());
            case "ios" -> new IOSDriver(server, iosOptions());
            default -> throw new IllegalArgumentException("PLATFORM must be android or ios, got " + platform);
        };
    }

    private static UiAutomator2Options androidOptions() {
        return new UiAutomator2Options()
                .setDeviceName(Env.required("DEVICE_NAME"))
                .setApp(Env.required("APP_PATH"))
                .setAutoGrantPermissions(true)
                .amend("appium:settings[disableIdLocatorAutocompletion]", true);
    }

    private static XCUITestOptions iosOptions() {
        return new XCUITestOptions()
                .setDeviceName(Env.required("DEVICE_NAME"))
                .setPlatformVersion(Env.required("PLATFORM_VERSION"))
                .setApp(Env.required("APP_PATH"))
                .setAutoAcceptAlerts(true);
    }
}
