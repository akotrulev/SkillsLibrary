# Room 2 → 3

Source: developer.android.com/jetpack/androidx/releases/room3. Room 3.0 (`androidx.room3`, 3.0.3) lives **beside** Room 2.8 — different group id and package, so both can coexist in a project (WorkManager still pulls Room 2). **A Room 2.8 project stays Room 2.8 until this move is chosen.** Never mix the two inside one database.

## What changes

| Room 2.x | Room 3.x |
|---|---|
| `androidx.room:room-runtime` | `androidx.room3:room3-runtime` |
| `androidx.room.*` imports | `androidx.room3.*` |
| kapt / Java annotation processing / KSP | **KSP only** — `ksp("androidx.room3:room3-compiler:…")` |
| Room Gradle plugin `androidx.room` | `id("androidx.room3")` with **`room3 { schemaDirectory(…) }` required** |
| Optional driver; `SupportSQLiteOpenHelper` | **A `SQLiteDriver` is required** — `.setDriver(AndroidSQLiteDriver())` or `BundledSQLiteDriver()` |
| `Executor` configuration | A `CoroutineContext` on the builder |
| Blocking DAO functions | **`suspend`**, or `Flow` / a custom return type |
| `runInTransaction { }` | `withWriteTransaction { }` |
| `query(…).use { cursor -> }` | `useReaderConnection { it.usePrepared("…") { stmt -> } }` |
| `InvalidationTracker.Observer` | `invalidationTracker.createFlow("Table")` |
| `Migration.migrate(SupportSQLiteDatabase)` | Takes a `SQLiteConnection` |
| `@TypeConverter` | `@ColumnTypeConverter` |
| Built-in Rx / LiveData / Guava / Paging | `@DaoReturnTypeConverters` + `room3-rxjava3` / `-livedata` / `-guava` / `-paging` |
| Java code generation | **Kotlin only**; KSP still reads Java entities and DAOs |

## Order

1. Be on AGP 9 / KSP already ([`agp8-to-9`](agp8-to-9.md)); Room 2.8 on KSP, no kapt.
2. **One database at a time.** Add the Room 3 dependencies beside Room 2's.
3. Change imports and annotations; add the schema directory (`room3 { schemaDirectory("$projectDir/schemas") }`) and commit the generated JSON. The existing version-N schema files carry over so migration tests keep working.
4. Make every DAO function `suspend` or `Flow`; callers that were blocking (a background thread, a `LiveData` transform) become coroutine calls — move LiveData / Rx consumers first ([`livedata-rx-to-flow`](livedata-rx-to-flow.md)), or add the converter artifacts as a bridge.
5. Add the driver. **State which**: `AndroidSQLiteDriver()` uses the device's SQLite (version varies); `BundledSQLiteDriver()` ships one known SQLite and is required for KMP — a change of SQLite engine is a behaviour change, so test the existing migrations against it.
6. Port custom migrations to `SQLiteConnection`; re-run every migration test from every old schema version.
7. Remove Room 2 dependencies when no import is left. The `room3-sqlite-wrapper` artifact (`getSupportWrapper()`) is a **bridge** for code that still uses `SupportSQLiteDatabase`, with a removal task.

## Traps

- **The on-disk database is the same file.** The schema hash and `room_master_table` carry over; a changed entity set or version number is a **schema change**, not part of this move.
- A missing `schemaDirectory` fails the build; one committed from a different Room version fails a test — regenerate once, then commit.
- `fallbackToDestructiveMigration()` is never the way through; a user database is not rebuilt.
- Paging 3 needs the converter annotation on the DAO; without it the compile error names the return type.
- Instrumented tests that opened the DB through `Room.databaseBuilder(context, …)` need the driver; use the context-free builder only in KMP code.

## Verify

- `rg -n "androidx\.room\." -g '*.kt' -g '*.kts' -g '*.java'` is empty for the migrated database (the `room3` group id has no dot after `room`).
- Migration tests pass from every shipped schema version; an upgrade-install from the production build keeps its rows.
