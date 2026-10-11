import { expect } from '@wdio/globals';
import { BasePage } from './BasePage.js';
import { OrderRow } from './OrderRow.js';

export class OrdersPage extends BasePage {
  private static readonly LIST_ID = 'Orders.List';

  private get list() {
    return this.byTestId(OrdersPage.LIST_ID);
  }

  async verifyPageLoaded(): Promise<void> {
    await expect(this.list).toBeDisplayed({ message: 'Expected OrdersPage to be visible but the orders list was not found' });
  }

  row(orderNumber: string): OrderRow {
    return new OrderRow(orderNumber);
  }
}
