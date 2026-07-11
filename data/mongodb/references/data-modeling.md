# MongoDB — Data Modeling

Document/subdocument **mechanics**, the canonical modeling patterns, `_id` strategy, schema validators, and time-series collections. The cross-engine *choice* of embed-vs-reference, id strategy, money representation, soft-delete, and multi-tenant pattern lives in `data/_shared/schema-design` — this file is the MongoDB mechanics that implement that choice.

## The core trait: the document is the unit of atomicity

A single-document write is atomic. Everything you embed in one document updates, versions, and reads together in one round trip. Everything you split into a second collection needs a second query (or a `$lookup`) and has **no cross-document atomicity** unless you open a multi-document transaction. Model around this: *data that is read together and changes together belongs in the same document; data with an independent lifecycle or unbounded growth does not.*

## Embed vs reference — the mechanics

The *decision framework* is `_shared/schema-design`. Here is how each side is actually built and where each breaks.

| Embed when | Reference when |
|---|---|
| Child is **always** loaded with the parent | Child is queried on its own |
| 1-to-few, **bounded** (≲ dozens, hard cap in the low hundreds) | 1-to-many, **unbounded** |
| Lifecycle matches the parent (deleted with it) | Independent lifecycle |
| Updates rewrite mostly the whole document | Child updates hot and often, parent rarely |

**The 16 MB document limit is a hard ceiling — design to a ~1 MB working budget.** The classic failure is an unbounded embedded array ("all events on this order forever"): it grows without limit, every update rewrites the whole document, and the working set bloats. Bound every embedded array or don't embed it.

### Referencing mechanics

Store the related `_id` (or a small key) on the child or parent and read with a second query. Prefer a **second query in application code** over `$lookup` for OLTP — it is easier to index, page, and cache. Reserve `$lookup` for read-model/aggregation paths, and only against an **indexed** foreign field.

```javascript
// child holds the parent ref
{ _id: ObjectId("…line1"), orderId: ObjectId("…order"), sku: "ABC-1", qty: 2 }
// index the join field on the many side
db.orderLines.createIndex({ orderId: 1 });
```

### The extended (subset) reference pattern

Embed a **read-only snapshot of the few fields you always display**, keep the full record in its own collection, and store the reference for when you need the rest. This kills the N+1 read for list views without duplicating the whole entity.

```javascript
// order embeds just enough customer to render a list row
{
  _id: ObjectId("…"),
  customer: { _id: ObjectId("…cust"), name: "Ada L.", tier: "gold" },  // subset snapshot
  totalMinor: NumberLong(9999)
}
// full customer lives in `customers`; snapshot is refreshed on the rare name/tier change
```

The trade-off is **duplication that can drift** — you own a backfill/repair path (a change-stream updater or a scheduled reconciler) for when the source field changes. Only snapshot fields that change rarely.

### The computed pattern

Store pre-computed rollups (counts, sums, "last activity") on the parent, updated with atomic operators (`$inc`, `$max`, `$push` with `$slice`) on write, instead of aggregating on every read.

```javascript
db.orders.updateOne(
  { _id: id },
  { $inc: { lineCount: 1, totalMinor: 2999 },
    $push: { recentEvents: { $each: [evt], $slice: -20 } } }  // bounded array!
);
```

`$slice: -20` keeps the embedded array bounded — the pattern that makes "recent activity" embeddable safely.

### The bucket pattern (for time-series-shaped data)

When you have a high-volume stream of small measurements (IoT, metrics, event logs) and don't want a document per point, **bucket** many points into one document per (source, time-window). This slashes document count and index size. On 8.0/7.0 prefer **native time-series collections** (below) over hand-rolled buckets — the engine does the bucketing for you.

## `_id` strategy

- Default `ObjectId` (driver-generated, 12 bytes, roughly time-ordered) — use it unless you need a cross-system meaningful id.
- For client-generated / external-system ids use a `_id: <string>`; **UUIDv7** is the right choice (timestamp-ordered → insert locality, unlike v4). Store it as the BSON UUID subtype where the driver supports it, not a hex string, to save space.
- Never duplicate `_id` into a second field "for querying" — query `_id` directly.
- `_id` is immutable and always uniquely indexed; don't add a redundant unique index on it.

## Schema validation ($jsonSchema)

Validation is opt-in but belongs on **every production collection** — it is the closest Mongo gets to a schema contract. Turn it on when the collection is created and evolve it expand-contract (see the router's Migrations rules).

```javascript
db.createCollection('orders', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['customerId', 'status', 'totalMinor', 'currency', 'placedAt'],
      additionalProperties: false,            // reject unexpected fields
      properties: {
        customerId: { bsonType: 'objectId' },
        status:     { enum: ['pending', 'paid', 'cancelled', 'refunded'] },
        totalMinor: { bsonType: 'long', minimum: 0 },
        currency:   { bsonType: 'string', pattern: '^[A-Z]{3}$' },
        placedAt:   { bsonType: 'date' }
      }
    }
  },
  validationLevel: 'strict',      // validate all inserts and updates
  validationAction: 'error'       // reject; use 'warn' only during a migration window
});
```

- `additionalProperties: false` is what makes the validator a real contract rather than a suggestion — otherwise typo'd field names sail through.
- `enum` in the validator is the Mongo equivalent of a CHECK/lookup constraint; there is no native enum type.
- `validationLevel: 'moderate'` validates only inserts + updates to already-valid docs — use it briefly while backfilling legacy data.

## Data types

- **Money**: integer minor units as `NumberLong` (BSON `long`). Never `Number`/double — floating point loses cents. `Decimal128` is available for high-precision domains (rates, tax) but minor-unit longs are the default.
- **Timestamps**: BSON `Date`, always UTC. Never ISO strings (no range index semantics, sorts lexically), never the internal `Timestamp` type (that's for the oplog).
- **Enumerations**: strings constrained by the validator `enum`.
- **References**: the related `_id`'s native type (usually `ObjectId`), not a stringified copy.

## Time-series collections (native, 5.0+; recommended over hand-rolled buckets)

For measurements/events keyed by time and a metadata identity, create a native time-series collection — the engine buckets internally, giving smaller storage and faster range scans than a document-per-point design.

```javascript
db.createCollection('readings', {
  timeseries: { timeField: 'ts', metaField: 'sensorId', granularity: 'minutes' },
  expireAfterSeconds: 2592000    // built-in TTL — 30-day retention
});
```

- `metaField` groups points that share an identity (the low-cardinality dimension you filter/group by); `timeField` is the BSON `Date`.
- Set `expireAfterSeconds` for automatic retention instead of a manual TTL cleanup job.
- 8.0 brings substantial time-series aggregation/query speedups over 7.0 — same API, faster engine.

## Anti-patterns (modeling)

- Unbounded embedded arrays — the number-one Mongo modeling bug. Bound with `$slice`, or promote to a child collection.
- Massive documents you read whole to use one field — split hot from cold fields.
- Modeling a relational schema in Mongo (many small normalized collections joined with `$lookup` everywhere) — if the access pattern is relational, you picked the wrong engine.
- Storing money as double, dates as strings, or enums as free-text with no validator.
- A `type`/`kind` discriminator collection holding wildly different shapes with no validator — either use per-type collections or a validator with `oneOf`.

## Handoffs

- Embed-vs-reference **decision**, id strategy, money, soft-delete, multi-tenant *pattern choice* → `data/_shared/schema-design`
- Indexes for the shapes you just designed → `references/indexing.md`
- Field-level encryption of sensitive properties → `references/security.md`
- Evolving a validator / reshaping documents safely → `data/_shared/migrations` + the router's Migrations rules
