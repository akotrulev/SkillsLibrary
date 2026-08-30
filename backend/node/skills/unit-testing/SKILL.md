---
name: be-node-unit-testing
description: Use when backend TypeScript logic needs a dev-side unit test — Vitest (Jest when the repo uses it): what deserves a test, the five untestable seams (time, id, randomness, config, outbound I/O), DI over `vi.mock`, both branches of every `Result<T,E>`, Zod schema tests. In-process, no HTTP, container, or real database. Triggers "unit-test this service", "test this Zod schema", "how do I fake the clock in Vitest". Do NOT use for supertest/HTTP-level or integration tests (`qa-api-typescript`).
---

# Node — Unit Testing (Vitest + TypeScript strict)

Owns **dev-side unit tests of backend logic**: construct a class or call a function directly, pass fakes in, assert on the return value or the observable effect on a fake collaborator. **In-process only — no HTTP, no container, no real database, no broker, no filesystem, no clock.**

**The boundary, one sentence:** if the test needs supertest, a booted Nest/Express app, a Testcontainer, or a live dependency, it is not a unit test and it belongs to the **peer** [`qa-api-typescript`](../../../../qa/typescript/agents/qa-api-typescript.md).

**Construct with `new`, not with a container.** For NestJS, `Test.createTestingModule` boots the DI container — it is the Node analogue of Spring's slice tests. A logic class needs none of it: `new PlaceOrderService(fakeRepo, fakePublisher, clock)` is faster, has no metadata failure modes, and proves the constructor contract. Reach for `createTestingModule` only when the class genuinely depends on Nest-resolved metadata, and never call `app.init()`/`app.listen()` here.

**This skill is not a licence to replace integration tests with mocks.** `CLAUDE.md`'s preference for real-DB integration tests over mocks governs the integration lane, which is the peer's:

| Never unit-test this | Because | Belongs to |
|---|---|---|
| A Prisma/Drizzle/TypeORM query | You'd be asserting against a query builder, not against SQL the engine accepted | `qa-api-typescript` `db-testing/testcontainers` |
| A migration | Only a real engine proves it applies | `qa-api-typescript` + `data-architect` |
| A transaction boundary / `$transaction` rollback | The engine is the mechanism | `qa-api-typescript` |
| JWT verification against a JWKS, guard/middleware chains end-to-end | The pipeline is the thing under test | `qa-api-typescript` `test-login-tokens`, `qa-security` |
| Route wiring, body parsing, `ValidationPipe` firing at the boundary | Transport concerns | `qa-api-typescript` |

**`mockDeep<PrismaClient>()` is the trap this table exists for.** It produces a green test that proves your code called a builder in a shape you also wrote. Put the query behind a repository interface, unit-test the logic against a fake of **your** interface, and verify the query itself against a real engine in the peer's lane.

## Version policy

**First act: detect the Node major and the package manager** (`package.json` `engines`, `packageManager`, the lockfile). **Node 24 active LTS primary, 22 maintenance supported. Node 20 is EOL (April 2026)** — flag it, don't target it. `strict: true` in `tsconfig.json` applies to test files too; a test directory excluded from strict checking hides the API's real nullability.

## When to use

- A class or function `pattern-writer` just generated has behavior: a discriminated-union strategy, a `Result<T,E>` producer, a higher-order-function decorator, a handler, a factory.
- A domain rule, invariant, or guard needs pinning before a refactor.
- A calculation: money (minor units), rounding, proration, date math.
- A Zod schema — its accept **and** reject cases, including the error path.
- A mapper, a branded-id conversion, an error-to-ProblemDetails translation.
- Reproducing a bug at the unit level before fixing it (`ep-systematic-debugging` RED, `ep-test-driven-development`).

## When NOT to use

- supertest / a booted app / HTTP-level assertions → **peer** `qa-api-typescript`
- Contract / integration / E2E, Testcontainers, real-DB seed-assert-clean → **peer** `qa-api-typescript` (`db-testing/*`)
- Whether the tests actually catch faults (mutation score) → **peer** `qa-test-quality-check-typescript` (StrykerJS) — **not built yet; see Handoffs**
- Suite-scale builders / fixtures → **peer** `qa-test-data-builder-typescript`
- React components / hooks → `fe-react-component-testing`
- **Types with no runtime behavior, barrel re-exports, constants, generated clients** → don't test them at all

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
    clearMocks: true,                     // reset call history between tests
    restoreMocks: true,                   // undo spies — order-independence, not politeness
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

