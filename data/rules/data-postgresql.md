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

<!-- data rules v1 (2026-11-03): PostgreSQL. Installed by /data:rules when the project uses PostgreSQL; narrow the paths above to this engine's files when the repo has several engines. -->

# PostgreSQL standards (18 primary, 15–17 supported)

Severity tags as in the core data rules. Never an 18-only construct on 15–17.

- `GENERATED ALWAYS AS IDENTITY`, never `serial`/`bigserial`. `uuidv7()` on 18; app-side UUIDv7 on 15–17. *major*
- `timestamptz`, never `timestamp` without time zone; `text` over `varchar(n)` unless `n` is a real limit. *major; minor for varchar*
- No `CREATE TYPE … AS ENUM` without an evolution plan. *major*
- `jsonb` only for sparse, variable-shape data; a path you filter on becomes a generated column; GIN only for the operators in use. *minor*
- `CREATE INDEX CONCURRENTLY` on a hot table, outside a transaction (Flyway `flyway:no-transaction`, EF `suppressTransaction: true`); an `INVALID` index from a failed build is dropped and rebuilt. *major*
- FK or CHECK on a large table: `NOT VALID`, then `VALIDATE CONSTRAINT`. NOT NULL: on 18 `NOT NULL NOT VALID` then validate; on 15–17 nullable, backfill, `SET NOT NULL`. A volatile default is split the same way. *major*
- Migration sessions set `lock_timeout`, so DDL fails fast instead of queueing behind a long read. *major*
- RLS: `ENABLE` and `FORCE ROW LEVEL SECURITY`; the policy is a plain indexed `tenant_id` comparison with `current_setting('app.tenant_id')` and no `missing_ok`, so an unset context fails closed; the context is `SET LOCAL`, never `SET` behind PgBouncer. *blocker*
- `ALTER DEFAULT PRIVILEGES` for the schema, so the runtime role can read the tables new migrations create. *major*
- `statement_timeout` per app role. *minor*
- `SELECT … FOR UPDATE` only with a `LIMIT` or unique predicate in a short transaction; `SKIP LOCKED` for queue tables. *major*
- `REFRESH MATERIALIZED VIEW CONCURRENTLY`, with its unique index, for a view readers depend on. *major*
- Sequence gaps are normal; never "fix" them. *nit*
