---
paths:
  - "**/src/test*/**/*.kt"
  - "**/src/*Test/**/*.kt"
---

<!-- mobile-android rules v1 (2026-11-03): tests. Installed by /mobile-android:rules; edit to fit this project. -->

# Android dev-side test standards

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- JUnit 4 and fakes; JUnit 5 only where its Android plugin is present; no mock framework added, and no mock of Room, DataStore, Retrofit, a repository or a ViewModel. *major*
- Time, ids, randomness, configuration and dispatchers enter through the constructor; no interface created only for a test. *major*
- `runTest` with `StandardTestDispatcher`, advancing the clock explicitly; `UnconfinedTestDispatcher` carries a reason. *major; minor for the dispatcher*
- No `Thread.sleep` or `delay` to make a test pass; tests are independent and order-free. *major*
- One behaviour per test, one expected value per assertion, never "this or that"; no `if` / `for` driving assertions, parameterize instead. *major*
- No `try` / `catch` in a test body: `assertFailsWith`, or the exception reaches the runner. *major*
- No `!!` where `requireNotNull` / `assertNotNull` would name the value. *minor*
- Names state behaviour; test data with four or more fields comes from a builder. *minor*
- Compose tests use the v2 APIs, test one stateless screen with hand-built state, and wait for idle before asserting launched work. *major*
- Screenshot tests cover single composables, never whole screens, and never replace an assertion. *minor*
- A Room migration test runs the real database against the exported schemas. *major*
- No tests of getters, DTOs or forwarding wrappers; journeys, gestures and system dialogs belong to `qa-mobile-<stack>`. *minor*
- New code ships with tests covering at least 80% of the branches it wrote, measured with Kover; only an asserting test counts. *major*
