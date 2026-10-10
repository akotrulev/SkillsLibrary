---
name: mobile-shared-store-compliance
description: Use when a mobile app is about to ship or changes what it does — before a release, on adding a permission, SDK, account system, tracking or purchases, or near a store deadline. Triggers "will App Store review pass this", "Play rejected the update", "do we need a privacy manifest", "account deletion rules". Do NOT use for signing and rollout (`mobile-shared-release`), IAP mechanics (`mobile-shared-in-app-purchases`), or scanning a built binary (qa `mobile-app-scan`).
---

# Mobile — Store Compliance

Turns the App Store and Google Play rules that **code or config can satisfy** into checks an agent runs against a repo. The house rule from `CLAUDE.md` § Mobile code rules: **store rules are code rules** — privacy manifest, Required Reason APIs, in-app account deletion, permission declarations, target API level.

**The honest boundary.** Half of what a store reviews lives only in **App Store Connect** or **Play Console** — privacy nutrition labels, the Data safety form, age rating, the data-deletion URL, permission declaration forms, listing metadata. A repo read cannot see them. Those rows are reported as **likely mismatch — verify in the console**, never as passed. A green repo scan is "the code is consistent with a clean submission", not "the store will accept it".

**Dated rules.** Store rules move every quarter. Every row below carries a `Source` and a `Re-verify after` date; a row past its date is re-checked at the source before it is relied on, and a fact that has changed is corrected here, not worked around.

## When to use

- Before every release candidate, as the last gate before upload
- Adding a permission, a third-party SDK, an account system, analytics / tracking, or anything that sells
- A store deadline is near (target API, SDK upload floor, 16 KB pages, developer verification)
- A rejection or a Play pre-launch warning has arrived and its cause must be located in code
- Brownfield intake — what would a store reviewer find today?

## When NOT to use

- Signing, build numbers, tracks, phased rollout, OTA rules → `mobile-shared-release`
- StoreKit / Play Billing mechanics and guideline 3.1.1 implementation → `mobile-shared-in-app-purchases`
- Secure-coding rules (storage, TLS, WebView) → `mobile-shared-security`
- Scanning a built APK/AAB/IPA → qa `mobile-app-scan` (peer, not loaded)
- Accessibility implementation → the stack's `accessibility` skill (this skill only lists the store-facing label)

## Version lane (verified 2026-10-10)

| Fact | Value |
|---|---|
| iOS upload floor | Xcode 26 SDK since 2026-04-28; **iOS 27 SDK from April 2027**; minimum deployment target iOS 13 since 2026-09-09 |
| Android target | **API 36** for new apps and updates since 2026-08-31 (extensions to 2026-11-01) |
| Review guidelines | Apple revised 2026-06-08; Play policy pages updated continuously |
| Detected from | `Info.plist` / `project.pbxproj` / `app.json` / `app.config.*`; `build.gradle(.kts)` `targetSdk`; `AndroidManifest.xml` |

Detect the project's lane first (Expo managed vs bare, SwiftUI vs UIKit, Compose vs Views) — the *file* a rule lands in differs, the rule does not. Never raise a target as a side effect of this audit; report the gap and let `project-setup` / `migration` own the change.

## Procedure

1. **Inventory what the app does.** Read, do not guess: accounts (sign-up, sign-in providers), purchases, tracking / analytics / ads SDKs, permissions requested (manifest + plist purpose strings), AI features that send user data to a model, user-generated content, web views, OTA update tooling, background modes / foreground services, target SDK and deployment target. Write the inventory as a table at the top of the report — every later row cites it.
2. **Select the rules that apply.** Match the inventory to the rule table below and open the platform reference: [`references/apple.md`](references/apple.md) for iOS, [`references/google-play.md`](references/google-play.md) for Android. A React Native / Expo app is both; the config plugin or `app.json` field that produces each native artifact is named in the reference.
3. **Check the repo side.** For each selected rule, find the file that satisfies it (privacy manifest present and complete, `<uses-permission>` justified, account-deletion screen reachable, `targetSdk` current, native libs 16 KB aligned). Cite `file:line`.
4. **Split the console side.** For each rule whose evidence lives only in App Store Connect / Play Console, emit a **console item** with the exact form or field and what the repo implies it must say — e.g. "code requests `ACCESS_FINE_LOCATION` and links the Firebase Analytics SDK → Data safety must declare precise location and device identifiers". A console item is **always** `likely mismatch — verify`, never a pass.
5. **Check SDKs.** Every third-party SDK on the platform's required-manifest list must ship its own privacy manifest and signature (iOS) or be on a 16 KB-aligned version (Android). Update the dependency; never hand-write another vendor's manifest.
6. **Report.** Findings use the audit severities (blocker — a rejection or block; major; minor; nit) with ids from [`references/audit-checks.md`](references/audit-checks.md) (`L1…`). Deadlines inside 90 days are called out even when the code already passes.

## Rule table (dated)

