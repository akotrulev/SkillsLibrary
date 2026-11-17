import type { Locator, Page } from '@playwright/test';

type WebMcp = Page['webmcp'];
type WebMcpTool = Awaited<ReturnType<WebMcp['tools']>>[number];

export class ProductPage {
  readonly cartBadge: Locator;
  private readonly webmcp: WebMcp;

  constructor(private readonly page: Page) {
    this.cartBadge = page.getByTestId('Cart.Badge');
    this.webmcp = page.webmcp;
  }

  async goto(sku: string): Promise<void> {
    await this.page.goto(`/products/${sku}`);
  }

  async toolNames(timeout: number): Promise<string[]> {
    const tools = await this.webmcp.tools({ timeout });
    return tools.map(tool => tool.name);
  }

  async tool(name: string, timeout: number): Promise<WebMcpTool | undefined> {
    const tools = await this.webmcp.tools({ timeout });
    return tools.find(tool => tool.name === name);
  }

  callTool(name: string, input: Parameters<WebMcp['callTool']>[1], timeout: number): ReturnType<WebMcp['callTool']> {
    return this.webmcp.callTool(name, input, { timeout });
  }
}
