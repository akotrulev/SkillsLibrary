---
name: data-elasticsearch
description: Use when the user asks to design indexes, set up clients, secure a cluster (native realm / API keys / document- & field-level security / TLS), plan migrations, or write queries on Elasticsearch / OpenSearch from a .NET 10 / Java 21 / Node 24 backend — full-text search, structured search, aggregations, log search (off the OTel/Loki path), vector search (kNN). Also the destination for self-hosted full-text/semantic search handed off from `data/mongodb`, and vector search beyond a cache handed off from `data/redis`. Triggers: "design an Elasticsearch index for X", "build a search query", "reindex strategy", "OpenSearch on AWS vs Elastic Cloud", "vector search for embeddings", "document-level security per tenant". Do NOT use for log shipping (use `observability/loki-tempo-setup`), relational stores (use `data/<sql-db>`), or operational metrics (use Prometheus / Mimir).
---

# Data — Elasticsearch / OpenSearch

Index design, client setup, ingest, query shape, security, and operational concerns for **Elasticsearch 9** and **OpenSearch 3** from the library's three backend stacks. Use for **full-text search**, **structured queries on semi-structured documents**, **aggregations on event data**, and **vector / kNN search**. Logs are handled by Loki (`observability/loki-tempo-setup`); only use ES for logs if you have a strong reason (rich aggregations / wildcards that LogQL struggles with).

