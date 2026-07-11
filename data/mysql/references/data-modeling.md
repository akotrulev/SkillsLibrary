# MySQL — Data modeling (schemas, keys, relationships, charset, JSON)

MySQL/InnoDB-specific modeling mechanics. Cross-engine *decisions* — id strategy, money as minor units, soft-delete policy, multi-tenancy pattern choice, embed-vs-reference — live in `data/_shared/schema-design`; apply those defaults here, don't re-derive them. Tenancy *enforcement* (MySQL has no RLS) → `references/security.md`.

## Normalization first

- **Normalize to 3NF by default.** Denormalize only with a measured query, its `EXPLAIN ANALYZE`, and evidence the join is the cost.
- Acceptable denormalizations, in preference order: a **covering (secondary) index** → a **summary table** maintained by a job or trigger (`references/caching.md`) → a maintained duplicate column via a **generated column** or app-side dual-write (document the invariant). InnoDB has no materialized views.

## The clustered primary key (InnoDB's defining trait)

InnoDB **always** stores the table's rows inside the primary key's B-tree — the PK *is* the table (the clustered index). Every **secondary index leaf stores the primary key value** as its row locator. Consequences that drive every key decision:

- A secondary-index lookup that needs non-indexed columns does a second lookup **into the PK** (the "double lookup") — cover hot queries so it doesn't (`references/indexing.md`).
- A **wide PK bloats every secondary index** (each stores a copy). Keep the PK narrow.
- A **random PK fragments the clustered index on insert** — every insert lands at a random point, causing page splits. This is *the* reason not to use a random UUID (v4) as the PK.
- If you don't declare a PK, InnoDB invents a hidden 6-byte one — always declare yours.

## Identifiers

- Default surrogate key: **`BIGINT UNSIGNED AUTO_INCREMENT`** — narrow, monotonic (perfect clustered PK), `UNSIGNED` doubles the range. `INT` runs out at ~4.2B (`UNSIGNED`); start at `BIGINT` unless provably tiny.
- Need client-generated / unguessable / cross-service ids → **`BINARY(16)` holding a UUIDv7** (time-ordered → sequential inserts → no clustered-PK fragmentation; half the bytes of `CHAR(36)`):
  - Generate UUIDv7 in the app (libraries exist for .NET/Java/Node) and store as `BINARY(16)`. MySQL 8's `UUID_TO_BIN(uuid, 1)` swaps the time bytes to make **v1** sortable; for v7 pass the raw bytes.
  - Never `CHAR(36)` (36 bytes vs 16, and text-collation comparisons), never random **v4** as the PK.
- Natural keys only for stable reference data (currency/country codes).

## Charset & collation

- `DEFAULT CHARSET = utf8mb4`, `COLLATE = utf8mb4_0900_ai_ci` (MySQL 8; accent- and case-insensitive). MariaDB: `utf8mb4_uca1400_ai_ci` (its own newer default) — flavors differ.
- **Never `utf8`** — it's the legacy 3-byte alias that silently drops emoji and 4-byte CJK.
- Binary-equality columns (tokens, hashes): `utf8mb4_bin` or a `BINARY`/`VARBINARY` type.
- Set the charset at the column/table level explicitly; a mismatched-collation join causes implicit conversion and kills index use (`references/indexing.md`).

## Timestamps

- **`DATETIME(6)`** for events — microsecond precision, no silent TZ conversion; store UTC, render in the app.
- `TIMESTAMP` has a **2038 cliff** and converts on the session TZ — use only where neither matters.
- `created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)`; `updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)`.

## Relationship patterns

| Relationship | Shape |
|---|---|
| 1:1 | Same table unless the extension is sparse/optional or has a different access profile → separate table, PK is also the FK |
| 1:N | FK on the many side, `NOT NULL` unless orphan is a real domain state |
| M:N | Junction table with a **composite PK** `(a_id, b_id)`; add the reverse index `(b_id, a_id)` for lookups from the other side |
| Self-referencing hierarchy | `parent_id` FK to own PK; recursive CTE (MySQL 8; **not** in MariaDB < 10.2 the same way) |
| Polymorphic | Avoid `(owner_type, owner_id)` — no FK integrity. One nullable FK per target + a `CHECK` that exactly one is set |

## Foreign keys

InnoDB **auto-creates an index on an FK column if one doesn't already exist** (unlike Postgres/SQL Server) — but rely on your own explicit, correctly-ordered index rather than the auto one, because the auto index is single-column and often not the composite your queries need.

```sql
customer_id BIGINT UNSIGNED NOT NULL,
CONSTRAINT fk_orders_customers FOREIGN KEY (customer_id) REFERENCES customers (id),
INDEX idx_orders_customer_id (customer_id)    -- explicit; serves your joins
```

### `ON DELETE` / `ON UPDATE` — always explicit

| Action | Semantics | Use when |
|---|---|---|
| `RESTRICT` / `NO ACTION` | Delete of parent fails if children exist (InnoDB checks immediately — both behave the same) | **Default for business data** |
| `CASCADE` | Children deleted with parent | True composition only (order → order_lines). Cascade chains still fire row-by-row in InnoDB — avoid deep chains |
| `SET NULL` | FK nulled on parent delete | Optional association where orphan is meaningful — column must be nullable |

