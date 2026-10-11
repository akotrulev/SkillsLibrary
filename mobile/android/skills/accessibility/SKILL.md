---
name: accessibility
description: Use when a Compose or Views screen must work with TalkBack, font scale to 200%, Switch Access and the animator duration scale — semantics, contentDescription, merged descendants, roles, state descriptions, custom actions, focus, live regions, 48 dp targets. Triggers "TalkBack reads the wrong thing", "text clips at large font", "announce the result". Do NOT use for scanning (`qa-mobile-<stack>`), field errors (`-forms`) or animation mechanics (`-animation`).
---

# Android — Accessibility

Standardises **authoring** accessible Android screens against **WCAG 2.2 AA** and TalkBack's conventions. The house rule: **a real control with the right semantics; never rebuild a button out of a `Box` with a click handler.** Web analog: [`fe-react:accessibility`](../../../../frontend/react/skills/accessibility/SKILL.md) — semantic-first, announcements and focus management carry over; landmarks, Tab order and skip links do not. Sibling: [`mobile-ios:accessibility`](../../../ios/skills/accessibility/SKILL.md).

**Boundary — authoring, not scanning.** Proving it on a device (a TalkBack pass, Accessibility Scanner, Espresso / Appium journeys with a screen reader on) is `qa-mobile-<stack>`'s. The dev-side automated check in a Compose test is in [`unit-testing`](../unit-testing/SKILL.md). Target size and a non-drag alternative are design decisions made first (`design/accessible-by-design`); this skill implements them. Design facts come from `design/ui-ux-pro-max` (`--stack jetpack-compose`); the corpus wins on a disagreement.

## Version lane

| Concern | Compose (primary) | `[Views]` |
|---|---|---|
| Name / role / state | `Modifier.semantics { }`, `contentDescription`, `role`, `stateDescription`, `Role.Button` etc. | `android:contentDescription`, `ViewCompat.setAccessibilityDelegate`, `AccessibilityNodeInfoCompat` |
| Merge | `Modifier.semantics(mergeDescendants = true)`; `clickable`, `toggleable`, `selectable` merge by themselves | `android:importantForAccessibility`, a focusable container |
| Announcement | `liveRegion = LiveRegionMode.Polite` on a semantics node | `ViewCompat.setAccessibilityLiveRegion`, `announceForAccessibility` is a last resort |
| Focus | `FocusRequester` + `Modifier.focusRequester`; traversal `Modifier.semantics { traversalIndex = … }` inside `isTraversalGroup = true` | `requestFocus()`, `setAccessibilityTraversalBefore/After` |
| Large text | `sp` via `MaterialTheme.typography`; the system **font scale** and **non-linear scaling up to 200 %** | `sp` and `TextView` autosize |
| Motion | The animator duration scale = 0 as Reduce Motion ([`animation`](../animation/SKILL.md)) | Same |
| `[API36]` | Predictive back is on at target 36; it never replaces a visible back control | [`navigation`](../navigation/SKILL.md) |
| Compose test checks | `enableAccessibilityChecks()` from `androidx.compose.ui:ui-test-junit4-accessibility` (Compose 1.8+) | Espresso `AccessibilityChecks.enable()` |

Detect first: Compose or Views per screen, any in-house component library that already sets semantics (use it), and any `fontScale` or `sp`-locking in the theme or the manifest.

## When to use

- Naming a control, merging a row into one TalkBack stop, marking headings, exposing state and a value
- Focus and announcements after navigation, a dialog, an async result or an error
- Large text, touch targets, contrast, motion settings, state not by colour alone
- A swipe, long-press or drag that needs a non-gesture alternative

## When NOT to use

- Scanning, TalkBack journeys, audits in CI → `qa-mobile-<stack>` (peer)
- Validation messages on fields → [`forms`](../forms/SKILL.md) · banner and failed regions → [`error-handling`](../error-handling/SKILL.md)
- Reduce-motion mechanics → [`animation`](../animation/SKILL.md) · colour and type tokens → [`styling`](../styling/SKILL.md)
- `testTag` / resource ids → [`test-ids`](../test-ids/SKILL.md) (an id is never a description)
- Other stacks → `mobile-react-native:accessibility`, `mobile-ios:accessibility`

## Lean on the platform

