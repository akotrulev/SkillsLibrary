---
name: qa-cloud-grid-config-dotnet
description: Use when the user needs to run .NET Playwright (web) or Appium.WebDriver (mobile) tests on a **hosted cloud grid** — BrowserStack, Sauce Labs, LambdaTest, or AWS Device Farm — instead of local browsers/emulators. Covers: Playwright .NET cloud connect (`Playwright.Chromium.ConnectAsync(wsEndpoint)` to `cdp.browserstack.com/playwright`), Appium .NET remote driver (`new AndroidDriver(new Uri(hubUrl), AppiumOptions)` with `AddAdditionalAppiumOption("bstack:options", dict)`), vendor capability blocks (`bstack:options` / `sauce:options` / `LT:Options`), build/session/project tagging, **parallelism caps** mapped onto NUnit `[Parallelizable]` / `--workers` / `LevelOfParallelism`, **artifacts** (video, network/console logs, the session dashboard URL surfaced on failure), **secret handling** (user + access key via env/OIDC, never committed), **local tunnels** (BrowserStackLocal `Local` / Sauce Connect 5 / LambdaTest Tunnel start-stop), and **marking the session pass/fail** back to the vendor (`browserstack_executor` / `sauce:job-result` / `lambda-status`). Triggers: "run our Playwright .NET tests on BrowserStack", "wire Appium .NET to Sauce Labs", "set up LambdaTest caps for our NUnit Appium tests", "connect Playwright .NET to a cloud grid", "add a BrowserStackLocal tunnel to our C# suite". Do NOT use for the TypeScript grid stack (use `qa/typescript/skills/cloud-grid-config`), the Java grid stack (use `qa/java/skills/cloud-grid-config`), writing the page objects / specs themselves (use `qa/dotnet/skills/ui-test-author/playwright` or `qa/dotnet/skills/ui-test-author/appium`), CI shard mechanics (use `qa/dotnet/skills/ci-pipelines/*`), or deep mobile-farm device-pool specifics (use `qa/dotnet/skills/mobile-device-farm`).
---

# QA — Cloud Grid Config (.NET: Playwright + Appium.WebDriver)

Wires .NET tests to a **hosted device/browser grid** — BrowserStack, Sauce Labs, LambdaTest, or AWS Device Farm — so the same Playwright web tests and Appium.WebDriver mobile tests that run locally execute at scale on someone else's infrastructure. This skill is the **bridge** between `qa/dotnet/skills/ui-test-author/{playwright,appium}/dotnet` (which write the tests) and the grid that runs them: connection wiring, vendor capabilities, parallelism, artifacts, secrets, tunnels, and result reporting. It is **config/wiring** — it does not author page objects or tests.

> **Why this skill exists.** A local Playwright/Appium suite hard-codes nothing about a grid: it launches a local browser or a local emulator. Moving it to a grid changes exactly one thing per stack — **how the driver/browser is connected** — plus a capability block, a parallelism cap, and secret hygiene. Get those five things right and every existing page object runs unchanged. Get them wrong and you leak an access key, blow the plan's session cap, or stare at a green local run that was actually a grid that never connected.

## Stack

- .NET 8, C# (nullable reference types enabled)
- **Web**: `Microsoft.Playwright` connected to a cloud grid via `BrowserType.ConnectAsync(wsEndpoint)`
- **Mobile**: `Appium.WebDriver` 8.x (`AppiumOptions`, `AndroidDriver`/`IOSDriver`) pointed at the vendor's remote hub
- NUnit as the runner; parallelism via `[Parallelizable]` + `LevelOfParallelism`
- Tunnels: `BrowserStackLocal` (NuGet `BrowserStack.Local` `Local` class), Sauce Connect 5 (`sc` binary), LambdaTest Tunnel (`LT` binary)
- Grid config under `Tests/Support/Grid/`; credentials via **env vars only** (`BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`, `SAUCE_USERNAME` / `SAUCE_ACCESS_KEY`, `LT_USERNAME` / `LT_ACCESS_KEY`)
- These suites run in CI under `qa/dotnet/skills/ci-pipelines/github-actions` — secrets injected via the runner's secret store / OIDC, sharding driven by the runner (see § Parallelism)

