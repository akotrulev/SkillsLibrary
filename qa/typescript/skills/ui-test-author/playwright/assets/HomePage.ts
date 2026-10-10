import type { Locator, Page } from '@playwright/test';

export class HomePage {
  readonly greeting: Locator;

  constructor(private readonly page: Page) {
    this.greeting = page.getByTestId('Home.Greeting');
  }

  async goto(): Promise<void> {
    await this.page.goto('/');
  }
}
