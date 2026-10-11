# React Native / Expo — purchase libraries

**Checked 2026-10-10** (npm registry + GitHub API). This ecosystem changes hands; re-check the row you rely on before writing it as fact.

## Which library

| Library | Version (npm) | Last release | Maintainer / repo | Use when |
|---|---|---|---|---|
| `react-native-purchases` (RevenueCat) | **10.12.2** (hotfix tag 9.15.3) | 2026-10-08 | RevenueCat, `revenuecat/react-native-purchases` | **Default.** A hosted service owns receipt validation, entitlements and store notifications; Expo-compatible with a development build |
| `expo-iap` | **6.0.0** | 2026-10-09 | `hyodotdev/openiap` monorepo (the old `hyochan/expo-iap` repo is **archived**) | You own the backend and want direct StoreKit 2 + Play Billing access with Expo config-plugin support |
| `react-native-iap` | **17.0.0** (Nitro modules, needs `react-native-nitro-modules`) | 2026-10-09 | `hyodotdev/openiap` monorepo (old `dooboolab-community` repo **archived**) | Bare React Native, own backend |
| `expo-in-app-purchases` | — | removed | Expo | **Do not use** — deprecated and removed from the SDK |

**Recommendation (verified lane, not a taste):** RevenueCat when there is no existing purchase backend — it satisfies the server-owns-entitlements rule out of the box. `expo-iap` / `react-native-iap` when the team runs its own verification and notification endpoints (the `SKILL.md` server contract). **One purchase library per app.** Both `expo-iap` and `react-native-iap` are one maintainer's OpenIAP line; they shipped a major within hours of this check — pin exact versions and read the changelog before upgrading.

**Native code is required** — none of these run in Expo Go. Use a development build (CNG / config plugins), never hand-edited `ios/` / `android/`.

## RevenueCat

```bash
npx expo install react-native-purchases react-native-purchases-ui
```

```ts
import Purchases from 'react-native-purchases';

Purchases.configure({ apiKey: Platform.select({ ios: IOS_PUBLIC_KEY, android: ANDROID_PUBLIC_KEY })! });
await Purchases.logIn(userId);

const offerings = await Purchases.getOfferings();
const { customerInfo } = await Purchases.purchasePackage(offerings.current!.availablePackages[0]);
```

- The keys here are **public SDK keys** (safe in the bundle); the **secret** REST key and webhook auth header live on the server only.
- `Purchases.logIn(appUserId)` ties purchases to your user — the equivalent of the account token.
- `customerInfo.entitlements.active` is a **cache for display**. Access the app enforces comes from the **server** reading RevenueCat's REST API / webhooks (`INITIAL_PURCHASE`, `RENEWAL`, `CANCELLATION`, `EXPIRATION`, `BILLING_ISSUE`, `REFUND`), authenticated by the webhook authorization header and deduped on the event id.
- Restore: `Purchases.restorePurchases()` behind a visible button.
- RevenueCat Paywalls (`react-native-purchases-ui`) are a system-level paywall; they still need the 3.1.2 terms and a Manage control.

## expo-iap / react-native-iap (OpenIAP)

```ts
import { useIAP } from 'expo-iap';

const { connected, subscriptions, fetchProducts, requestPurchase, finishTransaction } = useIAP({
  onPurchaseSuccess: async (purchase) => {
    const accepted = await entitlementsApi.verify(purchase);
    if (accepted) await finishTransaction({ purchase, isConsumable: false });
  },
  onPurchaseError: (error) => reportPurchaseError(error),
});
```

- The hook names have moved between majors (`getProducts` / `fetchProducts`, `getSubscriptions`); **read the installed version's types** instead of copying a snippet.
- `finishTransaction` maps to `transaction.finish()` on iOS and acknowledge/consume on Android — call it **only after** the server accepted the proof (the same rule as the native references).
- Send the platform proof the server needs: iOS signed transaction (JWS) / transaction id; Android `purchaseToken` + product ids. Account tie: pass the app account token (iOS) / obfuscated account id (Android) in the request options.
- The library bumps Play Billing and StoreKit inside its native layer — check which Play Billing major a given release bundles against the dates in `play-billing.md` before shipping.

## RN-specific traps

- **Server state, not client state.** Entitlements are TanStack Query data from the server (`GET /entitlements`), never a Zustand/MMKV flag. Invalidate on foreground and after a purchase.
- **Three-state + offline region** for the paywall: products loading, loaded, failed; offline is told apart from a store error; every call has a timeout.
- **`testID`** on every purchase, restore and manage control (`Paywall.Subscribe.Monthly`, `Paywall.Restore`) — never the price text.
- **Config plugin** changes (billing permission, StoreKit config) go through the plugin, not hand edits; EAS builds produce the test binary; sandbox/licence testers are QA setup.
- **OTA updates** must not change purchase flows beyond what review saw (`mobile-<stack>:store-compliance` L8).
