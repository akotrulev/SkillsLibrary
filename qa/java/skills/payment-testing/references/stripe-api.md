# Stripe sandbox at the API layer (TestNG + REST Assured + stripe-java)

Test cards and tokens checked against [docs.stripe.com/testing](https://docs.stripe.com/testing) and test clocks
against [docs.stripe.com/billing/testing/test-clocks/api-advanced-usage](https://docs.stripe.com/billing/testing/test-clocks/api-advanced-usage)
on 2026-11-14. SDK surface checked in the `stripe-java` 34.1.0 source (`StripeClient.v1()`, `Webhook.Signature`).

## Versions

| Artifact | Version | Note |
|---|---|---|
| `com.stripe:stripe-java` | **34.1.0** | Each major pins one Stripe API version (`Stripe.API_VERSION`); match the SUT's major, never up-level it as a side effect |
| `io.rest-assured:rest-assured` | the project's | Clients come from `api-client-writer`; this skill adds no HTTP code of its own |
| `org.awaitility:awaitility` | 4.2.2 | The lane's bounded poll |
| Stripe CLI | 1.55.11 | `stripe listen` / `stripe trigger` — see `webhooks.md` |

```kotlin
testImplementation("com.stripe:stripe-java:34.1.0")
testImplementation("org.awaitility:awaitility:4.2.2")
```

## 1. The guard and the sandbox helper

`support/StripeSandbox.java`. The only place that holds the key, refuses a live one, reads provider state and owns
cleanup.

```java
package com.example.apitests.support;

import com.stripe.StripeClient;
import com.stripe.exception.StripeException;
import com.stripe.model.Customer;
import com.stripe.model.PaymentIntent;
import com.stripe.model.PaymentMethod;
import com.stripe.model.Refund;
import com.stripe.model.testhelpers.TestClock;
import com.stripe.param.CustomerCreateParams;
import com.stripe.param.CustomerUpdateParams;
import com.stripe.param.PaymentMethodAttachParams;
import com.stripe.param.RefundListParams;
import com.stripe.param.testhelpers.TestClockAdvanceParams;
import com.stripe.param.testhelpers.TestClockCreateParams;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.UUID;

import static org.awaitility.Awaitility.await;

public final class StripeSandbox {
    private static final List<String> TEST_MODE_PREFIXES = List.of("sk_test_", "rk_test_");
    private static final Set<String> CANCELLABLE =
            Set.of("requires_payment_method", "requires_confirmation", "requires_action", "requires_capture");

    private final StripeClient client;
    private final List<String> paymentIntentIds = new ArrayList<>();
    private final List<String> clockIds = new ArrayList<>();

    private StripeSandbox(StripeClient client) {
        this.client = client;
    }

    public static StripeSandbox fromEnvironment() {
        String key = System.getenv("STRIPE_SECRET_KEY");
        if (key == null || key.isBlank()) {
            throw new IllegalStateException("STRIPE_SECRET_KEY is not set");
        }
        if (TEST_MODE_PREFIXES.stream().noneMatch(key::startsWith)) {
            throw new IllegalStateException("Refusing to run payment tests: STRIPE_SECRET_KEY starts with '"
                    + key.substring(0, Math.min(8, key.length())) + "', not a test-mode prefix");
        }
        return new StripeSandbox(new StripeClient(key));
    }

    public void track(String paymentIntentId) {
        paymentIntentIds.add(paymentIntentId);
    }

    public PaymentIntent paymentIntent(String id) throws StripeException {
        PaymentIntent intent = client.v1().paymentIntents().retrieve(id);
        if (Boolean.TRUE.equals(intent.getLivemode())) {
            throw new IllegalStateException("PaymentIntent " + id + " is live-mode: the SUT is not on a sandbox key");
        }
        return intent;
    }

    public List<Refund> refundsFor(String paymentIntentId) throws StripeException {
        return client.v1().refunds()
                .list(RefundListParams.builder().setPaymentIntent(paymentIntentId).build())
                .getData();
    }

    public TestClock startClock(Instant frozenTime, String name) throws StripeException {
        TestClock clock = client.v1().testHelpers().testClocks().create(TestClockCreateParams.builder()
                .setFrozenTime(frozenTime.getEpochSecond())
                .setName(name)
                .build());
        clockIds.add(clock.getId());
        return clock;
    }

    public Customer customerOnClock(String clockId, String paymentMethodToken) throws StripeException {
        Customer customer = client.v1().customers().create(CustomerCreateParams.builder()
                .setTestClock(clockId)
                .setEmail("qa." + UUID.randomUUID() + "@example.test")
                .build());
        PaymentMethod method = client.v1().paymentMethods().attach(paymentMethodToken,
                PaymentMethodAttachParams.builder().setCustomer(customer.getId()).build());
        return client.v1().customers().update(customer.getId(), CustomerUpdateParams.builder()
                .setInvoiceSettings(CustomerUpdateParams.InvoiceSettings.builder()
                        .setDefaultPaymentMethod(method.getId())
                        .build())
                .build());
    }

    public void advanceClock(String clockId, Instant frozenTime) throws StripeException {
        client.v1().testHelpers().testClocks().advance(clockId,
                TestClockAdvanceParams.builder().setFrozenTime(frozenTime.getEpochSecond()).build());
        TestClock settled = await("test clock " + clockId + " to stop advancing")
                .atMost(Duration.ofSeconds(90))
                .pollInterval(Duration.ofSeconds(1))
                .until(() -> client.v1().testHelpers().testClocks().retrieve(clockId),
                        clock -> !"advancing".equals(clock.getStatus()));
        if (!"ready".equals(settled.getStatus())) {
            throw new IllegalStateException("Test clock " + clockId + " ended in status " + settled.getStatus());
        }
    }

    public void cleanUp() throws StripeException {
        for (String id : paymentIntentIds) {
            PaymentIntent intent = client.v1().paymentIntents().retrieve(id);
            if (CANCELLABLE.contains(intent.getStatus())) {
                client.v1().paymentIntents().cancel(id);
            }
        }
        for (String clockId : clockIds) {
            client.v1().testHelpers().testClocks().delete(clockId);
        }
        paymentIntentIds.clear();
        clockIds.clear();
    }
}
```

- The guard covers the test's key. The SUT holds its own: a PaymentIntent the SUT created under another account or
  a live key cannot be read with the test key (`resource_missing`), and the `livemode` check catches the rest.
- Deleting a clock deletes its customers and cancels their subscriptions. Succeeded payments stay in the sandbox;
  tag what the SUT creates with an order id in `metadata` so a leftover can be traced.

## 2. Test cards

```java
package com.example.apitests.support;

public final class TestCards {
    public static final String VISA = "pm_card_visa";
    public static final String GENERIC_DECLINE = "pm_card_visa_chargeDeclined";
    public static final String INSUFFICIENT_FUNDS = "pm_card_visa_chargeDeclinedInsufficientFunds";
    public static final String LOST_CARD = "pm_card_visa_chargeDeclinedLostCard";
    public static final String EXPIRED_CARD = "pm_card_chargeDeclinedExpiredCard";
    public static final String INCORRECT_CVC = "pm_card_chargeDeclinedIncorrectCvc";
    public static final String AUTHENTICATION_ALWAYS = "pm_card_authenticationRequired";
    public static final String DISPUTE = "pm_card_createDispute";
    public static final String REFUND_FAILS = "pm_card_refundFail";

    private TestCards() {
    }
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
`code`, not `decline_code`: test them in their own data provider against `getLastPaymentError().getCode()`.

## 3. The SUT contract used in the samples

The samples assume `POST /api/checkout/orders` (creates an order), `POST /api/checkout/orders/{id}/payments`
(body `PayOrderDto(paymentMethodId)`, header `Idempotency-Key`; `200 PaymentDto` or `402` problem with
`declineCode` and `paymentIntentId`), `POST /api/checkout/orders/{id}/refunds` and `GET /api/checkout/orders/{id}`.
Take yours from the contract. `CheckoutClient` comes from `api-client-writer` with the lane's raw `Response` and
typed `int expectedStatus` overloads; `Orders.twoMugsIn("EUR")` is an ObjectMother over a seeded catalog where a
mug costs EUR 34.00 / JPY 500.

## 4. Payment outcomes

```java
package com.example.apitests.tests.checkout.payments;

import com.example.apitests.base.BaseTest;
import com.example.apitests.clients.AuthHelper;
import com.example.apitests.clients.checkout.CheckoutClient;
import com.example.apitests.models.checkout.OrderDto;
import com.example.apitests.models.checkout.PayOrderDto;
import com.example.apitests.models.checkout.PaymentDto;
import com.example.apitests.models.checkout.PaymentProblemDto;
import com.example.apitests.support.IdempotencyKey;
import com.example.apitests.support.Orders;
import com.example.apitests.support.StripeSandbox;
import com.example.apitests.support.TestCards;
import com.stripe.exception.StripeException;
import com.stripe.model.PaymentIntent;
import io.restassured.response.Response;
import org.apache.http.HttpStatus;
import org.testng.Assert;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.DataProvider;
import org.testng.annotations.Test;
import org.testng.asserts.SoftAssert;

public class PayOrderTest extends BaseTest {

    private StripeSandbox stripe;
    private CheckoutClient checkout;

    @BeforeMethod
    public void connectToSandbox() {
        stripe = StripeSandbox.fromEnvironment();
        checkout = new CheckoutClient(AuthHelper.getToken(TestUsers.SHOPPER));
    }

    @AfterMethod(alwaysRun = true)
    public void releaseSandboxObjects() throws StripeException {
        stripe.cleanUp();
    }

    @Test
    public void Should_MarkOrderPaid_When_CardSucceeds() throws StripeException {
        OrderDto order = checkout.createOrder(Orders.twoMugsIn("EUR"), HttpStatus.SC_CREATED);

        PaymentDto payment = checkout.pay(order.id(), new PayOrderDto(TestCards.VISA), IdempotencyKey.next(), HttpStatus.SC_OK);
        stripe.track(payment.paymentIntentId());

        PaymentIntent intent = stripe.paymentIntent(payment.paymentIntentId());
        SoftAssert soft = new SoftAssert();
        soft.assertEquals(checkout.getOrder(order.id(), HttpStatus.SC_OK).status(), "Paid");
        soft.assertEquals(intent.getStatus(), "succeeded");
        soft.assertEquals(intent.getAmount().longValue(), order.totalMinor());
        soft.assertAll();
    }

    @DataProvider
    public Object[][] declines() {
        return new Object[][] {
                {TestCards.GENERIC_DECLINE, "generic_decline"},
                {TestCards.INSUFFICIENT_FUNDS, "insufficient_funds"},
                {TestCards.LOST_CARD, "lost_card"},
        };
    }

    @Test(dataProvider = "declines")
    public void Should_Return402WithDeclineCode_When_CardIsDeclined(String paymentMethod, String declineCode)
            throws StripeException {
        OrderDto order = checkout.createOrder(Orders.twoMugsIn("EUR"), HttpStatus.SC_CREATED);

        Response response = checkout.pay(order.id(), new PayOrderDto(paymentMethod), IdempotencyKey.next());

        Assert.assertEquals(response.getStatusCode(), HttpStatus.SC_PAYMENT_REQUIRED, response.asString());
        PaymentProblemDto problem = response.as(PaymentProblemDto.class);
        stripe.track(problem.paymentIntentId());
        PaymentIntent intent = stripe.paymentIntent(problem.paymentIntentId());
        SoftAssert soft = new SoftAssert();
        soft.assertEquals(problem.declineCode(), declineCode);
        soft.assertEquals(checkout.getOrder(order.id(), HttpStatus.SC_OK).status(), "PaymentFailed");
        soft.assertEquals(intent.getStatus(), "requires_payment_method");
        soft.assertEquals(intent.getLastPaymentError().getDeclineCode(), declineCode);
        soft.assertAll();
    }

    @Test
    public void Should_LeaveOrderAwaitingAuthentication_When_CardRequires3DSecure() throws StripeException {
        OrderDto order = checkout.createOrder(Orders.twoMugsIn("EUR"), HttpStatus.SC_CREATED);

        PaymentDto payment = checkout.pay(order.id(), new PayOrderDto(TestCards.AUTHENTICATION_ALWAYS), IdempotencyKey.next(), HttpStatus.SC_OK);
        stripe.track(payment.paymentIntentId());

        SoftAssert soft = new SoftAssert();
        soft.assertEquals(checkout.getOrder(order.id(), HttpStatus.SC_OK).status(), "AwaitingAuthentication");
        soft.assertEquals(stripe.paymentIntent(payment.paymentIntentId()).getStatus(), "requires_action");
        soft.assertAll();
    }
}
```

`IdempotencyKey.next()` returns a fresh UUID string. The 3DS test stops at `requires_action`: answering the
challenge needs a browser (`checkout-ui.md`), and the `@AfterMethod` cancels the open intent. A response that does
not deserialize fails with the body: `PaymentProblemDto` is read through the lane's Jackson setup, whose
`MismatchedInputException` names the path.

## 5. Minor units, idempotency, refunds

```java
@DataProvider
public Object[][] currencies() {
    return new Object[][] {{"EUR", 6800L}, {"JPY", 1000L}};
}

@Test(dataProvider = "currencies")
public void Should_ChargeTotalInMinorUnits_When_OrderIsPaid(String currency, long expectedMinor) throws StripeException {
    OrderDto order = checkout.createOrder(Orders.twoMugsIn(currency), HttpStatus.SC_CREATED);

    PaymentDto payment = checkout.pay(order.id(), new PayOrderDto(TestCards.VISA), IdempotencyKey.next(), HttpStatus.SC_OK);
    stripe.track(payment.paymentIntentId());

    PaymentIntent intent = stripe.paymentIntent(payment.paymentIntentId());
    SoftAssert soft = new SoftAssert();
    soft.assertEquals(intent.getAmount().longValue(), expectedMinor);
    soft.assertEquals(intent.getCurrency(), currency.toLowerCase(java.util.Locale.ROOT));
    soft.assertAll();
}

@Test
public void Should_ReuseOnePaymentIntent_When_PayIsRetriedWithSameIdempotencyKey() {
    OrderDto order = checkout.createOrder(Orders.twoMugsIn("EUR"), HttpStatus.SC_CREATED);
    String key = IdempotencyKey.next();
    PaymentDto first = checkout.pay(order.id(), new PayOrderDto(TestCards.VISA), key, HttpStatus.SC_OK);
    stripe.track(first.paymentIntentId());

    PaymentDto retried = checkout.pay(order.id(), new PayOrderDto(TestCards.VISA), key, HttpStatus.SC_OK);

    Assert.assertEquals(retried.paymentIntentId(), first.paymentIntentId());
}

@DataProvider
public Object[][] refunds() {
    return new Object[][] {{6800L, "Refunded"}, {1500L, "PartiallyRefunded"}};
}

@Test(dataProvider = "refunds")
public void Should_RefundRequestedAmount_When_RefundIsIssued(long refundMinor, String orderStatus) throws StripeException {
    OrderDto order = checkout.createOrder(Orders.twoMugsIn("EUR"), HttpStatus.SC_CREATED);
    PaymentDto payment = checkout.pay(order.id(), new PayOrderDto(TestCards.VISA), IdempotencyKey.next(), HttpStatus.SC_OK);
    stripe.track(payment.paymentIntentId());

    checkout.refund(order.id(), new RefundOrderDto(refundMinor), HttpStatus.SC_CREATED);

    List<Refund> refunds = stripe.refundsFor(payment.paymentIntentId());
    SoftAssert soft = new SoftAssert();
    soft.assertEquals(checkout.getOrder(order.id(), HttpStatus.SC_OK).status(), orderStatus);
    soft.assertEquals(refunds.stream().map(refund -> refund.getAmount() + ":" + refund.getStatus()).toList(),
            List.of(refundMinor + ":succeeded"));
    soft.assertAll();
}
```

- Zero-decimal currencies (JPY, KRW) take the whole amount; three-decimal ones (KWD, BHD) take three decimals and
  must end in `0`. Check Stripe's currency page before adding a row.
- The idempotency test proves the SUT forwards a stable key to Stripe (`RequestOptions.builder().setIdempotencyKey`)
  or dedupes itself. Two different ids mean a retried click can charge twice.
- Async refund outcomes (`pm_card_refundFail`, `pm_card_pendingRefund`) end through a webhook: assert them in the
  webhook suite.

## 6. Subscriptions with a test clock

The SUT must accept an existing Stripe customer in its test environment (a documented seam), and `stripe listen`
must forward `invoice.*` events to it (`webhooks.md` §3).

```java
@Test
public void Should_RecordSecondPaidInvoice_When_MonthlySubscriptionRenews() throws StripeException {
    Instant start = Instant.parse("2026-01-01T09:00:00Z");
    TestClock clock = stripe.startClock(start, "monthly renewal");
    Customer customer = stripe.customerOnClock(clock.getId(), TestCards.VISA);
    SubscriptionClient subscriptions = new SubscriptionClient(AuthHelper.getToken(TestUsers.SHOPPER));
    SubscriptionDto subscription = subscriptions.subscribe(new SubscribeDto(customer.getId(), Plans.MONTHLY_PRICE_ID), HttpStatus.SC_CREATED);

    stripe.advanceClock(clock.getId(), start.atZone(ZoneOffset.UTC).plusMonths(1).plusHours(2).toInstant());

    SubscriptionDto renewed = await("second paid invoice on " + subscription.id())
            .atMost(Duration.ofSeconds(60))
            .pollInterval(Duration.ofSeconds(2))
            .until(() -> subscriptions.get(subscription.id(), HttpStatus.SC_OK), current -> current.paidInvoices() == 2);
    Assert.assertEquals(renewed.status(), "Active");
}
```

- A clock can only move forward, at most two billing intervals per advance; a renewal invoice stays `draft` for
  about an hour, so advance past that window.
- Up to three customers per clock. A clock is deleted automatically after 30 days; `cleanUp()` deletes it now.
- Objects a clock generates are left out of unfiltered list calls: filter by customer or clock.

## Anti-patterns

- A `sk_live_` key in a CI variable "because the sandbox was down" — the guard throws; keep it that way.
- Accepting either of two statuses in one assertion — pin the one status the card produces.
- Asserting the SUT's success message and never retrieving the PaymentIntent.
- Raw card numbers in API calls — use the `pm_card_*` token.
- `Thread.sleep` while a clock advances or a webhook lands — Awaitility with a deadline.
- One test card shared by parallel scenarios that save it to a customer — card state carries over; give each its own.
