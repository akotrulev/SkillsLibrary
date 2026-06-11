---
name: qa-db-testing-client-dotnet
description: Use when the user asks to connect from .NET 8 tests to a real database (Postgres / SQL Server / SQLite / Mongo) to seed fixtures, run read-only assertion queries, and clean up safely. Triggers: "connect from these tests to Postgres", "assert the row was written in SQL", "seed and clean a SQL fixture without leaks".
---

# QA — DB Testing Client (.NET 8)

Wires .NET 8 NUnit tests to talk to a **real** database — seed fixtures via builders (no inline raw SQL inserts duplicated across tests), run read-only assertion queries, wait for eventual consistency where it matters, and clean state safely. Pairs with `qa/dotnet/skills/db-testing/testcontainers` for the container lifecycle and `qa/dotnet/skills/db-testing/query-author` for SQL safety.

## When to use

- A test must verify a row was written, an FK held, a trigger fired, or a soft-delete column was set.
- Test setup needs to seed reference data (currencies, countries, plan tiers) that production reads.
- Async write flows need a "wait until the projection catches up" helper.
- Test suite leaks data between tests and needs a deterministic cleanup strategy.

## When NOT to use

- Production data-access code → `design-patterns/dotnet/generator` (Repository / EF Core / Dapper patterns).
- Container booting itself → `qa/dotnet/skills/db-testing/testcontainers`.
- SQL guardrails (parameterization, no `SELECT *` in assertions) → `qa/dotnet/skills/db-testing/query-author`.
- Pure unit tests with no SQL surface — keep them mock-driven.
- Java / TypeScript stacks → `qa/{java,typescript}/skills/db-testing/client`.

## Stack

- **Runtime**: .NET 8
- **Test runner**: NUnit 4.x
- **DB clients**:
  - **Dapper** (`Dapper`) — preferred for assertion queries; tiny surface, parameterized by default.
  - **Npgsql** / `Microsoft.Data.SqlClient` — raw `DbCommand` only when Dapper is overkill.
  - **EF Core read-only** (`AsNoTracking().AsQueryable()`) — when an `IQueryable` reads better than SQL for a specific projection assertion.
  - **`MongoDB.Driver`** — Mongo assertions.
- **Cleanup**: **Respawn** (default) for SQL engines; transactional rollback when the SUT fits in one ambient TX; `TRUNCATE … CASCADE` as a fallback.
- **Migration**: EF Core migrations (`Database.MigrateAsync()`) or FluentMigrator — applied once in `[OneTimeSetUp]` via `qa/dotnet/skills/db-testing/testcontainers`.

```
IntegrationTests/
├── Fixtures/
│   ├── PostgresFixture.cs           ← see qa/dotnet/skills/db-testing/testcontainers
│   └── OrdersIntegrationTests.cs
├── DbClients/
│   ├── DbConnectionFactory.cs       ← single connection-string source
│   └── OrdersDbProbe.cs              ← read-only assertion queries
├── Builders/                         ← test data builders — see qa/dotnet/skills/test-data-builder
└── Seeders/
    └── OrdersSeeder.cs               ← writes seeded rows via builders
```

## Connection management

One factory, one source of truth for the connection string. **Never** read the connection string in a test class.

```csharp
public sealed class DbConnectionFactory
{
    private readonly string _connectionString;
    public DbConnectionFactory(string connectionString) => _connectionString = connectionString;

    public async Task<NpgsqlConnection> OpenAsync(CancellationToken ct = default)
    {
        var conn = new NpgsqlConnection(_connectionString);
        await conn.OpenAsync(ct);
        return conn;
    }
}
```

Construct once in `[OneTimeSetUp]` (typically inside `PostgresFixture` from `qa/dotnet/skills/db-testing/testcontainers`) and inject into seeders / probes / SUT.

**Never** new `NpgsqlConnection` (or `SqlConnection`) in a `[Test]` method. Always go through the factory so the connection string lives in one place.

## Seeding fixtures via builders

Test data shape comes from `qa/dotnet/skills/test-data-builder`; the DB seeder takes the built shape and persists it. **Shape building and persistence stay separate** (the builder is pure; the seeder writes).

