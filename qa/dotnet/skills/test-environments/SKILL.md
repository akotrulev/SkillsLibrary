---
name: qa-test-environments-dotnet
description: Use when the user asks to spin up a whole multi-service environment (not just one database) for .NET 8 integration/E2E tests via Testcontainers. Triggers: "spin up the whole stack (api + postgres + redis) for these tests", "Testcontainers multi-container network in NUnit", "boot app + DB + RabbitMQ together and wait for all of them".
---

# QA — Test Environments with Testcontainers (.NET)

Boots a **whole dependency topology** — application-under-test plus its real backing services (DB, cache, queue, object store, mail catcher, third-party stub) — for .NET 8 integration/E2E tests, using the `Testcontainers` NuGet packages. This is the **general environment spin-up** skill: a multi-container network built in code. For a *single* database container with EF migrations and per-test Respawn reset, that is the narrower `qa/dotnet/skills/db-testing/testcontainers` skill — this one owns everything from two containers up.

Testcontainers for .NET has **no docker-compose driver** (unlike the Node/Java bindings), so the idiomatic multi-service path is a hand-built topology: a user-defined `INetwork` shared across several `ContainerBuilder` services, with `WithNetworkAliases` giving each container a DNS name its peers reach it by. Every service is waited on by an **explicit readiness condition**, never a `Task.Delay`. Connection details (hostname + dynamically-mapped port) are read off the started containers and surfaced to tests through an NUnit **fixture base** — tests never hardcode `localhost:5432`.

## Stack

- .NET 8, C# (nullable reference types on)
- `Testcontainers` core (`ContainerBuilder`, `NetworkBuilder`, `Wait`, `WithReuse`) + module packages (`Testcontainers.PostgreSql`, `.Redis`, …) where a module exists
- NUnit (`[OneTimeSetUp]`/`[OneTimeTearDown]` — NUnit has no `IAsyncLifetime`), async all the way
- `Microsoft.AspNetCore.Mvc.Testing` when the app surface is exercised over HTTP
- These suites run on `ubuntu-latest` (Docker pre-installed) under `qa/dotnet/skills/ci-pipelines`

## When to use

- You need **more than one** container per fixture: app + DB + Redis, or DB + RabbitMQ + a third-party stub
- The app-under-test must run *as a container* and reach its dependencies by hostname (inter-container DNS)
- You want fast local re-runs by **reusing** already-running containers, but a clean fresh environment in CI
- You're booting a mail catcher / object store / message broker that has no dedicated db-testing skill

## When NOT to use

- A single DB with EF migrations + per-test Respawn reset → `qa/dotnet/skills/db-testing/testcontainers`
- TypeScript / JVM stacks → `qa/{typescript,java}/skills/test-environments`
- The CI workflow that runs these (Docker enablement, artifact upload) → `qa/dotnet/skills/ci-pipelines`
- In-browser HTTP mocking/interception (no real services) → `qa/dotnet/skills/network-monitoring`
- Pure unit tests with no out-of-process dependency

## Inputs needed

Ask at most 3 questions; infer the rest from the solution.

1. **Topology** — which services make up the environment (app, DB engine, cache, queue, mail, stubs)?
2. **App image** — is the app-under-test exercised as a container image, or in-process via `WebApplicationFactory` against containerized dependencies?
3. **Scope** — one environment per *fixture* (default) or per assembly?

Infer the test framework (NUnit per CLAUDE.md), namespace, and image source from the solution layout.

## Decision matrix

| Decision | Default | Override when |
|---|---|---|
| Orchestration | **Hand-built topology**: shared `INetwork` + several `ContainerBuilder` services | — (.NET Testcontainers has no compose driver; keep dev `docker-compose.yml` separate) |
| App under test | **`WebApplicationFactory` in-process** against containerized deps (fastest, debuggable) | Containerize the app too when testing the real image / container networking |
| Environment scope | **Per fixture** (`[OneTimeSetUp]`) | Per assembly only when boot cost dominates and fixtures can share |
| Inter-container DNS | `WithNetworkAliases("db")` on a shared `INetwork` | — (never hardcode container IPs) |
| Wait strategy | **Per service**: `UntilHttpRequestIsSucceeded` for the app, `UntilPortIsAvailable`/`UntilMessageIsLogged` for deps | Module default when using a typed builder (`PostgreSqlBuilder`) |
| Reuse | **`.WithReuse(true)` locally** (+ `testcontainers.reuse.enable=true`); **fresh per fixture in CI** | Never reuse in CI — a leaked dirty container makes runs non-deterministic |
| Image tags | **Pinned** (`postgres:17.2`, `redis:7.4`) | Never `latest` |
| Connection details | **Read from the started container** (`Hostname` + `GetMappedPublicPort`) and surfaced via the fixture | Never hardcode `localhost:5432` — ports are dynamic |
| Teardown | `DisposeAsync()` on containers + network in `[OneTimeTearDown]` (Ryuk as backstop) | Skip dispose only for a reused local container (leave it running) |

