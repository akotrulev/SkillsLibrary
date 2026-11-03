---
paths:
  - "**/src/{common,android,ios,apple,native,jvm,desktop,js,wasmJs}Main/**/*.kt"
  - "**/src/commonTest/**/*.kt"
---

<!-- mobile-android rules v1 (2026-11-03): Kotlin Multiplatform. Installed by /mobile-android:rules; edit to fit this project. -->

# Kotlin Multiplatform standards

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. These apply only where the project has multiplatform modules.

- Share logic by default; share UI only by an explicit, recorded decision. *major*
- No Android type (`Context`, `Activity`, `Uri`, any `android.*` import) in `commonMain`. *major*
- No Hilt or Dagger in a shared module: `@HiltViewModel` and `@Inject` modules stay out of `commonMain`. *blocker*
- DI in shared code is Koin, Metro or manual, and constructor-injected. *major*
- A platform call is an injected interface, not an `expect` / `actual` for everything. *major*
- No secret in shared storage. *blocker*
- Navigation stays per platform unless Compose Multiplatform owns the UI; no hand-rolled shared router. *major*
- Swift export is labelled Alpha and never switched on in a shipping app for being newer; the Objective-C export framework is the default. *major*
- The exposed iOS surface is deliberate; the Swift consumer is `mobile-ios`'s, never written here. *minor*
- The shared Ktor client sets `HttpTimeout`, a bounded `HttpRequestRetry` and a single-flight `Auth`. *major*
- Shared logic has `commonTest` tests with fakes. *major*
