---
name: data-schema-design
description: Use when choosing which database engine fits a workload, or designing a data model across any SQL or document engine — engine selection, entities, identifiers, soft delete, multi-tenancy, audit trails, money, enums — before engine-specific DDL. Triggers: "which database for this workload", "does Postgres suffice or do I need Mongo/Redis", "embed or reference", "multi-tenant model". Do NOT use for engine-specific syntax (`data/<db>`) or query optimization (`slow-query-fixes`).
---

# Data — Schema Design (cross-engine)

First-pass schema decisions that apply across SQL and document engines. Identifiers, timestamps, money, enums, multi-tenancy, soft delete, audit trails. Engine specifics live in the per-DB skills.

## When to use

- **Engine selection** — which database fits this workload (or whether Postgres already suffices) before committing to one
- New entity model before picking engine DDL
- Identifier choice (surrogate vs natural; autoincrement vs UUID vs ULID/UUIDv7)
- Timestamp conventions (`created_at`, `updated_at`, time zones, event time vs ingest time)
- Soft delete vs hard delete trade-offs
- Multi-tenant strategy (shared schema + tenant column, schema-per-tenant, db-per-tenant)
- Audit trails (event-sourced, change tables, application-managed)
- Money, decimal, bool conventions
- Embed vs reference for document stores

## When NOT to use

- Engine-specific DDL → `data/<db>`
- Migration mechanics → `data/_shared/migrations`
- Query tuning → `data/_shared/slow-query-fixes`
- Caching → `data/_shared/caching-patterns`

## Engine selection

Before any DDL, confirm the **engine fits the workload** — this is the cross-engine *decision* the scope fence puts here (the engine skill owns the mechanics once the engine is picked). The rule the `data-architect` agent enforces: **justify the engine against the workload shape; never silently default to Postgres — but know when Postgres genuinely suffices.** Adding a second store is a real operational tax (backups, failover, another on-call surface); earn it.

**Workload-shape → engine:**

| Workload shape | Reach for | Not when |
|---|---|---|
| Transactional system of record, relational integrity, ad-hoc queries | **PostgreSQL** (`data/postgresql`) — the default. Also absorbs many "I need another store" cases (below) | Access is a single known key at massive scale, or you need managed global multi-region writes |
| Same, but the shop is Microsoft / Azure-first | **SQL Server / Azure SQL** (`data/sqlserver`) | No Microsoft alignment — Postgres is cheaper and as capable |
| Same, but MySQL/MariaDB/Aurora is mandated or already in place | **MySQL** (`data/mysql`) — note: **no row-level security**, tenant isolation is app-enforced + mandatory leak test | Greenfield with a free engine choice — prefer Postgres for RLS + richer types |
| Flexible/evolving documents, embed-heavy aggregates, per-document schema variance | **MongoDB** (`data/mongodb`) | The data is relational and you're reaching for Mongo to "avoid migrations" — you'll rebuild joins in app code |
| Cache / rate limiter / lock / session / leaderboard / ephemeral queue — a **second-tier** store in front of a system of record | **Redis / Valkey** (`data/redis`) | You need it to be the durable source of truth |
| Single-digit-ms KV/wide-column at scale with **known access patterns**, AWS-native, serverless ops | **DynamoDB** (`data/dynamodb`) | Access patterns are unknown/ad-hoc, or you need rich server-side queries — model-first rigidity bites |
| Globally distributed, multi-region writes, tunable consistency, Azure-native | **Cosmos DB** (`data/cosmosdb`) | A single-region relational store would do — Cosmos's partition/consistency model + RU pricing is overhead you don't need |
| Full-text / relevance ranking, faceted search, aggregations over event data, hybrid + vector (kNN) search at dedicated scale | **Elasticsearch / OpenSearch** (`data/elasticsearch`) | It's the *only* store — ES is a search/index layer beside a system of record, not the record itself; and for logs use Loki, not ES |

**"Postgres suffices" — reach for a feature before a store.** Before adding Mongo / Redis / a dedicated search or vector DB to a Postgres-backed app, check whether Postgres already covers it:

| Tempting second store | Postgres feature that often removes the need |
|---|---|
| MongoDB for "flexible documents" | `jsonb` columns + GIN indexes — schemaless fields on a relational row |
| Elasticsearch for "search" | `tsvector` full-text search (+ `pg_trgm` fuzzy) for moderate corpora |
| Redis/SQS for "a job queue" | `SELECT … FOR UPDATE SKIP LOCKED` — a correct, transactional queue on a table |
| A dedicated vector DB for "embeddings / RAG" | **pgvector** — a `vector(n)` column next to the row it embeds, HNSW index (see `data/postgresql/references/indexing.md`) |

Cross the line to a second store when the Postgres feature stops paying off — corpus/relevance beyond `tsvector`, queue throughput beyond a single table, embedding volume/filtered-ANN recall beyond pgvector, or the data doesn't live in Postgres in the first place. Qualify each with the workload's **consistency / latency SLO / scale** needs, and record the decision in the agent's Phase 1 (engine + version + why-this-engine). If none of the eight catalog engines fits (local-first/embedded, OLAP/analytics at column-store scale, a dedicated vector DB), say so plainly — it's out of this catalog's current scope, not a silent Postgres default.

## Identifiers

| Choice | Pros | Cons | When |
|---|---|---|---|
| **`bigint` IDENTITY / AUTO_INCREMENT** | Compact, dense, sortable | Centralized generation; leaks insert order | Single-engine OLTP, default |
| **UUID v4** | Generated anywhere, no DB round-trip, unguessable | Random — fragments clustered indexes; 16 bytes | Distributed inserts where uniqueness must be guaranteed before write |
| **UUID v7 / ULID** | Time-prefixed, sortable, distributed-friendly | Slightly more complex; supported broadly but newer | **Modern default** for new distributed systems |
| **Natural key** | No surrogate, no join needed | Renames hurt; cross-domain references awkward | Reference tables (currencies, countries) only |

Rules:

- **One id per row, generated at insert.** Don't expose the autoincrement to clients — they can't predict it (good); it leaks ordering (sometimes bad).
- **UUID v7** is the right default for new distributed systems — sortable, indexable, distributable.
- **Surrogate by default**; natural keys only when the value is truly stable and not user-mutable.
- **Never re-use** an id after delete.

*The native generator is engine-specific — pick it in the engine skill:* PostgreSQL 18 `uuidv7()` (15–17: app-side / `gen_random_uuid()`), SQL Server `NEWSEQUENTIALID()`, MySQL app-side v7, Mongo `ObjectId` (already time-ordered). The **decision** (v7 vs `bigint`) is here; the DDL is `data/<db>`.

## Timestamps

| Field | Required? | Type | Default |
|---|---|---|---|
| `created_at` | Always | `timestamptz` / `datetime2(7)` / `DATETIME(6)` / BSON `Date` | DB `now()` / `SYSUTCDATETIME()` / `CURRENT_TIMESTAMP(6)` |
| `updated_at` | When the row is mutable | Same | Updated on every write (trigger / ORM / migration) |
| `deleted_at` | Only if soft-delete is the policy (see below) | Same nullable | `NULL` until soft-deleted |
| Event timestamps | Domain events (`placed_at`, `paid_at`, `cancelled_at`) | Same | App-supplied, not DB-defaulted |

- **Store UTC**, render in the app per user locale
- **Never** `timestamp without time zone` in Postgres or `datetime` in SQL Server
- **`updated_at`** is updated by a trigger or ORM in production code — never trust client-supplied
- Event timestamps (`placed_at`) are part of the domain; they're app-supplied and never auto-updated

## Money & decimals

- **Store money in minor units** (`bigint` cents / öre / smallest currency unit). Never `float`. Never `numeric(n,2)` if you can avoid it across services — minor-unit `bigint` is portable and arithmetic-safe everywhere.
- **Currency lives next to amount** — `total_minor BIGINT NOT NULL` + `currency CHAR(3) NOT NULL`. Never store a USD-equivalent without a currency.
- For high-precision decimals (chemistry, scientific), use `decimal(p,s)` / `NUMERIC(p,s)` with explicit precision — but money is always minor units.

