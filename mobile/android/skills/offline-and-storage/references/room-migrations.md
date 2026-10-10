# Room — migrations, schema tests and the Room 2.8 lane

A schema change is a plan written **before** the first field changes. Room 3's migration-callback API (`SQLiteConnection` replacing `SupportSQLiteDatabase`) is confirmed on the release page; the exact signatures below are **re-checked against the "Migrate your database" page before use** — decision D28 records them as unconfirmed.

## The rule

- Every `@Database(version = N)` bump ships a migration from `N-1`, **and** the exported schema JSON for `N` is committed (`schemas/<db>/<N>.json`). A bump without both is a **blocker** for a user-data database.
- Prefer `@AutoMigration(from = N-1, to = N)` for additive changes (new nullable column, new table, rename with `@RenameColumn`). Write a manual `Migration` for data transforms, splits and merges.
- `fallbackToDestructiveMigration()` is allowed only on a database the network can fully rebuild, and the database class doc says so.

## Room 3 — manual migration

```kotlin
val Migration2To3 = object : Migration(2, 3) {
    override suspend fun migrate(connection: SQLiteConnection) {
        connection.execSQL("ALTER TABLE orders ADD COLUMN syncState TEXT NOT NULL DEFAULT 'Synced'")
        connection.execSQL("CREATE INDEX IF NOT EXISTS index_orders_updatedAt ON orders(updatedAt)")
    }
}
```

- The callback receives an **`SQLiteConnection`**, not `SupportSQLiteDatabase`; `Cursor` is gone — read with `connection.prepare(sql).use { statement -> … }`.
- Registered with `.addMigrations(Migration2To3)` on the builder; multi-step upgrades chain through every intermediate migration.
- A migration is **idempotent where cheap** (`IF NOT EXISTS`) and runs in the open transaction Room provides — do not `COMMIT` inside it.
- `AutoMigrationSpec.onPostMigrate` and `RoomDatabase.Callback` also take `SQLiteConnection` in Room 3.

## Testing every path

- Room 2.8: `MigrationTestHelper` in an instrumented test — create the database at version `N-1` from the committed schema, insert representative rows through raw SQL, run `runMigrationsAndValidate(name, N, true, migration)`, assert the rows and the validated schema.
- Room 3: the equivalent helper from the Room 3 testing artifact against the same committed schemas; confirm its name before use.
- One parameterised test walks **1 → current** so a skipped intermediate migration fails.
- A dev-side test that opens the in-memory database on JVM (Robolectric, or the bundled driver) covers DAO queries — [`unit-testing`](../../unit-testing/SKILL.md).

## Room 2.8 lane `[Room2]`

- Imports `androidx.room.*`; `ksp("androidx.room:room-compiler:2.8.x")` — **KSP, never `kapt`** (a `kapt` Room is a finding for [`mobile-android-migration`](../../migration/SKILL.md), not a side-effect fix).
- Built-in integrations work: `Flow` and `suspend` DAOs, plus `LiveData`, RxJava and `PagingSource` return types **in an existing codebase** — match, do not remove; do not add `LiveData` to new DAOs.
- `Room.databaseBuilder(context, AppDatabase::class.java, "app.db")`, `setQueryExecutor` / `setQueryCoroutineContext`, `SupportSQLite` callbacks and `runInTransaction` / `withTransaction` as in the project.
- Room 2.8 can be given a `SQLiteDriver` (`setDriver`) — the first step of a gradual Room 3 move; the full path is one file in `mobile-android-migration`.
- Room 2 and Room 3 have different group ids and can coexist **in separate databases** during migration; one database is never opened by both.

## Room 2 → 3 pointers (owned by `mobile-android-migration`)

`androidx.room` → `androidx.room3` imports and `room3-*` artifacts · add `driver` · `suspend` DAOs · `runInTransaction` → `withWriteTransaction` · `openHelper` → `getSupportWrapper()` via `room3-sqlite-wrapper` for a gradual move · `InvalidationTracker.Observer` → `createFlow` · executors → `CoroutineContext` · Rx / Paging / LiveData / Guava → converter artifacts · drop `kapt` and Java annotation processing.

## Encrypted databases

A sensitive database uses an encrypted `SQLiteDriver` with a Keystore-wrapped passphrase (generated once, stored through [`SecretStore`](../SKILL.md#secrets--keystore-and-tink)), or sensitive columns are sealed with the Tink `Aead` before the DAO. A passphrase in source or `BuildConfig` is a **blocker** (`mobile-shared-security` K-series).
