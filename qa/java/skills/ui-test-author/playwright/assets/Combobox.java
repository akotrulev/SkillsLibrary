package com.example.uitests.components.controls;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.options.AriaRole;

public final class Combobox {
    private final Locator input;
    private final Locator openListbox;

    public Combobox(Locator root) {
        this.input = root.getByRole(AriaRole.COMBOBOX).describe("Combobox input");
        this.openListbox = root.page().getByRole(AriaRole.LISTBOX);
    }

    public void choose(String optionText) {
        input.fill(optionText);
        openListbox.getByRole(AriaRole.OPTION, new Locator.GetByRoleOptions().setName(optionText).setExact(true)).click();
    }

    public Locator input() {
        return input;
    }
}
