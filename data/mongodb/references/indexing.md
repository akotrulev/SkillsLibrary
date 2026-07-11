# MongoDB — Indexing

Index type selection, the ESR rule for compound indexes, covered queries, the specialty indexes (multikey/partial/TTL/wildcard), full-text (`$text` vs Atlas Search / Vector Search), and build discipline. Universal query triage (ESR as a cross-engine idea, keyset pagination, N+1) is in `data/_shared/query-optimization`; this is the MongoDB mechanics.

## The mental model

Every collection has an `_id` index you can't drop. Every other index is a B-tree of the indexed keys pointing at documents. A query either **uses an index** (`IXSCAN` → optionally `FETCH` the document) or **scans the collection** (`COLLSCAN`). The job of indexing is: for every hot query, an index that (a) filters, (b) supplies the sort, and ideally (c) covers the projection so no `FETCH` is needed. Verify with `.explain('executionStats')` (`references/performance.md`), never by assumption.

## Index types

| Type | Use for |
|---|---|
| **Single-field** | Equality / range / sort on one field |
| **Compound** | Multi-predicate queries — order by the **ESR rule** (below) |
| **Multikey** | A field that holds an array — created automatically when any indexed field is an array; one doc yields many index entries |
| **Partial** | Index only documents matching a filter — smaller, cheaper; the skewed-data / soft-delete workhorse |
| **TTL** | Auto-expire documents N seconds after a date field |
| **Unique** | Enforce uniqueness (optionally + partial for "unique among active") |
| **Wildcard** | Variable/unknown field names (`$**` or a subtree) — never on a hot path, expensive |
| **Text** | Built-in full-text (`$text`) — one per collection, limited |
| **Hashed** | Hashed-shard-key distribution (sharding only) |
| **Geospatial** | `2dsphere` for geo queries |

## The ESR rule (compound index field order)

Order compound-index fields **Equality → Sort → Range**:

1. **Equality** fields first (predicates using `=`/`$in`) — they narrow the scan to a contiguous range.
2. **Sort** fields next — so the index supplies the order and no in-memory `SORT` stage is needed.
3. **Range** fields last (`$gt`/`$lt`/`$gte`/`$lte`) — a range can't be followed by an equality or sort in the same index efficiently.

```javascript
// query: find({ customerId: X, totalMinor: { $gt: 1000 } }).sort({ placedAt: -1 })
db.orders.createIndex({ customerId: 1, placedAt: -1, totalMinor: 1 });
//                       └ Equality    └ Sort        └ Range
```

Get the order wrong (e.g. range before sort) and the planner adds a blocking `SORT` stage that reads the whole candidate set into memory. The **leftmost-prefix rule** applies: `{a, b, c}` also serves queries on `{a}` and `{a, b}`, but not `{b}` or `{c}` alone.

## Covered queries

If **every field the query needs** (filter + sort + projection) is in the index and you **exclude `_id`** from the projection (unless `_id` is in the index), Mongo answers from the index alone — `IXSCAN` with no `FETCH`. This is the fastest read Mongo can do.

```javascript
db.orders.createIndex({ customerId: 1, placedAt: -1 });
db.orders.find(
  { customerId: X },
  { _id: 0, customerId: 1, placedAt: 1 }   // only indexed fields → covered
).sort({ placedAt: -1 });
```

`explain` shows `totalDocsExamined: 0` when a query is truly covered.

## Specialty indexes

### Partial (the workhorse)

Index only the documents you actually query — smaller index, less write amplification.

```javascript
// only index active orders; queries that filter status:'active' can use it
db.orders.createIndex(
  { customerId: 1, placedAt: -1 },
  { partialFilterExpression: { status: 'active' } }
);

// "unique among active" — unique + partial, the correct soft-delete uniqueness pattern
db.users.createIndex(
  { email: 1 },
  { unique: true, partialFilterExpression: { deletedAt: { $exists: false } } }
);
```

Prefer a **partial index** over the legacy **sparse** index — partial is strictly more general.

### TTL

Auto-delete documents a fixed time after a `Date` field. A background task purges roughly every 60 s (not instantly — don't rely on it for security-sensitive precision).

```javascript
db.sessions.createIndex({ expiresAt: 1 }, { expireAfterSeconds: 0 });  // delete at the stored date
db.events.createIndex({ createdAt: 1 }, { expireAfterSeconds: 2592000 }); // 30-day retention
```

For native time-series collections use the collection's `expireAfterSeconds` instead (`references/data-modeling.md`).

### Multikey (arrays)

Automatic when an indexed field is an array. Caveats: you **cannot** compound-index two array fields together (the planner would face a cartesian explosion), and multikey changes sort behavior — verify with `explain`.

### Wildcard

For genuinely unknown/variable key names (a `metadata` sub-document of user-defined attributes). Costly to maintain; never put one on a high-write hot path. Prefer modeling the variable data as an array of `{k, v}` pairs with a normal compound index when you can.

## Full-text search: `$text` vs Atlas

- **`$text` index** (built-in, self-hosted and Atlas): one per collection, basic stemming/stop-words, no relevance tuning, no facets. Fine for "search a title field." Language-limited.
- **Atlas Search** (`$search`, Lucene-backed): fuzzy, faceted, autocomplete, relevance scoring, multi-field — the real search engine. **Atlas-only** (managed `mongot` process); not available on the Community server.
- **Atlas Vector Search** (`$vectorSearch`): kNN over embedding vectors for semantic/RAG retrieval, GA, with quantization to cut memory. **Atlas-only.**

**The fence:** if the project is self-hosted and needs real search, `$text` won't cut it — route to a dedicated search engine (`data/elasticsearch`) rather than pretending Mongo does search. State this explicitly.

## Build discipline

- Index creation is **online by default** on modern versions (builds without blocking writes), but state it and watch resource use on large collections.
- For very large collections on a replica set, do a **rolling index build** (build on each secondary in turn, then step down and build on the former primary) to avoid a heavy build on the serving primary.
- **Declare indexes in a migration**, never at app startup / `auto-index-creation` — an app instance racing to create an index on boot is a production incident.
- Drop unused indexes: `db.collection.aggregate([{ $indexStats: {} }])` shows access counts; an index with near-zero `accesses.ops` over a representative window is dead weight (every index taxes writes).
- Watch for **redundant prefixes**: `{a,b}` makes a standalone `{a}` redundant.

## What NOT to do

- No index whose field order ignores ESR (range before sort → blocking in-memory SORT).
- No compound index across two array fields (illegal — cartesian multikey).
- No wildcard index on a hot write path as a substitute for knowing your queries.
- No relying on `$text` for real search on self-hosted (route to a search engine).
- No index created at app startup; declare in a migration.
- No leaving an obviously unused index in place — it slows every write.
- No unique index on a soft-deleted field without a `partialFilterExpression` (blocks legitimate re-creates).

## Handoffs

- Reading `explain` output / diagnosing why an index isn't used → `references/performance.md`
- ESR as a cross-engine principle, keyset pagination, N+1 → `data/_shared/query-optimization`
- The document shapes these indexes serve → `references/data-modeling.md`
- Self-hosted full-text/semantic search that outgrows `$text` → `data/elasticsearch`
