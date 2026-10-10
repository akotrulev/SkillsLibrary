# Google Play Billing — Android reference

Checked 2026-10-10 against developer.android.com/google/play/billing/release-notes and /deprecation-faq (page updated 2026-09-09).

## Version and deadlines

| Library major | New apps + updates must use ≥ | Extension to |
|---|---|---|
| 7 | 2026-08-31 (passed) | 2026-11-01 |
| 8 | **2027-08-31** | 2027-11-01 |
| 9 | 2028-08-31 | 2028-11-01 |

- **Current: 9.1.0** (2026-06-18; Billing Choice APIs). 9.0.0 (2026-05-19) changed the blocked-Play-Store response from `ERROR` to `BILLING_UNAVAILABLE`.
- The rule in the table is "that version **or later**": from 2027-08-31 an update must be on **9+**. A project on 8.x passes today and has a dated deadline — report it as a finding with the date.
- Detect from `com.android.billingclient:billing-ktx:<version>` in `build.gradle(.kts)` / the version catalog. Never raise it as a side effect; `mobile-android-migration` owns the upgrade (follow the PBL 9 migration guide).

## Connect, query, launch

```kotlin
val client = BillingClient.newBuilder(context)
    .setListener(purchasesUpdatedListener)
    .enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build())
    .enableAutoServiceReconnection()
    .build()

val details = client.queryProductDetails(
    QueryProductDetailsParams.newBuilder()
        .setProductList(listOf(
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId("pro_monthly")
                .setProductType(ProductType.SUBS)
                .build()))
        .build()
)

val offerToken = productDetails.subscriptionOfferDetails!!.first().offerToken
val flowParams = BillingFlowParams.newBuilder()
    .setObfuscatedAccountId(userIdHash)
    .setProductDetailsParamsList(listOf(
        BillingFlowParams.ProductDetailsParams.newBuilder()
            .setProductDetails(productDetails)
            .setOfferToken(offerToken)
            .build()))
    .build()
client.launchBillingFlow(activity, flowParams)
```

- Use the `-ktx` suspend functions (`queryProductDetails`, `queryPurchasesAsync`, `acknowledgePurchase`, `consumePurchase`) so nothing blocks the main thread; the client lives in a repository scoped to the application, with the dispatcher injected.
- `setObfuscatedAccountId` carries an opaque id (a hash, never an email) so the server can tie the purchase to a user.
- Prices come from `ProductDetails` (`formattedPrice`); a `!!` above is for brevity of the sample — production code handles the null as a failed state.

## Handle purchases — acknowledge only after the server accepts

```kotlin
suspend fun handle(purchase: Purchase) {
    if (purchase.purchaseState != Purchase.PurchaseState.PURCHASED) return
    val accepted = entitlementsApi.verify(purchase.purchaseToken, purchase.products)
    if (!accepted) return
    if (!purchase.isAcknowledged) {
        client.acknowledgePurchase(
            AcknowledgePurchaseParams.newBuilder().setPurchaseToken(purchase.purchaseToken).build()
        )
    }
}
```

- **Acknowledge (subscriptions, non-consumables) or consume (consumables) within 3 days** or Google refunds the purchase automatically.
- `PENDING` purchases (cash payment methods) are not entitled yet — wait for the update; do not acknowledge.
- Re-run `queryPurchasesAsync(SUBS)` and `(INAPP)` in `onResume` and at launch: purchases made outside the app (Play Store, promo code, another device) arrive only that way or through RTDN.

## Server side — Play Developer API and RTDN

| Need | Call |
|---|---|
| Subscription state | `purchases.subscriptionsv2.get` (by `purchaseToken`) — `subscriptionState`, `lineItems[].expiryTime`, `acknowledgementState` |
| One-time product | `purchases.products.get` (or `productsv2`) |
| Acknowledge from the server | `purchases.subscriptions.acknowledge` / `purchases.products.acknowledge` |
| Voided purchases (refunds, chargebacks) | `purchases.voidedpurchases.list` — poll as a backstop to RTDN |

**Real-time developer notifications (RTDN)** — Play publishes to a **Cloud Pub/Sub topic** you create and link in Play Console; a push subscription delivers to your HTTPS endpoint.

- Authenticate the push (Pub/Sub OIDC token with your audience) before reading it.
- The message is a *signal*: read `purchaseToken`, then call `subscriptionsv2.get` for the truth.
- Handle `SUBSCRIPTION_RENEWED`, `_CANCELED`, `_ON_HOLD`, `_IN_GRACE_PERIOD`, `_RECOVERED`, `_EXPIRED`, `_REVOKED`, and `VOIDED_PURCHASE`; dedupe on the Pub/Sub `messageId`; log and ignore unknown types.
- A service-account key with Play Developer API access is a **server secret**; use workload identity where the host allows.

## Management, policy

- Manage/cancel deep link: `https://play.google.com/store/account/subscriptions?sku=<productId>&package=<packageName>`.
- Digital goods use Play Billing unless a program applies (user-choice billing, alternative billing, external offers — country- and enrolment-gated, re-verify at support.google.com/googleplay/android-developer). `mobile-shared-store-compliance` owns the Console-only items.
- Offers: base plan + offer ids come from `subscriptionOfferDetails`; eligibility is the store's decision.
- Testing: licence testers and internal-test tracks are QA fixtures; do not ship test product ids.

## ViewModel hand-off (Compose)

One `uiState: StateFlow` per screen (CLAUDE.md § Mobile code rules) exposing `Loading | Ready(products) | Purchasing | Pending | Failed(reason)`; the billing client's `purchasesUpdatedListener` feeds a repository `SharedFlow` the ViewModel maps — no ViewModel-to-UI one-shot events.
