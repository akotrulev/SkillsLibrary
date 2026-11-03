---
paths:
  - "**/migrations/**"
  - "**/{store,db,repo,repository,persistence,queries}.rs"
  - "**/{store,db,repo,repository,persistence,queries}/**/*.rs"
  - "**/sqlx.toml"
---

<!-- be-rust rules v1 (2026-11-03): persistence. Installed by /be-rust:rules; edit the paths above to where this project keeps its queries and migrations. -->

# Rust persistence standards (sqlx; diesel / sea-orm where the repo has them)

Severity tags as in the core Rust rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Values go only through binds (`$1`, `push_bind`). No `format!` into SQL; `AssertSqlSafe` only around static fragments; a client-chosen column or sort maps from a closed `enum`. *blocker*
- Migrations are forward-only: a fix is a new migration, never an edit to an applied one. *blocker*
- `query!` / `query_as!` wherever the SQL is static; `.sqlx/` committed and `cargo sqlx prepare --check` in CI. *minor; major for stale metadata*
- No `SELECT *` in `query_as!`; nullability overrides (`"col!"`, `"col?"`) only from real knowledge, never an `Option` added to make an upgrade compile. *major*
- A multi-statement write runs in one transaction, and every `begin()` has its `commit()` on the success path. Inner functions take `&mut PgConnection`. *major; minor for the parameter*
- No transaction open across an outbound call or a long computation. *major*
- No connection or transaction in `AppState`; no pool in a `static`. The pool is sized against the server's budget across replicas and has an `acquire_timeout`. *major; minor for sizing*
- Optimistic concurrency: a version column, `rows_affected() == 0` → a conflict error, distinct from a refused transition. *major*
- A write plus an event that must not be lost is an outbox row in the same transaction. *major*
- No query inside a loop over rows: children load with `= ANY($1)`, bulk inserts with `UNNEST` or `COPY`. *major*
- Keyset pagination for anything a client scrolls, not `OFFSET`. *minor*
- Money is `BIGINT` minor units; timestamps are `timestamptz`. *major*
- One migration runner, stated; in a workspace each module crate owns its schema and migrations, with no foreign key into another module's schema. One persistence crate per service. *major*