```csharp
public sealed class OrdersSeeder
{
    private readonly DbConnectionFactory _db;
    public OrdersSeeder(DbConnectionFactory db) => _db = db;

    public async Task<Guid> InsertAsync(Order order, CancellationToken ct = default)
    {
        await using var conn = await _db.OpenAsync(ct);
        await conn.ExecuteAsync(
            """
            INSERT INTO orders (id, customer_id, status, total_minor, currency, placed_at)
            VALUES (@Id, @CustomerId, @Status, @TotalMinor, @Currency, @PlacedAt)
            """,
            new { order.Id, order.CustomerId, order.Status, order.TotalMinor, order.Currency, order.PlacedAt });
        return order.Id;
    }
}
```

```csharp
[Test]
public async Task Cancelling_paid_order_writes_refund_row()
{
    var order = Orders.Paid().WithTotal(15_000).Build();           // builder (qa/dotnet/skills/test-data-builder)
    await _ordersSeeder.InsertAsync(order);                         // persist

    await _sut.CancelAsync(order.Id);                                // SUT does the work

    var refund = await _ordersProbe.GetRefundFor(order.Id);          // assertion query
    Assert.That(refund, Is.Not.Null);
    Assert.That(refund!.AmountMinor, Is.EqualTo(15_000));
}
```

## Read-only assertion queries — DB probes

A **probe** is a small read-only class. One method per assertion the tests need. Each method names the column(s) it reads.

```csharp
public sealed class OrdersDbProbe
{
    private readonly DbConnectionFactory _db;
    public OrdersDbProbe(DbConnectionFactory db) => _db = db;

    public async Task<RefundRow?> GetRefundFor(Guid orderId, CancellationToken ct = default)
    {
        await using var conn = await _db.OpenAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<RefundRow>(
            """
            SELECT id, order_id AS OrderId, amount_minor AS AmountMinor, currency, refunded_at AS RefundedAt
            FROM   refunds
            WHERE  order_id = @orderId
            """,
            new { orderId });
    }

    public sealed record RefundRow(Guid Id, Guid OrderId, long AmountMinor, string Currency, DateTimeOffset RefundedAt);
}
```

Probe rules:
- **Read-only** — probes never write. Writes go through the SUT or a seeder.
- **Project explicit columns** — no `SELECT *`. The probe's record type documents what the test cares about.
- **Parameterized** — every value is a parameter; no string concatenation.
- **One method per assertion** — `GetRefundFor`, `CountActiveOrdersForCustomer`, `HasAuditEventOfType`.

## Waiting for eventual consistency

Async write flows (CDC, outbox → projection, message queue) don't surface the new row instantly. Use a deterministic poll, not `Task.Delay`.

```csharp
public static async Task<T> WaitForAsync<T>(
    Func<CancellationToken, Task<T?>> probe,
    Func<T, bool>                     predicate,
    TimeSpan                          timeout,
    TimeSpan                          interval,
    CancellationToken                 ct = default) where T : class
{
    using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
    cts.CancelAfter(timeout);

    while (!cts.IsCancellationRequested)
    {
        var value = await probe(cts.Token);
        if (value is not null && predicate(value)) return value;
        await Task.Delay(interval, cts.Token);
    }
    throw new TimeoutException($"Probe did not satisfy predicate within {timeout}.");
}

// Usage
var refund = await WaitForAsync(
    ct => _ordersProbe.GetRefundFor(orderId, ct),
    r  => r.AmountMinor == 15_000,
    timeout:  TimeSpan.FromSeconds(5),
    interval: TimeSpan.FromMilliseconds(100));
```

`TimeSpan.FromSeconds(5)` is a sane default for projection lag in a local test environment; bump in CI if needed but **never** use `Task.Delay(5000)` as the assertion.

## Cleanup strategies

| Strategy | When | Notes |
|---|---|---|
| **Respawn** | Default for SQL engines | `await respawner.ResetAsync(_connectionString)` in `[TearDown]`. Keeps schema, deletes data. |
| **Transactional rollback** | SUT runs inside one ambient transaction (e.g. `TransactionScope`) | `[TearDown]` rolls back; fastest. Doesn't work across HTTP boundaries. |
| **`TRUNCATE … CASCADE`** | Respawn unavailable (e.g. specific Mongo / Redis flows) | Targeted, fast, explicit. List tables in dependency order. |
| **Per-test database** | Cross-test mutation is unavoidable (schema migrations, multi-tenant) | Slowest; reserve for the few tests that need it. |

```csharp
private Respawner _respawner = null!;

[OneTimeSetUp]
public async Task InitRespawn()
{
    await using var conn = await _db.OpenAsync();
    _respawner = await Respawner.CreateAsync(conn, new RespawnerOptions
    {
        DbAdapter = DbAdapter.Postgres,
        TablesToIgnore = [ new("__EFMigrationsHistory") ],
        SchemasToInclude = [ "public" ]
    });
}

[TearDown]
public async Task ResetData() => await _respawner.ResetAsync(_connectionString);
```

