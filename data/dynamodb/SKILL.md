---
name: data-dynamodb
description: Use when designing tables / access patterns, setting up clients, securing a table (fine-grained IAM, encryption, PITR), planning migrations, writing queries, or tuning Amazon DynamoDB from a .NET / Java / Node backend. Triggers: "design a DynamoDB table", "model an access pattern", "set up a GSI", "single-table design", "on-demand vs provisioned capacity". Do NOT use for relational stores, document stores with rich query (`data/mongodb`), Redis (`data/redis`), or Cosmos DB (`data/cosmosdb`).
---

# Data — DynamoDB

Single-table design driven by access patterns, capacity model, indexes, streams, transactions, and tuning for Amazon DynamoDB from the three backend stacks. The mental shift compared with SQL: **model access patterns first, schema second**.

## Stack defaults

- **DynamoDB** in a single AWS region (Global Tables when multi-region active-active is required)
- **.NET 10**: **AWS SDK for .NET v4** (`AWSSDK.DynamoDBv2` 4.x — GA Aug 2025); the Object Persistence model for typed entities + low-level `IAmazonDynamoDB` for transactions and complex queries
- **Java 21**: AWS SDK v2 (`software.amazon.awssdk:dynamodb-enhanced` + `dynamodb`)
- **Node 24 + TypeScript**: AWS SDK v3 — `@aws-sdk/client-dynamodb` + `@aws-sdk/lib-dynamodb` 3.x (`DynamoDBDocumentClient`)
- Capacity: **On-demand** unless you've measured a stable, predictable load that pays for provisioned + autoscaling
- Identity: IAM roles via IRSA (EKS) / Task Role (ECS) / instance profile — **no access keys in apps**
- Encryption at rest is **always on**; choose the key ownership tier deliberately (see Security & IAM)
- Caching: **DAX** in front of Dynamo for sub-ms reads when the workload justifies it; otherwise Redis or in-process

### SDK version note — AWS SDK for .NET v4 (breaking vs v3)

The current data samples pinned .NET 8 + SDK v3. On **v4** (the .NET 10 default):

- **DynamoDB Streams moved out** of `AWSSDK.DynamoDBv2` into its own package `AWSSDK.DynamoDBStreams` — add it explicitly if you consume Streams from the app.
- Construct the context via **`DynamoDBContextBuilder`**; the old public `DynamoDBContext` constructors that implicitly `DescribeTable` are obsoleted (they cost a call + IAM permission per type).
- `DynamoDBOperationConfig` is split into operation-specific `SaveConfig` / `LoadConfig` / `QueryConfig` / `ScanConfig`.
- New `ITable` / `IDocumentBatchWrite` / `IDocumentBatchGet` interfaces make the Document model mockable — use them in tests instead of hitting DynamoDB Local for pure-mapping logic.

Version-aware rule: on a project still on SDK v3 / .NET 8–9, keep the v3 shapes (single `AWSSDK.DynamoDBv2` package, `DynamoDBContext` ctor, `DynamoDBOperationConfig`). Never up-level a down-level project.

## When to use

- Single-table design driven by enumerated access patterns
- Partition / sort key choice; GSI / LSI design
- SDK setup (.NET v4 (v3 down-level) / Java v2 / Node v3) with the Document / Enhanced client
- Capacity mode (on-demand vs provisioned + autoscaling)
- DynamoDB Streams + Lambda for change capture
- TTL, conditional writes, `TransactWriteItems`
- Performance tuning (hot partition diagnosis, adaptive capacity, read consistency choice)

## When NOT to use

- Relational engines → `data/postgresql` / `data/sqlserver` / `data/mysql`
- Document store with rich query → `data/mongodb`
- Cache / KV / queue → `data/redis`
- Azure-native NoSQL → `data/cosmosdb`

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
- **Global Secondary Index (GSI)** — independent PK/SK; eventually consistent by default; strongly consistent via projection settings is not supported on GSIs.
- Prefer GSIs for new design; LSIs are vestigial.

### Step 5 — Sort key patterns

- **Timestamp prefix** (`<ISO8601>#<id>`) for newest-first listings via `ScanIndexForward=false`
- **Type prefix** (`ORDER#`, `LINE#`) for hierarchical reads (parent + children) in one query
- **Composite numeric padding** (`PRIORITY#003#TS#...`) when range filtering needs lexical ordering of numbers — pad with zeros

## Connections (per stack)

### .NET 10 (AWS SDK for .NET v4)

```csharp
builder.Services.AddAWSService<IAmazonDynamoDB>();        // credentials from IAM role
builder.Services.AddSingleton<IDynamoDBContext>(sp =>
    new DynamoDBContextBuilder()                          // v4: builder, not the obsoleted ctor
        .WithDynamoDBClient(() => sp.GetRequiredService<IAmazonDynamoDB>())
        .ConfigureContext(c =>
        {
            c.ConsistentRead = false;
            c.TableNamePrefix = builder.Configuration["Dynamo:TablePrefix"];
            c.DisableFetchingTableMetadata = true;         // no per-type DescribeTable call
        })
        .Build());
```

