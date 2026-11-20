---
name: background-and-helpers
description: Use when a Mac app runs outside its window (SMAppService login item or agent, XPCSession helper). Triggers "launch at login". Not for permissions (sandbox-and-permissions).
disable-model-invocation: true
---

# macOS — Background and Helpers

What runs when no window is open: a login item that starts with the user, a launch agent that keeps a job alive, an XPC service that does risky or privileged work out of process, and scheduled background activity. **`SMAppService` registers every one of them; hand-installed `launchd` plists are not used. IPC is `XPCSession`.** Quitting mid-work is routine, a dead helper is a scoped failed region, never a dead app. Audit rows are section J of `desktop-macos:standards-audit`.

## Version lane

| Concern | Primary | Notes |
|---|---|---|
| `SMAppService` | macOS 13+: `.mainApp`, `.loginItem(identifier:)`, `.agent(plistName:)`, `.daemon(plistName:)` | Replaces `SMLoginItemSetEnabled`, `SMJobBless` and `~/Library/LaunchAgents` plists |
| `XPCSession` / `XPCListener` | macOS 14+ (Swift) | A macOS 13 target uses `NSXPCConnection` — a lane, flagged |
| Background scheduling | `NSBackgroundActivityScheduler` (10.10+) | For deferrable maintenance while the app runs |
| macOS 27 `launchd` | Does not load plists that carry the quarantine attribute | Wording ambiguous in the release notes; test an unzipped download |
| Neural Engine in the background | `com.apple.developer.background-tasks.continued-processing.inference` (27) | Only for inference work |
| App Store 2.4.5(iii) | No login or auto-launch code **without the user's consent** | **[MAS]** |

Detect first: how the project registers existing helpers (an old `SMLoginItemSetEnabled` call, a copied plist) and its deployment target. **Migrating an existing helper to `SMAppService` is a recorded step (`migration`), not a side effect.**

## Which mechanism?

| Need | Use | Lives in the bundle at |
|---|---|---|
| Start the **app** at login | `SMAppService.mainApp` | the app itself |
| Start a **helper app** at login | `SMAppService.loginItem(identifier:)` | `Contents/Library/LoginItems/<Helper>.app` |
| A background job under the user's launchd | `SMAppService.agent(plistName:)` | `Contents/Library/LaunchAgents/<label>.plist` |
| Out-of-process work started on demand | An **XPC service** | `Contents/XPCServices/<Name>.xpc` |
| Root-owned work | `SMAppService.daemon(plistName:)` — needs admin approval | `Contents/Library/LaunchDaemons/` — exception, reason recorded |
| Work while the app runs | `NSBackgroundActivityScheduler` | in-process |

Choose the **least privileged** row. A Login Items setting is a user decision: the app registers only when the user turns the control on.

## Login item — the settings control

```swift
@Observable
final class LaunchAtLogin {
    private(set) var status: SMAppService.Status
    private let service = SMAppService.mainApp

    init() {
        status = service.status
    }

    func setEnabled(_ enabled: Bool) throws {
        if enabled { try service.register() } else { try service.unregister() }
        status = service.status
    }

    func refresh() {
        status = service.status
    }

    func openSystemSettings() {
        SMAppService.openSystemSettingsLoginItems()
    }
}
```

- **Register only on the user's action** (a toggle in `Settings`); never at first launch, never silently. Unregister when the toggle goes off.
- **Four statuses, four screens**: `.enabled` (toggle on), `.notRegistered` (off), `.requiresApproval` (the user must approve in System Settings → General → Login Items: show the explanation and **Open System Settings** via `openSystemSettingsLoginItems()`), `.notFound` (the bundle layout is wrong: a failed state with a log line, not a crash).
- `register()` throws; the error goes to the inline banner, not an alert.
- **Re-read `status` on activation** (`refresh()`): the user flips it in System Settings behind the app's back. The toggle reflects `status`, never a stored copy.
- A helper (`.loginItem`) is a separate app target with `LSUIElement = YES` and its own entitlements; the main app registers it by the helper's bundle identifier.

## Agents — a job under the user's launchd

The plist ships **inside the bundle** and `SMAppService.agent(plistName:)` registers it; the app never writes into `~/Library/LaunchAgents`, never calls `launchctl` and never copies a plist at runtime.

```swift
let agent = SMAppService.agent(plistName: "com.example.orders.sync.plist")
try agent.register()
```

```xml
<plist version="1.0"><dict>
    <key>Label</key><string>com.example.orders.sync</string>
    <key>BundleProgram</key><string>Contents/MacOS/OrdersSync</string>
    <key>AssociatedBundleIdentifiers</key><array><string>com.example.orders</string></array>
    <key>MachServices</key><dict><key>com.example.orders.sync</key><true/></dict>
    <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
</dict></plist>
```

- `BundleProgram` is a path inside the bundle, relative to it; `AssociatedBundleIdentifiers` makes System Settings show the app's name and icon instead of the developer's name.
- A moved, renamed or re-signed app invalidates the registration: re-read `status` at launch and re-register when it reports `.notFound` after an update.
- A quarantined plist is not loaded on macOS 27: an unzipped, unsigned test build looks "registered" but never runs; test with the signed, notarized build.

## IPC — `XPCSession`

