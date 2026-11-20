---
name: dynamodb
description: Use when designing, securing or tuning Amazon DynamoDB (access patterns, single-table design, GSIs, capacity). Triggers "design a DynamoDB table", "set up a GSI". Not for Cosmos DB (cosmosdb).
disable-model-invocation: true
---

# Data — DynamoDB

Single-table design driven by access patterns, capacity model, indexes, streams, transactions, and tuning for Amazon DynamoDB from the three backend stacks. The mental shift compared with SQL: **model access patterns first, schema second**.

## Stack defaults

- **DynamoDB** in a single AWS region (Global Tables when multi-region active-active is required)
- **.NET 10**: **AWS SDK for .NET v4** (`AWSSDK.DynamoDBv2` 4.x); the Object Persistence model for typed entities + low-level `IAmazonDynamoDB` for transactions and complex queries
- **Java 21**: AWS SDK v2 (`software.amazon.awssdk:dynamodb-enhanced` + `dynamodb`)
- **Node 24 + TypeScript**: AWS SDK v3 — `@aws-sdk/client-dynamodb` + `@aws-sdk/lib-dynamodb` 3.x (`DynamoDBDocumentClient`)
- Capacity: **On-demand** unless you've measured a stable, predictable load that pays for provisioned + autoscaling
- Identity: IAM roles via IRSA (EKS) / Task Role (ECS) / instance profile — **no access keys in apps**
- Encryption at rest is **always on**; choose the key ownership tier deliberately (`references/security-iam.md`)
- Caching: **DAX** in front of Dynamo for sub-ms reads when the workload justifies it; otherwise Redis or in-process

### SDK version note — AWS SDK for .NET v4 (breaking vs v3)

On **v4** (the .NET 10 default):

- **DynamoDB Streams moved out** of `AWSSDK.DynamoDBv2` into its own package `AWSSDK.DynamoDBStreams` — add it explicitly if you consume Streams from the app.
- Construct the context via **`DynamoDBContextBuilder`**; the old public `DynamoDBContext` constructors that implicitly `DescribeTable` are obsoleted (they cost a call + IAM permission per type).
- `DynamoDBOperationConfig` is split into operation-specific `SaveConfig` / `LoadConfig` / `QueryConfig` / `ScanConfig`.
- New `ITable` / `IDocumentBatchWrite` / `IDocumentBatchGet` interfaces make the Document model mockable — use them in tests instead of hitting DynamoDB Local for pure-mapping logic.

Version-aware rule: on a project still on SDK v3 / .NET 8–9, keep the v3 shapes (single `AWSSDK.DynamoDBv2` package, `DynamoDBContext` ctor, `DynamoDBOperationConfig`). Never up-level a down-level project.

## Inputs needed

1. **Enumerated access patterns** — every read/write the application must serve, with cardinality and latency targets
2. **Workload shape** — read/write ratio, peak vs steady, item size distribution
3. **Multi-region / multi-account** scope (Global Tables needed?)
4. **Backend stack** for SDK + client choice
5. **Item lifecycle** — TTL eligibility, archival to S3 via Streams

## Single-table design

DynamoDB is built around a **single table per service** (sometimes per microservice), modeled around access patterns. You **do not** map one logical entity to one table the way you would in SQL — you map many entity types into a shared table with overloaded PK / SK.

### Step 1 — List access patterns

Write them down before any schema:

| # | Access pattern | Cardinality | Latency target |
|---|---|---|---|
| AP1 | Get order by orderId | 1 | < 10ms p99 |
| AP2 | List orders for customer, newest first, paginated | 0–100 | < 50ms p99 |
| AP3 | Get all order lines for an order | 1–50 | < 30ms p99 |
| AP4 | List orders by status (paid, pending) in a date range | 0–1000 | < 200ms p99 |
| AP5 | Lookup customer by external partner id | 1 | < 10ms p99 |

You will design the table to make every AP a **`GetItem` or `Query`** — never a `Scan`.

### Step 2 — Pick PK / SK and GSIs