## Patterns

### Multi-service topology over a shared network — `IntegrationTests/Fixtures/StackFixture.cs`

A user-defined `INetwork` gives the containers DNS names to reach each other; the app talks to `db:5432`, the host talks to the app's mapped port. Expose **intent** (`ApiBaseUrl`, `DatabaseConnectionString`), not raw container handles.

```csharp
using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Containers;
using DotNet.Testcontainers.Networks;
using NUnit.Framework;

namespace IntegrationTests.Fixtures;

public abstract class StackFixture
{
    // CI never reuses — a leaked dirty container would make the run non-deterministic.
    private static bool Reuse => Environment.GetEnvironmentVariable("CI") != "true";

    private INetwork _network = null!;
    private IContainer _db = null!;
    private IContainer _redis = null!;
    private IContainer _api = null!;

    protected string ApiBaseUrl { get; private set; } = null!;
    protected string DatabaseConnectionString { get; private set; } = null!;
    protected string RedisConnectionString { get; private set; } = null!;

    [OneTimeSetUp]
    public async Task StartStackAsync()
    {
        _network = new NetworkBuilder().Build();
        await _network.CreateAsync();

        _db = new ContainerBuilder()
            .WithImage("postgres:17.2")
            .WithNetwork(_network)
            .WithNetworkAliases("db")                 // the app reaches it as host "db"
            .WithEnvironment("POSTGRES_DB", "appdb")
            .WithEnvironment("POSTGRES_USER", "test")
            .WithEnvironment("POSTGRES_PASSWORD", "test")
            .WithPortBinding(5432, true)              // dynamic host port
            .WithWaitStrategy(Wait.ForUnixContainer().UntilPortIsAvailable(5432))
            .WithReuse(Reuse)
            .Build();

        _redis = new ContainerBuilder()
            .WithImage("redis:7.4")
            .WithNetwork(_network)
            .WithNetworkAliases("redis")
            .WithPortBinding(6379, true)
            .WithWaitStrategy(Wait.ForUnixContainer().UntilMessageIsLogged("Ready to accept connections"))
            .WithReuse(Reuse)
            .Build();

        _api = new ContainerBuilder()
            .WithImage("myorg/api:test")
            .WithNetwork(_network)
            .WithEnvironment("DATABASE_URL", "postgres://test:test@db:5432/appdb") // alias, not host:port
            .WithEnvironment("REDIS_URL", "redis://redis:6379")
            .WithPortBinding(8080, true)
            .WithWaitStrategy(Wait.ForUnixContainer()
                .UntilHttpRequestIsSucceeded(req => req.ForPort(8080).ForPath("/health")))
            .WithReuse(Reuse)
            .Build();

        await _db.StartAsync();
        await _redis.StartAsync();
        await _api.StartAsync();

        DatabaseConnectionString =
            $"Host={_db.Hostname};Port={_db.GetMappedPublicPort(5432)};Database=appdb;Username=test;Password=test";
        RedisConnectionString = $"{_redis.Hostname}:{_redis.GetMappedPublicPort(6379)}";
        ApiBaseUrl = $"http://{_api.Hostname}:{_api.GetMappedPublicPort(8080)}";
    }

    [OneTimeTearDown]
    public async Task StopStackAsync()
    {
        // In CI, tear the environment down. Locally with reuse on, leave it running for the next run.
        if (Reuse) return;
        await _api.DisposeAsync();
        await _redis.DisposeAsync();
        await _db.DisposeAsync();
        await _network.DeleteAsync();
    }
}
```

### Concrete fixture consuming the booted stack

