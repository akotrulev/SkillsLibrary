---
name: mobile-android-notifications-and-links
description: Use when an Android app needs push or local notifications, or opens from a link — FCM registration, notification channels, POST_NOTIFICATIONS, tap routing, immutable PendingIntent, full-screen-intent policy, App Links verification (assetlinks.json). Triggers "add push", "tap opens the order", "link opens the app". Do NOT use for the URI-to-keys parser (`mobile-android-navigation`), runtime permissions generally (`-device-features`), or the sending server.
---

# Android — Notifications and Links

Owns how the outside world gets into the app: **push and local notifications** (permission, channels, registration, tap, `PendingIntent`) and **links** (App Links verification, intent filters). Both deliver **untrusted input that chooses a destination**, validated before it routes ([`mobile-shared-security`](../../../_shared/security/SKILL.md), rule K16). [`navigation`](../navigation/SKILL.md) owns the pure URI → keys function; this skill owns everything up to calling it — it does not re-implement the parser.

## Version lane

| Concern | Detail | Lane |
|---|---|---|
| Permission | `POST_NOTIFICATIONS` is a runtime permission from API 33; FCM SDK ≥ 23.0.6 declares it in its manifest, the app still asks | minSdk 24: below 33 notifications are on until the user turns them off |
| Channels | Required from API 26; every notification names a channel | Same |
| FCM registration | **Firebase Installation ID (FID)**: manifest meta-data `firebase_messaging_installation_id_enabled` = `true`, override `onRegistered(installationId)` | `[FCM-token]` legacy: `onNewToken(token)` — Firebase's page calls the token flow deprecated, "removed in a future release" |
| App Links | `autoVerify` + `https://<host>/.well-known/assetlinks.json`; API 35+ re-verifies in the background (changes reach devices in up to 7 days), API 34 and lower only at install or update | Same |
| `PendingIntent` | Pass `FLAG_IMMUTABLE` (mandatory from API 31 to choose) | Same |
| Full-screen intents | Auto-granted at target 34+ only to calling and alarm apps | Same |

**FCM facts verified 2026-10-10** (firebase.google.com/docs/cloud-messaging/android/get-started and /receive-messages): the FID flow, the `onRegistered` triggers (after a manual `register()`, when the FID changes, and at startup / routine sync with auto-init on), `register()` when auto-init is disabled, Android 7.0+ with Play services. The **BoM / `firebase-messaging` version and the server field that targets an FID were not on those pages** — read the current BoM from the Firebase release notes and the server targeting from the HTTP v1 reference before writing either as fact; an existing project on tokens is **not flagged** for being on `onNewToken`, and is migrated deliberately with the server owner ([`migration`](../migration/SKILL.md)).

Detect the sender first (FCM, or a vendor SDK that wraps it) and keep it — never add a second sender.

## When to use

- Registering for push, sending the registration id to the server, receiving and tapping a notification
- Notification channels, local reminders, grouping, actions, the denied-permission path
- A link from mail, SMS, web or QR that must open an in-app screen — manifest filters, `assetlinks.json`, verification
- A `PendingIntent` anywhere (notification, widget, alarm)

## When NOT to use

- Mapping a URI to a back stack, restoring, signed-out replay → [`navigation`](../navigation/SKILL.md)
- Camera, location, the generic permission pattern → [`device-features`](../device-features/SKILL.md)
- WorkManager, foreground services, widgets, alarms → [`system-integration`](../system-integration/SKILL.md)
- The sending service and the registration table → the project's `be-*` agent
- Play declarations as policy → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Another stack → `mobile-ios-notifications-and-links`, `mobile-react-native-notifications-and-links`

## Permission — the same lifecycle

The pre-prompt, denied-is-a-working-screen and resume-recheck from [`device-features`](../device-features/SKILL.md) apply.

- **Ask in context** — after the first order is placed, not in `Application.onCreate`. The pre-prompt says what will be sent; only Continue launches `RequestPermission(POST_NOTIFICATIONS)`. At API 32 and below there is nothing to ask; `NotificationManagerCompat.areNotificationsEnabled()` is the one truth at every level and is **rechecked on resume** — the user can switch it off in system settings at any time.
- After two denials the system stops showing the dialog; route to `Settings.ACTION_APP_NOTIFICATION_SETTINGS` (extra `Settings.EXTRA_APP_PACKAGE`) rather than re-asking.
- **Denied still works**: the same information appears in an in-app list; settings shows "Notifications are off" with a button to the system screen.
- Push **must not be required for the app to work**; marketing and transactional messages are separate channels the user can mute independently.

## Channels

