---
name: mobile-react-native-device-features
description: Use when an Expo SDK 57 app must reach hardware or OS services — expo-camera, expo-image-picker, expo-location, expo-local-authentication, haptics, sharing, file system, expo-background-task — and ask for the permission first. Triggers "scan a QR code", "pick a photo", "use the user's location", "Face ID login", "permission denied dead end". Do NOT use for push or links (`-notifications-and-links`), custom native code (`-native-modules`), or secret storage (`-offline-and-storage`).
---

# React Native — Device Features and Permissions

Owns the code that touches the camera, library, location, biometrics, haptics, sharing, files and background work — and the **permission lifecycle** around each. Two rules are hard, not advice: **a permission is asked in context after a pre-prompt**, and **the denied path is a working screen**. A feature whose only denied behaviour is a blank view or an endless re-prompt is a **major** audit finding (J14, J15).

## Version lane

| Concern | Primary (SDK 57) | Notes |
|---|---|---|
| Modules | `expo-camera`, `expo-image-picker`, `expo-location`, `expo-local-authentication`, `expo-haptics`, `expo-sharing`, `expo-file-system`, `expo-background-task` + `expo-task-manager` | Install with `npx expo install`; versions are SDK-pinned |
| Permission strings | Set through each module's **config plugin** (`cameraPermission`, `photosPermission`, `locationWhenInUsePermission`, `faceIDPermission`) | Authored once in `app.json`; hand edits to `Info.plist` / the manifest are lost on `prebuild --clean` ([`native-modules`](../native-modules/SKILL.md)) |
| Expo Go | Face ID is not supported on iOS in Expo Go | Use a development build for anything permission-bearing |
| `[SDK58]` | No permission-API change known | Re-read the module page when 58 ships stable |
| Floor SDK 54 | Same hook shapes (`use*Permissions`) | Same recipes |

Detect the installed SDK from `expo` in `package.json`; never add a module the project's SDK does not pin.

## When to use

- Capturing, scanning, picking or saving media
- Reading the device position, once or while the screen is open
- Gating a screen or a sensitive action behind Face ID / Touch ID / fingerprint
- Haptic feedback, the system share sheet, reading and writing app files
- Periodic work while the app is not foregrounded

## When NOT to use

- Push tokens, notification permission, universal links → [`notifications-and-links`](../notifications-and-links/SKILL.md)
- A capability no SDK or community module covers → [`native-modules`](../native-modules/SKILL.md)
- Tokens, credentials, encrypted records → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- The store-side declaration rules (purpose strings, Play declarations) → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)

## The permission lifecycle (hard rules)

Every permission-bearing feature has **four states**, and each is a screen, not an `if`:

| State | What the user sees |
|---|---|
| **Undetermined** | A **pre-prompt**: one screen or sheet saying what the feature does with the capability and why now, with "Continue" and "Not now". The system dialog opens only from "Continue". |
| **Granted** | The feature. |
| **Denied, can ask again** | The same pre-prompt, with the reason it is needed; "Continue" re-requests. |
| **Denied, `canAskAgain === false`** | A working screen: what is unavailable, **an alternative path** (enter the code by hand, pick from the library, type the address), and an "Open Settings" button calling `Linking.openSettings()`. |

```tsx
import { useCameraPermissions } from 'expo-camera';
import { Linking } from 'react-native';

export function ScannerGate({ children }: { children: React.ReactNode }) {
  const [permission, requestPermission] = useCameraPermissions();

  if (permission === null) return <ScannerLoading testID="Scanner.Loading" />;
  if (permission.granted) return children;

  if (permission.canAskAgain) {
    return (
      <PermissionPrimer
        testID="Scanner.Primer"
        reason="We scan the code on your receipt to add it to the claim."
        onContinue={requestPermission}
        onDecline={goToManualEntry}
      />
    );
  }

  return (
    <PermissionDenied
      testID="Scanner.Denied"
      onOpenSettings={Linking.openSettings}
      onUseAlternative={goToManualEntry}
    />
  );
}
```

