---
name: system-integration
description: Use when an Android app must do work or appear outside its screens — WorkManager (periodic, expedited, constraints), foreground services with a type and Play declaration, Glance widgets, shortcuts, exact-alarm policy, API 37 background-audio rule. Triggers "sync in the background", "keep uploading", "add a widget", "schedule a reminder". Do NOT use for push and links (`mobile-android:push-and-deep-links`), offline data design (`-offline-and-storage`), or permissions (`-device-features`).
---

# Android — System Integration

Owns the work the app does **when its UI is not the thing running**: deferrable background work, user-visible long-running work, widgets, shortcuts and alarms. One rule orders it: **pick the weakest mechanism that does the job** — WorkManager over a foreground service, an inexact alarm over an exact one, a widget refreshed by data over one on a timer.

## Version lane

| Concern | Detail | Lane |
|---|---|---|
| WorkManager | **2.12.0** (2026-09-23); `minSdk` 24 — matches the house floor; `compileSdk` 33+ | `[WM-2.11-]` minSdk 23 on 2.11 |
| Foreground services | API 34+: **a type in the manifest, `FOREGROUND_SERVICE` plus the matching `FOREGROUND_SERVICE_<TYPE>` permission, runtime prerequisites**, and a Play Console declaration at target 34+ | Same |
| Background audio | **Any app**: background audio calls need a visible activity or a foreground service whose type is not `shortService`. **Target 37**: the foreground service must also have while-in-use capability, unless the app holds the exact-alarm permission and drives `USAGE_ALARM` streams. Failure is silent (focus returns `AUDIOFOCUS_REQUEST_FAILED`) | `[API37]` |
| Widgets | **Glance 1.2.0** stable (2026-08-26); 1.3 is alpha | `[API37]` `RemoteViews` bitmaps and icons capped at 1.5 × screen width × height × 4 bytes combined — over it is a fatal crash |
| Exact alarms | `USE_EXACT_ALARM` restricted to alarm / timer / calendar core function; `SCHEDULE_EXACT_ALARM` needs user approval and is denied by default since 13 | Same |
| Activity starts | API 37 extends background-activity-launch limits to `IntentSender`; use `MODE_BACKGROUND_ACTIVITY_START_ALLOW_IF_VISIBLE` | `[API37]` |

Sources read 2026-10-10: developer.android.com/jetpack/androidx/releases/{work,glance}, /develop/background-work/services/fgs/service-types, /about/versions/17/behavior-changes-17, /about/versions/17/changes/bg-audio. **Not verified:** the Glance widget refresh API details beyond the stable version — read the Glance release page and sample before quoting a signature.

## When to use

- Syncing, uploading, cleaning up — work that must survive the process
- A task the user started that must continue visibly (a download, a recording, a call, playback)
- A home-screen widget, an app shortcut, a pinned shortcut
- A reminder or an alarm at a time

## When NOT to use

- Push registration, channels, tap routing, `PendingIntent` rules → [`notifications-and-links`](../notifications-and-links/SKILL.md)
- What is stored and how it is synced → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Camera, location, microphone permissions → [`device-features`](../device-features/SKILL.md)
- Play declarations as policy → [`mobile-<stack>:store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Another stack → `mobile-ios:system-integration`, `mobile-react-native:device-features`

## Choosing the mechanism

| Need | Use | Not |
|---|---|---|
| Deferrable, must finish eventually (sync, upload, cleanup) | **WorkManager** `OneTimeWorkRequest` with constraints | A service, a coroutine in `Application` |
| Repeating (≥ 15 min) | `PeriodicWorkRequest` with `ExistingPeriodicWorkPolicy.KEEP` | `AlarmManager` repeating |
| Short, user-initiated, now | WorkManager `setExpedited(RUN_AS_NON_EXPEDITED_WORK_REQUEST)` | A foreground service for a few seconds |
| Long and user-visible (playback, call, active navigation, a long upload the user watches) | **Foreground service** with a type | WorkManager hiding a notification |
| At a clock time, user-visible | `AlarmManager` inexact (`setAndAllowWhileIdle`) → exact only by policy | `Handler.postDelayed` across process death |
| Reacting to a change in data | A repository `Flow` while the UI is up; WorkManager when it is not | A polling loop |

## WorkManager

```kotlin
class SyncOrdersWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val orders: OrderRepository,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result =
        orders.syncPending().fold(
            onSuccess = { Result.success() },
            onFailure = { if (runAttemptCount < MaxAttempts) Result.retry() else Result.failure() },
        )

    private companion object {
        const val MaxAttempts = 5
    }
}

