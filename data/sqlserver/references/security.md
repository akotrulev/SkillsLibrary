# SQL Server — Security (roles, RLS, encryption, masking, Ledger, audit)

Engine-level data security: who can connect, what they can touch, which rows they can see, what's masked, what's tamper-evident, and what gets recorded. Tenant/user claims arrive from the app's identity layer (`auth/auth0-{stack}` + `auth/_shared/auth0-concepts`); this file is where those claims meet the engine. Application-layer security testing → `qa/_shared/agents/qa-security` (peer).

## Principal model — least privilege by construction

SQL Server separates **logins** (server-level, authenticate) from **users** (database-level, authorize). Grant through **database roles**, never to users directly.

| Role | Rights | Used by |
|---|---|---|
| `db_ddladmin` (or a custom `app_migrator`) | `CREATE`/`ALTER`/`DROP` in the app schema | **Migration tool only** (Flyway/EF/DbUp CI step) |
| custom `app_rw` | `SELECT/INSERT/UPDATE/DELETE` on the app schema | The application runtime |
| custom `app_ro` | `SELECT` only | Reporting, dashboards, read replicas |

```sql
CREATE ROLE app_rw;
CREATE ROLE app_ro;

-- Grant at the SCHEMA level so future tables inherit automatically (SQL Server's
-- answer to Postgres ALTER DEFAULT PRIVILEGES — grant once on the schema):
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::app TO app_rw;
GRANT SELECT                          ON SCHEMA::app TO app_ro;

-- The app user is a member of the role, and NOTHING more:
CREATE USER app_login FOR LOGIN app_login WITH DEFAULT_SCHEMA = app;
ALTER ROLE app_rw ADD MEMBER app_login;
```

Rules:

- The app **never** connects as `db_owner`, `sysadmin`, or the schema owner — an owner/`sysadmin` connection **bypasses RLS** (see below) and can DROP objects.
- Prefer **EXECUTE-only on stored procedures** (grant `EXECUTE ON SCHEMA::app`, revoke table DML) when the data-access layer is procedure-based — the tightest surface.
- Azure SQL: **Entra ID (Managed Identity)** logins over SQL logins; contained database users where possible. Box: Windows auth over SQL auth.
- Schema-level grants are the inheritance mechanism — grant on `SCHEMA::app`, not table-by-table, so a new migration's table is immediately usable.

## Row-Level Security (RLS) — multi-tenant isolation

Defense in depth for shared-schema multi-tenancy (`data/_shared/schema-design` owns the pattern *choice*): every query still filters `TenantId` in app code; RLS makes the engine enforce it so one missed `WHERE` can't leak across tenants. SQL Server implements it as a **security policy** binding an inline table-valued **predicate function**.

### The canonical setup

```sql
-- 1. The predicate function: returns a row (=allow) when the tenant matches
--    the value the app stashed in SESSION_CONTEXT for this connection.
CREATE FUNCTION app.fn_tenant_predicate(@TenantId bigint)
    RETURNS TABLE
    WITH SCHEMABINDING
AS RETURN
    SELECT 1 AS ok
    WHERE @TenantId = CAST(SESSION_CONTEXT(N'TenantId') AS bigint);

-- 2. The security policy binds it as BOTH a filter (reads + which rows
--    UPDATE/DELETE can see) and a block (what INSERT/UPDATE may write).
CREATE SECURITY POLICY app.TenantSecurityPolicy
    ADD FILTER PREDICATE app.fn_tenant_predicate(TenantId) ON app.Orders,
    ADD BLOCK PREDICATE  app.fn_tenant_predicate(TenantId) ON app.Orders AFTER INSERT,
    ADD BLOCK PREDICATE  app.fn_tenant_predicate(TenantId) ON app.Orders AFTER UPDATE
    WITH (STATE = ON);
```

- **FILTER PREDICATE** silently removes non-matching rows from reads and from the scope of UPDATE/DELETE.
- **BLOCK PREDICATE** (`AFTER INSERT`/`AFTER UPDATE`) is the mandatory complement — without it a tenant could *insert* a row carrying another tenant's `TenantId`. Analogous to Postgres `WITH CHECK`.

The app sets the tenant context **per connection, from the validated JWT claim** — never from a request body:

```sql
EXEC sys.sp_set_session_context @key = N'TenantId', @value = 42, @read_only = 1;
```

