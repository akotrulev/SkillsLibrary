---
name: unit-testing
description: Use when TypeScript backend logic needs a unit test with Vitest (seams, DI over vi.mock, coverage floor). Triggers "unit-test this service", "fake the clock". Not for HTTP tests (api-tests).
disable-model-invocation: true
---

# Node — Unit Testing (Vitest + TypeScript strict)

Owns **dev-side unit tests of backend logic**: construct a class or call a function directly, pass fakes in, assert on the return value or the observable effect on a fake collaborator. **In-process only — no HTTP, no container, no real database, no broker, no filesystem, no clock.**

**The boundary, one sentence:** if the test needs supertest, a booted Nest/Express app, a Testcontainer, or a live dependency, it is not a unit test and it belongs to the **peer** [`qa-api-typescript`](../../../../qa/typescript/agents/qa-api-typescript.md).

**Construct with `new`, not with a container.** `Test.createTestingModule` boots the DI container, the analogue of Spring's slice tests. `new PlaceOrderService(fakeRepo, fakePublisher, clock)` is faster and proves the constructor contract. Use `createTestingModule` only when the class depends on Nest-resolved metadata; never call `app.init()`/`app.listen()` here.

**This skill is not a licence to replace integration tests with mocks:**

| Never unit-test this | Because | Belongs to |
|---|---|---|
| A Prisma/Drizzle/TypeORM query | You'd be asserting against a query builder, not against SQL the engine accepted | `qa-api-typescript` `db-testing/testcontainers` |
| A migration | Only a real engine proves it applies | `qa-api-typescript` + `data-architect` |
| A transaction boundary / `$transaction` rollback | The engine is the mechanism | `qa-api-typescript` |
| JWT verification against a JWKS, guard/middleware chains end-to-end | The pipeline is the thing under test | `qa-api-typescript` `test-login-tokens`, `qa-security` |
| Route wiring, body parsing, `ValidationPipe` firing at the boundary | Transport concerns | `qa-api-typescript` |

**`mockDeep<PrismaClient>()` is the trap this table exists for**: a green test proving your code called a builder in a shape you also wrote. Put the query behind a repository interface, unit-test the logic against a fake of **your** interface, and verify the query against a real engine in the peer's lane.

## Version policy

The lane per `CLAUDE.md` 'Version policy'. `strict: true` applies to test files too; a test directory excluded from strict checking hides the API's real nullability.

## Stack

```jsonc
// package.json
"devDependencies": { "vitest": "^3", "@vitest/coverage-v8": "^3" },
"scripts": { "test": "vitest run", "test:watch": "vitest" }
```

```ts
// vitest.config.ts — unit lane only; the integration lane is a separate project/config
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],        // integration tests live under a different pattern/task
    clearMocks: true,
    restoreMocks: true,
    unstubEnvs: true,
  },
});
```

| Concern | What | Notes |
|---|---|---|
| Runner | **Vitest** | House default; **Jest if the repo already uses it** — don't introduce a second runner |
| Doubles | **plain functions / objects first**, then `vi.fn()` | A fake is a value in TypeScript; you rarely need a mocking framework |
| Module mocking | `vi.mock` — **last resort** | See the hoisting trap below |
| Time | `vi.useFakeTimers()` or an injected clock function | Prefer injection; fake timers for code you can't change |
| Schemas | Zod (already a dependency at the boundaries) | `safeParse` in tests, assert on `error.issues` |

**`clearMocks` + `restoreMocks` are not optional**: leaked call history is the #1 source of order-dependent flakes.

`tsc --noEmit` failing inside `node_modules` on a fresh setup (`Cannot find name 'Disposable'`) → read `references/tsc-prerequisite.md`.

## What deserves a unit test — the selection matrix

| Unit shape | Test it? | What to assert |
|---|---|---|
| Domain invariant / guard | **Yes** | Invalid input → the error branch; valid → accepted |
| Discriminated-union strategy dispatch | **Yes** | Each variant routes correctly; **an unhandled variant fails to compile** (see exhaustiveness) |
| `Result<T,E>` producer | **Yes** | **Both** branches — an `ok`-only test is half a test |
| Higher-order-function decorator | **Yes** | Inner called once with the same args **and** the added behavior (retry count, cache hit) |
| Handler / use-case orchestration | **Yes** | Collaborators driven correctly; the returned value; the failure branch |
| Calculation (minor units, rounding, dates) | **Yes** | Boundaries, the rounding rule, no float drift |
| Zod schema | **Yes** | Accept case; reject case + `issues[].path` and `code` |
| Branded-id conversion / parser | **Yes** | Valid → branded value; invalid → rejection, not a cast |
| Mapper / DTO↔domain | **Yes** | Each branch; unmapped input doesn't become `undefined` silently |
| Config loader's **validation** | **Yes** | Bad env → startup rejection with the offending key |
| Type-only module / interface | **No** | No runtime behavior to assert |
| Prisma/Drizzle query | **No** | Integration lane — peer |
| DI module / provider wiring | **No** | One bootstrap smoke test at most, and that's the peer's |
| Controller as pure transport | **No** | Logic in a controller is the defect — move it down |

