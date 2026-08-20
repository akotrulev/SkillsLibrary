# Frida + objection — pinning bypass, storage & keychain dump, hooking

[Frida](https://frida.re) **17.16.4** is the instrumentation engine; [objection](https://github.com/sensepost/objection)
**v1.12.4** wraps it with pre-built commands so common tasks are one line instead of a custom script. Both are
GPL-3.0, `pip`-installable. **Everything here runs under the SKILL's authorization gate — owned, non-prod app,
recorded `#volatile` authorization line, loot redacted.**

```bash
pip install frida-tools objection            # frida-tools pulls frida 17.x; objection 1.12.4
```

## Attach modes

- **Rooted Android / jailbroken iOS:** push the matching `frida-server` (same 17.16.4 major) to the device,
  run it, then `objection -g <package> explore` or `frida -U -f <package>`.
- **Non-rooted / non-jailbroken (the gadget path):** `objection patchapk -s app.apk` /
  `objection patchipa -s app.ipa` embeds `frida-gadget` into the app, then you install the patched build and
  `objection explore`. This is why objection works without root/jailbreak — it modifies **your own** build
  under test (record that the patched build is what was tested).

## SSL pinning bypass (MASVS-NETWORK-2) — to *test* pinning, then report its efficacy

The goal is to see the traffic so you can test it — then report whether the pin held against a standard
bypass.

```bash
objection -g <package> explore
android sslpinning disable      # covers OkHttp, TrustManager, WebView, common libs
# or iOS:
ios sslpinning disable          # covers NSURLSession, AFNetworking, common libs
```

For a custom pinning implementation objection doesn't cover, use a Frida script (the community
"universal unpinning" scripts, or a targeted hook on the app's own verify method found during static
analysis). If **no** standard bypass works, report the pinning as **resilient to standard bypass** — that is a
positive finding, graded as defense-in-depth.

After the bypass, route traffic through the proxy in `references/traffic-interception.md`.

## Runtime storage & keychain dump (MASVS-STORAGE)

```bash
# Android
android hooking list activities
sqlite connect /data/data/<pkg>/databases/<db>     # inspect app DBs
ls /data/data/<pkg>/shared_prefs                   # read prefs for plaintext tokens
# iOS
ios keychain dump                                  # keychain items + accessibility class
ios nsuserdefaults get                             # NSUserDefaults contents
ios plist cat <path>                               # app plists
```

Look for: session/auth tokens at rest unencrypted, PII, API keys, a keychain item with a too-permissive
accessibility class (`kSecAttrAccessibleAlways`), a DB with no encryption. **Report by blast radius, redact
values.**

## Hooking for auth/crypto behavior (MASVS-AUTH / MASVS-CRYPTO)

`android hooking watch class_method <method> --dump-args --dump-return` (or a Frida script) to observe how
the app builds requests, signs them, derives keys, or validates a token at runtime — the behavior no static
read can confirm. Useful to prove a token is reused after logout, a nonce is predictable, or a key is derived
from a static seed.

## Resilience (MASVS-RESILIENCE)

Attempt to defeat root/jailbreak detection and anti-Frida (`objection`'s `android root disable` /
`ios jailbreak disable`, or a Frida anti-detection script). **Report whether it resisted.** A bypassable check
is a finding *only in proportion to the threat model* — RESILIENCE is defense-in-depth and never compensates
for a real STORAGE/NETWORK/AUTH flaw. Do not let strong resilience mask a weak core control.

## Hard rules (restating the SKILL gate at the tool level)

- Owned build under test only; the patched (gadget-injected) build is *your* build — never redistribute it.
- Bypassing pinning/root-detection here is a **test technique** to observe behavior, not a step in an
  exploitation chain — that is `penetration-testing`.
- Loot redaction: dumps contain tokens/keys/PII — report blast radius, keep dump files out of the repo.
