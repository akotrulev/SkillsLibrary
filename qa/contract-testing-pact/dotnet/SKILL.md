---
name: qa-contract-testing-pact-dotnet
description: Use when the user asks to set up consumer-driven contract testing with Pact in a .NET 8 service (PactNet v5+) — consumer tests with NUnit, provider verification, Pact Broker publish, can-i-deploy, state handlers. Triggers: "set up Pact for our .NET service", "PactNet consumer test for X", "verify our .NET provider against Y's contract", "wire can-i-deploy in our .NET deploy". Do NOT use for Java/JVM consumers or providers (use `qa/contract-testing-pact/java`), TypeScript/Node consumers or providers (use `qa/contract-testing-pact/typescript`), live-service API tests (use `qa/api-test-author/generator/dotnet`), or OpenAPI-only validation. Load `qa/contract-testing-pact/_shared` alongside this skill for the Broker / matchers / can-i-deploy concepts.
---

# QA — Contract Testing with Pact (.NET / PactNet)

Wires Pact V4 into a .NET 8 service via **PactNet v5+** for consumer-driven contract testing with NUnit. Covers the consumer test, provider verification, state handlers, and CI publish. Load `qa/contract-testing-pact/_shared` for the Broker model, matchers reference, and `can-i-deploy` gate that are shared across all stacks.

## When to use

- A .NET 8 service consumes or produces an HTTP API and needs contract coverage.
- Replacing brittle multi-service E2E tests with PactNet verification.
- Catching breaking changes at the .NET producer side before they ship.
- Pairing with `qa/contract-testing-pact/_shared` for Broker / `can-i-deploy` wiring.

## When NOT to use

- Java / JVM consumer or provider → `qa/contract-testing-pact/java`
- TypeScript / Node consumer or provider → `qa/contract-testing-pact/typescript`
- Live-service API tests (no contract) → `qa/api-test-author/generator/dotnet`
- OpenAPI-only validation with no consumer-driven aspect → schema validation library

## Stack

- **Runtime**: .NET 8
- **Test runner**: NUnit 4.x
- **Pact lib**: `PactNet` v5+ (`PactNet.Output.Xunit` not required for NUnit; the core lib is runner-agnostic)
- **Broker CLI**: `pactfoundation/pact-cli:latest` (containerized — language-independent)

Project layout:

```
src/
├── CartService/                       ← consumer
│   └── CartService.csproj
└── OrdersService/                     ← provider
    └── OrdersService.csproj
tests/
├── CartService.ContractTests/         ← consumer tests
│   ├── CartService.ContractTests.csproj
│   ├── OrdersConsumerTests.cs
│   └── pacts/                         ← generated, gitignored
└── OrdersService.ContractTests/       ← provider verification
    ├── OrdersService.ContractTests.csproj
    └── OrdersProviderTests.cs
```

`pacts/` is generated output — `.gitignore` it. The Broker is the source of truth.

## Consumer test (NUnit)

```csharp
using System.Net;
using PactNet;
using PactNet.Matchers;
using NUnit.Framework;

namespace CartService.ContractTests;

[TestFixture]
public class OrdersConsumerTests
{
    private IPactBuilderV4 _pact = null!;

    [OneTimeSetUp]
    public void Setup()
    {
        var pact = Pact.V4("cart-service", "orders-service", new PactConfig
        {
            PactDir = Path.Combine(TestContext.CurrentContext.WorkDirectory, "pacts"),
            LogLevel = PactLogLevel.Information,
        });
        _pact = pact.WithHttpInteractions();
    }

    [Test]
    public async Task GetOrder_Returns_Order()
    {
        _pact
            .UponReceiving("a request for order 123")
            .Given("order 123 exists for customer cus_alice")
            .WithRequest(HttpMethod.Get, "/orders/123")
            .WithHeader("Accept", "application/json")
            .WillRespond()
            .WithStatus(HttpStatusCode.OK)
            .WithHeader("Content-Type", "application/json; charset=utf-8")
            .WithJsonBody(new
            {
                id         = Match.Type("123"),
                customerId = Match.Type("cus_alice"),
                status     = Match.Regex("paid", "pending|paid|cancelled|refunded"),
                totalMinor = Match.Integer(9999),
                currency   = Match.Regex("EUR", "^[A-Z]{3}$"),
            });

        await _pact.VerifyAsync(async ctx =>
        {
            var client = new OrdersClient(ctx.MockServerUri);
            var order = await client.GetOrderAsync("123");
            Assert.That(order.Id, Is.EqualTo("123"));
        });
    }
}
```

