# Testing the SUT's Stripe webhook handler (.NET)

Signature scheme checked against the `Stripe.net` 53.1.0 source (`EventUtility.ComputeSignature`,
`EventUtility.ConstructEvent`, default tolerance 300 s) and the CLI against
[docs.stripe.com/cli/listen](https://docs.stripe.com/cli/listen) on 2026-11-14.

Two ways in, used for different questions:

| Question | Way in | Why |
|---|---|---|
| Does the handler verify signatures and apply an event once? | **Signed test events** posted straight to the SUT | Deterministic: the test owns the event id, the body and the timestamp |
| Does a real Stripe event reach the handler and move the order? | **`stripe listen --forward-to`** in the local run or CI job | The real delivery path, real event shape, real API version |

Stripe can deliver one event more than once and in any order. A handler that is not idempotent on the event id
ships a second parcel or books a second ledger row; that is the defect these tests exist for.

## 1. Signing an event

`StripeEventBuilder` builds the body; `WebhookSigner` builds the `Stripe-Signature` header (`t=<unix>,v1=<hex
HMAC-SHA256 of "<t>.<body>">`). The secret is the one the SUT is configured with (`STRIPE_WEBHOOK_SECRET`).

```csharp
using System.Globalization;
using System.Text.Json.Nodes;
using Stripe;

namespace ApiTests.Support;

public sealed class StripeEventBuilder
{
    private string _id = $"evt_qa_{Guid.NewGuid():N}";
    private string _type = "payment_intent.succeeded";
    private string _apiVersion = StripeConfiguration.ApiVersion;
    private DateTimeOffset _created = DateTimeOffset.UtcNow;
    private JsonNode _dataObject = new JsonObject();

    public StripeEventBuilder WithId(string id) { _id = id; return this; }
    public StripeEventBuilder OfType(string type) { _type = type; return this; }
    public StripeEventBuilder WithApiVersion(string apiVersion) { _apiVersion = apiVersion; return this; }
    public StripeEventBuilder CreatedAt(DateTimeOffset created) { _created = created; return this; }
    public StripeEventBuilder About(StripeEntity entity) { _dataObject = JsonNode.Parse(entity.ToJson())!; return this; }

    public string Build() => new JsonObject
    {
        ["id"] = _id,
        ["object"] = "event",
        ["type"] = _type,
        ["api_version"] = _apiVersion,
        ["created"] = _created.ToUnixTimeSeconds(),
        ["livemode"] = false,
        ["pending_webhooks"] = 1,
        ["data"] = new JsonObject { ["object"] = _dataObject.DeepClone() },
    }.ToJsonString();
}

public sealed class WebhookSigner(string secret)
{
    public string HeaderFor(string payload) => HeaderFor(payload, DateTimeOffset.UtcNow);

    public string HeaderFor(string payload, DateTimeOffset signedAt)
    {
        var timestamp = signedAt.ToUnixTimeSeconds().ToString(CultureInfo.InvariantCulture);
        return $"t={timestamp},v1={EventUtility.ComputeSignature(secret, timestamp, payload)}";
    }
}
```

- The event's `data.object` is the **real** sandbox PaymentIntent the SUT created (retrieved through
  `StripeSandbox`), so a handler that re-reads the intent from Stripe finds it.
- `api_version` defaults to the SDK's pinned version: `EventUtility.ConstructEvent` in a .NET SUT rejects a
  mismatched version unless it opts out.
- The payload is sent byte for byte. `WebhookClient.Deliver(payload, signature)` uses
  `AddStringBody(payload, ContentType.Json)` and the `Stripe-Signature` header — never `AddJsonBody`, which
  re-serialises and breaks the signature.

## 2. Idempotency and signature failure