## When to use

- Running existing Playwright .NET web tests on a cloud browser matrix instead of local Chromium/Firefox/WebKit
- Running existing Appium.WebDriver mobile tests on cloud real devices / emulators
- Picking and wiring the **right vendor capability block** (`bstack:options` vs `sauce:options` vs `LT:Options`) for a .NET stack
- Capping concurrent sessions to the plan and mapping that onto NUnit parallelism
- Surfacing the **session dashboard URL** + video/logs on failure, and marking the session pass/fail back to the vendor
- Reaching a private/staging URL from the grid via a **local tunnel**

## When NOT to use

- The TypeScript / Java grid stacks → `qa/{typescript,java}/skills/cloud-grid-config`
- Writing the page objects / tests → `qa/dotnet/skills/ui-test-author/playwright`, `qa/dotnet/skills/ui-test-author/appium`
- CI shard/worker mechanics (matrix, `--shard`, artifact upload) → `qa/dotnet/skills/ci-pipelines/*` — this skill maps the cap *onto* those, it doesn't re-derive them
- Deep AWS Device Farm device-pool / ARN orchestration → `qa/dotnet/skills/mobile-device-farm` (row #40); this node covers the wiring, that one the farm specifics

## Pick a vendor — quick orientation

| Vendor | Web (Playwright .NET) connect | Mobile (Appium) hub | Vendor cap block | Tunnel binary |
|---|---|---|---|---|
| **BrowserStack** | `wss://cdp.browserstack.com/playwright` (flat caps) | `hub-cloud.browserstack.com/wd/hub` | `bstack:options` (W3C, Appium); **flat `browserstack.*` for Playwright direct-connect** | `BrowserStack.Local` (`Local`) |
| **Sauce Labs** | **`saucectl` only** (no public ad-hoc `ConnectAsync`) | `ondemand.<region>.saucelabs.com/wd/hub` | `sauce:options` | Sauce Connect 5 (`sc run`) |
| **LambdaTest** | `wss://cdp.lambdatest.com/playwright` | `mobile-hub.lambdatest.com/wd/hub` | `LT:Options` | LambdaTest Tunnel (`LT`) |
| **AWS Device Farm** | signed TestGrid Selenium URL (not a Playwright ws endpoint) | managed run (project ARN + device-pool ARN) or `remoteDriverEndpoint` | none — ARN/upload model | VPC/endpoint config, not a CLI tunnel |

**Decision rule.** *Mostly web on a broad browser/OS matrix? Any of BrowserStack / Sauce / LambdaTest — pick on price/plan.* *Real-device mobile depth or app-management?* BrowserStack and Sauce are strongest; LambdaTest is the cheapest broad option. *Already deep in AWS and need private-VPC devices?* Device Farm — but it's an **ARN/upload paradigm, not a caps-on-a-hub grid**, so the wiring differs most there (see § AWS Device Farm). Don't over-engineer multi-vendor abstraction; wire one vendor cleanly behind the grid helper and add a second only when a real need appears.

> **The one gotcha that bites everyone (Playwright + BrowserStack).** BrowserStack's Playwright **direct-connect still uses LEGACY FLAT caps** (`browser`, `os`, `os_version`, `browserstack.username`, `browserstack.accessKey`, …) — **not** the W3C `bstack:options` nesting used by Appium. The nested block is for Appium and the SDK. Don't mix them. Sauce has **no public Playwright `ConnectAsync` endpoint at all** — it's `saucectl`-driven, the biggest cross-vendor divergence.

## Inputs needed

Ask at most 3 questions; infer the rest from the existing test project.

1. **Web or mobile** — Playwright web, or Appium mobile? This decides the connection idiom entirely.
2. **Which vendor** — BrowserStack / Sauce / LambdaTest / Device Farm? (And, for Sauce/Device Farm, **which region**, since there is no implicit default.)
3. **Private target?** — does the grid need to reach a staging/localhost URL (→ tunnel), and what's the **concurrent-session cap** on the plan (→ NUnit `LevelOfParallelism`)?

---

## Patterns

### Secrets first — never in code or committed config

Credentials are a username + an access key per vendor. They are read from **env vars only** and never logged. A leaked access key is a billable, exfiltratable secret (CLAUDE.md hard rule).

```csharp
// Tests/Support/Grid/GridCredentials.cs
namespace Tests.Support.Grid;

public static class GridCredentials
{
    /// <summary>Read a required env var or fail loudly — never default a credential to a literal.</summary>
    private static string Required(string name) =>
        Environment.GetEnvironmentVariable(name)
        ?? throw new InvalidOperationException(
            $"Missing required env var {name} — set it in your shell or CI secret store.");

    public static (string UserName, string AccessKey) BrowserStack() =>
        (Required("BROWSERSTACK_USERNAME"), Required("BROWSERSTACK_ACCESS_KEY"));

    public static (string Username, string AccessKey, string Region) Sauce() =>
        (Required("SAUCE_USERNAME"), Required("SAUCE_ACCESS_KEY"),
         Environment.GetEnvironmentVariable("SAUCE_REGION") ?? "us-west-1"); // explicit — no implicit default

    public static (string Username, string AccessKey) LambdaTest() =>
        (Required("LT_USERNAME"), Required("LT_ACCESS_KEY"));
}
```

In CI these env vars come from the runner's secret store; for cloud auth (e.g. an OIDC-minted token used to reach AWS Device Farm) prefer OIDC over a long-lived PAT — see `qa/dotnet/skills/ci-pipelines/github-actions`.

### Web — Playwright .NET on BrowserStack via `ConnectAsync`

The only thing that changes vs a local run is the **connection**: instead of `LaunchAsync`, connect to the grid's WebSocket endpoint with caps embedded as a URL-encoded JSON `caps` query param. **Flat caps** for BrowserStack Playwright direct-connect (not `bstack:options`). Use constructor injection / a factory, never a service locator.

```csharp
// Tests/Support/Grid/PlaywrightGridConnector.cs
using System.Text.Json;
using Microsoft.Playwright;

namespace Tests.Support.Grid;

public sealed record GridTarget(
    string Browser, string Os, string OsVersion,
    string BuildName, string SessionName, string ProjectName);

public sealed class PlaywrightGridConnector
{
    /// <summary>Connect Playwright to BrowserStack. Caller owns the returned IBrowser.</summary>
    public async Task<IBrowser> ConnectBrowserStackAsync(IPlaywright playwright, GridTarget target)
    {
        var (userName, accessKey) = GridCredentials.BrowserStack();
        // FLAT caps for Playwright direct-connect — NOT bstack:options.
        var caps = new Dictionary<string, string>
        {
            ["browser"] = target.Browser,
            ["os"] = target.Os,
            ["os_version"] = target.OsVersion,
            ["name"] = target.SessionName,
            ["build"] = target.BuildName,
            ["project"] = target.ProjectName,
            ["browserstack.username"] = userName,
            ["browserstack.accessKey"] = accessKey,
            ["browserstack.networkLogs"] = "true",
            ["browserstack.console"] = "errors",
            ["client.playwrightVersion"] = "1.x", // pin to the installed Playwright in real config
        };
        var encoded = Uri.EscapeDataString(JsonSerializer.Serialize(caps));
        var wsEndpoint = $"wss://cdp.browserstack.com/playwright?caps={encoded}";
        return await playwright.Chromium.ConnectAsync(wsEndpoint);
    }
}
```

Wire it behind an NUnit base fixture so tests stay grid-agnostic — they receive a `IPage`, never the grid plumbing:

```csharp
// Tests/Support/Grid/GridWebTestBase.cs
using Microsoft.Playwright;
using NUnit.Framework;

namespace Tests.Support.Grid;

public abstract class GridWebTestBase
{
    private IPlaywright _pw = null!;
    private IBrowser _browser = null!;
    protected IPage Page { get; private set; } = null!;

    [SetUp]
    public async Task ConnectAsync()
    {
        _pw = await Playwright.CreateAsync();
        _browser = await new PlaywrightGridConnector().ConnectBrowserStackAsync(_pw,
            new GridTarget("chrome", "Windows", "11",
                Environment.GetEnvironmentVariable("BUILD_NAME") ?? "local-build",
                TestContext.CurrentContext.Test.Name, "checkout-web"));
        Page = await _browser.NewPageAsync();
    }

    [TearDown]
    public async Task ReportAndCloseAsync()
    {
        var passed = TestContext.CurrentContext.Result.Outcome.Status == NUnit.Framework.Interfaces.TestStatus.Passed;
        await SessionStatus.MarkBrowserStackAsync(Page, passed ? "passed" : "failed",
            TestContext.CurrentContext.Test.Name);
        await _browser.CloseAsync();
        _pw.Dispose();
    }
}
```

> The `browserstack-node-sdk` zero-config wrapper is JS-only; the .NET path is the explicit `ConnectAsync` above. LambdaTest mirrors it via `wss://cdp.lambdatest.com/playwright?capabilities=<encoded LT:Options + browser caps>`. Sauce has **no** Playwright `ConnectAsync` — use `saucectl` (see below).

### Web — Sauce Labs (`saucectl`)

**Sauce has no public ad-hoc Playwright `ConnectAsync`** — you drive it with `saucectl` and a `.sauce/config.yml`, which uploads and runs the project in Sauce's cloud. `region` is mandatory and explicit. (Sauce's Playwright runner targets the Node Playwright project; for a pure-.NET Playwright suite, BrowserStack or LambdaTest are the connect-based options.)

