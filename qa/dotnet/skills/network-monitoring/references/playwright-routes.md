# QA — Playwright Network Monitoring & Interception (C# / .NET)

Intercepts, mocks, asserts, and shapes HTTP traffic in Playwright `Microsoft.Playwright` + NUnit tests on .NET 8. Built on the **`PageTest` base-class** model from `qa/dotnet/skills/ui-test-author/playwright`: route handlers and request-assertion helpers are wrapped in intent-revealing helper classes exposed through `BaseTest`, never raw `RouteAsync(...)` calls scattered across `[Test]` methods. Every wait is conditional on a request/response predicate; there is **no `WaitForTimeoutAsync`** as a wait anywhere in this skill.

This is the **.NET port of the canonical** `qa/typescript/skills/network-monitoring` — same patterns (mock / assert / modify-in-flight / HAR / offline / latency), re-expressed in `Microsoft.Playwright` async idioms.

## Stack

- .NET 8, C# (nullable reference types enabled), async all the way (`*Async`, never `.Result`/`.Wait()`)
- NUnit 4.x + `Microsoft.Playwright` + `Microsoft.Playwright.NUnit` (Playwright ≥ 1.49)
- Network helpers under `Tests/Support/Network/`, HAR archives under `Tests/Fixtures/Har/`
- Page objects under `Tests/Pages/`, test classes under `Tests/Specs/` (see the UI sibling)
- These tests run sharded in CI under `qa/dotnet/skills/ci-pipelines`

## When to use

- Mocking a backend or third-party response so a UI test is deterministic (stub JSON, force a `500`/`403`)
- **Asserting** an endpoint was (or was not) called, with the expected method / payload / headers
- Modifying a real response in flight (inject a flag, corrupt one field) to exercise an edge case
- Recording a HAR of a flaky third-party dependency, then replaying it offline for determinism
- Simulating offline / slow-network conditions to test loading and error states
- Blocking noisy resources (analytics, fonts, images) to speed up or stabilize a suite

## When NOT to use

- Playwright TypeScript / Java interception → `qa/{typescript,java}/skills/network-monitoring`
- Low-level CDP (`Network.*`, real bandwidth throttling, protocol tracing) → `qa/dotnet/skills/network-monitoring`
- An HTTP proxy in front of the browser (mitmproxy, system-level capture) → `qa/dotnet/skills/network-monitoring`
- Writing the page objects / test classes themselves → `qa/dotnet/skills/ui-test-author/playwright`
- Pure API contract/integration tests with no browser → `qa/dotnet/skills/api-test-author/generator`

## Inputs needed

Ask at most 3 questions; infer the rest from the test project and existing tests.

1. **What traffic** — exact endpoint(s) or URL glob/regex (`**/api/orders/**`), and is it first-party or a third-party dependency?
2. **Intent** — mock a response, assert a call happened, modify in flight, replay a HAR, or simulate offline/latency?
3. **Scope** — one page (`Page.RouteAsync`) or every page in the context including popups (`Context.RouteAsync`)?

## Decision matrix

| Goal | Tool | Notes |
|---|---|---|
| Return canned data, never hit the network | `route.FulfillAsync(new() { Json = obj })` | `Json` sets `content-type: application/json` and serializes |
| Force an error status | `route.FulfillAsync(new() { Status = 500, Json = ... })` | The app's error path is now deterministic |
| Block a resource (analytics, images) | `route.AbortAsync()` | `AbortAsync("blockedbyclient")` to be explicit |
| Let it through unchanged | `route.ContinueAsync()` | Goes straight to network; **skips** remaining handlers |
| Let an **earlier-registered** handler also run | `route.FallbackAsync()` | Chains to the next matching handler instead of the network |
| Modify a real response | `await route.FetchAsync()` → mutate → `route.FulfillAsync(new() { Response = r, Body = ... })` | Preserves original status/headers unless overridden |
| Tweak the outgoing request | `route.ContinueAsync(new() { Headers = ..., PostData = ... })` | Header tampering, payload rewrite |
| Assert a call happened | `RunAndWaitForRequestAsync` / `RunAndWaitForResponseAsync` | Action lambda first — the API shape removes the listener-ordering pitfall |
| Deterministic third-party dep | `RouteFromHARAsync(har, new() { Url = ..., NotFound = HarNotFound.Abort })` | Record once with `Update = true`, commit, replay |
| Whole-context offline | `Context.SetOfflineAsync(true)` | Cross-browser |
| Latency simulation | `await Task.Delay(ms)` inside the handler, then `route.ContinueAsync()` | No built-in `route` throttle; real bandwidth = CDP (Chromium-only) → `qa/dotnet/skills/network-monitoring` |

