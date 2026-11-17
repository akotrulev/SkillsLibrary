import type { Locator } from '@playwright/test';

export class GridRow {
  constructor(
    private readonly root: Locator,
    private readonly key: string,
  ) {}

  cell(column: string): Locator {
    return this.root.getByTestId(`DataGrid.Cell.${column}`).describe(`${column} of row ${this.key}`);
  }

  async select(): Promise<void> {
    await this.root.getByRole('checkbox').check();
  }

  async runAction(action: string): Promise<void> {
    await this.root.getByRole('button', { name: action, exact: true }).click();
  }
}
