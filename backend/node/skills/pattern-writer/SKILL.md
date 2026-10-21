---
name: patterns-apply
description: Use when scaffolding a TypeScript pattern (strict mode) into the active Node / NestJS / Express repo. Triggers: "scaffold a strategy with discriminated union", "create a Result type for X", "introduce branded types for ids", "type-safe config via Zod". Do NOT use for explanations (`pattern-guide`), reviews (`code-review`), or React (`frontend/react/skills/component-writer`).
---

# TypeScript Design Patterns — Generator

Scaffolds TS (strict mode) pattern implementations into the active repo. Prefers idiomatic TS — discriminated unions, `Result` types, branded ids, higher-order functions — over class-heavy GoF translations. Targets **Node 24 (active LTS) primary, Node 22 (maintenance) supported** + NestJS / Express / bare; works in monorepos.

## Version policy

Detect the project's Node major (`package.json` `engines`, `.nvmrc`, or lockfile) before scaffolding. Node 20 is EOL since April 2026 — flag it, don't target it. Nothing generated here is Node-version-gated between 22 and 24.

## When to use

- Replacing `if`/`else` / `switch` chains with discriminated unions
- Introducing a `Result<T, E>` type for domain failures
- Promoting string ids to branded types
- Extracting an `Options` config from scattered `process.env` reads (with Zod validation)
- Wrapping a function/handler with logging / retry / metrics via HOF decorators
- Building a repository when there's a real abstraction need (not just for the sake of it)

## When NOT to use

- Explanations → `backend/node/skills/pattern-guide`
- Reviewing → `backend/node/skills/code-review`
- React component patterns → `frontend/react/skills/component-writer`
- React Native → `mobile/react-native` (the `mobile-react-native` agent)
- Scaffolding tests → `backend/node/skills/unit-testing` for the class/function-level tests (Vitest, no HTTP); `qa/typescript/skills/api-test-author/writer` (peer) once it's reachable over HTTP

## Inputs needed

1. **Pattern** to scaffold
2. **Framework** (NestJS / Express / Fastify / bare)
3. **Domain** + concrete variants
4. **Existing call site** to refactor
5. **Module layout** (vertical slices preferred — `src/features/<feature>/{commands,queries,domain,infra}.ts`)

## Recipes

### Discriminated union for state / dispatch

```typescript
// src/features/orders/pricing.ts
export type Pricing =
  | { kind: 'standard' }
  | { kind: 'b2b'; contractId: string }
  | { kind: 'promo'; code: string };

export function price(cart: Cart, p: Pricing): Money {
  switch (p.kind) {
    case 'standard': return standardPrice(cart);
    case 'b2b':      return b2bPrice(cart, p.contractId);
    case 'promo':    return promoPrice(cart, p.code);
  }
  // exhaustiveness check — compile error if a case is added but not handled
  const _exhaustive: never = p;
  return _exhaustive;
}
```

### `Result<T, E>` for domain failures

```typescript
// src/shared/result.ts
export type Result<T, E = string> =
  | { ok: true; value: T }
  | { ok: false; error: E };

export const ok    = <T>(value: T): Result<T, never> => ({ ok: true,  value });
export const err   = <E>(error: E): Result<never, E> => ({ ok: false, error });
export const isOk  = <T, E>(r: Result<T, E>): r is { ok: true; value: T } => r.ok;
export const isErr = <T, E>(r: Result<T, E>): r is { ok: false; error: E } => !r.ok;
```

```typescript
// src/features/orders/create-order.ts
type CreateOrderError = 'cart-empty' | 'item-out-of-stock' | 'payment-declined';

export async function createOrder(
  cart: Cart,
  deps: { orders: OrderRepository; payments: PaymentService; clock: Clock },
): Promise<Result<OrderId, CreateOrderError>> {
  if (cart.lines.length === 0) return err('cart-empty');
  const stock = await deps.payments.reserveStock(cart);
  if (!stock.ok) return err('item-out-of-stock');
  // ... payment, save ...
  return ok(orderId);
}
```

### Branded types for ids

```typescript
// src/shared/brand.ts
export type Brand<T, B> = T & { readonly __brand: B };

// src/features/users/id.ts
import { z } from 'zod';

export const UserIdSchema = z.string().uuid().brand<'UserId'>();
export type UserId = z.infer<typeof UserIdSchema>;

// Construction
export const userId = (raw: string): UserId => UserIdSchema.parse(raw);
```

```typescript
// Now this is a compile error:
async function getUser(id: UserId) { /* ... */ }
const orderId = orderIdParse('...');
getUser(orderId);  // Error: Argument of type 'OrderId' is not assignable to parameter of type 'UserId'
```

### Higher-order function decorators

