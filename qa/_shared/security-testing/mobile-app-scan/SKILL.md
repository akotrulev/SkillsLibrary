---
name: qa-security-mobile-app-scan
description: Use for STATIC mobile app security testing — analyzing an Android APK/AAB or iOS IPA (and its source) for the flaws MobSF and the mobile SAST tools catch without running the app — hardcoded secrets, weak crypto, insecure storage config, a permissive manifest/Info.plist, cleartext/ATS-disabled traffic, missing binary hardening. Language-agnostic (any mobile stack — native, Flutter, React Native, MAUI), OWASP MASVS/MASTG-mapped, safe every build (no device). Triggers "scan our APK/IPA for security issues", "run MobSF static analysis", "check the app manifest / ATS / network security config", "find secrets in the mobile binary", "MASVS static coverage". Not for runtime/traffic testing on a device (`mobile-runtime-testing`), a running web API (`active-scan`), or lockfile CVEs (`dependency-scan`).
---

# Security Testing — Mobile Static Analysis (MobSF + mobile SAST)

The **static half** of the library's mobile-security lane: analyze a built **Android** (`.apk` / `.aab`) or
**iOS** (`.ipa`) artifact — and, when available, its source — for the vulnerability classes that surface
**without a running app or a device**. This is the mobile counterpart of the web `code-scan` + `secrets-scan`
+ `image-infra-scan` static gates: it reads the binary and its manifest, not live behavior.

**One binary, any stack.** [MobSF](https://github.com/MobSF/Mobile-Security-Framework-MobSF) **v4.4.6** (an
all-in-one Docker image / Python app) decompiles the artifact and runs the analysis — it does not care whether
the app is native Kotlin/Swift, Flutter, React Native, or .NET MAUI, so this is **one language-agnostic skill**,
not stack-triplicated (same reason `active-scan`/`image-infra-scan` aren't). Per-platform mechanics that go
beyond MobSF's one-click report live in `references/android.md` (APK: manifest, `network_security_config`,
smali, `apktool`/`jadx`/`apkleaks`) and `references/ios.md` (IPA: `Info.plist`/ATS, entitlements, binary
hardening — PIE, stack canary, ARC). `references/mobsf-static.md` owns the MobSF invocation, its REST API for
CI, and how to read the security score.

This skill is **lang-agnostic** and pairs with `qa/_shared/security` (the OWASP backbone — load it alongside
for the triage discipline and the automatable-vs-manual boundary). It owns the **static mobile invocation,
gating, and MASVS/MASTG mapping**; the runtime/device half is `mobile-runtime-testing`.

## The two spines — MASVS/MASTG, stated per finding

Mobile findings map to the **OWASP Mobile Application Security** project, not the web Top 10:

- **[MASVS](https://mas.owasp.org/MASVS/) v2.1.0** — the *what*: 8 categories, 24 controls. Static analysis
  covers **MASVS-STORAGE · MASVS-CRYPTO · MASVS-CODE · MASVS-PLATFORM · MASVS-PRIVACY**; the AUTH / NETWORK /
  RESILIENCE controls need a running app and belong to `mobile-runtime-testing`.
- **[MASTG](https://mas.owasp.org/MASTG/) v2.0.0** — the *how*: the test/technique catalog. Since the June-2026
  v2 refactor every test has a stable machine-readable id (`MASTG-TEST-0xxx`) — **cite the test id in the
  finding**, e.g. `MASTG-TEST-0003` (hardcoded crypto keys).
- **[MASWE](https://mas.owasp.org/MASWE/) v1.0.0** — the weakness enumeration (the middle layer, released
  Aug 2026) — use its `MASWE-nnnn` id where a finding maps to one; MASVS is the required spine, MASWE is
  the optional sharper label.

Every report line carries `MASVS: <control-ids>` + `MASTG: <test-ids>`, the way the web scanners carry OWASP ids.

## Decision matrix — which analysis, which platform

| Have | Run | Reads | MASVS |
|------|-----|-------|-------|
| An **APK / AAB** (release build preferred) | MobSF static → then `references/android.md` deep-dive | manifest, DEX/smali, resources, native libs, certs | STORAGE / PLATFORM / CODE / CRYPTO / PRIVACY |
| An **IPA** | MobSF static → then `references/ios.md` deep-dive | `Info.plist`, entitlements, Mach-O binary, embedded provisioning | STORAGE / PLATFORM / CODE / CRYPTO / PRIVACY |
| **Source, not a build** | build the release artifact first (an obfuscated/minified release binary is what ships — scan *that*, not the debug build), then as above | — | — |
| A **secret in the binary** specifically | MobSF secrets + `apkleaks` (Android) / `strings`+regex (iOS) | string tables, resources, assets | STORAGE-2 |

> **⚠️ Scan the release artifact, not the debug build.** A debug APK/IPA has different signing, a debuggable
> flag, unstripped symbols, and often extra logging — flags that would be false positives against production,
> and hardening that only the release build applies. If only a debug build exists, say so in the report and
> mark manifest/hardening findings `debug-build — re-verify on release`.

## Procedure (the static gate)

1. **Read `qa/_shared/security` first** (OWASP/MAS backbone, triage discipline), then `references/mobsf-static.md`
   for the invocation and, for the target platform, `references/android.md` **or** `references/ios.md`.
2. **Obtain the release artifact.** APK/AAB or IPA. Record its `versionName`/`CFBundleShortVersionString` +
   the build's git SHA in the report so a finding is pinned to a build.
3. **Run MobSF static** (Docker, headless upload via its REST API for CI — see `references/mobsf-static.md`).
   MobSF produces the decompiled tree, the manifest analysis, the secret/crypto/API findings, and a security
   score. **The score is a headline, not a gate** — gate on the finding severities, not the number.
4. **Deep-dive the platform specifics** MobSF summarizes but you must verify by hand: the effective
   `network_security_config` / ATS exceptions, exported components without permission, `Info.plist` privacy
   strings, binary-hardening flags. `references/android.md`/`ios.md` give the exact checks.
5. **Triage against a ticketed baseline**, exactly like the web static gates: a first run seeds the baseline;
   thereafter the gate fails the build only on **NEW** findings above the agreed severity. Suppressions are
   ticketed and visible, never silent.
6. **Map + report.** Each finding → `MASVS`/`MASTG` ids, severity (the library's blocker/major/minor/nit
   table), `file:line` into the decompiled tree or the manifest, and a fix direction routed to the app team.

## What static analysis proves — and what it cannot

- **Proves (safe every build):** hardcoded secrets/keys, weak/broken crypto primitives and modes, a manifest
  that allows cleartext traffic or exports a component unprotected, ATS globally disabled, missing binary
  hardening, `android:debuggable`/`allowBackup` misset, dangerous permissions, tapjacking-open activities,
  PII in the manifest/plist.
- **Cannot prove (needs the device → `mobile-runtime-testing`):** whether the app *actually* pins TLS and
  whether that pinning can be bypassed, what it *actually* writes to local storage at runtime, whether the
  keychain/keystore is used correctly, whether the auth/session tokens are handled safely, root/jailbreak
  detection efficacy, and runtime tampering resistance (MASVS-RESILIENCE). A green static scan says nothing
  about these — **the report must state the runtime carve-out**, never imply "static clean = app secure."

## Hard rules

- **Release artifact only** (debug findings are re-verified on release; see the box above).
- **The security score is not a gate** — gate on severities against a ticketed baseline.
- **State the runtime carve-out in every report** — static is one half of MASVS; the AUTH/NETWORK/RESILIENCE
  controls are unverified until `mobile-runtime-testing` runs on a device.
- **Loot redaction** — a recovered secret is reported by *what it unlocks and its blast radius*, never by
  value, and the decompiled tree (which contains the recovered strings) is not committed under `docs/`.
- **This is a SAFE gate** — no device, no network, no payloads — so it wires into CI like `code-scan`. It
  carries **no** authorization gate (that is `mobile-runtime-testing`'s, for the device half).

## Related skills & peers

- **`mobile-runtime-testing`** — the dynamic/device half; the AUTH/NETWORK/RESILIENCE controls this skill
  carves out. Static findings ("the manifest claims cleartext is allowed for `api.example.com`") become
  runtime hypotheses to prove there ("and here is the intercepted cleartext request").
- **`qa/_shared/security`** — the OWASP/MAS backbone (load alongside).
- **`qa-mobile-<stack>`** *(peer, not loaded)* — owns the functional mobile suite + page/screen objects; a
  confirmed vuln becomes a bug report through `qa-test-case-designer`'s `bug-report-writer`.
- **`mobile-app-crawler` / `mobile-screen-explorer`** *(peers)* — drive the live app to enumerate screens;
  they map *functionality*, this maps *security posture* of the binary.
- **`dependency-scan` (`<stack>`)** — mobile third-party library CVEs from the build graph; this skill owns
  the binary/manifest, not the lockfile.
- **CI owner** — the static gate rides the **build pipeline** (`devops/{github-actions,gitlab-ci,azure-pipelines}`
  or `qa/cicd/<stack>` per the existing fence), not a device farm.
