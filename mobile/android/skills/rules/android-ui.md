---
paths:
  - "**/*{Screen,Route,Content,Component,Composable,Theme,Activity,Dialog,Sheet,Navigation,NavHost}.kt"
  - "**/{ui,screen,screens,presentation,component,components,composable,composables,theme,navigation}/**/*.kt"
---

<!-- mobile-android rules v1 (2026-11-03): Compose UI. Installed by /mobile-android:rules; edit the paths above to where this project keeps its composables. -->

# Jetpack Compose UI standards

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. Data regions, failures and forms are in `android-ui-states.md`; accessibility and test ids in `android-ui-a11y.md`.

- The screen composable takes the ViewModel and collects `uiState`; everything below is stateless, `modifier` first among optional parameters and applied once to the root; no ViewModel or `NavController` passed down. *major*
- State down, events up; business state never in `remember`, a list never in `rememberSaveable`. *major*
- No sort, filter, format, parse or I/O in a composable body; side effects only in the effect APIs. *major*
- `LaunchedEffect` keys are the values it reads (`Unit` carries a reason); every registration is disposed. *major*
- Unbounded content is a lazy list with a stable `key` (never the index) and `contentType` for mixed rows; no `LazyColumn` inside `Column(verticalScroll)`. *major*
- `@Stable` / `@Immutable` only where the promise is true, never to silence a report. *minor*
- Material 3 components, never imitations; Expressive only on material3 1.5 or an existing opt-in. *major*
- Screens read `MaterialTheme.*` tokens: no `Color(0x…)`, `14.sp` or shape literals. *major*
- Layout branches on the window size class, read once at the top, never on device type; wide windows get two panes or bounded width. *major*
- Edge-to-edge: `Scaffold` `innerPadding` applied, no `fitsSystemWindows`, `imePadding()` so the IME never covers the focused field. *major*
- Navigation: one library; `@Serializable` keys carry ids, never models or lambdas; screens take callbacks; a destination loads from its key; never driven by a ViewModel event or `LaunchedEffect(Unit)`. *major*
- Back is predictive: no `onBackPressed()` override; `BackHandler` enabled only while it has a job. *major*
- `@Preview` for reusable composables, covering states, no live data. *minor*
