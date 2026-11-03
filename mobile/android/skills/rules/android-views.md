---
paths:
  - "**/*{Fragment,Adapter,ViewHolder,View}.kt"
  - "**/res/layout*/*.xml"
---

<!-- mobile-android rules v1 (2026-11-03): Views lane. Installed by /mobile-android:rules; edit the paths above to where this project keeps its Fragments and layouts. -->

# Android Views standards

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. A Views codebase is extended in Views; never rewrite a working screen to Compose as a side effect.

- Match the codebase's binding and navigation style; add Compose only through `ComposeView` and `AndroidView`. *major*
- New view access is ViewBinding: no `findViewById`, synthetics or `dataBinding` added to a ViewBinding project. *minor*
- A Fragment's binding is nulled in `onDestroyView` and never touched after. *major*
- Collect with `viewLifecycleOwner` inside `repeatOnLifecycle(STARTED)`; no `launchWhenStarted`, no `this` as the owner in `onCreateView`. *major*
- Lists are `ListAdapter` + `DiffUtil` on the domain id; `onBind` only assigns; no `notifyDataSetChanged`. *major*
- A `ComposeView` in a Fragment sets `DisposeOnViewTreeLifecycleDestroyed` before `setContent`. *major*
- `AndroidView` keeps state in `update` and releases in `onRelease`; no ViewModel captured in its factory. *major*
- The one-`uiState` rule holds: no `SharedFlow` or `Channel` event for navigation or errors, no state duplicated in a View field. *major*
- Back goes through `OnBackPressedDispatcher`; no `onBackPressed()` override. *major*
- No `Handler().postDelayed` for timing, no `AsyncTask`, no `Thread` + `runOnUiThread` for I/O. *major*
- Edge-to-edge insets are applied to the View that needs them; the IME never hides the focused field; no `adjustPan` hack. *major*
- Layouts carry no hard-coded text or `px`; actionable images have a `contentDescription`; targets ≥ 48 dp. *major*
- Every interactive View has a static snake_case `android:id` derived from its tag (`Login.EmailField` → `login_email_field`). *minor*
