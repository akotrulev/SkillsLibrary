---
name: mobile-ios-accessibility
description: Use when a SwiftUI or UIKit screen must work with VoiceOver, Dynamic Type through the accessibility sizes, Reduce Motion and Differentiate Without Color — labels, traits, values, grouping, rotors, custom actions, focus, announcements, touch targets. Triggers "VoiceOver reads the wrong thing", "text clips at large sizes", "announce the result". Do NOT use for scanning (`qa-mobile-ios`), field errors (`-forms`) or animation mechanics (`-animation`).
---

# iOS — Accessibility

Standardises **authoring** accessible iOS screens against **WCAG 2.2 AA** and VoiceOver's conventions. The house rule: **a real control with the right label, trait and value; never rebuild semantics on a bare `View` or `UIView`.** Web analog: [`fe-react-accessibility`](../../../../frontend/react/skills/accessibility/SKILL.md) — semantic-first, announcements and focus management carry over; landmarks, Tab order and skip links do not. Sibling: [`mobile-react-native-accessibility`](../../../react-native/skills/accessibility/SKILL.md) (the same rules through RN props).

**Boundary — authoring, not scanning.** Proving it on a device (a VoiceOver pass, Accessibility Inspector audit, XCUITest `performAccessibilityAudit()`, journeys with a screen reader on) is `qa-mobile-ios`'s. Target size, a non-drag alternative and accessible authentication are design decisions made first (`design/accessible-by-design`); this skill implements them. Design facts (type scale, contrast, targets) come from `design/ui-ux-pro-max` (`--stack swiftui`); the corpus wins on a disagreement.

## Version lane

| Concern | Primary (iOS 17+) | `[iOS16]` / UIKit |
|---|---|---|
| Label / trait / value | `.accessibilityLabel` · `.accessibilityAddTraits` · `.accessibilityValue` · `.accessibilityHint` | Same modifiers; UIKit `accessibilityLabel` / `accessibilityTraits` / `accessibilityValue` |
| Announcement | `AccessibilityNotification.Announcement(_:).post()` | `UIAccessibility.post(notification: .announcement, argument:)` |
| Focus | `@AccessibilityFocusState` + `.accessibilityFocused($)` | `UIAccessibility.post(notification: .layoutChanged / .screenChanged, argument: view)` |
| Large text | `@Environment(\.dynamicTypeSize)`, `@ScaledMetric`, text styles | `UIFontMetrics`, `adjustsFontForContentSizeCategory = true` |
| Settings | `\.accessibilityReduceMotion`, `\.accessibilityDifferentiateWithoutColor`, `\.accessibilityReduceTransparency`, `\.colorSchemeContrast` | `UIAccessibility.isReduceMotionEnabled` + its change notification |
| `[iOS27 SDK]` | Liquid Glass is forced; legibility over glass is yours to verify with Increase Contrast and Reduce Transparency on | Re-check each custom bar and overlay |
| Nutrition Labels | App Store Connect self-declaration, voluntary (§4.4) — declare only what a device pass proved | Same |

Detect first: SwiftUI or UIKit per screen, any in-house component library that already sets traits (use it), and whether any `.font(.system(size:))` or `.dynamicTypeSize(...)` clamp exists.

## When to use

- Labelling a control, grouping a row into one stop, marking headings, exposing a value
- Focus and announcements after navigation, a sheet, an async result or an error
- Large text, touch targets, contrast, Reduce Motion, Differentiate Without Color
- A swipe or drag action that needs a non-gesture alternative; readiness for Accessibility Nutrition Labels

## When NOT to use

- Scanning, VoiceOver journeys, audits in CI → `qa-mobile-ios` (peer)
- Validation messages on fields → [`forms`](../forms/SKILL.md) · banner and failed regions → [`error-handling`](../error-handling/SKILL.md)
- `withAnimation` / Reduce Motion mechanics → [`animation`](../animation/SKILL.md) · semantic colours and type tokens → [`styling`](../styling/SKILL.md)
- `accessibilityIdentifier` → [`test-ids`](../test-ids/SKILL.md) (an identifier is never a label)
- Other stacks → `mobile-react-native-accessibility`, `mobile-android-accessibility`

## Lean on the platform