**The tautology test:** if deleting the assertion leaves a passing test, delete the test.

## Project layout & setup

Match the repo. Colocated is the Vitest norm:

```
src/ordering/place-order.service.ts
src/ordering/place-order.service.test.ts      # this skill
src/ordering/__fakes__/in-memory-order-repository.ts
src/ordering/__builders__/order.builder.ts
```

- `*.test.ts` colocated (or `tests/unit/**` if the repo does that); **integration tests use a different include pattern**.
- A fake that can't satisfy the interface means the interface is too wide — narrow it to what the consumer needs (a `pattern-writer` edit).
- No shared mutable module state between tests; no top-level `let` a test mutates.

## Naming

`describe` names the unit, `it` states the behavior — `should X when Y` (`it('calls the repository')` is a mechanism):

```ts
describe('PlaceOrderService', () => {
  it('should reject the order when the cart is empty', …);
});
```

## The five seams — what makes logic untestable

If you can't write the test without one of these, **fix the seam first** — don't reach for `vi.mock`.

| Seam | Untestable | Injectable | Fake it with |
|---|---|---|---|
| **Time** | `Date.now()`, `new Date()`, `performance.now()` | a `clock: () => Date` parameter, or a `Clock` port | `() => new Date('2026-08-09T12:00:00Z')`, or `vi.setSystemTime` |
| **Identity** | `crypto.randomUUID()` | an `IdGenerator` port (or pass the id in) | a counter-backed stub |
| **Randomness** | `Math.random()` | an injected `random: () => number` | `() => 0.42` |
| **Config** | `process.env.X` read inside logic | a Zod-parsed config object passed in | the object literal, built once in the test |
| **Outbound I/O** | `fetch`, an SDK client, `fs` | your own typed port | a plain object implementing the port |

```ts
const clock = () => new Date('2026-08-09T12:00:00Z');
const service = new SubscriptionService(clock);
expect(service.isExpired({ expiresAt: new Date('2026-08-08T00:00:00Z') })).toBe(true);
```

**Never mock a type you don't own** — not `fetch`, not `PrismaClient`, not an SDK. Wrap it in your own port and pass a plain fake.

## Test doubles

**Preference order: real object → plain fake → `vi.fn()` spy → `vi.mock` (module).** In TypeScript a fake is just an object literal, so the first two cover most cases:

```ts
const fakeRepo: OrderRepository = {
  saved: [] as PlaceOrder[],
  async save(order) { this.saved.push(order); },
} as OrderRepository & { saved: PlaceOrder[] };
```

```ts
it('should publish OrderPlaced when the order is accepted', async () => {
  const publish = vi.fn();
  const service = new PlaceOrderService(fakeRepo, { publish }, clock);

  const result = await service.place({ customerId: CUSTOMER_ID, items: ['sku-1'] });

  expect(result.ok).toBe(true);
  expect(publish).toHaveBeenCalledTimes(1);
  expect(publish).toHaveBeenCalledWith(
    expect.objectContaining({ customerId: CUSTOMER_ID }),
  );
});
```

**Prefer a state assertion over a call assertion** where both work — `expect(fakeRepo.saved).toHaveLength(1)` survives a refactor that `toHaveBeenCalledWith` does not.

### `vi.mock` traps

- **`vi.mock` is hoisted above your imports.** The factory cannot close over a variable declared later in the file — that's the "Cannot access '…' before initialization" you'll hit. Use `vi.hoisted()` to declare shared fakes, or restructure so you don't need module mocking.
- **`vi.mock` applies to the whole file.** Two tests needing different module behavior are two files, or better, dependency injection.
- **Never `vi.mock` the module under test** or `vi.spyOn` a method of the class under test — you'd be testing your stub.
- **Async timer advancement is `await vi.advanceTimersByTimeAsync(ms)`** — the sync version won't flush promises.

## Both branches of every `Result<T,E>`

The house pattern is `Result<T,E>` over throwing (`pattern-writer`); the error path is where the business rules live:

```ts
it('should return InsufficientStock when stock is short', async () => {
  const result = await service.place({ customerId: CUSTOMER_ID, items: ['out-of-stock'] });

  expect(result.ok).toBe(false);
  if (!result.ok) expect(result.error.kind).toBe('InsufficientStock');   // narrows the union
});
```

**Exhaustiveness is a compile-time assertion.** A `never`-typed default (`const _exhaustive: never = variant`) breaks the build when a union member is added; keep it, and don't paper over it with a fallback `default:`.

## Zod schemas

```ts
it('should reject a missing customerId with a path-bearing issue', () => {
  const result = CreateOrderSchema.safeParse({ items: [] });

  expect(result.success).toBe(false);
  if (!result.success) {
    expect(result.error.issues[0]?.path).toEqual(['customerId']);
    expect(result.error.issues[0]?.code).toBe('invalid_type');
  }
});
```

Assert the **path and code**, not the message.

## Parameterized tests

`it.each` replaces `if`/`for` around assertions:

