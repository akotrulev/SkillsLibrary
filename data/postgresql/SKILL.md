---
name: data-postgresql
description: Use when designing tables, modeling relationships, securing data (roles/RLS/audit), writing queries or migrations, choosing indexes, caching, or tuning performance on PostgreSQL from a .NET / Java / Node backend. Triggers: "design a Postgres schema", "multi-tenant RLS", "this query is slow", "add an index", "audit who changed this row", "set up Postgres pooling". Pick the topic in the routing table, then read its reference file end-to-end. Do NOT use for SQL Server (`data/sqlserver`), MySQL (`data/mysql`), NoSQL stores, cross-engine modeling decisions (`data/_shared/schema-design`), or writing DB tests (`qa/<stack>/skills/db-testing`).
---

# Data — PostgreSQL

One registered skill, five topic references. This file routes and holds the rules shared by every topic: version policy, connections/pooling, migration discipline, and the hard rules. **Read the matching `references/<topic>.md` end-to-end before writing any code.** Unlike qa's one-of-N families, these split by *topic* — a task may need two files (a new multi-tenant schema = `data-modeling.md` + `security.md`).

## Routing table

| Read | Use when |
|------|----------|
| `references/data-modeling.md` | New tables/schemas, relationships, foreign keys, constraints, enum strategy, `jsonb` boundaries, history/temporal tables |
| `references/security.md` | Roles & grants, row-level security / multi-tenant isolation, encryption, TLS, audit logging / edit trails |
| `references/indexing.md` | Choosing or fixing indexes, composite ordering, partial/covering/expression indexes, index maintenance & bloat |
| `references/performance.md` | Slow queries, EXPLAIN reading, vacuum/autovacuum, partitioning, memory config, lock contention |
| `references/caching.md` | Materialized views, LISTEN/NOTIFY invalidation, prepared-statement/plan caching, buffer-cache mental model |

## Version policy — PG 18 primary, 15–17 supported

First act on an existing database: **detect the server version** (`SHOW server_version;` or `SELECT version();`) and key every recipe to it. Never apply an 18-only construct to a down-level server; never flag a down-level server for lacking one. 18-only constructs are tagged throughout the references with their 15–17 fallback beside them:

| PG 18 construct | 15–17 fallback |
|---|---|
| `uuidv7()` | `gen_random_uuid()` (v4) or app-side UUIDv7 generation |
| Virtual generated columns (read-time, the 18 default) | `GENERATED ALWAYS AS (...) STORED` |
| `NOT NULL NOT VALID` → `VALIDATE CONSTRAINT` | add nullable → batched backfill → `SET NOT NULL` |
| `RETURNING OLD.x, NEW.x` | separate `SELECT` before/after, or trigger capture |
| B-tree skip scan (non-leading-column composite use) | column-ordering rule applies strictly |
| Async I/O `io_method` (`worker` / `io_uring`) | n/a — config only, no code impact |

Managed cloud: PG 18 is GA on Aurora (18.3+) and Azure Flexible Server; minor-version lag on managed platforms is noted per recipe where it matters, not treated as a blocker.

## Stack defaults (align with CLAUDE.md)

- **.NET 10** (8/9 supported): Npgsql + EF Core (`Npgsql.EntityFrameworkCore.PostgreSQL`); raw Npgsql for hot paths. Migrations via EF Core or Flyway.
- **Java 21 + Spring Boot 3.x**: `spring-boot-starter-data-jpa` + `postgresql` driver, HikariCP pool. Migrations via Flyway (preferred) or Liquibase.
- **Node 24 + TypeScript**: `pg` driver, Prisma or Drizzle. Migrations via Prisma Migrate / Drizzle Kit / `node-pg-migrate`.
- **PgBouncer in transaction mode** in front of every production app. Transaction mode breaks session state (see `references/caching.md` for the prepared-statement interaction).

## Inputs needed

1. **Server version** (drives everything — see version policy)
2. **Hosting**: managed (Aurora / RDS / Azure Flexible Server) or self-hosted
3. **Backend stack** (.NET / Java / Node) — determines client + migration tool
4. **Workload shape**: OLTP, read-heavy, write-heavy, mixed, analytics
5. **Row counts and growth** — drives partitioning, index choices, autovacuum tuning
6. **Tenancy model** — single-tenant or multi-tenant (routes to `references/security.md` RLS)

## Connections (per stack)

### .NET 10

```csharp
builder.Services.AddDbContext<AppDb>(opt =>
    opt.UseNpgsql(builder.Configuration.GetConnectionString("Postgres"),
        npg => npg.EnableRetryOnFailure(maxRetryCount: 3)));

// Connection string from env / Key Vault, never appsettings.json:
// "Host=pg-prod;Port=6432;Database=orders;Username=app;SSL Mode=VerifyFull;Maximum Pool Size=20"
```

### Java 21 + Spring Boot

