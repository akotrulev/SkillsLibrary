# QA — Raw CDP Network & Performance Hooks (C# / .NET)

Drives the raw **Chrome DevTools Protocol** from a Playwright `Microsoft.Playwright` + NUnit test on .NET 8 via `page.Context.NewCDPSessionAsync(page)`, for the hooks that live **below the `RouteAsync` routing layer**: real bandwidth/latency throttling, HTTP-cache disable, CPU throttling, security-header/`securityDetails` auditing, and `Performance` metrics. Built on the **`PageTest` base-class** model from `qa/dotnet/skills/network-monitoring`: the CDP session and every command/event are wrapped in an intent-revealing `CdpControls` helper exposed through `BaseTest`, never raw `SendAsync("Domain.method", …)` scattered across `[Test]` methods. Every wait is conditional on a Playwright condition or a CDP event; there is **no `WaitForTimeoutAsync`** as a wait anywhere in this skill.

This is the **.NET port of the canonical** `qa/typescript/skills/network-monitoring` — same patterns (throttle / cache-disable / CPU-throttle / security audit / perf budget), re-expressed in `Microsoft.Playwright` async idioms. The one binding difference that drives the porting: .NET sends commands with **`SendAsync(method, Dictionary<string,object>)`** returning a `JsonElement?`, and subscribes to CDP events with **`session.Event("Network.responseReceived").OnEvent += (_, json) => …`** (no typed event payloads — you read a `JsonElement`).

> **Chromium-only.** CDP exists only in Chromium-based browsers. On Firefox/WebKit `NewCDPSessionAsync` throws. That is the price of dropping below the routing layer — guard the suite to the Chromium engine. For anything that must run cross-browser, stay at the `RouteAsync` layer (`playwright-routes`).

## Stack

- .NET 8, C# (nullable reference types enabled), async all the way (`*Async`, never `.Result`/`.Wait()`)
- NUnit 4.x + `Microsoft.Playwright` + `Microsoft.Playwright.NUnit` (Playwright ≥ 1.49)
- CDP helpers under `Tests/Support/Cdp/`
- Page objects under `Tests/Pages/`, test classes under `Tests/Specs/` (see the UI sibling)
- These tests run **only against Chromium**, sharded in CI under `qa/cicd/dotnet/skills/ci-pipelines`. No new secrets — CDP needs none.

## When to use

- Emulating a **real** slow connection (Slow/Fast 3G with actual throughput + latency numbers) to test loading/timeout/skeleton states — not the per-request `Task.Delay` `RouteAsync` can fake
- Forcing every request to **miss the HTTP cache** (`Network.setCacheDisabled`) for deterministic cold-cache behavior
- **CPU-throttling** the main thread (4×/6×) to surface jank, long tasks, and slow renders on low-end devices
- **Auditing security headers** — assert the document carries CSP / HSTS / `X-Frame-Options`, or inspect TLS `securityDetails`
- Capturing **performance metrics** (`Performance.getMetrics` — `JSHeapUsedSize`, `LayoutCount`, `TaskDuration`, …) and asserting a budget

## When NOT to use

- High-level request **mock / abort / fulfill / modify-in-flight**, HAR replay, or approximate offline (`SetOfflineAsync`) → `qa/dotnet/skills/network-monitoring` (the layer above; reach for it first)
- Playwright TypeScript / Java CDP → `qa/{typescript,java}/skills/network-monitoring`
- **Cross-browser** throttling/auditing, or capture for a non-Playwright / multi-process stack → `qa/dotnet/skills/network-monitoring`
- Writing the page objects / test classes themselves → `qa/dotnet/skills/ui-test-author/playwright`

## Inputs needed

Ask at most 3 questions; infer the rest from the test project and existing tests.

1. **Which hook** — network throttle (which preset?), cache disable, CPU throttle (which rate?), security-header audit, or perf metrics?
2. **Confirm Chromium-only is acceptable** — is this suite allowed to run only against the Chromium engine?
3. **The signal** — for throttle/CPU: which loading/jank state to assert? For audit: which headers, on which URL?

## Decision matrix — CDP domains used in tests