```typescript
// src/shared/decorators.ts
import { trace, SpanStatusCode } from '@opentelemetry/api';
import type { Logger } from 'pino';

type AsyncFn<I, O> = (input: I) => Promise<O>;

export function withSpan<I, O>(name: string, fn: AsyncFn<I, O>): AsyncFn<I, O> {
  const tracer = trace.getTracer('app');
  return async (input: I): Promise<O> => {
    return tracer.startActiveSpan(name, async (span) => {
      try {
        const result = await fn(input);
        span.setStatus({ code: SpanStatusCode.OK });
        return result;
      } catch (e) {
        span.recordException(e as Error);
        span.setStatus({ code: SpanStatusCode.ERROR });
        throw e;
      } finally {
        span.end();
      }
    });
  };
}

export function withLogging<I, O>(log: Logger, name: string, fn: AsyncFn<I, O>): AsyncFn<I, O> {
  return async (input: I): Promise<O> => {
    log.info({ name }, 'start');
    try {
      const result = await fn(input);
      log.info({ name }, 'ok');
      return result;
    } catch (e) {
      log.error({ name, err: e }, 'failed');
      throw e;
    }
  };
}

// Compose: cache → retry → logging → span → real impl
const placeOrder = withSpan('placeOrder', withLogging(log, 'placeOrder', realPlaceOrder));
```

One concern per decorator; explicit composition.

### Type-safe config via Zod

```typescript
// src/shared/config.ts
import { z } from 'zod';

const ConfigSchema = z.object({
  port: z.coerce.number().int().positive(),
  databaseUrl: z.string().url(),
  authIssuer: z.string().url(),
  ordersMaxLines: z.coerce.number().int().min(1).max(1000).default(100),
  cacheTtlMs: z.coerce.number().int().positive().default(300_000),
});

export type Config = z.infer<typeof ConfigSchema>;

export function loadConfig(env = process.env): Config {
  return ConfigSchema.parse({
    port: env.PORT,
    databaseUrl: env.DATABASE_URL,
    authIssuer: env.AUTH0_ISSUER,
    ordersMaxLines: env.ORDERS_MAX_LINES,
    cacheTtlMs: env.CACHE_TTL_MS,
  });
}
```

Validation at startup; downstream code receives `Config`, never reads `process.env`.

### Repository (only when justified)

```typescript
// src/features/orders/domain/order-repository.ts
export interface OrderRepository {
  findById(id: OrderId): Promise<Order | null>;
  findByCustomer(customerId: UserId, limit: number): Promise<readonly Order[]>;
  save(order: Order): Promise<void>;
}
```

```typescript
// src/features/orders/infra/prisma-order-repository.ts
import { PrismaClient } from '@prisma/client';

export class PrismaOrderRepository implements OrderRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: OrderId): Promise<Order | null> {
    const row = await this.prisma.order.findUnique({ where: { id } });
    return row ? toDomain(row) : null;
  }

  async findByCustomer(customerId: UserId, limit: number): Promise<readonly Order[]> {
    const rows = await this.prisma.order.findMany({ where: { customerId }, take: limit });
    return rows.map(toDomain);
  }

  async save(order: Order): Promise<void> {
    await this.prisma.order.upsert({
      where: { id: order.id },
      create: toRow(order),
      update: toRow(order),
    });
  }
}
```

For most apps using Prisma directly is fine — only wrap in a repository when there's a domain reason (multiple stores, complex queries, decoupling).

### Command handler (lightweight CQRS)

```typescript
// src/features/orders/commands/place-order.ts
type PlaceOrderCommand = { customerId: UserId; lines: readonly NewLine[] };
type PlaceOrderError = 'cart-empty' | 'item-out-of-stock';

type Deps = { orders: OrderRepository; clock: Clock };

export async function handlePlaceOrder(
  cmd: PlaceOrderCommand,
  deps: Deps,
): Promise<Result<OrderId, PlaceOrderError>> {
  if (cmd.lines.length === 0) return err('cart-empty');
  const order = Order.place(cmd.customerId, cmd.lines, deps.clock.now());
  await deps.orders.save(order);
  return ok(order.id);
}
```

For NestJS, the same logic lives in a `@CommandHandler` with `@nestjs/cqrs`.

### NestJS class with constructor injection

```typescript
@Injectable()
export class OrderService {
  constructor(
    @InjectRepository(OrderEntity) private readonly repo: Repository<OrderEntity>,
    @Inject(CLOCK) private readonly clock: Clock,
    private readonly events: EventBus,
  ) {}

  async place(cmd: PlaceOrderDto): Promise<OrderId> {
    const order = Order.place(cmd.customerId, cmd.lines, this.clock.now());
    await this.repo.save(toEntity(order));
    this.events.publish(new OrderPlacedEvent(order));
    return order.id;
  }
}
```

