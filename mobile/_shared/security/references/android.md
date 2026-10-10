# Android — secure-coding rules (Kotlin 2.4 / AGP 9.4 / targetSdk 36)

Applies to Compose and Views alike; React Native Android reaches the same manifest and APIs. Everything here is a **source / manifest / Gradle** read; what only shows at run time is marked **requires dynamic test → `qa-security`**.

## 1. Exported components (MASVS-PLATFORM-1)

Since targetSdk 31 every component with an `<intent-filter>` must declare `android:exported` explicitly, and the manifest merger pulls in library components too — read the **merged** manifest (`./gradlew :app:processReleaseManifest`, output under `build/intermediates/merged_manifests`).

- Default `android:exported="false"`. An exported Activity, Service, Receiver or Provider either needs `android:permission` (signature-level for first-party callers) or must be safe for any caller (`MASTG-TEST-0364–0366`).
- An exported `ContentProvider` exposes SQL or files to every app: no `grantUriPermissions="true"` blanket, parameterised queries only, `FileProvider` paths narrowed to a subfolder (`0339`, `0355–0357`).
- Intents that receive extras treat them as hostile: bound-check, type-check, never `startActivity` an `Intent` taken from an extra (intent redirection), prefer explicit intents for internal traffic (`0372`, `0374`, `0375`).
- **`PendingIntent` is `FLAG_IMMUTABLE`** unless mutability is required (`FLAG_MUTABLE` documented); never an empty base intent (`MASTG-TEST-0030`, `0381`).

```kotlin
val intent = PendingIntent.getActivity(
    context,
    requestCode,
    Intent(context, OrderActivity::class.java).putExtra(OrderActivity.ORDER_ID, orderId),
    PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
)
```

## 2. Network Security Config (NETWORK-1, NETWORK-2)

`android:networkSecurityConfig` points at an XML that is the single place cleartext and trust are decided; `usesCleartextTraffic="true"` in the manifest is a blocker unless a documented, scoped exception exists.

- `<base-config cleartextTrafficPermitted="false">`; a `<domain-config>` exception names one host and the owner.
- No `<certificates src="user" />` outside a `<debug-overrides>` block — user CAs are trusted by default only below API 24 (`MASTG-TEST-0285`, `0286`).
- Pinning: `<pin-set expiration="…">` with the primary SPKI **and a backup pin**; an expired pin-set silently stops pinning (`0243`). Whether the pin holds → **requires dynamic test → `qa-security`**.
- Never a trust-all `X509TrustManager`, a `HostnameVerifier { _, _ -> true }`, or an `onReceivedSslError` that calls `proceed()` (`0282`, `0283`, `0284`).

```xml
<network-security-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
    <domain-config>
        <domain includeSubdomains="true">api.example.com</domain>
        <pin-set expiration="2027-09-30">
            <pin digest="SHA-256">primaryPinBase64=</pin>
            <pin digest="SHA-256">backupPinBase64=</pin>
        </pin-set>
    </domain-config>
</network-security-config>
```

## 3. Backup and data extraction (STORAGE-1)

`android:allowBackup` defaults to true. For targetSdk 31+ the rules go in **`android:dataExtractionRules`** (Android 12+ cloud backup and device transfer) **and** `android:fullBackupContent` (Android 11 and below). Exclude databases, DataStore files, token stores and keyset files; or set `allowBackup="false"` for an app with no restore need (`MASWE-0006`, `MASTG-TEST-0216`, `0262`). Android Keystore keys never restore to another device, so an encrypted blob restored without its key is dead weight — exclude both.

## 4. Storage and the EncryptedSharedPreferences replacement (STORAGE-1, CRYPTO-2)

`androidx.security:security-crypto` (`EncryptedSharedPreferences`, `EncryptedFile`, `MasterKey`) is **deprecated**. For new code:

