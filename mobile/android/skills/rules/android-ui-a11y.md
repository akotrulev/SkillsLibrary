---
paths:
  - "**/*{Screen,Route,Content,Component,Composable,Theme,Activity,Dialog,Sheet,Navigation,NavHost}.kt"
  - "**/{ui,screen,screens,presentation,component,components,composable,composables,theme,navigation}/**/*.kt"
  - "**/res/layout*/*.xml"
  - "**/res/values*/strings.xml"
---

<!-- mobile-android rules v1 (2026-11-03): accessibility, test ids, strings, motion. Installed by /mobile-android:rules; keep the paths in step with android-ui.md. -->

# Android accessibility, test ids, strings and motion

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

## Accessibility

- A real control, never `clickable` on a bare `Box` with no role; every interactive element has an accessible name. *major*
- State lives in semantics, never in a description; decorative images are `null`-described. *minor*
- Text in `sp` from the theme; layouts survive 200 % font scale; no `fontScale` clamp, no `maxLines = 1` on content. *major*
- Touch targets ≥ 48 dp; the minimum is never opted out. *major*
- State never by colour alone. *major*
- A gesture-only operation has a custom action and a non-gesture alternative. *major*
- Motion honours the animator duration scale: a loop or large move has a static path at 0. *major*

## Test ids

- `testTagsAsResourceId = true` once, on the `setContent` root (and each window root the app owns), never per screen. *major*
- Every interactive element, list container and region state (`.Loading`, `.Error`, `.Retry`, `.Empty`, `.Stale`, the banner) carries a `Modifier.testTag`; Views use `android:id`. *major*
- Tags are static PascalCase `Screen.ElementType[.Qualifier]`; rows share one static tag; never an id, index, GUID, state or translated text. *major*
- `contentDescription` is never the id, and a tag is never a copied label. *major*

## Strings and formatting

- No user-visible literal in Kotlin or layouts; a ViewModel exposes typed state or a resource id. *major*
- Positional arguments, no concatenated sentences; plurals through `<plurals>`, never `count == 1`. *major*
- Money, numbers and dates are formatted at the edge with the current locale. *major*
- Layout uses start / end and auto-mirrored icons. *minor*

## Motion

- Animated transform or opacity is read in `graphicsLayer {}` or a lambda modifier, not in composition. *major*
- Animations have a `label` and take their specs from one set of motion tokens. *minor*
