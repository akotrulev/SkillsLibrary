---
name: mobile-shared-release
description: Use when a mobile build must be versioned, signed, uploaded, rolled out or patched over the air — build numbers, signing without secrets in the repo, TestFlight and Play tracks, phased rollout and halt, EAS Update, symbol upload. Triggers "how do we sign in CI", "halt the rollout", "can we ship this OTA". Do NOT use for pipeline YAML (`devops-engineer`), CI test wiring (`qa-cicd-<stack>`), or store rules (`mobile-shared-store-compliance`).
---

# Mobile — Release and Signing

Rules for getting a mobile build from a commit to users: **what number it carries, what signs it, where it lands, how it is rolled out, how it is halted, and what may change without a store review.** Tool detail lives in one reference per tool.

**The fence.** This skill states *what must be true*; it writes no pipeline. Workflow / pipeline YAML (GitHub Actions, Azure Pipelines, GitLab) is `devops-engineer`'s (`devops/github-actions`); the test-suite CI lane is `qa-cicd-<stack>`'s. Where a rule needs a pipeline step, name the step and hand it over — the EAS Workflows file in [`references/eas.md`](references/eas.md) is the one exception, because it is the build tool's own config.

## When to use

- Setting up or reviewing how an app is built, signed and uploaded
- Choosing the version / build-number scheme, or a build number was rejected as a duplicate
- Planning a rollout (TestFlight, Play tracks, phased / staged) or halting a bad one
- Deciding whether a change can go over the air or needs a store build
- Wiring crash-symbol upload (dSYM, R8 mapping, Hermes source maps)

## When NOT to use

- Writing the CI workflow / pipeline YAML → `devops-engineer` (`devops/github-actions`, `azure-pipelines`)
- Test sharding, Allure, device-farm wiring → `qa-cicd-<stack>`
- App Store / Play rules and deadlines → `mobile-shared-store-compliance`
- Where tokens live at runtime → `mobile-shared-security`
- Crash reporter choice and telemetry → `mobile-shared-observability`

## Version lane (verified 2026-10-10)

| Fact | Value | Re-verify after |
|---|---|---|
| fastlane | 2.240.1 | 2026-12-31 |
| GitHub-hosted `macos-14` | **removed 2026-11-02**; `macos-latest` = macos-26 arm64. Pin an explicit image, never `latest` | before 2026-11-02, then 2027-01-15 |
| Azure DevOps | macOS 26 / Xcode 27 agents in preview | 2026-12-31 |
| Apple upload | Xcode 26 SDK since 2026-04-28; iOS 27 SDK from April 2027 | 2027-01-15 |
| Play | target API 36; 16 KB page size — updates blocked from 2027-02-01 | 2027-01-15 |

Source: github.com/actions/runner-images · developer.apple.com/news/upcoming-requirements. Detect the project's tooling first (Expo managed / bare, Xcode project, Gradle) and follow the matching reference.

## Procedure

