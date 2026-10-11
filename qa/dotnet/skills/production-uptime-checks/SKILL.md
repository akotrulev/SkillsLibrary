---
name: qa-production-uptime-checks-dotnet
description: Use when authoring synthetic monitoring as code from the .NET / Azure stack — scheduled availability tests and scripted checks against live staging/prod via Azure Application Insights. The "is it up right now" layer, distinct from CI pre-merge tests. Triggers: "add a prod uptime check", "synthetic monitor for the login flow", "monitoring as code". Not for pre-merge CI gates (`qa-ci-pipelines-dotnet`) or load testing (`qa-load-testing-dotnet`).
---

# Synthetic Monitoring as Code (Azure App Insights · .NET 10) — **ported from the TypeScript/Checkly canonical**

The **dotnet** sibling of the `production-uptime-checks` family. The canonical stack is
`qa-production-uptime-checks-typescript` (**Checkly `@checkly/cli`**). This file **ports the discipline, not the
code** — with an honest divergence: **Checkly has no .NET SDK**, so the .NET-native tool is **Azure Application
Insights availability tests**, the way to write the probe **in C# end-to-end** and alert through the App
Insights an Azure shop already runs. If your team is happy writing TypeScript for monitoring, Checkly is the
richer experience even in a .NET shop: keep a small `monitoring/` TS sub-project (the canonical) and run its CLI
from your pipeline.

## What synthetic monitoring is (and what it is not)

**Synthetic monitoring** = scripted checks that run **on a schedule against a deployed, live target**
(staging/prod), alerting a human when the target is down or degraded. It is **not** a CI test (once, pre-merge,
ephemeral env — `qa-ci-pipelines-*`), **not** a load test (`qa-load-testing-dotnet`), and **not** a journey
author — it *reuses* the page objects from `qa-ui-test-writer-playwright-dotnet` and adds the assertion,
scheduling and alerting layer.

> **The discipline this skill encodes** (identical to the canonical):
>
> 1. **Two check types, both as code** — cheap HTTP **Standard availability tests** for "is the endpoint up and
>    within SLA", and **custom `TrackAvailability`** browser probes for "can a user actually do the thing". Both
>    declared in IaC + code and deployed by a pipeline — never clicked together in the portal.
> 2. **Assert an SLA, not just pass/fail** — a 200 that takes 8 seconds is a regression. The result carries a
>    **`Duration`**; gate `Success` on a latency budget and alert on the duration metric.
> 3. **Alert on the failure — and keep what explains it.** A metric alert + an action group page on-call; a
>    failed browser probe keeps its **trace, full-page screenshot and video**, so the page is read, not guessed.
> 4. **Wait on a condition, never a sleep** — Playwright auto-waits; never `Task.Delay`/`Thread.Sleep`.

## Decision matrix — which check for which job

| You want to know… | Check type | Mechanism | Gate on |
|---|---|---|---|
| Is the API/health endpoint up and fast? | **Standard availability test** | `Microsoft.Insights/webtests` (Bicep) / `azurerm_application_insights_standard_web_test` (Terraform) | expected status + content match + `Timeout` (the SLA) |
| Can a user log in / search / check out? | **Custom `TrackAvailability`** | a scheduled container running the Playwright probe | journey completes + `Duration` budget |
| Does a multi-call API flow work end-to-end? | **Custom `TrackAvailability`** | the same host chaining `HttpClient` calls | each step's exact status |
| Should several alerts share routing? | **action group** | `Microsoft.Insights/actionGroups` | (routing, not a check) |

**Rule of thumb:** *every endpoint* gets a cheap Standard test; *every business-critical journey* gets a custom
probe. Don't write a custom probe for what a Standard test can prove.

## Stack

