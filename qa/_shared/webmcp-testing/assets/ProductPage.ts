import type { Locator, Page } from '@playwright/test';

export class ProductPage {
  readonly cartBadge: Locator;
  readonly webmcp: Page['webmcp'];

  constructor(private readonly page: Page) {
    this.cartBadge = page.getByTestId('Cart.Badge');
    this.webmcp = page.webmcp;
  }

  async goto(sku: string): Promise<void> {
    await this.page.goto(`/products/${sku}`);
  }
}
