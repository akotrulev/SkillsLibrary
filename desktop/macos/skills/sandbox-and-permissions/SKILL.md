---
name: sandbox-and-permissions
description: Use when a Mac app needs entitlements, TCC permissions or user files (sandbox, bookmarks, camera, Full Disk Access). Triggers "permission denied". Not for helpers (background-and-helpers).
disable-model-invocation: true
---

# macOS — Sandbox and Permissions

How a Mac app gets to the things it does not own: the user's files, the camera, the screen, other apps. Two systems decide it. The **App Sandbox** (entitlements, signed into the binary) says what the app *may ask for*; **TCC** (the privacy database, the user's choice in System Settings) says what the user *allowed*. Every permission has a working denied path, a stale bookmark is a recoverable state, and Full Disk Access is never assumed. Audit rows are section J of `desktop-macos:standards-audit`.

## Version lane

| Concern | Primary | Notes |
|---|---|---|
| App Sandbox | Mandatory for the Mac App Store (2.4.5(i)); **on from day one** for Developer ID too | The container is bound to the code signature since macOS 14: another app's container access prompts |
| macOS 27 | Other teams' app containers and app-group containers: **denied by default, no prompt**; XProtect may block data malware targets; apps can no longer read the TCC database | Never read it; ask the API |
| Screen capture | `SCContentSharingPicker` (macOS 14): per-capture consent | Standing grants are re-confirmed periodically (monthly on Sequoia; 27 cadence not verified) |
| Security-scoped bookmarks | `.withSecurityScope` | macOS 10.7+ |
| Hardened Runtime | Required for notarization **[DevID]** | → `desktop/_shared/distribution` |

Detect first: the entitlements file, `ENABLE_APP_SANDBOX`, and whether the build is MAS or Developer ID. **Never turn the sandbox off, or add an entitlement, as a side effect.**

## When to use

- Adding an entitlement, or finding why a call is blocked in the sandbox
- Opening, saving or re-opening a file the user chose; remembering a folder
- Camera, microphone, screen recording, accessibility, input monitoring, Desktop/Documents/Downloads, Automation
- A feature that "needs Full Disk Access"
- A permission denied and the user is stuck

## When NOT to use

- The app's own container paths, Keychain → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Document open/save, autosave, versions → [`documents`](../documents/SKILL.md)
- Login items, XPC helpers → [`background-and-helpers`](../background-and-helpers/SKILL.md)
- Notifications permission, App Intents → [`system-integration`](../system-integration/SKILL.md)
- The outgoing-network entitlement → [`networking`](../networking/SKILL.md)
- Notarization, signing, App Store rules → `desktop/_shared/distribution`
- iOS permissions → `mobile-ios:device-features`; Windows → `desktop-windows:platform-integration`

## Entitlements — least privilege, every one with a reason

| Entitlement | Grants | Add when |
|---|---|---|
| `com.apple.security.app-sandbox` | The sandbox | Always |
| `com.apple.security.network.client` | Outgoing connections | The app calls an API |
| `com.apple.security.network.server` | Listening sockets | Only an app that listens |
| `com.apple.security.files.user-selected.read-only` / `.read-write` | Files chosen in an open/save panel | The user opens or saves files |
| `com.apple.security.files.bookmarks.app-scope` | Persistent access to chosen files | The app re-opens them next launch |
| `com.apple.security.files.downloads.read-write` (and Music, Movies, Pictures) | A standard folder | The feature is about that folder |
| `com.apple.security.device.camera` / `.audio-input` | Capture hardware | Camera or microphone |
| `com.apple.security.automation.apple-events` | Scripting other apps | Automation |
| `com.apple.security.application-groups` | A shared container | A helper or extension shares data |

- **Prefer the narrowest form**: `user-selected.read-only` before `read-write`; a panel before a standard-folder entitlement; a standard-folder entitlement before anything temporary-exception.
- `com.apple.security.temporary-exception.*` entitlements are a **major** finding on MAS (review rejects most); on Developer ID they carry a written reason.
- Keep one `<App>.entitlements` per target, and a short table of "entitlement → reason" in the repo; an unexplained entitlement is a finding.

## Files — panels, then bookmarks

Inside the sandbox the app reaches a user file only through a panel (`fileImporter`, `fileExporter`, `NSOpenPanel`, `NSSavePanel`, drag and drop, "Open With"). The grant lasts for the run. To remember it, make a **security-scoped bookmark**.

