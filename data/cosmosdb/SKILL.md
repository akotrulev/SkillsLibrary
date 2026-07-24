---
name: data-cosmosdb
description: Use when designing containers / partition keys, setting up clients, securing an account (Entra data-plane RBAC, CMK), planning migrations, writing queries, or tuning Azure Cosmos DB from a .NET / Java / Node backend. Triggers: "design a Cosmos container", "pick a partition key", "RU/s tuning", "autoscale vs provisioned vs serverless", "passwordless Cosmos with Entra ID". Do NOT use for relational stores, Mongo Atlas (`data/mongodb`), or DynamoDB (`data/dynamodb`).
---

# Data — Azure Cosmos DB (NoSQL API)

Container & partition key design, client setup, migrations, queries, and RU/s tuning for Azure Cosmos DB with the **NoSQL (Core) API** as the default. The MongoDB API is referenced where it differs; the Cassandra API is out of scope for this skill.

## Stack defaults

- **Cosmos DB NoSQL API** as the default (most idiomatic for new apps) — the API family is fixed at account creation and is immutable (see the API-family caveat under Security)
- **.NET 10**: `Microsoft.Azure.Cosmos` v3 — singleton `CosmosClient` per app
- **Java 21**: `com.azure:azure-cosmos` v4 (async/reactor + sync facades)
- **Node 24 + TypeScript**: `@azure/cosmos` v4
- Auth: **Microsoft Entra ID + data-plane RBAC** (passwordless, no keys in apps) — `DefaultAzureCredential`; disable local (key) auth on the account. Master keys only as a legacy fallback, Key-Vault-stored + rotated
- Capacity: **Autoscale** for prod containers, **Serverless** for dev/test or unpredictable spikes
- Consistency: **Session** is the default; bump to **Bounded Staleness** for multi-region writes, **Strong** rarely
- Partition keys: single key by default; **hierarchical (subpartition) keys** — now GA, up to 3 levels, new containers only — when one attribute can't be both high-cardinality and the hot filter

## When to use

- Container & partition-key design driven by access patterns and RU economics
- API choice — NoSQL (Core), MongoDB API (Mongo wire-compat), Cassandra API — and the trade-offs
- SDK setup with the singleton client + connection mode
- Capacity mode (autoscale vs provisioned vs serverless)
- Change feed + Azure Functions for downstream pipelines
- Consistency levels (Strong / Bounded staleness / Session / Consistent prefix / Eventual)
- Performance tuning (RU per query, hot partition, indexing policy customization)

## When NOT to use

- Relational engines → `data/postgresql` / `data/sqlserver` / `data/mysql`
- Mongo Atlas / self-hosted Mongo → `data/mongodb`
- Cache / KV → `data/redis`
- AWS-native NoSQL → `data/dynamodb`

## Inputs needed

1. **API** — NoSQL (default), MongoDB API (only when wire-protocol compat is required), Cassandra (rare)
2. **Workload shape** — read/write ratio, item size, multi-region writes (Y/N)
3. **Backend stack** for SDK choice
4. **Capacity expectation** — predictable steady? spiky? scale-to-zero acceptable?
5. **Access patterns** — every read/write, with cardinality + latency targets

## Container & partition-key design

### Partition key first

Cosmos DB containers are partitioned. The partition key determines:

- **Even distribution** of data and load (avoid hot partitions)
- **Query efficiency** (single-partition queries are cheap; cross-partition queries cost more RU)
- **20 GB logical partition limit** (a single PK value cannot exceed 20 GB of storage)

Rules of thumb:

- High **cardinality** (many distinct values) — `tenantId` for B2B; `customerId` for B2C; `orderId` for orders-by-id workloads
- **Distribution** roughly even across values; never a value that 80% of items share
- **Filter** matches PK on the hot read pattern (so most reads are single-partition)

When no single attribute satisfies all three, use a **synthetic** PK or **hierarchical partition keys** (now GA — up to 3 levels, set at container creation only):

```
Synthetic (one string key):   pk = "tenant#<tenantId>#date#<YYYY-MM>"
Hierarchical (real subkeys):   ["/tenantId", "/customerId", "/orderMonth"]
```

Prefer **hierarchical** over a hand-concatenated synthetic key when the levels are natural: a query that supplies a prefix (just `tenantId`, or `tenantId`+`customerId`) still routes to the right physical partitions instead of fanning out, and each full-key logical partition escapes the 20 GB cap. Hierarchical keys can only be defined on a **new** container — you cannot retrofit them, so decide at design time.