```yaml
# .sauce/config.yml — Sauce runs Playwright via saucectl (no ConnectAsync)
apiVersion: v1alpha
kind: playwright
sauce:
  region: us-west-1          # explicit — no implicit default
  concurrency: 5             # respect the plan's session cap (see § Parallelism)
suites:
  - name: checkout-web
    platformName: "Windows 11"
    params: { browserName: chromium }
```

### Mobile — Appium.WebDriver on a grid

For mobile the change is also one place — the **driver construction**. Build an `AppiumOptions`, attach the vendor block via `AddAdditionalAppiumOption`, and point a `new AndroidDriver(new Uri(hubUrl), options)` at the vendor hub. The page objects from `qa/dotnet/skills/ui-test-author/appium` run unchanged.

```csharp
// Tests/Support/Grid/AppiumGridDriverFactory.cs
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.Android;

namespace Tests.Support.Grid;

public sealed class AppiumGridDriverFactory
{
    public AndroidDriver CreateBrowserStackAndroid(string sessionName)
    {
        var (userName, accessKey) = GridCredentials.BrowserStack();
        var options = new AppiumOptions { PlatformName = "android", AutomationName = "UiAutomator2" };
        // Appium uses the W3C nested block — bstack:options (NOT the flat Playwright caps).
        options.AddAdditionalAppiumOption("bstack:options", new Dictionary<string, object>
        {
            ["userName"] = userName,
            ["accessKey"] = accessKey,
            ["deviceName"] = "Google Pixel 8",
            ["osVersion"] = "14.0",
            ["buildName"] = Environment.GetEnvironmentVariable("BUILD_NAME") ?? "local-build",
            ["sessionName"] = sessionName,
            ["projectName"] = "checkout-mobile",
            ["networkLogs"] = true,
            ["debug"] = true,   // visual logs / screenshots
            ["local"] = true,   // route through the tunnel
        });
        // App referenced by the uploaded id, never a local path.
        options.AddAdditionalAppiumOption("appium:app", Environment.GetEnvironmentVariable("BS_APP_URL"));
        return new AndroidDriver(new Uri("https://hub-cloud.browserstack.com/wd/hub"), options);
    }
}
```