```swift
actor FolderAccess {
    private let defaults: UserDefaults
    private let key: String

    init(defaults: UserDefaults = .standard, key: String) {
        self.defaults = defaults
        self.key = key
    }

    func remember(_ url: URL) throws {
        let data = try url.bookmarkData(options: .withSecurityScope, includingResourceValuesForKeys: nil, relativeTo: nil)
        defaults.set(data, forKey: key)
    }

    func withAccess<T>(_ body: (URL) async throws -> T) async throws -> T {
        guard let data = defaults.data(forKey: key) else { throw FolderAccessError.notChosen }
        var isStale = false
        let url = try URL(resolvingBookmarkData: data, options: .withSecurityScope, relativeTo: nil, bookmarkDataIsStale: &isStale)
        guard url.startAccessingSecurityScopedResource() else { throw FolderAccessError.denied(url) }
        defer { url.stopAccessingSecurityScopedResource() }
        if isStale { try remember(url) }
        return try await body(url)
    }
}
```

- **Start and stop are balanced**: every successful `startAccessing…` has exactly one `stopAccessing…`, in a `defer`, in the same scope. A leak holds a kernel resource until quit and eventually exhausts the budget; an unbalanced stop breaks a second user of the same URL. Nothing awaits across a long-lived start if a shorter scope will do.
- **A stale bookmark is a recoverable state.** `bookmarkDataIsStale` means the file moved or the volume changed: re-create the bookmark from the resolved URL and store it (above). A bookmark that **cannot resolve** (file deleted, volume gone) or whose `start…` returns `false` becomes the **failed region** with a message and a **Choose Folder…** button that re-opens the panel — never a crash, never an empty list.
- Store bookmark `Data` in the container (`UserDefaults` for a few, the database for many); it is not a secret but it is per-user and per-app.
- A bookmark handed to an XPC service or launch agent is a plain bookmark (no scope option); the service resolves it ([`background-and-helpers`](../background-and-helpers/SKILL.md)).
- Sidecar files next to a document (a `.srt` beside a `.mp4`) need `NSIsRelatedItemType` in the type declaration and an `NSFilePresenter`.
- **Never** `chmod`, `sudo`, `Process("/bin/sh")` or a temporary exception to reach a file the user did not pick.

## TCC permissions — ask in context, work when denied

TCC grants live in a per-user database the app cannot read. The app can only **check** through the API of the feature, **ask at the moment of use** after a pre-prompt screen that says why, and **react to the answer**.

| Permission | Ask / check | Usage string or entitlement |
|---|---|---|
| Camera, microphone | `AVCaptureDevice.authorizationStatus(for:)`, `requestAccess(for:)` | `NSCameraUsageDescription`, `NSMicrophoneUsageDescription` + `device.camera` / `device.audio-input` |
| Screen recording | Prefer `SCContentSharingPicker`; else `CGPreflightScreenCaptureAccess()` / `CGRequestScreenCaptureAccess()` | Picker needs no TCC grant |
| Accessibility | `AXIsProcessTrustedWithOptions` with the prompt option | User toggles in Settings; relaunch may be needed |
| Input Monitoring | `CGPreflightListenEventAccess()` / `CGRequestListenEventAccess()` | — |
| Desktop, Documents, Downloads, removable volumes | A panel in the sandbox; outside it the first access prompts | `NSDesktopFolderUsageDescription` etc. |
| Automation | `NSAppleEventsUsageDescription` | `automation.apple-events` + target list |
| **Full Disk Access** | **None — no API, no prompt, no entitlement** | User grants it in Settings |
| Local network | First connection prompts | `NSLocalNetworkUsageDescription` |

Usage-description strings are required, specific ("Used to record your voice notes") and localized; a missing one terminates the app at the request.

### The denied path is a working screen

Every row above ends in a state the user can act on:

```swift
enum PermissionState { case notDetermined, granted, denied }

struct CameraGate<Content: View>: View {
    @Environment(\.openURL) private var openURL
    let state: PermissionState
    let request: () async -> Void
    @ViewBuilder let content: () -> Content

    var body: some View {
        switch state {
        case .granted: content()
        case .notDetermined:
            ContentUnavailableView {
                Label("Camera access", systemImage: "camera")
            } description: {
                Text("Record clips for your notes. macOS will ask for permission.")
            } actions: {
                Button("Continue") { Task { await request() } }
                    .accessibilityIdentifier("Camera.Continue")
            }
        case .denied:
            ContentUnavailableView {
                Label("Camera is off", systemImage: "camera.fill")
            } description: {
                Text("Turn on Camera for this app in System Settings to record clips.")
            } actions: {
                Button("Open System Settings") {
                    openURL(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera")!)
                }
                .accessibilityIdentifier("Camera.OpenSettings")
            }
        }
    }
}
```

