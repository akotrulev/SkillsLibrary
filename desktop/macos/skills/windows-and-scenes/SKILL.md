---
name: windows-and-scenes
description: Use when declaring Mac windows (WindowGroup, Window, UtilityWindow, Settings, openWindow, restoration). Triggers "open a second window". Not for menu commands (menus-and-commands).
disable-model-invocation: true
---

# macOS — Windows and Scenes

A Mac app is a set of windows over shared data. Scenes are declared once in the `App`; the UI says "window", never "scene". `pushWindow` does not exist on macOS (visionOS only): **use `openWindow`.** Audit rows are section F of `desktop-macos:standards-audit`.

## Version lane

| Concern | Primary | Supported / notes |
|---|---|---|
| `WindowGroup`, `Settings`, `.keyboardShortcut`, `.onOpenURL`, `.handlesExternalEvents` | macOS 11+ | — |
| `Window`, `MenuBarExtra`, `.windowResizability`, `focusedSceneObject` | macOS 13+ | Below 13: `WindowGroup` plus AppKit (`appkit`) |
| `.inspector`, `openSettings` | macOS 14+ | — |
| `UtilityWindow`, `.defaultWindowPlacement`, `.windowLevel`, `.restorationBehavior`, `.defaultLaunchBehavior`, `.windowIdealSize`, `.windowManagerRole`, `WindowDragGesture` **[mac15+]** | macOS 15 (new-app primary) | On 14, size with `frame(minWidth:)` and place with AppKit |
| `.windowResizeAnchor`, `.glassEffect` | macOS 26 | `#available` gate |
| Toolbar overflow: `.visibilityPriority`, `ToolbarOverflowMenu` **[mac27SDK]** | 27 SDK | Older SDK: let the system overflow |

Detect the deployment target first; never raise it for a scene API. Design facts: `design/ui-ux-pro-max` `--stack swiftui`; HIG "Windows". The corpus wins.

## When to use

- Declaring the scenes of a new app, or adding a window kind
- Opening a window from a command, a button or a URL
- Window size, placement, restoration, full screen, toolbars
- A menu-bar-only app, a floating inspector, a Settings window

## When NOT to use

- Menu bar commands and shortcuts → [`menus-and-commands`](../menus-and-commands/SKILL.md)
- Document windows, autosave → [`documents`](../documents/SKILL.md)
- State shared across windows → [`architecture`](../architecture/SKILL.md)
- Sidebar, `Table`, inspector content → [`ui-components`](../ui-components/SKILL.md)
- URL schemes routed to windows → `system-integration`
- An AppKit-owned window → [`appkit`](../appkit/SKILL.md); Windows → `desktop-windows:windows-and-navigation`

## Pick the scene

| Need | Scene |
|---|---|
| Any number of windows of one kind | `WindowGroup` (`WindowGroup(for: Album.ID.self)` for a window per value) |
| Exactly one window (a library, an about box) | `Window` — the id is the only way to open it |
| Preferences, ⌘, | `Settings` — never a `WindowGroup` |
| Floating tool palette | `UtilityWindow` **[mac15+]**: hides when the app is inactive, Escape dismisses, adds a View-menu toggle, reads the focused main window's `FocusedValues` |
| Menu-bar presence | `MenuBarExtra` (`.menu` or `.window` style, `isInserted:`) |
| Files | `DocumentGroup` (`documents`) |

```swift
@main
struct AlbumsApp: App {
    @State private var library = LibraryModel(client: .live)

    var body: some Scene {
        WindowGroup("Albums", for: Album.ID.self) { $albumID in
            AlbumWindow(albumID: albumID)
        }
        .environment(library)
        .defaultSize(width: 900, height: 600)
        .windowResizability(.contentMinSize)

        Window("Activity", id: "activity") {
            ActivityView()
        }
        .environment(library)

        Settings { SettingsView() }
    }
}
```

