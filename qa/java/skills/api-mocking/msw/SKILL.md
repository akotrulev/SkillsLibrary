---
name: qa-api-mocking-msw-java
description: >-
  API-mocking with MSW (Mock Service Worker) from a Java 21 + Spring Boot 3 + TestNG SUT — the **sidecar
  port** of the TS-native canonical. MSW **cannot** intercept in-process in the JVM, so here it runs as a
  **standalone Node sidecar mock server**: MSW handlers (`http.get`/`http.post` → `HttpResponse.json`)
  wrapped in an Express server by `@mswjs/http-middleware`'s `createServer(...handlers)` (started as a
  process or a Testcontainers Node container), and the JVM SUT's **constructor-injected** typed HTTP
  client points at the sidecar's base URL. Use when a JVM team wants to reuse MSW handlers (shared with a
  front-end) to fake a downstream HTTP dependency for an integration test. Covers the sidecar lifecycle,
  per-test handler overrides (a `/__mocks` control route on the sidecar), closure-state staged responses,
  Awaitility condition-waits (no `Thread.sleep`), and verifying the call via the sidecar's exposed event
  log. Triggers: "run MSW as a sidecar for our Spring Boot test", "fake the payments API with MSW handlers
  from Java", "point our Java client at an MSW mock server". Do NOT use for: the in-process app's-own-fetch
  interception MSW is built for (that's TS — use qa-api-mocking-msw-typescript, the canonical); a JVM-native
  standalone mock server with in-process scenarios + a request journal (use qa-api-mocking-wiremock-java —
  usually the better fit for a pure-JVM shop); the .NET sidecar port (use qa-api-mocking-msw-dotnet); an
  out-of-browser MITM proxy (use qa-network-monitoring-proxy-java).
---

# API Mocking — MSW / Mock Service Worker (Java 21 — sidecar port)

The **Java port** of the canonical `qa-api-mocking-msw-typescript`. **Read that first** — it explains the
MSW model (handlers → resolvers → responses) and the events API in MSW's native, in-runtime form.

> **⚠️ The port inverts the tool's nature — read this before anything else.** MSW's whole point is
> intercepting the app's **own** HTTP **in-runtime** (a Service Worker / Node `http` patch). **That cannot
> happen in the JVM** — MSW is a JavaScript tool and there is no in-process JVM interception. So in Java,
> MSW only makes sense run as a **standalone Node sidecar mock server**: `@mswjs/http-middleware`'s
> `createServer(...handlers)` wraps the MSW handlers in an Express server you start as a **separate
> process** (or a Testcontainers Node container), and your JVM SUT's typed client points at its base URL.
> **This is the inverse of WireMock (#22):** WireMock is JVM-native (in-process server) with a *thin TS
> client*; MSW is TS-native (in-runtime) with a *sidecar-only* JVM port. It is the same shape as
> `qa-accessibility-testing-lighthouse-ci-java` (#21) — a Node tool the JVM stack drives out-of-process.

> **Honest recommendation.** For a **pure-JVM** shop with no front-end MSW handlers to reuse, the canonical
> JVM mock server is **WireMock** (`qa-api-mocking-wiremock-java`) — in-process, scenarios, a real request
> journal, no Node dependency. Choose the MSW sidecar specifically when you want **one set of handlers
> shared** between the front-end (where MSW runs natively in-runtime) and a JVM integration test, so the
> mock contract lives in exactly one place. Otherwise prefer WireMock.

## Decision matrix — MSW sidecar vs the rest of the `api-mocking` family

| Need | Use | Why |
|------|-----|-----|
| Reuse **front-end MSW handlers** to fake a downstream dependency for a JVM test | **MSW sidecar (this skill)** | One handler set shared FE + JVM; the contract lives once |
| A JVM-native standalone mock server, in-process, scenarios + request journal, no Node | **WireMock** (`qa-api-mocking-wiremock-java`, #22) | Native, richer, no sidecar — the default for pure-JVM |
| Mock the **app's own** `fetch` **in-runtime** (front-end/Node) | MSW native (`qa-api-mocking-msw-typescript`) | That's MSW's real home — in-process, no server |
| **Protocol-agnostic** over-the-wire imposters | Mountebank (#24) | Multi-protocol `mb` server |
| Mock derived **from an OpenAPI spec** | Prism (#25) | Spec-driven |
| Out-of-browser MITM on a *real* service's traffic | `qa-network-monitoring-proxy-java` (#10) | BrowserUp proxy on the wire; MSW *replaces* the service |

**Rule of thumb (Java):** want a JVM mock server? → **WireMock**, unless you specifically need to **share
MSW handlers with a front-end** — then run them as this **sidecar**.

## Stack

- Java 21 + Spring Boot 3.x + TestNG + AssertJ + Awaitility
- The **MSW sidecar** — a tiny Node project: `msw` + `@mswjs/http-middleware` (`createServer(...handlers)`),
  run as a process or a [Testcontainers](https://java.testcontainers.org/) `GenericContainer` Node image
  (cross-link `qa-test-environments-java` / `qa-db-testing-testcontainers-java`)
- The SUT is a typed JVM HTTP client (`qa-api-client-writer-java`) — **constructor-injected** with the
  sidecar's base URL (never a static URL; the port is dynamic)

```kotlin
// build.gradle.kts (test deps)
testImplementation("org.testng:testng:7.10.2")
testImplementation("org.assertj:assertj-core:3.26.0")
testImplementation("org.awaitility:awaitility:4.2.1")
testImplementation("org.testcontainers:testcontainers:1.20.1")
```

## The MSW sidecar — handlers + a control surface

The sidecar is a small Node entrypoint. It registers the shared MSW handlers via `createServer(...)` and
adds two **control routes** so the JVM test can (a) override handlers per test and (b) read which requests
were seen — because over an HTTP boundary the JVM can't call `server.use(...)` or subscribe to
`server.events` directly (those are in-process JS APIs). This control surface is the sidecar's contract.

```javascript
// msw-sidecar/server.mjs
import { http, HttpResponse } from 'msw';
import { createServer } from '@mswjs/http-middleware';
import express from 'express';

const seen = [];                                   // the "journal" MSW itself doesn't keep — we add one
const dynamic = new Map();                          // per-test overrides keyed by "METHOD path"

const baseHandlers = [
  http.get('/api/widgets/:id', ({ params, request }) => {
    seen.push({ method: 'GET', url: request.url });
    const override = dynamic.get(`GET /api/widgets/${params.id}`) ?? dynamic.get('GET /api/widgets/:id');
    if (override) return HttpResponse.json(override.body, { status: override.status });
    return HttpResponse.json({ id: Number(params.id), name: 'Sprocket', priceMinor: 1999 });
  }),
  http.post('/api/orders', async ({ request }) => {
    const body = await request.clone().json().catch(() => undefined);
    seen.push({ method: 'POST', url: request.url, body });
    const override = dynamic.get('POST /api/orders');
    return HttpResponse.json(override?.body ?? { orderId: 'ord-7' }, { status: override?.status ?? 201 });
  }),
];

const app = createServer(...baseHandlers);          // Express app with MSW handlers applied
app.use(express.json());
// Control surface for the JVM test harness:
app.post('/__mocks/override', (req, res) => { dynamic.set(req.body.key, req.body); res.sendStatus(204); });
app.post('/__mocks/reset',    (_req, res) => { dynamic.clear(); seen.length = 0; res.sendStatus(204); });
app.get('/__mocks/seen',      (_req, res) => res.json(seen));

app.listen(Number(process.env.PORT ?? 0), () => console.log(`msw-sidecar:${app.address?.()?.port}`));
```

> The control routes (`/__mocks/*`) are how the JVM reaches MSW's in-process features (`server.use`,
> `server.events`) **across the process boundary**. In the native TS skill these are just method calls;
> here they must be exposed over HTTP. This is the unavoidable cost of the port.

## Sidecar lifecycle — Testcontainers Node image (default) or a process

One sidecar per suite (a container per test is far too slow — the same trade-off as
`qa-db-testing-testcontainers-java`). The SUT's client is injected with the mapped base URL; reset the
sidecar's overrides + journal between tests via `/__mocks/reset`.

```java
public final class MswSidecar implements AutoCloseable {
    private final GenericContainer<?> container;
    private final HttpClient http = HttpClient.newHttpClient();

    public MswSidecar() {
        // A Node image that has the sidecar project mounted/built; exposes the Express port.
        this.container = new GenericContainer<>(DockerImageName.parse("msw-sidecar:local"))
                .withExposedPorts(8080)
                .waitingFor(Wait.forLogMessage(".*msw-sidecar.*", 1));
        container.start();
    }

    public String baseUrl() {
        return "http://%s:%d".formatted(container.getHost(), container.getMappedPort(8080));
    }

    public void overrideJson(String key, int status, String jsonBody) throws Exception {
        post("/__mocks/override",
                "{\"key\":\"%s\",\"status\":%d,\"body\":%s}".formatted(key, status, jsonBody));
    }

    public void reset() throws Exception { post("/__mocks/reset", ""); }

    public List<SeenRequest> seen() throws Exception {
        var res = http.send(HttpRequest.newBuilder(URI.create(baseUrl() + "/__mocks/seen")).GET().build(),
                HttpResponse.BodyHandlers.ofString());
        return SeenRequest.parseList(res.body());          // Jackson into a small record list
    }

    private void post(String path, String body) throws Exception {
        http.send(HttpRequest.newBuilder(URI.create(baseUrl() + path))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body)).build(),
                HttpResponse.BodyHandlers.discarding());
    }

    @Override public void close() { container.stop(); }
}
```

```java
public abstract class MswSidecarTest {
    protected static MswSidecar sidecar;
    protected WidgetApiClient client;

    @BeforeClass public static void startSidecar() { sidecar = new MswSidecar(); }
    @AfterClass  public static void stopSidecar()  { sidecar.close(); }

    @BeforeMethod public void wireClient() {
        // Constructor-injected base URL — never a static one; the mapped port is dynamic.
        client = new WidgetApiClient(sidecar.baseUrl());
    }

    @AfterMethod public void resetSidecar() throws Exception { sidecar.reset(); } // keep tests independent
}
```

## Core pattern — exercise, assert outcome, verify via the sidecar journal

```java
public final class WidgetLookupTest extends MswSidecarTest {

    @Test
    public void Should_return_the_widget_When_the_sidecar_responds_200() {
        // Uses the sidecar's default handler.
        Widget widget = client.getWidget(42);

        assertThat(widget)
                .isEqualTo(new Widget(42, "Sprocket", 1999));      // one logical assertion: the outcome
    }
}
```

## Per-test overrides — the `/__mocks/override` control route

The MSW-native `server.use(...)` becomes an HTTP call to the sidecar's control route. Reset in
`@AfterMethod` (already wired above) drops it so tests stay independent.

```java
@Test
public void Should_surface_an_error_When_the_dependency_returns_500() throws Exception {
    sidecar.overrideJson("GET /api/widgets/42", 500, "{\"message\":\"upstream down\"}");

    assertThatThrownBy(() -> client.getWidget(42))
            .isInstanceOf(UpstreamException.class)
            .hasMessageContaining("upstream");
}
```

## Stateful behavior — closure state in the sidecar (the Scenarios analogue)

Staged responses (first call pending, then done) live as **closure state in the handler** (a JS variable
in `server.mjs`), exactly as in the native skill — the JVM just polls the client until it sees the final
state. **Wait on the condition with Awaitility, never `Thread.sleep`** (the global no-sleep rule). The
sidecar's delay (if any) *simulates* latency; Awaitility *asserts* the condition.

```java
@Test
public void Should_poll_until_the_order_is_DONE() {
    // The /api/orders/7/status handler in server.mjs returns PENDING then DONE via a closure counter.
    await().atMost(Duration.ofSeconds(5)).pollInterval(Duration.ofMillis(100))
           .until(() -> client.getOrderStatus(7).state(), equalTo("DONE"));
}
```

## Verification — the sidecar's exposed event log (MSW has no journal)

The native skill subscribes to `server.events.on('request:match', ...)`; **MSW keeps no queryable request
journal**, so the sidecar collects intercepted requests into `seen[]` and exposes them at `/__mocks/seen`.
The JVM reads that log to assert the call happened with the right payload.

```java
@Test
public void Should_POST_the_order_once_with_the_right_body() throws Exception {
    client.submitOrder(OrderRequestMother.standard());

    List<SeenRequest> posts = sidecar.seen().stream()
            .filter(r -> r.method().equals("POST") && r.url().endsWith("/api/orders"))
            .toList();

    assertThat(posts).hasSize(1);
    assertThat(posts.get(0).body()).contains("\"sku\":\"SPR-1\"", "\"qty\":3");
}
```

Prefer asserting on the **SUT's resulting state** (a persisted row via `qa-db-testing-client-java`, a
returned value) when you can — it's stronger than "the call was made"; reach for the journal when the call
itself is the contract (idempotency key, exact payload).

## Run modes

| Mode | How | When |
|------|-----|------|
| **Testcontainers Node image** (default) | `GenericContainer("msw-sidecar:local")` exposing the Express port | CI-parity, reachable on the Docker network, no host Node needed |
| **Local Node process** | `node msw-sidecar/server.mjs` on a fixed port, started in `@BeforeClass` | Fast local iteration; needs Node on the box |
| **In-process** | n/a in the JVM | MSW can't intercept in-process here — that's the TS canonical only |

## Anti-patterns

- **Treating the JVM MSW sidecar as the default JVM mock server.** It carries a Node dependency + a
  bespoke control surface. *Fix:* use **WireMock** (`qa-api-mocking-wiremock-java`) for pure-JVM; pick the
  MSW sidecar only to **share handlers with a front-end**.
- **`Thread.sleep` to wait for a staged/async flow.** Races the sidecar. *Fix:* Awaitility `await()...until(...)`
  on the client's visible state; sidecar `delay` only *simulates* latency.
- **A static/hard-coded sidecar URL.** The mapped port is dynamic. *Fix:* constructor-inject
  `sidecar.baseUrl()` into the typed client.
- **Forgetting `/__mocks/reset` between tests.** Overrides + the journal leak; order starts to matter.
  *Fix:* `@AfterMethod` reset.
- **Starting a sidecar per test.** Too slow. *Fix:* one per suite (`@BeforeClass`), reset state between.
- **Asserting only the outcome when the call is the contract.** *Fix:* read `/__mocks/seen` and assert
  body/headers/count.

## Examples

**End-to-end: a retry-then-succeed flow via sidecar closure state + a verify on the POST count.**

```java
public final class OrderSubmissionTest extends MswSidecarTest {

    @Test
    public void Should_retry_then_succeed_When_orders_API_is_briefly_unavailable() throws Exception {
        // The sidecar's /api/orders handler returns 503 on the first call then 201 (closure counter).
        Order order = client.submitOrder(OrderRequestMother.standard());   // SUT has a retry policy

        assertThat(order.orderId()).isEqualTo("ord-7");                    // one logical assertion: outcome

        long attempts = sidecar.seen().stream()
                .filter(r -> r.method().equals("POST") && r.url().endsWith("/api/orders")).count();
        assertThat(attempts).isEqualTo(2);                                 // retried once
    }
}
```

**Test-data builder for request payloads (4+ fields → builder, per the global rules).**

```java
public final class OrderRequestMother {
    public static OrderRequest standard() {
        return new OrderRequestBuilder()
                .withSku("SPR-1").withQty(3).withCurrency("EUR").withIdempotencyKey("idem-123").build();
    }
}
```

## Rules (hard constraints)

- MSW **cannot** intercept in-process in the JVM — it runs as a **standalone Node sidecar**; the SUT's
  typed client is **constructor-injected** with the sidecar's mapped base URL (never static).
- One sidecar per suite (`@BeforeClass`) + `/__mocks/reset` in `@AfterMethod` — keep tests independent.
  Never a sidecar per test.
- Per-test overrides via the `/__mocks/override` control route; staged responses via closure state in the
  sidecar handler.
- **No `Thread.sleep`.** Awaitility `await()...until(...)` on the client's visible state; sidecar `delay`
  only to *simulate* latency.
- Verify via the sidecar's `/__mocks/seen` log (MSW has **no journal**); prefer asserting the SUT's
  resulting state when you can.
- Assert both sides: the **outcome** (one logical assertion) **and**, when the call is the contract, the
  **request** (body/headers/count) from `/__mocks/seen`.
- Builders/ObjectMother for request payloads with 4+ fields; test names `Should_X_When_Y`; structured
  logging (message templates); no secrets in handlers or sidecar config.
- Prefer **WireMock** for a pure-JVM mock server; use the MSW sidecar to **share handlers with a front-end**.

## Cross-references

- `qa-api-mocking-msw-typescript` — the **canonical**, TS-native stack: MSW intercepts the app's own
  `fetch` **in-runtime** (`setupServer`/`setupWorker`), no sidecar. Structure ported from there; the
  interception model becomes a server here.
- `qa-api-mocking-msw-dotnet` — the **.NET sidecar port**, same shape (Node sidecar + injected base URL,
  NUnit + `WaitForRequestAsync`-style condition-wait).
- `qa-api-mocking-wiremock-java` (#22) — the JVM-native standalone mock server (in-process
  `WireMockServer`, scenarios, real journal). **Usually the better fit for a pure-JVM shop**; the key
  contrast: WireMock is JVM-native, MSW is a Node sidecar here. The inverse of this node's port story.
- `qa-api-client-writer-java` + `qa-api-test-author-generator-java` — the typed JVM client / API tests
  pointed at the sidecar base URL (constructor injection).
- `qa-test-environments-java` + `qa-db-testing-testcontainers-java` — the Node-sidecar run mode (process
  or Testcontainers Node image) + the per-suite-vs-per-test lifecycle trade-off mirrored here.
- `qa-network-monitoring-proxy-java` (#10) — BrowserUp out-of-browser MITM proxy on a *real* service's
  traffic; MSW *replaces* the service. Mirror its fault-injection framing.
- `qa-ci-pipelines-github-actions-java` — runs these tests; needs Node available in the job for the
  sidecar (process) or Docker for the Testcontainers Node image.
