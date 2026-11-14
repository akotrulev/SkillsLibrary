# Checkout and 3DS2 in the browser (Playwright Test 1.64)

Built on the fixture model of `qa/typescript/skills/ui-test-author/playwright` (`testIdAttribute: 'data-testid'`).
The `stripeSandbox` fixture is the one from `stripe-api.md`.

## 1. Why frames, and which ones

Stripe renders the card fields inside its own iframe, and the 3DS2 test challenge inside a modal iframe that
holds a **second** iframe with the issuer's (here: Stripe's test) page. Playwright reaches both with
`frameLocator` chains; no `Frame` handle is ever stored, and every action auto-waits for the frame to attach.

The iframe selectors and the challenge's button names are **Stripe's markup, not a contract**. The values below
were observed with Stripe.js v3 and the Payment Element; before you pin them, run `npx playwright codegen` against
your checkout, take the challenge once, and copy what the inspector shows. They live in one page object so a
Stripe change is a one-file fix.

| Frame | Observed selector | Anchored on |
|---|---|---|
| Card fields | `iframe[title='Secure payment input frame']` inside `Checkout.PaymentElement` | the app's `data-testid` container |
| 3DS2 modal | `iframe[src*='three-ds-2-challenge']` | top-level page |
| Challenge page | `#challengeFrame` inside the modal | the modal frame |

If your recording shows a third level (some flows add an `acsFrame`), add one more `.frameLocator(...)` in
`StripeChallenge` and nowhere else.

## 2. Page objects

```typescript
import type { FrameLocator, Locator, Page } from '@playwright/test';

export class StripeChallenge {
  private readonly challenge: FrameLocator;

  constructor(page: Page) {
    this.challenge = page.frameLocator("iframe[src*='three-ds-2-challenge']").frameLocator('#challengeFrame');
  }

  async complete(): Promise<void> {
    await this.challenge.getByRole('button', { name: 'Complete' }).click();
  }

  async fail(): Promise<void> {
    await this.challenge.getByRole('button', { name: 'Fail' }).click();
  }
}

export class CheckoutPage {
  readonly challenge: StripeChallenge;
  readonly confirmation: Locator;
  readonly paymentError: Locator;
  private readonly cardFrame: FrameLocator;

  constructor(private readonly page: Page) {
    this.cardFrame = page.getByTestId('Checkout.PaymentElement').frameLocator("iframe[title='Secure payment input frame']");
    this.challenge = new StripeChallenge(page);
    this.confirmation = page.getByTestId('Checkout.Confirmation');
    this.paymentError = page.getByTestId('Checkout.PaymentError');
  }

  async openWithTwoMugs(): Promise<void> {
    await this.page.goto('/checkout?sku=MUG&qty=2');
  }

  async orderId(): Promise<string> {
    return this.page.getByTestId('Checkout.OrderId').innerText();
  }

  async payWithCard(cardNumber: string): Promise<void> {
    await this.cardFrame.getByRole('textbox', { name: 'Card number' }).fill(cardNumber);
    await this.cardFrame.getByRole('textbox', { name: 'Expiration date' }).fill('12 / 34');
    await this.cardFrame.getByRole('textbox', { name: 'Security code' }).fill('123');
    await this.page.getByTestId('Checkout.Pay').click();
  }
}

export const testCardNumbers = {
  visa: '4242424242424242',
  genericDecline: '4000000000000002',
  insufficientFunds: '4000000000009995',
  authenticationAlways: '4000002760003184',
} as const;
```

The UI types card numbers (`stripe-api.md` §2); API specs never use them. Country and postal-code fields appear
in the Payment Element for some locales: fill them in `payWithCard` when your recording shows them.

## 3. Fixtures — the order and its PaymentIntent

