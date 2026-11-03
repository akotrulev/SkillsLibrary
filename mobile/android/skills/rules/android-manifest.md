---
paths:
  - "**/AndroidManifest.xml"
  - "**/res/xml/*.xml"
---

<!-- mobile-android rules v1 (2026-11-03): manifest and platform config. Installed by /mobile-android:rules; edit to fit this project. -->

# Android manifest and platform-config standards

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**.

- TLS only: no `usesCleartextTraffic="true"`; cleartext and trust are decided in Network Security Config, with a recorded reason for any exception; no user CA outside `<debug-overrides>`. *blocker*
- Components are exported on purpose: `android:exported="true"` has a reason, and an exported `ContentProvider` or `Service` has a permission. *blocker*
- Declared permissions equal used permissions, with `maxSdkVersion` where one is retired. *major*
- No `MANAGE_EXTERNAL_STORAGE`, and no `READ_MEDIA_*` / `READ_EXTERNAL_STORAGE` to attach a photo; the photo picker serves it. *blocker for MANAGE, major otherwise*
- Background location is never in the same request as foreground location. *major*
- A foreground service declares its `foregroundServiceType` and the matching `FOREGROUND_SERVICE_*` permission. *blocker*
- `USE_FULL_SCREEN_INTENT` only in a calling or alarm app. *major*
- App Link filters are narrow `https` with `autoVerify`; no `pathPattern=".*"`; a custom scheme carries no secret. *major*
- Backup rules exclude databases, DataStore, the keyset and tokens. *major*
- One activity hosts the Compose tree. *minor*
- No `screenOrientation` lock, `resizeableActivity="false"` or `maxAspectRatio`. *major*
- Predictive back is on (`enableOnBackInvokedCallback`). *major*
- No `adjustPan` as the fix for a covered field. *major*
- `supportsRtl` is on; shipped locales are declared once (`generateLocaleConfig` or one `locale_config.xml`). *minor*