fun WorkManager.enqueueOrderSync() = enqueueUniqueWork(
    "OrderSync",
    ExistingWorkPolicy.KEEP,
    OneTimeWorkRequestBuilder<SyncOrdersWorker>()
        .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
        .build(),
)
```

- **`CoroutineWorker`**, with the dispatcher injected through `Configuration.workerCoroutineContext` when a test needs control; `@HiltWorker` + `@AssistedInject` for Hilt apps, a `WorkerFactory` for manual DI — never a service locator inside the worker.
- **Unique work** (`enqueueUniqueWork` / `enqueueUniquePeriodicWork`) always — a second tap or a restart must not stack duplicates.
- **Constraints say what the work needs** (`NetworkType`, `BatteryNotLow`, `StorageNotLow`); do not add `RequiresCharging` for convenience. Backoff minimum is 10 s; the default is exponential from 30 s.
- **Workers are idempotent and cancellation-aware**: a worker can be stopped and re-run at any time; check `stopReason` in tests; do suspending work, never block.
- **Periodic minimum is 15 min**; a flex window narrows when it runs. A time-of-day refresh uses `setNextScheduleTimeOverride` with `ExistingPeriodicWorkPolicy.UPDATE` (2.9+; read the API reference for the signature).
- **Expedited work is quota-limited** in the background; always set an `OutOfQuotaPolicy`. Pre-API 31 it may run as a foreground service, so an expedited `CoroutineWorker` implements `getForegroundInfo()`.
- **Long worker the user should see**: `setForeground(ForegroundInfo(id, notification, type))` with a valid type and its permission (below); catch the `IllegalStateException` / `ForegroundServiceStartNotAllowedException` and fall back to non-expedited work.
- Chains (`beginWith().then()`) for ordered steps; pass ids in `Data`, never models or tokens (Data is small and plain).
- The app reads results through the repository's `Flow`, or `getWorkInfosFlow` for progress UI — not LiveData in new code. Test with `work-testing` (`TestListenableWorkerBuilder`); a worker that needs a device to be tested is too big.

## Foreground services

A foreground service is **for work the user is aware of and can stop**, shown with an ongoing notification. Every one declares a type, its permission and meets its prerequisite:

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />

<service
    android:name=".playback.PlaybackService"
    android:foregroundServiceType="mediaPlayback"
    android:exported="false" />
```

```kotlin
ServiceCompat.startForeground(
    service,
    NotificationId,
    notification,
    ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK,
)
```

The full type table (manifest value, permission, runtime prerequisite) and timeouts are in [`references/foreground-services.md`](references/foreground-services.md).

- **Type + matching `FOREGROUND_SERVICE_*` permission + runtime prerequisite** (camera needs `CAMERA`, microphone `RECORD_AUDIO`, location a granted location permission) or `startForeground` throws. `shortService` (~3 minutes, needs no extra permission) is for brief work; implement `onTimeout`.
- **A type that needs a Play Console declaration at target 34+** — media, location, camera, microphone, data sync, special use and others — is declared under **Policy → App content**, with a demo video where the form asks. `specialUse` also needs the `PROPERTY_SPECIAL_USE_FGS_SUBTYPE` property text that review reads. A type with no feature behind it is a rejection (L17).
- **Start from a user action or a legal exemption.** Starting from the background is restricted (Android 12+); a boot receiver cannot start `dataSync`, `mediaPlayback` or similar types at target 15+; camera, microphone and location cannot start from the background at all without the listed exemptions. Handle `ForegroundServiceStartNotAllowedException`.
- **`dataSync` and `mediaProcessing` have timeouts** (media processing about 6 hours per 24); implement `onTimeout(startId, fgsType)` and stop within seconds or the system raises an ANR. A one-off upload is usually WorkManager, not `dataSync`.
- **`[API37]` background audio**: playback, focus requests and volume changes from the background require a foreground service that is not `shortService`, and at target 37 one with while-in-use capability — the service the user started while the app was visible has it; one started from a boot receiver or scheduled work does not. **Start playback services from the visible UI; handle `AUDIOFOCUS_REQUEST_FAILED`** — never assume focus was granted. Media3 `MediaSessionService` owns the notification and the service lifecycle for playback; do not hand-roll one.
- **Stop it when the work ends** (`stopSelf()` / `stopForeground`); a service the user cannot stop is a vitals problem (excessive wake locks are measured, [`performance`](../performance/SKILL.md)).
- The ongoing notification has its own channel ([`notifications-and-links`](../notifications-and-links/SKILL.md)); on API 33+ the service runs even when `POST_NOTIFICATIONS` is denied, but the user sees it only in the Task Manager.

## Widgets — Glance

Compose-style widgets with Glance (`glance-appwidget` 1.2.0, `glance-material3` for theming). The widget is **a view of data the app already has**, rendered as `RemoteViews` — a subset of Compose, not Compose.