| Want | Use — not |
|---|---|
| A tap target | `Button` — never `Text` + `.onTapGesture` (no trait, no focus, no Voice Control name) |
| Navigate | `NavigationLink` / `Button` pushing a route — not a gesture on a `VStack` |
| Text input | `TextField("Email", text:)` with a visible label — a placeholder is not a label |
| A toggle | `Toggle`, `Picker`, `Stepper` — they own their value and adjust actions |
| A heading | `.accessibilityAddTraits(.isHeader)` — one per section; the rotor navigates by it |
| A sheet | `.sheet` / `.fullScreenCover` — focus moves in and returns on dismiss by itself |

## Label, trait, value

```swift
Button { cart.add(item) } label: {
    Image(systemName: "cart.badge.plus")
}
.accessibilityLabel("Add \(item.name) to cart")
.accessibilityIdentifier("Catalog.Row.AddToCart")
```

- **Label is what it is, trait is what it does, value is its current state.** No "button" in a label (the trait says it); no "selected" in a label (use `.isSelected`); a slider's position is `.accessibilityValue`, not part of its label.
- **Icon-only controls need a label**; an SF Symbol with a text `Label` already has one. Decorative images are `.accessibilityHidden(true)` — an informative `Image` gets a label.
- **Labels are translated** (String Catalog — [`languages`](../languages/SKILL.md)); the hint is the *result* of the action, used sparingly, never a repeat of the label.
- **Group a row into one stop.** `.accessibilityElement(children: .combine)` joins a title and its subtitle into one utterance; `.ignore` plus an explicit label when the combined reading is wrong. A grouped row hides its children from a locator unless the parent carries the identifier — check [`test-ids`](../test-ids/SKILL.md) before grouping a tested row.
- **Reading order follows layout**; `.accessibilitySortPriority` only when layout order is wrong, never to paper over a layout built out of order.

## Custom actions, adjustable and rotors

A swipe-to-delete, a long press or a drag is invisible to a VoiceOver user unless it is also an action:

```swift
OrderRow(order: order)
    .swipeActions { Button("Archive", role: .destructive) { archive(order) } }
    .accessibilityAction(named: "Archive") { archive(order) }
```

- `.swipeActions` on a `List` row is exposed automatically; a **custom** gesture is not — add `.accessibilityAction(named:)` or `.accessibilityActions { }`.
- **Adjustable**: `.accessibilityAdjustableAction` for a custom stepper / rating; the system `Slider`, `Stepper` already do it.
- **Rotors**: `.accessibilityRotor("Unread") { ForEach(unread) { AccessibilityRotorEntry($0.title, id: $0.id) } }` on a long feed so users jump between meaningful items; `.accessibilityRepresentation { }` when a custom control should read as a standard one.

## Focus and announcements

```swift
struct SaveStatus: View {
    @AccessibilityFocusState private var errorFocused: Bool

    var body: some View {
        Text(message)
            .accessibilityFocused($errorFocused)
            .onChange(of: failure) { _, new in if new != nil { errorFocused = true } }
    }
}
```

- **After an async result or error, announce** — `AccessibilityNotification.Announcement("Order archived").post()` — without moving focus. The error banner ([`error-handling`](../error-handling/SKILL.md)) announces on appearance and never steals focus from the field being edited.
- **Move focus only when the screen's meaning changes** (a new sheet, a wizard step, an inline form error on submit). On a validation failure, focus the first invalid field.
- A custom overlay that is not a system sheet sets `.accessibilityAddTraits(.isModal)` so the background is not read; remove it when dismissed.
- UIKit: `.layoutChanged` for part of the screen, `.screenChanged` for a new screen — each with the view to focus.

## Dynamic Type — through the accessibility sizes

- **Text styles only** (`.font(.body)`, `.title3`); never `.font(.system(size: 14))` for readable text. Custom fonts scale through `Font.custom(_:size:relativeTo:)` / `UIFontMetrics`.
- **Layout survives `accessibility5`.** Rows switch axis: `ViewThatFits` or `@Environment(\.dynamicTypeSize).isAccessibilitySize` to move an `HStack` to a `VStack`; `ScrollView` over fixed-height containers; no `lineLimit(1)` on content that matters.
- **Metrics that accompany text scale with it** — `@ScaledMetric(relativeTo: .body) var iconSize = 24`.
- **Never clamp** with `.dynamicTypeSize(...DynamicTypeSize.large)` on content. A bounded range on a tab-bar label or a dense chart axis is allowed, with the reason written beside it as a doc comment on the view.
- Test on the largest accessibility size in Xcode's Dynamic Type preview and the simulator's accessibility settings.