## Module boundaries

For a modular monolith built to be split later (blueprint `Modules:` line) — one folder per module, one schema, one public surface, one architecture test. An existing codebase keeps the architecture it has.

- **One public API per module.** `src/modules/<name>/index.ts` exports the module's facade functions (or a Nest provider), its DTO types and the events it publishes; an entity or repository is never exported. Everything else is internal to the folder.
- **One schema per module.** Set it in the ORM mapping — Drizzle `pgSchema('orders')`, Prisma `@@schema("orders")` with `multiSchema` — with migrations per module. A module holds another module's id as a plain column: no relation to a foreign table, no foreign key into its schema.
- **A call between modules** imports the other module's `index.ts` and receives it through the constructor or a factory argument. **An event** is a type exported from the publisher's `index.ts`, delivered by a plain in-process emitter, and only when a second consumer or "must not fail the publisher" earns it; no bus.
- **The architecture test** is dependency-cruiser, run with the unit tests (`"test:arch": "depcruise src --config .dependency-cruiser.cjs"`, called from the same script CI runs). The `forbidden` rule below lets one module import another only through its `index.ts`; a module's own files are free to import each other.

```js
module.exports = {
  forbidden: [
    {
      name: 'module-reach-in',
      comment: 'A module may import another module only through its index.ts',
      severity: 'error',
      from: { path: '^src/modules/([^/]+)/' },
      to: {
        path: '^src/modules/[^/]+/',
        pathNot: '^src/modules/($1/|[^/]+/index\\.ts$)',
      },
    },
  ],
  options: {
    tsConfig: { fileName: 'tsconfig.json' },
    doNotFollow: { path: 'node_modules' },
  },
};
```

The first contract task writes the config and the script; a later task that needs a new dependency imports the owner's `index.ts` instead of editing the rule.

## Rules

- TypeScript **strict** mode (`tsconfig`: `strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`)
- No `any`, no `as unknown as X`; use unknown + narrowing
- Discriminated unions for sums; exhaustive `switch` with `never` check
- `Result<T, E>` for domain failures; throw for bugs / true exceptions
- Branded types for ids that cross boundaries
- Zod (or equivalent) for runtime validation at every external boundary
- ESM modules; no CommonJS in new code (`"type": "module"` in package.json)
- Constructor injection for classes; closures for functional modules
- No mutable module-level state (configuration constants are fine after `loadConfig`)
- Async errors via `Result` or thrown — never both within a single function

## What NOT to do

- No `any` / `@ts-ignore` to silence
- No `Optional`-ish wrappers around values — `T | null` (or `Result`) plus `noUncheckedIndexedAccess` is the TS way
- No class for what a function does (no `new StringUtils().capitalize(...)`)
- No `new Promise((res, rej) => ...)` to wrap an already-promise-returning API
- No `.then()` chains for new code; `async/await`
- No `throw` in domain code when a `Result` would let the caller handle the case
- No reading `process.env` outside `loadConfig`
- No global singletons mutated at runtime
- No nullable booleans (`isActive: boolean | undefined`) — pick a default
- No `enum` (use string union types or `as const` objects)
- No `namespace` keyword in modules — use modules

## Generation outputs

For every pattern:

1. The type definitions (`type Pricing = ...`, `interface OrderRepository`) under the feature's `domain/` or `shared/`
2. The implementations under `feature/` / `infra/` as appropriate
3. Unit tests for every logic-bearing unit produced — **conventions, seams, and doubles policy live in `backend/node/skills/unit-testing`** (Vitest, DI over `vi.mock`, **both branches of every `Result<T,E>`**). Once reachable over HTTP, the contract/integration layer is the **peer** `qa-api-typescript`'s
4. A small `index.ts` barrel where the project uses them — **in a modular monolith the module's `index.ts` is its one public surface**, written together with its schema and the dependency-cruiser config (Module boundaries)

## Validation

After scaffolding, run the project's own scripts (from `package.json`, with its `packageManager`) — unless you are inside a plan task marked `Gate: none`, which runs none of them and reports "written, not run":

- typecheck (`tsc --noEmit`) — 0 errors
- lint — 0 warnings
- test — generated tests pass
- Sweep old call sites; remove the `if-else` chain the new pattern replaces

## Handoffs

- Conceptual lookup → `backend/node/skills/pattern-guide`
- Reviewing the result → `backend/node/skills/code-review`
- React patterns → `frontend/react/skills/component-writer`
- API DTOs (Zod schemas) → `qa/typescript/skills/api-models`
- Unit-testing the generated code → `backend/node/skills/unit-testing`
- API tests (contract/integration) → **peer** `qa/typescript/skills/api-test-author/writer`
