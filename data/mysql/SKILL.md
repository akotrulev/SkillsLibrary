---
name: data-mysql
description: Use when designing tables, modeling relationships, securing data (privileges/tenancy/encryption/audit), writing queries or migrations, choosing indexes, caching, or tuning performance on MySQL / MariaDB / Aurora MySQL from a .NET / Java / Node backend. Triggers: "design a MySQL schema", "multi-tenant isolation without RLS", "this MySQL query is slow", "add an index", "InnoDB tuning", "online DDL on a huge table", "Aurora vs RDS MySQL". Pick the topic in the routing table, then read its reference file end-to-end. Do NOT use for PostgreSQL (`data/postgresql`), SQL Server (`data/sqlserver`), NoSQL stores, cross-engine modeling decisions (`data/_shared/schema-design`), or writing DB tests (`qa/<stack>/db-testing`).
---

# Data — MySQL / MariaDB / Aurora MySQL

One registered skill, five topic references. This file routes and holds the rules shared by every topic: version policy, connections/pooling, migration discipline, and the hard rules. **Read the matching `references/<topic>.md` end-to-end before writing any code.** These split by *topic*, not by tool — a task may need two files (a new multi-tenant schema = `data-modeling.md` + `security.md`).

## Routing table

| Read | Use when |
|------|----------|
| `references/data-modeling.md` | New tables/schemas, relationships, foreign keys, constraints, charset/collation, clustered-PK (InnoDB) design, JSON boundary |
| `references/security.md` | Privilege model & grants, **multi-tenancy without RLS** (views/app-enforced), encryption (TDE/keyring/app-side), TLS, audit logging |
| `references/indexing.md` | Choosing or fixing indexes, InnoDB clustered-PK effects, covering/prefix/functional/descending, invisible indexes, FULLTEXT |
| `references/performance.md` | Slow queries, `EXPLAIN ANALYZE`, buffer pool, Performance Schema / `sys`, replication lag, locking, partitioning |
| `references/caching.md` | Buffer pool as cache, why the query cache is gone, the external-cache seam, read-replica reads |

## Version policy — MySQL 8.4 LTS primary, 9.x Innovation supported, 8.0 legacy (EOL)

First act on an existing database: **detect the version and flavor** (`SELECT VERSION();`) and key every recipe to it. MySQL moved to a dual-track model: **8.4 LTS** (Premier support to ~2032) is the production default; **9.x Innovation** releases are short-lived, feature-forward, supported only for teams that track them; **MySQL 8.0 reached EOL in April 2026** — treat an 8.0 project as legacy, note the migration path, and don't build new work assuming its patches. Flavors diverge — call it out:

- **MariaDB 11.x LTS** is a fork, not a drop-in: different JSON (`LONGTEXT` alias + `JSON_*` functions, no native JSON type), `EXPLAIN ANALYZE` differs, `INSTANT` DDL coverage differs, no `SESSION_CONTEXT`/CTE-quirks parity, its own optimizer. Verify per feature; don't assume MySQL docs apply.
- **Amazon Aurora MySQL 3** is wire-compatible with MySQL 8.0 (Aurora tracks 8.0/8.4 on a lag) but replaces the storage/replication layer — Aurora-specific notes live in `references/performance.md`.

| 8.4 / 9.x construct | 8.0 / MariaDB fallback |
|---|---|
| `ALTER TABLE ... ALGORITHM=INSTANT` (broad column ops) | `INPLACE, LOCK=NONE` where supported, else pt-osc/gh-ost |
| Descending indexes (real, since 8.0) | reverse the scan / rely on backward index scan |
| Functional indexes (8.0.13+) | generated stored column + index on it |
| Invisible indexes (8.0) | drop-and-recreate to test index value |
| `EXPLAIN ANALYZE` (8.0.18+) | `EXPLAIN FORMAT=JSON` (no actual timings) |
| Native `JSON` type + multi-valued indexes | MariaDB: `LONGTEXT` + `JSON_VALID` CHECK |

