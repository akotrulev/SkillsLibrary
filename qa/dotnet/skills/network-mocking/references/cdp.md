# QA — Chrome DevTools Protocol Hooks (.NET 10 / Microsoft.Playwright 1.63 + NUnit)

Drives the raw **Chrome DevTools Protocol** from a Playwright for .NET test through
`Page.Context.NewCDPSessionAsync(Page)`, for the hooks that live **below the routing layer**: real bandwidth and
latency throttling, HTTP-cache disable, CPU throttling and `Performance` metrics. The session and every
command and event are wrapped in one `CdpControls` helper with intent names (`ThrottleAsync`,
`DisableCacheAsync`, `CpuThrottleAsync`, `MetricsAsync`, `NextResponseAsync`) — never
`SendAsync("Domain.method", …)` in a test. Every sample derives from `Example.UiTests.Support.BaseTest`; there is
no `Task.Delay`, `Thread.Sleep` or `WaitForTimeoutAsync` in this file.

The .NET binding, checked against playwright-dotnet v1.63.0 (`ICDPSession.cs`, `ICDPSessionEvent.cs`):

| Member | Shape |
|---|---|
| `ICDPSession.SendAsync(string method, Dictionary<string, object>? args = null)` | Returns `Task<JsonElement?>` |
| `ICDPSession.Event(string eventName)` | Returns the one `ICDPSessionEvent` for that name |
| `ICDPSessionEvent.OnEvent` | `event EventHandler<JsonElement?>` — the payload is **nullable**: read it as `payload!.Value.GetProperty(...)`, never `payload.GetProperty(...)` (CS1061) |
| `ICDPSession.DetachAsync()` | Ends the session early; not needed when the context closes |

> **Chromium only.** `NewCDPSessionAsync` throws on Firefox and WebKit. That is the price of dropping below
> routing. Anything that must run cross-browser stays in `references/playwright-routes.md` — including security
> headers and TLS details, which `IResponse.AllHeadersAsync()` and `SecurityDetailsAsync()` cover there.

## When to use

- A **real** slow connection (Slow or Fast 3G throughput and latency) to test loading, skeleton and timeout
  states — when the page must load *slowly*, not merely *not yet* (a held request covers that,
  `references/playwright-routes.md` §8).
- Every request must **miss the HTTP cache** (`Network.setCacheDisabled`) so the cold-cache path is
  deterministic.
- **CPU throttling** (4×, 6×) to surface jank and long tasks on low-end devices.
- **Performance metrics** (`Performance.getMetrics` — `JSHeapUsedSize`, `LayoutCount`, `TaskDuration`) with a
  budget.

## When NOT to use

- Mock, abort, modify, hold, assert, HAR replay, offline, security headers, TLS → `references/playwright-routes.md`
- A client with no Playwright `IPage`, or cross-browser capture → `references/proxy.md`
- Writing the page objects themselves → `qa/dotnet/skills/ui-test-author/playwright`
- TypeScript and Java CDP → `qa-network-mocking-typescript`, `qa-network-mocking-java`

## Inputs needed

1. **Which hook** — a throttle preset, cache disable, a CPU rate, or metrics.
2. **Chromium-only is acceptable** for this class.
3. **The signal** — the loading or ready state to assert.

## Decision matrix — the CDP calls

| Goal | Call | Notes |
|---|---|---|
| Network events on | `SendAsync("Network.enable")` | Before `responseReceived` fires or a throttle applies |
| Real bandwidth and latency | `SendAsync("Network.emulateNetworkConditions", args)` | Throughput in **bytes per second**, latency in **ms** |
| No HTTP cache | `SendAsync("Network.setCacheDisabled", new() { ["cacheDisabled"] = true })` | Every request goes to the network |
| CPU slowdown | `SendAsync("Emulation.setCPUThrottlingRate", new() { ["rate"] = 4 })` | `1` = none, `4` / `6` = low-end device |
| Response metadata | `Event("Network.responseReceived").OnEvent += (_, payload) => …` | `response.url`, `.status`, `.fromDiskCache` |
| Metrics | `Performance.enable`, then `Performance.getMetrics` | `{ metrics: [{ name, value }] }` |

