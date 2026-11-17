import type { Locator } from '@playwright/test';

export class Combobox {
  private readonly input: Locator;
  private readonly listbox: Locator;

  constructor(root: Locator) {
    this.input = root.getByRole('combobox');
    this.listbox = root.getByRole('listbox');
  }

  async choose(option: string): Promise<void> {
    await this.input.click();
    await this.listbox.getByRole('option', { name: option, exact: true }).click();
  }

  async search(query: string, option: string): Promise<void> {
    await this.input.fill(query);
    await this.listbox.getByRole('option', { name: option, exact: true }).click();
  }
}
