# Checkout and 3DS2 in the browser (Playwright Java 1.63 + TestNG)

Every sample extends `com.example.uitests.support.BaseTest`
(`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`), which sets `data-testid` as the test-id
attribute; the Playwright pin is in that skill's **Versions** table. `StripeSandbox` is the one from
`stripe-api.md`, copied into the UI module's `support` package with `com.stripe:stripe-java` added to its
`testImplementation`.

## 1. Why frames, and which ones

Stripe renders the card fields inside its own iframe, and the 3DS2 test challenge inside a modal iframe that
holds a **second** iframe with the issuer's (here: Stripe's test) page. Playwright reaches both with
`frameLocator` chains; no `Frame` handle is ever stored, and every action auto-waits for the frame to attach.

The iframe selectors and the challenge's button names are **Stripe's markup, not a contract**. The values below
were observed with Stripe.js v3 and the Payment Element; before you pin them, open your checkout with
Playwright's `codegen` (the `com.microsoft.playwright.CLI` main class, run through the build), take the challenge once, and copy what the inspector shows. They live in one page object so a Stripe
change is a one-file fix.

| Frame | Observed selector | Anchored on |
|---|---|---|
| Card fields | `iframe[title='Secure payment input frame']` inside `Checkout.PaymentElement` | the app's `data-testid` container |
| 3DS2 modal | `iframe[src*='three-ds-2-challenge']` | top-level page |
| Challenge page | `#challengeFrame` inside the modal | the modal frame |

If your recording shows a third level (some flows add an `acsFrame`), add one more `.frameLocator(...)` in
`StripeChallenge` and nowhere else.

## 2. Page objects

```java
package com.example.uitests.pages;

import com.microsoft.playwright.FrameLocator;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.AriaRole;

public final class CheckoutPage {
    private final Page page;
    private final FrameLocator cardFrame;
    private final StripeChallenge challenge;

    public CheckoutPage(Page page) {
        this.page = page;
        this.cardFrame = page.getByTestId("Checkout.PaymentElement")
                .frameLocator("iframe[title='Secure payment input frame']");
        this.challenge = new StripeChallenge(page);
    }

    public void openWithTwoMugs() {
        page.navigate("/checkout?sku=MUG&qty=2");
    }

    public String orderId() {
        return page.getByTestId("Checkout.OrderId").innerText();
    }

    public void payWithCard(String cardNumber) {
        cardFrame.getByRole(AriaRole.TEXTBOX, new FrameLocator.GetByRoleOptions().setName("Card number")).fill(cardNumber);
        cardFrame.getByRole(AriaRole.TEXTBOX, new FrameLocator.GetByRoleOptions().setName("Expiration date")).fill("12 / 34");
        cardFrame.getByRole(AriaRole.TEXTBOX, new FrameLocator.GetByRoleOptions().setName("Security code")).fill("123");
        page.getByTestId("Checkout.Pay").click();
    }

    public StripeChallenge challenge() {
        return challenge;
    }

    public Locator confirmation() {
        return page.getByTestId("Checkout.Confirmation");
    }

    public Locator paymentError() {
        return page.getByTestId("Checkout.PaymentError");
    }
}
```

```java
package com.example.uitests.pages;

import com.microsoft.playwright.FrameLocator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.AriaRole;

public final class StripeChallenge {
    private final FrameLocator challenge;

    public StripeChallenge(Page page) {
        this.challenge = page.frameLocator("iframe[src*='three-ds-2-challenge']").frameLocator("#challengeFrame");
    }

    public void complete() {
        challenge.getByRole(AriaRole.BUTTON, new FrameLocator.GetByRoleOptions().setName("Complete")).click();
    }

    public void fail() {
        challenge.getByRole(AriaRole.BUTTON, new FrameLocator.GetByRoleOptions().setName("Fail")).click();
    }
}
```

```java
package com.example.uitests.support;

public final class TestCardNumbers {
    public static final String VISA = "4242424242424242";
    public static final String GENERIC_DECLINE = "4000000000000002";
    public static final String INSUFFICIENT_FUNDS = "4000000000009995";
    public static final String AUTHENTICATION_ALWAYS = "4000002760003184";

    private TestCardNumbers() {
    }
}
```

The UI types card numbers (`stripe-api.md` §2); the API suite never uses them. Country and postal-code fields
appear in the Payment Element for some locales: fill them in `payWithCard` when your recording shows them.

## 3. The PaymentIntent behind the page

```java
package com.example.uitests.support;

import com.google.gson.Gson;
import com.microsoft.playwright.APIResponse;
import com.microsoft.playwright.Page;

public final class OrdersApi {
    private static final Gson GSON = new Gson();
    private final Page page;

    public OrdersApi(Page page) {
        this.page = page;
    }

    public OrderView order(String orderId) {
        APIResponse response = page.request().get("/api/checkout/orders/" + orderId);
        if (!response.ok()) {
            throw new IllegalStateException("GET order " + orderId + " returned " + response.status() + ": " + response.text());
        }
        return GSON.fromJson(response.text(), OrderView.class);
    }

    public record OrderView(String id, String status, String paymentIntentId) {
    }
}
```

