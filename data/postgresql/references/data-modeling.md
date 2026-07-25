# PostgreSQL — Data modeling (schemas, relationships, foreign keys, constraints)

Postgres-specific modeling mechanics. Cross-engine *decisions* — id strategy, money as minor units, soft-delete policy, multi-tenancy pattern choice, embed-vs-reference — live in `data/_shared/schema-design`; apply those defaults here, don't re-derive them. Tenant isolation enforcement (RLS) → `references/security.md`.

## Normalization first

- **Normalize to 3NF by default.** Every non-key column depends on the key, the whole key, and nothing but the key. This eliminates update anomalies and duplicate truth.
- **Denormalize only with a measurement**: a real query, its `EXPLAIN (ANALYZE, BUFFERS)`, and evidence the join is the cost. Premature denormalization is a standing maintenance tax (every write path must now update N copies).
- Acceptable denormalizations, in preference order: a **covering index** (often removes the join entirely, no schema change) → a **materialized view** (`references/caching.md`) → a maintained duplicate column with a trigger or app-side dual-write (last resort, document the invariant).

## Identifiers

- Default surrogate key: `bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY`. Never `serial`/`bigserial`.
- Need client-side generation, unguessability, or cross-service ids → UUID:
  - **PG 18**: `uuid DEFAULT uuidv7()` — timestamp-ordered, so B-tree locality is as good as bigint. This removes the classic "random UUIDs fragment the index" objection.
  - **PG 15–17**: `gen_random_uuid()` is v4 (random) — fine for moderate write rates; for write-heavy tables generate **UUIDv7 in the app** (libraries exist for .NET/Java/Node) and pass it in.
- Natural keys only for stable reference data (currency codes, country codes).

## Relationship patterns

| Relationship | Shape |
|---|---|
| 1:1 | Same table unless the extension is sparse/optional or has different access/security profile → separate table, PK is also the FK: `profile_id bigint PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE` |
| 1:N | FK on the many side, `NOT NULL` unless orphan is a real domain state |
| M:N | Junction table with a **composite PK** `(a_id, b_id)` + payload columns; add the reverse-order index `(b_id, a_id)` for lookups from the other side |
| Self-referencing hierarchy | `parent_id` FK to own PK (`ON DELETE CASCADE` or `RESTRICT` — decide); query with `WITH RECURSIVE`; consider `ltree` for deep path-heavy trees |
| Polymorphic ("this row belongs to an order OR an invoice") | Avoid a `(owner_type, owner_id)` pair — no FK integrity. Prefer one nullable FK per target + a `CHECK` that exactly one is set: `CHECK (num_nonnulls(order_id, invoice_id) = 1)` |

## Foreign keys — the full treatment

**Postgres does NOT automatically index FK columns.** It indexes the *referenced* PK, not the referencing column. Every FK column gets an explicit index — it serves your joins and, critically, the referenced table's DELETE/UPDATE (which must scan the referencing table without one).

```sql
customer_id bigint NOT NULL REFERENCES customers(id) ON DELETE RESTRICT
-- and always:
CREATE INDEX idx_orders_customer_id ON orders (customer_id);
```

### `ON DELETE` decision matrix — always explicit, never defaulted

| Action | Semantics | Use when |
|---|---|---|
| `RESTRICT` | Delete of parent fails immediately if children exist | **Default for business data** — forces the app to decide what happens to children |
| `NO ACTION` (the implicit default) | Same as RESTRICT but check is deferrable to commit | Only when you need the deferred check; otherwise write `RESTRICT` so intent is visible |
| `CASCADE` | Children deleted with parent | True composition only (order → order_lines, user → user_preferences). Never across aggregate boundaries — a cascading delete through 5 tables is an incident |
| `SET NULL` | FK nulled on parent delete | Optional association where orphan is meaningful (order.assigned_agent_id) — column must be nullable |
| `SET DEFAULT` | FK reset to a default row | Rare; "reassign to the Unassigned bucket" patterns |

### Deferrable constraints

