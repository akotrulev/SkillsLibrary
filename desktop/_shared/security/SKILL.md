---
name: security
description: Use when macOS or Windows desktop code stores secrets, loads libraries, hosts a WebView, handles URL schemes, files or IPC. Triggers "where do tokens live". Not for scanning a built app (qa-security)
---

# Desktop — Secure Coding (OWASP Desktop App Security Top 10)

The dev-side half of desktop security: the rules an agent follows **while writing** Swift/SwiftUI/AppKit and C#/C++ (WinUI, WPF, WinForms) code, and checks **while auditing** a source tree. It enforces `CLAUDE.md` § Desktop code rules — *least privilege; secrets never ship in the binary, `Info.plist`, `appsettings.json` or plain files; only signed, verified updates; embedded web content locked down; URL schemes, file activation and IPC are untrusted input*.

**The fence.** Scanning and attacking a **built** app, binary hardening checks, runtime hooking and traffic interception are `qa-security`'s. This skill reads **source and config** and writes the fix. It never runs a debugger, a proxy, a scanner or an installer. A rule whose truth only shows at run time is written **requires dynamic test → `qa-security`** and reported *unverified*, never *passed*.

## When to use

- Choosing where a token, key, PII or cache lives
- Adding a network call, a WebView, a URL scheme, file or protocol activation, an XPC service, a named pipe or a helper process
- Loading a plug-in, a native library or a framework; adding an entitlement or a manifest capability
- Wiring an update channel
- Reviewing or auditing desktop code for section K of the conformance checklist

## When NOT to use

- Signing, notarization, MSIX, Sparkle / Velopack mechanics, SmartScreen → `desktop/_shared/distribution` (section L)
- Auth0 flows, PKCE, loopback redirect → `auth0-macos` / `auth0-windows`
- A built `.app` / `.msix` / `.exe` needs scanning, or a control must be *proven* → `qa-security` (peer, not loaded)
- Server-side authn / authz, rate limits → the `be-*` stack
- Telemetry scrubbing and crash reporters → `desktop/_shared/observability`

## Version lane (verified 2026-11-15)

| Standard / fact | Version | Note |
|---|---|---|
| OWASP Desktop App Security Top 10 | **2021** (only edition) | `DA1…DA10`, map below. The project has not been revised since; a newer edition is a finding for this skill, not a silent swap |
| Hardened Runtime | required for notarization | library validation on by default; `DYLD_*` ignored |
| macOS 27 | other teams' containers denied by default; apps cannot read the TCC database; `launchd` ignores quarantined plists | `macos.md` §3.1, §3.3 |
| Windows | WebView2 `CoreWebView2Settings`; `SetDefaultDllDirectories`; packaged MSIX = minimal capabilities | `windows.md` §5, §6 |
| WebView2 SDK | 1.0.4314.35 | re-verify before pinning |

Sources: owasp.org/projects/desktop-app-security-top-10, developer.apple.com (Hardened Runtime, Security), learn.microsoft.com (Win32 DLL security, WebView2 security). Cite `DA<n>` in every finding. Platform detail: [`references/macos.md`](references/macos.md), [`references/windows.md`](references/windows.md); audit rows `K1…`: [`references/audit-checks.md`](references/audit-checks.md).

## Procedure

1. **Detect the lane**: macOS App Store / Developer ID, sandboxed or not, SwiftUI / AppKit; Windows packaged / unpackaged, WinUI / WPF / WinForms / C++/WinRT. A rule's *file* differs, not its intent.
2. **Inventory what is sensitive**: tokens, refresh tokens, keys, PII, documents, licence keys, anything the privacy policy calls personal.
3. **Apply the rules below**; open the platform reference for the API.
4. **Split static from dynamic.** What a source read proves is pass / fail with `file:line`. What it cannot prove is a **requires dynamic test** item handed to `qa-security`.
5. **Report** with the audit severities; blockers are the hard rules in § Desktop code rules.

## Rules, with the OWASP id

