import { expect, test } from './fixtures';

test.describe('Orders', { tag: '@regression' }, () => {
  test.beforeEach(async ({ ordersPage, seededOrder }) => {
    await ordersPage.goto();
    await ordersPage.placedFrom.select(seededOrder.placedOn);
    await ordersPage.applyFilters();
  });

  test('Should_ShowCancelledStatus_When_OrderIsCancelledFromTheGrid', async ({ ordersPage, seededOrder }) => {
    await ordersPage.orders.row(seededOrder.number).runAction('Cancel');

    await expect(ordersPage.orders.row(seededOrder.number).cell('Status'), `status of order ${seededOrder.number}`).toHaveText(
      'Cancelled',
    );
  });

  test('Should_HideOrder_When_StatusFilterExcludesIt', async ({ ordersPage, seededOrder }) => {
    await ordersPage.status.select('Shipped');
    await ordersPage.applyFilters();

    await expect(ordersPage.orders.row(seededOrder.number).cell('Title'), `order ${seededOrder.number} row`).toBeHidden();
  });
});