- A `GlanceAppWidget` with a `GlanceAppWidgetReceiver` and `res/xml` provider info; **responsive sizes** (`SizeMode.Responsive`) over one fixed size; theme with `GlanceTheme` so dynamic colour applies.
- **The widget never fetches on the main thread or on its own timer.** Data comes from the repository / DataStore; refresh by `updateAll` after a sync worker finishes, and by WorkManager for the periodic case. `updatePeriodMillis` is a floor of 30 minutes in the system — do not depend on it.
- Interaction is an `actionStartActivity` / `actionRunCallback` — an immutable `PendingIntent` under the hood, and the activity validates its extras ([`notifications-and-links`](../notifications-and-links/SKILL.md)).
- **`[API37]` keep bitmaps small**: a combined image budget over 1.5 × screen w × h × 4 bytes crashes the host process — downsample, prefer vector icons, no full-size hero images.
- A widget has a **loading / loaded / failed state like any data region**, never a blank tile; it must work signed-out (a sign-in prompt, not a crash).
- Content descriptions and 48 dp targets apply ([`accessibility`](../accessibility/SKILL.md)); test ids are not exposed through `RemoteViews` — widget journeys are `qa-mobile-*`'s with `content-desc`, which is the one place a label is the locator.

## Shortcuts

- **Static** shortcuts in `res/xml/shortcuts.xml` for fixed destinations; **dynamic** with `ShortcutManagerCompat` for recent items (keep the set small — the launcher shows about four); **pinned** on a user request through `requestPinShortcut`.
- A shortcut's intent is `VIEW` with an `https` URI or an explicit component + action — **the same validators as a link**; update or remove shortcuts when the item is deleted or the user signs out (`removeAllDynamicShortcuts`).
- Labels are string resources ([`languages`](../languages/SKILL.md)); a shortcut icon is an adaptive icon.

## Alarms and reminders

- **Default is inexact**: `setAndAllowWhileIdle` or WorkManager with `setInitialDelay` — within a minute or so of the time is enough for nearly everything.
- **Exact only when the user would call a late fire a failure** — an alarm clock, a timer, a calendar event notification. `USE_EXACT_ALARM` is a restricted permission for those core functions only; everyone else uses `SCHEDULE_EXACT_ALARM`, checks `alarmManager.canScheduleExactAlarms()`, and has a **working denied path** that falls back to inexact and offers `ACTION_REQUEST_SCHEDULE_EXACT_ALARM` (L16).
- Alarms **do not survive a reboot or an app force-stop**: re-register on `BOOT_COMPLETED` / `ACTION_MY_PACKAGE_REPLACED` from the persisted schedule, with a receiver `exported="false"`.
- A reminder's `PendingIntent` is immutable with a distinct request code per reminder; the alarm fires into a receiver that posts the notification — no long work in the receiver (`goAsync` window is short; enqueue a worker).
- An app targeting 37 that plays alarm audio from the background without a foreground service qualifies for the `USAGE_ALARM` exemption only while it holds the exact-alarm permission.

## Procedure

1. Detect: WorkManager version and minSdk, existing services and their manifest types, widget providers, alarm calls, the target SDK.
2. Pick the mechanism from the table; justify any foreground service or exact alarm in the PR text.
3. Write the worker (unique, constraint-minimal, idempotent) or the typed service (permission, prerequisite, stop path, `onTimeout`).
4. Widgets: provider info, responsive layout, three states, update after sync, bitmap budget.
5. Shortcuts and alarms: validators, denied paths, boot re-registration.
6. Add the Play declaration to the release checklist ([`mobile-<stack>:release`](../../../_shared/release/SKILL.md)); tests per [`unit-testing`](../unit-testing/SKILL.md).

## Validation (exit gate)

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- [ ] Every `<service>` that goes foreground has `foregroundServiceType` and the matching `FOREGROUND_SERVICE_*` permission; the Console declaration is listed
- [ ] Work is `enqueueUnique…`; the app survives process death mid-work and the worker re-runs cleanly
- [ ] A foreground service stops when its work ends; a denied `POST_NOTIFICATIONS` still lets it run
- [ ] At target 37, background playback starts only from a user-visible context and tolerates `AUDIOFOCUS_REQUEST_FAILED`
- [ ] `canScheduleExactAlarms()` is false in a test: the reminder falls back, the UI explains
- [ ] The widget shows loading, loaded and failed; bitmaps are under the combined budget
- [ ] Dev-side tests: workers with `TestListenableWorkerBuilder` and fakes; device journeys are `qa-mobile-*`'s

## Handoffs

- Push, channels, tap routing, immutable `PendingIntent` → [`notifications-and-links`](../notifications-and-links/SKILL.md)
- Offline-first repositories the worker calls → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Location, camera, microphone permission flows → [`device-features`](../device-features/SKILL.md)
- Play declarations and restricted permissions → [`mobile-<stack>:store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Wake locks, vitals, tracing → [`performance`](../performance/SKILL.md)
- Dev-side worker tests → [`unit-testing`](../unit-testing/SKILL.md)
