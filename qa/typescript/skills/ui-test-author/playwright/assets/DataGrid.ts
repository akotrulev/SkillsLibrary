import type { Locator } from '@playwright/test';
import { GridRow } from './GridRow';

export class DataGrid {
  private readonly rows: Locator;

  constructor(private readonly root: Locator) {
    this.rows = root.getByTestId('DataGrid.Row');
  }

  row(key: string): GridRow {
    const match = this.rows.filter({ has: this.root.page().getByText(key, { exact: true }) });
    return new GridRow(match, key);
  }

  column(name: string): Locator {
    return this.root.getByTestId(`DataGrid.Cell.${name}`).describe(`${name} column`);
  }

  async sortBy(column: string): Promise<void> {
    await this.root.getByRole('columnheader', { name: column, exact: true }).click();
  }
}
