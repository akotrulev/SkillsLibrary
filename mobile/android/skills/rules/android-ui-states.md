---
paths:
  - "**/*{Screen,Route,Content,Component,Composable,Activity,Dialog,Sheet,ViewModel}.kt"
  - "**/{ui,screen,screens,presentation,component,components,composable,composables,form,forms}/**/*.kt"
---

<!-- mobile-android rules v1 (2026-11-03): data regions, failures and forms. Installed by /mobile-android:rules; keep the paths in step with android-ui.md. -->

# Android data regions, failures and forms

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

## Regions and failures

- Each data region renders loading, loaded, empty, failed, stale and offline, scoped to the region; chrome, search and filters survive. *major*
- A failure also raises one persistent banner: safe-area top, closed only by its 48 dp control, deduped and capped; never an error `Snackbar`, `Toast` or `Log`-only catch. *major*
- A timeout has its own body; a cancelled request renders nothing; offline is not a server error and offers no retry. *major*
- A failed refetch keeps the data and marks it stale; the screen revalidates on resume and reconnect. *major*
- A `401` re-authenticates in place, never a straight sign-out; `403` is permission-denied; an unsupported app version gets the forced-update screen. *major*
- Process death restores small state and reloads the rest. *major*
- An unknown write outcome is reconciled, not shown as failed; a third-party failure stays in its own region. *major*
- `NotFound` on a record is "gone", with no retry; empty is three kinds, never a generic "No data". *minor*

## Forms

- One draft in `uiState`, one pure validator, one submit guarded in the ViewModel (not only by `enabled`) with one idempotency key per draft. *major*
- One text-field API per form, `TextFieldState` or value-based; never a `remember { mutableStateOf("") }` copy of ViewModel state. *major*
- Every field sets its keyboard type and `ImeAction`; `Next` moves focus. *major*
- Errors appear on focus loss or submit, clear on edit, as text plus `isError`; server field errors land on their fields, unmapped ones at form level. *major*
- A secret field is never in `SavedStateHandle`, `rememberSaveable`, logs or analytics. *blocker*
- Autofillable fields declare `ContentType`. *major*
