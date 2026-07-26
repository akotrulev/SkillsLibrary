# MongoDB — Performance

Reading `.explain('executionStats')`, the working-set/WiredTiger cache model, aggregation-pipeline tuning, read/write concern trade-offs, the profiler, and when (and only when) to shard. Engine index mechanics are in `references/indexing.md`; universal triage (ESR, N+1, pagination) is in `data/_shared/slow-query-fixes`.

## The single best predictor: working set vs RAM

MongoDB's storage engine (WiredTiger) keeps hot data + indexes in an in-memory cache (default ≈ 50% of RAM − 1 GB). **If the working set — the documents and index pages your queries actually touch — fits in that cache, Mongo is fast. If it doesn't, every query pages from disk and latency falls off a cliff.** Atlas tier guidance is essentially "buy enough RAM for your working set." Before reaching for exotic tuning, check: is the working set larger than cache? Symptoms: rising cache-eviction rate, high disk read IOPS, `bytesRead` climbing in `serverStatus`.

Levers, cheapest first: fix missing indexes (smaller scans → smaller working set), slim fat documents (project, split hot/cold, bucket), add RAM / bigger tier, then shard.

## Reading `.explain('executionStats')`

Run the query with `.explain('executionStats')` and read the winning plan's stages and counters:

| Signal | Meaning | Fix |
|---|---|---|
| `COLLSCAN` | No usable index — full scan | Add an index matching predicate + sort (ESR) |
| `IXSCAN` → `FETCH`, `docsExamined ≫ nReturned` | Index filters coarsely; most fetched docs are discarded | Add fields to the index so it filters tighter, or cover the projection |
| `totalKeysExamined ≫ nReturned` | Wrong index for the predicate | Reorder/replace the compound index (ESR) |
| Blocking `SORT` stage, `memUsage` near the 100 MB limit | Unbounded in-memory sort — will fail past 100 MB unless `allowDiskUse` | Add an index that supplies the sort order |
| `totalDocsExamined: 0` | **Covered query** — best case | — |
| `executionTimeMillis` high but few keys/docs | Contention, cache misses, or a slow `$lookup`/`$group` | See aggregation + concurrency below |

`nReturned` ≈ `totalKeysExamined` ≈ `totalDocsExamined` is the healthy shape: the index found almost exactly the rows you returned.

## Aggregation-pipeline tuning

The pipeline runs stage by stage; the planner pushes some optimizations down but you shape most of the win by **ordering stages to shrink the stream early**:

- **`$match` first** — filter on indexed fields before anything else so the pipeline starts from an `IXSCAN`, not the whole collection. A `$match` after a `$group` can't use an index.
- **`$project`/`$unset` early** — drop fields you don't need so later stages move less data.
- **`$sort` + `$limit` adjacent** — the planner fuses them into a bounded top-K sort (keeps only N in memory) instead of sorting everything.
- **`$sort` early enough to hit an index** — a `$sort` right after an indexed `$match` on the same key uses the index; a `$sort` after a `$group` is always a blocking in-memory sort.
- **`$lookup` only against an indexed foreign field**, and after you've filtered the driving collection down — a `$lookup` over a large unindexed collection is a nested full scan.
- Watch the **100 MB per-stage memory limit**; a blocking stage (`$group`, `$sort`) that exceeds it fails unless you pass `allowDiskUse: true` — and if you need disk, question the query.

Confirm with `.explain()` on the aggregate — check that the first stage is an `IXSCAN`.

## The profiler

Enable the database profiler to catch repeat offenders:

```javascript
db.setProfilingLevel(1, { slowms: 100 });   // log ops slower than 100 ms
// then mine system.profile for the worst patterns
db.system.profile.aggregate([
  { $group: { _id: '$command.find', n: { $sum: 1 }, avgMs: { $avg: '$millis' } } },
  { $sort: { avgMs: -1 } }, { $limit: 20 }
]);
```

On Atlas, use the **Query Profiler / Performance Advisor** (it also suggests indexes) instead of the raw profiler. Turn profiling off / raise `slowms` after diagnosis — it has overhead.

## Read & write concern (the durability/latency dial)

- **Write concern `w:'majority'`** — the write is acknowledged only after a majority of replica-set members have it; survives a failover. The default for anything that matters. `w:1` (primary only) is faster but can be lost on failover — reserve for low-value, reproducible events.
- **Read concern `'majority'`** — you read only majority-committed data (no dirty reads of writes that could roll back). `'local'` is faster but can read soon-to-be-rolled-back data.
- **Read preference** — `primary` for read-your-writes; `secondaryPreferred` for analytics/reporting where seconds of staleness is fine (offloads the primary). Reads from a secondary are eventually consistent — never use them for a read-after-write in the same flow.
- `readConcern:'majority'` + `readPreference:secondary` + causally-consistent sessions give read-your-writes off a secondary when you truly need it — but that's a specific, deliberate setup.

## Concurrency & connections

- WiredTiger uses document-level concurrency; write contention shows up as high `wiredTiger.concurrentTransactions` ticket waits — a signal of hot documents or under-provisioned IO.
- App pool sizes should be reasonable per instance (50–200). Server connections are ultimately capped by file descriptors; many instances × big pools exhausts the server. Reuse one client per process (router rule).
- Long-running / unindexed queries hold resources — set client-side `maxTimeMS` on queries so a runaway op is killed, the Mongo analog of `statement_timeout`.

## Sharding — last resort, not a starting point

Shard only when a single replica set genuinely can't hold the working set in RAM or serve the write throughput — **after** indexes and document shape are already right. Most "Mongo is slow" tickets are a missing index or a fat document, not a sharding need.

When you do shard, the **shard key is the decision that can't be easily undone** (though 8.0 makes resharding far faster and cheaper than before):

- Pick a key with **high cardinality**, **even write distribution**, and **alignment to your query filter** — a monotonically increasing key (timestamp, ObjectId) creates a hot shard; hash it or compound it.
- Queries that include the shard key are **targeted** (one shard); queries without it are **scatter-gather** (every shard) — keep the shard key in your hot query filters.
- 8.0: `$lookup` inside a transaction now works against sharded collections; resharding is dramatically faster — but "we can reshard later" is still not licence to pick a bad key first.

## What NOT to do

- No tuning before checking working-set-vs-cache and running `.explain()`.
- No blocking `$sort` after `$group` when an early indexed `$sort` would do.
- No `allowDiskUse: true` as a fix — it's a symptom that the pipeline is doing too much in memory.
- No `$lookup` against an unindexed / large collection.
- No secondary reads for read-after-write consistency.
- No `w:1` for data that must survive a failover.
- No profiler left at `slowms:0` in production (overhead).
- No sharding to fix what a missing index caused.

## Handoffs

- Index type/order to fix a COLLSCAN or over-fetch → `references/indexing.md`
- ESR principle, keyset pagination, N+1 across engines → `data/_shared/slow-query-fixes`
- Reducing document size / bucketing → `references/data-modeling.md`
- Offloading reads to a cache instead of the primary → `references/caching.md` + `data/redis`
- Latency dashboards / slow-op telemetry → `observability/*` skills (via the `observability-engineer-{dotnet,java,node}` peer bundled in the matching `be-*` plugin)
