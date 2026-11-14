# Property-based testing with CsCheck

Read this when a unit's rule holds for **every** input in a domain, not just the handful a `[TestCase]` table
lists: money arithmetic, rounding and allocation, parsers and serializers, a state machine, a collection or cache
the code implements itself. A property test states the rule once, CsCheck generates hundreds of inputs, and a
failure shrinks to the simplest input that still breaks it.

## When a property test earns its place

| Signal | Example test is enough | Add a property test |
|---|---|---|
| The rule names specific values | "an empty cart is rejected" | — |
| The rule holds for a whole range | — | "allocating any amount across any split loses no minor unit" |
| Two operations must undo each other | — | serialize → deserialize round-trips; encode → decode |
| A simple reference implementation exists | — | the optimized calculator agrees with the naive one (model-based) |
| Two routes must reach the same state | — | apply a discount then tax, or tax then the discount, where the rule says they commute (metamorphic) |
| The unit holds mutable state driven by a sequence of calls | — | a custom cache or queue behaves like `Dictionary` / `Queue` under any call sequence |

Keep the example tests: they document the named boundaries and read as a specification. A property test is
added beside them, never instead of them. A property that restates the implementation (`Assert.That(Add(a, b),
Is.EqualTo(a + b))` for a method that is `a + b`) proves nothing — the tautology rule applies.

## Package and version lane

| TFM | Package | Version |
|---|---|---|
| net10 | `CsCheck` | **5.0.1** (targets net10/net11 only) |
| net8 / net9 | `CsCheck` | **4.9.1** (targets net8) |

Verified on nuget.org, 2026-11. CsCheck needs no runner adapter: it fails by throwing, so it runs inside an
ordinary NUnit `[Test]`.

## Generators

Compose a `Gen<T>` from primitives with LINQ; there are no `Arb` classes and no hand-written shrinkers.

```csharp
private static readonly Gen<decimal> Amount = Gen.Decimal[0.01m, 1_000_000m].Select(a => decimal.Round(a, 2));
private static readonly Gen<int> Parts = Gen.Int[1, 50];
private static readonly Gen<List<int>> Weights = Gen.Int[1, 100].List[1, 10];
private static readonly Gen<string> Sku = Gen.String[Gen.Char.AlphaNumeric, 3, 8];
```

- Ranges: `Gen.Int[0, 9]`, `Gen.Decimal[start, finish]`; collections: `gen.Array[min, max]`, `gen.List[min, max]`.
- Combine with `Gen.Select(genA, genB)` (a tuple) or query syntax when one value depends on another.
- `Where` filters discard inputs and slow the run; generate valid values directly instead.
- Domain objects with 4+ fields: generate the varying fields and build them with the test-data builder, so the
  generator and the example tests share one construction path.

## A property test

```csharp
[Test]
public void Should_PreserveTheTotal_When_AnAmountIsAllocatedAcrossParts()
{
    Gen.Select(Amount, Parts).Sample((amount, parts) =>
    {
        var shares = MoneyAllocator.Allocate(amount, parts);

        Assert.That(shares.Sum(), Is.EqualTo(amount));
    });
}
```

`Sample` runs 100 iterations by default (`iter:` or `time:` change it), returns `false` or throws to fail, and
on failure shrinks the input before reporting.

## A failure is replayed from its seed

A failing `Sample` throws with the shrunk input and a line like:

```
Set seed: "0N0XIzNsQ0O2" or -e CsCheck_Seed=0N0XIzNsQ0O2 to reproduce (12 shrinks, 340 skipped, 4,000 total).
```

- Reproduce locally with the environment variable, without editing code:
  `CsCheck_Seed=0N0XIzNsQ0O2 dotnet test --filter "FullyQualifiedName~Should_PreserveTheTotal"`.
- **Turn the shrunk input into an example test** (`[TestCase]` row) that pins the defect, then fix the code. The
  example stays as the regression; the property keeps exploring.
- Never commit a `seed:` argument on a `Sample` call: it freezes the property onto one input forever.
- A CI failure's log carries the seed; the CI job needs nothing extra to make it replayable.

## Model-based: the unit against a simple model

When the unit is stateful, run the same random sequence of operations on it and on a model that is obviously
right, and require them to agree after every step:

```csharp
[Test]
public void Should_BehaveLikeADictionary_When_AnyOperationSequenceRuns()
{
    Gen.Const(() => (new LruCache<int, int>(capacity: 1_000), new Dictionary<int, int>()))
        .SampleModelBased(
            Gen.Select(Gen.Int[0, 50], Gen.Int).Operation<LruCache<int, int>, Dictionary<int, int>>(
                (cache, kv) => cache.Set(kv.Item1, kv.Item2),
                (model, kv) => model[kv.Item1] = kv.Item2),
            Gen.Int[0, 50].Operation<LruCache<int, int>, Dictionary<int, int>>(
                (cache, key) => cache.Remove(key),
                (model, key) => model.Remove(key)),
            equal: (cache, model) => cache.Count == model.Count
                && model.All(kv => cache.TryGet(kv.Key, out var value) && value == kv.Value));
}
```

The capacity is above the key range on purpose: the model has no eviction, so the property is "with no eviction
pressure, the cache is a dictionary". Eviction gets its own example tests.

## Metamorphic: two routes, one result

When no simple model exists, assert that two different ways of reaching a state agree. `SampleMetamorphic` takes
two copies of the same initial value, applies a different function to each, and compares them:

```csharp
[Test]
public void Should_ReachTheSameBasket_When_ItemsAreAddedInEitherOrder()
{
    Gen.Const(() => new BasketBuilder().Build())
        .SampleMetamorphic(
            Gen.Select(Sku, Sku).Metamorphic<Basket>(
                (basket, skus) => { basket.Add(skus.Item1); basket.Add(skus.Item2); },
                (basket, skus) => { basket.Add(skus.Item2); basket.Add(skus.Item1); }),
            equal: (left, right) => left.Total == right.Total && left.Lines.Count == right.Lines.Count);
}
```

## FsCheck, when the repo already has it

FsCheck 3.x (`FsCheck` + `FsCheck.NUnit` **3.6.0**, NUnit 4–5) is the older .NET property library: `Arbitrary`
types, `[Property]` test methods, generators built with `Gen`/`Arb`. Match it where the repo uses it; do not add a
second property library. For a new suite, CsCheck is the default: no `Arb` registration, faster parallel
shrinking, and seed replay from an environment variable.

## Counting toward the coverage floor

A property test is an asserting test and counts. It rarely reaches a guard-clause branch on its own, because the
generators produce valid input; the invalid-input branches keep their example tests.
