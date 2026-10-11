---
name: offline-and-storage
description: Use when an Expo SDK 57 app must persist anything — expo-secure-store for secrets, MMKV 4 createMMKV() for preferences, expo-sqlite / op-sqlite for relational data, TanStack Query cache persistence, an offline mutation queue, sync and conflicts. Triggers "where do I store the token", "work offline", "persist the cache", "MMKV v4". Do NOT use for the request layer (`mobile-react-native:networking`) or the storage-full UI (`-error-handling`).
---

# React Native — Offline and Storage

Owns **what is written to the device, where, and how it syncs back**: the storage ladder, secrets, the persisted Query cache, the offline mutation queue, sync and conflict policy. When a write fails because the disk is full, the **degradation** (fall back to memory, tell the user) is [`error-handling`](../error-handling/SKILL.md)'s; this skill makes the write fail loudly and typed.

## Version lane

| Concern | Primary (SDK 57) | Notes |
|---|---|---|
| `expo-secure-store` | SDK-bundled | Keychain (iOS) · Keystore-wrapped `SharedPreferences` (Android); small values only |
| MMKV | **4** (`react-native-mmkv` + `react-native-nitro-modules`) | `createMMKV()`, not `new MMKV()`; `remove()`, not `delete()`; RN ≥ 0.75, New Architecture |
| SQLite | `expo-sqlite` 18 or `op-sqlite` 18 | Match what the project has; `expo-sqlite` is the default |
| `@react-native-async-storage/async-storage` | legacy | Existing projects only; async, unencrypted; migrate hot paths to MMKV |
| WatermelonDB | **stale** — no release since 2025-04 | Flag it; do not start a project on it; a project on it gets a migration note, never a silent rewrite |
| TanStack Query persistence | `@tanstack/react-query-persist-client` | Persister over MMKV or AsyncStorage |
| `[SDK58]` / Floor 54 | same libraries | MMKV 4 on a floor project still needs RN ≥ 0.75 — fine on SDK 54 |

