# MySQL — Caching (what the engine offers, and the seam to the external cache)

Scope fence: the external-cache **pattern catalog** — cache-aside, stampede protection, TTL/key policy, invalidation — lives in `data/_shared/caching-patterns`, and Redis mechanics in `data/redis`. This file covers what MySQL itself offers (which is *less* than Postgres/SQL Server) and where it meets that layer.

## The blunt truth: MySQL has almost no in-engine caching feature to lean on

- **No materialized views** (Postgres has them, SQL Server has indexed views). Your only in-engine equivalent is a **summary/rollup table** you maintain yourself.
- **The query cache was removed in MySQL 8.0** — it was a scalability bottleneck (a global mutex invalidated on every write to a referenced table). Don't try to resurrect it; there's no `query_cache_size` to tune. MariaDB still has it but leave it off under concurrency.
- What's left in-engine is the **buffer pool** (a page cache, not a result cache) and **prepared statements** (parse/plan reuse).

So on MySQL the answer to "cache this" is more often **an external cache-aside layer** than on the other two engines. Decide in this order:

1. **Is the query just slow?** Fix the query/index first (`references/{indexing,performance}.md`). A cache in front of a missing index is debt with a TTL.
2. **Expensive aggregate over slowly-changing data?** → a **summary table** maintained by a scheduled job or trigger (below).
3. **Hot-path reads at volume / cross-service reuse / sub-ms latency?** → external cache-aside (`data/_shared/caching-patterns` + `data/redis`).

## Summary / rollup tables (the materialized-view substitute)

Since there's no `REFRESH MATERIALIZED VIEW`, maintain the aggregate yourself:

```sql
CREATE TABLE daily_revenue (
    tenant_id     BIGINT UNSIGNED NOT NULL,
    day           DATE            NOT NULL,
    revenue_minor BIGINT          NOT NULL,
    orders        INT             NOT NULL,
    PRIMARY KEY (tenant_id, day)
) ENGINE = InnoDB;

-- Scheduled recompute (cron / app scheduler / MySQL EVENT):
REPLACE INTO daily_revenue (tenant_id, day, revenue_minor, orders)
SELECT tenant_id, DATE(placed_at), SUM(total_minor), COUNT(*)
FROM orders WHERE status = 'paid' AND placed_at >= CURDATE() - INTERVAL 2 DAY
GROUP BY tenant_id, DATE(placed_at);
```

- Two maintenance strategies: **batch recompute** (simple; staleness = the schedule — state the SLA next to the table) or **incremental** (a trigger/app-side upsert bumps the rollup on each source write — always fresh, but couples every write path to the rollup and risks lock contention on the hot summary row).
- Index the summary table like any table — it serves real queries.
- A MySQL **`EVENT`** can run the recompute inside the DB (`SET GLOBAL event_scheduler = ON`), but an app scheduler / CI job is easier to observe and version — prefer that unless the DB must own it.

## Prepared statements & plan reuse

- The `mysql2` / JDBC / MySqlConnector drivers use server-side prepared statements — parse/plan the statement once, execute many with bound parameters. Wins parse cost on hot paths and is the parameterization mechanism (`SKILL.md` rules).
- Behind **ProxySQL**, server-side prepared statements are handled by the proxy's connection multiplexing — verify your prepared-statement path works through it (ProxySQL supports it, but misconfiguration silently falls back to text-protocol). RDS Proxy pins a connection while a prepared statement is open, reducing multiplexing — be aware for high-prepared-statement workloads.
- MySQL has no user-visible plan-forcing store (unlike SQL Server Query Store). Optimizer hints (`/*+ ... */`) are the lever when the optimizer picks wrong.

## Buffer pool — the mental model

Every read is served from the **InnoDB buffer pool** if the page is resident, else read from disk into it. This is a *page* cache, not a *result* cache — the same query re-runs its execution each time; only the underlying page reads are cached.

- You don't tune this per query; you observe it (`SHOW ENGINE INNODB STATUS`, `sys` buffer-pool views). A workload whose hot set fits is CPU-bound; one that doesn't is I/O-bound.
- Size it to ~70–80% of RAM on a dedicated host (`references/performance.md`); managed services set it per tier.
- **Buffer pool warmup**: `innodb_buffer_pool_dump_at_shutdown` / `innodb_buffer_pool_load_at_startup` (on by default in 8.0) reload the hot page set after a restart so you don't eat cold-cache latency live — the MySQL analog of Postgres `pg_prewarm`.

## The external-cache seam (summary + handoff)

- Pattern: **cache-aside** — read cache → miss → read MySQL → fill; write MySQL → then invalidate (never write cache-first). Full catalog incl. stampede protection, key versioning, negative caching: `data/_shared/caching-patterns`.
- Invalidation transport: TTL (baseline, mandatory) + **app-emitted events on write**. MySQL has no LISTEN/NOTIFY; if you need DB-driven invalidation, tail the **binlog** (Debezium / a CDC consumer) and emit cache-eviction events from there — heavier than app-emitted, use only when writes bypass the app.
- What belongs in Redis vs the engine: sub-ms hot keys, sessions, rate counters, distributed locks → Redis (`data/redis`); consistent aggregates over source rows → a summary table (accepting its staleness) or just the base table with the right index.

## Anti-patterns

- Trying to bring back the query cache (gone in 8.0 for good reasons; a mutex bottleneck in MariaDB).
- Caching a query a covering index would fix.
- An incremental rollup trigger that contends on one hot summary row under write load — prefer batch recompute unless freshness demands otherwise.
- Treating the buffer pool as a result cache (it caches pages, not query results).
- Assuming prepared statements multiplex cleanly through every proxy (verify ProxySQL / RDS Proxy behavior).
- Cache written before the DB commit (accidental write-behind).
- Reaching for binlog/CDC invalidation when app-emitted events would do.
