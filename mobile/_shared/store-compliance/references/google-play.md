# Google Play — rules that code and config satisfy

Verified 2026-10-10 against developer.android.com and the Play Console policy page (support.google.com/googleplay/android-developer/answer/9888170) except where marked. Re-verify after **2027-01-15**; the 2027-01-27 and 2027-02-01 dates make that the last safe review point.

## 1. Target API level

| Item | Rule | Source |
|---|---|---|
| New apps and updates | Must target **API 36** since 2026-08-31 (developers could request an extension to 2026-11-01) | developer.android.com/google/play/requirements/target-sdk |
| Existing apps, no update | Stay visible to users on devices at or below their target; below a threshold they are hidden from new users on newer devices | same |
| Expo | `expo-build-properties` → `android.targetSdkVersion`; SDK 57 defaults track the current requirement — check the generated manifest, not the default | docs.expo.dev |
| Kotlin / Gradle | `targetSdk` in `defaultConfig` (AGP 9.4); `compileSdk 37`, `minSdk 24` is the house baseline | build.gradle.kts |

Raising `targetSdk` changes runtime behaviour (edge-to-edge enforced at 35, predictive back at 36, large-screen orientation and resizability ignored ≥ sw600dp at 36). Report a gap; the migration is `migration`'s, never a side effect.

## 2. 16 KB memory page sizes

- **Official (developer.android.com/guide/practices/page-sizes), read 2026-10-10:** apps targeting **Android 15 (API 35) and higher** must support 16 KB page sizes on 64-bit devices; **starting 2027-02-01, updates that do not support it cannot be released**. Play Console shows the same warning.
- **Other dates circulate** — forum posts and secondary articles cite 2025-11-01 and 2026-05-31 for earlier waves and extensions. Treat the official page as the date of record and write `2027-02-01` in reports; if a console message shows a different date, report both and mark the console's as the one that binds that app.
- **Repo checks:** AGP 8.5.1+ / NDK r28+ build 16 KB-aligned `.so` files by default; older NDKs need `-Wl,-z,max-page-size=16384`. Every prebuilt native dependency (`.aar`, `.so` in `jniLibs`) must be a 16 KB-aligned release — `zipalign -c -P 16 4 app.apk` and `check_elf_alignment.sh` verify a built artifact (a build step, so G1 or CI runs it, not a source read). `android:extractNativeLibs="false"` with uncompressed libs is the packaging that pairs with it.
- **React Native / Expo:** the RN and Hermes binaries are aligned from the New Architecture releases; a third-party native module or an old `.so` is the usual miss.

## 3. Data safety, privacy policy (console + repo)

The **Data safety form** is console-only. It must describe every data type the app **and its SDKs** collect or share, whether it is optional, encrypted in transit, and deletable. An SDK's own documentation is the evidence (Firebase Analytics, Crashlytics, Ads, Auth0 all publish theirs). The repo's job is to produce the evidence list:

- Every SDK in `build.gradle*` / `package.json` mapped to the data types it collects.
- Every `<uses-permission>` mapped to a Data safety entry (location, contacts, photos, device identifiers).
- A privacy-policy URL reachable inside the app and set in the console.

Any mismatch is reported as a console item, `likely mismatch — verify`.

## 4. Account deletion — in the app and on the web

Apps that let people create an account must:

1. Provide an **in-app path** to start deletion (Settings → Account), naming what is deleted and what is retained and why.
2. Provide a **web path** — a public URL where a person who no longer has the app can request deletion — and enter it in the Console's data-deletion field.
3. Delete or anonymise the data on the server, not only locally.

Repo checks: the in-app screen and the call to the deletion endpoint. Console check: the URL field (console item). Apple's rule (5.1.1(v)) is stricter on in-app reach; one flow serves both — `apple.md` §6 adds Sign in with Apple token revocation.

## 5. Permission declarations

Restricted permissions need a declaration form in Play Console and are **blocked at publish** without an approved use. The manifest is the repo evidence; the form is a console item.

| Permission / feature | Policy |
|---|---|
| `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO` | Apps targeting API 33+ may request them **only if the system picker is not sufficient for core functionality**; otherwise use the photo picker (`PickVisualMedia`) and drop the permission. A declaration explains why the picker cannot work. |
| `MANAGE_EXTERNAL_STORAGE` (all-files access) | Restricted on Android 11+; core functionality only (file managers, backup, antivirus, document management); media access and picking individual files do **not** qualify — use SAF or MediaStore. Access review before publishing; user enables "All files access" in settings. |
| Exact alarms | `USE_EXACT_ALARM` is a **restricted permission** — declare it only if the app's **core functionality** needs exact alarms (alarm / timer apps, calendar apps showing event notifications); the Console declaration form applies and the app cannot publish with it otherwise. `SCHEDULE_EXACT_ALARM` provides the same capability with **user approval** and is the default for everything else; since Android 13 it is not pre-granted to newly installed apps (denied by default), so code must check `canScheduleExactAlarms()` and have a working denied path. Prefer inexact alarms and WorkManager when a minute of slack is acceptable. (Read 2026-10-10 from developer.android.com Android 14 behaviour-changes page and the Play policy page; the page lists no deadline.) |
| Foreground services | Every `<service android:foregroundServiceType>` declares a type, the matching `FOREGROUND_SERVICE_*` permission is requested, and Play Console asks for a **per-type declaration** and a demo video for the types it reviews. A foreground service may reach location only as a continuation of an in-app user-initiated action. API 37 adds background-audio FGS rules. |
| `USE_FULL_SCREEN_INTENT` | Targeting Android 14+: auto-granted only for calling and alarm apps; others must ask the user and explain why. Declaration form required to establish eligibility. Never for ads. |
| Background location | Declaration + minimum scope (coarse over fine, foreground over background). |
| `ACCESS_LOCAL_NETWORK` | New at API 37 — runtime permission for LAN access; add it only where the feature needs it. |

## 6. Developer verification

Google requires apps installed on certified devices to come from verified developers. Enforcement: **Brazil, Indonesia, Singapore, Thailand from 2026-09-30**, global in 2027. The registration is console-and-account work; the repo implication is that the package name and signing key are registered to the verified identity — a package or key change after registration re-opens verification. Report as a console item.

## 7. Dates that fall inside the next release cycle

| Date | Rule |
|---|---|
| 2026-11-01 | Latest extension of the API 36 target requirement |
| **2027-01-27** | **Contacts Permissions policy** — apps without broad contact needs use the Android Contact Picker; **Location Permissions policy** — the location button is the recommended minimum scope for precise location |
| **2027-02-01** | 16 KB page-size block on updates (§2) |
| 2027 (global) | Developer verification on all certified devices |
| 2027-02 | Android vitals: memory vitals begin to affect store visibility |

The 2027-01-27 and 2027-02-01 deadlines are one week apart; schedule the contact-picker and location-button work and the native-library alignment into the same release.

## 8. Quality bars that affect visibility

Play's Android vitals thresholds: crash rate 1.09 % (8 % per phone model), user-perceived ANR 0.47 % (8 % per model), excessive partial wake locks 5 % (enforced since 2026-03-01), slow start cold ≥ 5 s / warm ≥ 2 s / hot ≥ 1.5 s. They are telemetry, not repo facts — report them as console items and route the fix to `performance` and `error-handling`.
