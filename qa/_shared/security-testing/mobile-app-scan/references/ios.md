# iOS IPA — static deep-dive

The IPA is a zip: `Payload/<App>.app/` holds the Mach-O binary, `Info.plist`, embedded provisioning profile,
entitlements, and resources. Work on the **release**/ad-hoc IPA. Most checks run on any OS (unzip + parse
plists + inspect the Mach-O); a few binary tools are macOS-native — noted where they are.

## Tooling

| Tool | Does | Host |
|---|---|---|
| `unzip` + `plistutil`/`plutil` | extract, convert binary plists to XML | any (`plutil` is macOS; `plistutil` is the Linux port) |
| `otool` / `llvm-otool` | Mach-O load commands, linked libs, hardening flags | macOS / LLVM |
| `class-dump` / `otool -oV` | Objective-C class/method surface | macOS |
| `strings` + regex | secret hunt over the binary + resources | any |
| MobSF | wraps most of the above into one report | Docker (any) |

MobSF covers the IPA fully on Linux/Docker; reach for the native tools when you need to verify a specific
Mach-O flag MobSF summarized.

## `Info.plist` — MASVS-PLATFORM / MASVS-PRIVACY

- **App Transport Security** (`NSAppTransportSecurity`): `NSAllowsArbitraryLoads = true` disables ATS
  app-wide → cleartext + weak-TLS allowed → **major/blocker** (MASVS-NETWORK, static half). Per-domain
  `NSExceptionAllowsInsecureHTTPLoads` / `NSExceptionMinimumTLSVersion` downgrades for a host are findings too.
  A localhost/dev exception left in the release plist is a finding.
- **Privacy usage strings** (`NSCameraUsageDescription`, `NSLocationWhenInUseUsageDescription`,
  `NSContactsUsageDescription`, …) — their *presence* is required by App Store review, but a permission
  requested with no functional need is a MASVS-PRIVACY finding; cross-check against what the app actually does.
- **URL schemes** (`CFBundleURLTypes`) and **Associated Domains** (universal links) — deep-link entry points;
  flag handlers that trust the incoming URL without validation.
- **`UIFileSharingEnabled` / `LSSupportsOpeningDocumentsInPlace`** → the app's `Documents/` is exposed over
  iTunes/Finder file sharing → MASVS-STORAGE.

## Entitlements — MASVS-PLATFORM

Extract the embedded entitlements (`codesign -d --entitlements` on macOS, or read
`embedded.mobileprovision`):

- `get-task-allow = true` → the binary is debuggable → **must be false** on a release/App-Store build.
- **Keychain access groups**, **App Groups**, **data-protection class** (`NSFileProtectionComplete` vs
  `...None`) — a sensitive file written with `NSFileProtectionNone` is readable while the device is locked.
- Over-broad entitlements (e.g. a `keychain-access-group` shared wider than needed).

## Mach-O binary hardening — MASVS-CODE / MASVS-RESILIENCE

`otool -hv <App>` / MobSF's `binary_analysis`:

- **PIE** (`MH_PIE` in the header) — must be set, so ASLR applies. Absent → finding.
- **Stack canary** (`___stack_chk_guard` / `___stack_chk_fail` imported) — expected.
- **ARC** (`_objc_release` etc.) — automatic reference counting; its absence hints at manual memory bugs.
- **Encrypted** (`cryptid` in `LC_ENCRYPTION_INFO`) — App-Store binaries are FairPlay-encrypted; a `cryptid 0`
  on what should be a store build means it was decrypted (expected for a pulled binary you are analyzing).
- **`rpath`/insecure dylib load** commands worth a glance for dylib-hijack surface.

## Storage & crypto — MASVS-STORAGE / MASVS-CRYPTO

- Grep the binary + bundle for `NSUserDefaults` holding tokens (not encrypted, backed up), plaintext writes to
  `Documents/`/`Caches/`, a `Realm`/SQLite DB with no encryption.
- Crypto smells: `CCCrypt` with `kCCAlgorithmDES`/ECB, `CC_MD5`/`CC_SHA1` for security, a hardcoded key/IV in
  the strings, `arc4random` misuse, `Security.framework` key generation without the Secure Enclave where the
  threat model needs it.

## Secrets — MASVS-STORAGE-2

`strings` + the same regex families as Android (API keys, JWTs, cloud creds, private keys) over the binary and
`Payload/<App>.app/` resources. **Report by blast radius, never by value.** A binary-embedded secret is worse
than an Android one only in that iOS has no `strings.xml` equivalent — it is in the Mach-O, so state where.

## The runtime carve-out

Static confirms ATS is declared, pinning is declared, and the data-protection class is set. It **cannot**
confirm the app pins at runtime, that the pin resists an objection/Frida bypass, what actually lands in the
keychain, or whether jailbreak detection works — all MASVS-AUTH/NETWORK/RESILIENCE, all
`mobile-runtime-testing`. Say so in the report.