| Area | Dev rule | DA |
|---|---|---|
| Least privilege | Never require admin or root. Ship sandboxed (App Sandbox; packaged MSIX with minimal capabilities). Every entitlement and capability carries a recorded reason. An elevated host loses notifications and a safe WebView2 | DA5 · DA6 |
| Secrets storage | Tokens and keys only in Keychain (`kSecAttrAccessibleWhenUnlockedThisDeviceOnly` class), `PasswordVault` or DPAPI (`DataProtectionProvider("LOCAL=user")`). Never `UserDefaults`, `appsettings.json`, the registry in clear, a plain file, or the binary | DA3 · DA4 |
| Memory and logs | Clear a secret buffer after use where the platform allows; no secret, token or PII in logs, crash reports, pasteboard or `NSLog` / `Debug.WriteLine`; sign-out drops tokens from memory | DA3 · DA10 |
| Cryptography | Platform APIs only (CryptoKit, `System.Security.Cryptography`); AES-GCM / ChaCha20-Poly1305, SHA-256+, a fresh random IV per message; never ECB, DES, MD5 / SHA-1 for security, a constant key or IV, or a key derived from a constant | DA4 |
| Transport | HTTPS only; no ATS exception or `ServerCertificateCustomValidationCallback` returning `true` without a recorded reason; never disable chain or hostname validation | DA7 |
| Update channel | Only signed, verified updates (Sparkle EdDSA + signed feed; MSIX / Store; Velopack signed feed). An update never installs from an unsigned or HTTP source. Mechanics in `distribution` | DA8 · DA9 |
| IPC | XPC services validate the peer's code-signing requirement; named pipes carry an explicit ACL / `PipeSecurity` and never `Everyone`; every message is parsed as untrusted | DA1 · DA5 |
| Activation | URL schemes, protocol activation, file activation and command-line arguments are untrusted input: validate scheme, host, path and type before routing, opening or executing; no path reaches the file system, a shell or a query unvalidated | DA1 · DA6 |
| Code loading | macOS: Hardened Runtime on; library validation stays on (`disable-library-validation` only for a host that must load third-party plug-ins, with a recorded reason); no `allow-dyld-environment-variables`; `allow-jit` before `allow-unsigned-executable-memory`. Windows: absolute paths or `LOAD_LIBRARY_SEARCH_*` flags; `SetDefaultDllDirectories` once at start; never rely on the current directory or `PATH` | DA8 |
| WebView | `WKWebView` / WebView2 hosts only content on an allow-list; navigation is decided in `decidePolicyFor` / `NavigationStarting`; script bridges expose specific audited messages, never a generic proxy; devtools / inspector off in release | DA1 · DA6 |
| Command and SQL | No shell string built from input (`Process` with an argument array, `ProcessStartInfo.ArgumentList`); parameterised queries only | DA1 |
| Dependencies | Lockfiles committed; packages pinned; native libraries and WebView2 / Sparkle versions current; the scan itself is `dependency-scan` | DA9 |
| Debug leftovers | Release builds carry no `get-task-allow`, no debugger-attach entitlement, no test certificate, no devtools | DA6 · DA8 |

## What stays in the app, and what leaves

Nothing the user did not agree to. Telemetry and crash reports go through the gateway in `observability`; a secret never rides along.

## Output

A security setup or review: lane, what is sensitive and where each item lives, entitlements / capabilities with reasons, the code-loading and activation inventory, WebView posture, update-channel verdict, and a findings table citing `K<n>` and `DA<n>` with `file:line`. The report ends with the carve-out line below.

*Static read only — DA2 session handling, DA7 TLS behaviour on the wire, DA8 binary hardening of the built app, XPC / pipe peer checks at run time and what is actually on disk are unverified until `qa-security` runs on a built app.*

## References

- [`references/macos.md`](references/macos.md) — Keychain, sandbox and entitlements, library validation, XPC, URL schemes, `WKWebView`
- [`references/windows.md`](references/windows.md) — `PasswordVault` / DPAPI, capabilities, DLL loading, named pipes, protocol activation, WebView2
- [`references/audit-checks.md`](references/audit-checks.md) — fragment rows `K1…`, the DA map and the dynamic-test carve-out
