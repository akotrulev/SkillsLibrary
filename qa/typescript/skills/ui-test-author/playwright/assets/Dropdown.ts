import type { Locator } from '@playwright/test';

export class Dropdown {
  constructor(private readonly root: Locator) {}

  async select(option: string): Promise<void> {
    await this.root.selectOption({ label: option });
  }
}
