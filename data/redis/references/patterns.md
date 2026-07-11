# Redis — Application Patterns

The Redis-command implementations of the patterns Redis is reached for: rate limiting, distributed locks, idempotency/dedupe, sessions, queues, and pub/sub. These are the *mechanics*; the caching **strategy** (cache-aside vs read-through vs write-behind, key namespace, TTL tiers, stampede protection, negative caching) is owned by `data/_shared/caching-patterns` — read it for the "which pattern and why," come here for the commands.

Examples use `node-redis` syntax; the structure translates directly to `StackExchange.Redis` and Lettuce.

## Cache-aside (the mechanics)

The default. `_shared/caching-patterns` owns the strategy; here's the correct command shape:

```typescript
async function getOrder(id: string): Promise<Order | null> {
  const key = `v1:order:${id}`;
  const hit = await redis.get(key);
  if (hit) return JSON.parse(hit);

  const order = await db.orders.findOne({ _id: id });
  if (order) await redis.set(key, JSON.stringify(order), { EX: jitter(300) }); // TTL always
  return order;
}

async function updateOrder(id: string, patch: Partial<Order>): Promise<void> {
  await db.orders.updateOne({ _id: id }, { $set: patch });  // system of record FIRST
  await redis.unlink(`v1:order:${id}`);                     // then invalidate (UNLINK, not SET)
}
```

Non-negotiables (enforced across the skill): write to the source of record first; invalidate with `UNLINK`/`DEL`, never `SET` the new value (avoids the old-clobbers-new race); every key carries a jittered TTL.

## Rate limiting

### Fixed window (simplest, atomic)

```typescript
async function allowFixed(userId: string, limit = 100, windowSec = 60): Promise<boolean> {
  const key = `rl:${userId}:${Math.floor(Date.now() / 1000 / windowSec)}`;
  const n = await redis.incr(key);
  if (n === 1) await redis.expire(key, windowSec);   // TTL on first hit of the window
  return n <= limit;
}
```

Cheap and atomic, but allows up to **2× the limit at a window boundary** (burst at the end of one window + start of the next).

### Sliding-window log (tighter, ZSET)

Store one member per request scored by timestamp; trim the window; count what remains. Do it in one atomic Lua script or a `MULTI` so the trim+count+add can't interleave:

```
ZREMRANGEBYSCORE rl:user:7 0 (now-windowMs)   # drop old
ZADD rl:user:7 now uuid                         # record this request
ZCARD rl:user:7                                 # count in window → compare to limit
EXPIRE rl:user:7 windowSec                       # mandatory TTL
```

More memory (a member per request) but no boundary burst. For a middle ground, the **token-bucket** algorithm as a small Lua script gives smooth rate + burst allowance at O(1) memory.

## Distributed lock

For the simple single-instance case, `SET NX EX` + a compare-and-delete release:

```typescript
const token = crypto.randomUUID();
const ok = await redis.set(`lock:${key}`, token, { NX: true, EX: 30 });  // acquire, auto-expiring
if (!ok) return; // someone else holds it
try {
  await doExclusiveWork();
} finally {
  // release ONLY if we still own it — atomic compare-and-delete via Lua
  await redis.eval(
    `if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) else return 0 end`,
    { keys: [`lock:${key}`], arguments: [token] });
}
```

- The **auto-expiring TTL** is the safety net if the holder crashes; the **token + compare-and-delete** stops you releasing a lock that already expired and got re-acquired by someone else.
- For multi-node correctness under failover, the real **Redlock** algorithm exists — but weigh whether you need it. Most "I need a lock" cases are better solved by an **idempotent operation** or a **DB row lock**; a Redis lock is a performance optimization, not a correctness guarantee across a partition.

## Idempotency / dedupe

`SET NX` as a claim check — the webhook/at-least-once-delivery guard:

```typescript
const claimed = await redis.set(`idemp:webhook:${id}`, '1', { NX: true, EX: 86_400 });
if (!claimed) return;    // already processed within the last 24h
await processWebhook();
```

The TTL sets the dedupe horizon (how far back you remember). Size it to your delivery retry window.

## Sessions

JSON session keyed by an opaque token, **sliding TTL** — `EXPIRE` on every access so active users stay logged in and idle ones age out:

```typescript
const s = await redis.get(`sess:${token}`);
if (s) await redis.expire(`sess:${token}`, 1800);   // slide 30-min window on access
```

`.NET`: use `IDistributedCache` (`Microsoft.Extensions.Caching.StackExchangeRedis`). **Java**: `spring-session-data-redis`. Put sessions on a **separate logical DB/instance** with `noeviction` so a cache eviction storm can't log everyone out (router rule).

## Queues

- **Simple FIFO** — `LPUSH` + blocking `BRPOP` (or `BLMOVE` into a processing list for reliability). Fine for best-effort, no ack/replay.
- **Reliable** — **Streams** with consumer groups (`XADD`/`XREADGROUP`/`XACK`, `XAUTOCLAIM` for redelivery). Use when you need ack, replay, and DLQ semantics. See `references/data-structures.md` for the commands and mandatory `MAXLEN` trimming.
- Beyond in-app scale (ordered, durable, cross-system, exactly-once-ish) → a real broker (router handoff), not Redis.

## Pub/sub vs Streams

- **`PUBLISH`/`SUBSCRIBE`** is **fire-and-forget** — subscribers offline at publish time miss the message; no replay, no ack. Right for ephemeral fan-out (live presence, cache-invalidation hints where a missed message self-heals on TTL). Subscribers need a **dedicated connection** (router rule).
- When "must deliver / can replay" matters, use **Streams** (or a broker). Don't build reliable messaging on plain pub/sub.

## What NOT to do

- No cache write before the system-of-record write; no `SET`-the-new-value as invalidation.
- No fixed-window limiter where a 2× boundary burst is unacceptable — use sliding-window/token-bucket.
- No lock release without the token compare-and-delete (you'll release someone else's lock).
- No treating a single-node Redis lock as a correctness guarantee across failover — prefer idempotency / DB locks.
- No sessions on the same instance/policy as an LRU cache (eviction logs users out).
- No reliable-delivery expectations on plain pub/sub.
- No blocking pop on the shared multiplexed connection in a way that starves other commands — use the client's blocking-connection support correctly.

## Handoffs

- Which caching strategy/key/TTL wraps these mechanics → `data/_shared/caching-patterns`
- The underlying structures (ZSET/Stream/Hash) and their limits → `references/data-structures.md`
- Eviction policy per workload (why sessions ≠ cache) & persistence → `references/operations.md`
- Locking/ACL to run these safely → `references/security.md`
- Durable cross-system messaging → messaging brokers (router handoff)