### Container shape

```json
{
  "id": "order-1234",
  "type": "order",
  "pk": "tenant#42#date#2026-05",
  "tenantId": "42",
  "customerId": "cus_alice",
  "status": "Paid",
  "totalMinor": 9999,
  "currency": "EUR",
  "placedAt": "2026-05-28T10:00:00Z",
  "_etag": "..."
}
```

Single-container, multi-entity design is common in Cosmos NoSQL (like DynamoDB single-table). Discriminate by a `type` field; use the partition key to scope to one tenant / customer.

### Indexing policy

Default policy indexes every property — convenient but **expensive at write time**. For high-write workloads, customize:

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [{ "path": "/tenantId/?" }, { "path": "/status/?" }, { "path": "/placedAt/?" }],
  "excludedPaths": [{ "path": "/*" }]
}
```

Cuts write RU dramatically when items have many properties you never query on.

## Connections (per stack)

### .NET 10

```csharp
builder.Services.AddSingleton(_ =>
{
    var endpoint = builder.Configuration["Cosmos:Endpoint"]!;
    var creds = new DefaultAzureCredential();             // Entra ID: Managed Identity in Azure, dev creds locally
    return new CosmosClient(endpoint, creds, new CosmosClientOptions
    {
        ConnectionMode = ConnectionMode.Direct,           // Direct TCP > Gateway in throughput
        Serializer = new CosmosSystemTextJsonSerializer(),
        ApplicationName = "orders-api",
        ConsistencyLevel = ConsistencyLevel.Session
    });
});

builder.Services.AddSingleton(sp =>
    sp.GetRequiredService<CosmosClient>().GetContainer("orders-db", "orders"));
```

`CosmosClient` is thread-safe and expensive; create **one per process** and reuse.

### Java 21

```java
CosmosClient client = new CosmosClientBuilder()
    .endpoint(System.getenv("COSMOS_ENDPOINT"))
    .credential(new DefaultAzureCredentialBuilder().build())
    .preferredRegions(List.of("West Europe"))
    .consistencyLevel(ConsistencyLevel.SESSION)
    .directMode()
    .buildClient();
```

### Node 24 + TypeScript

```typescript
import { CosmosClient } from '@azure/cosmos';
import { DefaultAzureCredential } from '@azure/identity';

export const cosmos = new CosmosClient({
  endpoint: process.env.COSMOS_ENDPOINT!,
  aadCredentials: new DefaultAzureCredential(),
  connectionPolicy: { preferredLocations: ['West Europe'] },
  consistencyLevel: 'Session',
});