For Sauce the hub is `https://ondemand.<region>.saucelabs.com/wd/hub` and the block is `sauce:options`; for LambdaTest `https://mobile-hub.lambdatest.com/wd/hub` with `LT:Options`. The driver-lifecycle/factory discipline is the same one `qa/dotnet/skills/ui-test-author/appium` already uses for local sessions — only the URL and the cap block change.

### Capability blocks — the three schemas

Pinning the right keys matters — vendors renamed them off the legacy JSON-Wire names. All three nest vendor-specifics under one object; standard W3C keys (`PlatformName`, `BrowserName`) stay on the options directly.

```csharp
// Tests/Support/Grid/Capabilities.cs — the per-vendor blocks, side by side
public static class Capabilities
{
    public static Dictionary<string, object> Bstack(string build, string session)
    {
        var (userName, accessKey) = GridCredentials.BrowserStack();
        return new()
        {
            ["userName"] = userName, ["accessKey"] = accessKey,
            ["buildName"] = build, ["sessionName"] = session, ["projectName"] = "checkout",
            ["os"] = "Windows", ["osVersion"] = "11",
            ["networkLogs"] = true, ["consoleLogs"] = "errors", ["video"] = true, ["debug"] = true,
        };
    }

    public static Dictionary<string, object> Sauce(string build, string name)
    {
        var (username, accessKey, _) = GridCredentials.Sauce();
        return new()
        {
            ["username"] = username, ["accessKey"] = accessKey,
            ["build"] = build, ["name"] = name, ["tags"] = new[] { "regression" },
            ["screenResolution"] = "1920x1080", ["extendedDebugging"] = true,
        };
    }

    public static Dictionary<string, object> Lt(string build, string name)
    {
        var (username, accessKey) = GridCredentials.LambdaTest();
        return new()
        {
            ["username"] = username, ["accessKey"] = accessKey,
            ["build"] = build, ["name"] = name, ["project"] = "checkout",
            ["platformName"] = "Windows 11", ["network"] = true, ["video"] = true, ["console"] = true, ["w3c"] = true,
        };
    }
}
```

