# Redis — Operations

Persistence (RDB vs AOF), replication + Sentinel, cluster mode & hash slots, eviction policies, memory management, pipelining, keyspace notifications, and monitoring. This is the "how to run it so it doesn't fall over" layer — engine mechanics, distinct from the application patterns (`references/patterns.md`) and the caching strategy (`data/_shared/caching-patterns`).

## Persistence: RDB vs AOF

Redis is in-memory; persistence is how it survives a restart. Two mechanisms, often combined:

| | **RDB** (snapshot) | **AOF** (append-only log) |
|---|---|---|
| What | Point-in-time fork-and-dump of the dataset | Every write command appended to a log, replayed on start |
| Durability | Lose everything since the last snapshot (minutes) | Lose ≤ 1 s with `appendfsync everysec` (the default); near-zero with `always` (slow) |
| Restart speed | Fast (load one compact file) | Slower (replay the log) |
| File size | Small | Larger; needs periodic rewrite/compaction |
| Use for | Backups, fast restore, replicas | Stronger durability requirement |

Guidance by workload:

- **Pure cache** (data reconstructable from the system of record): you may run with **persistence off** — a cold cache after restart just re-warms. Cheapest, and eviction is expected anyway.
- **Sessions / queues / anything you can't reconstruct**: enable persistence — **AOF `everysec`** for the durability floor, and RDB snapshots for fast restore/backups. Managed tiers expose this as a durability tier; pick the one matching the workload class.
- Combine both (RDB + AOF): fast restore from RDB with AOF filling the gap. Redis 7+ uses a multi-part AOF that makes rewrites cheaper.
- **Snapshots and AOF files contain the whole keyspace in plaintext** — encrypt at rest and guard backups (`references/security.md`).

## Eviction — configure it explicitly

The default `maxmemory` is unbounded and the default policy is **`noeviction`** — meaning a server with no cap will consume memory until the OOM killer takes it, and a server with a cap but `noeviction` starts **rejecting writes** when full. Neither is what a cache wants. **Always set `maxmemory` and an explicit policy.**

| Policy | Behavior | Use for |
|---|---|---|
| `allkeys-lru` | Evict least-recently-used of any key | **General cache** (default choice) |
| `allkeys-lfu` | Evict least-frequently-used | Cache with a stable hot set (better hit ratio than LRU for skewed access) |
| `volatile-lru` / `volatile-lfu` / `volatile-ttl` | Evict only keys **with a TTL** | Mixed instance where some keys must never be evicted |
| `noeviction` | Reject writes when full | **Sessions / queues** — data loss unacceptable; you'd rather fail the write |

This is why the router insists on a **separate instance/logical DB per workload class**: a cache instance runs `allkeys-lru`, a session/queue instance runs `noeviction` — you can't serve both correctly with one policy. Target memory usage ≤ ~60–70%; above ~80% with fragmentation you risk swap death. Set `maxmemory` explicitly; watch `used_memory` / `mem_fragmentation_ratio` / `evicted_keys` in `INFO`.

## Replication & failover (Sentinel)

- A **replica** (`REPLICAOF`) gets an async copy of the primary — read scaling and a warm standby, but **asynchronous** (a failover can lose the last writes not yet replicated).
- **Sentinel** monitors primary+replicas and performs automatic failover + client discovery. The self-hosted HA answer below cluster scale.
- **Managed services** (ElastiCache/MemoryDB, Azure) do failover for you — you consume an endpoint. Prefer this over hand-rolling Sentinel.
- Because replication is async, **never treat a replica read as read-after-write consistent**, and don't assume a lock or counter survives a failover unmodified (`references/patterns.md` — prefer idempotency).

## Cluster mode — only when you must

**Cluster mode only when one node's memory or throughput genuinely can't cope** — it adds real constraints:

- The keyspace is sharded across **16384 hash slots**; each key maps to a slot by CRC16. A **multi-key command only works if all keys are in the same slot** — force it with **hash tags**: `{tenant:42}:user:7` and `{tenant:42}:cart:7` share the slot for `tenant:42`, so you can `MGET`/transaction/Lua across them.
- No cross-slot `MULTI`/Lua/`MGET` without co-location — design keys with hash tags up front for anything you operate on together.
- The client must be cluster-aware (StackExchange, Lettuce, node-redis all are) to follow `MOVED`/`ASK` redirects.
- Prefer **vertical scaling + replicas** first; reach for cluster when a single primary's RAM/CPU is the wall. Valkey 9 pushes cluster scaling much higher if that's your constraint.

