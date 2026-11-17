package com.example.uitests.components.controls;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.AriaRole;
import com.microsoft.playwright.options.WaitForSelectorState;

import java.util.List;

public final class DataGrid {
    private final Page page;
    private final Locator busyGrid;
    private final Locator headers;
    private final Locator rows;

    public DataGrid(Locator root) {
        this.page = root.page();
        this.busyGrid = root.and(page.locator("[aria-busy='true']"));
        this.headers = root.getByRole(AriaRole.COLUMNHEADER);
        this.rows = root.getByRole(AriaRole.ROW)
                .filter(new Locator.FilterOptions().setHas(page.getByRole(AriaRole.GRIDCELL)))
                .describe("Data grid rows");
    }

    public GridRow row(String key) {
        Locator keyCell = page.getByRole(AriaRole.GRIDCELL, new Page.GetByRoleOptions().setName(key).setExact(true));
        Locator row = rows.filter(new Locator.FilterOptions().setHas(keyCell)).describe("Row " + key);
        return new GridRow(row, columnNames());
    }

    public Locator rows() {
        return rows;
    }

    public List<String> columnValues(String column) {
        waitUntilLoaded();
        List<String> columns = columnNames();
        return rows.all().stream()
                .map(row -> new GridRow(row, columns).cell(column).innerText().strip())
                .toList();
    }

    private void waitUntilLoaded() {
        busyGrid.waitFor(new Locator.WaitForOptions().setState(WaitForSelectorState.HIDDEN));
    }

    private List<String> columnNames() {
        headers.first().waitFor();
        return headers.allInnerTexts().stream().map(String::strip).toList();
    }
}
