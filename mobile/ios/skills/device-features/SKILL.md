---
name: device-features
description: Use when an iOS app touches device capabilities — permissions with Info.plist usage strings and a pre-prompt, PhotosPicker, AVFoundation camera, Core Location, LocalAuthentication, haptics, ShareLink, fileImporter. Triggers "ask for camera access", "pick a photo", "get the user's location", "Face ID to unlock", "denied path". Do NOT use for push and links (`mobile-ios:push-and-deep-links`), widgets and background work (`-system-integration`) or Keychain (`-offline-and-storage`).
---

# iOS — Device Features

Every capability follows one shape: **prefer the system picker that needs no permission → ask in context, after a pre-prompt, with a specific purpose string → treat denial as a working screen → release the resource when the screen goes.** Rules: CLAUDE.md § Mobile code rules (permissions, lifecycle) and [`mobile-<stack>:security`](../../../_shared/security/SKILL.md). Design facts: `design/ui-ux-pro-max` `--stack swiftui`.

## Version lane

| Capability | iOS 17+ (primary) | `[iOS16]` |
|---|---|---|
| Photos / videos | `PhotosPicker` (SwiftUI, **no permission**) | Same (iOS 16+) |
| Camera | `AVCaptureSession`; `AVCaptureDevice.requestAccess(for:)` | Same |
| Location | `CLLocationUpdate.liveUpdates()` (iOS 17), `CLServiceSession` (iOS 18) | `CLLocationManager` delegate |
| Biometrics | `LAContext` | Same |
| Haptics | `.sensoryFeedback(_:trigger:)` | `UIImpactFeedbackGenerator` / `UINotificationFeedbackGenerator` |
| Share | `ShareLink` (iOS 16+) | Same |
| Files | `.fileImporter` / `.fileExporter` | Same |
| Tracking | `ATTrackingManager` + `NSUserTrackingUsageDescription` — [`mobile-<stack>:store-compliance`](../../../_shared/store-compliance/SKILL.md) | Same |

An API newer than the deployment target needs `#available`; never raise the target for a feature ([`project-setup`](../project-setup/SKILL.md)).

## When to use

- Reading photos, taking a picture, scanning a code, picking a file
- Reading the user's location (once, or while the app is open)
- Gating a screen or an action behind Face ID / Touch ID / passcode
- Haptic feedback, sharing a link, image or file out of the app
- A permission prompt that never appears, or a denied state that dead-ends

## When NOT to use

- APNs, `UNUserNotificationCenter`, universal links → `mobile-ios:push-and-deep-links`
- Widgets, App Intents, Live Activities, background tasks → `mobile-ios:system-integration`
- Storing the secret that biometrics unlock → [`offline-and-storage`](../offline-and-storage/SKILL.md) (`references/keychain.md`)
- A custom native C / Objective-C bridge for React Native → `mobile-react-native:native-modules`
- Permission declarations as store policy → [`mobile-<stack>:store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Another stack → `mobile-react-native:device-features`, `mobile-android:device-features`

## The permission recipe

Every protected capability in order:

1. **Can a system UI do it without permission?** `PhotosPicker`, `fileImporter`, the document camera (`VNDocumentCameraViewController`), `ShareLink` read or write through the user's explicit choice — **no permission, no `Info.plist` key.** Use them first.
2. **Declare a purpose string** — one `NS…UsageDescription` per resource, **specific to this app's use** ("Take a photo of your receipt to attach it to the expense"), localized in the String Catalog's `InfoPlist` strings. A missing key crashes the app at the request; a generic string is a review rejection (`mobile-<stack>:store-compliance` § purpose strings).
3. **Read the status; ask only from `notDetermined`.** The system prompt appears once; after a denial the only route is Settings.
4. **Pre-prompt in context**, from the moment the user taps the feature: a screen or sheet saying what the permission is for, with **Continue** and **Not now**. Only Continue triggers the system prompt. Never at launch.
5. **Denied is a working screen**: say what is unavailable, offer the alternative (a picker instead of the camera, manual address instead of location), and a button to `UIApplication.openSettingsURLString`. A denied status is rechecked on `scenePhase == .active` — the user may have changed it in Settings.
6. **Release**: stop the capture session, location updates and biometric contexts when the screen goes.

The key / status API per resource, and the privacy-manifest note, are in [`references/permissions.md`](references/permissions.md).

```swift
enum CameraAccess {
    case granted, undetermined, denied
}

func cameraAccess() -> CameraAccess {
    switch AVCaptureDevice.authorizationStatus(for: .video) {
    case .authorized: .granted
    case .notDetermined: .undetermined
    case .denied, .restricted: .denied
    @unknown default: .denied
    }
}

struct ReceiptCaptureView: View {
    @State private var access = cameraAccess()
    @State private var showingPrePrompt = false
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        content
            .onChange(of: scenePhase) { _, phase in
                if phase == .active { access = cameraAccess() }
            }
    }

    @ViewBuilder
    private var content: some View {
        switch access {
        case .granted:
            CameraPreview()
        case .undetermined:
            PermissionPrePrompt(
                title: "Scan receipts",
                message: "Allow camera access to photograph a receipt and attach it to your expense.",
                allow: { Task { access = await AVCaptureDevice.requestAccess(for: .video) ? .granted : .denied } }
            )
        case .denied:
            CameraDeniedView()
        }
    }
}
```

`PermissionPrePrompt` and `CameraDeniedView` are the app's two small shared views (the denied one has the Settings button and the picker alternative). Their buttons carry test ids (`Camera.PrePrompt.Allow`, `Camera.Denied.OpenSettings`).

## Photos and files — the pickers

```swift
struct AvatarPicker: View {
    @State private var selection: PhotosPickerItem?
    @State private var image: Image?

