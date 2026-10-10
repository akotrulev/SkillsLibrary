# Foreground service types — manifest, permission, prerequisite

Read 2026-10-10 from developer.android.com/develop/background-work/services/fgs/service-types. Since API 34 every foreground service declares a type, requests `FOREGROUND_SERVICE` **and** the matching permission, and meets its runtime prerequisite. At target 34+ the types are declared in Play Console under **Policy → App content**.

| Type (`foregroundServiceType`) | Permission | Runtime prerequisite |
|---|---|---|
| `camera` | `FOREGROUND_SERVICE_CAMERA` | `CAMERA` granted |
| `connectedDevice` | `FOREGROUND_SERVICE_CONNECTED_DEVICE` | A network / NFC / IR permission declared, or a Bluetooth / UWB permission granted, or `UsbManager.requestPermission()` called |
| `dataSync` | `FOREGROUND_SERVICE_DATA_SYNC` | None; has a timeout — see below |
| `health` | `FOREGROUND_SERVICE_HEALTH` | `HIGH_SAMPLING_RATE_SENSORS` declared, or a health / activity runtime permission granted |
| `location` | `FOREGROUND_SERVICE_LOCATION` | Location on and coarse or fine granted |
| `mediaPlayback` | `FOREGROUND_SERVICE_MEDIA_PLAYBACK` | None; `[API37]` background-audio rule applies |
| `mediaProcessing` | `FOREGROUND_SERVICE_MEDIA_PROCESSING` | None; ~6 h per 24 h shared across the app |
| `mediaProjection` | `FOREGROUND_SERVICE_MEDIA_PROJECTION` | User consent via `createScreenCaptureIntent()` first |
| `microphone` | `FOREGROUND_SERVICE_MICROPHONE` | `RECORD_AUDIO` granted |
| `phoneCall` | `FOREGROUND_SERVICE_PHONE_CALL` | `MANAGE_OWN_CALLS` declared, or `ROLE_DIALER` held |
| `remoteMessaging` | `FOREGROUND_SERVICE_REMOTE_MESSAGING` | None |
| `shortService` | none beyond `FOREGROUND_SERVICE` | None; ~3 min from `startForeground`, no sticky, cannot start other foreground services |
| `specialUse` | `FOREGROUND_SERVICE_SPECIAL_USE` | None, but `<property android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE" android:value="…"/>` explaining the use for Play review |
| `systemExempted` | `FOREGROUND_SERVICE_SYSTEM_EXEMPTED` | An eligibility criterion (device owner, VPN app, `ROLE_EMERGENCY`, …) |

## Timeouts

- `mediaProcessing` and `dataSync`: the system calls `Service.onTimeout(startId, fgsType)` and the service has a few seconds to call `stopSelf()`; otherwise an ANR ("did not stop within its timeout"). `onTimeout` does not exist on API 34 and lower — there, stop as soon as the work finishes.
- `shortService`: implement `onTimeout`; calling `startForeground` again extends it by 3 minutes only while the app is visible or has a start exemption; otherwise `ForegroundServiceStartNotAllowedException`.
- WorkManager 2.10+ reports `STOP_REASON_FOREGROUND_SERVICE_TIMEOUT` for a foreground worker stopped by a type timeout.

## Starting from the background

- Camera, microphone, location and body-sensor types cannot start from the background; location can with `ACCESS_BACKGROUND_LOCATION`, health with `READ_HEALTH_DATA_IN_BACKGROUND` (API 36) / `BODY_SENSORS_BACKGROUND` (33–35).
- At target 15+ `dataSync` and `mediaPlayback` services cannot be launched from a `BOOT_COMPLETED` receiver.

## `[API37]` background audio

Read 2026-10-10 from developer.android.com/about/versions/17/changes/bg-audio. All apps: background audio playback, focus requests and volume changes need a visible activity or a foreground service whose type is not `shortService`. Target 37: the foreground service in the background must also have while-in-use capability — granted when the user started it or while the app was visible. Exempt: apps holding the exact-alarm permission driving `USAGE_ALARM` streams. Failures are silent; `requestAudioFocus` returns `AUDIOFOCUS_REQUEST_FAILED`. **Not verified:** the full while-in-use eligibility list (system-started services, media-button starts) — read the page before relying on an edge case.
