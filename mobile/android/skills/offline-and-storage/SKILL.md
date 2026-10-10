---
name: mobile-android-offline-and-storage
description: Use when an Android app must persist data — Room 3 (KSP, SQLiteDriver) for new code and Room 2.8 as a lane, DataStore, Keystore + Tink in place of the deprecated EncryptedSharedPreferences, backup rules, WorkManager sync, Paging 3, offline-first repositories. Triggers "where do I store this", "migrate the schema", "token storage", "works offline". Do NOT use for fetch mechanics (`mobile-android-networking`) or the offline UI (`-error-handling`).
---

# Android — Offline and Storage

Owns **where data lives on the device and how it syncs**: the database, preferences, secrets, files and caches, and the offline-first repository that stitches them to the network. The failure *UI* is `mobile-android-error-handling`'s; the request is [`networking`](../networking/SKILL.md)'s; this skill owns the **degradation** (a full disk, a corrupt database, a wiped cache). Security rules are [`mobile-shared-security`](../../../_shared/security/references/android.md) § 3–4; sibling: [`mobile-ios-offline-and-storage`](../../../ios/skills/offline-and-storage/SKILL.md).

## Version lane

| Concern | Primary | Brownfield / lane |
|---|---|---|
| Database | **Room 3.0** (`androidx.room3:room3-runtime` / `room3-compiler`, 3.0.3) — **KSP only**, `suspend` / `Flow` DAOs, a `SQLiteDriver` is required | **Room 2.8** (`androidx.room`) `[Room2]` — correct for an existing app; coexists with Room 3 (own group id); migration is `mobile-android-migration` |
| Room integrations | Paging, Rx, Guava, LiveData are **not built in** — separate `room3-paging` / `-rxjava3` / `-guava` / `-livedata` converter artifacts | Room 2.8 has them built in |
| Preferences | **DataStore** (Preferences or Proto) | Existing plain `SharedPreferences` for non-secret flags — migrate with `SharedPreferencesMigration`, not as a side effect |
| Secrets | **Android Keystore key, or Tink `Aead` with a Keystore-wrapped keyset** | `EncryptedSharedPreferences` / `EncryptedFile` / `MasterKey` — **deprecated: flagged and migrated, never written in new code** |
| Background sync | WorkManager | Same |
| Large lists | Paging 3 | Same |
| KMP | Room, DataStore shared in `commonMain` `[KMP]` | [`kotlin-multiplatform`](../kotlin-multiplatform/SKILL.md) |

**A project with `androidx.room` imports is a Room 2.8 project — do not rewrite it to Room 3 as a side effect.** `kapt` is never added for Room; Room 2.8 on KSP is the lane.

## When to use

- Choosing where a value goes; adding a table, DAO or migration
- Storing a token, a key or other secret
- "It must work offline", an outbox of pending writes, sync on reconnect
- Caching responses, images, a draft
- Replacing `EncryptedSharedPreferences`

## When NOT to use

- The HTTP call, retries, refresh logic → [`networking`](../networking/SKILL.md)
- Offline indicator, stale marker, banner → `mobile-android-error-handling`
- State ownership → [`architecture`](../architecture/SKILL.md)
- Long-running, foreground, exact-time work → `mobile-android-system-integration`
- Room 2 → 3, `EncryptedSharedPreferences` migration steps → `mobile-android-migration`
- Another stack → `mobile-ios-offline-and-storage`, `mobile-react-native-offline-and-storage`

## Where does it go?

| Data | Home | Notes |
|---|---|---|
| Relational / queryable / large, user data | **Room** | Source of truth for lists the app shows offline |
| Small typed settings (theme, last tab, "pre-prompt shown") | **DataStore** | Never `SharedPreferences` in new code |
| Tokens, API keys the user owns, any secret | **Keystore-backed** (Tink `Aead` over DataStore, or a Keystore key) | Never plain DataStore, Room, files or logs |
| Downloaded files, images | `filesDir` (durable) / `cacheDir` (evictable) | Cache is wiped under pressure — rebuild it |
| User-visible documents | MediaStore or SAF | [`device-features`](../device-features/SKILL.md) |
| Ephemeral screen state | `SavedStateHandle` / `rememberSaveable` | Survives process death, not a reinstall; never a secret |

