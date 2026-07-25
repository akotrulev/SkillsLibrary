# MySQL — Security (privileges, tenancy without RLS, encryption, audit)

Engine-level data security: who can connect, what they can touch, how tenant isolation is enforced **without row-level security**, what's encrypted, and what's recorded. Tenant/user claims arrive from the app's identity layer (`auth/auth0-{stack}` + `auth/_shared/auth0-concepts`); this file is where those claims meet the engine. Application-layer security testing → `qa/_shared/agents/qa-security` (peer).

## The headline difference: MySQL has no row-level security

Unlike Postgres RLS and SQL Server security policies, **MySQL/InnoDB has no engine-level row filtering**. There is no `FORCE ROW LEVEL SECURITY`, no predicate policy. This changes the multi-tenant story fundamentally — isolation is **app-enforced**, with the engine helping only at coarser grains (views, per-tenant accounts, schemas). Design accordingly (see "Multi-tenancy" below); don't reach for an RLS pattern that doesn't exist.

## Privilege model — least privilege by construction

MySQL grants privileges to **accounts** (`'user'@'host'`). Grant through the narrowest scope that works; since MySQL 8 use **roles** to avoid per-account drift.

| Account/role | Rights | Used by |
|---|---|---|
| `app_migrator` | `CREATE, ALTER, DROP, INDEX, REFERENCES` on the app schema | **Migration tool only** (Flyway/EF/pt-osc CI step) |
| `app_rw` | `SELECT, INSERT, UPDATE, DELETE` on the app schema | The application runtime |
| `app_ro` | `SELECT` on the app schema | Reporting, dashboards, replicas |

```sql
CREATE ROLE 'app_rw', 'app_ro';
GRANT SELECT, INSERT, UPDATE, DELETE ON app.* TO 'app_rw';   -- schema-wide: new tables inherit
GRANT SELECT                          ON app.* TO 'app_ro';

CREATE USER 'app'@'10.0.%' IDENTIFIED BY :pw REQUIRE SSL;
GRANT 'app_rw' TO 'app'@'10.0.%';
SET DEFAULT ROLE 'app_rw' TO 'app'@'10.0.%';                  -- role active on connect
```

Rules:

- The app **never** connects as `root` or any account with `SUPER`/`ALL PRIVILEGES`. `SUPER` is deprecated — use the granular dynamic privileges (`SYSTEM_VARIABLES_ADMIN`, `CONNECTION_ADMIN`, etc.) for the rare admin need.
- **Grant at `app.*` (schema level)** so migration-created tables are immediately usable — MySQL's answer to Postgres `ALTER DEFAULT PRIVILEGES`. Avoid table-by-table grants (they drift).
- **Host-scope the account** (`'app'@'10.0.%'`) to your app subnet; never `'app'@'%'`.
- `REQUIRE SSL` (or `REQUIRE X509`) on the account forces TLS regardless of the client string.
- Per-account guardrails via a resource group / `max_execution_time` hint; account-level `MAX_USER_CONNECTIONS` to stop one service starving the pool.

## Multi-tenancy without RLS — the three real options

Since there's no RLS, isolation is a **design choice**, enforced in the app plus one of these engine-level aids:

1. **Shared schema, app-enforced `tenant_id` (default for most SaaS).** Every tenant-scoped table has `tenant_id`; **every query filters it in app code**, and the data-access layer is the single choke point that guarantees it (a base repository/queryset that always injects `WHERE tenant_id = ?`, never per-call). Harden with:
   - **Composite FKs** so a child can't reference a parent from another tenant (`references/data-modeling.md`).
   - **Every index leads with `tenant_id`** (`references/indexing.md`) so the filter is a seek.
   - A **`qa` integration test** that proves a query without the tenant filter is impossible through the DAL, and that tenant A can't read/write tenant B's rows (`qa/{java,dotnet,typescript}/skills/db-testing/*`). This test *replaces* the engine guarantee RLS would give — it's not optional.
2. **View-per-tenant / definer's-rights views.** Create views that hard-code `WHERE tenant_id = <t>` and grant the tenant account access only to the view, not the base table. `SQL SECURITY DEFINER` runs the view with the definer's privileges. Workable for a small, static tenant count; doesn't scale to thousands.
3. **Schema-per-tenant or database-per-tenant.** Strongest isolation (separate grants, separate backups, noisy-neighbor isolation) at the cost of migration fan-out (every schema change runs N times) and connection-pool fragmentation. Choose it for compliance/isolation requirements, not convenience — the pattern *choice* lives in `data/_shared/schema-design`.

State which model is in force at the top of the schema; the app's tenancy enforcement is a first-class, tested invariant, not an afterthought.

## Encryption

| | TDE (tablespace encryption) | `keyring` + column functions / app-side | TLS in transit |
|---|---|---|---|
| Protects against | Stolen data files / backups (at rest) | Anyone with table `SELECT` (high-value fields) | Network eavesdropping / MITM |
| Where | Transparent, in-engine | App or SQL function level | Client↔server |

