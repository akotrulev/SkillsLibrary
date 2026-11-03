---
paths:
  - "app/**/*.tsx"
  - "src/app/**/*.tsx"
---

<!-- mobile-react-native rules v1 (2026-11-03): Expo Router routes. Installed by /mobile-react-native:rules; edit the paths above to where this project's route files live. -->

# Expo Router route standards

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Native navigators only: `Stack` and native tabs, no JS stack; no custom JS header where the native header options cover it. *major*
- The native-tabs import matches the SDK (`unstable-native-tabs` on 57, `native-tabs` on 58); no more than 5 native tabs on Android. *major*
- Params are validated with a schema at the screen boundary and carry ids only: no object, token or PII in a param. Screen-scoped state is a typed route param. *major*
- `<Link href>` for in-app navigation, `router.*` for the result of logic; never `onPress` + `router.push` on a `View`. *major*
- Modals and sheets are routes. *minor*
- A guard is client UX, never authorization, and never treats `loading` as signed out; a link that needs sign-in enters the protected layout and resumes after it. *major*
- The root layout exports an `ErrorBoundary`, and so does each independently failing route; widgets get their own `react-error-boundary`. Each reports a reference id and offers retry. *major*
- i18n is initialised before the first render. *major*
- `+native-intent` rewrites known legacy paths and drops what it does not recognise. *minor*
- An OTA reload prompts once and never runs over unsaved work; no unguarded `Updates.reloadAsync()`. *major*