```ts
it.each([
  [1,   1],      // minor units in, minor units out
  [999, 999],
  [1000, 1000],
])('should keep %i cents exact', (input, expected) => {
  expect(roundMinorUnits(input)).toBe(expected);
});
```

## Beyond example tests

- [`references/property-based-testing.md`](references/property-based-testing.md) — a rule over a whole input range or a stateful unit vs a model (fast-check).
- [`references/snapshot-testing.md`](references/snapshot-testing.md) — a large output's whole shape is the contract (Vitest snapshots).

## Money — the JS-specific trap

**Never `number` floats for money** (`0.1 + 0.2 !== 0.3`). Use **integer minor units** (the `solution-planner` data-model default) or a decimal library, and assert on integers.

## Test data

- 1–3 fields: inline object literals.
- **4+ fields: a builder** with defaults, so a test overrides only its subject. In TS, a factory with a partial override:

```ts
const anOrder = (over: Partial<Order> = {}): Order => ({ ...defaults, ...over });
const shipped = anOrder({ status: 'Shipped' });
```

- Suite-scale fixtures → **peer** `qa-typescript:test-data-builder`.

## Async

- `await expect(promise).rejects.toThrow(SpecificError)` — assert the **type/kind**, not the message.
- A floating promise in a test is a silently passing test.
- `AbortSignal` propagation is behavior worth a test on anything long-running.

## Rules

The standards a test must meet are the be-node rule file `node-tests.md`, plus `node-config.md` for the Vitest config, not a list here. Read the project's copy in `.claude/rules/be-node/`, or the plugin's in `backend/node/skills/rules/` when the project has not installed them (`/be-node:rules` does). Where it and this skill disagree, the rule file wins. The coverage floor below is how its 80% rule is measured.

## Coverage floor — ≥ 80% of the branches you wrote

The tests cover **at least 80% of the branches in the code the change wrote**: every module it created, whole, and the functions it changed in a module that already existed. The scope is the change, never the repo — a legacy module's low number is not the excuse, and the repo-wide number is not the target.

- **Design for every branch; 80% is what gets measured.** Before writing tests, list the branch outcomes in the code you wrote — each `if`/`else` arm, `switch` case and its `default`, ternary, `??` and `?.`, short-circuit `&&`/`||`, a default parameter value, guard-clause return, `catch`, a loop run zero times and many, **both `Result` branches** — and give each a test or an `it.each` row that asserts its effect. The slack under 100% is for branches no honest unit test reaches, such as the `never` default of an exhaustive `switch`.
- **Only an asserting test counts.** A test that runs a branch without asserting what it did is a **major** finding; with no TypeScript mutation skill yet, the tautology test is this stack's only guard against hollow coverage.
- **Leave out what the matrix says not to test, by name.** Type-only files, barrels, constants and generated clients stay out of the measured file list, and the report names each one left out. Never reach 80% by lowering the number or by a `/* v8 ignore … */` hint over code that has behavior.
- **Measure.** Inside a plan task, the `Gate:` line runs this over the files the task and the landed tasks above it touched. Outside a plan, run it before you report (with the project's package manager — `npx`, `pnpm exec`, `yarn`):

  ```bash
  npx vitest run --coverage --coverage.reporter=text \
    --coverage.include=src/orders/place-order.ts --coverage.include=src/orders/pricing.ts
  ```

  `% Branch` on the `All files` row is the number; `Uncovered Line #s` points at the misses. **Name the files**: Vitest 4 reports only the files a test loaded, so an untested new module vanishes from the table instead of counting as 0% unless `--coverage.include` lists it. `@vitest/coverage-v8` matches the Vitest major.
- **Below 80%, write the missing tests.** The uncovered lines are the list.

## Generation steps

1. **Detect** the Node major, package manager, runner (Vitest/Jest), and existing test conventions — **the repo's choice wins**.
2. **Identify the units** from the selection matrix — for each type `pattern-writer`/`database-code` just produced, decide test / no-test and say why for the no-tests. For each tested unit, **list its branch outcomes**: that list is the test plan (*Coverage floor*).
3. **Fix the seams first** — a direct `Date.now()`, `crypto.randomUUID()`, `process.env` read, or `fetch` call is a `pattern-writer`-shaped edit to production code, done before the test.
4. **Write the failing test**, watch it fail for the right reason (the run a `Gate: own tests` task may make), make it pass.
5. **Add the boundary cases** with `it.each` — nulls, empties, min/max, the rounding boundary, **both `Result` branches**, the refused transition.
6. **Verify:** the project's test script green (from `package.json`, run with its `packageManager`), `tsc --noEmit` clean, lint clean, branch coverage of the changed code ≥ 80% (*Coverage floor*). Report counts and the coverage figure. Inside a plan task, `Gate: own tests` runs this task's tests — step 4's red run, then green —, the tests of the landed tasks above it, and the *Coverage floor* measure over the files the task and those tasks touched; the last runnable task runs everything else.
7. **Sweep:** a union whose members are handled in one place but tested in one case is a gap.
