import { $$, browser } from '@wdio/globals';
import { testIdSelector } from './BasePage.js';

export class OrderRow {
  private static readonly ROW_ID = 'OrderRow';
  private static readonly NUMBER_ID = 'OrderRow.Number';
  private static readonly TITLE_ID = 'OrderRow.Title';
  private static readonly STATUS_ID = 'OrderRow.Status';
  private static readonly TIMEOUT_MS = 10_000;

  constructor(private readonly orderNumber: string) {}

  async title(): Promise<string> {
    return (await this.root()).$(testIdSelector(OrderRow.TITLE_ID)).getText();
  }

  async status(): Promise<string> {
    return (await this.root()).$(testIdSelector(OrderRow.STATUS_ID)).getText();
  }

  async open(): Promise<void> {
    await (await this.root()).click();
  }

  private async root(): Promise<WebdriverIO.Element> {
    return browser.waitUntil(() => this.matchingRow(), {
      timeout: OrderRow.TIMEOUT_MS,
      timeoutMsg: `No ${OrderRow.ROW_ID} shows order ${this.orderNumber}`,
    });
  }

  private async matchingRow(): Promise<WebdriverIO.Element | undefined> {
    return $$(testIdSelector(OrderRow.ROW_ID)).findSeries(
      async (candidate) => (await candidate.$(testIdSelector(OrderRow.NUMBER_ID)).getText()) === this.orderNumber,
    );
  }
}
