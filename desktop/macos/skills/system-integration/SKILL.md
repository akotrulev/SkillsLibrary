---
name: system-integration
description: Use when a Mac app joins the system (App Intents, widgets, notifications, URL schemes, Services, drag and drop). Triggers "add a Shortcuts action". Not for helpers (background-and-helpers).
disable-model-invocation: true
---

# macOS — System Integration

How the app shows up outside its windows and how the system reaches in: **App Intents** (Spotlight, Shortcuts, Siri, widgets, controls), widgets, notifications, URLs routed to the right window, the Services menu, the pasteboard and drag and drop. Everything that arrives from outside — a URL, an intent parameter, a dropped file, a pasteboard item, a notification payload — is **untrusted input**, validated before it routes. Audit rows are section J of `desktop-macos:standards-audit`.

## Version lane

| Concern | Primary | Notes |
|---|---|---|
| App Intents, `AppShortcutsProvider` | macOS 13+ (App Intents); entities and Spotlight index macOS 14+ | WWDC26: entity schemas feed the Spotlight semantic index; View Annotations map views to entities; `AppIntentsTesting` tests adoption without UI automation |
| 27 SDK `@AppEntity(schema:)` | A schema entity adopted before 27 may stop compiling (new required properties) | AppEntity size limit 10 MB |
| Controls (Control Center, menu bar) | Tahoe (macOS 26) brought the Controls API to the Mac | The exact availability version is **not verified**; check before targeting |
| WidgetKit on Mac | macOS 11+; interactive widgets with App Intents macOS 14+ | — |
| Notifications | `UNUserNotificationCenter` (10.14) | — |
| URLs | `CFBundleURLTypes`, `.onOpenURL`, `.handlesExternalEvents` (11) | — |
| Drag and drop, pasteboard | `Transferable`, `.copyable`, `.onPasteCommand`; 27 SDK `List`: per-row `dropDestination`, `.reorderable()`, `.reorderContainer(for:)` | AppKit: `NSFilePromiseReceiver.receivePromisedFiles…` **throws if called outside the drag callbacks** on 27 |
| Services menu | Part of the standard app menu | → `menus-and-commands` |

Detect first: the deployment target, SwiftUI vs AppKit, and which of these the app already has. **Add the smallest surface the product needs**; every intent is public API the user scripts against.

## App Intents

One intent per user-facing action, a small entity per noun, and the **same model call the UI makes** — an intent never owns logic.

```swift
struct OpenOrderIntent: OpenIntent {
    static let title: LocalizedStringResource = "Open Order"
    static let openAppWhenRun = true

    @Parameter(title: "Order") var target: OrderEntity
    @Dependency var router: Router

    func perform() async throws -> some IntentResult {
        try await router.open(orderID: target.id)
        return .result()
    }
}

struct OrderEntity: AppEntity, Identifiable {
    static let typeDisplayRepresentation: TypeDisplayRepresentation = "Order"
    static let defaultQuery = OrderQuery()

    let id: UUID
    @Property(title: "Title") var title: String

    var displayRepresentation: DisplayRepresentation { DisplayRepresentation(title: "\(title)") }
}

struct OrdersShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: OpenOrderIntent(), phrases: ["Open order in \(.applicationName)"], shortTitle: "Open Order", systemImageName: "doc.text")
    }
}
```

- Register dependencies once at launch (`AppDependencyManager.shared.add`) from the app-wide model, never a singleton read.
- **Validate parameters** like request input: an id that no longer exists throws a user-readable error (`LocalizedError`), never a crash; text parameters are length-bounded.
- Keep the entity small (under the 10 MB limit by a wide margin): identifiers and display fields, loaded fully by the query on demand. Entity queries return **current** data after a sync, not a stale copy.
- Opening the app from an intent sets `openAppWhenRun`; an intent that mutates data without opening the app runs in the background process, so it reads and writes through the shared store (`offline-and-storage`, an app group) and never through window state.
- A schema entity on the 27 SDK may need new properties; build with both SDKs when the lane is "supported".
- Tests: `AppIntentsTesting` where available, else call `perform()` with fakes (`unit-testing`); no UI automation needed.

## Widgets and controls

A widget is a **separate extension target** with its own sandbox profile; it reads a timeline from the shared container (app group), never from a live network call at render time.

- One `TimelineProvider`, entries computed from the shared store; reload with `WidgetCenter.shared.reloadTimelines(ofKind:)` after the app writes, not on a timer.
- Interactivity goes through an `AppIntent` button or toggle.
- A widget and the app **share one model package** so the same code decodes the same data; the app group id is prefixed with the team id (otherwise the user is prompted).
- Controls (Control Center, menu bar) follow the widget pattern with `ControlWidget`; verify availability on the deployment target first.
- Respect Reduce Transparency and Increase Contrast: the widget background is the system container style, not a custom translucent fill.

## Notifications

Local notifications through `UNUserNotificationCenter`; **ask for authorization at the moment it matters** (the user turns on a reminder), after a pre-prompt, and handle all three states: the denied state is a screen with an **Open System Settings** link (`sandbox-and-permissions` shows the pattern; the pane anchor is `com.apple.Notifications-Settings.extension`, to be verified on the target).

