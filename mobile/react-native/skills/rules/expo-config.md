---
paths:
  - "**/app.json"
  - "**/app.config.{ts,js,mjs,cjs}"
  - "**/eas.json"
  - "**/plugins/**/with*.{ts,js}"
  - "modules/*/{ios,android}/**"
  - "{ios,android}/**"
---

<!-- mobile-react-native rules v1 (2026-11-03): Expo config, config plugins, native folders. Installed by /mobile-react-native:rules; edit to fit this project. -->

# Expo config and native change standards

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Under CNG, `ios/` and `android/` are generated: never hand-edit them; every native change is a config plugin or a local Expo module. *blocker*
- A config plugin is idempotent, tested as a pure function, and uses a typed mod, never `withDangerousMod` where one exists. *major*
- No secret in `app.json`, `extra`, `eas.json` env or `EXPO_PUBLIC_*`; they ship in the bundle. *blocker*
- TLS only: `usesCleartextTraffic` or `NSAllowsArbitraryLoads` only with a recorded reason. *blocker*
- Declare only the permissions the app requests; each purpose string says what it is used for and is localized. *major*
- New Architecture stays on; the React Compiler is never toggled as a side effect. *major*
- Links: verified https (`associatedDomains`, `autoVerify` intent filters) over a custom scheme, with narrow paths, never `/`. *major*
- Native code ships by a new build, never OTA; the runtime version moves with the SDK. *major*
- A development build, not Expo Go, for an app with native dependencies; rebuild it after a native dependency change. *major*
- A native module: narrow, typed, async; arguments validated natively; no main-thread I/O, no secret logged. *major*
- A native dependency is maintained, New-Architecture compatible and passes `npx expo-doctor`. *major*
- A Release-candidate dependency (NativeWind v5) is a recorded decision. *minor*
