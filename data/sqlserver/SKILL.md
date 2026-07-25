---
name: data-sqlserver
description: Use when designing tables, securing data (roles/RLS/Always Encrypted/Ledger), writing T-SQL queries or migrations, choosing indexes, caching, or tuning SQL Server / Azure SQL from a .NET / Java / Node backend. Pick the topic in the routing table, then read its reference. Triggers: "design a SQL Server schema", "row-level security", "this T-SQL is slow", "Azure SQL tier choice". Do NOT use for other engines, cross-engine modeling (`data/_shared/schema-design`), or DB tests (qa `db-testing`).
---

# Data — SQL Server / Azure SQL

One registered skill, five topic references. This file routes and holds the rules shared by every topic: version policy, connections/pooling, migration discipline, and the hard rules. **Read the matching `references/<topic>.md` end-to-end before writing any code.** These split by *topic*, not by tool — a task may need two files (a new multi-tenant schema = `data-modeling.md` + `security.md`).

## Routing table

| Read | Use when |
|------|----------|
| `references/data-modeling.md` | New tables/schemas, relationships, foreign keys, constraints, clustered-index choice, identity vs sequence, temporal (system-versioned) tables |
| `references/security.md` | Roles & schemas, row-level security (security policies), Always Encrypted / TDE / Dynamic Data Masking, Ledger, TLS/Entra auth, SQL Audit |
| `references/indexing.md` | Choosing or fixing indexes, clustered choice, INCLUDE/covering, filtered, columnstore, online/resumable rebuild, missing-index DMVs |
| `references/performance.md` | Slow queries, Query Store, execution plans, parameter sniffing, IQP, tempdb, deadlocks, memory grants, read scale-out |
| `references/caching.md` | Indexed views, in-memory OLTP, plan forcing as a cache, buffer pool mental model, the external-cache seam |

## Version policy — SQL Server 2025 primary, 2022 supported, 2019 down-level; Azure SQL evergreen

First act on an existing database: **detect the version and compatibility level** (`SELECT @@VERSION;` and `SELECT compatibility_level FROM sys.databases WHERE name = DB_NAME();`) and key every recipe to it. Never apply a 2025-only construct to a down-level server; never flag a down-level server for lacking one. Azure SQL Database is evergreen (always latest engine) — treat it as ≥ 2025 for engine features, but note its surface-area gaps (no `USE`, no cross-DB by default, no SQL Agent — use Elastic Jobs). Compatibility levels: **2025 = 170, 2022 = 160, 2019 = 150.**

| 2025 construct | 2022 / 2019 fallback |
|---|---|
| Native `json` data type + JSON indexes | `nvarchar(max)` + `CONSTRAINT ... CHECK (ISJSON(col) = 1)`, `JSON_VALUE`/`OPENJSON` |
| Native `vector` type + vector search | external vector store; no in-engine ANN |
| `REGEXP_LIKE` / regex T-SQL functions | `LIKE`/`PATINDEX`, or SQLCLR |
| Optional-parameter plan optimization | Parameter Sensitive Plan optimization (2022) · `OPTION (RECOMPILE)` / `OPTIMIZE FOR UNKNOWN` (2019) |
| Query Store **on by default** for new DBs (2022+) | enable it explicitly (`references/performance.md`) |
| `GENERATE_SERIES`, `DATETRUNC`, `LEAST`/`GREATEST` (2022+) | manual tally table / `DATEADD`+`DATEDIFF` / `CASE` |

Managed: Azure SQL MI tracks the box engine with a lag; RLS, Always Encrypted, Ledger, Query Store, temporal tables, columnstore, and online index rebuild are available across supported versions (only Enterprise gates a few — noted per recipe, e.g. online rebuild).

## Stack defaults (align with CLAUDE.md)

