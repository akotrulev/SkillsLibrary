# SQL Server — Indexing

Index selection, composition, and maintenance. Universal predicate triage / ESR rule / pagination → `data/_shared/slow-query-fixes`; reading plans to find the missing index → `references/performance.md`; the clustered-index *design* decision → `references/data-modeling.md`.

## The two-level model (SQL Server-specific)

Every table is either a **heap** or a **clustered index** (rows stored in key order — the clustered index *is* the table). Non-clustered indexes are separate B-trees whose leaf carries the **clustering key** (or the RID for a heap) as the row locator. Consequences that drive every decision here:

- A **key lookup** happens when a non-clustered index finds the row but must jump to the clustered index for columns it doesn't carry → fix with `INCLUDE`.
- A wide clustered key bloats **every** non-clustered index (each carries it). Keep the clustered key narrow (`references/data-modeling.md`).
- Heaps have no order and forward-pointer bloat on updates — non-clustered index lookups on a heap use a physical RID that a page split can invalidate. Cluster your tables.

## Index type selection

| Type | Serves | Use for |
|---|---|---|
| **Clustered** | The table's physical order; range scans on the key | The one you pick per table — narrow/monotonic/unique (`references/data-modeling.md`) |
| **Non-clustered** | `WHERE` / `JOIN` / `ORDER BY` columns | The workhorse — one per hot access path |
| **Covering (`INCLUDE`)** | Same, but carries extra columns at the leaf → index-only | Eliminate key lookups on hot read queries |
| **Filtered** | A predicate-scoped subset | Skewed data (`WHERE Status IN (...)`), "one active per X" unique |
| **Columnstore** | Analytical scans/aggregates | Fact tables ≥ ~1M rows — 10× compression + batch-mode execution |
| **Full-text / semantic** | `CONTAINS`/`FREETEXT` | Basic text search; serious search → OpenSearch/Elastic (`data/elasticsearch`) |

## Composite indexes — column ordering

Rule: **equality columns first, then the ORDER BY column, range predicates last** — and the leftmost prefix must match the query.

```sql
-- WHERE TenantId = @t AND Status = @s ORDER BY PlacedAt DESC
CREATE NONCLUSTERED INDEX IX_Orders_Tenant_Status_Placed
    ON dbo.Orders (TenantId, Status, PlacedAt DESC)
    INCLUDE (CustomerId, TotalMinor);   -- cover the SELECT list → no key lookup
```

- Equality first makes the seek a contiguous range; putting the range/sort column earlier fragments it.
- **Multi-tenant tables: `TenantId` leads every index** — it matches the RLS predicate (`references/security.md`) so the security filter is a seek, not a scan.
- Don't create `(A)` when `(A, B)` exists — the composite serves leading-column queries too.
- **Descending index columns** matter: an index on `(PlacedAt ASC)` can't cheaply serve `ORDER BY PlacedAt DESC` combined with another key's direction — declare the direction you query.

## Filtered & covering

```sql
-- Filtered: index only the rows queries touch — far smaller on skewed data
CREATE NONCLUSTERED INDEX IX_Orders_Open ON dbo.Orders (TenantId, PlacedAt DESC)
    WHERE Status IN ('Pending','Paid');

-- Filtered UNIQUE: "one active default per user" / soft-delete uniqueness
CREATE UNIQUE INDEX UX_Users_Email ON dbo.Users (Email) WHERE DeletedAt IS NULL;
```

- The query predicate must be provably contained by the filter for the index to be used — keep both simple, and note **parameterized queries sometimes won't use a filtered index** unless the filter is on a literal-comparable column; verify in the plan.
- `INCLUDE` columns add leaf size only (not key size) — include exactly what the hot query projects, no more.

## Columnstore

For analytics/reporting tables (aggregations over millions of rows):

- **Clustered columnstore** for a pure fact/append table — replaces the rowstore entirely, ~10× compression, batch-mode execution.
- **Non-clustered columnstore** on an OLTP table gives real-time analytics over live data without a second copy (HTAP) — but it's a write tax; measure.
- Not for OLTP point lookups / high-frequency singleton updates — that's what the rowstore clustered index is for.

## Missing-index DMVs (a starting point, never blind-applied)

```sql
SELECT TOP 25
    [Impact] = ROUND(s.avg_total_user_cost * s.avg_user_impact * (s.user_seeks + s.user_scans), 0),
    d.[statement] AS TableName, d.equality_columns, d.inequality_columns, d.included_columns
FROM sys.dm_db_missing_index_group_stats s
JOIN sys.dm_db_missing_index_groups   g ON s.group_handle = g.index_group_handle
JOIN sys.dm_db_missing_index_details  d ON g.index_handle = d.index_handle
ORDER BY [Impact] DESC;
```

The DMV suggests one index **per query shape** — it never dedupes or consolidates, and it over-`INCLUDE`s. Treat suggestions as raw input: consolidate overlapping ones, verify against Query Store's actual top queries (`references/performance.md`), and confirm the write cost is worth it before creating.

## Find unused & duplicate

```sql
-- Unused / rarely-used (check after a full workload cycle; stats reset on restart):
SELECT OBJECT_NAME(i.object_id) AS TableName, i.name,
       s.user_seeks, s.user_scans, s.user_lookups, s.user_updates
FROM sys.indexes i
LEFT JOIN sys.dm_db_index_usage_stats s
       ON s.object_id = i.object_id AND s.index_id = i.index_id AND s.database_id = DB_ID()
WHERE i.type_desc = 'NONCLUSTERED' AND OBJECTPROPERTY(i.object_id,'IsUserTable') = 1
ORDER BY s.user_updates DESC, s.user_seeks ASC;
```

A non-clustered index with high `user_updates` and ~zero seeks/scans is pure write tax — drop it (after confirming it isn't a rare-but-critical month-end path, and it isn't a unique/constraint-backing index).

## Maintenance — rebuild vs reorganize

- **Fragmentation < 5%**: do nothing.
- **5–30%**: `ALTER INDEX ... REORGANIZE` (online, incremental, no long lock).
- **> 30%**: `ALTER INDEX ... REBUILD WITH (ONLINE = ON, RESUMABLE = ON)` — `ONLINE` needs Enterprise / Azure SQL / Hyperscale; on Standard box it's offline (plan a window). `RESUMABLE` lets a long rebuild pause/resume.
- **Statistics** matter more than fragmentation for plan quality — keep auto-update on; `UPDATE STATISTICS ... WITH FULLSCAN` after bulk loads on skewed columns.
- Azure SQL Hyperscale and **Automatic tuning** (`FORCE_LAST_GOOD_PLAN`, `CREATE/DROP_INDEX`) can own much of this — let it, and review its recommendations.
- Never `DBCC SHRINK` as routine maintenance — it re-fragments every index it moves.

## Anti-patterns

- Unindexed FK columns (SQL Server doesn't auto-index them — `references/data-modeling.md`).
- Random-GUID clustered key fragmenting every non-clustered index.
- Blind-applying every missing-index DMV suggestion — overlapping, over-`INCLUDE`d, write-heavy indexes.
- Key lookups on a hot query that an `INCLUDE` would eliminate.
- One composite `(A)` redundant next to `(A, B)`.
- Columnstore on an OLTP point-lookup table; rowstore-only on a million-row analytics table.
- Heaps in production (missing clustered index) outside transient staging.
- `DBCC SHRINKDATABASE` in a maintenance job.
- Dropping "unused" indexes measured over a window that missed the monthly job, or dropping a constraint-backing index.
