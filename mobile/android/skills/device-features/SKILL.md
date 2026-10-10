---
name: mobile-android-device-features
description: Use when an Android app touches device capabilities — runtime permissions with a pre-prompt and denied path, the photo picker, CameraX, precise vs approximate location, BiometricPrompt, Credential Manager and passkeys, SAF, ACCESS_LOCAL_NETWORK. Triggers "ask for camera access", "pick a photo", "denied path". Do NOT use for push and links (`mobile-android-notifications-and-links`), widgets (`-system-integration`) or Keystore storage (`-offline-and-storage`).
---

# Android — Device Features

Owns **asking the user for a capability and using it well**: the permission recipe, the pickers that need no permission, camera, location, biometrics and credentials. Store policy for each permission is [`mobile-shared-store-compliance`](../../../_shared/store-compliance/references/google-play.md) § 5; the secure-coding rules are [`mobile-shared-security`](../../../_shared/security/references/android.md). Sibling: [`mobile-ios-device-features`](../../../ios/skills/device-features/SKILL.md).

## Version lane

| Concern | Primary (targetSdk 36, compileSdk 37) | Brownfield / notes |
|---|---|---|
| Permission request | `ActivityResultContracts.RequestPermission` / `RequestMultiplePermissions`, or Accompanist-free state in a ViewModel | `onRequestPermissionsResult` in older Views code — match, do not mix |
| Photos / video | **Photo picker** `PickVisualMedia` / `PickMultipleVisualMedia` — no permission | `READ_MEDIA_*` only when broad media access is the **core function** — [permissions](references/permissions.md) |
| Files | Storage Access Framework (`OpenDocument`, `CreateDocument`, `OpenDocumentTree`) | `MANAGE_EXTERNAL_STORAGE` is a restricted permission — never |
| Camera | CameraX 1.x (`Preview`, `ImageCapture`, `ImageAnalysis`); or the system camera intent, which needs no permission | Camera2 only where CameraX cannot |
| Location | Fused Location Provider (`play-services-location`) with `ACCESS_COARSE_LOCATION` + `ACCESS_FINE_LOCATION` requested together | Platform `LocationManager` for devices without Play services |
| Biometrics | `BiometricPrompt` (`androidx.biometric`) with a `CryptoObject` | A callback that only flips a boolean is bypassable |
| Sign-in | **Credential Manager 1.6** (passwords, passkeys, federated) | Google Sign-In / One Tap are legacy; FIDO2 API is superseded |
| Local network | `ACCESS_LOCAL_NETWORK` runtime permission at **API 37** | Below 37 no permission — nothing to detect |
| Contacts | Android Contact Picker for apps without broad contact needs (Play policy 2027-01-27) | `READ_CONTACTS` only for core contact functionality |

## When to use

- Asking for a permission, handling "don't ask again", building the denied screen
- Picking a photo, video or document; saving a file
- A camera preview, a scan, a capture
- "Where is the user", a map centred on them, geofencing as a feature
- Biometric unlock or re-auth; passkeys; saved passwords
- Reaching a device on the LAN at API 37

## When NOT to use

- Push, notification permission, App Links → `mobile-android-notifications-and-links`
- WorkManager, foreground services, widgets, exact alarms → `mobile-android-system-integration`
- Where secrets are stored, Keystore key setup → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Sign-in provider setup (Auth0 Universal Login) → `auth-auth0-android`
- Store declaration forms and policy dates → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Another stack → `mobile-ios-device-features`, `mobile-react-native-device-features`

## The permission recipe

Permissions are **asked in context, at the moment of use, after a pre-prompt; the denied path is a working screen.** A permission is requested from the screen that needs it — never at launch.

Every request has four states, held in the screen's `uiState`:

| State | Meaning | Screen |
|---|---|---|
| `Granted` | Use the feature | The feature |
| `NotAsked` | Never requested | Pre-prompt (why, benefit) → system dialog |
| `Rationale` | Denied once; the system will show the dialog again | A short explanation, then request again |
| `Denied` | Denied permanently (or twice) — the dialog will not appear | **Denied screen**: what is unavailable, the alternative, **Open Settings** |

```kotlin
@Composable
fun CameraGate(
    onGranted: @Composable () -> Unit,
    onUseAlternative: () -> Unit,
) {
    val context = LocalContext.current
    val activity = context.findActivity()
    var asked by rememberSaveable { mutableStateOf(false) }
    var granted by remember { mutableStateOf(hasPermission(context, Manifest.permission.CAMERA)) }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { result ->
        granted = result
        asked = true
    }

    LifecycleResumeEffect(Unit) {
        granted = hasPermission(context, Manifest.permission.CAMERA)
        onPauseOrDispose { }
    }

    when {
        granted -> onGranted()
        !asked -> CameraPrePrompt(onContinue = { launcher.launch(Manifest.permission.CAMERA) }, onNotNow = onUseAlternative)
        activity.shouldShowRequestPermissionRationale(Manifest.permission.CAMERA) ->
            CameraRationale(onTryAgain = { launcher.launch(Manifest.permission.CAMERA) }, onNotNow = onUseAlternative)
        else -> CameraDenied(onOpenSettings = { context.openAppSettings() }, onUseAlternative = onUseAlternative)
    }
}
```

