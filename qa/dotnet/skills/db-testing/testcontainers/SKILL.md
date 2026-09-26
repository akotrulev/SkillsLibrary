---
name: qa-db-testing-testcontainers-dotnet
description: Use when scaffolding .NET integration tests backed by a real database (Postgres / SQL Server / Mongo / Redis) via Testcontainers. Triggers "spin up a real Postgres for these tests", "Testcontainers fixture for X", "stop mocking the DB in IntegrationTests". Not for query guardrails (`db-testing/verification-queries`) or connect/seed/clean against an existing DB (`db-testing/connection`).
---

# QA — DB Testing with Testcontainers (.NET)

Scaffolds NUnit fixtures that boot a real database container per fixture (or per assembly), run schema migrations once on startup, and reset row data between tests with Respawn. Optimised for `dotnet test` locally and in Azure Pipelines.

## When to use

- New `IntegrationTests/Fixtures/{Resource}IntegrationTests.cs` fixture that needs a real DB
- Replacing `UseInMemoryDatabase` or hand-rolled SQL mocks with a real engine
- API tests that need to assert DB side-effects (rows written, FKs respected, triggers fired)
- Cross-engine compatibility checks (run the same suite against Postgres 16 and 17)

## When NOT to use

- Pure unit tests with no SQL surface — keep them mock-driven
- Performance/load runs against the DB — use `qa/dotnet/skills/load-testing`
- SQL safety review of assertion queries — use `qa/dotnet/skills/db-testing/verification-queries`
- Non-.NET stacks — use `qa/{java,typescript}/skills/db-testing/testcontainers`

## Inputs needed

Ask at most 2 questions; infer the rest.

1. Which engine? (Postgres / SQL Server / MongoDB / Redis — default Postgres)
2. Schema source: EF Core `DbContext` + migrations, FluentMigrator, raw SQL bootstrap, or Flyway image init?

Infer the rest from project layout: test framework (NUnit per global default), namespace, whether a `WebApplicationFactory` is already in use.

## Decision matrix

| Question | Default | Override when |
|---|---|---|
| Container scope | **Per fixture** (`[OneTimeSetUp]`) | Per-test only if tests cannot share an instance and Respawn cannot clean (e.g. schema mutation tests) |
| Image tag | **Pinned** (`postgres:17.2`, `mcr.microsoft.com/mssql/server:2022-CU14-ubuntu-22.04`) | Never `latest` — pin to the production version |
| Schema lifecycle | **Migrate once** in `[OneTimeSetUp]` | Re-migrate per test only when validating migration rollback |
| Row reset | **Respawn** between tests | Transactional rollback when the SUT can run inside one ambient TX; truncate when Respawn is unavailable (Mongo, Redis) |
| Connection string | **Injected** via `WebApplicationFactory.UseSetting` / `IConfiguration` | Never hardcoded; never echoed into logs |
| Parallelism | NUnit `LevelOfParallelism = 1` at fixture level | Higher parallelism only with one container per fixture *and* Respawn proven idempotent |

## Templates

### Fixture base — `IntegrationTests/Fixtures/PostgresFixture.cs`

NUnit lacks `IAsyncLifetime`, so use `[OneTimeSetUp]` + `[OneTimeTearDown]` with `ValueTask`/`Task`. Inherit fixtures from a common base.

```csharp
using System.Data.Common;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using NUnit.Framework;
using Respawn;
using Testcontainers.PostgreSql;

namespace IntegrationTests.Fixtures;

public abstract class PostgresFixture
{
    private static readonly PostgreSqlContainer Container = new PostgreSqlBuilder()
        .WithImage("postgres:17.2")
        .WithDatabase("appdb")
        .WithUsername("test")
        .WithPassword("test")
        .Build();

    private DbConnection _connection = null!;
    private Respawner _respawner = null!;

    protected string ConnectionString => Container.GetConnectionString();
    protected AppDbContext Db { get; private set; } = null!;

    [OneTimeSetUp]
    public async Task InitContainerAsync()
    {
        await Container.StartAsync();

        DbContextOptions<AppDbContext> options = new DbContextOptionsBuilder<AppDbContext>()
            .UseNpgsql(ConnectionString)
            .Options;

        Db = new AppDbContext(options);
        await Db.Database.MigrateAsync();

        _connection = new NpgsqlConnection(ConnectionString);
        await _connection.OpenAsync();

        _respawner = await Respawner.CreateAsync(_connection, new RespawnerOptions
        {
            DbAdapter = DbAdapter.Postgres,
            SchemasToInclude = ["public"],
            TablesToIgnore = [new Respawn.Graph.Table("__EFMigrationsHistory")],
        });
    }

    [SetUp]
    public async Task ResetRowsAsync()
    {
        await _respawner.ResetAsync(_connection);
    }

    [OneTimeTearDown]
    public async Task TearDownContainerAsync()
    {
        await Db.DisposeAsync();
        await _connection.DisposeAsync();
        await Container.DisposeAsync();
    }
}
```

