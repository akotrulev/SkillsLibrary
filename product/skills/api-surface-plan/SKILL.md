---
name: plan-api-surface
description: Use when a feature spec needs its ## API surface section (endpoints, typed bodies, errors, paging). Triggers "what endpoints does this feature need". Not for tables (plan-data-model).
disable-model-invocation: true
---

# API Surface — the feature spec's `## API surface` section

What a Swagger document would say about one feature, written at design time in a form a human can review: three levels (**service → resource → endpoint**), a one-line purpose and auth requirement per endpoint, typed request and response bodies, and every error the endpoint can return, most of them inherited from a **catalog defined once** rather than re-listed per endpoint.

The section has two audiences and both matter: the `be-<stack>` agent that implements it, and the `qa-api-<stack>` agent that writes contract tests against it. The validation catalog is, on purpose, a ready-made negative-test matrix.

`/product:plan-feature` reads this file in its step 8 when the feature adds or changes an endpoint, after the `## Data model`, and presents the result as one section of the spec. The user's approval of that section, then of the spec, is the gate; there is no other.

## Input

- **The spec so far:** the goal, the decisions from the interview, `## Acceptance criteria`, the `## Data model` (resources derive from its entities, state-conflict rules from its state diagrams, duplicate rules from its unique constraints) and, when the feature has screens, the `## Experience` (**response shapes derive from what the screens need**: an aggregate the tables lack, such as `seatsLeft`, becomes a computed field decided here).
- **The system plan's §3, when the feature came from one:** the error envelope, ids, pagination, auth and roles, and the modules (`Service` comes from them). Read the specs of the features this one depends on: their `## API surface` holds the API-wide contract, the shared schemas and the endpoints already designed.
- **Standalone (no system plan):** the existing API, from its OpenAPI document or its route definitions. What is there is `#observed` with `file:line`.

**Read [`references/validation-catalog.md`](references/validation-catalog.md) before writing any endpoint block.** It is the standard set every endpoint inherits, and the per-endpoint blocks are only meaningful as deltas against it.

## Output

The `## API surface` section of `docs/specs/NNN-<feature>-design.md`, with these subsections in this order: `### Builds on` · `### API-wide contract` · `### Endpoint map` · `### Shared schemas` · `### Validation & error contract` · `### Endpoints` · `### Pagination, filtering & sorting` · `### Versioning & deprecation` · `### Outbound webhooks` · `### Consumers` · `### Open questions`. A subsection with nothing to say is one line saying so. When the spec has an `## Experience`, also fill its `### Screen ↔ endpoint matrix`.

[`references/example-api-surface-section.md`](references/example-api-surface-section.md) is a filled section from the toy spec all four design skills share: its shapes are normative, its domain content illustrative.

## Scope

**This feature only, on top of what exists.** An endpoint, a shared schema or an API-wide decision that §3 or an earlier feature's spec defined is **referenced, never redefined**: a row in `### Builds on` naming where it is defined. A change the feature makes to one (a response field added, a new error) is a delta block under `### Endpoints`, headed with where the endpoint is defined, holding only what changes; a breaking change to it is a question to the user, never a quiet edit. A change to §3 itself (the error envelope, the pagination style, the auth model) is put to the user as "this changes the system plan's §3 <line>: keep it or change it?", and `plan-feature`'s close-out records an approved change.

---

## Procedure

### Step 1 — The API-wide contract: inherit, then state deviations

The contract is §3's and the earlier specs'; list it in one line per source and add only what nothing above decided. Where nothing did (the first feature with an API, or a standalone feature in a new repo), decide it here, once:

| Decision | Default | Note |
|---|---|---|
| **Base path & versioning** | `/api/v1/...`, major version in the path | URL versioning is the cheapest to route and test. Header versioning only if the org already does it |
| **Auth scheme** | Bearer JWT, per §3's provider | Name the claim that carries permissions or roles, and the one that carries tenant |
| **Error body** | RFC 9457 `application/problem+json` | One shape for every failure, including validation. See the catalog |
| **List envelope** | `{ items, page, pageSize, total }` or cursor `{ items, nextCursor }` | One for the whole API; a mixed API is a permanent client tax |
| **Casing** | `camelCase` JSON | Match the existing API if there is one |
| **Dates** | ISO 8601, UTC, `Z` suffix | Local-time fields are separate and explicitly named |
| **Idempotency** | `Idempotency-Key` on non-idempotent POSTs that move money or cause side effects | Not on every POST; say which and why |
| **Concurrency** | `ETag` + `If-Match` on resources with a version column | Ties to the `## Data model` concurrency choice |
| **Correlation** | `traceparent` accepted and propagated | The observability handshake |