DevTools' own profiles, encoded in `NetworkPreset` below:

| Preset | Download | Upload | Latency |
|---|---|---|---|
| Slow 3G | ~50 KB/s (500 kbit/s × 0.8 ÷ 8) | ~50 KB/s | 2000 ms (400 × 5) |
| Fast 3G | ~180 KB/s (1.6 Mbit/s × 0.9 ÷ 8) | ~84 KB/s (750 kbit/s × 0.9 ÷ 8) | ~562 ms (150 × 3.75) |

## 1. The helper — `Support/CdpControls.cs`

```csharp
using System.Text.Json;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.UiTests.Support;

public sealed class CdpControls
{
    private readonly ICDPSession _session;

    private CdpControls(ICDPSession session) => _session = session;

    public static async Task<CdpControls> AttachAsync(IPage page, string browserName)
    {
        Assume.That(browserName, Is.EqualTo("chromium"), "CDP is Chromium-only");
        var session = await page.Context.NewCDPSessionAsync(page);
        await session.SendAsync("Network.enable");
        return new CdpControls(session);
    }

    public Task ThrottleAsync(NetworkPreset preset) =>
        _session.SendAsync("Network.emulateNetworkConditions", new()
        {
            ["offline"] = false,
            ["downloadThroughput"] = preset.DownloadBytesPerSecond,
            ["uploadThroughput"] = preset.UploadBytesPerSecond,
            ["latency"] = preset.LatencyMs,
        });

    public Task DisableCacheAsync() =>
        _session.SendAsync("Network.setCacheDisabled", new() { ["cacheDisabled"] = true });

    public Task CpuThrottleAsync(int rate) =>
        _session.SendAsync("Emulation.setCPUThrottlingRate", new() { ["rate"] = rate });

    public async Task<IReadOnlyDictionary<string, double>> MetricsAsync()
    {
        await _session.SendAsync("Performance.enable");
        var result = await _session.SendAsync("Performance.getMetrics");
        return result!.Value.GetProperty("metrics").EnumerateArray()
            .ToDictionary(metric => metric.GetProperty("name").GetString()!, metric => metric.GetProperty("value").GetDouble());
    }

    public Task<CapturedResponse> NextResponseAsync(Func<string, bool> url)
    {
        var next = new TaskCompletionSource<CapturedResponse>(TaskCreationOptions.RunContinuationsAsynchronously);
        _session.Event("Network.responseReceived").OnEvent += (_, payload) =>
        {
            var response = CapturedResponse.From(payload!.Value.GetProperty("response"));
            if (url(response.Url))
            {
                next.TrySetResult(response);
            }
        };
        return next.Task;
    }
}

public sealed record CapturedResponse(string Url, int Status, bool FromDiskCache)
{
    public static CapturedResponse From(JsonElement response) => new(
        response.GetProperty("url").GetString()!,
        response.GetProperty("status").GetInt32(),
        response.TryGetProperty("fromDiskCache", out var cached) && cached.GetBoolean());
}

public sealed record NetworkPreset(double DownloadBytesPerSecond, double UploadBytesPerSecond, double LatencyMs)
{
    public static readonly NetworkPreset Slow3G = new(500 * 1000 * 0.8 / 8, 500 * 1000 * 0.8 / 8, 400 * 5);

    public static readonly NetworkPreset Fast3G = new(1.6 * 1000 * 1000 * 0.9 / 8, 750 * 1000 * 0.9 / 8, 150 * 3.75);
}
```

