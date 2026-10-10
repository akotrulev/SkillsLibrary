---
name: mobile-ios-notifications-and-links
description: Use when an iOS app needs push or local notifications, or opens from a link — APNs registration, UNUserNotificationCenter permission and delegate, notification service extension, universal links (entitlement + apple-app-site-association), URL-scheme caution. Triggers "add push", "tap opens the order", "link opens the app", "AASA". Do NOT use for route structure (`mobile-ios-navigation`), camera or location (`-device-features`), or the server that sends.
---

# iOS — Notifications and Links

Owns how the outside world gets into the app: **push and local notifications** (permission, registration, foreground display, tap, extension) and **links** (universal links, URL schemes). Both deliver **untrusted input that chooses a destination** — a payload or a URL is validated before it routes ([`mobile-shared-security`](../../../_shared/security/SKILL.md), rule K16). Where a validated URL lands is [`navigation`](../navigation/SKILL.md)'s (`onOpenURL` → route); this skill owns everything up to that call.

## Version lane

| Concern | iOS 17+ (primary) | `[iOS16]` |
|---|---|---|
| Permission, delegate | `UNUserNotificationCenter` — `requestAuthorization(options:)`, `notificationSettings()`, async `didReceive` | Same |
| Badge | `setBadgeCount(_:)` (iOS 16+) | Same |
| Registration | `UIApplication.registerForRemoteNotifications()` + a `UIApplicationDelegateAdaptor` | Same |
| Links | `onOpenURL` and `onContinueUserActivity(NSUserActivityTypeBrowsingWeb)` in SwiftUI; `scene(_:continue:)` `[UIKit]` | Same |
| AASA | `components` format (iOS 13+) | Same |
| Extension | `UNNotificationServiceExtension` | Same |
| `[iOS27 SDK]` | `canOpenURL:` deprecated — open and handle failure, do not probe | Same |

