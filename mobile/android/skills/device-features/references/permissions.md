# Permissions — manifest entries, request calls, policy

One row per capability. A runtime permission is requested from the screen that needs it, after a pre-prompt; Play policy for the restricted ones is [`mobile-shared-store-compliance`](../../../../_shared/store-compliance/references/google-play.md) § 5. Confirm a rarely used permission against the Android *Manifest.permission* reference for the target API before shipping.

| Capability | Manifest | Request | Prefer instead |
|---|---|---|---|
| Camera (own preview) | `CAMERA` | `RequestPermission` | `TakePicture` / `CaptureVideo` intent — no permission |
| Microphone | `RECORD_AUDIO` | `RequestPermission` | — |
| Photos / video pick | none | `PickVisualMedia` | this *is* the preferred route |
| Photos / video — broad library access (core function only) | `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO`, `READ_MEDIA_VISUAL_USER_SELECTED` | `RequestMultiplePermissions` | photo picker — **requires a Play declaration** |
| Audio library | `READ_MEDIA_AUDIO` | `RequestPermission` | `OpenDocument` for a single file |
| Files | none | SAF `OpenDocument` / `CreateDocument` / `OpenDocumentTree` | never `MANAGE_EXTERNAL_STORAGE` |
| Location, foreground | `ACCESS_COARSE_LOCATION` + `ACCESS_FINE_LOCATION` | `RequestMultiplePermissions` (both together) | the location button for a one-time fix |
| Location, background | `ACCESS_BACKGROUND_LOCATION` | separate, later `RequestPermission` | a foreground service continuing a user action |
| Contacts | `READ_CONTACTS` | `RequestPermission` | Android Contact Picker (Play policy **2027-01-27**) |
| Calendar | `READ_CALENDAR` / `WRITE_CALENDAR` | `RequestMultiplePermissions` | an `Intent.ACTION_INSERT` into the calendar app |
| Bluetooth | `BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT`, `BLUETOOTH_ADVERTISE` (API 31+), `neverForLocation` flag where true | `RequestMultiplePermissions` | companion device pairing (`CompanionDeviceManager`) |
| Nearby Wi-Fi | `NEARBY_WIFI_DEVICES` (API 33+) | `RequestPermission` | — |
| Local network (API 37) | `ACCESS_LOCAL_NETWORK` | `RequestPermission` | — |
| Notifications | `POST_NOTIFICATIONS` (API 33+) | `mobile-android-notifications-and-links` | — |
| Biometrics | `USE_BIOMETRIC` (normal permission, no prompt) | `BiometricPrompt` | — |
| Body sensors / activity recognition | `BODY_SENSORS`, `ACTIVITY_RECOGNITION` | `RequestPermission` | Health Connect with its own permission model |
| Phone state / call log / SMS | restricted by Play | — | do not request without a policy-qualifying core function |

## Status → screen

| System status | Screen |
|---|---|
| Not asked | Pre-prompt in context → system dialog |
| Granted | The feature |
| Granted partially (approximate location, selected photos) | The feature at the lower precision, plus a way to widen it |
| Denied, rationale available | Short explanation → request again |
| Denied permanently | Denied screen: what is unavailable, the alternative, **Open Settings** |
| Restricted by device policy (managed profile) | A message only — Settings will not help; the alternative path |

## Manifest hygiene

- Declare **only used permissions**; remove library-added ones you do not need with `tools:node="remove"` and say why in the merge decision.
- `maxSdkVersion` on a permission retired by the platform (`WRITE_EXTERNAL_STORAGE` has no use at the current target).
- `<uses-feature android:required="false">` for camera, location, Bluetooth and telephony unless the app cannot function without them.
- Every permission appears in the Play **Data safety** answers when it collects data; a declaration form exists for the restricted ones.

## Data that backs a feature

Permission **prompts** are not store declarations, but the data behind them is: location, photos, contacts and audio are declared in Data safety; their handling (retention, deletion on account removal) follows [`mobile-shared-store-compliance`](../../../../_shared/store-compliance/SKILL.md).