| Goal | CDP call | Notes |
|---|---|---|
| Enable network events | `await session.SendAsync("Network.enable")` | Required **before** `responseReceived`/`emulateNetworkConditions` |
| Real bandwidth + latency | `await session.SendAsync("Network.emulateNetworkConditions", new Dictionary<string,object> { … })` | Throughput in **bytes/s**, latency in **ms**; use the Slow/Fast 3G presets |
| Disable the HTTP cache | `await session.SendAsync("Network.setCacheDisabled", new() { ["cacheDisabled"] = true })` | Every request misses cache |
| Throttle the CPU | `await session.SendAsync("Emulation.setCPUThrottlingRate", new() { ["rate"] = 4 })` | `rate` = slowdown multiplier; `1` = none |
| Capture response metadata | `session.Event("Network.responseReceived").OnEvent += (_, json) => …` | `json` is a `JsonElement`; read `response.url`/`status`/`headers`/`securityDetails` |
| Perf metrics | `SendAsync("Performance.enable")` then `SendAsync("Performance.getMetrics")` | Returns `{ metrics: [{ name, value }] }` as a `JsonElement?` |
| Close the session | `await session.DetachAsync()` | Do it in `[TearDown]`; a detached session emits no events |

Realistic throttling numbers (Chrome DevTools' own Slow/Fast 3G profiles — encoded in `NetworkPresets` below):

| Preset | download | upload | latency |
|---|---|---|---|
| Slow 3G | ~50 KB/s (`500 kbit/s × 0.8 ÷ 8`) | ~50 KB/s | 2000 ms (`400 × 5`) |
| Fast 3G | ~180 KB/s (`1.6 Mbit/s × 0.9 ÷ 8`) | ~84 KB/s (`750 kbit/s × 0.9 ÷ 8`) | ~562 ms (`150 × 3.75`) |

## Patterns

### The CDP helper — `Tests/Support/Cdp/CdpControls.cs`

One helper owns the session: it opens it, enables `Network`, captures every `responseReceived` for later auditing, exposes intent-named methods, and detaches in teardown. Tests call `Cdp.ThrottleAsync(NetworkPresets.Slow3G)`, never `SendAsync("Network.emulateNetworkConditions", …)`.

```csharp
using System.Text.Json;
using Microsoft.Playwright;

namespace Example.Tests.Support.Cdp;

/// <summary>A response captured off the wire via Network.responseReceived.</summary>
public sealed record CapturedResponse(string Url, int Status, JsonElement Headers, JsonElement? SecurityDetails);

public sealed class CdpControls : IAsyncDisposable
{
    private readonly ICDPSession _session;
    private readonly List<CapturedResponse> _captured = [];

    private CdpControls(ICDPSession session)
    {
        _session = session;
        // Registered immediately after Network.enable, before any navigation — so no response is missed.
        _session.Event("Network.responseReceived").OnEvent += (_, json) =>
        {
            var response = json.GetProperty("response");
            _captured.Add(new CapturedResponse(
                response.GetProperty("url").GetString()!,
                response.GetProperty("status").GetInt32(),
                response.GetProperty("headers"),
                response.TryGetProperty("securityDetails", out var sd) ? sd : null));
        };
    }

    public static async Task<CdpControls> AttachAsync(IPage page)
    {
        var session = await page.Context.NewCDPSessionAsync(page); // Chromium-only — throws on FF/WebKit
        await session.SendAsync("Network.enable");
        return new CdpControls(session);
    }

    /// <summary>Apply a real bandwidth + latency profile (e.g. NetworkPresets.Slow3G).</summary>
    public Task ThrottleAsync(IReadOnlyDictionary<string, object> preset) =>
        _session.SendAsync("Network.emulateNetworkConditions", new Dictionary<string, object>(preset));

    /// <summary>Force every request to miss the HTTP cache — cold-cache path becomes deterministic.</summary>
    public Task DisableCacheAsync() =>
        _session.SendAsync("Network.setCacheDisabled", new Dictionary<string, object> { ["cacheDisabled"] = true });

    /// <summary>Slow the main thread by <paramref name="rate"/>× (1 = none, 4/6 = low-end device).</summary>
    public Task CpuThrottleAsync(int rate) =>
        _session.SendAsync("Emulation.setCPUThrottlingRate", new Dictionary<string, object> { ["rate"] = rate });

    /// <summary>Performance.getMetrics as a name→value map for budget assertions.</summary>
    public async Task<IReadOnlyDictionary<string, double>> MetricsAsync()
    {
        await _session.SendAsync("Performance.enable");
        var result = await _session.SendAsync("Performance.getMetrics");
        return result!.Value.GetProperty("metrics").EnumerateArray()
            .ToDictionary(m => m.GetProperty("name").GetString()!, m => m.GetProperty("value").GetDouble());
    }

    /// <summary>The captured response whose URL matches — for the security-header audit.</summary>
    public CapturedResponse? ResponseFor(Func<string, bool> predicate) =>
        _captured.FirstOrDefault(r => predicate(r.Url));

    public async ValueTask DisposeAsync() => await _session.DetachAsync();
}
```

The throttling presets (throughput in **bytes/second**, latency in **ms** — DevTools' own Slow/Fast 3G formulas):

```csharp
namespace Example.Tests.Support.Cdp;

public static class NetworkPresets
{
    public static readonly IReadOnlyDictionary<string, object> Slow3G = new Dictionary<string, object>
    {
        ["offline"] = false,
        ["downloadThroughput"] = 500 * 1000 * 0.8 / 8,
        ["uploadThroughput"] = 500 * 1000 * 0.8 / 8,
        ["latency"] = 400 * 5,
    };

    public static readonly IReadOnlyDictionary<string, object> Fast3G = new Dictionary<string, object>
    {
        ["offline"] = false,
        ["downloadThroughput"] = 1.6 * 1000 * 1000 * 0.9 / 8,
        ["uploadThroughput"] = 750 * 1000 * 0.9 / 8,
        ["latency"] = 150 * 3.75,
    };
}
```

Expose it on `BaseTest` so test classes get `Cdp` ready in `[SetUp]`, and gate the engine to Chromium:

```csharp
public abstract class CdpBaseTest : PageTest
{
    protected CdpControls Cdp { get; private set; } = default!;

    public override BrowserNewContextOptions ContextOptions() => new() { /* shared options */ };

    [SetUp]
    public async Task InitCdp()
    {
        // CDP is Chromium-only — declare the dependency loudly.
        Assume.That(BrowserName, Is.EqualTo("chromium"), "CDP is Chromium-only");
        Cdp = await CdpControls.AttachAsync(Page);
    }

    [TearDown]
    public async Task DisposeCdp() => await Cdp.DisposeAsync();
}
```

### Real network throttling — Slow 3G

```csharp
[TestFixture]
public class ThrottleTests : CdpBaseTest
{
    [Test]
    public async Task Should_Keep_The_Skeleton_Visible_When_Orders_Load_Over_Slow_3G()
    {
        await Cdp.ThrottleAsync(NetworkPresets.Slow3G); // apply BEFORE navigating

        await Page.GotoAsync("/orders");

        // The skeleton is the genuine loading signal — assert on it, never on a fixed delay.
        await Expect(Page.GetByTestId("orders-skeleton")).ToBeVisibleAsync();
        await Expect(Page.GetByTestId("orders-list")).ToBeVisibleAsync(new() { Timeout = 30_000 });
    }
}
```

`Expect(...)` retries until the slow load completes, so the longer `Timeout` is a deadline, **not** a `WaitForTimeoutAsync`.

### Disable the HTTP cache

```csharp
[Test]
public async Task Should_Refetch_The_Avatar_When_The_Cache_Is_Disabled()
{
    await Cdp.DisableCacheAsync();

    await Page.GotoAsync("/profile");
    await Expect(Page.GetByTestId("avatar")).ToBeVisibleAsync();
    await Page.GetByRole(AriaRole.Button, new() { Name = "Reload profile" }).ClickAsync();

    var avatar = Cdp.ResponseFor(u => u.Contains("/avatars/"));
    Assert.That(avatar?.Status, Is.EqualTo(200), "avatar should be re-fetched, not served from cache");
}
```

### CPU throttling — surface jank

```csharp
[Test]
public async Task Should_Render_The_Dashboard_Within_Budget_When_The_Cpu_Is_Throttled_4x()
{
    await Cdp.CpuThrottleAsync(4); // 4× slowdown ≈ a mid-tier mobile device

    await Page.GotoAsync("/dashboard");

    await Expect(Page.GetByTestId("dashboard-ready")).ToBeVisibleAsync(new() { Timeout = 15_000 });
}
```

### Security-header audit from captured `Network.responseReceived`

Assert the document response carries the expected security headers. CDP header keys are **lowercased** by the protocol, so normalize the lookup. This is **one logical assertion** ("the response is securely configured") expressed as a multi-assert block so a run reports *every* missing header at once via NUnit's `Assert.Multiple`.

```csharp
// Tests/Support/Cdp/SecurityHeaders.cs
using System.Text.Json;
using NUnit.Framework;

namespace Example.Tests.Support.Cdp;

public static class SecurityHeaders
{
    private static readonly string[] Required =
        ["content-security-policy", "strict-transport-security", "x-frame-options"];

    public static void AssertPresent(CapturedResponse? response)
    {
        Assert.That(response, Is.Not.Null, "no response was captured for that URL");

        var headers = response!.Headers.EnumerateObject()
            .ToDictionary(p => p.Name.ToLowerInvariant(), p => p.Value.GetString());

        Assert.Multiple(() =>
        {
            foreach (var name in Required)
                Assert.That(headers.ContainsKey(name), Is.True, $"{name} header is missing");
        });
    }
}
```

```csharp
[Test]
public async Task Should_Send_Csp_Hsts_And_X_Frame_Options_When_The_App_Shell_Loads()
{
    await Page.GotoAsync("/");
    await Expect(Page.GetByRole(AriaRole.Navigation)).ToBeVisibleAsync(); // shell loaded → its response was captured

    SecurityHeaders.AssertPresent(Cdp.ResponseFor(u => u == Page.Url));
}

[Test]
public async Task Should_Negotiate_Tls_1_3_For_The_Document_When_Loaded_Over_Https()
{
    await Page.GotoAsync("/");
    await Expect(Page.GetByRole(AriaRole.Navigation)).ToBeVisibleAsync();

    var doc = Cdp.ResponseFor(u => u.StartsWith("https://"));
    var protocol = doc?.SecurityDetails?.GetProperty("protocol").GetString();
    Assert.That(protocol, Is.EqualTo("TLS 1.3")); // securityDetails: protocol, issuer, validFrom/To, sanList
}
```

### Performance budget from `Performance.getMetrics`

```csharp
[Test]
public async Task Should_Stay_Under_The_Layout_And_Heap_Budget_When_The_Dashboard_Renders()
{
    await Page.GotoAsync("/dashboard");
    await Expect(Page.GetByTestId("dashboard-ready")).ToBeVisibleAsync(); // a real "done" signal before sampling

    var metrics = await Cdp.MetricsAsync();

    // One behavior — "the dashboard renders within budget" — verified by related metrics.
    Assert.Multiple(() =>
    {
        Assert.That(metrics["LayoutCount"], Is.LessThan(60), "too many layouts");
        Assert.That(metrics["JSHeapUsedSize"], Is.LessThan(50 * 1024 * 1024), "JS heap too large");
    });
}
```

Sample metrics **after** a user-visible "ready" signal, never after a delay.

## Rules

### Session lifecycle
- Open with `page.Context.NewCDPSessionAsync(page)` and **`DetachAsync()` in `[TearDown]`** (here via `IAsyncDisposable`) — a leaked session keeps emitting events and can outlive the page.
- Call `Network.enable` **before** subscribing to `Network.responseReceived` or applying `emulateNetworkConditions`; call `Performance.enable` before `getMetrics`.
- One session per page in the helper; don't sprinkle extra `NewCDPSessionAsync` calls through `[Test]` methods.

### Chromium-only
- `NewCDPSessionAsync` **throws on Firefox/WebKit.** Gate with `Assume.That(BrowserName, Is.EqualTo("chromium"), …)` (or run only the Chromium project). State the limitation in the fixture, not just in your head.
- If a test must be cross-browser, it does not belong here — use `RouteAsync` (`playwright-routes`) or an external `proxy`.

### Throttling & emulation
- `emulateNetworkConditions` throughput is **bytes/second**, latency is **milliseconds** — use the `NetworkPresets` constants, don't hand-roll raw numbers per test.
- Apply throttle / cache-disable / CPU-throttle **before** the navigation or action that should feel it.
- `Emulation.setCPUThrottlingRate` `rate` is a **slowdown multiplier** (`1` = none); reset to `1` only if you reuse one session across phases.

### Assertions & waits
- **No `Page.WaitForTimeoutAsync(ms)` / `Thread.Sleep`.** Every wait is a web-first `Expect(...).ToBeVisibleAsync(new() { Timeout = … })` on a real loading/ready signal, or driven by a captured CDP event. A longer `Timeout` under throttling is a deadline, not a sleep.
- CDP response **header keys are lowercased** — normalize with `ToLowerInvariant()` before lookup.
- A security-header / perf-budget check is **one logical assertion**; group its related checks in `Assert.Multiple` so the report lists every failure at once.
- Sample `Performance.getMetrics` (and read captured responses) **after** a user-visible completion signal, never after a fixed delay.
- Never `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` on any Playwright or CDP call — async all the way.

### Hygiene
- Protocol method/event names are **strings** — a typo (`"Network.emulateNetworkCondition"`) fails at runtime, not compile time. Keep every `SendAsync`/`Event` inside the typed `CdpControls` wrapper.
- `SendAsync` returns a `JsonElement?` — read it with `GetProperty`/`TryGetProperty`, don't re-deserialize the whole tree.
- Don't reach for CDP when `RouteAsync` would do — it's the more brittle, Chromium-only layer.

### What NOT to do
- No `SendAsync("Domain.method", …)` / `Event(...)` scattered through `[Test]` methods — wrap it in the `CdpControls` helper with an intent name.
- No CDP test running on Firefox/WebKit — it throws; gate to Chromium.
- No `Page.WaitForTimeoutAsync(ms)` / `Thread.Sleep` to "wait for the slow load" — assert on the loading/ready element with a `Timeout` deadline.
- No `emulateNetworkConditions` before `Network.enable`, no `getMetrics` before `Performance.enable`.
- No raw throughput numbers per test — use `NetworkPresets`.
- No `Content-Security-Policy` cased lookup against CDP headers — they're lowercased.
- No leaked session — `DetachAsync()` in teardown.
- No `.Result` / `.Wait()` on a CDP call.
- No CDP where `RouteAsync` (cross-browser, typed) expresses the test just as well.

## Generation steps

1. Confirm **which hook** (throttle / cache / CPU / security audit / perf), that **Chromium-only is acceptable**, and **the signal** to assert.
2. Add or extend `Tests/Support/Cdp/CdpControls.cs` — open the session, `Network.enable`, capture `responseReceived`, expose intent methods (`ThrottleAsync`, `DisableCacheAsync`, `CpuThrottleAsync`, `MetricsAsync`, `ResponseFor`), `DetachAsync()` via `IAsyncDisposable`. Expose it on `CdpBaseTest` with the `Assume.That(BrowserName == "chromium")` gate.
3. Apply the hook **before** the navigation/action; assert on a real loading/ready signal with a `Timeout` deadline — never `WaitForTimeoutAsync`.
4. For audits, normalize header case and use `SecurityHeaders.AssertPresent`; for budgets, sample `MetricsAsync()` after a ready signal.
5. Run `dotnet test` (Chromium engine); verify with the trace viewer's Network tab (throttled timings). Build with nullable warnings as errors.

## Cross-references

- **`qa/dotnet/skills/network-monitoring`** — the **layer above**; reach for it first (cross-browser mock/abort/fulfill/assert, HAR, approximate offline). Drop to CDP only when routing can't express the test.
- **`qa/typescript/skills/network-monitoring`** — the canonical skill this ports from; consult it for the conceptual model and the three-way pick.
- **`qa/java/skills/network-monitoring`** — the sibling Java port (`CDPSession.send`, Gson `JsonObject`, `client.on(event, …)`).
- **`qa/dotnet/skills/network-monitoring`** — out-of-browser MITM capture for cross-browser or non-Playwright stacks.
- **`qa/dotnet/skills/ui-test-author/playwright`** — the `PageTest` base-class / page-object model these CDP helpers layer on; the no-`WaitForTimeoutAsync` discipline originates there.
- **`qa/cicd/dotnet/skills/ci-pipelines`** — runs these tests (Chromium only) sharded; traces on failure show throttled timings.
