package com.example.uitests.pages;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;

public final class HomePage {
    private final Locator greeting;

    public HomePage(Page page) {
        this.greeting = page.getByTestId("Home.Greeting").describe("Home greeting");
    }

    public Locator greeting() {
        return greeting;
    }
}
