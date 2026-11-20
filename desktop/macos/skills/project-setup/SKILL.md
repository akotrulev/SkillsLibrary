---
name: project-setup
description: Use when creating or hardening a Mac app in Xcode (Swift 6, sandbox, hardened runtime, entitlements, xcconfig). Triggers "new Mac app". Not for signing, notarization and CI (distribution).
disable-model-invocation: true
---

# macOS — Project Setup

Stands up a SwiftUI Mac app on the Xcode 27 lane with the strictness every project ships on day one: Swift 6 mode, warnings as errors, **App Sandbox and Hardened Runtime on from the first commit**, an entitlements file with a recorded reason per entry, one xcconfig per environment, a formatter and a linter, test plans, a String Catalog and a privacy manifest. Signing, notarization, Sparkle and the Mac App Store live in [`desktop/_shared/distribution`](../../../_shared/distribution/SKILL.md); the Swift standard is [`basics`](../basics/SKILL.md).

## Version lane — detect first

Read the `.xcodeproj` / `Project.swift` / `Package.swift`, `swift --version`, `MACOSX_DEPLOYMENT_TARGET`, `ARCHS` and each target's `SWIFT_VERSION` **before** writing. Never up-level a toolchain, language mode, deployment target or architecture list as a side effect.

| Concern | Primary | Supported / rule |
|---|---|---|
| Toolchain | **Xcode 27.x, Swift 6.4, macOS 27 SDK** (Apple-silicon host, Tahoe 26.6+) | Xcode 26.x, Swift 6.2–6.3 |
| Template `SWIFT_VERSION` | **`5.0`: set `6` explicitly** | Same on 26 |
| Deployment target, new app | **macOS 15** | **macOS 14** `[mac14]`: no `UtilityWindow`, no `defaultWindowPlacement` |
| Deployment target, existing app | keep it | macOS 13 `[mac13]`; **12 is Xcode 27's floor**; below 13 is AppKit-only, flagged. Xcode 27.2 wrongly accepts 27.1 as a target: never use it |
| Architectures | **arm64 only** at a target ≥ 27 (`ARCHS_STANDARD` drops x86_64) `[mac27SDK]` | **Universal** while the target is < 27 and Intel Macs on Tahoe are in scope; a 27 target that must ship x86_64 adds it to `ARCHS` by hand and nothing warns |
| Linker | ld64 is gone; `-ld_classic` is ignored with a warning | Remove the flag |
| Project format | `.xcodeproj`; Xcode 27.2's JSON `.xcproj` is opt-in and merge-friendly | Do not convert as a side effect |
| `PreviewProvider` | Deprecated: `#Preview` | Works on older SDKs |
| Dependencies | **SPM**; CocoaPods trunk goes read-only 2026-12-02 → [`migration`](../migration/SKILL.md) | SPM |
| AppKit-only app | `[AppKit]` lane: [`appkit`](../appkit/SKILL.md); same strictness | Same |

**The deployment target and architecture choice is a recommendation (D4) derived from API availability, not an Apple rule.** An architecture that drops Intel is a product decision: say so in the PR, because Intel software stops running on macOS 28 and macOS 26 Tahoe is the last release for Intel Macs. The template's `SWIFT_VERSION = 5.0` is the trap: a project already in Swift 5 mode is migrated one module at a time, never flipped wholesale.

## When to use

- Creating a Mac app, or hardening one that has only the template's defaults
- Turning on the sandbox, Hardened Runtime or an entitlements file
- Splitting an app into local Swift packages
- Adding an environment, a formatter, a linter, a test plan, a String Catalog or a privacy manifest

## When NOT to use

- Signing, notarization, Sparkle, Mac App Store review → `desktop/_shared/distribution`
- State ownership → [`architecture`](../architecture/SKILL.md); screens → [`ui-components`](../ui-components/SKILL.md)
- Which entitlement or TCC permission a feature needs → `sandbox-and-permissions`
- Auth → `auth0-macos`; CI YAML → `devops-engineer`
- iOS → `mobile-ios:project-setup`; Windows → `desktop-windows:project-setup`

## Inputs needed