```swift
@MainActor
final class Notifier: NSObject, UNUserNotificationCenterDelegate {
    private let center = UNUserNotificationCenter.current()
    private let router: Router

    init(router: Router) {
        self.router = router
        super.init()
        center.delegate = self
    }

    func authorizationState() async -> PermissionState {
        switch await center.notificationSettings().authorizationStatus {
        case .authorized, .provisional: .granted
        case .denied: .denied
        default: .notDetermined
        }
    }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        guard let route = Route(userInfo: response.notification.request.content.userInfo) else { return }
        await MainActor.run { router.open(route) }
    }
}
```

- **A foreground failure is never a system notification**; the inline banner owns it. Notifications are for events the user opted into while the app is not in front.
- A notification action routes through the same validated `Route` as a URL.
- Re-read the authorization state on activation; the user changes it in System Settings.
- Content is minimal; never a token, a full address or a medical detail on the lock-screen-visible text.

## URLs and external events — one validated router

```swift
struct Route {
    enum Destination { case order(UUID), settings }

    init?(url: URL) {
        guard url.scheme == "myapp", let host = url.host, host.count <= 32 else { return nil }
        switch host {
        case "order":
            guard let id = UUID(uuidString: url.lastPathComponent) else { return nil }
            self = Route(destination: .order(id))
        case "settings":
            self = Route(destination: .settings)
        default:
            return nil
        }
    }
    let destination: Destination
    private init(destination: Destination) { self.destination = destination }
}

WindowGroup(for: UUID.self) { $id in OrderWindow(id: id) }
    .handlesExternalEvents(matching: ["order"])
```

- `CFBundleURLTypes` declares the scheme; `.onOpenURL` receives it; `.handlesExternalEvents(matching:)` sends it to the **window that owns it** instead of opening a new window per URL.
- **One parser** for URLs, notification payloads, intent parameters and file activations. Unknown host, bad id, oversize value → `nil`, logged without the payload, no window opened.
- A URL never carries a token or triggers a destructive action without a confirmation inside the app. A custom scheme is claimable by other apps: sign-in callbacks use a universal link or the provider's claimed redirect (`auth0-macos`).
- A route into data the user has not got (deleted, another account) shows a scoped "not found" state in the window.

## Services, pasteboard, drag and drop

- **Services**: the system lists what an app registers in `NSServices` (Info.plist); the handler gets a pasteboard, validates the type and size, and returns text or nothing. Never assume the selection is plain.
- **Copy and paste**: `.copyable` and `.onPasteCommand(of:)` with `Transferable`; paste validates content type and size and reports a rejection in the banner. Edit menu items come from the system; never replace Copy/Paste with custom items.
- **Drag and drop**: `Transferable` with `draggable` and `dropDestination`; a drop target shows its targeted state (`isTargeted`) and validates what it accepts (UTType, count, size, **not a path the app then opens blindly**). Dropped files are read through the grant the drop gives the sandbox; to keep one, bookmark it (`sandbox-and-permissions`).
- On the 27 SDK a `List` accepts drops into reorderable content with `.reorderable()`, with a per-row `dropDestination`; a long reorder is undoable.
- **AppKit**: `NSFilePromiseReceiver.receivePromisedFiles…` is called **inside** the drag callbacks on 27, or it throws.
- A hover-only drop affordance gets a click path: touch Macs exist.

## Rules

Standards come from `.claude/rules/desktop-macos/` (`/desktop-macos:rules` installs them); CLAUDE.md § Desktop code rules wins where they differ.

## Generation steps

1. Read the existing intents, widgets, URL types and drop targets; detect the deployment target and SDK.
2. Choose the smallest surface; write the shared model package if a widget or intent shares data.
3. Intents and entities: dependencies registered at launch, parameters validated, user-readable errors.
4. Widgets in their own targets, reading the app group store; reload after writes.
5. One `Route` parser; wire `.onOpenURL`, `.handlesExternalEvents`, notification responses and intents to it.
6. Notifications: request in context; three states; the Settings link; re-read on activation.
7. Drop and paste: validate type and size; keep access through bookmarks where needed.
8. Tests for the parser, the intent `perform()` and the validators (`unit-testing`); test ids on the drop targets and buttons (`test-ids`).

## Validation

- Shortcuts shows the action; running it with a deleted id returns the readable error.
- `open "myapp://order/<uuid>"` opens the order in its window once; `myapp://order/../x` and an oversize host open nothing.
- Deny notifications: the denied screen and the link show; grant in Settings and return, the screen heals.
- Drop a file of the wrong type and an oversize one: rejected with the banner, no crash.
- Widget updates after a write in the app within the reload; it renders with Reduce Transparency on.

## Common gotchas

- **An intent with its own logic**: drifts from the UI.
- **A route parser per entry point**: one of them forgets validation.
- **A widget reading the network at render**: blank widgets; read the shared store.
- **A new window per URL**: use `.handlesExternalEvents`.
- **A system notification for a foreground failure**: use the inline banner.
- **A hover-only drop zone**: no click path for touch.
- **A path from the pasteboard opened as-is**: validate, and the sandbox will refuse it anyway.