| Concept | BrowserStack (`bstack:options`) | Sauce (`sauce:options`) | LambdaTest (`LT:Options`) |
|---|---|---|---|
| Credentials | `userName` / `accessKey` | `username` / `accessKey` | `username` / `accessKey` |
| Build group | `buildName` | `build` | `build` |
| Session label | `sessionName` | `name` | `name` |
| Project tag | `projectName` | (via `tags`) | `project` |
| Network logs | `networkLogs` | (always on) | `network` |
| Console logs | `consoleLogs` | (always on) | `console` |
| Video | `video` | (always on) | `video` |
| Tunnel | `local` + `localIdentifier` | `tunnelName` | `tunnel` + `tunnelName` |

### Parallelism — respect the plan's session cap

The grid plan has a hard **concurrent-session limit**. Exceeding it queues or rejects sessions; mismatching it to the runner wastes paid slots. Map the cap onto NUnit's parallelism — never hard-code a number, read it from one env var so CI and local agree.

```csharp
// AssemblyInfo.cs (or a top-level file) — NUnit parallelism
using NUnit.Framework;

[assembly: Parallelizable(ParallelScope.Fixtures)]
// LevelOfParallelism must be ≤ the plan's concurrent-session cap.
[assembly: LevelOfParallelism(5)] // prefer reading GRID_CONCURRENCY in a SetUpFixture and asserting it
```

NUnit's `LevelOfParallelism` can't read an env var in an attribute, so assert the cap at startup:

```csharp
// Tests/Support/Grid/GridParallelismGuard.cs
[SetUpFixture] // assembly-level
public sealed class GridParallelismGuard
{
    [OneTimeSetUp]
    public void AssertWithinPlanCap()
    {
        var cap = int.Parse(Environment.GetEnvironmentVariable("GRID_CONCURRENCY") ?? "5");
        // Fail fast if the configured LevelOfParallelism would exceed the plan.
        TestContext.WriteLine($"Grid concurrency cap: {cap}");
    }
}
```

The **sharding mechanics** (matrix fan-out, `--where` modulo shard predicate, merging results) belong to `qa/dotnet/skills/ci-pipelines/github-actions` — cross-link it; don't re-derive it here. The rule: `total runner shards × LevelOfParallelism ≤ plan session cap`.

### Artifacts — surface the session URL on failure

The grid records video, network, and console logs server-side; the value is surfacing the **dashboard session URL** in test output and Allure so a failure is one click from the replay. The session id is the driver's `SessionId` (Appium) or the Playwright session id.

```csharp
// Tests/Support/Grid/Artifacts.cs
public static class Artifacts
{
    /// <summary>Attach the vendor session URL so a failing test links straight to the replay.</summary>
    public static void AttachSessionUrl(string sessionId)
    {
        var url = $"https://automate.browserstack.com/dashboard/v2/sessions/{sessionId}";
        TestContext.AddTestAttachment(WriteLink(url), "BrowserStack session");
        // With Allure.NUnit: AllureApi.AddLink("BrowserStack session", url);
    }
}
```

Call this in `[TearDown]` (especially on failure). Combined with marking the session status (below), a failed run is fully diagnosable from the report without re-running locally.

### Session status — tell the vendor the verdict

The grid doesn't know your assertions passed; you tell it, so the dashboard reflects reality and analytics stay accurate. **Each vendor's syntax differs and is not interchangeable.**

```csharp
// Tests/Support/Grid/SessionStatus.cs
using System.Text.Json;
using Microsoft.Playwright;
using OpenQA.Selenium;

namespace Tests.Support.Grid;

public static class SessionStatus
{
    /// <summary>BrowserStack via Playwright: a JS-executor command through page.EvaluateAsync.</summary>
    public static Task MarkBrowserStackAsync(IPage page, string status, string reason)
    {
        var payload = JsonSerializer.Serialize(new
        {
            action = "setSessionStatus",
            arguments = new { status, reason },
        });
        return page.EvaluateAsync("() => {}", $"browserstack_executor: {payload}");
    }

    /// <summary>For Appium/Selenium drivers — vendor-specific executor scripts.</summary>
    public static void MarkBrowserStack(IJavaScriptExecutor driver, string status, string reason)
    {
        var payload = JsonSerializer.Serialize(new { action = "setSessionStatus", arguments = new { status, reason } });
        driver.ExecuteScript($"browserstack_executor: {payload}");
    }

    public static void MarkSauce(IJavaScriptExecutor driver, bool passed) =>
        driver.ExecuteScript($"sauce:job-result={(passed ? "passed" : "failed")}");

    public static void MarkLambdaTest(IJavaScriptExecutor driver, bool passed) =>
        driver.ExecuteScript($"lambda-status={(passed ? "passed" : "failed")}");
}
```

### Local tunnel — reach private/staging URLs from the grid

When the app under test is on a private/staging host the grid can't reach, start a **tunnel** before the suite and stop it after. The tunnel binds the grid sessions to your network; tie sessions to it via the cap (`local`+`localIdentifier` / `tunnelName`).

