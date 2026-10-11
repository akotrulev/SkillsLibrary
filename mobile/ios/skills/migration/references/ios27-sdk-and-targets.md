# The iOS 27 SDK's forced changes, and deployment-target raises

Two moves that share one rule: **neither happens as a side effect.** Facts below are plan §4.2's; re-read the Xcode 27 release notes and developer.apple.com/news/upcoming-requirements before a run — Apple dates move.

## A. Linking the iOS 27 SDK

Xcode 27.0 (GA 2026-09-14/15) builds against the iOS 27 SDK. Apple's upload requirement is the Xcode 26 SDK today and **the iOS 27 SDK from April 2027** — so the move is a deadline, and the question is when, not whether. Linking it makes these mandatory:

| Change | What to do | Reference |
|---|---|---|
| **UIScene lifecycle** (TN3187) | A `UIApplicationSceneManifest` and a `UIWindowSceneDelegate`; the window leaves the app delegate. SwiftUI `App` lifecycle apps are already there | [`uikit/references/uiscene-migration.md`](../../uikit/references/uiscene-migration.md) |
| **A launch screen** | `UILaunchScreen` dictionary or a launch storyboard | [`project-setup`](../../project-setup/SKILL.md) |
| **Liquid Glass** | `UIDesignRequiresCompatibility` is ignored — the opt-out is gone. Remove it; re-screenshot every screen; delete custom bar backgrounds that fight system bars | [`styling`](../../styling/SKILL.md), E1–E3 |
| **The `@State` macro** | An `@State` initial value is evaluated once; read every `@State` whose initial value depends on a parameter or has a side effect | [`observation`](observation.md) |
| **Deprecations** | `PreviewProvider` → `#Preview`; `FileDocument` → its replacement per the release notes; `canOpenURL:` → drop probing (J10, F15) | A11, F15 |
| **Debugging device floor** | Xcode 27 debugs only devices on iOS 17+; an older test device stops being a debug target | — |

Steps, one commit each:

1. Baseline on the current Xcode. Open the project in Xcode 27 **without** changing the SDK-dependent settings; build and test.
2. Fix the scene lifecycle and launch screen (they block the archive).
3. Remove the glass opt-out; screenshot light / dark / large text / iPad; fix collisions.
4. Review `@State` sites and the deprecated APIs.
5. Archive; run the store-compliance rows ([`mobile-<stack>:store-compliance`](../../../../_shared/store-compliance/SKILL.md)); confirm Swift 6 settings were **not** changed by the new template (the Xcode 27 template still defaults `SWIFT_VERSION = 5.0` — [`project-setup`](../../project-setup/SKILL.md)).

Raising the Xcode version is not raising the Swift language mode or the deployment target: three settings, three decisions.

## B. A deployment-target raise

Primary iOS 17, supported iOS 16, below 16 the UIKit lane. Uploads need at least iOS 13 since 2026-09-09.

| Raise | Unlocks | Retires |
|---|---|---|
| 16 → 17 | `@Observable`, SwiftData, `#Preview`-era APIs, the `@State` macro behaviour on every device | `ObservableObject` as the default, Core Data for new stores, availability guards for 17 |
| 17 → 18 / later | Per the release notes of that iOS | The `#available` branches written for the older target |

1. **Decide with data** — the share of active devices on each iOS version from App Store Connect analytics, and the product owner's call. The skill does not choose.
2. **One iOS version per raise.** Set `IPHONEOS_DEPLOYMENT_TARGET` once per module (A8) — in the xcconfig, not scattered across targets.
3. **Delete only the guards the raise makes dead**: `rg -n "#available\(iOS|@available\(iOS" -g '*.swift'`. A guard for a version above the new target stays.
4. **Do not adopt the unlocked APIs in the same commit** — that is [`observation`](observation.md) and its siblings, as their own runs.
5. Update the store listing's minimum OS note and the QA device matrix (hand-off to the `qa-mobile-<stack>` peer).

## Done

SDK: archive builds on Xcode 27, the manifest and launch screen are in place, no screen lost its glass chrome to a custom background; audit rows A9, A11, E1, E2 pass. Target: one `IPHONEOS_DEPLOYMENT_TARGET` per module, dead guards removed, A4 and A8 pass.
