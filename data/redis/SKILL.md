---
name: data-redis
description: Use for Redis (or Valkey) as a cache, rate limiter, distributed lock, queue, session store, leaderboard, or pub/sub from a .NET / Java / Node backend — engine mechanics, data structures, ACL/TLS security, persistence, replication/cluster, and eviction. Triggers: "set up Redis caching", "pick a Redis data type", "implement a rate limiter", "Redis ACL / TLS", "RDB vs AOF", "Redis cluster", "eviction policy", "Valkey vs Redis". Pick the topic in the routing table, then read its reference file end-to-end. The cross-engine caching *strategy* catalog (pattern choice, key design, stampede, TTL tiers) is `data/_shared/caching-patterns`; this skill owns the Redis *mechanics*. Do NOT use for a primary system of record, full-text search (`data/elasticsearch` / Atlas Search), or durable exactly-once messaging at scale (Kafka/Service Bus — broker selection/implementation has no owning skill in this library yet; `qa/<stack>/skills/messaging-testing` only *tests* an existing broker).
---

# Data — Redis / Valkey

One registered skill, four topic references. This file routes and holds the shared rules: version/flavor policy, connections, the "second-tier store" framing, and the hard rules (mandatory TTL, one client per process). **Read the matching `references/<topic>.md` end-to-end before writing any code.** Topics split by concern — a task may need two (a rate-limited API = `patterns.md` + `operations.md`).

Redis is a **second-tier store** in front of a system of record — never the sole store. The strategic question "what caching pattern, what key, what TTL" is answered by `data/_shared/caching-patterns`; this skill answers "which Redis structure, which command, how to run it safely."

## Routing table

| Read | Use when |
|------|----------|
| `references/data-structures.md` | Picking a data type (string/hash/list/set/sorted-set/stream/bitmap/HLL/geo/probabilistic/vector), atomic ops, hash-field TTL, big-key discipline, the bundled modules (Search/JSON/TimeSeries) |
| `references/patterns.md` | Rate limiting, distributed locks, idempotency/dedupe, sessions, queues (LIST vs Streams + consumer groups), pub/sub vs Streams — the Redis-command implementations of application patterns |
| `references/security.md` | ACL users & rules, TLS, `protected-mode`, command renaming/disabling, network isolation, secrets, the no-`KEYS`-in-prod rule |
| `references/operations.md` | Persistence (RDB vs AOF), replication + Sentinel, cluster mode & hash slots, eviction policies, memory management, pipelining, keyspace notifications, monitoring |

## Version & flavor policy — Redis 8.x primary, 7.2/7.4 supported; Valkey is a real fork

First act: **detect the server and flavor** (`redis-cli INFO server` → `redis_version` / `server_name`; Valkey reports `valkey`). Key guidance to it.

- **Redis 8.x primary** (8.0 GA May 2025). Ships the former **Redis Stack modules bundled into core** — Query Engine/Search, JSON, Time Series, probabilistic types (Bloom/Cuckoo/Count-Min/Top-K/t-digest), and **vector sets** — no separate module install (`references/data-structures.md`).
- **7.2 / 7.4 supported fallback.** **7.4** stabilized **hash-field TTL** (`HEXPIRE`/`HTTL`/…). Before 7.4, TTL is per-key only (no per-field expiry) — tag that fallback.
- **Eviction default is still `noeviction`** — you must set `maxmemory` + a policy explicitly (`references/operations.md`).