- **.NET 10** (8/9 supported): `Microsoft.Data.SqlClient` + EF Core (`Microsoft.EntityFrameworkCore.SqlServer`); raw `SqlCommand` for hot paths. Migrations via EF Core or DbUp.
- **Java 21 + Spring Boot 3.x**: `mssql-jdbc` driver + Spring Data JPA, HikariCP pool. Migrations via Flyway (preferred) or Liquibase.
- **Node 24 + TypeScript**: `mssql` (Tedious) driver, or Prisma / Drizzle / TypeORM. Migrations via the ORM's tool.
- Driver connection pool per app instance (`Max Pool Size` default 100; size to your DB tier, not "as high as possible"). **MARS off** unless a specific interleaved-reader need — it hides subtle races. Behind the Azure SQL gateway for managed.

## Inputs needed

1. **Version + compatibility level** (drives everything — see version policy)
2. **Edition/hosting**: SQL Server box (Enterprise vs Standard — gates online rebuild, some columnstore) vs Azure SQL (Single / Elastic Pool / Hyperscale / Managed Instance)
3. **Backend stack** (.NET / Java / Node) — determines client + migration tool
4. **Workload shape**: OLTP, read-heavy, write-heavy, mixed, analytics
5. **Row counts and growth** — drives partitioning, columnstore, index choices
6. **Tenancy model** — single- or multi-tenant (routes to `references/security.md` RLS)

## Connections (per stack)

### .NET 10

```csharp
builder.Services.AddDbContext<AppDb>(opt =>
    opt.UseSqlServer(builder.Configuration.GetConnectionString("Sql"),
        sql => sql
            .EnableRetryOnFailure(maxRetryCount: 6, maxRetryDelay: TimeSpan.FromSeconds(10), errorNumbersToAdd: null)
            .CommandTimeout(30)));

// Connection string from env / Key Vault, never appsettings.json:
// "Server=tcp:yourco-prod.database.windows.net,1433;Database=orders;
//  Authentication=Active Directory Default;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30"
```

Prefer **Microsoft Entra ID auth via Managed Identity** over SQL logins for Azure SQL. `Encrypt=True` + `TrustServerCertificate=False` mandatory (2022+ drivers default `Encrypt=True`).

### Java 21 + Spring Boot

```yaml
spring:
  datasource:
    url: jdbc:sqlserver://yourco-prod.database.windows.net:1433;database=orders;encrypt=true;trustServerCertificate=false;loginTimeout=30
    driver-class-name: com.microsoft.sqlserver.jdbc.SQLServerDriver
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
      hibernate.dialect: org.hibernate.dialect.SQLServerDialect
```

### Node 24 + TypeScript

```typescript
import sql from 'mssql';

export const pool = await new sql.ConnectionPool({
  server: process.env.SQL_SERVER!,
  database: process.env.SQL_DB!,
  authentication: { type: 'azure-active-directory-default' },
  options: { encrypt: true, trustServerCertificate: false },
  pool: { max: 20, min: 0, idleTimeoutMillis: 30_000 },
}).connect();
```

Parameterize every query: `pool.request().input('id', sql.BigInt, id).query('SELECT ... WHERE Id = @id')` — never string-concat.

## Migrations

- **One migration per logical change.** Add-column AND backfill AND add-constraint is three migrations.
- **Forward-only in production.** Down scripts are local-dev only; roll forward with a corrective migration.
- **Online-safe DDL patterns:**
  - Nullable column add → metadata-only, instant.
  - NOT NULL with a **runtime-constant literal default** → metadata-only since 2012 (no rewrite). A computed/non-deterministic default rewrites — split into add-nullable → batched backfill → `ALTER COLUMN ... NOT NULL`.
  - Index on a large hot table → `WITH (ONLINE = ON)` (Enterprise / Azure SQL / Hyperscale; **offline on Standard box**). Add `RESUMABLE = ON` so a long build can be paused/resumed. Plan a window when online isn't available.
  - FK/CHECK on a large table → add `WITH NOCHECK` (stops new violations, no scan) then `WITH CHECK CHECK CONSTRAINT` to validate — but note a `NOCHECK` constraint is **not trusted** by the optimizer until validated.
  - Renames: expand-contract across two deploys (add new → dual-write → switch reads → drop old). Never drop a column in the same release that stops writing it.
