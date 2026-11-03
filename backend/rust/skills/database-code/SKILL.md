---
name: persistence
description: Use when setting up or refactoring Rust persistence with sqlx, diesel or sea-orm (queries, migrations, transactions, tuning). Triggers "add a sqlx query". Not for raw SQL (postgresql).
---

# Rust — Persistence with sqlx (default), diesel, sea-orm

**sqlx** is the default: you write SQL, the `query!` / `query_as!` macros check it against a real database at compile time, and there is no ORM layer to learn or fight. **diesel** (2.3, with `diesel-async` 0.9 for async) suits a team that wants a typed query DSL. **sea-orm** (2.0, built on sqlx 0.9) suits a team that wants ActiveRecord-style entities. Use whichever the repo already has, and never mix two in one service. The recipes assume Postgres (`data/postgresql`).

## Version policy

Read `Cargo.lock`. **sqlx 0.9 is current (May 2026) and needs Rust 1.94.** A project on 0.8 stays on 0.8 unless the task is the upgrade. The 0.9 changes that break code:

| 0.9 change | Effect |
|---|---|
| `query*()` take `impl SqlSafeStr` | Only a `&'static str` or `AssertSqlSafe(..)` compiles. `format!`-built SQL no longer compiles unless wrapped, which is the point |
| Runtime and TLS features split | Combined features such as `runtime-tokio-native-tls` are gone. Pick `runtime-tokio` plus one TLS feature — check the exact names against the lockfile's version |
| `offline` is an optional feature; `SQLX_OFFLINE_DIR` overrides | CI builds without a database need the feature and a committed `.sqlx/` |
| Postgres forces a generic plan when describing queries | `query!` nullability inference can change. Fix with column overrides, never by loosening a type to `Option` |
| Opt-in `sqlx.toml` (feature `sqlx-toml`) | Renames `DATABASE_URL`, sets type overrides, renames the migrations table |
| Repo moved to `transact-rs` | Same crate name on crates.io |

## When to use

- Adding a table's queries, a migration, or a transaction
- `query!` failing in CI, or a nullability mismatch after an upgrade
- Slow endpoints caused by N+1 or row-by-row inserts
- Lost updates (optimistic concurrency)
- Choosing between sqlx, diesel and sea-orm for a new service

## When NOT to use

- Table, index and constraint design, engine tuning, RLS → `data/postgresql` (the `data-architect` agent); this skill owns the Rust side of the queries
- Cross-engine migration strategy → `data/_shared/migrations`
- Caching → `data/_shared/caching-patterns`
- Pool exhaustion caused by tasks holding connections across slow work → also read `async-concurrency`

## Setup

```toml
sqlx = { version = "0.9", default-features = false, features = [
    "runtime-tokio", "tls-rustls", "postgres", "macros", "migrate", "uuid", "time",
] }
```

```rust
use secrecy::ExposeSecret as _;
use sqlx::postgres::{PgConnectOptions, PgPoolOptions};

pub async fn connect(config: &Config) -> Result<sqlx::PgPool, sqlx::Error> {
    let options: PgConnectOptions = config.database_url.expose_secret().parse()?;
    PgPoolOptions::new()
        .max_connections(config.db_max_connections)
        .acquire_timeout(Duration::from_secs(3))
        .connect_with(options)
        .await
}
```

- **Pool size** is a budget shared with every other replica: `replicas × max_connections` stays under the server's `max_connections` minus headroom. 10 is a sane default per replica. More connections rarely make Postgres faster.
- **`acquire_timeout`** turns pool exhaustion into a fast error instead of a hung request.
- The URL is a `SecretString` exposed only at this line.

## Migrations

```
migrations/20261031120000_create_orders.sql
```

```rust
sqlx::migrate!("./migrations").run(&pool).await?;
```

- `cargo sqlx migrate add -r <name>` creates reversible up/down files. Migrations are **forward-only in production**: a mistake is fixed by a new migration, never by editing an applied one, because sqlx checksums applied files and refuses to start.
- Choose one runner and state it in the plan. Running `migrate!` at startup suits a single-replica service. For several replicas, run it as a separate job or init container before the rollout; sqlx takes an advisory lock, but a slow migration still blocks every pod's startup.
- A change to a live table follows expand → migrate data → contract across releases (`data/_shared/migrations`).
- In a module-per-crate workspace, each module crate owns its `migrations/` folder and its schema. Give each module its own migrations table (`sqlx.toml` on 0.9, or `Migrator` with a table-name override) so the folders never conflict.

