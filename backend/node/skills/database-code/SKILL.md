---
name: persistence
description: Use when setting up or refactoring persistence in Node (24 primary, 22 maintenance) + TypeScript — Prisma (default), Drizzle, or TypeORM; schema, migrations, query patterns, transactions, optimistic concurrency, tuning. Triggers: "set up Prisma for X", "Drizzle vs Prisma", "transaction in Prisma", "raw SQL escape hatch". Do NOT use for non-ORM data access (`data/<db>`), cross-engine migrations (`data/_shared/migrations`), or .NET / Java persistence.
---

# TypeScript — Persistence with Prisma (default), Drizzle, TypeORM

The library's default persistence layer for TypeScript on **Node 24 (active LTS) primary, Node 22 (maintenance) supported**. **Prisma** for most apps — schema-first, generated typed client, good migration story. **Drizzle** when you want lower-level SQL access with TypeScript types; **TypeORM** when the team is already invested (don't pick it for new projects). All recipes assume Postgres (per `data/postgresql`); switch driver settings for MySQL / SQL Server.

## Version policy

Detect the project's Node major before scaffolding (`package.json` `engines` / `.nvmrc` / lockfile). Node 20 is EOL since April 2026 — flag it, don't target it. Prisma/Drizzle/TypeORM client behavior below is unaffected by the 22-vs-24 choice.

## When to use

- New Node service needs persistence
- Adding an entity / table to an existing schema
- Tuning a slow query
- Wiring optimistic concurrency
- Setting up the migrations workflow
- Choosing between Prisma / Drizzle / TypeORM

## When NOT to use

- DB engine specifics / DDL → `data/postgresql` / `data/sqlserver` / `data/mysql`
- Cross-engine migrations → `data/_shared/migrations`
- Cross-engine query optimization → `data/_shared/slow-query-fixes`
- Caching → `data/_shared/caching-patterns` + `data/redis`
- Raw SQL with no ORM — `pg` directly works fine; this skill is about typed ORMs
- .NET → `backend/dotnet/skills/database-code`
- Java → `backend/java/skills/database-code`

## Picking the ORM

| Tool | When | Pros | Cons |
|---|---|---|---|
| **Prisma** | Default | Schema-first, generated client, great DX, solid migration tool | Generated client is a heavy import; doesn't expose raw SQL composability easily |
| **Drizzle** | TypeScript-first teams who want raw-SQL-like ergonomics | Type-safe SQL builder, small, no generated client | Smaller ecosystem; more boilerplate per query |
| **TypeORM** | Teams already on it | Repository pattern, decorators familiar to .NET / Java devs | History of footguns (transactions, lazy relations); avoid for new projects |
| **MikroORM** | Niche | Unit of work + identity map | Smaller community |

**Prisma** is the recommendation. Switch to **Drizzle** when the team strongly prefers SQL composability.

## Prisma — recipe

### Schema

```prisma
// prisma/schema.prisma
generator client {
  provider      = "prisma-client-js"
  binaryTargets = ["native", "linux-musl-openssl-3.0.x"]   // Alpine container
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Order {
  id          String    @id @default(uuid()) @db.Uuid
  customerId  String    @map("customer_id") @db.Uuid
  status      OrderStatus
  totalMinor  BigInt    @map("total_minor")
  currency    String    @db.Char(3)
  placedAt    DateTime  @map("placed_at") @db.Timestamptz(6)
  paidAt      DateTime? @map("paid_at") @db.Timestamptz(6)
  version     Int       @default(0)

  lines       OrderLine[]

  @@map("orders")
  @@index([customerId])
  @@index([placedAt(sort: Desc)])
}

model OrderLine {
  id          String  @id @default(uuid()) @db.Uuid
  orderId     String  @map("order_id") @db.Uuid
  sku         String
  quantity    Int
  priceMinor  BigInt  @map("price_minor")

  order       Order   @relation(fields: [orderId], references: [id], onDelete: Cascade)

  @@map("order_lines")
}

enum OrderStatus {
  PENDING
  PAID
  CANCELLED
  REFUNDED

  @@map("order_status")
}
```

