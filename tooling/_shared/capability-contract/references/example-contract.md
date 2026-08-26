# Example — `docs/specs/001-orders-tool-contract.md`

> Shapes are normative; the domain content is illustrative. This is what a filled contract looks like at the point the builders are allowed to start.

---

# Orders tool contract

**Surface:** `orders` — the ordering slice of the Contoso storefront, exposed so an agent can place and track orders without a human in the browser.
**Source of truth:** derived from the codebase (`src/Contoso.Api`), cross-checked against `docs/plans/003-ordering/api-surface.md`.
**Detected stack:** .NET 10 (`net10.0`, `Directory.Build.props:7`) · API reached over HTTP · tool surface to be built in **TypeScript / Node 24** as a sidecar (see Dependencies).
**Envelope:** inherits `references/output-contract.md` unchanged — offset paging, default `pageSize` 50, max 200.

## Capabilities

| Capability | Intent | Kind | Source | Auth | Idempotent | Flow |
|---|---|---|---|---|---|---|
| `customers.list` | Find customers by email or name fragment | read | `CustomersController.cs:24` | `customers:read` | yes | Place |
| `products.search` | Find sellable products by SKU or name | read | `ProductsController.cs:31` | `catalog:read` | yes | Place |
| `orders.list` | Page the caller's orders, filterable by status | read | `OrdersController.cs:31` | `orders:read` | yes | Track |
| `orders.get` | One order with its lines | read | `OrdersController.cs:52` | `orders:read` | yes | Place, Track |
| `orders.place` | Create a pending order from resolved lines | write | `OrdersController.cs:70` | `orders:write` | via key | Place |
| `orders.cancel` | Move `pending\|paid` → `cancelled` | destructive | `OrdersController.cs:96` | `orders:write` | no | Cancel |

**Not exposed:** `POST /admin/orders/{id}/refund` (moves money, no agent workflow needs it) · `DELETE /orders/{id}` (hard delete, superseded by `orders.cancel`) · everything under `/internal/*` (operational, not domain).

## Contract blocks

#### `products.search` — Find sellable products
**Intent:** resolves a SKU or a name fragment to product ids, so `orders.place` can be called with real ids.
**Kind:** read · **Auth:** `catalog:read`
**Source:** `ProductsController.cs:31` → `ProductSearchQuery.cs:18`

**Inputs**
| Name | Type | Required | Constraints | Example | Notes |
|---|---|---|---|---|---|
| `query` | string | yes | 2–100 chars | `widget` | matches SKU exactly or name by prefix |
| `page` | int | no | ≥ 1, default 1 | `1` | |
| `pageSize` | int | no | 1–200, default 50 | `50` | |

**Output** — array of product summaries: `{ id, sku, name, priceMinor, currency, stock }`. Default sort `sku` ascending.
Summary projection only; there is no full product capability because no flow needs one.

**Errors** — `validation_failed` (query too short → lengthen it) · `unauthenticated` · `unavailable`.

---

#### `orders.place` — Place an order
**Intent:** creates a `pending` order from resolved customer and product ids and reserves stock.
**Kind:** write · **Auth:** `orders:write` (tenant comes from the token, never the input)
**Source:** `OrdersController.cs:70` → `PlaceOrderHandler.cs:24`
**Preconditions:** the customer exists and is `active`; every product is `sellable` with sufficient `stock`.

**Inputs**
| Name | Type | Required | Constraints | Example | Notes |
|---|---|---|---|---|---|
| `customerId` | uuid string | yes | exists, `active` | `3f2a1c8e-…` | from `customers.list` |
| `currency` | string(3) | yes | ISO 4217, tenant-enabled | `EUR` | |
| `lines` | array | yes | 1–100 items | | |
| `lines[].productId` | uuid string | yes | exists, `sellable` | `9c1b77d2-…` | from `products.search` |
| `lines[].quantity` | int | yes | 1–999 | `2` | |
| `idempotencyKey` | string | yes | 8–64 chars, stable across retries of one attempt | `place-7f3a` | a repeat within 24h returns the original order |

