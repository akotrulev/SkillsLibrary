---
paths:
  - "**/*.xcconfig"
  - "**/*Info.plist"
  - "**/*.entitlements"
  - "**/*.xcprivacy"
  - "**/Package.swift"
  - "**/Project.swift"
  - "**/project.pbxproj"
  - "**/Podfile"
---

<!-- desktop-macos rules v1 (2026-11-15): project, entitlements and signing config. Installed by /desktop-macos:rules; edit to fit this project. -->

# Xcode project, entitlements and signing standards (macOS)

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- No secret in an xcconfig, `Info.plist`, committed plist or the bundle; no committed `Local.xcconfig`, `.p12`, notarization password or Sparkle private key. *blocker*
- The App Sandbox is on (`com.apple.security.app-sandbox`) in every configuration that ships and in Debug, so a sandbox failure shows before release. *blocker for a Mac App Store build; major for Developer ID*
- Every entitlement has a recorded reason; the narrowest form is used (`user-selected.read-only` before `read-write`, a panel before a standard-folder entitlement, no temporary exception without a dated reason); `network.client` only when the app connects out. *major*
- Developer ID builds set Hardened Runtime and a secure timestamp and are notarized with `notarytool` and stapled; no `altool`. *blocker*
- A Mac App Store build has no self-updater, no licence keys and no downloaded code; every file is free of `com.apple.quarantine` at upload. *blocker*
- A shipped `.pkg` is signed under a Developer ID G2 certificate, not the original CA that expires 2027-02-01; `pkgbuild` sets `hostArchitectures` explicitly. *blocker after the date; major before*
- No `NSAllowsArbitraryLoads` or other ATS exception without a recorded reason. *blocker*
- Every protected resource has a specific `NS…UsageDescription`, localized in `InfoPlist.xcstrings`. *blocker*
- `PrivacyInfo.xcprivacy` declares collected data (Required Reason API declarations are not required on macOS). *major*
- `SWIFT_VERSION = 6` and warnings-as-errors are set explicitly (xcconfig, `swiftLanguageModes`, `treatAllWarnings`), never inherited from the template. *major*
- Default isolation `MainActor` in the app target only; packages stay `nonisolated`. *major*
- Never raise `SWIFT_VERSION`, `MACOSX_DEPLOYMENT_TARGET` or `ARCHS` as a side effect of other work; the deployment target is stated once per module, 12 is Xcode 27's floor, and a 27 target that must ship Intel adds x86_64 to `ARCHS` by hand. *major*
- No `MACOSX_DEPLOYMENT_TARGET = 27.1` (Xcode 27.2 accepts it by mistake) and no `-ld_classic`. *major*
- One xcconfig per environment, read once; no `#if DEBUG` / `#if STAGING` branching through features. *major*
- Modules are local packages depending one way, `App → Features → Core`; no `Common` / `Utils` package every module imports. *major*
- Tuist or XcodeGen present: edit the manifest and regenerate, never the generated `.pbxproj`. *major*
- No CocoaPods in a new project; an existing `Podfile` has a dated move to SPM (trunk read-only 2026-12-02). No dependency for something the SDK does, and no second crash or metrics SDK beside the one reporter. *major*
- A login item, agent or XPC service has its own entitlements file and a reason; `LSApplicationQueriesSchemes` is empty without a reason. *minor*
- `swift-format` and SwiftLint are committed and agree; no SwiftLint `--fix` in a build phase. *minor*
