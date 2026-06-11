---
name: qa-synthetic-monitoring-dotnet
description: Use when authoring synthetic monitoring as code from the .NET / Azure stack — scheduled availability tests and scripted checks against live staging/prod via Azure Application Insights. The "is it up right now" layer, distinct from CI pre-merge tests. Triggers: "add a prod uptime check", "synthetic monitor for the login flow", "monitoring as code".
---

# Synthetic Monitoring as Code (Azure App Insights · .NET 8) — **ported from the TypeScript/Checkly canonical**

This is the **dotnet** sibling of the `qa/dotnet/skills/synthetic-monitoring/` family. The canonical stack is
`qa-synthetic-monitoring-typescript` (**Checkly `@checkly/cli`**). This file **ports the discipline, not the
code** — and the port has an honest divergence: **Checkly has no official .NET SDK** (it's TS/JS-only; browser
checks are Playwright-JS). So the .NET-native tool is **Azure Application Insights availability tests**, the
only way to write the probe **in C# end-to-end** and integrate with the App Insights alerting an Azure shop
already runs. The four ideas are identical to the canonical — two check types, monitoring-as-code, alerting +
SLA thresholds, wait-on-a-condition — only the tool changes.

> **If your team is happy writing TypeScript for monitoring**, Checkly is the richer monitoring-as-code
> experience even in a .NET shop: keep a small `monitoring/` TS sub-project (the canonical) and run its CLI
> from your Azure DevOps pipeline. Pick **App Insights** (this file) when you want the probe authored in C#,
> co-located with your services, and wired into the Azure alerting/dashboards you already own.

## What synthetic monitoring is (and what it is not)

**Synthetic monitoring** = scripted checks that run **on a schedule against a deployed, live target**
(staging/prod), continuously, alerting a human when the target is down or degraded. A synthetic check is a
**continuously-running assertion**: you don't watch the result, you alert on its *failure*.

It is **not**:

- a **CI test** — CI tests run **once, pre-merge, against an ephemeral env** to gate a change
  (`qa-ci-pipelines-*`). A synthetic runs **forever, post-deploy, against the real thing**.
- a **load test** — `qa-performance-nbomber` drives throughput to find the breaking point; a synthetic fires
  one scripted journey every N minutes to answer "is it working *right now*".
- a **journey author** — this skill *reuses* the page objects authored by
  `qa-ui-test-author-playwright-dotnet`; it is the **assertion + scheduling + alerting layer**, not a new author.

> **The discipline this skill encodes** (identical to the canonical):
>
> 1. **Two check types, both as code** — cheap HTTP **Standard availability tests** for the "is the endpoint
>    up + within SLA" layer, and **custom `TrackAvailability`** browser/multi-step probes for "can a user
>    actually do the thing". Both declared in IaC + code, reviewed and deployed by a pipeline — never clicked
>    together in the portal.
> 2. **Assert an SLA, not just pass/fail** — a 200 that takes 8 seconds is a regression. The availability
>    result carries a **`Duration`**; gate the test's `Success` on a latency budget and alert on the duration metric.
> 3. **Alert on the failure** — an availability metric alert + an action group page on-call. A check no one is
>    paged on does nothing.
> 4. **Wait on a condition, never a sleep** — Playwright-.NET auto-waits; never `Task.Delay`/`Thread.Sleep` to
>    "let it settle".

## Decision matrix — which check for which job

| You want to know… | Check type | Mechanism | Gate on |
|---|---|---|---|
| Is the API/health endpoint up and fast? | **Standard availability test** | `azurerm_application_insights_standard_web_test` (Bicep/Terraform) | expected status + content match + `timeout` (the SLA) |
| Can a user log in / search / check out? | **Custom `TrackAvailability`** | Timer-triggered Function/worker running Playwright-.NET | journey completes + `Duration` budget + `Success` flag |
| Does a multi-call API flow work end-to-end? | **Custom `TrackAvailability`** | scheduled worker chaining `HttpClient` calls | each step's status + chained assertions |
| Should several alerts share routing? | **action group** | `azurerm_monitor_action_group` | (shared notification routing, not a check) |

