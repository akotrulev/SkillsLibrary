# TypeScript MCP server — patterns

Node 24 (active LTS; 22 maintenance) · TypeScript `strict: true` · `@modelcontextprotocol/sdk`.

**Check the installed SDK version before you write registrations** — `npm view @modelcontextprotocol/sdk version`, then confirm the registration signature against that version's README (`https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`). The API below matches the current `McpServer` surface; if the installed major differs, the README wins over this file.

## Project

```
package.json      "type": "module", bin entry, build script
tsconfig.json     strict, NodeNext modules, outDir dist
src/index.ts      server + transport
src/config.ts     env, validated at startup
src/client.ts     typed client to the project
src/envelope.ts   ok/error shape + error mapping
src/tools/*.ts    one file per capability noun
```

`package.json` essentials:

```json
{
  "name": "@acme/orders-mcp",
  "type": "module",
  "bin": { "orders-mcp": "dist/index.js" },
  "scripts": { "build": "tsc", "start": "node dist/index.js" },
  "dependencies": { "@modelcontextprotocol/sdk": "^1", "zod": "^3" },
  "devDependencies": { "typescript": "^5", "@types/node": "^24" }
}
```

`dist/index.js` needs `#!/usr/bin/env node` as its first line for the `bin` entry to be executable — put it at the top of `src/index.ts`.

## Config — fail at startup, not at first call

```ts
import { z } from "zod";

const Env = z.object({
  CONTOSO_API_BASE_URL: z.string().url(),
  CONTOSO_API_TOKEN: z.string().min(1),
});

const parsed = Env.safeParse(process.env);
if (!parsed.success) {
  const missing = parsed.error.issues.map((i) => i.path.join(".")).join(", ");
  console.error(`Missing or invalid configuration: ${missing}`);
  process.exit(1);
}

export const config = parsed.data;
```

Log to `stderr` only. **On stdio transport, anything written to stdout corrupts the protocol stream** — a stray `console.log` is the single most common reason a server "connects and then does nothing".

## Envelope

```ts
export type Ok<T> = { ok: true; data: T; meta?: Record<string, unknown> };
export type Err = {
  ok: false;
  error: { code: ErrorCode; message: string; field?: string; retryable: boolean };
};

export type ErrorCode =
  | "validation_failed" | "not_found" | "conflict" | "forbidden"
  | "unauthenticated" | "rate_limited" | "unavailable" | "internal";

const RETRYABLE: ReadonlySet<ErrorCode> = new Set(["rate_limited", "unavailable"]);

export const ok = <T>(data: T, meta?: Record<string, unknown>): Ok<T> => ({ ok: true, data, meta });

export const err = (code: ErrorCode, message: string, field?: string): Err => ({
  ok: false,
  error: { code, message, field, retryable: RETRYABLE.has(code) },
});
```

And the one place every handler funnels through, so no tool can return a different shape:

```ts
export async function respond<T>(
  summarize: (data: T) => string,
  run: () => Promise<Ok<T> | Err>,
) {
  const result = await run().catch(toEnvelopeError);
  const text = result.ok ? summarize(result.data) : `${result.error.code}: ${result.error.message}`;
  return { content: [{ type: "text" as const, text }], structuredContent: result, isError: !result.ok };
}
```

`toEnvelopeError` maps upstream failures — HTTP status, driver exception, timeout — to the closed code vocabulary. It is the only `catch` in the codebase that is allowed to be broad, and it never lets an upstream message through unfiltered.

## Registering a tool

```ts
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { ok, err, respond } from "../envelope.js";
import { api } from "../client.js";

const OrderLine = z.object({
  productId: z.string().uuid().describe("Product id from products_search. Example: 9c1b77d2-…"),
  quantity: z.number().int().min(1).max(999).describe("Units to order, 1–999. Example: 2"),
});

const PlaceInput = {
  customerId: z.string().uuid().describe("Customer id from customers_list. Example: 3f2a1c8e-…"),
  currency: z.enum(["EUR", "USD", "GBP"]).describe("ISO 4217 currency. Example: EUR"),
  lines: z.array(OrderLine).min(1).max(100).describe("Order lines, 1–100."),
  idempotencyKey: z.string().min(8).max(64)
    .describe("Caller-generated, stable across retries of one attempt. Example: place-7f3a"),
};

const PlaceOutput = {
  ok: z.boolean(),
  data: z.object({
    id: z.string(),
    status: z.enum(["pending", "paid", "cancelled"]),
    currency: z.string(),
    totalMinor: z.number().int(),
    createdAt: z.string(),
  }).nullable(),
};

export function registerOrderTools(server: McpServer) {
  server.registerTool(
    "orders_place",
    {
      title: "Place an order",
      description:
        "Creates a pending order from resolved customer and product ids and reserves stock. " +
        "Use after resolving ids with customers_list and products_search; to read an existing order use orders_get. " +
        "Retrying with the same idempotencyKey returns the original order.",
      inputSchema: PlaceInput,
      outputSchema: PlaceOutput,
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true },
    },
    async (input) =>
      respond(
        (o) => `Order ${o.id} placed, status ${o.status}, total ${o.totalMinor} ${o.currency}.`,
        async () => {
          const res = await api.placeOrder(input);
          return res.kind === "conflict"
            ? err("conflict", res.message, res.field)
            : ok(res.order);
        },
      ),
  );
}
```

