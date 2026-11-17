package com.example.uitests.components.controls;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.options.AriaRole;

import java.util.List;
import java.util.stream.IntStream;

public final class GridRow {
    private final Locator row;
    private final Locator cells;
    private final List<String> columns;

    GridRow(Locator row, List<String> columns) {
        this.row = row;
        this.cells = row.getByRole(AriaRole.GRIDCELL);
        this.columns = List.copyOf(columns);
    }

    public Locator cell(String column) {
        int index = IntStream.range(0, columns.size())
                .filter(position -> columns.get(position).equals(column))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("No column \"" + column + "\" in " + columns));
        return cells.nth(index).describe(column + " cell");
    }

    public void perform(String action) {
        row.getByRole(AriaRole.BUTTON, new Locator.GetByRoleOptions().setName(action).setExact(true)).click();
    }
}
