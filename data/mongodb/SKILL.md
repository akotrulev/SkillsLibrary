---
name: data-mongodb
description: Use when designing collections/documents, modeling relationships (embed vs reference mechanics), securing data (auth/roles/field-level encryption), writing queries or aggregation pipelines, choosing indexes, caching, or tuning performance on MongoDB from a .NET / Java / Node backend. Triggers: "design a Mongo collection", "write an aggregation pipeline", "this Mongo query is slow", "add an index", "queryable encryption", "embed or reference?", "set up the Mongo client". Pick the topic in the routing table, then read its reference file end-to-end. Do NOT use for relational engines (`data/postgresql` / `data/sqlserver` / `data/mysql`), Redis (`data/redis`), DynamoDB/Cosmos DB (their skills), cross-engine modeling decisions (`data/_shared/schema-design`), or writing DB tests (`qa/<stack>/skills/db-testing`).
---

# Data — MongoDB

One registered skill, five topic references. This file routes and holds the rules shared by every topic: version policy, connections/pooling, migration discipline, and the hard rules. **Read the matching `references/<topic>.md` end-to-end before writing any code.** These split by *topic*, not by tool — a task may need two files (a new field-encrypted collection = `data-modeling.md` + `security.md`).

## Routing table

| Read | Use when |
|------|----------|
| `references/data-modeling.md` | New collections/documents, embed-vs-reference **mechanics**, the extended-reference / computed / bucket patterns, schema validators (`$jsonSchema`), the 16 MB ceiling, `_id` strategy, time-series collections |
| `references/security.md` | Auth (SCRAM / x.509 / Entra-AWS-IAM), built-in vs custom roles, **CSFLE vs Queryable Encryption**, TLS, network isolation, auditing |
| `references/indexing.md` | Choosing or fixing indexes, the ESR rule, compound/multikey/partial/TTL/wildcard, covered queries, `$text` vs Atlas Search / Vector Search, index build discipline |
| `references/performance.md` | Slow ops, `.explain('executionStats')`, working-set/WiredTiger cache, aggregation-pipeline tuning, read/write concern, the profiler, sharding |
| `references/caching.md` | Change streams for invalidation, summary/rollup collections (materialized-view analog), read-preference-as-cache, the external Redis seam |

## Version policy — MongoDB 8.0 primary, 7.0 supported

First act on an existing database: **detect the server version** (`db.version()` or the `buildInfo` command) and key every recipe to it. Never apply an 8.0-only construct to a down-level server; never flag a down-level server for lacking one.

- **8.0 = current Major/LTS** (GA Oct 2024, supported to Oct 2029) — recommend for new work, Atlas and self-managed.
- **7.0 = supported fallback** (previous LTS). 6.0 is older LTS, upgrade-only.
- **Rapid releases (8.1 Atlas-only, 8.2+) are NOT for production self-hosting** — pin on-prem to the 8.0 LTS line. Atlas runs newer.

| 8.0 construct | 7.0 fallback |
|---|---|
| Queryable Encryption **range** queries GA (equality GA since 7.0) | QE equality only; range needs 8.0 |
| `$lookup` inside a transaction against **sharded** collections | unsharded only, or restructure |
| Faster resharding / online resharding at scale | plan a maintenance window |
| Time-series aggregation/query speedups (config-only, no API change) | n/a |

**Atlas vs self-hosted is a real fence.** **Atlas Search** and **Atlas Vector Search** are GA but are *Atlas platform* features (backed by managed `mongot`), **not** in the Community/self-managed server. On self-hosted, full-text search is the built-in `$text` index (limited) — say so and route serious search off-engine. See `references/indexing.md`.

## Stack defaults (align with CLAUDE.md)

- **.NET 10** (8/9 supported): `MongoDB.Driver` **3.x** (async API only; the 2.x sync/`...Async` split is gone).
- **Java 21 + Spring Boot 3.x**: `spring-boot-starter-data-mongodb` on the Mongo Java driver **5.x**.
- **Node 24 + TypeScript**: official `mongodb` driver **6.x**; Mongoose only when its schema/validation layer earns its weight (the driver + `$jsonSchema` validators usually suffice).
- **Replica set, always** — even a single-node dev cluster runs as a 1-member replica set so transactions and change streams work.
- **Migrations**: Mongock (Java/Spring), `migrate-mongo` (Node), or a hand-rolled idempotent runner recording applied scripts in a `_migrations` collection (.NET). Mongo has no native migration engine.

## Inputs needed

1. **Server version + platform** (Atlas vs self-managed — gates Search/Vector Search, some ops features)
2. **Topology**: single replica set vs sharded cluster
3. **Backend stack** (.NET / Java / Node) — determines driver + migration tool
4. **Workload shape**: read-heavy, write-heavy, mixed; point lookups vs full-collection aggregations
5. **Document size + growth** — drives embed-vs-reference, bucketing, time-series, sharding
6. **Tenancy + sensitivity** — multi-tenant isolation and whether fields need CSFLE/QE (routes to `references/security.md`)

## Connections (per stack)

Register **one client per process** and reuse it — the driver owns its own connection pool. Never `new` a client per request.

### .NET 10

```csharp
var settings = MongoClientSettings.FromConnectionString(
    builder.Configuration.GetConnectionString("Mongo")); // mongodb+srv://…, from env/Key Vault
settings.ApplicationName = "orders-api";
settings.MaxConnectionPoolSize = 100;
settings.RetryWrites = true;
settings.ReadConcern = ReadConcern.Majority;
settings.WriteConcern = WriteConcern.WMajority;

var client = new MongoClient(settings);
builder.Services.AddSingleton<IMongoClient>(client);
builder.Services.AddSingleton(sp =>
    sp.GetRequiredService<IMongoClient>().GetDatabase("orders"));
```

