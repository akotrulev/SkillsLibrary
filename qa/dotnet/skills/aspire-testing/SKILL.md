---
name: aspire-testing
description: Use when a .NET Aspire solution needs NUnit integration tests that start the AppHost via Aspire.Hosting.Testing. Triggers "test the Aspire AppHost". Not for one API host alone (db-testcontainers).
---

# QA — .NET Aspire Integration Testing (Aspire.Hosting.Testing + NUnit)

Scaffolds NUnit fixtures that start a solution's **Aspire AppHost** — every project, container and connection
string it declares — with `DistributedApplicationTestingBuilder`, wait until the resources under test are healthy,
and drive them over HTTP. The test sees the system as it runs: real processes, real containers, real service
discovery.

**The fence.** This is a **process-boundary test**: each resource runs in its own process or container, so a test
cannot substitute a service in DI or reach a class directly. It belongs to the `qa-api-dotnet` lane, never to a
`be-*` unit-test task. A class's logic is unit-tested by the `be-dotnet` `unit-testing` skill; one API host with
its database is a `WebApplicationFactory` + Testcontainers fixture (`db-testing/testcontainers`), which is
lighter and lets the test replace services. Reach for this skill when the behaviour under test spans the
resources the AppHost wires together.

## When to use

- The solution has an AppHost (`*.AppHost.csproj`, `Aspire.AppHost.Sdk`) and the test must exercise two or more
  of its resources together: an API and its worker, an API and the email it sends, a frontend and its backend.
- The AppHost's wiring itself is under test: connection strings, references, environment, health checks.
- Replacing a hand-written docker-compose test harness in an Aspire solution.

## When NOT to use

- One API host plus its database → `db-testing/testcontainers` with `WebApplicationFactory`
- A unit of logic → `be-dotnet` `unit-testing`
- Broker, blob or email assertions without an AppHost → `messaging-testing`, `file-storage-testing`,
  `email-testing`
- Load → `load-testing`; microbenchmarks → `benchmarks`
- A solution without an AppHost — do not add one only to test with it

## Inputs needed

1. The AppHost project and the resources the journey touches (names exactly as the AppHost declares them).
2. What the AppHost reads to vary its shape (`builder.Configuration` flags such as `UseVolumes`), so the test can
   turn off persistent volumes and external dependencies.

## Version lane

| Package | Version | Rule |
|---|---|---|
| `Aspire.Hosting.Testing` | **13.6.5** (net8 / net9 / net10, verified 2026-11) | **Match the AppHost's Aspire version** (its `Aspire.AppHost.Sdk/<version>` or `Aspire.Hosting.AppHost` package); never up-level the AppHost to reach a testing API |
| `CommunityToolkit.Aspire.Hosting.MailPit` | **13.6.1** | Only when the AppHost adds Mailpit (§ Email) |

The test project is a plain `Microsoft.NET.Sdk` NUnit project with a `<ProjectReference>` to the AppHost; the
reference generates the `Projects.<AppHost_Name>` type (dots become underscores). Container resources need Docker
on the machine and the CI agent.

## Procedure

1. Detect the TFM, the Aspire version, NUnit version and the AppHost's resource names; match them.
2. Add the test project with the package and the AppHost reference.
3. Write one `AppHostFixture` base per AppHost from the template below. **One AppHost per fixture, started in
   `[OneTimeSetUp]`, disposed in `[OneTimeTearDown]`** — never one per test: an AppHost start pulls and boots every
   container, which takes tens of seconds.
4. Make each test independent of the others sharing the app: unique data per test (a builder with a unique email or
   key), and reset any shared sink in `[SetUp]` (the Mailpit inbox below).
5. Run `dotnet test`; the first run pulls images, so budget the startup timeout for it.

## Templates

### `AppHostFixture` — `IntegrationTests/Fixtures/AppHostFixture.cs`

```csharp
using Aspire.Hosting;
using Aspire.Hosting.ApplicationModel;
using Aspire.Hosting.Testing;
using IntegrationTests.Email;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using NUnit.Framework;

namespace IntegrationTests.Fixtures;

public abstract class AppHostFixture
{
    private static readonly TimeSpan StartupBudget = TimeSpan.FromMinutes(3);

    private DistributedApplication? _app;

    protected DistributedApplication App => _app ?? throw new InvalidOperationException("The AppHost did not start.");
    protected HttpClient Api { get; private set; } = null!;
    protected MailpitClient Mail { get; private set; } = null!;

    [OneTimeSetUp]
    public async Task StartAppHostAsync()
    {
        using var startup = new CancellationTokenSource(StartupBudget);

        var builder = await DistributedApplicationTestingBuilder.CreateAsync<Projects.Shop_AppHost>(
            ["--environment=Testing", "UseVolumes=false"],
            startup.Token);

        builder.Services.AddLogging(logging => logging
            .SetMinimumLevel(LogLevel.Information)
            .AddFilter("Aspire.", LogLevel.Warning));

        builder.CreateResourceBuilder<ProjectResource>("api")
            .WithEnvironment("Payments__Mode", "Sandbox");

        _app = await builder.BuildAsync(startup.Token);
        await _app.StartAsync(startup.Token);

        await _app.ResourceNotifications.WaitForResourceHealthyAsync(
            "api", WaitBehavior.StopOnResourceUnavailable, startup.Token);
        await _app.ResourceNotifications.WaitForResourceHealthyAsync(
            "mailpit", WaitBehavior.StopOnResourceUnavailable, startup.Token);

        Api = _app.CreateHttpClient("api");
        Mail = new MailpitClient(_app.GetEndpoint("mailpit", "http"));
    }

    [SetUp]
    public async Task ClearInboxAsync()
    {
        await Mail.DeleteAllAsync();
    }

    [OneTimeTearDown]
    public async Task StopAppHostAsync()
    {
        if (_app is not null)
        {
            await _app.DisposeAsync();
        }
    }
}
```

