---
name: qa-db-connection-typescript
description: Use when the user asks to connect from Node + TypeScript tests to a real database (Postgres / MySQL / Mongo) to seed fixtures, run read-only assertion queries, and clean up safely. Triggers: "connect from our Vitest tests to Postgres", "node-postgres probe for the orders table", "seed and clean a SQL fixture without leaks". Do NOT use for the container lifecycle (`qa-db-testing-testcontainers-typescript`) or SQL-safety guardrails (`qa-db-verification-queries-typescript`).
---

# QA — DB Testing Client (TypeScript / Node 24)

Wires Node 24 + TypeScript Vitest tests to talk to a **real** database — seed fixtures via factories, run read-only assertion queries via `node-postgres` / Knex / Prisma, wait for eventual consistency, and clean state safely. Pairs with `qa/typescript/skills/db-testing/testcontainers` for the container lifecycle and `qa/typescript/skills/db-testing/verification-queries` for SQL safety.

## When to use

- A test must verify a row was written, an FK held, a trigger fired, or a soft-delete column was set.
- Test setup needs to seed reference data (currencies, countries, plan tiers) that production reads.
- Async write flows need a "wait until the projection catches up" helper.
- Test suite leaks data between tests and needs a deterministic cleanup strategy.

## When NOT to use

- Production data-access code → the `backend/node` dev stack's generator, if installed.
- Container booting itself → `qa/typescript/skills/db-testing/testcontainers`.
- SQL guardrails (parameterization, no `SELECT *` in assertions) → `qa/typescript/skills/db-testing/verification-queries`.
- Pure unit tests with no SQL surface — keep them mock-driven.
- .NET / Java stacks → `qa/{dotnet,java}/skills/db-testing/connection`.

## Stack

- **Runtime**: Node 24 (LTS)
- **Language**: TypeScript (`"strict": true`)
- **Test runner**: Vitest (Jest works the same — adjust imports)
- **DB clients**:
  - **`pg` (`node-postgres`)** — preferred for assertion queries; thin layer, parameterized via `$1` placeholders.
  - **Knex** — when probe queries grow joins and the query builder helps.
  - **Prisma client** — only when the production code already uses Prisma; `prisma.$queryRaw` for the assertion query.
  - **`mongodb` driver** — Mongo assertions.
- **Migration**: `node-pg-migrate` / `db-migrate` / Prisma `migrate deploy` — applied once on container startup (see `qa/typescript/skills/db-testing/testcontainers`).
- **Cleanup**: per-test `TRUNCATE … CASCADE` (default for `pg`), Knex transactional rollback when the SUT runs in-process.

```
tests/
├── integration/
│   ├── fixtures/
│   │   ├── postgres.ts                   ← see qa/typescript/skills/db-testing/testcontainers
│   │   └── orders.integration.spec.ts
│   ├── dbclients/
│   │   ├── poolFactory.ts                ← single pg.Pool source
│   │   └── ordersDbProbe.ts              ← read-only assertion queries
│   ├── builders/                          ← test data factories (qa/typescript/skills/test-data-builder)
│   └── seeders/
│       └── ordersSeeder.ts                ← writes seeded rows via factories
```

## Connection management

One `pg.Pool` per test process, configured from the Testcontainer's connection details. **Never** new a `Client` per test.

```ts
// tests/integration/dbclients/poolFactory.ts
import pg from 'pg';

let pool: pg.Pool | undefined;

export function getPool(): pg.Pool {
  if (!pool) throw new Error('Pool not initialised. Call initPool() in fixture setup.');
  return pool;
}

export function initPool(config: pg.PoolConfig): pg.Pool {
  pool = new pg.Pool({
    max: 10,
    idleTimeoutMillis: 30_000,
    ...config,
  });
  return pool;
}

export async function endPool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = undefined;
  }
}
```

In the fixture's `beforeAll`, call `initPool(...)` with the container's connection details. In `afterAll`, call `endPool()`.

## Seeding fixtures via factories

Test data shape comes from `qa/typescript/skills/test-data-builder` (`anOrder({ ... })`); the seeder takes the built shape and persists it. Shape and persistence stay separate.

