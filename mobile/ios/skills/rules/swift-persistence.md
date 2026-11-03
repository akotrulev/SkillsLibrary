---
paths:
  - "**/*{Store,Storage,Keychain,Database,Persistence,Schema,Migration,MigrationPlan}.swift"
  - "**/{Persistence,Storage,Database,Store}/**/*.swift"
  - "**/*.xcdatamodeld/**"
---

<!-- mobile-ios rules v1 (2026-11-03): persistence. Installed by /mobile-ios:rules; edit the paths above to where this project keeps its models and stores. -->

# Swift persistence standards (SwiftData / Core Data / GRDB / Keychain)

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- One store per concern, matching the project's; SwiftData only on iOS 17+; never rewrite an existing Core Data or GRDB store. *major*
- Secrets live in the Keychain with a `…ThisDeviceOnly` class: no `kSecAttrAccessibleAlways*`, and never in `UserDefaults`, `@AppStorage`, `@SceneStorage`, a plist or a model column. *blocker*
- Keychain writes update before adding; a fresh install clears stale items. *minor*
- A biometric-gated secret uses `SecAccessControl` with `.biometryCurrentSet`, never a boolean `evaluatePolicy` result. *major*
- Every shipped schema is versioned with a migration stage, and every migration has a test on an on-disk store; no `eraseDatabaseOnSchemaChange` in a release build. *blocker*
- No string-built SQL in GRDB; bound arguments only. *blocker*
- Model objects never cross actors; background work uses `@ModelActor` or a background context. *major*
- `UserDefaults`, file-timestamp and disk-space use is declared in `PrivacyInfo.xcprivacy`. *major*
- Private files carry file protection; regenerable files are excluded from backup; caches sit in `Caches` and are bounded. *major*
- No `@Query` over an unbounded table into a list that renders every row. *major*
- Offline writes queue with an idempotency key, replay in order through the one client, and show as pending or failed. *major*
- A store that fails to open, or a full disk, degrades to memory with one notice, never a crash; a secret is never moved to a weaker store. *major*
- Logout clears the store, the caches and the Keychain items. *major*
