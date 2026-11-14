# Stripe sandbox at the API layer (Playwright Test 1.64 + `stripe`)

Test cards and tokens checked against [docs.stripe.com/testing](https://docs.stripe.com/testing) and test clocks
against [docs.stripe.com/billing/testing/test-clocks/api-advanced-usage](https://docs.stripe.com/billing/testing/test-clocks/api-advanced-usage)
on 2026-11-14. SDK surface checked in the `stripe` 23.1.0 source (`testHelpers.testClocks`,
`webhooks.generateTestHeaderString`, `Stripe.API_VERSION`).

## Versions

| Package | Version | Note |
|---|---|---|
| `stripe` | **23.1.0** | Node ≥ 20. Each major pins one Stripe API version (`Stripe.API_VERSION`); match the SUT's major, never up-level it as a side effect |
| `@playwright/test` | the lane pin | API specs run in an `api` project on `APIRequestContext` (`api-test-author/playwright`) |
| Stripe CLI | 1.55.11 | `stripe listen` / `stripe trigger` — see `webhooks.md` |

## 1. The guard and the sandbox fixture

`tests/support/stripeSandbox.ts` holds the key, refuses a live one, reads provider state and owns cleanup;
`tests/payments.fixtures.ts` exposes it as a fixture whose teardown runs the cleanup.

```typescript
import { expect } from '@playwright/test';
import Stripe from 'stripe';

const TEST_MODE_PREFIXES = ['sk_test_', 'rk_test_'] as const;
const CANCELLABLE: ReadonlySet<Stripe.PaymentIntent.Status> = new Set([
  'requires_payment_method',
  'requires_confirmation',
  'requires_action',
  'requires_capture',
]);

export function sandboxKey(): string {
  const key = process.env.STRIPE_SECRET_KEY;
  if (key === undefined || key.trim() === '') {
    throw new Error('STRIPE_SECRET_KEY is not set');
  }
  if (!TEST_MODE_PREFIXES.some((prefix) => key.startsWith(prefix))) {
    throw new Error(`Refusing to run payment tests: STRIPE_SECRET_KEY starts with '${key.slice(0, 8)}', not a test-mode prefix`);
  }
  return key;
}

export class StripeSandbox {
  private readonly stripe = new Stripe(sandboxKey());
  private readonly paymentIntentIds: string[] = [];
  private readonly clockIds: string[] = [];

  track(paymentIntentId: string): void {
    this.paymentIntentIds.push(paymentIntentId);
  }

  async paymentIntent(id: string): Promise<Stripe.PaymentIntent> {
    const intent = await this.stripe.paymentIntents.retrieve(id);
    if (intent.livemode) {
      throw new Error(`PaymentIntent ${id} is live-mode: the SUT is not on a sandbox key`);
    }
    return intent;
  }

  async refundsFor(paymentIntentId: string): Promise<Stripe.Refund[]> {
    return (await this.stripe.refunds.list({ payment_intent: paymentIntentId })).data;
  }

  async startClock(frozenTime: Date, name: string): Promise<Stripe.TestHelpers.TestClock> {
    const clock = await this.stripe.testHelpers.testClocks.create({
      frozen_time: Math.floor(frozenTime.getTime() / 1000),
      name,
    });
    this.clockIds.push(clock.id);
    return clock;
  }

  async customerOnClock(clockId: string, paymentMethodToken: string): Promise<Stripe.Customer> {
    const customer = await this.stripe.customers.create({
      test_clock: clockId,
      email: `qa.${crypto.randomUUID()}@example.test`,
    });
    const method = await this.stripe.paymentMethods.attach(paymentMethodToken, { customer: customer.id });
    return this.stripe.customers.update(customer.id, {
      invoice_settings: { default_payment_method: method.id },
    });
  }

  async advanceClock(clockId: string, frozenTime: Date): Promise<void> {
    await this.stripe.testHelpers.testClocks.advance(clockId, {
      frozen_time: Math.floor(frozenTime.getTime() / 1000),
    });
    await expect
      .poll(async () => (await this.stripe.testHelpers.testClocks.retrieve(clockId)).status, {
        message: `test clock ${clockId} to finish advancing`,
        timeout: 90_000,
        intervals: [1_000],
      })
      .toBe('ready');
  }

  async cleanUp(): Promise<void> {
    for (const id of this.paymentIntentIds) {
      const intent = await this.stripe.paymentIntents.retrieve(id);
      if (CANCELLABLE.has(intent.status)) {
        await this.stripe.paymentIntents.cancel(id);
      }
    }
    for (const clockId of this.clockIds) {
      await this.stripe.testHelpers.testClocks.del(clockId);
    }
  }
}
```

```typescript
import { test as base } from './fixtures';
import { createCheckoutClient, type CheckoutClient } from '../src/clients/checkout/checkoutClient';
import { StripeSandbox } from './support/stripeSandbox';

type PaymentFixtures = { stripeSandbox: StripeSandbox; checkout: CheckoutClient };

export const test = base.extend<PaymentFixtures>({
  stripeSandbox: async ({}, use) => {
    const sandbox = new StripeSandbox();
    await use(sandbox);
    await sandbox.cleanUp();
  },
  checkout: async ({ shopperRequest }, use) => {
    await use(createCheckoutClient(shopperRequest));
  },
});

export { expect } from '@playwright/test';
```

- `shopperRequest` is the signed-in identity fixture from `api-test-author/playwright`.
- The guard covers the suite's key. The SUT holds its own: a PaymentIntent the SUT created under another account or
  a live key cannot be read with the test key (`resource_missing`), and the `livemode` check catches the rest.
- Deleting a clock deletes its customers and cancels their subscriptions. Succeeded payments stay in the sandbox;
  tag what the SUT creates with an order id in `metadata` so a leftover can be traced.

## 2. Test cards

```typescript
export const testCards = {
  visa: 'pm_card_visa',
  genericDecline: 'pm_card_visa_chargeDeclined',
  insufficientFunds: 'pm_card_visa_chargeDeclinedInsufficientFunds',
  lostCard: 'pm_card_visa_chargeDeclinedLostCard',
  expiredCard: 'pm_card_chargeDeclinedExpiredCard',
  incorrectCvc: 'pm_card_chargeDeclinedIncorrectCvc',
  authenticationAlways: 'pm_card_authenticationRequired',
  dispute: 'pm_card_createDispute',
  refundFails: 'pm_card_refundFail',
} as const;
```

| Scenario | Number (UI only) | Token (API) | Outcome on the PaymentIntent |
|---|---|---|---|
| Success | `4242424242424242` | `pm_card_visa` | `succeeded` |
| Generic decline | `4000000000000002` | `pm_card_visa_chargeDeclined` | `card_declined` / `generic_decline` |
| Insufficient funds | `4000000000009995` | `pm_card_visa_chargeDeclinedInsufficientFunds` | `card_declined` / `insufficient_funds` |
| Lost card | `4000000000009987` | `pm_card_visa_chargeDeclinedLostCard` | `card_declined` / `lost_card` |
| Expired card | `4000000000000069` | `pm_card_chargeDeclinedExpiredCard` | code `expired_card`, no decline code |
| Incorrect CVC | `4000000000000127` | `pm_card_chargeDeclinedIncorrectCvc` | code `incorrect_cvc`, no decline code |
| 3DS always | `4000002760003184` | `pm_card_authenticationRequired` | `requires_action` until the challenge is answered |
| 3DS unless set up | `4000002500003155` | `pm_card_authenticationRequiredOnSetup` | `requires_action` on-session; off-session after setup succeeds |
| 3DS then declined | `4000008260003178` | `pm_card_authenticationRequiredChargeDeclinedInsufficientFunds` | challenge, then `insufficient_funds` |
| 3DS failed | `4000002760003184`, answer **Fail** | — | `requires_payment_method`, code `payment_intent_authentication_failure` |
| Dispute (fraudulent) | `4000000000000259` | `pm_card_createDispute` | `charge.dispute.created` after the charge |
| Refund fails later | `4000000000005126` | `pm_card_refundFail` | refund `succeeded`, then `failed` |
| Refund pending | `4000000000007726` | `pm_card_pendingRefund` | refund `pending`, then `succeeded` |

In the UI, any future expiry (`12/34`) and any three-digit CVC work. Expired and incorrect-CVC declines set
`code`, not `decline_code`: give them their own table asserted on `last_payment_error.code`.

## 3. The SUT contract used in the samples

The samples assume `POST /api/checkout/orders` (creates an order), `POST /api/checkout/orders/{id}/payments`
(body `{ paymentMethodId }`, header `Idempotency-Key`; `200` payment or `402` problem with `declineCode` and
`paymentIntentId`), `POST /api/checkout/orders/{id}/refunds` and `GET /api/checkout/orders/{id}`. Take yours from
the contract. `createCheckoutClient` follows the lane's raw + typed layering (typed methods assert the exact status
and `Schema.parse` the body); `orders.twoMugsIn('EUR')` is an ObjectMother over a seeded catalog where a mug costs
EUR 34.00 / JPY 500.

## 4. Payment outcomes

```typescript
import { randomUUID } from 'node:crypto';
import { expect, test } from '../payments.fixtures';
import { PaymentProblemSchema } from '../../src/models/checkout/payment.schema';
import { orders } from '../support/orders';
import { testCards } from '../support/testCards';

test('Should_MarkOrderPaid_When_CardSucceeds', async ({ checkout, stripeSandbox }) => {
  const order = await checkout.createOrder(orders.twoMugsIn('EUR'));

  const payment = await checkout.pay(order.id, { paymentMethodId: testCards.visa }, randomUUID());
  stripeSandbox.track(payment.paymentIntentId);

  const intent = await stripeSandbox.paymentIntent(payment.paymentIntentId);
  expect((await checkout.getOrder(order.id)).status).toBe('Paid');
  expect({ status: intent.status, amount: intent.amount }).toEqual({ status: 'succeeded', amount: order.totalMinor });
});

const declines = [
  { card: testCards.genericDecline, declineCode: 'generic_decline' },
  { card: testCards.insufficientFunds, declineCode: 'insufficient_funds' },
  { card: testCards.lostCard, declineCode: 'lost_card' },
] as const;

for (const { card, declineCode } of declines) {
  test(`Should_Return402With_${declineCode}_When_CardIsDeclined`, async ({ checkout, stripeSandbox }) => {
    const order = await checkout.createOrder(orders.twoMugsIn('EUR'));

    const response = await checkout.payRaw(order.id, { paymentMethodId: card }, randomUUID());

    expect(response.status(), await response.text()).toBe(402);
    const problem = PaymentProblemSchema.parse(await response.json());
    stripeSandbox.track(problem.paymentIntentId);
    const intent = await stripeSandbox.paymentIntent(problem.paymentIntentId);
    expect(problem.declineCode).toBe(declineCode);
    expect((await checkout.getOrder(order.id)).status).toBe('PaymentFailed');
    expect({ status: intent.status, declineCode: intent.last_payment_error?.decline_code }).toEqual({
      status: 'requires_payment_method',
      declineCode,
    });
  });
}

test('Should_LeaveOrderAwaitingAuthentication_When_CardRequires3DSecure', async ({ checkout, stripeSandbox }) => {
  const order = await checkout.createOrder(orders.twoMugsIn('EUR'));

  const payment = await checkout.pay(order.id, { paymentMethodId: testCards.authenticationAlways }, randomUUID());
  stripeSandbox.track(payment.paymentIntentId);

  expect((await checkout.getOrder(order.id)).status).toBe('AwaitingAuthentication');
  expect((await stripeSandbox.paymentIntent(payment.paymentIntentId)).status).toBe('requires_action');
});
```

- The `for` loop sits at module level and generates one named test per row; no test body branches.
- A body that fails `PaymentProblemSchema.parse` throws a `ZodError` whose `issues[].path` names the field; the
  status line above it already printed the raw body.
- The 3DS spec stops at `requires_action`: answering the challenge needs a browser (`checkout-ui.md`), and the
  fixture's teardown cancels the open intent.

## 5. Minor units, idempotency, refunds

```typescript
const currencies = [
  { currency: 'EUR', expectedMinor: 6800 },
  { currency: 'JPY', expectedMinor: 1000 },
] as const;

for (const { currency, expectedMinor } of currencies) {
  test(`Should_ChargeTotalInMinorUnits_When_OrderIsPaidIn_${currency}`, async ({ checkout, stripeSandbox }) => {
    const order = await checkout.createOrder(orders.twoMugsIn(currency));

    const payment = await checkout.pay(order.id, { paymentMethodId: testCards.visa }, randomUUID());
    stripeSandbox.track(payment.paymentIntentId);

    const intent = await stripeSandbox.paymentIntent(payment.paymentIntentId);
    expect({ amount: intent.amount, currency: intent.currency }).toEqual({
      amount: expectedMinor,
      currency: currency.toLowerCase(),
    });
  });
}

test('Should_ReuseOnePaymentIntent_When_PayIsRetriedWithSameIdempotencyKey', async ({ checkout, stripeSandbox }) => {
  const order = await checkout.createOrder(orders.twoMugsIn('EUR'));
  const key = randomUUID();
  const first = await checkout.pay(order.id, { paymentMethodId: testCards.visa }, key);
  stripeSandbox.track(first.paymentIntentId);

  const retried = await checkout.pay(order.id, { paymentMethodId: testCards.visa }, key);

  expect(retried.paymentIntentId).toBe(first.paymentIntentId);
});

const refunds = [
  { refundMinor: 6800, orderStatus: 'Refunded' },
  { refundMinor: 1500, orderStatus: 'PartiallyRefunded' },
] as const;

for (const { refundMinor, orderStatus } of refunds) {
  test(`Should_SetOrder${orderStatus}_When_${refundMinor}IsRefunded`, async ({ checkout, stripeSandbox }) => {
    const order = await checkout.createOrder(orders.twoMugsIn('EUR'));
    const payment = await checkout.pay(order.id, { paymentMethodId: testCards.visa }, randomUUID());
    stripeSandbox.track(payment.paymentIntentId);

    await checkout.refund(order.id, { amountMinor: refundMinor });

    const issued = await stripeSandbox.refundsFor(payment.paymentIntentId);
    expect((await checkout.getOrder(order.id)).status).toBe(orderStatus);
    expect(issued.map(({ amount, status }) => ({ amount, status }))).toEqual([{ amount: refundMinor, status: 'succeeded' }]);
  });
}
```

- Zero-decimal currencies (JPY, KRW) take the whole amount; three-decimal ones (KWD, BHD) take three decimals and
  must end in `0`. Check Stripe's currency page before adding a row.
- The idempotency spec proves the SUT forwards a stable key to Stripe (`{ idempotencyKey }` request option) or
  dedupes itself. Two different ids mean a retried click can charge twice.
- Async refund outcomes (`pm_card_refundFail`, `pm_card_pendingRefund`) end through a webhook: assert them in the
  webhook suite.

## 6. Subscriptions with a test clock

The SUT must accept an existing Stripe customer in its test environment (a documented seam), and `stripe listen`
must forward `invoice.*` events to it (`webhooks.md` §3).

```typescript
test('Should_RecordSecondPaidInvoice_When_MonthlySubscriptionRenews', async ({ stripeSandbox, subscriptions }) => {
  const start = new Date('2026-01-01T09:00:00Z');
  const clock = await stripeSandbox.startClock(start, 'monthly renewal');
  const customer = await stripeSandbox.customerOnClock(clock.id, testCards.visa);
  const subscription = await subscriptions.subscribe({ customerId: customer.id, priceId: plans.monthlyPriceId });

  await stripeSandbox.advanceClock(clock.id, new Date('2026-02-01T11:00:00Z'));

  await expect
    .poll(async () => (await subscriptions.get(subscription.id)).paidInvoices, { timeout: 60_000, intervals: [2_000] })
    .toBe(2);
  expect((await subscriptions.get(subscription.id)).status).toBe('Active');
});
```

- `subscriptions` is a client fixture built like `checkout`; `plans.monthlyPriceId` is the sandbox price the
  test environment seeds.
- A clock can only move forward, at most two billing intervals per advance; a renewal invoice stays `draft` for
  about an hour, so advance past that window.
- Up to three customers per clock. A clock is deleted automatically after 30 days; the fixture deletes it now.
- Objects a clock generates are left out of unfiltered list calls: filter by customer or clock.

## Anti-patterns

- A `sk_live_` key in a CI variable "because the sandbox was down" — the guard throws; keep it that way.
- `expect([200, 402]).toContain(status)` — pin the one status the card produces.
- Asserting the SUT's success message and never retrieving the PaymentIntent.
- Raw card numbers in API calls — use the `pm_card_*` token.
- `page.waitForTimeout` while a clock advances or a webhook lands — `expect.poll` with a deadline.
- One test card shared by parallel scenarios that save it to a customer — card state carries over; give each its own.