- **The Chromium gate** is NUnit's `Assume.That` on `PlaywrightTest.BrowserName` (the runsettings
  `BrowserName`, or `BROWSER`): on another engine the test ends **inconclusive**, with the reason, instead of
  failing inside `NewCDPSessionAsync`. `BaseTest` runs Chromium by default; the gate keeps a CDP class honest
  when a run switches engines.
- **`NextResponseAsync` is registered before the action** and completes on the first matching
  `responseReceived` after it. The payload is `JsonElement?`, hence `payload!.Value`. The task completes with
  `RunContinuationsAsynchronously`, so the test's continuation never runs on Playwright's dispatch thread.
- **No detach hook.** The session belongs to the test's page; `BaseTest` closes the context after every test,
  which ends the session and its event handlers with it.
- Offline is `Context.SetOfflineAsync(true)` at the routing layer, so there is no offline preset here.

## 2. Real throttling — Slow 3G

```csharp
using Example.UiTests.Pages;
using Example.UiTests.Support;
using NUnit.Framework;

namespace Example.UiTests.Tests;

public class NetworkConditionsTests : BaseTest
{
    private CdpControls _cdp = null!;
    private OrdersPage _ordersPage = null!;
    private ProfilePage _profilePage = null!;
    private DashboardPage _dashboardPage = null!;

    [SetUp]
    public async Task AttachCdp()
    {
        _cdp = await CdpControls.AttachAsync(Page, BrowserName);
        _ordersPage = new OrdersPage(Page);
        _profilePage = new ProfilePage(Page);
        _dashboardPage = new DashboardPage(Page);
    }

    [Test]
    public async Task Should_ShowSkeletonUntilOrdersArrive_When_NetworkIsSlow3G()
    {
        await _cdp.ThrottleAsync(NetworkPreset.Slow3G);

        await _ordersPage.NavigateAsync();

        await Expect(_ordersPage.Skeleton, "orders skeleton under Slow 3G").ToBeVisibleAsync();
        await Expect(_ordersPage.List, "orders list after a Slow 3G load").ToBeVisibleAsync(new() { Timeout = 30_000 });
    }
}
```

Apply the profile **before** the navigation that should feel it. `NavigateAsync()` only navigates, so the
loading state is still observable. The longer `Timeout` is a deadline for a web-first assertion, not a sleep.
The two assertions are one behaviour: the skeleton holds until the slow list arrives.

§3–§5 are further methods of `NetworkConditionsTests`.

## 3. Cache disabled — the reload goes to the network

```csharp
[Test]
public async Task Should_RefetchAvatarFromNetwork_When_CacheIsDisabled()
{
    await _cdp.DisableCacheAsync();
    await _profilePage.OpenAsync();
    var reloadedAvatar = _cdp.NextResponseAsync(url => url.Contains("/avatars/"));

    await _profilePage.ReloadProfileAsync();

    var avatar = await reloadedAvatar.WaitAsync(TimeSpan.FromSeconds(10));
    Assert.That(avatar.FromDiskCache, Is.False, $"reloaded avatar {avatar.Url} (status {avatar.Status}) came from the disk cache");
}
```

- The listener starts **after** the first load and **before** the reload, so the response it returns is the
  reload's — the one the test is about. Reading the first captured avatar instead would read the response from
  before the reload, and the test could never fail.
- `WaitAsync(TimeSpan)` is a deadline: if no avatar response arrives, it throws `TimeoutException` at that line
  and the test fails.
- The message carries the URL and status of the response it judged.

## 4. CPU throttling

```csharp
[Test]
public async Task Should_RenderDashboardWithinDeadline_When_CpuIsThrottled4x()
{
    await _cdp.CpuThrottleAsync(4);

    await _dashboardPage.NavigateAsync();

    await Expect(_dashboardPage.Ready, "dashboard ready marker at 4× CPU slowdown").ToBeVisibleAsync(new() { Timeout = 15_000 });
}
```

Each test gets a fresh session on a fresh page, so the rate never needs resetting.

## 5. Performance budget

