# FCM on Android — registration, message types, payload contract

Verified 2026-10-10 against firebase.google.com/docs/cloud-messaging/android/get-started and /receive-messages. Items marked **not verified** were not on those pages.

## Registration

| Step | Detail |
|---|---|
| Manifest | `<meta-data android:name="firebase_messaging_installation_id_enabled" android:value="true" />` inside `<application>` |
| Callback | `override fun onRegistered(installationId: String)` on the `FirebaseMessagingService`; runs after a manual `register()`, when the FID changes, and at startup / routine sync with auto-init enabled |
| Manual | Auto-init off (`firebase_messaging_auto_init_enabled` and `firebase_analytics_collection_enabled` both `false`) → call `FirebaseMessaging.getInstance().register()` at startup or after consent; re-enable with `Firebase.messaging.isAutoInitEnabled = true` |
| Server | Send the FID to the app server on every callback. **Not verified:** the HTTP v1 field that targets an FID — read the FCM HTTP v1 reference with the server owner |
| Legacy `[FCM-token]` | `onNewToken(token)` and the `token` property; Firebase calls the flow deprecated. A project on it keeps working; moving is a coordinated client + server change, never client-only |
| Library | Android 7.0+ with Google Play services; `firebase-messaging` ≥ 23.0.6 declares `POST_NOTIFICATIONS`. **Not verified:** the current BoM — read the Firebase Android release notes |

## Message types and what runs

| Message | App in foreground | App in background / killed |
|---|---|---|
| Notification (`notification` block) | `onMessageReceived` | System tray posts it; **no app code**; a tap opens the launcher activity |
| Data (`data` only) | `onMessageReceived` | `onMessageReceived` (subject to Doze / app-standby and the sender's priority) |
| Both | `onMessageReceived` | Tray notification; the data arrives as launcher-activity intent extras |

- Prefer **data messages** when the app must validate, localize or suppress before showing; prefer **notification messages** for simple alerts that need no code. Never rely on a data message alone for correctness — delivery is best-effort.
- `onMessageReceived` has a short execution window — **do not do network or disk-heavy work in it**; enqueue WorkManager.
- `onDeletedMessages` fires when FCM dropped messages (more than 100 pending when the device connects, or no connection for over a month); respond with a full sync.
- **Not verified:** priority semantics and message TTL — read the Firebase "message priority" and "lifetime" pages when the feature depends on them.

## The payload contract (agree it with the server owner)

```json
{ "data": { "screen": "order", "orderId": "3f2a…" } }
```

- A closed set of `screen` values, each with typed ids; the client ignores the rest.
- No personal data, no secrets, no URL the client will open.
- The client treats the map as `Map<String, String>` — FCM data values are strings; parse and validate every field.

```kotlin
sealed interface PushTarget {
    data class Order(val id: OrderId) : PushTarget

    companion object {
        fun from(data: Map<String, String>): PushTarget? = when (data["screen"]) {
            "order" -> data["orderId"]?.let(OrderId::parseOrNull)?.let(::Order)
            else -> null
        }
    }
}
```
