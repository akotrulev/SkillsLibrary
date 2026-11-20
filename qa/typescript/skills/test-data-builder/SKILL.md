---
name: test-data-builder
description: Use when creating test data builders/ObjectMothers in a TypeScript test project to replace duplicated literals. Triggers "create a builder for User". Not for row data files (data-driven-testing).
disable-model-invocation: true
---

# QA — Test Data Builder / ObjectMother (TypeScript / Node 24)

Eliminates repeated inline test data literals in TypeScript test projects (Vitest primary) by generating function-based factories with `Partial<T>` overrides and ObjectMother namespaces. Required by `CLAUDE.md`: "Builder pattern for test data objects with 4+ fields" and "Test data via builders or ObjectMother, not inline literals duplicated across tests."

## Factory function vs class builder vs ObjectMother

| Pattern | When to choose |
|---|---|
| **Factory function** (`anOrder(overrides?)`) | Default — idiomatic TS, zero boilerplate, `Partial<T>` overrides |
| **Class builder** (`new OrderBuilder().withTotal(…).build()`) | Complex aggregates with conditional construction logic / list mutation that's awkward as overrides |
| **ObjectMother namespace** (`Orders.paid({ totalMinor: 15000 })`) | A few named canonical variants on top of the factory |

If you would write `anOrder()` with no overrides in 90% of cases → ObjectMother is what you actually want.

## Layout

```
tests/
├── builders/
│   ├── order.ts                     ← factory + types
│   ├── customer.ts
│   └── orderLine.ts
└── mothers/
    ├── orders.ts
    └── customers.ts
```

`tests/builders/` and `tests/mothers/` live in the test tree. They never appear in `src/`.

## Factory function template

```ts
// tests/builders/order.ts
import { faker } from '@faker-js/faker';

export type OrderStatus = 'pending' | 'paid' | 'cancelled' | 'refunded';

export type TestOrderLine = {
  sku: string;
  qty: number;
  priceMinor: number;
};

export type TestOrder = {
  id: string;
  customerId: string;
  status: OrderStatus;
  totalMinor: number;
  currency: string;
  placedAt: string;            // ISO 8601
  lines: ReadonlyArray<TestOrderLine>;
};

export function anOrder(overrides: Partial<TestOrder> = {}): TestOrder {
  return {
    id: faker.string.uuid(),
    customerId: 'cus_alice',
    status: 'pending',
    totalMinor: 9_999,
    currency: 'EUR',
    placedAt: '2026-01-01T12:00:00Z',
    lines: [{ sku: 'A', qty: 1, priceMinor: 9_999 }],
    ...overrides,
  };
}

export function anOrderLine(overrides: Partial<TestOrderLine> = {}): TestOrderLine {
  return {
    sku: 'A',
    qty: 1,
    priceMinor: 9_999,
    ...overrides,
  };
}
```

## ObjectMother on top

```ts
// tests/mothers/orders.ts
import { anOrder, type TestOrder } from '../builders/order.js';

export const Orders = {
  pending:  (overrides: Partial<TestOrder> = {}): TestOrder => anOrder({ status: 'pending',  ...overrides }),
  paid:     (overrides: Partial<TestOrder> = {}): TestOrder => anOrder({ status: 'paid',     ...overrides }),
  refunded: (overrides: Partial<TestOrder> = {}): TestOrder => anOrder({ status: 'refunded', ...overrides }),
} as const;
```

## Usage in Vitest

```ts
import { describe, it, expect } from 'vitest';
import { Orders } from '../mothers/orders.js';

describe('order cancellation', () => {
  it('succeeds for pending orders', () => {
    const order = Orders.pending();
    // arrange / act / assert
  });

  it('refunds to card for paid orders', () => {
    const order = Orders.paid({ totalMinor: 15_000 });
    // ...
  });
});
```

Same factory works under Playwright Test, Jest, WebdriverIO — the runner doesn't care.

## When to escalate to a class builder

For aggregates where you want to incrementally append children, or where the overrides API gets unwieldy:

```ts
export class OrderBuilder {
  private order: TestOrder = anOrder();

  forCustomer(id: string)        { this.order = { ...this.order, customerId: id }; return this; }
  withStatus(s: OrderStatus)     { this.order = { ...this.order, status: s }; return this; }
  withTotal(minor: number, ccy = 'EUR')
                                 { this.order = { ...this.order, totalMinor: minor, currency: ccy }; return this; }
  addLine(l: TestOrderLine)      { this.order = { ...this.order, lines: [...this.order.lines, l] }; return this; }

  build(): TestOrder             { return this.order; }
}
```