The store is created once in the `App` and injected into **every** scene: several windows on the same data share one source of truth, never a copy per window. Per-window state (selection, scroll, inspector shown) stays in the window.

## Opening windows — `openWindow`

```swift
struct AlbumRow: View {
    let album: Album
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        Button("Open in New Window") { openWindow(value: album.id) }
    }
}
```

- `openWindow(id:)` for a `Window`; `openWindow(value:)` for a typed `WindowGroup`. The same value focuses the existing window.
- A window kind the app opens from several places has its id in one enum, not string literals.
- HIG: do not open a new window by default; **offer** "Open in New Window". Settings opens with `openSettings` (macOS 14+) or the standard ⌘, item, never a hand-built window.
- Never a `pushWindow` call, never `NSApp.sendAction` for a window SwiftUI can open.

## Size, placement, restoration

| Rule | How |
|---|---|
| Resizable, with a floor | `windowResizability(.contentMinSize)` and `frame(minWidth:minHeight:)`; never a fixed size without a reason |
| Remembers size and position | The default; `restorationBehavior(.automatic)` **[mac15+]**. `.disabled` only for a window that must always open fresh, with the reason recorded |
| First launch size | `defaultSize`, `defaultWindowPlacement` **[mac15+]**, `windowIdealSize` |
| Survives monitor and Space changes | Do not store absolute frames yourself; the system restores to a connected display |
| Relaunch with no windows | `defaultLaunchBehavior(.presented)` **[mac15+]** on the main scene; `.suppressed` on helper scenes |
| Full screen | The system button works; `windowToolbarFullScreenVisibility` **[mac15+]** for the toolbar |
| Inactive look | `@Environment(\.appearsActive)` dims custom chrome |

Restored state holds **ids and layout only** — `@SceneStorage` carries selection and scroll; records come from the store (see `architecture`).

## Toolbars

`.toolbar { ToolbarItem(placement: .primaryAction) { … } }`; customizable toolbars with `.toolbar(id:)` and `ToolbarItem(id:)`. **Every toolbar item also exists as a menu command** — a toolbar is a shortcut to the menu bar, not a second home for commands. Items carry `accessibilityIdentifier`; icon-only items carry a label (`Label`) and `.help`. Do not paint a toolbar background on the 27 SDK (Liquid Glass; see `styling`).

## Menu-bar-only apps

`MenuBarExtra` with `LSUIElement = YES`; the system terminates the app when the user removes the extra, so persistent state saves on change. Provide a Quit item and a way to open the main window (`openWindow`). A `.window`-style extra is a small panel: a failure shows an inline banner there, never a modal alert.

## Lifecycle

- Work a window starts is cancelled when it closes: `.task` on the root view.
- Reactivation, wake and network change revalidate once, at the window root (`scenePhase`, `NSWorkspace.didWakeNotification`), not in each leaf.
- Closing the last window does not quit unless the app is a single-window utility (`applicationShouldTerminateAfterLastWindowClosed` in the AppKit delegate, `appkit`).
- Quit with unsaved work asks first (`documents` for documents).
- Touch Macs ship since 2026-11-06: a window control that appears on hover also has a click or context-menu path.

## Common gotchas

- **`pushWindow`**: not on macOS.
- **A `WindowGroup` for one-of windows**: users get duplicates; use `Window`.
- **A model created per window**: copies of the same records; create once in the `App`.
- **A hand-built preferences window**: use `Settings`.
- **A fixed-size window**: breaks on small displays and DPI changes.
- **Records in `@SceneStorage`**: store ids.
- **Commands only in toolbar buttons**: add them to the menu bar.

## Handoffs

- Menus and shortcuts → [`menus-and-commands`](../menus-and-commands/SKILL.md)
- Documents → [`documents`](../documents/SKILL.md)
- State shape → [`architecture`](../architecture/SKILL.md)
- AppKit windows, `NSHostingSceneRepresentation` → [`appkit`](../appkit/SKILL.md)
- Test ids → `test-ids`; accessibility → `accessibility`
