# AppKit → SwiftUI, one window or view at a time

Only on request. **An AppKit codebase is not a defect**; Apple's stance is that no app needs to be entirely SwiftUI. Run this move when the user wants it, never as a drive-by ([`appkit`](../../appkit/SKILL.md) owns the lane as it stands). A project below macOS 13 stays AppKit: report it and offer a deployment-target run first.

## 0. Decide the unit and the order

```bash
rg -ln "NSViewController|NSWindowController" -g '*.swift' | wc -l
rg -ln "\.xib|\.storyboard" --files -g '*.xib' -g '*.storyboard'
rg -ln "NSTableView|NSOutlineView|NSCollectionView" -g '*.swift'
rg -ln "NSApplicationDelegate|NSApplicationMain|@NSApplicationMain" -g '*.swift'
```

Order, leaves first: **a view nothing else embeds** (an inspector, a preferences pane, a detail view), then the windows that host it, then the sidebar and content, then the root. The app lifecycle moves last, or first only when nothing else depends on the delegate.

## 1. Seams: SwiftUI inside AppKit (the default direction)

| Step | Shape |
|---|---|
| Host a leaf | `NSHostingController` as a child view controller, or `NSHostingView` as a subview, pinned with Auto Layout. The view model is created by the controller and passed in by initializer |
| Share state | One `@Observable` model owned outside the hosting; the AppKit side reads it with observation tracking, the SwiftUI side with `@Bindable` ([`observation-and-async`](observation-and-async.md)) |
| Preferences | A `Settings` scene replaces the hand-built window; an AppKit app reaches it through `NSHostingSceneRepresentation` where the deployment target allows, else host a SwiftUI form in the existing preferences window controller |
| Menus | Keep the `NSMenu` until the windows move; then replace it with `commands`. Never duplicate a command in both ([`menus-and-commands`](../../menus-and-commands/SKILL.md)) |
| Toolbar | `NSToolbar` stays with its window until the window is a SwiftUI `WindowGroup`; then `.toolbar` |
| Table | `NSTableView` → `Table` only when selection, sorting and column behaviour have tests on the old one; a table with custom cell views or drag and drop is the last row to move |

Each commit moves one view. The AppKit controller it replaces is deleted in the same commit, so there are never two owners.

## 2. The reverse seam: AppKit inside SwiftUI

A view with no SwiftUI equivalent (a rich text editor, a custom canvas) stays an `NSViewRepresentable`: build in `makeNSView`, apply state idempotently in `updateNSView`, delegates in the `Coordinator`, cleanup in `dismantleNSView`. Never mutate SwiftUI state from `updateNSView`. A representable for what `TextField`, `Table` or `Map` already does is a finding.

## 3. Lifecycle

1. Move the entry point: `@main struct App: App` with an `NSApplicationDelegateAdaptor` for what only a delegate can do (open-file handling that predates scenes, `applicationShouldTerminate`). Delete `main.swift` / `@NSApplicationMain` once the delegate is the adaptor.
2. Window restoration: AppKit state restoration (`NSWindowRestoration`) becomes scene restoration (`@SceneStorage`, `restorationBehavior`); check the relaunch before deleting the old path ([`windows-and-scenes`](../../windows-and-scenes/SKILL.md)).
3. `NSDocument` → `DocumentGroup` is its own move, after the windows are SwiftUI ([`filedocument-to-document`](filedocument-to-document.md) covers the SwiftUI document side; an `NSDocument` port is one document type per commit with the same autosave and versions behaviour checked).

## Verify

- Every moved window: keyboard-only pass (focus order, Escape, Return), VoiceOver reads the same names, `accessibilityIdentifier`s unchanged so the QA suite still finds them ([`test-ids`](../../test-ids/SKILL.md)).
- Window size, position and full screen restore after relaunch; two windows on the same data still agree.
- `screencapture -l <windowid>` before and after, read back as images; no visual redesign rides along.

## Do not

- Redesign while porting.
- Port the root first and host the rest inside it: every AppKit controller then runs under a representable it was never built for.
- Delete a `.xib` before its replacement has a test or a screenshot.
- Introduce TCA or another architecture as part of the port.