Secrets are **never** `BuildConfig`, resources or `assets/`; they are public ([`mobile-shared-security`](../../../_shared/security/SKILL.md)).

## Room 3

```kotlin
@Entity(tableName = "orders")
data class OrderEntity(
    @PrimaryKey val id: String,
    val status: String,
    val total: Long,
    val updatedAt: Long,
    val syncState: SyncState,
)

@Dao
interface OrderDao {
    @Query("SELECT * FROM orders ORDER BY updatedAt DESC")
    fun observeAll(): Flow<List<OrderEntity>>

    @Query("SELECT * FROM orders WHERE syncState != :synced")
    suspend fun pending(synced: SyncState = SyncState.Synced): List<OrderEntity>

    @Upsert
    suspend fun upsert(orders: List<OrderEntity>)
}

@Database(entities = [OrderEntity::class, OutboxEntity::class], version = 3, exportSchema = true)
abstract class AppDatabase : RoomDatabase() {
    abstract fun orders(): OrderDao
    abstract fun outbox(): OutboxDao
}
```

```kotlin
@Provides
@Singleton
fun database(@ApplicationContext context: Context, @IoDispatcher io: CoroutineDispatcher): AppDatabase =
    Room.databaseBuilder<AppDatabase>(context, "app.db")
        .setDriver(BundledSQLiteDriver())
        .setQueryCoroutineContext(io)
        .build()
```

- Imports are `androidx.room3.*`; the Gradle setup is `ksp("androidx.room3:room3-compiler:…")` plus the Room Gradle plugin `id("androidx.room3")` with `room3 { schemaDirectory("$projectDir/schemas") }` — the schema directory is **committed**, one JSON per version.
- **A `SQLiteDriver` is required.** `AndroidSQLiteDriver()` uses the platform SQLite (version varies by OS); `BundledSQLiteDriver()` ships one known SQLite and is the choice when behaviour must match across devices and KMP targets. State which in the decision record; do not mix.
- **DAO functions are `suspend` or return `Flow`** (or a custom `@DaoReturnTypeConverter` type); a blocking DAO function is a compile error. Executors are gone — the dispatcher goes to the builder (`setQueryCoroutineContext`).
- **`Flow` DAOs are the observed read model** — the repository maps them to domain types; the screen sees changes without a refetch. `LiveData` and `Observable` return types are not used in new code.
- `InvalidationTracker.Observer` is gone — observe through `invalidationTracker.createFlow("orders")` or a `Flow` DAO.
- Transactions: `withWriteTransaction { … }` for multi-statement writes; one repository method = one transaction when it touches two tables. Raw access is `useReaderConnection` / `useWriterConnection` — for the rare query a DAO cannot express.
- **Entities are persistence types**, not domain types and not DTOs. A mapper per boundary, three small functions, not a mapping framework.
- **One database, one DAO per aggregate**, a singleton provided once; `enableMultiInstanceInvalidation()` only for a multi-process app.
- Never `fallbackToDestructiveMigration()` for user data; it is allowed for a **cache-only** database whose contents the network can rebuild, and says so in the database class doc.
- `Paging` needs the separate converter artifact: `@DaoReturnTypeConverters(PagingSourceDaoReturnTypeConverter::class)` on the DAO, `room3-paging` on the classpath.

Migrations, schema testing and the Room 2.8 lane are in [`references/room-migrations.md`](references/room-migrations.md).

## DataStore

```kotlin
val Context.settings: DataStore<Preferences> by preferencesDataStore(name = "settings")

class SettingsRepository @Inject constructor(@ApplicationContext private val context: Context) {
    val onboardingShown: Flow<Boolean> = context.settings.data
        .catch { if (it is IOException) emit(emptyPreferences()) else throw it }
        .map { it[ONBOARDING_SHOWN] ?: false }

    suspend fun markOnboardingShown() {
        context.settings.edit { it[ONBOARDING_SHOWN] = true }
    }

    private companion object {
        val ONBOARDING_SHOWN = booleanPreferencesKey("onboarding_shown")
    }
}
```

