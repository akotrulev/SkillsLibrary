---
name: capability-contract
description: Use when deriving a project's agent-drivable capabilities into a typed contract before building an MCP or CLI. Triggers "what tools should the MCP have". Not for building it (mcp-builder).
disable-model-invocation: true
---

# Capability Contract — what the tool exposes, before it exists

An MCP server and a CLI are two renderings of one thing: a set of **capabilities**, each with typed inputs, one predictable output shape, a fixed error vocabulary, and a stated place in a **flow**. Get that list right and both surfaces fall out of it mechanically. Get it wrong and you ship forty tools an agent cannot compose.

This skill produces the **one document both builders consume**. `tooling:mcp-builder` renders each capability as a tool; `tooling:cli-builder` renders each capability as a subcommand. Neither invents capabilities — if it is not in this document, it is not in the surface.

**Read `references/output-contract.md` before writing any capability block.** It fixes the envelope, pagination, error body, and token budget that every capability inherits; the per-capability blocks are only meaningful as deltas against it.

## Output

**`docs/specs/<NNN>-<surface>-tool-contract.md`**, where `<surface>` names the thing being exposed (`orders`, `deploy`, `test-data`).

**A filled golden example is at `references/example-contract.md`** — shapes normative, domain content illustrative.

---

## Procedure

### Step 1 — Choose the source of truth

Take the highest-fidelity input available and say in the document which one you used:

| Input available | What you do |
|---|---|
| An approved spec's `## API surface` / OpenAPI / gRPC proto | **Map, don't re-derive.** Each operation is a candidate capability; skip to Step 3 |
| A codebase | **Derive** (Step 2) from entry points, then confirm |
| Only a prose description of functionality | Ask for the entry points. Deriving a contract from prose alone produces a surface that does not compile |

Record the **detected stack and version** (TFM · JDK + Boot BOM · Node major from `package.json` · package manager) — it decides the builder's implementation lane, and it is the first thing the builders read out of this document.

**Done when** the document names the input it used and records the detected stack and version.

### Step 2 — Derive candidate capabilities from the code

Read the **entry points**, not the whole codebase. In order of value:

| Source | What it yields |
|---|---|
| HTTP route table (controllers, `app.get`, `@RestController`, minimal-API `Map*`) | The operation list, its auth, and its DTOs — the richest source |
| Public application-service / use-case classes | The intent-level operations, usually cleaner than the routes |
| Existing CLI entry points, `package.json` `scripts`, `Makefile`, `dotnet run --project` targets | Operations someone already found worth naming |
| Background jobs / queue consumers | Capabilities that exist but have no synchronous caller yet |
| Domain enums, state machines, validation attributes | The constraint column of the input tables, for free |
| Config binding + `IOptions`/`@ConfigurationProperties`/`process.env` reads | The dependency section: what must be set for any of this to run |

For each candidate, record where it came from as `file:line`. A capability with no source location is an invention and must be marked as one.

**Then cut.** Comprehensive coverage is the default, but three cuts always apply:

- **No capability without a consumer.** Name the agent workflow that calls it, or drop it.
- **Collapse CRUD noise.** Five near-identical getters differing by one filter are one capability with a filter parameter, not five.
- **Never expose a capability the caller cannot be trusted with.** Anything that deletes, spends money, mutates production, or reads secrets is either out of scope or flagged `destructive` and gated per `tool-contract.md`.

**Done when** every candidate has a `file:line` or an invention mark, and every one that survives the cuts names its consumer.

### Step 3 — The capability table

The whole surface on one screen. This table is what an agent's tool list will look like:

| Capability | Intent | Kind | Source | Auth | Idempotent | Flow |
|---|---|---|---|---|---|---|
| `orders.list` | Page the caller's orders, filterable by status | read | `OrdersController.cs:31` | `orders:read` | yes | Place |
| `orders.get` | One order with its lines | read | `OrdersController.cs:52` | `orders:read` | yes | Place |
| `orders.place` | Create a pending order from a cart | write | `OrdersController.cs:70` | `orders:write` | via key | Place |
| `orders.cancel` | Move `pending\|paid` → `cancelled` | destructive | `OrdersController.cs:96` | `orders:write` | no | Cancel |

Capability ids, kinds, intents and flows follow `tool-contract.md`.

**Done when** the table lists every surviving capability with all seven columns filled.

### Step 4 — Per-capability contract blocks