## Patterns

### Route-mocking helper — `Tests/Support/Network/MockApi.cs`

Wrap interception in a helper with intent-revealing methods. Tests call `MockApi.StubOrdersAsync([...])`, not `Page.RouteAsync("**/api/orders", ...)`.

```csharp
using System.Text.RegularExpressions;
using Microsoft.Playwright;

namespace Example.Tests.Support.Network;

public sealed class MockApi
{
    private readonly IPage _page;

    public MockApi(IPage page) => _page = page;

    /// <summary>Serve canned orders; the real backend is never hit.</summary>
    public Task StubOrdersAsync(object[] orders) =>
        _page.RouteAsync("**/api/orders", route =>
            route.FulfillAsync(new RouteFulfillOptions { Json = orders }));

    /// <summary>Force the orders endpoint to fail so the UI's error path runs.</summary>
    public Task FailOrdersWithAsync(int status) =>
        _page.RouteAsync("**/api/orders", route =>
            route.FulfillAsync(new RouteFulfillOptions
            {
                Status = status,
                Json = new { error = "simulated failure" },
            }));

    /// <summary>Drop noisy third-party traffic to stabilize and speed up the run.</summary>
    public Task BlockAnalyticsAsync() =>
        _page.RouteAsync(new Regex(@"google-analytics\.com|segment\.io"), route =>
            route.AbortAsync("blockedbyclient"));
}
```

Expose it on `BaseTest` so test classes get `MockApi` ready in `[SetUp]` (mirrors how the UI sibling wires page objects):

```csharp
public abstract class NetworkBaseTest : PageTest
{
    protected MockApi MockApi { get; private set; } = default!;

    [SetUp]
    public void InitNetwork() => MockApi = new MockApi(Page);
}
```

```csharp
// Tests/Specs/OrdersTests.cs
[TestFixture]
public class OrdersTests : NetworkBaseTest
{
    [Test]
    public async Task Renders_Empty_State_When_There_Are_No_Orders()
    {
        await MockApi.StubOrdersAsync([]);
        await Page.GotoAsync("/orders");

        await Expect(Page.GetByTestId("orders-empty")).ToBeVisibleAsync();
    }

    [Test]
    public async Task Shows_Error_Banner_When_Orders_Api_Fails()
    {
        await MockApi.FailOrdersWithAsync(500);
        await Page.GotoAsync("/orders");

        await Expect(Page.GetByRole(AriaRole.Alert))
            .ToContainTextAsync(new Regex("couldn’t load orders", RegexOptions.IgnoreCase));
    }
}
```

Register routes **before** the navigation/action that triggers them — a route registered after the request has fired won't catch it.

### Request-assertion helper — fail fast on a missing/mismatched call

`RunAndWaitForRequestAsync` takes the **action lambda first**, then the URL/predicate — the API shape sets up the listener before running the action, so the listener-before-action ordering pitfall (a footgun in the TS sibling) cannot happen here.

```csharp
// Tests/Support/Network/RequestAssertions.cs
using System.Text.Json;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.Tests.Support.Network;

public static class RequestAssertions
{
    /// <summary>
    /// Assert a request matching <paramref name="urlGlob"/> fires while <paramref name="action"/> runs,
    /// optionally matching method and JSON payload. Fails fast on timeout.
    /// </summary>
    public static async Task<IRequest> ExpectRequestAsync(
        IPage page,
        string urlGlob,
        Func<Task> action,
        string? method = null,
        Func<JsonElement, bool>? bodyMatches = null)
    {
        var request = await page.RunAndWaitForRequestAsync(action, urlGlob);

        if (method is not null)
            Assert.That(request.Method, Is.EqualTo(method), "request method did not match");

        if (bodyMatches is not null)
            Assert.That(bodyMatches(request.PostDataJSON!.Value), Is.True, "request payload did not match");

        return request;
    }
}
```

