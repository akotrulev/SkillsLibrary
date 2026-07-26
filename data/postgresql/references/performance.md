# PostgreSQL — Performance (EXPLAIN, vacuum, partitioning, memory, locks)

Engine-side tuning. Universal query triage (ESR, N+1, projection, keyset pagination) → `data/_shared/slow-query-fixes`; index design → `references/indexing.md`.

## EXPLAIN — the deep-dive

Always tune from evidence:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, status FROM orders
WHERE tenant_id = $1 AND customer_id = $2
ORDER BY placed_at DESC LIMIT 20;
```

Read it bottom-up (leaves execute first). What to look for:

| Symptom in the plan | Meaning | Fix |
|---|---|---|
| `Seq Scan` on a large table with a selective filter | Missing/unusable index | Add the index; check the predicate isn't wrapped in a function (→ expression index) or type-mismatched (`bigint` col vs `text` param) |
| `Rows Removed by Filter: <huge>` | Index found rows, filter discarded most | Extend the composite / add the filter column / partial index |
| `Sort` (esp. `Sort Method: external merge Disk`) | No index provides the order; spilled past `work_mem` | Index matching `ORDER BY` (incl. `DESC`), or raise `work_mem` for the analytics role |
| Estimated `rows=1` vs `actual rows=50000` | Stale/insufficient statistics | `ANALYZE` the table; raise the column's statistics target; extended statistics for correlated columns |
| `Nested Loop` over a huge inner side | Mis-estimated join cardinality | Fix the stats first — the planner chose wrong because it guessed wrong |
| `Heap Fetches: <high>` on an Index Only Scan | Visibility map stale | Vacuum the table |
| `Buffers: read=<high>` | Cold cache or genuinely scanning too much | Distinguish: re-run — if it becomes `hit`, it was cache warm-up; if it stays `read`, the query touches too much data |

Statistics fixes:

```sql
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 500;  -- skewed column
CREATE STATISTICS orders_tenant_status (dependencies) ON tenant_id, status FROM orders;
ANALYZE orders;
```

Fleet-wide: `pg_stat_statements` ordered by `total_exec_time DESC` finds the queries worth tuning — tune the top 10, not the one that annoyed someone today.

## Autovacuum & bloat

MVCC means every UPDATE/DELETE leaves a dead tuple; vacuum reclaims them and maintains the visibility map (which index-only scans depend on).

- Monitor `pg_stat_user_tables`: `n_dead_tup` vs `n_live_tup`, `last_autovacuum`, `last_autoanalyze`.
- Default trigger is ~20% of the table dead — on a 100M-row table that's 20M dead tuples. High-churn tables get per-table tuning:

```sql
ALTER TABLE orders SET (autovacuum_vacuum_scale_factor = 0.02,
                        autovacuum_analyze_scale_factor = 0.01);
```

- **Long-running transactions block vacuum globally** — nothing newer than the oldest open snapshot can be reclaimed. Hunt them:

```sql
SELECT pid, state, xact_start, query FROM pg_stat_activity
WHERE state = 'idle in transaction' ORDER BY xact_start;
```

Set `idle_in_transaction_session_timeout` on app roles (`references/security.md`) so leaked transactions kill themselves.
- PG 17+ vacuums use dramatically less memory for dead-tuple tracking; PG 18 async I/O speeds the vacuum read phase — both are free wins on upgrade, not knobs.

## Memory configuration

| Setting | Starting point | Notes |
|---|---|---|
| `shared_buffers` | 25% of RAM (dedicated host) | Managed platforms set this; don't fight their default |
| `work_mem` | 4–16 MB OLTP | **Per sort/hash operation, not per query** — a 10-way parallel hash join can take 10×. Raise per-role for analytics (`ALTER ROLE reporting SET work_mem = '256MB'`), not globally |
| `maintenance_work_mem` | 256 MB–1 GB | Speeds index builds and vacuum |
| `effective_cache_size` | 50–75% of RAM | Planner hint only (OS cache included) — costs nothing, affects plan choice |
| `io_method` (PG 18) | `worker` (default) | `io_uring` on modern Linux self-hosted; benefits seq scans, bitmap scans, vacuum — up to ~3× on I/O-bound scans |

## Partitioning

For time-series/append-mostly tables **> ~100M rows** where queries carry a time predicate and retention means deleting old data. Declarative range partitioning (never trigger-based):

```sql
CREATE TABLE events (
    id         bigint GENERATED ALWAYS AS IDENTITY,
    tenant_id  bigint NOT NULL,
    occurred_at timestamptz NOT NULL,
    payload    jsonb NOT NULL,
    PRIMARY KEY (occurred_at, id)      -- partition key must be in the PK
) PARTITION BY RANGE (occurred_at);

CREATE TABLE events_2026_07 PARTITION OF events
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
```

- Wins: partition pruning (queries touch only matching partitions), retention as `DROP TABLE` (instant, no vacuum debt vs a 100M-row DELETE), per-partition vacuum/indexes.
- Costs: every unique constraint must include the partition key; more planning overhead with thousands of partitions (keep it ≤ low hundreds); create partitions ahead via a scheduled job (`pg_partman` or cron).
- Don't partition to fix a slow query a better index would fix — partitioning is for lifecycle + scan-scope, not a substitute for indexing.

## Locks & contention triage

```sql
-- Who blocks whom, right now:
SELECT blocked.pid AS blocked_pid, blocked.query AS blocked_query,
       blocking.pid AS blocking_pid, blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid));
```

- DDL takes `ACCESS EXCLUSIVE` — a migration waiting on that lock queues **behind** long reads and blocks everything arriving after it. Set `lock_timeout = '5s'` in migration sessions so they fail fast and retry instead of freezing production.
- Hot-row contention (counters, "last seen" columns): batch in the app, or move the churn to Redis (`data/redis`).
- Queue tables: `SELECT ... FOR UPDATE SKIP LOCKED LIMIT n` — workers don't serialize on the same rows.
- Deadlocks: take locks in a consistent order (e.g. always ascending id); keep transactions short; retry on `40P01`.

## Read scaling

- Move analytics/reporting off the primary: read replica (streaming replication; managed platforms make this a checkbox) + the `app_ro` role.
- Replica reads are **eventually consistent** — read-your-own-writes flows stay on the primary.
- Wrap report transactions `BEGIN READ ONLY`.

## Quick-wins checklist

1. `pg_stat_statements` top-10 by `total_exec_time` — tune those.
2. Missing index on the filtered column (check for function-wrapped or type-mismatched predicates).
3. Keyset pagination replacing `OFFSET` (`data/_shared/slow-query-fixes`).
4. Drop unused + INVALID indexes (`references/indexing.md`).
5. `statement_timeout` + `idle_in_transaction_session_timeout` per app role.
6. Per-table autovacuum tuning on the churn tables.
7. Analytics to a replica with role-scoped `work_mem`.

## Anti-patterns

- Tuning without `EXPLAIN (ANALYZE, BUFFERS)` output in hand.
- Global `work_mem` cranked "because sorts spill" — OOM at concurrency.
- Partitioning as a first resort for slow queries.
- Migrations without `lock_timeout` freezing production behind one long read.
- A million-row `DELETE` where a partition drop (or batched delete) belongs.
- Ignoring `idle in transaction` sessions — the silent vacuum killer.
- Counters/heartbeats UPDATE-ing the same hot row from every request.