## Compile-checked queries and offline mode

```rust
pub struct OrderRow {
    pub id: OrderId,
    pub status: OrderStatus,
    pub total_minor: i64,
    pub version: i32,
}

pub async fn find(db: &PgPool, id: OrderId) -> Result<Option<OrderRow>, sqlx::Error> {
    sqlx::query_as!(
        OrderRow,
        r#"SELECT id AS "id: OrderId", status AS "status: OrderStatus", total_minor, version
           FROM orders.orders WHERE id = $1"#,
        id as OrderId,
    )
    .fetch_optional(db)
    .await
}
```

- **`query_as!` over `query_as::<_, T>()`** wherever the SQL is static. The macro checks column names, types and nullability against the database. The function form checks nothing until run time.
- Newtypes and enums map with `#[derive(sqlx::Type)]` (`#[sqlx(transparent)]` for a newtype, `#[sqlx(type_name = "order_status", rename_all = "snake_case")]` for an enum), and with the `AS "col: Type"` override in the macro.
- **Nullability overrides:** `AS "col!"` forces non-null (for example, a column that is non-null through a join the macro cannot see), and `AS "col?"` forces nullable. Use them for real knowledge, never to silence an error you don't understand.
- **Offline builds:** run `cargo sqlx prepare` (workspace: `cargo sqlx prepare --workspace`) against a migrated database and commit `.sqlx/`. CI builds with `SQLX_OFFLINE=true`, and a CI step runs `cargo sqlx prepare --check` so stale metadata fails the build. sqlx-cli 0.9 no longer installs with `--locked`.

## Dynamic SQL — `QueryBuilder`, never `format!`

```rust
let mut query = sqlx::QueryBuilder::<sqlx::Postgres>::new(
    "SELECT id, status, total_minor FROM orders.orders WHERE customer_id = ",
);
query.push_bind(customer_id);
if let Some(status) = filter.status {
    query.push(" AND status = ").push_bind(status);
}
query.push(" ORDER BY created_at DESC, id DESC LIMIT ").push_bind(page_size);
let rows = query.build_query_as::<OrderSummary>().fetch_all(db).await?;
```

Values always go through `push_bind`. A column or sort direction chosen by the client is mapped from a closed `enum` to a `&'static str`, never interpolated. `AssertSqlSafe` is allowed only around a string assembled from such static fragments, and the review checks every use of it.

## Transactions

```rust
pub async fn place(db: &PgPool, command: PlaceOrder, now: OffsetDateTime) -> Result<PlacedOrder, PlaceOrderError> {
    let mut tx = db.begin().await?;
    let order_id = OrderId::new();
    sqlx::query!(
        "INSERT INTO orders.orders (id, customer_id, status, total_minor, created_at, version) VALUES ($1, $2, 'placed', $3, $4, 0)",
        order_id as OrderId, command.customer_id as CustomerId, command.total_minor(), now,
    )
    .execute(&mut *tx)
    .await?;
    insert_lines(&mut tx, order_id, &command.lines).await?;
    tx.commit().await?;
    Ok(PlacedOrder { id: order_id, channel: command.channel, total_minor: command.total_minor_unsigned() })
}
```

- A `Transaction` **rolls back on drop** unless `commit()` ran. An early `?` return is therefore safe, and a forgotten `commit()` silently discards the work: every `begin()` has its `commit()` on the success path.
- Functions that run inside a caller's transaction take `&mut PgConnection` (pass `&mut *tx`), so they work both with and without one.
- Never hold a transaction open across an outbound HTTP call or a long computation. It pins a pool connection and holds row locks.
- A write plus an event that must not be lost is the **outbox**: the event row is inserted in the same transaction, and a background relay publishes it (`async-concurrency` for the relay task).

## Optimistic concurrency

```rust
let updated = sqlx::query!(
    "UPDATE orders.orders SET status = $1, version = version + 1 WHERE id = $2 AND version = $3",
    new_status as OrderStatus, id as OrderId, expected_version,
)
.execute(db)
.await?;
if updated.rows_affected() == 0 {
    return Err(ChangeStatusError::Conflict);
}
```

