# StoreKit 2 — iOS reference

Checked 2026-10-10 against developer.apple.com/documentation/storekit. iOS 15+ is the StoreKit 2 floor; the project's iOS 17 / 16 target (CLAUDE.md) covers it.

## Product, purchase, verify

```swift
let products = try await Product.products(for: ["pro.monthly", "pro.yearly"])

let result = try await product.purchase(options: [.appAccountToken(userUUID)])
switch result {
case .success(let verification):
    let transaction = try checkVerified(verification)
    try await entitlementsAPI.verify(signedTransaction: verification.jwsRepresentation)
    await transaction.finish()
case .pending, .userCancelled:
    break
@unknown default:
    break
}

func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
    switch result {
    case .verified(let value): value
    case .unverified(_, let error): throw error
    }
}
```

- `VerificationResult` is the **on-device** signature check against Apple's chain. It is necessary and **not sufficient** — the server still verifies and owns the entitlement.
- `.appAccountToken(UUID)` ties the transaction to your user. The UUID is stable per user and not personally identifying.
- `.pending` (Ask to Buy, SCA) is a normal state: show "waiting for approval", do not unlock, do not error.
- Finish **after** the server accepted the proof. An unfinished transaction is redelivered by `Transaction.updates`.

## Listen from launch — `Transaction.updates`

```swift
@MainActor
final class PurchaseObserver {
    private var task: Task<Void, Never>?

    func start(entitlements: EntitlementsAPI) {
        task = Task.detached {
            for await result in Transaction.updates {
                guard case .verified(let transaction) = result else { continue }
                await entitlements.sync(signedTransaction: result.jwsRepresentation)
                await transaction.finish()
            }
        }
    }

    deinit { task?.cancel() }
}
```

Start it at app launch, not when the paywall opens: renewals, Ask-to-Buy approvals, purchases from another device and refunds arrive here. Unfinished transactions from before launch are delivered on the first iteration.

## Restore and current entitlements

```swift
try await AppStore.sync()

for await result in Transaction.currentEntitlements {
    guard case .verified = result else { continue }
    await entitlements.sync(signedTransaction: result.jwsRepresentation)
}
```

`AppStore.sync()` prompts for the Apple ID and so belongs behind the explicit **Restore Purchases** button, never on launch. A revoked or refunded transaction is **absent** from `currentEntitlements` and carries `revocationDate` in `Transaction.all`.

## Subscription status and management

```swift
if let status = try await product.subscription?.status.first {
    switch status.state {
    case .subscribed, .inGracePeriod, .inBillingRetryPeriod: break
    case .expired, .revoked: break
    default: break
    }
}

try await AppStore.showManageSubscriptions(in: windowScene)
```

Display-only: the server's entitlement decides access. `showManageSubscriptions` is the cancel path (symmetry rule in `SKILL.md`). `AppStore.requestRefund(for:in:)` exists for in-app refund requests; the refund outcome still arrives as a notification.

## Offers and win-back

Introductory, promotional and win-back offers come from `product.subscription?.promotionalOffers` / `winBackOffers`; promotional offer signatures are generated **on the server** with the in-app purchase key. Eligibility (`isEligibleForIntroOffer`) is asked of the store, never inferred from local history.

## Server side — App Store Server API and Notifications v2

| Need | Call / event |
|---|---|
| Authoritative transaction | `GET /inApps/v1/transactions/{transactionId}` |
| Subscription statuses | `GET /inApps/v1/subscriptions/{transactionId}` |
| Full history on restore | `GET /inApps/v2/history/{transactionId}` |
| Consumption info for a refund request | `PUT /inApps/v1/transactions/consumption/{transactionId}` |
| Notifications | Server Notifications **v2** — one HTTPS URL per environment (production, sandbox) set in App Store Connect; the body is a signed JWS (`signedPayload`) |

- Authenticate with a **JWT signed by the In-App Purchase key** (key id + issuer id from App Store Connect). The key is a server secret; it never ships in the app.
- Verify the notification JWS **certificate chain to Apple's root** before reading it; Apple publishes official server libraries (Java, Node, Python, Swift) that do this — use them, do not hand-roll chain validation.
- Dedupe on `notificationUUID`. Handle `notificationType` + `subtype`; unknown types are logged, not failed (Apple adds types).
- Check `environment` (`Production` / `Sandbox`) and `bundleId` on every payload.
- Test with the sandbox environment and StoreKit configuration files (Xcode) — those are QA / dev fixtures, not shipped.

## Version notes

- `Transaction.updates`, `currentEntitlements`, `AppStore.sync()` — iOS 15+. `AppStore.showManageSubscriptions` — iOS 15+. Win-back offers — iOS 18+.
- SwiftUI: `SubscriptionStoreView` / `StoreView` give a system paywall (iOS 17+); they do not change the server-ownership rule.
- `SKPaymentQueue` / receipt files / `verifyReceipt` are the legacy lane: flag, migrate with `mobile-ios-migration`, never extend.