1. **Detect.** Expo / EAS (`eas.json`), fastlane (`Fastfile`), Xcode Cloud (`ci_scripts/`), Gradle Play Publisher (`com.github.triplet.play`). Several may coexist; one owns each artifact.
2. **Version and build number.** Two numbers, two jobs. The **version** (`CFBundleShortVersionString` / `versionName`) is the human release, semver-shaped, bumped by a person per release. The **build number** (`CFBundleVersion` / `versionCode`) is **monotonic and machine-assigned** — never edited by hand, never reused, never derived from a branch. Apple needs a higher build per version; Play needs a strictly higher `versionCode` across all tracks (max 2,100,000,000). Source it from the build system (EAS remote versioning `autoIncrement`, a CI run number, or the store's latest + 1), not from a committed file two branches can both edit.
3. **Sign with nothing in the repo.** No keystore, `.p12`, `.p8`, provisioning profile, or password in git or in the app bundle. See the table below; tool detail in the references.
4. **Pin the toolchain.** The CI runner image **and** the Xcode version are named explicitly (`macos-15` + `Xcode 26.x`, never `macos-latest` / "latest Xcode"); the Gradle wrapper, AGP and JDK are pinned in the repo. A floating image changes the SDK under a release with no diff.
5. **Distribute to a track first.** iOS: TestFlight internal (no review) → external (beta review) → App Store. Android: internal testing → closed → open → production. Nothing goes to production that has not sat on the previous track.
6. **Roll out gradually, with a halt path.** iOS: *phased release* over 7 days (1 → 2 → 5 → 10 → 20 → 50 → 100 %); it can be paused up to 30 days, and **a pause stops automatic updates only — people who search and tap Update still get it**. Android: *staged rollout* by percentage; **halt** stops new installs of that version, and the fix ships as a **higher `versionCode`** (a rollback is a new, higher build of the old code). State who may halt, on which signal (crash-free users, ANR rate, error-budget burn from `mobile-shared-observability`), and the threshold.
7. **Upload symbols with every build.** A crash report without symbols is unusable. See Symbols below. A build whose symbols did not upload is not released.
8. **Decide OTA vs store build** with the OTA rules below.

## Signing — what holds the secret

| Platform | Mechanism | Lives in | Never |
|---|---|---|---|
| iOS | **App Store Connect API key** (`.p8`, key id, issuer id) for upload and cert management | CI secret store, or EAS credentials | an Apple-ID password with 2FA workarounds |
| iOS | fastlane **`match`** — certs and profiles encrypted in a private git repo / bucket, passphrase in CI | private store + CI secret | the signing repo public, or the passphrase beside it |
| iOS | **Xcode Cloud** — cloud-managed signing, no certs on your machine | Apple | exporting the distribution cert "to be safe" |
| iOS + Android | **EAS credentials** (`eas credentials`, remote) | Expo | `credentials.json` committed |
| Android | **Play App Signing** — Google holds the app signing key; you hold only an **upload key** | Google + a CI secret for the upload key | the app signing key on a laptop; the upload keystore in git |

A lost upload key is recoverable (request a reset in Play Console); a lost non-Play-signed key is not — which is why Play App Signing is the default for every new app.

## OTA rules

OTA (EAS Update, and any JS-bundle updater) changes **JavaScript and assets only**. It is bounded, not open:

- **Apple Guideline 2.5.2 and DPLA §3.3.1(B):** downloaded code may not change the app's primary purpose or add features that were not in the reviewed binary; an interpreted-code update must run in the OS-provided WebKit / JavaScriptCore. A bug-fix or content change in the same feature set is the intended use.
- **Google Play — Device and Network Abuse policy:** an app may not download executable code (DEX, native libs) from outside Play; interpreted JS inside a VM / WebView, with no store-bypassing purchases and no deceptive behaviour, is allowed.
- **Never ship a native change over the air** — a new native module, a changed permission, entitlement, `Info.plist` / manifest edit, or SDK bump needs a store build. Tie the update channel to a compatibility key (`runtimeVersion` with the `fingerprint` policy) so an incompatible JS bundle can never reach an older binary.
- **Sign the updates** (code signing) so a compromised update server cannot push code.
- **Roll out OTA like a release:** a channel per environment, a staged percentage, and a rollback (re-point the channel / republish the previous update).

Anything else — "OTA any change that is not in the store binary" — is a policy violation, not a feature. `mobile-shared-store-compliance` row `L8` audits it.

## Symbols

| Artifact | Produced by | Goes to | Notes |
|---|---|---|---|
| **dSYM** | Xcode archive (`DWARF with dSYM`) | the crash reporter (Sentry / Crashlytics) | with bitcode gone, the dSYM from *your* archive matches; automate the upload as a build phase or post-archive step |
| **R8 / ProGuard mapping** (`mapping.txt`) | release build with minify on | Play Console (auto via AAB) **and** the crash reporter | per `versionCode`; never delete after release |
| **Hermes source maps** | `expo export` / Metro with `--sourcemap` | the crash reporter, keyed by release + dist | upload the **Hermes** map composed with the JS map; a plain JS map symbolicates wrong |
| **Native debug symbols** (`.so`) | NDK build | Play Console + reporter | needed for NDK crashes |

Key each upload to the exact `version (build)` the user runs — the same value the app reports as `service.version` (`mobile-shared-observability`).

## Output

A release setup note or review: version and build-number source, signing mechanism per platform, pinned runner + Xcode, track plan, rollout and halt thresholds, OTA verdict, symbol-upload step, and the hand-offs to `devops-engineer` (pipeline) and `qa-cicd-<stack>` (tests). Findings use ids from [`references/audit-checks.md`](references/audit-checks.md) (`T1…`).

## References

- [`references/eas.md`](references/eas.md) — EAS Build, credentials, Update, `runtimeVersion`, code signing, the Maestro E2E job
- [`references/fastlane.md`](references/fastlane.md) — `match`, App Store Connect API key, lanes, `pilot` / `deliver`
- [`references/xcode-cloud.md`](references/xcode-cloud.md) — workflows, `ci_scripts`, cloud signing, TestFlight
- [`references/gradle-play.md`](references/gradle-play.md) — Play App Signing, upload key, Gradle Play Publisher, tracks, staged rollout
- [`references/audit-checks.md`](references/audit-checks.md) — fragment rows `T1…`
