# PostgreSQL — Caching (what the engine offers, and the seams to the external cache)

Scope fence: the external-cache **pattern catalog** — cache-aside, stampede protection, TTL/key policy, invalidation strategies — lives in `data/_shared/caching-patterns`, and Redis mechanics in `data/redis`. This file covers what Postgres itself offers and where it meets that layer.

## Decide in this order

1. **Is the query just slow?** Fix the query/index first (`references/{indexing,performance}.md`). A cache in front of a missing index is debt with a TTL.
2. **Expensive aggregate over slowly-changing data?** → materialized view (in-engine, transactional, SQL-queryable).
3. **Hot-path reads at volume / cross-service reuse / sub-ms latency?** → external cache-aside (`data/_shared/caching-patterns` + `data/redis`).

## Materialized views

The engine-native cache for expensive aggregations (dashboards, rollups, reference joins):

```sql
CREATE MATERIALIZED VIEW mv_daily_revenue AS
SELECT tenant_id, date_trunc('day', placed_at) AS day,
       sum(total_minor) AS revenue_minor, count(*) AS orders
FROM orders WHERE status = 'paid'
GROUP BY 1, 2;

-- Mandatory for CONCURRENTLY:
CREATE UNIQUE INDEX mv_daily_revenue_pk ON mv_daily_revenue (tenant_id, day);

REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_revenue;
```

- **`REFRESH ... CONCURRENTLY`** requires that unique index; without `CONCURRENTLY` the refresh takes an exclusive lock and readers block. Concurrent refresh diffs against the previous contents — slower to run, invisible to readers.
- Refresh is **manual** — schedule it (pg_cron / app scheduler / CI job) or trigger it after the batch that changes the source data. Staleness = your refresh interval; state that SLA next to the view definition.
- Index the matview like a table — it serves real queries.
- A plain `VIEW` is not a cache (re-executes every query); a matview trades staleness for speed.
- Full refresh recomputes everything. If the source is append-only and the recompute hurts, a summary table maintained incrementally (trigger or app-side upsert into a rollup) is the next step up in complexity.

## LISTEN/NOTIFY — event-driven cache invalidation

The seam that makes external caches event-driven instead of TTL-guessing: notify on commit, listeners evict.

```sql
CREATE OR REPLACE FUNCTION notify_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_notify('cache_inval',
        json_build_object('table', TG_TABLE_NAME,
                          'id', COALESCE(NEW.id, OLD.id))::text);
    RETURN COALESCE(NEW, OLD);
END $$;

CREATE TRIGGER products_notify AFTER INSERT OR UPDATE OR DELETE ON products
    FOR EACH ROW EXECUTE FUNCTION notify_change();
```

App side: one dedicated **direct** connection (not from the transaction pool — PgBouncer transaction mode doesn't support LISTEN) per instance: Npgsql `conn.Notification` event + `WaitAsync`; JDBC `PGConnection.getNotifications` polling loop; node-pg `client.on('notification')`.

Rules:

- Notifications fire **on commit** (rolled-back transactions don't notify) — correct by default.
- **At-most-once + connection-scoped**: a listener that was disconnected missed the message. Treat NOTIFY as an optimization over TTL, never the sole consistency mechanism — keep a TTL on every cached key as the backstop (`data/_shared/caching-patterns` rule).
- 8000-byte payload cap; send keys, not data — receivers re-read the row.
- High-fanout/durable eventing belongs on a real broker (outbox pattern → `data/_shared/schema-design`; broker testing → qa `messaging-testing`). LISTEN/NOTIFY is for lightweight in-cluster signals like cache eviction.

## Prepared statements & plan caching

- Drivers prepare hot statements automatically (Npgsql: after 5 executions by default; JDBC `prepareThreshold`; node-pg: opt-in `name` on the query). Wins parse/plan cost on hot paths.
- **PgBouncer transaction mode** historically breaks server-side prepared statements (the session that prepared isn't the session that executes). PgBouncer **1.21+ supports protocol-level prepared statements in transaction mode** — set `max_prepared_statements` — otherwise disable driver-side preparation (`Max Auto Prepare=0`; JDBC `prepareThreshold=0`).
- Generic-plan trap: a prepared statement may switch to a generic plan that ignores parameter skew (fine for `id = $1`, bad for `status = $1` where one status is 90% of rows). If a prepared query is fast ad-hoc but slow prepared: `SET plan_cache_mode = force_custom_plan` for that role/statement.

## Buffer cache — the mental model

Two layers under every read: `shared_buffers` (Postgres' own cache, ~25% RAM) + the OS page cache (the rest). `EXPLAIN (BUFFERS)` `hit` = shared_buffers, `read` = OS cache **or** disk — a "read" isn't necessarily a disk I/O.

- You don't tune this per-query; you observe it. A workload whose hot set fits in shared_buffers is CPU-bound; one that doesn't is I/O-bound (PG 18 async I/O helps exactly here — `references/performance.md`).
- `pg_prewarm` extension to warm a critical table after a restart/failover instead of eating cold-cache latency live.
- Sizing → `references/performance.md`; don't fight managed platforms' defaults.

## The external-cache seam (summary + handoff)

- Pattern: **cache-aside** — read cache → miss → read Postgres → fill; write Postgres → then invalidate (never write cache-first). Full catalog incl. stampede protection, key versioning, negative caching: `data/_shared/caching-patterns`.
- Invalidation transport: TTL (baseline, mandatory) + LISTEN/NOTIFY or app-emitted events (accelerator).
- What belongs in Redis vs the engine: sub-ms hot keys, sessions, rate counters, locks → Redis (`data/redis`); anything needing transactional consistency with the source rows → the engine (matview or just the table with a proper index).

## Anti-patterns

- Caching a query that a `CREATE INDEX` would fix.
- `REFRESH MATERIALIZED VIEW` without `CONCURRENTLY` on a matview readers depend on (readers block for the whole refresh).
- Matview with no unique index, discovered the first time a concurrent refresh is attempted in prod.
- LISTEN on a pooled/PgBouncer connection.
- NOTIFY as the only invalidation (no TTL backstop) — one dropped connection = permanently stale cache.
- Fat NOTIFY payloads carrying row data.
- Prepared statements + old PgBouncer transaction mode ("prepared statement does not exist" in prod).
- Cache written before the DB commit (write-behind without meaning to).