In an existing API, **the existing convention wins**, even where it differs from these defaults.

### Step 2 — The endpoint map

One row per endpoint this feature adds, and one per existing endpoint it changes, marked `changed`:

| Service | Resource | Method | Path | Name | Description | Auth | Idempotent | Success |
|---|---|---|---|---|---|---|---|---|
| Ordering | Orders | POST | `/api/v1/orders` | Place order | Creates a pending order from a cart | `orders:write` | via key | 201 |
| Ordering | Orders | POST | `/api/v1/orders/{orderId}/cancel` | Cancel order | Moves `pending\|paid` → `cancelled` | `orders:write` | no | 200 |

- **`Service` is the deployable** (or the module, in a monolith), taken from §3, not invented.
- **Model state transitions as actions on sub-paths**, not as a `PATCH` that sets a status field. `POST /orders/{id}/cancel` is checkable, auditable and maps to one permission; `PATCH {status: "cancelled"}` puts the state machine in the client.
- **`Auth` is a specific permission, scope or role**, not "authenticated". "Any signed-in user" is a real answer and says so explicitly. This column is `qa-security`'s starting map for BOLA/BFLA testing.
- **Every resource that can be listed has a stated default sort**, or paging is nondeterministic.
- **Cover the lifecycle the feature adds:** each transition in the `## Data model` state diagram that this feature introduces has an endpoint.
- **No endpoint without a consumer.** A screen in `## Experience`, a background job or a named integration calls it, or it is dropped.

### Step 3 — Per-endpoint contract blocks

One block per new endpoint; one delta block per changed one. The typed tables are the Swagger equivalent, enough to generate DTOs from:

````markdown
#### POST `/api/v1/orders` — Place order
**Purpose:** creates a `pending` order from the caller's cart and reserves stock.
**Auth:** `orders:write`; tenant taken from the token, never from the body.
**Acceptance:** AC1, AC2
**Idempotency:** `Idempotency-Key` header required; a repeat within 24h returns the original 201 body.

**Request body**
| Field | Type | Required | Constraints | Notes |
|---|---|---|---|---|
| `customerId` | uuid | yes | must exist, same tenant, `active` | → `customers.id` |
| `lines` | array | yes | 1–100 items | |
| `lines[].productId` | uuid | yes | must exist, same tenant, `sellable` | → `products.id` |
| `lines[].quantity` | int | yes | 1–999 | |

**Response 201**
| Field | Type | Notes |
|---|---|---|
| `id` | uuid | |
| `status` | enum | always `pending` here |
| `totalMinor` | int64 | server-computed; a client-supplied total is ignored, not trusted |

`Location: /api/v1/orders/{id}` · `ETag: "<version>"`

**Errors:** standard set, plus —
| Status | Condition | `type` slug |
|---|---|---|
| 409 | product out of stock | `insufficient-stock` |
| 409 | idempotency key reused with a different body | `idempotency-conflict` |
````

Rules:

- **Every endpoint names the acceptance criteria it proves** on an `**Acceptance:**` line under `**Auth:**`, citing the spec's own `AC<k>`. Every criterion with an outcome visible at the API lands on at least one endpoint; an endpoint with no criterion is either a missing criterion or an endpoint nobody asked for. A `Q` task writes its tests from this line, citing `<spec path> AC<k>`.
- **The `not-implemented` stub response (catalog V8.6) is never listed per endpoint.** It is part of the standard set and exists only while a contract-task stub does.
- **"Standard set, plus —" is the required form.** Never re-list 401/403/404/400 per endpoint; state only what is *additional or different*. A deliberate omission (a public health check has no 401) is a delta too.
- **Every request field maps to something real:** a column in `## Data model`, a computed value or a named external input.
- **Every screen data need maps to a response field:** walk `## Experience`'s data-needed lines; a need with no field is a missing endpoint or an undeclared computed field, and a response field nothing reads is a candidate for removal.
- **Server-computed fields are marked and never trusted from the client:** totals, statuses, timestamps, ids, tenant. A security rule, not a style one.
- **Response fields are chosen, not dumped.** Say what is deliberately not returned (password hashes, internal ids, other tenants' data).

### Step 4 — Shared schemas

An object shape used by more than one endpoint is defined once (`Money`, `PagedResult<T>`, `ProblemDetails`) and referenced by name. A shape an earlier spec defined is cited there, never copied.

### Step 5 — Apply the validation catalog

**The spec cites a copy of the catalog the project's readers can open**, never this skill's `references/` path, which resolves to nothing in their repo. The first spec in the project that writes an `## API surface` copies `references/validation-catalog.md` to `docs/specs/validation-catalog.md` and commits it with the spec; every later spec cites that copy and never copies it again.

Then state, in `### Validation & error contract`:

1. Which parts of the standard set apply (essentially all of it), and the open choices the catalog's last section lists, unless an earlier spec already made them: cite it.
2. This feature's instantiation of the parameterized rules: the referential-integrity rule for each id it accepts (exists → visible to the caller → in a valid state, in that order), the state-transition rules from the `## Data model` state diagrams, and the uniqueness rules from its unique constraints.
3. The rate-limit policy, if the feature changes it.

The per-endpoint blocks then carry deltas only.

### Step 6 — Cross-cutting

- **Pagination, filtering, sorting:** the parameter names, defaults, maximums and the stable-sort rule, or "per <source>" when inherited.
- **Versioning & deprecation:** how a breaking change ships (`Deprecation` / `Sunset` headers).
- **Webhooks the API emits**, if any: event names, payloads, delivery guarantees, signature scheme, retries. Webhooks the API *receives* belong to `## Integrations` (`product/skills/integration-plan`).
- **Consumers:** which frontend, service or partner uses which resource.

---

## Section template

```markdown
## API surface

### Builds on
| What | Defined in | This feature |
|---|---|---|

### API-wide contract
<"Per §3 and <spec>." plus each decision nothing above made, with its reason>

### Endpoint map
| Service | Resource | Method | Path | Name | Description | Auth | Idempotent | Success |
|---|---|---|---|---|---|---|---|---|

### Shared schemas
<new shapes defined once; inherited ones cited>

### Validation & error contract
**Standard set:** `docs/specs/validation-catalog.md`, applied to every endpoint below.
**This feature's instantiation:** referential integrity per id · state transitions (from `## Data model`) · uniqueness (from `## Data model`) · rate limiting

### Endpoints
<one contract block per new endpoint; one delta block per changed endpoint, headed with where it is defined>

### Pagination, filtering & sorting
### Versioning & deprecation
### Outbound webhooks
### Consumers
| Consumer | Resources used | Notes |
|---|---|---|

### Open questions
| # | Question | Blocks | Owner |
|---|---|---|---|
```

## Self-check before presenting the section

1. Every endpoint, schema or contract decision defined elsewhere is in `### Builds on`, and nothing defined elsewhere is redefined; every change to one is a delta block.
2. Every transition the feature adds to a `## Data model` state diagram has an endpoint; every non-transition is a `409` rule in the validation contract.
3. Every unique constraint the feature adds has a `409 duplicate` rule; every id it accepts has an "exists / visible / valid state" rule.
4. Every endpoint has an auth value naming a permission or role, or explicitly "any signed-in user" / "anonymous", and an `**Acceptance:**` line; every API-visible criterion lands on an endpoint.
5. Every request field maps to a column, a computed value or a named external input; every server-computed response field is marked.
6. No endpoint re-lists the standard error set; no endpoint lacks a consumer; every shape used twice is a shared schema.
7. When the spec has an `## Experience`: every data need resolves to a response field, and the screen ↔ endpoint matrix is filled.
8. The validation contract cites `docs/specs/validation-catalog.md`, copied there by this spec or an earlier one, not the skill's path.

## Version policy

The contract itself is version-agnostic; the **framework idioms it implies** are not. Keyed to `CLAUDE.md`'s Stack defaults: **.NET 10 primary / 8-9** (minimal APIs vs controllers is the project's existing choice, not a design decision) · **Java 21 + Spring Boot 3.x** · **Node 24 / 22**. RFC 9457 `application/problem+json` is the error shape across all three; on .NET that is the built-in `ProblemDetails`, on Spring `ProblemDetail`, on Node a hand-rolled shape. The spec states the contract; the executing agent picks the mechanism.