Managed: Azure DB for MySQL Flexible Server and RDS/Aurora track 8.0→8.4 on their own cadence; note minor-version lag per recipe where it changes behavior, not as a blocker.

## Stack defaults (align with CLAUDE.md)

- **.NET 10** (8/9 supported): `MySqlConnector` (raw / preferred) or `Pomelo.EntityFrameworkCore.MySql` for EF Core. Migrations via EF Core or Flyway.
- **Java 21 + Spring Boot 3.x**: `mysql-connector-j` driver + Spring Data JPA, HikariCP pool. Migrations via Flyway (preferred) or Liquibase.
- **Node 24 + TypeScript**: `mysql2` (prepared-statement support; preferred over `mysql`), or Prisma / Drizzle. Migrations via the ORM's tool.
- Storage engine **InnoDB** always (no MyISAM). Charset **`utf8mb4`** / collation **`utf8mb4_0900_ai_ci`** (MySQL 8) — `utf8` is the 3-byte alias and silently truncates 4-byte emoji/CJK.
- Connection multiplexing: **ProxySQL** or **RDS Proxy** in front of large/serverless fleets — don't raise `max_connections` to cope.

## Inputs needed

1. **Version + flavor** (MySQL 8.4/9.x/8.0 · MariaDB 11 · Aurora MySQL) — drives everything
2. **Hosting**: managed (RDS, Aurora, Azure Flexible Server) or self-hosted
3. **Backend stack** (.NET / Java / Node) — client + migration tool
4. **Workload shape**: OLTP, read-heavy, write-heavy, mixed
5. **Row counts and growth** — drives partitioning, index choices, buffer-pool sizing
6. **Tenancy model** — single- or multi-tenant (routes to `references/security.md`; MySQL has **no RLS** — the pattern differs from Postgres/SQL Server)

## Connections (per stack)

### .NET 10

```csharp
builder.Services.AddDbContext<AppDb>(opt =>
    opt.UseMySql(
        builder.Configuration.GetConnectionString("MySql"),
        ServerVersion.AutoDetect(builder.Configuration.GetConnectionString("MySql")),
        mysql => mysql.EnableRetryOnFailure(maxRetryCount: 6)));

// "Server=db-prod;Port=3306;Database=orders;User=app;Password=...;
//  SslMode=VerifyFull;Pooling=true;Maximum Pool Size=20;"  (from env / secret store)
```

### Java 21 + Spring Boot

```yaml
spring:
  datasource:
    url: jdbc:mysql://db-prod:3306/orders?sslMode=VERIFY_IDENTITY&serverTimezone=UTC&characterEncoding=UTF-8
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
      hibernate.dialect: org.hibernate.dialect.MySQLDialect
```

### Node 24 + TypeScript

```typescript
import mysql from 'mysql2/promise';

export const pool = mysql.createPool({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  waitForConnections: true,
  connectionLimit: 20,
  enableKeepAlive: true,
  ssl: { rejectUnauthorized: true },   // verify the server cert — not just encrypt
});
```

Use `pool.execute('SELECT ... WHERE id = ?', [id])` — parameterized via the driver's prepared-statement path. Pool sizing: 20 per instance behind a proxy; every raw connection costs memory, so multiplex rather than crank `max_connections`.

## Migrations