## Pipelining vs transactions vs Lua

Three different tools, often confused:

- **Pipelining** — send many commands without waiting for each reply; the server processes them back-to-back and returns all replies together. **The performance tool** — turns 100 round-trips into one. Use it whenever you have a batch of independent commands. Not atomic.
- **`MULTI`/`EXEC`** — queues commands and runs them **atomically** (no other client interleaves). The **atomicity tool**, not a performance tool — don't use it to batch for speed (that's pipelining).
- **Lua (`EVAL`)** — runs a script atomically server-side; use for read-modify-write logic that must be a single atomic step (token-bucket limiter, compare-and-delete unlock). **Keep scripts short** — Redis is single-threaded, so script time is server-wide stall time. No long loops, no unbounded key access inside a script.

## Keyspace notifications (event seam)

Redis can publish events when keys change or expire (`notify-keyspace-events`). Useful for reacting to expiry (e.g. "session key expired → clean up") — but note **expiry events are best-effort pub/sub** (a subscriber offline at the moment misses it), so don't build correctness on them; pair with a reconciliation pass. For reliable change-driven work, prefer a Stream you write to explicitly.

## Monitoring

- `INFO` sections: `memory` (`used_memory`, `mem_fragmentation_ratio`, `evicted_keys`, `maxmemory`), `stats` (`keyspace_hits`/`keyspace_misses` → hit ratio, `instantaneous_ops_per_sec`), `clients` (`connected_clients`, `blocked_clients`), `replication` (`master_link_status`, lag), `persistence` (last save, AOF status).
- **Hit ratio** = `hits / (hits + misses)`; a low ratio on a cache means bad keys or too-short TTLs (`_shared/caching-patterns`).
- `SLOWLOG GET` surfaces slow commands (usually a big-key O(N) op or a `KEYS`).
- `redis-cli --bigkeys` / `--memkeys` / `--latency`; `LATENCY DOCTOR` for latency spikes.
- **Never leave `MONITOR` running in production** — it streams every command and tanks throughput; it's a short debugging tool only.

## Rules

- `maxmemory` + an explicit eviction policy always; `allkeys-lru`/`lfu` for caches, `noeviction` for sessions/queues → separate instances per class.
- Persistence off is OK for a pure cache; on (AOF `everysec` + RDB) for anything unreconstructable; encrypt the files.
- Pipeline for throughput, `MULTI`/`EXEC` for atomicity, short Lua for atomic read-modify-write — don't mix up their jobs.
- Cluster only when a single node is the wall; design hash-tagged keys for any multi-key operation before enabling it.
- Replica/failover is async — no read-after-write off a replica, no lock/counter correctness assumption across failover.
- Monitor hit ratio, memory, evictions, replication lag; `SLOWLOG` for O(N) offenders; no `MONITOR` in prod.

## What NOT to do

- No running without `maxmemory` set (OOM) or with `noeviction` on a cache (write rejections).
- No one instance serving both an LRU cache and `noeviction` sessions.
- No AOF `always` unless the latency cost is justified; no persistence-off for data you can't rebuild.
- No cross-slot multi-key op in cluster mode without hash tags.
- No long-running Lua; no `MULTI/EXEC` used as a batching-for-speed tool.
- No correctness built on best-effort keyspace-expiry notifications.
- No `MONITOR` left running in production.

## Handoffs

- Bounding structures so O(N) ops and big keys don't stall the single thread → `references/data-structures.md`
- Why sessions need `noeviction` and locks are async-fragile → `references/patterns.md`
- Securing the persistence files, ACLs, TLS → `references/security.md`
- Hit-ratio/memory/latency dashboards → `observability/*` skills (via the `observability-engineer-{dotnet,java,node}` peer bundled in the matching `be-*` plugin)
- Behavior under sustained cache load → `qa/<stack>/skills/performance/*`