```csharp
[Test]
public async Task Submits_The_Checkout_With_The_Cart_Total()
{
    await Page.GotoAsync("/cart");

    await RequestAssertions.ExpectRequestAsync(
        Page,
        "**/api/checkout",
        action: () => Page.GetByRole(AriaRole.Button, new() { Name = "Place order" }).ClickAsync(),
        method: "POST",
        bodyMatches: b => b.GetProperty("totalMinor").GetInt32() == 15_000
                       && b.GetProperty("currency").GetString() == "EUR");
}
```

`IRequest.PostDataJSON` is a `JsonElement?` property — read it directly; don't re-parse `PostData` by hand. For a plain "was it called", `RunAndWaitForResponseAsync(action, "**/api/checkout")` is enough.

### Asserting an endpoint was **not** called

There is no negative wait. Collect matching requests over the window of the action via the `Request` event, then assert the count.

```csharp
[Test]
public async Task Does_Not_Call_The_Legacy_Pricing_Endpoint()
{
    var calls = new List<string>();
    Page.Request += (_, req) =>
    {
        if (req.Url.Contains("/api/legacy-pricing")) calls.Add(req.Url);
    };

    await Page.GotoAsync("/cart");
    await Page.GetByRole(AriaRole.Button, new() { Name = "Recalculate" }).ClickAsync();
    await Expect(Page.GetByTestId("cart-total")).ToBeVisibleAsync(); // real signal the flow finished

    Assert.That(calls, Is.Empty, "legacy pricing endpoint should be retired");
}
```

Gate the assertion on a **user-visible signal** that the flow completed (`ToBeVisibleAsync` on the result), never on a fixed delay — otherwise the negative check passes simply because the request hadn't fired yet.

### Modify a real response in flight

Fetch the live response, mutate the body, re-serve. Passing `Response` keeps the original status and headers; `System.Text.Json.Nodes.JsonNode` gives a mutable tree.

```csharp
using System.Text.Json.Nodes;

await Page.RouteAsync("**/api/feature-flags", async route =>
{
    var response = await route.FetchAsync();
    var flags = JsonNode.Parse(await response.TextAsync())!;
    flags["betaCheckout"] = true;             // force the variant under test
    await route.FulfillAsync(new RouteFulfillOptions
    {
        Response = response,
        Body = flags.ToJsonString(),
    });
});
```

### Header / payload tampering on the outbound request

```csharp
await Page.RouteAsync("**/api/**", route =>
{
    var headers = new Dictionary<string, string>(route.Request.Headers) { ["x-test-tenant"] = "tenant-42" };
    return route.ContinueAsync(new RouteContinueOptions { Headers = headers });
});
```

### HAR record-then-replay for deterministic third-party deps

Record once against the live dependency, commit the archive, then replay offline on every run. Use `HarContentPolicy.Attach` so bodies live as separate files (reviewable diffs).

```csharp
// One-off recording run — Update = true, then commit Tests/Fixtures/Har/payments.har
await Page.RouteFromHARAsync("Tests/Fixtures/Har/payments.har", new PageRouteFromHAROptions
{
    Url = "**/api.stripe.com/**",
    Update = true,
    UpdateMode = HarMode.Minimal,
    UpdateContent = RouteFromHarUpdateContentPolicy.Attach,
});
```

```csharp
// Every CI run — replay. NotFound = Abort makes any un-recorded call a hard failure
// (so a new dependency can't silently slip through to the real network).
[SetUp]
public async Task ReplayPaymentsHar()
{
    await Page.RouteFromHARAsync("Tests/Fixtures/Har/payments.har", new PageRouteFromHAROptions
    {
        Url = "**/api.stripe.com/**",
        NotFound = HarNotFound.Abort,
    });
}
```

`BrowserNewContextOptions.RecordHarPath` (set via the `PageTest` `ContextOptions()` override) captures the **whole** context's traffic for debugging; `RouteFromHARAsync` is the scoped record/replay you want for a specific dependency.

### Offline and latency simulation

```csharp
[Test]
public async Task Shows_The_Offline_Banner_When_The_Network_Drops()
{
    await Page.GotoAsync("/dashboard");
    await Expect(Page.GetByTestId("live-feed")).ToBeVisibleAsync();

    await Context.SetOfflineAsync(true);
    await Page.GetByRole(AriaRole.Button, new() { Name = "Refresh" }).ClickAsync();

    await Expect(Page.GetByRole(AriaRole.Alert))
        .ToContainTextAsync(new Regex("you’re offline", RegexOptions.IgnoreCase));
}
```

