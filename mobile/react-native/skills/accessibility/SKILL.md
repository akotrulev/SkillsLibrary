---
name: accessibility
description: Use when a React Native screen must work with VoiceOver, TalkBack, large text and Reduce Motion — role / label / state props, the aria-* equivalents, focus and announcements, custom actions, touch targets, font scaling, contrast. Triggers "make this screen accessible", "VoiceOver reads the wrong thing", "text is cut off at large sizes", "announce the result". Do NOT use for scanning (`qa-mobile-typescript`), form errors (`-forms`) or motion mechanics (`-animation`).
---

# React Native — Accessibility

Standardises **authoring** accessible RN screens, targeting **WCAG 2.2 AA** as the baseline and the platform conventions of VoiceOver (iOS) and TalkBack (Android). The house rule: **real controls with the right role, label and state; never rebuild semantics from a bare `View`.** Web analog: [`fe-react:accessibility`](../../../../frontend/react/skills/accessibility/SKILL.md) — semantic-first, live announcements and focus management carry over; HTML, ARIA landmarks, `:focus-visible`, keyboard Tab order and skip links do not.

**Boundary — authoring, not scanning.** This skill makes the app accessible as it is built. *Proving* it on devices (a VoiceOver / TalkBack pass, Accessibility Inspector, Android Accessibility Scanner, journeys with a screen reader on) is `qa-mobile-typescript`'s. Several WCAG 2.2 criteria (target size, a non-drag alternative, accessible authentication, consistent help) are design decisions made first — `design/accessible-by-design` decides, this skill implements.

Design facts (type scale, contrast, touch target) come from `design/ui-ux-pro-max` (`--stack react-native`); where the corpus disagrees with this skill, the corpus wins.

## Version lane

| Concern | Primary (SDK 57 · RN 0.86) | Notes |
|---|---|---|
| Role / label / state | `role` + `aria-label` / `aria-disabled` / `aria-checked` / `aria-selected` / `aria-expanded` / `aria-busy` | The `aria-*` and `role` props are the current form; `accessibilityRole` / `accessibilityLabel` / `accessibilityState` are the older, still-supported equivalents — match what the codebase uses, never mix both on one element |
| Live regions | `aria-live` / `accessibilityLiveRegion` (**Android**), `AccessibilityInfo.announceForAccessibility` (iOS and Android) | iOS has no live-region prop; announce imperatively |
| Focus | `AccessibilityInfo.sendAccessibilityEvent(ref, 'focus')` | Moves the screen-reader cursor |
| Settings | `AccessibilityInfo.isScreenReaderEnabled`, `isReduceMotionEnabled`, `isBoldTextEnabled` + change listeners | Read live, remove listeners on cleanup |
| `[SDK58]` | no change | Native tabs and headers announce themselves — do not wrap them |
| Floor 54 | same props | Detect which prop family the project uses |

