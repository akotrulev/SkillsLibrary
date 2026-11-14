# Property-based testing with fast-check

Read this when a unit's rule holds for **every** input in a domain, not just the handful an `it.each` table lists:
money arithmetic in minor units, rounding and allocation, parsers and serializers, a state machine, a collection or
cache the code implements itself. A property test states the rule once, fast-check generates a hundred inputs, and a
failure shrinks to the simplest input that still breaks it.

## When a property test earns its place

| Signal | Example test is enough | Add a property test |
|---|---|---|
| The rule names specific values | "an empty cart is rejected" | — |
| The rule holds for a whole range | — | "allocating any amount across any split loses no minor unit" |
| Two operations must undo each other | — | serialize → parse round-trips; encode → decode; a Zod schema accepts what the mapper emits |
| A simple reference implementation exists | — | the optimized calculator agrees with the naive one (model-based) |
| Two routes must reach the same state | — | apply a discount then tax, or tax then the discount, where the rule says they commute (metamorphic) |
| The unit holds mutable state driven by a sequence of calls | — | a custom cache or queue behaves like a `Map` / array under any call sequence |

Keep the example tests: they document the named boundaries and read as a specification. A property test is added
beside them, never instead of them. A property that restates the implementation (`expect(add(a, b)).toBe(a + b)`
for a function that is `a + b`) proves nothing — the tautology rule applies.

## Packages and version lane

| Runner in the repo | Package | Version |
|---|---|---|
| Any | `fast-check` | **4.10.2** |
| Vitest 4.1+ / 5 | `@fast-check/vitest` | **0.5.0** (peer `vitest ^4.1.0 \|\| ^5.0.0`) |
| Vitest 1–4.0 | `@fast-check/vitest` | **0.3.0** |
| Jest 28+ | `@fast-check/jest` | **2.3.0** |

Verified on npm, 2026-11. `@fast-check/vitest` re-exports `fc` and adds `test.prop` / `it.prop`; it fails by
throwing, so a property runs and reports as an ordinary Vitest test.

## Arbitraries

Compose generators from the built-ins; there are no hand-written shrinkers.

```ts
import { fc } from '@fast-check/vitest';

const amountMinor = fc.integer({ min: 1, max: 100_000_000 });
const parts = fc.integer({ min: 1, max: 50 });
const weights = fc.array(fc.integer({ min: 1, max: 100 }), { minLength: 1, maxLength: 10 });
const sku = fc.stringMatching(/^[A-Z0-9]{3,8}$/);
```

- **Money is integer minor units** (`SKILL.md`, *Money*): generate `fc.integer`, never `fc.float` / `fc.double` for
  an amount.
- Ranges and sizes go in the constraints object (`min`, `max`, `minLength`, `maxLength`); combine with `fc.tuple`,
  `fc.record`, and derive with `.map` / `.chain` when one value depends on another.
- `.filter` discards inputs and slows the run; generate valid values directly instead.
- Domain objects with 4+ fields: generate the varying fields and build them with the test's builder, so the
  arbitrary and the example tests share one construction path:
  `fc.record({ quantity: fc.integer({ min: 1, max: 20 }), sku }).map((fields) => anOrderLine(fields))`.

## A property test

```ts
import { describe, expect } from 'vitest';
import { fc, it } from '@fast-check/vitest';
import { allocate } from './money-allocator';

describe('allocate', () => {
  it.prop([amountMinor, parts])('should preserve the total when an amount is allocated across parts', (amount, count) => {
    const shares = allocate(amount, count);

    expect(shares.reduce((sum, share) => sum + share, 0)).toBe(amount);
  });
});
```

A property runs 100 times by default (`it.prop([...], { numRuns: 500 })` changes it), fails when the body throws or
returns `false`, and shrinks the input before reporting. Assert with `expect`, as in any test — a returned boolean
loses the diff. Async bodies return their promise.

## A failure is replayed from its seed

A failing property reports the shrunk input and the line that replays it:

```
Property failed after 37 tests
{ seed: -1819918769, path: "36:2:1", endOnFailure: true }
Counterexample: [101,3]
Shrunk 4 time(s)
```

- Reproduce locally by passing that object as the property's parameters for one run —
  `it.prop([amountMinor, parts], { seed: -1819918769, path: '36:2:1', endOnFailure: true })` — and run only that test
  (`vitest run -t "should preserve the total"`).
- **Turn the counterexample into an example test** (an `it.each` row) that pins the defect, then fix the code. The
  example stays as the regression; the property keeps exploring.
- **Never commit a `seed`** on a property: it freezes the property onto one input forever. Remove it once the example
  test exists.
- A CI failure's log carries the seed and path; the job needs nothing extra to make it replayable.

## Model-based: the unit against a simple model

When the unit is stateful, run the same random sequence of commands on it and on a model that is obviously right, and
check them against each other after every step:

```ts
type Model = { entries: Map<number, number> };

class SetCommand implements fc.Command<Model, LruCache<number, number>> {
  constructor(readonly key: number, readonly value: number) {}
  check = () => true;
  run(model: Model, cache: LruCache<number, number>): void {
    cache.set(this.key, this.value);
    model.entries.set(this.key, this.value);
    expect(cache.get(this.key)).toBe(this.value);
  }
  toString = () => `set(${this.key}, ${this.value})`;
}

class RemoveCommand implements fc.Command<Model, LruCache<number, number>> {
  constructor(readonly key: number) {}
  check = () => true;
  run(model: Model, cache: LruCache<number, number>): void {
    cache.remove(this.key);
    model.entries.delete(this.key);
    expect(cache.size).toBe(model.entries.size);
  }
  toString = () => `remove(${this.key})`;
}

const commands = fc.commands([
  fc.tuple(fc.integer({ min: 0, max: 50 }), fc.integer()).map(([key, value]) => new SetCommand(key, value)),
  fc.integer({ min: 0, max: 50 }).map((key) => new RemoveCommand(key)),
]);

it.prop([commands])('should behave like a map when any command sequence runs', (sequence) => {
  fc.modelRun(() => ({ model: { entries: new Map() }, real: new LruCache<number, number>(1_000) }), sequence);
});
```

The capacity is above the key range on purpose: the model has no eviction, so the property is "with no eviction
pressure, the cache is a map". Eviction gets its own example tests. A failing sequence shrinks to the shortest list
of commands that breaks the unit, printed through each command's `toString`. Async units use `fc.asyncModelRun`.

## Metamorphic: two routes, one result

When no simple model exists, assert that two different ways of reaching a state agree:

```ts
it.prop([sku, sku])('should reach the same basket when items are added in either order', (first, second) => {
  const left = new BasketBuilder().build().add(first).add(second);
  const right = new BasketBuilder().build().add(second).add(first);

  expect(left.totalMinor).toBe(right.totalMinor);
});
```

## Counting toward the coverage floor

A property test is an asserting test and counts. It rarely reaches a guard-clause branch on its own, because the
arbitraries produce valid input; the invalid-input branches keep their example tests.
