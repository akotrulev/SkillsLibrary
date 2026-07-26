---
name: qa-test-data-builder-dotnet
description: Use when creating test data builders or ObjectMothers in a .NET 10 (8-9) test project to replace duplicated inline literals across tests with named, intention-revealing factories. Triggers "create a builder for User in C#", "set up test data for X in .NET", "extract this fixture into an OrderBuilder". Not for driving one test from an external data file (`data-driven-testing`).
---

# QA — Test Data Builder / ObjectMother (.NET 8)

Eliminates repeated inline test data literals in .NET 8 test projects (NUnit primary) by generating fluent builders and ObjectMother factories. Required by `CLAUDE.md`: "Builder pattern for test data objects with 4+ fields" and "Test data via builders or ObjectMother, not inline literals duplicated across tests."

## When to use

- Two or more tests construct the "same" object with slightly different fields → extract a builder
- One test sets 6 fields just to test one behavior → extract a builder that defaults the other 5
- A complex aggregate (Order → Lines → Customer → Address) needs assembling for many tests
- Reading a test is hard because half the body is data setup
- API tests need a known-shape DTO with one varying field per scenario

## When NOT to use

- Java test data → `qa/java/skills/test-data-builder`
- TypeScript test data → `qa/typescript/skills/test-data-builder`
- Production-code builders → the `backend/dotnet` dev stack's generator, if installed
- Test data for performance scenarios (volume) → `qa/dotnet/skills/load-testing`
- One-off fixture used by a single test → inline is fine; only extract on duplication

## Builder vs ObjectMother

| Pattern | When to choose |
|---|---|
| **Builder** (`OrderBuilder`) | Many fields, many variations, fluent assembly reads naturally |
| **ObjectMother** (`Orders.Paid()`) | A few **named, canonical** instances with no per-test variation |
| **Both together** | Mother returns a pre-configured builder; tests refine via `With…`/`For…` then call `Build()` |

If you would write `new OrderBuilder().Build()` with no chained methods in 90% of cases → ObjectMother is what you actually want.

## Layout

```
tests/OrdersApp.Tests/
├── Builders/
│   ├── OrderBuilder.cs
│   ├── CustomerBuilder.cs
│   └── OrderLineBuilder.cs
└── Mothers/
    ├── Orders.cs
    └── Customers.cs
```

`Builders/` and `Mothers/` live in the test project (same namespace family as the tests), never in the production project.

## Fluent builder template

```csharp
namespace OrdersApp.Tests.Builders;

public sealed class OrderBuilder
{
    private CustomerId        _customer   = TestCustomers.AlicesId;
    private string            _status     = "Pending";
    private long              _totalMinor = 9999;
    private string            _currency   = "EUR";
    private DateTimeOffset    _placedAt   = new(2026, 1, 1, 12, 0, 0, TimeSpan.Zero);
    private readonly List<OrderLine> _lines = [
        new(Sku: "A", Quantity: 1, PriceMinor: 9999)
    ];

    public OrderBuilder ForCustomer(CustomerId id)        { _customer = id; return this; }
    public OrderBuilder WithStatus(string s)              { _status = s; return this; }
    public OrderBuilder WithTotal(long minor, string ccy = "EUR")
        { _totalMinor = minor; _currency = ccy; return this; }
    public OrderBuilder PlacedAt(DateTimeOffset at)       { _placedAt = at; return this; }
    public OrderBuilder WithLine(OrderLine l)             { _lines.Add(l); return this; }
    public OrderBuilder WithLines(IEnumerable<OrderLine> lines)
        { _lines.Clear(); _lines.AddRange(lines); return this; }

    public Order Build() => new(
        Id:         OrderId.New(),
        CustomerId: _customer,
        Status:     _status,
        TotalMinor: _totalMinor,
        Currency:   _currency,
        PlacedAt:   _placedAt,
        Lines:      _lines.ToArray());
}
```

## ObjectMother on top

```csharp
namespace OrdersApp.Tests.Mothers;

public static class Orders
{
    public static OrderBuilder Pending()   => new OrderBuilder().WithStatus("Pending");
    public static OrderBuilder Paid()      => new OrderBuilder().WithStatus("Paid");
    public static Order        Refunded() => new OrderBuilder().WithStatus("Refunded").Build();
}
```

## Usage in NUnit

```csharp
[Test]
public void Cancelling_pending_order_succeeds()
{
    var order = Orders.Pending().Build();
    // arrange / act / assert
}

[Test]
public void Cancelling_paid_order_refunds_to_card()
{
    var order = Orders.Paid().WithTotal(15_000).Build();
    // ...
}
```

## Conventions

