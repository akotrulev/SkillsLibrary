# Gradle + Google Play

Docs: developer.android.com/studio/publish/app-signing · developer.android.com/guide/app-bundle · github.com/Triple-T/gradle-play-publisher.

## Signing: Play App Signing

- New apps use **Play App Signing**: Google holds the app signing key; you sign uploads with an **upload key**. A compromised or lost upload key is reset in Play Console; the app signing key never leaves Google.
- The upload keystore is **not in the repo**. CI decodes it from a base64 secret to a temp path and passes the four values (`storeFile`, `storePassword`, `keyAlias`, `keyPassword`) through environment variables read in `build.gradle(.kts)` — the build file holds only the `System.getenv` names.
- Local release builds without the env vars fall back to unsigned / debug; they must never fall back to a committed keystore.

## Version code

- `versionCode` is **monotonic across every track** and never reused. Assign it in the build from the CI run number or the Play latest + 1; do not hand-edit a committed number. `versionName` is the human release.
- Ship **AAB**, not APK, to Play.

## Tracks and rollout

- Internal testing → closed → open → production. New personal accounts have closed-testing prerequisites; check Play Console for the current count and duration before planning a first release.
- **Staged rollout:** production releases start at a percentage (1 → 5 → 20 → 50 → 100). **Halt** stops further distribution of that version; **a fix is a higher `versionCode`**, since a version code cannot be re-uploaded.
- Gradle Play Publisher: `play { track.set("internal"); userFraction.set(0.05); releaseStatus.set(ReleaseStatus.IN_PROGRESS) }`, service-account JSON from a CI secret. Verify plugin and DSL names against its README before use.

## Symbols

- R8 mapping: AABs upload `mapping.txt` to Play automatically when minification is on (`isMinifyEnabled = true`, R8 full mode); also upload it to the crash reporter per `versionCode`. Native debug symbols: `ndk { debugSymbolLevel = "FULL" }`.
- Firebase Crashlytics Gradle plugin uploads mapping on `assembleRelease` / `bundleRelease` given its config; Sentry's Gradle plugin likewise.

## Dated Play facts (see `mobile-shared-store-compliance`)

- Target API 36 for new apps and updates; 16 KB page size — updates blocked from 2027-02-01; developer verification enforced in BR / ID / SG / TH from 2026-09-30, global 2027. Re-verify at 2027-01-15.

## Traps

- Two uploaders (Gradle Play Publisher and `eas submit`) racing on one `versionCode`.
- A `versionCode` derived from `versionName` arithmetic that overflows or repeats.
- The pipeline invoking `./gradlew bundleRelease` is `devops-engineer`'s YAML.