An XPC service runs the risky or heavy work in its **own process with its own sandbox profile** and its own, smaller, entitlements; a crash there does not take the app down. **Check the `XPCSession` / `XPCListener` initializer labels (peer requirement, handlers) against the SDK in use before writing**: the sample shows the shape, and the exact signatures are not re-verified here.

```swift
struct ImportRequest: Codable { let bookmark: Data }
struct ImportReply: Codable { let rowCount: Int }

actor ImportClient {
    private var session: XPCSession?

    func importFile(_ request: ImportRequest) async throws -> ImportReply {
        let session = try activeSession()
        return try await session.send(request)
    }

    private func activeSession() throws -> XPCSession {
        if let session { return session }
        let created = try XPCSession(xpcService: "com.example.orders.importer") { [weak self] reason in
            Task { await self?.sessionEnded(reason) }
        }
        session = created
        return created
    }

    private func sessionEnded(_ reason: XPCRichError) {
        session = nil
    }
}
```

- Messages are `Codable` values. **Every message from the other side is untrusted input** (CLAUDE.md § Desktop code rules): decode, bound the sizes, validate, reject unknown kinds; never a `String` path, a `NSSecureCoding` object graph or a closure from a caller you have not checked.
- The **listener verifies its caller**: `XPCListener` with a code-signing requirement (`XPCListener(service:requirement:)` where the SDK exposes it) so only your team's apps connect. An unrestricted listener is a **blocker**.
- Give the service **a bookmark, not a path**: the service has its own sandbox. The app creates a plain bookmark (no security scope) and the service resolves it; a read-only grant stays read-only.
- **A dead service is recoverable.** The cancellation handler clears the session; the next call reconnects once; two failures in a row open a failed region ("The importer stopped. Try again") with a button, and the rest of the window keeps working. `error-handling` shows it.
- `NSXPCConnection` stays only in a codebase that already uses it (a macOS 13 target, or a legacy helper): a lane, with the same caller verification (`setCodeSigningRequirement`).

## Background activity while the app runs

```swift
let scheduler = NSBackgroundActivityScheduler(identifier: "com.example.orders.compact")
scheduler.repeats = true
scheduler.interval = 6 * 60 * 60
scheduler.tolerance = 60 * 60
scheduler.qualityOfService = .utility
scheduler.schedule { completion in
    if scheduler.shouldDefer { completion(.deferred); return }
    Task {
        await store.compact()
        completion(.finished)
    }
}
```

- Always honour `shouldDefer`; the system defers on battery, thermal pressure and Low Power Mode.
- The job is **idempotent and cancellable**: quitting mid-job is routine, the next run resumes or restarts cleanly.
- **Never block the main actor** for it; heavy work in a background `Task`.
- Disable App Nap (`ProcessInfo.beginActivity`) only around a user-visible long task, and end it in a `defer`.

## Lifecycle

- **Quit and relaunch**: the helper and the app agree on a version at connect; a mismatch after an update restarts the helper.
- **Sleep and wake**: a helper holding a connection reconnects on wake (`networking`); a scheduler job resumes by itself.
- **Update**: an auto-update (Sparkle) never restarts the app or the helper over unsaved work; the helper stops after finishing its current unit.
- **Uninstall**: unregister every `SMAppService` item when the user turns it off; never leave a registration behind for a removed feature.

## Rules

Standards come from `.claude/rules/desktop-macos/` (`/desktop-macos:rules` installs them); CLAUDE.md § Desktop code rules wins where they differ.

## Generation steps

1. Read the bundle layout, the entitlements and any existing helper registration; detect the deployment target.
2. Pick the least privileged mechanism from the table; record why in the PR.
3. Login item: a `LaunchAtLogin` model, the four statuses, `refresh()` on activation, the Open System Settings link.
4. Agent or service: put the plist or `.xpc` in the bundle; register through `SMAppService`; a `Codable` message type per call.
5. Verify the caller in the listener; validate every decoded message.
6. Wire the dead-service path to a scoped failed region; test it by killing the helper.
7. Tests with a fake of the one-method client (`unit-testing`); `accessibilityIdentifier` on the toggle (`test-ids`).

## Validation

- Toggle on: the app appears in System Settings → Login Items; log out and in, it starts; toggle off, it does not.
- `.requiresApproval`: the explanation and the link show; approve in Settings, return, the toggle turns on without a relaunch.
- `rg -n "LaunchAgents|launchctl|SMLoginItemSetEnabled|SMJobBless" -g '*.swift'` finds nothing in new code.
- `kill -9` the helper during a call: the window shows the scoped failed region, **Try again** reconnects.
- A second, unsigned process connects to the listener: rejected.

## Common gotchas

- **Registered at first launch to "be convenient"**: a consent violation, and a MAS rejection (2.4.5(iii)).
- **A copied plist in `~/Library/LaunchAgents`**: survives uninstall and is invisible in Login Items.
- **Toggle stored in `UserDefaults`** instead of read from `status`: drifts when the user changes Settings.
- **A helper that inherits the app's entitlements**: it does not; the helper's own file decides.
- **Passing a path to the service**: it cannot open it; pass a bookmark.
- **A listener that accepts anyone**: any process can drive your helper.
- **`.notFound` after an update**: the bundle moved; re-register.