| Want | Use — not |
|---|---|
| A tap target | `Button`, `IconButton`, `Modifier.clickable(role = Role.Button, onClickLabel = …)` on a `Row` — never a bare `pointerInput { detectTapGestures }` (no semantics, no TalkBack action) |
| A toggle | `Switch` / `Checkbox` inside a `Modifier.toggleable(role = …)` row — the row is the stop, the control carries `null` `onCheckedChange` |
| A selection | `Modifier.selectable(role = Role.RadioButton)` in a `selectableGroup()` |
| Text input | `TextField` / `OutlinedTextField` with a `label` — a placeholder is not a label |
| A heading | `Modifier.semantics { heading() }` — one per section; TalkBack navigates by it |
| A dialog | `AlertDialog` / `ModalBottomSheet` — focus moves in and returns on dismiss |

## Name, role, state

```kotlin
IconButton(
    onClick = { cart.add(item) },
    modifier = Modifier.testTag("Catalog.Row.AddToCart"),
) {
    Icon(
        imageVector = Icons.Outlined.AddShoppingCart,
        contentDescription = stringResource(R.string.add_to_cart, item.name),
    )
}
```

- **Name is what it is, role is what it does, state is its current condition.** No "button" in a description (the role says it); no "selected" in it (use `selected` / `stateDescription`); a slider's position is `stateDescription` or `progressBarRangeInfo`, not part of its name.
- **An icon-only control needs a `contentDescription`**; an `Icon` beside text is decorative — `contentDescription = null`. An informative `Image` gets a description; a purely decorative one gets `null`, never an empty string on a clickable (the accessibility check fails it).
- **Descriptions are string resources** ([`languages`](../languages/SKILL.md)), phrased as the action: "Add Blue mug to cart".
- **Merge a row into one stop**: `clickable` / `toggleable` merge their descendants; otherwise `Modifier.semantics(mergeDescendants = true) { }`. Use `clearAndSetSemantics { contentDescription = … }` only when the merged reading is wrong — it removes children from the tree **and from any test or locator that needs them**, so check [`test-ids`](../test-ids/SKILL.md) before clearing a tested row.
- **Reading order follows layout**; `isTraversalGroup` + `traversalIndex` only when layout order is wrong, never to paper over a layout built out of order.
- `[Views]` the same rules through `android:contentDescription`, `importantForAccessibility="no"` for decoration, and an `AccessibilityDelegateCompat` for a custom view's role, state and actions.

## Custom actions

A swipe-to-dismiss, a long press and a drag are invisible to TalkBack unless they are also actions:

```kotlin
OrderRow(
    order = order,
    modifier = Modifier.semantics {
        customActions = listOf(
            CustomAccessibilityAction(stringResource(R.string.archive)) {
                onArchive(order.id)
                true
            },
        )
    },
)
```

- `SwipeToDismissBox` on a row needs the custom action beside it; `onLongClickLabel` / `onClickLabel` on `combinedClickable` names what each gesture does.
- A custom slider or stepper exposes `progressBarRangeInfo` plus `setProgress { }`, or use the Material component that already does.
- A **drag handle** has a button alternative (move up / down) — WCAG 2.5.7 dragging movements.

## Focus and announcements

```kotlin
@Composable
fun SaveStatus(message: String?, modifier: Modifier = Modifier) {
    Text(
        text = message.orEmpty(),
        modifier = modifier.semantics { liveRegion = LiveRegionMode.Polite },
    )
}
```

- **After an async result or error, announce** through a live region on the node that changes — without moving focus. The error banner ([`error-handling`](../error-handling/SKILL.md)) is a polite live region and never steals focus from the field being edited; an urgent failure may use `LiveRegionMode.Assertive`, sparingly.
- **Move focus only when the screen's meaning changes** — a new dialog, a wizard step, the first invalid field on submit (`FocusRequester.requestFocus()` in a `LaunchedEffect` keyed by the submit attempt).
- A custom overlay that is not a system dialog sets `Modifier.semantics { isTraversalGroup = true }` and hides what is behind it from accessibility (`Modifier.clearAndSetSemantics {}` on the background is too blunt — prefer a real `Dialog`).
- `announceForAccessibility` and a `Toast` are not announcement mechanisms; a snackbar from the Material host is announced already.

## Font scale — through 200 %

