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

Severity tags as in the core Swift rules. The codebase wins where it consistently does otherwise. Recipes: `project-setup`, `shared/distribution`, `migration`.

- No secret in an xcconfig, `Info.plist`, committed plist or the bundle; no committed `.p12`, notarization password or Sparkle private key. *blocker*
- The App Sandbox is on in every configuration, Debug included. *blocker for a Mac App Store build; major for Developer ID*
- Every entitlement has a recorded reason and the narrowest form; no temporary exception without a dated reason. *major*
- Developer ID builds set Hardened Runtime and a secure timestamp, are notarized with `notarytool` and stapled. *blocker*
- A Mac App Store build has no self-updater, no licence keys and no downloaded code. *blocker*
- A shipped `.pkg` is signed under a Developer ID G2 certificate, with `hostArchitectures` set explicitly. *blocker after 2027-02-01; major before*
- No `NSAllowsArbitraryLoads` or other ATS exception without a recorded reason. *blocker*
- Every protected resource has a specific `NS…UsageDescription`, localized. *blocker*
- `PrivacyInfo.xcprivacy` declares collected data. *major*
- `SWIFT_VERSION` and warnings-as-errors are set explicitly, never inherited from the template; default isolation `MainActor` in the app target only. *major*
- Never raise `SWIFT_VERSION`, `MACOSX_DEPLOYMENT_TARGET` or `ARCHS` as a side effect; the target is stated once per module. *major*
- No `MACOSX_DEPLOYMENT_TARGET = 27.1` and no `-ld_classic`. *major*
- One xcconfig per environment; no `#if DEBUG` branching through features. *major*
- Modules are local packages depending one way, `App → Features → Core`; no `Common` / `Utils` package. *major*
- Tuist or XcodeGen present: edit the manifest and regenerate, never the generated `.pbxproj`. *major*
- No CocoaPods in a new project; an existing `Podfile` has a dated move to SPM. *major*
- A login item, agent or XPC service has its own entitlements file and a reason. *minor*