```ts
// tests/integration/seeders/ordersSeeder.ts
import { getPool } from '../dbclients/poolFactory.js';
import type { TestOrder } from '../builders/order.js';

export const ordersSeeder = {
  async insert(order: TestOrder): Promise<string> {
    await getPool().query(
      `INSERT INTO orders (id, customer_id, status, total_minor, currency, placed_at)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [order.id, order.customerId, order.status, order.totalMinor, order.currency, order.placedAt],
    );
    return order.id;
  },
};
```

```ts
import { describe, it, expect } from 'vitest';
import { Orders } from '../builders/order.js';
import { ordersSeeder } from '../seeders/ordersSeeder.js';
import { ordersDbProbe } from '../dbclients/ordersDbProbe.js';

describe('cancellation writes refund', () => {
  it('writes the refund row with the original total', async () => {
    const order = Orders.paid({ totalMinor: 15_000 });
    await ordersSeeder.insert(order);

    await sut.cancel(order.id);

    const refund = await ordersDbProbe.getRefundFor(order.id);
    expect(refund).not.toBeNull();
    expect(refund!.amountMinor).toBe(15_000);
  });
});
```

## Read-only assertion queries — DB probes

A **probe** is a small read-only module. One function per assertion. Each function names the columns it reads.

```ts
// tests/integration/dbclients/ordersDbProbe.ts
import { getPool } from './poolFactory.js';

export type RefundRow = {
  id: string;
  orderId: string;
  amountMinor: number;
  currency: string;
  refundedAt: Date;
};

export const ordersDbProbe = {
  async getRefundFor(orderId: string): Promise<RefundRow | null> {
    const result = await getPool().query<{
      id: string;
      order_id: string;
      amount_minor: string;        // pg returns BIGINT as string by default
      currency: string;
      refunded_at: Date;
    }>(
      `SELECT id, order_id, amount_minor, currency, refunded_at
       FROM   refunds
       WHERE  order_id = $1`,
      [orderId],
    );

    const row = result.rows[0];
    if (!row) return null;
    return {
      id: row.id,
      orderId: row.order_id,
      amountMinor: Number(row.amount_minor),
      currency: row.currency,
      refundedAt: row.refunded_at,
    };
  },
};
```

Probe rules:
- **Read-only** — probes never write. Writes go through the SUT or a seeder.
- **Project explicit columns** — no `SELECT *`. The probe's return type documents what the test cares about.
- **Parameterized via `$1, $2, …`** — never string-template a value into the query.
- **One function per assertion** — `getRefundFor`, `countActiveOrdersForCustomer`, `hasAuditEventOfType`.
- **`BIGINT`** values come back as strings from `pg`; convert to `number` explicitly (or use `BigInt`) — don't accidentally compare a string to a number in the assertion.

## Waiting for eventual consistency

Async write flows (CDC, outbox → projection, queue consumer) don't surface the new row instantly. Use a deterministic poll, **not** `setTimeout`.

```ts
export async function waitFor<T>(
  probe: () => Promise<T | null>,
  predicate: (value: T) => boolean,
  opts: { timeoutMs: number; intervalMs: number },
): Promise<T> {
  const deadline = Date.now() + opts.timeoutMs;
  while (Date.now() < deadline) {
    const value = await probe();
    if (value !== null && predicate(value)) return value;
    await new Promise((r) => setTimeout(r, opts.intervalMs));
  }
  throw new Error(`Probe did not satisfy predicate within ${opts.timeoutMs}ms.`);
}

