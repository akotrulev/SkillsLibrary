# macOS distribution — Developer ID, Mac App Store, notarization, Sparkle

Verified 2026-11-15 against developer.apple.com, github.com/sparkle-project/Sparkle and github.com/actions/runner-images. Pipeline YAML is `devops-engineer`'s; this file names the steps.

## Contents

1. Channels
2. Developer ID: sign, notarize, staple
3. The 2027-02-01 Developer ID CA expiry
4. Mac App Store (guideline 2.4.5)
5. Packaging: DMG and `.pkg`
6. Sparkle 2
7. Architectures
8. CI and secrets

## 1. Channels

| | Developer ID | Mac App Store |
|---|---|---|
| Certificates | Developer ID Application; Developer ID Installer for `.pkg` | Apple Distribution; Mac Installer Distribution |
| Sandbox | optional | required |
| Gate | notarization | App Review |
| Updates | Sparkle 2 | store only |

## 2. Developer ID: sign, notarize, staple

Notarization is required for all Developer ID software. Requirements: every executable signed with Developer ID, **Hardened Runtime**, a **secure timestamp**, no `get-task-allow`, SDK 10.9 or later, well-formed entitlements.

Steps, in order (each is a pipeline step handed to `devops-engineer`):

1. Sign nested code first (helpers, XPC services, frameworks, Sparkle's `Autoupdate` and XPC services), the app last: `codesign --force --options runtime --timestamp --sign "Developer ID Application: …"`. Never `--deep` as the signing strategy; it hides which nested item failed.
2. Package: a signed DMG, a signed `.pkg`, or a ZIP of the app (a ZIP cannot be stapled; notarize the app and ship a stapled DMG instead).
3. Submit: `xcrun notarytool submit <file> --keychain-profile <profile> --wait`. `altool` is rejected since 2023-11-01.
4. On `Invalid`, read the log: `xcrun notarytool log <id> --keychain-profile <profile>`.
5. Staple: `xcrun stapler staple <file>`, then verify with `xcrun stapler validate` and `spctl --assess --type execute --verbose`.

Gatekeeper: macOS Sequoia removed the Control-click override, so an un-notarized app needs System Settings → Privacy & Security → Open Anyway. A user who must do that is a distribution defect, not a support case. macOS 27 adds `spctl --purge` to clean entries for unmounted apps.

Entitlements that need a recorded reason in a Developer ID build: `com.apple.security.cs.allow-jit`, `allow-unsigned-executable-memory`, `disable-library-validation`. Each weakens Hardened Runtime. Rationale lives in `desktop/_shared/security`.

## 3. The 2027-02-01 Developer ID CA expiry

The original Developer ID Sub-CA expires **2027-02-01** (Apple Developer News, 2026-10-01).

| Artifact | Effect on 2027-02-01 |
|---|---|
| `.pkg` signed with a certificate from the original CA | **Stops installing.** Re-sign with a G2 certificate and re-notarize |
| Notarized app carrying a secure timestamp | Keeps working |
| New certificates | Issue from **Developer ID CA (G2)**; choose the G2 Sub-CA in Xcode |

This is a **blocker-class** finding for any project that ships a `.pkg` before that date and has not re-signed. Check the signing certificate's issuer: `security find-identity -v -p basic` then `codesign -dvv` on a built artifact, and read the `Authority` chain.

## 4. Mac App Store (guideline 2.4.5)

| Rule | Consequence |
|---|---|
| Sandboxed | `com.apple.security.app-sandbox` plus each entitlement with a reason |
| Packaged by Xcode; no third-party installer | No `.pkg` of your own, no installer script |
| No auto-launch or login code without consent | Use `SMAppService` and ask |
| No downloading code; no root escalation | No plug-in downloads, no `sudo` helpers |
| No licence keys or own copy protection | Use the store's purchase |
| **Updates only through the Mac App Store** | **No Sparkle in this build** |

Uploads: no `com.apple.quarantine` on any file (`xattr -dr com.apple.quarantine App.app`), enforced since 2025-02-18. There is no published macOS SDK minimum for uploads. Hardware-Checked Pointer Arithmetic (`arm64e.x1`) apps cannot upload from Tahoe 26.6 with automatic signing; use macOS 27 and Xcode 27, or manual signing. Beta goes through TestFlight for Mac. The privacy manifest declares collected data; required-reason API declarations are not required on macOS.

## 5. Packaging: DMG and `.pkg`

| Tool | Fact |
|---|---|
| `create-dmg` (shell) | 1.3.0 (2026-07-02) |
| `create-dmg` (Node, sindresorhus) | 8.1.0 (2026-03-21) |
| `pkgbuild` / `productbuild` | Set `hostArchitectures` explicitly; macOS 27 defaults a missing value to arm64 |
| fastlane | 2.241.2 (2026-10-26); `notarize` action staples unless `skip_stapling` |
| Xcode Cloud | Builds, tests, distributes to TestFlight, the App Store, or as a notarized app |

Sign the DMG itself, notarize the DMG, staple the DMG. Prefer a DMG for drag-install apps and a `.pkg` only when an installer must place helpers or run scripts.

## 6. Sparkle 2

**Sparkle 2.10.1** (2026-10-25), macOS 12+, CocoaPods support dropped; add by Swift Package Manager.

| Step | Detail |
|---|---|
| Controller | `SPUStandardUpdaterController` plus a "Check for Updates…" menu item in the app menu. `SUUpdater` is a deprecated stub |
| Keys | `generate_keys` puts the **EdDSA** private key in the Keychain; the public half goes in `Info.plist` as `SUPublicEDKey` |
| Feed | `SUFeedURL` over HTTPS; `generate_appcast` builds the appcast and deltas |
| Version | A monotonic `CFBundleVersion`; Sparkle compares it |
| Hardening | `SURequireSignedFeed` (needs `SUVerifyUpdateBeforeExtraction`); signed feeds are validated from 2.9; DSA signatures are being retired, migrate to EdDSA |
| Sandboxed app | Keep Sparkle's XPC services; non-sandboxed apps may remove them |
| Debug | With library validation, an ad-hoc local build may fail to load Sparkle: use an Apple Development certificate, or relax library validation **in Debug only** |

Update UX rules (quit-with-unsaved-work asks first) are in the desktop code rules. Rollback: publish a higher `CFBundleVersion` containing the old code; Sparkle never downgrades. A channel for betas is a separate appcast or a Sparkle `<sparkle:channel>` tag.

## 7. Architectures

| Deployment target | Build |
|---|---|
| Below 27, Intel Macs on Tahoe in scope | Universal (arm64 + x86_64) |
| 27 or later | arm64 only (`ARCHS_STANDARD` drops x86_64) |
| 27 target that must ship x86_64 | Add it to `ARCHS` by hand; nothing warns |

macOS 26 Tahoe is the last release for Intel; Intel software stops running on macOS 28. A `.pkg` with no `hostArchitecture` defaults to arm64.

## 8. CI and secrets

- Image: `macos-26` (arm64); `macos-26-intel` or `macos-15-intel` for Intel; `xcode-27` / `xcode-27-xlarge` labels are preview. `macos-14` was retired 2026-11-02; `macos-latest` floats and is never used.
- Certificates: import a `.p12` into a temporary keychain at job start, delete it at job end. Notarization uses an App Store Connect API key stored with `notarytool store-credentials`.
- Signing runs on protected refs only; Sparkle's private key is available to the appcast step alone.
