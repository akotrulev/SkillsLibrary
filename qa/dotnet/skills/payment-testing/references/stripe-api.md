# Stripe sandbox at the API layer (NUnit + RestSharp + Stripe.net)

Test cards and tokens checked against [docs.stripe.com/testing](https://docs.stripe.com/testing) and test clocks
against [docs.stripe.com/billing/testing/test-clocks/api-advanced-usage](https://docs.stripe.com/billing/testing/test-clocks/api-advanced-usage)
on 2026-11-14. SDK surface checked in the `Stripe.net` 53.1.0 source (`StripeClient.V1.*`, `EventUtility`).

## Versions

| Package | Version | Note |
|---|---|---|
| `Stripe.net` | **53.1.0** | Each major pins one Stripe API version (`StripeConfiguration.ApiVersion`); match the SUT's major, never up-level it as a side effect |
| `RestSharp` | 112.1.0 | The lane's pin (`api-project-setup`); clients come from `api-client-writer` |
| Stripe CLI | 1.55.11 | `stripe listen` / `stripe trigger` — see `webhooks.md` |

## 1. The guard and the sandbox helper

`ApiTests/Support/StripeSandbox.cs`. The only place that holds the key, refuses a live one, reads provider state
and owns cleanup.

```csharp
using NUnit.Framework;
using Stripe;
using Stripe.TestHelpers;

namespace ApiTests.Support;

public sealed class StripeSandbox
{
    private static readonly string[] TestModePrefixes = ["sk_test_", "rk_test_"];
    private static readonly string[] CancellableStatuses =
        ["requires_payment_method", "requires_confirmation", "requires_action", "requires_capture"];

    private readonly StripeClient _client;
    private readonly List<string> _paymentIntentIds = [];
    private readonly List<string> _clockIds = [];

    private StripeSandbox(StripeClient client) => _client = client;

    public static StripeSandbox FromEnvironment()
    {
        var key = Environment.GetEnvironmentVariable("STRIPE_SECRET_KEY");
        if (string.IsNullOrWhiteSpace(key))
        {
            throw new InvalidOperationException("STRIPE_SECRET_KEY is not set");
        }
        if (!TestModePrefixes.Any(key.StartsWith))
        {
            throw new InvalidOperationException(
                $"Refusing to run payment tests: STRIPE_SECRET_KEY starts with '{key[..Math.Min(8, key.Length)]}', not a test-mode prefix");
        }
        return new StripeSandbox(new StripeClient(key));
    }

    public void Track(string paymentIntentId) => _paymentIntentIds.Add(paymentIntentId);

    public async Task<PaymentIntent> PaymentIntentAsync(string id)
    {
        var intent = await _client.V1.PaymentIntents.GetAsync(id);
        if (intent.Livemode)
        {
            throw new InvalidOperationException($"PaymentIntent {id} is live-mode: the SUT is not on a sandbox key");
        }
        return intent;
    }

    public async Task<IReadOnlyList<Refund>> RefundsForAsync(string paymentIntentId) =>
        (await _client.V1.Refunds.ListAsync(new RefundListOptions { PaymentIntent = paymentIntentId })).Data;

    public async Task<TestClock> StartClockAsync(DateTime frozenTime)
    {
        var clock = await _client.V1.TestHelpers.TestClocks.CreateAsync(
            new TestClockCreateOptions { FrozenTime = frozenTime, Name = TestContext.CurrentContext.Test.Name });
        _clockIds.Add(clock.Id);
        return clock;
    }

    public async Task<Customer> CustomerOnClockAsync(string clockId, string paymentMethodToken)
    {
        var customer = await _client.V1.Customers.CreateAsync(new CustomerCreateOptions
        {
            TestClock = clockId,
            Email = $"qa.{Guid.NewGuid():N}@example.test",
        });
        var method = await _client.V1.PaymentMethods.AttachAsync(
            paymentMethodToken, new PaymentMethodAttachOptions { Customer = customer.Id });
        return await _client.V1.Customers.UpdateAsync(customer.Id, new CustomerUpdateOptions
        {
            InvoiceSettings = new CustomerInvoiceSettingsOptions { DefaultPaymentMethod = method.Id },
        });
    }

    public async Task AdvanceClockAsync(string clockId, DateTime frozenTime)
    {
        await _client.V1.TestHelpers.TestClocks.AdvanceAsync(clockId, new TestClockAdvanceOptions { FrozenTime = frozenTime });
        var settled = await Polling.WaitForAsync<TestClock>(
            async ct => await _client.V1.TestHelpers.TestClocks.GetAsync(clockId, cancellationToken: ct),
            clock => clock.Status != "advancing",
            timeout: TimeSpan.FromSeconds(90),
            interval: TimeSpan.FromSeconds(1));
        if (settled.Status != "ready")
        {
            throw new InvalidOperationException($"Test clock {clockId} ended in status {settled.Status}");
        }
    }

    public async Task CleanUpAsync()
    {
        foreach (var id in _paymentIntentIds)
        {
            var intent = await _client.V1.PaymentIntents.GetAsync(id);
            if (CancellableStatuses.Contains(intent.Status))
            {
                await _client.V1.PaymentIntents.CancelAsync(id);
            }
        }
        foreach (var clockId in _clockIds)
        {
            await _client.V1.TestHelpers.TestClocks.DeleteAsync(clockId);
        }
        _paymentIntentIds.Clear();
        _clockIds.Clear();
    }
}
```

- `Polling.WaitForAsync` is the bounded poll from `qa/dotnet/skills/db-testing/connection`, kept once in a static
  `Polling` class in `Support`.
- The guard covers the test's key. The SUT holds its own: a PaymentIntent the SUT created under another account or
  a live key cannot be read with the test key (`resource_missing`), and the `Livemode` check catches the rest.
- Deleting a clock deletes its customers and cancels their subscriptions. Succeeded payments stay in the sandbox;
  tag what the SUT creates with an order id in `metadata` so a leftover can be traced.

## 2. Test cards

`ApiTests/Support/TestCards.cs` — `const` so they can feed `[TestCase]`.

```csharp
namespace ApiTests.Support;

public static class TestCards
{
    public const string Visa = "pm_card_visa";
    public const string GenericDecline = "pm_card_visa_chargeDeclined";
    public const string InsufficientFunds = "pm_card_visa_chargeDeclinedInsufficientFunds";
    public const string LostCard = "pm_card_visa_chargeDeclinedLostCard";
    public const string ExpiredCard = "pm_card_chargeDeclinedExpiredCard";
    public const string IncorrectCvc = "pm_card_chargeDeclinedIncorrectCvc";
    public const string AuthenticationAlways = "pm_card_authenticationRequired";
    public const string AuthenticationThenInsufficientFunds = "pm_card_authenticationRequiredChargeDeclinedInsufficientFunds";
    public const string Dispute = "pm_card_createDispute";
    public const string RefundFails = "pm_card_refundFail";
}
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
`code`, not `decline_code`: test them in their own `[TestCase]` set against `LastPaymentError.Code`.

## 3. The SUT contract used in the samples

The samples assume `POST /api/checkout/orders` (creates an order), `POST /api/checkout/orders/{id}/payments`
(body `PayOrderDto(PaymentMethodId)`, header `Idempotency-Key`; `200 PaymentDto` or `402` problem with
`declineCode` and `paymentIntentId`), `POST /api/checkout/orders/{id}/refunds` and `GET /api/checkout/orders/{id}`.
Take yours from the contract. `CheckoutClient` comes from `api-client-writer` with the lane's raw and typed
overloads; `Orders.TwoMugsIn("EUR")` is an ObjectMother over a seeded catalog where a mug costs EUR 34.00 / JPY 500.

## 4. Payment outcomes

```csharp
using System.Net;
using ApiTests.Clients.Checkout;
using ApiTests.Models.Checkout;
using ApiTests.Support;
using NUnit.Framework;

namespace ApiTests.Tests;

[TestFixture]
public class PayOrderTests : BaseApiTest
{
    private StripeSandbox _stripe = null!;

    [SetUp]
    public void ConnectToSandbox() => _stripe = StripeSandbox.FromEnvironment();

    [TearDown]
    public Task ReleaseSandboxObjects() => _stripe.CleanUpAsync();

    [Test]
    public async Task Should_MarkOrderPaid_When_CardSucceeds()
    {
        var checkout = new CheckoutClient(AuthToken);
        var order = checkout.CreateOrder(Orders.TwoMugsIn("EUR"), HttpStatusCode.Created);

        var payment = checkout.Pay(order.Id, new PayOrderDto(TestCards.Visa), IdempotencyKey.New(), HttpStatusCode.OK);
        _stripe.Track(payment.PaymentIntentId);

        var intent = await _stripe.PaymentIntentAsync(payment.PaymentIntentId);
        Assert.Multiple(() =>
        {
            Assert.That(checkout.GetOrder(order.Id, HttpStatusCode.OK).Status, Is.EqualTo("Paid"));
            Assert.That(intent.Status, Is.EqualTo("succeeded"));
            Assert.That(intent.Amount, Is.EqualTo(order.TotalMinor));
        });
    }

    [TestCase(TestCards.GenericDecline, "generic_decline")]
    [TestCase(TestCards.InsufficientFunds, "insufficient_funds")]
    [TestCase(TestCards.LostCard, "lost_card")]
    public async Task Should_Return402WithDeclineCode_When_CardIsDeclined(string paymentMethod, string declineCode)
    {
        var checkout = new CheckoutClient(AuthToken);
        var order = checkout.CreateOrder(Orders.TwoMugsIn("EUR"), HttpStatusCode.Created);

        var response = checkout.Pay(order.Id, new PayOrderDto(paymentMethod), IdempotencyKey.New());

        AttachBody(response);
        Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.PaymentRequired));
        var problem = Deserialize<PaymentProblemDto>(response);
        _stripe.Track(problem.PaymentIntentId);
        var intent = await _stripe.PaymentIntentAsync(problem.PaymentIntentId);
        Assert.Multiple(() =>
        {
            Assert.That(problem.DeclineCode, Is.EqualTo(declineCode));
            Assert.That(checkout.GetOrder(order.Id, HttpStatusCode.OK).Status, Is.EqualTo("PaymentFailed"));
            Assert.That(intent.Status, Is.EqualTo("requires_payment_method"));
            Assert.That(intent.LastPaymentError.DeclineCode, Is.EqualTo(declineCode));
        });
    }

    [Test]
    public async Task Should_LeaveOrderAwaitingAuthentication_When_CardRequires3DSecure()
    {
        var checkout = new CheckoutClient(AuthToken);
        var order = checkout.CreateOrder(Orders.TwoMugsIn("EUR"), HttpStatusCode.Created);

        var payment = checkout.Pay(order.Id, new PayOrderDto(TestCards.AuthenticationAlways), IdempotencyKey.New(), HttpStatusCode.OK);
        _stripe.Track(payment.PaymentIntentId);

        var intent = await _stripe.PaymentIntentAsync(payment.PaymentIntentId);
        Assert.Multiple(() =>
        {
            Assert.That(checkout.GetOrder(order.Id, HttpStatusCode.OK).Status, Is.EqualTo("AwaitingAuthentication"));
            Assert.That(intent.Status, Is.EqualTo("requires_action"));
        });
    }
}
```

`IdempotencyKey.New()` returns a fresh GUID string. The 3DS test stops at `requires_action`: answering the
challenge needs a browser (`checkout-ui.md`), and teardown cancels the open intent.

## 5. Minor units, idempotency, refunds

```csharp
[TestCase("EUR", 6800L)]
[TestCase("JPY", 1000L)]
public async Task Should_ChargeTotalInMinorUnits_When_OrderIsPaid(string currency, long expectedMinor)
{
    var checkout = new CheckoutClient(AuthToken);
    var order = checkout.CreateOrder(Orders.TwoMugsIn(currency), HttpStatusCode.Created);

    var payment = checkout.Pay(order.Id, new PayOrderDto(TestCards.Visa), IdempotencyKey.New(), HttpStatusCode.OK);
    _stripe.Track(payment.PaymentIntentId);

    var intent = await _stripe.PaymentIntentAsync(payment.PaymentIntentId);
    Assert.That((intent.Amount, intent.Currency), Is.EqualTo((expectedMinor, currency.ToLowerInvariant())));
}