Latency injection has **no built-in `route` throttle** — `await Task.Delay` inside the handler. This is the one sanctioned delay in this skill (a *simulated* delay, not a *wait-and-hope*), and it belongs in a helper, not a test:

```csharp
static Task WithLatencyAsync(IPage page, string urlGlob, int ms) =>
    page.RouteAsync(urlGlob, async route =>
    {
        await Task.Delay(ms);
        await route.ContinueAsync();
    });

// Test the loading spinner stays up while /api/orders is slow.
await WithLatencyAsync(Page, "**/api/orders", 1_500);
await Page.GotoAsync("/orders");
await Expect(Page.GetByTestId("orders-spinner")).ToBeVisibleAsync();
```

For real bandwidth/latency emulation (not just per-request delay) use CDP `Network.emulateNetworkConditions` — Chromium-only — covered in `qa/dotnet/skills/network-monitoring`.

## Rules

### Matching
- URL patterns are a **glob** (`*` = any char except `/`; `**` spans `/`; `{a,b}` alternation), a **`Regex`**, or a `Func<string,bool>` predicate. Prefer a glob for path shape, a `Regex` for ids/query specifics.
- **Glob `?` and `[]` (character classes) are not supported** since Playwright 1.43 — use a `Regex` for those.
- **`BaseURL` gotcha:** a string pattern that does **not** start with `*` is resolved against `BaseURL`; a pattern starting with `*`/`**` is treated as a raw glob and is **not** joined to `BaseURL`. Don't write `"/api/orders"` expecting a glob — write `"**/api/orders"`.

### Handler discipline
- A route handler **must call exactly one** of `FulfillAsync` / `AbortAsync` / `ContinueAsync` / `FallbackAsync`. Calling none hangs the request; calling two throws.
- **Handlers run last-registered-first.** The most recent `RouteAsync(...)` wins; use `route.FallbackAsync()` to defer to an earlier handler. `route.ContinueAsync()` goes straight to the network and **skips** the remaining handlers.
- `route.FulfillAsync(new() { Json = obj })` over manual `Body = JsonSerializer.Serialize(...)` + `ContentType` — `Json` sets the header and serializes.
- Serve large mock payloads from a file via `route.FulfillAsync(new() { Path = "Tests/Fixtures/Responses/orders.json" })`, not a giant inline literal.
- `route.Request` is a property (no `Async`); `route.FetchAsync()` is the awaited network call.

### Scope
- `Page.RouteAsync` for one page (handles its popups); `Context.RouteAsync` for **every** page in the context. Page-level routes take precedence over context-level for the same request.
- Mock at the **narrowest** scope that works — context routes that leak across tests are a common source of cross-test contamination. `PageTest` gives a fresh context per test, so prefer `Page.RouteAsync`.

### Assertions & waits
- Use `RunAndWaitForRequestAsync(action, urlOrPredicate)` / `RunAndWaitForResponseAsync(...)` — the **action lambda is the first argument**, so the listener is always armed before the action runs. Never wire a manual `WaitForResponseAsync` *after* the click.
- Use **predicates** to assert method/status/url together: `r => r.Url.Contains("/api/x") && r.Status == 200`.
- Read payloads with `request.PostDataJSON` (a `JsonElement?` property) / `request.Headers` and `await response.JsonAsync()` / `response.Status` — don't re-parse `PostData` by hand.
- **Negative assertions** ("endpoint not called") collect from the `Page.Request` event and assert `Is.Empty` **after** a user-visible completion signal — never after a delay.
- **No `Page.WaitForTimeoutAsync(ms)` as a wait.** The only `Task.Delay` allowed is inside a latency-injection route handler, and only there. Never `Thread.Sleep`, never `.Result`/`.Wait()`.

### HAR
- Record with `Update = true` once, commit, then replay with no `Update`. Re-record in a dedicated PR, never silently in CI.
- Use `RouteFromHarUpdateContentPolicy.Attach` (bodies as files) for reviewable diffs; `HarMode.Minimal` unless you need timings.
- Set `NotFound = HarNotFound.Abort` on replay so an un-recorded request is a hard failure, not a silent hit to the real third party.

