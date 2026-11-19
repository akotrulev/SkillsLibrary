import { expect, type Locator, type Page } from '@playwright/test';
import { DataGrid } from './DataGrid';
import { DatePicker } from './DatePicker';
import { Dropdown } from './Dropdown';

export class OrdersPage {
  readonly placedFrom: DatePicker;
  readonly status: Dropdown;
  readonly orders: DataGrid;
  private readonly apply: Locator;

  constructor(private readonly page: Page) {
    this.placedFrom = new DatePicker(page.getByTestId('Orders.PlacedFrom'));
    this.status = new Dropdown(page.getByTestId('Orders.Status'));
    this.orders = new DataGrid(page.getByTestId('Orders.Grid'));
    this.apply = page.getByRole('button', { name: 'Apply filters' });
  }

  async goto(): Promise<void> {
    await this.page.goto('/orders');
    await expect(this.page.locator('body')).toHaveAttribute('data-hydrated', 'true');
  }

  async applyFilters(): Promise<void> {
    await this.apply.click();
  }
}