    var body: some View {
        PhotosPicker("Choose photo", selection: $selection, matching: .images)
            .accessibilityIdentifier("Profile.PhotoPicker")
            .task(id: selection) {
                guard let selection else { return }
                image = try? await selection.loadTransferable(type: Image.self)
            }
    }
}
```

- **`loadTransferable` is async and can fail** (iCloud download, unsupported type) — a failure renders an error state, not a silent nothing; the sample's `try?` is the minimum for a decorative preview, never for an upload.
- Large images are downsampled with `CGImageSource` thumbnail options before display or upload; never decode a 48 MP original into a `UIImage` on the main actor.
- `.fileImporter(isPresented:allowedContentTypes:)` returns **security-scoped URLs**: bracket access with `startAccessingSecurityScopedResource()` / `stopAccessingSecurityScopedResource()` and copy into the app container if the file is needed later. `.fileExporter` writes where the user chooses.
- `FileDocument` is deprecated by the iOS 27 SDK; a new document type is `ReferenceFileDocument` / `UIDocument` where the codebase has them.

## Camera

`AVCaptureSession` runs **off the main actor** (`session.startRunning()` blocks); an `actor` or a dedicated serial queue owns the session, the `UIViewRepresentable` preview layer ([`uikit`](../uikit/SKILL.md) interop) only displays it. Stop the session in `onDisappear` and on `scenePhase != .active`; handle `AVCaptureSession.wasInterruptedNotification`. Barcode scanning is `DataScannerViewController` (iOS 16+, supported devices — check `isSupported` / `isAvailable`) before a hand-built metadata output. A device with no camera (simulator, some iPads) reaches the denied-style fallback.

## Location

- **Ask for When In Use first** (`NSLocationWhenInUseUsageDescription`); *Always* only for a feature that demonstrably needs it, requested later and separately.
- **One-off position**: `CLLocationUpdate.liveUpdates()` taking the first non-nil `location`, then ending the loop — not a manager left running. Continuous use ends with the screen.
- **Precise vs approximate**: `CLLocationManager.accuracyAuthorization`; request the accuracy the feature needs, and a `NSLocationTemporaryUsageDescriptionDictionary` key for a one-off precise request. A feature that works with approximate location does not ask for precise.
- `desiredAccuracy` and `distanceFilter` match the need (a store locator does not need `kCLLocationAccuracyBest`); battery is a cost.
- Coordinates are personal data: not in logs, not in analytics at full precision, not in a URL.

## Biometrics — LocalAuthentication

```swift
struct BiometricGate {
    func unlock(reason: String) async throws -> Bool {
        let context = LAContext()
        var availability: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &availability) else {
            throw BiometricError.unavailable
        }
        return try await context.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: reason)
    }
}

