---
paths:
  - "**/*{View,Window,Row,Sheet,Form,Inspector,Scene,Commands,Controller,Cell}.swift"
  - "**/{Views,Windows,Scenes,Components,UI,Commands,Inspectors,Controllers,ViewControllers}/**/*.swift"
---

<!-- desktop-macos rules v1 (2026-11-15): accessibility and test ids. Installed by /desktop-macos:rules; edit the paths above to where this project keeps its UI. -->

# Mac accessibility and test id standards

Severity tags as in the core Swift rules. The codebase wins where it consistently does otherwise. Recipes: `accessibility`, `test-ids`.

## Accessibility

- Every command is reachable from the keyboard; focus order follows reading order, focus is visible, and the system focus ring is not removed without a drawn replacement and a recorded reason. *major*
- Escape closes sheets, popovers and inline editors; Return commits the default action; Tab never traps focus. *major*
- A tappable thing is a `Button`, `Toggle` or `NavigationLink`, never `.onTapGesture`; a custom control is `.focusable()`, handles keys and has an accessible name. *major*
- Every interactive element has an accessible name, icon-only toolbar items included; state lives in traits and values, not in the label. *major*
- Click targets are at least 20 × 20 pt; text uses system text styles, never a fixed-size font for readable text; no fixed-height container around text. *major*
- Colour is never the only cue; contrast holds in light, dark and Increase Contrast. *major*
- A drag, a hover reveal or a gesture has a keyboard route and an `accessibilityAction`. *major*
- An async result or error is announced without moving focus. *major*
- Custom motion honours Reduce Motion, translucent surfaces Reduce Transparency. *major*
- Decorative images are hidden; no `.accessibilityHidden(true)` on an interactive element. *minor*

## Test ids

- Every interactive element and every list, table or container carries an `accessibilityIdentifier`, never the accessibility label. *major*
- Ids are static `Window.ElementType[.Qualifier]` in PascalCase: no row id, GUID, index, state value or translated text. *major; minor for casing*
- Region states (`.Loading`, `.Error`, `.Retry`, `.Empty`, `.Stale`) and the error banner are tagged. *major*
- `.accessibilityElement(children: .combine)` hides tagged children: tag leaves. *major*
- No wrapper view that exists only to carry ids; no id on layout stacks. *minor*