- Assert **types** with `Match.Type` / `Match.Integer` / `Match.Regex` — not exact values, except where the contract truly requires a specific value (e.g. status enum).
- `Given(...)` names a provider state — the provider implements a handler for that name.
- `VerifyAsync` boots the in-process mock, runs the callback against `ctx.MockServerUri`, then writes the pact file under `PactDir` on success.

## Provider verification (NUnit)

```csharp
using PactNet.Verifier;
using NUnit.Framework;

namespace OrdersService.ContractTests;

[TestFixture]
public class OrdersProviderTests
{
    private static IHost _host = null!;
    private const int ProviderPort = 5050;

    [OneTimeSetUp]
    public async Task StartProvider()
    {
        _host = Program.CreateHostBuilder(new[] { $"--urls=http://localhost:{ProviderPort}" })
                       .Build();
        await _host.StartAsync();
    }

    [OneTimeTearDown]
    public async Task StopProvider() => await _host.StopAsync();

    [Test]
    public void Verify()
    {
        var brokerUrl    = Environment.GetEnvironmentVariable("PACT_BROKER_BASE_URL")!;
        var brokerToken  = Environment.GetEnvironmentVariable("PACT_BROKER_TOKEN")!;
        var gitSha       = Environment.GetEnvironmentVariable("GIT_SHA")!;
        var branch       = Environment.GetEnvironmentVariable("BRANCH_NAME")!;

        new PactVerifier("orders-service", new PactVerifierConfig())
            .WithHttpEndpoint(new Uri($"http://localhost:{ProviderPort}"))
            .WithPactBrokerSource(new Uri(brokerUrl), opts => opts
                .TokenAuthentication(brokerToken)
                .ConsumerVersionSelectors(
                    new ConsumerVersionSelector { MainBranch = true },
                    new ConsumerVersionSelector { DeployedOrReleased = true })
                .PublishResults(gitSha, new[] { branch }))
            .WithProviderStateUrl(new Uri($"http://localhost:{ProviderPort}/_pact/provider-states"))
            .Verify();
    }
}
```

### State handler endpoint (on the provider service)

PactNet expects a `POST /_pact/provider-states` endpoint that receives `{ state: string, action: 'setup' | 'teardown', params: {...} }`. Wire it in `Program.cs` **only in test/CI profiles**:

```csharp
if (app.Environment.IsEnvironment("Test") || app.Environment.IsEnvironment("CI"))
{
    app.MapPost("/_pact/provider-states", async (ProviderStateRequest req, IOrdersRepository repo) =>
    {
        if (req.Action != "setup") return Results.NoContent();

        switch (req.State)
        {
            case "order 123 exists for customer cus_alice":
                await repo.UpsertAsync(new Order("123", "cus_alice", "paid", 9999, "EUR"));
                break;
            // additional states...
        }
        return Results.NoContent();
    });
}
```

Never expose this endpoint in `Production` environment configuration.

## CI — consumer side

After `dotnet test`, publish the generated pact:

```bash
# consumer pipeline
dotnet test tests/CartService.ContractTests/CartService.ContractTests.csproj \
  --logger "trx;LogFileName=contract.trx"

docker run --rm \
  -v "$PWD/tests/CartService.ContractTests/bin/Debug/net8.0/pacts:/pacts" \
  -e PACT_BROKER_BASE_URL=$PACT_BROKER_BASE_URL \
  -e PACT_BROKER_TOKEN=$PACT_BROKER_TOKEN \
  pactfoundation/pact-cli:latest \
  broker publish /pacts \
  --consumer-app-version "$GIT_SHA" \
  --branch "$BRANCH_NAME"
```

## CI — provider side

```bash
# provider pipeline
PACT_BROKER_BASE_URL=$BROKER \
PACT_BROKER_TOKEN=$TOKEN \
GIT_SHA=$GIT_SHA \
BRANCH_NAME=$BRANCH_NAME \
  dotnet test tests/OrdersService.ContractTests/OrdersService.ContractTests.csproj
```