```kotlin
fun createChannels(context: Context) {
    val manager = context.getSystemService(NotificationManager::class.java)
    manager.createNotificationChannels(
        listOf(
            NotificationChannel(Channels.ORDERS, context.getString(R.string.channel_orders), NotificationManager.IMPORTANCE_DEFAULT),
            NotificationChannel(Channels.PROMOTIONS, context.getString(R.string.channel_promotions), NotificationManager.IMPORTANCE_LOW),
        )
    )
}

object Channels {
    const val ORDERS = "orders"
    const val PROMOTIONS = "promotions"
}
```

- **One channel per user-meaningful category**, created at app start (idempotent); the id is a constant, the name and description are localized string resources ([`languages`](../languages/SKILL.md)).
- **Importance is the user's after creation** — you cannot raise it by recreating the channel; to change defaults, ship a new channel id. Never `IMPORTANCE_HIGH` for convenience; heads-up is for time-critical events.
- Declare the FCM default channel in the manifest (`com.google.firebase.messaging.default_notification_channel_id`, plus `default_notification_icon` and `default_notification_color`) so a notification-message delivered while the app is in the background lands on a channel you created.

## Registration and the id

```kotlin
class PushService : FirebaseMessagingService() {

    @Inject lateinit var registrations: DeviceRegistrationRepository

    override fun onRegistered(installationId: String) {
        registrations.enqueueUpload(installationId)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val target = PushTarget.from(message.data) ?: return
        notifier.show(target)
    }
}
```

`enqueueUpload` schedules a WorkManager job with a network constraint ([`system-integration`](../system-integration/SKILL.md)) — the callback runs on a short execution window and **never does network I/O itself**. Hilt injection in a service needs `@AndroidEntryPoint`; manual DI reads from the `Application`.

- **Upload every time the callback fires**, as Firebase recommends; the id changes on reinstall, restore and clearing data. Keep it out of logs.
- **Delete the registration server-side on sign-out and account deletion**, so the next user of the device receives nothing.
- With auto-init disabled (a consent-gated app), call `FirebaseMessaging.getInstance().register()` once the user has consented and notifications are enabled.
- Declare the service `android:exported="false"` with the `com.google.firebase.MESSAGING_EVENT` intent filter. Check Play services availability in `onCreate` and `onResume` of the launcher activity.
- Registration, message types and the payload contract detail: [`references/fcm.md`](references/fcm.md).

## Receiving: foreground, tap, cold start

| Moment | What runs | Rule |
|---|---|---|
| Notification message, app in background | The system tray posts it; **no app code runs** | A tap launches the launcher activity with the data in the intent extras |
| Data message (any state), notification message in the foreground | `onMessageReceived` | Build and post the notification yourself, or update state; short window — hand long work to WorkManager |
| User taps | The `PendingIntent` you attached | Activity `onCreate` / `onNewIntent` → validate → route |
| `onDeletedMessages` | FCM dropped messages (> 100 pending, or offline > 1 month) | Do a full sync from the server |

- **A payload decides a destination only after validation.** `PushTarget.from(data)` is one pure function — a closed set of `screen` values and typed ids; anything else opens the start destination and is logged without the payload. Unit-test it with hostile maps.
- **Both entry points**: `onCreate` and `onNewIntent` (a `singleTop` activity) feed the same function ([`navigation`](../navigation/SKILL.md) § Deep links).
- **Signed-out taps**: store the validated target, route to sign-in, replay after.
- **No PII in a payload** — it crosses Google's servers and sits on the lock screen. Send an id and fetch the content after the tap. `setVisibility(VISIBILITY_PRIVATE)` with a `setPublicVersion` for anything sensitive (K20).
- **Local notifications**: `NotificationCompat.Builder` with one notification id per reminder so a reschedule replaces rather than duplicates; timed ones through `AlarmManager` inexact or WorkManager ([`system-integration`](../system-integration/SKILL.md) for the exact-alarm policy).

## `PendingIntent` — immutable and explicit

```kotlin
fun openOrder(context: Context, orderId: String): PendingIntent {
    val intent = Intent(context, MainActivity::class.java)
        .setAction(Actions.OPEN_ORDER)
        .putExtra(Extras.ORDER_ID, orderId)
    return PendingIntent.getActivity(
        context,
        orderId.hashCode(),
        intent,
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )
}
```

- **`FLAG_IMMUTABLE` always**; `FLAG_MUTABLE` only for an API that must fill the intent (inline reply, bubbles), with the reason recorded (K15).
- **An explicit component and an action — never an empty `Intent()`.** A mutable `PendingIntent` over an empty intent lets another app redirect it.
- Distinct request codes, or `FLAG_UPDATE_CURRENT`, for distinct targets — otherwise two notifications share one `PendingIntent` and open the wrong order.
- The activity validates its extras like any untrusted input; an `Intent` carried inside an extra is never launched.

