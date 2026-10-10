# Bare React Native → Expo (`install-expo-modules`, adopting prebuild)

Sources: docs.expo.dev/bare/installing-expo-modules · docs.expo.dev/guides/adopting-prebuild · docs.expo.dev/bare/using-expo-cli · expo.dev/blog/how-i-migrated-my-bare-react-native-app-to-expo.

Two separate moves — **adopt Expo modules** (low risk, reversible), then **adopt prebuild / CNG** (the real migration). Each is its own change; stopping after the first is a valid end state.

## Pre-flight

1. **Pick the Expo SDK that matches the installed React Native** — not every RN version has an SDK. If none does, the RN upgrade is a separate, earlier run (React Native Upgrade Helper).
2. **Clean tree, builds on both platforms**, baseline recorded (SKILL gate). Commit the generated-vs-edited picture: `git ls-files ios android | head`.
3. **List every native edit** — `AppDelegate`, `MainActivity` / `MainApplication`, `Info.plist`, `AndroidManifest.xml`, Gradle files, Podfile, extensions, signing, schemes, entitlements. This list is the config-plugin work list.

## Move 1 — Expo modules and CLI

```bash
npx install-expo-modules@latest
```

Installs `expo`, wires `AppDelegate` / `MainApplication` for the Expo Modules API, and enables EAS Update, Expo Router, `expo-dev-client` and the SDK's libraries. If the automatic edit fails, follow the manual steps on the docs page and say which you did.

Then switch the tooling: scripts to `expo start` / `expo run:ios` / `expo run:android`, Metro config to `expo/metro-config`, Babel preset to `babel-preset-expo`, entry via `expo/AppEntry` or `registerRootComponent`. Install further natives only with `npx expo install`.

Verify: both platforms build and launch; `npx expo-doctor` clean.

## Move 2 — adopt prebuild (CNG)

Adopting prebuild means `ios/` and `android/` become **generated and gitignored**, and every native edit lives in config. Do it only when the team wants it; a bare project that keeps native code by hand is a legitimate end state (`[bare]`).

1. **Set `ios.bundleIdentifier` and `android.package`** in `app.json` / `app.config.ts`; add `scheme`, icons, splash, permission strings, `newArchEnabled` where the SDK still reads it.
2. **Translate each native edit** from the pre-flight list into the cheapest home, in this order: built-in `app.json` field → the library's own config plugin → a small local config plugin (`withInfoPlist`, `withAndroidManifest`, `withAppDelegate`…) ([`native-modules`](../../native-modules/SKILL.md)). Native source files that cannot be generated move into a local Expo module.
3. **Prove it on a scratch copy of the folders:** move `ios/` and `android/` aside, run `npx expo prebuild --clean`, build both, diff the generated projects against the moved ones. The diff is what your plugins still miss.
4. **Commit the config, then remove `ios/` and `android/` from git** and add them to `.gitignore`. Do not do the removal in the same commit as the first plugin.
5. **EAS / CI.** `eas build` runs prebuild itself; local scripts call `expo prebuild` or `expo run:*`. Re-state signing and entitlements in config ([`mobile-shared-release`](../../../../_shared/release/SKILL.md)).
6. **Re-run** a development build, a release build and the primary flows on both platforms.

## Traps

- **Deleting `ios/` and `android/` before the plugins exist** loses native edits for good.
- **A plugin that passes on first prebuild and breaks on the second** — plugins must be idempotent; test with two consecutive `prebuild --clean` runs.
- **Pods / Gradle versions pinned by hand** in the old projects — they move to `expo-build-properties`.
- **Mixed `@react-navigation/*` and Expo Router** — pick one; SDK 56+ Expo Router has its own core.
- **A native module nobody owns** — list it under Known unknowns rather than guessing a plugin.