| Redis 8.x construct | 7.2 / 7.4 fallback |
|---|---|
| Bundled Search/JSON/TimeSeries/Bloom/vector-sets in core | install Redis Stack modules separately (or don't have them) |
| `HGETEX` / `HSETEX` / `HGETDEL` (atomic get+expire / get+delete on hash fields) | `HEXPIRE`+`HGET` (7.4), or per-key only (< 7.4) |
| Hash-field TTL (`HEXPIRE`, `HTTL`, `HPERSIST`) | **7.4+ only** — below that, model the TTL'd item as its own key |

### The Valkey fork (like MariaDB is to MySQL — call it out)

When Redis moved to source-available RSALv2/SSPL in 2024, the community forked **Valkey** (from Redis 7.2.4), now governed by the **Linux Foundation** under the permissive **BSD-3-Clause** license. Redis 8 later re-added an **AGPLv3** option (Redis 8 is tri-licensed AGPLv3 / RSALv2 / SSPL). Consequences to flag:

- **They have genuinely diverged** — Valkey 9 has its own hash-field-expiry, large-cluster scaling, and BSD-licensed JSON/Search/vector modules; command sets and roadmaps no longer track 1:1. Don't assume a Redis-8-only command exists on Valkey (and vice versa) — detect and check.
- **Managed services** increasingly default to Valkey (AWS ElastiCache/MemoryDB offer Valkey; it's cheaper). The wire protocol is compatible, so **your client and the patterns in this skill work on both** — but pin and test against the flavor you actually run.
- **License matters if you embed/redistribute.** For a normal server-side cache you consume over the network, AGPLv3 (Redis 8) and BSD (Valkey) are both fine; if legal wants a permissive license, that's a point for Valkey.

Treat "Redis" throughout as "Redis or a protocol-compatible Valkey"; where a command is flavor/version-specific, `references/*` says so.

## Stack defaults (align with CLAUDE.md)

- **.NET 10** (8/9 supported): `StackExchange.Redis` **3.x** — one shared `ConnectionMultiplexer` (thread-safe, owns its own multiplexing). App-cache abstraction via `Microsoft.Extensions.Caching.StackExchangeRedis` (`IDistributedCache`).
- **Java 21 + Spring Boot 3.x**: `spring-boot-starter-data-redis` on **Lettuce** (default; async/reactive-capable, Redis-8-aware) — Jedis only when blocking simplicity wins.
- **Node 24 + TypeScript**: **`node-redis`** (the actively-developed, MIT client — recommended for new work, full Redis 8 feature support). `ioredis` is stable but maintenance-mode; keep it only on existing projects that depend on its cluster/sentinel ergonomics.
- **Deployment**: replica + automatic failover (Sentinel or the managed service); **cluster mode only when memory or throughput genuinely needs it** (`references/operations.md`).

## Inputs needed

1. **Use case** — cache / lock / rate limiter / queue / sessions / leaderboard / pub-sub (routes to `patterns.md`)
2. **Server + flavor + version** — Redis 8 vs 7.x vs Valkey (gates hash-field TTL, bundled modules)
3. **Hosting** — ElastiCache/MemoryDB, Azure Cache/Managed Redis, Upstash, self-hosted; standalone vs cluster
4. **Backend stack** — client choice
5. **Sizing** — keyspace size, peak ops/sec, largest value, eviction tolerance
6. **Consistency tolerance** — can reads be slightly stale, or must they reflect the latest write?

## Connections (per stack)

**One client per process, reused** — the client owns its own connection multiplexing/pool. Never construct per request. Pub/sub subscribers need a **separate** connection (a subscribed connection can't serve normal commands).

### .NET 10

```csharp
builder.Services.AddSingleton<IConnectionMultiplexer>(_ =>
    ConnectionMultiplexer.Connect(new ConfigurationOptions
    {
        EndPoints = { builder.Configuration["Redis:Host"]! },
        Password = builder.Configuration["Redis:Password"],   // from env/Key Vault
        Ssl = true,
        AbortOnConnectFail = false,
        ConnectRetry = 5,
        ConnectTimeout = 5000,
    }));
builder.Services.AddSingleton(sp =>
    sp.GetRequiredService<IConnectionMultiplexer>().GetDatabase());
```

### Java 21 + Spring Boot

```yaml
spring:
  data:
    redis:
      host: ${REDIS_HOST}
      port: 6379
      password: ${REDIS_PASSWORD}
      ssl:
        enabled: true
      lettuce:
        pool: { max-active: 16, max-idle: 8, min-idle: 2 }
        shutdown-timeout: 200ms
```

Add `spring-boot-starter-cache` + `@EnableCaching` for `@Cacheable`/`@CacheEvict` (read-through with less boilerplate — the pattern is still cache-aside, `_shared/caching-patterns`).

### Node 24 + TypeScript

```typescript
import { createClient } from 'redis';           // node-redis (recommended)

export const redis = createClient({
  url: process.env.REDIS_URL,                     // rediss://… for TLS
  socket: { tls: true, reconnectStrategy: (r) => Math.min(r * 50, 2000) },
});
redis.on('error', (e) => logger.error({ err: e }, 'redis error'));
await redis.connect();
```

## Rules

- **Every key has a TTL. No exceptions.** A TTL-less key is a memory leak (`SET k v EX <s>`, or `EXPIRE`/`HEXPIRE` after write). The only exception is a dedicated bucket under a documented eviction policy — and you document why.
- One client per process, reused; a **separate** connection for pub/sub subscribers.
- **Versioned, namespaced keys** — `v1:tenant:42:user:7` (key design is owned by `_shared/caching-patterns`; follow it).
- **Bound every aggregate** (hash/list/set/sorted-set) you write to — big keys block the single-threaded server (`references/data-structures.md`).
- **`SCAN`, never `KEYS`, in production**; `UNLINK` over `DEL` for large keys (async free).
- **TLS on the wire** (`rediss://`) to any managed/remote Redis; auth via **ACL user** (not just `requirepass`) in a secret store (`references/security.md`).
- **Write to the system of record first, then invalidate** the cache; invalidate with `UNLINK`/`DEL`, never `SET` the new value.
- Set `maxmemory` + an explicit eviction policy — never run with the implicit default and no cap (`references/operations.md`).
- Separate logical DB or instance per workload class (cache vs session vs queue) so an eviction event can't wipe sessions.
- Keep Lua scripts short — Redis is single-threaded; script time is server-wide stall time.

## What NOT to do

- No Redis as the only store of record.
- No key without a TTL (outside a documented, eviction-policied bucket).
- No unbounded hash/list/set/sorted-set (a 100 MB value stalls the event loop on access).
- No `KEYS *` — ever — in production.
- No "write cache then DB" (cache becomes the source of truth on failure).
- No `MULTI/EXEC` for *performance* (it's for atomicity) — pipeline instead.
- No long-running Lua; no synchronous blocking calls on the shared connection.
- No assuming pub/sub delivery (offline subscribers miss messages) — use Streams / a real broker when delivery must be guaranteed.
- No cache logic scattered across the codebase — one cache-aside helper per entity.
- No running without `maxmemory` set (OOM kill / swap death).

## Generation steps

1. Confirm use case, flavor/version, hosting, stack, consistency tolerance.
2. Pick the pattern (`_shared/caching-patterns` for the *strategy*; `references/patterns.md` for the Redis *implementation*).
3. Pick the data structure (`references/data-structures.md`).
4. Generate the singleton client + a small typed helper for the pattern (e.g. `OrderCache.getOrLoad(id)`), with TTL + versioned key + invalidation hooks on the write path.
5. Set security (ACL user, TLS) and operational config (maxmemory/eviction/persistence) per `references/security.md` + `references/operations.md`.
6. Smoke with `redis-cli MONITOR` / `--bigkeys` to verify keys, TTLs, and sizes behave under load.

## Handoffs

- Caching **strategy** (pattern choice, key namespace, TTL tiers, stampede, negative caching, multi-level) → `data/_shared/caching-patterns`
- Systems of record Redis fronts → `data/postgresql` · `data/mongodb` · `data/sqlserver` · `data/mysql`
- Durable/ordered/at-scale messaging beyond Streams → a real broker (Kafka / Service Bus / SQS); broker selection/implementation has no owning skill in this library yet, and `qa/<stack>/skills/messaging-testing` only *tests* an existing broker
- Hit-ratio / key-count / latency telemetry → `observability/*` skills (via the `observability-engineer-{dotnet,java,node}` peer bundled in the matching `be-*` plugin)
- Load/soak behavior under cache pressure → `qa/<stack>/skills/performance/*`
