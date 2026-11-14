---
name: payment-testing
description: Use when .NET/NUnit tests must drive a payment sandbox (Stripe test cards, 3DS, webhooks, refunds). Triggers "test our Stripe checkout", "test the payment webhook". Not for mocks (network-mocking).
---

# QA — Payment Flow Testing against a Provider Sandbox (.NET 10 / NUnit + Stripe.net)

A payment bug costs money in both directions: a double charge, an order shipped on a declined card, a refund
recorded but never sent. A mock cannot catch any of these, because the defect lives between the SUT and the
provider. This skill tests the real round trip against the provider's **sandbox**, with Stripe as the worked
example, and reads the outcome at three layers: the SUT's API response, the SUT's order state, and the provider's
own object.

**Sandbox only.** Every suite takes its key from the environment or the secret store and refuses to start when
the key is not a test-mode key (`sk_live_` / `rk_live_`). The refusal lives in the `StripeSandbox` helper, never in
a test body. Read the reference for the layer you are writing before any code.

## References

| Read | When |
|---|---|
| `references/stripe-api.md` | The guard, test cards, API-level payment tests (success, declines, 3DS `requires_action`), amounts in minor units, idempotency keys, refunds, cleanup, test clocks for subscriptions |
| `references/webhooks.md` | The SUT's webhook handler: signed test events, duplicate delivery, bad signature, `stripe listen` / `stripe trigger` in local runs and CI |
| `references/checkout-ui.md` | Playwright .NET 1.63 checkout: card entry in Stripe's iframe, completing or failing the 3DS2 test challenge through nested frames |

## When to use

- A checkout, a pay endpoint or a subscription must be proven against Stripe's sandbox, not a stub
- Decline handling, 3DS/SCA, refunds or partial refunds must reach the right order state
- The SUT's webhook handler must verify signatures and apply each event once
- A renewal, trial end or dunning path needs simulated time (test clocks)

## When NOT to use

- The provider is replaced by a canned response to test UI states → `network-mocking`
- Load on the pay endpoint → `load-testing` (never against a provider sandbox: it rate-limits)
- Purchase events sent to GA4 or a pixel → `analytics-testing`
- The provider SDK itself — test what the SUT does with it

## Decision matrix

| To prove | Drive | Assert |
|---|---|---|
| A good card pays the order | the SUT's pay endpoint with `pm_card_visa` | `200`, order `Paid`, PaymentIntent `succeeded`, amount = order total in minor units |
| A decline is surfaced, not swallowed | one `[TestCase]` per decline token | `402`, the decline code, order `PaymentFailed`, PaymentIntent `last_payment_error.decline_code` |
| SCA is requested | `pm_card_authenticationRequired` | PaymentIntent `requires_action`; the challenge itself in the UI suite |
| The 3DS challenge completes or fails | the checkout page with `4000002760003184` | confirmation or the app's error, then the PaymentIntent status |
| A retried request does not double-charge | the same `Idempotency-Key` twice | one PaymentIntent id |
| Refund / partial refund | the SUT's refund endpoint | order status, the Refund objects' amounts and status |
| The webhook applies once | a signed event delivered twice | `200` twice, one side effect |
| A forged webhook is rejected | an event signed with the wrong secret | `400`, no side effect |
| A subscription renews | a test clock advanced one period | the SUT's subscription state after the clock is `ready` |

## Rules

- **Test-mode keys only**, from `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` (env or secret store, never
  `appsettings.json`). `StripeSandbox.FromEnvironment()` throws for any key that does not start with `sk_test_` or
  `rk_test_`, and every PaymentIntent it reads is checked for `Livemode == false`.
- **`pm_card_*` tokens at the API layer.** Raw card numbers appear only where a test types into Stripe's own field
  (the UI suite). Constants live in `TestCards`; a test never spells a token or a number.
- **Assert the layer that owns the outcome.** The SUT's response, then the SUT's order state, then the provider
  object retrieved by id. A UI message alone proves nothing about money.
- **One expected value per assertion.** A decline test asserts `402` and the one decline code its card produces.
  Scenarios differ by data, so they are `[TestCase]` rows, never a branch in the test.
- **Amounts are integers in the currency's minor unit** (`6800` for EUR 68.00, `1000` for JPY 1,000). Never assert
  a `decimal` against a Stripe amount.
- **No sleeps.** Wait on a page condition (`Expect`), on the SUT state with `WaitForAsync`
  (`qa/dotnet/skills/db-testing/connection`), or on the clock's `status` reaching `ready`.
- **Cleanup is registered, not inline.** Every PaymentIntent, customer and test clock the test touches is
  tracked on `StripeSandbox`; `[TearDown]` calls `CleanUpAsync()`. Stripe cannot delete a payment, so open
  intents are cancelled and clocks (with their customers) deleted.
- Request bodies with four or more fields, and every webhook event, come from builders (`test-data-builder`).

## Other providers

The model carries over; only the names change. **Adyen**: the test environment (`Environment.Test` in
`Adyen` for .NET) with a test-account API key; guard on the environment, not only the key; test cards and 3DS2
challenge cards are on Adyen's test-card page; webhooks are verified with the HMAC key from the Customer Area.
**PayPal**: sandbox REST base URL `api-m.sandbox.paypal.com` with sandbox app credentials and sandbox buyer
accounts; guard on the base URL; webhooks are verified through the verify-webhook-signature API. Look up each
provider's current test data at the time of writing; never copy it from an old suite.

## Handoffs

- `BaseApiTest`, clients, `ProblemDetails` → `qa/dotnet/skills/api-test-author/writer`, `api-client-writer`
- `BaseTest`, page objects, `Directory.Packages.props` → `qa/dotnet/skills/ui-test-author/playwright`
- Builders → `qa/dotnet/skills/test-data-builder`; order-state probes → `qa/dotnet/skills/db-testing`
- CI secrets and the `stripe listen` step → `qa/cicd/dotnet/skills/ci-pipelines`
- TypeScript and Java → `qa-typescript:payment-testing`, `qa-java:payment-testing`
