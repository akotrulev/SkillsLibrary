# Trace correlation — the app's requests carry the test's trace id

A UI test that fails on a backend error is diagnosed in the backend's trace and logs. The browser sends no
`traceparent` of its own, so the test adds one: **one trace id per test**, a new `parent-id` per request, flags
`01` (W3C Trace Context: `00-<32 hex>-<16 hex>-01`, lowercase). The backend's OpenTelemetry instrumentation
reads it with the default W3C propagator, so every server span the journey caused lands in one trace, and
``qa/reporting/java/skills/test-reports`` (`references/trace-links.md`) links that trace and its logs from the failed result.

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
- API seeding through the context's request client (``page.request()``) is not routed. Seeding is not what the test
  asserts; it stays outside the trace.

## `BaseTest` — in `openContext()`, after the context is created

Added to the existing `@BeforeMethod` rather than a second one: TestNG does not order two `@BeforeMethod`
methods of one class.

```java
private static final SecureRandom RANDOM = new SecureRandom();
private static final HexFormat HEX = HexFormat.of();
private String traceId;

@BeforeMethod(alwaysRun = true)
public void openContext() {
    context = browser.newContext(contextOptions()
            .setBaseURL(requiredEnv("BASE_URL"))
            .setRecordVideoDir(RAW_VIDEOS));
    correlateTraces();
    context.tracing().start(new Tracing.StartOptions()
            .setScreenshots(true)
            .setSnapshots(true)
            .setSources(true));
    page = context.newPage();
}

private void correlateTraces() {
    traceId = randomHex(16);
    URI base = URI.create(requiredEnv("BASE_URL"));
    String appOrigin = base.getScheme() + "://" + base.getRawAuthority();
    context.route(url -> url.startsWith(appOrigin + "/"), route -> {
        Map<String, String> headers = new HashMap<>(route.request().headers());
        headers.put("traceparent", "00-" + traceId + "-" + randomHex(8) + "-01");
        route.fallback(new Route.FallbackOptions().setHeaders(headers));
    });
}

private static String randomHex(int bytes) {
    byte[] buffer = new byte[bytes];
    RANDOM.nextBytes(buffer);
    return HEX.formatHex(buffer);
}
```

In `closeContext(ITestResult result)`, inside its first `if (failed)` branch, attach the links with the
helper from `test-reports`:

```java
TelemetryLinks.uriList(traceId).ifPresent(links ->
        Allure.attachment("telemetry", "text/uri-list", links, AttachmentOptions.withFileExtension("uri")));
```

The `traceId` field is per test because the context is: `parallel="classes"` runs one class's methods on one
thread. A second owned origin is a second `context.route` with the API's origin and the same handler.

## Rules

- One trace id per test, recorded where the failure is read (test output or annotation, and the `telemetry`
  attachment); a new `parent-id` per request; flags `01`.
- The route matches owned origins only. Never `extraHTTPHeaders` for `traceparent` in a UI test.
- The route is added once per test, by the base class or fixture, never per spec.