- **Never call a `request*Async` on mount, in a root layout, or on a screen the user did not choose.** The trigger is the user's tap on the feature.
- **iOS shows the system dialog once.** After a denial `canAskAgain` is `false` and a second `request` does nothing — only Settings changes it. Do not loop on `request`.
- **Android re-asks until the user chooses "Don't ask again"** (or denies twice on recent versions); treat `canAskAgain` as the only truth, never a counter you keep.
- **Re-read the status on foreground.** The user may have changed it in Settings: refresh on `AppState` `active` (the `use*Permissions` hooks' `get` function), and never cache "denied" across sessions.
- **Ask for the least.** Foreground before background; coarse before precise; the picker before library access; a one-shot capture before continuous capture.
- **The purpose string is specific** ("Used to scan receipts for expense claims"); "Needs camera access" is an App Review rejection. Authored in the config plugin, in every shipped language ([`languages`](../languages/SKILL.md)).
- **Declare only what you request.** An unused `NSLocationAlwaysAndWhenInUseUsageDescription` or `ACCESS_BACKGROUND_LOCATION` is a store finding ([`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)).

## Camera and scanning — `expo-camera`

- `useCameraPermissions()` → the gate above. `CameraView` renders only inside the granted branch.
- `CameraView` with `onBarcodeScanned` and `barcodeScannerSettings={{ barcodeTypes: ['qr'] }}` — list only the types you parse. Debounce: the callback fires per frame; set a ref or state on the first hit and ignore the rest.
- A scanned value is **untrusted input**: validate it with a schema before it routes, opens a URL, or reaches a request ([`mobile-shared-security`](../../../_shared/security/SKILL.md)).
- Unmount releases the camera; do not keep a `CameraView` mounted under a hidden tab. Mute the preview (`active={false}`) while a modal covers it.
- `cameraPermission: false` in the plugin blocks the Android `CAMERA` permission when a dependency adds it unasked.

## Photos and files — `expo-image-picker`

- **Launching the library needs no permission request** (the system picker runs out of process); do not ask for library access to pick. The exception is iOS video selection with the defaults (`allowsEditing: false`, `videoExportPreset: 'Passthrough'`), which needs media-library access to read the original file — request it first, or set a `videoExportPreset` that does not.
- `requestCameraPermissionsAsync` before `launchCameraAsync`; the camera always needs consent.
- `selectionLimit` with `allowsMultipleSelection: true`; `0` means the system maximum — set a number you can upload.
- Read `result.canceled` before `result.assets`; a cancel is not an error.
- Downscale and re-encode **before** upload (`quality`, or an image manipulator); a 12 MP original on a cell link is a timeout. Strip location EXIF you do not need.
- Never request `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` for picking — Play blocks the declaration unless the picker cannot serve core functionality ([`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)).
- `photosPermission` sets `NSPhotoLibraryUsageDescription`; it is needed only if you read or save to the library.

## Location — `expo-location`

| Need | API | Permission |
|---|---|---|
| One fix, e.g. "find stores near me" | `getCurrentPositionAsync({ accuracy })` | `useForegroundPermissions()` |
| Follow while the screen is open | `watchPositionAsync(options, callback)` → `subscription.remove()` on unmount | foreground |
| While backgrounded | `startLocationUpdatesAsync` + a task | foreground **first**, then `requestBackgroundPermissionsAsync` — a foreground-service type and a Play declaration |

- Read `ios.accuracy` (`'full'` / `'reduced'`) and `android.accuracy` (`'fine'` / `'coarse'`): **approximate location is a valid grant** — the feature must still work, or say so.
- On Android 11+ `requestBackgroundPermissionsAsync` opens the Settings page, so explain before it. On iOS an "Allow Once" grant returns denied for a later background request in the same session.
- `locationWhenInUsePermission` sets `NSLocationWhenInUseUsageDescription`; `isAndroidBackgroundLocationEnabled` stays `false` unless background is the product.
- Always remove the watch subscription in the effect cleanup, and stop updates when the screen goes — battery and the "excessive wake locks" Android vital.
- Play's 2027-01-27 location policy recommends the **location button** as the minimum scope for precise location — a one-shot, in-context request is the compliant shape.

## Biometrics — `expo-local-authentication`

- Check `hasHardwareAsync()` **and** `isEnrolledAsync()` before offering the control; neither → hide it and keep the password path.
- `authenticateAsync({ promptMessage })` returns `{ success: true }` or `{ success: false, error }`. Handle `user_cancel` silently; handle `lockout` with the fallback; never treat `success: false` as an exception to swallow.
- **Biometrics unlock a secret, they are not the secret.** The result of `authenticateAsync` is a boolean on the JS thread and can be faked on a rooted device; gate access to a Keychain / Keystore item with `requireAuthentication` in `expo-secure-store`, so the OS enforces it ([`offline-and-storage`](../offline-and-storage/SKILL.md), [`mobile-shared-security`](../../../_shared/security/SKILL.md)).
- `faceIDPermission` sets `NSFaceIDUsageDescription`; without it iOS falls back to the passcode silently.
- `disableDeviceFallback` and `fallbackLabel` are product decisions — default to the device passcode fallback so a user with a changed face is not locked out.

## Haptics, sharing, files

- `expo-haptics` for confirmation, selection and warning feedback — never a substitute for a visible state change, and never on every scroll tick. Respect the system setting; an unavailable engine is a no-op, not an error.
- `expo-sharing` `shareAsync(uri)` after `isAvailableAsync()`; share a file the app wrote, not a path from a link parameter.
- `expo-file-system`: write under the app's document or cache directory; files you can re-download go in cache. Never write a token, a PII export or a decrypted record to disk unprotected. Check free space before a large download and handle a full disk as a failed state ([`error-handling`](../error-handling/SKILL.md)).
- A filename or path built from server or link data is validated and normalised — no `..` segments.

## Background work — `expo-background-task`

| Fact | Detail |
|---|---|
| Engine | WorkManager (Android), `BGTaskScheduler` (iOS), JS run through `expo-task-manager` |
| Interval | `minimumInterval` in **minutes**, default 720, floor 15; the OS decides the actual time and iOS often ignores short values |
| Define | `TaskManager.defineTask(name, fn)` in **module scope** of a file loaded at startup; `registerTaskAsync` may run from a component |
| Result | return `BackgroundTaskResult.Success` or `.Failed` |
| Testing | `triggerTaskWorkerForTestingAsync()` in debug builds only; **unavailable on iOS simulators** |

- Background work is **best-effort and short**. It refreshes caches and flushes the mutation queue ([`offline-and-storage`](../offline-and-storage/SKILL.md)); it never carries a guarantee the product depends on — a foreground catch-up on `AppState` `active` is still required.
- `expo-background-fetch` is the older module; a project still on it migrates to `expo-background-task` (confirm the deprecation on docs.expo.dev for the project's SDK).
- Exact-time delivery is a notification concern; `SCHEDULE_EXACT_ALARM` is denied by default on Android 13+ ([`notifications-and-links`](../notifications-and-links/SKILL.md)).

## Procedure

1. Detect the SDK, the installed device modules and any existing permission helper; match it.
2. For each capability, list the plugin strings, the four states and the alternative path before writing code.
3. Write the gate (pre-prompt → granted → denied-askable → denied-settings) with a stable test id on each state.
4. Wire the feature; clean up subscriptions, cameras and watchers in the unmount path.
5. Validate any value that came from the device (a scan, a file name) before it is used.
6. Set the purpose strings in `app.json` plugins, in every shipped language; note them for [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md).

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Fresh install: the screen shows the pre-prompt first; the system dialog opens only after "Continue".
- Deny, then deny with "don't ask again": the denied screen offers the alternative and an Open Settings button that lands on the app's settings.
- Grant in Settings, return to the app: the feature unlocks without a restart.
- Choose approximate location: the feature works or says exactly what it cannot do.
- Leave the screen: the camera, watcher or listener is released.
- `rg` for `request.*Async` outside a handler or primer → none (J14).

## Handoffs

- Push permission, channels, tokens, deep links → [`notifications-and-links`](../notifications-and-links/SKILL.md)
- Config plugins for a native change, a custom module → [`native-modules`](../native-modules/SKILL.md)
- Secure storage, queued writes → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Purpose strings, Play declarations, data-safety → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Untrusted scan / file input, Keychain, pinning → [`mobile-shared-security`](../../../_shared/security/SKILL.md)
- Failure UI for a full disk or a failed capture → [`error-handling`](../error-handling/SKILL.md)
- Test ids on the primer and denied screens → [`test-ids`](../test-ids/SKILL.md)
- Permission dialogs in a device journey → `qa-mobile-typescript` (peer)