- **Snake_case columns** via `@map` (matches `data/_shared/schema-design`)
- **`BigInt` for money in minor units** — Prisma exposes as JS `BigInt`; serialize in DTO layer
- **`@db.Timestamptz(6)`** for timestamps (microsecond precision, TZ-aware)
- **Explicit indexes** with sort hints

### Client setup (singleton)

```typescript
// src/persistence/prisma.ts
import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'info', 'warn', 'error'] : ['warn', 'error'],
    datasources: { db: { url: process.env.DATABASE_URL! } },
  });

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;
```

One PrismaClient per process. The dev-mode `globalThis` trick avoids client churn during Next.js hot reload.

### Queries

```typescript
import { prisma } from './persistence/prisma';
import { OrderStatus, Prisma } from '@prisma/client';

// Get by id (typed return — Prisma generates the `Order` type)
export async function getOrder(id: string) {
  return prisma.order.findUnique({ where: { id } });
}

// Get with relation — explicit include
export async function getOrderWithLines(id: string) {
  return prisma.order.findUnique({
    where: { id },
    include: { lines: true },
  });
}

// Projection — select only the columns you need
export async function listOrderSummaries(customerId: string, take = 20) {
  return prisma.order.findMany({
    where: { customerId },
    select: { id: true, status: true, totalMinor: true, currency: true, placedAt: true },
    orderBy: { placedAt: 'desc' },
    take,
  });
}

// Keyset pagination
export async function nextOrdersPage(cursorId: string, take = 20) {
  return prisma.order.findMany({
    skip: 1,                                // skip the cursor itself
    cursor: { id: cursorId },
    orderBy: { placedAt: 'desc' },
    take,
  });
}
```

Rules:

- **Always `select` what you need** — never the full entity for read endpoints
- **Always `take`** for collection queries
- **`include` only when necessary** — produces a `LEFT JOIN` (or multiple queries depending on the relation)
- **Keyset pagination** (`cursor`) for large tables; not `skip: N` for paging deep

### Write + transaction

```typescript
import { Prisma } from '@prisma/client';

type CreateOrderError = 'duplicate' | 'concurrency-conflict';

export async function createOrder(cmd: CreateOrderCommand): Promise<Result<string, CreateOrderError>> {
  try {
    const order = await prisma.order.create({
      data: {
        id: crypto.randomUUID(),
        customerId: cmd.customerId,
        status: 'PENDING',
        currency: cmd.currency,
        totalMinor: cmd.lines.reduce((s, l) => s + l.priceMinor * BigInt(l.quantity), 0n),
        placedAt: new Date(),
        lines: { create: cmd.lines.map((l) => ({ /* ... */ })) },
      },
    });
    return ok(order.id);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === 'P2002') {
      return err('duplicate');
    }
    throw e;
  }
}

// Multi-step transaction (interactive)
export async function cancelOrder(id: string): Promise<Result<void, 'not-found' | 'invalid-state' | 'concurrency-conflict'>> {
  return prisma.$transaction(async (tx) => {
    const order = await tx.order.findUnique({ where: { id } });
    if (!order) return err('not-found');
    if (order.status !== 'PENDING') return err('invalid-state');

    // Optimistic concurrency via the version column
    const updated = await tx.order.updateMany({
      where: { id, version: order.version },
      data:  { status: 'CANCELLED', version: { increment: 1 } },
    });

    if (updated.count === 0) return err('concurrency-conflict');
    return ok(undefined);
  });
}
```

