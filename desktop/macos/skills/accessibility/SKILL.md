---
name: accessibility
description: Use when a SwiftUI or AppKit Mac window must work with VoiceOver, Full Keyboard Access and Reduce Motion. Triggers "VoiceOver reads the wrong thing". Not for a11y scanning (qa-desktop-typescript).
---

# macOS: Accessibility

Standardises **authoring** accessible Mac windows against **WCAG 2.2 AA** (EN 301 549; the European Accessibility Act applies since 2025-06-28) and VoiceOver's conventions. The house rule: **a real control with the right label, role and value; never rebuild semantics on a bare `View` or `NSView`.** Web analog: [`fe-react:accessibility`](../../../../frontend/react/skills/accessibility/SKILL.md): semantic-first, announcements and focus management carry over. Sibling: [`mobile-ios:accessibility`](../../../../mobile/ios/skills/accessibility/SKILL.md) (the same modifiers; the Mac adds the keyboard as a first-class input and a pointer, and has no touch-target rule). Audit rows are section M of `desktop-macos:standards-audit`.

**Boundary: authoring, not scanning.** Proving it (a VoiceOver pass, the Accessibility Inspector audit, `performAccessibilityAudit()`, journeys with VoiceOver on) is `qa-desktop-<lang>`'s. Design facts (contrast, type, sizes) come from `design/ui-ux-pro-max` (`--stack swiftui`); the corpus wins on a disagreement.

## Version lane

| Concern | Primary (macOS 14+) | `[mac13]` / AppKit |
|---|---|---|
| Label / trait / value | `.accessibilityLabel` · `.accessibilityAddTraits` · `.accessibilityValue` · `.accessibilityHint` | AppKit `setAccessibilityLabel`, `setAccessibilityRole`, `setAccessibilityValue` |
| Announcement | `AccessibilityNotification.Announcement(_:).post()` | `NSAccessibility.post(element:notification:)` with `.announcementRequested` |
| Focus | `@AccessibilityFocusState` + `.accessibilityFocused($)` | `NSAccessibility.post(… .focusedUIElementChanged)` |
| Keyboard focus | `@FocusState`, `.focusable()`, `.focusSection()` | `nextKeyView` / `nextValidKeyView`, the key-view loop |
| Settings | `\.accessibilityReduceMotion`, `\.accessibilityReduceTransparency`, `\.colorSchemeContrast`, `\.accessibilityDifferentiateWithoutColor` | `NSWorkspace.shared.accessibilityDisplayShould…` properties |
| Text size | System text styles and fixed Mac sizes (§ Text, below) | Same |
| `[mac27SDK]` | A SwiftUI `Menu` with a plain or custom button style exposes `AXTitle`, not `AXDescription`; the keyboard loop is fixed when full keyboard navigation is off; open/save panel tab order is fixed. Liquid Glass is forced: verify legibility with Increase Contrast and Reduce Transparency on | Re-check each custom bar and overlay |
| `XCUIVoiceOverService` | Xcode 27 / macOS 27: UI tests can drive VoiceOver and assert focus and spoken output. A QA tool, not a dev-side one | `qa-desktop-<lang>` |

Detect first: SwiftUI or AppKit per window, any in-house component library that already sets roles (use it), and whether `.font(.system(size:))` or a fixed frame exists around text.

## When to use

- Labelling a control, grouping a row into one stop, marking headings, exposing a value
- Keyboard reach, focus order and Full Keyboard Access in a new window
- Focus and announcements after a sheet, an async result or an error
- Text and control sizes, contrast, Reduce Motion, Reduce Transparency, Increase Contrast
- A drag or context-menu-only action that needs a keyboard alternative

## When NOT to use

- Scanning, VoiceOver journeys, audits in CI → `qa-desktop-<lang>` (peer)
- Validation messages on fields → [`forms`](../forms/SKILL.md) · banner and failed regions → [`error-handling`](../error-handling/SKILL.md)
- Menu commands and shortcuts → [`menus-and-commands`](../menus-and-commands/SKILL.md)
- Motion mechanics, tokens, Liquid Glass → [`styling`](../styling/SKILL.md)
- `accessibilityIdentifier` → [`test-ids`](../test-ids/SKILL.md) (an identifier is never a label)
- Windows apps → `desktop-windows:accessibility`; iOS → `mobile-ios:accessibility`

