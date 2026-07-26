# MySQL — Indexing (InnoDB)

Index selection, composition, and maintenance for InnoDB. Universal predicate triage / ESR rule / pagination → `data/_shared/slow-query-fixes`; reading plans to find the missing index → `references/performance.md`; the clustered-PK *design* decision → `references/data-modeling.md`.

## The clustered-PK model (drives everything)

InnoDB stores rows in the **primary key** B-tree (the clustered index), and **every secondary index leaf stores the PK value** as its locator. So:

- A secondary-index read that needs columns the index doesn't carry does a **second lookup into the PK** ("bookmark lookup"). Cover hot queries to avoid it.
- Because the PK is appended to every secondary index, a **fat PK inflates all of them** — keep the PK narrow (`BIGINT`, not `CHAR(36)`).
- The PK order determines physical insert locality — a monotonic PK inserts at the end (good), a random one splits pages everywhere (bad).

## Index type selection

| Type | Serves | Use for |
|---|---|---|
| **B-tree** (the only general index; "BTREE") | `= < <= > >= BETWEEN IN`, `ORDER BY`, `LIKE 'abc%'` | Everything scalar — PK, FKs, filters, sorts |
| **Composite** | Multi-column filters/sorts (leftmost prefix) | The workhorse — order by ESR |
| **Prefix** (`col(20)`) | Long string columns where the leading chars are selective | Index a `VARCHAR(1000)` cheaply — but no covering/`ORDER BY` benefit |
| **Functional** (8.0.13+) | Expression predicates | `WHERE LOWER(email) = ?` → index `((LOWER(email)))` (MariaDB: generated column + index) |
| **Multi-valued** (8.0) | JSON arrays | `WHERE ? MEMBER OF (metadata->'$.tags')` |
| **FULLTEXT** | `MATCH ... AGAINST` | Basic text search; serious search → Elastic/OpenSearch (`data/elasticsearch`) |
| **Spatial (R-tree)** | `ST_*` geometry | GIS columns |

There is **no `INCLUDE`/covering-payload syntax** — you make an index covering by putting the projected columns *into the key* (they're then also sorted, which is fine or wasteful depending). And **no partial/filtered index** (Postgres/SQL Server have them) — emulate with a generated column that's NULL for excluded rows, indexed (NULLs aren't stored compactly, so measure).

## Composite indexes — column ordering

Rule: **equality columns first, then the ORDER BY column, range predicates last** — and the leftmost prefix must match the query.

```sql
-- WHERE tenant_id = ? AND status = ? ORDER BY placed_at DESC
CREATE INDEX idx_orders_tenant_status_placed
    ON orders (tenant_id, status, placed_at DESC);
```

- Equality first makes the scan a contiguous range; a range/sort column earlier fragments it.
- A range predicate (`>`, `<`, `BETWEEN`, `LIKE 'x%'`) **stops the index from being used for columns after it** — put ranges last.
- **Multi-tenant tables: `tenant_id` leads every index** — app-enforced tenancy relies on that filter being a seek (`references/security.md`).
- **Descending indexes are real since MySQL 8** (`placed_at DESC`) — before 8.0 the keyword was accepted but ignored; MariaDB support differs. Declare the direction you sort.
- Don't create `(a)` when `(a, b)` exists — the composite serves leading-column queries too.

## Covering & making an index cover

A **covering index** is served entirely from the secondary index (no bookmark lookup into the PK) — the plan shows `Using index`. Since there's no `INCLUDE`, put the projected columns in the key:

```sql
-- Covers: SELECT status, total_minor FROM orders WHERE tenant_id=? ORDER BY placed_at DESC
CREATE INDEX idx_orders_cover ON orders (tenant_id, placed_at DESC, status, total_minor);
```

Weigh it: the extra key columns widen the index (more I/O per read, more write cost) — only cover genuinely hot queries.

## Invisible indexes — test before you drop (8.0)

Before dropping a suspected-unused index, make it **invisible** (the optimizer ignores it but it's still maintained) — if nothing regresses, drop it; if something breaks, flip it back instantly:

```sql
ALTER TABLE orders ALTER INDEX idx_maybe_unused INVISIBLE;   -- observe, then DROP or VISIBLE
```

Far safer than drop-and-hope on a large table where recreating the index is expensive.

## Prefix indexes

For long strings where you can't/shouldn't index the whole column:

```sql
CREATE INDEX idx_users_email_prefix ON users (email(20));
```

- Choose the prefix length by selectivity: `SELECT COUNT(DISTINCT LEFT(email,20)) / COUNT(*) FROM users;` — aim close to the full-column distinctness ratio.
- Prefix indexes **can't** be covering and **can't** satisfy `ORDER BY` — they only narrow the initial scan.

## Write-side costs

- Every secondary index taxes every INSERT/UPDATE/DELETE. Insert-heavy tables: minimum viable index set; bulk loads: drop non-essential indexes → load → recreate.
- **`innodb_change_buffering`** batches secondary-index maintenance for non-unique indexes — helps write-heavy workloads; it doesn't apply to unique indexes (they need an immediate read to check uniqueness).
- Random-PK inserts cause page splits across the clustered index — the strongest argument for a monotonic PK (`references/data-modeling.md`).

## Finding problem indexes

```sql
-- Unused indexes (Performance Schema / sys):
SELECT * FROM sys.schema_unused_indexes;

-- Redundant / duplicate indexes:
SELECT * FROM sys.schema_redundant_indexes;

-- Statement digests that scan the most rows (candidates for a missing index):
SELECT digest_text, count_star, sum_rows_examined, sum_rows_sent
FROM performance_schema.events_statements_summary_by_digest
ORDER BY sum_rows_examined DESC LIMIT 20;
```

`sys.schema_redundant_indexes` directly flags an `(a)` made redundant by `(a, b)` — drop the redundant one (via INVISIBLE first). Before dropping a "unused" one, confirm it isn't serving a rare-but-critical monthly job and that stats have covered a full workload cycle.

## Maintenance

- InnoDB has no manual rebuild ritual like SQL Server; index/table bloat from churn is reclaimed by `OPTIMIZE TABLE` (which for InnoDB does an online `ALTER ... FORCE` rebuild) — run it rarely and off-peak, not on a cron.
- Statistics: InnoDB samples index pages automatically (`innodb_stats_persistent`); after a huge data change you *may* `ANALYZE TABLE`, but not routinely.

## Anti-patterns

- Random UUID (v4) / `CHAR(36)` PK — page splits across the clustered index, fat locator in every secondary index.
- Putting a range column before an equality column in a composite (the range stops index use for later columns).
- Expecting a partial/filtered index (MySQL has none) or `INCLUDE` syntax (put columns in the key instead).
- Dropping an index outright on a big table instead of testing with `INVISIBLE` first.
- Prefix index where the query needs covering or `ORDER BY` (a prefix index can't do either).
- One `(a)` index redundant next to `(a, b)` (check `sys.schema_redundant_indexes`).
- FULLTEXT as the "real search" solution at scale.
- `OPTIMIZE TABLE` / `ANALYZE TABLE` on a cron — let InnoDB manage stats; rebuild only when measured bloat warrants.