| Rule | Platform | Current fact | In repo? | Source | Re-verify after |
|---|---|---|---|---|---|
| Privacy manifest + Required Reason APIs | iOS | `PrivacyInfo.xcprivacy` in the app and in every SDK / framework that uses a Required Reason API; reasons from Apple's closed list; enforced since 2024-05-01 | Yes | developer.apple.com/documentation/bundleresources/privacy-manifest-files | 2027-01-15 |
| Listed third-party SDKs | iOS | A listed SDK needs its own manifest **and** a valid signature | Yes | developer.apple.com/support/third-party-SDK-requirements | 2027-01-15 |
| Purpose strings | iOS | One `NS…UsageDescription` per protected resource, specific, never generic | Yes | developer.apple.com/documentation/bundleresources/information-property-list | 2027-01-15 |
| App Tracking Transparency | iOS | `NSUserTrackingUsageDescription` + `ATTrackingManager` before any tracking; **EU alternative prompt from iOS 27.2** | Partly (label in console) | developer.apple.com/app-store/review/guidelines §5.1.2 | 2026-12-31 |
| In-app account deletion | iOS + Android | Any app with account creation offers deletion **in the app** (Apple 5.1.1(v)); Play requires in-app **and** a web path | Yes (UI) + console (URL) | Apple guidelines 5.1.1(v) · support.google.com/googleplay/android-developer/answer/13327111 | 2027-01-15 |
| Sign in with Apple revocation | iOS | On deletion, revoke the Apple token via the REST API | Yes (backend call) | developer.apple.com/documentation/sign_in_with_apple | 2027-01-15 |
| Downloaded / interpreted code | iOS | Guideline 2.5.2 + DPLA §3.3.1(B): no behaviour change through downloaded code beyond what review saw | Yes (OTA config) | Apple guidelines 2.5.2 | 2026-12-31 |
| Login services | iOS | 4.8: offer an equivalent privacy-preserving login when third-party / social login is the primary sign-in | Yes | Apple guidelines 4.8 | 2027-01-15 |
| AI data-sharing consent | iOS | 5.1.2: explicit consent before sending personal data to a third-party AI | Yes (consent UI) | Apple guidelines 5.1.2 | 2026-12-31 |
| Age-rating questionnaire | iOS | Mandatory since 2026-01-31 | Console only | App Store Connect | 2027-01-15 |
| Accessibility Nutrition Labels | iOS | Voluntary; claim only what was tested | Console only | developer.apple.com/accessibility | 2027-04-01 |
| Target API level | Android | API 36 for new apps and updates since 2026-08-31 (extensions to 2026-11-01) | Yes | developer.android.com/google/play/requirements/target-sdk | 2026-12-15 |
| 16 KB page size | Android | Updates targeting API 35+ with 64-bit libs blocked from **2027-02-01**; other dates circulate | Yes | developer.android.com/guide/practices/page-sizes | 2027-01-01 |
| Data safety form | Android | Must match SDK behaviour; the SDK's own declaration is not yours | Console only | support.google.com/googleplay/android-developer/answer/10787469 | 2027-01-15 |
| Permission declarations | Android | Photo/video, all-files, exact alarm, FGS types, full-screen intent need Console declarations | Yes (manifest) + console | support.google.com/googleplay/android-developer/answer/9888170 | 2027-01-15 |
| Photo picker | Android | Photo / video permissions only when core functionality needs more than the system picker | Yes | same | 2027-01-15 |
| Developer verification | Android | Enforced in BR / ID / SG / TH from 2026-09-30, global 2027 | Console only | developer.android.com/developer-verification | 2027-01-15 |
| Contact picker, location button | Android | Policies effective **2027-01-27** | Yes | support.google.com/googleplay/android-developer/answer/9888170 | 2027-01-27 |
| Android vitals | Android | Crash 1.09 %, user-perceived ANR 0.47 %, partial wake locks 5 % — exceeding them lowers store visibility | Telemetry (not repo) | developer.android.com/topic/performance/vitals | 2027-02-01 |

A row marked **Console only** is a console item every time; a row marked **Yes** is checked in the repo and, where the console also holds a mirror, produces a console item as well.

## Output

```
## Inventory
| Capability | Evidence (file:line) |

## Repo findings        (L-ids, severity, file:line, fix direction)
## Console items        (form / field → what the repo implies → likely mismatch — verify)
## Deadlines ≤ 90 days  (rule, date, state)
## Not checked          (rules whose source was past its re-verify date and could not be re-read)
```

## Worked example

Inventory: Expo SDK 57 app, Auth0 login with Google + email, Firebase Analytics, push, `expo-updates`, photo upload, `targetSdkVersion 35`.

- `app.json` has no `ios.privacyManifests` and `expo-file-system` + AsyncStorage are installed → **L1 (blocker)**: declare `FileTimestamp C617.1` and `UserDefaults CA92.1`, then confirm with the Xcode privacy report; Firebase ships its own manifest.
- Google sign-in is the primary login with no Apple option → **L9 (blocker)**: guideline 4.8.
- No delete-account screen under Settings → **L5 (blocker)**: in-app deletion, token revocation, and a console item for Play's web deletion URL.
- `READ_MEDIA_IMAGES` in the manifest, upload uses a file input → **L14 (major)**: use the photo picker, drop the permission.
- `targetSdkVersion 35` → **L12 (blocker)**: API 36.
- Console items: Data safety (device IDs + analytics), App privacy labels, age rating — all `likely mismatch — verify`.

## Hard rules

- A console-only rule is never reported as passed.
- A reason code, date or deadline not re-read at its source this session is written with its `Re-verify after` date and flagged **unverified today** when that date has passed.
- Never write another vendor's privacy manifest; update the SDK.
- Never raise `targetSdk` or a deployment target as a side effect — report it.

## Related skills & peers

- `mobile-shared-security` — secure-coding rules; MASVS-PRIVACY overlaps here (permission minimisation, tracking domains)
- `mobile-shared-release` — signing, tracks, OTA mechanics
- `mobile-shared-in-app-purchases` — 3.1.1 and Play payments policy implementation
- `design/ethical-patterns` — permission priming, consent symmetry
- qa `mobile-app-scan` *(peer, not loaded)* — scans the built binary for what the store scanner will also find