- **Type is `sp` from the theme** (`MaterialTheme.typography.bodyLarge`); never `dp` for text, never `TextUnit` read from `LocalDensity` and divided back, never `fontScale` locked in the manifest or by overriding the configuration. Text scales up to **200 %** non-linearly on API 34+; both small and large text must stay readable.
- **Layouts survive 200 %**: rows switch axis (`FlowRow`, or `LocalConfiguration.current.fontScale` read in a composable only to choose the layout), content scrolls, **no `maxLines = 1` on text that matters**, no fixed `height` on a container of text — `heightIn(min = …)`.
- **Metrics that accompany text scale with it** (`with(LocalDensity.current) { 24.sp.toDp() }` for an icon beside a label).
- Test at the largest font and the largest *display size* in Settings; both together is the worst case.

## Touch targets, contrast, colour and motion

- **Targets ≥ 48 × 48 dp** — Material components enforce it through `LocalMinimumInteractiveComponentSize`; a custom clickable adds `Modifier.minimumInteractiveComponentSize()`, or pads inside the hit area. **Never disable the minimum** (`LocalMinimumInteractiveComponentSize provides Dp.Unspecified`) to tighten a layout.
- **Contrast 4.5 : 1 body, 3 : 1 large text and UI edges** in light, dark and dynamic colour — measure the *resolved* roles, not the seed colour ([`styling`](../styling/SKILL.md)).
- **Never colour alone** — an error is an icon and text beside the red; a chart series differs by pattern or label.
- **Reduce motion**: read the animator duration scale ([`animation`](../animation/SKILL.md)); at 0 skip parallax, auto-playing loops and large zooms.
- **Switch Access / keyboard**: every action reachable without touch; visible focus; `Modifier.focusable()` only on real controls.

## Rules

- A real control, never a tap handler on a `Box`; every interactive element has a name, a role and its state in semantics.
- Decorative content is `null`-described; informative content described; rows merged into one stop; headings marked.
- Every gesture-only operation has a custom action; results announced through a live region; focus moves only on a meaning change.
- `sp` text from the theme; layouts survive 200 % font scale; no `maxLines = 1` on content; no locked font scale.
- Targets ≥ 48 dp, minimum never disabled; contrast holds in light, dark and dynamic colour; state never by colour alone; reduced motion honoured.

## What NOT to do

- No `Modifier.clickable` on a bare `Box` with no role; no "button", "selected" or "disabled" inside a description.
- No `contentDescription = ""` on a clickable; no `contentDescription` on a decorative image.
- No `contentDescription` used as a test id, no id copied into a description.
- No `clearAndSetSemantics` over a tested row without moving the id; no `hideFromAccessibility` on an interactive element.
- No `dp` text, no `fontScale` clamp, no `LocalMinimumInteractiveComponentSize` opt-out.
- No accessibility claim made from code reading alone — it needs a TalkBack pass.

## Generation steps

1. Read the screen, the component library and the font handling already present; match them.
2. Replace gesture-only controls with real ones; add name, role, state; merge rows; mark headings.
3. Add custom actions for gestures, live regions for async results, focus moves for meaning changes.
4. Convert fixed sizes to `sp` and `heightIn`; add the axis switch for large font scale.
5. Add the state-not-by-colour and reduced-motion branches; check targets and contrast.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- A Compose test with `enableAccessibilityChecks()` per screen: no missing label, no target under 48 dp, no low contrast ([`unit-testing`](../unit-testing/SKILL.md)).
- Accessibility Scanner on each screen; a TalkBack pass at the largest font: each row is one stop, each action reachable, the error announced once.
- Settings → Accessibility with bold text, colour correction, remove animations and the largest display size on: nothing clips, nothing disappears.
- Device journeys with a screen reader → `qa-mobile-<stack>`.

## Handoffs

- Field-level error wiring → [`forms`](../forms/SKILL.md) · failure surfaces → [`error-handling`](../error-handling/SKILL.md)
- Motion setting → [`animation`](../animation/SKILL.md) · tokens and dynamic colour → [`styling`](../styling/SKILL.md)
- Ids → [`test-ids`](../test-ids/SKILL.md) · localized descriptions → [`languages`](../languages/SKILL.md)
- Accessibility declarations and store rules → [`mobile-<stack>:store-compliance`](../../../_shared/store-compliance/SKILL.md)