- **At-rest / TDE**: managed services (RDS, Aurora, Azure Flexible Server) encrypt by default — leave it on. Self-hosted: InnoDB tablespace encryption via a `keyring` plugin (`keyring_file` for dev, a KMS-backed keyring for prod). Protects stolen disks/backups, nothing against a live query.
- **Column/field encryption**: MySQL's `AES_ENCRYPT`/`AES_DECRYPT` exist but leak keys into SQL text and logs and make values unindexable — prefer **app-side encryption with KMS-held keys** for PII that never needs a SQL predicate (the DB never sees plaintext). Keep an equality-searchable field as a separate deterministic hash column if you must look it up.
- **In transit**: `REQUIRE SSL` on the account **and** `sslMode=VERIFY_IDENTITY` (JDBC) / `SslMode=VerifyFull` / `rejectUnauthorized:true` (Node) in the client — plain `REQUIRED`/`PREFERRED` encrypts but does not verify the server cert, allowing MITM. IAM database authentication on RDS/Aurora where available (short-lived tokens, no stored password).
- Ordering: at-rest (always, free on managed) → TLS with identity verification (always) → app-side field encryption (PII) → SQL `AES_*` only when encryption must happen in a query (rare, and mind the leaks).

## Audit — who changed what

MySQL Community has **no built-in audit log** — this is an enterprise/flavor gap to plan around:

| | Trigger-based edit log | Audit plugin | Binary log |
|---|---|---|---|
| Availability | Any MySQL | **MySQL Enterprise Audit** (paid) · **MariaDB Audit Plugin** (free) · Percona Audit Plugin (free) | Any MySQL (it's the replication log) |
| Captures | Row-level OLD/NEW diff, actor, reason | Connection + statement events, by policy | Every data-changing statement/row image |
| Answers | "who changed this row and what did it say before" | "what ran, by whom, from where" | "what changed" (for replication/PITR, not friendly forensics) |
| Use for | **High-value records** (below) | Compliance/connection audit (if you have the plugin) | Replication, PITR, CDC — not a primary audit tool |

### Trigger-based edit log (the house pattern where no plugin exists)

Attach **selectively** — admin settings/config, permission changes, seeding provenance, financially significant records. The actor comes from an app-set session variable, since `CURRENT_USER()` is just `app_rw`:

```sql
CREATE TABLE audit_log (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    at          DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    table_name  VARCHAR(64)  NOT NULL,
    row_pk      VARCHAR(100) NOT NULL,
    op          CHAR(1)      NOT NULL,          -- I/U/D
    actor       VARCHAR(128) NOT NULL,
    request_id  VARCHAR(64)      NULL,
    old_row     JSON             NULL,
    new_row     JSON             NULL,
    INDEX idx_audit_at (at)
) ENGINE = InnoDB;

CREATE TRIGGER tr_app_settings_au AFTER UPDATE ON app_settings
FOR EACH ROW
    INSERT INTO audit_log (table_name, row_pk, op, actor, request_id, old_row, new_row)
    VALUES ('app_settings', OLD.id, 'U',
            COALESCE(@app_actor, CURRENT_USER()),   -- app sets @app_actor per connection
            @app_request_id,
            JSON_OBJECT('status', OLD.status, 'value', OLD.value),
            JSON_OBJECT('status', NEW.status, 'value', NEW.value));
```

Rules:

- The app sets `SET @app_actor = ?, @app_request_id = ?` at the **start of the transaction** (these are connection-scoped session variables — set them every transaction; a pooled connection reuses the previous value otherwise, the same hazard as SQL Server `SESSION_CONTEXT`).
- MySQL triggers are **FOR EACH ROW only** (no statement-level triggers) and you write one per operation (`AFTER INSERT` / `AFTER UPDATE` / `AFTER DELETE`) — three triggers per audited table.
- Grant `app_rw` **INSERT only** on `audit_log` (no UPDATE/DELETE) — append-only by privilege. Retention via partitioning by `at` + `ALTER TABLE ... DROP PARTITION`, run by `app_migrator`.
- Triggers add write latency and don't fire for `pt-osc`/`gh-ost` shadow-table cutover or bulk `LOAD DATA` in some configs — know the gaps; for hard compliance use an audit plugin.

## Connection security

- `REQUIRE SSL` on the account + `VERIFY_IDENTITY`/`VerifyFull` in the client (see Encryption). Managed services publish their CA bundle.
- `caching_sha2_password` (MySQL 8 default) over `mysql_native_password`; secrets in env/secret store, rotated via two live accounts (create new → cut over → drop old).
- Disable/lock unused accounts; no anonymous accounts; `root` reachable only from localhost / a bastion.

## Anti-patterns

- Reaching for an "RLS-style" engine policy — MySQL has none; leaving tenant isolation to scattered per-query `WHERE` clauses instead of a single tested DAL choke point.
- App connects as `root` / an account with `SUPER` / `ALL PRIVILEGES` / `'app'@'%'`.
- `tenant_id` read from the request body instead of the validated token claim.
- `sslMode=REQUIRED` in production ("encrypted to whoever answered") — no cert verification.
- `AES_ENCRYPT` with the key passed in SQL text (leaks to logs, general log, binlog).
- Audit `@app_actor` set once and assumed to persist across a pooled connection's next transaction.
- Audit/history table the runtime role can UPDATE/DELETE.
- Table-by-table grants that drift instead of a schema-level grant on `app.*`.
- Assuming Community has an audit log (it doesn't) or that MariaDB's audit plugin config matches MySQL Enterprise's (it doesn't).
