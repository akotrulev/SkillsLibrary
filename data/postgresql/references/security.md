# PostgreSQL — Security (roles, RLS, encryption, audit)

Engine-level data security: who can connect, what they can touch, which rows they can see, and what gets recorded when they change something. Tenant/user claims arrive from the app's identity layer (`auth/auth0-{stack}` + `auth/_shared/auth0-concepts`); this file is where those claims meet the engine. Application-layer security testing → `qa/_shared/agents/qa-security` (peer).

## Role model — least privilege by construction

Three-role minimum per database, none of them superuser:

| Role | Rights | Used by |
|---|---|---|
| `app_owner` | Owns schema + objects; `CREATE`/`ALTER`/`DROP` | **Migration tool only** (Flyway/EF/Prisma CI step) |
| `app_rw` | `SELECT/INSERT/UPDATE/DELETE` on app tables; `USAGE` on sequences | The application runtime |
| `app_ro` | `SELECT` only | Reporting, dashboards, ad-hoc analysis, read replicas |

```sql
CREATE ROLE app_owner NOLOGIN;
CREATE ROLE app_rw    LOGIN PASSWORD :'pw' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE app_ro    LOGIN PASSWORD :'pw' NOSUPERUSER;

GRANT USAGE ON SCHEMA app TO app_rw, app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO app_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO app_rw;
GRANT SELECT ON ALL TABLES IN SCHEMA app TO app_ro;

-- Future objects created by migrations inherit the grants — without this,
-- every new table silently lacks runtime permissions:
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app
  GRANT SELECT ON TABLES TO app_ro;
```

Rules:

- The app **never** connects as the owner — an owner connection bypasses RLS on its own tables (see below) and can DROP them.
- Revoke the footguns: `REVOKE CREATE ON SCHEMA public FROM PUBLIC;` (default-open `public` schema pre-PG 15; 15+ already restricts it).
- Per-role guardrails: `ALTER ROLE app_rw SET statement_timeout = '30s';` and `SET idle_in_transaction_session_timeout = '60s';`
- Passwords are SCRAM: `password_encryption = scram-sha-256` (default since PG 14); no `md5` entries left in `pg_hba.conf`. PG 18 adds OAuth 2.0 authentication — relevant for human/SSO access, not app service accounts.

## Row-Level Security (RLS) — multi-tenant isolation

Defense in depth for shared-schema multi-tenancy (`data/_shared/schema-design` owns the pattern *choice*): every query still filters `tenant_id` explicitly in app code; RLS makes the engine enforce it so one missed `WHERE` can't leak across tenants.

### The canonical setup

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;   -- applies to the table owner too

CREATE POLICY tenant_isolation ON orders
  USING (tenant_id = current_setting('app.tenant_id')::bigint);
  -- USING gates reads + which rows UPDATE/DELETE can see;
  -- add WITH CHECK (same predicate) to also gate what INSERT/UPDATE may write —
  -- without it a tenant could insert rows carrying another tenant_id.

CREATE POLICY tenant_isolation_write ON orders
  FOR INSERT WITH CHECK (tenant_id = current_setting('app.tenant_id')::bigint);
```

The app sets the tenant context **per transaction**, from the validated JWT claim — never from a request body:

```sql
SET LOCAL app.tenant_id = '42';   -- SET LOCAL: scoped to the transaction,
                                  -- mandatory under PgBouncer transaction mode