### Java 21 + Spring Boot

```yaml
spring:
  data:
    mongodb:
      uri: mongodb+srv://app:${MONGO_PASSWORD}@cluster.mongodb.net/orders?retryWrites=true&w=majority&readConcernLevel=majority
      auto-index-creation: false     # a migration owns indexes, never app start-up
```

### Node 24 + TypeScript

```typescript
import { MongoClient, ServerApiVersion } from 'mongodb';

const client = new MongoClient(process.env.MONGO_URI!, {   // from env/Secrets Manager
  serverApi: { version: ServerApiVersion.v1, strict: true, deprecationErrors: true },
  maxPoolSize: 100,
  retryWrites: true,
  w: 'majority',
});
await client.connect();
export const db = client.db('orders');
```

Pool sizing: 100 is the driver default; size to the deployment (50–200 typical). Server-side connections are capped by file descriptors — many app instances × large pools exhausts the server before the app.

## Migrations

Mongo has no native migration engine, so pick one tool per stack and use it consistently. Rules:

- **Every migration is idempotent.** Creating a unique index or backfilling twice must not throw or double-apply — guard with existence checks / `upsert` / a query that excludes already-migrated docs.
- **Backfills run in batches** (`updateMany` filtered to un-migrated docs), never one statement over millions of rows — there is no cross-collection transaction to lean on.
- **Index builds are online by default** on modern versions but state it; for very large collections use a **rolling build** across replica-set members (`references/indexing.md`).
- **Validator tightening is expand-contract**: deploy code that writes the new shape → backfill old docs → then raise `validationLevel`/`validationAction`. Never flip a validator to `strict/error` before the data conforms.
- Universal expand-contract pattern + tool table → `data/_shared/migrations`.

## Rules

- One driver client per process, reused — never per request.
- Schema validator (`$jsonSchema`, `validationAction: 'error'`) on every production collection (`references/data-modeling.md`).
- Every collection has the indexes its queries need, **declared in a migration** — never `auto-index-creation` / app-startup index creation.
- Connection URIs + credentials in env / Key Vault / Secrets Manager; TLS on the wire; `sslmode`-equivalent `tls=true` for self-hosted, always on for `+srv`.
- BSON `Date` for timestamps (store UTC), integer minor units (`NumberLong`) for money — never strings, never floats for money.
- Consistent `_id` strategy per project — driver `ObjectId` by default, or a UUIDv7 string when you need external-system meaningful ids; never store the same value as both `_id` and a second field.
- **Always project** (no `find({})` bare) and **always `.limit(n)`** on array-returning queries.
- Read concern `majority` + write concern `w:'majority'` for anything that must survive failover; relax only for explicitly low-value events.
- Multi-document transactions only when genuinely needed — they are per-replica-set with real overhead; most "I need a transaction" cases are a modeling fix (embed the related data).
- Parameterize/bind values through the driver's query builder — never string-concatenate a query or `$where` JavaScript.

## What NOT to do

- No `find({})` without a projection; no query without a `.limit(n)`.
- No unbounded growing array embedded in a document (order → "every event ever") — bucket or promote to a child collection (`references/data-modeling.md`).
- No `$lookup` against a large **unindexed** collection — Mongo is not a relational engine; heavy multi-collection joins mean the wrong store or the wrong model.
- No `$where` / server-side JS in queries (injection + no index use).
- No `String` for dates or money; no double/float for money.
- No app-driven index creation at startup; no `auto-index-creation: true`.
- No app role with `dbAdmin`/`clusterAdmin` — runtime is `readWrite` on its own database only (`references/security.md`).
- No `mongoexport`/`mongorestore` as the production backup strategy — use Atlas snapshots / `mongodump`-to-managed-snapshot with PITR.
- No sharding as a starting point — most "Mongo is slow" is a missing index or a fat document, not a shard-key decision.
- No denormalized copy without a documented backfill/repair path for when it drifts (it will).

## Generation steps

1. Detect version + platform (Atlas vs self-managed), topology, stack, workload, tenancy — confirm what can't be detected.
2. Route: read the matching reference file(s) end-to-end before writing anything.
3. New collection → design the document (embed vs reference **mechanics** here; the *choice* is `_shared/schema-design`), draft the `$jsonSchema` validator, list indexes by the ESR rule, write the idempotent migration.
4. Slow op → `.explain('executionStats')` on representative data; identify COLLSCAN / over-fetch / in-memory SORT; smallest fix first (`references/performance.md`).
5. Validate against a seeded dataset; smoke the hot queries via the matching `qa/<stack>/skills/db-testing` peer.

## Handoffs

- Cross-engine modeling decisions (embed-vs-reference *choice*, id strategy, money, soft-delete, tenancy pattern) → `data/_shared/schema-design`
- Expand-contract pattern + migration tool selection → `data/_shared/migrations`
- Cache-aside/stampede/TTL pattern catalog → `data/_shared/caching-patterns` + `data/redis`
- Universal query triage (ESR, N+1, pagination) → `data/_shared/query-optimization`
- Testing the schema/queries (seed/assert/clean, Testcontainers, safe queries) → `qa/{java,dotnet,typescript}/skills/db-testing/*`
- Tenant/user claims feeding access control → `auth/auth0-{stack}` + `auth/_shared/auth0-concepts`
- Query-latency telemetry → `observability/*` skills (via the `observability-engineer-{dotnet,java,node}` peer bundled in the matching `be-*` plugin)
- Relational / KV equivalents → `data/postgresql` · `data/sqlserver` · `data/mysql` · `data/redis`
