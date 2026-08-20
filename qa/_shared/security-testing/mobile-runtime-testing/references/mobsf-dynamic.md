# MobSF — dynamic analysis (v4.4.6)

MobSF's dynamic analyzer runs the app in an instrumented Android environment and records file activity, a
runtime API monitor, captured HTTP(S) traffic, and an automated TLS/pinning test — an automated first pass
that maps the runtime surface before you go hands-on with Frida/objection. **This is device/VM work under the
SKILL's authorization gate — not the static path.**

> **Android is the well-supported target.** MobSF dynamic analysis needs either the bundled Android VM
> (Genymotion / a real rooted device / an AVD with the right setup) or a corellium-backed device. **iOS
> dynamic** requires a jailbroken device or corellium and is materially harder to stand up — for iOS runtime
> work, objection + a proxy (the other two references) is usually the faster path than MobSF dynamic.

## Setup (Android)

1. A **rooted emulator or owned device** reachable over `adb`. MobSF talks to it via `adb`/Frida; it needs
   root to install its runtime CA and to read app-private storage.
2. Start MobSF (same pinned image as static — `v4.4.6`) with device access; the "Dynamic Analysis" tab lists
   the connected device and the uploaded app (use the same `hash` from the static upload so static + dynamic
   share one report).
3. Set `MOBSF_ANALYZER_IDENTIFIER` to the `adb` device id when driving headless.

## What the dynamic run gives you

| MobSF section | Observes | MASVS |
|---|---|---|
| **HTTP(S) traffic** | requests via MobSF's built-in CA (it configures the proxy + installs its cert) | NETWORK / AUTH / PRIVACY |
| **TLS/SSL security tester** | attempts a pinning bypass and reports whether traffic became visible | NETWORK-2 |
| **File activity monitor** | files created/read/written during the session, and their contents | STORAGE |
| **API monitor** | crypto, keystore, IPC, reflection, network calls made at runtime | CRYPTO / STORAGE / PLATFORM |
| **Runtime logs** | `logcat` output — tokens/PII logged is a STORAGE/PRIVACY finding | STORAGE / PRIVACY |
| **Exported activity tester** | launches exported activities to probe unprotected surfaces | PLATFORM |

MobSF drives Frida under the hood, so its pinning bypass covers the common cases (OkHttp, TrustManager). When
it *fails* to bypass, that is a signal the app pins in a non-standard way — hand off to
`references/frida-objection.md` for a targeted script, and report the pin as resilient to the automated bypass.

## Reading it for the report

- Traffic visible **without** a bypass → no pinning (or user-CA trust) → NETWORK finding.
- Traffic visible **only after** MobSF's bypass → pinning present but bypassable → grade per threat model
  (pinning is defense-in-depth; note it, don't overstate).
- File-activity / logcat entries containing tokens/PII/keys → STORAGE/PRIVACY findings, reported by blast
  radius, capture files kept out of the repo.
- Everything here is **redacted loot** — MobSF's captured flows contain secrets; treat the report directory as
  sensitive and do not commit it.