**Output** — `{ id, status, currency, totalMinor, lines: [{ productId, sku, quantity, unitPriceMinor }], createdAt }`.
`status` is one of `pending` · `paid` · `cancelled`.

**Errors**
| Code | When | What the caller does next |
|---|---|---|
| `validation_failed` | an input constraint fails | fix the field named in `error.field`, retry |
| `not_found` | `customerId` or a `productId` does not exist | re-resolve via `customers.list` / `products.search` |
| `conflict` | insufficient stock | `error.field` names the line index; reduce `quantity` or drop the line, retry with the **same** `idempotencyKey` |
| `forbidden` | token lacks `orders:write` | stop and report |

---

#### `orders.cancel` — Cancel an order
**Intent:** moves a `pending` or `paid` order to `cancelled` and releases the stock reservation.
**Kind:** **destructive** · **Auth:** `orders:write`
**Source:** `OrdersController.cs:96` → `CancelOrderHandler.cs:19`
**Gate:** requires `confirm: true`; the MCP tool carries `destructiveHint: true`, the CLI prompts unless `--yes` is passed.

**Inputs**
| Name | Type | Required | Constraints | Example | Notes |
|---|---|---|---|---|---|
| `orderId` | uuid string | yes | exists, status `pending\|paid` | `b41d…` | from `orders.list` / `orders.place` |
| `reason` | string | yes | 3–200 chars | `customer changed their mind` | written to the audit log |
| `confirm` | boolean | yes | must be `true` | `true` | refuses without it — the action is irreversible |

**Output** — `{ id, status: "cancelled", cancelledAt }`.

**Errors** — `conflict` (already `cancelled` or `shipped` → read `orders.get` and stop; there is no forward path) · `not_found` · `forbidden`.

## Flows

#### Flow: Place
1. `customers.list` — resolve the customer by email → `customerId`
2. `products.search` — resolve each requested SKU → `productId`
3. `orders.place` — ids from 1–2 plus a fresh `idempotencyKey` → `orderId`
4. `orders.get` — confirm `status == "pending"`

**Carries:** `customerId` (1→3) · `productId` (2→3) · `orderId` (3→4)
**Fails at 3 with `conflict`:** `error.field` names the line; reduce or drop it and repeat 3 with the same `idempotencyKey`.
**Fails at 3 with `not_found`:** an id went stale between 1–2 and 3; re-run the step that produced it.

#### Flow: Track
1. `orders.list` — filter `status=pending` → `orderId[]`
2. `orders.get` — per id, for the lines

**Carries:** `orderId` (1→2). Leaf flow; nothing mutates.

#### Flow: Cancel
1. `orders.get` — read current `status`
2. `orders.cancel` — only if `status` is `pending` or `paid`, with `confirm: true`

**Carries:** `orderId`. Step 1 is not optional: cancelling without reading is how an agent cancels a shipped order.

## Dependencies

| Dependency | Kind | Required by | How it is supplied |
|---|---|---|---|
| `CONTOSO_API_BASE_URL` | config | all | env var, no default; fail at startup if absent |
| `CONTOSO_API_TOKEN` | secret | all | env var, read once at startup — **never** a capability input |
| Contoso API (`net10.0`) | service | all | HTTP; the tool surface is a Node sidecar, not in-process |
| PostgreSQL 18 | service | all | behind the API; the tool never connects directly |
| Redis 7.4 | service | `orders.place` | idempotency store, behind the API |

**Trust boundary:** the surface is read-and-write on the caller's own tenant only. Tenant is taken from the token; no capability accepts a tenant id. `orders.cancel` is the only destructive capability and is gated. Admin, refund, and hard-delete routes are out of scope and will not be added without a stated agent workflow.

## Open questions

1. `orders.list` — should the default filter exclude `cancelled`? The API returns all statuses; every flow so far wants open orders. *(Assumed: no default filter; agent passes `status`.)*
2. `products.search` — `stock` is a live read and can be stale by the time `orders.place` runs. Accepted: the `conflict` path handles it.
