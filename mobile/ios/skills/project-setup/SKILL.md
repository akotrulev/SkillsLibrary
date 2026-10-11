---
name: project-setup
description: Use when creating or hardening an iOS app on Xcode 27 — Swift 6 mode set explicitly (the template still says 5.0), warnings as errors, local Swift packages as modules, xcconfig per environment, swift-format + SwiftLint, test plans, scene lifecycle, launch screen, String Catalog, PrivacyInfo.xcprivacy. Triggers "new iOS app", "split into packages", "set up xcconfig". Do NOT use for signing and CI (`mobile-<stack>:release`), state design (`-architecture`) or screens (`-ui-components`).
---

# iOS — Project Setup

Stands up a SwiftUI app on the Xcode 27 lane with the strictness every project ships on day one: Swift 6 mode, warnings as errors, modules as local packages, one xcconfig per environment, a formatter and a linter, test plans, the scene lifecycle, a launch screen, a String Catalog and a privacy manifest. Signing, Xcode Cloud, Fastlane and TestFlight live in [`mobile/_shared/release`](../../../_shared/release/references/xcode-cloud.md); the Swift standard itself is [`basics`](../basics/SKILL.md).

## Version lane — detect first

Read the `.xcodeproj` / `.xcworkspace` / `Project.swift` / `Package.swift`, `swift --version`, `IPHONEOS_DEPLOYMENT_TARGET` and each target's `SWIFT_VERSION` **before** writing. Never up-level a project's toolchain, language mode or deployment target as a side effect of setup work.

| Concern | Xcode 27 / Swift 6.4 (primary) | Xcode 26.x / Swift 6.2–6.3 (supported) |
|---|---|---|
| Template `SWIFT_VERSION` | **`5.0` — set `6` explicitly** | `5.0` — same |
| Deployment target | **iOS 17** default for new apps; Xcode 27 debugs only on iOS 17+ devices | iOS 17 |
| `[iOS16]` | Supported: `ObservableObject`, no SwiftData, no `@Observable`; Xcode 27 cannot debug on-device | Same |
| Scene lifecycle (TN3187) | Mandatory against the iOS 27 SDK; a launch screen is mandatory | Optional until the SDK is linked |
| Uploads | Xcode 26 SDK required since 2026-04-28; **iOS 27 SDK from April 2027** | Fine until then |
| `PreviewProvider` | Deprecated — `#Preview` | Works |
| Dependencies | **SPM**; CocoaPods trunk goes read-only **2026-12-02** → [`migration`](../migration/SKILL.md) | SPM |
| UIKit-only app | `[UIKit]` lane — [`uikit`](../uikit/SKILL.md); still gets the same strictness | Same |

The Xcode template's `SWIFT_VERSION = 5.0` is the trap: strict-concurrency errors you expect are silent. **A project that is already Swift 5-mode is migrated one module at a time (`mobile-ios:migration`), never flipped wholesale.**

## When to use

- Creating an iOS app, or hardening one that has only the template's defaults
- Splitting an app into local Swift packages
- Adding an environment (dev / staging / prod), a formatter, a linter, a test plan
- Adding a String Catalog or a privacy manifest

## When NOT to use

- Signing, provisioning, TestFlight, Xcode Cloud → `mobile-<stack>:release`
- App architecture and state ownership → [`architecture`](../architecture/SKILL.md)
- Writing screens → [`ui-components`](../ui-components/SKILL.md); routes → [`navigation`](../navigation/SKILL.md)
- Required Reason APIs and the privacy questionnaire → `mobile-<stack>:store-compliance`
- Auth → `auth0-ios`; CI YAML → `devops-engineer`
- React Native / Expo project setup → `mobile-react-native:project-setup`; Android → `mobile-android:project-setup`

## Inputs needed

- App name, bundle id, environments, minimum iOS (default 17)
- Whether the project is generated (**Tuist**, XcodeGen) or hand-edited `.xcodeproj`
- Single module or packages; third-party dependencies already present

## The project

**Greenfield:** Xcode → *iOS App*, Interface *SwiftUI*, Language *Swift*, Testing System *Swift Testing*, Storage *None* (SwiftData is added by [`offline-and-storage`](../offline-and-storage/SKILL.md) when needed). Then the sections below, in order. **Brownfield:** apply only what is missing, one change per commit, and do not rename or move existing targets.

**Tuist or XcodeGen present:** `Project.swift` / `project.yml` is the source of truth. Make every change there, regenerate, and never hand-edit the `.pbxproj` it produces. The settings below are the same; they live in the manifest's `settings` and `.xcconfig` references.

