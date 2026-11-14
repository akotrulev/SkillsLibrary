# Checkout and 3DS2 in the browser (Playwright .NET 1.63 + NUnit)

Every sample derives from `Example.UiTests.Support.BaseTest`
(`qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs`); the Playwright pin is in that skill's
**Versions** table. `StripeSandbox` and `TestCards` are the ones from `stripe-api.md`, copied into the UI
project's `Support` folder.

## 1. Why frames, and which ones

Stripe renders the card fields inside its own iframe, and the 3DS2 test challenge inside a modal iframe that
holds a **second** iframe with the issuer's (here: Stripe's test) page. Playwright reaches both with
`FrameLocator` chains; no frame handle is ever stored, and every action auto-waits for the frame to attach.

The iframe selectors and the challenge's button names are **Stripe's markup, not a contract**. The values below
were observed with Stripe.js v3 and the Payment Element; before you pin them, open your checkout with
`playwright codegen`, take the challenge once, and copy what the inspector shows. They live in one page object so a
Stripe change is a one-file fix.

| Frame | Observed selector | Anchored on |
|---|---|---|
| Card fields | `iframe[title='Secure payment input frame']` inside `Checkout.PaymentElement` | the app's `data-testid` container |
| 3DS2 modal | `iframe[src*='three-ds-2-challenge']` | top-level page |
| Challenge page | `#challengeFrame` inside the modal | the modal frame |

If your recording shows a third level (some flows add an `acsFrame`), add one more `.FrameLocator(...)` in
`StripeChallenge` and nowhere else.

## 2. Page objects

```csharp
using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public sealed class CheckoutPage(IPage page)
{
    private readonly IFrameLocator _cardFrame = page.GetByTestId("Checkout.PaymentElement")
        .FrameLocator("iframe[title='Secure payment input frame']");

    public StripeChallenge Challenge { get; } = new(page);

    public ILocator Confirmation => page.GetByTestId("Checkout.Confirmation");

    public ILocator PaymentError => page.GetByTestId("Checkout.PaymentError");

    public async Task OpenWithTwoMugsAsync() => await page.GotoAsync("/checkout?sku=MUG&qty=2");

    public async Task<string> OrderIdAsync() => await page.GetByTestId("Checkout.OrderId").InnerTextAsync();

    public async Task PayWithCardAsync(string cardNumber)
    {
        await _cardFrame.GetByRole(AriaRole.Textbox, new() { Name = "Card number" }).FillAsync(cardNumber);
        await _cardFrame.GetByRole(AriaRole.Textbox, new() { Name = "Expiration date" }).FillAsync("12 / 34");
        await _cardFrame.GetByRole(AriaRole.Textbox, new() { Name = "Security code" }).FillAsync("123");
        await page.GetByTestId("Checkout.Pay").ClickAsync();
    }
}

public sealed class StripeChallenge(IPage page)
{
    private readonly IFrameLocator _challenge = page
        .FrameLocator("iframe[src*='three-ds-2-challenge']")
        .FrameLocator("#challengeFrame");

    public async Task CompleteAsync() => await _challenge.GetByRole(AriaRole.Button, new() { Name = "Complete" }).ClickAsync();

    public async Task FailAsync() => await _challenge.GetByRole(AriaRole.Button, new() { Name = "Fail" }).ClickAsync();
}
```

```csharp
public static class TestCardNumbers
{
    public const string Visa = "4242424242424242";
    public const string GenericDecline = "4000000000000002";
    public const string InsufficientFunds = "4000000000009995";
    public const string AuthenticationAlways = "4000002760003184";
}
```

The UI types card numbers (`stripe-api.md` §2); the API suite never uses them. Country and postal-code fields appear in the Payment
Element for some locales: fill them in `PayWithCardAsync` when your recording shows them.

## 3. The PaymentIntent behind the page

```csharp
using System.Text.Json;
using Microsoft.Playwright;

namespace Example.UiTests.Support;

public sealed record OrderView(string Id, string Status, string PaymentIntentId);

public sealed class OrdersApi(IPage page)
{
    public async Task<OrderView> OrderAsync(string orderId)
    {
        var response = await page.APIRequest.GetAsync($"/api/checkout/orders/{orderId}");
        var body = await response.TextAsync();
        if (!response.Ok)
        {
            throw new InvalidOperationException($"GET order {orderId} returned {response.Status}: {body}");
        }
        return JsonSerializer.Deserialize<OrderView>(body, JsonSerializerOptions.Web)
            ?? throw new InvalidOperationException($"Order {orderId} did not deserialize: {body}");
    }
}
```

