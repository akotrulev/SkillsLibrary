---
name: mobile-shared-in-app-purchases
description: Use when an app sells anything inside the app — subscriptions, consumables, unlocks — on iOS, Android or React Native. Triggers "add a subscription", "restore purchases", "refund but still has access", "Apple rejected under 3.1.1". Server-owned entitlements, restore, refund notifications, store payment policy, cancel symmetry. Do NOT use for signing/rollout (`mobile-shared-release`), privacy/store forms (`mobile-shared-store-compliance`), or paywall visual design.
---

# Mobile — In-App Purchases

Owns **the money path**: what is bought, who decides the user is entitled, how a refund or a lapse reaches the app, and where store policy draws the line. The platform mechanics sit in references; the rules that never change sit here.

## The invariant

**The server owns entitlements. The client never decides access from a local receipt, a `Transaction`, a `Purchase` or an SDK flag alone.** The client reports a purchase; the server verifies it with the store, writes the entitlement, and the app reads its access from the server. A local check is allowed only as a display hint (instant unlock while the server round-trip completes) and it expires.

## When to use

- Adding, changing or reviewing a paywall, subscription, consumable, or non-consumable
- "Restore purchases", family sharing, account switching, multi-device entitlement
- A refund, chargeback, grace period, billing retry or revocation is not reaching the app
- A review rejection citing guideline 3.1.1 / 3.1.2 or a Play payments-policy warning
- Brownfield intake — where does this app decide access today?

## When NOT to use

- Signing, tracks, rollout → `mobile-shared-release`
- Privacy manifest, Data safety, account deletion → `mobile-shared-store-compliance`
- Secrets and token storage rules → `mobile-shared-security`
- Auth sign-in → `auth-auth0-react-native` / `auth-auth0-ios` / `auth-auth0-android`
- Paywall layout, copy and consent design → `design-ethical-patterns`, `design-ux-writing` (corpus-led)
- The backend that stores entitlements → the `be-*` agent for that stack (this skill defines the contract it must meet)

## Version lane (verified 2026-10-10)

| Fact | Value | Source |
|---|---|---|
| Play Billing Library | **9.1.0** current (2026-06-18); 9.0.0 2026-05-19. **8 or later required** for new apps and updates since 2026-08-31; **9 or later from 2027-08-31**; v7 extension ends 2026-11-01 | developer.android.com/google/play/billing/release-notes · /deprecation-faq (page updated 2026-09-09) |
| StoreKit | **StoreKit 2** (`Product`, `Transaction`, `AppStore.sync()`); the original receipt API is the legacy lane. Server: App Store Server API + **Server Notifications v2** | developer.apple.com/documentation/storekit |
| RN libraries | `react-native-purchases` (RevenueCat) **10.12.2**; `expo-iap` **6.0.0** and `react-native-iap` **17.0.0** (both moved into the `hyodotdev/openiap` monorepo; the old `hyochan/*` repos are archived) | npm registry, checked 2026-10-10 |
| Store policy | Apple guideline **3.1.1** (digital goods use IAP); US-storefront link-out is **court-driven and unsettled** (see below) | developer.apple.com/app-store/review/guidelines |

Detect first: `Package.swift` / `.xcodeproj` (StoreKit import, `SKPaymentQueue` = legacy), `build.gradle` (`billing-ktx` version), `package.json` (`react-native-purchases`, `expo-iap`, `react-native-iap`). Never up-level a project's billing library as a side effect; report the gap.

## The flow every stack implements