Verification results are published back to the Broker via `PublishResults(...)` inside the test.

## `can-i-deploy` gate (both pipelines)

See `qa/contract-testing-pact/_shared` for the shared `can-i-deploy` and `record-deployment` commands. Wire them in the deploy stage of **both** the consumer and the provider pipelines, before `kubectl apply` / `az containerapp update`.

## Rules (.NET-specific)

- **Async all the way down.** `VerifyAsync` callbacks must be `async`; no `.Result` / `.Wait()`.
- **Constructor injection** — the consumer's HTTP client takes an `HttpClient` (or base URL) via constructor; the test passes `ctx.MockServerUri`. No statics like `OrdersClient.BaseUrl = ...`.
- **`Pact.V4`** for new contracts; do not author V3 unless interoperating with an older Broker.
- **`PactDir` per project**, placed under the test project's working directory and gitignored. Never commit pact files as the source of truth.
- **State handlers via the `POST /_pact/provider-states` endpoint** — implemented in code, gated to non-Production environments.
- **Pact verification logs** captured in CI as artifacts (verbose at minimum on first failure).
- **Nullable reference types enabled**; no `!`-bang scattered through DTOs.
- **`Match.Type` / `Match.Integer` / `Match.Regex`** for variable values — not `Match.Equality` unless the value is part of the contract (enum, fixed identifier).

## What NOT to do

- No verifying against the consumer's `localhost` test instance — always boot the real provider host on a known port (`5050` in examples) and verify against it.
- No leaking the `/_pact/provider-states` route into production.
- No `Match.Equality` everywhere — over-asserting breaks on harmless field additions.
- No pact files committed and treated as the source of truth.
- No `Thread.Sleep` between `VerifyAsync` and the underlying call — the mock is already running.
- No `PactBuilder` reused across tests with conflicting interactions in the same fixture — keep one interaction per `[Test]`.
- No `ConsumerVersionSelectors` set only to `MainBranch` — always include `DeployedOrReleased` so currently-running consumers are honored.
- No publishing without `--branch` and `--consumer-app-version` — Broker becomes incapable of correctly answering `can-i-deploy`.

## Generation steps

1. Add `PactNet` to `tests/{Service}.ContractTests/{Service}.ContractTests.csproj`.
2. For the consumer: scaffold `{Provider}ConsumerTests.cs` with `[OneTimeSetUp]` building `IPactBuilderV4`; add one interaction; run `dotnet test` and confirm a pact file appears under `pacts/`.
3. For the provider: scaffold `{Service}ProviderTests.cs` that boots `Program.CreateHostBuilder`, calls `PactVerifier.WithPactBrokerSource(...)`, and points at `/_pact/provider-states`.
4. Add the `POST /_pact/provider-states` handler in `Program.cs` under a non-Production environment guard.
5. Wire consumer CI: `dotnet test` → `pact-cli broker publish` with `--branch` and `--consumer-app-version`.
6. Wire provider CI: `dotnet test` with `PACT_BROKER_*` and `GIT_SHA` / `BRANCH_NAME` env vars.
7. Add `can-i-deploy` and `record-deployment` to both deploy pipelines (see `_shared`).
8. Smoke a full cycle: change the contract on the consumer → fail provider verification → fix → success.

## Handoffs

- Cross-stack Broker / `can-i-deploy` / matchers concepts → `qa/contract-testing-pact/_shared`
- Java consumer/provider → `qa/contract-testing-pact/java`
- TypeScript consumer/provider → `qa/contract-testing-pact/typescript`
- Live-service API tests → `qa/api-test-author/generator/dotnet`
- DTOs → `qa/api-dto-writer/dotnet`
- CI pipeline syntax → `qa/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` or `devops/<ci>`
- Allure publishing for contract test results → `qa/allure-reporting/dotnet`

## Changelog

- 2026-05-29: Split from monolithic `qa/contract-testing-pact/SKILL.md` into the .NET-specific sibling. Adds .NET-specific guidance: `PactNet` v5+ APIs, NUnit `[OneTimeSetUp]` lifecycle, in-process provider host on a fixed port, `/_pact/provider-states` route gated to non-Production environments, async-all-the-way enforcement, and gitignored `pacts/` per test project.
