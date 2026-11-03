---
paths:
  - "app/**/*.ts"
  - "src/app/**/*.ts"
  - "**/*.{native,ios,android}.ts"
---

<!-- mobile-react-native rules v1 (2026-11-03): networking, storage, offline. Installed by /mobile-react-native:rules; widen the paths above to this project's API, query, store and storage modules. -->

# React Native networking, storage and offline

Severity tags as in the core rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- One API module; base URL from `EXPO_PUBLIC_*` config; a timeout budget per endpoint class. *major*
- Retries live once, in the query client: at most 2 for idempotent reads, jittered, honouring `Retry-After`; none for a write without an idempotency key; none while offline; no retry loop inside `api()`. *major*
- No `fetch` in `useEffect` without an abort; no `.then()` that swallows an error into a blank region; no `Promise.all` spanning a critical and an optional call. *major*
- Query keys carry every dependency; `signal` is forwarded; dependent queries are `enabled`-gated. *major*
- A 401 runs one shared refresh, replays once, then re-authenticates in place; a 403 is permission-denied; never sign out straight off a 401. *major*
- No socket opened in render or left open in the background. *major*
- Refresh token in `expo-secure-store`, access token in memory; no encryption key in source, `app.json` or `EXPO_PUBLIC_*`. *blocker*
- MMKV 4 through `createMMKV()` and `remove()`, one module-level instance per concern, never in Expo Go. *minor*
- Relational or large data in SQLite: async API, bound parameters, versioned migrations; never edit a shipped migration. *blocker for concatenated SQL, else major*
- No new WatermelonDB. *minor*
- The Query persister is opt-in per query, version-busted, cleared at sign-out; never the whole cache by default, never a query holding a secret. *major*
- Offline writes carry idempotency keys, replay in order per entity and show their state; no hand-built queue beside TanStack's persisted mutations without a recorded reason. *major*
- Every entity has a recorded conflict policy, a version check by default; never "last write wins" by omission. *major*
- Caches are bounded (`maxAge`, size cap, eviction); sign-out leaves no data behind. *major*
- A storage write that fails throws a typed error at one boundary and degrades to memory with one notice. *minor*
- An unknown write outcome is reconciled, not reported as failed. *major*