## Booleans & enums

- Use the engine's `bool` / `boolean` / `bit` type, not `0/1` integers
- Enums as **strings constrained by a CHECK / validator / app-level enum**:

```sql
status TEXT NOT NULL CHECK (status IN ('pending','paid','cancelled','refunded'))
```

- Don't use the engine's native `ENUM` (Postgres `CREATE TYPE ... AS ENUM`, MySQL `ENUM(...)`) unless you have a clear evolution plan — `ALTER TYPE ... ADD VALUE` is restrictive on Postgres; renames are awkward on MySQL.
- For values that grow (categories, product types), use a lookup table with a FK.

## Soft delete vs hard delete

Soft delete (a `deleted_at` column) is **default off** in this library. It pays an ongoing tax:

- Every query needs `WHERE deleted_at IS NULL`
- Unique constraints break (you can't have a unique email when soft-deleted ghosts compete with new users)
- Foreign keys break or need cascading "soft" — which doesn't exist
- Backups + analytics see deleted data unless filtered

When to **actually use** soft delete:

| Reason | Verdict |
|---|---|
| Audit / compliance / legal retention | **Move to an archive table** (or audit log) instead. Soft delete in the live table makes day-to-day queries worse. |
| "User might want to undo" | **30-day grace period** in a separate column; hard-delete after. Not a permanent soft-delete. |
| "We never delete anything" | A philosophy, not a design — pick which data is keep-forever and store it explicitly |

Default: **hard delete + audit table** (or event store) for what needs retention. Use soft delete only when the audit trail is the table itself and the workload genuinely demands queryability of the soft-deleted rows.

## Multi-tenancy

Three patterns, in increasing isolation cost:

| Pattern | Isolation | Cost | When |
|---|---|---|---|
| **Shared schema + tenant column** | Logical (enforced by app + Row-Level Security where supported) | Cheapest | Default; B2C; multi-tenant SaaS at any scale |
| **Schema per tenant** | Schema-level (different `Orders` table per tenant) | Medium | Large enterprise contracts requiring "their own DB inside our DB" |
| **Database per tenant** | Physical | Highest | Enterprise B2B with regulatory boundary; small-N tenants |

**Always** carry `tenant_id` (or `org_id`) on every multi-tenant table — even when you're using physical isolation, it future-proofs queries.

For shared schema + tenant column:

- **Index every query** with `tenant_id` as the first column of the compound index
- **Row-Level Security** (Postgres / SQL Server) — defense in depth so an app bug can't leak across tenants
- **Every query** in app code filters by tenant_id explicitly; never rely on RLS alone
- **Auth context** carries `tenant_id` from the JWT claim (see `auth/_shared/auth0-concepts`) — the app never trusts a tenant id from a request body

*The enforcement mechanism is engine-specific — the pattern choice is here, the isolation DDL is in the engine's `security` reference:* Postgres RLS `CREATE POLICY` + `current_setting` (`data/postgresql/references/security.md`), SQL Server security policies + `SESSION_CONTEXT` (`data/sqlserver/references/security.md`), **MySQL and MongoDB have no row-level security — isolation is app-enforced** (`data/mysql` / `data/mongodb/references/security.md`, mandatory cross-tenant leak test), DynamoDB fine-grained `dynamodb:LeadingKeys`, Cosmos partition-scoped, Elasticsearch DLS. Whichever the engine, the cross-tenant leak test is a `qa-security` handoff.

## Audit trails

Three patterns:

| Pattern | When |
|---|---|
| **Event sourcing** (events are the source of truth; state is derived) | Complex domain with audit-as-business-requirement |
| **Change Data Capture / change tables** | When the DB engine supports it and analytics needs it |
| **Application-managed audit table** | Most common; a separate `audit_events` table written by the app on every mutation |

The cheapest pattern that satisfies the requirement wins. **Don't event-source unless you've measured the need.**

Outbox pattern when audit must be reliable across a transaction + an external sink (Kafka, EventBridge):

```
BEGIN
  UPDATE orders SET status = 'paid' WHERE id = ?;
  INSERT INTO outbox (event_type, payload) VALUES ('OrderPaid', '...');
COMMIT;
-- async: worker reads outbox → publishes → marks consumed
```

## Embed vs reference (document stores)

Document stores let you embed children inline. Decision table:

| Use embedding | Use reference |
|---|---|
| Child data is **always** loaded with the parent | Child data is queried independently |
| 1-to-few (bounded, ~< 100) | 1-to-many (unbounded) |
| Lifecycle matches parent | Independent lifecycle |
| Updates are mostly the whole document | Children update frequently without parent |

The 16 MB document limit (Mongo) / 2 MB item limit (Cosmos) / 400 KB item limit (DynamoDB) is a hard ceiling — design with a working limit far below.

This table is the **decision**. The modeling *mechanics* that flow from it — extended-reference / computed / bucket patterns, `$jsonSchema` validators, the anti-pattern of unbounded embedded arrays — live in the engine skill: `data/mongodb/references/data-modeling.md`, `data/cosmosdb/SKILL.md` (hierarchical partition keys), `data/dynamodb/SKILL.md` (single-table design). Decide embed-vs-reference here, then hand off.

## Naming conventions

- Table / collection: **plural**, `snake_case` for SQL, `camelCase` for Mongo/Dynamo/Cosmos — pick one per project and stay consistent
- Columns / attributes: `snake_case` (SQL) / `camelCase` (document)
- Boolean columns: positive form (`is_active`, not `is_inactive`)
- Timestamp suffix: `_at` for instants (`placed_at`), `_on` for dates (`due_on`), `_until` for ranges
- Foreign keys: `<referent>_id` (`customer_id`)
- Index names: `idx_<table>_<columns>`; uniques: `uq_<table>_<columns>`; constraints: `ck_<table>_<rule>`

## Rules

- One id per row, generated at insert; **UUID v7 default for distributed**, `bigint` IDENTITY for single-engine OLTP
- All timestamps UTC with TZ-aware types
- **Money as `bigint` minor units + currency `CHAR(3)`**
- Booleans as boolean, not int
- Enums as strings constrained by check/validator, lookup table when values grow
- Default to **hard delete** + audit table; soft delete only with explicit justification
- Multi-tenant default: shared schema + tenant column + RLS; always carry `tenant_id`
- `created_at` and `updated_at` populated by the engine / ORM, never by client input
- Naming consistent across the project; codified in a style guide
- Every table has a PK; every FK has an explicit `ON DELETE` action

## What NOT to do

- No floats for money
- No `timestamp without time zone` (Postgres) / `datetime` (SQL Server) / `TIMESTAMP` (MySQL legacy) for events
- No native engine ENUM unless you're prepared to live with the constraints
- No `is_active` AND `is_deleted` AND `is_archived` — pick one state model
- No "soft delete on every table" as a default
- No multi-tenant tables without `tenant_id` (or row-level security tied to it)
- No client-supplied `updated_at` accepted in writes
- No FK without an explicit `ON DELETE` action
- No `UUID v4` as a clustered PK on a write-heavy table (fragmentation) — `UUID v7` / `NEWSEQUENTIALID()` instead
- No mixing naming conventions within one project
- No "this column might be useful later" placeholders — add columns when you need them

## Generation steps

1. Identify entities and the relationships among them.
2. Pick id strategy (UUIDv7 default for new, `bigint` for tightly coupled single-engine OLTP).
3. Decide timestamps per entity (`created_at`, `updated_at`, event timestamps).
4. Pick money / enum / bool conventions; never invent per-table.
5. Pick multi-tenancy pattern; carry `tenant_id` on every multi-tenant table.
6. Decide audit strategy; design the outbox table if external sinks are involved.
7. For document stores, decide embed-vs-reference per relationship.
8. Hand off to `data/<db>` for the actual DDL.

## Handoffs

- Engine DDL → `data/<db>`
- Migration shape (expand-contract, online-safe) → `data/_shared/migrations`
- Query patterns / indexing → `data/_shared/slow-query-fixes`
- Caching layer in front of the schema → `data/_shared/caching-patterns`
- Tenant identity in tokens → `auth/_shared/auth0-concepts`
