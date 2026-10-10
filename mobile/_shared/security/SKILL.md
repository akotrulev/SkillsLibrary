---
name: mobile-shared-security
description: Use when writing or reviewing mobile app code that stores data, talks to a server, handles auth tokens, opens links, hosts a WebView or exports components — secure coding keyed to OWASP MASVS 2.1, MASWE and MASTG. Triggers "where do tokens live", "is this safe to ship", "review mobile security". Do NOT use for scanning a built APK/IPA (qa `mobile-app-scan`), device testing (`mobile-runtime-testing`), or store rules (`mobile-shared-store-compliance`).
---

# Mobile — Secure Coding (MASVS 2.1)

The dev-side half of mobile security: the rules an agent follows **while writing** React Native, Swift and Kotlin code, and checks **while auditing** a source tree. It enforces `CLAUDE.md` § Mobile code rules — *secrets never ship in the binary or bundle; tokens live only in Keychain / Keystore-backed storage; TLS only; deep links, push payloads and intents are untrusted input*.

**The fence.** Scanning and attacking are `qa-security`'s: `mobile-app-scan` reads a **built** APK/AAB/IPA with MobSF; `mobile-runtime-testing` drives a device, authorization-gated. This skill reads **source and config** and writes the fix. It never runs MobSF, Frida, a proxy or a device. A rule whose truth only shows at run time is written **requires dynamic test → `qa-security`** and reported *unverified*, never *passed*.

## When to use

- Choosing where a token, key, PII or cache lives
- Adding a network call, a WebView, a deep link, a push handler, an exported Android component or an iOS extension
- Adding biometric unlock, a screenshot-sensitive screen, a clipboard copy
- Reviewing or auditing mobile code for the K section of the conformance checklist

## When NOT to use

- A built artifact needs scanning → qa `mobile-app-scan` (peer, not loaded)
- Pinning, storage-at-runtime, jailbreak / root, tamper resistance must be *proven* → qa `mobile-runtime-testing` (peer, not loaded)
- App Store / Play rules (privacy manifest, deletion, declarations) → `mobile-shared-store-compliance`
- Server-side auth, rate limits, authorisation → the `be-*` stack (MASVS-AUTH-1 lives there)
- Auth0 integration mechanics → `auth-auth0-react-native` / `auth-auth0-ios` / `auth-auth0-android`

## Version lane (verified 2026-10-10)

| Standard | Version | Note |
|---|---|---|
| MASVS | **2.1.0** | 24 controls in 8 groups |
| MASWE | **1.0.0** (2026-08-17) | `MASWE-0001…0078` — the weakness layer between MASVS and MASTG |
| MASTG | **2.0.0** (2026-06-30) | tests are `MASTG-TEST-####`, split into `references` (static) and `runtime` (dynamic) variants |
| Mobile Top 10 | **2024** | M1…M10, mapped below |

Cite `MASVS-<group>-<n>`, the `MASWE-####` and the `MASTG-TEST-####` in every finding. Platform detail lives in [`references/ios.md`](references/ios.md), [`references/android.md`](references/android.md), [`references/react-native.md`](references/react-native.md); rows for the audit in [`references/audit-checks.md`](references/audit-checks.md) (`K1…`).

## Procedure

1. **Detect the lane** — Expo managed / bare, SwiftUI / UIKit, Compose / Views; a rule's *file* differs, not its intent.
2. **Inventory what is sensitive**: tokens, refresh tokens, PII, keys, payment data, anything the privacy policy calls personal.
3. **Apply the group rules below**; open the platform reference for the API.
4. **Split static from dynamic.** What a source read proves is reported pass / fail with `file:line`. What it cannot prove is a **requires dynamic test** item handed to `qa-security`.
5. **Report** with the audit severities; blockers are the hard rules in § Mobile code rules.

## MASVS 2.1 group by group

Each row: the dev rule, then the MASWE and the MASTG tests an auditor can cite. `A` = Android test, `I` = iOS test.

### MASVS-STORAGE

| Control | Dev rule | MASWE | MASTG tests |
|---|---|---|---|
| STORAGE-1 data stored securely | Tokens and keys only in Keychain / Keystore-backed storage; nothing sensitive in `UserDefaults`, `SharedPreferences`, `AsyncStorage`, plain files or unencrypted Room / SQLite; sensitive data excluded from backup | 0001 · 0003 · 0004 · 0006 | A `0287` `0304–0306` `0216` `0262` · I `0299–0302` `0215` |
| STORAGE-2 no unintended leaks | No sensitive data in logs, clipboard, keyboard cache, external / shared storage, notifications or screenshots | 0002 · 0005 | A `0200–0203` `0231` · I `0296` `0297` `0303` `0313` |

