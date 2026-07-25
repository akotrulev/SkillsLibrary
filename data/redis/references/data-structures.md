# Redis — Data Structures

Picking the right native structure, the atomic operations that make Redis useful, hash-field TTL, big-key discipline, and the modules now bundled into Redis 8 core. Which *application pattern* to build on top (rate limiter, lock, queue) is `references/patterns.md`; the caching *strategy* is `data/_shared/caching-patterns`.

## The one rule that governs all of them: bound the size

Redis is **single-threaded for command execution**. Any command that touches a huge value (a 100 MB hash, a million-element list) blocks *every other client* for the duration. So the governing rule for every structure below is: **bound its size, and reach for the O(1)/O(log N) operations, not the O(N) ones.** A "big key" is the most common Redis performance incident.

## Choosing a structure

| Structure | Model | Reach for it when | Key ops |
|---|---|---|---|
| **String** | Bytes / number / serialized blob | Cache-aside value, counter, flag, token | `SET`/`GET`, `INCR`/`INCRBY`, `SET … EX NX` |
| **Hash** | Field→value map under one key | Object with independently-updated fields; session; per-field TTL (7.4+) | `HSET`/`HGET`, `HINCRBY`, `HEXPIRE` |
| **List** | Ordered, dup-allowing, push/pop ends | Simple FIFO/LIFO queue, capped recent-items | `LPUSH`/`RPOP`, `LMOVE`, `LTRIM`, `BRPOP` |
| **Set** | Unordered unique members | Membership, dedupe, tags, relations | `SADD`, `SISMEMBER`, `SINTER`/`SUNION` |
| **Sorted set (ZSET)** | Members ranked by score | Leaderboard, priority queue, sliding-window log, time index | `ZADD`, `ZRANGEBYSCORE`, `ZREMRANGEBYSCORE`, `ZRANK` |
| **Stream** | Append-only log + consumer groups | Durable-ish queue with ack/replay/DLQ | `XADD`, `XREADGROUP`, `XACK`, `XAUTOCLAIM` |
| **Bitmap** (on String) | Bit array | Compact per-id booleans (daily-active flags) | `SETBIT`, `BITCOUNT`, `BITOP` |
| **HyperLogLog** | Probabilistic cardinality | "Roughly how many unique X" at tiny memory (~12 KB) | `PFADD`, `PFCOUNT` |
| **Geo** (on ZSET) | Lon/lat points | Radius / nearest queries | `GEOADD`, `GEOSEARCH` |

Pick by **access pattern**, not by what's convenient to serialize. If you only ever read/write the whole object → a `String` of JSON is fine. If fields update independently or need their own TTL → a `Hash`. If you rank/range by a score → a `ZSET`.

## Strings — the cache-aside default & atomic counters

The default cache value type. Two idioms carry most of the weight:

```bash
SET v1:order:123 "<json>" EX 300 NX     # set with 5-min TTL only if absent (NX) — the lock/idempotency primitive
INCR rl:user:7:1699999999               # atomic counter — rate limiting, sequence
```

`INCR`/`INCRBY`/`DECR` are atomic — no read-modify-write race. Never `GET` → parse → `+1` → `SET` in app code; use `INCR`.

## Hashes & hash-field TTL (7.4+)

A hash groups related fields under one key so you can update or read one field without rewriting the whole object (`HSET`/`HGET`/`HINCRBY`). **From 7.4, individual fields can expire independently** — before 7.4, TTL is per-key only.

```bash
HSET v1:cart:42 item:abc 2 item:xyz 1
HINCRBY v1:cart:42 item:abc 3           # atomic per-field increment
HEXPIRE v1:cart:42 900 FIELDS 1 item:abc   # 7.4+: expire just this field in 15 min
```

Redis 8 adds atomic combinations — **`HGETEX`** (get + set/clear expiry), **`HSETEX`** (set + expiry in one), **`HGETDEL`** (get + delete). On < 7.4 you cannot expire a single field: model each independently-expiring item as its own key instead (router version table).

Keep hashes bounded — a hash with millions of fields is a big key. Split by a sub-namespace if it grows.

## Sorted sets — leaderboards, priority queues, sliding windows

The most versatile structure. Score-ordered, so it does ranking, range-by-score, and time-window work in O(log N):