## Lean on the platform

| Want | Use, not |
|---|---|
| A click target | `Button`, never `Text` + `.onTapGesture` (no role, no focus, no Full Keyboard Access, no Voice Control name) |
| Navigate | `NavigationLink` / `Button` pushing a route, not a gesture on a `VStack` |
| Text input | `TextField("Email", text:)` with a visible label; a placeholder is not a label |
| A toggle, choice | `Toggle`, `Picker`, `Stepper`: they own their value and adjust actions |
| A heading | `.accessibilityAddTraits(.isHeader)`: one per section; the rotor navigates by it |
| A sheet | `.sheet`: focus moves in and returns on dismiss by itself |
| A command | A menu-bar command with a shortcut ([`menus-and-commands`](../menus-and-commands/SKILL.md)); a toolbar button is the second route, never the only one |

## Keyboard first

The Mac is keyboard-and-pointer. **Every action reachable by click or drag is reachable by keyboard**, and the app survives **Full Keyboard Access** (System Settings → Accessibility → Keyboard), where Tab moves through every control, not only text fields.

- **The standard shortcuts stay.** ⌘Q, ⌘W, ⌘, ⌘Z, ⌘C/V/X, ⌘F, ⌘A and the system's own are never rebound; a new shortcut never collides with a system or VoiceOver key.
- **Focus order follows reading order**, top to bottom, leading to trailing, sidebar before content before inspector. Fix the order by layout, not by sorting. `.focusSection()` groups a region so arrow keys move inside it and Tab moves between regions.
- **Focus is visible** on every focusable element: do not remove the system focus ring (`.focusEffectDisabled()` on a custom control needs a drawn replacement and a recorded reason).
- **A custom control is `.focusable()` and handles keys** with `onKeyPress` (macOS 14) or `.keyboardShortcut`: Space and Return activate, arrows move, Escape cancels.
- **Escape closes** sheets, popovers and inline editors; **Return** commits the default action; Tab does not trap focus in a sheet.
- **A drag has a keyboard route**: a reorder by drag also has Move Up / Move Down commands; a drop target also has Paste or an Open panel.
- **A context menu is never the only route** to a command: the same action sits in the menu bar.
- `[AppKit]` keep the key-view loop complete: `nextKeyView` reaches every control once, in order, and custom views override `acceptsFirstResponder` where they take keys.

## Label, role, value

```swift
Button { library.add(album) } label: {
    Image(systemName: "plus")
}
.accessibilityLabel("Add \(album.title) to library")
.accessibilityIdentifier("Library.Row.AddButton")
```

- **Label is what it is, trait is what it does, value is its current state.** No "button" in a label; no "selected" in a label (use `.isSelected`); a slider's position is `.accessibilityValue`.
- **Icon-only controls need a label**, including every toolbar item; an SF Symbol with a text `Label` already has one. Decorative images are `.accessibilityHidden(true)`.
- **Labels are translated** ([`languages`](../languages/SKILL.md)); a hint is the *result* of the action, used sparingly.
- **Group a row into one stop.** `.accessibilityElement(children: .combine)` joins a title and its subtitle; `.ignore` plus an explicit label when the combined reading is wrong. A grouped row hides children from a locator: check [`test-ids`](../test-ids/SKILL.md) before grouping a tested row.
- **A `Table`** exposes rows and columns to VoiceOver on its own; give column headers real titles and do not flatten the table into one custom view.
- **Custom actions** for what a gesture or hover does: `.accessibilityAction(named: "Archive") { … }`; **rotors** (`.accessibilityRotor`) on long lists so users jump between meaningful items; `.accessibilityRepresentation { }` when a custom control should read as a standard one.
- **Hover content is not the only content.** A tooltip or hover-revealed button also exists as an accessibility action or a menu command.

## Focus and announcements

- **After an async result or error, announce** with `AccessibilityNotification.Announcement("Album archived").post()` without moving focus. The inline banner ([`error-handling`](../error-handling/SKILL.md)) announces on appearance and never steals focus from the field being edited.
- **Move focus only when the window's meaning changes**: a new sheet, a wizard step, an inline form error on submit (focus the first invalid field with `@AccessibilityFocusState`).
- A custom overlay that is not a system sheet sets `.accessibilityAddTraits(.isModal)` and removes it on dismiss.
- A new window takes focus on its first meaningful control, and closing it returns focus to the window that opened it.