- App name, bundle id, environments, deployment target (default 15), whether Intel is in scope
- Distribution: **Mac App Store** `[MAS]`, **Developer ID** `[DevID]`, or both
- Generated project (Tuist, XcodeGen) or hand-edited `.xcodeproj`; single module or packages

## The project

**Greenfield:** Xcode → *macOS App*, Interface *SwiftUI*, Language *Swift*, Testing System *Swift Testing*, Storage *None*. Then the sections below in order. **Brownfield:** apply only what is missing, one change per commit, never rename or move targets.

**Tuist or XcodeGen present:** the manifest is the source of truth; regenerate and never hand-edit the `.pbxproj`.

```
App/
  MyApp.xcodeproj
  Sources/            @main App, composition root, app-only views
  Resources/          Assets.xcassets, Localizable.xcstrings, PrivacyInfo.xcprivacy
  Config/             Base.xcconfig, Debug.xcconfig, Staging.xcconfig, Release.xcconfig, MyApp.entitlements
  TestPlans/          Unit.xctestplan, UI.xctestplan
Packages/
  Core/               Package.swift: models, formatting, no UI
  Features/           Package.swift: one library target per feature
.swiftlint.yml
.swift-format
```

## Swift 6, strictness and isolation — set, never inherited

In `Base.xcconfig`:

```
SWIFT_VERSION = 6
SWIFT_TREAT_WARNINGS_AS_ERRORS = YES
GCC_TREAT_WARNINGS_AS_ERRORS = YES
SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor
SWIFT_APPROACHABLE_CONCURRENCY = YES
MACOSX_DEPLOYMENT_TARGET = 15.0
ENABLE_USER_SCRIPT_SANDBOXING = YES
ENABLE_APP_SANDBOX = YES
ENABLE_HARDENED_RUNTIME = YES
CODE_SIGN_ENTITLEMENTS = Config/MyApp.entitlements
```

| Setting | App target | Package target |
|---|---|---|
| Language mode | `SWIFT_VERSION = 6` | `swiftLanguageModes: [.v6]` |
| Default isolation | `MainActor` | **`nonisolated`**: a package never assumes a main-actor caller |
| Approachable Concurrency | `YES` | `.enableUpcomingFeature("NonisolatedNonsendingByDefault")`, `InferIsolatedConformances` |
| Warnings | `SWIFT_TREAT_WARNINGS_AS_ERRORS = YES` | `.treatAllWarnings(as: .error)` |

State the choice per module in the PR. `[Swift6]` audit rows apply only to modules in Swift 6 mode.

## Sandbox, Hardened Runtime and the entitlements file — day one

**Least privilege is a project setting, not a late chore.** The App Sandbox is mandatory for the Mac App Store (guideline 2.4.5) and the default for a Developer ID app too; Hardened Runtime is required for notarization.

```xml
<key>com.apple.security.app-sandbox</key><true/>
<key>com.apple.security.network.client</key><true/>
<key>com.apple.security.files.user-selected.read-write</key><true/>
```

- **Start from the three keys above and add one entry per feature that needs it**, each with its reason recorded in the PR that adds it (a Markdown table `Config/ENTITLEMENTS.md`: key, feature, reason). An entitlement with no recorded reason is a finding.
- Never ship `com.apple.security.cs.disable-library-validation`, `cs.allow-jit`, `cs.allow-unsigned-executable-memory` or `com.apple.security.get-task-allow` in a release build without a written reason; Debug may carry `get-task-allow`.
- **Hardened Runtime exceptions** are the same list. Xcode 27 ships an `audit-xcode-security-settings` agent skill: use it where installed, never require it.
- Never require admin or root; no `sudo` helper, no privileged install script. A privileged operation is an `SMAppService` daemon with a recorded reason (`background-and-helpers`).
- Container paths, TCC permissions and bookmarks are `sandbox-and-permissions`; the entitlement a feature adds is added **by that feature's skill**, never pre-declared.

## Local Swift packages as modules

A module is a local SwiftPM package (or a library target in one). Dependency direction is one-way: `App → Features → Core`. Split on the second real need. Third-party dependencies are SPM, `.upToNextMinor` in a package or an exact version in the project, `Package.resolved` committed. Prefer the platform: `URLSession`, SwiftData, Swift Testing, `os.Logger` need no dependency. Pins that matter on the Mac: **Sparkle 2.10.1**, **OpenTelemetry Swift 2.6.0**, **Sentry 9.34**; all need macOS 12+.