The SUT in the samples fulfils on `payment_intent.succeeded` only (Stripe's recommendation), creating one shipment
per order; the pay endpoint itself creates none. Use the side effect your handler owns.

```csharp
[TestFixture]
public class StripeWebhookTests : BaseApiTest
{
    private StripeSandbox _stripe = null!;
    private WebhookSigner _signer = null!;

    [SetUp]
    public void ConnectToSandbox()
    {
        _stripe = StripeSandbox.FromEnvironment();
        _signer = new WebhookSigner(Environment.GetEnvironmentVariable("STRIPE_WEBHOOK_SECRET")
            ?? throw new InvalidOperationException("STRIPE_WEBHOOK_SECRET is not set"));
    }

    [TearDown]
    public Task ReleaseSandboxObjects() => _stripe.CleanUpAsync();

    [Test]
    public async Task Should_CreateOneShipment_When_SameEventIsDeliveredTwice()
    {
        var (checkout, order, intent) = await PaidOrderAsync();
        var payload = new StripeEventBuilder().OfType("payment_intent.succeeded").About(intent).Build();
        var webhooks = new WebhookClient();

        var first = webhooks.Deliver(payload, _signer.HeaderFor(payload));
        var duplicate = webhooks.Deliver(payload, _signer.HeaderFor(payload));

        Assert.Multiple(() =>
        {
            Assert.That(first.StatusCode, Is.EqualTo(HttpStatusCode.OK), first.Content);
            Assert.That(duplicate.StatusCode, Is.EqualTo(HttpStatusCode.OK), duplicate.Content);
            Assert.That(checkout.GetShipments(order.Id, HttpStatusCode.OK), Has.Count.EqualTo(1));
        });
    }

    [Test]
    public async Task Should_Return400AndShipNothing_When_SignatureUsesWrongSecret()
    {
        var (checkout, order, intent) = await PaidOrderAsync();
        var payload = new StripeEventBuilder().OfType("payment_intent.succeeded").About(intent).Build();
        var forger = new WebhookSigner("whsec_not_the_endpoint_secret");

        var response = new WebhookClient().Deliver(payload, forger.HeaderFor(payload));

        Assert.Multiple(() =>
        {
            Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.BadRequest), response.Content);
            Assert.That(checkout.GetShipments(order.Id, HttpStatusCode.OK), Is.Empty);
        });
    }

    [Test]
    public async Task Should_Return400_When_SignatureIsOlderThanTolerance()
    {
        var (_, _, intent) = await PaidOrderAsync();
        var payload = new StripeEventBuilder().OfType("payment_intent.succeeded").About(intent).Build();

        var response = new WebhookClient().Deliver(payload, _signer.HeaderFor(payload, DateTimeOffset.UtcNow.AddMinutes(-10)));

        Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.BadRequest), response.Content);
    }

    private async Task<(CheckoutClient, OrderDto, PaymentIntent)> PaidOrderAsync()
    {
        var checkout = new CheckoutClient(AuthToken);
        var order = checkout.CreateOrder(Orders.TwoMugsIn("EUR"), HttpStatusCode.Created);
        var payment = checkout.Pay(order.Id, new PayOrderDto(TestCards.Visa), IdempotencyKey.New(), HttpStatusCode.OK);
        _stripe.Track(payment.PaymentIntentId);
        return (checkout, order, await _stripe.PaymentIntentAsync(payment.PaymentIntentId));
    }
}
```

- Run this fixture **without** `stripe listen` forwarding to the same SUT, or the real `payment_intent.succeeded`
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
- The listener's signing secret is stable across restarts of `stripe listen`, so the SUT can be started with it
  before the listener; export it **before** the SUT starts.
- The CLI never gets `--live`. It reads `STRIPE_API_KEY` from the test-mode secret; the CI step runs the same
  prefix check as `StripeSandbox` before starting it.
- Keep `stripe-listen.log` as a CI artifact: it lists every forwarded event id and the SUT's response code.

End-to-end tests on this path drive the SUT's own flow and wait for the webhook-driven state:

```csharp
[Test]
public async Task Should_MarkOrderShipped_When_StripeDeliversPaymentSucceeded()
{
    var checkout = new CheckoutClient(AuthToken);
    var order = checkout.CreateOrder(Orders.TwoMugsIn("EUR"), HttpStatusCode.Created);
    var payment = checkout.Pay(order.Id, new PayOrderDto(TestCards.Visa), IdempotencyKey.New(), HttpStatusCode.OK);
    _stripe.Track(payment.PaymentIntentId);

    var shipped = await Polling.WaitForAsync<OrderDto>(
        _ => Task.FromResult<OrderDto?>(checkout.GetOrder(order.Id, HttpStatusCode.OK)),
        current => current.Status == "Shipped",
        timeout: TimeSpan.FromSeconds(30),
        interval: TimeSpan.FromMilliseconds(500));

    Assert.That(checkout.GetShipments(shipped.Id, HttpStatusCode.OK), Has.Count.EqualTo(1));
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
