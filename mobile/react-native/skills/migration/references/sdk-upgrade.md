# Expo SDK upgrade — one SDK per change

Sources: docs.expo.dev/workflow/upgrading-expo-sdk-walkthrough · expo.dev/changelog/sdk-<n> · expo.dev/blog/upgrading-to-sdk-<n>. Re-read the walkthrough before a run: commands and codemod names move with SDKs.

## The loop (repeat per SDK — 52 → 53 → 54 → … → 57)

1. **Baseline.** Clean tree; record type-check, lint, Jest and `npx expo-doctor` (SKILL gate).
2. **Read** `expo.dev/changelog/sdk-<next>` and the "upgrading to SDK <next>" post: breaking changes, removed packages, minimum Node / Xcode.
3. **Install the next SDK's `expo`** — a specific major, not `latest`, or you will skip one:

```bash
npx expo install expo@^55.0.0
npx expo install --fix
npx expo-doctor
```

`--fix` realigns every Expo-managed dependency to the SDK's bundled versions. Resolve what `expo-doctor` reports before going on; it also checks the React Native Directory for libraries unmaintained or untested on the New Architecture.
4. **Apply the SDK's codemods and config changes** from its release notes (for the Expo Router fork on 56: `npx expo-codemod sdk-56-expo-router-react-navigation-replace`; for RNTL 14 async APIs: `rntl-v14-async-functions`).
5. **Native layer.**
   - CNG (`ios/` and `android/` ignored): `npx expo prebuild --clean` — it cleans by default since SDK 57 — then a new development build.
   - Bare (`[bare]`): follow the SDK's native diff (React Native Upgrade Helper for the RN version) by hand; every native edit you keep becomes a candidate config plugin.
6. **Rebuild** the development build (`npx expo run:ios`, `npx expo run:android`, or `eas build --profile development`).
7. **Verify** per the SKILL; commit; **stop**. The next SDK is a new run.

## Lane-specific work at each crossing

| Crossing | Check |
|---|---|
| → 54 | Last legacy SDK: do [`new-architecture`](new-architecture.md) here, not later; Reanimated 4 / FlashList 2 only run on the New Architecture |
| 54 → 55 | `newArchEnabled` is gone from `app.json` (New Architecture only); legacy-only libraries block the move; `expo-brownfield` arrives |
| 55 → 56 | Hermes V1 default (RN 0.84); Expo Router forks the React Navigation core — remove `@react-navigation/*` imports; Expo UI stable |
| 56 → 57 | Default template changes do **not** rewrite your project — leave `src/app`, alias and Compiler as the project has them; `prebuild` cleans by default; RN 0.86; `expo@57.0.9`+ fixes the Reanimated memory regression |
| 57 → 58 `[SDK58]` | Only after stable: AGP 9, scene lifecycle default (iOS 27), native tabs at `expo-router/native-tabs`, Gesture Handler 3 (API change), Reanimated 4.7 + worklets 0.13, Expo Router core rework |

Intermediate SDKs (below 54) are not authored for; their notes are read, their breaking lists applied, and the project continues to the bridge.

## Packages that pin the lane

| Package | Rule |
|---|---|
| `react-native-reanimated` | 4.x needs `react-native-worklets` (Babel plugin moved) and the New Architecture; NativeWind projects stay on 3 until NativeWind supports 4 |
| `react-native-gesture-handler` | 2.32 bundled on SDK 57, 3.x on 58 — the `Gesture` API differs; migrate gestures in their own commit |
| `@shopify/flash-list` | 2.x drops `estimatedItemSize` and needs the New Architecture |
| `react-native-mmkv` | 4 is `createMMKV()` on Nitro; a 3 → 4 move is its own change |
| `@testing-library/react-native` | 14 makes `render` / `fireEvent` / `act` / `renderHook` async |
| `eslint-config-expo` | `flat` config on current SDKs |
| `@react-navigation/*` | Remove from an Expo Router app on 56+; bare React Navigation stays 7.x |

## When it breaks

- **A native module is missing at runtime** → you reloaded JS onto an old binary; rebuild.
- **Duplicate native versions** → `npx expo-doctor`, then `npx expo install --fix`, then delete the lockfile entry for the offender and reinstall — never hand-pin around it.
- **Metro cannot resolve a package** → a package moved; read the changelog before editing `metro.config.js`.
- **Babel / worklet errors** → the Reanimated 4 + `react-native-worklets` plugin order.
- **A green dev build, a red release build** → minifier / Hermes; reproduce with the `preview` profile.
