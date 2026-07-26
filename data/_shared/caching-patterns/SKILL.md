---
name: data-caching-patterns
description: Use when the user is choosing a caching strategy in front of any database — cache-aside vs read-through vs write-through vs write-back vs refresh-ahead, invalidation, key design, TTL strategy, stampede protection. Triggers: "pick a caching strategy", "how should we invalidate this cache", "cache key naming", "TTL for X", "stampede protection", "negative caching". Do NOT use for Redis-specific commands (use `data/redis`) or for engine-specific tuning (use `data/<db>`).
---

# Data — Caching Patterns (cross-engine)

Decision frame for caching in front of any system of record (Postgres / Mongo / SQL Server / etc.). Picks the right pattern, names keys, sizes TTLs, defends against stampedes, and chooses invalidation. Engine details (Redis commands, in-memory specifics) live in `data/redis`.

## When to use

- Picking among cache-aside / read-through / write-through / write-back / refresh-ahead
- Designing key namespace and versioning
- TTL strategy per entity tier
- Invalidation: explicit, TTL-based, event-driven (CDC / change streams / Outbox)
- Stampede protection (request coalescing, jittered TTLs, soft TTLs)
- Multi-level caching (in-process + Redis)
- Negative caching (cache the "not found")

## When NOT to use

- Redis commands / data types / clients → `data/redis`
- Engine-specific perf → `data/postgresql` / `data/mongodb` / etc.

## Decision matrix — which pattern?

| Pattern | Reads | Writes | Consistency | Complexity | When to choose |
|---|---|---|---|---|---|
| **Cache aside** | App reads cache → falls through to DB → fills cache | App writes DB → invalidates cache | Eventually consistent within TTL | Low | **Default** — read-heavy + tolerant of slight staleness |
| **Read-through** | Cache library auto-loads on miss | App writes DB → invalidates cache | Same as cache aside | Low | Framework provides it (Spring `@Cacheable`) — same pattern with less boilerplate |
| **Write-through** | Cache or DB | App writes cache → cache writes DB synchronously | Cache and DB always agree (cache is authoritative for the write path) | Medium | Simplifies reads, complicates failure handling — rare in our stacks |
| **Write-behind / write-back** | Cache | App writes cache → async flush to DB | Risk of data loss on failure | High | Latency-critical writes that tolerate eventual durability |
| **Refresh-ahead** | Cache (background refresher repopulates before expiry) | Whatever | Predictable cold latency | Medium | Hot keys with predictable access; top-N lists; reference data |

Rule: **start with cache-aside**, escalate only when the read pattern, consistency model, or write load justifies it.

## Key design

### Naming convention

```
v<schemaVersion>:<tenant>:<entity>:<id>[:<sub>]
```

Examples:

```
v1:tenant:42:user:7
v1:tenant:42:user:7:permissions
v2:tenant:42:order:abc:lines
```

- **`v<n>`** — bump to invalidate a whole class of keys when the cached shape changes (cheap migration)
- **`tenant:<id>`** — enables per-tenant flush (`SCAN MATCH v1:tenant:42:*` + `UNLINK`)
- **`<entity>:<id>`** — the actual resource
- **`<sub>`** — sub-resource or derived view

Keep keys readable; the few extra bytes don't matter at the scale where caching helps.

### Cardinality

- A single cache key per logical resource — not one per query variation
- Compose keys for views (`order:123:summary`, `order:123:lines`) when you need different invalidation lifetimes
- Avoid keys driven by query parameters with high combinatorial explosion (`search:<freeform-text>`) — those age out before they're useful

## TTL strategy

| Tier | Examples | TTL |
|---|---|---|
| **Reference / config** | Currencies, country list, feature flags | Hours to days (with explicit invalidation on update) |
| **User profile / permissions** | `user:7:profile`, `user:7:permissions` | Minutes (e.g. 5–15) |
| **Computed derived views** | Reports, leaderboards | Seconds to minutes; refresh-ahead candidate |
| **Per-request memoization** | Same call, same request | Process-local in-memory cache (`MemoryCache`, Caffeine, lru-cache) |

Every key has a TTL. **No exceptions.** A key without a TTL is a memory leak waiting for someone to forget about it.

### Jittered TTLs

```
ttl = base_ttl + uniform_random(0, base_ttl * 0.2)
```

A 20% jitter prevents thousands of keys minted at the same time from expiring at the same time and stampeding the DB.

## Invalidation strategies

| Strategy | When | Cost |
|---|---|---|
| **TTL-only** | Tolerable staleness; no coordination | Cheap |
| **Explicit on write** | Read-your-writes within one process; not coordinated across processes | Cheap |
| **Versioned keys (bump prefix)** | Schema-shape change, mass invalidation | Cheap |
| **Per-tenant flush** | Tenant-level admin events | `SCAN` + `UNLINK` — medium |
| **Event-driven via CDC / change streams** | Strong consistency between write source and cache | Highest |

### Event-driven invalidation

Postgres logical replication, Mongo change streams, DynamoDB Streams, Cosmos change feed — all give you a reliable channel to invalidate cache keys when the write happens, no matter which app instance wrote. Pattern:

```
write → DB → CDC/stream → invalidation worker → DEL/UNLINK cache key
```

Pair with TTLs as a safety net — if the worker hiccups, the key still expires.

*The change channel itself is engine-specific — the invalidation strategy is here, the wiring is in the engine skill:* Postgres logical replication / `LISTEN/NOTIFY` (`data/postgresql/references/caching.md`), Mongo change streams (`data/mongodb/references/caching.md` — the change-stream invalidation seam), DynamoDB Streams, Cosmos change feed. Redis command mechanics for the cache itself (`SETNX`, `UNLINK`, `SCAN`) live in `data/redis/references/patterns.md`.

## Stampede protection

### Cache stampede / thundering herd

100 requests hit on a cache miss. Without protection, all 100 hit the DB. The DB melts; the cache fills; the next batch melts the DB again. Mitigations:

1. **Request coalescing** — only the first miss queries the DB; later misses wait for the first to complete and reuse its result. Implement via `SETNX` lock + poll, or a per-process "single-flight" group:

```typescript
// Single-flight pseudo
async function getOrLoad(key: string, loader: () => Promise<T>): Promise<T> {
  if (inFlight.has(key)) return inFlight.get(key)!;
  const p = loader().finally(() => inFlight.delete(key));
  inFlight.set(key, p);
  return p;
}
```

2. **Jittered TTLs** — desynchronize key expiry
3. **Soft TTL / refresh-ahead** — return stale data and refresh asynchronously when the value is near expiry
4. **Probabilistic early expiration** (XFetch) — recompute as the value approaches expiry with rising probability

For most workloads, **single-flight + jittered TTLs** is enough.

### Negative caching

When the DB returns "not found", cache that result with a **short TTL** (30–60s). Without it, hammered lookups of nonexistent ids overwhelm the DB. Be careful — too-aggressive negative caching delays legitimate creates.

```
v1:user:7   → { ... }              (300s)
v1:user:99  → __MISS__              (30s)
```

## Multi-level caching

```
Request → in-process LRU (microseconds) → Redis (milliseconds) → DB (tens of ms)
```

In-process is faster but per-instance — invalidation is harder. Reasonable when:

- Per-request memoization within one handler (free, no invalidation worry)
- Read-mostly reference data that updates rarely (config, flag values) — refresh on a timer

Always invalidate **both** layers when invalidating; the in-process layer is the trap.

## Metrics that matter

- **Hit ratio** — too low (< ~70% for cache-aside reads) means TTL is too short or keys are wrong
- **p99 cold latency** — what users feel on a miss; if it's bad, the cache is masking a real DB problem
- **Key cardinality** — explosion (millions of keys) usually means a query parameter or unbounded id is in the key
- **Eviction rate** — eviction events mean the working set is bigger than the cache; size up or shorten TTL on cold keys
- **Stampede events** — track DB query rate on a single key right after expiry; spikes = need single-flight

## Rules

- **Default to cache-aside.** Escalate to other patterns only when the data justifies it.
- Every cache key has a **TTL** and a **version prefix**
- Write to DB **first**, then invalidate cache (never cache-then-DB — cache becomes the source of truth on failure)
- Use **DEL/UNLINK on invalidation**, not `SET` with the new value — avoids stale-write races
- **Jitter** TTLs (~20%) on any high-cardinality key class
- **Single-flight** for any expensive miss path
- **Negative cache** with short TTL for "not found"
- Avoid caching write paths
- One owner per cache namespace; document the invalidation contract
- Pair TTL with event-driven invalidation when consistency matters — TTL is the safety net
- Track hit ratio and act on regressions

## What NOT to do

- No TTL-less keys (except in dedicated buckets with eviction policy and documented rationale)
- No "cache first, DB second" on writes
- No `SET` with the new value as invalidation — `DEL`/`UNLINK`
- No keys derived from unbounded query strings — cardinality explosion
- No "we'll invalidate manually from an admin endpoint when the data changes" — make it automatic via event-driven invalidation or TTL
- No global flush as a routine invalidation — tank the DB on the recovery
- No different invalidation strategies for the same entity in different code paths — pick one, centralize it
- No assuming cache is consistent across instances when caches are local
- No caching personalized data under a non-personalized key
- No caching response objects with `Set-Cookie` / `Authorization` headers

## Generation steps

1. Confirm the entity to cache, read/write rates, staleness tolerance.
2. Pick the pattern from the decision matrix (cache-aside is the default).
3. Design the key namespace (`v1:tenant:<id>:entity:<id>:sub`).
4. Pick TTLs from the tier table; add jitter where stampedes are possible.
5. Decide invalidation strategy — TTL-only, explicit, or event-driven.
6. Implement single-flight if the miss path is expensive.
7. Add negative cache if "not found" lookups are a workload.
8. Instrument hit ratio and key cardinality from day one.

## Handoffs

- Redis commands & data types → `data/redis`
- Engine-specific perf → `data/postgresql` / `data/mongodb` / `data/sqlserver` / etc.
- Migration of cache key shape → bump version prefix; the rest follows TTL
- Observability for hit ratio / latency → `observability/dashboards` + `observability/queries`
