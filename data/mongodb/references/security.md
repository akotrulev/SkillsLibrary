# MongoDB — Security

Authentication, the role model + least-privilege, in-use encryption (**CSFLE vs Queryable Encryption** — the headline), TLS, network isolation, multi-tenant isolation, and auditing. Tenant/user claims that drive access come from `auth/auth0-{stack}` + `auth/_shared/auth0-concepts`.

## Authentication

Auth is **off** on a fresh `mongod` — a database with `--auth` disabled and a reachable port is the classic "Mongo left open to the internet" breach. Turn it on, always.

| Mechanism | Use when |
|---|---|
| **SCRAM-SHA-256** | Default username/password. Fine for app→DB with credentials in a secret store. |
| **x.509 certificate** | Service identities without shared passwords; mutual-TLS environments. |
| **Cloud IAM** (Atlas: AWS IAM / Entra ID / GCP workload identity) | **Preferred on Atlas** — no long-lived DB password; the app authenticates with its cloud identity. |
| **LDAP / Kerberos** | Enterprise directory integration (self-managed Enterprise). |

Prefer **passwordless** (x.509 or cloud IAM) over SCRAM wherever the platform supports it. When you must use SCRAM, the password lives in Key Vault / Secrets Manager, never in a URI in config.

## Roles — least privilege

Built-in roles, scoped to a database:

- Runtime app user: **`readWrite` on its own database only**. Never `dbAdmin`, `dbOwner`, `clusterAdmin`, or `root`.
- Migration user: a separate identity with the index/DDL privileges the migration tool needs, used only by the migration job.
- Read-only analytics/report user: `read` on the database (point it at a secondary via read preference).
- Admin operations: a human/break-glass identity, not the app.

Define **custom roles** when built-ins are too coarse — grant specific actions on specific collections:

```javascript
db.createRole({
  role: 'ordersAppRW',
  privileges: [{
    resource: { db: 'orders', collection: '' },        // all collections in `orders`
    actions: ['find', 'insert', 'update', 'remove']    // no createIndex, no dropCollection
  }],
  roles: []
});
db.createUser({ user: 'orders-api', pwd: '…', roles: ['ordersAppRW'] });
```

The app can't create or drop indexes/collections — that's the migration identity's job. This is the Mongo equivalent of "runtime gets DML, migrations get DDL."

## In-use encryption: CSFLE vs Queryable Encryption

MongoDB has **three encryption layers**; only the in-use pair is a design decision:

| Layer | What it protects | Boundary |
|---|---|---|
| **Encryption at rest** (WiredTiger / Atlas / cloud KMS) | Data on disk | DBAs with server access still see plaintext in memory/queries |
| **TLS in transit** | Data on the wire | — |
| **In-use (client-side)** — CSFLE **or** QE | Field values — encrypted by the **driver**, the server never sees plaintext or keys | The real confidentiality boundary against the DB operator |

At-rest + TLS are table stakes (turn both on). The design choice is **which in-use scheme** for genuinely sensitive fields (PII, PHI, secrets):

| | **CSFLE** (Client-Side Field Level Encryption) | **Queryable Encryption (QE)** |
|---|---|---|
| Encryption | Deterministic (for queryable fields) or random | Structured/randomized |
| Queries on encrypted fields | **Equality only** (deterministic fields) | **Equality + range** (GA); prefix/suffix/substring in preview |
| Determinism leak | Deterministic fields leak equality (same plaintext → same ciphertext) | No — randomized, no frequency leak |
| Availability | 4.2+ | equality GA **7.0**, **range GA in the 8.0 line** |
| Recommendation | Legacy / equality-only need | **Default for new designs** — stronger, more query support |

Both keep keys in a **KMS** (AWS KMS / Azure Key Vault / GCP KMS / KMIP), with a data-encryption-key vault collection. The application driver holds the key material; the database node cannot decrypt. Encrypt only the fields that need it — encrypted fields have query and index limits.

> Version note: QE **range** queries require the 8.0 line. On 7.0 you get QE equality only — for range-queryable encryption you must be on 8.0.

## TLS & network isolation

- **TLS required** for every connection (`tls=true`; `+srv` Atlas URIs enforce it). Self-hosted: `net.tls.mode: requireTLS`.
- **Never expose `mongod`/`mongos` to the public internet.** Bind to private subnets; Atlas: use **private endpoints / VPC peering** and an IP access list, not `0.0.0.0/0`.
- Keep `mongod` off the default port on untrusted networks and behind a security group / firewall that only the app tier can reach.

## Multi-tenant isolation

Mongo has no row-level-security engine feature. The isolation options (the *choice* is `_shared/schema-design`; mechanics here):

- **Shared collection + `tenantId` field** — every document carries `tenantId`, every query and index leads with it, and a **single application data-access choke point** injects the tenant filter. Because the engine won't enforce it, this **requires a mandatory QA test** proving no query can return another tenant's data (the test replaces the missing engine guarantee). Compound every index with `tenantId` first (ESR: it's an equality field).
- **Database-per-tenant** — strong isolation, per-tenant backup/restore, but connection and operational overhead grows with tenant count; good for tens/low-hundreds of tenants.
- **Collection-per-tenant** — middle ground; watch the total collection/index count ceiling.

Feed `tenantId` from the authenticated principal's claims (`auth/_shared/auth0-concepts`), never from a client-supplied parameter.

## Auditing

- **Enterprise / Atlas** ship a native **audit log** (auth events, DDL, CRUD by filter) — enable it for compliance; it's the audit source of truth.
- **Community server has no native audit log.** For an application-level change trail, capture writes via a **change stream** (`references/caching.md`) into an append-only `audit` collection, or write audit records in the same code path as the change. Don't pretend Community has server audit.
- Log auth failures and admin actions to the centralized log pipeline regardless of edition.

## Rules

- `--auth` on, always; no unauthenticated `mongod` reachable from anywhere.
- Prefer x.509 / cloud IAM over SCRAM; SCRAM passwords live in a secret store.
- Runtime user = `readWrite` on one database; migrations use a separate DDL identity; no app user with `dbAdmin`+.
- TLS on every connection; private networking + IP access list; never `0.0.0.0/0`.
- At-rest encryption + TLS are baseline; add CSFLE/QE for sensitive fields — **QE for new designs**.
- Multi-tenant shared-collection isolation is app-enforced → back it with a mandatory cross-tenant-leak QA test.
- Audit via native log (Enterprise/Atlas) or change-stream capture (Community); never assume Community audits.

## What NOT to do

- No `mongod` without auth; no public-internet binding; no `0.0.0.0/0` access list.
- No app connecting as `root`/`dbOwner`/`clusterAdmin`.
- No SCRAM password in a connection string committed to config.
- No CSFLE deterministic encryption on a high-cardinality-leak-sensitive field (it leaks equality) — use QE.
- No client-supplied `tenantId` trusted for isolation.
- No assuming the Community server writes an audit log.

## Handoffs

- Which fields are sensitive / the tenancy *pattern choice* → `data/_shared/schema-design`
- Tenant/user claims feeding `tenantId` and roles → `auth/auth0-{stack}` + `auth/_shared/auth0-concepts`
- Change-stream capture for an app-level audit trail → `references/caching.md`
- Verifying tenant isolation (the mandatory leak test) → `qa/{java,dotnet,typescript}/skills/db-testing/*` + `qa/{java,dotnet,typescript}/skills/security-testing/access-control-testing`