```bash
ZADD leaderboard 4200 player:7            # score = points
ZREVRANGE leaderboard 0 9 WITHSCORES      # top 10
# sliding-window rate limit: score = timestamp
ZADD rl:user:7 1699999999 req:uuid
ZREMRANGEBYSCORE rl:user:7 0 (now-window) # drop entries older than the window
ZCARD rl:user:7                           # count remaining = requests in window
```

This is the backbone of the sliding-window rate limiter and priority queue in `references/patterns.md`.

## Streams — the durable-ish queue

When you need consumer groups, acknowledgement, replay, and dead-letter behavior, **Streams** outclass a `LIST`:

```bash
XADD orders '*' customerId 42 totalMinor 9999
XREADGROUP GROUP order-workers worker-1 COUNT 10 BLOCK 5000 STREAMS orders '>'
XACK orders order-workers <id>
XAUTOCLAIM orders order-workers worker-2 60000 0   # reclaim messages a dead worker never ACKed
```

- `MAXLEN`/`MINID` trimming (`XADD … MAXLEN ~ 100000`) is mandatory — an untrimmed stream grows forever (a big key by another name).
- Unacked messages sit in the Pending Entries List; `XAUTOCLAIM` is your DLQ/redelivery mechanism.
- Streams are a good in-app middle ground; for cross-system, ordered, exactly-once-ish at scale, use a real broker (router handoff).

## The bundled modules (Redis 8 core; Redis Stack ≤ 7.x; Valkey has its own)

Redis 8 folds the former Redis Stack modules **into core** — no separate install:

- **Query Engine / Search** (`FT.*`) — secondary indexing + full-text + **vector similarity** over hashes/JSON. The in-Redis alternative to scanning keys; also the vector-search path for RAG caches.
- **JSON** (`JSON.*`) — store/update/query JSON documents atomically at a path (`JSON.SET k $.field v`) instead of get-parse-set whole strings.
- **Time Series** (`TS.*`) — downsampling, retention, aggregation for metrics.
- **Probabilistic** — Bloom/Cuckoo (set membership at tiny memory), Count-Min, Top-K, t-digest.
- **Vector sets** — native vector similarity structure.

Version/flavor fences: on **7.x** these need Redis Stack installed separately (many managed tiers don't have them). On **Valkey**, the equivalent modules are the Foundation's own BSD-licensed builds and lag/differ — detect and check before using a `FT.*`/`JSON.*` command. Don't assume they exist.

## Big-key discipline

- Inspect with `redis-cli --bigkeys` and `MEMORY USAGE <key>`; alert on outliers.
- Cap collections proactively: `LTRIM` lists, `XADD MAXLEN` streams, shard oversized hashes/sets by a sub-key.
- Delete large keys with **`UNLINK`** (async, non-blocking), never `DEL` (synchronous, blocks on free).
- Never `SMEMBERS`/`HGETALL`/`LRANGE 0 -1` a key that could be large — use `SSCAN`/`HSCAN`/cursored reads.

## What NOT to do

- No unbounded structure (untrimmed stream/list, ever-growing hash/set) — that's a big key.
- No `KEYS`, `SMEMBERS`, `HGETALL`, `LRANGE 0 -1` on potentially large keys in prod — use `SCAN`/`SSCAN`/`HSCAN`.
- No `DEL` on a large key — `UNLINK`.
- No read-modify-write for counters — `INCR`/`HINCRBY`/`ZINCRBY`.
- No assuming `FT.*`/`JSON.*`/`TS.*` exist on 7.x-without-Stack or on Valkey — detect first.
- No JSON-blob string when fields update independently (rewrites the whole value) — use a hash or JSON module.

## Handoffs

- Building a rate limiter / lock / queue / session on these structures → `references/patterns.md`
- TTL as a mandatory rule + eviction interaction → the router + `references/operations.md`
- Which caching strategy wraps the value → `data/_shared/caching-patterns`
- Vector search beyond a cache → `pgvector` on the Postgres you already run (`data/postgresql/references/indexing.md`) if the embeddings belong to relational data; `data/elasticsearch` / a dedicated vector store when you need relevance/hybrid ranking, independent scaling, or non-Postgres data
