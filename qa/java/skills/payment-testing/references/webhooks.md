# Testing the SUT's Stripe webhook handler (Java)

Signature scheme checked against the `stripe-java` 34.1.0 source (`Webhook.Signature.generateSignatureHeader`,
`Webhook.constructEvent`, default tolerance 300 s) and the CLI against
[docs.stripe.com/cli/listen](https://docs.stripe.com/cli/listen) on 2026-11-14.

Two ways in, used for different questions:

| Question | Way in | Why |
|---|---|---|
| Does the handler verify signatures and apply an event once? | **Signed test events** posted straight to the SUT | Deterministic: the test owns the event id, the body and the timestamp |
| Does a real Stripe event reach the handler and move the order? | **`stripe listen --forward-to`** in the local run or CI job | The real delivery path, real event shape, real API version |

Stripe can deliver one event more than once and in any order. A handler that is not idempotent on the event id
ships a second parcel or books a second ledger row; that is the defect these tests exist for.

## 1. Signing an event

`StripeEventBuilder` builds the body; `Webhook.Signature.generateSignatureHeader` builds the `Stripe-Signature`
header (`t=<unix>,v1=<hex HMAC-SHA256 of "<t>.<body>">`). The secret is the one the SUT is configured with
(`STRIPE_WEBHOOK_SECRET`).

```java
package com.example.apitests.support;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.stripe.Stripe;
import com.stripe.model.StripeObject;

import java.time.Instant;
import java.util.UUID;

public final class StripeEventBuilder {
    private String id = "evt_qa_" + UUID.randomUUID().toString().replace("-", "");
    private String type = "payment_intent.succeeded";
    private String apiVersion = Stripe.API_VERSION;
    private Instant created = Instant.now();
    private JsonObject dataObject = new JsonObject();

    public StripeEventBuilder withId(String id) {
        this.id = id;
        return this;
    }

    public StripeEventBuilder ofType(String type) {
        this.type = type;
        return this;
    }

    public StripeEventBuilder withApiVersion(String apiVersion) {
        this.apiVersion = apiVersion;
        return this;
    }

    public StripeEventBuilder createdAt(Instant created) {
        this.created = created;
        return this;
    }

    public StripeEventBuilder about(StripeObject object) {
        this.dataObject = JsonParser.parseString(object.toJson()).getAsJsonObject();
        return this;
    }

    public String build() {
        JsonObject data = new JsonObject();
        data.add("object", dataObject.deepCopy());
        JsonObject event = new JsonObject();
        event.addProperty("id", id);
        event.addProperty("object", "event");
        event.addProperty("type", type);
        event.addProperty("api_version", apiVersion);
        event.addProperty("created", created.getEpochSecond());
        event.addProperty("livemode", false);
        event.addProperty("pending_webhooks", 1);
        event.add("data", data);
        return event.toString();
    }
}
```

```java
package com.example.apitests.support;

import com.stripe.net.Webhook;

import java.security.GeneralSecurityException;
import java.time.Instant;

public final class WebhookSigner {
    private final String secret;

    public WebhookSigner(String secret) {
        this.secret = secret;
    }

    public String headerFor(String payload) throws GeneralSecurityException {
        return headerFor(payload, Instant.now());
    }

    public String headerFor(String payload, Instant signedAt) throws GeneralSecurityException {
        return Webhook.Signature.generateSignatureHeader(payload, secret, signedAt.getEpochSecond());
    }
}
```

- `stripe-java` already ships Gson, so the builder adds no dependency.
- The event's `data.object` is the **real** sandbox PaymentIntent the SUT created (retrieved through
  `StripeSandbox`), so a handler that re-reads the intent from Stripe finds it.
- `api_version` defaults to the SDK's pinned version; a handler that checks the version sees a match.
- The payload is sent byte for byte. `WebhookClient.deliver(payload, signature)` sets
  `.contentType(ContentType.JSON).header("Stripe-Signature", signature).body(payload)` with the `String` —
  never a POJO body, which REST Assured re-serialises and breaks the signature.

## 2. Idempotency and signature failure

