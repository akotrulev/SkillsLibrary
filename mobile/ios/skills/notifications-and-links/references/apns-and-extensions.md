# APNs, the service extension and the AASA file

Long-standing shapes from prior knowledge, not re-fetched this session (plan D23). Confirm a header value or key against Apple's current documentation before depending on an unusual one.

## What the sender sends

| Item | Value |
|---|---|
| Endpoint | `https://api.push.apple.com/3/device/<token>` (production) · `https://api.sandbox.push.apple.com/3/device/<token>` (development) — HTTP/2 only |
| Auth | Token-based: a JWT signed with the `.p8` key (ES256), `Authorization: bearer <jwt>`; refresh the JWT between 20 and 60 minutes old |
| `apns-topic` | The bundle id; `<bundle id>.push-type.liveactivity` for a Live Activity |
| `apns-push-type` | `alert` · `background` · `liveactivity` · `voip` (needs a declared reason — avoid) · `location` · `complication` · `fileprovider` · `mdm` |
| `apns-priority` | `10` immediately (alerts) · `5` power-considerate (`background` pushes must be 5) |
| `apns-expiration` | Unix time after which APNs stops retrying; `0` = deliver once, do not store |
| `apns-collapse-id` | Replaces a pending notification with the same id — use for "order status" updates |

The device token is **per app, per device, per environment** — a development-signed build produces a sandbox token that the production endpoint rejects (`BadDeviceToken`). A `410 Unregistered` response means delete the token.

## Payload shapes

An alert with a localized body and a targetable destination:

```json
{
  "aps": {
    "alert": { "title-loc-key": "order.shipped.title", "loc-key": "order.shipped.body", "loc-args": ["4821"] },
    "sound": "default",
    "thread-id": "order-4821",
    "mutable-content": 1
  },
  "screen": "order",
  "orderId": "3f2b9c7e-5d1a-4c7e-9b60-0a1d2e3f4a5b"
}
```

- `loc-key` / `title-loc-key` resolve against the **app's** String Catalog on the device, so the notification follows the user's language ([`languages`](../../languages/SKILL.md)); the server sends keys and arguments, not translated sentences.
- `thread-id` groups notifications in the list; `collapse-id` is a header, not a payload key.
- `mutable-content: 1` hands the notification to the service extension; `content-available: 1` with no `alert` is a silent push.
- The whole payload is limited to **4 KB** (5 KB for VoIP). Custom keys sit beside `aps`, not inside it.
- Custom keys are **untrusted on arrival** — the closed-set parser in `SKILL.md` § Receiving validates them.

## Notification service extension

Runs for ~30 seconds when `mutable-content` is `1`; its job is to change the content before display — fetch an image, decrypt an end-to-end-encrypted body, or look up a title by id.

```swift
final class NotificationService: UNNotificationServiceExtension {
    private var contentHandler: ((UNNotificationContent) -> Void)?
    private var bestAttempt: UNMutableNotificationContent?

    override func didReceive(_ request: UNNotificationRequest, withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void) {
        self.contentHandler = contentHandler
        bestAttempt = request.content.mutableCopy() as? UNMutableNotificationContent
        guard let bestAttempt else { return contentHandler(request.content) }
        Task {
            if let body = await DecryptedBody(userInfo: bestAttempt.userInfo) { bestAttempt.body = body }
            contentHandler(bestAttempt)
        }
    }

    override func serviceExtensionTimeWillExpire() {
        if let contentHandler, let bestAttempt { contentHandler(bestAttempt) }
    }
}
```

- **Always call the handler** — in the normal path and in `serviceExtensionTimeWillExpire` with the best content so far. An extension that never answers shows the original payload, or nothing.
- The extension is a **separate process with a tight memory cap**: no app UI code, a small image download only, no Core Data stack. Share data with the app through an **App Group** container or a shared Keychain access group, never through a global.
- A decryption key lives in the **Keychain access group** both targets share, with `AfterFirstUnlockThisDeviceOnly` — a push can arrive while the device is locked ([`offline-and-storage` `references/keychain.md`](../../offline-and-storage/references/keychain.md)). A notification that cannot be decrypted shows a generic body ("You have a new message"), never the ciphertext.
- Attachments: `UNNotificationAttachment` from a file downloaded into the extension's temporary directory; check the type and size before attaching.
- An extension that touches a Required Reason API needs its own `PrivacyInfo.xcprivacy` entry ([`mobile-<stack>:store-compliance`](../../../../_shared/store-compliance/SKILL.md)).

## Universal links — the AASA file

```json
{
  "applinks": {
    "details": [
      {
        "appIDs": ["ABCDE12345.com.example.app"],
        "components": [
          { "/": "/orders/*", "comment": "order detail" },
          { "/": "/admin/*", "exclude": true }
        ]
      }
    ]
  }
}
```

- The `appID` is `<Team ID>.<bundle id>`; one `details` entry per app, several `appIDs` for one family.
- `components` match in order; the first match wins, so an `exclude` goes before the broad rule it carves out. `/`, `?` (query) and `#` (fragment) are the match keys; `*` and `?` wildcards apply inside a value.
- Serve it from `https://<host>/.well-known/apple-app-site-association` with `Content-Type: application/json`, no extension, **no redirect** (including `http` → `https` and `www` → apex), a valid certificate, and no login — Apple's CDN fetches it, not the device.
- **Caching**: the CDN and the device cache it; a change reaches a device at the next install or update. `?mode=developer` on the entitlement makes a debug build on a developer-mode device fetch the file directly from the host.
- Every host in `applinks:` is a host the AASA must serve. A subdomain needs its own entitlement entry (`applinks:*.example.com` covers subdomains but not the apex).
- Verify: `curl -sI https://example.com/.well-known/apple-app-site-association` (status, type, no `Location`); on a device, Settings → Developer → Universal Links → Diagnostics (Xcode 14+ developer mode) tests a URL; the simulator takes `xcrun simctl openurl booted "<url>"`.
- A link that **should not** open the app (a marketing page, a password-reset page that must show in the browser) is excluded in AASA rather than ignored in code.

## URL schemes

`CFBundleURLTypes` in `Info.plist` claims `myapp://`. Any app can claim the same scheme, and nothing proves who sent the URL — so a scheme URL carries **no secret and triggers no destructive action**; treat it exactly as `DeepLink(url:)` treats a universal link, and never accept an auth code or token through one without PKCE and `state` validation ([`mobile-<stack>:security`](../../../../_shared/security/SKILL.md)). Prefer `ASWebAuthenticationSession` for an OAuth redirect; its https callback form (where the OS supports it) is bound to a domain the way a universal link is.
