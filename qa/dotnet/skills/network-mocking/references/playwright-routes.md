# QA — Playwright Routing, Mocking and Traffic Assertions (.NET 10 / Microsoft.Playwright 1.63 + NUnit)

Intercepts, mocks, holds, asserts and shapes HTTP traffic in Playwright for .NET with NUnit. Every sample
derives from `Example.UiTests.Support.BaseTest` (`qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs`),
which owns the browser, a context and page per test, and the failure evidence. Route handlers and traffic
reads live in two helpers, `MockApi` and `Traffic`, built in the class's own `[SetUp]`; a test calls intent
methods, never `Page.RouteAsync(...)`. Every wait is a request or response predicate or a page object's
completion signal. Async all the way: every Playwright call is awaited, never `.Result` or `.Wait()`.

## When to use

- Mock a backend or third-party response so a UI test is deterministic — canned JSON, a forced `500`.
- **Assert** an endpoint was called, with the expected method and payload — or was **not** called.
- Assert the app shell's **security headers** and **TLS** details.
- Modify a real response in flight (force a feature flag) or tag an outgoing request.
- Replay a committed HAR of a third-party dependency.
- Show the loading state while a request is **held**, or the offline state.

## When NOT to use

- Real bandwidth and latency, cache disable, CPU throttling, performance metrics → `references/cdp.md`
- A client with no Playwright `IPage` (Selenium, Appium, `HttpClient`) → `references/proxy.md`
- Recording a HAR as evidence → `qa/dotnet/skills/evidence-capture` §5
- WebSocket and SSE → `qa/dotnet/skills/realtime-stream-testing`
- No browser at all → `qa/dotnet/skills/api-test-author`
- Writing the page objects themselves → `qa/dotnet/skills/ui-test-author/playwright`

## Inputs needed

1. **What traffic** — the endpoint(s) as a glob or `Regex`, first-party or third-party.
2. **Intent** — mock, hold, assert called / not called, modify, HAR replay, offline, headers or TLS.
3. **Scope** — the test's page (`Page.RouteAsync`) or every page of the context including popups
   (`Context.RouteAsync`).

## Decision matrix

| Goal | Call | Note |
|---|---|---|
| Canned data, never hit the network | `route.FulfillAsync(new() { Status = 200, ContentType = "application/json", Body = json })` | `Json = obj` also works but serializes with System.Text.Json **defaults** — PascalCase for C# records (§1) |
| A forced error | `route.FulfillAsync(new() { Status = 500, … })` | The app's error path becomes deterministic |
| Block a resource | `route.AbortAsync("blockedbyclient")` | Analytics, ads, fonts |
| Let it through unchanged | `route.ContinueAsync()` | Goes to the network and **skips** the remaining handlers |
| Defer to an earlier handler | `route.FallbackAsync()` | Chains to the next matching handler |
| Modify a real response | `route.FetchAsync()` → edit `TextAsync()` → `route.FulfillAsync(new() { Response = response, Body = … })` | Keeps the real status and headers |
| Tag the outgoing request | `route.ContinueAsync(new() { Headers = headers })` | A `Cookie` header set here is ignored since 1.52 |
| Hold a request, release it later | a handler that awaits a `TaskCompletionSource`, then continues | Playwright dispatches each route without blocking the others (§8) |
| Assert a call happened | `Page.RunAndWaitForRequestAsync(action, glob)` / `RunAndWaitForResponseAsync(action, predicate)` in a page object | The action runs **inside** the wait |
| Assert a call did not happen | `Page.RequestsAsync()` after the completion signal | The page's recent requests; no listener |
| Security headers, TLS | `response.AllHeadersAsync()`, `response.SecurityDetailsAsync()` | Cross-browser; no CDP |
| Deterministic third party | `Page.RouteFromHARAsync(har, new() { Url = …, NotFound = HarNotFound.Abort })` | Update deliberately (§7) |
| Offline | `Context.SetOfflineAsync(true)` | Cross-browser |

## 1. The helpers