Use the high-level Object Persistence (`IDynamoDBContext`) for typed CRUD; drop to `IAmazonDynamoDB` for `TransactWriteItems`, conditional updates, batch ops. Set `DisableFetchingTableMetadata` (and declare keys via attributes) so the app needs no `dynamodb:DescribeTable` grant at runtime.

### Java 21

```java
DynamoDbClient ddb = DynamoDbClient.builder().region(Region.EU_WEST_1).build();
DynamoDbEnhancedClient enhanced = DynamoDbEnhancedClient.builder().dynamoDbClient(ddb).build();
DynamoDbTable<Order> table = enhanced.table("orders", TableSchema.fromBean(Order.class));
```

`TableSchema.fromBean` discovers `@DynamoDbBean` / `@DynamoDbPartitionKey` annotations.

### Node 24 + TypeScript (AWS SDK v3)

```typescript
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb';

const client = new DynamoDBClient({});                    // IAM role-resolved credentials
export const ddb = DynamoDBDocumentClient.from(client, {
  marshallOptions: { removeUndefinedValues: true, convertClassInstanceToMap: true },
});
```

Use the **DocumentClient** — it marshals JS objects to/from DynamoDB's `AttributeValue` wire format. Raw `DynamoDBClient` is rarely needed. One client + document client per process; both are cheap to share and expensive to recreate per request.

## Security & IAM

DynamoDB has no database users, roles, or `GRANT` — **IAM is the entire authorization surface**. Everything below is IAM policy plus a small amount of table configuration.

### Fine-grained (item- and attribute-level) access control

The headline capability: an IAM policy can restrict a principal to **only the items whose partition key matches the caller's identity**, and to **only a subset of attributes** — without any application code enforcing it. This is how you get real row-level multi-tenant isolation on a shared table.

- **`dynamodb:LeadingKeys`** (v2 alias **`FirstPartitionKeyValues`**) — restricts an operation to items whose **partition key** equals a value you bind to the caller's identity. Use with the **`ForAllValues:StringEquals`** set operator and a policy variable substituted from the identity (Cognito identity id, a SAML/OIDC claim, or a session tag).
- **`dynamodb:Attributes`** — whitelist the attributes a principal may read or write; pair with `dynamodb:Select = SPECIFIC_ATTRIBUTES` (reads) and `dynamodb:ReturnValues = NONE` (writes) so a caller can't exfiltrate columns by asking for `ALL_ATTRIBUTES`.

```json
{
  "Effect": "Allow",
  "Action": ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:UpdateItem"],
  "Resource": "arn:aws:dynamodb:eu-west-1:111122223333:table/app",
  "Condition": {
    "ForAllValues:StringEquals": {
      "dynamodb:LeadingKeys": ["${cognito-identity.amazonaws.com:sub}"]
    },
    "StringEquals": { "dynamodb:Select": "SPECIFIC_ATTRIBUTES" },
    "ForAllValues:StringEquals": {
      "dynamodb:Attributes": ["PK", "SK", "name", "status", "totalMinor"]
    }
  }
}
```

The classic delivery vehicle is the **Token Vending Machine**: the client authenticates, a broker returns short-lived STS credentials scoped by `LeadingKeys` to that user/tenant, and the client talks to DynamoDB directly — the data plane enforces isolation even if the app query is sloppy. Because the guarantee lives in IAM, it is exactly the kind of control the `qa-security` peer's **BOLA/IDOR** access-control matrix should verify: prove tenant A's credentials cannot read tenant B's partition.

**Caveat:** `LeadingKeys` only constrains the **partition key**, and only on operations that carry it (`GetItem`, `Query`, `BatchGetItem`, `PutItem`, `UpdateItem`, `DeleteItem`). It cannot scope a `Scan`, and it cannot filter by sort key — model the tenant boundary into the partition key or don't rely on this.

### Action / resource scoping

- Grant **per-table and per-index** ARNs, never `dynamodb:*` on `*`. Index actions need the index ARN: `.../table/app/index/GSI1`.
- Separate read vs write policies; most services need `GetItem`/`Query`/`BatchGetItem` far more than `PutItem`/`UpdateItem`.
- Deny `dynamodb:DeleteTable`, `dynamodb:*Backup*`, and PITR-disabling actions on the runtime role — those belong to an ops/IaC role.
- If the app declares keys via attributes (see the `.NET` note), it needs **no `dynamodb:DescribeTable`** grant.

### Encryption at rest — pick the key tier

At-rest encryption is **always enabled and cannot be turned off**; the only decision is who owns the key:

| Key tier | Use when | Notes |
|---|---|---|
| **AWS owned** (default) | No compliance requirement for key custody | Free, invisible, no CloudTrail on key use |
| **AWS managed** (`aws/dynamodb`) | You want key usage in CloudTrail with no key management | Free KMS key AWS rotates |
| **Customer managed (CMK)** | Compliance / audit / cross-account / "revoke by disabling the key" | You control rotation, grants, and CloudTrail; per-request KMS cost; **DynamoDB caches data keys** so it isn't per-item |