enum BiometricError: Error { case unavailable }
```

- Declare `NSFaceIDUsageDescription` — without it Face ID falls back to the passcode or fails.
- **`.deviceOwnerAuthentication` includes the passcode fallback**; `.deviceOwnerAuthenticationWithBiometrics` is for flows that must be biometric and have their own fallback. A user without enrolment reaches the fallback path, not a dead end.
- **A `true` from `evaluatePolicy` is a UI convenience, not authentication of a secret.** Anything that matters is a Keychain item behind `SecAccessControl` with `.biometryCurrentSet` — the secret is released only by the OS ([`offline-and-storage` `references/keychain.md`](../offline-and-storage/references/keychain.md); `MASWE-0020`). A user cancel (`LAError.userCancel`) is not an error banner.
- Re-auth on resume for sensitive screens: call on `scenePhase` returning to `.active` after a stated interval, and cover content while inactive (`mobile-<stack>:security` § 3).

## Haptics, share and links out

- `.sensoryFeedback(.success, trigger: didSave)` (iOS 17) after a user-initiated result; no haptics for passive events or on every scroll tick; respect that the system disables them under Low Power or Silent settings automatically.
- `ShareLink(item: url, subject: Text(title), message: Text(summary))` for a URL or `Transferable`; a share of a **file or image** provides it as `Transferable` with a preview. The share sheet is the system's — no custom sheet.
- Opening other apps: `Link` / `openURL`; `canOpenURL:` is deprecated by the iOS 27 SDK, so do not probe for installed apps — open and handle failure, and keep `LSApplicationQueriesSchemes` empty unless a recorded reason exists.
- The pasteboard: never read at launch; a secret is never copied (`mobile-<stack>:security` § 4).

## Rules

- A permission-free system picker before a permission; one specific, localized purpose string per resource.
- Ask only from `notDetermined`, after an in-context pre-prompt, never at launch.
- The denied and restricted states are working screens with an alternative and a Settings route, rechecked on foreground.
- Sessions, location updates and contexts end with the screen; nothing runs while backgrounded unless declared.
- Heavy work (capture start, image decode, large file copy) is off the main actor.
- Biometrics release a Keychain secret; a boolean alone gates nothing that matters.
- Location asks When In Use, at the accuracy the feature needs.
- Test ids on the pre-prompt, denied and picker controls.

## What NOT to do

- No permission prompt at app launch or on the first screen "to get it over with".
- No generic purpose strings ("We need your location"), no missing keys, no `NSLocationAlwaysAndWhenInUse…` for a foreground feature.
- No hand-built photo grid asking for full library access where `PhotosPicker` fits.
- No `startRunning()` on the main thread; no capture session left running behind a pushed screen.
- No `LAContext.evaluatePolicy` result as the only protection of a stored secret.
- No `canOpenURL:` probing; no reading `UIPasteboard` at launch.
- No dead end on denial — a button that does nothing or an empty screen.

## Generation steps

1. Read the existing permission views and `Info.plist` / String Catalog keys; detect the deployment target.
2. Choose per capability: system picker → permission; list each `NS…UsageDescription` needed and add it, localized.
3. Write the status check, pre-prompt, request and denied views; recheck on foreground.
4. Implement the capability off the main actor with start/stop tied to the screen.
5. For biometrics, put the secret behind `SecAccessControl`; the LAContext prompt is a fallback only for UI gating.
6. Add test ids; add `PrivacyInfo.xcprivacy` entries for any Required Reason API the code touches.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Build with warnings as errors; the project's formatter and linter pass.
- On a device after "Reset Location & Privacy" (Settings → General → Transfer or Reset): each feature shows the pre-prompt, then the system prompt once; denying shows the denied screen with a working Settings button; flipping the permission in Settings and returning updates the screen.
- A camera screen popped mid-capture leaves the camera indicator off; location updates stop with the screen.
- Face ID with no enrolment reaches the passcode path.
- Dev-side tests: the status → state mapping and the pre-prompt flow behind a one-method fake; device journeys with permission dialogs are `qa-mobile-<stack>`'s (peer).

## Handoffs

- Notifications and links → `mobile-ios:push-and-deep-links` · system surfaces → `mobile-ios:system-integration`
- Keychain behind biometrics → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Purpose strings and Required Reason entries as store policy → [`mobile-<stack>:store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Audit of what the app asks → [`mobile-<stack>:security`](../../../_shared/security/SKILL.md)
- UIKit controllers (document camera, pickers) → [`uikit`](../uikit/SKILL.md)
- Accessibility of the pre-prompt → `mobile-ios:accessibility`