Notes:

- `inputSchema` / `outputSchema` take a **raw Zod shape object**, not `z.object(...)`. Wrapping it is the most common registration mistake.
- `.describe()` on every field. It is what the agent sees; a field without one is a guess.
- `z.enum` over `z.string()` wherever the contract enumerates values.
- The handler contains no validation — Zod already rejected bad input before it ran.

## Destructive tools

```ts
const CancelInput = {
  orderId: z.string().uuid().describe("Order id from orders_list or orders_place. Example: b41d…"),
  reason: z.string().min(3).max(200).describe("Recorded in the audit log. Example: customer changed their mind"),
  confirm: z.literal(true).describe("Must be true. Cancelling releases stock and cannot be undone."),
};
```

`z.literal(true)` makes the gate part of the schema: the agent cannot call it accidentally, and the refusal costs no round trip. Pair it with `annotations: { destructiveHint: true, idempotentHint: false }`.

## Paging and the token budget

```ts
const MAX_PAGE_SIZE = 200;
const DEFAULT_PAGE_SIZE = 50;

const pageSize = Math.min(input.pageSize ?? DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE);
const page = await api.listOrders({ ...input, pageSize });

return ok(page.items.map(toSummary), {
  page: page.page,
  pageSize,
  total: page.total,
  hasMore: page.page * pageSize < page.total,
});
```

Clamp rather than reject: an agent asking for 10 000 gets 200 and `hasMore: true`, which it can act on, instead of a validation error it has to think about. Map to a **summary projection** on lists — the full object belongs to `orders_get`.

## Transport

stdio, the default:

```ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new McpServer({ name: "orders-mcp", version: "1.0.0" });
registerOrderTools(server);
registerProductTools(server);

await server.connect(new StdioServerTransport());
```

Streamable HTTP, stateless, when the server is shared:

```ts
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";

const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
await server.connect(transport);
```

`sessionIdGenerator: undefined` selects the stateless mode — every request is self-contained, so the server scales horizontally with no sticky routing. Mount it behind the project's existing auth; do not invent an auth scheme in the tool layer.

## Testing

```bash
npm run build
npx @modelcontextprotocol/inspector node dist/index.js
```

Call every tool once with the contract's `Example` values, then walk one flow using only prior outputs as inputs. For a repeatable check, a small script speaking stdio JSON-RPC and asserting `structuredContent.ok` per tool is worth more than a unit test of the handler — it exercises the schema, the registration, and the envelope together.

## Client registration

```json
{
  "mcpServers": {
    "orders": {
      "command": "npx",
      "args": ["-y", "@acme/orders-mcp"],
      "env": { "CONTOSO_API_BASE_URL": "https://api.example.com", "CONTOSO_API_TOKEN": "…" }
    }
  }
}
```

Ship this block in the README with the values redacted, and say where each one comes from.

## Checklist

- [ ] `strict: true`, no `any`, build clean
- [ ] Every env var validated at startup; process exits non-zero and names what is missing
- [ ] Nothing written to stdout on stdio transport
- [ ] One tool per capability; names derived from capability ids
- [ ] Every input field typed, constrained, `.describe()`d with an example
- [ ] Enums as `z.enum`, not `z.string()`
- [ ] `outputSchema` + `structuredContent` on every tool
- [ ] Annotations set from the contract's `Kind`; `confirm: z.literal(true)` on every destructive tool
- [ ] Every handler funnels through `respond`; no throw escapes
- [ ] Lists clamp `pageSize` and return `hasMore`
- [ ] Every tool smoked; one flow and one failure path proven
- [ ] README ships the tool table, the flows, and the registration block