A CMK gives you the kill switch: disable the key and the table is instantly unreadable. Grant the runtime role `kms:Decrypt` (and `kms:GenerateDataKey` for writes) on that CMK. **In transit** is TLS by default — enforce it with an `aws:SecureTransport = true` condition and, in-VPC, a **gateway VPC endpoint** (`com.amazonaws.<region>.dynamodb`) so traffic never leaves the AWS network; scope the endpoint policy to the same table ARNs.

### Backup & recovery

- **PITR (point-in-time recovery)** — continuous backups, restore to any second in a rolling 35-day window. Turn it on for every table holding non-reconstructable data; it's the defense against a bad deploy or bulk delete. Restore creates a **new table** (you re-point the app), it never overwrites in place.
- **On-demand backups** — full snapshots you retain long-term (compliance holds) independent of the 35-day PITR window; via AWS Backup for cross-account/cross-region vaulting.

### Global tables (multi-region)

Global tables (current version `2019.11.21`) replicate a table across regions with **active-active, last-writer-wins** multi-region writes. They need PITR-grade discipline: identical IAM in each region, the CMK replicated per region (a CMK is regional — use a multi-region key or a per-region key), and app awareness that a write in one region is **eventually** visible in another. Reach for them only for genuine multi-region active-active or low-latency-global-reads requirements, not "for resilience" (a single-region table with PITR already survives an AZ loss).

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
  Item: { PK: `ORDER#${id}`, SK: 'ORDER', /* ... */ },
  ConditionExpression: 'attribute_not_exists(PK)',
}));
// Throws ConditionalCheckFailedException if the item already exists
```

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

- Single-table design per service; **never** "one table per entity" except in the simplest CRUD apps
- Access patterns enumerated before schema design
- Every read is `GetItem` or `Query` — never `Scan` in app code
- Item size budget per record (1 KB typical, 400 KB hard limit); store large blobs in S3 and put the key in the item
- TTL on every ephemeral entity (sessions, idempotency keys, transient events)
- Conditional writes for idempotency / optimistic concurrency
- IAM least-privilege — per-table, per-GSI grants; never `dynamodb:*` on `*`; split read vs write policies
- Multi-tenant isolation enforced in IAM via `LeadingKeys` (partition-key = identity), not just in app code — and QA'd with a cross-tenant BOLA test
- PITR on every table holding non-reconstructable data; a CMK when key custody / a revoke switch is required
- Enforce TLS (`aws:SecureTransport`) and keep in-VPC traffic on a gateway VPC endpoint
- Item attributes use short names (`pk`, `sk`, `s`, `n`) when storage cost matters at scale — readability vs. cost trade-off; document the mapping
- All keys typed: PK / SK / GSI keys are always strings (use string-encoded ULIDs / ISO timestamps), never `Number` unless the entire app treats them numerically

## What NOT to do

- No `Scan` in application code paths
- No client-side joins across tables in a hot path — model the relationship into the table
- No relational thinking ("FK to customers table") — denormalize, dual-write, use Streams to maintain consistency
- No mixing item types under the same PK without a type-discriminator field
- No items growing unboundedly (huge attribute, ever-growing list) — split or store in S3
- No `Strong consistency` reads as the default — only when truly required; they cost more and may fail during failover
- No GSIs added "just in case" — they cost storage + per-write
- No IAM users — IAM roles + role assumption
- No long-lived clients per request — one per process
- No app-side encryption layered over DynamoDB's at-rest encryption "for extra safety" without a real threat model — adds query restrictions

## Generation steps

1. Enumerate access patterns with the user, including cardinality + latency targets. Refuse to schema-design without this list.
2. Design PK / SK and GSIs to make every pattern a `GetItem` or `Query`.
3. Generate IaC (CDK / Terraform) for the table — partition key, sort key, GSIs, billing mode, TTL, Streams settings, **PITR on, encryption tier (CMK where required), and the least-privilege IAM policy** (per-table/index ARNs, `LeadingKeys` for tenant isolation where applicable).
4. Generate the typed client setup for the chosen stack + a thin repository per logical entity.
5. Smoke locally with DynamoDB Local or LocalStack; replay the AP list against the schema; confirm every read is a `Query` or `GetItem` in the trace.

## Handoffs

- Cross-engine query patterns → `data/_shared/slow-query-fixes`
- Caching layer → `data/_shared/caching-patterns` + `data/redis`
- Schema evolution / migration patterns → `data/_shared/migrations`
- AWS deployment of the table + IAM / Streams-driven Lambda handlers → cloud provisioning / IaC for the store itself has no owning skill in this library yet; out of this domain's scope
- Verifying `LeadingKeys` tenant isolation actually holds (cross-tenant BOLA/IDOR matrix) → the `qa-security` peer + `qa/<stack>/skills/security-testing/permission-testing`
- Observability — CloudWatch metrics for `ConsumedRead/WriteCapacityUnits`, `Throttled*` → `observability/*` skills (via the `observability-engineer-{dotnet,java,node}` peer bundled in the matching `be-*` plugin)
