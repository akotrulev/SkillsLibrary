# SQL Server — Caching (what the engine offers, and the seam to the external cache)

Scope fence: the external-cache **pattern catalog** — cache-aside, stampede protection, TTL/key policy, invalidation — lives in `data/_shared/caching-patterns`, and Redis mechanics in `data/redis`. This file covers what SQL Server itself offers and where it meets that layer.

## Decide in this order

1. **Is the query just slow?** Fix the query/index first (`references/{indexing,performance}.md`). A cache in front of a missing index is debt with a TTL.
2. **Expensive aggregate over slowly-changing data?** → indexed view (in-engine, always-consistent, maintained by the engine).
3. **Hot-path reads at volume / cross-service reuse / sub-ms latency?** → external cache-aside (`data/_shared/caching-patterns` + `data/redis`).

## Indexed views — the engine-native materialized aggregate

Unlike Postgres materialized views (manual `REFRESH`, staleness), a SQL Server **indexed view** is maintained **synchronously by the engine** — always consistent, no refresh job — at the cost of write amplification on the base tables.

```sql
CREATE VIEW dbo.vw_DailyRevenue WITH SCHEMABINDING AS
    SELECT TenantId,
           CAST(PlacedAt AS date) AS Day,
           SUM(TotalMinor)        AS RevenueMinor,
           COUNT_BIG(*)           AS Orders     -- COUNT_BIG(*) is mandatory
    FROM dbo.Orders
    WHERE Status = 'Paid'
    GROUP BY TenantId, CAST(PlacedAt AS date);

CREATE UNIQUE CLUSTERED INDEX IX_vw_DailyRevenue
    ON dbo.vw_DailyRevenue (TenantId, Day);   -- materializes it
```

Constraints (real and strict):

- `WITH SCHEMABINDING`, two-part object names, and a **unique clustered index** are required to materialize.
- `COUNT_BIG(*)` must be present in any aggregate view; no `COUNT(*)`, no outer joins, no subqueries, no `DISTINCT`, deterministic expressions only.
- **Every base-table write updates the indexed view synchronously** — great for read-heavy/rarely-written aggregates, a write tax on hot OLTP tables. Measure before adding to a write-heavy table.
- Enterprise auto-matches indexed views into unrelated queries; Standard/Azure SQL requires `WITH (NOEXPAND)` to force their use. Query the view directly with `NOEXPAND` to be sure.

When you'd rather trade consistency for cheaper writes (Postgres-matview semantics), maintain a **summary table** via a scheduled job or a trigger/app-side upsert instead — state the staleness SLA next to it.

## In-Memory OLTP (memory-optimized tables)

For extreme write/latency contention (session state, hot counters, staging, queue tables) where lock/latch contention on a disk table is the bottleneck:

- Memory-optimized tables + natively-compiled stored procedures eliminate latching and use optimistic MVCC.
- Best fit: transient/ephemeral hot data (the SQL Server answer to "put the session in Redis" when you want it in-engine), not your whole schema.
- Costs: memory sizing, schema restrictions, `SCHEMA_ONLY` (non-durable, lost on restart — perfect for cache-like data) vs `SCHEMA_AND_DATA`. Available on Azure SQL Business Critical / Premium, not General Purpose.

## Plan cache — related but not a data cache

The engine caches **execution plans**, not results. Relevant to caching because plan reuse (good) and plan-cache bloat from un-parameterized ad-hoc SQL (bad) both live here:

- Parameterize queries so plans are reused (`references/performance.md`); un-parameterized ad-hoc SQL floods the plan cache with single-use plans. `OPTIMIZE FOR AD HOC WORKLOADS` server option caps that bloat.
- Plan forcing via Query Store is stability, not a result cache (`references/performance.md`).

## Buffer pool — the mental model

Every read is served from the **buffer pool** (SQL Server's in-memory page cache) if the page is resident, else read from disk into it. `SET STATISTICS IO ON` shows `logical reads` (from the buffer pool) vs `physical reads` (from disk).

- You don't tune this per query; you observe it. A workload whose hot set fits in the buffer pool is CPU-bound; one that doesn't is I/O-bound.
- `max server memory` caps it (box) — set it so the OS keeps headroom; Azure SQL manages it per tier.
- High `physical reads` on a repeated query = the hot set doesn't fit, or a scan is reading too much (fix the query/index first).

## The external-cache seam (summary + handoff)

- Pattern: **cache-aside** — read cache → miss → read SQL Server → fill; write SQL Server → then invalidate (never write cache-first). Full catalog incl. stampede protection, key versioning, negative caching: `data/_shared/caching-patterns`.
- Invalidation transport: TTL (baseline, mandatory) + app-emitted events on write. (SQL Server's legacy **Query Notifications / SqlDependency** exists but is deprecated-in-practice and brittle at scale — prefer app-emitted invalidation over Service Broker notifications.)
- What belongs in Redis vs the engine: sub-ms hot keys, sessions, rate counters, distributed locks → Redis (`data/redis`); anything needing transactional consistency with the source rows → the engine (indexed view, or just the table with the right index).

## Anti-patterns

- Caching a query a covering index would fix.
- Indexed view on a write-heavy OLTP table without measuring the synchronous-maintenance write tax.
- Indexed view without `COUNT_BIG(*)` / `SCHEMABINDING` / unique clustered index — it won't materialize.
- Relying on Enterprise auto-matching of indexed views on Standard/Azure SQL (need `NOEXPAND`).
- Un-parameterized ad-hoc SQL flooding the plan cache.
- `SqlDependency`/Query Notifications as the invalidation backbone at scale.
- Cache written before the DB commit (accidental write-behind).
- Treating the buffer pool as something to tune per query instead of observe.
