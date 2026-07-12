---
name: be-node-reference
description: Use when the user asks to explain or look up a design pattern in TypeScript (strict mode) — for Node / NestJS / Express backends, or shared utilities. Triggers: "what is the strategy pattern in TS", "tagged union vs class hierarchy", "branded types for ids", "result type vs exceptions", "TS discriminated unions". Do NOT use for scaffolding (use `backend/node/skills/generator`), reviews (use `backend/node/skills/reviewer`), React-specific patterns (use `frontend/react/skills/reference`), or React Native (use `frontend/react-native`).
---

# TypeScript Design Patterns — Reference

Conceptual reference for design patterns as applied in TypeScript (strict mode) — **Node 24 (active LTS) primary, Node 22 (maintenance) supported**, for NestJS / Express / bare backends, shared libraries, and isomorphic code. Node 20 is EOL as of April 2026 — flag it rather than target it. TypeScript-specific idioms (discriminated unions, branded types, `Result` types, dependency injection patterns) often replace classical OO patterns from the GoF book.

## Version policy

Detect the project's Node major from `package.json` `engines` / `.nvmrc` / lockfile before answering. None of the patterns below are Node-version-gated — they apply equally on 22 and 24 — but flag Node 20 as EOL if encountered rather than silently targeting it.

## When to use

- The user asks "what is pattern X in TypeScript"
- The user wants a comparison between idiomatic TS approaches (tagged union vs class hierarchy)
- The user wants a small canonical example, not scaffolding

## When NOT to use

- Scaffolding → `backend/node/skills/generator`
- Reviewing code → `backend/node/skills/reviewer`
- React patterns → `frontend/react/skills/reference`
- React Native → `frontend/react-native`

---

## Strategy

Classical OO version (works fine in TS):

```typescript
interface PricingStrategy {
  calculate(cart: Cart): Money;
}

class StandardPricing implements PricingStrategy { /* ... */ }
class B2bPricing       implements PricingStrategy { /* ... */ }

const strategies = new Map<string, PricingStrategy>([
  ['standard', new StandardPricing()],
  ['b2b',      new B2bPricing()],
]);

function price(cart: Cart, mode: string): Money {
  const s = strategies.get(mode);
  if (!s) throw new Error(`Unknown mode: ${mode}`);
  return s.calculate(cart);
}
```

TypeScript-idiomatic version using **discriminated unions + functions**:

```typescript
type Pricing =
  | { kind: 'standard' }
  | { kind: 'b2b'; contractId: string }
  | { kind: 'promo'; code: string };

function price(cart: Cart, p: Pricing): Money {
  switch (p.kind) {
    case 'standard': return standardPrice(cart);
    case 'b2b':      return b2bPrice(cart, p.contractId);
    case 'promo':    return promoPrice(cart, p.code);
  }
  // exhaustiveness check at compile time
  // const _: never = p;
}
```

`switch` on a discriminator with `never` exhaustiveness gives you sealed-type behavior without class hierarchies.

## Discriminated unions (the most important pattern)

TypeScript's superpower. Use for state machines, message types, response shapes:

```typescript
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

async function getUser(id: string): Promise<Result<User, 'not-found' | 'forbidden'>> {
  const row = await db.users.find(id);
  if (!row) return { ok: false, error: 'not-found' };
  if (!row.isActive) return { ok: false, error: 'forbidden' };
  return { ok: true, value: row };
}

const r = await getUser('123');
if (r.ok) console.log(r.value.email);   // type-narrowed
else      console.log(r.error);         // literal union
```

## `Result` type vs throwing

For domain failures (validation, not-found, forbidden), prefer `Result<T, E>`. Reserve thrown errors for **truly exceptional** conditions (bugs, network unreachability, OOM).

The line: if the caller is expected to handle this case in normal flow, return a `Result`. If recovery is "log and bail", throw.

```typescript
// Domain failure → Result
type CreateOrderError = 'cart-empty' | 'item-out-of-stock' | 'payment-declined';
async function createOrder(cart: Cart): Promise<Result<Order, CreateOrderError>> { /* ... */ }

// Programming bug → throw
function divide(a: number, b: number): number {
  if (b === 0) throw new Error('Division by zero');
  return a / b;
}
```

## Branded types (nominal typing for ids)

Plain `type UserId = string` doesn't stop `function getUser(orderId: string)` from accepting a `UserId` by mistake. Branded types fix it:

```typescript
type Brand<T, B> = T & { readonly __brand: B };
type UserId  = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;

const userId  = '...' as UserId;
const orderId = '...' as OrderId;

function getUser(id: UserId): Promise<User> { /* ... */ }

getUser(userId);   // ok
getUser(orderId);  // compile error
```

For runtime validation, pair with Zod:

```typescript
import { z } from 'zod';
export const UserIdSchema = z.string().uuid().brand<'UserId'>();
export type UserId = z.infer<typeof UserIdSchema>;
```

## Factory

Trivial in TS — just a function:

```typescript
type Gateway = 'stripe' | 'adyen';

function createGateway(g: Gateway, config: GatewayConfig): PaymentGateway {
  switch (g) {
    case 'stripe': return new StripeGateway(config);
    case 'adyen':  return new AdyenGateway(config);
  }
}
```

A class is overkill unless the factory holds state.

## Decorator

Two flavors. **Higher-order function** (preferred in functional / Express code):

```typescript
type Handler<T> = (input: T) => Promise<Result<T, Error>>;

function withLogging<T>(h: Handler<T>, name: string): Handler<T> {
  return async (input) => {
    console.log(`[${name}] start`);
    const r = await h(input);
    console.log(`[${name}] ${r.ok ? 'ok' : 'fail'}`);
    return r;
  };
}

const placeOrder = withLogging(withRetry(withMetrics(realPlaceOrder)), 'placeOrder');
```