This is also the **destination for two inbound handoffs** authored elsewhere in `data/`: `data/mongodb/references/indexing.md` routes *self-hosted* full-text / semantic search here (Atlas Search / Vector Search is Atlas-only, so self-hosted Mongo that needs real relevance ranking projects into ES); `data/redis/references/data-structures.md` routes *vector search beyond a cache* here (Redis's vector module is fine as a fast KV-adjacent ANN cache, but a durable, filterable, reindexable vector store is an ES/OpenSearch `dense_vector` job).

## Version & distribution policy

Version-aware like the rest of `data/`: detect the cluster version first, then key guidance to it. Never apply a 9-only construct to an 8.x cluster; never flag an 8.x cluster for lacking one.

- **Elasticsearch 9.x primary** (9.3.x current, 2026), **8.x supported**. The major-9 line is the default for new clusters.
- **OpenSearch 3.x** (3.6 current) is the actively-supported fork line if you're on OpenSearch.

### The fork divergence (mirror the Valkey / MariaDB treatment)

Elasticsearch and OpenSearch share a Lucene core and a common ancestor but have **genuinely diverged** — treat them like Redis↔Valkey and MySQL↔MariaDB, not like drop-in equivalents.

| | Elasticsearch (Elastic) | OpenSearch (fork) |
|---|---|---|
| **Origin** | Reference implementation | AWS-led fork of ES 7.10 (Apr 2021) |
| **Governance** | Elastic (company) | **OpenSearch Software Foundation** under the Linux Foundation (since Sept 2024) |
| **License** | Tri-licensed **AGPLv3 / SSPL / Elastic License 2.0** (AGPLv3 added late 2024 — OSI-approved again) | **Apache 2.0** (permissive throughout) |
| **Feature velocity** | ~7× the commit activity since the fork; new features land here first | Slower; caught up well on vector/kNN, lags elsewhere |
| **Managed hosting** | Elastic Cloud (any cloud), self-host | **AWS OpenSearch Service** is the default managed path; self-host |
| **Security config** | X-Pack security (`xpack.security.*`), native realm, API keys, DLS/FLS built in | OpenSearch Security plugin (analogous concepts, different config surface) |

**Pick by hosting + license posture**: AWS-first and want Apache-2.0 → OpenSearch on AWS OpenSearch Service; want the newest ES features / Elastic Cloud → Elasticsearch. Both speak compatible REST at the basic level; **advanced features, security config, and client libraries diverge** — don't assume an ES recipe drops onto OpenSearch unchanged.

## When to use

- App needs a search box that does relevance ranking, fuzzy matching, synonyms, highlighting
- Aggregations on event / document data ("top sellers by region this month") that don't fit a relational shape
- Vector / kNN search for embedding-based retrieval (RAG, similar-product)
- Time-series event store where Postgres would be slow without significant work

## When NOT to use

- Logs / observability — `observability/loki-tempo-setup`
- Transactional store of record — use Postgres / Mongo / SQL Server / etc.
- Operational metrics — Prometheus / Mimir
- Strongly-relational queries with joins — Postgres
- Tiny datasets (< 100k rows) — Postgres `tsvector` full-text is fine

## Stack defaults

- **Cluster**: 3 master-eligible nodes (production); separate data + ingest nodes at scale
- **Clients** (one per process — thread-safe, expensive to construct): `@elastic/elasticsearch` (Node 24), `Elastic.Clients.Elasticsearch` (.NET 10), `co.elastic.clients:elasticsearch-java` (Java 21) — or the matching `@opensearch-project/opensearch` / `opensearch-java` clients on OpenSearch (the clients are **not** cross-compatible on advanced APIs)
- **Index management**: ILM (Elastic) / ISM (OpenSearch) for hot-warm-cold tiering + retention
- **Auth**: security enabled; **API keys** for services + role-based access with document/field-level security; IAM auth for AWS OpenSearch
- **Ingest**: bulk API from the backend, never single-document inserts on hot paths

## Index design

### Index per resource family, time-based aliases for streams

```
products_v1            ← single index, full reindex on schema change (replace alias)
events-2026.05         ← time-based (monthly), aliased as `events` for writes
events-*               ← read alias spanning all months
```

- Static reference data → **versioned index + alias** (`products_v1`, alias `products`); on schema change create `products_v2`, reindex, swap the alias atomically
- Time-series / log-like data → **rollover by time or size** (`events-000001`, `events-000002`); ILM/ISM rotates and deletes

### Mapping

Always **explicit**. Dynamic mapping creates surprises (string fields auto-mapped as `text` + `keyword`, dates auto-detected from strings, etc.).

```json
PUT /products_v1
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "analysis": {
      "analyzer": {
        "english_with_synonyms": {
          "tokenizer": "standard",
          "filter": ["lowercase", "english_stop", "english_stemmer", "product_synonyms"]
        }
      },
      "filter": {
        "english_stop": { "type": "stop", "stopwords": "_english_" },
        "english_stemmer": { "type": "stemmer", "language": "english" },
        "product_synonyms": { "type": "synonym", "synonyms_path": "synonyms/products.txt" }
      }
    }
  },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "id":          { "type": "keyword" },
      "name":        { "type": "text", "analyzer": "english_with_synonyms", "fields": { "keyword": { "type": "keyword", "ignore_above": 256 } } },
      "description": { "type": "text", "analyzer": "english_with_synonyms" },
      "category":    { "type": "keyword" },
      "priceMinor":  { "type": "long" },
      "currency":    { "type": "keyword" },
      "tags":        { "type": "keyword" },
      "createdAt":   { "type": "date" },
      "updatedAt":   { "type": "date" },
      "embedding":   { "type": "dense_vector", "dims": 1536, "index": true, "similarity": "cosine" }
    }
  }
}
```

- **`dynamic: strict`** — reject documents with fields not in the mapping
- **`text` for full-text** search; **`keyword` for exact match / aggregation / sort**
- **Multi-fields** (`fields.keyword`) for fields you need both ways
- **Long for money** (minor units); never `float` / `scaled_float` without thought
- **`dense_vector`** for vector search (ES 8 / OpenSearch with kNN)

### Shard count — get this right early

- Shards are immutable; you can't change `number_of_shards` after creation. Plan ahead.
- Rule of thumb: **target shard size 10–50 GB**. A 100 GB index needs 2–10 shards.
- For small indexes (< 50 GB total ever), **1 primary + 1 replica** is fine.
- Over-sharding (1000s of tiny shards) is the most common operational pain.

## Client setup

### Node 24 + TypeScript

```typescript
// src/persistence/es.ts
import { Client } from '@elastic/elasticsearch';

export const es = new Client({
  node: process.env.ES_URL!,
  auth: {
    apiKey: process.env.ES_API_KEY!,                // never username/password in apps
  },
  tls: { rejectUnauthorized: true },
});
```

### .NET 10

```csharp
using Elastic.Clients.Elasticsearch;
using Elastic.Transport;

var settings = new ElasticsearchClientSettings(new Uri(builder.Configuration["Es:Url"]!))
    .Authentication(new ApiKey(builder.Configuration["Es:ApiKey"]!))
    .DefaultIndex("products_v1");

builder.Services.AddSingleton(new ElasticsearchClient(settings));
```

### Java 21

```java
RestClient httpClient = RestClient.builder(HttpHost.create(System.getenv("ES_URL")))
    .setDefaultHeaders(new Header[]{ new BasicHeader("Authorization", "ApiKey " + System.getenv("ES_API_KEY")) })
    .build();
ElasticsearchTransport transport = new RestClientTransport(httpClient, new JacksonJsonpMapper());
ElasticsearchClient es = new ElasticsearchClient(transport);
```

All clients are **thread-safe and expensive to construct** — one per process.

## Ingest

Always **bulk**, never one-doc-per-request on hot paths.

```typescript
await es.bulk({
  operations: products.flatMap((p) => [
    { index: { _index: 'products_v1', _id: p.id } },
    { name: p.name, description: p.description, category: p.category, priceMinor: p.priceMinor, currency: p.currency, tags: p.tags, createdAt: p.createdAt, updatedAt: p.updatedAt },
  ]),
});
```

Batch size 500–5000 docs / 5–15 MB per bulk request. Track errors per item (`response.errors === true` + scan the `items[]` array). Throttle on backpressure (429s).

## Search queries

### Full-text with relevance

```json
GET /products/_search
{
  "size": 20,
  "query": {
    "multi_match": {
      "query": "wireless headphones",
      "fields": ["name^3", "description"],
      "fuzziness": "AUTO",
      "operator": "and"
    }
  },
  "highlight": { "fields": { "name": {}, "description": {} } }
}
```

`^3` boosts the `name` field over `description`. `fuzziness: AUTO` handles typos. `operator: and` requires all terms (precise); default `or` recalls more.

### Structured + full-text hybrid

```json
{
  "query": {
    "bool": {
      "must":   [{ "multi_match": { "query": "wireless headphones", "fields": ["name^3", "description"] }}],
      "filter": [
        { "term": { "category": "electronics" } },
        { "range": { "priceMinor": { "lte": 50000 } } }
      ]
    }
  }
}
```

`filter` clauses don't affect score (don't pay the relevance cost) and **cache automatically** — use them for facet / refinement filters.