export const orders = cosmos.database('orders-db').container('orders');
```

## Security & IAM

Cosmos DB has **two independent auth models** and **two independent RBAC planes** — the common mistake is conflating them.

- **Keys (local auth)** — the account's primary/secondary master keys and resource tokens. Powerful, long-lived, hard to scope, and a standing liability. Treat as legacy.
- **Microsoft Entra ID** — passwordless, per-identity, auditable, revocable. The default for new apps.

And two RBAC planes that do **not** overlap:

- **Control-plane RBAC** (Azure RBAC roles like *Cosmos DB Account Reader*, *Contributor*) governs **management** — creating containers, changing throughput, reading keys. It does **not** grant access to the data inside.
- **Data-plane RBAC** governs reading/writing **items**. Historically this was Cosmos's own native role system (built-in *Cosmos DB Built-in Data Reader* / *Data Contributor*, assigned via `az cosmosdb sql role assignment`). As of 2026 these data actions are also surfaced in the standard **Azure RBAC** role UI (*Cosmos DB Data Reader* / *Cosmos DB Data Contributor*), so a data-plane grant looks like any other Azure role assignment.

> A principal with *Contributor* on the account can read the **keys** and thereby the data — unless you disable local auth. Control-plane power is a data-plane backdoor until keys are off.

### Go passwordless, then lock the door

1. Assign the app's managed identity a **data-plane** role (Built-in Data Reader for read-only services, Data Contributor for writers) scoped as narrowly as the model allows (account → database → container).
2. Authenticate with `DefaultAzureCredential` (already in the samples above) — no key in config anywhere.
3. Set **`disableLocalAuth = true`** on the account. Now every request must carry an Entra token; any request using an account key is **rejected**. This is the difference between "we use Entra" and "keys can't be used" — a genuine **zero-key** account where every access is a named, auditable, revocable identity.
4. Enforce it in policy: the built-in Azure Policy *"Cosmos DB database accounts should have local authentication methods disabled"* flags/denies accounts that leave keys enabled.

Note the tooling cost: with local auth off, the **Azure Portal Data Explorer** needs your Entra identity to hold a data-plane role too, or it can't show items.

### Network isolation

- **Private endpoints** (Private Link) — the account gets a private IP in your VNet; combine with disabled public network access so the data plane is unreachable from the internet.
- **IP firewall / VNet service endpoints** — coarser alternatives when Private Link isn't warranted; always at least restrict to known ranges rather than "all networks".
- TLS is enforced on the wire by the service; nothing to configure app-side beyond trusting the CA.

### Encryption at rest — service-managed vs CMK

At-rest encryption is **always on**. Default keys are Microsoft-managed. For key custody / compliance / a revoke switch, configure **customer-managed keys (CMK)** backed by Azure Key Vault (or Managed HSM): Cosmos wraps its data-encryption keys with your Key Vault key, and revoking the key or its access renders the account unreadable. CMK must be set at **account creation** for the NoSQL API — you cannot retrofit it — so decide up front. Use a Key Vault access policy / RBAC grant for the Cosmos service principal and enable key auto-rotation.

### API-family caveat (do not conflate with `data/mongodb`)

An account's **API is chosen at creation and is immutable**: NoSQL (Core), MongoDB API, Cassandra API, Gremlin, or Table. This skill covers the **NoSQL API** — the idiomatic, fully-featured target for new apps, and the only one that gets the newest features (hierarchical keys, the full data-plane RBAC story, change feed) first.

- **MongoDB API** is a wire-protocol **compatibility layer** — it speaks the Mongo protocol so existing Mongo drivers/tools connect, but it is Cosmos underneath (RU billing, Cosmos partitioning, a subset of Mongo operators). Choose it only to lift-and-shift an existing Mongo app onto Azure without rewriting the data layer. It is **not** MongoDB — for real MongoDB (Atlas or self-hosted, `$lookup`, full aggregation, Queryable Encryption) use `data/mongodb`.
- **Cassandra / Gremlin / Table** APIs are likewise compatibility surfaces for those ecosystems and out of scope here.

The partition-key, RU, consistency, and security guidance in this skill is written for the **NoSQL API**; the Mongo-API surface differs (e.g. it exposes Mongo-style auth and indexing), so don't apply NoSQL recipes to it blind.

## Migrations / schema evolution

Like Mongo and Dynamo, no `ALTER`. Patterns:

- **Add property** — write new items with it; tolerate missing in read code
- **Rename / restructure** — dual-write + backfill via change feed-driven Function + cutover read path + remove old
- **Change partition key** — new container + change feed migration + cutover (treat as a rebuild)
- **Indexing policy changes** — applied online; reindexing runs in the background

Use the **change feed** as the universal migration channel — same primitive as Mongo's change streams and Dynamo Streams.

## Queries

### Cosmos SQL (NoSQL API)

```sql
SELECT c.id, c.status, c.totalMinor
FROM c
WHERE c.tenantId = @tenantId AND c.status = 'Paid'
ORDER BY c.placedAt DESC
OFFSET 0 LIMIT 20
```

- **Always include the partition key** in the `WHERE` clause for single-partition queries; otherwise it's a **cross-partition query** (slower, more RU)
- `ORDER BY` requires the property to be in the indexing policy
- `OFFSET / LIMIT` works but has cost — prefer continuation tokens for pagination

### Reads

- **Point reads** (`container.item(id, pk).read()`) are the cheapest operation (1 RU for a 1 KB item); use for `GetById`
- **Queries** use 2.5+ RU depending on complexity, projection size, and index hits
- Use **continuation tokens** for paging; don't `OFFSET 10000`

### Conditional writes & ETag

```typescript
await orders.item(id, pk).replace(updatedItem, {
  accessCondition: { type: 'IfMatch', condition: existingEtag },
});
```

`_etag` is Cosmos's optimistic concurrency token — read the item, modify, write back with `If-Match: <etag>`.

### Transactions

**Transactional batches** within one partition key (up to 100 ops). Cross-partition transactions are not supported in the NoSQL API.

## Change feed

Long-lived processor with Azure Functions or a managed change-feed processor library. Use cases:

- Materialize a derived container (denormalization)
- Fan out to Service Bus / Event Grid
- Backfills, migrations, audit
- Search index updates (push to Cognitive Search)

```csharp
// Azure Function with Cosmos Trigger
[Function("OrderChangeFeed")]
public Task Run(
    [CosmosDBTrigger(databaseName: "orders-db", containerName: "orders",
                     Connection = "Cosmos", LeaseContainerName = "leases", CreateLeaseContainerIfNotExists = true)]
    IReadOnlyList<OrderDoc> orders) { /* ... */ }