Detect the sender first (the project's own backend through APNs directly, or a vendor SDK such as Firebase or OneSignal) and keep it — never add a second sender. Facts here are from long-standing APIs and not re-confirmed against Apple pages this session (plan D23); confirm a header value or key against the installed SDK before relying on it.

## When to use

- Registering for push, storing the device token, receiving and tapping a notification
- Local reminders and scheduled notifications
- Changing or decrypting a push before display (service extension)
- A link from mail, SMS, the web or a QR code that must open an in-app screen
- Setting up `apple-app-site-association` and the app side of it

## When NOT to use

- Routes, typed destinations, restoring a path → [`navigation`](../navigation/SKILL.md)
- Camera, location, biometrics → [`device-features`](../device-features/SKILL.md)
- Widgets, Live Activities, App Intents, background tasks → `mobile-ios-system-integration`
- The sending service, the device-token table → the project's `be-*` agent
- Store declarations (privacy manifest, entitlements as policy) → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Another stack → `mobile-react-native-notifications-and-links`, `mobile-android-notifications-and-links`

## Permission — the same lifecycle

The pre-prompt, the denied-is-a-working-screen rule and the foreground recheck from [`device-features`](../device-features/SKILL.md) apply. Notification-specific:

- **Ask in context** — after the first order is placed, not at launch. The pre-prompt says what will be sent ("Delivery updates for this order"); only Continue triggers the system prompt. Read `notificationSettings().authorizationStatus` and ask only from `.notDetermined`.
- `.provisional` delivers quietly to the notification list without a prompt — a legitimate first step when the value is not yet proven.
- Push **must not be required for the app to work** and must not carry promotions without an in-app opt-in and an opt-out (App Review 4.5.4, `mobile-shared-store-compliance`). Marketing and transactional notifications are separate categories the user can tell apart.
- **Denied still works**: the same information appears in an in-app list; settings shows "Notifications are off" with a button to `UIApplication.openNotificationSettingsURLString` (falls back to `openSettingsURLString`).
- **Time Sensitive** and **Critical** interruption levels need entitlements (Critical needs an Apple approval); do not set `interruptionLevel` above `.active` for convenience.

## Registration and the token

```swift
@MainActor
final class PushRegistrar {
    private let center = UNUserNotificationCenter.current()

    func enable() async throws -> Bool {
        let granted = try await center.requestAuthorization(options: [.alert, .sound, .badge])
        guard granted else { return false }
        UIApplication.shared.registerForRemoteNotifications()
        return true
    }
}

final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken token: Data) {
        let hex = token.map { String(format: "%02x", $0) }.joined()
        Task { await DeviceRegistration.shared.upload(token: hex) }
    }

    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        Logger.push.error("APNs registration failed: \(error.localizedDescription, privacy: .public)")
    }
}
```

Wire the delegate with `@UIApplicationDelegateAdaptor(AppDelegate.self)` in the `App`.

- **Call `registerForRemoteNotifications()` on every launch once authorised** — the token can change (restore, reinstall, OS update); upload only when it differs from the last uploaded value. The registration call is cheap and needs no network from your code.
- The upload is `async` and **never blocks launch or a screen**; offline, retry on the next foreground.
- **Delete the token server-side on sign-out and account deletion**, so the next user of the device gets nothing; call `unregisterForRemoteNotifications()` when the user turns the feature off.
- The **Push Notifications capability** adds the `aps-environment` entitlement (`development` in debug, `production` in release, set by the provisioning profile); a build signed with the wrong environment registers but never receives.
- The server authenticates with a **token-based APNs key (`.p8`)**, not a per-app certificate; the key lives only in the sender's secret store ([`mobile-shared-security`](../../../_shared/security/SKILL.md)). Headers and payload shape: [`references/apns-and-extensions.md`](references/apns-and-extensions.md).
- A simulator on Xcode 14+ / iOS 16+ on Apple silicon can receive a push through `xcrun simctl push booted <bundle-id> payload.json` — handy for tap routing, no APNs involved.

## Receiving: foreground, tap, cold start

The delegate **must be set before the app finishes launching** or a tap that launched the app is lost — assign it in `AppDelegate.application(_:didFinishLaunchingWithOptions:)`.

```swift
final class NotificationRouter: NSObject, UNUserNotificationCenterDelegate {
    private let open: @MainActor (NotificationTarget) -> Void

    init(open: @escaping @MainActor (NotificationTarget) -> Void) { self.open = open }

    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        [.banner, .list]
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        guard let target = NotificationTarget(userInfo: response.notification.request.content.userInfo) else { return }
        await open(target)
    }
}

enum NotificationTarget: Equatable {
    case order(Order.ID)

    init?(userInfo: [AnyHashable: Any]) {
        guard userInfo["screen"] as? String == "order",
              let raw = userInfo["orderId"] as? String,
              let id = Order.ID(raw) else { return nil }
        self = .order(id)
    }
}
```

| Moment | Where | Rule |
|---|---|---|
| Arrives in the foreground | `willPresent` | Nothing shows unless you return options; return the smallest set that suits the screen (suppress when the user is already looking at that order) |
| User taps | `didReceive response` | Read `userInfo`, validate, route; the same parser serves cold start, background and foreground |
| App was killed, tap launched it | `didReceive` is called after launch | Hold the validated target until the root view exists, route once, drop it |
| Silent / data-only (`content-available: 1`) | `application(_:didReceiveRemoteNotification:fetchCompletionHandler:)` | Best-effort: throttled, not delivered after a force-quit; never the only path to correctness |

- **A payload decides a destination only after validation.** A closed set of `screen` values and typed ids (above); anything else opens the home screen and is logged, never `openURL`. `userInfo` is `[AnyHashable: Any]` — parse it in one pure function and unit-test it with hostile shapes.
- **Signed-out taps**: store the validated target, route to sign-in, replay it after — the same replay `navigation` uses for links.
- **No PII in a payload** — it crosses Apple's servers and sits on the lock screen. Send an id and fetch the content after the tap, or have a service extension fetch it ([`references/apns-and-extensions.md`](references/apns-and-extensions.md)); a notification with a sensitive body is rule K20.
- Badge counts come from the server's truth via `setBadgeCount`; clear them on read, not on launch.
- **Local notifications**: `UNMutableNotificationContent` + `UNCalendarNotificationTrigger` / `UNTimeIntervalNotificationTrigger`, one request id per reminder so a reschedule replaces rather than duplicates. The system keeps at most 64 pending local notifications per app — schedule the next few, not a year.
- **Actions** (`UNNotificationCategory` + `UNNotificationAction`) are registered at launch with `setNotificationCategories`; a destructive action carries `.destructive`, and an action's handler receives untrusted input like a tap.

## Links — universal links first, schemes with caution

| Part | What it is |
|---|---|
| Entitlement | `com.apple.developer.associated-domains` = `applinks:example.com` (add `?mode=developer` for a debug build so the device bypasses Apple's cache) |
| Hosted file | `https://example.com/.well-known/apple-app-site-association` — JSON, **no file extension**, `application/json`, served over valid HTTPS with **no redirect**, no authentication |
| App side | `onOpenURL` receives the URL for both a universal link and a custom scheme; `onContinueUserActivity(NSUserActivityTypeBrowsingWeb)` receives the web URL on some entry paths |

The AASA `components` shape, path exclusions, caching and testing are in [`references/apns-and-extensions.md`](references/apns-and-extensions.md) § Universal links.

- **Prefer verified https links to a custom scheme.** Any app can claim a URL scheme; a universal link is bound to your domain. Keep a scheme only for development, an internal tool, or an `ASWebAuthenticationSession` callback that has no https option.
- **Narrow the paths** in AASA (`/orders/*`), not `/*`. Every path claimed is a path validated; exclude `/admin/*`, `/api/*`, and anything the website must keep.
- **A link is untrusted input.** `DeepLink(url:)` — scheme, host allow-list, a fixed path shape, typed ids — is one pure function, unit-tested; a link parameter never reaches `openURL`, a `WKWebView` request, a file path or a query ([`navigation`](../navigation/SKILL.md) § URL → route).
- A universal link does not open the app when the user **types the URL** into Safari or taps a link to the same domain from that domain's own page; a long-press can choose the browser. Test through Notes, Messages or `xcrun simctl openurl`, not a Safari address bar.
- Apple's CDN fetches the AASA, so a change lags — a device re-reads it at install or update. Never debug by editing the file in production repeatedly.
- Opening **out**: `Link` / `openURL` only on a URL the app built from a constant host; handle the failure result. Do not probe with `canOpenURL:` (deprecated at the iOS 27 SDK); keep `LSApplicationQueriesSchemes` empty without a recorded reason.
- Handoff, Spotlight and Siri entry points are `NSUserActivity` / App Intents — see `mobile-ios-system-integration`.

## Procedure

1. Detect the sender, the deployment target, any existing delegate, entitlements and URL types.
2. Notifications: capability → pre-prompt → authorization → `registerForRemoteNotifications` → upload token → delegate set at launch → `NotificationTarget` parser.
3. Write one parser for payload data and one for link URLs; both feed the same route function.
4. Add `applinks:` entitlement, publish AASA with narrow `components`, keep the scheme only where justified.
5. Delete the token on sign-out; re-upload when it changes.
6. Add test ids on the primer, the denied row and the in-app notification list ([`test-ids`](../test-ids/SKILL.md)); localize notification copy ([`languages`](../languages/SKILL.md)).

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- A device build with the right `aps-environment`: the pre-prompt appears first, then the system prompt once; denying keeps the in-app list and shows the Settings row.
- Tap from killed, background and foreground: each lands on the right screen once.
- A payload with an unknown `screen` or a non-UUID id lands on home with nothing opened; a hostile link (`https://evil.example/orders/x`, `//` paths) is ignored.
- `xcrun simctl openurl booted "https://example.com/orders/<id>"` opens the order screen on a build with the entitlement; the AASA URL returns 200, `application/json`, no redirect.
- Sign out: the token is gone from the backend for the device.
- Dev-side tests: `NotificationTarget(userInfo:)` and `DeepLink(url:)` against valid, malformed and hostile inputs; device journeys are `qa-mobile-<stack>`'s (peer).

## Handoffs

- URL → route, protected routes, restoration → [`navigation`](../navigation/SKILL.md)
- Permission pattern, Settings route → [`device-features`](../device-features/SKILL.md)
- Payload and link validation, lock-screen content, secrets → [`mobile-shared-security`](../../../_shared/security/SKILL.md)
- Guideline 4.5.x, entitlements, background modes as policy → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Live Activity push, widget refresh → `mobile-ios-system-integration`
- Token storage → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Push-sending service → the project's `be-*` agent
- Link and push journeys on a device → `qa-mobile-<stack>` (peer)
