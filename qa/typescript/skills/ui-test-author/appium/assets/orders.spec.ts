import { expect } from '@wdio/globals';
import { requiredEnv } from './env.js';
import { LoginPage } from './LoginPage.js';

describe('Orders', () => {
  it('Should_ShowOrderTitle_When_OrderIsInHistory', async () => {
    const login = new LoginPage();
    await login.verifyPageLoaded();
    const orders = await login.signIn(requiredEnv('E2E_USER'), requiredEnv('E2E_PASSWORD'));
    await orders.verifyPageLoaded();
    const orderNumber = requiredEnv('E2E_ORDER_NUMBER');

    const title = await orders.row(orderNumber).title();

    expect({ orderNumber, title }).toEqual({ orderNumber, title: requiredEnv('E2E_ORDER_TITLE') });
  });
});