```typescript
import { z } from 'zod';
import { test as base } from './fixtures';
import { CheckoutPage } from './CheckoutPage';
import { StripeSandbox } from './support/stripeSandbox';

const OrderViewSchema = z.object({ id: z.string(), status: z.string(), paymentIntentId: z.string() });
type OrderView = z.infer<typeof OrderViewSchema>;

type CheckoutFixtures = {
  stripeSandbox: StripeSandbox;
  checkoutPage: CheckoutPage;
  orderOf: (orderId: string) => Promise<OrderView>;
  openCheckout: () => Promise<OrderView>;
};

export const test = base.extend<CheckoutFixtures>({
  stripeSandbox: async ({}, use) => {
    const sandbox = new StripeSandbox();
    await use(sandbox);
    await sandbox.cleanUp();
  },
  checkoutPage: async ({ page }, use) => {
    await use(new CheckoutPage(page));
  },
  orderOf: async ({ page }, use) => {
    await use(async (orderId) => {
      const response = await page.request.get(`/api/checkout/orders/${orderId}`);
      if (!response.ok()) {
        throw new Error(`GET order ${orderId} returned ${response.status()}: ${await response.text()}`);
      }
      return OrderViewSchema.parse(await response.json());
    });
  },
  openCheckout: async ({ checkoutPage, orderOf, stripeSandbox }, use) => {
    await use(async () => {
      await checkoutPage.openWithTwoMugs();
      const order = await orderOf(await checkoutPage.orderId());
      stripeSandbox.track(order.paymentIntentId);
      return order;
    });
  },
});

export { expect } from '@playwright/test';
```

`page.request` shares the context's base URL and cookies, so it reads the order as the signed-in shopper. The
sample SUT creates the PaymentIntent when the checkout page opens and shows the order id; read the id from
wherever your page exposes it (a `data-testid`, or the `payment_intent` query parameter Stripe appends to the
`return_url` after a redirect).

## 4. Specs

```typescript
import { expect, test } from './checkout.fixtures';
import { testCardNumbers } from './CheckoutPage';
import { checkoutCopy } from './support/checkoutCopy';

test('Should_ConfirmOrderAndCapturePayment_When_ShopperCompletesAuthentication', async ({ checkoutPage, openCheckout, stripeSandbox }) => {
  const order = await openCheckout();
  await checkoutPage.payWithCard(testCardNumbers.authenticationAlways);

  await checkoutPage.challenge.complete();

  await expect(checkoutPage.confirmation).toBeVisible();
  expect((await stripeSandbox.paymentIntent(order.paymentIntentId)).status).toBe('succeeded');
});

test('Should_ShowAuthenticationErrorAndLeaveIntentUnpaid_When_ShopperFailsAuthentication', async ({ checkoutPage, openCheckout, stripeSandbox }) => {
  const order = await openCheckout();
  await checkoutPage.payWithCard(testCardNumbers.authenticationAlways);

  await checkoutPage.challenge.fail();

  await expect(checkoutPage.paymentError).toHaveText(checkoutCopy.authenticationFailed);
  const intent = await stripeSandbox.paymentIntent(order.paymentIntentId);
  expect({ status: intent.status, code: intent.last_payment_error?.code }).toEqual({
    status: 'requires_payment_method',
    code: 'payment_intent_authentication_failure',
  });
});

const declinedCards = [
  { cardNumber: testCardNumbers.genericDecline, declineCode: 'generic_decline' },
  { cardNumber: testCardNumbers.insufficientFunds, declineCode: 'insufficient_funds' },
] as const;

for (const { cardNumber, declineCode } of declinedCards) {
  test(`Should_ShowDeclineAndKeepOrderUnpaid_When_CardIs_${declineCode}`, async ({ checkoutPage, openCheckout, orderOf, stripeSandbox }) => {
    const order = await openCheckout();

    await checkoutPage.payWithCard(cardNumber);

    await expect(checkoutPage.paymentError).toBeVisible();
    expect((await stripeSandbox.paymentIntent(order.paymentIntentId)).last_payment_error?.decline_code).toBe(declineCode);
    expect((await orderOf(order.id)).status).toBe('AwaitingPayment');
  });
}
```

- `expect(locator)` is the wait: it retries until the confirmation or error renders. Never wait on the modal
  closing with `page.waitForTimeout`.
- `checkoutCopy` holds the app's own error strings from the copy deck. Do not assert Stripe's wording.
- Payment specs run serially per card when they save cards to customers; plain checkout specs are safe in parallel
  because every one opens its own order.

## Anti-patterns

- `page.frames()[2]` or a stored `Frame` — indexes shift when Stripe adds a frame; chain `frameLocator`.
- Locating the card field by a CSS class from Stripe's bundle — use the role and accessible name.
- `page.waitForTimeout` "for the 3DS modal" — the click on the challenge button already waits for it.
- Treating the confirmation banner as proof of payment — retrieve the PaymentIntent.
- Typing a `pm_card_*` token into the card field — the UI takes card numbers; tokens are for API calls.
