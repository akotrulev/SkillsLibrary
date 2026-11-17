package com.example.uitests.components.controls;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.options.SelectOption;

public final class Dropdown {
    private final Locator select;
    private final Locator selectedOption;

    public Dropdown(Locator select) {
        this.select = select;
        this.selectedOption = select.locator("option:checked").describe("Selected option");
    }

    public void choose(String optionText) {
        select.selectOption(new SelectOption().setLabel(optionText));
    }

    public Locator selectedOption() {
        return selectedOption;
    }
}