## Sizes: controls and text

These are the Mac's own numbers, from the HIG; they replace the iOS 44 pt touch target.

| Measure | Rule |
|---|---|
| **Control size** | A click target is **at least 20 × 20 pt**; the default control height is **28 pt**. Use `.controlSize(.regular)`; `.small` and `.mini` only in dense inspectors and never for the primary action. Pad a small glyph with `.frame(minWidth: 20, minHeight: 20)` and `.contentShape(Rectangle())` |
| **Text size** | **At least 10 pt**; the default body is **13 pt**. Use the system text styles (`.body`, `.callout`, `.caption`), never `.font(.system(size: 9))` for readable text |
| **Touch-capable Macs** | A control on a touch surface follows the HIG touch guidance and is larger; design for pointer first |

macOS has **no Dynamic Type equivalent confirmed**: the HIG asks for text that can be enlarged but the Mac mechanism was not verified (research: not verified). Do not claim Dynamic Type on a Mac. Use text styles, let windows resize, and let the layout reflow: no fixed-height containers around text, no `lineLimit(1)` on content that matters, no clamp. Where the user's system text setting is available through the project's target, honour it.

## Contrast, colour and motion

- **Contrast 4.5:1 body, 3:1 large text and UI edges** in light, dark and **Increase Contrast** (`\.colorSchemeContrast == .increased`); semantic colours and asset-catalog variants ([`styling`](../styling/SKILL.md)). Over Liquid Glass (forced by the 27 SDK), verify legibility with **Reduce Transparency** on.
- **Never colour alone**: `\.accessibilityDifferentiateWithoutColor` true ⇒ add an icon or text beside a red / green state.
- **Reduce Motion** ⇒ cross-fade or no motion for custom transitions; parallax, auto-playing loops, large zooms and window-sized slides stop (`\.accessibilityReduceMotion`).
- **Voice Control**: the visible text is the spoken name; when the label differs, add `.accessibilityInputLabels(["Add", "Add to library"])`.

## Rules

Standards come from the desktop-macos rule file `mac-accessibility.md` in `.claude/rules/desktop-macos/` (`/desktop-macos:rules` installs it), or the plugin's copy when the project has none; CLAUDE.md § Desktop code rules wins where they differ.

## Generation steps

1. Read the window's views, any component library and the focus handling already present; match them.
2. Replace gesture-only controls with real controls; add label, role, value; group rows; mark headings.
3. Walk the window with the keyboard only (Tab, arrows, Space, Return, Escape): fix every unreachable action and add the menu command for it.
4. Add custom actions, announcements for async results, focus moves for meaning changes.
5. Check control and text sizes, add Reduce Motion, Reduce Transparency, Increase Contrast and Differentiate Without Color branches.

## Validation

- Accessibility Inspector audit on each window: no unlabelled element, no clipped text, no control under 20 pt.
- With Full Keyboard Access on, Tab reaches every control in reading order; Escape closes each sheet; nothing needs the mouse.
- A VoiceOver pass: each row is one stop, each action reachable, the error announced once, no hover-only content.
- System Settings → Accessibility with Increase Contrast, Reduce Transparency, Reduce Motion and Differentiate Without Color on: nothing disappears, nothing relies on colour.
- Dev-side tests of the logic that picks a layout or label: [`unit-testing`](../unit-testing/SKILL.md); VoiceOver journeys → `qa-desktop-<lang>`.

## Handoffs

- Field-level error wiring → [`forms`](../forms/SKILL.md) · failure surfaces → [`error-handling`](../error-handling/SKILL.md)
- Shortcuts and the menu bar → [`menus-and-commands`](../menus-and-commands/SKILL.md) · tokens, motion and Liquid Glass → [`styling`](../styling/SKILL.md)
- Identifiers → [`test-ids`](../test-ids/SKILL.md) · localized labels → [`languages`](../languages/SKILL.md)
- Windows and focus across windows → [`windows-and-scenes`](../windows-and-scenes/SKILL.md)
