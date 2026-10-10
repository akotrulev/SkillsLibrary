# Background work, Live Activities and extension setup

Long-standing shapes from prior knowledge, not re-fetched this session (plan D23). Budgets are system-controlled and change between OS releases — measure on a device and read the installed SDK's documentation before relying on a number.

## Targets, entitlements and keys

| Need | Where | Key |
|---|---|---|
| Share data with an extension | App + extension targets | `com.apple.security.application-groups` = `group.<bundle id>`; one container for both |
| Share a secret with an extension | App + extension targets | Keychain access group (`keychain-access-groups`) — see [`offline-and-storage` `references/keychain.md`](../../offline-and-storage/references/keychain.md) |
| Live Activities | App `Info.plist` | `NSSupportsLiveActivities` = `YES`; `NSSupportsLiveActivitiesFrequentUpdates` = `YES` only for a justified high-rate activity |
| BG tasks | App `Info.plist` | `BGTaskSchedulerPermittedIdentifiers` (array; a wildcard suffix for `BGContinuedProcessingTask`) and `UIBackgroundModes` (`fetch`, `processing`) |
| Push-updated activity | Push capability | `aps-environment` (see `notifications-and-links`) |
| Widget / intent extension | Its own target | Its own `Info.plist`, `PrivacyInfo.xcprivacy` entries and bundle id `<app bundle id>.<name>` |

A background mode that is declared but unused is a review question; one that is used but undeclared never runs.

## Live Activity push updates

```swift
Task {
    for await tokenData in activity.pushTokenUpdates {
        let token = tokenData.map { String(format: "%02x", $0) }.joined()
        await ActivityRegistration.shared.upload(orderReference: activity.attributes.orderReference, token: token)
    }
}
```

The server updates the activity with an APNs request whose headers are `apns-push-type: liveactivity`, `apns-topic: <bundle id>.push-type.liveactivity` and a priority (`10` immediate but budgeted, `5` for low-urgency updates):

```json
{
  "aps": {
    "timestamp": 1760000000,
    "event": "update",
    "content-state": { "status": "outForDelivery", "etaMinutes": 12 },
    "stale-date": 1760001800
  }
}
```

- `event` is `update` or `end`; a `dismissal-date` on `end` removes the card at a chosen time.
- `content-state` must decode into `ContentState` exactly — a field rename in the app needs a server change and a version-tolerant `Codable` (optional new fields) or an old activity stops updating.
- The activity token is **per activity**, rotates, and is deleted server-side when the activity ends (`activityUpdates` / `activityStateUpdates` tell the app).
- **Push-to-start** (iOS 17.2): `Activity<…>.pushToStartTokenUpdates` yields a token the server uses to *start* an activity with no foreground app — only for an event the user already asked for (a delivery they ordered). Never a way to start an unsolicited activity (guideline 4.5.3).
- Update frequency is budgeted per app; a server sending several updates a minute for a slow event is throttled and wastes the user's trust. Send on state change, not on a timer.

## Background task skeleton

```swift
@main
struct ShopApp: App {
    var body: some Scene {
        WindowGroup { RootView() }
            .backgroundTask(.appRefresh("com.example.app.refresh")) {
                await scheduleNextRefresh()
                await FeedRefresher().refresh()
            }
    }
}

func scheduleNextRefresh() async {
    let request = BGAppRefreshTaskRequest(identifier: "com.example.app.refresh")
    request.earliestBeginDate = .now.addingTimeInterval(4 * 60 * 60)
    do { try BGTaskScheduler.shared.submit(request) }
    catch { Logger.background.error("refresh not scheduled: \(error.localizedDescription, privacy: .public)") }
}
```

- In the SwiftUI modifier the system cancels the task's `Task` at expiry — write the work as cooperative and cancellable, checking `Task.isCancelled` and saving progress. The UIKit form uses `expirationHandler` and an explicit `setTaskCompleted(success:)`.
- `earliestBeginDate` is a floor, not a time; submit again on every foreground and every run. An app the user has not opened for days is deprioritised.
- `BGProcessingTaskRequest`: set `requiresNetworkConnectivity` and `requiresExternalPower` for heavy jobs; the system runs them when it suits, commonly overnight.
- **Continued processing** (`BGContinuedProcessingTaskRequest(identifier:title:subtitle:)`, iOS 26): submitted on a user gesture; the system shows progress UI; the task reports `task.progress` and `updateTitle`, and ends when work ends or the user cancels. Its submission strategy chooses between failing and queueing when resources are short. Treat its API as the least settled in this skill and read the installed SDK before writing.

## Background URLSession checklist

1. One `URLSessionConfiguration.background(withIdentifier:)` per purpose, created **at launch** with the same identifier every time.
2. `sessionSendsLaunchEvents = true`; `isDiscretionary = true` for non-urgent work; `waitsForConnectivity` for transfers that should hold until a network exists.
3. A delegate class (`URLSessionDownloadDelegate` / `URLSessionTaskDelegate`) — **no async/await data calls and no completion handlers**; uploads are `uploadTask(with:fromFile:)`, a file written first.
4. A download's temporary file is moved out of `didFinishDownloadingTo` before the method returns.
5. Call the system completion handler from `urlSessionDidFinishEvents(forBackgroundURLSession:)` on the main actor.
6. The auth header is fixed at task creation — a token expiring mid-transfer needs a refresh strategy on the server side (pre-signed upload URLs avoid it).

## Extension memory and runtime

| Surface | Practical limits to design for |
|---|---|
| Widget | Small memory ceiling; timeline generation is time-limited; no long network |
| Notification service extension | ~30 s, then `serviceExtensionTimeWillExpire`; tight memory |
| Live Activity UI | Rendered by the widget extension; no network inside the view |
| App Intent in an extension | Short; long work belongs in the app via `openAppWhenRun` or a background session |

An extension is a separate process: a crash there does not crash the app but it blanks the surface. Log with `os.Logger` under the extension's own subsystem and check Console on a device.