```csharp
using System.Net;
using System.Net.Http.Json;
using NUnit.Framework;

namespace IntegrationTests.Fixtures;

[TestFixture]
public class CheckoutIntegrationTests : StackFixture
{
    private HttpClient _client = null!;

    [OneTimeSetUp]
    public void CreateClient() => _client = new HttpClient { BaseAddress = new Uri(ApiBaseUrl) };

    [OneTimeTearDown]
    public void DisposeClient() => _client.Dispose();

    [Test]
    public async Task Should_persist_order_and_publish_event_When_checkout_succeeds()
    {
        HttpResponseMessage response = await _client.PostAsJsonAsync("/checkout", new { Sku = "ABC", Qty = 2 });

        Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.Created));
    }
}
```

### In-process app via `WebApplicationFactory` against containerized deps

Often the app need not be containerized — run it in-process and inject the **container** connection strings via `IConfiguration`. Faster to boot, breakpoint-debuggable, and still exercises the real DB/cache. (Inter-container DNS aliases are unnecessary here — the in-process app reaches the deps via their host-mapped ports.)

```csharp
public sealed class ApiFactory : WebApplicationFactory<Program>
{
    public required string DatabaseConnectionString { get; init; }
    public required string RedisConnectionString { get; init; }

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseSetting("ConnectionStrings:AppDb", DatabaseConnectionString);
        builder.UseSetting("ConnectionStrings:Redis", RedisConnectionString);
        builder.UseEnvironment("Test");
    }
}
```

### Container reuse for fast local loops

`WithReuse(true)` keeps a container running between runs; the next run with an identical config hash attaches to it instead of booting fresh. Gate it off in CI (the `Reuse` flag above already does this).

```csharp
_db = new ContainerBuilder()
    .WithImage("postgres:17.2")
    .WithPortBinding(5432, true)
    .WithWaitStrategy(Wait.ForUnixContainer().UntilPortIsAvailable(5432))
    .WithReuse(true)                  // no-op unless reuse is enabled (see below)
    .Build();
```

Reuse only activates when `testcontainers.reuse.enable=true` is set in `~/.testcontainers.properties` (or `TESTCONTAINERS_REUSE_ENABLE=true`). With reuse on, **do not** `DisposeAsync()` — leave the container running for the next run. CI sets neither, so the same code boots fresh and Ryuk reaps it.

### Custom wait strategy for a bespoke service

```csharp
IContainer broker = new ContainerBuilder()
    .WithImage("rabbitmq:3.13-management")
    .WithPortBinding(5672, true)
    .WithWaitStrategy(Wait.ForUnixContainer().UntilMessageIsLogged("Server startup complete"))
    .Build();
```

`UntilHttpRequestIsSucceeded(req => …)`, `UntilPortIsAvailable(port)`, `UntilMessageIsLogged("…")`, `UntilContainerIsHealthy()` (Docker `HEALTHCHECK`). **Never** `Task.Delay` to wait for readiness.

## Rules