`MockApi` owns every route; `Traffic` reads what the page sent. Both wrap the `IPage` `BaseTest` opened and
own no lifecycle — the context, and with it every route, is closed after each test.

```csharp
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Microsoft.Playwright;

namespace Example.UiTests.Support;

public sealed record Order(string Id, string Status, long TotalMinor);

public sealed record CheckoutRequest(long TotalMinor, string Currency);

public sealed class MockApi(IPage page)
{
    private static readonly string PaymentsHar = Path.Combine(ProjectPaths.Root, "Fixtures", "Har", "payments.har");
    private static readonly bool HarUpdate = Environment.GetEnvironmentVariable("HAR_UPDATE") == "1";

    public Task StubOrdersAsync(IReadOnlyList<Order> orders) =>
        page.RouteAsync("**/api/orders", route => FulfillJsonAsync(route, 200, "application/json", orders));

    public Task FailOrdersWithAsync(int status) =>
        page.RouteAsync("**/api/orders", route => FulfillJsonAsync(route, status, "application/problem+json", new { title = "Simulated failure", status }));

    public Task BlockAnalyticsAsync() =>
        page.Context.RouteAsync(new Regex(@"google-analytics\.com|segment\.io"), route => route.AbortAsync("blockedbyclient"));

    public Task EnableFlagAsync(string flag) =>
        page.RouteAsync("**/api/feature-flags", async route =>
        {
            var response = await route.FetchAsync();
            var flags = JsonNode.Parse(await response.TextAsync())!.AsObject();
            flags[flag] = true;
            await route.FulfillAsync(new() { Response = response, Body = flags.ToJsonString() });
        });

    public Task TagTenantAsync(string tenantId) =>
        page.RouteAsync("**/api/**", route => route.ContinueAsync(new()
        {
            Headers = new Dictionary<string, string>(route.Request.Headers) { ["x-test-tenant"] = tenantId },
        }));

    public async Task<HeldRequests> HoldOrdersAsync()
    {
        var held = new HeldRequests();
        await page.RouteAsync("**/api/orders", held.HoldAsync);
        return held;
    }

    public Task ReplayPaymentsAsync() =>
        page.RouteFromHARAsync(PaymentsHar, new()
        {
            Url = "https://api.stripe.com/**",
            NotFound = HarNotFound.Abort,
            Update = HarUpdate,
            UpdateContent = RouteFromHarUpdateContentPolicy.Attach,
            UpdateMode = HarMode.Minimal,
        });

    public Task GoOfflineAsync() => page.Context.SetOfflineAsync(true);

    private static Task FulfillJsonAsync(IRoute route, int status, string contentType, object payload) =>
        route.FulfillAsync(new()
        {
            Status = status,
            ContentType = contentType,
            Body = JsonSerializer.Serialize(payload, JsonSerializerOptions.Web),
        });

    public sealed class HeldRequests
    {
        private readonly TaskCompletionSource _released = new(TaskCreationOptions.RunContinuationsAsynchronously);

        internal async Task HoldAsync(IRoute route)
        {
            await _released.Task;
            await route.ContinueAsync();
        }

        public void Release() => _released.TrySetResult();
    }
}
```

```csharp
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Playwright;

namespace Example.UiTests.Support;

public sealed class Traffic(IPage page)
{
    public async Task<IReadOnlyList<string>> RequestedUrlsAsync(Regex url) =>
        (await page.RequestsAsync()).Select(request => request.Url).Where(url.IsMatch).ToList();

    public Task<IReadOnlyList<string>> PageErrorsAsync() => page.PageErrorsAsync();

    public static T JsonBody<T>(IRequest request) =>
        request.PostDataJSON()?.Deserialize<T>(JsonSerializerOptions.Web)
        ?? throw new InvalidOperationException($"{request.Method} {request.Url} has no JSON body; post data: {request.PostData}");
}
```