## Touch targets, contrast, colour and motion

- **Targets ≥ 44 × 44 pt** — `.frame(minWidth: 44, minHeight: 44)` plus `.contentShape(Rectangle())` for a small glyph; the system's own controls already comply.
- **Contrast 4.5:1 body, 3:1 large text and UI edges** in light, dark and **Increase Contrast** (`\.colorSchemeContrast == .increased`); use semantic colours and asset-catalog variants ([`styling`](../styling/SKILL.md)). Over Liquid Glass, verify legibility with Reduce Transparency on.
- **Never colour alone** — `\.accessibilityDifferentiateWithoutColor` true ⇒ add an icon or text beside a red / green state.
- **Reduce Motion** ⇒ cross-fade or no motion for custom transitions; parallax, auto-playing loops and large zooms stop. Mechanics: [`animation`](../animation/SKILL.md).
- **Voice Control**: the visible text is the spoken name; when the label differs from visible text, add `.accessibilityInputLabels(["Add", "Add to cart"])`.

## Accessibility Nutrition Labels — readiness

A voluntary App Store Connect declaration per supported feature (VoiceOver, Voice Control, Larger Text, Sufficient Contrast, Dark Interface, Differentiate Without Color, Reduced Motion, Captions, Audio Descriptions). **Declare a feature only after a device pass proved it on the common tasks** (`qa-mobile-ios`); this skill makes the code ready — labelled controls, scaling layout, contrast tokens, motion respect — and never writes the declaration. Re-check the Connect options before filing; they are not verified here.

## Rules

- `Button` / `Toggle` / `NavigationLink`, never a tap gesture on a view; every control has a label, the right trait and a value where it holds state.
- Decorative content hidden; informative content described; rows grouped into one stop; headings marked.
- Every gesture-only operation has an `accessibilityAction`; results are announced, focus moves only on meaning change.
- Text styles and `@ScaledMetric`; layouts survive `accessibility5`; no clamp on content.
- Targets ≥ 44 pt; contrast holds in light, dark and Increase Contrast; state never by colour alone; Reduce Motion honoured.

## What NOT to do

- No `.onTapGesture` as a button; no "button", "selected" or "disabled" inside a label.
- No `.font(.system(size:))` for readable text; no `lineLimit(1)` on content; no `.dynamicTypeSize` clamp on content.
- No `accessibilityLabel` used as a test identifier, no identifier copied into a label.
- No `.accessibilityHidden(true)` on an interactive element; no fixed-height container around scalable text.
- No Nutrition Label declared from code reading alone.

## Generation steps

1. Read the screen's views, the component library and the Dynamic Type handling already present; match them.
2. Replace gesture-only controls with real controls; add label, trait, value; group rows; mark headings.
3. Add custom actions for gestures, announcements for async results, focus moves for meaning changes.
4. Convert fixed sizes to text styles and `@ScaledMetric`; add the axis switch for accessibility sizes.
5. Add `Differentiate Without Color` and Reduce Motion branches; check targets and contrast.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Accessibility Inspector audit on each screen: no unlabelled element, no clipped text, no target under 44 pt.
- A VoiceOver pass at `accessibility5`: each row is one stop, each action reachable, the error announced once.
- Settings → Accessibility with Increase Contrast, Reduce Transparency, Reduce Motion and Differentiate Without Color on: nothing disappears, nothing relies on colour.
- Dev-side tests of the logic that picks a layout or label: [`unit-testing`](../unit-testing/SKILL.md); device journeys → `qa-mobile-ios`.

## Handoffs

- Field-level error wiring → [`forms`](../forms/SKILL.md) · failure surfaces → [`error-handling`](../error-handling/SKILL.md)
- Reduce Motion mechanics → [`animation`](../animation/SKILL.md) · tokens and Liquid Glass → [`styling`](../styling/SKILL.md)
- Identifiers → [`test-ids`](../test-ids/SKILL.md) · localized labels → [`languages`](../languages/SKILL.md)
- Store declarations → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
