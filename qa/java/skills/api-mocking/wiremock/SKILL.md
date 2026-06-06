---
name: qa-api-mocking-wiremock-java
description: >-
  Service-virtualization / API-mocking with WireMock in Java (TestNG): stand up a standalone HTTP server
  that returns stubbed responses for matched requests, point the system-under-test's typed client at the
  server's base URL, exercise the flow, then `verify(...)` the SUT called the dependency as expected.
  Use when a test must run against a controlled fake of a downstream HTTP dependency (flaky, unavailable,
  rate-limited, or costly) instead of the real service — `new WireMockServer(options().dynamicPort())`,
  `stubFor(get(urlPathEqualTo(...)).willReturn(okJson(...)))`, request matching (URL/method/headers/query
  /body JSON/JSONPath), response definition + Handlebars templating, fault & delay injection
  (`withFixedDelay`/`Fault.CONNECTION_RESET_BY_PEER`), stateful **Scenarios** (state machine), `verify(...)`
  call assertions, record-&-playback, and run modes (in-process / standalone JAR / Testcontainers
  `WireMockContainer`). Triggers: "mock the payment API with WireMock", "stand up a fake downstream
  service for this integration test", "WireMock stub returns 202 then 200", "verify our client POSTed the
  right body", "inject a 500 / timeout / connection-reset from a stubbed dependency". Do NOT use for:
  in-browser request interception with a Playwright `page` (use qa-network-monitoring-playwright-routes-java),
  an out-of-browser MITM proxy over a real client's live traffic (use qa-network-monitoring-proxy-java),
  the TypeScript stack (use qa-api-mocking-wiremock-typescript), or the .NET stack (use
  qa-api-mocking-wiremock-dotnet). Sibling tools in this family: MSW (qa-api-mocking-msw-*), Mountebank,
  Prism.
---

# API Mocking — WireMock (Java / TestNG) — **canonical stack**

This is the **canonical** stack of the `qa/java/skills/api-mocking/wiremock/` node — WireMock is JVM-native, so the
Java surface is the richest and most authentic (in-process `WireMockServer`, the full
`stubFor`/`verify`/Scenarios/templating DSL). The `dotnet` (`WireMock.Net`, a faithful in-process
reimplementation) and `typescript` (`wiremock-captain` talking to a Testcontainers WireMock container)
siblings are ported from this file — same model and section order, re-expressed in each stack's idioms.

WireMock is an **HTTP service-virtualization / API-mocking server**: a real HTTP server you stand up so
your tests run against a **controlled fake** of a downstream dependency instead of the real service —
which may be flaky, unavailable in CI, rate-limited, or costly to call. You register **stub mappings**
(a request matcher → a response definition), point the system-under-test's HTTP client at the server's
base URL, exercise the flow, then **verify** the SUT called the dependency the way you expected.

> **The boundary that defines this skill.** WireMock is a **standalone HTTP server you point a client at**
> — not an in-process hook into a browser. That is the sharp line against the `network-monitoring`
> family: `qa-network-monitoring-playwright-routes-java` intercepts requests *inside a Playwright `page`*
> (no separate server, browser-only), and `qa-network-monitoring-proxy-java` is an *out-of-browser MITM
> proxy* sitting on a real client's live traffic. WireMock owns the other end of the wire: it **is** the
> dependency, fully under the test's control. Reach for WireMock when you want the SUT to talk to a fake
> service; reach for the proxy/route tools when you want to observe or rewrite traffic to a real one.

## Decision matrix — WireMock vs the rest of the `api-mocking` family, vs network-monitoring