- **Recheck on every resume** — the user may have toggled it in Settings; a stale `granted` flag is a bug.
- `shouldShowRequestPermissionRationale` is `false` both before the first ask and after a permanent denial; the `asked` flag tells them apart. The "asked" bit is **plain preference data** (DataStore), not the user's answer.
- The pre-prompt is **shown before the system dialog** and says what the feature does with the data; "Not now" leads to the alternative path (typing, the picker), not to a dead end. Do not repeat a declined pre-prompt in the same session.
- **The denied screen works**: it states what is unavailable, offers an alternative where one exists, and links to `Settings.ACTION_APPLICATION_DETAILS_SETTINGS` (`openAppSettings`). It never shows a blank preview.
- **One-time and auto-reset permissions**: since Android 11 the user can grant "Only this time", and unused apps' permissions auto-reset. Treat every launch as possibly *not granted* and never cache `Granted` across process starts.
- Every permission is declared in the manifest with a `maxSdkVersion` where it is retired; **declare only what is used** — the permission list is audited ([`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md) `L`-series). Table of permissions, request calls and policy notes: [`references/permissions.md`](references/permissions.md).
- Request state lives in the ViewModel when more than one composable reacts to it; the **launcher** is created in the composable (it needs the `ActivityResultRegistry`).

## Photos and files — the pickers

**The photo picker needs no permission and no manifest entry.** Use it for every "attach / choose a photo or video".

```kotlin
val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
    uri?.let(viewModel::onPhotoPicked)
}
Button(onClick = {
    picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
}) { Text(stringResource(R.string.choose_photo)) }
```

- `PickMultipleVisualMedia(maxItems)` for several; the contract falls back to the system picker (or a GMS backport) on older devices — **no `READ_EXTERNAL_STORAGE`**.
- **`READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` only when broad, ongoing media access is the app's core function** (a gallery, a photo editor library, a backup tool) and the picker cannot do the job; Play requires a declaration. An upload form, an avatar chooser or an attachment button uses the picker — requesting the permission for it is a **major** finding. `READ_MEDIA_VISUAL_USER_SELECTED` (partial access) is handled when `READ_MEDIA_*` is legitimately used.
- The returned `Uri` is **temporary**: copy what you need, or `takePersistableUriPermission` for SAF documents; never assume a `file` path. Read and decode off the main thread.
- SAF for documents: `OpenDocument(arrayOf("application/pdf"))`, `CreateDocument`, `OpenDocumentTree`; **no `MANAGE_EXTERNAL_STORAGE`**. Saving a user-visible photo or download uses MediaStore insert (no permission from API 29).
- Treat a picked file as untrusted input: check MIME against content (not the extension), size-limit, never `Runtime.exec` or `loadLibrary` from it.
- Sharing out: `ShareCompat` / `Intent.createChooser` with `FileProvider` URIs and `FLAG_GRANT_READ_URI_PERMISSION`; `FileProvider` paths narrowed to a subfolder ([`mobile-shared-security`](../../../_shared/security/references/android.md) § 1).

## Camera — CameraX

```kotlin
@Composable
fun CameraPreview(controller: LifecycleCameraController, modifier: Modifier = Modifier) {
    val lifecycleOwner = LocalLifecycleOwner.current
    AndroidView(
        factory = { context ->
            PreviewView(context).apply {
                this.controller = controller
                controller.bindToLifecycle(lifecycleOwner)
            }
        },
        modifier = modifier,
    )
}
```

- `LifecycleCameraController` (or `ProcessCameraProvider.bindToLifecycle`) ties the camera to the **lifecycle owner** — it releases on stop; no manual `close()` in `onStop`. A camera held after the screen leaves is a leak and a privacy finding.
- Needs `CAMERA` only when the app opens the camera itself. **A capture via `ActivityResultContracts.TakePicture` / `CaptureVideo` needs no permission** — prefer it when a plain photo is enough.
- Capture and analysis callbacks run on an **executor that is not the main thread**; frames are `close()`d; analysis uses `STRATEGY_KEEP_ONLY_LATEST`.
- Scan flows: ML Kit barcode scanning through `ImageAnalysis`, or the Google code scanner (no camera permission) when it is enough.
- `uses-feature android:name="android.hardware.camera" android:required="false"` unless the app is useless without one.
- The preview and capture button carry `testTag`s; the preview has a text alternative of the action, not of the pixels.

## Location — precise and approximate

- **Ask for both `ACCESS_COARSE_LOCATION` and `ACCESS_FINE_LOCATION` in one request**; Android 12+ lets the user grant **approximate only**, and the app works with it. Ask for fine only when the feature needs street-level precision (turn-by-turn, "nearest door"); coarse is enough for "stores near me".
- Foreground only by default. **Background location is a separate, later request**, needs a declaration and a stated core need, and a foreground service reaches location only as a continuation of a user-initiated action (`mobile-android-system-integration`).
- For a one-shot "where am I", use `FusedLocationProviderClient.getCurrentLocation(Priority.PRIORITY_BALANCED_POWER_ACCURACY, cancellationToken)` — cancel it with the screen; for updates, a `callbackFlow` over `requestLocationUpdates` that removes updates in `awaitClose`, collected in `repeatOnLifecycle(STARTED)`.
- Play's Location Permissions policy (**2027-01-27**) points to the **location button** as the recommended minimum scope for precise location — use it where a feature needs a one-time fix.
- Location is personal data: declared in the Data safety form, never logged, never sent unless the feature needs it, and the "location services off" state is a handled screen (`SettingsClient.checkLocationSettings`).

## Biometrics

`BiometricPrompt` unlocks a Keystore key through a `CryptoObject` — a success callback that only flips a flag is a security finding; `BIOMETRIC_STRONG` for sensitive actions; none-enrolled, no-hardware and lockout states have screens. Sample and rules: [`references/biometrics-and-credentials.md`](references/biometrics-and-credentials.md).

## Credential Manager and passkeys

Sign-in is Credential Manager 1.6 (password + passkey + federated); the server owns the challenge and verification; cancellation is silent; One Tap and Google Sign-In are legacy. [`references/biometrics-and-credentials.md`](references/biometrics-and-credentials.md).

## Local network at API 37

`ACCESS_LOCAL_NETWORK` is requested in context only where a feature reaches the LAN, with a manual-address alternative; never raise the target for it. [`references/biometrics-and-credentials.md`](references/biometrics-and-credentials.md).

## Rules

- Permissions asked in context, after a pre-prompt; a denied screen that works; recheck on resume; never at launch.
- Photo picker for every pick of photos and videos; `READ_MEDIA_*` only for core, broad media access.
- Approximate location always works; precise only when needed; background location is its own later request.
- Camera is bound to a lifecycle owner; a system capture intent is preferred when it is enough.
- Biometrics unlock a Keystore key through a `CryptoObject`; enrolment, hardware and lockout states have screens.
- Credential Manager for sign-in; server owns the challenge and verification.
- Picked `Uri`s are temporary and untrusted; reads and decodes are off the main thread.
- Declared permissions equal used permissions.

## What NOT to do

- No permission request in `Application.onCreate` or the first screen "to get it over with".
- No `READ_EXTERNAL_STORAGE` / `READ_MEDIA_IMAGES` to attach a photo; no `MANAGE_EXTERNAL_STORAGE`.
- No blank preview or crash when camera, location or biometrics are denied or absent.
- No `BiometricPrompt` whose success callback only flips a flag; no silent fallback to a weaker check for a sensitive action.
- No permission result cached in a singleton across process starts.
- No Google One Tap / Google Sign-In / FIDO2 API in new code.
- No `ACCESS_BACKGROUND_LOCATION` bundled in the same request as foreground location.
- No `File(uri.path)` on a picker result; no decoding a full-size bitmap on the main thread.

## Generation steps

1. Read the manifest, the existing request style (launcher vs callbacks) and the compileSdk/targetSdk.
2. Decide per feature whether it needs a permission at all (picker, system intent, location button).
3. Write the four-state gate, the pre-prompt and the denied screen; add the manifest entry.
4. Write the feature (picker / CameraX / fused location / biometric / Credential Manager) bound to the lifecycle.
5. Add `testTag`s for the buttons, preview and denied actions.
6. Add ViewModel unit tests with a fake permission state and a fake client.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Build clean; Android Lint (`MissingPermission`, `ScopedStorage`) passes; the merged manifest lists only used permissions (`./gradlew :app:processReleaseManifest`).
- On a device: deny once → rationale; deny again → denied screen with **Open Settings**; grant in Settings → returning resumes the feature; "Only this time" re-asks next launch.
- Biometrics with none enrolled and with a lockout: a working screen each time.
- The photo picker works on an emulator without Play services; no storage permission is requested.
- Dev-side tests: [`mobile-android-unit-testing`](../unit-testing/SKILL.md); device journeys belong to `qa-mobile-android`.

## Handoffs

- Push permission, deep links → `mobile-android-notifications-and-links`
- Foreground-service types, widgets, exact alarms → `mobile-android-system-integration`
- Keystore keys, secrets → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Permission declarations, Data safety → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Manifest, FileProvider, WebView hardening → [`mobile-shared-security`](../../../_shared/security/SKILL.md)
- Sign-in form → [`forms`](../forms/SKILL.md) · TalkBack, 48 dp → `mobile-android-accessibility`