For circular references or reorder-within-transaction patterns (swap two rows' unique `position`):

```sql
CONSTRAINT fk_a_b FOREIGN KEY (b_id) REFERENCES b(id) DEFERRABLE INITIALLY DEFERRED
```

Checks run at `COMMIT` instead of per-statement. Use sparingly — deferred checks hold their violation until commit, which surfaces errors far from their cause. `UNIQUE` constraints can be deferrable too (the position-swap case).

### Composite FKs

When a child must belong to the same tenant/parent-scope as its parent, a composite FK enforces it at the engine:

```sql
FOREIGN KEY (tenant_id, order_id) REFERENCES orders (tenant_id, id)
```

Requires a `UNIQUE (tenant_id, id)` on the parent. This is the cheapest cross-table tenant-integrity guarantee and complements RLS (`references/security.md`).

### Adding an FK to a large live table

`ADD CONSTRAINT ... NOT VALID` (takes only a brief lock, stops new violations) → clean existing violations → `VALIDATE CONSTRAINT` (weak lock, scans without blocking writes).

## Enum strategy — CHECK vs native ENUM vs lookup table

| | `CHECK (col IN (...))` | `CREATE TYPE ... AS ENUM` | Lookup table + FK |
|---|---|---|---|
| Add a value | One migration, trivial | `ALTER TYPE ... ADD VALUE` (can't run in a transaction pre-PG 12 caveats; can't remove/reorder ever) | `INSERT` |
| Remove/rename | Migration | **Not supported** (rename yes, remove no) | `UPDATE`/`DELETE` with FK discipline |
| Payload (display name, sort order) | No | No | Yes |
| **Verdict** | **Default** for small closed sets | Avoid unless the set is truly frozen | Values that grow or carry attributes |

## `jsonb` boundary rules

`jsonb` is for **sparse, variable-shape, schema-last** data — vendor payloads, user-defined attributes, webhook bodies.

- Anything you filter/join/aggregate on frequently → promote to a real column (PG 18: a **virtual generated column** over the jsonb path is a zero-storage promotion; 15–17: `GENERATED ... STORED`).
- Validate shape at the boundary if it matters: `CHECK (jsonb_typeof(metadata->'items') = 'array')`.
- Index with GIN only for the operators you actually use (`@>`, `?`) — `references/indexing.md`.
- Never `jsonb` as a substitute for a junction table or a column you'd otherwise design.

## Embeddings / vector columns (pgvector)

An embedding lives **next to the row it embeds** — a `vector(n)` column on the same table as the source text, not a bolted-on parallel store:

- **Pin the dimension to the model** — `vector(1536)` for `text-embedding-3-small`, `vector(3072)` for `-large`, etc. It's part of the column type; changing models means a new column, not an `ALTER`.
- **Normalize the vector out to its own table** only when the embedding lifecycle diverges from the row (multiple embeddings per row for different models/chunks, or the base row churns while the embedding is stable) — otherwise keep it inline, `NULL` until embedded.
- **Re-embedding is a backfill**, not an in-place migration: add the new column, backfill in batches (a new model, or a re-chunk), then cut over reads and drop the old column — the batched-backfill + expand-contract discipline in `data/_shared/migrations`. A synchronous "re-embed every row in one migration" locks the table and hammers the embedding API.
- Index + ANN mechanics (HNSW/IVFFlat, operator class, `ef_search`, filtered-ANN recall) → `references/indexing.md`.

## Constraint catalog

- `CHECK` for value rules — cheap, always on: `CHECK (total_minor >= 0)`, `CHECK (paid_at IS NULL OR paid_at >= placed_at)`.
- `UNIQUE NULLS NOT DISTINCT` (PG 15+) when NULLs should collide (one active default address per user with `deleted_at IS NULL` semantics). Pre-15: partial unique index.
- **Partial unique index** for "unique among the live ones": `CREATE UNIQUE INDEX ... ON users (email) WHERE deleted_at IS NULL;`
- `EXCLUDE` for "no two rows overlap" — the booking/reservation constraint SQL can't express with UNIQUE:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE bookings ADD CONSTRAINT no_overlap
  EXCLUDE USING gist (room_id WITH =, during WITH &&);   -- during tstzrange
```

- Name constraints explicitly (`ck_orders_total_nonneg`) — auto-generated names make future migrations guesswork.

## History / temporal tables (full queryable edit history)

When "what did this row look like on date X" is a **modeling requirement** (pricing, contracts, configuration with effective dates) — distinct from a lighter audit *log* of who changed what (→ `references/security.md`, which has the decision matrix between the two):

**Pattern A — append-only history table + current table** (default):

```sql
CREATE TABLE price_history (
    id          bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id  bigint      NOT NULL REFERENCES products(id),
    price_minor bigint      NOT NULL,
    valid_from  timestamptz NOT NULL,
    valid_to    timestamptz,            -- NULL = current
    CONSTRAINT no_overlap EXCLUDE USING gist (
        product_id WITH =, tstzrange(valid_from, valid_to) WITH &&)
);
```

Writes close the open row (`valid_to = now()`) and insert the new one, in one transaction. The EXCLUDE constraint makes overlapping validity a hard error. Point-in-time query: `WHERE product_id = $1 AND tstzrange(valid_from, valid_to) @> $2::timestamptz`.

**Pattern B — trigger-maintained shadow table**: current table stays clean; a row-level trigger copies OLD into `<table>_history` on UPDATE/DELETE. Less app-code intrusion, but history writes are invisible to the app and the trigger must be kept in sync with schema changes. (PG 18's `RETURNING OLD` helps app-side capture without a trigger.)

Choose the cheapest that satisfies the requirement; don't event-source unless measured need (`data/_shared/schema-design`).

## Sample DDL (the house shape)

```sql
CREATE TABLE orders (
    id           bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id    bigint      NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    customer_id  bigint      NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    status       text        NOT NULL CHECK (status IN ('pending','paid','cancelled','refunded')),
    total_minor  bigint      NOT NULL CHECK (total_minor >= 0),
    currency     char(3)     NOT NULL,
    placed_at    timestamptz NOT NULL DEFAULT now(),
    paid_at      timestamptz CHECK (paid_at IS NULL OR paid_at >= placed_at),
    metadata     jsonb       NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX idx_orders_tenant_customer ON orders (tenant_id, customer_id);
CREATE INDEX idx_orders_placed_at       ON orders (placed_at DESC);
```

Money as `bigint` minor units + `currency char(3)`; `timestamptz` everywhere; every FK indexed; every FK's `ON DELETE` explicit.

## Anti-patterns

- FK column without an index (locks + seq-scans the child table on parent delete).
- Implicit `ON DELETE NO ACTION` because nobody decided.
- `CASCADE` chains crossing aggregate boundaries.
- `(owner_type, owner_id)` polymorphic pairs with no FK.
- Native ENUM for a value set that will ever change.
- Structured, frequently-queried fields buried in `jsonb`.
- EAV (entity-attribute-value) tables where `jsonb` + promoted columns would do.
- Unnamed constraints.
- One giant `public` schema for app + ETL + reporting objects with no ownership story (role/schema separation → `references/security.md`).
