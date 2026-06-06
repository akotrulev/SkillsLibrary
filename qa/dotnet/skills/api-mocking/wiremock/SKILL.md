---
name: qa-api-mocking-wiremock-dotnet
description: >-
  Service-virtualization / API-mocking with WireMock.Net in .NET (NUnit): stand up a standalone HTTP
  server that returns stubbed responses for matched requests, point the system-under-test's typed client
  at the server's base URL, exercise the flow, then assert (via `server.FindLogEntries(...)`) the SUT
  called the dependency as expected. Use when a test must run against a controlled fake of a downstream
  HTTP dependency (flaky, unavailable, rate-limited, or costly) instead of the real service —
  `WireMockServer.Start()`, `server.Given(Request.Create().WithPath(...).UsingGet()).RespondWith(
  Response.Create().WithStatusCode(200).WithBodyAsJson(...))`, request matching (URL/method/headers/query
  /body JSON/JSONPath), response definition + Handlebars templating, fault & delay injection
  (`WithDelay`/`WithFault`), stateful **scenarios** (`.InScenario(...).WhenStateIs(...).WillSetStateTo(...)`),
  request verification via `server.LogEntries`/`FindLogEntries`, record-&-playback (proxy), and run modes
  (in-process / standalone / container). Triggers: "mock the payment API with WireMock.Net", "fake a
  downstream service for this integration test", "WireMock returns 202 then 200", "verify our HttpClient
  POSTed the right body", "inject a 500 / timeout / connection-drop from a stubbed dependency". Do NOT use
  for: in-browser request interception with a Playwright `page` (use qa-network-monitoring-playwright-routes-dotnet),
  an out-of-browser MITM proxy over a real client's live traffic (use qa-network-monitoring-proxy-dotnet),
  the Java stack (use qa-api-mocking-wiremock-java), or the TypeScript stack (use
  qa-api-mocking-wiremock-typescript). Sibling tools in this family: MSW (qa-api-mocking-msw-*),
  Mountebank, Prism.
---

# API Mocking — WireMock.Net (.NET / NUnit)

The .NET port of the canonical `qa-api-mocking-wiremock-java`. Same model (a standalone HTTP server that
fakes a downstream dependency), same lifecycle, same matcher → response → verify shape — re-expressed in
`WireMock.Net` + NUnit idioms. `WireMock.Net` is a **faithful, idiomatic .NET reimplementation** of
WireMock (a different codebase, not a binding): `WireMockServer.Start()`, the fluent
`Given(Request.Create()...).RespondWith(Response.Create()...)` DSL, scenarios, and a `LogEntries`-based
verification model.

WireMock is an **HTTP service-virtualization / API-mocking server**: a real HTTP server you stand up so
your tests run against a **controlled fake** of a downstream dependency instead of the real service —
which may be flaky, unavailable in CI, rate-limited, or costly. You register **stub mappings** (a request
matcher → a response definition), point the SUT's `HttpClient`/typed client at the server's base URL,
exercise the flow, then **verify** the SUT called the dependency the way you expected.

> **The boundary that defines this skill.** WireMock is a **standalone HTTP server you point a client at**
> — not an in-process hook into a browser. That is the sharp line against the `network-monitoring`
> family: `qa-network-monitoring-playwright-routes-dotnet` intercepts requests *inside a Playwright
> `page`* (no separate server, browser-only), and `qa-network-monitoring-proxy-dotnet` is an
> *out-of-browser MITM proxy* sitting on a real client's live traffic. WireMock owns the other end of the
> wire: it **is** the dependency, fully under the test's control.

## Decision matrix — WireMock vs the rest of the `api-mocking` family, vs network-monitoring

