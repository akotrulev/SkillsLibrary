# MongoDB — Caching & the external seam

What MongoDB itself offers for read acceleration, the **change-stream invalidation seam** that makes an external cache reliable, and summary/rollup collections as the materialized-view analog. The cross-engine pattern catalog (cache-aside, stampede, TTL, negative caching) lives in `data/_shared/caching-patterns`; the Redis command mechanics live in `data/redis`. This file is only the Mongo-side integration.

## What Mongo gives you natively

Mongo has **no query-result cache and no materialized views** in the SQL sense. Its "cache" is the **WiredTiger cache** (hot documents + index pages in RAM — see `references/performance.md`). The performance lever is "keep the working set in RAM," not "add a cache layer inside the engine." For application-level caching you reach outside the engine (Redis) or pre-compute (summary collections).

## Summary / rollup collections (the materialized-view analog)

When a read is an expensive aggregation refreshed periodically ("dashboard revenue by day", "top-N sellers"), **write the computed result into a summary collection** and read from that — the Mongo equivalent of a materialized view.

Two refresh models:

- **Batch refresh** — a scheduled job runs the aggregation with `$merge` / `$out` into the summary collection. `$merge` upserts (incremental, keeps the collection live); `$out` replaces the whole collection (simple, but the target is unavailable mid-write).

```javascript
db.orders.aggregate([
  { $match: { status: 'paid', placedAt: { $gte: since } } },
  { $group: { _id: { day: { $dateTrunc: { date: '$placedAt', unit: 'day' } } },
              revenueMinor: { $sum: '$totalMinor' } } },
  { $merge: { into: 'dailyRevenue', on: '_id', whenMatched: 'replace', whenNotMatched: 'insert' } }
]);
```

- **Incremental on write** — maintain the rollup with atomic operators (`$inc`, `$max`) on the write path (the *computed pattern*, `references/data-modeling.md`). Cheaper reads, but the write path owns keeping it correct.

Choose batch when the read tolerates minutes of staleness and the source churns constantly; choose incremental when the read must be fresh and the update math is simple.

## Change streams — the invalidation seam

A **change stream** (`db.collection.watch()`) is a durable, resumable feed of inserts/updates/deletes, driven off the replica-set oplog. It is the reliable channel for **event-driven cache invalidation**: instead of hoping every writer remembers to invalidate, one worker watches the collection and invalidates keys no matter which app instance wrote.

```typescript
const stream = db.collection('orders').watch(
  [{ $match: { operationType: { $in: ['update', 'replace', 'delete'] } } }],
  { fullDocument: 'updateLookup' }
);
for await (const change of stream) {
  const id = change.documentKey._id.toString();
  await redis.unlink(`v1:order:${id}`);          // invalidate the cache key
  resumeToken = change._id;                        // persist for restart
}
```

- **Persist the resume token** and restart the stream from it so a worker restart doesn't miss changes — this is what makes it reliable rather than best-effort.
- Requires a **replica set** (hence the router's "replica set always" rule) and majority read concern.
- Pair it with a **TTL on the cache key** as a safety net: if the worker hiccups, the key still expires. (This is the `_shared/caching-patterns` event-driven + TTL pattern, realized with Mongo change streams.)
- Change streams also drive audit capture (`references/security.md`) and cross-store projections — same mechanism.

## Read-preference offload (not a cache, but related)

For read-heavy analytics that tolerate seconds of staleness, `readPreference: secondaryPreferred` offloads the primary by serving from secondaries (`references/performance.md`). It reduces primary load like a cache would, without a separate store — but it is **eventually consistent** and never valid for read-after-write. Use it for reporting, not for the hot transactional path.

## The external cache seam (Redis in front of Mongo)

For sub-millisecond reads on hot keys, the default is **cache-aside in Redis in front of Mongo**:

1. Read Redis → on miss, read Mongo, `SET` with a jittered TTL, return.
2. On write, write Mongo **first**, then invalidate the Redis key — via the write path *and* via the change-stream worker as the coordinated safety net.
3. Version + namespace keys (`v1:order:<id>`); every key has a TTL.

All of that discipline — pattern choice, key design, stampede protection, negative caching — is owned by `data/_shared/caching-patterns` and implemented with `data/redis` commands. Mongo's only jobs in that architecture are: be the system of record, and emit the change stream that keeps the cache honest.

## Rules

- No engine-internal query cache exists — don't design as if one does; tune the working set (`references/performance.md`) or cache externally.
- Expensive periodic reads → summary collection via `$merge` (incremental) or `$out` (replace), not re-aggregation per request.
- Event-driven invalidation → a **single change-stream worker** with a **persisted resume token**, paired with a TTL safety net.
- Write to Mongo first, then invalidate the cache; `UNLINK`/`DEL`, never `SET` the new value.
- Secondary reads for staleness-tolerant analytics only — never for read-after-write.

## What NOT to do

- No expectation of a built-in result cache or materialized view.
- No `$out` into a collection that must stay continuously readable (it replaces atomically but is unavailable mid-build for readers expecting the old data) — use `$merge`.
- No change-stream consumer without a persisted resume token (silent gap on restart).
- No cache invalidation that relies solely on every writer remembering — back it with the change stream + TTL.
- No secondary read where the caller just wrote and expects to see it.

## Handoffs

- Cache-aside / read-through / stampede / TTL / negative-cache pattern catalog → `data/_shared/caching-patterns`
- Redis commands, key design, client setup → `data/redis`
- The computed/rollup pattern on the document itself → `references/data-modeling.md`
- Working-set / secondary-read tuning → `references/performance.md`
- Change-stream-driven audit trail → `references/security.md`
