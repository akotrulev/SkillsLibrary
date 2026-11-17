package com.example.uitests.components.controls;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.options.AriaRole;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

public final class DatePicker {
    private static final DateTimeFormatter MONTH = DateTimeFormatter.ofPattern("MMMM", Locale.ENGLISH);

    private final Locator field;
    private final Locator toggle;
    private final Dropdown month;
    private final Dropdown year;
    private final Locator days;

    public DatePicker(Locator root) {
        this.field = root.getByRole(AriaRole.TEXTBOX).describe("Date field");
        this.toggle = root.getByRole(AriaRole.BUTTON, new Locator.GetByRoleOptions().setName("Choose date"));
        Locator calendar = root.getByRole(AriaRole.DIALOG);
        this.month = new Dropdown(calendar.getByRole(AriaRole.COMBOBOX, new Locator.GetByRoleOptions().setName("Month")));
        this.year = new Dropdown(calendar.getByRole(AriaRole.COMBOBOX, new Locator.GetByRoleOptions().setName("Year")));
        this.days = calendar.getByRole(AriaRole.GRID);
    }

    public void select(LocalDate date) {
        toggle.click();
        month.choose(date.format(MONTH));
        year.choose(String.valueOf(date.getYear()));
        days.getByRole(AriaRole.GRIDCELL, new Locator.GetByRoleOptions()
                .setName(String.valueOf(date.getDayOfMonth()))
                .setExact(true)).click();
    }

    public Locator field() {
        return field;
    }
}