- **Sensible default for every field** — a test doesn't have to know about fields it doesn't care about.
- **Method names** read like prose: `With<Field>` / `For<Aggregate>` / `<Verb>At` / `Adding<Child>`.
- **`Build()` is the only terminal method** and returns the real domain type, not the builder.
- **Records** for produced domain types; the builder mutates its own private state and produces an immutable record.
- **Sealed builders** — nothing inherits a builder.
- **Test project namespaces** (`OrdersApp.Tests.Builders`) — builders never leak to production assemblies.
- **`InternalsVisibleTo`** is fine if the builder needs to touch internal constructors of the domain — but only the test assembly.

## Random vs deterministic data

- **Default to deterministic literal defaults** (`"cus_alice"`, `new DateTimeOffset(2026, 1, 1, ...)`) — tests that fail on a random Tuesday are a nightmare.
- Use `Bogus.Faker` **only** for fields where uniqueness matters per test (ids), or where any value is acceptable and the test does not assert on it.
- Seed Bogus deterministically per test run (`Randomizer.Seed = new Random(42)`) when randomness touches assertions.
- **Never** assert on a random field — assert on the field you set; defaults are scaffolding.

## Aggregate / child relationships

```csharp
var customer = Customers.Alice().Build();
var order = Orders.Paid()
    .ForCustomer(customer.Id)
    .WithLine(new OrderLine(Sku: "B", Quantity: 2, PriceMinor: 5000))
    .Build();
```

- Expose `WithLine` (append) and `WithLines(IEnumerable<OrderLine>)` (replace).
- Don't expose internal mutable collections via getters — `Build()` snapshots them via `.ToArray()`.

## Persistence-aware builders

Separate **shape building** from **persistence**:

```csharp
// Shape only — pure.
var order = Orders.Pending().Build();

// Persistence — through the same client production uses.
var created = await ordersClient.CreateAsync(order);
```

Don't build "an order in the DB" inside the builder — that couples the builder to a particular persistence path and hides the API call dependency. Persistence is the test's job; the builder is shape.

## Rules

- Builders live under `tests/<project>/Builders/`; ObjectMothers under `tests/<project>/Mothers/`.
- Every field has a sensible default — adding a non-nullable field doesn't ripple through 50 tests.
- Field setters are `With<X>` / `For<X>` / `<Verb>At`.
- One builder per aggregate; child aggregates have their own builders.
- Defaults are deterministic literals; only id-like fields use random with reason (seeded Bogus).
- `Build()` returns the real domain type, never the builder itself.
- `Build()` is idempotent — calling it twice produces equal but independent instances.
- ObjectMother helpers return a builder (so tests can refine); return a fully built object only when no test ever varies it.
- Tests never construct domain objects with raw `new`/`{ ... }` across more than 1–2 places — extract to a builder.
- Constructor injection only — builders never use a service locator.
- Async never appears in the builder (no `BuildAsync`); building is pure.

## What NOT to do

- No inline test data literals duplicated across test files.
- No `null` for required fields in defaults — pick a real default.
- No randomness on fields the test asserts against.
- No "god builder" with 30 chained methods covering 4 unrelated aggregates — split per aggregate.
- No persistence in the builder — shape and save are separate concerns.
- No production-code builders disguised as test builders ("we'll reuse this in prod too") — separate them.
- No exposing mutable collections through getters — snapshot in `Build()`.
- No defaults that violate domain invariants (e.g. negative `TotalMinor`) — the default builder must produce a valid object.
- No `Build()` that mutates state outside the builder (no DB writes, no logging).
- No `Build()` whose return type is `dynamic` or `object` — return the real type.
- No `IFixture` / AutoFixture stacked on top of these builders — pick one; mixing breaks predictability.

## Generation steps

1. Grep the test tree for repeated literal patterns (`new Order(`, `new User(`, anonymous object literals in request bodies).
2. Per aggregate, list the fields, the sensible defaults, and the variant-producing helpers (`Pending`/`Paid`/`Cancelled` etc.).
3. Generate the builder under `tests/<project>/Builders/` following the template.
4. Add an ObjectMother under `tests/<project>/Mothers/` with the canonical variants.
5. Replace inline literals in 2–3 representative tests so the pattern is set; leave the rest as a follow-up sweep.
6. Run `dotnet test` — every test still passes with the new defaults.

## Handoffs

- Java test data → `qa/java/skills/test-data-builder`
- TypeScript test data → `qa/typescript/skills/test-data-builder`
- API tests where these feed into request bodies → `qa/dotnet/skills/api-test-author/writer`
- UI tests where they back form-fill helpers → `qa/dotnet/skills/ui-test-author/playwright` / `qa/dotnet/skills/ui-test-author/selenium` / `qa/dotnet/skills/ui-test-author/appium`
- Test reviewers (verify builders used, not literals) → `qa/dotnet/skills/api-test-author/review` / `qa/dotnet/skills/ui-test-author/review`
- Test strategy / pyramid → `qa/manual/test-strategy`
- Production-code builders → the `backend/dotnet` dev stack's generator, if installed
