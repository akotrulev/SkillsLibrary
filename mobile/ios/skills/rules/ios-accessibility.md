---
paths:
  - "**/*{View,Screen,Row,Sheet,Form,Controller,Cell}.swift"
  - "**/{Views,Screens,Components,UI,Controllers,ViewControllers}/**/*.swift"
---

<!-- mobile-ios rules v1 (2026-11-03): accessibility and test ids. Installed by /mobile-ios:rules; edit the paths above to where this project keeps its UI. -->

# iOS accessibility and test id standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

## Accessibility

- A tappable thing is a `Button`, `Toggle` or `NavigationLink`, never `.onTapGesture`; every interactive element has an accessible name; state lives in traits and values, not in the label. *major*
- Text uses text styles and `@ScaledMetric` (`UIFontMetrics` in UIKit): no `.font(.system(size:))`, no `lineLimit(1)` or `.dynamicTypeSize` clamp on content, no fixed-height text container. *major*
- Touch targets are at least 44 × 44 pt. *major*
- Colour is never the only cue; contrast holds in light, dark and Increase Contrast. *major*
- A gesture-only operation has an `accessibilityAction` or a visible alternative. *major*
- An async result or error is announced; focus moves only when the meaning of the screen changes. *major*
- Decorative images hidden, informative ones described; rows grouped into one stop; headings marked; no `.accessibilityHidden(true)` on an interactive element. *minor*

## Test ids

- Every interactive element and every list or grid container carries an `accessibilityIdentifier` (UIKit: on the view, a cell's `contentView`, `UIBarButtonItem`). *major*
- The id is never the accessibility label, and a label is never an id. *major*
- Ids are static `Screen.ElementType[.Qualifier]` in PascalCase: no row id, GUID, index, state value or translated text; list rows share one locator. *major; minor for casing*
- Region states (`.Loading`, `.Error`, `.Retry`, `.Empty`, `.Stale`) and the error banner are tagged. *major*
- `.accessibilityElement(children: .combine)` hides tagged children; tag leaves and check the page source. *major*
- Ids are interpolated from the value in scope, never an `[Enum: String]` map; two non-row elements never share one. *minor*
- No wrapper view that exists only to carry ids; no id on layout stacks. *minor*