- The deep link is `x-apple.systempreferences:com.apple.preference.security?Privacy_<Pane>` (`Privacy_Camera`, `Privacy_Microphone`, `Privacy_ScreenCapture`, `Privacy_Accessibility`, `Privacy_ListenEvent`, `Privacy_AllFiles`, `Privacy_Automation`). **Verify the anchor on the deployment target before shipping**: Settings panes are renamed between releases, and an unknown anchor opens the top-level pane, which is acceptable; a crash is not.
- `.denied` and "restricted by a profile" both reach the same screen; the second says "managed by your organisation".
- The rest of the window keeps working: only the feature's region swaps. No modal alert, no relaunch loop.
- **Re-check on activation**: the user changes the setting in System Settings and comes back; `scenePhase == .active` re-reads the state, so the screen heals itself. Accessibility and screen recording may need an app restart; say so, and offer **Quit and Reopen**.
- A permission asked at launch "to be safe" is a **major** finding.

### Full Disk Access is never assumed

No feature requires FDA to work for a sandboxed app, and an unsandboxed one must run without it. If a feature is *better* with it (a disk analyser, a backup tool), detect by attempting a read of a protected path inside `do`/`catch`, **degrade** to what the panels reach, explain once inline, and offer **Open System Settings** (`Privacy_AllFiles`). Never instruct the user to grant FDA to get the app to start. Never read the TCC database (macOS 27 blocks it).

## Sandbox failures — reading the signal

A sandbox denial is a kernel log line, not an exception the app sees clearly: `Operation not permitted`, `-1003`, `NSCocoaErrorDomain 257`. Find it with Console or `log stream --predicate 'subsystem == "com.apple.sandbox.reporting"'`, add the narrowest entitlement or panel that fixes it, and record the reason. Test with the **sandboxed Release build**, not a Debug run from Xcode with the sandbox off.

## Rules

Standards come from `.claude/rules/desktop-macos/` (`/desktop-macos:rules` installs them); CLAUDE.md § Desktop code rules wins where they differ.

## Generation steps

1. Read the entitlements file and the Info.plist usage strings; detect MAS vs Developer ID.
2. List every file and device feature the app touches; give each its narrowest entitlement and a reason.
3. Files: a panel first; a bookmark through `FolderAccess` when the app must re-open; stale and unresolvable paths wired to the failed region.
4. For each TCC permission: usage string, pre-prompt, request at the moment of use, the three states, the deep link, re-check on activation.
5. Add `accessibilityIdentifier` to the buttons (`test-ids`); tests for the state mapping (`unit-testing`).

## Validation

- Release build with the sandbox on: every feature works through its panel or entitlement.
- Reset a grant with `tccutil reset Camera <bundle id>` (also `Microphone`, `ScreenCapture`, `Accessibility`, `ListenEvent`, `AppleEvents`), launch, deny: the denied screen shows, the link opens the right pane, granting in Settings and returning heals the screen.
- Move a bookmarked folder, relaunch: stale path is re-bookmarked or the failed region offers **Choose Folder…**; delete it: same.
- `start`/`stop` counts match under a stress loop (Instruments, or a counting wrapper in tests).
- Full Disk Access off: the app launches and every non-FDA feature works.

## Common gotchas

- **Works in Debug, blocked in Release**: Debug ran unsandboxed.
- **Missing usage string**: the app is killed at the request, with a crash log naming the key.
- **Bookmark made without `.withSecurityScope`**: resolves, but `start…` returns `false` after relaunch.
- **`start…` with no `stop…` on the throw path**: use `defer`.
- **Stale bookmark ignored**: works once more, then the folder "forgets" the grant.
- **Asking for Accessibility at launch** to enable one rarely used feature.
- **Opening `Privacy_AllFiles` as the first run step** for an app that could run without it.

## Handoffs

- Container paths, Keychain → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Documents and their panels → [`documents`](../documents/SKILL.md)
- Helpers receiving a bookmark → [`background-and-helpers`](../background-and-helpers/SKILL.md)
- Notifications, App Intents → [`system-integration`](../system-integration/SKILL.md)
- Network entitlement → [`networking`](../networking/SKILL.md)
- Signing, notarization, App Review → `desktop/_shared/distribution`; secrets → `desktop/_shared/security`
- Settings-link screen states → `error-handling`; test ids → `test-ids`
- iOS counterpart → `mobile-ios:device-features`
