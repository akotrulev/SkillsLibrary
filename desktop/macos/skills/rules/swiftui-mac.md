---
paths:
  - "**/*{View,Window,Row,Sheet,Form,Inspector,Scene,Commands,Settings}.swift"
  - "**/{Views,Windows,Scenes,Components,UI,Commands,Inspectors}/**/*.swift"
---

<!-- desktop-macos rules v1 (2026-11-15): SwiftUI on the Mac. Installed by /desktop-macos:rules; edit the paths above to where this project keeps its views, scenes and commands. -->

# SwiftUI on the Mac: view, window and command standards

Severity tags as in the core Swift rules. The codebase wins where it consistently does otherwise; a SwiftUI rule is never flagged on an AppKit window. Recipes: `ui-components`, `windows-and-scenes`, `menus-and-commands`, `forms`.

## Views

- `body` is pure and cheap: no network call, `UserDefaults` read, decode, formatter construction or sort. *major*
- Async work starts in `.task` / `.task(id:)`, never `Task { }` in `onAppear` or a load in `init`. *major*
- Every data region renders loading, loaded, empty and failed (plus stale and offline where cached), scoped to the response-dependent subtree; an undecodable response is failed, never empty. *major*
- Every surfaced failure also raises the one persistent inline banner in the window content, dismissed only by the user; a background failure never raises a modal alert; never render `localizedDescription`. *major*
- Unbounded data is a `Table` or `List` with stable domain ids: no `id: \.self` on non-unique data, no index. *major*
- System controls and SF Symbols at Mac sizes; no custom title bar, iOS-style tab bar or web look; no hover-only control. *major*
- No `AnyView` to dodge a type error. *minor*

## Windows and scenes

- Scenes are declared in the `App` (`WindowGroup`, `Window`, `Settings` for preferences, `MenuBarExtra`); windows open via `openWindow`. *major*
- A window is resizable, has a minimum size, restores its size and position and survives a monitor or scale change. *major*

## Commands

- Every command lives in the menu bar in the standard order; an unavailable command is disabled, never hidden. *major*
- Commands read the focused window's state through `@FocusedValue` / `focusedSceneValue`, never a captured model. *major*
- Standard shortcuts (⌘Q, ⌘W, ⌘, ⌘Z, ⌘C/V/X, ⌘F, ⌘A) are never rebound. *major*

## Forms and sheets

- A form has one pure validator, errors beside the field, a re-entry-guarded submit with one idempotency key, and focus on the first invalid field. *major*
- Sheets use `.sheet(item:)`; Escape cancels, Return is the default action. *minor*
