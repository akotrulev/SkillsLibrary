---
paths:
  - "**/*{Store,Storage,Keychain,Database,Persistence,Schema,Migration,MigrationPlan,Document,Bookmark}.swift"
  - "**/{Persistence,Storage,Database,Store,Documents}/**/*.swift"
  - "**/*.xcdatamodeld/**"
---

<!-- desktop-macos rules v1 (2026-11-15): persistence, documents and files. Installed by /desktop-macos:rules; edit the paths above to where this project keeps its models and stores. -->

# Swift persistence standards (SwiftData / Core Data / GRDB / Keychain / documents)

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- One store per concern, matching the project's and shared by every window; never rewrite an existing Core Data or GRDB store. *major*
- Paths come from `FileManager` and the sandbox container, never a hard-coded `~/Library/...`. *major*
- Secrets live in the data protection keychain with a `…ThisDeviceOnly` class: never in `UserDefaults`, `@AppStorage`, `@SceneStorage`, a plist or a model column. *blocker*
- A biometric-gated secret uses `SecAccessControl` with `.biometryCurrentSet`, never a boolean `evaluatePolicy` result. *major*
- Every shipped schema is versioned with a migration stage, and every migration has a test on an on-disk store; no `eraseDatabaseOnSchemaChange` in a release build. *blocker*
- No string-built SQL in GRDB; bound arguments only. *blocker*
- Model objects never cross actors; background work uses `@ModelActor` or a background context and identifiers. *major*
- A store that fails to open, or a full disk, degrades to memory with one notice, never a `try!` crash at launch. *major*
- Security-scoped bookmarks are created with `.withSecurityScope`; every `startAccessing…` has one `stopAccessing…` in a `defer`. *major*
- Documents: new code on the 27 SDK uses `Document`, not `FileDocument`; reads and writes are `async` and off the main actor; edits register undo. *major*
- `UserDefaults` holds small non-secret preferences only; per-window state is `@SceneStorage` holding ids. *minor*
- No `@Query` over an unbounded table into a list that renders every row. *major*
- Offline writes queue with an idempotency key and show as pending or failed. *major*
- Logout clears the store, the caches and the Keychain items. *major*