### Aggregations

```json
{
  "size": 0,
  "aggs": {
    "by_category": {
      "terms": { "field": "category", "size": 10 },
      "aggs": {
        "avg_price": { "avg": { "field": "priceMinor" } }
      }
    }
  }
}
```

`size: 0` skips returning documents — useful when you only want the aggregation.

### Vector / kNN search

```json
{
  "knn": {
    "field": "embedding",
    "query_vector": [0.12, -0.04, ...],
    "k": 20,
    "num_candidates": 200
  }
}
```

Hybrid (lexical + vector):

```json
{
  "query": {
    "match": { "name": "wireless headphones" }
  },
  "knn": {
    "field": "embedding",
    "query_vector": [...],
    "k": 50,
    "num_candidates": 200,
    "boost": 0.3
  }
}
```

For RAG / similar-product features.

## Pagination

| Approach | Use when |
|---|---|
| **`from` + `size`** | First few pages; **never beyond `from: 10000`** (default max) |
| **`search_after`** | Keyset pagination; deep paging; the right default for any large result set |
| **`scroll`** | Bulk exports only; deprecated for general use — prefer `search_after` |
| **PIT (Point-in-Time) + `search_after`** | Stable snapshot pagination across writes |

## Reindexing & schema changes

You **cannot** add a new field to an existing field's mapping in incompatible ways (text → keyword), nor change analyzers. The pattern:

1. Create `products_v2` with the new mapping
2. Reindex (`POST /_reindex`) from `products_v1` → `products_v2`, optionally with a pipeline that transforms documents
3. Application writes to both during cutover (dual-write) or pause writes briefly
4. Swap the alias atomically (`POST /_aliases`) from `v1` → `v2`
5. Delete `v1` after a hold period

For zero-downtime, **always read via an alias**, never the index name. Same pattern as expand-contract (`data/_shared/migrations`).

## Security & access control

Security is **on** in modern ES/OpenSearch by default — never run a cluster with it disabled, even internally (the classic "internal-only" open cluster is how search indexes end up on the public internet). The model has four layers.

### Authentication — API keys, not passwords

- **API keys** are the credential for services. Each key carries its own **role descriptors**; when you omit them the key inherits a point-in-time snapshot of the creating user's permissions, and when you supply them the key's effective permissions are the **intersection** of the descriptors and the creating user's — so a key can only ever be *narrower* than its creator. Mint one key per service, scoped to the indices/aliases it touches, and rotate them.
- The **native realm** (users stored in ES) is for humans/bootstrap; back it with SSO (SAML/OIDC) realms for real user auth. Never ship the `elastic` superuser to an application.
- On **AWS OpenSearch Service**, use **IAM / SigV4** request signing (or fine-grained access control with internal users) rather than static credentials.

### Authorization — roles, then row/column scoping

Roles grant cluster + per-index privileges. Two capabilities make a role a real multi-tenant boundary:

- **Document-level security (DLS)** — attach a **Query DSL** filter to a role so the holder can only read documents matching it, e.g. `{ "term": { "tenantId": "42" } }`. This is the mechanism for per-tenant read isolation on a shared index; the tenant filter is enforced by the cluster, not the app query, so a forgotten `WHERE` can't leak across tenants.
- **Field-level security (FLS)** — grant/deny individual fields per role (e.g. hide `ssn`, `salary`). Combine with DLS on the same role for row+column scoping.

```json
PUT /_security/role/tenant_42_reader
{
  "indices": [{
    "names": ["products", "orders"],
    "privileges": ["read"],
    "query": { "term": { "tenantId": "42" } },                 // DLS: only this tenant's docs
    "field_security": { "grant": ["*"], "except": ["internalNotes"] }  // FLS: hide a field
  }]
}
```