**Rule of thumb:** *every endpoint* gets a cheap **Standard test** (portal/IaC-managed, runs from Azure
points-of-presence). *Every business-critical journey* gets a **custom `TrackAvailability`** probe (your code,
your Playwright journey). Don't write a custom probe for what a Standard test can prove.

## Stack

- .NET 8, NUnit (for any local verification of the probe logic) — **no `Task.Delay` / `Thread.Sleep`-as-wait**
- `Microsoft.ApplicationInsights` — `TelemetryClient.TrackAvailability(AvailabilityTelemetry)`
- `Microsoft.Playwright` — custom browser-journey probes; **reuse** the page objects from
  `qa-ui-test-author-playwright-dotnet` (cross-link — this skill does not author them)
- Azure Functions (Timer trigger, isolated worker) **or** a `BackgroundService` worker — the schedule host
- Bicep / Terraform — Standard web tests + metric alerts + action groups as **config-as-code**
- Secrets via env / Key Vault, read lazily, never logged (`APPLICATIONINSIGHTS_CONNECTION_STRING`, target creds)

```
monitoring/
├── infra/
│   ├── availability.bicep            ← Standard web tests + metric alerts + action groups (config-as-code)
│   └── main.tf                       ← (alt) the same as Terraform
├── src/Monitoring.Probes/
│   ├── CheckoutJourneyProbe.cs       ← a TrackAvailability probe: Playwright-.NET, REUSES Pages/*
│   ├── ApiFlowProbe.cs               ← a TrackAvailability probe: chained HttpClient calls
│   └── ProbeTimerFunction.cs         ← Timer-triggered Function that runs the probes on a schedule
└── README.md
```

## Monitoring-as-code — IaC for the cheap layer, a scheduled worker for the rich layer

Nothing is hand-clicked in the portal. The cheap HTTP layer is **declarative IaC**; the rich journey layer is
**a scheduled worker** deployed by the same pipeline.

**Standard availability test as config-as-code (Bicep):**

```bicep
// monitoring/infra/availability.bicep
param location string = resourceGroup().location
param appInsightsId string

resource healthTest 'Microsoft.Insights/webtests@2022-06-15' = {
  name: 'storefront-health'
  location: location
  kind: 'standard'
  tags: { 'hidden-link:${appInsightsId}': 'Resource' }   // links the test to the App Insights resource
  properties: {
    SyntheticMonitorId: 'storefront-health'
    Name: 'Storefront API — health + SLA'
    Enabled: true
    Frequency: 300                                        // every 5 min (seconds)
    Timeout: 30                                           // FAIL if the request takes > 30s — the latency budget
    Kind: 'standard'
    Locations: [                                          // run from multiple Azure POPs — catch regional outages
      { Id: 'us-tx-sn1-azr' }
      { Id: 'emea-nl-ams-azr' }
    ]
    Request: { RequestUrl: 'https://staging.acme.example/api/health', HttpVerb: 'GET' }
    ValidationRules: {
      ExpectedHttpStatusCode: 200
      SSLCheck: true
      SSLCertRemainingLifetimeCheck: 30                   // also alert 30 days before the TLS cert expires
      ContentValidation: { ContentMatch: '"status":"healthy"', IgnoreCase: false, PassIfTextFound: true }
    }
  }
}
```

Deploy it from the pipeline (`az deployment group create` / `terraform apply`) — cross-link
`qa-ci-pipelines`. This is the synthetic-vs-CI boundary: this resource runs **forever, against
the live target**, not as a pre-merge gate.

## Check type 1 — Standard availability tests (status + latency + content)

The Bicep above *is* the API/uptime layer. The key SLA controls: **`Timeout`** is the hard latency budget (the
test fails if the response is slower), `ExpectedHttpStatusCode` + `ContentMatch` assert status **and body
shape**, and `Locations` runs it from multiple Azure points-of-presence so a regional blip is distinguishable
from a real outage. **Assert the SLA, not just the status** — that's what makes it a monitor and not a ping.

## Check type 2 — custom `TrackAvailability` (a real journey, reusing your page objects)

