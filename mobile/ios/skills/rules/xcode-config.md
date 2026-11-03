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

<!-- mobile-ios rules v1 (2026-11-03): project and build config. Installed by /mobile-ios:rules; edit to fit this project. -->

# Xcode project and configuration standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- No secret in an xcconfig, `Info.plist`, committed plist or the bundle; no committed `Local.xcconfig`, `.p12` or server-keyed `GoogleService-Info.plist`. *blocker*
- No `NSAllowsArbitraryLoads` or other ATS exception without a recorded reason. *blocker*
- Every protected resource has a specific `NS…UsageDescription`, localized in `InfoPlist.xcstrings`; `When In Use` location, never `Always` for a foreground feature. *blocker; major for the location class*
- `PrivacyInfo.xcprivacy` exists in the app and in each package that uses a Required Reason API. *major*
- `SWIFT_VERSION = 6` and warnings-as-errors are set explicitly (xcconfig, `swiftLanguageModes`, `treatAllWarnings`), never inherited from the template. *major*
- Default isolation `MainActor` in the app target only; packages stay `nonisolated`. *major*
- Never raise `SWIFT_VERSION` or `IPHONEOS_DEPLOYMENT_TARGET` as a side effect of other work; the deployment target is stated once per module. *major*
- One xcconfig per environment, read once; no `#if DEBUG` / `#if STAGING` branching through features. *major*
- Modules are local packages depending one way, `App → Features → Core`; no `Common` / `Utils` package every module imports. *major*
- Tuist or XcodeGen present: edit the manifest and regenerate, never the generated `.pbxproj`. *major*
- No CocoaPods in a new project; an existing `Podfile` has a dated move to SPM. No dependency for something the SDK does, and no second crash or metrics SDK beside MetricKit and the one reporter. *major*
- The scene manifest and a launch screen are present; no `UIRequiresFullScreen`. *major*
- Only the entitlements and background modes the code uses; `LSApplicationQueriesSchemes` empty without a reason. *minor*
- `swift-format` and SwiftLint are committed and agree; no SwiftLint `--fix` in a build phase. *minor*
