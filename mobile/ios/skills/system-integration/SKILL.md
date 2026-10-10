---
name: mobile-ios-system-integration
description: Use when an iOS app reaches outside its own screens — App Intents and App Shortcuts, WidgetKit widgets and controls, Live Activities, BGTaskScheduler, BGContinuedProcessingTask, background URLSession. Triggers "add a widget", "Siri / Shortcuts action", "Live Activity for delivery", "run work in the background", "upload after the app closes". Do NOT use for push setup (`mobile-ios-notifications-and-links`), foreground networking (`-networking`) or SwiftData (`-offline-and-storage`).
---

# iOS — System Integration

The app is not always on screen. Widgets, Siri and Shortcuts, Live Activities and background work let the **system** run a slice of the app on its own schedule — and the system, not the app, decides when. Every surface here shares three rules: **the system budgets it** (refreshes, runtime, updates are allowances, not promises), **it runs outside the app's UI** (a separate process or a cold launch — no singleton state), and **its input is untrusted** (a Shortcut parameter, a background wake and a push-driven update are all data to validate). Rules: CLAUDE.md § Mobile code rules (lifecycle, secrets) and [`mobile-shared-security`](../../../_shared/security/SKILL.md).

## Version lane

| Surface | iOS 17+ (primary) | Later / `[iOS16]` |
|---|---|---|
| App Intents | `AppIntent`, `AppEntity`, `AppShortcutsProvider`, intents in a Swift package | `[iOS16]` App Intents need iOS 16; interactive widgets need 17 |
| Widgets | WidgetKit with `AppIntentConfiguration`; interactive `Button(intent:)` / `Toggle(intent:)` (iOS 17) | Controls in Control Center (iOS 18); widget push updates (iOS 26 — confirm) |
| Live Activities | ActivityKit, push-to-start (iOS 17.2) | Needs iOS 16.1; Dynamic Island on supported iPhones |
| Background | `BGAppRefreshTask`, `BGProcessingTask`, background `URLSession` | `BGContinuedProcessingTask` (iOS 26) |
| `[Swift6]` | Intents and timeline providers are `Sendable`-clean; shared state goes through an `actor` or a value | — |

Facts below are long-standing API shapes from prior knowledge, not re-confirmed against Apple pages this session (plan D23); where a number is a budget, treat it as "small and system-controlled" and measure on a device.

## When to use

- A Home Screen, Lock Screen or StandBy widget; a Control Center control
- An action Siri, Spotlight, Shortcuts or the Action button can run
- A Live Activity for something with a clear start and end (a delivery, a game, a timer)
- Refreshing data while the app is closed; finishing an upload after the user leaves
- A long user-started export that should continue in the background

## When NOT to use

- Registering for push, universal links → `mobile-ios-notifications-and-links`
- Foreground requests, timeouts, retries → [`networking`](../networking/SKILL.md)
- The store the widget reads → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Camera, location, biometrics → [`device-features`](../device-features/SKILL.md)
- Entitlements and background modes as store policy → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Another stack → `mobile-android-system-integration` (widgets, WorkManager)

## Sharing with an extension

A widget, an intent extension and a Live Activity UI are **separate targets and processes**. They share code through a **local Swift package** and data through an **App Group container** (a SwiftData store or a file there) or a shared Keychain access group — never a singleton.

- **The extension reads; the app writes.** Put the data the widget shows in a small, read-optimised snapshot the app refreshes; the extension never opens the full database to render.
- `UserDefaults(suiteName:)` for a group is a Required Reason API (the group-container reason code); declare it in the extension target's `PrivacyInfo.xcprivacy` ([`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)).
- **No token or secret in the group container in clear** — a widget does not need the session; give it the already-fetched, non-sensitive snapshot. What a widget shows is visible on a locked screen: mark sensitive views `.privacySensitive()` and honour `redactionReasons`.

## App Intents and App Shortcuts

```swift
struct ReorderIntent: AppIntent {
    static let title: LocalizedStringResource = "Reorder last order"
    static let authenticationPolicy: IntentAuthenticationPolicy = .requiresLocalDeviceAuthentication

    @Parameter(title: "Order")
    var order: OrderEntity

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let placed = try await OrderService.shared.reorder(order.id)
        return .result(dialog: "Reordered \(placed.reference).")
    }
}

struct AppShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: ReorderIntent(), phrases: ["Reorder in \(.applicationName)"], shortTitle: "Reorder", systemImageName: "arrow.clockwise")
    }
}
```