```

## Capacity & RU/s

| Mode | When |
|---|---|
| **Autoscale** (provisioned, max RU/s, min = 10%) | Default production; predictable budget with spike headroom |
| **Provisioned** (fixed RU/s) | Steady, predictable workload; rare in modern usage |
| **Serverless** (per-request billing, cap 1M RU/s, 50 GB) | Dev/test, bursty, low-volume; not for large prod |

Container-level vs database-level RU sharing:

- **Container-level RU**: dedicated capacity; one container's traffic doesn't starve another
- **Database-level RU**: shared across containers in the database; cheaper for many small containers but contention possible

Pick **container-level RU per workload** unless you have many small low-traffic containers.

## Consistency

| Level | When |
|---|---|
| **Strong** | Single-region writes; read-your-writes guaranteed everywhere; lowest write availability across regions |
| **Bounded Staleness** | Multi-region writes with bounded lag (K versions or T time); audit-style reads |
| **Session** (default) | Reads within the same session see writes; the right default for most apps |
| **Consistent Prefix** | Writes seen in order; rare |
| **Eventual** | Anything goes; cheapest reads; use only when truly eventual is fine |

Session consistency is the right default. Bump to Strong only when you've measured the need.

## Rules

- One `CosmosClient` per process — singleton
- Always include the partition key in queries from app code
- Indexing policy explicit on production containers — don't ship the "index everything" default unless writes are infrequent
- ETag-based optimistic concurrency on every write that competes with another writer
- Entra ID + data-plane RBAC for auth, `DefaultAzureCredential`; then **`disableLocalAuth = true`** for a zero-key account — master keys only as a legacy fallback, Key-Vault-stored + rotated
- Data-plane role for item access is separate from control-plane Azure roles — grant the data-plane role explicitly, scoped as narrowly as possible
- Private endpoint + public network access disabled for production accounts; CMK at account creation where key custody is required
- Autoscale for prod containers
- Change feed processed via Azure Functions or the SDK's hosted processor with a separate leases container
- Container-level RU per workload class
- Point reads (`item().read()`) for `GetById` — cheapest op
- Session consistency the default; document any deviation

## What NOT to do

- No master keys in app config or env vars — go passwordless and disable local auth
- No assuming a control-plane Contributor role can't read your data — it can read the keys unless local auth is off
- No expecting to change an account's API family or add a CMK / hierarchical partition key after creation — all three are creation-time only
- No cross-partition queries on hot paths — design the PK around the access pattern
- No `SELECT * FROM c` without a `WHERE c.partitionKey = @pk` in production code
- No `Strong` consistency as the default — measure first
- No "index everything" policy on a high-write container
- No more than one `CosmosClient` per process
- No partition keys with low cardinality (e.g., `status` with 4 values)
- No items > 2 MB (hard limit) — split or move to Blob Storage with the pointer in the item
- No long-lived change-feed processors that don't checkpoint — they'll re-process on every restart
- No production workloads on Serverless above ~50 GB or sustained > 1k RU/s — graduate to Autoscale

## Generation steps

1. Confirm API choice (NoSQL is the default), workload shape, access patterns, multi-region needs.
2. Design partition key from access patterns — single-partition reads dominant.
3. Generate IaC (Bicep / Terraform) for the database + container with autoscale RU, partition key (hierarchical where the levels are natural), indexing policy, TTL, change feed, **`disableLocalAuth = true`, the data-plane role assignment for the app identity, a private endpoint, and CMK if key custody is required** (CMK + API + hierarchical keys are all creation-time).
4. Generate the singleton client setup and a typed repository per logical entity.
5. Smoke locally with the Cosmos emulator; replay access patterns; confirm queries are single-partition and within RU budget.

## Handoffs

- Cross-engine query patterns → `data/_shared/query-optimization`
- Caching → `data/_shared/caching-patterns` + `data/redis`
- Schema evolution → `data/_shared/migrations`
- Azure deployment for the account / change-feed-driven Azure Functions → cloud provisioning / IaC for the store itself has no owning skill in this library yet; out of this domain's scope
- Observability — diagnostic settings → Log Analytics; Cosmos metrics in Azure Monitor → `observability/*` skills (via the `observability-engineer-{dotnet,java,node}` peer bundled in the matching `be-*` plugin)
