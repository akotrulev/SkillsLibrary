package com.example.uitests.pages;

import com.example.uitests.components.controls.DataGrid;
import com.example.uitests.components.controls.DatePicker;
import com.example.uitests.components.controls.GridRow;
import com.microsoft.playwright.Page;

import java.util.List;

public final class OrdersPage {
    private final Page page;
    private final DatePicker placedOn;
    private final DataGrid orders;

    public OrdersPage(Page page) {
        this.page = page;
        this.placedOn = new DatePicker(page.getByTestId("Orders.PlacedOn"));
        this.orders = new DataGrid(page.getByTestId("Orders.Grid"));
    }

    public void goTo() {
        page.navigate("/orders");
    }

    public DatePicker placedOn() {
        return placedOn;
    }

    public GridRow order(String orderNumber) {
        return orders.row(orderNumber);
    }

    public List<String> orderColumn(String column) {
        return orders.columnValues(column);
    }
}
