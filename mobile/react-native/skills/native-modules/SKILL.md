---
name: native-modules
description: Use when an Expo SDK 57 app needs native code — the ladder (Expo SDK module, maintained community module, Expo Modules API in Swift / Kotlin, Nitro / TurboModule in bare), config plugins for every native change, Expo UI, DOM components. Triggers "is there a native module for", "write a Swift module", "edit Info.plist", "config plugin". Do NOT use for camera, location or push features (`mobile-react-native:device-features`, `-notifications-and-links`) or project setup.
---

# React Native — Native Modules

Owns **going native**: deciding whether to, which rung of the ladder, how an Expo module and a config plugin are written, and how native UI is reached. **The Swift and Kotlin written here follow the native standards** — load [`mobile-ios:concepts`](../../../ios/skills/basics/SKILL.md) for every `.swift` file and [`mobile-android:concepts`](../../../android/skills/basics/SKILL.md) for every `.kt` file before writing them; both read without an app project.

## Version lane

| Concern | Primary (SDK 57 · RN 0.86) | Notes |
|---|---|---|
| Native change | **config plugin** | `expo prebuild` **cleans by default since SDK 57** — a hand edit to `ios/` or `android/` is lost on the next prebuild |
| Expo Modules API | SDK-versioned (`expo-modules-core`) | Swift + Kotlin DSL; `create-expo-module` scaffolds |
| Expo UI | `@expo/ui` — SwiftUI + Jetpack Compose primitives, stable since SDK 56 | Hosts native trees inside RN |
| Nitro Modules | `react-native-nitro-modules` | Typed JSI, used by MMKV 4; for high-frequency or large-payload calls |
| TurboModules / Fabric | RN core, codegen | **Bare RN** (no Expo modules); New Architecture only |
| DOM components | `'use dom'` | Web UI in a WebView-backed component — see below |
| `[SDK58]` | Expo Router core reworked; scene lifecycle default (iOS 27) | Re-check a module's lifecycle hooks on upgrade |
| Floor SDK 54 | prebuild not yet clean-by-default | Same recipes; the rule "plugin, never hand edit" is unchanged |

Detect first: `ios/` and `android/` tracked in git (**bare**) or ignored (**CNG**); `expo` in `package.json`; `app.json` / `app.config.ts` `plugins`; `expo-dev-client`. A bare project without `expo` has the TurboModule rung and no config-plugin rung until `install-expo-modules` ([`migration`](../migration/SKILL.md)).

## When to use

- "Is there a library for…?", "can Expo do…?", "I need to call a native API"
- Writing or reviewing a local Expo module (Swift / Kotlin)
- Changing `Info.plist`, `AndroidManifest.xml`, entitlements, Gradle or Podfile properties
- Putting a SwiftUI or Compose control into the app (Expo UI)
- Reaching for a Nitro or TurboModule in a bare app

## When NOT to use

- Camera, photo picker, location, biometrics, haptics → [`device-features`](../device-features/SKILL.md)
- Push and links → [`notifications-and-links`](../notifications-and-links/SKILL.md)
- Scaffold, EAS, `app.config.ts` basics → [`project-setup`](../project-setup/SKILL.md)
- A UI kit choice → [`component-library`](../component-library/SKILL.md)
- Upgrading SDK, bare → Expo → [`migration`](../migration/SKILL.md)
- A fully native app → `mobile-ios` / `mobile-android`
- Pinning, RASP libraries, manifest hardening → [`mobile-<stack>:security`](../../../_shared/security/SKILL.md)

## The ladder — climb only as far as needed

1. **An Expo SDK module** (`expo-camera`, `expo-secure-store`, `expo-sensors`, …) — versioned with the SDK, config plugin included. Check `docs.expo.dev/versions/latest` first.
2. **A maintained community module** — passes the check below; installed with `npx expo install`, its config plugin added to `plugins`.
3. **A local Expo module** (Expo Modules API) — Swift + Kotlin you write, in `modules/<name>`, autolinked, no `ios/` edit.
4. **A Nitro module** — when calls are hot (per frame, audio, large buffers) or payloads are big; typed C++/Swift/Kotlin bridge.
5. **A TurboModule / Fabric component** — **bare RN only**, codegen specs; Expo apps use rung 3 or 4 instead.

**Maintenance check before rung 2** (also `npx expo-doctor`, which consults React Native Directory): a release inside 12 months; New Architecture supported; supports the project's Expo SDK and RN; a config plugin or a documented one; no open crash issues on the iOS / Android of the day; licence acceptable. An archived or unmaintained library is a **major** finding with rung 3 as the fix — and a library that needs a native edit with no config plugin is a candidate for rung 3.

**Do not go native when JS does it.** A single REST call, a date format, a hash with `expo-crypto`, a file read with `expo-file-system` are JS. Native code costs two languages, two test suites and every SDK upgrade.

