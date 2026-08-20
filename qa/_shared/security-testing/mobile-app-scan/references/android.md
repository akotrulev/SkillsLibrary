# Android APK/AAB — static deep-dive

The checks MobSF summarizes but you verify by hand, plus the standalone tools for the parts MobSF misses.
Work on the **release** artifact. Decompile once, then run the checks against the extracted tree.

## Tooling

| Tool | Pin | Does |
|---|---|---|
| `apktool` | 2.11.x | decode resources + `AndroidManifest.xml` to readable XML/smali |
| `jadx` / `jadx-gui` | 1.5.x | DEX → readable Java (best for reading logic) |
| `apkleaks` | 2.6.x | regex secret/endpoint hunt over the decompiled app |
| `semgrep` + mobile rules | — | `p/mobsfscan` / `p/android` rulesets for code-level SAST |
| `mobsfscan` | 0.4.x | the SAST engine MobSF wraps, runnable standalone on source |

```bash
apktool d app-release.apk -o apk-src          # manifest + smali + resources
jadx -d jadx-out app-release.apk              # readable Java
apkleaks -f app-release.apk -o apkleaks.txt   # secrets + endpoints
```

## Manifest checks (`AndroidManifest.xml`) — MASVS-PLATFORM

- **`android:debuggable="true"`** on a release build → **blocker** (JDWP debugger attach, arbitrary code).
  Absent (the default) on release is correct.
- **`android:allowBackup="true"`** (or unset on API < 31, where it defaults true) → app data extractable via
  `adb backup` → MASVS-STORAGE. Set `false` or define a scoped backup rules file.
- **Exported components** — any `<activity>`/`<service>`/`<receiver>`/`<provider>` with
  `android:exported="true"` (or an implicit intent-filter, which forces exported) **and no
  `android:permission`** is an attack surface: reachable by any app on the device. List each, and for a
  `content provider` check `grantUriPermissions`/path-permissions. MASWE maps these to the exported-component
  weaknesses.
- **`android:usesCleartextTraffic="true"`** → cleartext allowed app-wide → MASVS-NETWORK. On API 28+ the
  default is `false`; an explicit `true` or a permissive network-security-config re-opens it.
- **`taskAffinity` / `launchMode`** open to task-hijacking (StrandHogg) on older targets.
- **Custom permission `protectionLevel`** — a `normal`/`dangerous` custom permission guarding a sensitive
  component should usually be `signature`.

## Network Security Config — MASVS-NETWORK (static half)

`@xml/network_security_config` (referenced from `<application android:networkSecurityConfig=...>`) is the
declared TLS policy. Read the **effective** config, not just the manifest flag:

- `<base-config cleartextTrafficPermitted="true">` or any per-`<domain-config>` cleartext exception →
  cleartext for those hosts. A `<domain-config>` for `localhost`/`10.0.2.2` in a **debug**-only overlay is
  fine; in the release config it is a finding.
- `<trust-anchors>` that add `<certificates src="user"/>` → the app trusts **user-installed** CAs → trivial
  MITM (this is often added to make Frida/Burp work and left in by mistake).
- `<pin-set>` present → the app *declares* certificate pinning. **Static only proves it is declared**; whether
  it holds and can be bypassed is `mobile-runtime-testing`'s job.

## Storage & crypto — MASVS-STORAGE / MASVS-CRYPTO

- Grep smali/Java for `MODE_WORLD_READABLE`/`MODE_WORLD_WRITEABLE`, `getExternalStorage*` writes of sensitive
  data, `SharedPreferences` holding tokens in plaintext (should be `EncryptedSharedPreferences` /
  Jetpack Security / Keystore-backed).
- Crypto smells: `DES`/`3DES`/`RC4`, `AES/ECB`, a hardcoded IV, `Cipher.getInstance("AES")` (defaults to ECB),
  `MD5`/`SHA-1` for security, `Random` (not `SecureRandom`) for keys/tokens, a hardcoded key or salt.
- **KeyStore misuse** — key material generated in code instead of `AndroidKeyStore`, or without
  `setUserAuthenticationRequired` where the threat model needs it.

## WebView & code — MASVS-CODE

- `setJavaScriptEnabled(true)` + `addJavascriptInterface(...)` on a WebView loading remote/untrusted content →
  JS-to-native bridge RCE surface.
- `setAllowFileAccess`/`setAllowUniversalAccessFromFileURLs(true)` on a WebView.
- Deep-link / App Links handlers that trust the URI without validation (open-redirect, intent-redirection).

## Secrets — MASVS-STORAGE-2

`apkleaks` + a targeted grep over `res/values/strings.xml`, `assets/`, and the decompiled code for API keys,
Firebase/GCP config, JWTs, private keys, cloud credentials. **Report by blast radius** ("a Google Maps API key
with no application restriction — usable from any origin"), never by value. A key that is *meant* to be public
(a client-side Firebase config, an ad SDK id) is `info`, not a finding — say why.