### Fixture that consumes the SUT via `WebApplicationFactory`

When the test exercises the HTTP surface, inject the container connection string into the SUT through `IConfiguration` — never mutate the service collection by hand.

```csharp
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;

namespace IntegrationTests.Fixtures;

public sealed class ApiFactory : WebApplicationFactory<Program>
{
    public required string ConnectionString { get; init; }

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseSetting("ConnectionStrings:AppDb", ConnectionString);
        builder.UseEnvironment("Test");
    }
}

[TestFixture]
public class TransactionsIntegrationTests : PostgresFixture
{
    private ApiFactory _factory = null!;
    private HttpClient _client = null!;

    [OneTimeSetUp]
    public void CreateFactory()
    {
        _factory = new ApiFactory { ConnectionString = ConnectionString };
        _client = _factory.CreateClient();
    }

    [OneTimeTearDown]
    public void DisposeFactory()
    {
        _client.Dispose();
        _factory.Dispose();
    }

    [Test]
    public async Task PostTransaction_PersistsRow()
    {
        HttpResponseMessage response = await _client.PostAsJsonAsync(
            "/transactions",
            new { Amount = 12.50m, Currency = "EUR" });

        Assert.Multiple(() =>
        {
            Assert.That(response.StatusCode, Is.EqualTo(System.Net.HttpStatusCode.Created));
            Assert.That(Db.Transactions.Count(), Is.EqualTo(1));
        });
    }
}
```

### SQL Server variant

```csharp
private static readonly MsSqlContainer Container = new MsSqlBuilder()
    .WithImage("mcr.microsoft.com/mssql/server:2022-CU14-ubuntu-22.04")
    .WithPassword("Str0ng!Passw0rd")
    .Build();
```

Use `DbAdapter.SqlServer` in `RespawnerOptions` and `SchemasToInclude = ["dbo"]`.

### MongoDB / Redis (no Respawn — clean explicitly)

```csharp
private static readonly MongoDbContainer Mongo = new MongoDbBuilder()
    .WithImage("mongo:7.0")
    .Build();

[SetUp]
public async Task ClearCollectionsAsync()
{
    IMongoDatabase db = new MongoClient(Mongo.GetConnectionString()).GetDatabase("appdb");
    foreach (string name in (await db.ListCollectionNamesAsync()).ToList())
    {
        await db.DropCollectionAsync(name);
    }
}
```

Redis: `await redis.GetServer(...).FlushDatabaseAsync()` in `[SetUp]`.

### Custom wait strategy (only when the built-in module doesn't cover it)

```csharp
new ContainerBuilder()
    .WithImage("ghcr.io/myco/legacy-app:1.4.0")
    .WithPortBinding(8080, true)
    .WithWaitStrategy(Wait.ForUnixContainer()
        .UntilHttpRequestIsSucceeded(req => req.ForPort(8080).ForPath("/health")))
    .Build();
```

**Never** `Task.Delay` to wait for readiness — every Testcontainers module ships a correct wait strategy. Reach for a custom strategy only on a generic container.

## Rules

### Fixture structure
- One fixture base per engine. Concrete `[TestFixture]` classes inherit from it.
- Container is `static readonly` inside the fixture base. One instance per test assembly is acceptable; one per fixture is the default.
- `[OneTimeSetUp]` returns `Task` and is `await`-able. **No `.Result` / `.Wait()`** (global rule).
- Dispose the container in `[OneTimeTearDown]` even on test failure — `DisposeAsync` is idempotent.