- .NET 10 (8/9 supported — match the services' TFM); `Microsoft.ApplicationInsights` —
  `TelemetryClient.TrackAvailability(AvailabilityTelemetry)` and `FlushAsync(CancellationToken)`.
- **Microsoft.Playwright** at the version in the **Versions** table of
  `qa/dotnet/skills/ui-test-author/playwright/SKILL.md` (this skill pins nothing) — the probe **reuses** that
  suite's page objects. A probe is not a test fixture: there is no NUnit runner and no `BaseTest`, so the probe
  owns its `Playwright.CreateAsync()`, its context and its evidence, in `BaseTest`'s order.
- **The host runs a container that carries the browsers**: an Azure Container Apps **job** on a cron schedule
  (or a Functions Premium/Dedicated plan on a custom container), built `FROM
  mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` — browsers preinstalled, the tag equal to the package
  version. A Consumption-plan Function cannot launch Chromium.
- Bicep / Terraform for Standard tests, metric alerts and action groups.
- Configuration from env / Key Vault, read once at start, never logged: `APPLICATIONINSIGHTS_CONNECTION_STRING`,
  `SYNTHETIC_BASE_URL`, `SYNTHETIC_USER`, `SYNTHETIC_PASSWORD`, `SYNTHETIC_EVIDENCE_DIR`, `REGION_NAME`.

```
monitoring/
├── infra/availability.bicep        ← Standard web tests + metric alerts + action groups
├── src/Monitoring.Probes/
│   ├── CheckoutJourneyProbe.cs     ← TrackAvailability: the Playwright journey, REUSING UiTests/Pages
│   ├── ProbeEvidence.cs            ← trace, screenshot, video kept on failure
│   ├── ProbeSettings.cs
│   ├── Program.cs                  ← one run per scheduled job execution
│   └── Dockerfile                  ← FROM mcr.microsoft.com/playwright/dotnet:v1.63.0-noble
└── README.md
```

## Check type 1 — Standard availability tests (status + latency + content)

Declarative IaC, deployed by the pipeline. The SLA controls: **`Timeout`** is the hard latency budget,
`ExpectedHttpStatusCode` + `ContentMatch` assert status **and body shape**, and several `Locations` separate a
regional blip from an outage. The Bicep, the alerts and the action group are in
[`references/details.md`](references/details.md) §1–§2.

## Check type 2 — custom `TrackAvailability` (a real journey, reusing your page objects)

The probe runs the journey with the CI suite's page objects and pushes the verdict to App Insights. Its
`try`/`catch` converts **one named exception** — `PlaywrightException`, which every Playwright action timeout
and every failed `Expect(...)` assertion throws in .NET — into the result; anything else (the browser cannot
launch, the evidence volume is missing) propagates, and the `finally` still records a failed result.

```csharp
using System.Diagnostics;
using Example.UiTests.Pages;
using Microsoft.ApplicationInsights;
using Microsoft.ApplicationInsights.DataContracts;
using Microsoft.Playwright;
using static Microsoft.Playwright.Assertions;

namespace Monitoring.Probes;

public sealed class CheckoutJourneyProbe(TelemetryClient telemetry, ProbeEvidence evidence, ProbeSettings settings)
{
    private const string CheckName = "checkout-journey";
    private static readonly TimeSpan Budget = TimeSpan.FromSeconds(15);

    public async Task RunAsync(string runLocation, CancellationToken cancellationToken)
    {
        var availability = new AvailabilityTelemetry { Name = CheckName, RunLocation = runLocation, Timestamp = DateTimeOffset.UtcNow };
        var stopwatch = Stopwatch.StartNew();
        try
        {
            using var playwright = await Playwright.CreateAsync();
            await using var browser = await playwright.Chromium.LaunchAsync();
            var context = await browser.NewContextAsync(new() { BaseURL = settings.BaseUrl, RecordVideoDir = evidence.RawVideoDirectory });
            context.SetDefaultTimeout((float)Budget.TotalMilliseconds);
            await context.Tracing.StartAsync(new() { Title = CheckName, Screenshots = true, Snapshots = true });
            var page = await context.NewPageAsync();

            var failure = await RunJourneyAsync(page);
            var kept = await evidence.KeepAsync(CheckName, context, page, failed: failure is not null, cancellationToken);

            availability.Success = failure is null && stopwatch.Elapsed <= Budget;
            availability.Message = failure ?? (availability.Success ? null : $"Journey exceeded the {Budget.TotalSeconds:0}s budget: {stopwatch.Elapsed}");
            availability.Properties["evidence"] = string.Join(";", kept);
        }
        finally
        {
            availability.Duration = stopwatch.Elapsed;
            telemetry.TrackAvailability(availability);
            await telemetry.FlushAsync(cancellationToken);
        }
    }

    private async Task<string?> RunJourneyAsync(IPage page)
    {
        try
        {
            await new LoginPage(page).SignInAsync(new LoginPage.Credentials(settings.User, settings.Password));
            var cart = new CartPage(page);
            await cart.AddFirstFeaturedItemAsync();
            await Expect(cart.ItemCount, "cart badge after adding one item").ToHaveTextAsync("1");
            return null;
        }
        catch (PlaywrightException exception)
        {
            return exception.Message;
        }
    }
}
```

- **`BaseURL` comes from `SYNTHETIC_BASE_URL`**, so `LoginPage.GoToAsync()`'s `"/login"` resolves against the
  live target — the same page object the CI suite runs against `BASE_URL`.
- **`SetDefaultTimeout(Budget)`** bounds every action, so a hung page fails inside the budget instead of
  holding the job.
- **`cancellationToken` reaches every call that takes one** — the evidence step (checked once its files are
  complete) and `FlushAsync`; Playwright's .NET calls take none, which is what the action timeout is for.
- **The verdict is recorded in `finally`**, so a probe that cannot even launch reads as a failed check, not as
  silence. `AvailabilityTelemetry.Success` starts `false`.
- A multi-call API probe has the same shape with `HttpClient`: assert each step's **exact** status, record the
  first mismatch with its body as the message.

## Failure evidence — `ProbeEvidence`

The probe has no test runner, no `bin/` folder and no Allure report, so it keeps evidence the way `BaseTest`
does — recorded on every run, **kept only on failure**, in `BaseTest`'s order — under
`SYNTHETIC_EVIDENCE_DIR`: a private, mounted volume (an Azure Files share on the job) with a lifecycle rule
deleting files after 14 days, as `qa/cicd/ci-conventions` retains CI evidence.

| Evidence | Kept when | File |
|---|---|---|
| Trace (screenshots, DOM snapshots) | the journey failed | `<SYNTHETIC_EVIDENCE_DIR>/<check>.<UTC yyyyMMddTHHmmssZ>.zip` |
| Full-page screenshot | the journey failed | `….png` |
| Video | the journey failed | `….webm` (raw recordings in `raw-videos/`, always deleted) |

The order is fixed — stop the trace to a path, take the screenshot, close the context, `SaveAsAsync` the video,
always `DeleteAsync` — with **no catch** (a screenshot of a crashed page throws; the trace is already saved).
The kept paths go into the availability result's `evidence` property and a warning log line, so the alert links
to them. Code: [`references/details.md`](references/details.md) §3. A trace carries the synthetic user's
session: the volume is private, the user is a disposable synthetic account, and evidence is never uploaded
anywhere public.

## Alerting + SLA thresholds — the part that makes it a monitor

Both check types land in App Insights as **availability results**. One metric alert on
`availabilityResults/availabilityPercentage` (< 100 over the window) and a second on
`availabilityResults/duration` (> the budget) route to one action group — both declared in Bicep
([`references/details.md`](references/details.md) §2). Absorb a single transient blip by requiring the failure
across **multiple evaluation periods**, never by retrying inside the probe.

## The boundary — a synthetic monitor vs a CI gate

| | CI test (`qa-ci-pipelines-*`) | Synthetic monitor (this skill) |
|---|---|---|
| **When** | Pre-merge / pre-promote, once | On a schedule, forever |
| **Against** | An ephemeral env | The live prod/staging target |
| **Host** | The CI runner | App Insights (Standard test) / a scheduled container (custom) |
| **Alerts?** | No — green/red gate | Yes — metric alert + action group pages on-call |

One set of page objects, two execution models: the NUnit suite runs them against the preview env (the gate);
the probe runs them against the live env (the monitor).

## Anti-patterns

- **Asserting only the status code.** *Fix:* `Timeout` on the Standard test, the `Duration` budget in the probe,
  an alert on `availabilityResults/duration`.
- **A probe with no alert**, or **hand-clicked tests in the portal**. *Fix:* metric alert + action group in Bicep.
- **`catch (Exception)` around the whole journey.** It files a missing volume or a broken deployment as "the
  checkout is down", and nothing explains the failure. *Fix:* catch `PlaywrightException` only, record the
  verdict in `finally`, keep the evidence.
- **A failed probe that keeps nothing.** *Fix:* `ProbeEvidence` — trace, screenshot, video on failure.
- **A relative `GotoAsync` with no `BaseURL`**, or a hardcoded host. *Fix:* `SYNTHETIC_BASE_URL` on the context.
- **A Consumption-plan Function launching Chromium.** It has no browser. *Fix:* the pinned Playwright image on
  a container job or a Premium/Dedicated custom container.
- **`Task.Delay` / `Thread.Sleep` to "let it settle"**, or **re-authoring the journey inside the probe**. *Fix:*
  auto-waiting `Expect(...)`; the CI suite's page objects.
- **Secrets in Bicep or `appsettings.json`**, or **no flush before the host exits**. *Fix:* `@secure()` params
  from Key Vault; `FlushAsync` in `finally`.

## Rules (hard constraints)

- **Synthetics run against a LIVE target, post-deploy, on a schedule — never as the merge gate.**
- **Assert an SLA, not just a status code**; **every check has an alert**; absorb transients with the alert
  window, never with retries inside the probe (`qa-flaky-test-quarantine-dotnet`).
- **A browser probe keeps trace, full-page screenshot and video on failure**, in `BaseTest`'s order, under
  `SYNTHETIC_EVIDENCE_DIR`, and puts the paths in the result.
- **Catch only `PlaywrightException`** in the journey; record the verdict in `finally`; flush with the
  cancellation token.
- **The probe reuses the UI suite's page objects** and resolves them against `SYNTHETIC_BASE_URL`.
- **Wait on a condition, never a sleep.** Async all the way; constructor injection; structured logging
  (message templates); secrets from env / Key Vault, never logged.

## Cross-references

- `qa-production-uptime-checks-typescript` — the **canonical** stack (Checkly); prefer it if your team writes TS.
- `qa-production-uptime-checks-java` — Grafana Cloud Synthetic Monitoring and the `@Scheduled` Playwright-Java
  probe; the same evidence shape.
- `qa-ui-test-writer-playwright-dotnet` — the page objects the probe reuses, and `BaseTest`'s evidence order.
- `qa-evidence-capture-dotnet` — reading a kept trace (`trace open` / `show-trace`, trace.playwright.dev).
- `qa-load-testing-dotnet` — throughput, not uptime.
- `qa-ci-pipelines-dotnet` — the pre-merge gate, and where `az deployment` / `terraform apply` and the probe
  image build are wired.
- `qa-test-login-tokens-dotnet` — M2M / test-user tokens for probes hitting an authenticated endpoint.
- `qa-flaky-test-quarantine-dotnet` — a probe that needs the alert window widened to stay green is flaky; fix
  the cause.