```
App/
  MyApp.xcodeproj
  Sources/            @main App, composition root, app-only views
  Resources/          Assets.xcassets, Localizable.xcstrings, PrivacyInfo.xcprivacy, LaunchScreen
  Config/             Base.xcconfig, Debug.xcconfig, Staging.xcconfig, Release.xcconfig
  TestPlans/          Unit.xctestplan, UI.xctestplan
Packages/
  Core/               Package.swift — models, formatting, no UI
  Networking/         Package.swift — see mobile-ios:networking
  Features/           Package.swift — one library target per feature
.swiftlint.yml
.swift-format
```

## Swift 6 mode, strictness and isolation — set, never inherited

Set these in `Base.xcconfig` (or the target's build settings), not left to the template:

```
SWIFT_VERSION = 6
SWIFT_TREAT_WARNINGS_AS_ERRORS = YES
GCC_TREAT_WARNINGS_AS_ERRORS = YES
SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor
SWIFT_APPROACHABLE_CONCURRENCY = YES
IPHONEOS_DEPLOYMENT_TARGET = 17.0
ENABLE_USER_SCRIPT_SANDBOXING = YES
```

| Setting | App target | Package / library target |
|---|---|---|
| Language mode | `SWIFT_VERSION = 6` | `swiftLanguageModes: [.v6]` |
| Default isolation | `MainActor` **[Swift 6.2]** — views and models need no annotation | **`nonisolated`** (the default) — a package never assumes a main-actor caller |
| Approachable Concurrency | `YES` | `.enableUpcomingFeature("NonisolatedNonsendingByDefault")` and `InferIsolatedConformances` |
| Warnings | `SWIFT_TREAT_WARNINGS_AS_ERRORS = YES` | `swiftSettings: [.treatAllWarnings(as: .error)]` |

State the choice per module in the PR. Detail and the `Package.swift` shape: [`references/packages-and-config.md`](references/packages-and-config.md). `[Swift6]`-tagged audit rows apply only to modules in Swift 6 mode.

## Local Swift packages as modules

A **module is a local SwiftPM package** (or a library target in one), not a folder inside the app target. Packages give a compile-time dependency direction, parallel builds, a test target each and `public` / `package` access control that means something.

- **Dependency direction is one-way:** `App → Features → Core`. A feature never imports another feature's internals; a shared need moves down into `Core`.
- **Split on the second real need, not the first.** A one-feature app is one app target plus `Core`. Add a package when a boundary is being violated or build time hurts — not to look architected.
- Add the package folder to the project as a *local* package; products link to the app target. A package's `Package.swift` pins `swift-tools-version` and `platforms: [.iOS(.v17)]`.
- **Third-party dependencies are SPM, pinned `.upToNextMinor` in a package or an exact version in the project**, with `Package.resolved` committed. Prefer the platform: `URLSession`, SwiftData, Swift Testing, `os.Logger` need no dependency.

## xcconfig per environment

One `Base.xcconfig`, one file per environment that `#include`s it and overrides only what differs: `PRODUCT_BUNDLE_IDENTIFIER`, `PRODUCT_NAME` suffix, `API_BASE_URL`, app icon set, `SWIFT_ACTIVE_COMPILATION_CONDITIONS`.

```
#include "Base.xcconfig"
PRODUCT_BUNDLE_IDENTIFIER = com.example.app.staging
INFOPLIST_KEY_CFBundleDisplayName = MyApp Staging
API_BASE_URL = https:/$()/api.staging.example.com
```

- Wire configurations: Debug → `Debug.xcconfig`, a `Staging` configuration duplicated from Release, Release → `Release.xcconfig`; **schemes** per environment, shared and committed.
- Values reach code through `Info.plist` keys (`$(API_BASE_URL)`) read once at the composition root — never `#if STAGING` scattered in features.
- **An xcconfig is public.** The binary, `Info.plist` and xcconfig carry no secret; a key that must stay secret lives behind your backend ([`mobile/_shared/security`](../../../_shared/security/references/ios.md)). Per-developer or CI values come from an uncommitted `Local.xcconfig` with `#include? "Local.xcconfig"`.

## Format and lint

- **`xcrun swift-format`** ships in the toolchain — it is the formatter. Commit a `.swift-format` (JSON; 4-space indent, `lineLength` 120 is typical) and run `xcrun swift-format lint --strict --recursive App Packages` in CI; `format --in-place` locally.
- **SwiftLint** (0.65) is the linter, **not** a second formatter. Commit `.swiftlint.yml` with `opt_in_rules` for `force_unwrapping`, `force_cast`, `force_try`, `unused_import`, `explicit_acl` off; `custom_rules` forbidding `print(` / `NSLog(` and `DispatchQueue.main`. Run as a build-tool plugin or a CI step, never an Xcode run-script that mutates files.
- Both run on the same paths; the formatter owns whitespace and the linter owns semantics, so the two never argue. Config detail: [`references/packages-and-config.md`](references/packages-and-config.md).

## Test plans

Two `.xctestplan` files in `TestPlans/`, referenced by the shared scheme: **`Unit`** (Swift Testing targets of the app and every package, parallelised, random order, code coverage on) and **`UI`** (XCUITest only for what [`qa-mobile-*`](../test-ids/SKILL.md) does not own). Package test targets are added to `Unit` by name. Writing the tests is [`unit-testing`](../unit-testing/SKILL.md); this skill only makes sure they have a place to run.

## Scene lifecycle and launch screen

Both are mandatory against the iOS 27 SDK (TN3187).

- **SwiftUI `App` lifecycle** is already scene-based — `@main struct MyApp: App { var body: some Scene { WindowGroup { RootView() } } }`. Anything that used `AppDelegate` window setup moves to scene APIs; keep `@UIApplicationDelegateAdaptor` only for what has no SwiftUI equivalent (push-token callbacks — [`notifications-and-links`](../notifications-and-links/SKILL.md)).
- **UIKit apps `[UIKit]`** adopt `UIWindowSceneDelegate` and the `UIApplicationSceneManifest` in `Info.plist`; remove the `window` property from the app delegate.
- **Launch screen:** `INFOPLIST_KEY_UILaunchScreen_Generation = YES` with a `UILaunchScreen` dictionary (background colour + image from the asset catalog), or a `LaunchScreen.storyboard`. No splash that imitates a loaded UI, no text on it (it cannot localise).
- Scene phase handling (resume revalidation) is [`error-handling`](../error-handling/SKILL.md).

## String Catalog and privacy manifest — day one

- **`Localizable.xcstrings`** with the development language set; `LOCALIZATION_PREFERS_STRING_CATALOGS = YES`, `SWIFT_EMIT_LOC_STRINGS = YES`, and *Use Compiler to Extract Swift Strings* on so literals in `Text("…")` land in the catalog. Plurals, formatting and RTL are [`languages`](../languages/SKILL.md).
- **`PrivacyInfo.xcprivacy`** in the app target from the first commit, with `NSPrivacyTracking` `false`, `NSPrivacyTrackingDomains` and `NSPrivacyCollectedDataTypes` empty arrays, and `NSPrivacyAccessedAPITypes` listing each Required Reason API **as it is added** (`UserDefaults` is one). Every local package that uses a Required Reason API ships its own manifest. Reason codes and the privacy questionnaire: [`mobile/_shared/store-compliance`](../../../_shared/store-compliance/references/apple.md); a manifest edit is part of the change that needs it.
- Usage-description strings for permissions are added by the feature that asks ([`device-features`](../device-features/SKILL.md)), never pre-declared.

## Rules

- `SWIFT_VERSION = 6` and warnings-as-errors are **set in the xcconfig**, not inherited.
- One module = one local package once a boundary earns it; direction `App → Features → Core`.
- Default isolation `MainActor` in the app target only; packages stay `nonisolated`.
- One xcconfig per environment; no secret in xcconfig, `Info.plist` or the bundle.
- `xcrun swift-format` formats, SwiftLint lints; both in CI.
- Tuist / XcodeGen present → edit the manifest, regenerate; never the generated `.pbxproj`.
- A privacy manifest and a String Catalog exist before the first feature.
- Never raise the deployment target or language mode of an existing module as a side effect.

## What NOT to do

- Trust the template's `SWIFT_VERSION` or flip a Swift 5 project to 6 in one commit.
- Put `MainActor` default isolation on a package.
- Branch on `#if DEBUG` / `#if STAGING` through feature code instead of reading config once.
- Add CocoaPods to a new project, or a dependency for something the SDK does.
- Commit `Local.xcconfig`, a `.p12`, an API secret or a `GoogleService-Info.plist` with server keys.
- Run SwiftLint's `--fix` in a build phase.
- Add a `Common` / `Utils` package that every module imports.

## Validation (exit gate)

- [ ] `SWIFT_VERSION`, `SWIFT_TREAT_WARNINGS_AS_ERRORS` and isolation are in the xcconfig and `rg -n "SWIFT_VERSION" -g '*.pbxproj'` shows no stray `5.0` on a new module
- [ ] Each environment has an xcconfig, a configuration and a shared scheme
- [ ] `.swift-format` and `.swiftlint.yml` committed; both pass on the tree
- [ ] `Unit` and `UI` test plans exist and the scheme references them
- [ ] Launch screen and scene lifecycle in place; `Localizable.xcstrings` and `PrivacyInfo.xcprivacy` in the app target
- [ ] No secret in any xcconfig or plist

## Handoffs

- Architecture and state → [`architecture`](../architecture/SKILL.md)
- Swift standard, concurrency → [`basics`](../basics/SKILL.md)
- Signing, CI, TestFlight → `mobile-<stack>:release`
- Privacy manifest depth → `mobile-<stack>:store-compliance`
- Swift 5 → 6, CocoaPods → SPM → [`migration`](../migration/SKILL.md)
- Dependencies' security → `mobile-<stack>:security`
- Test ids → [`test-ids`](../test-ids/SKILL.md)