The client sends the version it read (an `If-Match` ETag, or a field). Zero rows affected means someone else changed it → `409 Conflict` / `412 Precondition Failed`, per the plan's validation catalog. A refused status transition is checked in the domain **before** the update, and it is a different error from a conflict.

## N+1 and bulk work

```rust
let lines = sqlx::query_as!(
    LineRow,
    r#"SELECT order_id AS "order_id: OrderId", sku, quantity FROM orders.order_lines WHERE order_id = ANY($1)"#,
    &order_ids as &[OrderId],
)
.fetch_all(db)
.await?;
```

Load the children of many parents with one `= ANY($1)` query and group them in memory. A query inside a loop over rows is the N+1 finding.

```rust
sqlx::query!(
    "INSERT INTO orders.order_lines (order_id, sku, quantity)
     SELECT $1, * FROM UNNEST($2::text[], $3::int4[])",
    order_id as OrderId, &skus as &[String], &quantities as &[i32],
)
.execute(&mut *tx)
.await?;
```

Postgres caps one statement at **65,535 bind parameters**. `QueryBuilder::push_values` hits that limit at a few thousand rows; arrays with `UNNEST` do not, and they keep the query compile-checked. For very large loads, use `COPY` (`PgConnection::copy_in_raw`).

## Pagination

Use keyset pagination for anything a client scrolls: `WHERE (created_at, id) < ($1, $2) ORDER BY created_at DESC, id DESC LIMIT $3`, with an index that matches. `OFFSET` scans and discards rows, so deep pages get linearly slower. Use the cursor format defined in the plan's pagination contract.

## Testing the queries

Queries are proven only against a real engine. `#[sqlx::test]` creates a fresh database per test, runs the migrations, and hands the test a pool — that is the integration lane, not `unit-testing`'s. **No `qa-*-rust` plugin exists yet**, so for now:

- `be-rust` writes `#[sqlx::test]` query tests in `tests/` when the task asks for them. They need `DATABASE_URL` pointing at a disposable server (a CI service container or `deploy/local/`), and they stay out of the unit lane and out of the unit coverage measure.
- Black-box HTTP contract tests against the running service belong to `qa-api-typescript`, which tests over HTTP without caring about the server's language.
- Never substitute SQLite or a mocked pool for Postgres. Dialect differences make it a false-negative machine.

## Rules

- `query!` / `query_as!` for static SQL; `.sqlx/` committed and `prepare --check` in CI
- Values only through binds; dynamic fragments only from closed enums
- Pool sized against the server budget, with `acquire_timeout`
- Every `begin()` has a `commit()`; no transaction across outbound I/O
- Inner functions take `&mut PgConnection`
- Version column + `rows_affected() == 0` → conflict
- `= ANY($1)` for children; `UNNEST` / `COPY` for bulk
- Keyset pagination; money as integer minor units (`BIGINT`), timestamps as `timestamptz`
- Migrations forward-only, one runner, module-owned schemas in a workspace

## What NOT to do

- No `format!` into SQL; no `AssertSqlSafe` around anything that contains client input
- No `query()` + `.bind()` where `query!` fits
- No connection or transaction kept in `AppState`; no global pool in a `static`
- No `Option<T>` added to a row struct only to make an upgrade compile
- No editing an applied migration
- No `SELECT *` in `query_as!` — a new column breaks the mapping, and the column list is the contract
- No mocking `PgPool`, and no SQLite stand-in for Postgres tests

## Generation steps

1. Detect the persistence crate and version; on a new service, add sqlx with the features above and `store::connect`.
2. Write the migration (schema from `data-model.md` or from `data-architect`).
3. Write the queries with `query!` / `query_as!`, newtypes via `sqlx::Type`, and a transaction where more than one statement must succeed together.
4. Run `cargo sqlx prepare` and commit `.sqlx/`.
5. Unit-test the logic around the queries (`unit-testing`); write `#[sqlx::test]` tests only when the task asks for them (see *Testing the queries*).
6. Validate: `cargo clippy`, `cargo sqlx prepare --check`, the tests.

## Handoffs

- Schema, indexes, engine specifics → `data/postgresql` via `data-architect`
- The outbox relay task, pool exhaustion under load → `async-concurrency`
- A slow query → `data/_shared/slow-query-fixes`, then `performance` if the cost is in Rust
- Review → `code-review`
