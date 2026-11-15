---
paths:
  - "**/*{Store,Storage,Vault,Database,DbContext,Settings,Migration,Repository,Cache}.cs"
  - "**/{Persistence,Storage,Data,Database,Migrations,Settings}/**/*.cs"
---

<!-- desktop-windows rules v1 (2026-11-15): persistence, secrets and settings. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its storage. -->

# Windows persistence standards

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- The store matches package identity: packaged apps use `ApplicationData`; unpackaged apps use a deliberate path (`LocalApplicationData`, or `GetForUnpackaged` on the SDK in use), never `ApplicationData.Current` with no identity and never a hard-coded path. *blocker*
- Settings are one typed service: versioned, written atomically, holding no secret. *major*
- Secrets live only in `PasswordVault` or DPAPI `CurrentUser`; never in settings, files, the registry in clear, logs or the package. *blocker*
- A `PasswordVault` miss is handled (it throws when empty) and reads happen after an opt-in sign-in. *major*
- Migrations run at startup behind a loading state with a failed body; the file is backed up first. *major*
- No `EnsureCreated` on a database that evolves; no in-memory provider (`UseInMemoryDatabase`, SQLite for another engine) standing in for the shipped one. *major*
- A `DbContext` is short-lived (one unit of work) and never held by a window or a view model. *major*
- No file, database or registry I/O on the UI thread; writes are atomic (temp file, then move). *major*
- Cache and data folders are right (`LocalCacheFolder` for the cache, `LocalFolder` for data); the cache has a size or age cap. *minor*
- Offline writes go to an idempotent outbox drained in order; cached data is shown as stale and offline with the persistent banner. *major*
- A path that arrives from outside is validated (canonicalized, inside the allowed root) before it is opened. *major*
- Unsaved work is autosaved or asked about; relaunch restores state; a storage failure is a recoverable, explained state. *major*
