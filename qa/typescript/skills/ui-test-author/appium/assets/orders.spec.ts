import { strict as assert } from 'node:assert';
import { randomUUID } from 'node:crypto';
import { requiredEnv } from './env.js';
import { LoginPage } from './LoginPage.js';
import { OrderSeeder, type SeededOrder } from './OrderSeeder.js';
import type { OrdersPage } from './OrdersPage.js';

describe('Orders', () => {
  const seeder = new OrderSeeder();
  let order: SeededOrder;
  let orders: OrdersPage;

  beforeEach(async () => {
    order = await seeder.create(`QA order ${randomUUID()}`);
    const login = new LoginPage();
    await login.verifyPageLoaded();
    orders = await login.signIn(requiredEnv('E2E_USER'), requiredEnv('E2E_PASSWORD'));
    await orders.verifyPageLoaded();
  });

  afterEach(async () => {
    await seeder.deleteCreated();
  });

  it('Should_ShowOrderTitle_When_OrderIsInHistory', async () => {
    const title = await orders.row(order.number).title();

    assert.equal(title, order.title, `title of order ${order.number}`);
  });
});
