---
name: qa-test-data-builder-typescript
description: Use when the user asks to create test data factories or ObjectMothers in a Node + TypeScript test project to replace duplicated inline literals across tests with named, intention-revealing factories. Triggers: "create a builder for User in TS", "set up test data for X in Vitest", "extract this fixture into a factory". Do NOT use for many-row data files (`qa-data-driven-testing-typescript`) or database seeding (`qa-db-connection-typescript`).
---

# QA — Test Data Builder / ObjectMother (TypeScript / Node 24)

Eliminates repeated inline test data literals in TypeScript test projects (Vitest primary) by generating function-based factories with `Partial<T>` overrides and ObjectMother namespaces. Required by `CLAUDE.md`: "Builder pattern for test data objects with 4+ fields" and "Test data via builders or ObjectMother, not inline literals duplicated across tests."

## When to use

- Two or more tests construct the "same" object with slightly different fields → extract a factory
- One test sets 6 fields just to test one behavior → extract a factory that defaults the other 5
- A complex aggregate (Order → Lines → Customer → Address) needs assembling for many tests
- Reading a test is hard because half the body is data setup
- API tests need a known-shape DTO with one varying field per scenario

## When NOT to use

- .NET test data → `qa/dotnet/skills/test-data-builder`
- Java test data → `qa/java/skills/test-data-builder`
- Production-code builders → the `backend/node` dev stack's generator, if installed
- Test data for performance scenarios (volume) → `qa/typescript/skills/load-testing`
- One-off fixture used by a single test → inline is fine; only extract on duplication

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

## Rules

- Factories live under `tests/builders/`; ObjectMothers under `tests/mothers/`.
- Every field has a sensible default — adding a non-nullable field doesn't ripple through 50 tests.
- One factory per aggregate; child aggregates have their own factories.
- Defaults are deterministic literals; only id-like fields use random with reason (seeded faker).
- Factory return type is the real DTO type (the same shape the production code consumes), not `any` / `Record<string, unknown>`.
- ObjectMother methods accept `Partial<T>` and return the built object (because TS already has `Partial`).
- Tests never construct domain objects with inline literals across more than 1–2 places — extract to a factory.
- Strict TypeScript: no `any`, no `as unknown as X`, factory params and returns fully typed.
- No async / `Promise<T>` returns from factories — factories are pure.
- ESLint `no-floating-promises` enabled to catch missed `await` on persistence calls (which live outside the factory).

## What NOT to do

- No inline test data literals duplicated across test files.
- No `null` for required fields in defaults — pick a real default.
- No randomness on fields the test asserts against.
- No "god factory" with 30 optional parameters covering 4 unrelated aggregates — split per aggregate.
- No persistence in the factory — shape and save are separate concerns.
- No production-code factories disguised as test factories ("we'll reuse this in prod too") — separate them; remove `Test*` prefix only when promoting deliberately.
- No exposing mutable arrays without `ReadonlyArray<>` — accidental in-place mutation across tests is hard to debug.
- No defaults that violate domain invariants (e.g. negative `totalMinor`) — the default factory must produce a valid object.
- No mixing factory + class builder for the same aggregate — pick one.
- No `Object.assign({}, defaults, overrides)` — use spread (`...`) so TS narrows the literal correctly.
- No `Date.now()` / `new Date()` calls in defaults — pin an ISO string so the date doesn't drift across runs.

## Generation steps

1. Grep the test tree for repeated literal patterns (`{ id: …, customerId: …, status: … }`, request body literals in API tests).
2. Per aggregate, list the fields, the sensible defaults, and the variant-producing helpers (`pending`/`paid`/`cancelled` etc.).
3. Generate the factory under `tests/builders/<noun>.ts` following the template.
4. Add an ObjectMother under `tests/mothers/<noun>.ts` with the canonical variants.
5. Replace inline literals in 2–3 representative tests so the pattern is set; leave the rest as a follow-up sweep.
6. Run the project's own test script with the package manager `packageManager` names — every test still passes with the new defaults.
7. Run `tsc --noEmit` — strict TS green. Inside a plan task marked `Gate: none`, run none of steps 6–7 and report the files as "written, not run".

## Handoffs

- .NET test data → `qa/dotnet/skills/test-data-builder`
- Java test data → `qa/java/skills/test-data-builder`
- API tests where these feed into request bodies → `qa/typescript/skills/api-test-author/writer`
- UI tests where they back form-fill helpers → `qa/typescript/skills/ui-test-author/playwright` / `qa/typescript/skills/ui-test-author/selenium` / `qa/typescript/skills/ui-test-author/appium`
- Test reviewers (verify factories used, not literals) → `qa/typescript/skills/api-test-author/review` / `qa/typescript/skills/ui-test-author/review`
- Test strategy / pyramid → `qa/manual/test-strategy`
- Production-code builders → the `backend/node` dev stack's generator, if installed
