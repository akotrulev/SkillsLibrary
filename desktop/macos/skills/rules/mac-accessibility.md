---
paths:
  - "**/*{View,Window,Row,Sheet,Form,Inspector,Scene,Commands,Controller,Cell}.swift"
  - "**/{Views,Windows,Scenes,Components,UI,Commands,Inspectors,Controllers,ViewControllers}/**/*.swift"
---

<!-- desktop-macos rules v1 (2026-11-15): accessibility and test ids. Installed by /desktop-macos:rules; edit the paths above to where this project keeps its UI. -->

# Mac accessibility and test id standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

## Accessibility

- Every command is reachable from the keyboard; focus order follows reading order (sidebar, content, inspector), focus is visible, and the system focus ring is not removed without a drawn replacement and a recorded reason. *major*
- The standard shortcuts stay; Escape closes sheets, popovers and inline editors; Return commits the default action; Tab never traps focus. *major*
- A tappable thing is a `Button`, `Toggle` or `NavigationLink`, never `.onTapGesture`; a custom control is `.focusable()`, handles keys (Space and Return activate, arrows move) and has an accessible name. *major*
- Every interactive element has an accessible name, including every icon-only toolbar item; state lives in traits and values, not in the label; no "button" or "selected" in a label. *major*
- Click targets are at least 20 × 20 pt; the default control height is 28 pt; `.small` and `.mini` only in dense inspectors, never for the primary action. Text is at least 10 pt (13 pt body), set with system text styles, never a fixed-size font for readable text. *major*
- No fixed-height container around text, no `lineLimit(1)` on content that matters; windows resize and layouts reflow. *major*
- Colour is never the only cue (Differentiate Without Color); contrast holds in light, dark and Increase Contrast (4.5:1 body, 3:1 large text and UI edges). *major*
- A drag, a hover reveal or a gesture has a keyboard route and an `accessibilityAction`; a context menu is never the only route to a command. *major*
- An async result or error is announced without moving focus; focus moves only when the meaning of the window changes. *major*
- Rows are grouped into one VoiceOver stop where that reads better; long lists have rotors; headings are marked; decorative images are hidden; no `.accessibilityHidden(true)` on an interactive element. *minor*
- Custom motion honours Reduce Motion, and translucent surfaces honour Reduce Transparency. *major*

## Test ids

- Every interactive element and every list, table or container carries an `accessibilityIdentifier` (AppKit: `setAccessibilityIdentifier` on the view, a cell's subviews). *major*
- The id is never the accessibility label, and a label is never an id. *major*
- Ids are static `Window.ElementType[.Qualifier]` in PascalCase: no row id, GUID, index, state value or translated text; list rows share one locator inside their container. *major; minor for casing*
- Region states (`.Loading`, `.Error`, `.Retry`, `.Empty`, `.Stale`) and the error banner are tagged. *major*
- `.accessibilityElement(children: .combine)` hides tagged children; tag leaves and check the page source. *major*
- Ids are interpolated from the value in scope, never an `[Enum: String]` map; two non-row elements never share one. *minor*
- No wrapper view that exists only to carry ids; no id on layout stacks. *minor*
