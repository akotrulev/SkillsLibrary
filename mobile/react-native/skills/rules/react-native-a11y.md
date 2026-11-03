---
paths:
  - "app/**/*.tsx"
  - "src/app/**/*.tsx"
  - "**/*.{native,ios,android}.tsx"
---

<!-- mobile-react-native rules v1 (2026-11-03): accessibility, test ids, motion. Installed by /mobile-react-native:rules; widen the paths above to this project's component folders. -->

# React Native accessibility, test ids and motion

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Every interactive element has a role, a name saying what it does, state in `aria-*` and a target of at least 44 pt / 48 dp; no `View` + gesture handler as a button. *major*
- An icon-only control has a label; decorative images are hidden, informative ones described. No role, "image of" or state word in a label. *major*
- Text scales: no `allowFontScaling={false}`, no fixed text-container height, nothing clipped at the largest size. *major*
- Focus moves into and out of modals and returns to the trigger; results are announced without stealing focus, never per keystroke. Headings are marked; reading order matches the visual order. *major*
- Every gesture has an `accessibilityActions` alternative; no `accessible={false}` or `aria-hidden` on content a user must reach. *major*
- No state by colour alone; contrast holds in light and dark. *major*
- One accessibility prop family per element (`role` + `aria-*`, or `accessibility*`), as the project uses. *minor*
- Every interactive element, list container, region state and banner carries a `testID`, inline; no wrapper only to carry one, none on layout `View`s. *major*
- A `testID` is static PascalCase `Screen.ElementType[.Qualifier]`: never an index, GUID, record id, state value or translated string, never the accessibility label, never `nativeID`. *major*
- Rows share one static id (`Orders.Row`); the key, not the test id, is unique. *minor*
- Animate `transform` and `opacity` only, from Reanimated shared values on the UI thread; no JS-driver `Animated` or `setState` per frame. *major*
- With the Compiler on, shared values use `.get()` / `.set()`, never `.value`; no shared value in React state. *major*
- `withDelay` / `withSequence`, never `setTimeout` choreography. *minor*
- Reduce Motion is honoured (`ReduceMotion.System`, never `Never` on decorative motion); looping motion pauses and can be stopped; no state shown by motion alone. *major*
