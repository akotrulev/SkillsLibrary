# Legacy → New Architecture (through the SDK 54 bridge)

Sources: docs.expo.dev/guides/new-architecture · expo.dev/blog/expo-sdk-upgrade-guide (SDK 54) · reactnative.dev/blog (0.82). New Architecture is the only architecture from RN 0.82 / SDK 55; SDK 54 is the last SDK where the legacy one can still be on.

## Rule

**Do not upgrade the SDK and switch the architecture in the same change.** Stand on SDK 54, turn it on, prove it, commit — then run [`sdk-upgrade`](sdk-upgrade.md) to 55 and onward. A project below 54 reaches 54 one SDK at a time first.

## Steps (on SDK 54)

1. **Audit dependencies.** `npx expo-doctor` lists libraries with no New Architecture support. For each native library not in the Expo SDK, check React Native Directory and its release notes. Interop covers many legacy modules, but not all.

```bash
npx expo-doctor
rg -n "newArchEnabled|RCT_NEW_ARCH_ENABLED|jsEngine" app.json app.config.* eas.json ios android
```

2. **Replace what blocks.** A library without support is replaced, or pinned with a recorded reason, before the switch — never left to crash on launch. Known pairings: Reanimated 4 + `react-native-worklets`; FlashList 2; MMKV 4; Gesture Handler by SDK.
3. **Turn it on.** On SDK 54 set `"newArchEnabled": true` in `app.json` / `app.config.ts`. Bare `[bare]`: Android `newArchEnabled=true` in `gradle.properties`, iOS `RCT_NEW_ARCH_ENABLED=1 pod install`.
4. **Fresh build.** `npx expo prebuild --clean` (CNG) and a new development build for both platforms. The JS bundle alone proves nothing.
5. **Walk the app.** Native modules, gestures, animations, lists, keyboard handling, deep links, push registration. Fix what is red; recheck the audit rows A2, J (native code) and N (performance).
6. **Swap deprecated bridge-era code** that was only tolerated by the interop layer: custom `NativeModules` access, `findNodeHandle`, `UIManager` command dispatch → Expo Modules API or the library's current API ([`native-modules`](../../native-modules/SKILL.md)).
7. **Commit; stop.** The SDK upgrade is the next run.

## Done when

- `npx expo-doctor` is clean for the lane, no `newArchEnabled: false` / `RCT_NEW_ARCH_ENABLED=0` remains
- Both platforms launch a fresh development build and the primary flows pass
- Each library kept on interop is listed in the report with the reason

## Traps

- **Reanimated 4 fails at launch** without `react-native-worklets` and its Babel plugin.
- **A release build crashes where debug does not** — a native module that loaded through lenient interop in debug; reproduce on the `preview` profile.
- **Expo Go hides it.** Judge the switch only on a development build.
- **Third-party UI kits** pinned to the old renderer — check the library's issue tracker before blaming your code.