- **One `DataStore` instance per file per process** (the delegate guarantees it); two instances on one file corrupt it.
- Reads are `Flow`; writes are `suspend` and **transactional** (`edit`). No `runBlocking { dataStore.data.first() }` on the main thread — that is the `SharedPreferences` ANR rebuilt.
- A read that throws `IOException` degrades to defaults (above); a `CorruptionException` is handled with `ReplaceFileCorruptionHandler`.
- Proto DataStore with a `@Serializable` schema when the shape is structured; the schema change is a versioned migration like Room's.
- A stable key set in one file; keys are not secrets' names.

## Secrets — Keystore and Tink

`androidx.security:security-crypto` is **deprecated** (all APIs, since 1.1.0-beta01; Google points to platform APIs and the Keystore). **Never write `EncryptedSharedPreferences`, `EncryptedFile` or `MasterKey` in new code.** Secrets are sealed with a Tink `Aead` whose keyset is wrapped by a Keystore key, stored in DataStore; a decrypt failure means "signed out"; refresh tokens only in this store. The `SecretStore` class, direct-Keystore option and brownfield handling: [`references/keystore-and-secrets.md`](references/keystore-and-secrets.md).

## Backup

Declare `android:dataExtractionRules` and `android:fullBackupContent`; exclude databases, DataStore, keyset and tokens — Keystore keys never restore. [`references/keystore-and-secrets.md`](references/keystore-and-secrets.md).

## Files, caches and the OS

- `filesDir` is durable, `cacheDir` is evictable — **a missing cache file is a refetch, never a crash**; size-bound every cache; no secrets in `getExternalFilesDir`.
- Writes go through a temp file and an atomic rename; no disk or database call on the main thread (injected `IoDispatcher`; `StrictMode` disk detection in debug builds).

## Offline-first repositories

The pattern: **Room is the source of truth; the network refreshes it; the UI observes Room.**

```kotlin
class OrdersRepository @Inject constructor(
    private val api: OrdersApi,
    private val dao: OrderDao,
    private val outbox: OutboxDao,
    @IoDispatcher private val io: CoroutineDispatcher,
) {
    fun observe(): Flow<List<Order>> = dao.observeAll().map { rows -> rows.map(OrderEntity::toDomain) }

    suspend fun refresh(): Result<Unit> = suspendRunCatching {
        val remote = api.orders(page = 0, query = null)
        dao.upsert(remote.items.map { it.toEntity(SyncState.Synced) })
    }

    suspend fun placeOrder(draft: OrderDraft) = withContext(io) {
        val key = draft.idempotencyKey
        dao.upsert(listOf(draft.toEntity(SyncState.Pending)))
        outbox.enqueue(OutboxEntity(key = key, kind = OutboxKind.PlaceOrder, payload = draft.toJson()))
    }
}
```

- **Reads**: the screen collects `observe()`; `refresh()` runs on entry, on foreground and on reconnect; a failed refresh leaves the cached rows on screen and **marks them stale** — the data is shown, the banner says why (`mobile-android-error-handling`).
- **Writes** are applied locally with `SyncState.Pending`, and a row is added to an **outbox table** with a stable idempotency key created once per user intent. The UI reflects the pending state; it never pretends the server has it.
- **The outbox drains in a WorkManager `CoroutineWorker`** with a `NetworkType.CONNECTED` constraint, unique work (`enqueueUniqueWork(…, ExistingWorkPolicy.KEEP, …)`) and `BackoffPolicy.EXPONENTIAL`. Each item is sent with its key; success deletes the row, a `409` / `422` marks it **conflicted** for the user, a `5xx` leaves it for retry. The worker is idempotent — it can run twice. Foreground or exact-time work is `mobile-android-system-integration`.
- **Conflicts** have a stated policy per entity: server wins (default, overwrite the row), last-write-wins by `updatedAt`, or **ask the user** for fields where silent loss is unacceptable. Never merge silently.
- Deletes are a tombstone (`deletedAt`) until synced.
- **Paging**: Paging 3 with a `RemoteMediator` over Room 3 (`room3-paging`) when the list is long; otherwise a `Flow` DAO.
- A sync that must not run twice in parallel is unique work, not a mutex in memory.