- **JSON naming.** `RouteFulfillOptions.Json` serializes with `JsonSerializer.Serialize(json)` and default
  options (playwright-dotnet v1.63.0, `Route.cs`), so a C# record goes out as `{"TotalMinor":…}`. An API that
  speaks camelCase gets `JsonSerializerOptions.Web` through `FulfillJsonAsync`, and reads back through
  `Traffic.JsonBody` with the same options. A large payload is a fixture file:
  `route.FulfillAsync(new() { Path = Path.Combine(ProjectPaths.Root, "Fixtures", "Responses", "orders.json") })`.
- **`PostDataJSON()` is a method** returning `JsonElement?` — not a property. `JsonBody` deserializes it into
  the record, and a body that is not JSON fails with the method, the URL and the raw post data in the message.
- **`ProjectPaths.Root`** is the project folder, written into the test assembly at build time — the same
  helper `qa/dotnet/skills/visual-regression`'s `references/playwright-snapshots.md` §1 adds for baselines.
  `dotnet test` runs from `bin/<cfg>/net10.0/`, so a relative fixture path would read a copy and a HAR update
  would write into `bin/`:

  ```xml
  <ItemGroup>
    <AssemblyAttribute Include="System.Reflection.AssemblyMetadataAttribute">
      <_Parameter1>ProjectDirectory</_Parameter1>
      <_Parameter2>$(MSBuildProjectDirectory)</_Parameter2>
    </AssemblyAttribute>
  </ItemGroup>
  ```

  ```csharp
  using System.Reflection;

  namespace Example.UiTests.Support;

  public static class ProjectPaths
  {
      public static readonly string Root = typeof(ProjectPaths).Assembly
          .GetCustomAttributes<AssemblyMetadataAttribute>()
          .Single(attribute => attribute.Key == "ProjectDirectory")
          .Value!;
  }
  ```
- The payload records sit next to the helpers; a payload with four or more fields gets a builder
  (`qa/dotnet/skills/test-data-builder`).

## 2. Mocking a response

```csharp
using Example.UiTests.Pages;
using Example.UiTests.Support;
using NUnit.Framework;

namespace Example.UiTests.Tests;

public class OrdersNetworkTests : BaseTest
{
    private MockApi _mockApi = null!;
    private OrdersPage _ordersPage = null!;

    [SetUp]
    public void CreateHelpers()
    {
        _mockApi = new MockApi(Page);
        _ordersPage = new OrdersPage(Page);
    }

    [Test]
    public async Task Should_ShowEmptyState_When_ThereAreNoOrders()
    {
        await _mockApi.StubOrdersAsync([]);

        await _ordersPage.NavigateAsync();

        await Expect(_ordersPage.EmptyState, "orders empty state").ToBeVisibleAsync();
    }

    [Test]
    public async Task Should_ShowErrorBanner_When_OrdersApiFails()
    {
        await _mockApi.FailOrdersWithAsync(500);

        await _ordersPage.NavigateAsync();

        await Expect(_ordersPage.ErrorBanner, "orders error banner").ToHaveTextAsync("We couldn't load your orders");
    }
}
```

- `_mockApi` is a field built in `[SetUp]`, which NUnit runs after `BaseTest` opened the page. Register the
  route **before** the navigation or action that fires the request; a route added afterwards catches nothing.
- `OrdersPage.NavigateAsync()` only navigates; `OpenAsync()` navigates and returns once the list is visible.
  The difference matters in §8, where the list never arrives while a request is held. `GotoAsync("/orders")`
  resolves against `BaseTest`'s `BaseURL`.
- Every locator the page object returns carries `Describe(...)`, and `Expect(locator, "message")` [1.60] names
  the subject in a failure.
- §3–§8 are further tests of classes shaped like this one: `_cartPage`, `_appShellPage` and
  `_traffic = new Traffic(Page)` are fields built in the same `[SetUp]`.

## 3. Asserting a call — method and typed payload

The page object starts the wait and performs the action in one call, so the request cannot fire first:

```csharp
public Task<IRequest> PlaceOrderAsync() =>
    _page.RunAndWaitForRequestAsync(() => _placeOrder.ClickAsync(), "**/api/checkout");
```