```csharp
[Test]
public async Task Should_StayWithinLayoutAndHeapBudget_When_DashboardRenders()
{
    await _dashboardPage.OpenAsync();

    var metrics = await _cdp.MetricsAsync();

    Assert.Multiple(() =>
    {
        Assert.That(metrics["LayoutCount"], Is.LessThan(60), "layout count");
        Assert.That(metrics["JSHeapUsedSize"], Is.LessThan(50 * 1024 * 1024), "JS heap bytes");
    });
}
```

`OpenAsync()` returns once the dashboard's ready marker is visible; sampling before that passes only because
the page had not finished rendering. The two assertions are one behaviour, "renders within budget", and
`Assert.Multiple` reports both. A missing metric throws `KeyNotFoundException` naming the key.

## Rules

### Session lifecycle

- `CdpControls.AttachAsync(Page, BrowserName)` in the class's own `[SetUp]` — one session per test's page. It
  ends with the context `BaseTest` closes.
- `Network.enable` before subscribing to `Network.responseReceived` or throttling; `Performance.enable` before
  `getMetrics`.

### Chromium only

- `AttachAsync` gates on `BrowserName` with `Assume.That(..., Is.EqualTo("chromium"), ...)`.
- A test that must run cross-browser does not belong here — `references/playwright-routes.md` or
  `references/proxy.md`.

### Throttling and emulation

- Throughput is **bytes per second**, latency **milliseconds** — use `NetworkPreset`, not raw numbers per test.
- Apply throttle, cache disable and CPU rate **before** the navigation or action that should feel them.

### Assertions and waits

- Every wait is a web-first assertion with a deadline on a real loading or ready signal, or a
  `NextResponseAsync` task registered before the action and awaited with `WaitAsync(timeout)`.
- Sample metrics after a user-visible ready signal.

### Hygiene

- Protocol method and event names are strings — a typo fails at runtime. Keep every `SendAsync` and `Event`
  inside `CdpControls`.
- The event payload and the `SendAsync` result are `JsonElement?`: unwrap with `!.Value` (or check
  `HasValue`), then read with `GetProperty` / `TryGetProperty`.

## What NOT to do

- No `SendAsync(...)` or `Event(...)` in a `[Test]` method.
- No `payload.GetProperty(...)` on the event payload — it is `JsonElement?`.
- No CDP class without the Chromium gate.
- No `Task.Delay`, `WaitForTimeoutAsync` or polling loop to "wait for the slow load".
- No `emulateNetworkConditions` before `Network.enable`; no `getMetrics` before `Performance.enable`.
- No raw throughput numbers per test.
- No listener registered after the action it should observe.
- No security-header or TLS audit here — routing covers both, cross-browser.
- No `ContextOptions()` override returning `new()`, and no `CdpBaseTest` beside `BaseTest` — the helper is
  enough.
- No CDP where `Page.RouteAsync` expresses the test just as well.

## Generation steps

1. Confirm the hook, that Chromium-only is acceptable, and the signal.
2. Extend `CdpControls` with an intent method; build it and the page objects in the class's `[SetUp]`.
3. Apply the hook before the navigation; assert on a real loading or ready signal with a deadline.
4. For captured responses, register `NextResponseAsync` before the action and await it with a deadline.
5. Read a failure's trace (`qa/dotnet/skills/evidence-capture`, "Reading a failure"): the network view shows the
   throttled timings.

## Cross-references

- `references/playwright-routes.md` — the layer above; reach for it first.
- `references/proxy.md` — capture for a client with no Playwright `IPage`.
- `qa/dotnet/skills/ui-test-author/playwright` — `BaseTest`, page objects, `references/assertions.md` §5.
- `qa/dotnet/skills/evidence-capture` — traces and reading a failure.
- `qa/cicd/dotnet/skills/ci-pipelines` — the UI job (Chromium).
- `qa-network-mocking-typescript`, `qa-network-mocking-java` — the sibling lanes.