- Universal expand-contract pattern + tool table → `data/_shared/migrations`.

## Rules

- Schema changes only via the migration tool; never SSMS in prod.
- Separate roles/schemas: migrations get DDL, runtime gets DML only, nobody's app connects as `db_owner` (`references/security.md`).
- `Encrypt=True`; Entra ID auth where possible, else short-lived passwords from Key Vault.
- Parameterized queries only — no string concatenation, ever.
- `datetime2(7)` for events (never legacy `datetime`); `datetimeoffset(7)` when the zone must be preserved; store UTC.
- `READ COMMITTED` with **`READ_COMMITTED_SNAPSHOT ON`** as the default isolation (no reader-writer blocking) — the safe Azure SQL default.
- Every collection query has a `TOP`/`OFFSET…FETCH`; keyset pagination over deep `OFFSET`.
- Explicit columns — no `SELECT *` in code.
- `rowversion` column + optimistic concurrency for shared rows (EF Core uses it natively).
- Query Store enabled in prod with a storage cap; `NOLOCK` reviewed and rejected unless documented as accepting dirty reads.

## What NOT to do

- No `IDENTITY` + `SEQUENCE` for the same logical key.
- No `NEWID()` as a clustered-PK default — heavy fragmentation; use `NEWSEQUENTIALID()` or a `bigint IDENTITY` surrogate with a non-clustered PK on the GUID.
- No legacy `datetime`; `datetime2(7)`.
- No `NOLOCK` in business/financial queries — ever (dirty + missing/double reads).
- No `SELECT *` in app code; no `OFFSET 1000000 ROWS FETCH 20`.
- No application code issuing DDL — migrations only.
- No `DBCC SHRINKDATABASE` as routine maintenance — it fragments every index.
- No app role with `db_owner`; runtime is `db_datareader` + `db_datawriter` (or EXECUTE-on-procs only).
- No mixing collations across joined columns without intent — implicit conversion kills seeks.
- No `mssql` backup-by-BACPAC as the production strategy — use native backups / managed PITR.

## Generation steps

1. Detect version + compatibility level, edition/hosting, stack, workload, tenancy — confirm what can't be detected.
2. Route: read the matching reference file(s) end-to-end before writing anything.
3. New schema → DDL + one initial migration in the project's tool; choose the clustered index deliberately (+ RLS security policy if multi-tenant).
4. Slow query → capture the **actual** plan + Query Store history, smallest fix first (`references/performance.md`).
5. Validate with SSMS + `SET STATISTICS IO, TIME ON`; in CI, smoke a representative query against a seeded DB.

## Handoffs

- Cross-engine modeling decisions (id strategy, money, soft-delete, tenancy pattern *choice*) → `data/_shared/schema-design`
- Expand-contract pattern + migration tool selection → `data/_shared/migrations`
- Cache-aside/stampede/TTL pattern catalog → `data/_shared/caching-patterns` + `data/redis`
- Universal query triage (ESR, N+1, pagination) → `data/_shared/query-optimization`
- Testing the schema/queries → `qa/{java,dotnet,typescript}/skills/db-testing/*`
- Tenant/user claims feeding the RLS `SESSION_CONTEXT` → `auth/auth0-{stack}` + `auth/_shared/auth0-concepts`
- Azure deployment of the DB itself → cloud provisioning / IaC for the store itself has no owning skill in this library yet; out of this domain's scope
- Query-latency telemetry → `observability/*` skills (via the `observability-engineer-{dotnet,java,node}` peer bundled in the matching `be-*` plugin)
- Postgres / MySQL equivalents → `data/postgresql` · `data/mysql`
