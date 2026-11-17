import type { Locator, Page } from '@playwright/test';

export class HomePage {
  readonly greeting: Locator;

  constructor(private readonly page: Page) {
    this.greeting = page.getByTestId('Home.Greeting').describe('Home greeting');
  }

  async goto(): Promise<void> {
    await this.page.goto('/');
  }
}
