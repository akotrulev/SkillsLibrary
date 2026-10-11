---
name: plan-api-surface
description: Use when a planned data model needs its API surface specified — a service → resource → endpoint table with typed request/response bodies, the shared validation/error catalog, and pagination/versioning contract. Triggers "what endpoints do we need", "plan the API surface", "spec the REST contract". Do NOT use to write controllers/DTOs/clients (`be-<stack>`), write API tests (`qa-api-<stack>`), manage an OpenAPI file (`qa/_shared/api-spec-assets`), or plan tables (`dev:plan-data-model`).
---

# API Surface Plan — the contract, before the code

What a Swagger document would say, written at plan time and in a form a human can review: three levels (**service → resource → endpoint**), a one-line purpose and auth requirement per endpoint, typed request and response bodies, and every error the endpoint can return — most of them inherited from a **catalog defined once** rather than re-listed 40 times.

The document has two audiences and both matter: the `be-<stack>` agent that implements it, and the `qa-api-<stack>` agent that writes contract tests against it. The validation catalog is, on purpose, a ready-made negative-test matrix.

**Prerequisites:** an approved `blueprint.md` and a written `data-model.md` — plus `experience-plan.md` when the initiative has a frontend. Resources derive from entities; state-conflict rules derive from lifecycle diagrams; duplicate rules derive from unique constraints; **response shapes derive from what the screens need** (`experience-plan.md` §4's data-needed lines — an aggregate the tables lack, such as `bookedCount`, becomes a computed field decided here). On finishing, fill the experience plan's §5 screen ↔ endpoint matrix and hand the file back.

**Read `references/validation-catalog.md` before writing any endpoint block.** It is the standard set every endpoint inherits, and the per-endpoint blocks are only meaningful as deltas against it.

## When to use

- Step 4 of a `solution-planner` run (after the experience plan, which is skipped when nothing is user-facing)
- A new functional area adds endpoints to an existing API (`EXTEND` — plan the delta, inherit the existing envelope and conventions)
- An existing API needs its contract documented as the baseline for planned changes (`RESUME` — read routes and DTOs out of the code, mark `#confirmed`, then plan the delta)

## When NOT to use

- The project already keeps a committed OpenAPI/Swagger asset and the ask is to update from a newer spec → `qa/_shared/api-spec-assets` owns that diff-driven lane
- The ask is to implement or to test the endpoints → `be-<stack>` / `qa-api-<stack>`
- The protocol is GraphQL or gRPC → the three-level table still works (service → type/service → operation), but the envelope rules differ; note it and keep the error semantics native to the protocol (`{data,errors}` / gRPC status codes), not HTTP status codes translated badly

## Output

**`docs/plans/<NNN>-<initiative>/api-surface.md`** in the initiative folder.

**A filled golden example is at `references/example-api-surface.md`** (the shared `001-workshop-booking` pack — shapes normative, domain content illustrative).

---

## Procedure

### Step 1 — Establish the API-wide contract

Decide once, at the top; every endpoint inherits it and only deviations are stated:

| Decision | Default | Note |
|---|---|---|
| **Base path & versioning** | `/api/v1/...`, major version in the path | URL versioning is the cheapest to route and test. Header versioning only if the org already does it |
| **Auth scheme** | Bearer JWT, per the blueprint's provider | Name the claim that carries permissions and the one that carries tenant |
| **Error body** | RFC 9457 `application/problem+json` | One shape for every failure, including validation. See the catalog |
| **List envelope** | `{ items, page, pageSize, total }` or cursor `{ items, nextCursor }` | Pick one for the whole API — a mixed API is a permanent client tax |
| **Casing** | `camelCase` JSON | Match the existing API if there is one |
| **Dates** | ISO 8601, UTC, `Z` suffix | Local-time fields are separate and explicitly named |
| **Idempotency** | `Idempotency-Key` on non-idempotent POSTs that create money or side effects | Not on every POST — say which and why |
| **Concurrency** | `ETag` + `If-Match` on resources with a version column | Ties directly to `data-model.md`'s concurrency choice |
| **Correlation** | `traceparent` accepted and propagated | The observability handshake |

In an existing API, **the existing convention wins**, even where it differs from these defaults. Record what it does.

### Step 2 — The three-level table

The map of the whole surface, readable in one screen. One row per endpoint:

| Service | Resource | Method | Path | Name | Description | Auth | Idempotent | Success |
|---|---|---|---|---|---|---|---|---|
| Ordering | Orders | GET | `/api/v1/orders` | List orders | Paged orders for the caller's tenant, filterable by status | `orders:read` | yes | 200 |
| Ordering | Orders | POST | `/api/v1/orders` | Place order | Creates a pending order from a cart | `orders:write` | via key | 201 |
| Ordering | Orders | GET | `/api/v1/orders/{orderId}` | Get order | Single order with its lines | `orders:read` | yes | 200 |
| Ordering | Orders | POST | `/api/v1/orders/{orderId}/cancel` | Cancel order | Moves `pending\|paid` → `cancelled` | `orders:write` | no | 200 |

Rules:

- **`Service` is the deployable** (or the module, in a monolith) — it comes from the blueprint, not from invention.
- **Model state transitions as actions on sub-paths**, not as a `PATCH` that sets a status field. `POST /orders/{id}/cancel` is checkable, auditable, and maps to one permission; `PATCH {status: "cancelled"}` puts the state machine in the client.
- **`Auth` is a specific permission or scope**, not "authenticated". "Any logged-in user" is a real answer and should say so explicitly. This column is `qa-security`'s starting map for BOLA/BFLA testing, so a vague value costs a real test.
- **Every resource that can be listed needs a stated default sort**, or paging is nondeterministic.
- **Cover the whole lifecycle** for each entity: create, read one, list, update, the state transitions from the state diagram, delete (and whether delete is soft, per `data-model.md`).
- **No endpoint without a consumer.** If nothing in the blueprint or a frontend plan calls it, either name the consumer or drop it. Speculative endpoints are the cheapest thing to add and the most expensive to keep.

### Step 3 — Per-endpoint contract blocks

One block per endpoint. The typed tables are the Swagger equivalent — enough to generate DTOs from, without hand-writing OpenAPI:

````markdown
#### POST `/api/v1/orders` — Place order
**Purpose:** creates a `pending` order from the caller's cart and reserves stock.
**Auth:** `orders:write`; tenant taken from the token, never from the body.
**Idempotency:** `Idempotency-Key` header required; a repeat within 24h returns the original 201 body.

**Request body**
| Field | Type | Required | Constraints | Notes |
|---|---|---|---|---|
| `customerId` | uuid | yes | must exist, same tenant, `active` | → `customers.id` |
| `currency` | string(3) | yes | ISO 4217, in the tenant's enabled set | |
| `lines` | array | yes | 1–100 items | |
| `lines[].productId` | uuid | yes | must exist, same tenant, `sellable` | → `products.id` |
| `lines[].quantity` | int | yes | 1–999 | |
| `note` | string | no | ≤ 500 chars | |

**Response 201**
| Field | Type | Notes |
|---|---|---|
| `id` | uuid | |
| `orderNumber` | string | tenant-unique, generated |
| `status` | enum | always `pending` here |
| `totalMinor` | int64 | server-computed; a client-supplied total is ignored, not trusted |
| `currency` | string(3) | |
| `lines[]` | object[] | `productId`, `quantity`, `unitPriceMinor`, `lineTotalMinor` |
| `placedAt` | datetime | |

`Location: /api/v1/orders/{id}` · `ETag: "<version>"`

**Errors:** standard set, plus —
| Status | Condition | `type` slug |
|---|---|---|
| 409 | product out of stock | `insufficient-stock` |
| 409 | idempotency key reused with a different body | `idempotency-conflict` |
| 422 | currency not enabled for the tenant | `currency-not-enabled` |
````

Rules:

- **"Standard set, plus —" is the required form.** Never re-list 401/403/404/400 per endpoint; state only what is *additional or different*. If an endpoint deliberately omits part of the standard set (a public health check has no 401), say so explicitly — that is a delta too.
- **Every request field maps to something real** — a column in `data-model.md`, a computed value, or a named external input. A field that maps to nothing is either a missing table or a field nobody needs.
- **Every screen data need maps to a response field** — walk `experience-plan.md` §4 line by line; a need with no field is a missing endpoint or a computed field you have not declared, and a response field no screen and no integration reads is a candidate for removal.
- **Server-computed fields are marked as such and are never trusted from the client.** Totals, statuses, timestamps, ids, tenant. This is a security rule, not a style one.
- **Response fields are chosen, not dumped.** Say what is deliberately not returned (password hashes, internal ids, other tenants' data, soft-deleted rows).
- **Nested objects get their own field table** if they appear more than once — define a shared schema block near the top and reference it.

### Step 4 — Shared schemas

Any object shape used by more than one endpoint gets defined once in a **Shared schemas** section (`Money`, `Address`, `PagedResult<T>`, `ProblemDetails`, `AuditStamp`) and is referenced by name. Repeating a shape inline in six endpoints guarantees they drift.

### Step 5 — Apply the validation catalog

**First, copy `references/validation-catalog.md` into the initiative folder** as `docs/plans/<NNN>-<initiative>/validation-catalog.md`, and have the plan cite that copy. The plan's readers — the QA agents, Mission Control, the human — read the initiative folder, not this skill's directory; a skill-relative path in the written artifact resolves to nothing for them.

Then read the catalog and state, in the document's own **Validation & error contract** section:

1. Which parts of the standard set apply API-wide (essentially all of it).
2. The concrete instantiation of the parameterized rules for *this* API: the permission model, the not-found-vs-forbidden disclosure policy, the referential-integrity rule (a referenced id must exist **and** be visible to the caller **and** be in a valid state — all three, in that order), the state-transition rules taken from `data-model.md`'s state diagrams, and the uniqueness rules taken from its unique constraints.
3. The rate-limit policy, if any, and where it is enforced.

The per-endpoint blocks then carry deltas only.

### Step 6 — Cross-cutting sections

- **Pagination, filtering, sorting** — the exact parameter names, defaults, maximums, and the stable-sort rule. One contract for every list endpoint.
- **Versioning & deprecation** — how a breaking change ships, what notice consumers get, how a deprecated endpoint announces itself (`Deprecation` / `Sunset` headers).
- **Webhooks the API emits**, if any — event names, payload shapes, delivery guarantees, signature scheme, retry policy. (Webhooks the API *receives* are `dev:plan-integrations`'s.)
- **Consumers** — which frontend, service, or partner uses which resource. This is what makes a later breaking-change assessment possible.

---

## API surface template

```markdown
# <Initiative> — API Surface Plan

**Date:** YYYY-MM-DD · **Written by:** `dev:plan-api-surface`
**Blueprint:** `./blueprint.md` · **Data model:** `./data-model.md`

## 1. API-wide contract
| Decision | Choice | Note |
|---|---|---|

## 2. Endpoint map
| Service | Resource | Method | Path | Name | Description | Auth | Idempotent | Success |
|---|---|---|---|---|---|---|---|---|

## 3. Shared schemas
<!-- Money, Address, PagedResult<T>, ProblemDetails, … — defined once -->

## 4. Validation & error contract
**Standard set:** `./validation-catalog.md` (the copy in this folder), applied API-wide.
**This API's instantiation:**
- Permission model: …
- Not-found vs forbidden disclosure: …
- Referential integrity: exists → visible to caller → in a valid state
- State transitions (from `data-model.md`): …
- Uniqueness (from `data-model.md`): …
- Rate limiting: …

## 5. Endpoints
<!-- one contract block per endpoint: purpose, auth, idempotency, request table, response table, headers, "standard set, plus —" errors -->

## 6. Pagination, filtering & sorting
## 7. Versioning & deprecation
## 8. Outbound webhooks
## 9. Consumers
| Consumer | Resources used | Notes |
|---|---|---|

## 10. Open questions
| # | Question | Blocks | Owner |
|---|---|---|---|
```

## Self-check before handing off

1. Every entity in `data-model.md` that clients touch has a full endpoint set; every entity with none is deliberately internal, and said to be.
2. Every state-diagram transition has an endpoint; every non-transition is a `409` rule in section 4.
3. Every unique constraint has a `409 duplicate` rule; every FK has an "exists / visible / valid state" rule.
4. Every endpoint has an auth value that names a permission, or explicitly says "any authenticated user" / "anonymous".
5. Every request field maps to a column, a computed value, or a named external input; every server-computed response field is marked.
6. No endpoint re-lists the standard error set. No endpoint lacks a consumer.
7. Every shape used twice is a shared schema.
8. Every table in `data-model.md` is written or read by at least one endpoint, background job, or integration — list any orphans; a deliberately internal table counts, named as such.
9. When `experience-plan.md` exists: every §4 data need resolves to a response field, and §5 is filled — every user-facing endpoint on at least one screen, or named machine-to-machine.
9. The validation catalog is copied into the initiative folder and the plan cites the copy, not the skill's `references/` path.

## Handoffs

- **→ `dev:plan-experience`** — hand back its §5 screen ↔ endpoint matrix, filled.
- **→ `dev:plan-integrations`** (Step 5). Any endpoint that calls out to a third party names it there.
- **→ `be-<stack>` agents** — `api-models` equivalents and controllers/handlers come from these tables.
- **→ `qa-api-<stack>`** — this is the contract-test basis. The standard validation set is the negative-test matrix; the endpoint table is the positive one.
- **→ `qa-security`** — the Auth column is the BOLA/IDOR/BFLA permission matrix.
- **→ `fe-react` / `fe-blazor`** — the response shapes and the error envelope are what their data-fetching and error-handling layers bind to.
- **→ `qa/_shared/api-spec-assets`** — once a real OpenAPI document exists in the repo, that skill owns it and its diff-driven updates; this plan becomes the design record, not the source of truth. On a greenfield build, `dev:plan-delivery` schedules a standard task (after the last endpoint task) for the `be-<stack>` agent to generate and commit that asset from the implemented surface — the plan does not write it itself.

## Version policy

The contract itself is version-agnostic; the **framework idioms it implies** are not. Keyed to `CLAUDE.md`'s Stack defaults — **.NET 10 primary / 8-9** (minimal APIs vs controllers is the project's existing choice, not a plan decision) · **Java 21 + Spring Boot 3.x** · **Node 24 / 22**. RFC 9457 `application/problem+json` is the error shape across all three; on .NET that is the built-in `ProblemDetails`, on Spring `ProblemDetail`, on Node a hand-rolled shape — the plan states the contract, the executing agent picks the mechanism.