`Page.APIRequest` shares the context's base URL and cookies, so it reads the order as the signed-in shopper.

## 4. Tests

```csharp
using Example.UiTests.Pages;
using Example.UiTests.Support;
using NUnit.Framework;

namespace Example.UiTests.Tests;

public class CardCheckoutTests : BaseTest
{
    private CheckoutPage _checkout = null!;
    private OrdersApi _orders = null!;
    private StripeSandbox _stripe = null!;

    [SetUp]
    public void CreateHelpers()
    {
        _stripe = StripeSandbox.FromEnvironment();
        _checkout = new CheckoutPage(Page);
        _orders = new OrdersApi(Page);
    }

    [TearDown]
    public Task ReleaseSandboxObjects() => _stripe.CleanUpAsync();

    [Test]
    public async Task Should_ConfirmOrderAndCapturePayment_When_ShopperCompletesAuthentication()
    {
        await _checkout.OpenWithTwoMugsAsync();
        var order = await _orders.OrderAsync(await _checkout.OrderIdAsync());
        _stripe.Track(order.PaymentIntentId);
        await _checkout.PayWithCardAsync(TestCardNumbers.AuthenticationAlways);

        await _checkout.Challenge.CompleteAsync();

        await Expect(_checkout.Confirmation).ToBeVisibleAsync();
        var intent = await _stripe.PaymentIntentAsync(order.PaymentIntentId);
        Assert.That(intent.Status, Is.EqualTo("succeeded"));
    }

    [Test]
    public async Task Should_ShowAuthenticationErrorAndLeaveIntentUnpaid_When_ShopperFailsAuthentication()
    {
        await _checkout.OpenWithTwoMugsAsync();
        var order = await _orders.OrderAsync(await _checkout.OrderIdAsync());
        _stripe.Track(order.PaymentIntentId);
        await _checkout.PayWithCardAsync(TestCardNumbers.AuthenticationAlways);

        await _checkout.Challenge.FailAsync();

        await Expect(_checkout.PaymentError).ToHaveTextAsync(CheckoutCopy.AuthenticationFailed);
        var intent = await _stripe.PaymentIntentAsync(order.PaymentIntentId);
        Assert.Multiple(() =>
        {
            Assert.That(intent.Status, Is.EqualTo("requires_payment_method"));
            Assert.That(intent.LastPaymentError.Code, Is.EqualTo("payment_intent_authentication_failure"));
        });
    }

    [TestCase(TestCardNumbers.GenericDecline, "generic_decline")]
    [TestCase(TestCardNumbers.InsufficientFunds, "insufficient_funds")]
    public async Task Should_ShowDeclineAndKeepOrderUnpaid_When_CardIsDeclined(string cardNumber, string declineCode)
    {
        await _checkout.OpenWithTwoMugsAsync();
        var order = await _orders.OrderAsync(await _checkout.OrderIdAsync());
        _stripe.Track(order.PaymentIntentId);

        await _checkout.PayWithCardAsync(cardNumber);

        await Expect(_checkout.PaymentError).ToBeVisibleAsync();
        var intent = await _stripe.PaymentIntentAsync(order.PaymentIntentId);
        Assert.Multiple(async () =>
        {
            Assert.That(intent.LastPaymentError.DeclineCode, Is.EqualTo(declineCode));
            Assert.That((await _orders.OrderAsync(order.Id)).Status, Is.EqualTo("AwaitingPayment"));
        });
    }
}
```

- The sample SUT creates the PaymentIntent when the checkout page opens and shows the order id; read the id from
  wherever your page exposes it (a `data-testid`, or the `payment_intent` query parameter Stripe appends to the
  `return_url` after a redirect).
- `Expect(...)` is the wait: it retries until the confirmation or error renders. Never wait on the modal closing
  with a delay.
- `CheckoutCopy` holds the app's own error strings from the copy deck. Do not assert Stripe's wording.
- `Assert.Multiple(async () => …)` is NUnit 4's async form.

## Anti-patterns

- `Page.Frames[2]` or a stored `IFrame` — indexes shift when Stripe adds a frame; chain `FrameLocator` instead.
- Locating the card field by a CSS class from Stripe's bundle — use the role and accessible name.
- `Task.Delay` "for the 3DS modal" — the click on the challenge button already waits for it.
- Treating the confirmation banner as proof of payment — retrieve the PaymentIntent.
- Typing a `pm_card_*` token into the card field — the UI takes card numbers; tokens are for API calls.