**`clearMocks` + `restoreMocks` are not optional.** Leaked call history across tests is the #1 source of order-dependent flakes in Vitest suites.

**The `tsc` prerequisite the Step-3 gate depends on.** Vitest's own type surface needs Node types and a modern `lib`, or `tsc --noEmit` fails inside `node_modules` (`Cannot find name 'Disposable' / 'setImmediate'`, `Cannot find type definition file for 'node'`) — errors that have nothing to do with your code and will block the gate on a fresh setup. The test lane needs:

```jsonc
// tsconfig.json
"lib": ["ESNext"],                       // Symbol.asyncDispose, used by rollup/vite types
"types": ["node", "vitest/globals"]      // + devDependency @types/node matching the Node major
```

Add `@types/node` at the **project's** Node major (24 → `@types/node@24`, 22 → `@types/node@22`) — a mismatched major reintroduces the same class of error.

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

- `*.test.ts` colocated (or `tests/unit/**` if the repo does that) — **integration tests must use a different include pattern** so `pnpm test` stays fast and this lane stays honest.
- **No `any` in tests, no `as unknown as X` to force a fake.** A fake that can't satisfy the interface means the interface is too wide — narrow it to what the consumer needs (that's a `pattern-writer` edit).
- No shared mutable module state between tests; no top-level `let` a test mutates.

## Naming

`describe` names the unit, `it` states the behavior — `should X when Y` (`CLAUDE.md`):

```ts
describe('PlaceOrderService', () => {
  it('should reject the order when the cart is empty', …);
  it('should publish OrderPlaced when the order is accepted', …);

  // bad
  it('works', …);
  it('calls the repository', …);   // a mechanism, not a behavior
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
- **`vi.mock` is per-module-graph, not per-test.** It applies to the whole file. If two tests in one file need different module behavior, that's two files — or, better, dependency injection.
- **`vi.mocked(x)`** is a typing helper only; it doesn't create a mock.
- **Never `vi.mock` the module under test** or `vi.spyOn` a method of the class under test — you'd be testing your stub.
- **`vi.useFakeTimers()` must be paired with `vi.useRealTimers()`** in cleanup, and async timer advancement is `await vi.advanceTimersByTimeAsync(ms)` — the sync version won't flush promises.
- **Don't assert on the logger.** Logs aren't the contract.

## Both branches of every `Result<T,E>`

The stack's house pattern is `Result<T,E>` over throwing (`pattern-writer`). A test suite that only asserts the `ok` branch leaves the error path unproven — and the error path is where the business rules live:

```ts
it('should return InsufficientStock when stock is short', async () => {
  const result = await service.place({ customerId: CUSTOMER_ID, items: ['out-of-stock'] });

  expect(result.ok).toBe(false);
  if (!result.ok) expect(result.error.kind).toBe('InsufficientStock');   // narrows the union
});
```

**Exhaustiveness is a compile-time assertion.** If dispatch uses a `never`-typed default (`const _exhaustive: never = variant`), adding a union member breaks the build — a stronger guarantee than any runtime test. Keep it, and don't paper over it with a `default:` that returns a fallback.

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

Assert the **path and code**, not the human-readable message — messages are localizable and change between Zod versions.

## Parameterized tests

`CLAUDE.md` forbids `if`/`for` driving assertions. `test.each` is the escape hatch:

```ts
it.each([
  [1,   1],      // minor units in, minor units out
  [999, 999],
  [1000, 1000],
])('should keep %i cents exact', (input, expected) => {
  expect(roundMinorUnits(input)).toBe(expected);
});
```

## Money — the JS-specific trap

**Never `number` floats for money.** `0.1 + 0.2 !== 0.3`, and `toBe` will show you exactly that. Use **integer minor units** (the house default per `solution-planner`'s data-model conventions) or a decimal library, and assert on integers. A money test whose expected value is `0.30000000000000004` is a design finding, not a test to adjust.

## Test data

- 1–3 fields: inline object literals.
- **4+ fields: a builder** (`CLAUDE.md`) with defaults, so a test overrides only its subject. In TS the cheapest readable form is a factory with a partial override:

```ts
const anOrder = (over: Partial<Order> = {}): Order => ({ ...defaults, ...over });
const shipped = anOrder({ status: 'Shipped' });
```

- Suite-scale fixtures → **peer** `qa-test-data-builder-typescript`.

## Async

- `await expect(promise).rejects.toThrow(SpecificError)` — assert the **type/kind**, not the message.
- Every promise is awaited; a floating promise in a test is a silently passing test.
- No `setTimeout`-based waiting. If the code needs time to pass, that's the clock seam or `vi.advanceTimersByTimeAsync`.
- `AbortSignal` propagation is behavior worth a test on anything long-running.

## Rules

- One logical assertion per test; group related expectations on one object with `toMatchObject`.
- Arrange–Act–Assert, visibly separated. A 20-line arrange is a coupling finding.
- Tests are independent and order-free; `clearMocks`/`restoreMocks` on.
- The unit under test is real and constructed directly — never resolved from a DI container.
- Verify RED once per new behavior (`ep-test-driven-development`).
- `strict: true` applies; no `any`, no `as unknown as`.
- No coverage-% gate here — assertion quality is a mutation-score question (see Handoffs).

## What NOT to do

- **`mockDeep<PrismaClient>()`** to "unit-test the repository" — proves nothing about SQL. Integration lane.
- **supertest / `app.init()` / `createTestingModule().compile()` + full app** in this lane — that's the peer's suite.
- **An in-memory SQLite standing in for Postgres** — dialect differences make it a false-negative machine.
- **`vi.mock` where a constructor parameter would do** — module mocking couples the test to the import graph.
- **`as any` to satisfy a fake** — narrow the interface instead.
- **Snapshot-testing an object** as the only assertion — it locks shape, proves no behavior, and gets blind-updated with `-u`.
- **Testing only the `ok` branch** of a `Result`.
- **`it.skip` without a linked issue** — quarantine is the reporting peer's process.
- **Testing the framework** — that Zod validates, that Nest injects, that `structuredClone` clones.
- **Reaching into a module's private state** via `// @ts-expect-error` — extract the concept instead.