The SUT in the samples fulfils on `payment_intent.succeeded` only (Stripe's recommendation), creating one shipment
per order; the pay endpoint itself creates none. Use the side effect your handler owns.

```java
public class StripeWebhookTest extends BaseTest {

    private StripeSandbox stripe;
    private CheckoutClient checkout;
    private WebhookSigner signer;
    private final WebhookClient webhooks = new WebhookClient();

    @BeforeMethod
    public void connectToSandbox() {
        stripe = StripeSandbox.fromEnvironment();
        checkout = new CheckoutClient(AuthHelper.getToken(TestUsers.SHOPPER));
        signer = new WebhookSigner(Config.required("STRIPE_WEBHOOK_SECRET"));
    }

    @AfterMethod(alwaysRun = true)
    public void releaseSandboxObjects() throws StripeException {
        stripe.cleanUp();
    }

    @Test
    public void Should_CreateOneShipment_When_SameEventIsDeliveredTwice() throws Exception {
        OrderDto order = checkout.createOrder(Orders.twoMugsIn("EUR"), HttpStatus.SC_CREATED);
        String payload = new StripeEventBuilder().ofType("payment_intent.succeeded").about(paidIntentOf(order)).build();

        Response first = webhooks.deliver(payload, signer.headerFor(payload));
        Response duplicate = webhooks.deliver(payload, signer.headerFor(payload));

        SoftAssert soft = new SoftAssert();
        soft.assertEquals(first.getStatusCode(), HttpStatus.SC_OK, first.asString());
        soft.assertEquals(duplicate.getStatusCode(), HttpStatus.SC_OK, duplicate.asString());
        soft.assertEquals(checkout.getShipments(order.id(), HttpStatus.SC_OK).size(), 1);
        soft.assertAll();
    }

    @Test
    public void Should_Return400AndShipNothing_When_SignatureUsesWrongSecret() throws Exception {
        OrderDto order = checkout.createOrder(Orders.twoMugsIn("EUR"), HttpStatus.SC_CREATED);
        String payload = new StripeEventBuilder().ofType("payment_intent.succeeded").about(paidIntentOf(order)).build();
        WebhookSigner forger = new WebhookSigner("whsec_not_the_endpoint_secret");

        Response response = webhooks.deliver(payload, forger.headerFor(payload));

        SoftAssert soft = new SoftAssert();
        soft.assertEquals(response.getStatusCode(), HttpStatus.SC_BAD_REQUEST, response.asString());
        soft.assertEquals(checkout.getShipments(order.id(), HttpStatus.SC_OK), List.of());
        soft.assertAll();
    }

    @Test
    public void Should_Return400_When_SignatureIsOlderThanTolerance() throws Exception {
        OrderDto order = checkout.createOrder(Orders.twoMugsIn("EUR"), HttpStatus.SC_CREATED);
        String payload = new StripeEventBuilder().ofType("payment_intent.succeeded").about(paidIntentOf(order)).build();

        Response response = webhooks.deliver(payload, signer.headerFor(payload, Instant.now().minus(Duration.ofMinutes(10))));

        Assert.assertEquals(response.getStatusCode(), HttpStatus.SC_BAD_REQUEST, response.asString());
    }

    private PaymentIntent paidIntentOf(OrderDto order) throws StripeException {
        PaymentDto payment = checkout.pay(order.id(), new PayOrderDto(TestCards.VISA), IdempotencyKey.next(), HttpStatus.SC_OK);
        stripe.track(payment.paymentIntentId());
        return stripe.paymentIntent(payment.paymentIntentId());
    }
}
```

- `Config.required` is the lane's env reader (`BaseTest` configuration); it throws with the variable's name.
- Run this class **without** `stripe listen` forwarding to the same SUT, or the real `payment_intent.succeeded`
  arrives too and the shipment count is no longer the test's to control. Give it its own job or environment.
- The status your handler returns for a bad signature is the contract's: pin that one value.
- Also worth a case each: an unknown event type returns `200` and changes nothing; an event for a PaymentIntent
  the SUT never created returns `200` and changes nothing.

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
  starts and start the SUT with it.
- The CLI never gets `--live`. It reads `STRIPE_API_KEY` from the test-mode secret; the CI step runs the same
  prefix check as `StripeSandbox` before starting it.
- Keep `stripe-listen.log` as a CI artifact: it lists every forwarded event id and the SUT's response code.

End-to-end tests on this path drive the SUT's own flow and wait for the webhook-driven state:

```java
@Test
public void Should_MarkOrderShipped_When_StripeDeliversPaymentSucceeded() throws StripeException {
    OrderDto order = checkout.createOrder(Orders.twoMugsIn("EUR"), HttpStatus.SC_CREATED);
    PaymentDto payment = checkout.pay(order.id(), new PayOrderDto(TestCards.VISA), IdempotencyKey.next(), HttpStatus.SC_OK);
    stripe.track(payment.paymentIntentId());

    await("order " + order.id() + " shipped")
            .atMost(Duration.ofSeconds(30))
            .pollInterval(Duration.ofMillis(500))
            .until(() -> checkout.getOrder(order.id(), HttpStatus.SC_OK).status(), "Shipped"::equals);

    Assert.assertEquals(checkout.getShipments(order.id(), HttpStatus.SC_OK).size(), 1);
}
```

`stripe trigger payment_intent.succeeded` creates a fresh PaymentIntent the SUT never saw: use it as a smoke check
that the endpoint answers `200` to an unknown intent (read `stripe-listen.log`), not as an order test.

| Async outcome | Card / action | Event the handler must apply |
|---|---|---|
| Refund fails after succeeding | `pm_card_refundFail`, then refund | `refund.failed` (and `charge.refund.updated`) |
| Refund settles later | `pm_card_pendingRefund`, then refund | `refund.updated` to `succeeded` |
| Dispute opened | `pm_card_createDispute` | `charge.dispute.created` |
| Renewal paid / failed | test clock advance (`stripe-api.md` §6) | `invoice.paid` / `invoice.payment_failed` |

Confirm the event names your SUT subscribes to against its endpoint configuration; the list above is the minimum
a card shop handles.