```yaml
spring:
  datasource:
    url: jdbc:postgresql://pg-prod:6432/orders?sslmode=verify-full
    username: app
    password: ${DB_PASSWORD}
    hikari:
      maximum-pool-size: 20
      connection-timeout: 5000
      leak-detection-threshold: 60000
  jpa:
    hibernate:
      ddl-auto: validate          # the migration tool owns DDL; Hibernate only validates
    properties:
      hibernate.jdbc.batch_size: 50
      hibernate.order_inserts: true
```

### Node 24 + TypeScript

```typescript
import { drizzle } from 'drizzle-orm/node-postgres';
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL, // ...?sslmode=verify-full
  max: 20,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
});
export const db = drizzle(pool);
```

Pool sizing: 20 per instance behind PgBouncer; 10 without it. Never crank app pools instead of adding PgBouncer — per-connection overhead on the engine is real.

## Migrations

- **One migration per logical change.** Add-column AND backfill AND add-constraint is three migrations.
- **Forward-only in production.** Down scripts are local-dev only; roll forward with a corrective migration.
- **Online-safe DDL patterns:**
  - Column with a non-volatile default: metadata-only since PG 11 — safe. Volatile defaults rewrite the table — split into add-nullable → backfill → set-default.
  - NOT NULL on a large table: **PG 18** `ALTER TABLE ... ADD CONSTRAINT ... NOT NULL NOT VALID` then `VALIDATE CONSTRAINT` (validation takes only a weak lock). 15–17: add nullable → batched backfill → `SET NOT NULL`.
  - FK/CHECK on a large table: add `NOT VALID` (all versions) → `VALIDATE CONSTRAINT` separately.
  - Index on a hot table: **`CREATE INDEX CONCURRENTLY`** outside a transaction (Flyway: `-- $$$ flyway:no-transaction $$$`; EF: `suppressTransaction: true`). A failed concurrent build leaves an `INVALID` index — detect and drop/retry (`references/indexing.md`).
  - Renames: expand-contract across two deploys (add new → dual-write → switch reads → drop old). Never drop a column in the same release that stops writing it.
- Universal expand-contract pattern + tool table → `data/_shared/migrations`.

## Rules

- Schema changes only via the migration tool; never psql in prod.
- Separate roles: migrations get DDL, runtime gets DML only, nobody logs in as the owner (`references/security.md`).
- `sslmode=verify-full` + SCRAM-SHA-256; connection strings in env/secret store only.
- Parameterized queries only — no SQL string concatenation, ever.
- `timestamptz` always; `text` over `varchar(n)` unless `n` is a real domain constraint.
- Every collection query has a `LIMIT`; keyset pagination over `OFFSET` past ~10k rows.
- Explicit columns — no `SELECT *` in code.
- `statement_timeout` set per app role so a runaway query can't run for hours.
- Explicit isolation level when it matters; default `READ COMMITTED` otherwise.
- `SELECT ... FOR UPDATE` only with `LIMIT` (or unique predicate) inside a short transaction; `SKIP LOCKED` for queues.

## What NOT to do

- No `serial`/`bigserial` — `GENERATED ALWAYS AS IDENTITY`.
- No `timestamp without time zone` for events.
- No application code issuing DDL.
- No unbatched `DELETE`/`UPDATE` touching millions of rows in one transaction.
- No `CREATE INDEX` without `CONCURRENTLY` on a hot production table.
- No native `CREATE TYPE ... AS ENUM` without an evolution plan (`references/data-modeling.md`).
- No FK column left unindexed (Postgres does NOT auto-index FK columns — `references/data-modeling.md`).
- No app login as table owner / superuser; no `GRANT ALL` to runtime roles.
- No `pg_dump` as the production backup strategy — PITR / managed snapshots.
- No fixing sequence gaps — gaps from rollbacks are normal and expected.

## Generation steps

1. Detect server version, hosting, stack, workload shape, tenancy — confirm with the user what can't be detected.
2. Route: read the matching reference file(s) end-to-end before writing anything.
3. New schema → DDL + one initial migration in the project's tool (+ RLS policies if multi-tenant).
4. Slow query → `EXPLAIN (ANALYZE, BUFFERS)`, smallest fix first (`references/performance.md`).
5. Validate with `psql` + `EXPLAIN ANALYZE`; smoke a representative query against seeded data in CI.

## Handoffs

- Cross-engine modeling decisions (id strategy, money, soft-delete, tenancy pattern *choice*) → `data/_shared/schema-design`
- Expand-contract pattern + migration tool selection → `data/_shared/migrations`
- Cache-aside/stampede/TTL pattern catalog → `data/_shared/caching-patterns` + `data/redis`
- Universal query triage (ESR, N+1, pagination) → `data/_shared/query-optimization`
- Testing the schema/queries (seed/assert/clean, Testcontainers, safe SQL) → `qa/{java,dotnet,typescript}/skills/db-testing/*`
- Tenant/user claims feeding the RLS session context → `auth/auth0-{stack}` + `auth/_shared/auth0-concepts`