```
PK              SK                              Type     Other attributes
CUST#<custId>   PROFILE                         Customer name, email, partnerId
CUST#<custId>   ORDER#<placedAt>#<orderId>      Order    status, totalMinor, currency
ORDER#<orderId> ORDER                           Order    customerId, status, totalMinor
ORDER#<orderId> LINE#<lineNo>                   Line     sku, qty, priceMinor
```

GSIs (Global Secondary Indexes) for the patterns the base table can't serve:

```
GSI1 — Status + date range
  GSI1PK = STATUS#<status>
  GSI1SK = <placedAt>#<orderId>

GSI2 — Customer external partner id
  GSI2PK = PARTNER#<partnerId>
  GSI2SK = <custId>
```

### Step 3 — Map each AP to a base-table or GSI query

| AP | Query |
|---|---|
| AP1 Get order by id | `GetItem(PK=ORDER#<id>, SK=ORDER)` |
| AP2 List orders for customer | `Query(PK=CUST#<id>, SK begins_with ORDER#)` |
| AP3 Get all lines for an order | `Query(PK=ORDER#<id>, SK begins_with LINE#)` |
| AP4 List by status + date | `Query(GSI1, PK=STATUS#<status>, SK between ...)` |
| AP5 Customer by partner id | `Query(GSI2, PK=PARTNER#<partnerId>)` |

If you can't reduce every AP to a `Query` / `GetItem`, the table model is wrong. Iterate.

### Step 4 — Index types

- **Local Secondary Index (LSI)** — alternative sort key for the same PK. Limited (5 per table), must be created at table creation, eventually consistent reads only.
- **Global Secondary Index (GSI)** — independent PK/SK; eventually consistent reads only.
- Prefer GSIs for new design; LSIs are vestigial.

### Step 5 — Sort key patterns

- **Timestamp prefix** (`<ISO8601>#<id>`) for newest-first listings via `ScanIndexForward=false`
- **Type prefix** (`ORDER#`, `LINE#`) for hierarchical reads (parent + children) in one query
- **Composite numeric padding** (`PRIORITY#003#TS#...`) when range filtering needs lexical ordering of numbers — pad with zeros

## Connections and security

- **Client setup**: a stack in the task → read `references/connections.md` (.NET 10, Java 21, Node 24 sections). One client per process.
- **IAM, tenant isolation, KMS key tier, PITR, backups, TLS or global tables** → read `references/security-iam.md`. IAM is the entire authorization surface; there are no database users or `GRANT`.

## Migrations / schema evolution

DynamoDB schemas don't have ALTER TABLE in the SQL sense. Migration patterns:

- **Add attribute** — Just start writing the new attribute. Old items don't have it. Tolerate missing in read code.
- **Rename attribute** — Dual-write to old + new for one release; backfill via a Streams-driven Lambda or a one-off scan-and-update job; switch reads to new; remove old.
- **Change PK / SK shape** — New table + Streams + Lambda to dual-write + bulk migration job + cutover. Treat as a rebuild.
- **Add GSI** — Online operation; takes minutes to hours depending on table size. Cost is real.
- **Remove GSI** — Online; free except for the storage.

Always set **TTL** on items that are ephemeral (sessions, events, idempotency keys). Items are deleted (eventually) at no cost; Streams fire on TTL deletion.

## Queries & writes

### `GetItem` / `Query` / `Scan`

- **`GetItem`** — single item by full PK (+ SK for tables with sort key). Cheap.
- **`Query`** — items sharing the same PK, optionally filtered by SK condition. The bread-and-butter operation.
- **`Scan`** — full-table read. Forbidden in normal application code. Acceptable for batch migrations / analytics with `Segment` parallelization.

### Conditional writes for idempotency

```typescript
await ddb.send(new PutCommand({
  TableName: 'orders',
  Item: { PK: `ORDER#${id}`, SK: 'ORDER', status: 'pending' },
  ConditionExpression: 'attribute_not_exists(PK)',
}));
```

The write throws `ConditionalCheckFailedException` when the item already exists.

Idempotency keys: use a partition + SK pair like `IDEMP#<requestId>` with TTL, conditional-write `attribute_not_exists` — DynamoDB enforces single-execution semantics.

