# Deep-dive details — `qa-dotnet:browser-cloud-setup`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Patterns

### Secrets first — never in code or committed config

Credentials are a username + an access key per vendor, read from **env vars only** and never logged. A leaked
access key is a billable, exfiltratable secret (CLAUDE.md hard rule). The build name is required too: a
defaulted build name files every local run under one dashboard build.

```csharp
namespace Example.UiTests.Support.Grid;

public static class GridCredentials
{
    public static string Required(string name)
    {
        var value = Environment.GetEnvironmentVariable(name);
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new InvalidOperationException($"Environment variable {name} is not set (cloud grid credentials)");
        }
        return value;
    }

    public static string BuildName() => Required("BUILD_NAME");

    public static (string UserName, string AccessKey) BrowserStack() =>
        (Required("BROWSERSTACK_USERNAME"), Required("BROWSERSTACK_ACCESS_KEY"));

    public static (string UserName, string AccessKey, string Region) Sauce() =>
        (Required("SAUCE_USERNAME"), Required("SAUCE_ACCESS_KEY"), Required("SAUCE_REGION"));

    public static (string UserName, string AccessKey) LambdaTest() =>
        (Required("LT_USERNAME"), Required("LT_ACCESS_KEY"));
}
```

In CI these come from the runner's secret store; for cloud auth (an OIDC-minted token reaching AWS Device Farm)
prefer OIDC over a long-lived key — `qa/cicd/dotnet/skills/ci-pipelines`.

### Web — Playwright .NET on BrowserStack through `ConnectOptionsAsync()`