For "can a user actually do the thing", a Standard test isn't enough — you need a real browser journey. Write
it as a **custom availability test**: a scheduled probe runs a Playwright-.NET journey (**reusing the page
objects** from `qa-ui-test-author-playwright-dotnet`) and pushes the verdict to App Insights via
`TelemetryClient.TrackAvailability`. This is the only way to author the probe **in C#**.

```csharp
// monitoring/src/Monitoring.Probes/CheckoutJourneyProbe.cs
public sealed class CheckoutJourneyProbe
{
    private readonly TelemetryClient _telemetry;   // constructor injection — no service locator

    public CheckoutJourneyProbe(TelemetryClient telemetry) => _telemetry = telemetry;

    public async Task RunAsync(string runLocation, CancellationToken ct)
    {
        var availability = new AvailabilityTelemetry
        {
            Name = "checkout-journey",
            RunLocation = runLocation,                       // which region this probe ran from
            Success = false,
        };
        var stopwatch = Stopwatch.StartNew();
        try
        {
            using var playwright = await Playwright.CreateAsync();
            await using var browser = await playwright.Chromium.LaunchAsync();
            var page = await browser.NewPageAsync();

            // REUSE the SAME page objects the CI suite uses — intent, not selectors
            var login = new LoginPage(page);
            await login.GotoAsync();
            // creds from env, read lazily, NEVER logged — set in app settings / Key Vault
            await login.SignInAsAsync(
                Environment.GetEnvironmentVariable("SYNTHETIC_USER")!,
                Environment.GetEnvironmentVariable("SYNTHETIC_PASSWORD")!);

            var cart = new CartPage(page);
            await cart.AddFirstFeaturedItemAsync();
            // Playwright auto-waits on the condition — NO Task.Delay to "let the cart update"
            await Microsoft.Playwright.Assertions.Expect(cart.ItemCount).ToHaveTextAsync("1");

            availability.Success = true;                     // SLA: also fail if too slow (see below)
            if (stopwatch.Elapsed > TimeSpan.FromSeconds(15))
            {
                availability.Success = false;
                availability.Message = $"Journey exceeded the 15s SLA: {stopwatch.Elapsed}";
            }
        }
        catch (Exception ex)
        {
            availability.Success = false;
            availability.Message = ex.Message;               // the failure reason travels to App Insights
            _telemetry.TrackException(ex);
        }
        finally
        {
            stopwatch.Stop();
            availability.Duration = stopwatch.Elapsed;       // the latency the alert can gate on
            availability.Timestamp = DateTimeOffset.UtcNow;
            _telemetry.TrackAvailability(availability);       // ← the verdict App Insights monitors + alerts on
            _telemetry.Flush();                               // ensure it's sent before the host tears down
        }
    }
}
```

The **schedule host** is a Timer-triggered Function (or a `BackgroundService`) — it runs the probe every N
minutes, exactly like Checkly's scheduler runs a browser check:

```csharp
// monitoring/src/Monitoring.Probes/ProbeTimerFunction.cs (isolated-worker Azure Functions)
public sealed class ProbeTimerFunction
{
    private readonly CheckoutJourneyProbe _probe;

    public ProbeTimerFunction(CheckoutJourneyProbe probe) => _probe = probe;   // DI, async all the way

    [Function("CheckoutJourneyProbe")]
    public Task RunAsync([TimerTrigger("0 */15 * * * *")] TimerInfo timer, CancellationToken ct)  // every 15 min
        => _probe.RunAsync(runLocation: Environment.GetEnvironmentVariable("REGION_NAME") ?? "local", ct);
}
```

## Alerting + SLA thresholds — the part that makes it a monitor

Both check types surface into App Insights as **availability results**. Alert on them with a metric alert +
an action group — declared as config-as-code so the alert is reviewed and versioned like everything else.