```

Per stack: EF Core — open the transaction, issue `SET LOCAL` via an interceptor; Spring — a `ConnectionPreparer`/AOP advice around `@Transactional`; Node — `pool.query` wrapper that runs `SET LOCAL` first in the same transaction.

### RLS rules and caveats

- **`FORCE ROW LEVEL SECURITY`** always — otherwise the table owner bypasses policies silently (and `BYPASSRLS`/superuser roles always bypass; that's another reason the app role is neither).
- `current_setting('app.tenant_id')` with no second argument **throws** when unset — good: an unset context fails closed. `current_setting(..., true)` returns NULL and fails open; don't use it in policies.
- **Performance**: the policy predicate is added to every query. Keep it a plain indexed comparison (`tenant_id = ...`). Every multi-tenant index leads with `tenant_id`. Policies that call subqueries or non-`LEAKPROOF` functions block index/qual pushdown and can wreck plans — check `EXPLAIN` output for the policy qual.
- RLS composes with composite FKs (`references/data-modeling.md`) — engine-level row visibility + engine-level cross-table tenant integrity.
- Test it like code: a `qa` integration test that sets tenant A's context and asserts tenant B's rows are invisible *and unwritable* (`qa/{java,dotnet,typescript}/skills/db-testing/*`).

## Column privileges & encryption

- **Column-level grants** for narrow needs: `GRANT SELECT (id, email) ON users TO support_role;` — cheaper than a view when it's just column hiding; use a view when rows also need filtering (or RLS).
- **Encryption at rest** is the platform's job (Aurora/Azure Flexible Server encrypt by default; self-hosted: disk/filesystem encryption). It protects stolen disks, not queried data.
- **`pgcrypto` (`pgp_sym_encrypt`)** protects data from anyone with table SELECT — but the key must live outside the database (app/KMS), values are unindexable (equality only via a separate deterministic hash column), and `pg_stat_statements`/logs can leak parameters. Use for narrow high-value fields (tokens, government ids).
- **App-side encryption** (encrypt before INSERT, KMS-held keys) is the stronger default for PII fields that never need SQL predicates — the DB never sees plaintext.
- Ordering: at-rest (always, free) → column grants/views (cheap) → app-side field encryption (PII) → `pgcrypto` (only when encryption must happen in SQL).

## Connection security

- `sslmode=verify-full` in every connection string — `require` (the common copy-paste) encrypts but does **not** verify the server cert, allowing MITM. Managed platforms publish their CA bundle.
- `pg_hba.conf` (self-hosted): `hostssl` entries only, `scram-sha-256`, no `trust`, no `0.0.0.0/0`.
- Secrets in env/secret store; rotate via two live logins (create new → cut over → drop old), never in-place password edits under load.

## Audit — who changed what, when, and why

Three tools; pick by requirement (and see `references/data-modeling.md` for the fourth option — a full history/temporal table when *queryable point-in-time state* is the requirement, not just a log):

| | Trigger-based edit log | `pgaudit` | History/temporal table |
|---|---|---|---|
| Captures | Row-level OLD/NEW diff, actor, reason | Statement text + role (no row values by default) | Full row versions |
| Answers | "who changed this row and what did it say before" | "what DDL/DML ran, by whom" (compliance/forensics) | "what did the row look like on date X" |
| Cost | Trigger per write on opted-in tables | Log volume; no schema | Table growth; write amplification |
| Use for | **High-value records** (see below) | Regulatory statement logging, DDL audit | Effective-dated domain data |

### Trigger-based edit log (the house pattern for high-value records)

Attach **selectively** — not to every table. Warranted for: admin-panel settings/configuration tables, permission/role assignments, data-seeding runs (seed provenance: which batch inserted/changed a row), snapshot/restore events, and financially significant records.

```sql
CREATE TABLE audit_log (
    id          bigint      GENERATED ALWAYS AS IDENTITY,
    at          timestamptz NOT NULL DEFAULT now(),
    table_name  text        NOT NULL,
    row_pk      text        NOT NULL,
    op          text        NOT NULL CHECK (op IN ('I','U','D')),
    actor       text        NOT NULL,   -- from the app-set GUC, not session_user
    request_id  text,                   -- correlation id from the app
    reason      text,                   -- optional "why", app-supplied
    old_row     jsonb,
    new_row     jsonb,
    PRIMARY KEY (at, id)
) PARTITION BY RANGE (at);              -- monthly partitions; DROP old partitions per retention

CREATE OR REPLACE FUNCTION audit_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO audit_log (table_name, row_pk, op, actor, request_id, old_row, new_row)
    VALUES (TG_TABLE_NAME,
            COALESCE(NEW.id, OLD.id)::text,
            left(TG_OP, 1),
            current_setting('app.actor'),            -- fails closed if unset
            current_setting('app.request_id', true),
            to_jsonb(OLD), to_jsonb(NEW));
    RETURN COALESCE(NEW, OLD);
END $$;

CREATE TRIGGER settings_audit AFTER INSERT OR UPDATE OR DELETE ON app_settings
    FOR EACH ROW EXECUTE FUNCTION audit_row();
```

Rules:

- Actor + request id come from **app-set GUCs** (`SET LOCAL app.actor = ...` alongside the tenant GUC) — `session_user` is just `app_rw` and tells you nothing.
- The log table gets **no UPDATE/DELETE grants** for `app_rw` — append-only by privilege (`GRANT INSERT ON audit_log TO app_rw;` only). Retention = `DROP PARTITION`, run by the owner role.
- Store the **diff you'll actually read**: `to_jsonb(OLD)`/`to_jsonb(NEW)` full rows are simplest and compress well; strip bulky columns in the trigger if a table carries blobs.
- PG 18 alternative for app-side capture: `UPDATE ... RETURNING OLD.*, NEW.*` lets the app write the audit row itself in the same transaction — fewer triggers, but every write path must remember to do it; the trigger can't be forgotten.

### `pgaudit`

Extension (available on RDS/Aurora/Azure): `pgaudit.log = 'ddl, role'` is the low-noise baseline (all DDL + grants), widen to `write` per compliance need. It logs statements, not row images — pair with the trigger log when before/after values are required.

## Anti-patterns

- App connects as owner/superuser; RLS silently bypassed.
- RLS without `FORCE`; policies using `current_setting(..., true)` (fails open).
- Tenant id read from the request body instead of the validated token claim.
- `SET` instead of `SET LOCAL` under PgBouncer transaction mode (context leaks across pooled transactions).
- `sslmode=require` in production ("encrypted to whoever answered").
- Audit triggers on every table "just in case" — write amplification with no reader.
- Audit log the runtime role can UPDATE/DELETE.
- `pgcrypto` keys stored in the same database they protect.
- Missing `ALTER DEFAULT PRIVILEGES` — every migration ships tables the app can't read until someone gets paged.
