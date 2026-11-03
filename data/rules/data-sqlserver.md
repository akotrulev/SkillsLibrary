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

<!-- data rules v1 (2026-11-03): SQL Server. Installed by /data:rules when the project uses SQL Server or Azure SQL; narrow the paths above to this engine's files when the repo has several engines. -->

# SQL Server / Azure SQL standards (2025 primary, 2022 supported, 2019 down-level)

Severity tags as in the core data rules. Never a 2025-only construct below compatibility level 170.

- `datetime2(7)` for events, `datetimeoffset(7)` when the zone must survive, in UTC; never legacy `datetime`. *major*
- Never `NEWID()` as the clustered key: `NEWSEQUENTIALID()`, or a `bigint IDENTITY` clustered key with a non-clustered GUID. Never `IDENTITY` and a `SEQUENCE` for one key. No heap outside transient staging. *major*
- A `rowversion` column for optimistic concurrency on shared rows. *major*
- No multiple cascade paths to one table. *major*
- Before 2025, JSON in `nvarchar(max)` carries `CHECK (ISJSON(col) = 1)`; a queried field is promoted to a computed column. *minor*
- `READ_COMMITTED_SNAPSHOT ON` as the default isolation; never `NOLOCK` in a business or financial query. *blocker*
- No `OPTION (RECOMPILE)` sprinkled as a fix; no mixed collations across joined columns. *major*
- Index on a large hot table `WITH (ONLINE = ON, RESUMABLE = ON)` where the edition has it, else a planned window. FK or CHECK on a large table: `WITH NOCHECK`, then `WITH CHECK CHECK CONSTRAINT`. A non-constant default with NOT NULL is nullable, backfill, then `ALTER COLUMN … NOT NULL`. *major*
- RLS: a security policy with both FILTER and BLOCK predicates on a `SCHEMABINDING` function; `SESSION_CONTEXT` is set on every connection open, because pooled connections keep the last tenant. *blocker*
- The runtime role is `db_datareader` + `db_datawriter` (or `EXECUTE` on procs), granted `ON SCHEMA::`; never `db_owner` or `sysadmin`. Dynamic Data Masking is not a security boundary. *blocker*
- No `DBCC SHRINKDATABASE` or `SHRINKFILE` in a maintenance job. *major*
- Query Store on in production, with a storage cap. *minor*