- An intent is **a small struct that calls the same service the screens call** — no second code path. `perform()` is `async`, bounded, and returns a result the system can speak or show.
- **Parameters are untrusted input.** A Shortcut can pass any value: validate ids and ranges, and fail with a thrown error the system presents, never a crash. `AppEntity` + `EntityQuery` expose app data to the system; expose only what a user would expect Siri to see, and re-check ownership on the server.
- **`authenticationPolicy`** gates an intent behind unlock (`.requiresLocalDeviceAuthentication`) or sign-in; a destructive or money-moving intent also calls `requestConfirmation()` before it acts.
- `openAppWhenRun` only where the action needs the UI; most intents run without launching the app.
- Phrases include the app name token; `AppShortcutsProvider` shortcuts appear in Spotlight and Shortcuts with **no user setup**, so they ship localized ([`languages`](../languages/SKILL.md)). Intents live in a **Swift package shared by the app and the widget extension**, so one definition serves Siri, Shortcuts, widgets and Controls.

## WidgetKit

A widget is a **timeline of pre-rendered entries**; the system shows the entry whose date has arrived, and asks for a new timeline only when it chooses.

```swift
struct OrdersProvider: AppIntentTimelineProvider {
    func placeholder(in context: Context) -> OrdersEntry { .placeholder }

    func snapshot(for configuration: SelectOrdersIntent, in context: Context) async -> OrdersEntry {
        await OrdersSnapshotStore().latest(for: configuration) ?? .placeholder
    }

    func timeline(for configuration: SelectOrdersIntent, in context: Context) async -> Timeline<OrdersEntry> {
        let entry = await OrdersSnapshotStore().latest(for: configuration) ?? .placeholder
        return Timeline(entries: [entry], policy: .after(.now.addingTimeInterval(60 * 60)))
    }
}

struct OrdersWidget: Widget {
    var body: some WidgetConfiguration {
        AppIntentConfiguration(kind: "OrdersWidget", intent: SelectOrdersIntent.self, provider: OrdersProvider()) { entry in
            OrdersWidgetView(entry: entry).containerBackground(.fill.tertiary, for: .widget)
        }
        .configurationDisplayName("Orders")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
```

- **Refresh is budgeted by the system.** `.after(date)` is a hint, not a schedule; a widget gets a limited number of refreshes a day depending on how often the user looks at it, and a timeline reload from the app (`WidgetCenter.shared.reloadTimelines(ofKind:)`) is budgeted too. Never design a widget that must be fresh to be correct; show **when the data is from** if staleness matters.
- **The widget never polls.** Precompute entries for known future moments (a countdown is a view that renders a date, not a timer — `Text(date, style: .timer)`), and let the app call `reloadTimelines` after a user-visible change. Widget push updates, where the SDK offers them, replace polling entirely.
- `getTimeline` may make **one short, timed network call** or read the group snapshot; prefer the snapshot. Long work is killed.
- Widget **memory and runtime are small and unforgiving**: downsample images to the widget's size, no heavy decode. A widget that exceeds its memory shows a blank.
- Interactive widgets: `Button(intent:)` / `Toggle(intent:)` run an App Intent in the extension; the view updates from the new timeline entry, so the intent writes the group snapshot first.
- Deep link from a widget with `.widgetURL(_:)` / `Link` — it arrives at `onOpenURL` and is validated like any link ([`notifications-and-links`](../notifications-and-links/SKILL.md)).
- Every family renders at the largest Dynamic Type size, and the placeholder state exists (`#Preview(as:)` with a timeline).

## Live Activities

A Live Activity is a Lock Screen and Dynamic Island card for **one ongoing event with a start and an end**. ActivityKit starts it; ActivityKit or a push updates it.

```swift
struct DeliveryAttributes: ActivityAttributes {
    struct ContentState: Codable, Hashable {
        var status: DeliveryStatus
        var etaMinutes: Int
    }
    var orderReference: String
}

func startDelivery(reference: String, state: DeliveryAttributes.ContentState) throws -> Activity<DeliveryAttributes> {
    try Activity.request(
        attributes: DeliveryAttributes(orderReference: reference),
        content: .init(state: state, staleDate: .now.addingTimeInterval(30 * 60)),
        pushType: .token
    )
}
```

