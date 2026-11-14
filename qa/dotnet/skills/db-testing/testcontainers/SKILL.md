---
name: db-testcontainers
description: Use when scaffolding .NET integration tests on a real database via Testcontainers. Triggers "spin up Postgres for these tests". Not for an existing DB (db-connection).
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
    private static readonly PostgreSqlContainer Container = new PostgreSqlBuilder("postgres:17.2")
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

Testcontainers 4.10+ takes the image in the builder's constructor; the parameterless constructor (and `.WithImage` after it) is `[Obsolete]`. Pin `Testcontainers.*` packages to one 4.x version (4.16.0 verified 2026-11).

### Assembly setup — `IntegrationTests/TestAssemblySetup.cs`

Every in-process host (`WebApplicationFactory`, `Host.CreateApplicationBuilder`) watches `appsettings*.json` for changes by default, and each watcher costs an inotify instance; on Linux CI agents a suite that starts dozens of hosts exhausts the per-user limit and fails with `The configured user limit (128) on the number of inotify instances has been reached`. Turn reload off once, before any host starts:

```csharp
using System.Runtime.CompilerServices;

namespace IntegrationTests;

internal static class TestAssemblySetup
{
    [ModuleInitializer]
    internal static void DisableConfigReload()
    {
        Environment.SetEnvironmentVariable("DOTNET_HOSTBUILDER__RELOADCONFIGONCHANGE", "false");
    }
}
```

The host reads `hostBuilder:reloadConfigOnChange` from its `DOTNET_`-prefixed environment, so this one variable covers every host the assembly creates; tests never edit config files at run time, so nothing is lost.

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
private static readonly MsSqlContainer Container = new MsSqlBuilder("mcr.microsoft.com/mssql/server:2022-CU14-ubuntu-22.04")
    .WithPassword("Str0ng!Passw0rd")
    .Build();
```

Use `DbAdapter.SqlServer` in `RespawnerOptions` and `SchemasToInclude = ["dbo"]`.

### MongoDB / Redis (no Respawn — clean explicitly)

```csharp
private static readonly MongoDbContainer Mongo = new MongoDbBuilder("mongo:7.0")
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
new ContainerBuilder("ghcr.io/myco/legacy-app:1.4.0")
    .WithPortBinding(8080, true)
    .WithWaitStrategy(Wait.ForUnixContainer()
        .UntilHttpRequestIsSucceeded(req => req.ForPort(8080).ForPath("/health")))
    .Build();
```

**Never** `Task.Delay` to wait for readiness — every Testcontainers module ships a correct wait strategy. Reach for a custom strategy only on a generic container.

## Rules

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `db-verification.md` and `automation.md`. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Conventions

- One fixture base per engine; concrete `[TestFixture]` classes inherit it. The container is `static readonly` in the base; one per fixture by default, one per assembly is acceptable. `DisposeAsync` in `[OneTimeTearDown]` is idempotent.
- Record the production version the tag is pinned to, with the date, and bump the tag in a dedicated PR.
- Migrate once in `[OneTimeSetUp]` with the same `DbContext` / Flyway / FluentMigrator that production runs; seed data every test needs after the migrations and exclude those tables from Respawn (`TablesToIgnore`).
- Respawn by default; transactional rollback only when the whole test, SUT included, runs in one ambient `TransactionScope`. Mongo / Redis: drop collections or flush in `[SetUp]`.
- The connection string is read from `Container.GetConnectionString()` and injected with `WebApplicationFactory.UseSetting("ConnectionStrings:AppDb", ...)`.
- Default to serial fixtures (`[assembly: LevelOfParallelism(1)]`); to parallelize, one container per fixture, and prove Respawn isolation by running the suite twice in a row.
- On failure attach `await Container.GetLogsAsync()` to Allure (`postgres.log`); the publish step is `qa/reporting/dotnet/skills/test-reports`.
- Wait for the database with the module's built-in wait strategy; never mix in-memory and Testcontainers providers in one fixture.

## Generation steps

1. Read existing fixtures under `IntegrationTests/Fixtures/` (or equivalent) to match the project's namespace and base-class conventions.
2. Confirm the production schema source (EF Core `DbContext` path, FluentMigrator assembly, or raw SQL folder).
3. Generate:
   - `IntegrationTests/Fixtures/{Engine}Fixture.cs` (base class) — only if a sibling base doesn't already exist.
   - `IntegrationTests/Fixtures/{Resource}IntegrationTests.cs` (concrete fixture) inheriting from the base.
   - `IntegrationTests/IntegrationTests.csproj` updates: add `Testcontainers.PostgreSql` / `.MsSql` / `.MongoDb`, `Respawn`, `Microsoft.AspNetCore.Mvc.Testing` if HTTP surface is exercised.
4. Run `dotnet test IntegrationTests/IntegrationTests.csproj --filter "FullyQualifiedName~{Resource}IntegrationTests"` — expect green or a real assertion failure (not a setup crash).
5. Cross-link: in the fixture file's header comment, point to `qa/dotnet/skills/db-testing/verification-queries` for assertion-query rules and `qa/dotnet/skills/test-data-builder` for seed builders.

## Cross-references

- **`qa/dotnet/skills/db-testing/verification-queries`** — SQL guardrails for assertion queries inside these tests.
- **`qa/dotnet/skills/test-data-builder`** — builders for seed data (preferred over inline literals).
- **`qa/cicd/dotnet/skills/ci-pipelines`** — Docker-in-Docker enablement, container caching, and Allure publish for integration test stages.
- **`qa/reporting/dotnet/skills/test-reports`** — attach container logs on failure.