| Need | Use | Why |
|------|-----|-----|
| A **standalone HTTP server** that fakes a downstream dependency; rich request matching + stateful scenarios + verification; first-class in **every** stack | **WireMock (this skill)** | JVM-born; `WireMock.Net` is a mature, idiomatic .NET reimplementation |
| Intercept **browser** requests inside a Playwright test, no separate server | `qa-network-monitoring-playwright-routes-dotnet` (#8) | `page.route` lives in the browser; no server to point at |
| Observe / rewrite a **real client's** live traffic out-of-browser (MITM) | `qa-network-monitoring-proxy-dotnet` (#10) | Proxy sits on the wire to the *real* service; WireMock replaces it |
| Mock `fetch`/XHR in a **browser or Node** app via the request layer | MSW (`qa-api-mocking-msw-*`, #23) | Request-interception in the app's own runtime, not a separate server |
| **Protocol-agnostic** over-the-wire imposters (TCP/HTTP/SMTP), language-neutral | Mountebank (#24) | Multi-protocol; heavier than an HTTP-only stub server |
| Mock derived **from an OpenAPI spec** automatically | Prism (#25) | Spec-driven; the contract *is* the mock |

**Rule of thumb:** *Need a fake HTTP dependency you fully control and assert against, from any stack?*
→ WireMock. *Need to touch a real browser's or real service's traffic?* → the network-monitoring family.

## Stack

- .NET 8 + NUnit (`NUnit`, `NUnit3TestAdapter`)
- `WireMock.Net` (the in-process `WireMockServer`) — `WireMock.Net.Testcontainers` for the container mode
- A typed API client (`qa-api-client-writer-dotnet`) is the SUT — **constructor-injected** with the base
  address (an `HttpClient` whose `BaseAddress` = the mock's URL)
- `using WireMock.Server; using WireMock.RequestBuilders; using WireMock.ResponseBuilders; using
  WireMock.Matchers;`

## The WireMock model — lifecycle

A `WireMockServer` is a real HTTP server. The lifecycle of every test that uses it:

1. **Start** the server on a random (or fixed) port — `WireMockServer.Start()`.
2. **Register stub mappings** — `server.Given(Request.Create()...).RespondWith(Response.Create()...)`.
3. **Point the SUT at the server's base URL** — `server.Url` (e.g. `http://localhost:54321`), injected
   into the client's `HttpClient.BaseAddress`.
4. **Exercise** the SUT so it calls the dependency.
5. **Verify** the SUT sent the requests you expected — `server.FindLogEntries(...)` / `server.LogEntries`.
6. **Reset / stop** — `server.Reset()` between tests, `server.Stop()`/`Dispose()` at teardown.

### Per-fixture vs per-test lifecycle (the same trade-off as Testcontainers)

Mirror the lifecycle trade-off from `qa-db-testing-testcontainers-dotnet`:

- **One server per fixture** (`[OneTimeSetUp]`/`[OneTimeTearDown]`), `server.Reset()` in `[TearDown]` —
  fastest, but you **must** reset between tests so stubs/recorded requests don't leak. Default; tests
  stay independent because state is reset.
- **One server per test** (`[SetUp]`/`[TearDown]`) — maximal isolation, no reset needed, slower.

```csharp
public abstract class WireMockTestBase
{
    protected WireMockServer Server = null!;
    protected WidgetApiClient Client = null!;

    [OneTimeSetUp]
    public void StartServer()
    {
        Server = WireMockServer.Start();   // dynamic port
        // The SUT's typed client is constructor-injected with the mock's base address — never a static URL.
        var http = new HttpClient { BaseAddress = new Uri(Server.Url!) };
        Client = new WidgetApiClient(http);
    }

    [TearDown]
    public void ResetServer() => Server.Reset();   // wipe stubs + log entries so each test starts clean

    [OneTimeTearDown]
    public void StopServer() => Server.Stop();
}
```

## Core pattern — stub, point the client, exercise, verify

The SUT is a typed client constructor-injected with the base address (cross-link
`qa-api-client-writer-dotnet`). The test stubs the dependency, drives the client `async`, asserts the
**response** (one logical assertion), and verifies the **request** the client sent.

```csharp
using WireMock.RequestBuilders;
using WireMock.ResponseBuilders;
using static WireMock.Matchers.MatchBehaviour;

public class WidgetLookupTests : WireMockTestBase
{
    [Test]
    public async Task Should_return_the_widget_When_the_service_responds_200()
    {
        // 1. Stub: matcher → response definition.
        Server
            .Given(Request.Create().WithPath("/api/widgets/42").UsingGet()
                .WithHeader("Accept", new WildcardMatcher("*application/json*")))
            .RespondWith(Response.Create()
                .WithStatusCode(200)
                .WithHeader("Content-Type", "application/json")
                .WithBodyAsJson(new { id = 42, name = "Sprocket", priceMinor = 1999 }));

        // 2. Exercise the SUT (already pointed at Server.Url).
        var widget = await Client.GetWidgetAsync(42);

        // 3. Assert the response (one logical assertion).
        Assert.That(widget, Is.EqualTo(new Widget(42, "Sprocket", 1999)));

        // 4. Verify the request the SUT actually sent.
        var calls = Server.FindLogEntries(
            Request.Create().WithPath("/api/widgets/42").UsingGet());
        Assert.That(calls, Has.Count.EqualTo(1));
    }
}
```

`WithBodyAsJson(obj)` serializes and sets `Content-Type: application/json`. Stub mappings must be
registered **before** the action that triggers the request — a stub added after the client has already
called won't match. Async all the way: `await Client.GetWidgetAsync(...)`, never `.Result`/`.Wait()`.

## Request matching — which requests this stub answers

Match on URL, method, query, headers, cookies, and body via `WireMock.Matchers`. Use the **narrowest**
matcher that expresses intent.

```csharp
Server
    .Given(Request.Create().WithPath("/api/orders").UsingPost()      // method + exact path
        .WithParam("dryRun", "false")                               // query param
        .WithHeader("Content-Type", new WildcardMatcher("*application/json*"))   // header
        .WithBody(new JsonMatcher(new { sku = "SPR-1", qty = 3 }, ignoreCase: true))  // JSON equality
        .WithBody(new JsonPathMatcher("$.qty")))                    // JSONPath presence
    .RespondWith(Response.Create().WithStatusCode(201));
```

Matcher cheatsheet:

| Match on | Call |
|----------|------|
| Exact path | `.WithPath("/a/b")` |
| Path regex | `.WithPath(new RegexMatcher("/a/[0-9]+"))` |
| Query param | `.WithParam("k", "v")` |
| Header (wildcard) | `.WithHeader("Accept", new WildcardMatcher("*json*"))` |
| Body JSON equality | `.WithBody(new JsonMatcher(obj))` |
| Body JSONPath | `.WithBody(new JsonPathMatcher("$.field"))` |
| Body XPath | `.WithBody(new XPathMatcher("//id"))` |
| Body regex | `.WithBody(new RegexMatcher(".*foo.*"))` |

**Priority & catch-all.** When two stubs could match, the lower `.AtPriority(n)` wins (1 = highest).
A catch-all default catches unmatched requests so the SUT sees a deterministic response instead of
WireMock's default `404`:

```csharp
Server.Given(Request.Create().WithPath("*").UsingAnyMethod()).AtPriority(10)   // low priority = fallback
      .RespondWith(Response.Create().WithStatusCode(404).WithBody("no stub matched"));
Server.Given(Request.Create().WithPath("/api/widgets/42").UsingGet()).AtPriority(1)   // specific wins
      .RespondWith(Response.Create().WithBodyAsJson(new { id = 42 }));
```

## Response definition — status, headers, body, templating

```csharp
Server.Given(Request.Create().WithPath("/api/widgets/42").UsingGet())
    .RespondWith(Response.Create()
        .WithStatusCode(200)
        .WithHeader("Content-Type", "application/json")
        .WithHeader("Cache-Control", "no-cache")
        .WithBody("{ \"id\": 42 }"));                  // inline body

Server.Given(Request.Create().WithPath("/api/widgets/99").UsingGet())
    .RespondWith(Response.Create().WithBodyFromFile("widgets/99.json"));   // body from a file
```

**Response templating (Handlebars)** derives the response from the request. Enable with
`.WithTransformer()`, then reference `{{request.*}}` in the body:

```csharp
Server.Given(Request.Create().WithPath(new RegexMatcher("/api/widgets/[0-9]+")).UsingGet())
    .RespondWith(Response.Create()
        .WithStatusCode(200)
        .WithHeader("Content-Type", "application/json")
        // {{request.PathSegments.[2]}} echoes the id from the URL the SUT requested.
        .WithBody("{ \"id\": {{request.PathSegments.[2]}}, \"name\": \"generated\" }")
        .WithTransformer());                           // enable Handlebars for this stub
```

### Fault & delay injection — resilience / chaos testing

WireMock simulates latency and broken responses so you can test the SUT's **error paths** (retries,
timeouts, circuit breakers). This is WireMock's own feature — **not** `Task.Delay`/`Thread.Sleep` in the
test:

```csharp
// Latency: the stub itself is slow — SIMULATE slowness here, never sleep in the test.
Server.Given(Request.Create().WithPath("/api/slow").UsingGet())
      .RespondWith(Response.Create().WithBodyAsJson(new { }).WithDelay(TimeSpan.FromSeconds(2)));

// Faults: malformed / dropped responses to exercise the client's failure handling.
Server.Given(Request.Create().WithPath("/api/reset").UsingGet())
      .RespondWith(Response.Create().WithFault(FaultType.EMPTY_RESPONSE));        // dropped
Server.Given(Request.Create().WithPath("/api/garbage").UsingGet())
      .RespondWith(Response.Create().WithFault(FaultType.MALFORMED_RESPONSE_CHUNK));
Server.Given(Request.Create().WithPath("/api/boom").UsingGet())
      .RespondWith(Response.Create().WithStatusCode(500));
```

Cross-link the fault-injection angle of `qa-network-monitoring-proxy-dotnet` — the proxy injects faults
onto a *real* service's traffic; WireMock injects them as *the* (fake) service. Assert on the SUT's
**visible outcome** (a thrown `HttpRequestException`, a fallback value, a retry count) — never
sleep-then-check.

## Stateful behavior — scenarios (the state machine)

A **scenario** lets one stub's response depend on the server's current state — the way to model eventual
consistency, multi-step flows, or "first call pending, then done". Each stub declares the state it
matches (`WhenStateIs`) and optionally the state it transitions to (`WillSetStateTo`):

```csharp
const string Poll = "order-fulfilment";

// First poll: 202 Accepted, then advance the scenario.
Server.Given(Request.Create().WithPath("/api/orders/7/status").UsingGet())
    .InScenario(Poll)
    .WillSetStateTo("READY")
    .RespondWith(Response.Create().WithStatusCode(202).WithBodyAsJson(new { state = "PENDING" }));

// Subsequent polls (state == READY): 200 Done.
Server.Given(Request.Create().WithPath("/api/orders/7/status").UsingGet())
    .InScenario(Poll)
    .WhenStateIs("READY")
    .RespondWith(Response.Create().WithStatusCode(200).WithBodyAsJson(new { state = "DONE" }));
```

The SUT polls until it sees `DONE`. **Wait on the condition (the `DONE` payload), not on a clock** — poll
with a condition helper (e.g. Polly / a small retry loop with an explicit deadline), never `Task.Delay`:

```csharp
await Assert.That(async () =>
    (await Client.GetOrderStatusAsync(7)).State,
    Is.EqualTo("DONE").After(10).Seconds.PollEvery(200).MilliSeconds);
```

(`Assert.That(...).After(...).PollEvery(...)` is NUnit's built-in condition-poll — a deadline, not a sleep.)

## Verification — assert the SUT called the dependency

`WireMock.Net` records every received request in `server.LogEntries`; verification is done by querying
that log (the server-side "was X called, with what" assertion — the same intent as the request-assertion
framing in `qa-network-monitoring-playwright-routes-dotnet`, but recorded server-side, decoupled from the
stub):

```csharp
// Called exactly once, with this body.
var orders = Server.FindLogEntries(
    Request.Create().WithPath("/api/orders").UsingPost()
        .WithBody(new JsonMatcher(new { sku = "SPR-1", qty = 3 }, ignoreCase: true)));
Assert.That(orders, Has.Count.EqualTo(1));

// Never called (negative assertion).
Assert.That(
    Server.FindLogEntries(Request.Create().WithPath("/api/legacy-pricing").UsingGet()),
    Is.Empty);

// Inspect a captured request's headers.
var idem = orders.Single().RequestMessage.Headers!["Idempotency-Key"];
Assert.That(idem, Is.Not.Null);
```

`FindLogEntries` keeps the **assertion** (request was sent) separate from the **stub** (what to answer) —
you can stub a generic 201 and still assert the exact body that was POSTed.

## Record & playback (mention, don't over-invest)

To bootstrap stubs from a real service, start the server in **proxy-and-record** mode pointing at the
real upstream, drive the SUT once, then save the generated mappings to replay offline:

```csharp
var server = WireMockServer.Start(new WireMockServerSettings
{
    ProxyAndRecordSettings = new ProxyAndRecordSettings
    {
        Url = "https://real.example.com",
        SaveMapping = true,
        SaveMappingToFile = true
    }
});
// …drive the SUT once… mappings are written to disk for replay.
```

Prefer hand-written stubs for tests you'll maintain; recorded mappings are verbose and brittle.

## Run modes — in-process / standalone / container

| Mode | How | When |
|------|-----|------|
| **In-process** (default) | `WireMockServer.Start()` in the test process | Fastest; unit/integration tests — recommended default. `WireMock.Net` is in-process-first |
| **Standalone** | `WireMock.Net.StandAlone` / the standalone exe with `mappings/` + `__admin` API | A shared mock across processes; manual exploration; record-&-playback |
| **Container** | `WireMock.Net.Testcontainers` `WireMockContainerBuilder` | Language-agnostic / CI parity, or when the SUT runs in its own container and needs the mock on the Docker network |

```csharp
// Container run mode — cross-link qa-test-environments-dotnet / qa-db-testing-testcontainers-dotnet.
await using var wiremock = new WireMockContainerBuilder().Build();
await wiremock.StartAsync();
var http = new HttpClient { BaseAddress = new Uri(wiremock.GetPublicUrl()) };
var client = new WidgetApiClient(http);
// …exercise + assert…
```

The in-process server is the default for fast .NET integration tests; reach for the container only when
you need the mock reachable from another container or the exact standalone image CI will run.

## Anti-patterns

- **`Task.Delay`/`Thread.Sleep` to wait for an async / scenario flow.** Races the server and is slow.
  *Fix:* drive a **scenario** for staged responses and an NUnit `After(...).PollEvery(...)` condition.
  Use WireMock's `WithDelay` only to *simulate* latency.
- **`.Result`/`.Wait()`/`.GetAwaiter().GetResult()` on the client call.** Violates async-all-the-way and
  can deadlock. *Fix:* `await` the client; mark the test `async Task`.
- **Forgetting `server.Reset()` with a per-fixture server.** Stubs and log entries leak into the next
  test. *Fix:* `Server.Reset()` in `[TearDown]` (or one server per test).
- **Hard-coding the SUT's base address instead of injecting `Server.Url`.** The port is dynamic. *Fix:*
  construct the `HttpClient` with `BaseAddress = new Uri(Server.Url!)` and inject it.
- **Asserting only the response, never the request.** A passing response can hide a wrong payload/header.
  *Fix:* `FindLogEntries(...)` the request the SUT sent (body, headers, count).
- **One giant catch-all stub for everything.** Tests pass even when the SUT calls the wrong endpoint.
  *Fix:* narrow stubs per case; a `404` catch-all only as an explicit low-priority fallback.
- **Reaching for WireMock when you have a Playwright `page`.** *Fix:* use
  `qa-network-monitoring-playwright-routes-dotnet` for in-browser interception; WireMock is for a service
  talking HTTP to a dependency.

## Examples

**End-to-end: a retry-then-succeed flow gated on a scenario, with a verify on the final POST.**

```csharp
public class OrderSubmissionTests : WireMockTestBase
{
    [Test]
    public async Task Should_retry_then_succeed_When_orders_API_is_briefly_unavailable()
    {
        const string Flow = "orders-transient-503";

        // First attempt: 503 (transient), then advance to "UP".
        Server.Given(Request.Create().WithPath("/api/orders").UsingPost())
            .InScenario(Flow).WillSetStateTo("UP")
            .RespondWith(Response.Create().WithStatusCode(503));

        // Retry (state == UP): 201 Created with the order id.
        Server.Given(Request.Create().WithPath("/api/orders").UsingPost())
            .InScenario(Flow).WhenStateIs("UP")
            .RespondWith(Response.Create().WithStatusCode(201)
                .WithHeader("Content-Type", "application/json")
                .WithBodyAsJson(new { orderId = "ord-7" }));

        // SUT has a retry policy; it should transparently recover.
        var order = await Client.SubmitOrderAsync(OrderRequestMother.Standard());

        Assert.That(order.OrderId, Is.EqualTo("ord-7"));               // one logical assertion: outcome
        var attempts = Server.FindLogEntries(Request.Create().WithPath("/api/orders").UsingPost());
        Assert.That(attempts, Has.Count.EqualTo(2));                   // retried once
    }
}
```

Lifecycle for this test:
1. `[OneTimeSetUp]` starts the in-process server; the typed client's `HttpClient.BaseAddress` = `Server.Url`.
2. Two scenario stubs stage a 503 → 201 sequence on the same endpoint.
3. The SUT's retry policy turns the transient 503 into success — the test asserts the **outcome** and
   verifies the dependency was hit exactly twice via `FindLogEntries`.
4. `[TearDown]` `Server.Reset()` wipes stubs + log entries; the next test starts clean.

**Test-data builder for stub payloads (4+ fields → builder, per the global rules).**

```csharp
public static class OrderRequestMother
{
    public static OrderRequest Standard() => new OrderRequestBuilder()
        .WithSku("SPR-1").WithQty(3).WithCurrency("EUR").WithIdempotencyKey("idem-123").Build();
}
```

## Rules (hard constraints)

- WireMock is a **standalone HTTP server you point a client at** — inject `Server.Url` into the typed
  client's `HttpClient.BaseAddress` (`qa-api-client-writer-dotnet`); never hard-code the dynamic port.
- Register stub mappings **before** the action that triggers the request.
- One server per fixture with `Reset()` between tests (default), **or** one per test — keep tests
  independent and verification counts correct.
- Assert both sides: the **response** (one logical assertion) **and** the **request**
  (`FindLogEntries(...)` — body/headers/count).
- **Async all the way:** `await` the client, no `.Result`/`.Wait()`. **No `Task.Delay`/`Thread.Sleep`** —
  use `WithDelay` to *simulate* latency and an NUnit `After(...).PollEvery(...)` condition to *assert*.
  Use **scenarios** for staged/eventual-consistency responses.
- Use the **narrowest** matcher; a catch-all only as an explicit low-priority fallback.
- Builders/ObjectMother for stub & request payloads with 4+ fields.
- Test names `Should_X_When_Y`; structured logging; no secrets in stub files.
- Don't use WireMock when a Playwright `page.route` or the MITM proxy is the right tool.

## Cross-references

- `qa-api-mocking-wiremock-java` — the **canonical** stack, Java / TestNG (`org.wiremock:wiremock`,
  `stubFor(get(...).willReturn(...))`, `inScenario`/`whenScenarioStateIs`, `server.verify(...)`).
  Structure ported from there.
- `qa-api-mocking-wiremock-typescript` — same skill, Node 20 + TS (`wiremock-captain` against a
  Testcontainers WireMock container). Thin client to a running server; structure ported.
- `qa-api-mocking-msw-dotnet` (#23, next) — the second `api-mocking` sibling: MSW intercepts requests in
  the app's own runtime (browser/Node) rather than a separate server. Plus Mountebank (#24) and
  Prism (#25, OpenAPI-spec-driven).
- `qa-network-monitoring-playwright-routes-dotnet` (#8) — in-browser `page.route` interception; no
  separate server, Playwright-only. The boundary: route = inside the browser, WireMock = a server you
  point at.
- `qa-network-monitoring-proxy-dotnet` (#10) — out-of-browser MITM proxy on a *real* service's traffic;
  WireMock *replaces* the service. Mirror its fault-injection framing.
- `qa-api-client-writer-dotnet` + `qa-api-test-author-generator-dotnet` — the typed client / API tests
  pointed at the WireMock base URL (constructor injection).
- `qa-test-environments-dotnet` + `qa-db-testing-testcontainers-dotnet` — the container run mode + the
  per-fixture-vs-per-test lifecycle trade-off mirrored here.
- `qa-ci-pipelines-github-actions-dotnet` — runs these tests; the in-process server needs no service
  wiring (vs the container run mode, which needs Docker).