- `NSSupportsLiveActivities` = `YES` in `Info.plist`; start it **from the foreground** on a user action (push-to-start from iOS 17.2 is the server-driven exception). Check `ActivityAuthorizationInfo().areActivitiesEnabled` — the user can switch Live Activities off, and that path still works (the order screen shows the same status).
- **Guideline 4.5.3 applies**: Apple services are not for spam, phishing or unsolicited messages — a Live Activity is for something the user started and is waiting on, **never a promotion, a re-engagement nudge or a persistent ad**. End it when the event ends (`activity.end(_:dismissalPolicy:)`); one that runs without an event is a rejection and a trust loss.
- **Content is small and public**: `ContentState` and `attributes` are `Codable` and capped at **4 KB** in total; the Lock Screen shows it to anyone holding the phone, so no sensitive data (`.privacySensitive()`, redacted `isLuminanceReduced` states) ([`mobile-shared-security`](../../../_shared/security/SKILL.md)).
- **Updates are budgeted.** Local `activity.update(_:)` works while the app can run; a remote update is an APNs push with `apns-push-type: liveactivity` to the **activity's own push token** (`activity.pushTokenUpdates`, uploaded like a device token — [`references/background-and-activities.md`](references/background-and-activities.md)); high-frequency updates need `NSSupportsLiveActivitiesFrequentUpdates` and still throttle. A `staleDate` makes the UI say "out of date" instead of lying.
- An activity lives at most **8 hours active**; design for it being **ended by the system**. The widget extension draws the UI (`ActivityConfiguration`: Lock Screen, Dynamic Island); `Text(timerInterval:)` for countdowns, never per-second updates.

## Background work — what the system runs when

| Need | API | Allowance |
|---|---|---|
| Refresh a feed for the next open | `BGAppRefreshTaskRequest` | ~30 s, system-chosen time; learns from usage |
| Longer work (sync, index, clean-up) | `BGProcessingTaskRequest` (`requiresNetworkConnectivity`, `requiresExternalPower`) | Minutes, usually overnight and charging |
| A user-started long task that must outlive the screen | `BGContinuedProcessingTaskRequest` (iOS 26) | Runs with system progress UI the user can cancel |
| Upload or download after the user leaves | background `URLSession` | The system does the transfer, wakes the app after |

- **Register at launch, before the app finishes launching** — `BGTaskScheduler.shared.register(forTaskWithIdentifier:using:launchHandler:)` (or the SwiftUI `.backgroundTask(.appRefresh(id))` scene modifier), with every identifier in `BGTaskSchedulerPermittedIdentifiers` and the matching `UIBackgroundModes` (`fetch`, `processing`). Declare **only the modes the app uses** ([`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)).
- A task **reschedules itself** on entry, sets `expirationHandler` to cancel its work and save progress, and **always calls `setTaskCompleted(success:)`** — or the system penalises the next wake.
- **Nothing is guaranteed.** The system skips a task for a low battery, Low Power Mode, a force-quit app or low usage. Background refresh is a head start, never the only path to correct data ([`error-handling`](../error-handling/SKILL.md) — resume revalidates).
- `BGContinuedProcessingTask`: submit **from the foreground on a direct user action**, report real `progress`, stop when cancelled — the replacement for `beginBackgroundTask` hacks on long exports. `beginBackgroundTask` is for **finishing a write** as the app leaves (seconds), not for work.
- **Background `URLSession`** is **delegate-based** (no `async` data calls), uploads from a **file**, and is recreated with the same identifier at launch; the checklist and policies (timeouts, token refresh from [`networking`](../networking/SKILL.md)) are in the reference.
- Test a background task by simulating its launch from the debugger (`_simulateLaunchForTaskWithIdentifier:`), not by waiting.

Detail, entitlement list and per-surface checklists: [`references/background-and-activities.md`](references/background-and-activities.md).

## Procedure

1. Detect the deployment target, existing extensions, App Group id and background modes already declared.
2. Pick the surface by the need: App Intent (an action) → widget (glanceable state) → Live Activity (one live event) → background task (work without the user).
3. Put shared types in a local Swift package; write the app-side snapshot writer before the widget reader.
4. Add each target's entitlements, `Info.plist` keys, privacy manifest entry and test ids.
5. Validate every intent parameter and every background wake as input; end activities and cancel tasks when their purpose ends.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- The widget gallery shows the widget with the placeholder; a data change in the app reloads it; with the app killed the last snapshot still renders and says how old it is.
- An intent run from Shortcuts with a hostile parameter fails with a message, not a crash; a destructive intent asks for confirmation and unlock.
- A Live Activity starts on the action, updates, ends when the event does, and a device with Live Activities off still shows the status in-app.
- A BG task fired from the debugger completes with `setTaskCompleted`; expiring it saves progress.
- A background upload continues after the app is swiped away from the switcher's background (not force-quit) and relaunches the app on completion.
- Dev-side tests: the snapshot store, the timeline policy, intent `perform()` with a fake service, the BG task's work function — all fakes, no extension process.

## Handoffs

- Push registration, universal links, widget and activity deep links → `mobile-ios-notifications-and-links`
- Request policy for background transfers → [`networking`](../networking/SKILL.md)
- The shared store → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Resume revalidation, offline states → [`error-handling`](../error-handling/SKILL.md)
- Entitlements, background modes, 4.5.3, privacy manifest → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Extension signing and targets in the build → [`mobile-shared-release`](../../../_shared/release/SKILL.md)
- Widget and intent journeys on a device → `qa-mobile-ios` (peer)