One block per row. This is the part the builders compile into Zod / `Option<T>` / picocli annotations, so it must be typed, not prose:

````markdown
#### `orders.place` — Place an order
**Intent:** creates a `pending` order from the caller's cart and reserves stock.
**Kind:** write · **Auth:** `orders:write` (tenant comes from the token, never the input)
**Source:** `OrdersController.cs:70` → `PlaceOrderHandler.cs:24`
**Preconditions:** the customer exists and is `active`; every product is `sellable`.

**Inputs**
| Name | Type | Required | Constraints | Example | Notes |
|---|---|---|---|---|---|
| `customerId` | uuid | yes | exists, same tenant, `active` | `3f2a…` | from `customers.list` |
| `currency` | string(3) | yes | ISO 4217, tenant-enabled | `EUR` | |
| `lines` | array | yes | 1–100 items | | |
| `lines[].productId` | uuid | yes | exists, `sellable` | `9c1b…` | from `products.search` |
| `lines[].quantity` | int | yes | 1–999 | `2` | |
| `idempotencyKey` | string | yes | caller-generated, stable per attempt | `place-7f3` | repeat within 24h returns the original result |

**Output** — `order` object: `{ id, status, currency, total, lines[], createdAt }`.
`status` is one of `pending` · `paid` · `cancelled`. `total` is minor units, integer.

**Errors**
| Code | When | What the caller does next |
|---|---|---|
| `validation_failed` | any input constraint fails | fix the named field and retry — the error names the field path |
| `not_found` | `customerId` or a `productId` does not exist | re-resolve the id via `customers.list` / `products.search` |
| `conflict` | a product is out of stock | reduce `quantity` or drop the line; the error names the line index |
| `forbidden` | token lacks `orders:write` | stop and report — retrying will not help |
````

The block rules (examples, input provenance, the error table's last column, enumerated enums) are in `tool-contract.md`.

**Done when** every table row has a block with typed inputs, an `Example` on each input and an error table.

### Step 5 — Flows

The ordered sequences an agent actually runs. This is the section that makes the surface usable:

````markdown
#### Flow: Place an order
1. `customers.list` — resolve the customer by email → `customerId`
2. `products.search` — resolve each line by SKU → `productId`
3. `orders.place` — with the ids from 1–2 and a fresh `idempotencyKey` → `orderId`
4. `orders.get` — confirm `status == "pending"`

**Carries:** `customerId` (1→3) · `productId` (2→3) · `orderId` (3→4)
**Fails at 3 with `conflict`:** drop or reduce the named line and repeat 3 with the **same** `idempotencyKey`.
````

**Done when** every capability is in a flow or marked a leaf, and every flow names the fields it carries and the recovery for its likeliest failure.

### Step 6 — Dependencies and the trust boundary

What must be true for any of this to run, and what the surface refuses to do:

| Dependency | Kind | Required by | How it is supplied |
|---|---|---|---|
| `API_BASE_URL` | config | all | env var, no default |
| `API_TOKEN` | secret | all | env var, read at startup, **never** a tool/CLI input |
| PostgreSQL 18 | service | `orders.*` | reached through the API, not directly |
| Redis 7.4 | service | `orders.place` | idempotency store |

Then state which capabilities are `destructive`, what is deliberately not exposed and why, and where each secret comes from; the gates and the secret rule are in `tool-contract.md`.

**Done when** the dependency table lists every config value and secret with its source, and the destructive and not-exposed statements are written.

### Step 7 — Confirm before anyone builds

Present the capability table, the flows, and the not-exposed list, and get them confirmed. Ask about **inferences, not preferences** — the things you guessed from code and could have guessed wrong:

- capabilities you derived that have no obvious consumer
- anything you classified `destructive` that may be routine, or `write` that may be irreversible
- ids you could not resolve to a source location

Everything the code answers, answer from the code. Do not ask the user to confirm the type of a parameter you can read.

**Exit gate:** capability table filled with a source location per row · a contract block per capability with examples and an error table · every capability in a flow or explicitly marked a leaf · dependency table with secrets sourced from config · the not-exposed list written · confirmation received.

---

## Rules

The standards a contract must meet are the tooling rule file `tool-contract.md`. Read the project's copy in `.claude/rules/tooling/`, or the plugin's in `tooling/skills/rules/` when the project has not installed it (`/tooling:rules` does). Where it and this skill disagree, the rule file wins.