```csharp
[Test]
public async Task Should_PostCartTotal_When_OrderIsPlaced()
{
    await _cartPage.OpenAsync();

    var checkout = await _cartPage.PlaceOrderAsync();

    Assert.Multiple(() =>
    {
        Assert.That(checkout.Method, Is.EqualTo("POST"), $"checkout request method; post data: {checkout.PostData}");
        Assert.That(Traffic.JsonBody<CheckoutRequest>(checkout), Is.EqualTo(new CheckoutRequest(15_000, "EUR")), "checkout request body");
    });
}
```

- The two assertions are one behaviour — "the order is posted with the cart total" — and `Assert.Multiple`
  reports both. Record equality compares every field, and NUnit prints both records on a mismatch, so the
  payload is in the failure — never `Assert.That(bodyMatches(…), Is.True)`, which drops it.
- For "it was called and answered", `RunAndWaitForResponseAsync(action, response => …)` returns the
  `IResponse`; assert its exact `Status` with the body as the message
  (`ui-test-author/playwright/references/assertions.md` §7).

## 4. Asserting a call did NOT happen, and that the page raised no errors

```csharp
[Test]
public async Task Should_NotCallLegacyPricing_When_CartIsRecalculated()
{
    await _cartPage.OpenAsync();

    await _cartPage.RecalculateAsync();

    Assert.That(await _traffic.RequestedUrlsAsync(new Regex("/api/legacy-pricing")), Is.Empty, "legacy pricing calls");
}

[Test]
public async Task Should_RaiseNoPageErrors_When_CartOpens()
{
    await _cartPage.OpenAsync();

    Assert.That(await _traffic.PageErrorsAsync(), Is.Empty, "uncaught errors on the cart page");
}
```

- `RecalculateAsync()` returns once the new total is visible. The list is read **after** that signal, or the
  check passes only because the request had not fired yet.
- `Page.RequestsAsync()`, `ConsoleMessagesAsync()` and `PageErrorsAsync()` [1.56] return the page's most recent
  buffered items — no listener to register, no list to manage. The buffer is capped (100 requests, 200 console
  messages and errors in 1.63), so for a long flow subscribe to `Page.Request` in the class's `[SetUp]` and
  collect into a `ConcurrentQueue<string>` instead.
- Each page has its own buffer: a popup's traffic is read from the popup's `IPage`.

## 5. Security headers and TLS — at the routing layer

The page object's `OpenAsync()` returns the `IResponse` that `GotoAsync` gave it — the document, after any
redirects:

```csharp
[Test]
public async Task Should_SendSecurityHeaders_When_AppShellLoads()
{
    var shell = await _appShellPage.OpenAsync();

    var headers = await shell.AllHeadersAsync();

    Assert.That(headers.Keys, Is.SupersetOf(new[] { "content-security-policy", "strict-transport-security", "x-frame-options" }), "security headers on the app shell");
}

[Test]
public async Task Should_NegotiateTls13_When_AppShellLoads()
{
    var shell = await _appShellPage.OpenAsync();

    var tls = await shell.SecurityDetailsAsync();

    Assert.That(tls?.Protocol, Is.EqualTo("TLS 1.3"), $"TLS details of {shell.Url}: issuer {tls?.Issuer}, subject {tls?.SubjectName}");
}
```

- `AllHeadersAsync()` returns every response header with **lower-cased** names, including the ones the
  `Headers` property omits; `HeaderValueAsync(name)` reads one case-insensitively. NUnit's superset failure
  prints the keys that were there.
- `SecurityDetailsAsync()` returns a `ResponseSecurityDetailsResult` (`Protocol`, `Issuer`, `SubjectName`,
  `ValidFrom`, `ValidTo`) — or `null` over plain HTTP, which the assertion reports as `null` instead of a
  `NullReferenceException`.
- Both checks are cross-browser. CDP is not needed for either.

## 6. Modifying traffic in flight

- **The response:** `_mockApi.EnableFlagAsync("betaCheckout")` fetches the real flags and re-serves them with
  one flag forced. Passing the `IAPIResponse` as `Response` keeps the real status and headers.
