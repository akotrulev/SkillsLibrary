import type { Locator } from '@playwright/test';

export class DatePicker {
  readonly selected: Locator;
  private readonly open: Locator;
  private readonly calendar: Locator;

  constructor(root: Locator) {
    this.selected = root.getByRole('textbox').describe('Selected date');
    this.open = root.getByRole('button', { name: 'Choose date' });
    this.calendar = root.getByRole('dialog');
  }

  async select(date: Date): Promise<void> {
    await this.open.click();
    await this.calendar.getByRole('combobox', { name: 'Year' }).selectOption(String(date.getUTCFullYear()));
    await this.calendar
      .getByRole('combobox', { name: 'Month' })
      .selectOption({ label: date.toLocaleString('en-US', { month: 'long', timeZone: 'UTC' }) });
    await this.calendar.getByRole('gridcell', { name: String(date.getUTCDate()), exact: true }).click();
  }
}