### Transactions

`TransactWriteItems` allows ACID across up to 100 items / 4 MB. Use sparingly — twice the cost of regular writes and limited to 100 items.

### Pagination

Every `Query` / `Scan` returns up to 1 MB; use `LastEvaluatedKey` / `ExclusiveStartKey` to page. Wrap in a helper that yields pages, not items, so the app handles backoff per page.

## Capacity & cost

| Mode | When |
|---|---|
| **On-demand** | New workloads, spiky / unpredictable traffic, dev/test, anything sub-100 req/s sustained |
| **Provisioned + autoscaling** | Predictable, sustained workload where the cost math beats on-demand |

On-demand is the default — it scales instantly, no capacity planning, slightly more expensive per request but no idle cost. Switch to provisioned when load is stable and analysis shows savings.

**Hot partitions** are the #1 perf trap. Symptoms: throttling on `Query` / `Update` despite low total RCUs/WCUs used. Diagnosis: enable **Contributor Insights** on the table or GSI; find the hot key; redesign the PK (add a shard suffix `#<rand[0..N]>` if the access pattern allows fan-out reads).

**DAX** (DynamoDB Accelerator) — write-through cluster cache that returns sub-ms reads. Adds operational complexity; reach for it only when the workload demands it.

## Streams & change capture

Enable Streams (`NEW_AND_OLD_IMAGES` or `NEW_IMAGE`) and trigger Lambda to:

- Project into S3 / Athena for analytics
- Fan out events to SQS / SNS / EventBridge
- Maintain a derived "outbox" or search index
- Run TTL-deletion handlers (TTL deletes appear in the stream)

Streams give you Mongo-style change feeds; combine with Lambda for serverless reactive pipelines. On **AWS SDK for .NET v4**, consuming Streams from application code (not Lambda) needs the separate `AWSSDK.DynamoDBStreams` package — it's no longer bundled in `AWSSDK.DynamoDBv2`.

## Rules

Each rule is stated nowhere else in this file.

- Keep each item under 1 KB where possible (400 KB is the hard limit); store large blobs in S3 and put the key in the item.
- Model relationships into the table by denormalizing and dual-writing, with Streams keeping copies consistent; a hot path never joins client-side across tables.
- Give every item type under a shared PK a type-discriminator field.
- Bound item growth: split an ever-growing list or large attribute into more items, or store it in S3.
- Read eventually consistent by default; use a strongly consistent read only where the access pattern needs it, since it costs more and may fail during failover.
- Add a GSI for a named access pattern; each one costs storage and a write per item.
- Store keys (PK, SK, GSI keys) as strings: string-encoded ULIDs and ISO timestamps, never `Number` unless the whole app treats them numerically.
- Use short attribute names (`pk`, `sk`, `s`, `n`) when storage cost matters at scale, and document the mapping.
- Rely on DynamoDB's at-rest encryption; add app-side encryption only against a named threat model, since it restricts queries.

## Generation steps

1. Enumerate the access patterns with the user, with cardinality and latency targets. Done when every pattern is in the AP table; schema design waits for it.
2. Design PK / SK and GSIs. Done when every access pattern maps to one `GetItem` or `Query` row.
3. Generate IaC (CDK or Terraform) for the table. Done when the IaC plan lists PITR, the key tier (CMK where required), billing mode, TTL, Streams settings and a per-ARN least-privilege policy (`LeadingKeys` for tenant isolation where applicable).
4. Generate the typed client setup for the chosen stack. Wrap it in a repository only when a second store or a test seam needs it. Done when the client reads the table through the stack's connection pattern in `references/connections.md`.
5. Smoke locally with DynamoDB Local or LocalStack. Done when the AP list is replayed against the schema and every read is a `Query` or `GetItem` in the trace.
