---
paths:
  - "**/*{View,Window,Row,Sheet,Form,Inspector,Scene,Commands,Settings}.swift"
  - "**/{Views,Windows,Scenes,Components,UI,Commands,Inspectors}/**/*.swift"
---

<!-- desktop-macos rules v1 (2026-11-15): SwiftUI on the Mac. Installed by /desktop-macos:rules; edit the paths above to where this project keeps its views, scenes and commands. -->

# SwiftUI on the Mac: view, window and command standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise; a SwiftUI rule is never flagged on an AppKit window.

## Views

- `body` is pure and cheap: no network call, `UserDefaults` read, decode, formatter construction or sort. *major*
- Async work starts in `.task` / `.task(id:)`, never `Task { }` in `onAppear` or a load in `init`. *major*
- Every data region is one `LoadState` enum rendering loading, loaded, empty and failed, plus stale and offline where cached, scoped to the response-dependent subtree; toolbar, search and filters survive. *major*
- An undecodable response is failed, never empty; a failed refetch keeps the data, marked stale; a cancelled request renders nothing; offline is not a server error and offers no retry. *major*
- Every surfaced failure also raises the one persistent inline banner inside the window content, dismissed only by the user, deduped; a background failure never raises a modal alert. *major*
- Never render `localizedDescription`, a raw server string or a body. *major*
- Unbounded data is a `Table` or `List` with stable domain ids and selection: no `id: \.self` on non-unique data, no index, no `UUID()` per render. *major*
- System controls and SF Symbols at Mac control sizes; no custom title bar, no iOS-style tab bar, no web look. *major*
- Hover-only controls have a click, context-menu or keyboard path (touch-screen Macs ship). *major*
- No `AnyView` to dodge a type error, no `GeometryReader` as a default layout tool. *minor*
- `#Preview` per state with no live data; no `PreviewProvider` in new code. *minor*

## Windows and scenes

- Scenes are declared in the `App`: `WindowGroup` for many, `Window` for one-of windows, `Settings` for preferences (never a hand-built preferences window), `MenuBarExtra` for a menu-bar item, `UtilityWindow` for a palette on macOS 15+; windows open through `openWindow`. *major*
- A window is resizable, has a minimum size, restores its size and position, and survives a monitor or scale change; no fixed-size main window. *major*
- Window selection and drafts restore from `@SceneStorage` as ids, never records. *major*
- `NavigationSplitView` for sidebar apps; the sidebar, content and inspector keep working at the minimum width. *minor*

## Commands

- Every command lives in the menu bar (`commands`, `CommandMenu`, `CommandGroup`) in the standard order; a toolbar button or context-menu item is never the only route. *major*
- An unavailable command is disabled, never hidden: no `if` around a menu item. *major*
- Commands read the focused window's state through `@FocusedValue` / `focusedSceneValue`, never a model captured in the command. *major*
- Standard shortcuts (⌘Q, ⌘W, ⌘, ⌘Z, ⌘C/V/X, ⌘F, ⌘A) are never rebound; a new shortcut does not collide with a system one; Settings comes from the `Settings` scene, not a second menu entry. *major*
- Menu-bar icons are set explicitly where they carry meaning (the 27 SDK hides them by default). *minor*

## Forms and sheets

- Forms: one pure validator; errors as localized text beside the field; submit guards re-entry, shows progress and carries one idempotency key; `@FocusState` moves focus to the first invalid field on submit; the key-view loop is complete; `SecureField` for secrets; server field errors land on their fields, unknown ones in a form-level message. *major*
- Sheets use `.sheet(item:)` with Escape to cancel and Return for the default action; Tab does not trap focus. *minor*
