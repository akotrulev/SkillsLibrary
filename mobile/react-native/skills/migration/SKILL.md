---
name: mobile-react-native-migration
description: Use when an Expo / React Native project changes lane — an Expo SDK upgrade (one SDK per change), moving from the legacy to the New Architecture on SDK 54, bare → Expo (`install-expo-modules`, adopting prebuild), or embedding RN in an existing native app (`expo-brownfield`, Callstack). Triggers "upgrade to SDK 57", "we are on SDK 52", "adopt CNG", "add React Native to our iOS app". Do NOT use for feature work, minor bumps or a fresh app (`mobile-react-native-project-setup`).
---

# React Native / Expo — Migration

Owns changing the **version lane or workflow** of an existing project. Every other skill in this stack is version-aware and applies what is already there; this one is the only skill that moves the lane, and it does so as **its own change** — never inside feature work, never two moves at once.

## Version lane

| Lane | SDK | Migration consequence |
|---|---|---|
| **Primary** | **57** (RN 0.86, React 19.2) | The target of every upgrade unless the project names another |
| `[SDK58]` | 58 beta | Not a target until stable; when it ships, 57 → 58 is one more run of [`sdk-upgrade`](references/sdk-upgrade.md) |
| Supported | 55–56 | One step each to reach 57; SDK 56 + Hermes V1 + Reanimated is fixed in `expo@57.0.9` — a reason to move |
| Floor | 54 | Last SDK where the legacy architecture can be on — the bridge in [`new-architecture`](references/new-architecture.md) |
| Below 54 | — | One SDK at a time up to 54, then the bridge, then onward |

## When to use

- The user names a target SDK, or the audit reports A1 (below the floor), A6, A7
- An old project must reach the New Architecture ([`new-architecture`](references/new-architecture.md))
- A bare React Native app should adopt Expo modules, the CLI, prebuild ([`bare-to-expo`](references/bare-to-expo.md))
- React Native must live inside an existing iOS / Android app ([`embed-in-native-app`](references/embed-in-native-app.md))
- A post-upgrade break: a dead gesture, a missing native module, `expo-doctor` complaints, a hand-edited `ios/` file wiped by `prebuild --clean`

## When NOT to use

- New app → [`project-setup`](../project-setup/SKILL.md)
- A library major with no SDK change (FlashList, MMKV, RNTL) → the owning skill names the change; run it here only as its own change
- Patch / minor bumps inside an SDK — dependency hygiene, `expo install --fix`
- Feature work, a bug fix → the agent's FIX / EXTEND modes; they never up-level a lane
- Native-side Swift / Kotlin modernization → the `mobile-ios` / `mobile-android` plugins

## Inputs needed

1. **Current SDK, RN, React** (`package.json`), Expo Router or bare React Navigation, `ios/` and `android/` tracked or ignored
2. **Target** — a single SDK, the New Architecture, CNG, or an embed; one per run
3. **Which libraries pin the lane** — Reanimated, NativeWind, FlashList, MMKV, Gesture Handler, any `@react-navigation/*` (never beside Expo Router, SDK 56+)
4. **EAS profiles and OTA** — an OTA update targets a runtime version; a lane move changes it

## The gate — before any version moves

1. **Clean tree, green baseline.** Record `npx tsc --noEmit`, `npx expo lint`, `npx jest` and `npx expo-doctor` results *before* touching a version, or no later failure is attributable. Outside a `Gate: none` plan task, run them; inside one, say they were not run.
2. **One change, one commit series.** One SDK, one architecture switch, one workflow move. Work in the checkout you are given — never create a branch or worktree.
3. **Inventory the blast radius first** — count the removed APIs and the pinned libraries; that number is the real size of the job.
4. **Read the release notes of the SDK you are crossing** (`expo.dev/changelog/sdk-<n>`) — the codemods and the breaking list live there, not in this file.
5. **Never combine** an SDK upgrade with the New Architecture switch, a router change or a styling-library swap: when something breaks you will not know which move did it.

## The four runs