Rule of thumb: start with `anOrder({ ... })`. Promote to a class builder only when you've seen three or more tests fighting the `Partial<T>` shape (typically because they assemble children incrementally).

## Conventions

- **Sensible default for every field** — a test never has to know about fields it doesn't care about.
- **Factory function name** is `a{Noun}` / `an{Noun}` (`anOrder`, `aCustomer`) — reads naturally at the call site.
- **ObjectMother is a `const` namespace** (`Orders.paid(...)`), not a class.
- **Types live next to the factory** (`export type TestOrder`); don't import production types into the test factory unless they're already exported as DTOs.
- **`Test*` prefix** on test-only types when there's any risk of confusion with a production type.
- **`Partial<T>` overrides spread last** so caller wins over defaults.
- **`as const`** on the ObjectMother literal to lock the shape.
- **ESM extensions** (`'../builders/order.js'`) when `"type": "module"` is set.

## Random vs deterministic data

- **Default to deterministic literal defaults** (`'cus_alice'`, `'2026-01-01T12:00:00Z'`).
- Use `@faker-js/faker` **only** for fields where uniqueness matters per test (ids) and where any value is acceptable.
- Seed faker deterministically when randomness touches assertions:

  ```ts
  // tests/setup.ts
  import { faker } from '@faker-js/faker';
  import { beforeAll } from 'vitest';
  beforeAll(() => { faker.seed(42); });
  ```

- **Never** assert on a random field — assert on the field you set; defaults are scaffolding.

## Production-shaped data and PII

- **Never copy production rows** into a builder default, a seed script, a fixture file or a test asset. A
  dump, an export or a pasted record is personal data the moment it lands in the repo, a CI log or a report.
- **Defaults are obviously synthetic but realistic**: a valid format and a plausible length, so validation and
  layout are exercised, and nobody owns the value — `Mira Kovac`, `mira.kovac@example.com`,
  `+44 7700 900123`. Reserved names only: `example.com` / `.test` domains (RFC 2606), Ofcom's
  `07700 900000–900999` drama range or the US `555-0100–0199` range. Never `test@test.com`, `foo` or
  `John Doe`: they hide the formats the field really accepts.
- **When a test needs production shape** (real distributions, edge-case values, volume), mask a copy outside
  the repo with a **deterministic pseudonymiser**: one keyed hash per field class, so a real value always maps
  to the same fake one. Referential integrity survives — a customer id masked in `customers` and in `orders`
  still joins — and a rerun rebuilds the same dataset. The key comes from the secret store, never the repo;
  without it the mapping cannot be rebuilt by hashing a phone book.

| Field class | Masked as |
|---|---|
| Email | `user.<token>@example.com` |
| Phone | a number in the fictional range, picked by the hash |
| Name, address | a faker seeded from the hash |
| Ids, account numbers | a prefix plus the token, same length and format where the API validates it |
| Free text (notes, comments) | replaced whole — it carries PII no pattern finds |
| Date of birth | shifted by a hash-derived number of days, same age band |

```ts
import { createHmac } from 'node:crypto';
import { Faker, en } from '@faker-js/faker';

export function createPseudonymizer(key: Buffer) {
  const hash = (real: string, fieldClass: string): Buffer =>
    createHmac('sha256', key).update(`${fieldClass}:${real}`).digest();
  const token = (real: string, fieldClass: string): string => hash(real, fieldClass).subarray(0, 6).toString('hex');
  const number = (real: string, fieldClass: string, bound: number): number => hash(real, fieldClass).readUInt32BE(0) % bound;
  const seeded = (real: string, fieldClass: string): Faker => {
    const faker = new Faker({ locale: [en] });
    faker.seed(number(real, fieldClass, 2 ** 31));
    return faker;
  };

  return {
    email: (real: string) => `user.${token(real, 'email')}@example.com`,
    phone: (real: string) => `+44 7700 900${String(number(real, 'phone', 1000)).padStart(3, '0')}`,
    fullName: (real: string) => seeded(real, 'name').person.fullName(),
    streetAddress: (real: string) => seeded(real, 'address').location.streetAddress(),
    customerId: (real: string) => `cus_${token(real, 'customer')}`,
  } as const;
}
```

A seeded `Faker` instance per value, never the shared `faker` singleton: reseeding the singleton would change
every other test's random fields.

Mask every column that identifies a person on its own or combined (postcode + date of birth + gender); amounts,
enums and timestamps that carry no identity stay as they are. Before the set is used, grep it for the source's
email domains and phone prefixes — a hit fails the masking job.

