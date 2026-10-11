# Permissions — keys, status APIs, request calls

One row per protected resource. **Always** localize the string in the `InfoPlist` String Catalog and write it for this app's use. A missing key is a crash at the request; the key list below is the long-standing set — confirm a rarely used one against Apple's *Information Property List Key Reference* before shipping.

| Resource | `Info.plist` key | Status | Request |
|---|---|---|---|
| Camera | `NSCameraUsageDescription` | `AVCaptureDevice.authorizationStatus(for: .video)` | `await AVCaptureDevice.requestAccess(for: .video)` |
| Microphone | `NSMicrophoneUsageDescription` | `AVCaptureDevice.authorizationStatus(for: .audio)` / `AVAudioApplication.shared.recordPermission` (iOS 17) | `AVAudioApplication.requestRecordPermission` (iOS 17), `AVAudioSession` below |
| Photos — read / write the whole library | `NSPhotoLibraryUsageDescription` | `PHPhotoLibrary.authorizationStatus(for: .readWrite)` | `PHPhotoLibrary.requestAuthorization(for:)` — **avoid; use `PhotosPicker`** |
| Photos — save only | `NSPhotoLibraryAddUsageDescription` | `…(for: .addOnly)` | `…requestAuthorization(for: .addOnly)` |
| Location (foreground) | `NSLocationWhenInUseUsageDescription` | `CLLocationManager().authorizationStatus` | `requestWhenInUseAuthorization()` |
| Location (always) | `NSLocationAlwaysAndWhenInUseUsageDescription` | same | `requestAlwaysAuthorization()` after When In Use |
| Face ID | `NSFaceIDUsageDescription` | `LAContext.canEvaluatePolicy` | `evaluatePolicy` |
| Contacts | `NSContactsUsageDescription` | `CNContactStore.authorizationStatus(for: .contacts)` | `CNContactStore().requestAccess(for:)` — prefer `ContactAccessButton` / the contact picker where available |
| Calendars / Reminders | `NSCalendarsFullAccessUsageDescription`, `NSCalendarsWriteOnlyAccessUsageDescription`, `NSRemindersFullAccessUsageDescription` (iOS 17) | `EKEventStore.authorizationStatus(for:)` | `requestFullAccessToEvents()` / `requestWriteOnlyAccessToEvents()` |
| Bluetooth | `NSBluetoothAlwaysUsageDescription` | `CBManager.authorization` | Created `CBCentralManager` triggers it |
| Local network | `NSLocalNetworkUsageDescription` (+ `NSBonjourServices`) | no API — appears on first use | first connection |
| Motion | `NSMotionUsageDescription` | `CMMotionActivityManager.authorizationStatus()` | first query |
| Speech | `NSSpeechRecognitionUsageDescription` | `SFSpeechRecognizer.authorizationStatus()` | `SFSpeechRecognizer.requestAuthorization` |
| Notifications | none | `UNUserNotificationCenter.notificationSettings()` | `requestAuthorization` — `mobile-ios:push-and-deep-links` |
| Tracking (ATT) | `NSUserTrackingUsageDescription` | `ATTrackingManager.trackingAuthorizationStatus` | `ATTrackingManager.requestTrackingAuthorization` after the pre-prompt; **EU alternative from iOS 27.2** — store-compliance owns it |

## Needs no permission

`PhotosPicker`, `fileImporter` / `fileExporter`, `ShareLink`, `VNDocumentCameraViewController`, `ContactAccessButton`-style system pickers, `CLLocationButton` (a one-tap, temporary location grant), and the system share, print and Open In sheets.

## Status → screen

| System status | Screen |
|---|---|
| `notDetermined` | Pre-prompt in context → system prompt |
| `authorized` / `granted` | The feature |
| `limited` (Photos, Contacts) | The feature, plus a "manage selection" affordance |
| `denied` | Denied screen: what is unavailable, the alternative, **Open Settings** |
| `restricted` (parental / MDM) | A message only — Settings will not help; the alternative path |

Recheck on `scenePhase == .active`.

## Required Reason and privacy manifest

Permission **prompts** are not manifest entries, but code that backs these features often touches Required Reason APIs (file timestamps when caching a photo, disk space before a recording, `UserDefaults` for "pre-prompt shown"). Add the matching `NSPrivacyAccessedAPITypes` entries; confirm with Archive → *Generate Privacy Report* ([`mobile-<stack>:store-compliance`](../../../../_shared/store-compliance/references/apple.md) § 2). Collected data (location, photos, contacts) is declared in `NSPrivacyCollectedDataTypes` and in the App Privacy answers.

## The pre-prompt, once

A pre-prompt records that it was shown so it is not repeated after "Not now" in the same session; the **denied** path is what appears afterwards. The "shown" flag is a plain `UserDefaults` bool — no data about the user's answer beyond that.
