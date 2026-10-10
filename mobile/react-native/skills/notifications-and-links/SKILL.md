---
name: mobile-react-native-notifications-and-links
description: Use when an Expo SDK 57 app needs push or local notifications, or opens from a link — expo-notifications (permission, Android 13+ runtime prompt, channels, Expo / APNs / FCM tokens, tap routing), universal links and Android App Links through Expo Router. Triggers "add push", "tap opens the order", "link opens the app", "assetlinks". Do NOT use for hardware permissions (`-device-features`), route structure (`-navigation`), or the server that sends.
---

# React Native — Notifications and Links

Owns how the outside world gets into the app: **push and local notifications** (permission, channel, token, foreground display, tap) and **links** (universal links, Android App Links, custom schemes). Both deliver **untrusted input that chooses a destination** — a payload or a URL is validated before it routes ([`mobile-shared-security`](../../../_shared/security/SKILL.md)). Route structure and typed `href`s are [`navigation`](../navigation/SKILL.md)'s.

## Version lane

| Concern | Primary (SDK 57) | Notes |
|---|---|---|
| Library | `expo-notifications` (config plugin: `icon`, `color`, `defaultChannel`, `sounds`, `enableBackgroundRemoteNotifications`) | Plugin options are build-time — a change needs a new native build |
| Expo Go | Local notifications work; **remote push does not on Android** (from SDK 53) | Use a development build |
| Foreground handler | `setNotificationHandler` returns `shouldShowBanner`, `shouldShowList`, `shouldPlaySound`, `shouldSetBadge` | `shouldShowAlert` is deprecated; **with no handler, nothing shows**; the handler has **3 s** to answer |
| Tokens | `getExpoPushTokenAsync({ projectId })` (Expo Push Service) or `getDevicePushTokenAsync()` (raw APNs / FCM) | Pass `projectId` explicitly; the Expo call needs the network |
| Links | Expo Router handles the URL; `scheme`, `ios.associatedDomains`, Android `intentFilters` with `autoVerify` | |
| `[SDK58]` | No notification change known | Router core is reworked — re-read the linking page |
| Floor SDK 54 | Same API | Same recipes |

Detect whether the project sends through Expo Push or straight APNs / FCM; keep it — do not add a second sender.

## When to use

- Registering for push, storing the token, receiving and tapping a notification
- Local reminders and scheduled notifications
- A link from mail, SMS, the web or a QR code that must open an in-app screen
- Setting up `apple-app-site-association` / `assetlinks.json` and the app side of both

## When NOT to use

- Camera, location, biometrics → [`device-features`](../device-features/SKILL.md)
- The route tree, protected routes, typed `href` → [`navigation`](../navigation/SKILL.md)
- Sending from a backend → the project's `be-*` agent; this skill owns the token's lifecycle on the device and the receive side
- Store declarations → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)

## Notification permission — the same lifecycle, plus Android 13+

