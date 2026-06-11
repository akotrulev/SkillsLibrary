---
name: qa-db-testing-query-author-typescript
description: Use when the user asks to write a safe verification query for tests in Node 20 + TypeScript, assert this row exists from a test, review my test SQL for guardrails, add a `COUNT(*)` check from an integration test, or wait for an eventually-consistent row.
---

# QA — DB Testing Query Author (TypeScript / Node 20)

Guardrails for the **SQL string itself** when a Node 20 + TypeScript Vitest integration test reaches into the database to verify behaviour. The pool, seeder, and probe scaffolding live in `qa/typescript/skills/db-testing/client`; this skill owns *what the SQL is allowed to look like* — `$1` placeholder binding only, explicit column lists, safe `LIKE`, type-correct parsing (especially `BIGINT` → `number`), exists / not-exists / count helpers, a `waitFor` poller that re-runs the same safe query, and a hard refusal list for destructive verbs outside cleanup.

## When to use

- A test is about to embed a SQL string (`pool.query(...)`, `knex.raw(...)`, `prisma.$queryRaw`) and you need it reviewed or generated.
- An existing probe / seeder uses template-literal interpolation, `SELECT *`, or unbounded `DELETE` and needs a rewrite.
- A test needs an "assert exactly one row matches these columns" or "assert no row matches" helper.
- An async flow needs a wait-for-eventual-consistency poll that re-runs the verification query.

## When NOT to use

- Pool / fixture lifecycle / cleanup wiring → `qa/typescript/skills/db-testing/client`.
- Container boot, migrations on startup → `qa/typescript/skills/db-testing/testcontainers`.
- Production data-access SQL → `design-patterns/typescript/generator`.
- .NET SQL guardrails → `qa/dotnet/skills/db-testing/query-author`.
- Java SQL guardrails → `qa/java/skills/db-testing/query-author`.
- Pure unit tests with no SQL surface — keep them mock-driven.

## Inputs needed (≤2 questions)

1. **Engine + client**: Postgres + `pg` (default), Postgres + Knex (when joins / windowing earn it), Postgres + Prisma (`$queryRaw`, only if production already uses Prisma), or Mongo?
2. **Assertion shape**: exists / not-exists / single-row projection / count / poll-until-row-appears?

## Decision matrix