`BrowserTest.ConnectOptionsAsync()` returns `null` by default, and `BrowserTest` launches from the
runsettings. A grid fixture returns `(wsEndpoint, options)` instead, and `BrowserTest` connects with
`BrowserType.ConnectAsync(wsEndpoint, options)` — once per NUnit worker (SKILL.md, "How a Playwright .NET suite
reaches a grid"). The caps travel URL-encoded in the endpoint, **flat** for BrowserStack's Playwright
direct-connect.

```csharp
using System.Text.Json;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.UiTests.Support.Grid;

public static class GridConnection
{
    public static (string, BrowserTypeConnectOptions?)? BrowserStack(string browser, string os, string osVersion)
    {
        var (userName, accessKey) = GridCredentials.BrowserStack();
        var caps = new Dictionary<string, string>
        {
            ["browser"] = browser,
            ["os"] = os,
            ["os_version"] = osVersion,
            ["build"] = GridCredentials.BuildName(),
            ["name"] = $"{GridCredentials.BuildName()} {TestContext.CurrentContext.WorkerId}",
            ["project"] = "checkout-web",
            ["browserstack.username"] = userName,
            ["browserstack.accessKey"] = accessKey,
            ["browserstack.networkLogs"] = "true",
            ["browserstack.console"] = "errors",
            ["client.playwrightVersion"] = InstalledPlaywrightVersion(),
        };
        return ($"wss://cdp.browserstack.com/playwright?caps={Uri.EscapeDataString(JsonSerializer.Serialize(caps))}", null);
    }

    private static string InstalledPlaywrightVersion() =>
        typeof(IPlaywright).Assembly.GetName().Version?.ToString(3)
        ?? throw new InvalidOperationException("The loaded Microsoft.Playwright assembly carries no version");
}
```

- **The session is the worker's**, so its name is the build plus NUnit's worker id, not a test name.
- **The version** is the loaded assembly's — the package the project actually restored, never a literal that
  drifts from it.
- **The browser** connects through the runsettings `BrowserName` (Chromium by default), which is what
  BrowserStack's Chrome and Edge targets expect.

A grid fixture reruns an existing test class on the grid. It sits in `Example.UiTests.Grid`, carries the
`grid` category, and adds nothing but the connection and the verdict:

```csharp
using Example.UiTests.Support.Grid;
using Example.UiTests.Tests;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.UiTests.Grid;

[Category("grid")]
public class CheckoutTestsOnBrowserStack : CheckoutTests
{
    public override Task<(string, BrowserTypeConnectOptions?)?> ConnectOptionsAsync() =>
        Task.FromResult(GridConnection.BrowserStack("chrome", "Windows", "11"));

    [TearDown]
    public async Task ReportSessionAsync() => await GridSession.ReportAsync(Page);
}
```

- NUnit runs the inherited tests again in this fixture. Its `[TearDown]` runs **before** `BaseTest`'s, so the
  page is still open for the executor calls.
- **Every fixture in a grid run overrides `ConnectOptionsAsync()`**, because the first fixture on a worker
  decides that worker's browser. That is why the grid run is `--filter TestCategory=grid` and the local run
  excludes the category.
- `BaseTest`'s trace, screenshot and video come back from the remote browser through Playwright's artifact
  channel (`SaveAsAsync`, never `PathAsync`, which a connected browser cannot answer).

LambdaTest mirrors this with `wss://cdp.lambdatest.com/playwright?capabilities=<encoded LT:Options + browser caps>`.

### Session status and the dashboard link — `GridSession`

The grid doesn't know your assertions passed. Each vendor's syntax differs and is not interchangeable.

```csharp
using System.Text.Json;
using Allure.Net.Commons;
using Microsoft.Playwright;
using NUnit.Framework;
using NUnit.Framework.Interfaces;

namespace Example.UiTests.Support.Grid;

public static class GridSession
{
    public static async Task ReportAsync(IPage page)
    {
        var failed = TestContext.CurrentContext.Result.Outcome.Status == TestStatus.Failed;
        var verdict = JsonSerializer.Serialize(new
        {
            action = "setSessionStatus",
            arguments = new { status = failed ? "failed" : "passed", reason = TestContext.CurrentContext.Test.FullName },
        });
        await page.EvaluateAsync("_ => {}", $"browserstack_executor: {verdict}");
        if (failed)
        {
            var details = await page.EvaluateAsync<string>("_ => {}", """browserstack_executor: {"action": "getSessionDetails"}""");
            var url = JsonDocument.Parse(details).RootElement.GetProperty("browser_url").GetString()
                ?? throw new InvalidOperationException($"BrowserStack session details carry no browser_url: {details}");
            AllureApi.AddLink("BrowserStack session", url);
            TestContext.Out.WriteLine("BrowserStack session: {0}", url);
        }
    }
}
```

- The verdict is marked per test, and the session's last mark wins. That is right here because a failed test
  ends its session (the worker disposes the browser), so a session's only failure is always its last mark.
- The link goes to Allure and to the test output (TRX `StdOut`), on failure only.
- `getSessionDetails` and its `browser_url` field are BrowserStack's executor spellings; check one failed run's
  link before relying on them.

For Appium/Selenium drivers the same verdicts are executor scripts:

```csharp
using System.Text.Json;
using OpenQA.Selenium;

namespace Example.UiTests.Support.Grid;

public static class DriverSessionStatus
{
    public static void MarkBrowserStack(IJavaScriptExecutor driver, bool passed, string reason) =>
        driver.ExecuteScript($"browserstack_executor: {JsonSerializer.Serialize(new { action = "setSessionStatus", arguments = new { status = passed ? "passed" : "failed", reason } })}");

    public static void MarkSauce(IJavaScriptExecutor driver, bool passed) =>
        driver.ExecuteScript($"sauce:job-result={(passed ? "passed" : "failed")}");

    public static void MarkLambdaTest(IJavaScriptExecutor driver, bool passed) =>
        driver.ExecuteScript($"lambda-status={(passed ? "passed" : "failed")}");
}
```

### Web — Sauce Labs (`saucectl`)

**Sauce has no public ad-hoc Playwright connect endpoint** — you drive it with `saucectl` and a
`.sauce/config.yml`, which uploads and runs the project in Sauce's cloud. `region` is mandatory and explicit.
Sauce's Playwright runner targets the Node Playwright project; for a pure-.NET Playwright suite, BrowserStack or
LambdaTest are the connect-based options.

```yaml
apiVersion: v1alpha
kind: playwright
sauce:
  region: us-west-1
  concurrency: 5
suites:
  - name: checkout-web
    platformName: "Windows 11"
    params: { browserName: chromium }
```

`concurrency` is the plan's session cap, like `GRID_CONCURRENCY` for the connect-based vendors.

### Mobile — Appium.WebDriver on a grid

For mobile the change is also one place — the **driver construction**. Build an `AppiumOptions`, attach the
vendor block via `AddAdditionalAppiumOption`, and point `new AndroidDriver(new Uri(hubUrl), options)` at the
vendor hub. Appium uses the W3C nested block (`bstack:options`), never the flat Playwright caps; the app is the
uploaded id, never a local path. The page objects from `qa/dotnet/skills/ui-test-author/appium` run unchanged.

```csharp
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.Android;

namespace Example.MobileTests.Support.Grid;

public sealed class AppiumGridDriverFactory
{
    public AndroidDriver CreateBrowserStackAndroid(string sessionName)
    {
        var (userName, accessKey) = GridCredentials.BrowserStack();
        var options = new AppiumOptions { PlatformName = "android", AutomationName = "UiAutomator2" };
        options.AddAdditionalAppiumOption("bstack:options", new Dictionary<string, object>
        {
            ["userName"] = userName,
            ["accessKey"] = accessKey,
            ["deviceName"] = "Google Pixel 8",
            ["osVersion"] = "14.0",
            ["buildName"] = GridCredentials.BuildName(),
            ["sessionName"] = sessionName,
            ["projectName"] = "checkout-mobile",
            ["networkLogs"] = true,
            ["debug"] = true,
            ["local"] = true,
        });
        options.AddAdditionalAppiumOption("appium:app", GridCredentials.Required("BS_APP_URL"));
        return new AndroidDriver(new Uri("https://hub-cloud.browserstack.com/wd/hub"), options);
    }
}
```

The mobile project carries the same `GridCredentials` in its own `Support/Grid/`. `debug` turns on the vendor's
visual logs; `local` routes the session through the tunnel. For Sauce the hub is
`https://ondemand.<region>.saucelabs.com/wd/hub` and the block is `sauce:options`; for LambdaTest
`https://mobile-hub.lambdatest.com/wd/hub` with `LT:Options`. The driver-lifecycle discipline is the one
`qa/dotnet/skills/ui-test-author/appium` already uses for local sessions — only the URL and the cap block change.

### Capability blocks — the three schemas

All three nest vendor specifics under one object; standard W3C keys (`PlatformName`, `BrowserName`) stay on
the options directly.

```csharp
namespace Example.MobileTests.Support.Grid;

public static class Capabilities
{
    public static Dictionary<string, object> Bstack(string session)
    {
        var (userName, accessKey) = GridCredentials.BrowserStack();
        return new()
        {
            ["userName"] = userName, ["accessKey"] = accessKey,
            ["buildName"] = GridCredentials.BuildName(), ["sessionName"] = session, ["projectName"] = "checkout",
            ["os"] = "Windows", ["osVersion"] = "11",
            ["networkLogs"] = true, ["consoleLogs"] = "errors", ["video"] = true, ["debug"] = true,
        };
    }

    public static Dictionary<string, object> Sauce(string name)
    {
        var (userName, accessKey, _) = GridCredentials.Sauce();
        return new()
        {
            ["username"] = userName, ["accessKey"] = accessKey,
            ["build"] = GridCredentials.BuildName(), ["name"] = name, ["tags"] = new[] { "regression" },
            ["screenResolution"] = "1920x1080", ["extendedDebugging"] = true,
        };
    }

    public static Dictionary<string, object> Lt(string name)
    {
        var (userName, accessKey) = GridCredentials.LambdaTest();
        return new()
        {
            ["username"] = userName, ["accessKey"] = accessKey,
            ["build"] = GridCredentials.BuildName(), ["name"] = name, ["project"] = "checkout",
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

The plan has a hard **concurrent-session limit**: exceeding it queues or rejects sessions, undershooting it
wastes paid slots. A Playwright grid run holds **one session per NUnit worker**, so the cap is the worker
count, passed on the command line from one env var so CI and local agree:

```bash
dotnet test UiTests --filter "TestCategory=grid" -- NUnit.NumberOfTestWorkers=$GRID_CONCURRENCY
```

- An assembly `[LevelOfParallelism(5)]` attribute cannot read the variable, and a `[SetUpFixture]` that only
  prints the cap guards nothing — the run argument is the guard.
- `BaseTest`'s `ParallelScope.Self` stays: fixtures run in parallel, a fixture's tests share its page.
- Sharding (class filters computed once, `ci/nunit-shards.sh`) belongs to `qa/cicd/dotnet/skills/ci-pipelines`.
  The rule: `shards × NUnit.NumberOfTestWorkers ≤ plan session cap`.
- Appium grid suites own one driver per fixture; the same worker argument caps them.

### Local tunnel — reach private/staging URLs from the grid

When the app under test is on a private/staging host the grid can't reach, start a **tunnel** before the grid
fixtures and stop it after. Tie sessions to it via the cap (`local` + `localIdentifier` / `tunnelName`).

```csharp
using BrowserStack;

namespace Example.UiTests.Support.Grid;

public sealed class GridTunnel(string localIdentifier) : IDisposable
{
    private readonly Local _local = new();

    public void Start()
    {
        var (_, accessKey) = GridCredentials.BrowserStack();
        _local.start(new List<KeyValuePair<string, string>>
        {
            new("key", accessKey),
            new("localIdentifier", localIdentifier),
            new("forcelocal", "true"),
        });
    }

    public void Dispose() => _local.stop();
}
```

```csharp
using Example.UiTests.Support.Grid;
using NUnit.Framework;

namespace Example.UiTests.Grid;

[SetUpFixture]
public sealed class GridTunnelSetup
{
    private GridTunnel _tunnel = null!;

    [OneTimeSetUp]
    public void StartTunnel()
    {
        _tunnel = new GridTunnel(GridCredentials.BuildName());
        _tunnel.Start();
    }

    [OneTimeTearDown]
    public void StopTunnel() => _tunnel.Dispose();
}
```

- NUnit scopes a `[SetUpFixture]` to its namespace, so this one runs only when a fixture in
  `Example.UiTests.Grid` runs — the local run never opens a tunnel.
- Match the `localIdentifier` to the caps (`browserstack.localIdentifier` on the flat Playwright caps,
  `bstack:options.localIdentifier` for Appium). For **Sauce** the binary is **Sauce Connect 5**
  (`sc run --region us-west-1 --tunnel-name <build>`), tied via `sauce:options.tunnelName`; for **LambdaTest**,
  `LT --user … --key … --tunnelName …`, tied via `LT:Options.tunnel` + `tunnelName`. Keys from env, never literals.

### AWS Device Farm — the different paradigm

Device Farm is **not a caps-on-a-hub grid**. You upload the app + a test package to a **project ARN**, then
schedule a run against a **device-pool ARN** via the AWS SDK for .NET (`AmazonDeviceFarmClient.ScheduleRunAsync`).
For live Appium, create a remote-access session and read the `RemoteDriverEndpoint` from
`GetRemoteAccessSession`; for desktop browsers, the TestGrid APIs mint a short-lived signed Selenium URL you hand
to a `RemoteWebDriver`. The wiring is AWS-SDK calls, not capability JSON. For the device-pool/ARN orchestration
defer to `qa/dotnet/skills/device-cloud`; this node covers only the connection shape.