- **`$transaction` for multi-step** atomic operations
- **`updateMany` with the version column** is the optimistic concurrency pattern in Prisma (Prisma doesn't have built-in `@Version`)
- **Prisma error codes** — `P2002` unique constraint, `P2025` record not found, etc. Handle them with a single `instanceof` check.

### Bulk operations

```typescript
// Single UPDATE statement
await prisma.order.updateMany({
  where: { placedAt: { lt: cutoff }, status: 'PENDING' },
  data:  { status: 'CANCELLED' },
});

// Bulk insert
await prisma.order.createMany({
  data: orders,
  skipDuplicates: true,
});
```

For very large batches, drop to raw SQL via `$executeRawUnsafe` — see below.

### Raw SQL escape hatch

```typescript
// Tagged template (recommended) — parameters are bound safely
const rows = await prisma.$queryRaw<Array<{ id: string; total: bigint }>>`
  SELECT id, total_minor AS total
  FROM orders
  WHERE customer_id = ${customerId}::uuid
    AND placed_at > NOW() - INTERVAL '30 days'
  ORDER BY placed_at DESC
  LIMIT 50
`;
```

Always tagged templates (`$queryRaw`) or `$queryRawUnsafe` with explicitly bound parameters. Never string concatenation.

### Migrations

```bash
npx prisma migrate dev --name add_orders_paidat        # in dev (creates + applies)
npx prisma migrate deploy                              # in CI (apply pending migrations)
```

Rules:

- Migrations in source control (`prisma/migrations/`)
- `migrate dev` only on developer laptops; `migrate deploy` in CI / pre-deploy
- For online-safe DDL, write raw SQL into the migration directory and skip Prisma's generator if needed
- App never auto-migrates at startup

See `data/_shared/migrations` for cross-engine recipes; this skill covers the Prisma-side mechanics.

## Drizzle — recipe

When the team prefers a SQL-like builder over the schema-first Prisma model:

```typescript
// src/persistence/schema.ts
import { pgTable, uuid, varchar, bigint, timestamp, char, integer, index } from 'drizzle-orm/pg-core';

export const orders = pgTable('orders', {
  id:         uuid('id').primaryKey(),
  customerId: uuid('customer_id').notNull(),
  status:     varchar('status', { length: 20 }).notNull(),
  totalMinor: bigint('total_minor', { mode: 'bigint' }).notNull(),
  currency:   char('currency', { length: 3 }).notNull(),
  placedAt:   timestamp('placed_at', { withTimezone: true, precision: 6 }).notNull(),
  paidAt:     timestamp('paid_at', { withTimezone: true, precision: 6 }),
  version:    integer('version').default(0).notNull(),
}, (t) => ({
  customerIdx: index('idx_orders_customer_id').on(t.customerId),
  placedIdx:   index('idx_orders_placed_at').on(t.placedAt.desc()),
}));
```

```typescript
import { drizzle } from 'drizzle-orm/node-postgres';
import { Pool } from 'pg';
import { eq, and, lt, desc } from 'drizzle-orm';
import { orders } from './schema';

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
export const db = drizzle(pool);

// Query
const recent = await db.select({
  id: orders.id, status: orders.status, totalMinor: orders.totalMinor,
}).from(orders).where(eq(orders.customerId, customerId)).orderBy(desc(orders.placedAt)).limit(20);

// Update with optimistic concurrency
const result = await db.update(orders)
  .set({ status: 'CANCELLED', version: orders.version + 1 })
  .where(and(eq(orders.id, id), eq(orders.version, currentVersion)))
  .returning({ id: orders.id });

if (result.length === 0) /* concurrency conflict */ ;
```

Drizzle Kit handles migrations (`drizzle-kit generate` / `drizzle-kit push`).

## TypeORM — recipe (for existing projects)

Decorator-based; familiar if the team came from Java/.NET. Don't pick it for new projects; if you have it, the patterns are:

```typescript
@Entity({ name: 'orders' })
export class Order {
  @PrimaryColumn('uuid')                                 id!: string;
  @Column({ name: 'customer_id', type: 'uuid' })         customerId!: string;
  @Column({ length: 20 })                                status!: string;
  @VersionColumn()                                       version!: number;
  // ...
  @OneToMany(() => OrderLine, (l) => l.order, { cascade: ['insert'] })
  lines!: OrderLine[];
}
```

Watch out for: lazy relations, `cascade: true` global, mixing query builder + repository patterns.

## Connection pooling

Pool size **per app instance** is small (5–20). For serverless or large fleets, use **PgBouncer** in front (transaction mode) so app-side pools can be moderate without overwhelming Postgres. See `data/postgresql` for the engine-side rules.

## DI / repository wrappers (when to bother)

For a typical service, **calling `prisma.order.create(...)` directly from a handler is fine** — Prisma is the abstraction. Wrap in a repository class only when:

- You need to swap the persistence layer (rare)
- You want a stable test seam (mock the repository, not Prisma)
- The query surface for one aggregate is broad and benefits from a named API

In NestJS, an `@Injectable() OrdersRepository` is conventional; in Express / bare Node, plain functions importing `prisma` are simpler.

## OTel instrumentation

`@opentelemetry/instrumentation-pg` (for raw `pg`) and Prisma's built-in tracing (`previewFeatures = ["tracing"]` + register the Prisma OTel extension) put every DB call on a span. Pair with `observability/opentelemetry-node` for the full pipeline.

```prisma
generator client {
  provider        = "prisma-client-js"
  previewFeatures = ["tracing"]
}
```

```typescript
import { PrismaInstrumentation } from '@prisma/instrumentation';
registerInstrumentations({ instrumentations: [new PrismaInstrumentation()] });
```

## Common anti-patterns

- **`include` everything** — load whole graphs for every read
- **`findFirst` then update** outside a transaction — race condition
- **`upsert` for "create if not exists, do nothing on duplicate"** — use `createMany({ skipDuplicates: true })` if you don't need the read-modify shape
- **`BigInt` round-tripped through JSON.stringify** — explodes (BigInt isn't serializable by default); convert to string in DTO
- **Multiple `await` queries instead of one `Promise.all`** for independent fetches
- **Mixing Prisma + raw `pg` Pool** sharing connections — leak risk
- **`prisma.$disconnect()` after every request** — kills the pool benefit
- **Auto-migrate in production** — `prisma migrate deploy` from the pipeline only

## Rules

- One ORM per project — Prisma default, Drizzle when SQL-composability matters
- Schema in source control; migrations in source control; both reviewed in PRs
- Snake_case columns via `@map`; BigInt for money; Timestamptz with precision
- Singleton client per process
- `select` what you need; `take` every collection query; `cursor` for paging
- Transactions via `$transaction` for multi-step writes
- Optimistic concurrency via a `version` column + `updateMany` (Prisma) or `@VersionColumn` (TypeORM)
- Migrations applied via CI / pipeline, not app startup
- OTel tracing on every DB call
- Raw SQL via tagged templates only

## What NOT to do

- No `prisma.user.findUnique` without `where` (won't even compile, but worth saying — never bypass the typed where)
- No global `prisma` reinstantiation per request
- No `include` cascading 3 levels deep on a read endpoint
- No string-concat in `$queryRawUnsafe` — use `$queryRaw` tagged template
- No app-side migration on startup
- No mixing two ORMs in one project
- No `BigInt` serialized via `JSON.stringify` without explicit conversion
- No long-running connections held outside a transaction
- No `Prisma.PrismaClientKnownRequestError` swallowed silently — match on `e.code`
- No new project on TypeORM (when Prisma / Drizzle exist)

## Generation steps

1. Confirm DB engine, framework (NestJS / Express / Fastify), and ORM choice (Prisma default).
2. Generate `prisma/schema.prisma` with the entity (snake_case mappings, indexes, relations, version column).
3. Generate `src/persistence/prisma.ts` singleton.
4. Generate the queries / commands / repository module per aggregate.
5. Author the first migration via `prisma migrate dev`; review the SQL.
6. Wire `migrate deploy` into the deploy pipeline.
7. Enable Prisma tracing + register OTel instrumentation per `observability/opentelemetry-node`.
8. Smoke locally with Postgres in Docker; confirm queries log + traces appear.

## Handoffs

- DB engine specifics → `data/postgresql` / `data/sqlserver` / `data/mysql`
- Migrations across engines → `data/_shared/migrations`
- Query optimization principles → `data/_shared/slow-query-fixes`
- Caching → `data/_shared/caching-patterns` + `data/redis`
- API contracts (Zod) → `qa/typescript/skills/api-models`
- API tests → `qa/typescript/skills/api-test-author/writer`
- .NET equivalent → `backend/dotnet/skills/database-code`
- Java equivalent → `backend/java/skills/database-code`