### MASVS-CRYPTO

| Control | Dev rule | MASWE | MASTG tests |
|---|---|---|---|
| CRYPTO-1 current algorithms | AES-GCM / ChaCha20-Poly1305, SHA-256+, `SecureRandom` / `SecRandomCopyBytes`; never ECB, DES, MD5, SHA-1, `Math.random`, a reused IV | 0007 · 0008 · 0009 · 0012 · 0013 | A `0221` `0232` `0204` `0208` `0309` · I `0210` `0211` `0311` `0317` `0209` |
| CRYPTO-2 key management | Keys generated on device in Keystore / Secure Enclave, non-exportable, purpose-bound; never hardcoded; keys not derived from a constant | 0003 · 0014 · 0016 | A `0212` `0307` · I `0213` `0214` |

### MASVS-AUTH

| Control | Dev rule | MASWE | MASTG tests |
|---|---|---|---|
| AUTH-1 server-side authn / authz | **Out of scope here** — the backend enforces it; the app never decides authorisation | 0018 | — |
| AUTH-2 local authentication | Biometrics gate a Keystore / Keychain key via `BiometricPrompt` `CryptoObject` / `SecAccessControl` `.biometryCurrentSet`; no boolean-only check; no silent fallback for sensitive actions | 0020 · 0021 · 0022 | A `0326–0330` · I `0266` `0268` `0270` |
| AUTH-3 step-up | A sensitive action re-authenticates; a session is invalidated on logout and credentials leave memory | 0023 · 0024 | A `0017` `0018` · I `0064` |

### MASVS-NETWORK

| Control | Dev rule | MASWE | MASTG tests |
|---|---|---|---|
| NETWORK-1 secure channel | HTTPS only; ATS and Network Security Config stay strict; any cleartext or ATS exception carries a recorded reason | 0026 | A `0233` `0235–0238` · I `0321–0323` `0342` |
| NETWORK-2 identity verified | Never disable certificate or hostname validation; no trust-all `TrustManager` / `URLSessionDelegate`; pinning, where the risk warrants it, pins the SPKI with a backup pin and an expiry plan | 0027 · 0028 | A `0242` `0243` `0282` `0283` · I `0385` `0396` `0397` |

### MASVS-PLATFORM

| Control | Dev rule | MASWE | MASTG tests |
|---|---|---|---|
| PLATFORM-1 IPC and links | Exported components carry a permission or are not exported; `PendingIntent` is `FLAG_IMMUTABLE`; App Links / Universal Links verified; custom-scheme and push payloads validated before routing | 0029 · 0032 · 0018 | A `0364–0366` `0030` `0381` `0393` `0394` · I `0370` `0371` `0395` |
| PLATFORM-2 WebViews | JS off unless needed; no `file://` / content access from untrusted content; a bridge exposes only audited methods; origin allow-list | 0033 · 0034 · 0035 | A `0250` `0252` `0334` `0398` · I `0332` `0333` `0376` |
| PLATFORM-3 UI exposure | Sensitive screens hidden in the app switcher and from screenshots; secure text entry; clipboard not used for secrets; notifications carry no sensitive body | 0036 · 0037 · 0038 · 0030 · 0039 | A `0289` `0291–0294` `0315` `0316` · I `0290` `0276–0280` `0346` |

### MASVS-CODE

| Control | Dev rule | MASWE | MASTG tests |
|---|---|---|---|
| CODE-1 current platform | `targetSdk` / deployment target current; an enforced-update path when a vulnerable version must die | 0041 · 0042 · 0043 | A `0245` `0392` · I `0383` |
| CODE-2 up-to-date dependencies | Lockfiles scanned (`dependency-scan`), SDKs patched | 0044 | A `0272` `0274` · I `0273` `0275` |
| CODE-3 compiler protections | PIE / ASLR, stack canaries, ARC / R8 on; no debug build shipped | 0045 · 0046 | A `0222` `0223` · I `0228–0230` |
| CODE-4 untrusted input | Validate and bound all input from links, intents, pushes, files, deserialised data; parameterised queries in content providers | 0050 | A `0337` `0339` `0372` `0375` · I `0386` |

### MASVS-RESILIENCE

Resilience is defence in depth for apps whose threat model includes a hostile device; it is **never a substitute** for server-side checks and **never provable from source**.

