# Traffic interception — the MASVS-NETWORK proof

The intercepting proxy is where you *prove* what the app sends: cleartext, weak TLS, tokens in headers/URLs,
PII, missing pinning. Static analysis declares the policy; this shows the behavior. **Under the SKILL's
authorization gate — owned app, non-prod, loot redacted; captured flows contain secrets and stay out of the
repo.**

## Proxy choice

- **mitmproxy** (8.x) — scriptable, CLI/`mitmweb`, the portable default. `mitmdump -w flows.mitm` to capture.
- **Burp Suite** (Community is enough for interception) — nicer UI, Repeater for follow-up.

Both work the same way: the device routes HTTP(S) through the proxy, and the proxy's CA must be trusted for
TLS to be readable.

## Setup

1. Put the device/emulator and the proxy host on the same network; set the device Wi-Fi proxy to the host:port
   (mitmproxy default `8080`).
2. Install the proxy CA on the device:
   - **Android:** modern apps ignore **user**-store CAs (API 24+ default), so a plain user-cert install only
     works if the app's `network_security_config` trusts user CAs (itself a finding). Otherwise install the CA
     into the **system** store (rooted device / emulator with writable system), or use the objection/Frida
     pinning bypass which sidesteps the trust-store question entirely.
   - **iOS:** install the mitmproxy CA profile, then **enable full trust** under Settings → General → About →
     Certificate Trust Settings (installing without enabling trust is the usual "still not decrypting" cause).
3. If traffic is still not visible after the CA is trusted, the app **pins** → apply the objection/Frida
   bypass from `references/frida-objection.md`, then re-capture.

## What to assert (MASVS-NETWORK / AUTH / PRIVACY)

- **Cleartext:** any `http://` request carrying app data → NETWORK-1 (confirms or refutes the static
  `cleartext-permitted` finding).
- **TLS quality:** the negotiated version/cipher; a downgrade to TLS 1.0/1.1 or a weak cipher → NETWORK-1.
- **Pinning:** whether traffic was visible **only after** a bypass (pinned, bypassable), **without** a bypass
  (not pinned / trusts user CA), or **not at all** despite a bypass attempt (resilient pin) → NETWORK-2. State
  which.
- **Tokens/secrets in transit:** auth tokens in a URL query string (logged by proxies/servers) rather than a
  header, a token with no expiry/refresh, credentials in a request body over a downgraded channel → AUTH.
- **PII / over-collection:** device identifiers, location, contacts sent to first- or third-party endpoints →
  PRIVACY (cross-check the embedded trackers the static scan flagged).
- **Auth/session logic:** replay a captured request after logout (token still valid?), tamper an id
  (server-side authz — the mobile analog of BOLA/IDOR), check whether the app trusts a `200` blindly.

## Reporting

Each finding: the observed behavior (technique + endpoint, **redacted** — host + shape, never the token/PII
value), MASVS/MASTG ids, severity, the `Authorization` line, and a fix direction to the app team. The `.mitm`
capture is sensitive loot — handled per the engagement's data rules, never committed under `docs/`.
