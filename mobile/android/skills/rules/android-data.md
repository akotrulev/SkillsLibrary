---
paths:
  - "**/*{Dao,Database,Entity,Repository,DataSource,Api,Client,Interceptor,Authenticator,Store,Worker}.kt"
  - "**/{data,db,database,local,remote,network,storage,repository,sync}/**/*.kt"
  - "**/schemas/**/*.json"
---

<!-- mobile-android rules v1 (2026-11-03): data, storage and networking. Installed by /mobile-android:rules; edit the paths above to where this project keeps its repositories, Room and API code. -->

# Android data, storage and networking standards

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

## Storage

- New databases are Room 3 on KSP; Room 2.8 stays Room 2.8, and the two never mix in one database. DAOs are `suspend` or `Flow`. *major*
- Every schema change has a migration and a committed schema JSON; no `fallbackToDestructiveMigration()` on user data. *blocker*
- No main-thread Room or DataStore read: no `allowMainThreadQueries()`, no `runBlocking` on a read. *blocker*
- Entities, DTOs and domain types are separate; no entity in a composable. *minor*
- Settings are DataStore, one instance per file; no new `SharedPreferences`. *major*
- No `EncryptedSharedPreferences`, `EncryptedFile`, `MasterKey` or `security-crypto` in new code; an existing one is flagged, not rewritten in passing. *major*
- Secrets are Keystore-backed; a decrypt failure means signed out. *blocker*
- Room feeds the UI; a failed refresh keeps rows and marks them stale. *major*
- Offline writes go through an outbox with idempotency keys, drained by unique WorkManager work. *major*
- A storage failure degrades to memory and surfaces once; a user database is never auto-wiped. *major*

## Networking

- One client per API; no second HTTP or JSON library beside the one present. *major*
- `https` only; every request has connect, read, write and a per-endpoint-class call timeout. *major*
- Retries live in one place: ≤ 2 for reads, jittered, `Retry-After` honoured, none offline, none for a write without an idempotency key. *major*
- A decode failure is `Drifted` and renders as failed, never empty. *major*
- A `401` runs one shared, locked refresh, replays once and never loops; `403` is not `401`. *blocker*
- No logging interceptor in a release build. *blocker*
- A socket is open only while the screen is `STARTED`. *major*
- No one-implementation interface over Retrofit or Room "for testing"; a repository fake, `MockWebServer` or in-memory Room is the seam. *major*
