# Trace correlation — the app's requests carry the test's trace id

A UI test that fails on a backend error is diagnosed in the backend's trace and logs. The browser sends no
`traceparent` of its own, so the test adds one: **one trace id per test**, a new `parent-id` per request, flags
`01` (W3C Trace Context: `00-<32 hex>-<16 hex>-01`, lowercase). The backend's OpenTelemetry instrumentation
reads it with the default W3C propagator, so every server span the journey caused lands in one trace, and
``qa/reporting/dotnet/skills/test-reports`` (`references/trace-links.md`) links that trace and its logs from the failed result.

## App-origin requests only

The header is added by a **context route scoped to the origins the team owns** — the app's (`BASE_URL`), plus
the API's when the front end calls another host. Never by `extraHTTPHeaders`: that sends the header with every
request the page makes, to analytics, fonts, CDNs and identity providers, leaking a correlation id to third
parties and, on a cross-origin call, triggering CORS preflights the real app never makes.

- The handler ends in `fallback` with the merged headers, never `continue`: a route registered later in a test
  (a mock from `network-mocking`) runs first and still decides the response; a request it lets through
  reaches this handler and gets the header. A test handler that ends in `continue` sends its request without
  it — use `fallback` there too.
- The predicate compares the origin plus `/`, so `https://app.test.evil.com` never matches `https://app.test`.
- Enabling routing disables the browser's HTTP cache for the context, and requests a Service Worker
  intercepts are not routed. A suite measuring caching or testing a PWA's offline mode leaves this off for
  those tests.
- API seeding through the context's request client (``Context.APIRequest``) is not routed. Seeding is not what the test
  asserts; it stays outside the trace.

## `BaseTest` — at the end of its `[SetUp]`

Added to the existing `StartTracing` `[SetUp]` rather than a second one: NUnit does not order two `[SetUp]`
methods of one class.

```csharp
private string _traceId = string.Empty;

[SetUp]
public async Task StartTracing()
{
    await Context.Tracing.StartAsync(new()
    {
        Title = TestContext.CurrentContext.Test.FullName,
        Screenshots = true,
        Snapshots = true,
        Sources = true,
    });
    await CorrelateTracesAsync();
}

private async Task CorrelateTracesAsync()
{
    _traceId = ActivityTraceId.CreateRandom().ToHexString();
    TestContext.Out.WriteLine($"trace-id {_traceId}");
    var appOrigin = new Uri(RequiredEnv("BASE_URL")).GetLeftPart(UriPartial.Authority);
    await Context.RouteAsync(url => url.StartsWith(appOrigin + "/", StringComparison.Ordinal), async route =>
    {
        var headers = new Dictionary<string, string>(route.Request.Headers)
        {
            ["traceparent"] = $"00-{_traceId}-{ActivitySpanId.CreateRandom().ToHexString()}-01",
        };
        await route.FallbackAsync(new() { Headers = headers });
    });
}
```

`ActivityTraceId` and `ActivitySpanId` (`System.Diagnostics`) produce lowercase hex of the W3C lengths. In
`KeepEvidenceOnFailure`, inside its `if (failed)` branch, attach the links with the helper from
`test-reports`:

```csharp
var links = TelemetryLinks.UriList(_traceId);
if (links is not null)
{
    AllureApi.AddAttachment("telemetry", "text/uri-list", Encoding.UTF8.GetBytes(links), ".uri");
}
```

A second owned origin is a second `RouteAsync` with the API's origin and the same handler.

## Rules

- One trace id per test, recorded where the failure is read (test output or annotation, and the `telemetry`
  attachment); a new `parent-id` per request; flags `01`.
- The route matches owned origins only. Never `extraHTTPHeaders` for `traceparent` in a UI test.
- The route is added once per test, by the base class or fixture, never per spec.