- **One migration per logical change.** Add-column AND backfill AND add-constraint is three migrations.
- **Forward-only in production.** Down scripts are local-dev only; roll forward with a corrective migration.
- **Online-safe DDL patterns:**
  - `ALGORITHM=INSTANT` (MySQL 8.0+, broadened in 8.4) for adding/dropping columns, renames — metadata-only. Verify the op is INSTANT-eligible per version; MariaDB coverage differs.
  - `ALGORITHM=INPLACE, LOCK=NONE` for many index/constraint ops — check the op's support matrix.
  - When neither works (or on a huge table you can't risk), use **`pt-online-schema-change`** or **`gh-ost`** — they build a shadow table + triggers/binlog and cut over. Mandatory for large-table changes on standard MySQL.
  - `ADD COLUMN ... NOT NULL` needing a backfill rewrites the table → split add-nullable → batched backfill → set-not-null.
  - Adding an FK to a large table is expensive and takes metadata locks; do it via pt-osc/gh-ost or a low-traffic window.
  - Renames: expand-contract across two deploys. Never drop a column in the same release that stops writing it.
- Universal expand-contract pattern + tool table → `data/_shared/migrations`.

## Rules

- Schema changes only via the migration tool (or pt-osc/gh-ost); never `mysql` CLI ad-hoc DDL in prod.
- Least-privilege grants: migrations get DDL, runtime gets DML only, nobody uses `root`/`SUPER` (`references/security.md`).
- TLS with **identity verification** (`sslMode=VERIFY_IDENTITY` / `SslMode=VerifyFull` / `rejectUnauthorized:true`) — plain `REQUIRED` encrypts but doesn't verify the cert (MITM); IAM auth on managed where supported.
- Parameterized queries only — no string concatenation, ever.
- `utf8mb4` charset universally; reject `utf8`.
- `DATETIME(6)` for events (store UTC); `TIMESTAMP` only where the 2038 cliff and silent TZ conversion don't matter.
- `BIGINT UNSIGNED AUTO_INCREMENT` surrogate PK; `BINARY(16)` UUIDv7 for distributed/client-generated ids — never `CHAR(36)`.
- Every collection query has a `LIMIT`; keyset pagination over deep `OFFSET`.
- Explicit columns — no `SELECT *` in code.
- Default isolation `REPEATABLE READ` (InnoDB) is fine for OLTP — know about gap locks / phantom behavior; `max_execution_time` hint caps runaway `SELECT`s.

## What NOT to do

- No `MyISAM` for new schemas (no transactions, no FKs, table-level locks).
- No `utf8` (3-byte) — always `utf8mb4`.
- No `CHAR(36)` UUIDs, and no **random** UUID (v4) as the clustered PK — it fragments InnoDB's primary (`references/data-modeling.md`).
- No `SELECT *` in app code; no `OFFSET 1000000 LIMIT 20`.
- No application code issuing DDL — migrations / pt-osc / gh-ost only.
- No `query_cache_size` tuning — the query cache was removed in 8.0.
- No `ANALYZE TABLE` on a cron — InnoDB updates stats automatically.
- No FK constraints "disabled for performance" without a plan to re-enable.
- No long-lived transactions — they pin the undo log and block purge (`references/performance.md`).
- No app account with `SUPER`/`ALL PRIVILEGES`; granular grants only.
- No `mysqldump` as the production backup strategy — managed snapshots / PITR / Percona XtraBackup.

## Generation steps

1. Detect version + flavor, hosting, stack, workload, tenancy — confirm what can't be detected.
2. Route: read the matching reference file(s) end-to-end before writing anything.
3. New schema → DDL (`utf8mb4`, `BIGINT UNSIGNED` PK, `DATETIME(6)`) + one initial migration in the project's tool.
4. Slow query → `EXPLAIN ANALYZE` (8.0.18+), smallest fix first (`references/performance.md`).
5. Validate with the `mysql` CLI + `EXPLAIN ANALYZE`; in CI, smoke a representative query against a seeded DB.

## Handoffs

- Cross-engine modeling decisions (id strategy, money, soft-delete, tenancy pattern *choice*) → `data/_shared/schema-design`
- Expand-contract pattern + migration tool selection → `data/_shared/migrations`
- Cache-aside/stampede/TTL pattern catalog → `data/_shared/caching-patterns` + `data/redis`
- Universal query triage (ESR, N+1, pagination) → `data/_shared/query-optimization`
- Testing the schema/queries → `qa/{java,dotnet,typescript}/skills/db-testing/*`
- Tenant/user claims feeding app-enforced tenancy → `auth/auth0-{stack}` + `auth/_shared/auth0-concepts`
- AWS (RDS/Aurora) / Azure (Flexible Server) deployment → `devops/*`; query-latency telemetry → `observability/*`
- Postgres / SQL Server equivalents → `data/postgresql` · `data/sqlserver`
