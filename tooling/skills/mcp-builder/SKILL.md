---
name: tool-mcp-builder
description: Use when a project's capabilities must reach agents as an MCP server — render a confirmed capability contract as a schema-validated server: one tool per capability, one envelope, actionable errors, a smoke test. Triggers "build an MCP for this project", "expose these functions as MCP tools". Do NOT use to derive capabilities (`tool-capability-contract`), for a terminal surface (`tool-cli-builder`), or to wrap a third-party API with no local codebase (vendor `ai-development/mcp-builder`).
---

# MCP Builder — the contract, rendered as tools

An MCP server is a **projection of the capability contract**, nothing more. Every design question — what tools exist, what they accept, what they return, what they refuse — was answered in `docs/specs/<NNN>-<surface>-tool-contract.md`. This skill's job is to render that document into a server that compiles, validates its inputs, and returns the same envelope from every tool.

**Prerequisite: a confirmed capability contract.** No contract, no server — run `tool-capability-contract` first. Building tools from a vague description is how a surface ends up with an `execute(command: string)` tool.

**Read before writing code:** the contract's capability table, flows, and dependency section, plus `tooling/_shared/capability-contract/references/output-contract.md` — the envelope you are about to implement.

## When to use

- Step 2 of a `tooling-engineer` run, after the contract is confirmed
- An existing MCP server gains capabilities (`EXTEND` — read the existing server, inherit its naming, prefix, and envelope; add only the delta)
- A CLI built from the same contract now needs an MCP twin — the contract is already there; only the rendering is new

## When NOT to use

- No local project, just a third-party HTTP API → the vendor `ai-development/mcp-builder` skill owns the API-wrapping lane and its evaluation harness
- The surface is for humans at a terminal → `tool-cli-builder`
- The ask is to *use* an existing MCP server → nothing to build

## Implementation lane

Decide once, from the contract's detected stack, and state which lane you took:

| Project stack | Lane | Why |
|---|---|---|
| Node / TypeScript | **In-process TypeScript** — the server imports the project's own modules | No network hop, types shared with the source |
| .NET, Java, Python, Go, anything else reached over HTTP | **TypeScript sidecar** over the project's HTTP API | The SDK is best-supported, `npx` distribution is trivial, and the project keeps one deployable |
| .NET or Java **with no HTTP API**, where the capabilities are in-process only | **Stack-native** — `ModelContextProtocol` (.NET) or Spring AI MCP (Java) | A sidecar cannot reach in-process code; do not add an HTTP API just to enable one |

TypeScript is the default because it is where the SDK is strongest — not because the project's stack is wrong. **Never up-level or rewrite the project to suit the tool surface.**

- **TypeScript (both TS lanes):** [`references/typescript.md`](references/typescript.md)
- **Stack-native .NET / Java:** [`references/stack-native.md`](references/stack-native.md)

## Transport

| Deployment | Transport |
|---|---|
| Local, per-developer, launched by the client | **stdio** — the default; simplest, no ports, no auth layer of your own |
| Shared / remote / multi-user | **Streamable HTTP, stateless JSON** — scales without sticky sessions |

Do not build both until something needs both. If the server may become remote later, keep transport wiring in one file so the change is one file.

---

## Procedure

### Step 1 — Orient

Read 2–3 existing files in the project before writing any: how it does config, how it does errors, how it calls its own API. Match that over this skill's defaults. If the project already ships an MCP server, read it and inherit its prefix and envelope — a second convention in the same repo is a defect.

Confirm the SDK version you actually have (`npm view @modelcontextprotocol/sdk version`, or the NuGet/Maven equivalent) and check the registration API against it before generating. **The MCP SDKs move; do not write from memory.**

### Step 2 — Project skeleton

One file per concern, flat until it hurts:

```
src/
  index.ts          server construction + transport wiring
  config.ts         env reading, validated at startup, fails loud
  client.ts         the typed client that reaches the project (HTTP or in-process import)
  envelope.ts       ok/error envelope + error-code mapping, used by every tool
  tools/
    orders.ts       one file per capability noun, one registration per capability
    products.ts
```

No `BaseTool` class, no registry abstraction, no plugin loader. Registering a tool is three lines; a framework to generate three lines is the abstraction the library's simplicity rule exists to prevent.

### Step 3 — Config, fail-fast

Read every dependency from the contract's dependency table at startup, validate it, and **exit non-zero with a message naming the missing variable** if it is absent. A server that starts without its token and fails on the first tool call has moved a config error into an agent's transcript.

Secrets are read from the environment. **No capability takes a credential as an input** — if the contract has one, that is a blocker, fix the contract.

### Step 4 — One tool per capability

Mechanical, per row of the capability table:

| Contract | MCP |
|---|---|
| Capability id `orders.place` | Tool name `orders_place` (or `<prefix>_orders_place` if the surface needs disambiguating) |
| Intent sentence | Tool `description`, verbatim, plus the flow note |
| Inputs table | The input schema — one field per row, with constraints and the `Example` in the field description |
| Output shape | `outputSchema`, and `structuredContent` on the response |
| Kind `read` | `readOnlyHint: true`, `destructiveHint: false` |
| Kind `write` | `readOnlyHint: false`, `destructiveHint: false`, `idempotentHint` per the table |
| Kind `destructive` | `destructiveHint: true` **and** a required `confirm` boolean that must be `true` |
| Errors table | The error mapping in `envelope.ts` — code, message, `field`, `retryable` |

Rules that are not negotiable:

- **Every field is typed and constrained in the schema**, not validated by hand in the handler. Constraints in the schema are visible to the agent before it calls; constraints in the handler are only visible after it fails.
- **Every field description ends with its example.** It is the agent's first-call template.
- **Enums are enums.** A `status: string` where the contract says `pending|paid|cancelled` is a wasted turn every single call.
- **Every tool returns the envelope** from `envelope.ts` — both `structuredContent` (the object) and `content[0].text` (a one-or-two-line human summary of the same facts). Never a raw upstream payload.
- **Errors never throw out of a handler.** Catch at the client boundary, map to a code from the closed vocabulary, and return `ok: false` with the "what next" sentence from the contract. An uncaught exception reaches the agent as an opaque protocol error it cannot act on.
- **Paging and the 25 KB budget are enforced in the handler**, not hoped for from upstream. Clamp `pageSize` to the contract's maximum; set `meta.truncated` when you cut.
- **Tools that name each other do so in the description.** `products_search` says "ids from here are what `orders_place` expects"; that one sentence is what makes the flow discoverable without a prompt.

### Step 5 — Tool descriptions that route

The description is the only thing an agent reads before choosing. Three lines, in this order:

1. **What it does**, the contract's intent sentence.
2. **When to use it / when not** — one clause, naming the sibling it is confused with.
3. **Where its inputs come from**, if they come from another tool.

> `orders_place` — Creates a pending order from resolved customer and product ids and reserves stock. Use after resolving ids with `customers_list` and `products_search`; to check an existing order use `orders_get`. Requires a caller-generated `idempotencyKey`; retrying with the same key returns the original order.

Long prose in a description costs context on every single request. Three lines, no fluff, no markdown headings.

### Step 6 — Flows become nothing

Deliberately: flows are **not** encoded as a tool. Do not build an `place_order_flow` mega-tool that runs the whole sequence — it collapses the agent's decision points and hides the failure it is supposed to handle. Flows live in:

- the **tool descriptions** ("ids from here go to X"), and
- the server's **README**, one short section per flow, copied from the contract.

Build a workflow tool only when the steps are genuinely atomic — they must all succeed or all be undone — and say why in the code's one permitted doc comment.

### Step 7 — Build, smoke, verify

1. **Build.** The project's own build script (from `package.json`, run with the package manager `packageManager` names, or the stack's equivalent) must be clean — no errors, no `any`, `strict: true`.
2. **Smoke each tool once** with the `Example` values from the contract, through the MCP Inspector (`npx @modelcontextprotocol/inspector`) or a scripted stdio client. Every tool, including the ones you are sure about.
3. **Prove one full flow** end to end, using only outputs from the previous step as inputs to the next. If a field you need is not in the previous tool's output, that is a contract defect — fix the contract, then the code.
4. **Prove one failure path** — force a `validation_failed` and a `conflict`, and check the agent-facing message actually says what to do next.
5. **Destructive tools:** prove the `confirm` gate refuses without it.

Report what you ran and what it returned. "It should work" is not a verification. Inside a `Gate: none` plan task, run none of these checks and report the server as "written, not run".

### Step 8 — Ship the registration snippet

The server is not delivered until someone can install it. Emit, in the README:

- the exact client config block (command, args, env var names — **never values**),
- what each env var is and where to get it,
- the flow sections from the contract,
- the tool table: name, kind, one-line intent.

---

## Anti-patterns

| Anti-pattern | Why it fails | Instead |
|---|---|---|
| One `execute` / `query` tool taking free text | Nothing is validated, the grammar is undocumented, the agent guesses | One tool per capability, typed |
| A `BaseTool` class + registry + factory for six tools | Three lines of registration wrapped in thirty of indirection | Register directly; abstract on the second real need |
| Returning the raw upstream JSON | Leaks internals, breaks the envelope, blows the token budget | Map to the contract's output shape |
| Throwing out of a handler | Reaches the agent as an opaque protocol error | Catch, map to a code, return `ok: false` |
| Descriptions that are paragraphs | Paid for on every request, in every session | Three lines |
| A tool per HTTP route | Ships `health_get` and three list variants | The contract already did this cut — follow it |
| Credentials as tool inputs | Leaks into transcripts | Env vars, read at startup |
| `destructiveHint` on everything, "to be safe" | The hint stops meaning anything | Set it from the contract's `Kind`, exactly |