## Storage failures degrade to memory

The repository, not the screen, catches `SQLiteFullException` / `IOException`, keeps the working set in memory, reports `StorageDegraded` and raises the banner — never a crash, never a silent loss. A cache database is rebuilt; a user-data database is never auto-wiped. [`references/keystore-and-secrets.md`](references/keystore-and-secrets.md).

## Rules

- Room 3 for new databases on KSP with a `SQLiteDriver`; Room 2.8 stays Room 2.8; never `kapt`.
- DAO functions `suspend` or `Flow`; entities separate from DTOs and domain types; one transaction per multi-table write.
- Every schema change has a migration and a committed schema JSON; no destructive fallback for user data.
- DataStore, not `SharedPreferences`, in new code; one instance per file; no main-thread blocking read.
- Secrets in Keystore-backed storage only; **no `EncryptedSharedPreferences` in new code**; a decrypt failure means signed out.
- Backup rules exclude databases, DataStore, keyset and tokens.
- Room (or the repository's source of truth) feeds the UI; the network refreshes it; stale data stays visible.
- Offline writes go through an outbox with idempotency keys, drained by unique WorkManager work.
- A storage failure degrades to memory and surfaces; it never crashes and never silently loses an edit.

## What NOT to do

- No `fallbackToDestructiveMigration()` on a user-data database.
- No `allowMainThreadQueries()`; no `runBlocking` on a DataStore or Room read.
- No `LiveData` / RxJava return types in Room 3; no `androidx.room` and `androidx.room3` mixed inside one database.
- No token, password or key in `SharedPreferences`, plain DataStore, Room, `BuildConfig`, files, logs or `SavedStateHandle`.
- No `EncryptedSharedPreferences`, `EncryptedFile`, `MasterKey` or `security-crypto` dependency in new code.
- No repository interface with one implementation to "mock Room" — Room runs in-memory in a test, or a fake DAO is the seam ([`unit-testing`](../unit-testing/SKILL.md)).
- No DTO as an entity; no entity in a composable.

## Generation steps

1. Read the existing storage (Room version, DataStore, `SharedPreferences`, `security-crypto`), the DI setup and the dispatcher qualifiers; detect Room 2 vs 3 and KSP.
2. Decide the home for each datum with the table above; list secrets.
3. Write entities, DAOs, the database class, the builder with the driver and dispatcher; commit the schema directory.
4. Write the migration for every version bump and its test ([`references/room-migrations.md`](references/room-migrations.md)).
5. Write the repository (Room as source of truth, `refresh`, outbox) and the `CoroutineWorker`.
6. Put secrets behind the Keystore/Tink store; add backup rules.
7. Add the degrade-to-memory path and the repository tests with a fake dispatcher and an in-memory database.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Build clean; detekt, ktlint and Android Lint pass; the schema JSON for the current version exists.
- Migration tests walk every version to current with `MigrationTestHelper` (Room 2 lane) or the Room 3 equivalent against the committed schemas.
- Airplane mode: the screen shows cached rows marked stale; a queued write drains after reconnect exactly once; the process killed mid-write leaves a consistent database.
- `adb shell run-as <package>` shows no plaintext token in `shared_prefs` or `databases`; a backup/restore dry run (`bmgr`) excludes them.
- Dev-side tests: [`mobile-android-unit-testing`](../unit-testing/SKILL.md).

## Handoffs

- Request, refresh, retries → [`networking`](../networking/SKILL.md)
- Stale marker, banner, storage-degraded copy → `mobile-android-error-handling`
- Biometric-bound keys → [`device-features`](../device-features/SKILL.md)
- Foreground services, exact work → `mobile-android-system-integration`
- Keystore, backup, WebView data rules → [`mobile-shared-security`](../../../_shared/security/SKILL.md)
- Room 2 → 3, `EncryptedSharedPreferences` replacement → `mobile-android-migration`
- Account deletion data purge → [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)