Respawn keeps the schema; it just deletes rows. Schema migrations stay alive for the whole fixture.

## Mongo / Redis

Mongo: use `IMongoDatabase.DropCollection` per collection in `[TearDown]`. Don't drop the database — schema (indexes) goes with it.

```csharp
[TearDown]
public async Task ResetMongo()
{
    foreach (var name in await _mongo.ListCollectionNames().ToListAsync())
        if (name != "system.indexes") await _mongo.DropCollectionAsync(name);
}
```

Redis: `FLUSHDB` is fine in test mode; never in shared environments.

## Connection-string secrets

- Connection string lives in `DbConnectionFactory`, sourced from the `WebApplicationFactory.UseSetting(...)` override (`qa/dotnet/skills/db-testing/testcontainers`) or `IConfiguration`.
- **Never** log the connection string.
- **Never** check connection strings into `appsettings.Test.json`. Use env vars / per-pipeline secret store.

## Rules

- Single `DbConnectionFactory` per fixture; no `new NpgsqlConnection(...)` in tests.
- Seeders write; probes read; SUT does the business action. Each class has one job.
- Probes are read-only and explicitly project columns (no `SELECT *`).
- Every parameter is bound — no string concatenation into SQL.
- `Task.Delay` is forbidden as an assertion wait — use the polling helper with a predicate.
- `[OneTimeSetUp]` migrates schema + initializes Respawn; `[TearDown]` resets data.
- `[Parallelizable(ParallelScope.None)]` on integration fixtures unless the suite is verified for per-fixture isolation.
- DI-friendly factories, seeders, probes — constructor injection only; never service-locator (`ServiceProvider.GetRequiredService` inside a test).
- Records for probe row types (`public sealed record RefundRow(...)`).
- Async all the way — `OpenAsync`, `QueryAsync`, `ExecuteAsync`; never `.Result` / `.Wait()` / `.GetAwaiter().GetResult()`.

## What NOT to do

- No `Task.Delay(5000)` as the assertion wait — poll a probe with a predicate.
- No `SELECT * FROM orders WHERE id = '…'` with the value inlined — bind a parameter, project the columns you need.
- No raw `INSERT` SQL duplicated across tests — go through a seeder backed by `qa/dotnet/skills/test-data-builder`.
- No `_connection` stored as a long-lived field across tests — open per call (Npgsql pooling handles reuse).
- No `Database.EnsureCreated()` for schema setup — use real migrations so production drift is caught.
- No mutating production-style data without `tenant=test` / `customer=test-XXX` namespacing.
- No reading `ConnectionString` from a global `Configuration.Get<string>(...)` lookup inside a test — go through the factory.
- No probe method that returns the entire entity for a small assertion — return just the projected row record.
- No `RAW("…")` EF queries when Dapper is already in scope — pick one library per concern.
- No connection-string logging — sanitize structured logs.
- No catching `DbException` in tests to assert failure modes — failures should surface as exceptions and fail the test; if you must, assert on the exception's code, not the message text.

## Generation steps

1. Confirm engine (Postgres default), schema-source (EF migrations / FluentMigrator), and which assertion queries each new test needs.
2. Add `DbConnectionFactory` if not present; wire it via DI in the fixture base.
3. For each new test set, scaffold an `<Aggregate>Seeder.cs` (write) and `<Aggregate>DbProbe.cs` (read), reusing builders from `qa/dotnet/skills/test-data-builder`.
4. Add the polling helper if the SUT involves async projections.
5. Pick a cleanup strategy (Respawn default); wire `[OneTimeSetUp]` / `[TearDown]`.
6. Run `dotnet test` — every test passes; no leaks between fixtures.

## Handoffs

- Container lifecycle → `qa/dotnet/skills/db-testing/testcontainers`
- SQL guardrails on assertion queries → `qa/dotnet/skills/db-testing/query-author`
- Test data builders feeding seeders → `qa/dotnet/skills/test-data-builder`
- Java DB testing client → `qa/java/skills/db-testing/client`
- TypeScript DB testing client → `qa/typescript/skills/db-testing/client`
- API tests that own the SUT call → `qa/dotnet/skills/api-test-author/generator`
- Test strategy where DB tests fit → `qa/manual/test-strategy`
- Production data access patterns → `design-patterns/dotnet/generator`
