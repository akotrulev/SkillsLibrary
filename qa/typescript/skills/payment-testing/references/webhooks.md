# Testing the SUT's Stripe webhook handler (TypeScript)

Signature scheme checked against the `stripe` 23.1.0 source (`webhooks.generateTestHeaderString`,
`webhooks.constructEvent`, default tolerance 300 s) and the CLI against
[docs.stripe.com/cli/listen](https://docs.stripe.com/cli/listen) on 2026-11-14.

Two ways in, used for different questions:

| Question | Way in | Why |
|---|---|---|
| Does the handler verify signatures and apply an event once? | **Signed test events** posted straight to the SUT | Deterministic: the spec owns the event id, the body and the timestamp |
| Does a real Stripe event reach the handler and move the order? | **`stripe listen --forward-to`** in the local run or CI job | The real delivery path, real event shape, real API version |

Stripe can deliver one event more than once and in any order. A handler that is not idempotent on the event id
ships a second parcel or books a second ledger row; that is the defect these specs exist for.

## 1. Signing an event

`StripeEventBuilder` builds the body; `stripe.webhooks.generateTestHeaderString` builds the `Stripe-Signature`
header (`t=<unix>,v1=<hex HMAC-SHA256 of "<t>.<body>">`). The secret is the one the SUT is configured with
(`STRIPE_WEBHOOK_SECRET`).

```typescript
import Stripe from 'stripe';
import { sandboxKey } from './stripeSandbox';

export class StripeEventBuilder {
  private id = `evt_qa_${crypto.randomUUID().replaceAll('-', '')}`;
  private type = 'payment_intent.succeeded';
  private apiVersion: string = Stripe.API_VERSION;
  private created = new Date();
  private dataObject: object = {};

  withId(id: string): this {
    this.id = id;
    return this;
  }

  ofType(type: string): this {
    this.type = type;
    return this;
  }

  withApiVersion(apiVersion: string): this {
    this.apiVersion = apiVersion;
    return this;
  }

  createdAt(created: Date): this {
    this.created = created;
    return this;
  }

  about(object: object): this {
    this.dataObject = structuredClone(object);
    return this;
  }

  build(): string {
    return JSON.stringify({
      id: this.id,
      object: 'event',
      type: this.type,
      api_version: this.apiVersion,
      created: Math.floor(this.created.getTime() / 1000),
      livemode: false,
      pending_webhooks: 1,
      data: { object: this.dataObject },
    });
  }
}

export class WebhookSigner {
  private readonly stripe = new Stripe(sandboxKey());

  constructor(private readonly secret: string) {}

  headerFor(payload: string, signedAt: Date = new Date()): string {
    return this.stripe.webhooks.generateTestHeaderString({
      payload,
      secret: this.secret,
      timestamp: Math.floor(signedAt.getTime() / 1000),
    });
  }
}
```

- The event's `data.object` is the **real** sandbox PaymentIntent the SUT created (retrieved through the
  `stripeSandbox` fixture), so a handler that re-reads the intent from Stripe finds it.
- `api_version` defaults to the SDK's pinned version, so a handler that checks it sees a match.
- The payload is sent byte for byte. `webhookClient.deliverRaw(payload, signature)` posts with
  `data: payload` as a **string** and `headers: { 'content-type': 'application/json', 'stripe-signature': signature }`
  — never an object, which `APIRequestContext` re-serialises and breaks the signature.

Add the fixtures to `payments.fixtures.ts`:

```typescript
webhookSigner: async ({}, use) => {
  const secret = process.env.STRIPE_WEBHOOK_SECRET;
  if (secret === undefined) {
    throw new Error('STRIPE_WEBHOOK_SECRET is not set');
  }
  await use(new WebhookSigner(secret));
},
webhooks: async ({ request }, use) => {
  await use(createWebhookClient(request));
},
paidIntentOf: async ({ checkout, stripeSandbox }, use) => {
  await use(async (orderId: string) => {
    const payment = await checkout.pay(orderId, { paymentMethodId: testCards.visa }, crypto.randomUUID());
    stripeSandbox.track(payment.paymentIntentId);
    return stripeSandbox.paymentIntent(payment.paymentIntentId);
  });
},
```

## 2. Idempotency and signature failure

