---
paths:
  - "**/*{Permission,Camera,Location,Biometric,Credential,Notification,Messaging,Push,Worker,Service,Receiver,Widget,Alarm,Picker}*.kt"
  - "**/{permission*,camera,location,biometric*,notification*,push,work*,service*,widget*,alarm*}/**/*.kt"
---

<!-- mobile-android rules v1 (2026-11-03): device features, notifications and background work. Installed by /mobile-android:rules; edit the paths above to where this project keeps that code. -->

# Android device features, notifications and background work

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

## Permissions and devices

- A permission is asked in context after a pre-prompt, never at launch; the denied path is a working screen with Open Settings; status is rechecked on resume, never cached across process starts. *major*
- Photos and video come from the photo picker; a picked `Uri` is temporary and untrusted, never `File(uri.path)`, and is read and decoded off the main thread. *major*
- Approximate location always works; precise only when needed; background location is a later, separate request; updates stop with the lifecycle, never logged. *major*
- CameraX is bound to a lifecycle owner; a system capture intent when enough. *major*
- `BiometricPrompt` unlocks a Keystore key through a `CryptoObject`, never a success flag; enrolment, hardware and lockout have screens; no silent fallback to a weaker check. *blocker*
- Sign-in uses Credential Manager; no Google One Tap, Google Sign-In or FIDO2 API in new code. *major*

## Notifications

- `POST_NOTIFICATIONS` is asked in context after a pre-prompt; the denied state keeps an in-app list and a Settings route. *major*
- Every notification names a channel created at start; importance is not raised for convenience. *major*
- The push registration is uploaded through WorkManager, refreshed when it changes and deleted on sign-out. *major*

## Background work

- Deferrable work is unique, idempotent WorkManager work with the weakest constraints that hold. *major*
- A foreground service starts from a visible context, stops when its work ends and implements `onTimeout` where its type has one. *major*
- Exact alarms only for an alarm, timer or calendar core function, behind `canScheduleExactAlarms()` with a working denied path. *major*
- A widget reads the repository, shows loading, loaded and failed, and updates after sync. *major*
- Wake locks are bounded. *major*