Per stack: EF Core — a `DbConnectionInterceptor` that runs `sp_set_session_context` when the connection opens (and clears/re-sets it because **pooled connections are reused** — always set it on every open, never assume the previous tenant's value is gone); Spring — a `DataSource` wrapper / AOP advice; Node `mssql` — a per-request wrapper that runs it first. `@read_only = 1` stops app code from tampering with it after it's set.

### RLS rules and caveats

- **Pooled-connection hazard**: `SESSION_CONTEXT` lives for the connection's life and connections are pooled. Set `TenantId` on **every** connection open/reset; a leaked value = cross-tenant read. This is the single most common RLS-in-SQL-Server bug.
- `sysadmin` and the db owner **bypass** RLS entirely — another reason the app role is neither.
- **Performance**: the predicate is `AND`-ed into every query. Keep it a plain indexed comparison and make sure **every index leads with `TenantId`** (`references/indexing.md`) so the predicate is a seek, not a scan. Check the actual plan for the added predicate.
- `SCHEMABINDING` on the function is required and pins the referenced objects.
- Test it like code: a `qa` integration test that sets tenant A's context and asserts tenant B's rows are invisible *and unwritable* (`qa/{stack}/skills/db-testing/*`).

## Encryption — Always Encrypted vs TDE vs column-level

Three different threats; **order them, don't confuse them**:

| | TDE | Always Encrypted | Dynamic Data Masking |
|---|---|---|---|
| Protects against | Stolen `.mdf`/backup files (at rest) | The DBA / anyone with SELECT — plaintext never enters the engine | Casual over-shoulder / low-priv app users seeing full values |
| Where decryption happens | In the engine (transparent) | In the **client driver** | Nowhere — it's display masking only |
| Queryable | Fully | Equality only (deterministic) or not at all (randomized) | Fully (masking is cosmetic) |
| Real security boundary | Disk theft only | **Yes** — strongest | **No** — trivially bypassed with `UNMASK` or a computed expression |

- **TDE**: on by default in Azure SQL; enable on the box for any DB with regulated data. Protects at-rest files, nothing against a live query. Free — always on.
- **Always Encrypted**: for high-value fields (SSN, card PAN) where even the DBA must not see plaintext. Keys: a **Column Master Key** in a key store (Azure Key Vault / Windows cert store) + **Column Encryption Keys** in the DB encrypted by the CMK. Deterministic encryption allows equality lookups (and equality joins on the same CEK); randomized is stronger but unqueryable. Use **Always Encrypted with secure enclaves** (2019+) to get range queries + in-place encryption. The driver must be enclave-aware and the connection string carries `Column Encryption Setting=Enabled`.
- **Dynamic Data Masking is NOT a security control** — it only changes display for principals lacking `UNMASK`; a `WHERE` on the column or a join still sees real values. Use it for convenience (hide most of an email in a support UI), never as the boundary.
- **Ordering**: TDE (always, free) → column grants / views (cheap, hide columns) → DDM (cosmetic convenience) → Always Encrypted (the real boundary for PII the DB must never see in plaintext).

## Ledger — tamper-evidence (2022+)

For records where you must **prove** data wasn't altered (financial ledgers, audit trails, regulatory): **updatable ledger tables** (history + cryptographic hashes) or **append-only ledger tables** (insert-only, no UPDATE/DELETE permitted). The engine maintains a Merkle-tree database digest you can store off-box (immutable Azure storage) and later verify with `sys.sp_verify_database_ledger`. Reach for it when the requirement is *tamper-evidence*, not merely history (temporal tables, `references/data-modeling.md`) or *who-did-what* (audit log, below).

## Connection security

- `Encrypt=True` + `TrustServerCertificate=False` in every connection string — 2022+ drivers default `Encrypt=True`, but be explicit. `TrustServerCertificate=True` disables cert validation → MITM; never in production.
- Entra ID auth (Managed Identity) for Azure SQL; secrets in Key Vault, rotated via two live logins (create new → cut over → drop old), never in-place under load.
- Box: firewall to app subnets only; disable the `sa` login; no `xp_cmdshell`.

## Audit — who changed what, when, and why

Pick by requirement (and see `references/data-modeling.md` for temporal tables — the fourth option, when *queryable point-in-time state* is the requirement, not a log):

| | Trigger-based edit log | SQL Server Audit | Change Data Capture / Change Tracking | Ledger |
|---|---|---|---|---|
| Captures | Row-level OLD/NEW diff, actor, reason | Statement/action + principal (server or DB level) | Row changes for **consumers** (ETL/sync), not forensics | Cryptographically verifiable change proof |
| Answers | "who changed this row and what did it say before" | "what action ran, by whom" (compliance) | "what rows changed since I last read" | "prove nobody tampered with this" |
| Cost | Trigger per write on opted-in tables | Managed feature; log volume | Log reader / version store overhead | Storage + digest management |
| Use for | **High-value records** (below) | Regulatory action logging, DDL/login audit | Data movement / incremental sync | Tamper-evidence requirement |

### Trigger-based edit log (the house pattern for high-value records)

Attach **selectively** — admin settings/config tables, permission/role changes, data-seeding provenance, financially significant records. Not every table.

```sql
CREATE TABLE app.AuditLog (
    Id         bigint       IDENTITY(1,1),
    At         datetime2(7) NOT NULL CONSTRAINT DF_AuditLog_At DEFAULT SYSUTCDATETIME(),
    TableName  sysname      NOT NULL,
    RowPk      nvarchar(100) NOT NULL,
    Op         char(1)      NOT NULL CHECK (Op IN ('I','U','D')),
    Actor      nvarchar(128) NOT NULL,      -- from SESSION_CONTEXT, not SUSER_SNAME()
    RequestId  nvarchar(64)      NULL,
    OldRow     nvarchar(max)     NULL,      -- FOR JSON
    NewRow     nvarchar(max)     NULL,
    CONSTRAINT PK_AuditLog PRIMARY KEY CLUSTERED (At, Id)
);

CREATE TRIGGER app.TR_AppSettings_Audit ON app.AppSettings
    AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO app.AuditLog (TableName, RowPk, Op, Actor, RequestId, OldRow, NewRow)
    SELECT N'AppSettings',
           CAST(COALESCE(i.Id, d.Id) AS nvarchar(100)),
           CASE WHEN i.Id IS NOT NULL AND d.Id IS NOT NULL THEN 'U'
                WHEN i.Id IS NOT NULL THEN 'I' ELSE 'D' END,
           CAST(SESSION_CONTEXT(N'Actor') AS nvarchar(128)),      -- app-set, per connection
           CAST(SESSION_CONTEXT(N'RequestId') AS nvarchar(64)),
           (SELECT d.* FOR JSON PATH, WITHOUT_ARRAY_WRAPPER),
           (SELECT i.* FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i FULL JOIN deleted d ON i.Id = d.Id;
END;
```

Rules:

- Actor + request id come from **`SESSION_CONTEXT`** set by the app (alongside `TenantId`) — `SUSER_SNAME()`/`SYSTEM_USER` is just `app_rw` and tells you nothing.
- The trigger fires **once per statement** (set-based), not per row — that `FULL JOIN inserted/deleted` handles multi-row writes correctly; a row-at-a-time trigger is a bug and a perf trap.
- The audit table gets **INSERT-only** grants for `app_rw` (`GRANT INSERT ON app.AuditLog TO app_rw;`, no UPDATE/DELETE) — append-only by privilege. Retention: partition by `At` and switch out old partitions (or a scheduled purge run by the owner role).
- Store the diff you'll actually read (`FOR JSON`); strip bulky/blob columns.

### SQL Server Audit

The managed feature for compliance: define a **server audit** (target = file / Windows Security log) + **audit specifications** (`DATABASE_OBJECT_CHANGE_GROUP`, `SCHEMA_OBJECT_ACCESS_GROUP`, login audit, etc.). Logs actions and principals, not before/after row images — pair it with the trigger log when row diffs are required. Azure SQL uses **Auditing to a storage account / Log Analytics**.

## Anti-patterns

- App connects as `db_owner`/`sysadmin`; RLS silently bypassed.
- `SESSION_CONTEXT` set once and assumed to persist — pooled connection reuse leaks the previous tenant's value; set it on **every** open.
- RLS FILTER predicate without the matching BLOCK predicate — cross-tenant inserts.
- Tenant id read from the request body instead of the validated token claim.
- Treating Dynamic Data Masking as a security boundary (it isn't — `UNMASK` / any `WHERE` bypasses it).
- `TrustServerCertificate=True` in production ("encrypted to whoever answered").
- Row-at-a-time audit trigger (wrong for multi-row DML + slow).
- Audit/ledger table the runtime role can UPDATE/DELETE.
- Always Encrypted keys stored where the DBA who's the threat can reach them.
- Table-by-table grants instead of `GRANT ... ON SCHEMA::app` — new migration tables silently unreadable until someone gets paged.