The pre-prompt, the four states and the denied screen from [`device-features`](../device-features/SKILL.md#the-permission-lifecycle-hard-rules) apply. Notification-specific traps:

- **Android 13 (API 33) and later require the `POST_NOTIFICATIONS` runtime permission**, and the system prompt **does not appear until at least one notification channel exists**. Create the channel first, then request.
- **`setNotificationChannelAsync` must run before `getExpoPushTokenAsync` / `getDevicePushTokenAsync`** or no token is returned on Android.
- On iOS read `permissions.ios?.status`, not the root `status`; provisional authorization delivers quietly without a prompt and is a legitimate first step.
- **Ask in context**: after the first order is placed, not at launch. The pre-prompt says what will be sent ("Delivery updates for this order"). A granted-then-revoked permission is re-read on foreground.
- **The denied path works**: the app still shows the same information in an in-app list; settings has a row "Notifications are off — open Settings" (`Linking.openSettings()`).

```ts
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

export async function enableOrderUpdates(projectId: string): Promise<string | null> {
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('orders', {
      name: 'Order updates',
      importance: Notifications.AndroidImportance.DEFAULT,
    });
  }
  const current = await Notifications.getPermissionsAsync();
  const granted = current.granted || (current.canAskAgain && (await Notifications.requestPermissionsAsync()).granted);
  if (!granted) return null;
  const { data } = await Notifications.getExpoPushTokenAsync({ projectId });
  return data;
}
```

- `getExpoPushTokenAsync` calls Expo's servers and **fails offline** — catch it, keep the feature on, and retry on the next foreground or reconnect; never block the screen on it.
- **Channels are the user's controls on Android**: one per purpose (`orders`, `promotions`, `security`), a human-readable `name`, a sensible `importance`. A channel's settings cannot be changed by the app after creation — a wrong importance means a new channel id.
- **Tokens rotate.** Subscribe with `addPushTokenListener` and re-register; send the token to the backend with the device id, upsert, and **delete it on sign-out** and account deletion so the next user of the device gets nothing.
- Push on iOS needs a physical device or a simulator on Xcode 14+ / iOS 16+; Android needs Google Play services and an FCM credential uploaded to EAS.

## Receiving: foreground, tap, cold start

```ts
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});
```

| Moment | API | Rule |
|---|---|---|
| Arrives in the foreground | the handler above; `addNotificationReceivedListener` for in-app side effects | Set the handler **once**, at module scope of the root layout, before any notification can land |
| User taps | `addNotificationResponseReceivedListener` | Read `response.notification.request.content.data`, validate, then route |
| App was killed, tap launched it | `useLastNotificationResponse()` — `undefined` while unknown, `null` if none | Route once, then `clearLastNotificationResponseAsync()` so a re-render does not navigate again |
| Silent / data-only | `expo-task-manager` task via `Notifications.registerTaskAsync`; iOS `_contentAvailable: true` and `enableBackgroundRemoteNotifications` | Define the task in module scope of an early-loaded file; payload carries `data` only; best-effort |

**A payload decides a destination only after validation.** Parse `data` with a Zod schema that allows a closed set of `screen` values and typed ids; route with a typed `href`; an unknown shape goes to the home screen and is logged, never to `Linking.openURL`:

```ts
const target = z.object({ screen: z.enum(['order']), orderId: z.string().uuid() });

function routeFromNotification(data: unknown) {
  const parsed = target.safeParse(data);
  if (!parsed.success) return router.replace('/');
  router.push({ pathname: '/orders/[orderId]', params: { orderId: parsed.data.orderId } });
}
```

- **Signed-out taps**: stash the validated target, route to sign-in, resume after — the `Stack.Protected` redirect in [`navigation`](../navigation/SKILL.md) carries the intent.
- No PII in a payload (it passes through APNs / FCM); send an id and fetch the content after the tap.
- Local notifications: `scheduleNotificationAsync` with a `trigger`. Exact-time delivery on Android 12+ needs `SCHEDULE_EXACT_ALARM`, which is **denied by default since Android 13** — give the denied path (an inexact reminder), and prefer inexact unless the product is an alarm or calendar ([`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)).
- Badge counts come from the server's truth, set with `setBadgeCountAsync`; clear on read.

## Links — universal links, App Links, schemes

Expo Router turns a URL into a route: `https://example.com/orders/42` opens `app/orders/[orderId].tsx` when the app owns that host and path. The three parts:

| Part | iOS | Android |
|---|---|---|
| App config | `"ios": { "associatedDomains": ["applinks:example.com"] }` | `"android": { "intentFilters": [{ "action": "VIEW", "autoVerify": true, "data": [{ "scheme": "https", "host": "example.com", "pathPrefix": "/orders" }], "category": ["BROWSABLE", "DEFAULT"] }] }` |
| Hosted file | `https://example.com/.well-known/apple-app-site-association` — JSON, no extension, `application/json`, no redirect | `https://example.com/.well-known/assetlinks.json` — package name and the **signing-certificate SHA-256** (the Play app-signing key for store builds) |
| Fallback | Custom `scheme` for dev and internal links only | Same |

- **Prefer verified https links to a custom scheme.** Any app can claim a custom scheme; a verified link is bound to your domain. Keep a `scheme` for development builds and the OAuth redirect.
- Narrow the paths: `pathPrefix` or an explicit list, not `/`. Every path you claim is a path you must validate.
- **A link is untrusted input.** Route params are parsed with a schema at the screen ([`navigation`](../navigation/SKILL.md) F6); the host and path are allow-listed; **a link parameter never reaches `Linking.openURL`, a WebView `source`, a file path or a query** ([`mobile-shared-security`](../../../_shared/security/SKILL.md)).
- `+native-intent.tsx` rewrites an incoming URL before routing — the place to map a legacy or marketing path to a real route, and to drop what you do not recognise.
- A link that needs sign-in: route into the protected layout and let the redirect resume it; never open a screen's data before the session is known.
- Opening **out**: `Linking.openURL` only on a string the app built from a constant host; `canOpenURL` on iOS needs `LSApplicationQueriesSchemes` and is deprecated at the iOS 27 SDK — try `openURL` and handle the rejection.
- Android App Links verification depends on a release-signed build matching `assetlinks.json`; a debug build is **not** verified — test with the development client plus `adb shell pm get-app-links <package>` and `adb shell am start -a android.intent.action.VIEW -d "<url>"`; iOS with `xcrun simctl openurl booted "<url>"`.
- Deferred deep links (install first, route after) are a third-party concern — do not hand-roll one.

## Procedure

1. Detect the SDK, the sender (Expo Push / direct APNs / FCM), the existing handler and the `scheme` / domains already in `app.json`.
2. Notifications: create channels → pre-prompt → permission → token (with `projectId`) → send to the backend → listeners.
3. Write one validator for payload data and one for link params; both route through typed `href`.
4. Configure `associatedDomains`, `intentFilters` with `autoVerify`, and publish both association files; narrow the paths.
5. Remove the token on sign-out; subscribe to token rotation.
6. Add test ids on the primer, the denied row and the in-app notification list ([`test-ids`](../test-ids/SKILL.md)).

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Android 13+ device: the permission prompt appears only after the channel exists and only after the pre-prompt.
- Deny notifications: the in-app list still shows the update; the settings row opens Settings.
- Tap from killed, background and foreground: each lands on the right screen once.
- A payload with an unknown `screen` or a non-UUID id lands on home, with nothing opened.
- `xcrun simctl openurl booted "https://example.com/orders/<id>"` and the `adb` command open the order screen on a release-signed build.
- Sign out: the token no longer appears on the backend for the device.

## Handoffs

- Hardware permission pattern, location, camera → [`device-features`](../device-features/SKILL.md)
- Routes, protected layouts, typed `href`, `+native-intent` placement → [`navigation`](../navigation/SKILL.md)
- Payload / link validation rules, allow-lists, WebView → [`mobile-shared-security`](../../../_shared/security/SKILL.md)
- Exact alarms, notification disclosures, Data safety → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Token storage on the device → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Push-sending service, device-token table → the project's `be-*` agent
- Link and push journeys on a device → `qa-mobile-typescript` (peer)