1. **Fetch products** from the store (never hard-code prices; show the store's localized `displayPrice` / `formattedPrice`).
2. **Purchase** — the client starts the store sheet, passing the **app account token** (`appAccountToken` on Apple, `obfuscatedAccountId` on Play) so the store can tie the transaction to your user without a second lookup.
3. **Hand the proof to the server** — Apple's signed transaction (JWS) / transaction id; Play's `purchaseToken`. Not a price, not a boolean.
4. **Server verifies with the store** — App Store Server API (`Get Transaction Info`) / Play Developer API (`purchases.subscriptionsv2.get`, `purchases.products.get`), checks bundle id / package name, product, environment, and writes the entitlement.
5. **Finish the transaction** only after the server accepted it — `transaction.finish()` on Apple; **acknowledge or consume within 3 days** on Play or the purchase is refunded automatically.
6. **The app reads access from the server** and refreshes on foreground.
7. **Notifications keep the server current** — the server, not the app, hears about renewals, lapses, refunds and revocations.

## Restore

- **Apple**: StoreKit 2 syncs automatically via `Transaction.currentEntitlements`; a visible **Restore Purchases** control must still exist (3.1.1), calling `AppStore.sync()` and then re-reading entitlements and re-sending proofs to the server.
- **Google**: `queryPurchasesAsync` on launch/foreground; a restore control is expected so a user on a new device can re-sync.
- **Across accounts**: restore re-binds proofs to the *signed-in* user on the server; define what happens when a transaction already belongs to another account (reject and say so — never silently move it).
- The restore path is **a working screen with loading / success / nothing-to-restore / failed states**, not a toast.

## Refunds, revocations and renewals — the server hears first

| Event | Apple (Server Notifications v2) | Google (RTDN → Pub/Sub) | Server does |
|---|---|---|---|
| Renewal / expiry | `DID_RENEW`, `EXPIRED` | `SUBSCRIPTION_RENEWED`, `SUBSCRIPTION_EXPIRED` | Move the entitlement end date |
| Billing trouble | `DID_FAIL_TO_RENEW` (+ grace) | `SUBSCRIPTION_IN_GRACE_PERIOD`, `ON_HOLD` | Keep access during grace; show "fix payment" |
| Refund / revoke | `REFUND`, `REVOKE` | `SUBSCRIPTION_REVOKED`, `VOIDED_PURCHASE` | **Remove access**, reverse consumable grants |
| Plan change / cancel intent | `DID_CHANGE_RENEWAL_STATUS` | `SUBSCRIPTION_CANCELED` | Record intent; access stays until period end |

The endpoint verifies the notification's **signature** (Apple signed JWS chain; Google authenticated Pub/Sub push), is **idempotent** (dedupe on `notificationUUID` / message id), and treats the notification as a trigger to **re-fetch authoritative state** from the store API rather than trusting the payload's story. Missing a refund means a user keeps paid access forever.

## Store policy boundary

| Rule | Code consequence |
|---|---|
| **Apple 3.1.1** — digital content, features and subscriptions unlocked in the app use IAP | No external payment button, no "pay on our website for 20% less" text outside what the current rules allow |
| **US-storefront link-out** — following the *Epic v. Apple* contempt ruling, US-storefront apps may link to external purchase; the permitted commission is **still being set by the court and under Supreme Court review (2026)** | Treat as a **configuration flag by storefront**, never hard-coded; re-verify against the live guidelines before relying on it; non-US storefronts follow 3.1.1 |
| **Apple 3.1.2** — subscription terms disclosed: price, period, auto-renew, how to cancel; Restore present | Paywall shows the store price and renewal terms next to the button |
| **Google Play payments policy** — digital goods on Android use Play Billing unless a program (user-choice billing, alternative billing, external offers by region) applies | Region programs are config gated by country and enrolment; never a default |
| **Physical goods / services consumed outside the app** (rides, retail) | Not IAP at all — do not route through the store |

Console-only facts (agreements, tax, price tiers, offer eligibility, program enrolment) are flagged **likely mismatch — verify in App Store Connect / Play Console**, never reported as passed.

## Cancel as easy as subscribe

Per `design-ethical-patterns` (symmetry; FTC click-to-cancel; DSA Art. 25): the path to **manage / cancel** has no more steps than the path to buy. In the app that means a visible *Manage subscription* row in Settings that deep-links to the store's management screen (`AppStore.showManageSubscriptions(in:)` · the Play subscriptions URL for the package), the renewal date and price shown next to it, no cancellation survey as a gate, no hidden trial-to-paid switch, and a pre-renewal reminder for annual plans. A purchase made on one platform is cancelled on that platform — say which one.

## Procedure

1. **Detect** the stack and billing library; list every place that decides access (`rg` leads in the fragment).
2. **Find the entitlement source.** If the client decides, that is a blocker — route to the contract below.
3. **Apply the flow** with the platform reference: [`references/storekit.md`](references/storekit.md), [`references/play-billing.md`](references/play-billing.md), [`references/react-native.md`](references/react-native.md).
4. **Wire restore and notifications**; confirm the server endpoints exist (coordinate with the `be-*` agent; this skill supplies the contract).
5. **Check policy** against the table above and the paywall copy.
6. **Report** with ids from [`references/audit-checks.md`](references/audit-checks.md) (`X1…`).

## Server contract (what the backend must offer)

| Endpoint | Does |
|---|---|
| `POST /purchases/verify` | Takes store proof + user id; verifies with the store; upserts entitlement; returns the entitlement |
| `GET /entitlements` | Authoritative access for the signed-in user |
| `POST /webhooks/apple` · `POST /webhooks/google` | Signature-verified, idempotent notification intake |

## Rules

- Entitlement source of truth is the server; the client caches for display only.
- Purchases carry an account token; the server rejects a proof for another user.
- Transactions are finished / acknowledged only after server acceptance.
- Refund and revocation notifications remove access.
- A visible Restore and a visible Manage subscription exist.
- Store price strings come from the store, never from a literal.
- Secrets (App Store Server API key, Play service-account key) live server-side only — never in the bundle.

## What NOT to do

- No "isPremium" in `UserDefaults` / `AsyncStorage` / `SharedPreferences` as the gate
- No client-side receipt validation as the only check
- No unacknowledged Play purchase left to auto-refund
- No custom payment form for digital goods
- No mixing the sandbox/test environment into production verification (check the environment field)
- No re-implementing StoreKit on top of RevenueCat or vice-versa — one purchase library per app

## Handoffs

- Store forms and privacy → `mobile-shared-store-compliance`
- Test-only purchase flows, sandbox accounts, E2E → qa `mobile-*` peers (not loaded)
- Backend webhook implementation → `be-dotnet` / `be-java` / `be-node`
- Auth of the purchasing user → the stack's `auth-auth0-*`