## Aggregate / child relationships

```ts
const customer = Customers.alice();
const order = Orders.paid({
  customerId: customer.id,
  lines: [
    anOrderLine({ sku: 'B', qty: 2, priceMinor: 5_000 }),
  ],
});
```

- For list-typed fields, prefer constructing the list outside and passing via overrides.
- `ReadonlyArray<...>` on the type prevents accidental mutation; spread to a new array when modifying.

## Persistence-aware factories

Separate **shape building** from **persistence**:

```ts
// Shape only — pure.
const order = Orders.pending();

// Persistence — through the same client production uses.
const created = await ordersClient.createTyped(order, 201);
```

Don't build "an order in the DB" inside the factory — that couples the factory to a particular persistence path and hides the API call dependency. Persistence is the test's job; the factory is shape.

## Data the test did not create: three sanctioned patterns

The default is the one above: the test builds a value unique to it, persists it through a client or seeder, and registers it for teardown. The rule file `test-data.md` sanctions three more. None of them changes the builder, which stays pure and deterministic.

- **Read-only reference data.** A search or filter test may read curated records that already exist in the environment. Name them where the test reads them, as constants in a mother (`tests/mothers/reference.ts`: `ReferenceDeals.januaryShipped = { tradeDate: '2026-01-15', dealType: 'Swap' }`) or in the feature's `Examples`, and never write to them. The test asserts that at least one row came back before it asserts on the rows: "every row has X" over an empty result proves nothing.
- **Pre-clean.** A precondition removes a leftover record before the test, in addition to teardown, so a crashed run cannot poison the next one. It is a seeder method, `customerSeeder.deleteByEmail(email)`, which searches and deletes every match, so a clean environment is zero deletions rather than a branch. Call it from the hook, fixture or `Given … does not exist` step that needs it; never drive the UI to clean up.
- **Keep on failure.** The teardown registry deletes when the test passed and logs the kept ids when it failed (`ui-test-author/playwright`, `references/config-and-fixtures.md` §2). The identifying field then has to be unique per run, so the fixture overrides it at the call site, ``anOrder({ title: `QA order ${randomUUID()}` })``, and the builder default stays deterministic.

## Typed query-parameter builder

A search endpoint with several documented parameters gets a builder too: one fluent method per parameter, building the suite's typed parameter object. The client turns that object into the query string; a test never passes positional strings or an untyped `Record<string, string>`.

```ts
export type OrderSearchParams = {
  readonly status?: OrderStatus;
  readonly customerId?: string;
  readonly placedFrom?: string;
  readonly page?: number;
  readonly pageSize?: number;
};

export class OrderSearchParamsBuilder {
  private params: OrderSearchParams = {};

  status(status: OrderStatus)       { this.params = { ...this.params, status }; return this; }
  customerId(customerId: string)    { this.params = { ...this.params, customerId }; return this; }
  placedFrom(isoDate: string)       { this.params = { ...this.params, placedFrom: isoDate }; return this; }
  page(page: number)                { this.params = { ...this.params, page }; return this; }
  pageSize(pageSize: number)        { this.params = { ...this.params, pageSize }; return this; }

  build(): OrderSearchParams        { return this.params; }
}
```

```ts
const params = new OrderSearchParamsBuilder().status('Shipped').pageSize(25).build();
const result = await ordersClient.searchTyped(params, 200);
```

The method names are the documented parameter names, so the builder doubles as the list of what the endpoint accepts. A parameter the API adds is one more method and one more optional field.

## Rules

Factories live under `tests/builders/`, ObjectMothers under `tests/mothers/`, one factory per aggregate.

The standards this skill's output must meet are the qa-typescript rule files, not a list here: `qa-typescript.md` and `test-data.md`. Read the project's copy in `.claude/rules/qa-typescript/`, or the plugin's in `qa/typescript/skills/rules/` when the project has not installed them (`/qa-typescript:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Generation steps

1. Grep the test tree for repeated literal patterns (`{ id: …, customerId: …, status: … }`, request body literals in API tests).
2. Per aggregate, list the fields, the sensible defaults, and the variant-producing methods (`pending`/`paid`/`cancelled` etc.).
3. Generate the factory under `tests/builders/<noun>.ts` following the template.
4. Add an ObjectMother under `tests/mothers/<noun>.ts` with the canonical variants.
5. Replace inline literals in 2–3 representative tests so the pattern is set; leave the rest as a follow-up sweep.
6. Run the project's own test script with the package manager `packageManager` names — every test still passes with the new defaults.
7. Run `tsc --noEmit` — strict TS green.