[Test]
public void Should_ReuseOnePaymentIntent_When_PayIsRetriedWithSameIdempotencyKey()
{
    var checkout = new CheckoutClient(AuthToken);
    var order = checkout.CreateOrder(Orders.TwoMugsIn("EUR"), HttpStatusCode.Created);
    var key = IdempotencyKey.New();
    var first = checkout.Pay(order.Id, new PayOrderDto(TestCards.Visa), key, HttpStatusCode.OK);
    _stripe.Track(first.PaymentIntentId);

    var retried = checkout.Pay(order.Id, new PayOrderDto(TestCards.Visa), key, HttpStatusCode.OK);

    Assert.That(retried.PaymentIntentId, Is.EqualTo(first.PaymentIntentId));
}

[TestCase(6800L, "Refunded")]
[TestCase(1500L, "PartiallyRefunded")]
public async Task Should_RefundRequestedAmount_When_RefundIsIssued(long refundMinor, string orderStatus)
{
    var checkout = new CheckoutClient(AuthToken);
    var order = checkout.CreateOrder(Orders.TwoMugsIn("EUR"), HttpStatusCode.Created);
    var payment = checkout.Pay(order.Id, new PayOrderDto(TestCards.Visa), IdempotencyKey.New(), HttpStatusCode.OK);
    _stripe.Track(payment.PaymentIntentId);

    checkout.Refund(order.Id, new RefundOrderDto(refundMinor), HttpStatusCode.Created);

    var refunds = await _stripe.RefundsForAsync(payment.PaymentIntentId);
    Assert.Multiple(() =>
    {
        Assert.That(checkout.GetOrder(order.Id, HttpStatusCode.OK).Status, Is.EqualTo(orderStatus));
        Assert.That(refunds.Select(refund => (refund.Amount, refund.Status)), Is.EqualTo(new[] { (refundMinor, "succeeded") }));
    });
}
```

- Zero-decimal currencies (JPY, KRW) take the whole amount; three-decimal ones (KWD, BHD) take three decimals and
  must end in `0`. Check Stripe's currency page before adding a row.
- The idempotency test proves the SUT forwards a stable key to Stripe (`RequestOptions.IdempotencyKey`) or dedupes
  itself. Two different ids mean a retried click can charge twice.
- Async refund outcomes (`pm_card_refundFail`, `pm_card_pendingRefund`) end through a webhook: assert them in the
  webhook suite.

## 6. Subscriptions with a test clock

The SUT must accept an existing Stripe customer in its test environment (a documented seam), and `stripe listen`
must forward `invoice.*` events to it (`webhooks.md` §3).

```csharp
[Test]
public async Task Should_RecordSecondPaidInvoice_When_MonthlySubscriptionRenews()
{
    var start = new DateTime(2026, 1, 1, 9, 0, 0, DateTimeKind.Utc);
    var clock = await _stripe.StartClockAsync(start);
    var customer = await _stripe.CustomerOnClockAsync(clock.Id, TestCards.Visa);
    var subscriptions = new SubscriptionClient(AuthToken);
    var subscription = subscriptions.Subscribe(new SubscribeDto(customer.Id, Plans.MonthlyPriceId), HttpStatusCode.Created);

    await _stripe.AdvanceClockAsync(clock.Id, start.AddMonths(1).AddHours(2));

    var renewed = await Polling.WaitForAsync<SubscriptionDto>(
        _ => Task.FromResult<SubscriptionDto?>(subscriptions.Get(subscription.Id, HttpStatusCode.OK)),
        current => current.PaidInvoices == 2,
        timeout: TimeSpan.FromSeconds(60),
        interval: TimeSpan.FromSeconds(2));
    Assert.That(renewed.Status, Is.EqualTo("Active"));
}
```

- A clock can only move forward, at most two billing intervals per advance; a renewal invoice stays `draft` for
  about an hour, so advance past that window.
- Up to three customers per clock. A clock is deleted automatically after 30 days; `CleanUpAsync` deletes it now.
- Objects a clock generates are left out of unfiltered list calls: filter by customer or clock.

## Anti-patterns

- A `sk_live_` key in a CI variable "because the sandbox was down" — the guard throws; keep it that way.
- `Assert.That(status, Is.EqualTo(200).Or.EqualTo(402))` — pin the one status the card produces.
- Asserting the SUT's success message and never retrieving the PaymentIntent.
- Raw card numbers in API calls — use the `pm_card_*` token.
- `Task.Delay` while a clock advances or a webhook lands — poll the status with a deadline.
- One test card shared by parallel scenarios that save it to a customer — card state carries over; give each its own.
