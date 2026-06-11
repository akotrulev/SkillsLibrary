# Deep-dive details — `qa-performance-nbomber-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## SLO-shaped assertions (thresholds)

NBomber has **two** ways to turn a run into a pass/fail gate. Use both: runtime thresholds for early-abort + report visibility, and a post-run stats check for the deterministic CI exit code.

### Runtime thresholds — `.WithThresholds` (NBomber ≥ 5.8)

Runtime thresholds are evaluated **every 5 seconds during the test**, surface in the HTML report, and can abort a doomed run early. Attach them to the scenario:

```csharp
return Scenario.Create("orders_average", async ctx => { /* ... */ })
    .WithLoadSimulations(
        Simulation.Inject(rate: 50, interval: TimeSpan.FromSeconds(1), during: TimeSpan.FromMinutes(5)))
    .WithThresholds(
        // Fail if error rate exceeds 0.5%
        Threshold.Create(stats => stats.Fail.Request.Percent < 0.5),

        // Fail if p95 latency exceeds 300ms
        Threshold.Create(stats => stats.Ok.Latency.Percent95 < 300),

        // RPS floor — but only start checking after the 30s warm-up window
        Threshold.Create(stats => stats.Ok.Request.RPS > 100,
                         startCheckAfter: TimeSpan.FromSeconds(30)),

        // Abort the whole test after 5 consecutive checks see 503s
        Threshold.Create(stats => !stats.Fail.StatusCodes.Exists("503"),
                         abortWhenErrorCount: 5));
```

`Threshold.Create` also reads custom metrics (`stats => stats.Counters.Get("retries").Value < 100`) when a scenario records them.

### Post-run stats check — the CI exit code

Runtime thresholds influence the report, but the **deterministic build gate** is a post-run check against the final stats, with a non-zero `Environment.Exit`:

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

Wrap in a small helper and call from `Program.cs`. Non-zero exit fails the pipeline step. Prefer the post-run check for the build gate because it's explicit and unit-testable; use runtime thresholds for fail-fast and report annotations.