- Preferences: **Jetpack DataStore** (Proto or Preferences) holding values **encrypted with a Tink `Aead`** whose keyset is wrapped by an Android Keystore key (`AndroidKeysetManager`), or a direct Keystore `AES/GCM/NoPadding` key encrypting the value.
- Keys: `KeyGenParameterSpec` with `setUserAuthenticationRequired(true)` + `setInvalidatedByBiometricEnrollment(true)` for biometric-gated keys, `setIsStrongBoxBacked(true)` where the device has StrongBox (fall back deliberately), purpose-bound, non-exportable.
- Brownfield: an existing `EncryptedSharedPreferences` is **flagged and migrated**, not rewritten as a side effect; the migration reads old, writes new, deletes old.
- Room: encrypt sensitive columns with the Tink `Aead`, or use an encrypted SQLite driver whose passphrase is Keystore-wrapped; never a hardcoded passphrase (`MASTG-TEST-0304–0306`).
- Never `MODE_WORLD_READABLE`, never write secrets to `getExternalFilesDir` / shared storage (`0200–0202`).

## 5. WebView (PLATFORM-2)

`setJavaScriptEnabled(true)` only for first-party content; `allowFileAccess`, `allowContentAccess`, `allowFileAccessFromFileURLs`, `allowUniversalAccessFromFileURLs` all `false` (`MASTG-TEST-0252`, `0250`); `addJavascriptInterface` exposes only `@JavascriptInterface` methods that validate their arguments and is loaded only for an allow-listed origin (use `WebViewCompat.addWebMessageListener` with an origin rules set); `WebViewClient.shouldOverrideUrlLoading` allow-lists hosts (`0398`); `onReceivedSslError` never `proceed()`; `setWebContentsDebuggingEnabled` only in debug builds (`0227`); `Safe Browsing` left on (`0399`); clear cache and cookies on logout (`0320`).

## 6. Screens, clipboard, notifications (PLATFORM-3)

- `WindowManager.LayoutParams.FLAG_SECURE` (or `Window.setFlags`) on screens showing credentials, codes, balances or messages — blocks screenshots, screen recording and the Recents thumbnail; for Compose dialogs set `DialogProperties(securePolicy = SecureFlagPolicy.SecureOn)` (`MASTG-TEST-0294`); `setRecentsScreenshotEnabled(false)` for the Recents image (`0292`). Whether it is effective on a given OS → **requires dynamic test → `qa-security`**.
- Clipboard: mark sensitive clips `ClipDescription.EXTRA_IS_SENSITIVE` (API 33+), expire them, never copy a secret by default.
- Notifications: `setVisibility(VISIBILITY_PRIVATE)` with a redacted public version for anything sensitive (`0315`).
- Sensitive fields: `android:importantForAutofill`, `inputType="textPassword"` (Compose `KeyboardType.Password`), no keyboard cache for secrets (`0258`).
- Overlay (tapjacking): `filterTouchesWhenObscured` on security-sensitive buttons (`0035`, `0340`).

## 7. Logging (STORAGE-2)

Timber (or `android.util.Log`) wrapped so release builds plant no tree that writes to logcat; no tokens, PII or request bodies; strip with R8 `-assumenosideeffects` as a backstop only (`MASWE-0005`, `MASTG-TEST-0231`, `0203`).

## 8. Manifest and build hygiene (CODE-1, CODE-3, RESILIENCE-2)

`android:debuggable` is never set in release (`MASTG-TEST-0226`); targetSdk current (`0245`); R8 **full mode** with strict keep rules, `shrinkResources` on; native libraries built with the platform defaults (PIE, stack canaries — `0222`, `0223`); APK signature scheme v2+ (`0224`); dependencies scanned (`dependency-scan`). Properties of the **built** artifact → **requires dynamic test → `qa-security`** (`mobile-app-scan`).

## 9. Play Integrity and biometrics (RESILIENCE-1, AUTH-2)

- **Play Integrity API**: request a verdict with a server-generated nonce (standard request, `IntegrityManager.prepareIntegrityToken` warm-up), send the token to **the backend**, which decrypts and decides. The device never trusts its own verdict (`MASWE-0054`, `0056`).
- **Biometrics**: `BiometricPrompt` with a `CryptoObject` bound to a Keystore key; a callback that merely flips a boolean is bypassable (`MASWE-0020`); `BIOMETRIC_STRONG` for sensitive actions; the key invalidates on enrollment change; no silent fallback to device credentials for sensitive transactions (`MASWE-0021`, `MASTG-TEST-0326–0328`). Efficacy → **requires dynamic test → `qa-security`**.