### Determinism & hygiene
- If `RouteAsync` mocks are being bypassed, set `ServiceWorkers = ServiceWorkerPolicy.Block` in `ContextOptions()` — a Service Worker can intercept before your route does.
- A route handler is only invoked for the **first** URL of a redirect chain — assert on the final response, not the 30x hop.
- Never put real secrets/tokens in committed mock responses or HAR files — scrub auth headers (use `RecordHarContent = HarContentPolicy.Omit` or a redaction step).

### What NOT to do
- No `Page.WaitForTimeoutAsync(ms)` / `Thread.Sleep` to "wait for the request" — use `RunAndWaitForRequestAsync`/`RunAndWaitForResponseAsync` with a predicate.
- No raw `Page.RouteAsync("**/api/...", ...)` scattered through `[Test]` methods — wrap it in a `MockApi`-style helper with an intent name.
- No handler that calls neither `FulfillAsync`/`AbortAsync`/`ContinueAsync`/`FallbackAsync` (hangs) or two of them (throws).
- No `route.ContinueAsync()` when you meant `route.FallbackAsync()` — `Continue` skips your other handlers.
- No `"/api/orders"` string pattern expecting glob behavior — it gets `BaseURL`-resolved; write `"**/api/orders"`.
- No glob `?`/`[abc]` since 1.43 — switch to a `Regex`.
- No `Body = JsonSerializer.Serialize(x)` + `ContentType = "application/json"` where `Json = x` does the same.
- No giant inline JSON literal as a mock — `route.FulfillAsync(new() { Path = ... })` from a fixture file.
- No silent HAR re-record in CI (`Update = true` left on) — recordings drift and tests stop testing anything.
- No `NotFound = HarNotFound.Fallback` on a third-party HAR replay you intend to be hermetic — it lets un-recorded calls hit the live service.
- No secrets/PII committed inside a mock response or HAR archive.
- No `Context.RouteAsync` for something one page needs — it leaks the mock into every page in the context.
- No asserting "not called" after a fixed delay — gate on a user-visible completion signal.
- No `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` on any Playwright call — async all the way.

## Generation steps

1. Confirm **traffic** (endpoints + glob/regex), **intent** (mock / assert / modify / HAR / offline), and **scope** (page vs context).
2. Add or extend `Tests/Support/Network/MockApi.cs` with one intent-named method per scenario (`StubOrdersAsync`, `FailOrdersWithAsync`, `BlockAnalyticsAsync`). Expose it on `NetworkBaseTest` via `[SetUp]`.
3. For call assertions, use `RequestAssertions.ExpectRequestAsync` (or a direct `RunAndWaitForResponseAsync` predicate); assert payload via `PostDataJSON`.
4. For third-party determinism, record a HAR with `Update = true`, commit it under `Tests/Fixtures/Har/` with `Attach` content, then replay with `NotFound = HarNotFound.Abort`.
5. For offline/latency states, use `Context.SetOfflineAsync(true)` and a `Task.Delay` latency helper — never `WaitForTimeoutAsync`/`Thread.Sleep`.
6. Run `dotnet test`; verify with the trace viewer's Network tab (which requests were routed vs hit the network). Build with nullable warnings as errors for strict-null green.

## Cross-references

- **`qa/typescript/skills/network-monitoring`** — the canonical skill this ports from; consult it for the conceptual model and the glob/Service-Worker notes.
- **`qa/java/skills/network-monitoring`** — the sibling Java port (`route.resume()`, no `setJson`/`json()`).
- **`qa/dotnet/skills/ui-test-author/playwright`** — the `PageTest` base-class / page-object model these network helpers layer on; `RunAndWaitForResponseAsync` ordering and the no-`WaitForTimeoutAsync` discipline originate there.
- **`qa/dotnet/skills/network-monitoring`** — low-level CDP (`Network.emulateNetworkConditions` for real throttling) when `RouteAsync` isn't enough.
- **`qa/dotnet/skills/network-monitoring`** — out-of-browser HTTP capture for multi-process or non-browser traffic.
- **`qa/dotnet/skills/ci-pipelines`** — runs these tests sharded; HAR archives and traces are uploaded as artifacts there.
- **`qa/dotnet/skills/test-data-builder`** — builds the shapes you stub into `route.FulfillAsync(new() { Json = ... })`.
- **`qa/dotnet/skills/api-test-author/generator`** — when the test needs no browser, assert against the API directly.
