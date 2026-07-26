---
name: data-slow-query-fixes
description: Use when the user is diagnosing a slow query or designing an index across any SQL or document engine — applying universal principles (selectivity, projection, paging, plan analysis, ESR rule) before reaching for engine-specific tactics. Triggers: "why is this query slow", "design an index for X", "should I paginate with offset", "ESR rule", "missing index", "N+1 query". Do NOT use for engine-specific syntax (use `data/<db>`) or caching layer questions (use `data/_shared/caching-patterns`).
---

# Data — Query Optimization (cross-engine)

Cross-engine principles for diagnosing and fixing slow queries. Applies to PostgreSQL / SQL Server / MySQL / MongoDB / DynamoDB / Cosmos DB. Engine-specific syntax lives in `data/<db>`.

## When to use

- A query is slow and the user wants the systematic approach before fiddling with hints
- Designing the first index for a new query pattern
- Choosing between `OFFSET` and keyset pagination
- Reading a plan / `EXPLAIN` / `executionStats` structurally
- Spotting anti-patterns (N+1, missing projections, accidental full scans, unbounded queries)

## When NOT to use

- Engine-specific syntax / DMVs / system views → `data/<db>`
- Caching as a substitute for a missing index → `data/_shared/caching-patterns`

## The universal triage

For every slow query, walk these in order. **Don't skip steps.**

1. **Is the query bounded?** Does it have a `WHERE` that limits rows, a `LIMIT`, a partition-key filter? Unbounded queries are a different problem than slow ones.
2. **Does the predicate use an indexable column?** Is there an index that matches the columns in `WHERE` and `ORDER BY`?
3. **Is the index covered?** Does the index include all columns the query needs, or does the engine have to look up rows from the table for each match?
4. **What is the plan doing?** Scan vs seek vs index lookup vs sort vs hash. Each plan node tells you where time is going.
5. **What does the data look like?** Skew, cardinality, distribution — wrong stats produce wrong plans even with the right indexes.
6. **Is this query the right question?** Sometimes the answer is "don't ask the DB this question" — cache it, precompute it, denormalize it.

### Plan reading — the universal nodes

| Node | What it does | Bad sign |
|---|---|---|
| Sequential / table scan | Reads every row | On a large table where the query asks for a subset |
| Index scan / seek | Walks the index | Many "lookup" or "key lookup" calls back to the table |
| Sort | Orders the result | Spilling to disk; sort-node with a million rows when only top-N is wanted |
| Hash match / hash join | Builds a hashtable in memory | Memory grant huge for a small join — usually wrong stats |
| Nested loop | Outer × inner | Tens of thousands of inner lookups (uncovered index) |
| Filter | Discards rows after read | High "rows removed by filter" — predicate not pushed to index |

## The ESR rule (compound indexes)

Universal rule for compound indexes across engines:

**E**quality first → **S**ort next → **R**ange last.

For `find({ tenantId, status: 'paid' }).sort({ placedAt: -1 }).filter({ totalMinor: { $gt: x } })`:

- Equality on `tenantId`, `status`
- Sort on `placedAt`
- Range on `totalMinor`

Index: `{ tenantId: 1, status: 1, placedAt: -1, totalMinor: 1 }`

The same idea applies in SQL — compound index on `(tenant_id, status, placed_at DESC, total_minor)` covers an equivalent SQL query.

When you have multiple query patterns, you'll need multiple indexes — don't try to make one index serve everything; the planner won't use it well.

## Selectivity & cardinality

An index helps when the predicate selects a **small fraction** of the rows.

| Predicate selectivity | Index helps? |
|---|---|
| < 1% of rows | Yes, huge win |
| 1–10% | Usually yes |
| 10–30% | Depends; sometimes a scan is cheaper |
| > 30% | Usually no; scan is fine |

Don't index columns that don't reduce the row count.

**Partial / filtered indexes** are the antidote to skewed data — index only the rows you actually query for.

```sql
-- Postgres: index only "live" rows
CREATE INDEX orders_active_idx ON orders (placed_at DESC) WHERE status IN ('pending', 'paid');
```

Smaller index, faster reads, cheaper writes.

## Projection discipline

`SELECT *` is the most common cause of slow queries that "should be fast". Read what you need.

- The engine can satisfy a query from a covering index when all projected columns are in the index — never if `*` forces a back-to-table lookup
- Wire formats balloon when entire rows are serialized for queries that need three columns
- Mongo projections (`.find(filter, { _id: 1, status: 1 })`) skip unused fields server-side

## Pagination

| Method | When |
|---|---|
| `LIMIT N` (only) | Top-N queries with no continuation |
| `OFFSET N LIMIT M` | Small tables, dashboards where users rarely page deep |
| **Keyset pagination** (`WHERE (placed_at, id) < (?, ?) ORDER BY placed_at DESC, id DESC LIMIT M`) | Tables > ~10k rows, deep pagination, infinite scroll |
| Continuation tokens (DynamoDB / Cosmos) | NoSQL engines that hand back a cursor |

`OFFSET 1000000 LIMIT 20` is a fast way to make any engine cry. The engine reads 1,000,020 rows and discards 1,000,000 — keyset reads exactly 20.

