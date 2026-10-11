# Deep-dive details — `qa-dotnet:production-uptime-checks`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## 1. Standard availability test as config-as-code (Bicep)

`monitoring/infra/availability.bicep`:

```bicep
param location string = resourceGroup().location
param appInsightsId string
param healthUrl string

resource healthTest 'Microsoft.Insights/webtests@2022-06-15' = {
  name: 'storefront-health'
  location: location
  kind: 'standard'
  tags: { 'hidden-link:${appInsightsId}': 'Resource' }
  properties: {
    SyntheticMonitorId: 'storefront-health'
    Name: 'Storefront API — health + SLA'
    Enabled: true
    Frequency: 300
    Timeout: 30
    Kind: 'standard'
    Locations: [
      { Id: 'us-tx-sn1-azr' }
      { Id: 'emea-nl-ams-azr' }
    ]
    Request: { RequestUrl: healthUrl, HttpVerb: 'GET' }
    ValidationRules: {
      ExpectedHttpStatusCode: 200
      SSLCheck: true
      SSLCertRemainingLifetimeCheck: 30
      ContentValidation: { ContentMatch: '"status":"healthy"', IgnoreCase: false, PassIfTextFound: true }
    }
  }
}
```

- The `hidden-link` tag links the test to the App Insights resource; without it the results land nowhere.
- `Frequency: 300` runs it every five minutes; **`Timeout: 30` is the latency budget** — slower is a failure.
- Two `Locations` (Azure points of presence) separate a regional blip from an outage.
- `SSLCertRemainingLifetimeCheck: 30` fails the test 30 days before the TLS certificate expires.
- `healthUrl` is the environment's own health endpoint, passed per environment by the pipeline's parameter
  file — the template never hardcodes one environment for all.

Deploy it from the pipeline (`az deployment group create` / `terraform apply`), never the portal —
`qa-dotnet:ci-pipelines`.

## 2. Alerts and the action group

```bicep
@secure()
param pagerDutyWebhookUri string

resource oncall 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'storefront-oncall'
  location: 'global'
  properties: {
    groupShortName: 'sfOncall'
    enabled: true
    emailReceivers: [ { name: 'oncall', emailAddress: 'oncall@acme.example' } ]
    webhookReceivers: [ { name: 'pagerduty', serviceUri: pagerDutyWebhookUri } ]
  }
}

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

- The alert covers **both** check types: Standard tests and `TrackAvailability` probes write the same metric.
- A second alert on `availabilityResults/duration` (`GreaterThan`, threshold = the budget) catches
  **slow-but-up** — the canonical's `degradedResponseTime`.
- `windowSize` > `evaluationFrequency` requires the failure across several periods: that absorbs one transient
  blip without a retry inside the probe. Never widen it just to silence a real flake.
- The webhook URI and every other secret are `@secure()` params sourced from Key Vault, never literals.

## 3. The probe's support code

### `ProbeSettings` — read once, required

```csharp
namespace Monitoring.Probes;

public sealed record ProbeSettings(string BaseUrl, string User, string Password, string EvidenceDirectory)
{
    public static ProbeSettings FromEnvironment() => new(
        Required("SYNTHETIC_BASE_URL"),
        Required("SYNTHETIC_USER"),
        Required("SYNTHETIC_PASSWORD"),
        Required("SYNTHETIC_EVIDENCE_DIR"));

    public static string Required(string name)
    {
        var value = Environment.GetEnvironmentVariable(name);
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new InvalidOperationException($"Environment variable {name} is not set (synthetic probe configuration)");
        }
        return value;
    }
}
```

The record's generated `ToString()` prints every property, the password included: never log the settings object.

### `ProbeEvidence` — `BaseTest`'s order, kept on failure

```csharp
using Microsoft.Extensions.Logging;
using Microsoft.Playwright;

namespace Monitoring.Probes;

public sealed class ProbeEvidence(ProbeSettings settings, ILogger<ProbeEvidence> logger)
{
    public string RawVideoDirectory => Path.Combine(settings.EvidenceDirectory, "raw-videos");

    public async Task<IReadOnlyList<string>> KeepAsync(string check, IBrowserContext context, IPage page, bool failed, CancellationToken cancellationToken)
    {
        var video = page.Video ?? throw new InvalidOperationException("No video recorded: the probe's context needs RecordVideoDir");
        var name = $"{check}.{DateTimeOffset.UtcNow:yyyyMMddTHHmmssZ}";
        var kept = new List<string>();
        if (failed)
        {
            kept.Add(await KeepTraceAsync(context, name));
            kept.Add(await KeepScreenshotAsync(page, name));
        }
        else
        {
            await context.Tracing.StopAsync();
        }
        await context.CloseAsync();
        if (failed)
        {
            kept.Add(await KeepVideoAsync(video, name));
            logger.LogWarning("Synthetic check {Check} failed; evidence kept: {Evidence}", check, kept);
        }
        await video.DeleteAsync();
        cancellationToken.ThrowIfCancellationRequested();
        return kept;
    }

