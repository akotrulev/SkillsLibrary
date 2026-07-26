# MySQL — Performance (EXPLAIN, buffer pool, Performance Schema, locking, partitioning)

Engine-side tuning for InnoDB. Universal query triage (ESR, N+1, projection, keyset pagination) → `data/_shared/slow-query-fixes`; index design → `references/indexing.md`.

## EXPLAIN — the deep dive

Tune from evidence. On MySQL 8.0.18+ use **`EXPLAIN ANALYZE`** — it *runs* the query and reports actual per-node timing and row counts (MariaDB's `ANALYZE` output differs; older MySQL only has estimated `EXPLAIN FORMAT=JSON`):

```sql
EXPLAIN ANALYZE
SELECT id, status FROM orders
WHERE tenant_id = ? AND customer_id = ?
ORDER BY placed_at DESC LIMIT 20;
```

| Symptom | Meaning | Fix |
|---|---|---|
| `type: ALL` (full table scan) on a big table | No usable index, or non-SARGable predicate | Add/extend the index; unwrap functions (`WHERE col = ?`, not `WHERE fn(col) = ?`); fix a type/collation mismatch |
| `key: NULL` | Optimizer found no index to use | The above — check the composite's leftmost prefix matches |
| `rows` estimate ≫ rows actually returned (`Extra: Using where`) | Index found rows, filter discarded most | Extend the composite / add the filter column |
| `Extra: Using filesort` | No index provides the `ORDER BY` | Index matching the sort (incl. direction) |
| `Extra: Using temporary` | Group/derived table materialized in memory/disk | Index the `GROUP BY` columns; avoid `SELECT DISTINCT` over big sets |
| `Extra: Using index` | Covering — good, no PK bookmark lookup | (this is the goal for hot reads) |
| Implicit collation/type conversion (visible in `FORMAT=JSON` `attached_condition`) | e.g. `utf8mb4` col vs `latin1` param, string vs int | Match types/collations — silently defeats the index |

Fleet-wide, the offender list comes from Performance Schema (below), not from staring at one query.

## Performance Schema & `sys` — the observability backbone

The canonical source of "what's actually slow" (enable it — it's on by default in 8.0):

```sql
-- Top statements by total latency (the queries worth tuning):
SELECT * FROM sys.statement_analysis ORDER BY total_latency DESC LIMIT 20;

-- Full-table-scan offenders:
SELECT * FROM sys.statements_with_full_table_scans ORDER BY rows_examined DESC LIMIT 20;

-- Raw digest table (aggregated by normalized statement):
SELECT digest_text, count_star, avg_timer_wait, sum_rows_examined
FROM performance_schema.events_statements_summary_by_digest
ORDER BY sum_timer_wait DESC LIMIT 20;
```

Tune the top few by total latency and `rows_examined`, not the query that annoyed someone today. The **slow query log** + **`pt-query-digest`** (Percona Toolkit) is the classic complementary workhorse for offline analysis.

## Buffer pool & core InnoDB knobs

- **`innodb_buffer_pool_size`** — the single biggest knob. Target ~70–80% of RAM on a dedicated DB host. This is InnoDB's page cache; a workload whose hot set fits here is CPU-bound, one that doesn't is I/O-bound. Managed services set it per tier — don't fight their default.
- **`innodb_redo_log_capacity`** (8.0.30+; older: `innodb_log_file_size`) — bigger redo means fewer flushes under write load; size up on busy write systems.
- **`innodb_flush_method = O_DIRECT`** (Linux) — avoids double-caching between InnoDB and the OS page cache.
- **`innodb_flush_log_at_trx_commit`** — `1` (default) is fully durable (flush per commit); `2` trades a ~1s crash window for throughput. Never silently weaken this on financial data.
- **`max_connections`** — every connection costs memory; multiplex with **ProxySQL / RDS Proxy** rather than raising it (`SKILL.md`).

## Locking, blocking, deadlocks

InnoDB is row-level locking with MVCC; the default isolation is **`REPEATABLE READ`**.

- **Gap locks / next-key locks**: under `REPEATABLE READ`, range statements lock the *gaps* between index rows to prevent phantoms — this causes lock contention and deadlocks that surprise people coming from other engines. Reducing to `READ COMMITTED` removes most gap locks (at the cost of phantom-read protection) — a legitimate choice for high-contention OLTP; decide deliberately.
- **Current blocking**:

```sql
SELECT * FROM sys.innodb_lock_waits;                    -- who waits on whom
SELECT * FROM performance_schema.data_locks;            -- lock detail
```

- **Deadlocks**: `SHOW ENGINE INNODB STATUS` shows the last deadlock graph. Root cause is almost always inconsistent lock ordering — take locks in a consistent order (e.g. ascending PK), keep transactions short, retry on deadlock (error 1213) / lock-wait timeout (1205).
- **Long-running transactions** pin the undo log and block purge of old row versions — history bloat + degrading performance. Hunt them:

```sql
SELECT trx_id, trx_started, trx_mysql_thread_id, trx_query
FROM information_schema.innodb_trx ORDER BY trx_started;
```

Set `innodb_lock_wait_timeout` and cap statement time (`max_execution_time` hint for SELECTs) so a wedged transaction self-terminates.

## Partitioning

For time-series/append-mostly tables **> ~100M rows** where queries carry a partition-key predicate and retention means dropping old data. InnoDB native `RANGE` partitioning:

```sql
ALTER TABLE events PARTITION BY RANGE (TO_DAYS(occurred_at)) (
    PARTITION p2026_07 VALUES LESS THAN (TO_DAYS('2026-08-01')),
    PARTITION p2026_08 VALUES LESS THAN (TO_DAYS('2026-09-01')),
    PARTITION pmax      VALUES LESS THAN MAXVALUE
);
```

- Wins: **partition pruning** (queries touch only matching partitions), retention as `ALTER TABLE ... DROP PARTITION` (instant vs a 100M-row DELETE), per-partition operations.
- Constraints (MySQL-specific): **every unique key / PK must include the partition key** — often forces a composite PK `(id, occurred_at)`, which changes clustering. Partitioning **disables foreign keys** on the partitioned table. Pruning only works when the `WHERE` uses the partition-key expression directly.
- Create future partitions ahead via a scheduled job (there's no `pg_partman` equivalent — script it or use a tool).
- Don't partition to fix a query a better index would fix.

## Aurora MySQL specifics

- **Aurora Replicas** share the distributed storage layer — replication lag is typically < 100 ms and there's no binlog-replay per replica. Read scaling is a reader-endpoint routing choice, not a lag-management project.
- **Aurora Global Database** for cross-region read replicas with ~1 s lag; **Backtrack** rewinds the cluster in place (no PITR restore) — useful after a bad data operation.
- **RDS Proxy** for connection multiplexing — effectively required for Lambda-fronted Aurora/MySQL to avoid connection storms.
- Some box-tuning knobs (`innodb_flush_method`, redo sizing) are Aurora-managed / no-ops — don't try to tune the storage layer Aurora owns.

## Read scaling

- Route reporting/analytics reads to a replica (RDS read replica / Aurora reader endpoint) with the `app_ro` role (`references/security.md`).
- Replica reads are **eventually consistent** — read-your-own-writes flows stay on the primary/writer.

## Quick-wins checklist

1. `sys.statement_analysis` top-by-latency → tune those.
2. Missing index on the filtered column (check SARGability + collation/type match).
3. Make the hot read covering (`Using index`) — put projected columns in the key (`references/indexing.md`).
4. Keyset pagination replacing deep `OFFSET` (`data/_shared/slow-query-fixes`).
5. `innodb_buffer_pool_size` ~70–80% RAM (self-hosted).
6. Hunt long-running transactions (`information_schema.innodb_trx`); set lock-wait + statement timeouts.
7. Consider `READ COMMITTED` if gap-lock contention dominates.
8. Analytics to a replica / Aurora reader.

## Anti-patterns

- Tuning without `EXPLAIN ANALYZE` (or `FORMAT=JSON`) output in hand.
- Non-SARGable predicates: `WHERE DATE(placed_at) = ?`, `WHERE CAST(id AS CHAR) = ?` — defeats the index.
- Ignoring implicit collation/type conversion (the silent index-killer, esp. `utf8mb4` vs `latin1`, string-vs-int).
- Partitioning as a first resort for a slow query a better index would fix.
- Forgetting that partitioning forces the partition key into every unique key and disables FKs.
- Long-lived transactions bloating the undo log / blocking purge.
- Raising `max_connections` instead of adding a proxy.
- Weakening `innodb_flush_log_at_trx_commit` on durable/financial data for throughput.
- Trying to tune Aurora's managed storage-layer knobs.
