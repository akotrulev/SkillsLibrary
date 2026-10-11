# React Native / Expo — secure-coding rules (SDK 57 primary, 55–56 supported)

The JS layer adds four mistakes the native stacks cannot make; everything else is the native rules in `ios.md` and `android.md`, reached through the libraries named here. A source read proves the shape; what only shows at run time is marked **requires dynamic test → `qa-security`**.

## 1. Secrets in the bundle (MASVS-STORAGE-1, M1)

**Everything in the JS bundle, `app.json` / `app.config.*`, `extra`, `EXPO_PUBLIC_*` and `process.env` read at build time is public.** `EXPO_PUBLIC_` variables are inlined into the bundle on purpose; naming a secret that way publishes it. Hardcoded keys and `.env` files committed to the repo are the same defect (`MASWE-0004`, `MASTG-TEST-0212`, `0213`).

| Held in the app | Verdict |
|---|---|
| Public client id, publishable key, analytics write key, API base URL | acceptable in `EXPO_PUBLIC_*` |
| Auth0 client **secret**, Stripe secret key, signing keys, LLM API keys, DB credentials | **never** — the server holds them and exposes a narrow endpoint |
| A third-party key that needs referrer / package restriction | restrict it in the vendor console **and** treat it as public |

Fix direction: a backend-for-frontend holds the secret; the app sends a user token. An exposed secret is **rotated**, not moved. Search both the source and the built bundle (`bundle` output is `mobile-app-scan`'s).

## 2. Hermes bytecode is not obfuscation (RESILIENCE-3)

Hermes compiles JS to bytecode for startup speed; the bytecode is **decompilable** (`hbc-decompiler`, `hermes-dec`) and strings stay readable. It is not encryption and not obfuscation. Rules: no secret relies on being "compiled"; where IP protection is a requirement, obfuscation is a separate, named tool whose effect is **requires dynamic test → `qa-security`**. Source maps stay out of the app and go to the crash reporter only.

## 3. Token storage: secure-store and Keychain (STORAGE-1, CRYPTO-2)

| Library | Backing | Use |
|---|---|---|
| `expo-secure-store` | iOS Keychain · Android Keystore-wrapped `SharedPreferences` | **Default** for tokens and small secrets; values ≤ ~2 KB |
| `react-native-keychain` | Keychain · Keystore, with biometric access control | Bare apps, biometric-gated secrets |
| `react-native-mmkv` + encryption key | encrypted file; the key itself must come from secure-store | Large encrypted caches only |
| `AsyncStorage`, plain MMKV, `localStorage` shims | plain files | **never** for tokens, PII or keys |

```ts
import * as SecureStore from "expo-secure-store";

export async function saveRefreshToken(token: string): Promise<void> {
  await SecureStore.setItemAsync("auth.refreshToken", token, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    requireAuthentication: false,
  });
}
```

- `keychainAccessible` is the iOS access class (`ios.md` §2); `WHEN_UNLOCKED_THIS_DEVICE_ONLY` unless background refresh needs `AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY`.
- `requireAuthentication: true` gates reads behind biometrics; a feature that unlocks on a biometric **boolean** from `expo-local-authentication` and then reads an unprotected token is `MASWE-0020`.
- Access tokens live in memory; only the refresh token is persisted. `Auth0`'s credentials manager (`mobile-react-native:auth0`) handles storage — do not hand-roll beside it.
- Server state belongs in TanStack Query's cache, which is in-memory by default; persisting the query cache to `AsyncStorage` persists whatever the responses contained — exclude sensitive queries from the persister (`dehydrateOptions.shouldDehydrateQuery`).

## 4. WebView and links (PLATFORM-1, PLATFORM-2, CODE-4)

- `react-native-webview`: set `originWhitelist` to the exact `https://` origins (default `['http://*', 'https://*']` is permissive), also guard navigation in `onShouldStartLoadWithRequest`; keep `javaScriptEnabled` off unless the content is first-party; `allowFileAccess`, `allowUniversalAccessFromFileURLs` and `mixedContentMode="always"` stay off; never load a URL that came from a deep link or push without validating it (`MASTG-TEST-0398`, `0332`).
- A web-to-native bridge (`onMessage`, `injectedJavaScript`) is an IPC channel: validate `event.nativeEvent.url` against the allow-list, parse messages with a schema (Zod), never `eval`, never pass a bridge argument into `Linking.openURL` or a file path. `injectedJavaScript` built from interpolated user data is XSS into your own WebView.
- **`Linking` and Expo Router deep links are untrusted input.** Prefer verified App Links / Universal Links over a custom scheme; parse `Linking.parse(url)` / route params with a schema; allow-list hosts, paths and parameter ranges before navigating; never pass a link parameter to `Linking.openURL`, a WebView `source`, a file path or a query (`MASTG-TEST-0370`, `0394`, `0395`). `Linking.openURL(userString)` with an unchecked scheme can launch `tel:`, `sms:` or an intent URL.
- Push payload data decides a destination only after the same validation.

## 5. Pinning and RASP library maintenance (NETWORK-2, RESILIENCE)

JS cannot pin by itself: `fetch` / Axios use the platform stack. Pinning needs a native layer, and the available libraries are community-maintained and drift.

| Need | Option | Maintenance check before adopting |
|---|---|---|
| TLS pinning | iOS `NSPinnedDomains` + Android `network_security_config` pin-set through a config plugin | none — platform-native; **preferred** |
| TLS pinning in code | `react-native-ssl-public-key-pinning`, TrustKit-based wrappers | last release inside 12 months; supports the current RN New Architecture and Expo SDK; open issues on Android 15 / iOS 27; a backup pin and expiry plan |
| Root / jailbreak, hook detection (RASP) | `jail-monkey`, `freerasp-react-native`, commercial SDKs | same maintenance check; treat output as a **signal sent to the server**, never a client-side gate |

A pinning or RASP library that is archived, unreleased for 12+ months or incompatible with the current SDK is a **major** finding with the platform-native option as the fix. Whether pinning holds or detection works → **requires dynamic test → `qa-security`** (`mobile-runtime-testing`); never mark it passed because the import exists.

## 6. Native modules and config plugins (CODE-3, PLATFORM-1)

Manifest and `Info.plist` changes go through config plugins (CLAUDE.md § Mobile code rules); a plugin that sets `android:exported="true"`, `usesCleartextTraffic`, `NSAllowsArbitraryLoads` or `allowBackup` is audited like a hand edit. After `expo prebuild`, read the **generated** manifest and plist once — the plugin chain is where an exported component or a cleartext flag arrives unnoticed. Every native dependency is a supply-chain input (M2): scanned, pinned in the lockfile, reviewed on upgrade.

## 7. Logging and OTA (STORAGE-2, CODE-1)

- No `console.log` of tokens, PII or payloads in release (`babel-plugin-transform-remove-console` or a guarded logger); crash reporters receive scrubbed breadcrumbs.
- OTA updates (`expo-updates`): enable **code signing** of updates; scope updates to a `runtimeVersion` fingerprint; never ship native changes OTA. Whether signature verification rejects a tampered update → **requires dynamic test → `qa-security`**. Store rules for OTA are in `mobile-<stack>:store-compliance`.
