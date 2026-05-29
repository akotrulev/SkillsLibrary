---
name: qa-performance-nbomber-dotnet
description: Use when the user asks to design or author NBomber performance / load tests in .NET 8 (C#) — scenarios, load simulations (RampingInject / Inject / RampingConstant / KeepConstant), step types, HTTP plugin, thresholds via `WithLoadSimulations` + assertions, seeded fixtures, env-driven config, HTML/CSV reports, CI integration. Triggers: "write an NBomber scenario for X", "NBomber load test for our .NET API", "ramp profile for spike in NBomber", "publish NBomber report from CI". Do NOT use for k6 tests (use `qa/performance/k6/typescript`), Gatling tests (use `qa/performance/gatling/java`), functional tests, or microbenchmarks (use BenchmarkDotNet). Load `qa/performance/_shared` alongside this skill for workload models, environment policy, and the reporting template.
---

# QA — Performance Testing with NBomber (.NET 8)

Authors NBomber 5.x scenarios in C# against deployed services. NBomber is the right tool when the team strongly prefers writing perf tests in C# (shared DTOs / clients with the production code) and wants full .NET DSL access. For all other cases default to k6 (`qa/performance/k6/typescript`).

## When to use

- .NET-resident teams that want to share DTOs / API clients with the production project.
- Perf tests that need rich step types (HTTP + SQL + message broker in one scenario).
- Teams already familiar with C# and NUnit / xUnit who would rather not learn k6's JS API.

## When NOT to use

- New perf work without a strong C# preference → `qa/performance/k6/typescript`
- JVM-native author experience → `qa/performance/gatling/java`
- Functional behavior tests → `qa/api-test-author/generator/dotnet`
- Microbenchmarks (loop bodies, parsing speed) → BenchmarkDotNet
- Defining the SLO itself → `qa/_shared/quality-metrics`

Load `qa/performance/_shared` for workload models, open-loop vs closed-loop guidance, environment policy, and the reporting template.

## Stack

- **Runtime**: .NET 8
- **Package**: `NBomber` 5.x, `NBomber.Http` for HTTP, `NBomber.Sinks.InfluxDB` / `NBomber.Sinks.Loki` for streaming metrics (optional)
- **Test host**: a standalone console app (`PerfTests/PerfTests.csproj`) — **not** an NUnit / xUnit fixture, NBomber is its own runner.

```
PerfTests/
├── PerfTests.csproj            ← <OutputType>Exe</OutputType>
├── Program.cs                  ← entry point — picks scenario from args
├── Env.cs                      ← BASE_URL / TOKEN resolution
├── Fixtures.cs                 ← seed / cleanup helpers
└── Scenarios/
    ├── OrdersSmoke.cs
    ├── OrdersAverage.cs
    ├── OrdersSpike.cs
    └── OrdersSoak.cs
```

## Average-load scenario

```csharp
// PerfTests/Scenarios/OrdersAverage.cs
using NBomber.Contracts;
using NBomber.CSharp;
using NBomber.Http.CSharp;

namespace PerfTests.Scenarios;

public static class OrdersAverage
{
    public static ScenarioProps Build()
    {
        var http = HttpClientFactory.Create();

        return Scenario.Create("orders_average", async ctx =>
        {
            var id  = $"o-{Random.Shared.Next(1, 6):D3}";
            var req = Http.CreateRequest("GET", $"{Env.BaseUrl}/orders/{id}")
                          .WithHeader("Authorization", $"Bearer {Env.Token}");

            var response = await Http.Send(http, req);

            return response.IsError
                ? Response.Fail(statusCode: response.StatusCode.ToString())
                : Response.Ok(statusCode: response.StatusCode.ToString());
        })
        .WithLoadSimulations(
            Simulation.RampingInject(rate: 50, interval: TimeSpan.FromSeconds(1), during: TimeSpan.FromMinutes(1)),
            Simulation.Inject       (rate: 50, interval: TimeSpan.FromSeconds(1), during: TimeSpan.FromMinutes(5)));
    }
}
```

`Simulation.Inject` / `RampingInject` are the **open-loop** simulations — the right default for "we want N RPS". `KeepConstant` / `RampingConstant` are closed-loop (concurrency-targeted).

## Entry point — pick scenario by argument

```csharp
// PerfTests/Program.cs
using NBomber.CSharp;
using PerfTests.Scenarios;

var which = args.Length > 0 ? args[0] : "average";

ScenarioProps scenario = which switch
{
    "smoke"   => OrdersSmoke.Build(),
    "average" => OrdersAverage.Build(),
    "spike"   => OrdersSpike.Build(),
    "soak"    => OrdersSoak.Build(),
    _         => throw new ArgumentException($"unknown scenario: {which}")
};

NBomberRunner
    .RegisterScenarios(scenario)
    .WithReportFolder("perf-reports")
    .WithReportFormats(ReportFormat.Html, ReportFormat.Csv, ReportFormat.Md)
    .WithReportingInterval(TimeSpan.FromSeconds(15))
    .WithTestSuite("orders")
    .WithTestName(which)
    .Run();
```

Run: `dotnet run --project PerfTests -- average`.

## Smoke (1-minute PR gate)

```csharp
return Scenario.Create("orders_smoke", /* ... */)
    .WithLoadSimulations(
        Simulation.Inject(rate: 5, interval: TimeSpan.FromSeconds(1), during: TimeSpan.FromMinutes(1)));
```

## Spike

```csharp
.WithLoadSimulations(
    Simulation.Inject       (rate: 10,  interval: TimeSpan.FromSeconds(1), during: TimeSpan.FromMinutes(1)),
    Simulation.RampingInject(rate: 500, interval: TimeSpan.FromSeconds(1), during: TimeSpan.FromSeconds(10)),
    Simulation.Inject       (rate: 500, interval: TimeSpan.FromSeconds(1), during: TimeSpan.FromMinutes(1)),
    Simulation.RampingInject(rate: 10,  interval: TimeSpan.FromSeconds(1), during: TimeSpan.FromMinutes(1)));
```

## Soak (4-hour endurance)

```csharp
.WithLoadSimulations(
    Simulation.Inject(rate: 100, interval: TimeSpan.FromSeconds(1), during: TimeSpan.FromHours(4)));
```

Watch the **slope** in the HTML report — latency drifting upward over the 4 hours is the leak the soak is meant to catch.

## SLO-shaped assertions (thresholds)

NBomber expresses thresholds via `Scenario.WithLoadSimulations(...).WithInit(...)` plus post-run assertions in `NBomberRunner`. The idiomatic gate uses the **stats API** at the end of the run:

```csharp
var result = NBomberRunner
    .RegisterScenarios(scenario)
    .Run();

var stats = result.ScenarioStats[0];
var p95   = stats.Ok.Latency.Percent95;
var fail  = stats.Fail.Request.Count / (double)stats.AllRequestCount;

if (p95 > 300)           Environment.Exit(1);   // p95 latency SLO
if (fail > 0.005)        Environment.Exit(1);   // error-rate SLO
```

Wrap in a small helper and call from `Program.cs`. Non-zero exit fails the pipeline step.

## Step types (multi-step scenarios)

For "log in → fetch → check" flows:

```csharp
return Scenario.Create("checkout", async ctx =>
{
    var login = await Step.Run("login", ctx, async () =>
    {
        var resp = await Http.Send(http, Http.CreateRequest("POST", $"{Env.BaseUrl}/auth/login")
            .WithJsonBody(new { user = "perf-001", pwd = "perf" }));
        return resp.IsError ? Response.Fail() : Response.Ok(payload: resp.Payload.Value);
    });

    var token = ExtractToken(login.Payload);

    var checkout = await Step.Run("checkout", ctx, async () =>
    {
        var resp = await Http.Send(http, Http.CreateRequest("POST", $"{Env.BaseUrl}/checkout")
            .WithHeader("Authorization", $"Bearer {token}")
            .WithJsonBody(new { cartId = "c-001" }));
        return resp.IsError ? Response.Fail() : Response.Ok();
    });

    return checkout.IsError ? Response.Fail() : Response.Ok();
});
```

Per-step latencies appear in the HTML report — diagnose where the time goes.

## Seeded fixtures

```csharp
// PerfTests/Fixtures.cs
public static class Fixtures
{
    public static async Task<List<string>> SeedOrders(int count)
    {
        var ids = new List<string>(count);
        for (var i = 0; i < count; i++)
        {
            var id = $"perf-{Guid.NewGuid():N}";
            // Use the production client to create the fixture.
            await ProductionOrdersClient.CreateAsync(id);
            ids.Add(id);
        }
        return ids;
    }

    public static async Task CleanUp(IEnumerable<string> ids)
    {
        foreach (var id in ids) await ProductionOrdersClient.DeleteAsync(id);
    }
}
```

Call from `Program.cs` around the `Run()`:

```csharp
var ids = await Fixtures.SeedOrders(50);
try
{
    NBomberRunner.RegisterScenarios(OrdersAverage.Build(ids)).Run();
}
finally
{
    await Fixtures.CleanUp(ids);
}
```

Namespace fixture ids per run (`perf-<guid>`) so parallel runs don't collide.

## Tool version pinning

Pin every NuGet reference in `PerfTests.csproj`:

```xml
<PackageReference Include="NBomber"      Version="5.7.0" />
<PackageReference Include="NBomber.Http" Version="5.4.0" />
```

Never use floating-version (`5.*`).

## CI integration

### GitHub Actions

```yaml
perf-smoke:
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-dotnet@v4
      with: { dotnet-version: '8.0.x' }
    - name: NBomber smoke
      env:
        BASE_URL:   ${{ secrets.STAGING_URL }}
        AUTH_TOKEN: ${{ secrets.STAGING_TOKEN }}
      run: dotnet run --project PerfTests -- smoke
    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: nbomber-report
        path: PerfTests/perf-reports
```

### Azure Pipelines

```yaml
- task: UseDotNet@2
  inputs: { version: '8.0.x' }

- script: dotnet run --project PerfTests -- smoke
  displayName: NBomber smoke
  env:
    BASE_URL:   $(STAGING_URL)
    AUTH_TOKEN: $(STAGING_TOKEN)

- task: PublishBuildArtifacts@1
  condition: always()
  inputs:
    PathtoPublish: PerfTests/perf-reports
    ArtifactName: nbomber-report
```

For the HTML report, use the `PublishHtmlReport@1` task pointing at `PerfTests/perf-reports/*/report.html`.

## Streaming metrics

For live correlation with the service's own metrics during a long run:

```csharp
NBomberRunner
    .RegisterScenarios(scenario)
    .WithReportingSinks(new InfluxDBSink("http://influxdb:8086", "nbomber"))
    .Run();
```

Grafana dashboards (`observability/grafana-dashboards`) then show client and server metrics on one chart.

## Rules (NBomber-specific)

- **Open-loop simulations (`Inject` / `RampingInject`)** by default. `KeepConstant` / `RampingConstant` only when modelling a fixed concurrency cap.
- **Standalone console app**, not an NUnit / xUnit fixture — NBomber is its own runner.
- **Single `HttpClient` reused via `HttpClientFactory.Create()`** — never `new HttpClient()` per iteration; you'll exhaust sockets within minutes.
- **`Http.CreateRequest` + `Http.Send`** instead of raw `HttpClient.SendAsync` so per-request metrics land in the report.
- **Async all the way** in scenario bodies — `.Result` / `.Wait()` deadlocks the runner under load.
- **Per-step latency** via `Step.Run` when a scenario has multiple HTTP hops — without it you can't tell which hop is slow.
- **`Environment.Exit(non-zero)`** on threshold breach so CI fails the build.
- **`WithReportFolder("perf-reports")`** — never write into the repo root; publish as a CI artifact.
- **Constructor-injection-friendly fixtures**: production clients consumed via DI live in `Fixtures.cs`, not constructed inline in scenarios.
- **Pin every NuGet package version** in `PerfTests.csproj`.
- **`Env.*` static class** loads from environment variables — never hardcode `BASE_URL` / tokens.

## What NOT to do

- No `new HttpClient()` per iteration — single `HttpClientFactory.Create()` per scenario.
- No `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` in scenario bodies.
- No closed-loop `KeepConstant` for an RPS target — use `Inject` / `RampingInject`.
- No hardcoded base URLs / tokens — env vars only.
- No `Console.WriteLine` in hot scenario paths — costs throughput; use NBomber's reporting interval instead.
- No persistence-mutating tests against prod — staging or dedicated perf env only.
- No reusing the same seeded fixture id across parallel runs — namespace per run id.
- No floating NuGet versions (`NBomber Version="5.*"`).
- No `Step.Run` per single-HTTP-call scenario — adds overhead without insight.
- No NUnit `[Test]` wrapper around NBomber scenarios — NBomber is its own runner; you'll fight two orchestrators.
- No mixing `NBomber.Http` with `RestSharp` in the same scenario — pick one HTTP path.

## Generation steps

1. Confirm tool (NBomber chosen over k6 because team prefers C#), workload model, SLO targets, target environment. (See `_shared`.)
2. Create `PerfTests/PerfTests.csproj` as `<OutputType>Exe</OutputType>`; add `NBomber` + `NBomber.Http` pinned.
3. Author `Env.cs` (env-var loader), `Fixtures.cs` (seed + cleanup via the production client), `Scenarios/<Name>.cs`.
4. Wire `Program.cs` to pick a scenario by CLI arg, run NBomberRunner, then exit non-zero on threshold breach.
5. Add CI step (smoke on PR; full on release). Publish `PerfTests/perf-reports/` as a CI artifact.
6. Run locally; review per-step latencies; confirm the test fails when an SLO is breached.
7. Add the report to the release / change notes (see `_shared` template).

## Handoffs

- Workload models, environment policy, reporting → `qa/performance/_shared`
- k6 (TypeScript) → `qa/performance/k6/typescript`
- Gatling (Java) → `qa/performance/gatling/java`
- SLO targets the test validates → `qa/_shared/quality-metrics`
- Grafana dashboards for server-side correlation → `observability/grafana-dashboards`
- Pipeline integration → `qa/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` or `devops/<ci>`
- Allure publishing for perf reports → `qa/allure-reporting/dotnet`
- Bug filings discovered during perf → `qa/bug-report-writer`

## Changelog

- 2026-05-29: Split from monolithic `qa/performance/SKILL.md` into the NBomber-specific .NET 8 sibling. Adds NBomber-specific guidance: standalone console-app runner (not NUnit fixture), open-loop `Inject` / `RampingInject` default, single `HttpClient` via `HttpClientFactory.Create`, `Step.Run` for multi-hop scenarios, post-run threshold gate via `Environment.Exit`, HTML / CSV / MD reports as CI artifacts, NuGet version pinning policy.