**Class decorator** (TS 5+ stage-3 decorators, mostly with NestJS):

```typescript
function Logged<T extends { new (...args: any[]): {} }>(constructor: T) {
  return class extends constructor {
    constructor(...args: any[]) {
      super(...args);
      console.log(`Created ${constructor.name}`);
    }
  };
}
```

## Repository

NestJS has a strong Repository pattern via TypeORM / Mikro-ORM; Prisma is the modern default and largely makes a custom repository unnecessary unless the abstraction earns it.

```typescript
// NestJS-style with constructor injection
@Injectable()
export class OrderRepository {
  constructor(@InjectRepository(OrderEntity) private readonly repo: Repository<OrderEntity>) {}

  async findById(id: OrderId): Promise<Order | null> {
    const row = await this.repo.findOneBy({ id });
    return row ? toDomain(row) : null;
  }

  async save(order: Order): Promise<void> {
    await this.repo.save(toEntity(order));
  }
}
```

Without NestJS DI, a plain class with constructor injection works the same.

## Command / Query handler (lightweight CQRS)

```typescript
// commands/place-order.ts
type PlaceOrderCommand = { customerId: UserId; lines: NewLine[] };

export async function handlePlaceOrder(
  cmd: PlaceOrderCommand,
  deps: { orders: OrderRepository; clock: Clock },
): Promise<Result<OrderId, 'cart-empty' | 'item-out-of-stock'>> {
  if (cmd.lines.length === 0) return { ok: false, error: 'cart-empty' };
  const order = Order.place(cmd.customerId, cmd.lines, deps.clock.now());
  await deps.orders.save(order);
  return { ok: true, value: order.id };
}
```

Dependencies passed as an object — clear at the test site, no DI container needed. NestJS users put the same logic in a `@CommandHandler`.

## Specification (predicate composition)

```typescript
type Specification<T> = (t: T) => boolean;

const and = <T>(a: Specification<T>, b: Specification<T>): Specification<T> => (t) => a(t) && b(t);
const or  = <T>(a: Specification<T>, b: Specification<T>): Specification<T> => (t) => a(t) || b(t);

const active: Specification<User> = (u) => u.status === 'active';
const inEU:   Specification<User> = (u) => EU.includes(u.country);

const target = and(active, inEU);
const matches = users.filter(target);
```

## Pipeline / middleware

Native to Node — Express middleware, NestJS interceptors, Fastify hooks. Reuse them:

```typescript
// Express style
app.use(authMiddleware);
app.use(rateLimitMiddleware);
app.use(validateMiddleware);

// Custom in-process pipeline
type Stage<T> = (input: T) => Promise<T | Terminal>;
type Terminal = { terminal: true; outcome: unknown };

async function runPipeline<T>(stages: Stage<T>[], input: T): Promise<T | Terminal> {
  for (const s of stages) {
    const r = await s(input);
    if (isTerminal(r)) return r;
    input = r;
  }
  return input;
}
```

## Options pattern (typed config + Zod validation)

```typescript
import { z } from 'zod';

const OrdersConfigSchema = z.object({
  pricingMode: z.enum(['standard', 'b2b']),
  maxLines: z.number().int().min(1).max(1000),
  cacheTtlMs: z.number().int().positive(),
});

export type OrdersConfig = z.infer<typeof OrdersConfigSchema>;

export function loadOrdersConfig(env: NodeJS.ProcessEnv): OrdersConfig {
  return OrdersConfigSchema.parse({
    pricingMode: env.ORDERS_PRICING_MODE,
    maxLines: Number(env.ORDERS_MAX_LINES),
    cacheTtlMs: Number(env.ORDERS_CACHE_TTL_MS),
  });
}
```

Validation at startup; the rest of the app uses the parsed config, never re-reading `process.env`.

## Dependency injection

Three viable styles:

| Style | When |
|---|---|
| **Constructor injection (plain classes)** | Backend services, NestJS, shared libraries |
| **Function + closure** | Pure functional code; pass dependencies in an object argument |
| **DI container** (NestJS, tsyringe, Inversify) | Service-heavy apps with cross-cutting wiring concerns |

For most TS code, **classes with constructor parameters** + a small composition root work fine. Reach for a container when the wiring becomes painful.

## Async patterns

- **`async`/`await`** everywhere; no `.then().catch()` chains
- **Errors via `Result`** for domain failures; throw for true exceptions
- **`Promise.all`** for parallel independent work; `Promise.allSettled` when partial failures are OK
- **`AbortController`** for cancellation; thread `signal` through every async boundary
- **Avoid `Promise` constructors** unless wrapping a legacy callback API — `new Promise((res, rej) => ...)` is a footgun

## Modern type tools

- **`satisfies`** to check a value against a type while keeping the literal type:

```typescript
const routes = { home: '/', login: '/login' } satisfies Record<string, string>;
type RouteKey = keyof typeof routes;   // "home" | "login"
```

- **Template literal types** for typed URLs / event names
- **`const` assertions** (`as const`) for literal-narrow inference
- **Conditional + mapped types** for advanced library APIs; resist over-engineering in app code

## Handoffs

- Scaffolding patterns → `backend/node/skills/generator`
- Reviewing code → `backend/node/skills/reviewer`
- React-specific patterns → `frontend/react/skills/reference`
- API DTO scaffolding → `qa/typescript/skills/api-dto-writer`
- .NET equivalent → `backend/dotnet/skills/reference`
- Java equivalent → `backend/java/skills/reference`