## Config plugins — every native change

A **config plugin** is a function in `app.config.ts` (or a package) that edits the generated project at prebuild. It is the only sanctioned way to change native files, because prebuild regenerates them.

```ts
import { type ConfigPlugin, withInfoPlist, withAndroidManifest } from 'expo/config-plugins';

const withScannerPermissions: ConfigPlugin<{ reason: string }> = (config, { reason }) => {
  const withIos = withInfoPlist(config, (mod) => {
    mod.modResults.NSCameraUsageDescription = reason;
    return mod;
  });
  return withAndroidManifest(withIos, (mod) => {
    const manifest = mod.modResults.manifest;
    manifest['uses-permission'] = [
      ...(manifest['uses-permission'] ?? []),
      { $: { 'android:name': 'android.permission.CAMERA' } },
    ];
    return mod;
  });
};

export default withScannerPermissions;
```

- **Never hand-edit `ios/` or `android/`** in a CNG project — `prebuild --clean` is the default since SDK 57 and discards it. If a native edit is already there and untracked, move it into a plugin **now**, then re-run prebuild to prove the plugin reproduces it.
- Prefer the declarative surface first: `ios.infoPlist`, `ios.entitlements`, `android.permissions`, `android.blockedPermissions`, `expo-build-properties` for Gradle / Podfile properties, `expo-font`, `expo-splash-screen`. Write a plugin only where none fits.
- **Compose with the `with*` mods** (`withInfoPlist`, `withEntitlementsPlist`, `withAndroidManifest`, `withGradleProperties`, `withAppBuildGradle`, `withDangerousMod` as the last resort). Mods are idempotent: running twice must not duplicate.
- **A plugin is audited like a hand edit**: it must not set `android:exported="true"` on a component without a reason, `usesCleartextTraffic`, `NSAllowsArbitraryLoads`, `allowBackup`; read the **generated** manifest and plist once after prebuild ([`mobile-<stack>:security`](../../../_shared/security/references/react-native.md) §6).
- **Permission strings and declarations** come from [`mobile-<stack>:store-compliance`](../../../_shared/store-compliance/SKILL.md); each declared permission has a use in code ([`device-features`](../device-features/SKILL.md)).
- Test a plugin: a Jest test that runs the plugin against a fixture config and asserts the resulting `Info.plist` / manifest object — a pure function, no device.
- A native change needs a **new development build or EAS build**; it never ships through an OTA update ([`mobile-<stack>:release`](../../../_shared/release/SKILL.md)).

## Local Expo module

```text
modules/haptic-pattern/
  expo-module.config.json
  index.ts
  src/HapticPatternModule.ts
  ios/HapticPatternModule.swift
  android/src/main/java/expo/modules/hapticpattern/HapticPatternModule.kt
```

Scaffold: `npx create-expo-module@latest --local`. The module is autolinked from `modules/`; `expo-module.config.json` lists the platforms and module classes. Detail, with Swift and Kotlin definitions, events, views and shared objects, is in [`references/expo-modules-api.md`](references/expo-modules-api.md).

Rules for a module:

- **A narrow, typed surface** — a few `Function` / `AsyncFunction` entries with Records for structured arguments; the TypeScript wrapper in `index.ts` is the only public API.
- **Async by default** — `AsyncFunction`; a synchronous `Function` only for a trivial, instant read. Native work never blocks the JS thread or the UI thread; heavy work moves to a background queue (Swift) or an injected dispatcher (Kotlin).
- **Errors are typed** — throw an `Exception` subclass with a code; the JS wrapper maps it to the app's error type. No silent catch.
- **Lifecycle** — register `OnCreate` / `OnDestroy` / `OnStartObserving`; a module that holds a listener or a hardware handle releases it; events stop when no JS listener remains.
- **Swift follows `mobile-ios:concepts`** (Swift 6 isolation, no force unwrap, `os.Logger`, narrowest access); **Kotlin follows `mobile-android:concepts`** (no `!!`, structured concurrency, injected dispatchers). Read the matching basics before the first line.
- **Untrusted input** — arguments from JS are validated natively before they reach a file path, a URL or an Intent.
- **Tests** — the TypeScript wrapper with Jest and a fake native module; Swift / Kotlin logic that is not API glue is pulled into a plain class and tested with `mobile-ios:unit-testing` / `mobile-android:unit-testing` patterns. Device behaviour is `qa-mobile-typescript`'s.
- A module that fails to link or load **crashes at startup** — wrap optional modules with `requireOptionalNativeModule` and degrade, and record the dependency in [`error-handling`](../error-handling/SKILL.md)'s third-party-failure rule.

## Expo UI — native SwiftUI and Compose primitives