// Usage
const refund = await waitFor(
  () => ordersDbProbe.getRefundFor(orderId),
  (r) => r.amountMinor === 15_000,
  { timeoutMs: 5_000, intervalMs: 100 },
);
```

`5_000ms` is a sane default locally; bump in CI if needed. **Never** `await new Promise((r) => setTimeout(r, 5000));` as the assertion.

## Cleanup strategies

| Strategy | When | Notes |
|---|---|---|
| **`TRUNCATE … CASCADE`** | Default for `pg`-driven tests | `beforeEach` truncates the test's working tables. Fast, deterministic, keeps schema. |
| **Knex transactional rollback** | SUT runs in-process and consumes the same Knex connection | `knex.transaction(async (trx) => { ... throw; })` — automatic rollback. Doesn't work across HTTP. |
| **Schema-per-test** | Cross-test mutation is unavoidable (migrations, multi-tenant) | Slowest; reserve for tests that need it. |
| **Mongo: drop collections** | `beforeEach` drops every collection except system ones. |

### Truncate template

```ts
beforeEach(async () => {
  await getPool().query('TRUNCATE orders, refunds, audit_events RESTART IDENTITY CASCADE');
});
```

List tables explicitly. Don't loop over `pg_catalog` — you'll truncate Flyway / Prisma migration tables too.

### Prisma cleanup

If the project uses Prisma:

```ts
beforeEach(async () => {
  await prisma.$transaction([
    prisma.refund.deleteMany(),
    prisma.order.deleteMany(),
  ]);
});
```

Order the deletes by FK dependency.

## Secrets

- Connection details come from the Testcontainer's `getConnectionUri()` (test-time) or `process.env.TEST_DATABASE_URL` (rare); **never** committed credentials.
- Never `console.log` the connection URI — it contains the password.
- `.env.test` does **not** contain raw passwords — use placeholder env vars (`${TEST_DATABASE_URL}`).

## Rules

- Single `pg.Pool` per test process, initialized in fixture `beforeAll`, ended in `afterAll`.
- Seeders write; probes read; SUT does the business action. Each module has one job.
- Probes are read-only and explicitly project columns (no `SELECT *`).
- Every parameter is bound via `$1, $2, …` (or Knex's `.where({...})` placeholders) — never string-template values.
- `setTimeout` is forbidden as the assertion wait — use the polling helper with a predicate.
- `BIGINT` results from `pg` are strings — convert explicitly; never compare a string `'15000'` to a number `15000`.
- Default cleanup is `TRUNCATE … CASCADE` per test; transactional rollback only when feasible.
- Constructor-injection-style modules — accept the pool / connection as an argument or rely on the shared `getPool()` getter; never `new pg.Client(...)` per test.
- ESM modules (`"type": "module"`), explicit `.js` extensions on relative imports.
- Strict TS — no `any` in probe / seeder signatures or return types.
- ESLint `no-floating-promises` enabled so missed `await` on a probe / seed is a build error.

## What NOT to do

- No `await new Promise((r) => setTimeout(r, 5000))` as the assertion wait — poll a probe with a predicate.
- No `SELECT * FROM orders WHERE id = '…'` with the value inlined — bind `$1`, project the columns you need.
- No raw `INSERT` SQL duplicated across tests — go through a seeder backed by `qa/typescript/skills/test-data-builder`.
- No `new pg.Client({ ... })` inside a test — use the shared pool.
- No template-literal SQL that interpolates values (`` `WHERE id = '${id}'` ``) — SQL injection in tests still hides bugs and may corrupt fixtures.
- No `await pool.query('TRUNCATE *')` — list tables explicitly.
- No `Flyway-style "clean"` between tests — drops schema; truncate row data instead.
- No mixing Prisma client + `pg` queries on the same connection — pick one library per concern in the test path.
- No probe that returns the entire row as `Record<string, unknown>` — typed projection only.
- No reading the connection URI from `console.log`-able global state — go through the pool factory.
- No `catch` blocks around `pool.query` that swallow exceptions — let them bubble and fail the test.
- No `process.env.DATABASE_URL` in tests pointing at a shared dev DB — use the Testcontainer's URI.

## Generation steps

1. Confirm engine (Postgres default), schema-source (`node-pg-migrate` / Prisma), and which assertion queries each new test needs.
2. Add `poolFactory.ts` if not present; call `initPool(...)` in fixture `beforeAll` with the container's connection config.
3. For each new test set, scaffold an `<aggregate>Seeder.ts` (write) and `<aggregate>DbProbe.ts` (read), reusing factories from `qa/typescript/skills/test-data-builder`.
4. Add the `waitFor` polling helper if the SUT involves async projections.
5. Pick a cleanup strategy (`TRUNCATE … CASCADE` default); wire `beforeEach`.
6. Run the project's own test script with the package manager `packageManager` names — every test passes; no leaks between specs.
7. Run `tsc --noEmit` — strict TS green. Inside a plan task marked `Gate: none`, run none of steps 6–7 and report the files as "written, not run".

## Handoffs

- Container lifecycle → `qa/typescript/skills/db-testing/testcontainers`
- SQL guardrails on assertion queries → `qa/typescript/skills/db-testing/verification-queries`
- Test data factories feeding seeders → `qa/typescript/skills/test-data-builder`
- .NET DB testing client → `qa/dotnet/skills/db-testing/connection`
- Java DB testing client → `qa/java/skills/db-testing/connection`
- API tests that own the SUT call → `qa/typescript/skills/api-test-author/writer`
- Test strategy where DB tests fit → `qa/manual/test-strategy`
- Production data access patterns → the `backend/node` dev stack's generator, if installed
