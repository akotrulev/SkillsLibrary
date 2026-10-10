---
name: qa-security-mobile-runtime-testing
description: Use when a mobile app must be tested DYNAMICALLY on a device you own — TLS-pinning bypass + traffic interception, runtime storage/keychain, logging, session tokens, jailbreak-detection efficacy. MASVS/MASTG-mapped; Frida, objection, mitmproxy. Authorization-gated, never a per-PR gate. Triggers "bypass SSL pinning", "what does the app store at runtime", "test our jailbreak detection". Not for static analysis (`mobile-app-scan`), a web API (`active-scan`), or a kill chain (`penetration-testing`).
---

# Security Testing — Mobile Runtime / Dynamic Analysis (MobSF dynamic · Frida · objection)

The **dynamic half** of the mobile-security lane: run the app on a **device or emulator you own** and observe
what static analysis cannot — the *actual* TLS behavior, what actually lands on disk and in the keychain, how
tokens and sessions are handled, and whether anti-tampering controls hold. This is the mobile counterpart of
the web `active-scan` / `client-side-security` dynamic gates: it exercises a **running** app, so it carries the
same **authorization discipline** and is **never a per-PR gate**.

**One tool chain, any stack.** [Frida](https://frida.re) **17.16.4** (dynamic instrumentation),
[objection](https://github.com/sensepost/objection) **v1.12.4** (a Frida wrapper with one-command SSL-pinning
bypass / storage dump / hooking, works on non-rooted Android & non-jailbroken iOS via gadget injection), MobSF
**v4.4.6**'s dynamic analyzer, and `mitmproxy`/Burp for the intercepting proxy — all framework-agnostic, so
this is **one language-agnostic skill**. Per-area mechanics: `references/mobsf-dynamic.md` (MobSF's automated
dynamic run), `references/frida-objection.md` (pinning bypass, storage/keychain dump, hooking), and
`references/traffic-interception.md` (proxy + system-cert + the MASVS-NETWORK proof).

Pairs with `qa/_shared/security` (OWASP/MAS backbone — load alongside) and with the static sibling
`mobile-app-scan`: static findings become runtime hypotheses to prove here.

## ⚠️ Authorization gate — read before running anything

A dynamic run drives a **live** app: it bypasses controls, injects code, and captures traffic (which contains
tokens and PII). It runs **only** under the library's authorization discipline, identical to the web dynamic
lane:

1. **Owned, non-production, throwaway target only** — your own app on your own device/emulator, with test
   accounts and test data. Never a third party's app; never a production account's real data. This mirrors the
   `mobile-app-crawler` "test-account-on-non-production" precedent.
2. **A recorded, per-run, expiring `#volatile` authorization line** — `Authorization: <app + device/env + who
   authorized it + expiry>` in every report. Never cached in the orientation cache.
3. **Production (or a real user's data) is a separate, louder second sign-off** — the default posture is a
   lab/test build with test accounts.
4. **Loot never lands in the repo** — a recovered token/keychain item/intercepted body is reported by *blast
   radius* ("session token extractable from `NSUserDefaults`, valid 30 days, no device binding"), never by
   value. Capture files (flows, dumps) are handled per the engagement's data rules and never committed under
   `docs/`.
5. **No destructive acts** — read/observe/intercept; do not corrupt the app's data or the device. This is a
   security *test*, not an exploitation kill chain (that is `penetration-testing`).

## The two spines — MASVS/MASTG, stated per finding

Runtime covers the controls static cannot: **MASVS-NETWORK · MASVS-AUTH · MASVS-STORAGE (runtime writes) ·
MASVS-CRYPTO (runtime key use) · MASVS-RESILIENCE**. Cite the **MASTG v2.0.0** test id (`MASTG-TEST-0xxx`) and,
where it sharpens the label, the **MASWE v1.0.0** id. Every line: `MASVS: <ids>` + `MASTG: <ids>` +
`Authorization: <...>`.

## Decision matrix — which technique for which control

| Question | Technique | Reference | MASVS |
|---|---|---|---|
| Does the app pin TLS, and can the pin be bypassed? | objection `sslpinning disable` / Frida script → then proxy | `frida-objection.md` + `traffic-interception.md` | NETWORK-2 |
| What is in the app's real traffic (headers, tokens, PII, cleartext)? | mitmproxy/Burp after pinning bypass | `traffic-interception.md` | NETWORK / AUTH / PRIVACY |
| What does the app write to disk / keychain at runtime? | objection storage/keychain dump, or MobSF dynamic file-activity | `frida-objection.md` / `mobsf-dynamic.md` | STORAGE |
| How are session tokens / auth handled at runtime? | intercept + hook the auth/storage calls | `traffic-interception.md` + `frida-objection.md` | AUTH |
| Does root/jailbreak detection or anti-Frida hold? | attempt the bypass; report whether it resisted | `frida-objection.md` | RESILIENCE |
| An automated first-pass over all of the above | MobSF dynamic analyzer | `mobsf-dynamic.md` | STORAGE / NETWORK / PLATFORM |

## Procedure

1. **Confirm authorization** (the gate above) and read `qa/_shared/security` + the reference(s) for the chosen
   techniques.
2. **Stand up the target** — a rooted emulator / genuinely owned device, or objection's gadget-injection path
   for a non-rooted/non-jailbroken device. Install the **build under test** (the same version/SHA the static
   scan covered — pin it in the report).
3. **Start with MobSF dynamic** for the automated first pass (file activity, runtime API monitor, captured
   traffic, TLS test) — it maps the surface cheaply; see `references/mobsf-dynamic.md`.
4. **Prove TLS behavior** — set up the proxy, install the CA, and confirm whether traffic is visible. If it is
   *not*, the app pins → attempt the bypass with objection/Frida and report **whether the pin held**. If it is
   visible without a bypass, the app does not pin (or trusts user CAs) — a NETWORK finding. See
   `references/traffic-interception.md`.
5. **Inspect runtime storage** — dump `SharedPreferences`/`NSUserDefaults`/keychain/keystore, DBs, and files
   written during a session; look for tokens/PII/keys at rest. See `references/frida-objection.md`.
6. **Probe resilience** (if in scope) — attempt to bypass root/jailbreak detection and anti-Frida; report
   whether it resisted. RESILIENCE is defense-in-depth, not a substitute for the other controls — grade it as
   such.
7. **Map + report** — each finding → MASVS/MASTG ids, severity, the reproduction (technique + hook/command,
   loot redacted), the `Authorization` line, and a fix direction routed to the app team. State which controls
   were **not** exercised.

## Hard rules

- **Authorization line in every report; owned non-prod target; prod is a 2nd sign-off** (the gate above).
- **NOT a per-PR gate** — this runs in an authorized window, nightly/pre-release, like the web active scan.
- **Loot redaction is mandatory** — blast radius, never contents; capture files stay out of the repo.
- **RESILIENCE is graded as defense-in-depth** — a bypassable root check is a finding, but a strong one never
  compensates for a real STORAGE/NETWORK/AUTH flaw. Don't let "we have pinning + jailbreak detection" mask
  cleartext tokens.
- **Pinning bypass is a test technique here, not an exploit** — the goal is to *see the traffic to test it*,
  then report the pin's efficacy. Chaining a foothold into network access is `penetration-testing`.

## Related skills & peers

- **`mobile-app-scan`** — the static sibling; its findings ("cleartext declared for host X", "pinning
  declared") are this skill's runtime hypotheses to confirm or refute.
- **`qa/_shared/security`** — OWASP/MAS backbone (load alongside).
- **`client-side-security`** — the web analog for a mobile app's embedded WebView / hybrid content; if the app
  is a WebView shell, the DOM-XSS/CSP checks there apply to its web layer.
- **`qa-mobile-<stack>`, `mobile-app-crawler`, `mobile-screen-explorer`** *(peers, not loaded)* — own the
  functional mobile suite and live-app screen mapping; a confirmed vuln becomes a bug report via
  `qa-test-case-designer`'s `bug-report-writer`; the fix goes to `mobile-react-native` / `mobile-ios` / `mobile-android`. The crawler's device/emulator setup is reusable here.
- **`penetration-testing`** *(peer plugin)* — if a runtime finding is to be chained into network-altitude
  access (a foothold, lateral movement), that is its `initial-access` lane under its scope-file gates; this
  skill stops at single-app runtime proof and hands off.