`page.request()` shares the context's base URL and cookies, so it reads the order as the signed-in shopper.
Playwright Java already depends on Gson.

## 4. Tests

```java
package com.example.uitests.tests;

import com.example.uitests.pages.CheckoutPage;
import com.example.uitests.support.BaseTest;
import com.example.uitests.support.CheckoutCopy;
import com.example.uitests.support.OrdersApi;
import com.example.uitests.support.OrdersApi.OrderView;
import com.example.uitests.support.StripeSandbox;
import com.example.uitests.support.TestCardNumbers;
import com.stripe.exception.StripeException;
import com.stripe.model.PaymentIntent;
import org.testng.Assert;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.DataProvider;
import org.testng.annotations.Test;
import org.testng.asserts.SoftAssert;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public class CardCheckoutTest extends BaseTest {
    private CheckoutPage checkout;
    private OrdersApi orders;
    private StripeSandbox stripe;

    @BeforeMethod(alwaysRun = true)
    public void createHelpers() {
        stripe = StripeSandbox.fromEnvironment();
        checkout = new CheckoutPage(page);
        orders = new OrdersApi(page);
    }

    @AfterMethod(alwaysRun = true)
    public void releaseSandboxObjects() throws StripeException {
        stripe.cleanUp();
    }

    @Test
    public void Should_ConfirmOrderAndCapturePayment_When_ShopperCompletesAuthentication() throws StripeException {
        OrderView order = openCheckout();
        checkout.payWithCard(TestCardNumbers.AUTHENTICATION_ALWAYS);

        checkout.challenge().complete();

        assertThat(checkout.confirmation()).isVisible();
        Assert.assertEquals(stripe.paymentIntent(order.paymentIntentId()).getStatus(), "succeeded");
    }

    @Test
    public void Should_ShowAuthenticationErrorAndLeaveIntentUnpaid_When_ShopperFailsAuthentication() throws StripeException {
        OrderView order = openCheckout();
        checkout.payWithCard(TestCardNumbers.AUTHENTICATION_ALWAYS);

        checkout.challenge().fail();

        assertThat(checkout.paymentError()).hasText(CheckoutCopy.AUTHENTICATION_FAILED);
        PaymentIntent intent = stripe.paymentIntent(order.paymentIntentId());
        SoftAssert soft = new SoftAssert();
        soft.assertEquals(intent.getStatus(), "requires_payment_method");
        soft.assertEquals(intent.getLastPaymentError().getCode(), "payment_intent_authentication_failure");
        soft.assertAll();
    }

    @DataProvider
    public Object[][] declinedCards() {
        return new Object[][] {
                {TestCardNumbers.GENERIC_DECLINE, "generic_decline"},
                {TestCardNumbers.INSUFFICIENT_FUNDS, "insufficient_funds"},
        };
    }

    @Test(dataProvider = "declinedCards")
    public void Should_ShowDeclineAndKeepOrderUnpaid_When_CardIsDeclined(String cardNumber, String declineCode)
            throws StripeException {
        OrderView order = openCheckout();

        checkout.payWithCard(cardNumber);

        assertThat(checkout.paymentError()).isVisible();
        SoftAssert soft = new SoftAssert();
        soft.assertEquals(stripe.paymentIntent(order.paymentIntentId()).getLastPaymentError().getDeclineCode(), declineCode);
        soft.assertEquals(orders.order(order.id()).status(), "AwaitingPayment");
        soft.assertAll();
    }

    private OrderView openCheckout() {
        checkout.openWithTwoMugs();
        OrderView order = orders.order(checkout.orderId());
        stripe.track(order.paymentIntentId());
        return order;
    }
}
```

- `BaseTest`'s `@AfterMethod` closes the context; TestNG runs the subclass's `@AfterMethod` first, so cleanup
  still has the sandbox client it needs (it does not need the page).
- The sample SUT creates the PaymentIntent when the checkout page opens and shows the order id; read the id from
  wherever your page exposes it (a `data-testid`, or the `payment_intent` query parameter Stripe appends to the
  `return_url` after a redirect).
- `assertThat(locator)` is the wait: it retries until the confirmation or error renders. Never wait on the modal
  closing with a sleep.
- `CheckoutCopy` holds the app's own error strings from the copy deck. Do not assert Stripe's wording.

## Anti-patterns

- `page.frames().get(2)` or a stored `Frame` — indexes shift when Stripe adds a frame; chain `frameLocator`.
- Locating the card field by a CSS class from Stripe's bundle — use the role and accessible name.
- `Thread.sleep` "for the 3DS modal" — the click on the challenge button already waits for it.
- Treating the confirmation banner as proof of payment — retrieve the PaymentIntent.
- Typing a `pm_card_*` token into the card field — the UI takes card numbers; tokens are for API calls.