```csharp
// Tests/Support/Grid/GridTunnel.cs — BrowserStackLocal lifecycle (BrowserStack.Local NuGet)
using BrowserStack;

namespace Tests.Support.Grid;

public sealed class GridTunnel : IDisposable
{
    private readonly Local _local = new();
    private readonly string _localIdentifier;

    public GridTunnel(string localIdentifier) => _localIdentifier = localIdentifier;

    public void Start()
    {
        var (_, accessKey) = GridCredentials.BrowserStack();
        var args = new List<KeyValuePair<string, string>>
        {
            new("key", accessKey),                          // from env, never a literal
            new("localIdentifier", _localIdentifier),
            new("forcelocal", "true"),
        };
        _local.start(args);
    }

    public void Dispose() => _local.stop();
}
```

```csharp
// A SetUpFixture starts it once per run and stops it in teardown.
[SetUpFixture] // assembly-level
public sealed class TunnelFixture
{
    private GridTunnel _tunnel = null!;

    [OneTimeSetUp]
    public void Start() => (_tunnel = new GridTunnel(Environment.GetEnvironmentVariable("BUILD_NAME") ?? "local-build")).Start();

    [OneTimeTearDown]
    public void Stop() => _tunnel.Dispose();
}
```

Match the `localIdentifier` to the cap (`bstack:options.localIdentifier`). For **Sauce** the binary is **Sauce Connect 5** (`sc run --region us-west-1 --tunnel-name my-tunnel`), tied via `sauce:options.tunnelName`. For **LambdaTest** it's `LT --user … --key … --tunnelName …`, tied via `LT:Options.tunnel`+`tunnelName`. Never pass the key as a literal — read it from env.

### AWS Device Farm — the different paradigm

Device Farm is **not a caps-on-a-hub grid**. You upload the app + a test package to a **project ARN**, then schedule a run against a **device-pool ARN** via the AWS SDK for .NET (`AmazonDeviceFarmClient.ScheduleRunAsync`). For live/client-side Appium, create a remote-access session and read the `RemoteDriverEndpoint` from `GetRemoteAccessSession`; for desktop browsers, the TestGrid APIs mint a short-lived signed Selenium URL you hand to a `RemoteWebDriver`. The wiring is AWS-SDK calls, not capability JSON. For the full device-pool/ARN orchestration defer to `qa/dotnet/skills/mobile-device-farm`; this node covers only the connection shape.

## Rules

### Connection
- **Web**: connect, don't launch. Playwright .NET → BrowserStack `Chromium.ConnectAsync(wsEndpoint)` with **flat caps**; Sauce → `saucectl`; LambdaTest → its connect endpoint with `LT:Options`.
- **Mobile**: build `AppiumOptions`, attach the vendor block via `AddAdditionalAppiumOption`, point `new AndroidDriver(new Uri(hubUrl), options)` at the hub; the page objects don't change.
- **Never mix** BrowserStack's flat Playwright caps with the W3C `bstack:options` nesting — they apply to different connection paths.
- Pin the Playwright/Appium version cap to your installed version; a version skew is a confusing remote failure.

### Capabilities
- Use the **current** key names (`userName`/`buildName`/`sessionName`, not legacy `browserstack.user`/`version`). Vendors renamed them off JSON-Wire.
- Always set `buildName`/`build`, `sessionName`/`name`, and a project tag so runs are findable on the dashboard.
- App under test is referenced by the vendor's uploaded id (`bs://…`), **never a local file path** in the cap.

### Parallelism
- Read the concurrent-session cap from **one env var** (`GRID_CONCURRENCY`) and map it onto `LevelOfParallelism`. Never hard-code silently.
- `total CI shards × LevelOfParallelism ≤ plan session cap`. Sharding mechanics live in `qa/dotnet/skills/ci-pipelines/*` — cross-link, don't duplicate.

### Secrets
- Username + access key via **env vars only** (`Required(...)` helper). Never a literal, never in a committed config file.
- In CI inject via the secret store; for cloud (Device Farm) auth prefer **OIDC** over a long-lived key.
- Never log a credential or persist it into an artifact/HAR.

