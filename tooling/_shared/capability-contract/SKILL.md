---
name: capability-contract
description: Use when a project (or part of it) must become an agent-drivable surface — derive the capabilities, typed input/output contracts, flows and runtime dependencies into a reviewable contract document. Triggers "expose this project to an agent", "what tools should the MCP have", "spec the CLI commands". Do NOT use to implement the surface (`tooling:mcp-builder` / `tooling:cli-builder`), to plan a REST API (`dev:plan-api-surface`), or to document a feature for humans (`dev:doc-feature-trace`).
---

# Capability Contract — what the tool exposes, before it exists

An MCP server and a CLI are the same thing wearing different clothes: a set of **capabilities**, each with typed inputs, one predictable output shape, a fixed error vocabulary, and a stated place in a **flow**. Get that list right and both surfaces fall out of it mechanically. Get it wrong and you ship forty tools an agent cannot compose.

This skill produces the **one document both builders consume**. `tooling:mcp-builder` renders each capability as a tool; `tooling:cli-builder` renders each capability as a subcommand. Neither invents capabilities — if it is not in this document, it is not in the surface.

**Read `references/output-contract.md` before writing any capability block.** It fixes the envelope, pagination, error body, and token budget that every capability inherits; the per-capability blocks are only meaningful as deltas against it.

## When to use

- Step 1 of a `tooling-engineer` run, before any MCP or CLI code exists
- An existing MCP/CLI is being extended and the delta needs a contract (`EXTEND` — inherit the existing envelope and naming, spec only the new capabilities)
- An existing MCP/CLI has no written contract and is about to be changed (`RESUME` — recover the contract from the code, mark recovered rows `#confirmed`, then spec the delta)

## When NOT to use

- The ask is to write the server or the CLI → `tooling:mcp-builder` / `tooling:cli-builder`
- The ask is to design a REST API for human/browser clients → `dev:plan-api-surface` owns that; this skill *consumes* its output when one exists
- The ask is to explain a feature to a person → `dev:doc-feature-trace` / `dev:doc-business-model`
- The target is a third-party HTTP API with no local project → the vendor `ai-development/mcp-builder` skill owns the API-wrapping lane; this one derives from a codebase

## Output

**`docs/specs/<NNN>-<surface>-tool-contract.md`**, where `<surface>` names the thing being exposed (`orders`, `deploy`, `test-data`).

**A filled golden example is at `references/example-contract.md`** — shapes normative, domain content illustrative.

---

## Procedure

### Step 1 — Choose the source of truth

Take the highest-fidelity input available and say in the document which one you used:

| Input available | What you do |
|---|---|
| An approved `api-surface.md` / OpenAPI / gRPC proto | **Map, don't re-derive.** Each operation is a candidate capability; skip to Step 3 |
| A codebase | **Derive** (Step 2) from entry points, then confirm |
| Only a prose description of functionality | Ask for the entry points. Deriving a contract from prose alone produces a surface that does not compile |

Record the **detected stack and version** (TFM · JDK + Boot BOM · Node major from `package.json` · package manager) — it decides the builder's implementation lane, and it is the first thing the builders read out of this document.

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
- **Never expose a capability the caller cannot be trusted with.** Anything that deletes, spends money, mutates production, or reads secrets is either out of scope or explicitly flagged `destructive` and gated (see Step 6).

### Step 3 — The capability table

The whole surface on one screen. This table is what an agent's tool list will look like:

| Capability | Intent | Kind | Source | Auth | Idempotent | Flow |
|---|---|---|---|---|---|---|
| `orders.list` | Page the caller's orders, filterable by status | read | `OrdersController.cs:31` | `orders:read` | yes | Place |
| `orders.get` | One order with its lines | read | `OrdersController.cs:52` | `orders:read` | yes | Place |
| `orders.place` | Create a pending order from a cart | write | `OrdersController.cs:70` | `orders:write` | via key | Place |
| `orders.cancel` | Move `pending\|paid` → `cancelled` | destructive | `OrdersController.cs:96` | `orders:write` | no | Cancel |

Rules:

- **`Capability` is `<noun>.<verb>`, lower-case, dot-separated.** It is the single id both builders derive their names from: the MCP tool is `<prefix>_<noun>_<verb>`, the CLI is `<bin> <noun> <verb>`. One id, two renderings, no divergence.
- **The noun is the domain object, singular or plural consistently across the whole surface** — pick one and never mix. The verb is `list` · `get` · `create`/`place` · `update` · `delete` · or the domain's own transition verb.
- **`Kind` is one of `read` · `write` · `destructive`.** It is not decoration: it drives the MCP annotations and the CLI's confirmation prompt, and it is the only thing standing between an agent and an irreversible action.
- **`Intent` is a sentence an agent can route on**, not a restatement of the name. "Page the caller's orders, filterable by status" routes; "lists orders" does not.
- **`Flow` names the flow from Step 5** this capability participates in. A capability in no flow is either a leaf lookup (fine — say so) or unjustified (cut it).

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

Rules:

- **Every input carries an `Example`.** It is what the agent copies on its first call, and it is the fixture the builder's smoke test uses.
- **Every input whose value comes from another capability says so** in `Notes` (`from products.search`). This is how an agent learns the surface is composable without being told.
- **The error table's last column is the point of the table.** "What the caller does next" is the difference between an agent recovering and an agent retrying the same failing call six times.
- **Enumerate enums.** `status` as `string` is a wasted turn; `status` as `pending|paid|cancelled` is a correct first call.

### Step 5 — Flows

The ordered sequences an agent actually runs. This is the section that makes the surface usable and the one most often skipped:

````markdown
#### Flow: Place an order
1. `customers.list` — resolve the customer by email → `customerId`
2. `products.search` — resolve each line by SKU → `productId`
3. `orders.place` — with the ids from 1–2 and a fresh `idempotencyKey` → `orderId`
4. `orders.get` — confirm `status == "pending"`

**Carries:** `customerId` (1→3) · `productId` (2→3) · `orderId` (3→4)
**Fails at 3 with `conflict`:** drop or reduce the named line and repeat 3 with the **same** `idempotencyKey`.
````

- **Name the field that carries between steps.** A flow whose steps do not share a field is not a flow, it is a list.
- **State the recovery for the most likely failure**, per flow, once — not per capability.
- **A flow that needs a capability the table does not have is the finding.** Add the capability or state the gap; do not let the flow assume it.

### Step 6 — Dependencies and the trust boundary

What must be true for any of this to run, and what the surface refuses to do:

| Dependency | Kind | Required by | How it is supplied |
|---|---|---|---|
| `API_BASE_URL` | config | all | env var, no default |
| `API_TOKEN` | secret | all | env var, read at startup, **never** a tool/CLI input |
| PostgreSQL 18 | service | `orders.*` | reached through the API, not directly |
| Redis 7.4 | service | `orders.place` | idempotency store |

Then state, explicitly:

- **Which capabilities are `destructive`** and what gate they carry (MCP: `destructiveHint` + a required confirmation input; CLI: an interactive prompt plus `--yes`).
- **What is deliberately not exposed** and why — the single most useful line in the document for the next person who asks "why can't the agent do X".
- **Where secrets come from.** A credential is never a capability input; it is process configuration. A contract that accepts a token as a parameter is a blocker finding.

### Step 7 — Confirm before anyone builds

Present the capability table, the flows, and the not-exposed list, and get them confirmed. Ask about **inferences, not preferences** — the things you guessed from code and could have guessed wrong:

- capabilities you derived that have no obvious consumer
- anything you classified `destructive` that may be routine, or `write` that may be irreversible
- ids you could not resolve to a source location

Everything the code answers, answer from the code. Do not ask the user to confirm the type of a parameter you can read.

**Exit gate:** capability table filled with a source location per row · a contract block per capability with examples and an error table · every capability in a flow or explicitly marked a leaf · dependency table with secrets sourced from config · the not-exposed list written · confirmation received.

---

## Anti-patterns

| Anti-pattern | Why it fails | Instead |
|---|---|---|
| One `execute` tool taking a free-text command | The agent has to guess a grammar you never documented; nothing is validated | One capability per operation, typed |
| A capability per HTTP route, mechanically | Ships `GET /health` and three paginated variants of the same list as separate tools | Map to intent, collapse variants, cut the unconsumed |
| Untyped `object` / `any` inputs | Moves validation from the schema to a runtime error the agent cannot pre-empt | Type every field; enumerate every enum |
| Errors as free prose | Agent cannot branch on them and retries blindly | Fixed code vocabulary + a "what next" column |
| Secrets as parameters | Leaks credentials into transcripts and shell history | Process config, read at startup |
| No flows section | Agent has tools but no idea in what order | Step 5 is not optional |