## Generation steps

1. **Detect** the Node major, package manager, runner (Vitest/Jest), and existing test conventions — **the repo's choice wins**.
2. **Identify the units** from the selection matrix — for each type `pattern-writer`/`database-code` just produced, decide test / no-test and say why for the no-tests.
3. **Fix the seams first** — a direct `Date.now()`, `crypto.randomUUID()`, `process.env` read, or `fetch` call is a `pattern-writer`-shaped edit to production code, done before the test.
4. **Write the failing test**, watch it fail for the right reason, make it pass.
5. **Add the boundary cases** with `it.each` — nulls, empties, min/max, the rounding boundary, **both `Result` branches**, the refused transition.
6. **Verify:** `pnpm test` green, `tsc --noEmit` clean, lint clean. Report counts.
7. **Sweep:** a union whose members are handled in one place but tested in one case is a gap.

## Handoffs

- supertest / HTTP-level, contract / integration / E2E → **peer** [`qa-api-typescript`](../../../../qa/typescript/agents/qa-api-typescript.md)
- Real-DB verification, Testcontainers → **peer** `qa/typescript/skills/db-testing/*`
- Do the tests actually catch faults? → **peer** `qa-test-quality-check-typescript` (StrykerJS) — **this skill does not exist yet**; the java/dotnet siblings do. Until it lands, treat mutation grading as unavailable on this stack rather than substituting a coverage number (tracked in `backend/UNIT-TESTING-PLAN.md` §7)
- Suite-scale builders / fixtures → **peer** `qa/typescript/skills/test-data-builder`
- Flaky triage / quarantine → **peer** `qa/reporting/typescript/skills/flaky-test-quarantine`
- The red-green-refactor loop → [`ep-test-driven-development`](../../../../engineering-practices/test-driven-development/SKILL.md)
- The unit needs a seam / a pattern → [`pattern-writer`](../pattern-writer/SKILL.md)
- Reviewing the tests with the change → [`code-review`](../code-review/SKILL.md)
- .NET equivalent → `backend/dotnet/skills/unit-testing` · Java equivalent → `backend/java/skills/unit-testing`