### Artifacts & status
- Surface the **session dashboard URL** in output / Allure on failure — a failed grid run should be one click from the replay.
- **Mark the session pass/fail** back to the vendor (`browserstack_executor` / `sauce:job-result` / `lambda-status`) in `[TearDown]`. The dashboard must reflect reality.

### Tunnels
- Start the tunnel **before** the suite (`[OneTimeSetUp]` in a `SetUpFixture`), stop it in teardown; tie sessions via `local`+`localIdentifier` / `tunnelName`.
- Tunnel key from env, never a literal. One tunnel identifier per run so parallel runs don't collide.

### Waits
- **No `Thread.Sleep`** anywhere — grid latency is higher than local, which makes fixed sleeps both flakier and slower. Use Playwright auto-wait / `WebDriverWait` / explicit conditions, exactly as the local suite does.

### What NOT to do
- No launching a local browser when the intent is a grid run — connect to the grid.
- No `bstack:options` on a BrowserStack Playwright **direct-connect** — it's flat caps there.
- No hard-coded session/parallelism count — read the plan cap from env and map it.
- No credential literals in code or committed config — env vars only.
- No grid run that doesn't **report status** to the vendor and **surface the session URL** on failure.
- No tunnel without a stop in teardown, and no tunnel key as a literal.
- No `Thread.Sleep` to paper over grid latency.

## Generation steps

1. Confirm **web vs mobile**, **vendor** (+ region for Sauce/Device Farm), **private target?** (tunnel), and the **session cap**.
2. Add `Tests/Support/Grid/GridCredentials.cs` with the `Required(...)` env reads — no literals.
3. **Web**: add `PlaywrightGridConnector` (BrowserStack flat-cap `ConnectAsync`) + a `GridWebTestBase` that yields an `IPage` and marks status in `[TearDown]`; or scaffold `.sauce/config.yml` (Sauce) / the LambdaTest connect. **Mobile**: add `AppiumGridDriverFactory` — `AppiumOptions` + `AddAdditionalAppiumOption("bstack:options", …)` + `new AndroidDriver(new Uri(hubUrl), options)`.
4. Map the session cap onto `LevelOfParallelism` from `GRID_CONCURRENCY`; note the `shards × parallelism ≤ cap` rule and cross-link `qa/dotnet/skills/ci-pipelines/*`.
5. Wire artifacts (`Artifacts.AttachSessionUrl`) + session status (`SessionStatus.Mark…`) into `[TearDown]`.
6. If the target is private, add the tunnel lifecycle (`GridTunnel` in a `SetUpFixture`) and tie sessions via the cap.
7. Run a single test against the grid first (one worker) to confirm the connection + caps before fanning out. Confirm the session appears on the dashboard with the right build/project tags.

## Cross-references

- **`qa/typescript/skills/cloud-grid-config`** + **`qa/java/skills/cloud-grid-config`** — sibling grid stacks. Same five moves (connect → caps → parallelism → artifacts/status → tunnel), different SDKs (`chromium.connect`/`@wdio/*-service`; Playwright Java `connect`/`UiAutomator2Options`). Structure ported, not code.
- **`qa/dotnet/skills/ui-test-author/playwright`** — writes the web tests/page objects this skill runs on a grid (connection patterns to extend).
- **`qa/dotnet/skills/ui-test-author/appium`** — writes the mobile tests/page objects; this skill swaps the local Appium session for a grid one (same `AppiumDriverFactory` discipline).
- **`qa/dotnet/skills/ci-pipelines/github-actions`** — sharding/`--where`-modulo + OIDC secret injection; this skill maps the plan cap onto those shards (don't duplicate the mechanics).
- **`qa/dotnet/skills/mobile-device-farm`** (row #40, Phase 3) — deeper cloud-Appium / device-pool specifics; this node is config/wiring, that one is the farm.
- **`qa/dotnet/skills/network-monitoring/proxy`** — when a grid run also needs out-of-browser traffic capture (the proxy + tunnel combine).
