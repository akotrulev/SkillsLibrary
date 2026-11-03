---
paths:
  - "app/**/*.tsx"
  - "src/app/**/*.tsx"
  - "**/*.{native,ios,android}.tsx"
---

<!-- mobile-react-native rules v1 (2026-11-03): forms and languages. Installed by /mobile-react-native:rules; widen the paths above to this project's component folders. -->

# React Native forms and languages

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- React Hook Form + one Zod schema per form, type inferred; a `Controller` per input; no `useState` per field, no form state in a store. *major*
- `mode: 'onBlur'`; no validation per keystroke; async rules debounced and cancellable. *minor*
- Every input has a label (never only a placeholder), `inputMode`, `autoComplete`, `textContentType` and `returnKeyType`; a password never blocks the password manager with `autoComplete="off"`. *major*
- One keyboard handler: a scroll container with `keyboardShouldPersistTaps="handled"`; no `KeyboardAvoidingView` nested in a scroll view beside another. *minor*
- Submit is disabled while pending; a replayable write carries an idempotency key; a failed submit never clears the form. *major*
- Server errors land on fields with `setError`, the rest on `root` and the banner. *major*
- Formatting is always locale-aware; localized text is opt-in, and a language ships only with a complete catalog. *minor*
- One i18n library; keys are stable ids; plurals and interpolation are ICU in the catalog, never string concatenation for a sentence, plural or list. *major*
- `Intl` objects are hoisted, never created in render or `renderItem`; money never takes its currency from the locale or a fixed separator. *major*
- Logical styles (`start` / `end`), no `left` / `right` in a shared component; the RTL flip reloads. *minor*
- No raw key visible in a release build when a translation is missing. *major*
- The language comes from `getLocales()`, never a `Platform.OS` guess; native strings are localized through config plugins. *minor*
