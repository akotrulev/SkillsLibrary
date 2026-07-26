# SQL Server — Performance (Query Store, plans, parameter sniffing, tempdb, locks)

Engine-side tuning. Universal query triage (ESR, N+1, projection, keyset pagination) → `data/_shared/slow-query-fixes`; index design → `references/indexing.md`.

## Query Store first — the tuning system of record

SQL Server's distinguishing tuning feature: Query Store captures every query's plans + runtime stats over time, so you tune from **history**, not a one-off `EXPLAIN`. On by default for new DBs on 2022+; enable explicitly on 2019/older:

```sql
ALTER DATABASE CURRENT SET QUERY_STORE = ON;
ALTER DATABASE CURRENT SET QUERY_STORE (
    OPERATION_MODE = READ_WRITE,
    QUERY_CAPTURE_MODE = AUTO,          -- skip trivial/one-off queries
    MAX_STORAGE_SIZE_MB = 1000,
    INTERVAL_LENGTH_MINUTES = 15);
```

Workflow:

1. **Find the offenders**: the SSMS "Top Resource Consumers" / "Regressed Queries" reports, or query `sys.query_store_runtime_stats`. Tune the top few by total duration/CPU/reads — not the one that annoyed someone today.
2. **Diagnose a regression**: a query that got slower usually has a **new, worse plan** (stats change, a parameter-sniffing flip, an upgrade). Query Store shows both plans side by side.
3. **Force the good plan**: `EXEC sys.sp_query_store_force_plan @query_id = ..., @plan_id = ...;` — pins the known-good plan while you fix the root cause. **Automatic tuning** (`FORCE_LAST_GOOD_PLAN`) does this automatically; enable it and review its actions.

## Reading a plan

Capture the **actual** plan (estimated lies when stats are wrong):

```sql
SET STATISTICS IO, TIME ON;
-- (SSMS: "Include Actual Execution Plan")
SELECT Id, Status FROM dbo.Orders
WHERE TenantId = @t AND CustomerId = @c
ORDER BY PlacedAt DESC OFFSET 0 ROWS FETCH NEXT 20 ROWS ONLY;
```

| Symptom in the plan | Meaning | Fix |
|---|---|---|
| **Scan** where you expected a **Seek** on a large table | Missing/unusable index, or predicate not SARGable | Add/extend the index; unwrap functions on the column (`WHERE col = @p`, not `WHERE fn(col) = @p`); fix type mismatch (implicit convert) |
| **Key Lookup** | Non-clustered index found the row, jumped to clustered for missing columns | `INCLUDE` those columns (`references/indexing.md`) |
| Thick arrow: estimated rows ≪ actual rows | Stale/insufficient statistics | `UPDATE STATISTICS`; check for parameter sniffing |
| Large **Sort** + spill warning | No index provides the order, or memory grant too small | Index matching `ORDER BY`, or fix the row estimate |
| **Hash Match** on a small join | Bad cardinality estimate | Fix stats — the optimizer chose hash because it guessed big |
| Yellow **memory-grant warning** (excessive grant / spill) | Estimate wrong → grant wrong | Fix stats; `OPTION (RECOMPILE)` if parameter-driven |
| **Implicit conversion** warning | `nvarchar` param vs `varchar` column (or vice versa) | Match the type — this silently defeats index seeks |

## Parameter sniffing — the #1 SQL Server gotcha

The optimizer builds and caches a plan for the **first** parameter value it sees; a later value with wildly different selectivity reuses that plan. Symptom: fast for one input, slow for another. Escalating fixes:

1. **Optional-parameter plan optimization (2025)** / **Parameter Sensitive Plan optimization (2022)** — the engine keeps multiple plans keyed to parameter cardinality automatically. Often the whole fix on current versions; make sure the DB compat level enables it.
2. `OPTIMIZE FOR UNKNOWN` (or `OPTIMIZE FOR (@p = <typical>)`) — plan for the average, not the sniffed value.
3. `OPTION (RECOMPILE)` — compile per execution (CPU cost per call; only for infrequent, wildly-varying queries). Document the trade-off.
4. Force a good plan in Query Store while you refactor.

## Intelligent Query Processing (IQP) — free wins per compat level