## xcconfig per environment

One `Base.xcconfig`, one file per environment that `#include`s it and overrides only what differs: `PRODUCT_BUNDLE_IDENTIFIER`, `PRODUCT_NAME` suffix, `API_BASE_URL`, app icon set, `SWIFT_ACTIVE_COMPILATION_CONDITIONS`.

```
#include "Base.xcconfig"
PRODUCT_BUNDLE_IDENTIFIER = com.example.app.staging
INFOPLIST_KEY_CFBundleDisplayName = MyApp Staging
API_BASE_URL = https:/$()/api.staging.example.com
```

Shared, committed schemes per environment. Values reach code through `Info.plist` keys read once at the composition root, never `#if STAGING` in features. **An xcconfig is public**: the binary, `Info.plist` and xcconfig carry no secret; per-developer or CI values come from an uncommitted `Local.xcconfig` via `#include? "Local.xcconfig"`.

## Format and lint

`xcrun swift-format` is the formatter: commit `.swift-format`, run `xcrun swift-format lint --strict --recursive App Packages` in CI. **SwiftLint** (0.65) is the linter, not a second formatter: opt-in `force_unwrapping`, `force_cast`, `force_try`, `unused_import`, and custom rules forbidding `print(`, `NSLog(` and `DispatchQueue.main`. Both are CI steps or build-tool plugins, never a run-script that mutates files.

## Test plans

`Unit` (Swift Testing targets of the app and every package, parallelised, random order, coverage on) and `UI` (XCUITest only for what a `qa-desktop-*` peer does not own), both referenced by the shared scheme. Writing the tests is `unit-testing`. Parallel XCUITest on the Mac is unverified; do not claim it.

## String Catalog and privacy manifest — day one

- `Localizable.xcstrings`, `LOCALIZATION_PREFERS_STRING_CATALOGS = YES`, `SWIFT_EMIT_LOC_STRINGS = YES`. Plurals and formatting are `languages`.
- **`PrivacyInfo.xcprivacy`** in the app target from the first commit: `NSPrivacyTracking` `false`, empty `NSPrivacyTrackingDomains`, and `NSPrivacyCollectedDataTypes` declaring the data the app collects. **Required-reason API declarations are not required on macOS**; do not copy the iOS list. A package that collects data ships its own manifest.
- Usage-description strings are added by the feature that asks, never pre-declared.

## Rules

The standards this skill's output must meet are the desktop-macos rule files (`xcode-config.md`). Read the project's copy in `.claude/rules/desktop-macos/`, or the plugin's in `desktop/macos/skills/rules/` when not installed (`/desktop-macos:rules` does). Where they and this skill disagree, the rule files win.

## Validation (exit gate)

- [ ] `SWIFT_VERSION`, `SWIFT_TREAT_WARNINGS_AS_ERRORS`, isolation, `ENABLE_APP_SANDBOX` and `ENABLE_HARDENED_RUNTIME` are in the xcconfig; no stray `SWIFT_VERSION = 5.0` on a new module
- [ ] The entitlements file holds only keys with a recorded reason
- [ ] The deployment target and `ARCHS` follow the lane table and the choice is stated
- [ ] Each environment has an xcconfig, a configuration and a shared scheme
- [ ] `.swift-format` and `.swiftlint.yml` committed and passing; `Unit` and `UI` plans exist
- [ ] `Localizable.xcstrings` and `PrivacyInfo.xcprivacy` in the app target; no secret in any xcconfig or plist

## Handoffs

- Architecture and state → [`architecture`](../architecture/SKILL.md)
- Swift standard, concurrency → [`basics`](../basics/SKILL.md)
- Signing, notarization, Sparkle, store → `desktop/_shared/distribution`
- Entitlements and TCC per feature → `sandbox-and-permissions`
- Swift 5 → 6, CocoaPods → SPM, Intel → arm64 → [`migration`](../migration/SKILL.md)
- Test ids → `test-ids`