### Image pinning
- Use a specific tag tied to the production version. `postgres:17.2`, not `postgres:latest`, not `postgres:17`.
- Record the production version in the fixture file's header comment with the date pinned.
- Bump the tag in a dedicated PR so the diff is reviewable.

### Schema lifecycle
- Migrate once at `[OneTimeSetUp]`. Do not migrate per test.
- Migration source is the same `DbContext` (or `Flyway` / `FluentMigrator`) that runs in production. Never a bespoke "test schema".
- For seed data that every test needs, seed *after* migrations in `[OneTimeSetUp]` and exclude those tables from Respawn via `TablesToIgnore`.

### Row reset
- Default: Respawn in `[SetUp]`. Faster than truncate, respects FK ordering.
- Use transactional rollback only when the entire test (including the SUT) participates in one ambient `TransactionScope`. Most ASP.NET Core stacks do not — Respawn is safer.
- For Mongo/Redis, drop collections / flush DB in `[SetUp]`.

### Connection string handling
- Read it from the container (`Container.GetConnectionString()`) and inject via `WebApplicationFactory.UseSetting("ConnectionStrings:AppDb", ...)`.
- Never echo a connection string into logs, Allure attachments, or test names.
- Never hardcode `"Host=localhost;Port=5432"` — the port is assigned by Docker and varies per run.

### Parallelism
- Default: serial fixtures (`[assembly: LevelOfParallelism(1)]`). Containers are expensive; parallel fixtures stack RAM.
- If you must parallelize: one container *per fixture*, not shared. Verify Respawn isolation by running the suite twice in a row.

### Diagnostics
- On test failure, attach the container's stdout/stderr to Allure: `await Container.GetLogsAsync()` → `AllureLifecycle.Instance.AddAttachment("postgres.log", "text/plain", bytes)`.
- Pair with `qa/reporting/dotnet/skills/test-reports` for the publish step.

### What NOT to do
- No `Task.Delay` / `Thread.Sleep` waiting for the DB. Use the module's built-in wait strategy.
- No `latest` image tags.
- No hardcoded host/port — always derive from `Container.GetConnectionString()`.
- No mixing of in-memory and Testcontainers providers in the same fixture.
- No `Database.EnsureCreated()` — it bypasses migrations and drifts from production schema.
- No connection-string strings in test names or log lines (secrets policy).
- No starting a container in `[SetUp]` — that's per-test container creation; use `[OneTimeSetUp]`.
- No swallowing `OneTimeSetUp` exceptions — let NUnit mark the fixture as errored so CI fails loudly.

## Generation steps

1. Read existing fixtures under `IntegrationTests/Fixtures/` (or equivalent) to match the project's namespace and base-class conventions.
2. Confirm the production schema source (EF Core `DbContext` path, FluentMigrator assembly, or raw SQL folder).
3. Generate:
   - `IntegrationTests/Fixtures/{Engine}Fixture.cs` (base class) — only if a sibling base doesn't already exist.
   - `IntegrationTests/Fixtures/{Resource}IntegrationTests.cs` (concrete fixture) inheriting from the base.
   - `IntegrationTests/IntegrationTests.csproj` updates: add `Testcontainers.PostgreSql` / `.MsSql` / `.MongoDb`, `Respawn`, `Microsoft.AspNetCore.Mvc.Testing` if HTTP surface is exercised.
4. Run `dotnet test IntegrationTests/IntegrationTests.csproj --filter "FullyQualifiedName~{Resource}IntegrationTests"` — expect green or a real assertion failure (not a setup crash). Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
5. Cross-link: in the fixture file's header comment, point to `qa/dotnet/skills/db-testing/verification-queries` for assertion-query rules and `qa/dotnet/skills/test-data-builder` for seed builders.

## Cross-references

- **`qa/dotnet/skills/db-testing/verification-queries`** — SQL guardrails for assertion queries inside these tests.
- **`qa/dotnet/skills/test-data-builder`** — builders for seed data (preferred over inline literals).
- **`qa/cicd/dotnet/skills/ci-pipelines`** — Docker-in-Docker enablement, container caching, and Allure publish for integration test stages.
- **`qa/reporting/dotnet/skills/test-reports`** — attach container logs on failure.