| Need | Use | Why |
|------|-----|-----|
| A **standalone HTTP server** that fakes a downstream dependency; rich request matching + stateful scenarios + `verify`; first-class in **every** stack | **WireMock (this skill)** | JVM-born, full-featured stub server; mature clients in Java / .NET / Node |
| Intercept **browser** requests inside a Playwright test, no separate server | `qa-network-monitoring-playwright-routes-java` (#8) | `page.route` lives in the browser; no server to point at |
| Observe / rewrite a **real client's** live traffic out-of-browser (MITM) | `qa-network-monitoring-proxy-java` (#10) | Proxy sits on the wire to the *real* service; WireMock replaces it |
| Mock `fetch`/XHR in a **browser or Node** app via the Service Worker / request layer | MSW (`qa-api-mocking-msw-*`, #23) | Request-interception in the app's own runtime, not a separate server |
| **Protocol-agnostic** over-the-wire imposters (TCP/HTTP/SMTP), language-neutral | Mountebank (#24) | Multi-protocol; heavier than an HTTP-only stub server |
| Mock derived **from an OpenAPI spec** automatically | Prism (#25) | Spec-driven; the contract *is* the mock |

**Rule of thumb:** *Need a fake HTTP dependency you fully control and assert against, from any stack?*
→ WireMock. *Need to touch a real browser's or real service's traffic?* → the network-monitoring family.
*Spec-first or browser-runtime mocking?* → Prism / MSW.

## Stack

- Java 21 + TestNG + AssertJ (`org.testng:testng`, `org.assertj:assertj-core`)
- `org.wiremock:wiremock` (WireMock 3.x — standalone, includes Jetty; the in-process `WireMockServer`)
- A typed API client (`qa-api-client-writer-java`) is the SUT — **constructor-injected** with the base URL
- Optional: `org.wiremock.integrations.testcontainers:wiremock-testcontainers-module` for the container
  run mode (cross-link `qa-test-environments-java` / `qa-db-testing-testcontainers-java`)
- Static imports from `com.github.tomakehurst.wiremock.client.WireMock.*` (WireMock 3 kept the legacy
  package names for source compatibility)

## The WireMock model — lifecycle

A WireMock server is a real HTTP server. The lifecycle of every test that uses it:

1. **Start** the server on a random (or fixed) port — `new WireMockServer(options().dynamicPort())`.
2. **Register stub mappings** — `server.stubFor(<request matcher>.willReturn(<response definition>))`.
3. **Point the SUT at the server's base URL** — `server.baseUrl()` (e.g. `http://localhost:54321`),
   injected into the client's constructor.
4. **Exercise** the SUT so it calls the dependency.
5. **Verify** the SUT sent the requests you expected — `server.verify(...)`.
6. **Reset / stop** — `server.resetAll()` between tests, `server.stop()` at teardown.

### Per-class vs per-test lifecycle (the same trade-off as Testcontainers)

Mirror the lifecycle trade-off from `qa-db-testing-testcontainers-java`:

- **One server per test class** (`@BeforeClass`/`@AfterClass`), `server.resetAll()` in `@AfterMethod` —
  fastest, but you **must** reset between tests so stubs/recorded requests don't leak. This is the
  default; tests stay independent because state is reset.
- **One server per test** (`@BeforeMethod`/`@AfterMethod`) — maximal isolation, no reset needed, slower.
  Use it only when a test mutates server config in a way `resetAll()` can't cleanly undo.

```java
public abstract class WireMockTestBase {
    protected WireMockServer server;
    protected WidgetApiClient client;

    @BeforeClass(alwaysRun = true)
    public void startServer() {
        server = new WireMockServer(options().dynamicPort());
        server.start();
        // The SUT's typed client is constructor-injected with the mock's base URL — never a static URL.
        client = new WidgetApiClient(URI.create(server.baseUrl()));
    }

    @AfterMethod(alwaysRun = true)
    public void resetServer() {
        server.resetAll();   // wipe stubs + recorded requests so each test starts clean and independent
    }

    @AfterClass(alwaysRun = true)
    public void stopServer() {
        if (server != null) server.stop();
    }
}
```

> JUnit 5 users would use `@WireMockTest` / `WireMockExtension` (which manage this lifecycle for you).
> The house runner is TestNG, which has no WireMock extension — so own the lifecycle explicitly as above.

## Core pattern — stub, point the client, exercise, verify

The SUT is a typed client constructor-injected with the base URL (cross-link `qa-api-client-writer-java`).
The test stubs the dependency, drives the client, asserts the **response** (AssertJ, one logical
assertion), and `verify`s the **request** the client sent.

```java
import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static org.assertj.core.api.Assertions.assertThat;

public class WidgetLookupTest extends WireMockTestBase {

    @Test
    public void Should_return_the_widget_When_the_service_responds_200() {
        // 1. Stub: matcher → response definition.
        server.stubFor(get(urlPathEqualTo("/api/widgets/42"))
                .withHeader("Accept", containing("application/json"))
                .willReturn(okJson("""
                        { "id": 42, "name": "Sprocket", "priceMinor": 1999 }
                        """)));

        // 2. Exercise the SUT (already pointed at server.baseUrl()).
        Widget widget = client.getWidget(42);

        // 3. Assert the response (one logical assertion).
        assertThat(widget).isEqualTo(new Widget(42, "Sprocket", 1999));

        // 4. Verify the request the SUT actually sent.
        server.verify(getRequestedFor(urlPathEqualTo("/api/widgets/42"))
                .withHeader("Accept", containing("application/json")));
    }
}
```

`okJson(body)` is shorthand for `aResponse().withStatus(200).withHeader("Content-Type",
"application/json").withBody(body)`. Stub mappings must be registered **before** the action that
triggers the request — a stub added after the client has already called won't match.

## Request matching — which requests this stub answers

Match on URL, method, query, headers, cookies, and body. Use the **narrowest** matcher that expresses
intent so unrelated traffic doesn't accidentally match.

```java
server.stubFor(post(urlPathEqualTo("/api/orders"))                  // method + exact path
        .withQueryParam("dryRun", equalTo("false"))                 // query param
        .withHeader("Content-Type", containing("application/json")) // header
        .withCookie("session", matching("^[A-Za-z0-9]+$"))          // cookie regex
        .withRequestBody(equalToJson("""
                { "sku": "SPR-1", "qty": 3 }
                """, true, true))                                   // JSON equality (ignore order/extra)
        .withRequestBody(matchingJsonPath("$.qty"))                 // JSONPath presence
        .willReturn(aResponse().withStatus(201)));
```

Matcher cheatsheet:

| Match on | Call |
|----------|------|
| Exact path | `urlPathEqualTo("/a/b")` |
| Path regex | `urlPathMatching("/a/[0-9]+")` |
| Path + query (raw) | `urlEqualTo("/a?x=1")` |
| Query param | `.withQueryParam("k", equalTo("v"))` |
| Header | `.withHeader("Accept", containing("json"))` |
| Body JSON equality | `.withRequestBody(equalToJson(json, true, true))` |
| Body JSONPath | `.withRequestBody(matchingJsonPath("$.field"))` |
| Body XPath | `.withRequestBody(matchingXPath("//id"))` |
| Body regex | `.withRequestBody(matching(".*foo.*"))` |

**Priority & catch-all.** When two stubs could match, the lower `.atPriority(n)` wins (1 = highest).
A catch-all default stub catches anything unmatched so the SUT sees a deterministic response instead of
WireMock's `404`:

```java
server.stubFor(any(anyUrl()).atPriority(10)             // low priority = fallback
        .willReturn(aResponse().withStatus(404).withBody("no stub matched")));
server.stubFor(get(urlPathEqualTo("/api/widgets/42")).atPriority(1)   // specific wins
        .willReturn(okJson("{ \"id\": 42 }")));
```

## Response definition — status, headers, body, templating

```java
server.stubFor(get(urlPathEqualTo("/api/widgets/42")).willReturn(aResponse()
        .withStatus(200)
        .withHeader("Content-Type", "application/json")
        .withHeader("Cache-Control", "no-cache")
        .withBody("{ \"id\": 42 }")));                  // inline body

server.stubFor(get(urlPathEqualTo("/api/widgets/99")).willReturn(aResponse()
        .withStatus(200)
        .withBodyFile("widgets/99.json")));             // body from src/test/resources/__files/...
```

**Response templating (Handlebars)** derives the response from the request — useful for echoing an id or
generating realistic data without a stub per value. Enable the transformer at server build time, then
reference `{{request.*}}` in the body:

```java
server = new WireMockServer(options().dynamicPort()
        .globalTemplating(true));                        // enable Handlebars for all stubs
server.start();

server.stubFor(get(urlPathMatching("/api/widgets/[0-9]+")).willReturn(aResponse()
        .withStatus(200)
        .withHeader("Content-Type", "application/json")
        // {{request.pathSegments.[2]}} echoes the id from the URL the SUT requested.
        .withBody("{ \"id\": {{request.pathSegments.[2]}}, \"name\": \"generated\" }")));
```

### Fault & delay injection — resilience / chaos testing

WireMock can simulate latency and broken responses so you can test the SUT's **error paths** (retries,
timeouts, circuit breakers). This is WireMock's own delay/fault feature — **not** `Thread.sleep`:

```java
// Latency: the stub itself is slow — use this to SIMULATE slowness, never Thread.sleep in the test.
server.stubFor(get(urlPathEqualTo("/api/slow")).willReturn(okJson("{}").withFixedDelay(2_000)));
server.stubFor(get(urlPathEqualTo("/api/jitter")).willReturn(okJson("{}")
        .withRandomDelay(new UniformDistribution(50, 500))));

// Faults: malformed / dropped responses to exercise the client's failure handling.
server.stubFor(get(urlPathEqualTo("/api/reset")).willReturn(aResponse()
        .withFault(Fault.CONNECTION_RESET_BY_PEER)));   // socket dropped
server.stubFor(get(urlPathEqualTo("/api/garbage")).willReturn(aResponse()
        .withFault(Fault.MALFORMED_RESPONSE_CHUNK)));   // garbage then close
server.stubFor(get(urlPathEqualTo("/api/boom")).willReturn(aResponse().withStatus(500)));
```

Cross-link the fault-injection angle of `qa-network-monitoring-proxy-java` — the proxy injects faults
onto a *real* service's traffic; WireMock injects them as *the* (fake) service. Assert on the SUT's
**visible outcome** (a thrown exception, a fallback value, a retry count) — never a sleep-then-check.

## Stateful behavior — Scenarios (the state machine)

A **Scenario** lets one stub's response depend on the server's current state — the way to model
eventual consistency, multi-step flows, or "first call pending, then done". Each stub declares the
scenario state it matches (`whenScenarioStateIs`) and optionally the state it transitions to
(`willSetStateTo`). Scenarios start in `Scenario.STARTED`.

```java
final String poll = "order-fulfilment";

// First poll: 202 Accepted, then advance the scenario to "READY".
server.stubFor(get(urlPathEqualTo("/api/orders/7/status"))
        .inScenario(poll)
        .whenScenarioStateIs(Scenario.STARTED)
        .willReturn(aResponse().withStatus(202).withBody("{ \"state\": \"PENDING\" }"))
        .willSetStateTo("READY"));

// Subsequent polls (state == READY): 200 Done.
server.stubFor(get(urlPathEqualTo("/api/orders/7/status"))
        .inScenario(poll)
        .whenScenarioStateIs("READY")
        .willReturn(okJson("{ \"state\": \"DONE\" }")));
```

The SUT polls until it sees `DONE`. **Wait on the condition (the `DONE` payload), not on a clock** — use
Awaitility, never `Thread.sleep`:

```java
import static org.awaitility.Awaitility.await;

await().atMost(Duration.ofSeconds(10)).pollInterval(Duration.ofMillis(200))
        .until(() -> client.getOrderStatus(7).state().equals("DONE"));
```

## Verification — assert the SUT called the dependency

`verify(...)` asserts the dependency was called the expected number of times, with the expected payload —
the server-side "was X called, with what" assertion (the same intent as the request-assertion framing in
`qa-network-monitoring-playwright-routes-java`, but here it is recorded server-side, decoupled from the
stub):

```java
// Called exactly once, with this body.
server.verify(exactly(1), postRequestedFor(urlPathEqualTo("/api/orders"))
        .withRequestBody(equalToJson("{ \"sku\": \"SPR-1\", \"qty\": 3 }", true, true)));

// Never called (negative assertion).
server.verify(exactly(0), getRequestedFor(urlPathEqualTo("/api/legacy-pricing")));

// At-least-once / count ranges.
server.verify(moreThanOrExactly(2), getRequestedFor(urlPathMatching("/api/orders/7/status")));
```

For richer assertions, pull the recorded requests and inspect them with AssertJ:

```java
List<LoggedRequest> orders = server.findAll(postRequestedFor(urlPathEqualTo("/api/orders")));
assertThat(orders).singleElement()
        .extracting(r -> r.getHeader("Idempotency-Key"))
        .isNotNull();
```

`verify` keeps the **assertion** (request was sent) separate from the **stub** (what to answer) — you can
stub a generic 201 and still assert the exact body that was POSTed.

## Record & playback (mention, don't over-invest)

To bootstrap stubs from a real service: run WireMock as a proxy to the real upstream once, record the
traffic into mappings, then replay offline. Useful for capturing a baseline; prefer hand-written stubs
for tests you'll maintain (recorded mappings are verbose and brittle).

```java
server.startRecording(WireMockConfiguration.options().toString());     // or: startRecording(targetBaseUrl)
// …drive the SUT against the real upstream once…
SnapshotRecordResult recorded = server.stopRecording();                // mappings written to disk
```

(The standalone JAR offers the same via `--record-mappings --proxy-all=https://real.example.com`.)

## Run modes — in-process / standalone JAR / Testcontainers

| Mode | How | When |
|------|-----|------|
| **In-process** (default) | `new WireMockServer(options().dynamicPort())` in the JVM under test | Fastest; unit/integration tests — the recommended default |
| **Standalone JAR** | `java -jar wiremock-standalone.jar --port 8080`, mappings in `mappings/`, files in `__files/` | A shared mock across processes/teams; manual exploration; record-&-playback |
| **Testcontainers** | `new WireMockContainer("wiremock/wiremock:3.x")` (the `wiremock-testcontainers-module`) | Language-agnostic / CI parity, or when the SUT runs in its own container and needs the mock on the Docker network |

```java
// Testcontainers run mode — cross-link qa-test-environments-java / qa-db-testing-testcontainers-java.
try (WireMockContainer wiremock = new WireMockContainer("wiremock/wiremock:3.9.1")
        .withMappingFromResource("widgets", "wiremock/widgets.json")) {
    wiremock.start();
    var client = new WidgetApiClient(URI.create(wiremock.getBaseUrl()));
    // …exercise + assert…
}
```

The in-process server is the default for fast Java integration tests; reach for the container only when
you need the mock reachable from another container or want the exact standalone image CI will run.

## Anti-patterns

- **`Thread.sleep(...)` to wait for an async / scenario flow.** Races the server and is slow. *Fix:*
  drive a **Scenario** for staged responses and **Awaitility** to poll the client's visible state on a
  condition. Use WireMock's `withFixedDelay`/`withRandomDelay` only to *simulate* latency.
- **Forgetting `resetAll()` with a per-class server.** Stubs and recorded requests leak into the next
  test, so order matters and `verify` counts are wrong. *Fix:* `server.resetAll()` in `@AfterMethod`
  (or one server per test).
- **Stubbing `urlEqualTo` with a query string when you mean the path.** `urlEqualTo("/a")` won't match
  `/a?x=1`. *Fix:* `urlPathEqualTo("/a")` + `.withQueryParam(...)`.
- **Hard-coding the SUT's base URL instead of injecting `server.baseUrl()`.** The port is dynamic; a
  hard-coded URL points at nothing. *Fix:* constructor-inject `server.baseUrl()` into the typed client.
- **Asserting only the response, never the request.** A passing response can hide a wrong payload/header.
  *Fix:* `verify(...)` the request the SUT sent (body, headers, count).
- **One giant catch-all stub for everything.** Tests pass even when the SUT calls the wrong endpoint.
  *Fix:* narrow stubs per case; a `404` catch-all only as an explicit low-priority fallback.
- **Reaching for WireMock when you have a Playwright `page`.** In-browser routing (`page.route`) needs
  no separate server. *Fix:* use `qa-network-monitoring-playwright-routes-java` for browser interception;
  WireMock is for when the SUT is a service/client talking HTTP to a dependency.
- **Sharing one server across parallel test classes without isolation.** Stubs/verifications collide.
  *Fix:* one server per class (reset between methods) or per parallel worker.

## Examples

**End-to-end: a retry-then-succeed flow gated on a Scenario, with a verify on the final POST.**

```java
import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static org.assertj.core.api.Assertions.assertThat;

public class OrderSubmissionTest extends WireMockTestBase {

    @Test
    public void Should_retry_then_succeed_When_orders_API_is_briefly_unavailable() {
        final String flow = "orders-transient-503";

        // First attempt: 503 (transient), then advance to "UP".
        server.stubFor(post(urlPathEqualTo("/api/orders"))
                .inScenario(flow).whenScenarioStateIs(Scenario.STARTED)
                .willReturn(aResponse().withStatus(503))
                .willSetStateTo("UP"));

        // Retry (state == UP): 201 Created with the order id.
        server.stubFor(post(urlPathEqualTo("/api/orders"))
                .inScenario(flow).whenScenarioStateIs("UP")
                .willReturn(aResponse().withStatus(201)
                        .withHeader("Content-Type", "application/json")
                        .withBody("{ \"orderId\": \"ord-7\" }")));

        // SUT has a retry policy; it should transparently recover.
        Order order = client.submitOrder(OrderRequestMother.standard());

        assertThat(order.orderId()).isEqualTo("ord-7");                 // one logical assertion: outcome
        server.verify(exactly(2), postRequestedFor(urlPathEqualTo("/api/orders")));   // retried once
    }
}
```

Lifecycle for this test:
1. `@BeforeClass` starts the in-process server; the typed client is injected with `server.baseUrl()`.
2. Two scenario stubs stage a 503 → 201 sequence on the same endpoint.
3. The SUT's retry policy turns the transient 503 into success — the test asserts the **outcome** and
   `verify`s the dependency was hit exactly twice.
4. `@AfterMethod` `resetAll()` wipes stubs + recorded requests; the next test starts clean.

**Test-data builder for stub payloads (4+ fields → builder, per the global rules).**

```java
public final class OrderRequestMother {
    public static OrderRequest standard() {
        return new OrderRequest.Builder()
                .sku("SPR-1").qty(3).currency("EUR").idempotencyKey("idem-123").build();
    }
}
```

## Rules (hard constraints)

- WireMock is a **standalone HTTP server you point a client at** — constructor-inject `server.baseUrl()`
  into the typed client (`qa-api-client-writer-java`); never hard-code the dynamic port.
- Register stub mappings **before** the action that triggers the request.
- One server per test class with `resetAll()` between methods (default), **or** one per test — keep tests
  independent and `verify` counts correct.
- Assert both sides: the **response** (AssertJ, one logical assertion) **and** the **request**
  (`verify(...)` — body/headers/count).
- **No `Thread.sleep`.** Use WireMock's `withFixedDelay`/`withRandomDelay` to *simulate* latency and
  **Awaitility** to *assert* on a condition. Use **Scenarios** for staged/eventual-consistency responses.
- Use the **narrowest** matcher (`urlPathEqualTo` + `withQueryParam`, not a broad `urlMatching`); a
  catch-all only as an explicit low-priority fallback.
- Builders/ObjectMother for stub & request payloads with 4+ fields.
- Test names `Should_X_When_Y`; structured logging; no secrets in stub files.
- Don't use WireMock when a Playwright `page.route` (in-browser, no server) or the MITM proxy (real
  traffic) is the right tool — justify the standalone-server choice.

## Cross-references

- `qa-api-mocking-wiremock-dotnet` — same skill, .NET / NUnit (`WireMock.Net`: `WireMockServer.Start()`,
  `server.Given(Request.Create()...).RespondWith(Response.Create()...)`, `.InScenario(...)`,
  `server.FindLogEntries(...)`). Faithful in-process reimplementation; structure ported.
- `qa-api-mocking-wiremock-typescript` — same skill, Node 20 + TS (`wiremock-captain` against a
  Testcontainers WireMock container: `mock.register({request, response})`, `verify`). Thin client to a
  running server; structure ported.
- `qa-api-mocking-msw-java` (#23, next) — the second `api-mocking` sibling: MSW intercepts requests in
  the app's own runtime (browser/Node) rather than a separate server. Plus Mountebank (#24,
  protocol-agnostic imposters) and Prism (#25, OpenAPI-spec-driven).
- `qa-network-monitoring-playwright-routes-java` (#8) — in-browser `page.route` interception; no separate
  server, Playwright-only. The boundary: route = inside the browser, WireMock = a server you point at.
- `qa-network-monitoring-proxy-java` (#10) — out-of-browser MITM proxy on a *real* service's traffic;
  WireMock *replaces* the service. Mirror its fault-injection framing.
- `qa-api-client-writer-java` + `qa-api-test-author-generator-java` — the typed client / API tests
  pointed at the WireMock base URL (constructor injection).
- `qa-test-environments-java` + `qa-db-testing-testcontainers-java` — the Testcontainers run mode and the
  per-class-vs-per-test lifecycle trade-off mirrored here.
- `qa-ci-pipelines-github-actions-java` — runs these tests; the in-process server needs no service wiring
  (vs the container run mode, which needs Docker).