| Control | Dev rule | MASWE | MASTG tests |
|---|---|---|---|
| RESILIENCE-1 platform integrity | If the threat model needs it: Play Integrity / App Attest verified **by the server** | 0054 · 0056 | A `0324` `0325` · I `0240` `0241` |
| RESILIENCE-2 anti-tampering | Release builds signed, not debuggable, no debug entitlement | 0058 · 0061 · 0063 | A `0224` `0226` · I `0220` `0261` |
| RESILIENCE-3 anti-static analysis | R8 / obfuscation where the IP justifies it; secrets are never "protected" by obfuscation | 0059 · 0060 | A `0368` `0369` · I `0391` |
| RESILIENCE-4 anti-dynamic analysis | Debugger / hook / root detection feeds a server-side risk signal | 0051 · 0064 · 0065 | A `0341` `0353` · I `0354` `0402` |

### MASVS-PRIVACY

| Control | Dev rule | MASWE | MASTG tests |
|---|---|---|---|
| PRIVACY-1 minimise data | Request the narrowest permission, at the moment of use; collect only what a feature needs | 0066 · 0069 | A `0254–0257` · I `0360` `0362` |
| PRIVACY-2 prevent identification | No stable device identifier for tracking; pseudonymise analytics | 0067 · 0068 | A `0318` `0319` · I `0281` |
| PRIVACY-3 transparency | Declared SDK data matches behaviour (manifest, Data safety) | 0070 · 0072 · 0073 · 0074 | A `0206` · I `0281` |
| PRIVACY-4 user control | Consent before collection, deletion in-app, preferences honoured | 0071 · 0076 · 0077 · 0078 | store rules → `mobile-shared-store-compliance` |

## What a source read cannot prove

| Claim | Why static fails | Handed to |
|---|---|---|
| Pinning holds and cannot be bypassed | Needs a proxy and a hook framework | `qa-security` → `mobile-runtime-testing` |
| What actually lands on disk | Config says where, not what | same |
| Keychain / Keystore usage is correct at run time | Access control flags and key attributes show only in a live process | same |
| Root / jailbreak, hook, debugger detection works | Efficacy is behavioural | same |
| Obfuscation resists reversing | Needs a decompiled release | `mobile-app-scan` + runtime |
| Screens are hidden from screenshots and the switcher | Depends on OS version and window flags | same |
| 16 KB alignment, binary hardening flags | Properties of the built artifact | `mobile-app-scan` |

Every report carries the line: *static read only — MASVS-NETWORK-2, STORAGE runtime content, AUTH-2 efficacy and RESILIENCE are unverified until `mobile-runtime-testing` runs on a device.*

## OWASP Mobile Top 10 — 2024 map

| # | Risk | Where this skill covers it |
|---|---|---|
| M1 | Improper Credential Usage | STORAGE-1 · CRYPTO-2 · AUTH-2 — no hardcoded keys, secure token storage |
| M2 | Inadequate Supply Chain Security | CODE-2 — pinned, scanned dependencies (`dependency-scan`) |
| M3 | Insecure Authentication / Authorization | AUTH-2 · AUTH-3; server side is the backend's |
| M4 | Insufficient Input / Output Validation | CODE-4 · PLATFORM-1 · PLATFORM-2 |
| M5 | Insecure Communication | NETWORK-1 · NETWORK-2 |
| M6 | Inadequate Privacy Controls | PRIVACY-1…4 · STORAGE-2; store rules in `mobile-shared-store-compliance` |
| M7 | Insufficient Binary Protections | RESILIENCE-1…4 · CODE-3 — defence in depth |
| M8 | Security Misconfiguration | PLATFORM-1 · NETWORK-1 · CODE-3 — exported components, cleartext, debuggable |
| M9 | Insecure Data Storage | STORAGE-1 · STORAGE-2 |
| M10 | Insufficient Cryptography | CRYPTO-1 · CRYPTO-2 |

## Output

```
## Coverage      (lane, platforms, files read)
## Findings      (K-id · MASVS · MASWE · MASTG · severity · file:line · fix direction)
## Unverified    (requires dynamic test → qa-security, each with the question to ask on a device)
```

## Hard rules

- A secret in source, `app.json`, `EXPO_PUBLIC_*`, `BuildConfig`, `Info.plist` or a resource file is a **blocker**; it is reported by what it unlocks, never by value.
- A rule not provable from source is **never** reported as passed.
- A recovered secret is rotated, not hidden.
- Obfuscation is not encryption; Hermes bytecode is not obfuscation.
- Do not add a pinning or RASP library on the assumption it works — verify it is maintained and test it dynamically.

## Related skills & peers

- qa `mobile-app-scan` / `mobile-runtime-testing` *(peers, not loaded)* — the static-binary and device halves; fixes land back here
- `mobile-shared-store-compliance` — privacy manifest, deletion, declarations
- `mobile-shared-release` — signing keys, CI secrets
- `auth-auth0-react-native` · `auth-auth0-ios` · `auth-auth0-android` — token handling in the Auth0 SDKs
- `be-*` stacks — server-side authorisation (MASVS-AUTH-1)
