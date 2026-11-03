---
paths:
  - "**/*.sql"
  - "**/*.prisma"
  - "**/db/migration/**"
  - "**/migrations/**"
  - "**/Migrations/**"
  - "**/db/changelog/**"
  - "**/alembic/versions/**"
  - "**/drizzle/**"
---

<!-- data rules v1 (2026-11-03): core. Installed by /data:rules; edit the paths above to where this project keeps its SQL, schema and migrations, re-run to compare with the plugin's copy. -->

# Data standards: schema, SQL and migrations

Apply these to every SQL file, schema file and migration you write, edit or review. The tag after a rule is the severity a review reports: **blocker** loses data, leaks it or takes production down, **major** is a design or correctness problem, **minor** is style, **nit** is preference. Migration rules and the engine rules (`data-postgresql.md`, `data-sqlserver.md`, `data-mysql.md`, whichever this project installed) are separate files that load with the same files.

**The codebase wins.** Where this project consistently does something another way (its id strategy, naming, migration tool, tenancy mechanism), follow it and do not flag it. Detect the engine and version before writing: a probe (`SHOW server_version`, `SELECT @@VERSION`, `SELECT VERSION()`), else the compose image tag or the ORM provider. Never use a construct the server lacks (`uuidv7()` needs PostgreSQL 18; `ALGORITHM=INSTANT` coverage differs by MySQL version and MariaDB), and never flag a down-level server for lacking one.

## Keys and types

- Every table has a primary key. One surrogate id per row, generated once at insert and never reused; natural keys only for stable reference data (currencies, countries). *major*
- UUIDv7 for distributed or client-generated ids, `bigint` identity for single-engine OLTP. Never a random UUIDv4 as the clustered key of a write-heavy table. *major*
- Timestamps are timezone-aware or UTC. `created_at`/`updated_at` are set by the engine or ORM, never from client input; domain event times (`placed_at`) are app-supplied. *major*
- Money is `bigint` minor units with a `currency CHAR(3)` beside it, never `float`; other decimals carry explicit precision. *blocker for float money, else major*
- Booleans use the engine's boolean type, not `0/1`; one state model, never `is_active` + `is_deleted` + `is_archived`. *minor*
- Enums are strings under a `CHECK`, or a lookup table with an FK when the set grows; a native `ENUM` type only with a written evolution plan. *major*
- Every FK states its `ON DELETE`: `RESTRICT` for business data, `CASCADE` only inside one aggregate. No polymorphic `(owner_type, owner_id)` pair without an FK. *major*
- Every FK column is indexed unless the engine does it (InnoDB does; PostgreSQL and SQL Server do not). *major*
- Hard delete plus an audit or archive table by default; a `deleted_at` soft delete only with a stated reason. *major*
- A field that is filtered or joined on is a column, not buried in JSON. No placeholder columns for "later". *minor*

## Naming

- Tables plural, tables and columns `snake_case`; FKs `<referent>_id`; `_at` for instants, `_on` for dates; booleans positive (`is_active`). One convention per project. *minor*
- Constraints and indexes are named explicitly (`idx_<table>_<cols>`, `uq_…`, `ck_…`), never left to the engine. *minor*

## Multi-tenancy

- Every multi-tenant table carries `tenant_id`, and it leads every compound index on that table. *blocker when missing*
- Row-level security where the engine has it, as defence in depth; queries still filter by tenant explicitly, and the tenant id comes from the validated token claim, never a request body. *blocker*

## Queries

- Values are bound parameters, never concatenated or interpolated into SQL. *blocker*
- Explicit column lists; no `SELECT *` in application SQL. *major*
- Every collection query is bounded (`LIMIT`, `TOP`, `FETCH`); keyset pagination past ~10k rows, never a deep `OFFSET`. *major*
- Predicates are SARGable: no function or cast around an indexed column, no implicit type or collation conversion. *major*
- Indexes per query pattern (equality, then sort, then range), not one per column; no index that a wider one's prefix already covers. *minor*
- No dirty reads (`NOLOCK`, `READ UNCOMMITTED`) and no hints as a performance fix: read the plan, fix the query, index or statistics. *major*
- No unbatched `UPDATE`/`DELETE` over millions of rows in one transaction; no long-lived transaction. *major*

## Security

- No secret, password or key in a SQL, schema or migration file; credentials come from the environment or a secret store. *blocker*
- The migration runner has its own DDL role; the runtime role has DML only and is never the owner, superuser, `db_owner` or `root`; no `GRANT ALL`. Grants are schema-level, so the next migration's tables are readable. *blocker*
- Application code never issues DDL; the schema changes only through the migration tool. *major*
- The runtime role cannot update or delete an audit or history table. *major*

## Comments

- No `--` comment narrating a statement, no banner, no commented-out SQL; a short comment only for a non-obvious reason (a deliberate deviation, a lock or ordering constraint). Strip scaffolded comments. `COMMENT ON` and extended properties are schema metadata, not comments. *minor*