Detect first: the prop family in use (`role` vs `accessibilityRole`), the component library (React Native Paper, Tamagui, gluestack set roles themselves — use their props, don't layer a second), and whether any screen locks font scaling.

## When to use

- Labelling a control, giving it a role and state, grouping related content into one stop
- Focus and announcements after navigation, a modal, an async result or an error
- Touch targets, hit slop, large text, contrast, Reduce Motion
- Custom gestures that need an accessible alternative; reviewing a screen for screen-reader use

## When NOT to use

- Scanning, device screen-reader journeys, audits in CI → `qa-mobile-typescript` (peer)
- Validation message wiring on fields → [`forms`](../forms/SKILL.md) · the banner and failed regions → [`error-handling`](../error-handling/SKILL.md)
- Reanimated Reduce Motion mechanics → [`animation`](../animation/SKILL.md) · tokens and font loading → [`styling`](../styling/SKILL.md)
- Native Swift / Kotlin → `mobile-ios:accessibility` / `mobile-android:accessibility`

## Lean on the platform

Native controls already carry semantics. The moment you replace them you own them.

| Want | Use — not |
|---|---|
| A tap target | `Pressable` with `role="button"` and a label — never a `View` + `onTouchEnd`, never `TouchableWithoutFeedback` with no role |
| Navigate | `<Link href>` (Expo Router) with `role="link"` — not a `Pressable` calling `router.push` with no role |
| Text input | `TextInput` with a visible label and `aria-label` / `accessibilityLabel` — a placeholder is not a label |
| Switch, checkbox, radio | `Switch`, or `Pressable` with `role="checkbox"` / `"radio"` and `aria-checked` |
| A heading | `<Text role="heading">` — one per section; screen-reader users navigate by heading |
| Modal | a native modal / sheet (`ui-components`); focus moves in and returns on close |
| Tabs | the Expo Router tab navigator — it exposes `tab` roles and selected state itself |

## Role, label, state, value

```tsx
<Pressable
  role="button"
  aria-label="Add to cart"
  aria-disabled={!inStock}
  onPress={addToCart}
  style={styles.target}
  hitSlop={8}
  testID="Product.AddToCart"
>
  <CartIcon />
</Pressable>
```

- **Every interactive element has an accessible name.** Text children name a button on their own; an **icon-only control needs a label**. The label says what it **does** ("Add to cart"), not what it **is** ("Plus icon"), and never contains the role ("button") — the platform appends it.
- **Roles from the platform vocabulary**: `button`, `link`, `header`/`heading`, `image`, `imagebutton`, `search`, `switch`, `checkbox`, `radio`, `tab`, `tablist`, `adjustable`, `alert`, `text`, `none`. A decorative image is `role="none"` or `accessible={false}`; an informative one has `alt` / a label.
- **State is state, not label text.** Disabled, checked, selected, expanded and busy go in `aria-*` (or `accessibilityState`) so the platform says "dimmed", "selected", "expanded" in the user's language; "Menu, open" in a label is a bug.
- **Values** for sliders and progress: `aria-valuenow` / `valuemin` / `valuemax` / `valuetext` ("40 percent"); `role="adjustable"` where the control reacts to swipe up / down.
- **Hints** (`accessibilityHint`) only when the result is not obvious from name + role ("Opens your order history"); never restate the label.
- **Group** a row into **one stop** with `accessible` on the container and a composed label, so a screen reader doesn't read six fragments; keep inner buttons separate stops only if each is independently actionable (or expose them as `accessibilityActions`).
- **Hide what is not there**: `aria-hidden` / `importantForAccessibility="no-hide-descendants"` for an off-screen or covered tree (content behind a modal), never on something a user can reach.
- **Labels are translated** through the i18n layer ([`languages`](../languages/SKILL.md)); a `testID` is **never** the label and a label is never a `testID` ([`test-ids`](../test-ids/SKILL.md)).

## Focus and announcements

Native navigators move the screen-reader cursor on a push; everything else you must do.

- **A modal or sheet opening** moves focus to its title or first control; closing returns it to the trigger. On iOS a custom overlay needs `accessibilityViewIsModal` so VoiceOver ignores what is behind it; on Android hide the content behind with `importantForAccessibility`.
- **Programmatic focus** after a context change (reveal a panel, show an error summary, first invalid field on submit):

```tsx
const errorRef = useRef<View>(null);

useEffect(() => {
  if (!failed || errorRef.current === null) return;
  AccessibilityInfo.sendAccessibilityEvent(errorRef.current, 'focus');
}, [failed]);
```

- **Announce results that don't move focus** ("Order saved", "12 results"): `AccessibilityInfo.announceForAccessibility('Order saved')`. On Android `aria-live="polite"` on a persistent text node also works; use `"assertive"` / `role="alert"` for errors only. Don't announce on every keystroke or render.
- **Errors**: a field's error text is `role="alert"` and tied to the field ([`forms`](../forms/SKILL.md)); the error banner is `role="alert"` and announced, without stealing focus from the field being typed in ([`error-handling`](../error-handling/SKILL.md)).
- **Loading**: `aria-busy` on the region plus a visible indicator; announce completion, not progress.
- **Custom actions** for swipe-to-delete, drag handles, long-press menus and reorder: expose each as `accessibilityActions` + `onAccessibilityAction` so a screen-reader user has the same operations a sighted user has by gesture (WCAG 2.5.7).

```tsx
<Pressable
  accessibilityActions={[{ name: 'delete', label: 'Delete' }]}
  onAccessibilityAction={(event) => event.nativeEvent.actionName === 'delete' && remove(id)}
/>
```

- **Reading order** follows the visual order; fix it by changing the tree, not with `zIndex` tricks.

## Touch targets, text size, contrast, motion

- **Targets ≥ 44 × 44 pt (iOS) / 48 × 48 dp (Android)**, with at least ~8 pt between neighbours. Grow the hit area with `hitSlop` or padding instead of enlarging the glyph; `hitSlop` does not extend past a clipping parent.
- **Text scales with the system setting and is never locked.** No `allowFontScaling={false}`; at most a `maxFontSizeMultiplier` (≥ 2) on a fixed-height chrome element, with the layout checked at the largest sizes. Layouts grow — no fixed heights on text containers, no truncation of essential content; wrap, or switch a row to a column when `PixelRatio.getFontScale()` is high. Bold Text and Display Zoom must not break the layout.
- **Contrast** ≥ 4.5:1 for body text, 3:1 for large text and for UI component boundaries and icons that carry meaning, in **both** light and dark schemes; verify against the real token values ([`styling`](../styling/SKILL.md)).
- **No state by colour alone** — pair an error or selected state with an icon, text or shape.
- **Reduce Motion** is a hard floor: honour it with Reanimated's `ReduceMotion.System` and `useReducedMotion()`; auto-playing or looping motion has a pause control ([`animation`](../animation/SKILL.md) owns the mechanics).
- **Orientation and zoom**: don't lock orientation without a product reason; support pinch-to-zoom on content that is meant to be zoomed.
- **Time limits** and auto-advancing carousels are user-controlled or removable.

## Rules

- Every interactive element: a role, an accessible name that says what it does, state in `aria-*`, a target ≥ 44 pt / 48 dp, and a `testID`.
- Icon-only controls always carry a label; decorative images are hidden; informative ones are described.
- State is never in the label text; the role is never in the label.
- Headings are marked; related content is one stop; the reading order matches the visual order.
- Focus moves in and out of modals and returns to the trigger; results and errors are announced without stealing focus.
- Every gesture has an `accessibilityActions` alternative.
- Text scales; no `allowFontScaling={false}`; layouts survive the largest sizes.
- Contrast and non-colour cues hold in light and dark; Reduce Motion is honoured.
- One prop family per element (`role` + `aria-*`, or the older `accessibility*`), consistent with the project.

## What NOT to do

- No `View` + gesture handler as a button; no `Pressable` without a role and a name; no icon-only control without a label.
- No placeholder as the only label; no "button", "image of" or state words in a label.
- No `allowFontScaling={false}`, no fixed text-container heights, no clipped text at large sizes.
- No `accessible={false}` on something a user must reach; no `aria-hidden` on content that is on screen.
- No swipe-only or drag-only operation without `accessibilityActions`.
- No announcement per keystroke or per render; no focus stolen from a field by a banner.
- No colour-only error or selection; no contrast checked in light mode only.
- No second accessibility prop family mixed onto one element.

## Generation steps

1. Detect the prop family, the component library and any locked font scaling.
2. For each interactive element add role, name, state, target size and `testID` in one edit.
3. Add focus movement and announcements for every modal, async result and error.
4. Add `accessibilityActions` for every gesture-only operation.
5. Check the layout at the largest text size and in both colour schemes.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Dev-side: `getByRole('button', { name })` finds each control; `toBeDisabled`, `toHaveAccessibleName` and `accessibilityState` assertions hold ([`component-testing`](../component-testing/SKILL.md)).
- On devices (peer): VoiceOver and TalkBack read each screen in order with sensible names; the largest text size clips nothing; Reduce Motion removes decorative motion — `qa-mobile-typescript`.
- Lint: `eslint-plugin-react-native-a11y` through the project's ESLint config catches missing roles and labels as you type.

## Handoffs

- Scanning, screen-reader journeys, audits → `qa-mobile-typescript` (peer)
- Field-level errors → [`forms`](../forms/SKILL.md) · region states, banner → [`error-handling`](../error-handling/SKILL.md)
- Motion mechanics → [`animation`](../animation/SKILL.md) · tokens, font scale, contrast tokens → [`styling`](../styling/SKILL.md)
- Native menus and modals → [`ui-components`](../ui-components/SKILL.md) · ids → [`test-ids`](../test-ids/SKILL.md)
- WCAG 2.2 design decisions → `design/accessible-by-design`
