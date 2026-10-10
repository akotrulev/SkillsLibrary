# Embedding React Native in an existing native app

Sources: docs.expo.dev/brownfield/overview · docs.expo.dev/brownfield/isolated-approach · oss.callstack.com/react-native-brownfield · reactnative.dev/docs/integration-with-existing-apps. `expo-brownfield` is **alpha** (arrived with SDK 55): pin the version, read its changelog before each run, and say so in the report.

## Choose the approach first

| Approach | Shape | Pick when | Cost |
|---|---|---|---|
| **Isolated** (`expo-brownfield`) | RN project builds an **XCFramework** (iOS) and **AAR** (Android); the native app consumes the artifacts | Native and RN teams are separate; native developers must not need Node or RN tooling | Artifact versioning and publishing; two repos or a monorepo with a producer |
| **Callstack** (`@callstack/react-native-brownfield`) | Same artifact idea, with `ReactNativeView` for SwiftUI, a Gradle plugin for the fat AAR, Brownie for shared state, packaging with `rnef package:ios` / `rnef package:aar` | Works on legacy and New Architecture; richer native↔JS state sharing | A third-party library to track (5.x) |
| **Integrated** | RN sources added to the host app's Gradle / CocoaPods build | One team owns both sides | The host's build now needs Node and RN tooling |
| RN core integration | `react-native` pods / Gradle by hand, no Expo | Expo is out of the question | You own every native step; `[bare]` |

Default for a mixed team: **isolated with `expo-brownfield`**; Callstack when shared state or SwiftUI embedding is the need. Say which was chosen and why.

## Isolated run (`expo-brownfield`)

1. **Producer project.** A normal Expo app (SDK 57, CNG) that owns the RN screens.

```bash
npx expo install expo-brownfield
```

2. **Config plugin** in `app.json`: iOS target name and bundle identifier; Android library name, group, package, version. The artifact coordinate comes from these (for example `com.example:brownfield:1.0.0`).
3. **Build artifacts:** `npx expo-brownfield build:ios` → XCFrameworks (Hermes and the app) under `artifacts/`; `npx expo-brownfield build:android` → an AAR published to the local Maven repo (`~/.m2`) or a remote repository.
4. **Consume in the host:** add the XCFrameworks / the Maven dependency; initialise and present the RN view from a native screen; pass initial props and handle close / navigation back to native explicitly.
5. **Version the contract** — props in, events out — as a typed schema both sides read; artifact versions follow it.
6. **Verify** on a simulator and an emulator through the **host** app, not the producer.

## Rules

- **Never run `prebuild` in the hand-maintained host.** The producer may use CNG; its generated `ios/` and `android/` stay separate from the host's projects.
- **One RN root, one Hermes.** Do not ship two RN runtimes in one app.
- **Push, deep links, auth:** the host owns the OS entry points and forwards validated payloads to RN ([`notifications-and-links`](../../notifications-and-links/SKILL.md)); tokens stay in the host's Keychain / Keystore.
- **Startup cost:** RN initialisation is lazy where the product allows; measure cold start before and after ([`performance`](../../performance/SKILL.md)).
- **Back and lifecycle** cross the boundary explicitly — a hardware back press or a swipe-back must reach the right owner.
- **Release:** the artifact is built by CI from the producer; the host pins an exact version ([`mobile-shared-release`](../../../../_shared/release/SKILL.md)).

## Done when

- The host app presents an RN screen from a pinned artifact on both platforms
- The prop / event contract is written and typed
- Cold-start and app-size deltas are recorded
- The alpha status of `expo-brownfield` (or the Callstack version) is stated in the report