### Topology & orchestration
- .NET Testcontainers has **no compose driver** — build the multi-service topology in code with a shared `INetwork` + several `ContainerBuilder`s. Keep any dev `docker-compose.yml` separate.
- Prefer running the app **in-process** (`WebApplicationFactory`) against containerized dependencies; containerize the app only when testing the real image or container networking.
- Boot the environment **once per fixture** in `[OneTimeSetUp]`. Never start the stack in `[SetUp]` (that's per-test).
- Containers talk to each other by **network alias** (`WithNetworkAliases`) — never by hardcoded container IP.

### Wait strategies (no sleeps)
- Every service gets an **explicit readiness condition**. App → `UntilHttpRequestIsSucceeded`; DB/broker → `UntilPortIsAvailable`/`UntilMessageIsLogged`/`UntilContainerIsHealthy`.
- **No `Task.Delay`/`Thread.Sleep`** as a readiness wait, anywhere (global rule).

### Connection details
- Read `Hostname` + `GetMappedPublicPort(internalPort)` off the **started** container; ports are assigned dynamically by Docker.
- Surface them through the fixture base as intent-named properties (`ApiBaseUrl`, `DatabaseConnectionString`); concrete fixtures consume those, never `GetMappedPublicPort` directly.
- **Never** hardcode `Host=localhost;Port=5432` — that's the container-internal port, not the host-mapped one.
- Never echo a credentialed connection string into logs, Allure attachments, or test names (secrets policy).

### Reuse vs fresh
- `.WithReuse(true)` + `testcontainers.reuse.enable=true` for **fast local loops**; with reuse on, do not dispose.
- **CI always boots fresh and tears down** — gate `WithReuse` on `Environment.GetEnvironmentVariable("CI") != "true"`. A reused dirty container makes CI non-deterministic.

### Teardown & the reaper
- `DisposeAsync()` containers (reverse order) + `DeleteAsync()` the network in `[OneTimeTearDown]` (CI). The **Ryuk** reaper is the backstop that kills leaked containers if the process dies — never the primary cleanup.
- `DisposeAsync` is idempotent — call it even on a failed setup.

### Images & scope
- Pin every image (`postgres:17.2`, not `latest`/`17`). Document the prod version in a comment.
- Default `[assembly: LevelOfParallelism(1)]` — containers are heavy; parallel fixtures stack RAM. Parallelize only with one network/topology per fixture and proven isolation.

### Diagnostics
- On failure, attach service logs to Allure: `await container.GetLogsAsync()` → `AllureLifecycle.Instance.AddAttachment(...)`. Pair with `qa/dotnet/skills/allure-reporting`.

### What NOT to do
- No `Task.Delay`/`Thread.Sleep` to wait for a service — use a `Wait.ForUnixContainer().Until…` strategy.
- No `latest`/floating image tags.
- No hardcoded `localhost:<fixed-port>` — read `GetMappedPublicPort()` from the started container.
- No container-to-container traffic via IP — use `WithNetworkAliases`.
- No `WithReuse(true)` left active in CI (gate on `CI`), and no `DisposeAsync` when reuse is on locally.
- No starting the stack in `[SetUp]` — that's a fresh environment per test; use `[OneTimeSetUp]`.
- No EF migrations / per-test Respawn reset in here — that's `qa/dotnet/skills/db-testing/testcontainers`'s job; this skill stops at booting the topology.
- No credentialed connection string in logs or test names (secrets policy).
- No swallowing a `[OneTimeSetUp]` boot exception — let NUnit mark the fixture errored so CI fails loudly.

## Generation steps

1. Read existing fixtures under `IntegrationTests/Fixtures/` (or equivalent) to match namespace and base-class conventions, and find the app image / `Dockerfile`.
2. Confirm the **topology**, whether the app runs **in-process or containerized**, and the **scope** (per-fixture vs per-assembly).
3. Generate:
   - `IntegrationTests/Fixtures/StackFixture.cs` (base) — shared `INetwork` + `ContainerBuilder` services, explicit per-service waits, CI-gated `WithReuse`, intent-named connection properties.
   - A concrete `IntegrationTests/Fixtures/{Feature}IntegrationTests.cs` inheriting it (with `ApiFactory` if in-process).
   - `IntegrationTests.csproj`: add `Testcontainers` (+ `Testcontainers.PostgreSql`/`.Redis` if using typed builders), `Microsoft.AspNetCore.Mvc.Testing` if HTTP surface is exercised.
4. Run `dotnet test --filter "FullyQualifiedName~{Feature}IntegrationTests"` — expect green or a real assertion failure, not a boot/wait crash.
5. Confirm reuse works locally (`testcontainers.reuse.enable=true`, run twice — the second is fast) and that CI (`CI=true`) boots fresh and tears down.

## Cross-references

- **`qa/typescript/skills/test-environments`** (canonical) + **`qa/java/skills/test-environments`** — the sibling stacks; this file ports the canonical TS skill into `Testcontainers`/NUnit idioms.
- **`qa/dotnet/skills/db-testing/testcontainers`** — the narrower skill for a *single* DB container with EF migrations + Respawn reset; this environment skill is what you graduate to when the suite needs the app + DB + other services together. It cross-links back here for multi-container orchestration.
- **`qa/dotnet/skills/db-testing/client`** — the DB client/query wiring that runs against the `DatabaseConnectionString` this fixture surfaces.
- **`qa/dotnet/skills/ci-pipelines`** — runs these suites on `ubuntu-latest` (Docker pre-installed, Ryuk works out of the box); uploads TRX + logs.
- **`qa/dotnet/skills/test-data-builder`** — seeds data into the booted services.
- **`qa/dotnet/skills/allure-reporting`** — attach per-service container logs on failure.