    private async Task<string> KeepTraceAsync(IBrowserContext context, string name)
    {
        var path = Path.Combine(settings.EvidenceDirectory, $"{name}.zip");
        await context.Tracing.StopAsync(new() { Path = path });
        return path;
    }

    private async Task<string> KeepScreenshotAsync(IPage page, string name)
    {
        var path = Path.Combine(settings.EvidenceDirectory, $"{name}.png");
        await page.ScreenshotAsync(new() { Path = path, FullPage = true });
        return path;
    }

    private async Task<string> KeepVideoAsync(IVideo video, string name)
    {
        var path = Path.Combine(settings.EvidenceDirectory, $"{name}.webm");
        await video.SaveAsAsync(path);
        return path;
    }
}
```

- The order is `BaseTest`'s (`qa/dotnet/skills/ui-test-author/playwright/references/lifecycle.md` §6): the trace
  needs the open context, the screenshot the live page, and the video exists only after the context closes.
- No catch: a screenshot of a crashed page throws, the probe's `finally` records the failed result, and the
  trace is already on the volume.
- The cancellation check comes after the files are complete, so a shutdown never leaves half a video.

### Page objects

The probe references the UI suite's `Pages/` (a project reference to `UiTests`, or a shared page-object
library): `LoginPage` and `LoginPage.Credentials` are `qa/dotnet/skills/ui-test-author/playwright`'s assets;
`CartPage` (`AddFirstFeaturedItemAsync()`, `ItemCount`) is the suite's own page object for the cart.

### `Program.cs` — one run per scheduled execution

```csharp
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Monitoring.Probes;

var builder = Host.CreateApplicationBuilder(args);
builder.Services.AddApplicationInsightsTelemetryWorkerService(options =>
    options.ConnectionString = ProbeSettings.Required("APPLICATIONINSIGHTS_CONNECTION_STRING"));
builder.Services.AddSingleton(ProbeSettings.FromEnvironment());
builder.Services.AddSingleton<ProbeEvidence>();
builder.Services.AddSingleton<CheckoutJourneyProbe>();

using var host = builder.Build();
await host.StartAsync();
var stopping = host.Services.GetRequiredService<IHostApplicationLifetime>().ApplicationStopping;
await host.Services.GetRequiredService<CheckoutJourneyProbe>().RunAsync(ProbeSettings.Required("REGION_NAME"), stopping);
await host.StopAsync();
```

The composition root is the one place services are resolved by type; every class below it takes its
dependencies through the constructor. `ApplicationStopping` fires when the job's container is told to stop.

### `Dockerfile` and the schedule

```dockerfile
FROM mcr.microsoft.com/playwright/dotnet:v1.63.0-noble
WORKDIR /app
COPY publish/ .
ENTRYPOINT ["dotnet", "Monitoring.Probes.dll"]
```

- The image carries the browsers for exactly that Playwright version and a .NET 10 SDK; its tag moves with the
  package version, never ahead of it.
- Run it as an **Azure Container Apps job** with a cron trigger (`*/15 * * * *` — every 15 minutes), one job per
  region (`REGION_NAME`), with the Azure Files share mounted at `SYNTHETIC_EVIDENCE_DIR`.
- A Functions **Premium/Dedicated** plan on a custom container works too, if the image installs the browsers
  (`pwsh bin/Release/net10.0/playwright.ps1 install --with-deps chromium` at build time). A Consumption plan
  cannot launch Chromium at all.

## 4. Secrets from env, never logged

`APPLICATIONINSIGHTS_CONNECTION_STRING`, the target URL and the synthetic user's credentials come from the job's
secrets (Key Vault references), never committed and never logged. In Bicep, webhook URIs and the connection
string are `@secure()` params. The synthetic user is a disposable account with the least privilege the journey
needs — its session is in every kept trace.

## 5. Worked example

`availability.bicep` declares the Standard `storefront-health` test (every 5 min, 30 s timeout, content match)
and the alerts. Two Container Apps jobs (`us`, `emea`) run `Monitoring.Probes` every 15 minutes; each run signs
in through the CI suite's `LoginPage`, adds a featured item and expects the cart badge to read `1`, then pushes a
`checkout-journey` availability result.

One morning the payment provider's script hangs in EMEA. The EMEA probe's `Expect(cart.ItemCount)` times out
with a `PlaywrightException`; the result is `Success = false` with that message, `Duration` 15 s, and an
`evidence` property naming `checkout-journey.20261011T071500Z.{zip,png,webm}` on the share. The availability
alert fires after the 15-minute window; on-call opens the trace (`npx playwright@1.63.0 trace open …` or
trace.playwright.dev), sees the blocked script request, and the US probe staying green confirms it is regional.