- **The request:** `_mockApi.TagTenantAsync("tenant-42")` adds a header. A `Cookie` header set through
  `route.ContinueAsync` is ignored since 1.52 — add the cookie with `Context.AddCookiesAsync(...)` in the class's
  `[SetUp]`.

## 7. HAR replay and update

- `_mockApi.ReplayPaymentsAsync()` serves `https://api.stripe.com/**` from the committed
  `UiTests/Fixtures/Har/payments.har`. `HarNotFound.Abort` turns any request the HAR does not hold into a
  failure, so a new dependency cannot slip through to the live service; `HarNotFound.Fallback` would let it.
- **Updating** is a deliberate, local run against the real dependency:
  `HAR_UPDATE=1 dotnet test UiTests --filter "FullyQualifiedName~PaymentsTests"`. With `Update = true` the
  requests reach the network and the HAR is written when the context closes — which `BaseTest` does after the
  test — into the project folder, through `ProjectPaths.Root`. Commit it in a dedicated PR; never update in CI.
- `UpdateContent = RouteFromHarUpdateContentPolicy.Attach` stores bodies as separate files (reviewable diffs);
  `UpdateMode = HarMode.Minimal` keeps only what replay needs. The **recording** options —
  `Context.Tracing.StartHarAsync(path, options)` [1.60] per test, or `RecordHarPath` in the class's
  `ContextOptions()` — are evidence, owned by `qa/dotnet/skills/evidence-capture` §5.
- Scrub tokens, cookies and personal data from a committed HAR; record against disposable test accounts.

## 8. Offline, and a request held in flight

```csharp
[Test]
public async Task Should_ShowOfflineBanner_When_NetworkDrops()
{
    await _ordersPage.OpenAsync();

    await _mockApi.GoOfflineAsync();
    await _ordersPage.RefreshAsync();

    await Expect(_ordersPage.OfflineBanner, "offline banner").ToHaveTextAsync("You are offline");
}

[Test]
public async Task Should_KeepSpinnerVisible_When_OrdersAreStillInFlight()
{
    await _mockApi.HoldOrdersAsync();

    await _ordersPage.NavigateAsync();

    await Expect(_ordersPage.Spinner, "orders spinner").ToBeVisibleAsync();
}

[Test]
public async Task Should_ShowOrders_When_HeldRequestIsReleased()
{
    var orders = await _mockApi.HoldOrdersAsync();
    await _ordersPage.NavigateAsync();

    orders.Release();

    await Expect(_ordersPage.List, "orders list").ToBeVisibleAsync();
}
```