- FKs are only enforced in **InnoDB** — a MyISAM table silently ignores them (another reason MyISAM is banned).
- No deferrable constraints. For circular refs, make one FK nullable and set it in a second statement, or `SET FOREIGN_KEY_CHECKS=0` inside the transaction (last resort, re-enable in the same transaction).

### Composite FK for tenant integrity

MySQL has no RLS, so engine-level tenant integrity leans harder on the schema. A composite FK ties a child to its parent's tenant (requires a `UNIQUE (tenant_id, id)` on the parent):

```sql
FOREIGN KEY (tenant_id, order_id) REFERENCES orders (tenant_id, id)
```

Pair this with the app-enforced tenancy discipline in `references/security.md`.

## Enum strategy

| | `ENUM('a','b',...)` | `CHECK (col IN (...))` | Lookup table + FK |
|---|---|---|---|
| Add a value | `ALTER TABLE` (rewrite risk on old versions; append at the end only) | One migration | `INSERT` |
| Payload (display name, sort) | No | No | Yes |
| **Verdict** | OK for **frozen** small sets — but reorder/remove is painful and the values are position-encoded | Default for evolving-but-simple sets (`CHECK` enforced since 8.0.16; **silently ignored on older MySQL** and needs care on MariaDB) | Values that grow or carry attributes |

MySQL's native `ENUM` is genuinely usable (unlike SQL Server, which has none) but its position-encoding and painful evolution make a lookup table the safer default for anything that might change.

## JSON

- MySQL 8 has a **native `JSON` type** (binary, validated) — use for genuinely sparse/variable payloads. MariaDB's `JSON` is a `LONGTEXT` alias with a `JSON_VALID` check — **not** the same; verify functions per flavor.
- Promote frequently-filtered fields to a **generated column** and index it (MySQL 8 also supports **multi-valued indexes** on JSON arrays for `MEMBER OF`/`JSON_CONTAINS`):

```sql
metadata   JSON NOT NULL,
region     VARCHAR(2) AS (JSON_UNQUOTE(JSON_EXTRACT(metadata,'$.region'))) STORED,
INDEX idx_region (region)
```

- Never use JSON as a substitute for a real column or a junction table.

## Sample DDL (the house shape)

```sql
CREATE TABLE orders (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id    BIGINT UNSIGNED NOT NULL,
    customer_id  BIGINT UNSIGNED NOT NULL,
    status       ENUM('pending','paid','cancelled','refunded') NOT NULL,
    total_minor  BIGINT          NOT NULL CHECK (total_minor >= 0),
    currency     CHAR(3)         NOT NULL,
    placed_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    paid_at      DATETIME(6)         NULL,
    metadata     JSON            NOT NULL,
    UNIQUE KEY uq_orders_tenant (tenant_id, id),           -- backs composite tenant FK
    INDEX idx_orders_tenant_customer (tenant_id, customer_id),
    INDEX idx_orders_placed_at (placed_at DESC),
    CONSTRAINT fk_orders_customers FOREIGN KEY (customer_id) REFERENCES customers (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;
```

Money as `BIGINT` minor units + `currency CHAR(3)`; monotonic `BIGINT` clustered PK; `DATETIME(6)` events; `utf8mb4`; `ROW_FORMAT=DYNAMIC` (the 8.0 default, explicit for clarity — needed for long VARCHAR/BLOB off-page storage).

## History / temporal

MySQL has **no built-in system-versioning** (MariaDB **does**: `WITH SYSTEM VERSIONING` — a real advantage of that flavor). On MySQL, when queryable point-in-time history is a requirement, build it explicitly:

- **Append-only history table + current table**: writes close the open row (`valid_to = now()`) and insert the new one in one transaction; a `UNIQUE`/app check prevents overlaps. Point-in-time query filters on the validity range.
- **Trigger-maintained shadow table**: a row trigger copies OLD into `<table>_history` on UPDATE/DELETE — less app intrusion, but the trigger must track schema changes.
- For a lighter *who-changed-what* log (not full queryable state) → `references/security.md` audit section.

Choose the cheapest that satisfies the requirement; don't event-source without measured need (`data/_shared/schema-design`).

## Anti-patterns

- Random UUID (v4) or `CHAR(36)` as the InnoDB primary key — fragments the clustered index, bloats every secondary index.
- No explicit PK (InnoDB invents a hidden one you can't use or index-plan around).
- `utf8` instead of `utf8mb4`; mismatched collations across joined columns.
- MyISAM (no transactions, no FK enforcement, table locks).
- `TIMESTAMP` for domain events (2038 + silent TZ conversion).
- `(owner_type, owner_id)` polymorphic pairs with no FK.
- Native `ENUM` for a value set that will be reordered or pruned.
- Frequently-queried fields buried in `JSON` with no generated-column promotion.
- Assuming MariaDB JSON == MySQL JSON (it isn't).