| Need | Use | Notes |
|---|---|---|
| "Row exists with these columns" | `pool.query<TRow>(...)` then `rows[0] ?? null` | Returns `null` if missing; assert `not.toBeNull()`. |
| "Exactly one row matches" | query then assert `rows.length === 1` before reading | Surfaces fixture leaks immediately. |
| "No row matches" | `SELECT EXISTS (...)` → read `rows[0].exists` (boolean) | Cheaper than `COUNT(*)`; short-circuits. |
| "How many rows match" | `SELECT COUNT(*)` → `Number(rows[0].count)` | `pg` returns `bigint` as **string**; convert with `Number(...)`. |
| Joins / windowing get ugly in raw SQL | Knex `.select(cols).from(...).where({...})` | Builder keeps values bound by construction. |
| "Wait until row appears" | `waitFor(probe, predicate, opts)` (below) | Re-runs the same parameterized query; never `setTimeout` as the assertion. |
| Free-text contains | `LIKE $1` with a pattern escaped in TS (`% _ \`) + `ESCAPE '\'` | Treat user input as data; see helper below. |
| `IN (...)` of N values | `WHERE col = ANY($1)` (pass a JS array) | Never interpolate the list. |
| Soft-delete check | Explicit `WHERE deleted_at IS NULL` | Don't rely on a view abstraction in tests. |

## Stack

- **Runtime**: Node 20 (LTS), TypeScript (`"strict": true`), ESM (`"type": "module"`, explicit `.js` on relative imports)
- **Test runner**: Vitest (Jest works the same — adjust imports)
- **Clients**: `pg` (`node-postgres`, default), Knex when joins / windowing earn it, Prisma `$queryRaw` only when production already uses Prisma
- **Connection**: shared `pg.Pool` from `qa/typescript/skills/db-testing/client` via `getPool()` — never `new pg.Client(...)` in the probe
- **Lint**: ESLint `no-floating-promises` on so a missed `await` on a probe is a build error

## Parameterized read — the only allowed shape

```ts
// tests/integration/dbclients/ordersDbProbe.ts
import { getPool } from './poolFactory.js';

export type OrderRow = {
  id: string;
  customerId: string;
  status: string;
  totalMinor: number;
  currency: string;
};

type OrderRowRaw = {
  id: string;
  customer_id: string;
  status: string;
  total_minor: string;          // pg returns BIGINT as string
  currency: string;
};

export const ordersDbProbe = {
  async getOrder(orderId: string): Promise<OrderRow | null> {
    const result = await getPool().query<OrderRowRaw>(
      `SELECT id, customer_id, status, total_minor, currency
       FROM   orders
       WHERE  id = $1`,
      [orderId],
    );

    const row = result.rows[0];
    if (!row) return null;
    return {
      id: row.id,
      customerId: row.customer_id,
      status: row.status,
      totalMinor: Number(row.total_minor),   // explicit BIGINT → number
      currency: row.currency,
    };
  },
};
```

Rules baked in:
- Explicit column list — every column is named and mapped to the typed projection.
- Single placeholder `$1`, value passed in the values array — no interpolation, no `` `... WHERE id = '${orderId}'` ``.
- `BIGINT` comes back as a **string** from `pg`; convert with `Number(...)` (or keep `BigInt` if the value can exceed 2^53). Never compare a string `'15000'` to a number `15000`.
- The probe returns a typed projection, not `Record<string, unknown>`.

## Exists / not-exists helpers

```ts
// tests/integration/dbclients/dbAssertions.ts
import type { Pool } from 'pg';

export async function exists(
  pool: Pool,
  table: string,        // literal, owned by test code — never runtime input
  whereClause: string,  // e.g. 'order_id = $1 AND status = $2'
  params: unknown[],
): Promise<boolean> {
  const result = await pool.query<{ exists: boolean }>(
    `SELECT EXISTS (SELECT 1 FROM ${table} WHERE ${whereClause}) AS exists`,
    params,
  );
  return result.rows[0].exists;
}

// Usage
const paid = await exists(
  getPool(),
  'orders',
  'id = $1 AND status = $2',
  [orderId, 'PAID'],
);
expect(paid, 'expected a PAID row for the seeded order').toBe(true);
```

`table` and `whereClause` are **literal strings owned by the test code**, never composed from runtime input. Values *always* travel through the `$n` placeholder array.

## `COUNT(*)` patterns

```ts
async function countActiveOrdersForCustomer(customerId: string): Promise<number> {
  const result = await getPool().query<{ count: string }>(
    `SELECT COUNT(*) AS count
     FROM   orders
     WHERE  customer_id = $1
       AND  status      = ANY($2)`,
    [customerId, ['PLACED', 'PAID', 'SHIPPED']],
  );
  return Number(result.rows[0].count);
}
```

- `COUNT(*)` returns `bigint` → a **string** in `pg`; wrap in `Number(...)` (large counts: keep `BigInt`).
- The status list is passed as a JS array bound to `ANY($2)`, never string-joined into the SQL.

## Safe `LIKE` escaping

```ts
export function escapeLike(raw: string): string {
  return raw
    .replace(/\\/g, '\\\\')
    .replace(/%/g, '\\%')
    .replace(/_/g, '\\_');
}

async function countOrdersWithReferenceContaining(fragment: string): Promise<number> {
  const pattern = `%${escapeLike(fragment)}%`;   // built in TS, then bound
  const result = await getPool().query<{ count: string }>(
    `SELECT COUNT(*) AS count
     FROM   orders
     WHERE  reference LIKE $1 ESCAPE '\\'`,
    [pattern],
  );
  return Number(result.rows[0].count);
}
```

`%`, `_`, and `\` are escaped in TypeScript before binding so a fragment of `100%` doesn't match every row.

## `BIGINT` / number / timestamp parsing

- **`BIGINT` / `COUNT(*)`** → `pg` returns a **string**. Convert with `Number(...)` (safe under 2^53) or keep `BigInt`. This is the #1 TS-specific footgun: `expect(count).toBe(3)` fails silently against `'3'`.
- **`integer` / `numeric`** → numbers come back as `number`; `numeric`/`decimal` can also arrive as string for precision — convert intentionally.
- **`uuid`** → `string`; pass it as a `string` parameter, never re-wrap it.
- **`timestamptz`** → `pg` parses to a JS `Date` (UTC instant). Assert against an ISO string or epoch millis; don't compare `Date` objects by reference.
- **`boolean`** → `pg` returns a real `boolean`; don't coerce `'t'`/`'f'`.

## Knex tasteful subset

Use Knex only when raw SQL starts composing joins / window functions and the builder earns the dependency. Keep values bound by construction:

```ts
async function getRefundFor(orderId: string): Promise<RefundRow | null> {
  const row = await knex('refunds')
    .select('id', 'order_id', 'amount_minor', 'currency', 'refunded_at')  // explicit columns
    .where({ order_id: orderId })   // bound, not interpolated
    .first();
  if (!row) return null;
  return {
    id: row.id,
    orderId: row.order_id,
    amountMinor: Number(row.amount_minor),
    currency: row.currency,
    refundedAt: row.refunded_at,
  };
}
```

Rules:
- Explicit `.select('col', 'col', ...)` — **never `.select('*')` or a bare `knex('table')`** in tests (those project everything).
- `.where({...})` / `.whereIn('col', values)` — values become bind parameters by construction.
- If you must drop to `knex.raw`, use `?` for values and `??` for identifiers — never template-literal a value into the raw string.

## Wait-for-eventual-consistency poller

Reuse the `waitFor` helper from `qa/typescript/skills/db-testing/client` — the poller re-runs the **same** safe probe; it never builds SQL itself.

```ts
const refund = await waitFor(
  () => ordersDbProbe.getRefundFor(orderId),
  (r) => r.amountMinor === 15_000,
  { timeoutMs: 5_000, intervalMs: 100 },
);
expect(refund.currency).toBe('EUR');
```

`setTimeout` is forbidden as the assertion wait — it's only the inter-poll backoff inside `waitFor`. Never `await new Promise((r) => setTimeout(r, 5000))` before an assertion.

## Refusal patterns — destructive verbs

If a generated or reviewed query contains any of the following **outside** a designated cleanup helper, refuse and require an explicit cleanup path:

| Verb | Refused when | Allowed only in |
|---|---|---|
| `DROP TABLE` / `DROP SCHEMA` | Ever, in a test body | Never. Migrations own schema. |
| `TRUNCATE` | Inside an `it(...)` body | `beforeEach` / `afterEach` cleanup helpers in `qa/typescript/skills/db-testing/client`. |
| `DELETE` without `WHERE` | Anywhere | Never. `TRUNCATE` is the right primitive. |
| `UPDATE` without `WHERE` | Anywhere | Never. |
| `ALTER TABLE` | Test body | Migration only. |

The reviewer should produce the standard finding table (from `CLAUDE.md`) and mark these **blocker**.

## Anti-patterns

- **Template-literal interpolation of values**: `` pool.query(`SELECT id FROM orders WHERE id = '${orderId}'`) `` — even with a UUID, this trains the wrong habit and breaks (and injects) the moment the value is a string. Use `$1`.
- **`SELECT *` in an assertion**: hides which columns the test depends on; every schema change touches every test.
- **`BIGINT` compared as if it were a number**: `expect(Number(count)).toBe(3)` is right; `expect(count).toBe(3)` silently fails against `'3'`.
- **`DELETE FROM orders` in a test**: no `WHERE`, no cleanup helper. Truncate explicit tables in `beforeEach`.
- **Hidden Prisma/ORM lazy relation in an assertion**: reading `order.customer.name` off a fetched entity issues a second query the author can't see. Probe with explicit SQL.
- **`await new Promise(r => setTimeout(r, 5000))` before the assertion**: not deterministic; use `waitFor`.
- **`IN (...)` built by `values.map(v => `'${v}'`).join(',')`**: classic injection vector even in tests. Use `= ANY($1)` with a JS array.
- **`whereClause` / `table` built from runtime input** in the `exists` helper: only literal strings owned by the test code may flow into the SQL shape.
- **Logging the SQL with bound values**: leaks PII / secrets into structured logs. Log the probe *name* and IDs you already trust.
- **`bare knex('orders')` or `.select('*')`**: projects everything; name the columns.
- **`any` in a probe return type**: defeats the typed-projection guarantee; use a typed row.

## Examples

### Example 1 — assert one row exists with these columns

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
    expect(refund!.currency).toBe('EUR');
  });
});
```

### Example 2 — assert no row matches

```ts
it('failed payment does not create an order', async () => {
  await sut.attemptPayment(failingCardToken);

  const created = await exists(
    getPool(),
    'orders',
    'customer_id = $1',
    [customerId],
  );
  expect(created).toBe(false);
});
```

### Example 3 — poll until projection catches up

```ts
const refund = await waitFor(
  () => ordersDbProbe.getRefundFor(order.id),
  (r) => r.amountMinor === 15_000,
  { timeoutMs: 5_000, intervalMs: 100 },
);
expect(refund.currency).toBe('EUR');
```

## Anti-examples

```ts
// BLOCKER — template-interpolated value, no placeholder
const refund = await pool.query(
  `SELECT * FROM refunds WHERE order_id = '${orderId}'`);

// BLOCKER — DELETE without WHERE in a test body
await pool.query('DELETE FROM orders');

// MAJOR — SELECT *, hides what the assertion depends on
const { rows } = await pool.query('SELECT * FROM orders WHERE id = $1', [id]);

// MAJOR — BIGINT compared as a number without conversion
const { rows: c } = await pool.query('SELECT COUNT(*) AS count FROM orders');
expect(c[0].count).toBe(3);        // fails: '3' !== 3

// MAJOR — setTimeout as the assertion wait
await new Promise((r) => setTimeout(r, 5000));
const refund = await ordersDbProbe.getRefundFor(orderId);

// MAJOR — IN list built by string join
const ids = orderIds.map((i) => `'${i}'`).join(',');
const r = await pool.query(`SELECT id, status FROM orders WHERE id IN (${ids})`);

// MAJOR — hidden ORM lazy relation in the assertion
const order = await prisma.order.findUnique({ where: { id: orderId }, include: { customer: true } });
expect(order!.customer.name).toBe('Alice');   // extra query, surprise
```

## Rules

- Placeholder binding only — every value flows through the `$n` values array (or Knex `?` / `.where({...})`).
- Explicit column lists in every assertion query; typed projection types (never `any` / `Record<string, unknown>`).
- `SELECT EXISTS (...)` for boolean checks; `COUNT(*)` read via `Number(rows[0].count)` (string → number).
- `LIKE` patterns built in TS with `escapeLike` before binding, with `ESCAPE '\'`.
- `BIGINT` → `Number(...)` (or `BigInt`) explicitly; `timestamptz` → `Date`, asserted via ISO/epoch — no string-vs-number or by-reference `Date` comparisons.
- No `setTimeout` as an assertion wait — use `waitFor` with the same probe.
- No destructive verbs outside designated cleanup; refuse with the reviewer finding table.
- Probes are read-only modules using the shared `getPool()`; never `new pg.Client(...)` per test.
- Strict TS; ESM with explicit `.js` extensions; ESLint `no-floating-promises` on.
- Knex only when joins / windowing earn it; always explicit `.select(col, ...)`; `??` for identifiers, `?` for values in `knex.raw`.

## Handoffs

- Pool / fixture / cleanup wiring → `qa/typescript/skills/db-testing/client`
- Container lifecycle → `qa/typescript/skills/db-testing/testcontainers`
- Test data factories feeding seeders → `qa/typescript/skills/test-data-builder`
- .NET SQL guardrails → `qa/dotnet/skills/db-testing/query-author`
- Java SQL guardrails → `qa/java/skills/db-testing/query-author`
- Production data access SQL → `design-patterns/typescript/generator`
- Test strategy where DB tests fit → `qa/manual/test-strategy`