## Full-screen intents and ads

`USE_FULL_SCREEN_INTENT` is auto-granted at target 34+ **only to calling and alarm apps**; others must ask the user and the Play declaration applies ([`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md), L18). Never use it to surface a promotion. Check `NotificationManager.canUseFullScreenIntent()` and fall back to a normal heads-up. A non-calling, non-alarm app that declares it is a major finding.

## Links — App Links first, schemes with caution

```xml
<intent-filter android:autoVerify="true">
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="https" android:host="app.example.com" android:pathPrefix="/orders" />
</intent-filter>
```

| Part | What it is |
|---|---|
| Manifest | `autoVerify="true"` on a `VIEW` + `DEFAULT` + `BROWSABLE` filter with scheme `https` — **narrow host and `pathPrefix`**, never `pathPattern=".*"` |
| Hosted file | `https://<host>/.well-known/assetlinks.json` per unique host: the package name and the **release signing certificate SHA-256** (and the Play App Signing key if enrolled), served over valid HTTPS with no redirect |
| App side | `intent.data` in `onCreate` and `onNewIntent` → the `navigation` parser |

The file's shape, per-variant fingerprints and the `adb` verification commands are in [`references/app-links.md`](references/app-links.md).

- **Prefer verified https links to a custom scheme.** Any app can claim a scheme; a verified link is bound to your domain and signing key. A scheme carries no secret, code or token (F11).
- **Narrow the paths**; exclude `/admin` and `/api`. Every path claimed is a path validated.
- **A link is untrusted input**: scheme, host allow-list, fixed path shape, typed ids — the `navigation` parser. A link parameter never reaches `startActivity`, a `WebView.loadUrl`, a file path or a query.
- **Verification is per signing certificate**: a debug build signed with another key is not verified; list the debug fingerprint in a separate statement only for non-production hosts. `pm get-app-links` is the truth, not the browser's behaviour.
- When a domain is not verified the user can associate it in `Settings.ACTION_APP_OPEN_BY_DEFAULT_SETTINGS` — explain why first. Only one app per device holds a verified domain.
- Opening **out**: `ACTION_VIEW` only on a URL built from a constant host, handling `ActivityNotFoundException` with a visible fallback; `<queries>` narrow, never `QUERY_ALL_PACKAGES` undeclared.

## Procedure

1. Detect the sender (FCM or vendor), the FCM lane (FID or token), the target SDK, existing channels, manifest filters and `PendingIntent` sites.
2. Notifications: channels → pre-prompt → `POST_NOTIFICATIONS` → registration callback → upload via WorkManager → `PushTarget` parser → tap activity.
3. One parser for push data, the `navigation` parser for URIs; both feed one route function.
4. Narrow `autoVerify` filter, publish `assetlinks.json`, verify with `pm get-app-links`.
5. Make every `PendingIntent` immutable and explicit; delete the registration on sign-out.
6. Test ids on the primer, the denied row, the in-app list ([`test-ids`](../test-ids/SKILL.md)); localize channel names and copy ([`languages`](../languages/SKILL.md)).

## Validation (exit gate)

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- [ ] Pre-prompt appears first, then the system dialog once; denying keeps the in-app list and shows the Settings row
- [ ] Tap from killed, background and foreground each opens the right screen once
- [ ] A payload with an unknown `screen` or a malformed id opens the start destination and nothing else
- [ ] `adb shell pm get-app-links <package>` shows `verified` for every host; the `assetlinks.json` URL returns 200, JSON, no redirect
- [ ] `adb shell am start -a android.intent.action.VIEW -d "https://app.example.com/orders/<id>"` opens the order with a back stack
- [ ] Sign out removes the registration server-side
- [ ] Dev-side tests: `PushTarget.from` against valid, malformed and hostile maps; device journeys are `qa-mobile-*`'s

## Handoffs

- URI → keys, restore, signed-out replay → [`navigation`](../navigation/SKILL.md)
- Permission pattern, Settings route → [`device-features`](../device-features/SKILL.md)
- Upload job, widgets, alarms, foreground services → [`system-integration`](../system-integration/SKILL.md)
- Payload and link validation, lock-screen content, `PendingIntent`, exported components → [`mobile-shared-security`](../../../_shared/security/SKILL.md)
- Full-screen intent and exported-component policy → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Token and registration storage → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Push-sending service → the project's `be-*` agent
- Link and push journeys on a device → `qa-mobile-*` (peer)