- **Wait for healthy, not for running.** `WaitForResourceHealthyAsync` completes when the resource's health checks
  pass (a resource with none counts as healthy once it is running), so give the API a health check in the AppHost
  (`.WithHttpHealthCheck("/health")`). `WaitBehavior.StopOnResourceUnavailable` fails fast when a resource fails to
  start instead of waiting out the budget.
- **One cancellation budget for startup**; the first run on a clean agent pulls images, so 3 minutes, not 30 s.
- **No retry handler on the test's `HttpClient`.** A standard resilience handler turns a real 5xx into a pass on the
  second try; the health wait already removes the startup race.
- **Ports stay randomized** (the default) so fixtures and parallel CI jobs do not collide; never pass
  `DcpPublisher:RandomizePorts=false` unless a resource genuinely needs a fixed port.
- `App.GetConnectionStringAsync("db")` gives the test the same connection string the API received, for seeding or
  verifying rows with `db-testing/verification-queries`.

### Overriding the AppHost for tests

| Need | How |
|---|---|
| Switch a behaviour the AppHost reads from configuration | Pass it as an argument: `"UseVolumes=false"`, `"--environment=Testing"` |
| Change one resource's environment | `builder.CreateResourceBuilder<ProjectResource>("api").WithEnvironment("Key__Sub", "value")` before `BuildAsync` |
| Assert on how the model is wired (references, mounts) | Inspect `builder.Resources` before `BuildAsync` |
| Replace an external dependency (a payment provider) | Make the AppHost choose it from a configuration flag and pass the flag; never edit the AppHost per test |

A test cannot replace a service inside a running project: the project is a separate process. Behaviour that
needs a fake belongs in the AppHost's configuration or in a `WebApplicationFactory` test.

### A test

```csharp
using System.Net;
using System.Net.Http.Json;
using IntegrationTests.Fixtures;
using NUnit.Framework;

namespace IntegrationTests.Orders;

public sealed class PlaceOrderTests : AppHostFixture
{
    [Test]
    public async Task Should_ReturnCreated_When_AValidOrderIsPosted()
    {
        var request = new PlaceOrderRequestBuilder().Build();

        var response = await Api.PostAsJsonAsync("/orders", request);

        Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.Created), await response.Content.ReadAsStringAsync());
    }
}
```

## Email — Mailpit as an Aspire resource

When the AppHost sends mail, model the sink in the AppHost instead of starting a second container from the test:

```csharp
var mailpit = builder.AddMailPit("mailpit");

builder.AddProject<Projects.Shop_Api>("api")
    .WithReference(mailpit)
    .WaitFor(mailpit);
```

`AddMailPit` exposes an `smtp` endpoint (the connection string the API receives) and an `http` endpoint (the
Mailpit API and UI). The fixture builds the `MailpitClient` from `email-testing/references/mailpit.md` on
`App.GetEndpoint("mailpit", "http")`, clears it in `[SetUp]`, and the test waits for the message with
`Mail.WaitForAsync(recipient, subject)`:

```csharp
[Test]
public async Task Should_SendTheConfirmation_When_AnOrderIsPlaced()
{
    var request = new PlaceOrderRequestBuilder().WithEmail($"buyer-{Guid.NewGuid():N}@test.local").Build();

    var response = await Api.PostAsJsonAsync("/orders", request);
    Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.Created), await response.Content.ReadAsStringAsync());

    var confirmation = await Mail.WaitForAsync(request.Email, "Order confirmation");

    Assert.That(confirmation.To, Has.Exactly(1).Matches<MailpitAddress>(a => a.Address == request.Email));
}
```

The shared email rules apply: a unique recipient per test, a condition-wait, never a sleep. Snapshotting the
rendered email is `email-testing/references/html-snapshots.md`.

## Rules

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `api.md`,
`automation.md` and `test-data.md`. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in
`qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this
skill's recipes disagree, the rule files win.

## Output format

```
Created: IntegrationTests/Fixtures/AppHostFixture.cs   Purpose: one AppHost per fixture, healthy before tests
Created: IntegrationTests/<Area>/<Feature>Tests.cs     Purpose: Should_X_When_Y tests over the resources
```

Then: the resources the fixture waits for, the configuration it overrides, and the `dotnet test` result.

## Anti-examples

- **`DistributedApplicationTestingBuilder` in `[SetUp]`** — a full AppHost start per test; the suite takes minutes
  per class. Start it in `[OneTimeSetUp]`.
- **`await Task.Delay(...)` until the API answers** — wait with `WaitForResourceHealthyAsync`.
- **Asserting a unit's branches through the AppHost** — slow and imprecise; that is the `be-dotnet` unit test.
- **A resilience handler on the test client** — it hides the first failure the test exists to see.

## Handoffs

- Database seeding and row verification → `db-testing/verification-queries`
- Mailpit client and email assertions → `email-testing`
- The CI job (Docker on the agent, image pulls) → `qa/cicd/dotnet/skills/ci-pipelines`
- Unit tests of the logic inside a resource → `be-dotnet` `unit-testing`