- **Holding is how a test shows a slow response.** The handler awaits the `TaskCompletionSource` and only then
  continues the route. playwright-dotnet dispatches every route on its own task (`_ = OnRouteAsync(route)` in
  v1.63.0's `Page.cs`) and waits for the route to be handled (`RouteHandler.HandleInternalAsync`), so a held
  route blocks nothing else — the page keeps loading, the assertions keep polling. The loading state is
  observable for as long as the test needs, with no timing in the test at all.
- `Release()` lets the request go to the network. A held request that is never released ends with the context,
  which `BaseTest` closes after the test.
- **Never `Task.Delay(ms)` in a handler** as a "slow" response: the test then races a number — too short and the
  spinner is gone before the assertion, too long and the suite slows down — and `Thread.Sleep` would also block a
  thread-pool thread.
- **Real bandwidth and latency** — a page that must load *slowly* rather than *not yet* — is CDP's
  `Network.emulateNetworkConditions`, Chromium-only, in `references/cdp.md`.
- **A delay the client must time out on** (a request that answers after the app's 10-second timeout) belongs
  to the server: a test endpoint or a stub server that delays on purpose.

## Rules

### Matching

- A URL matcher is a **glob** (`*` matches any character except `/`; `**` spans `/`; `{a,b}` alternates), a
  `Regex`, or a `Func<string, bool>`.
- **Glob `?` and `[]` are not supported since Playwright 1.52** — use a `Regex` for a single-character
  wildcard or a character class.
- **The base URL gotcha:** a string that does not start with `*` is resolved against the context's `BaseURL`;
  one that starts with `*` / `**` is a raw glob. Write `"**/api/orders"`, not `"/api/orders"` expecting a glob.

### Handlers

- A handler calls **exactly one** of `FulfillAsync`, `AbortAsync`, `ContinueAsync`, `FallbackAsync` — now, or
  later on a held route. None, and the request waits forever; two, and the second throws.
- Handlers run **last registered first**. `FallbackAsync()` defers to the next matching handler;
  `ContinueAsync()` goes straight to the network and skips them.
- `route.Request` is a property; `route.FetchAsync()` is the awaited network call.

### Scope

- `Page.RouteAsync` covers that page only. A popup is a new page, so a mock it needs is
  `Context.RouteAsync(...)`. `BaseTest` gives each test a fresh context, so a context route cannot leak into
  the next test.
- A service worker can answer before a route does: `options.ServiceWorkers = ServiceWorkerPolicy.Block` in the
  class's `ContextOptions()` (amending `base.ContextOptions()`) when mocks are bypassed.
- A route sees only the first request of a redirect chain — assert on the final response.

### Assertions and waits

- `RunAndWaitForRequestAsync(action, matcher)` / `RunAndWaitForResponseAsync(action, matcher)` in a page
  object — the action runs inside the wait. Never a listener registered after the click.
- "Not called" reads `Page.RequestsAsync()` after a user-visible completion signal.
- Non-locator values — a method, a parsed body, a header set — are `Assert.That` with one expected value and
  a message carrying the evidence.

## What NOT to do

- No `Task.Delay` or `Thread.Sleep` in a route handler or a test — hold the request, throttle with CDP, or
  delay the server.
- No `Page.RouteAsync(...)` or `Page.GotoAsync(...)` in a `[Test]` method — a `MockApi` method and a page
  object.
- No `request.PostDataJSON!.Value` — it is a method, `PostDataJSON()`.
- No `Assert.That(predicate(body), Is.True, "payload did not match")` — deserialize and compare records.
- No glob `?` or `[abc]` — a `Regex`.
- No `"/api/orders"` string expecting glob behaviour.
- No giant inline JSON literal — a record, or a fixture file under `ProjectPaths.Root`.
- No `Update = true` left on in CI; no `HarNotFound.Fallback` on a replay meant to be hermetic.
- No security-header or TLS audit through CDP — `AllHeadersAsync()` and `SecurityDetailsAsync()` cover it.
- No `ContextOptions()` override that returns `new()` — amend `base.ContextOptions()`.
- No secrets in a mock or a committed HAR.

## Generation steps

1. Confirm the **traffic**, the **intent** and the **scope**.
2. Add one intent-named method per scenario to `MockApi`; read requests through `Traffic` or a page-object
   method that wraps `RunAndWaitForRequestAsync` / `RunAndWaitForResponseAsync`.
3. Build both helpers and the page objects in the test class's `[SetUp]`.
4. For a third party, replay a committed HAR with `HarNotFound.Abort`; update it with `HAR_UPDATE=1`, locally.
5. For loading and offline states, hold the request or go offline — never a sleep.
6. Read a failure's trace (`qa/dotnet/skills/evidence-capture`, "Reading a failure"): its network view shows
   which requests were routed and which reached the network.

## Cross-references

- `references/cdp.md` — real throttling, cache disable, CPU throttling, metrics (Chromium only).
- `references/proxy.md` — a client with no Playwright `IPage`.
- `qa/dotnet/skills/ui-test-author/playwright` — `BaseTest`, page objects, `references/assertions.md` §7.
- `qa/dotnet/skills/evidence-capture` — HAR recording, traces.
- `qa/dotnet/skills/realtime-stream-testing` — WebSocket and SSE.
- `qa/dotnet/skills/test-data-builder` — builders for the payloads the mocks serve.
- `qa/cicd/dotnet/skills/ci-pipelines` — the UI job and its artifact upload.
- `qa-typescript:network-mocking`, `qa-java:network-mocking` — the sibling lanes.