| Run | Reference | One-line shape |
|---|---|---|
| SDK upgrade | [`sdk-upgrade`](references/sdk-upgrade.md) | Install the next SDK's `expo`, `expo install --fix`, `expo-doctor`, codemods, prebuild if CNG, dev build, repeat |
| Legacy → New Architecture | [`new-architecture`](references/new-architecture.md) | On SDK 54: audit dependencies, flip it on, dev build, fix; only then SDK 55 |
| Bare → Expo | [`bare-to-expo`](references/bare-to-expo.md) | `npx install-expo-modules`, switch scripts to Expo CLI, then adopt prebuild and move native edits into config plugins |
| Embed in a native app | [`embed-in-native-app`](references/embed-in-native-app.md) | Isolated (`expo-brownfield` AAR / XCFramework) or integrated; Callstack's library for a prebuilt artifact |

## Cross-run rules

- **Never up-level as a side effect.** A feature task that finds an old SDK reports it and offers this skill — it does not start it.
- **Install natives with `npx expo install <pkg>`**, never `add`, so the version matches the SDK.
- **A hand edit in a generated `ios/` or `android/` is the defect class.** Under CNG it is erased by the next `prebuild --clean`; the fix is a config plugin ([`native-modules`](../native-modules/SKILL.md)), applied to every instance found.
- **Rebuild the development build after any native dependency change** — a JS reload cannot load new native code.
- **An OTA update crosses a lane only through a new build.** Bump the runtime version with the SDK; never publish an update built on SDK *n+1* to a binary built on *n* ([`mobile-shared-release`](../../../_shared/release/SKILL.md)).
- **Pin what the lane pins.** Reanimated 4 needs `react-native-worklets` and the New Architecture; NativeWind stays on Reanimated 3 until its own release says otherwise; Gesture Handler is 2.32 on SDK 57 and 3.x on SDK 58 — different APIs ([`animation`](../animation/SKILL.md)).
- **No `@react-navigation/*` imports in an Expo Router app** — SDK 56 forked the core; the codemod is `npx expo-codemod sdk-56-expo-router-react-navigation-replace`.

## Verification (every run, non-negotiable)

1. `npx expo-doctor` reports clean for the new SDK; `npx expo install --check` reports nothing outdated.
2. Type-check, lint and the Jest suite match or beat the baseline.
3. A fresh development build launches on an iOS simulator **and** an Android emulator; the primary flow runs end to end; `xcrun simctl io booted screenshot <file>` / `adb exec-out screencap -p > <file>` for the record.
4. A release build (EAS profile `production` or `preview`) completes — Hermes and the minifier break what a debug build hides.
5. The OTA / runtime-version policy is restated for the new lane.
6. Re-run the conformance audit's section A ([`standards-audit`](../standards-audit/SKILL.md)).

## Anti-patterns

- **Jumping several SDKs at once** because the codemods "handle it" — each SDK's breaking list is separate; do one at a time.
- **Upgrading and enabling the New Architecture together.**
- **`--legacy-peer-deps` / `--force` to silence a peer conflict** — the conflict is the migration's work list.
- **Deleting `ios/` and `android/` on a bare project** to "regenerate" — native edits are lost, not migrated.
- **Running `prebuild` inside a hand-maintained native host app** ([`embed-in-native-app`](references/embed-in-native-app.md)).
- **Copying hook or API names from memory** for a package whose major changed — read the installed types.
- **Bundling a feature into the upgrade commit.**

## Handoffs

- Concepts and the web-React map → [`basics`](../basics/SKILL.md)
- Config plugins, Expo Modules → [`native-modules`](../native-modules/SKILL.md)
- Project scaffold and config → [`project-setup`](../project-setup/SKILL.md)
- Signing, runtime versions, OTA, EAS → `mobile-shared-release`
- Review the migration diff → [`code-review`](../code-review/SKILL.md)
- Conformance after the move → [`standards-audit`](../standards-audit/SKILL.md)
- Dev-side tests that lock the move → [`component-testing`](../component-testing/SKILL.md)
- Device journeys after an upgrade → peer `qa-mobile-typescript`