> DLS/FLS restrict **reads**. Writes still need the app to stamp the correct `tenantId` — enforce it in the ingest path and QA it with a cross-tenant leak test (the `qa-security` peer's BOLA/IDOR matrix), the same discipline `data/mongodb` requires for app-enforced multi-tenancy.

### Encryption & transport

- **TLS on the HTTP layer** (client ↔ cluster) **and the transport layer** (node ↔ node) — both, not just the HTTP endpoint. `rejectUnauthorized: true` / verify the CA in every client (the samples above do).
- **Encryption at rest** is the host/managed-service responsibility (encrypted EBS / disk on AWS OpenSearch / Elastic Cloud); enable it and snapshot to encrypted object storage.
- Put the cluster in a private network (VPC / VNet); never expose 9200 publicly. Front user-facing search through your API, not the cluster directly.

## Operational

- **ILM / ISM**: hot tier (recent writes), warm tier (older data, fewer replicas), cold tier (frozen / object storage), delete tier (retention)
- **Snapshots** to S3 / Blob / GCS — daily snapshot lifecycle
- **Cluster sizing**: rule of thumb — heap = 50% of RAM, capped at 30 GB; CPU per shard during heavy queries; SSD storage
- **Index templates** drive the mapping for all future indices matching a pattern; pair with ILM for time-based streams
- **Refresh interval**: 1s default; bump to 30s or `-1` (disabled) during bulk ingest, restore after
- **Replicas**: 1 in prod minimum; 0 during initial reindex bulk loads, then bump back

## Observability

- **Slow query log** — `index.search.slowlog.threshold.query.warn: 10s` etc.
- Cluster health, node JVM heap, indexing rate, search rate, queue rejections in Grafana via Prometheus exporter or built-in monitoring
- Query latency p95 / p99 via the slow log + dashboards

## Rules

- Explicit mapping (`dynamic: strict`)
- Index design: versioned for reference data, rolling for time-series; always alias-fronted
- Bulk ingest; never per-doc on hot paths
- Use `filter` clauses for non-scoring conditions (cached, fast)
- `from + size` only for the first few pages; `search_after` beyond
- Reindex pattern for breaking schema changes
- ILM / ISM for time-series retention
- Security enabled always; per-service API keys scoped by role descriptor (never the `elastic` superuser); IAM/SigV4 for AWS OpenSearch
- Multi-tenant isolation via a **DLS** query on the role (+ FLS for sensitive fields), not just an app-side filter — and QA'd with a cross-tenant leak test
- TLS on both HTTP and transport layers; cluster on a private network, never 9200 exposed publicly
- Snapshots to encrypted object storage on a schedule
- Shard size 10–50 GB; over-sharding is the #1 operational pain

## What NOT to do

- No dynamic mapping in production
- No per-document indexing in a tight loop
- No `from: 100000` deep paging
- No 1000+ small shards
- No `text` field on something you need to sort / aggregate (use `keyword` or a multi-field)
- No username/password auth — API keys / IAM
- No live mapping changes on a hot index — reindex
- No queries unfiltered by tenant / customer when multi-tenant — enforce with DLS on the role, don't rely on the app remembering
- No running with security disabled, even "internally"
- No assuming an ES recipe drops onto OpenSearch unchanged (diverged security config + clients + advanced APIs)
- No production cluster without snapshots
- No ES for logs when Loki is in the stack — different optimization curves
- No `_id` derived from a value the application doesn't control (use UUIDs or app-known keys)

## Generation steps

1. Confirm distribution (ES / OpenSearch), hosting (managed / self), and use case (full-text / aggregations / vector / time-series).
2. Design the mapping; explicit fields, multi-fields for text+keyword, analyzers + synonyms if relevance matters.
3. Pick index strategy (versioned + alias for reference; rolling for time-series + ILM/ISM).
4. Generate the client singleton for the stack (API-key auth, TLS verified).
5. Generate ingest helpers (bulk-only).
6. Generate query helpers per use case (search, filter, aggregation, kNN).
7. Define roles + per-service API keys; add DLS (+ FLS) where the index is multi-tenant or holds sensitive fields.
8. Add observability — slow-log thresholds + Grafana dashboards from `observability/grafana-dashboards`.
9. Plan reindex strategy + snapshot (encrypted) retention; document the runbook.

## Handoffs

- Log search → `observability/loki-tempo-setup` (use Loki, not ES, for logs)
- Source of record alongside ES → `data/postgresql` / `data/mongodb`
- Caching in front of ES → `data/_shared/caching-patterns` + `data/redis`
- Vector embeddings producer → application code; this skill consumes them
- **Inbound** (this skill is the destination): self-hosted full-text/semantic search from `data/mongodb/references/indexing.md`; vector search beyond a cache from `data/redis/references/data-structures.md`
- Verifying tenant DLS actually isolates (cross-tenant leak matrix) → the `qa-security` peer + `qa/<stack>/skills/security-testing/access-control-testing`
- IaC / cloud deploy for the cluster (OpenSearch Service, Elastic Cloud) → cloud provisioning / IaC for the store itself has no owning skill in this library yet; out of this domain's scope