The SUT in the samples fulfils on `payment_intent.succeeded` only (Stripe's recommendation), creating one shipment
per order; the pay endpoint itself creates none. Use the side effect your handler owns.

```typescript
import { expect, test } from '../payments.fixtures';
import { StripeEventBuilder, WebhookSigner } from '../support/stripeEvents';
import { orders } from '../support/orders';

test.describe('Stripe webhook handler', () => {
  test('Should_CreateOneShipment_When_SameEventIsDeliveredTwice', async ({ checkout, webhooks, webhookSigner, paidIntentOf }) => {
    const order = await checkout.createOrder(orders.twoMugsIn('EUR'));
    const payload = new StripeEventBuilder().ofType('payment_intent.succeeded').about(await paidIntentOf(order.id)).build();

    const first = await webhooks.deliverRaw(payload, webhookSigner.headerFor(payload));
    const duplicate = await webhooks.deliverRaw(payload, webhookSigner.headerFor(payload));

    expect(first.status(), await first.text()).toBe(200);
    expect(duplicate.status(), await duplicate.text()).toBe(200);
    expect(await checkout.getShipments(order.id)).toHaveLength(1);
  });

  test('Should_Return400AndShipNothing_When_SignatureUsesWrongSecret', async ({ checkout, webhooks, paidIntentOf }) => {
    const order = await checkout.createOrder(orders.twoMugsIn('EUR'));
    const payload = new StripeEventBuilder().ofType('payment_intent.succeeded').about(await paidIntentOf(order.id)).build();
    const forger = new WebhookSigner('whsec_not_the_endpoint_secret');

    const response = await webhooks.deliverRaw(payload, forger.headerFor(payload));

    expect(response.status(), await response.text()).toBe(400);
    expect(await checkout.getShipments(order.id)).toEqual([]);
  });

  test('Should_Return400_When_SignatureIsOlderThanTolerance', async ({ checkout, webhooks, webhookSigner, paidIntentOf }) => {
    const order = await checkout.createOrder(orders.twoMugsIn('EUR'));
    const payload = new StripeEventBuilder().ofType('payment_intent.succeeded').about(await paidIntentOf(order.id)).build();
    const tenMinutesAgo = new Date(Date.now() - 10 * 60 * 1000);

    const response = await webhooks.deliverRaw(payload, webhookSigner.headerFor(payload, tenMinutesAgo));

    expect(response.status(), await response.text()).toBe(400);
  });
});
```

- Run these specs in a project **without** `stripe listen` forwarding to the same SUT, or the real
  `payment_intent.succeeded` arrives too and the shipment count is no longer the spec's to control.
- The status your handler returns for a bad signature is the contract's: pin that one value.
- Also worth a spec each: an unknown event type returns `200` and changes nothing; an event for a PaymentIntent the
  SUT never created returns `200` and changes nothing.

## 3. The real delivery path: `stripe listen` and `stripe trigger`

```bash
export STRIPE_API_KEY="$STRIPE_SECRET_KEY"
export STRIPE_WEBHOOK_SECRET="$(stripe listen --print-secret)"
stripe listen \
  --events payment_intent.succeeded,payment_intent.payment_failed,charge.refunded,charge.dispute.created,invoice.paid,invoice.payment_failed \
  --forward-to http://localhost:8080/webhooks/stripe > stripe-listen.log 2>&1 &
```

- `--forward-to` needs `--events` (or `--all-snapshot`); without one the CLI exits with an error.
- The listener's signing secret is stable across restarts of `stripe listen`, so export it **before** the SUT
  starts and start the SUT with it (a `webServer` entry in `playwright.config.ts` inherits the environment).
- The CLI never gets `--live`. It reads `STRIPE_API_KEY` from the test-mode secret; the CI step runs the same
  prefix check as `sandboxKey()` before starting it.
- Keep `stripe-listen.log` as a CI artifact: it lists every forwarded event id and the SUT's response code.

End-to-end specs on this path drive the SUT's own flow and wait for the webhook-driven state:

```typescript
test('Should_MarkOrderShipped_When_StripeDeliversPaymentSucceeded', async ({ checkout, paidIntentOf }) => {
  const order = await checkout.createOrder(orders.twoMugsIn('EUR'));

  await paidIntentOf(order.id);

  await expect
    .poll(async () => (await checkout.getOrder(order.id)).status, { timeout: 30_000, intervals: [500] })
    .toBe('Shipped');
  expect(await checkout.getShipments(order.id)).toHaveLength(1);
});
```

`stripe trigger payment_intent.succeeded` creates a fresh PaymentIntent the SUT never saw: use it as a smoke check
that the endpoint answers `200` to an unknown intent (read `stripe-listen.log`), not as an order spec.

| Async outcome | Card / action | Event the handler must apply |
|---|---|---|
| Refund fails after succeeding | `pm_card_refundFail`, then refund | `refund.failed` (and `charge.refund.updated`) |
| Refund settles later | `pm_card_pendingRefund`, then refund | `refund.updated` to `succeeded` |
| Dispute opened | `pm_card_createDispute` | `charge.dispute.created` |
| Renewal paid / failed | test clock advance (`stripe-api.md` §6) | `invoice.paid` / `invoice.payment_failed` |

Confirm the event names your SUT subscribes to against its endpoint configuration; the list above is the minimum
a card shop handles.