```bicep
// action group — the routing (email / SMS / webhook / PagerDuty)
resource oncall 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'storefront-oncall'
  location: 'global'
  properties: {
    groupShortName: 'sfOncall'
    enabled: true
    emailReceivers: [ { name: 'oncall', emailAddress: 'oncall@acme.example' } ]
    webhookReceivers: [ { name: 'pagerduty', serviceUri: pagerDutyWebhookUri } ]   // uri from a secure param
  }
}

// metric alert — availability < 100% over the window pages on-call (covers BOTH check types)
resource availabilityAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'storefront-availability-below-sla'
  location: 'global'
  properties: {
    severity: 1
    enabled: true
    scopes: [ appInsightsId ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [ {
        name: 'availability'
        metricNamespace: 'microsoft.insights/components'
        metricName: 'availabilityResults/availabilityPercentage'
        operator: 'LessThan'
        threshold: 100
        timeAggregation: 'Average'
        criterionType: 'StaticThresholdCriterion'
      } ]
    }
    actions: [ { actionGroupId: oncall.id } ]
  }
}
```

A second alert on `availabilityResults/duration` (operator `GreaterThan`, threshold = your latency budget)
catches **slow-but-up** — the SLA-breach signal the canonical's `degradedResponseTime` gives you. To absorb a
single transient blip without paging (the canonical's bounded retry), set the test's evaluation to require the
failure across **multiple periods** (`windowSize` > `evaluationFrequency`) rather than retrying inside the probe.

## Secrets from env, never logged

Connection string, target URLs, and test-user creds come from app settings / Key Vault — read lazily, never
committed, never logged:

```csharp
// Program.cs — the connection string is the ONLY App Insights secret; from env, never hard-coded
builder.Services.AddApplicationInsightsTelemetryWorkerService(o =>
    o.ConnectionString = Environment.GetEnvironmentVariable("APPLICATIONINSIGHTS_CONNECTION_STRING"));
builder.Services.AddSingleton<CheckoutJourneyProbe>();
```

In Bicep, pass webhook URIs and the connection string as `@secure()` params sourced from Key Vault — never
literals in the template.

## The boundary — a synthetic monitor vs a CI gate

Same distinction as the canonical, made concrete in Azure:

| | CI test (`qa-ci-pipelines-*`) | Synthetic monitor (this skill) |
|---|---|---|
| **When** | Pre-merge / pre-promote, once | On a schedule, forever |
| **Against** | An ephemeral env | The live prod/staging target |
| **Host** | The CI runner | App Insights (Standard test) / a Timer Function (custom) |
| **Alerts?** | No — green/red gate | Yes — metric alert + action group pages on-call |

A Playwright-.NET journey can serve **both**: run it as an NUnit test in CI against the preview env (the gate),
**and** run the same page objects from the `TrackAvailability` probe against the live env (the monitor). One
set of page objects, two execution models.

## Anti-patterns

- **Asserting only the status code.** A 200 that takes 9 seconds is a regression. *Fix:* set `Timeout` (the
  latency budget) on the Standard test, gate the custom probe's `Success` on `Duration`, and alert on the
  `availabilityResults/duration` metric.
- **A probe with no alert.** It runs, it goes red in App Insights, no one is paged. *Fix:* a
  `metricAlert` on `availabilityPercentage` + an `actionGroup`; a synthetic *is* its alert.
- **`Task.Delay(3000)` / `Thread.Sleep` to "let it settle".** Flaky and slow, banned across the library. *Fix:*
  Playwright-.NET auto-waits; `Expect(...).ToHaveTextAsync(...)`. (Cross-link `qa-flaky-test-quarantine-dotnet`.)
- **Hand-clicking availability tests in the Azure portal.** Unversioned, unreviewed, lost on resource churn.
  *Fix:* Bicep/Terraform for Standard tests + alerts; a deployed Function for custom probes.
- **Running the synthetic as the merge gate against an ephemeral env.** That's a CI test, wrong tool. *Fix:*
  the gate is an NUnit run in CI; the monitor is the Standard test / `TrackAvailability` probe against the live target.
- **Re-authoring the journey inside the probe.** Duplicated selectors that drift from the CI suite. *Fix:* the
  probe **imports the same page objects** from `qa-ui-test-author-playwright-dotnet`.
- **Connection string / creds in the Bicep template or `appsettings.json`.** Committed secrets. *Fix:* `@secure()`
  params from Key Vault + `APPLICATIONINSIGHTS_CONNECTION_STRING` from env, read lazily.
- **Forgetting `_telemetry.Flush()` in a short-lived host.** The availability result never ships and the
  monitor looks dead. *Fix:* flush in the `finally` before the host tears down.

## Examples

**End-to-end: a cheap Standard test + a custom journey probe, both alerting through one action group.**

The `availability.bicep` above declares the Standard `health` test (every 5 min, 30s timeout, content match);
the `ProbeTimerFunction` runs the `CheckoutJourneyProbe` (Playwright-.NET, reusing `Pages/*`) every 15 min and
pushes `TrackAvailability`; one `metricAlert` on `availabilityPercentage` covers **both** and routes to the
`storefront-oncall` action group. The Standard test pages if the API is down or slow; the custom probe pages if
a user can't check out — and the same `LoginPage`/`CartPage` page objects are exercised by the CI NUnit suite
(the gate) and the probe (the monitor).

## Rules (hard constraints)

- **Synthetics run against a LIVE target, post-deploy, on a schedule — never as the merge gate.** Standard
  tests + `TrackAvailability` probes monitor the live env; the pre-merge gate is an NUnit run in CI
  (`qa-ci-pipelines-*`).
- **Assert an SLA, not just a status code.** Standard test `Timeout` + custom-probe `Duration` budget + a
  `availabilityResults/duration` metric alert — not only `ExpectedHttpStatusCode: 200`.
- **Every check has an alert.** A `metricAlert` on `availabilityPercentage`/`duration` + an `actionGroup`. A
  synthetic *is* its alert.
- **Absorb transients without masking.** Require failure across multiple evaluation periods rather than
  retrying-to-green inside the probe; never widen the window just to silence a real flake
  (`qa-flaky-test-quarantine-dotnet`).
- **Wait on a condition, never a sleep.** Playwright-.NET auto-waits; `Expect(...).ToHave*Async`. No
  `Task.Delay`/`Thread.Sleep`-as-wait. Async all the way — no `.Result`/`.Wait()`.
- **Monitoring-as-code.** Standard tests + alerts in Bicep/Terraform, custom probes in a deployed Function —
  reviewed and pipeline-deployed, never hand-clicked in the portal.
- **Custom probes REUSE the page objects** from `qa-ui-test-author-playwright-dotnet` — intent, not selectors;
  this skill is the assertion/scheduling/alerting layer, not a journey author.
- **Secrets from env / Key Vault, never logged.** `APPLICATIONINSIGHTS_CONNECTION_STRING` + creds from env,
  `@secure()` Bicep params, read lazily. Constructor injection only; structured logging (message templates).

## Cross-references

- `qa-synthetic-monitoring-typescript` — the **canonical** stack (Checkly `@checkly/cli`), the richest
  monitoring-as-code experience; this dotnet file ports its four ideas. **If your team will write TS for
  monitoring, prefer Checkly even in a .NET shop** (small `monitoring/` TS sub-project run from the pipeline).
- `qa-synthetic-monitoring-java` — same four ideas, the JVM/observability-native tool: **Grafana Cloud
  Synthetic Monitoring**. Honest divergence: no Checkly Java SDK either.
- `qa-ui-test-author-playwright-dotnet` — authors the page objects + journeys that the **custom probes reuse**.
  This skill schedules and alerts on them; it does not author them. Mirror its intent-not-selectors discipline.
- `qa-performance-nbomber` — load testing (throughput), NOT uptime. Synthetics check "is it working"; NBomber
  checks "how much can it take".
- `qa-ci-pipelines` / `-github-actions` / `-gitlab-ci` — the **pre-merge gate against
  ephemeral envs** boundary; also where `az deployment` / `terraform apply` for the Standard tests + Function
  deploy are wired.
- `qa-auth0-test-tokens-dotnet` — M2M / test-user tokens for probes hitting an **authenticated** live
  endpoint (mint in the probe; creds from env, lazily).
- `qa-flaky-test-quarantine-dotnet` — a probe that needs the alert window widened to stay green is
  *flaky*; fix the root cause rather than masking the alert.
- `qa-allure-reporting-dotnet` — surfacing probe-verification runs (the synthetic's reporting layer beyond the
  App Insights availability dashboard); also `observability` for the Azure Monitor / dashboards the
  availability results feed.