`@expo/ui` renders SwiftUI (`@expo/ui/swift-ui`) and Jetpack Compose (`@expo/ui/jetpack-compose`) controls inside RN. Every native tree sits inside a **`<Host>`**; flex props do not apply inside it; platform files (`Thing.ios.tsx`, `Thing.android.tsx`) keep the imports apart. The component-level guidance and `references/expo-ui.md` are [`component-library`](../component-library/SKILL.md)'s; this skill covers when Expo UI is **not enough** (a control Expo UI lacks → rung 3, a local module with a native view).

## DOM components

A file with `'use dom'` at the top renders **web** React inside a WebView on native and as plain DOM on web. Use it for a rich-text editor, a chart library or a code-heavy widget that exists only for the web. Props cross the boundary as serialisable data; functions are async actions. It is a WebView — apply the WebView rules in [`mobile-<stack>:security`](../../../_shared/security/references/react-native.md) §4 (origin allow-list, no untrusted URL, no bridge `eval`) and the cost warning: not for list rows, not for a primary navigation surface.

## Bare React Native — Nitro and TurboModules

- **Nitro** (`react-native-nitro-modules`): author a TypeScript spec, `npx nitrogen` generates the native interfaces, implement in Swift / Kotlin (or C++), register in `nitro.json`. Nitro is also usable in an Expo app through a development build.
- **TurboModule / Fabric** (bare, New Architecture only): a typed `Native<Name>.ts` spec, codegen entries in `package.json`, native implementation in Obj-C++/Swift and Kotlin. Hand-edited `ios/` / `android/` are legitimate **in bare** — they are source there.
- In a bare app with Expo modules installed (`install-expo-modules`), prefer rung 3 over a TurboModule: less boilerplate, same autolinking.
- Choosing between them: Expo Modules API for app-level features; Nitro for performance-critical, library-grade modules; TurboModule where a library must support non-Expo consumers.

## Rules

- Climb the ladder one rung at a time; justify each step down in the PR.
- Every native change is a config plugin or a local module; never a hand edit to generated `ios/` / `android/` in a CNG project.
- A community module passes the maintenance check and `expo-doctor`.
- A plugin is idempotent, tested as a pure function, and its generated output is read once.
- Module surfaces are narrow, typed, async; Swift and Kotlin follow the two `basics`.
- Native changes ship by build, never OTA; a module that can fail to load degrades.
- JS-callable arguments are validated natively; no secret logged natively.

## What NOT to do

- No `ios/` or `android/` edit in a project whose native folders are generated.
- No native module for what an Expo SDK module or plain JS already does.
- No unmaintained or New-Architecture-incompatible library; no library without a config plugin and no plan.
- No synchronous native call that waits on I/O; no work on the main thread.
- No `AndroidManifest` / `Info.plist` change that skips the permission and compliance rules.
- No TurboModule in an Expo-managed app where an Expo module fits.
- No DOM component as a list row or the main navigation chrome.
- No Swift or Kotlin written without loading the matching `basics`.
- No `withDangerousMod` where a typed mod exists.

## Generation steps

1. Detect CNG vs bare, SDK, `plugins`, `expo-dev-client`.
2. State the capability and walk the ladder; record each rung rejected and why.
3. Config-only change → declarative field, else a typed plugin with a Jest fixture test.
4. A local module → scaffold, load the two `basics`, write TS wrapper + Swift + Kotlin, typed errors, lifecycle.
5. Native UI → Expo UI primitive inside `Host`; a missing control → module with a native view.
6. Prebuild once (outside a `Gate: none` task), read the generated manifest and plist, then build a development client.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- `npx expo prebuild --clean` reproduces every native setting from plugins alone; `git status` on `ios/` / `android/` is empty in CNG.
- `npx expo-doctor` clean; development build launches; the module is callable on iOS **and** Android.
- The generated `AndroidManifest.xml` and `Info.plist` hold no unreviewed `exported`, cleartext or ATS flag.
- Jest tests for the plugin and the TypeScript wrapper; native logic tests per the native unit-testing skills.

## Handoffs

- Features built on SDK modules → [`device-features`](../device-features/SKILL.md), [`notifications-and-links`](../notifications-and-links/SKILL.md)
- Kit and Expo UI components → [`component-library`](../component-library/SKILL.md) · scaffold, EAS → [`project-setup`](../project-setup/SKILL.md)
- Bare ↔ Expo, SDK upgrades → [`migration`](../migration/SKILL.md)
- Swift standard → [`mobile-ios:concepts`](../../../ios/skills/basics/SKILL.md) · Kotlin standard → [`mobile-android:concepts`](../../../android/skills/basics/SKILL.md)
- Manifest, pinning, WebView → [`mobile-<stack>:security`](../../../_shared/security/SKILL.md) · permissions, privacy manifest → [`mobile-<stack>:store-compliance`](../../../_shared/store-compliance/SKILL.md)
