---
name: test-data-builder
description: Use when creating test data builders/ObjectMothers in a .NET test project to replace duplicated literals. Triggers "create a builder for User". Not for row data files (data-driven-testing).
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

```csharp
public sealed class Pseudonymizer(byte[] key)
{
    public string Email(string real) => $"user.{Token(real, "email")}@example.com";
    public string Phone(string real) => $"+44 7700 900{Number(real, "phone", 1000):D3}";
    public string FullName(string real) => Seeded(real, "name").Name.FullName();
    public string StreetAddress(string real) => Seeded(real, "address").Address.StreetAddress();
    public string CustomerId(string real) => $"cus_{Token(real, "customer")}";

    private Faker Seeded(string real, string fieldClass) =>
        new() { Random = new Randomizer(Number(real, fieldClass, int.MaxValue)) };

    private string Token(string real, string fieldClass) =>
        Convert.ToHexString(Hash(real, fieldClass), 0, 6).ToLowerInvariant();

    private int Number(string real, string fieldClass, int bound) =>
        (int)(BitConverter.ToUInt32(Hash(real, fieldClass)) % (uint)bound);

    private byte[] Hash(string real, string fieldClass) =>
        HMACSHA256.HashData(key, Encoding.UTF8.GetBytes($"{fieldClass}:{real}"));
}
```

Mask every column that identifies a person on its own or combined (postcode + date of birth + gender); amounts,
enums and timestamps that carry no identity stay as they are. Before the set is used, grep it for the source's
email domains and phone prefixes — a hit fails the masking job.

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

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `test-data.md` (and `automation.md` for the tests that use the builders). Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this skill's recipes disagree, the rule files win.

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