Raising the DB compatibility level turns on IQP features (batch mode on rowstore, memory-grant feedback, adaptive joins, table-variable deferred compilation, scalar UDF inlining, cardinality-estimation feedback). **The upgrade risk is real**: a compat-level bump can change plans. Bump it in a test environment with Query Store on, watch for regressions, and force plans for anything that regresses before promoting.

## Statistics

- Keep **auto-create** and **auto-update** stats on. On very large tables, enable `AUTO_UPDATE_STATISTICS_ASYNC` so a query doesn't stall waiting for a stats refresh.
- After a bulk load / large delete: `UPDATE STATISTICS dbo.Orders WITH FULLSCAN;`
- Skewed columns needing better histograms: `CREATE STATISTICS` with a filter, or filtered stats per hot value range.

## tempdb

- **tempdb is a shared, global bottleneck** — sorts, hash spills, version store (RCSI/snapshot), temp tables all land there.
- Box: multiple equally-sized data files (start at #cores, cap ~8) to reduce allocation-page (PFS/GAM/SGAM) contention; enable `TF 1117/1118`-equivalent behavior (default in 2016+). Managed Azure SQL handles this — don't touch it.
- Watch `sys.dm_db_task_space_usage` / waits on `PAGELATCH_*` on tempdb pages.

## Locking, blocking, deadlocks

```sql
-- Who blocks whom, right now:
SELECT r.session_id AS blocked, r.blocking_session_id AS blocker,
       r.wait_type, r.wait_time, t.text AS blocked_sql
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE r.blocking_session_id <> 0;
```

- **Default to `READ_COMMITTED_SNAPSHOT ON`** (row-versioning) so readers don't block writers — the safe Azure SQL default; enable it on box OLTP DBs. Version store lands in tempdb — size for it.
- **Deadlocks**: capture the deadlock graph via the `system_health` extended-events session (always on). Root cause is almost always **inconsistent lock ordering** across transactions — take locks in a consistent order (e.g. always by ascending key), keep transactions short, retry on error 1205.
- **Lock escalation** (row → table at ~5000 locks): batch large DML into chunks so a single statement doesn't escalate and block the table.
- Migrations: set a short `LOCK_TIMEOUT` in the migration session so a DDL statement waiting behind a long read fails fast and retries instead of freezing production behind an `Sch-M` lock.

## Read scaling

- **Azure SQL Read Scale-Out** (Premium / Business Critical / Hyperscale): route read-only workloads to a replica with `ApplicationIntent=ReadOnly` in the connection string + the `app_ro` role.
- **Geo-replica** for cross-region reads. Replica reads are eventually consistent — read-your-own-writes flows stay on the primary.
- Hyperscale adds up to 30 named replicas for heavy read fan-out.

## Quick-wins checklist

1. Query Store top consumers → tune those; force plans for regressions.
2. Missing index on the filtered column (check SARGability: no function wrap, no implicit convert).
3. Eliminate key lookups with `INCLUDE` (`references/indexing.md`).
4. Keyset pagination replacing deep `OFFSET` (`data/_shared/slow-query-fixes`).
5. `READ_COMMITTED_SNAPSHOT ON` to end reader-writer blocking.
6. `UPDATE STATISTICS WITH FULLSCAN` after bulk loads.
7. Address parameter sniffing (PSP optimization → `OPTIMIZE FOR UNKNOWN` → `RECOMPILE`).

## Anti-patterns

- Tuning without the **actual** plan + Query Store history in hand.
- `OPTION (RECOMPILE)` sprinkled everywhere to "fix perf" — CPU burn, hides the real stats problem.
- `WITH (NOLOCK)` as a "go faster" button — it permits dirty, missing, and doubled reads.
- Non-SARGable predicates: `WHERE YEAR(PlacedAt) = 2026`, `WHERE CAST(Id AS nvarchar) = @p` — defeats the index seek.
- Ignoring implicit-conversion warnings (the silent seek-killer).
- Bumping compat level in production without Query Store watching for plan regressions.
- Million-row single-statement DML that escalates to a table lock.
- `DBCC SHRINK` in a maintenance job (`references/indexing.md`).