Detect first: `react-native-mmkv` major (3 → `new MMKV()` is correct for v3; never flag a v3 project for lacking `createMMKV`, and say a v4 move is the migration skill's), the SQLite library, any persister, and whether the app already has a sync backend.

## When to use

- "Where do I store this?" — token, preference, draft, cache, relational data
- Persisting the Query cache; showing data while offline
- An offline write queue; sync after reconnect; conflicts
- Choosing `expo-sqlite` vs `op-sqlite` vs MMKV

## When NOT to use

- Calling the API, timeouts, retries → [`networking`](../networking/SKILL.md)
- The disk-full banner, memory fallback, offline indicator → [`error-handling`](../error-handling/SKILL.md)
- Zustand store shape → [`architecture`](../architecture/SKILL.md)
- Auth provider and credentials manager → `auth0-react-native`
- Privacy manifest, backup exclusion rules → [`mobile-<stack>:store-compliance`](../../../_shared/store-compliance/SKILL.md); encryption policy → [`mobile-<stack>:security`](../../../_shared/security/SKILL.md)
- Native Swift / Kotlin storage → `mobile-ios:offline-and-storage` / `mobile-android:offline-and-storage`
- Web `localStorage` / IndexedDB → `fe-react:pwa`

## The storage ladder

| Data | Store | Never |
|---|---|---|
| Access token, refresh token, API key issued to the user, biometric-gated secret | **`expo-secure-store`** (only) | MMKV, AsyncStorage, Zustand `persist`, a file |
| Preferences, flags, onboarding state, small client state, a Zustand `persist` backend | MMKV 4 | secrets or PII |
| Relational or large data, queries, an offline dataset | `expo-sqlite` / `op-sqlite` | JSON blobs of lists in MMKV |
| Server data shown offline | persisted TanStack Query cache | a hand-copied store |
| Binary files, images, downloads | `expo-file-system` in the cache or document directory | the database |
| An encrypted large cache | MMKV with an encryption key **held in `expo-secure-store`** | a key in code or `EXPO_PUBLIC_*` |

**Secrets only in `expo-secure-store`.** Nothing sensitive in `UserDefaults`, `SharedPreferences`, AsyncStorage, plain MMKV, logs or the bundle ([`mobile-<stack>:security`](../../../_shared/security/references/react-native.md) §1, §3).

```ts
import * as SecureStore from 'expo-secure-store';

export async function saveRefreshToken(token: string): Promise<void> {
  await SecureStore.setItemAsync('auth.refreshToken', token, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function readRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync('auth.refreshToken');
}
```

- Values ≤ ~2 KB; keys use `[A-Za-z0-9._-]`. Access tokens live in memory; only the refresh token is persisted.
- `AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY` only when background refresh needs it; record why.
- `requireAuthentication: true` gates a read behind biometrics — a biometric **boolean** from `expo-local-authentication` followed by an unprotected read is not protection ([`device-features`](../device-features/SKILL.md)).
- Keychain items survive an iOS reinstall; **clear them on first launch after install** when the app records its own first-run flag in MMKV.
- Tokens stay out of MMKV even "encrypted" unless the key is in secure-store and the reason is recorded.

## MMKV 4

```ts
import { createMMKV } from 'react-native-mmkv';

export const preferences = createMMKV({ id: 'preferences' });

preferences.set('theme', 'dark');
const theme = preferences.getString('theme');
preferences.remove('theme');
```

- **`createMMKV()`**, never `new MMKV()` (v3). One instance per concern, created at module level in its own file and imported — a single `id` is not created twice. Install `react-native-nitro-modules` beside it; run a development build, **not Expo Go**.
- `delete` → `remove` (returns a boolean); `set` throws a typed error if the value cannot be written — catch **at the repository boundary**, not per call, and hand it to [`error-handling`](../error-handling/SKILL.md).
- MMKV is **synchronous and fast, but not free**: no multi-megabyte JSON on the JS thread during a gesture. Large structures belong in SQLite.
- Hooks (`useMMKVString`, `useMMKVBoolean`, `useMMKVKeys`) read reactively for preferences; stores read it through `persist`'s storage adapter ([`architecture`](../architecture/SKILL.md)).
- Encryption: `createMMKV({ id, encryptionKey })` with a key generated once and stored in secure-store; never a literal.
- Drop 32-bit Android ABIs from `reactNativeArchitectures` if the build complains (MMKVCore 2 dropped them).

## SQLite

```ts
import * as SQLite from 'expo-sqlite';

const database = await SQLite.openDatabaseAsync('app.db');
await database.execAsync('PRAGMA journal_mode = WAL;');
await database.runAsync('INSERT INTO orders (id, title, updated_at) VALUES (?, ?, ?)', id, title, updatedAt);
const rows = await database.getAllAsync<OrderRow>('SELECT id, title FROM orders WHERE archived = 0 ORDER BY updated_at DESC');
```

- **Async API only** — `openDatabaseAsync`, `runAsync`, `getAllAsync`; the synchronous API blocks the JS thread and is for tooling.
- **Parameterised statements** always; no string-built SQL (injection and plan-cache cost).
- **Migrations are versioned**: `PRAGMA user_version`, one ordered list of steps, each in a transaction (`withTransactionAsync`); never edit a shipped step. The migration runs once at startup before the first query, behind the splash.
- **`op-sqlite`** when the project needs SQLCipher encryption, JSI speed on large result sets or sqlite-vec; the two have different APIs — do not mix in one app.
- A reactive ORM (Drizzle with `expo-sqlite`) is the project's choice; one data-access module hides the library from screens. Read it before adding another.
- **WatermelonDB is stale** (last release 2025-04): do not scaffold it; where it exists, keep it, pin it, note the migration path to SQLite + Query persistence, and never claim New Architecture support the project has not proven.
- Schema design depth, indexes and sync-table shape → the `data` plugin (SQLite section) — an on-device schema is still a schema.

## Persisting the Query cache — show last known data

```ts
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';
import { createMMKV } from 'react-native-mmkv';

const cacheStorage = createMMKV({ id: 'query-cache' });
const persister = createSyncStoragePersister({
  storage: {
    getItem: (key) => cacheStorage.getString(key) ?? null,
    setItem: (key, value) => cacheStorage.set(key, value),
    removeItem: (key) => void cacheStorage.remove(key),
  },
});

export function QueryProvider({ children }: { children: ReactNode }) {
  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister,
        maxAge: 1000 * 60 * 60 * 24,
        buster: appVersion,
        dehydrateOptions: { shouldDehydrateQuery: (query) => query.meta?.persist === true },
      }}
    >
      {children}
    </PersistQueryClientProvider>
  );
}
```

- **Opt in per query** (`meta: { persist: true }`) — a persister writes whatever a response held. Never persist account, payment, health or token-bearing queries ([`mobile-<stack>:security`](../../../_shared/security/references/react-native.md) §3).
- `gcTime` ≥ `maxAge` or the persisted entry is collected first; `buster` ties the cache to a build so a shape change does not hydrate stale data; a Zod parse on hydrate drops drifted entries.
- Restored data is shown **marked stale** and revalidated on foreground and reconnect ([`networking`](../networking/SKILL.md)); the stale marker UI is [`error-handling`](../error-handling/SKILL.md)'s.
- Clear the cache and user tables **on sign-out** and on account deletion.

## Offline writes — the mutation queue

Use TanStack's persisted mutations before writing a queue by hand:

- `networkMode: 'online'` pauses a mutation offline; persist the mutation cache (`dehydrate` `mutations`) and call `resumePausedMutations()` after restore.
- Register `mutationFn` by **key** with `queryClient.setMutationDefaults` so a restored mutation can run after a restart.
- Each queued write carries a stable **idempotency key** created when the user acted.
- **Order matters**: writes to one entity replay in order (a `scope: { id }` on the mutation serialises them); an update to a not-yet-created entity waits on the create.
- Surface the queue: count of pending writes, a per-item "not synced" state, a retry control — no silent drop and no silent success ([`error-handling`](../error-handling/SKILL.md)).
- Poison items (a `4xx` on replay) leave the queue as a *failed* item the user can edit or discard; they do not block everything behind them.

A bespoke SQLite outbox is justified only when the queue must outlive cache clears, carry binary payloads or sync in a background task ([`device-features`](../device-features/SKILL.md) `expo-background-task`). It is one table `(id, entity, operation, payload, idempotency_key, status, attempts, created_at)` and one drain function — not a framework.

## Sync and conflicts — decide, then write it down

| Policy | Use when |
|---|---|
| **Server wins** | The data is reference data, or the user cannot edit it offline |
| **Last write wins** (`updated_at`) | Low-stakes single-writer data; accept that a concurrent edit is lost |
| **Version / ETag check** (`If-Match`, `409`) | Default for user-authored records — the server rejects a stale write and the client shows both versions |
| **Field-level merge** | Different fields edited on two devices |
| **CRDT** | Collaborative text or counters only — a library decision, not a default |

Record the chosen policy per entity in the feature's doc. A `409` keeps the user's input and offers *keep mine / take theirs / merge* ([`error-handling`](../error-handling/SKILL.md)). Pull sync uses a server cursor (`updated_since`), never "fetch everything" on each launch; deletes are tombstones until every client has seen them. Time comes from the server where order matters — device clocks drift.

## Rules

- Secrets only in `expo-secure-store`; refresh token persisted, access token in memory.
- MMKV 4 through `createMMKV()`; `remove()`; development build; one module-level instance per concern.
- Relational or large data in SQLite, async API, parameterised, versioned migrations.
- WatermelonDB is stale: never scaffolded; flagged where found.
- The Query persister is opt-in per query, version-busted, and cleared at sign-out.
- Offline writes carry idempotency keys, replay in order per entity and surface their state.
- Every entity has a recorded conflict policy; default is a version check.
- Writes can fail (disk full, quota): they throw a typed error at one boundary; the degradation is `error-handling`'s.
- No storage call on a UI-critical path that blocks a frame; nothing sensitive in backups unless the platform class is reviewed ([`mobile-<stack>:store-compliance`](../../../_shared/store-compliance/SKILL.md)).

## What NOT to do

- No token, password or PII in AsyncStorage, MMKV, Zustand `persist`, SQLite plaintext or a file.
- No `new MMKV()` on a v4 project; no `.delete()`; no MMKV in Expo Go.
- No encryption key in source, `app.json` or `EXPO_PUBLIC_*`.
- No `expo-sqlite` synchronous API in app code; no string-concatenated SQL; no edited shipped migration.
- No persisting the whole Query cache by default; no persisted query with a secret.
- No hand-rolled offline queue beside TanStack's persisted mutations without a recorded reason.
- No new project on WatermelonDB.
- No "last write wins" chosen by omission; no unbounded cache growth (set `maxAge`, size caps, an eviction rule).
- No data left behind after sign-out.

## Generation steps

1. Inventory what the feature stores; classify each datum by the ladder above.
2. Detect MMKV major, SQLite library, persister, existing sync.
3. Secrets → secure-store module; preferences → MMKV module; relational → SQLite module with migrations.
4. Add Query persistence with opt-in `meta`, `buster`, `maxAge`, and the sign-out purge.
5. Offline writes: mutation defaults by key, idempotency keys, ordered scope, a visible queue state.
6. Record the conflict policy per entity; write the `409` path.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Typecheck and lint with the project's scripts clean; `npx expo-doctor` clean (a library not in the SDK's version set).
- Device: write in airplane mode → item shows "not synced"; reconnect → it replays once; kill the app mid-queue → it resumes.
- Sign out → secure-store, MMKV user keys, SQLite user tables and the persisted cache are empty.
- Fill the disk (or force the typed error) → the write fails without a crash; behaviour is `error-handling`'s.
- Dev-side tests with fakes for the native modules: `mobile-react-native:component-testing`.

## Handoffs

- Request layer, retries, idempotency → [`networking`](../networking/SKILL.md) · degradation, banner, stale → [`error-handling`](../error-handling/SKILL.md)
- Store shape → [`architecture`](../architecture/SKILL.md) · biometrics, file picking → [`device-features`](../device-features/SKILL.md)
- Threat model, backups → [`mobile-<stack>:security`](../../../_shared/security/SKILL.md), [`mobile-<stack>:store-compliance`](../../../_shared/store-compliance/SKILL.md)
- Native module for a storage gap → [`native-modules`](../native-modules/SKILL.md)