## N+1 queries

The single most common ORM trap. Symptoms:

- Listing endpoint runs N+1 round-trips (one for the list, one per item)
- Total query time is `latency × N`, not `single-query latency`

Fixes:

- **Eager loading**: EF Core `.Include(o => o.Lines)`; Hibernate `@EntityGraph`; Prisma `include: { lines: true }`
- **Batched fetches**: load all parents, then load all children with `WHERE parent_id IN (...)`, then assemble in app code
- **Dataloaders** (graphql-style): batch + dedupe within a request scope

Tracing (OTel) shows N+1 as a fan of identical short queries on a span — quick to spot. Add it to your `qa/<stack>/skills/api-test-author/reviewer` checklist.

## Filtering & sorting

- Filter on indexed columns; if the column isn't selective enough, **don't** index it — it'll add write cost without read benefit
- Sort on an index that matches the sort key + direction. Mismatched direction (ASC sort against DESC index) often still works but check the plan.
- Functional indexes (`(LOWER(email))`, `(date_trunc('day', placed_at))`) when the predicate uses an expression — otherwise the index is bypassed

## Engine-specific triage (cross-engine summary — deep version in `data/<db>`)

The universal triage above is the frame. Each engine's plan-reading, index types, and access-pattern discipline are owned by its own skill; the essentials to know cross-engine:

**Document stores (Mongo / Cosmos).** Same triage, plus: aggregation pipelines **`$match` first, `$project` early** to shrink the document stream; read `.explain('executionStats')` (Mongo) / query metrics (Cosmos) — `keysExamined` vs `nReturned` should be ≤ 2:1; Cosmos partition key in `WHERE` makes the query **single-partition**, non-negotiable on hot paths. Deep: `data/mongodb/references/performance.md`, `data/cosmosdb/SKILL.md`.

**DynamoDB.** **Never `Scan`** in application code — design PK / SK / GSIs so every read is a `GetItem` or `Query`; hot partition → Contributor Insights, then redesign the key; `BatchGetItem` (≤ 100 items) for parent + children, `TransactGetItems` for cross-item consistent reads. Deep: `data/dynamodb/SKILL.md`.

**SQL engines.** Query Store first on SQL Server, `EXPLAIN (ANALYZE, BUFFERS)` on Postgres, `EXPLAIN ANALYZE` + Performance Schema on MySQL. Deep: each engine's `performance.md`.

## Quick wins checklist

1. Add the missing index on the column in the `WHERE` clause
2. Project the columns you need instead of `*`
3. Replace `OFFSET` paging with keyset
4. Drop the unused indexes
5. Set a query/statement timeout per connection
6. Move read-only analytics off the primary
7. Cache the answer when the data tolerates it
8. Re-collect statistics on the hot table after large data shifts

## Anti-patterns to flag

- **`SELECT *`** in production code
- **Unbounded queries** — no `LIMIT`, no PK filter
- **`OFFSET 100000 LIMIT 20`** deep pagination
- **N+1** in any ORM-backed listing endpoint
- **Index every column** policies that double write cost
- **`WITH (NOLOCK)` / dirty reads** sprinkled to "make it fast" — that's not a fix
- **Wrap an ORM in another wrapper** to "make queries safer" — usually just hides the slow query
- **`SELECT COUNT(*)`** on a huge table for "how many records are there" — approximate counts (`pg_class.reltuples`) often suffice
- **Query the DB for something that doesn't change between requests** — cache it
- **Wide composite indexes** (8 columns) trying to cover every query

## Rules

- Walk the triage in order; don't skip plan reading
- Indexes designed per query pattern, not per column
- Compose indexes via ESR (Equality / Sort / Range)
- Partial / filtered indexes for skewed data
- Projection discipline — never `*` in app code
- Keyset pagination above ~10k rows
- N+1 caught at code-review time, not in prod
- Statement timeouts so runaway queries don't run for hours
- Stats kept fresh on hot tables
- Cache only when the cost of staleness < cost of compute

## What NOT to do

- No `SELECT *`
- No unbounded queries
- No `OFFSET` deep paging
- No "index everything" as a strategy
- No `NOLOCK` / dirty reads as a perf strategy
- No N+1 left in the codebase after review
- No "the DB will figure it out" attitude — read the plan
- No caching to mask a missing index
- No assuming the optimizer is right about stats — verify
- No tuning by adding hints before fixing the underlying query / index / data

## Generation steps

1. Capture the slow query + a representative `EXPLAIN ANALYZE` / `executionStats` output.
2. Walk the universal triage and identify the symptom (scan vs seek, missing projection, missing index, N+1, deep page, wrong stats).
3. Propose the smallest fix that addresses the symptom; reach for the engine's specific feature only when the universal one doesn't apply.
4. Confirm with a re-run plan; measure latency before/after.
5. Add a test (`qa/<stack>/skills/api-test-author/generator`) that asserts the response shape so the optimization doesn't regress the contract.

## Handoffs

- Engine-specific syntax → `data/<db>`
- Caching layer → `data/_shared/caching-patterns`
- Tracing the query in prod → `observability/opentelemetry-{stack}` (slow query = long span)
- Schema redesign → `data/_shared/schema-design`
