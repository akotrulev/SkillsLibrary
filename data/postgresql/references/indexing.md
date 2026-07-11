# PostgreSQL — Indexing

Index selection, composition, and maintenance. Universal predicate triage / ESR rule / pagination → `data/_shared/query-optimization`; reading plans to find the missing index → `references/performance.md`.

## Index type selection

| Type | Operators it serves | Use for | Don't use for |
|---|---|---|---|
| **B-tree** (default) | `= < <= > >= BETWEEN IN`, `ORDER BY`, `LIKE 'abc%'` | Everything scalar — PKs, FKs, filters, sorts | Containment, similarity, huge append-only ranges |
| **GIN** | `@> ? ?& ?\|` (jsonb), `&&` (arrays), `@@` (full-text) | `jsonb` containment, array membership, FTS | Scalar equality (B-tree is smaller/faster); high-churn columns (GIN update cost; mitigate with `fastupdate`) |
| **GiST** | `&&` (ranges/geometry), nearest-neighbor `<->` | `tstzrange` overlap (EXCLUDE constraints), PostGIS | Anything B-tree can do |
| **BRIN** | Range comparisons on physically-correlated columns | `created_at` on huge append-only tables — MBs instead of GBs | Tables with random update order (correlation dies, index useless) |
| **Hash** | `=` only | Rarely — B-tree ties it in practice | Anything else |

`pg_trgm` + GIN for `LIKE '%abc%'` / fuzzy search; expression index on `lower(email)` for case-insensitive equality (preferred over `citext` unless a constraint needs it).

## Composite indexes — column ordering

Rule: **equality columns first, then the sort column, range predicates last** — and the leftmost prefix must match the query.

```sql
-- WHERE tenant_id = $1 AND status = $2 ORDER BY placed_at DESC
CREATE INDEX idx_orders_tenant_status_placed
    ON orders (tenant_id, status, placed_at DESC);
```

- Equality first makes the index a contiguous slice; putting the range/sort column earlier fragments it.
- An index on `(a, b)` serves `WHERE a = ...` but historically not `WHERE b = ...` alone. **PG 18 skip scan** relaxes this — a composite can serve a non-leading-column filter when the leading column has few distinct values — but it's a rescue, not a design strategy: order columns for your real queries on all supported versions.
- Multi-tenant tables: `tenant_id` leads every index (matches the RLS qual — `references/security.md`).
- Don't create `(a)` when `(a, b)` exists — the composite serves leading-column queries too.

## Partial, covering, expression

```sql
-- Partial: index only the rows queries touch — small + fast on skewed data
CREATE INDEX idx_orders_open ON orders (tenant_id, placed_at DESC)
    WHERE status IN ('pending','paid');

-- Covering: INCLUDE payload columns → index-only scan, no heap visit
CREATE INDEX idx_orders_list ON orders (tenant_id, placed_at DESC)
    INCLUDE (status, total_minor);

-- Expression: index the transformed value the query actually filters on
CREATE INDEX idx_users_email_lower ON users (lower(email));
```

- Partial index predicates must match the query's predicate **verbatim enough** for the planner to prove containment — keep both simple.
- The classic partial-unique: `CREATE UNIQUE INDEX ... ON users (email) WHERE deleted_at IS NULL;`
- Index-only scans need the visibility map to be fresh — a table that never gets vacuumed never delivers them (`references/performance.md`).
- `INCLUDE` columns add size; include only what the hot query projects.

## Write-side costs

- Every index is a tax on every INSERT/UPDATE/DELETE. Insert-heavy tables: minimum viable index set; bulk loads: drop indexes → load → recreate.
- **HOT updates**: an UPDATE touching only non-indexed columns can rewrite in-page without touching any index — but only if the page has slack. For update-heavy tables: don't index the churning columns, and set `ALTER TABLE ... SET (fillfactor = 90);` to leave that slack.
- Split hot (frequently updated) and cold (static) columns into separate tables when a wide row churns constantly (`references/data-modeling.md` 1:1 pattern).

## Operational discipline

### `CREATE INDEX CONCURRENTLY`

Mandatory on hot production tables (plain `CREATE INDEX` blocks writes for the whole build). Cannot run inside a transaction — migration tools need the escape hatch (Flyway `-- $$$ flyway:no-transaction $$$`, EF `suppressTransaction: true`). **A failed concurrent build leaves an `INVALID` index** — it's dead weight that still taxes writes:

```sql
SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;  -- detect
DROP INDEX CONCURRENTLY idx_bad; -- then retry the build
```

### Find missing, unused, duplicate

```sql
-- Unused (check idx_scan on a system that's been up through a full workload cycle):
SELECT indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC;

-- Missing: high seq_scan + high seq_tup_read on big tables
SELECT relname, seq_scan, seq_tup_read, idx_scan
FROM pg_stat_user_tables ORDER BY seq_tup_read DESC LIMIT 20;
```

Plus `pg_stat_statements` ordered by `total_exec_time` for the queries that deserve one (`references/performance.md`). Before dropping a "unused" index: confirm it isn't a constraint backing index or serving a rare-but-critical job (month-end reports), and remember stats reset on major upgrades.

### Bloat

Heavily-updated indexes bloat (dead entries). Rebuild online: `REINDEX INDEX CONCURRENTLY idx_name;` (PG 12+). Schedule for chronically bloated ones rather than reacting.

## Anti-patterns

- Unindexed FK columns (`references/data-modeling.md` — Postgres doesn't auto-index them).
- Index-everything-in-the-WHERE-clause-once-each: five single-column indexes where one composite serves the real query.
- GIN on a whole `jsonb` column when queries only touch one path — expression/generated-column B-tree instead.
- `CREATE INDEX` without `CONCURRENTLY` on a hot table.
- INVALID indexes left in place after a failed concurrent build.
- Redundant `(a)` next to `(a, b)`.
- Indexing the updated-every-write column on an update-heavy table (kills HOT).
- BRIN on tables without physical correlation.
- Dropping "unused" indexes measured over a window that missed the monthly job.
