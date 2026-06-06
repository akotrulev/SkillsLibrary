---
name: qa-api-mocking-mountebank-java
description: >-
  Service-virtualization / API-mocking with Mountebank (`mb`) in Java 21 (TestNG): run Mountebank as a
  **standalone, protocol-agnostic** server (a Testcontainers `bbyars/mountebank` `GenericContainer`, or the
  `mb` CLI) and drive it entirely over its **HTTP REST control API** with `java.net.http.HttpClient` —
  `POST /imposters` to create an **imposter** (`{ port, protocol, stubs:[{predicates,responses}],
  recordRequests }`), point the system-under-test's constructor-injected typed client at the imposter's port,
  exercise the flow, read the imposter's recorded `requests` array to verify, then `DELETE /imposters` to
  reset. Use when a test must run against a controlled fake of a downstream dependency and you want a
  **standalone server** (like WireMock) that is **stack-agnostic** and can speak **multiple protocols**
  (`http`, `https`, `tcp`, `smtp`). Covers predicates (`equals`/`deepEquals`/`contains`/`matches`/`exists`/
  `startsWith`/`endsWith`, jsonpath/xpath, `and`/`or`/`not`), responses (`is` canned / `proxy` record-replay
  / `inject` JS), the **multiple-responses cycling** staged analogue (`[{is:503},{is:201}]`), `_behaviors`
  (`wait`/`repeat`/`decorate`), a `tcp` imposter, and per-imposter recorded-request verification with
  Awaitility for condition-waits. Triggers: "mock the payment API with Mountebank in Java", "create an mb
  imposter for this TestNG test", "Mountebank returns 503 then 201", "fake a TCP service", "verify the
  imposter recorded the POST". Do NOT use for: an out-of-browser MITM proxy on a real client's live traffic
  (use qa-network-monitoring-proxy-java), the richest HTTP-only server with in-process JVM run mode (prefer
  WireMock, qa-api-mocking-wiremock-java), an OpenAPI-spec-driven mock (use Prism, #25), the TypeScript stack
  (the canonical — use qa-api-mocking-mountebank-typescript), or the .NET stack (use
  qa-api-mocking-mountebank-dotnet).
---

# API Mocking — Mountebank (Java 21 / TestNG)

The Java port of the canonical `qa-api-mocking-mountebank-typescript`. Mountebank is **stack-agnostic** —
there is **no native in-process Mountebank in any runtime** (unlike WireMock, which the `qa-api-mocking-
wiremock-java` sibling runs in-process on the JVM). Every stack does the identical thing: it is a **thin HTTP
client to a running `mb` server** driven over an **HTTP REST control API**. So this file ports the canonical
almost 1:1 — same `POST /imposters` → exercise → `GET /imposters/:port` → `DELETE /imposters` REST calls;
only the HTTP-client idioms change (here, `java.net.http.HttpClient` + Jackson).

Mountebank is a **standalone, protocol-agnostic service-virtualization server**: stand up `mb` (here a
container), `POST` an **imposter** to it (a fake service bound to a port speaking a chosen protocol), point
the SUT's typed client at the imposter's port, exercise, then read the imposter's recorded `requests` to
verify, and `DELETE` imposters between tests.

> **The boundary that defines this skill.** Mountebank is a **standalone server you point a client at** — it
> *replaces* the dependency, the same end of the wire as WireMock. That is the line against the
> `network-monitoring` family: `qa-network-monitoring-proxy-java` is an *out-of-browser MITM proxy* on a
> *real* client's live traffic. Mountebank, like WireMock, **is** the dependency — but it adds **multiple
> protocols** and is driven purely over a REST API.

## Decision matrix — Mountebank vs the rest of the `api-mocking` family, vs network-monitoring

| Need | Use | Why |
|------|-----|-----|
| A **multi-protocol** (`http`/`https`/`tcp`/`smtp`) standalone server, driven over a REST API, stack-agnostic | **Mountebank (this skill)** | Imposters speak more than HTTP — the headline; thin REST client in every stack |
| The **richest HTTP** server + **in-process JVM** run mode; Handlebars templating, scenarios | **WireMock** (`qa-api-mocking-wiremock-java`, #22) | HTTP-focused but deeper; runs in-process in the JVM (Mountebank never does) |
| Mock the app's **own** outbound HTTP **in-runtime**, no separate server | **MSW** (`qa-api-mocking-msw-java` — a Node sidecar port, #23) | Interception in the app's process; TS-native, Java is a sidecar |
| Observe / rewrite a **real client's** live traffic out-of-browser (MITM) | `qa-network-monitoring-proxy-java` (#10) | Proxy on the wire to the *real* service; Mountebank replaces it |
| Mock derived **from an OpenAPI spec** automatically | Prism (#25) | Spec-driven |

**Rule of thumb (Java):** *Need a standalone fake and your dependency speaks **TCP/SMTP** or you want one tool
across many stacks?* → Mountebank. *HTTP-only, want in-process on the JVM or Handlebars/scenarios?* →
WireMock. *Real-service traffic?* → the network-monitoring family.

## Stack

- Java 21 + TestNG + AssertJ
- [Testcontainers](https://testcontainers.com/) (`GenericContainer`) running the
  [`bbyars/mountebank`](https://hub.docker.com/r/bbyars/mountebank) image — the default run mode (cross-link
  `qa-test-environments-java` / `qa-db-testing-testcontainers-java`)
- `java.net.http.HttpClient` (JDK built-in) for the thin REST client to the `mb` **admin API** (port `2525`)
  and to the imposter; **Jackson** (`ObjectMapper`) for the imposter/predicate/response JSON
- [Awaitility](http://www.awaitility.org/) for condition-waits (never `Thread.sleep`)
- A typed client (`qa-api-client-writer-java`) is the SUT — **constructor-injected** with the imposter base URL

```kotlin
// build.gradle.kts
testImplementation("org.testng:testng:7.10.2")
testImplementation("org.assertj:assertj-core:3.26.3")
testImplementation("org.testcontainers:testcontainers:1.20.4")
testImplementation("org.awaitility:awaitility:4.2.2")
testImplementation("com.fasterxml.jackson.core:jackson-databind:2.18.2")
```

## The Mountebank model — imposters, stubs, lifecycle

Mountebank's whole model is three nested concepts, all JSON over the REST API:

- An **imposter** = a fake service bound to a `port`, speaking a `protocol` (`http`/`https`/`tcp`/`smtp`),
  holding an ordered list of **stubs**.
- A **stub** = `{ predicates, responses }`. The **first stub whose predicates all match** answers the request.
- **Predicates** decide *whether* a stub matches; **responses** decide *what* it returns.

The lifecycle of every suite that uses `mb`:

1. **Start** the `mb` server — a `GenericContainer("bbyars/mountebank")` exposing the admin port `2525`.
2. **Connect** the admin client — an `HttpClient` pointed at `http://<host>:<adminPort>`.
3. **Create an imposter** — `POST /imposters` with `{ port, protocol, stubs, recordRequests: true }`.
4. **Point the SUT at the imposter's base URL** — injected into the typed client's constructor.
5. **Exercise** the SUT so it calls the dependency.
6. **Verify** via the imposter's recorded `requests` — `GET /imposters/:port`.
7. **Reset** between tests — `DELETE /imposters`; **stop** the container at teardown.

### The admin client + container fixture (per-class)

Mirror the lifecycle trade-off from `qa-db-testing-testcontainers-java`: **one container per class**
(`@BeforeClass`/`@AfterClass`), delete imposters in `@AfterMethod` so they don't leak. A container per test is
far too slow.

```java
// src/test/java/support/MbClient.java — a thin REST client to the mb admin API (port 2525).
package support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.List;

public final class MbClient {
    private final HttpClient http = HttpClient.newHttpClient();
    private final ObjectMapper mapper = new ObjectMapper();
    private final String adminUrl;

    public MbClient(String adminUrl) {
        this.adminUrl = adminUrl;
    }

    /** POST /imposters — body is the imposter spec built as a Jackson tree (see ImposterBuilder). */
    public void createImposter(JsonNode imposter) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(adminUrl + "/imposters"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(imposter)))
                .build();
        HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString());
        if (res.statusCode() >= 300) {
            throw new IllegalStateException("createImposter failed: " + res.statusCode() + " " + res.body());
        }
    }

    /** GET /imposters/:port — the recorded-request journal (needs recordRequests:true on the imposter). */
    public List<JsonNode> recordedRequests(int imposterPort) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(adminUrl + "/imposters/" + imposterPort)).GET().build();
        HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString());
        JsonNode requests = mapper.readTree(res.body()).path("requests");
        List<JsonNode> out = new ArrayList<>();
        requests.forEach(out::add);
        return out;
    }

    public void deleteAllImposters() throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(adminUrl + "/imposters")).DELETE().build();
        http.send(req, HttpResponse.BodyHandlers.discarding());
    }
}
```

```java
// src/test/java/support/MountebankFixture.java
package support;

import org.testcontainers.containers.GenericContainer;
import org.testcontainers.utility.DockerImageName;

public final class MountebankFixture {
    public static final int IMPOSTER_PORT = 4545;   // the imposter's own port — distinct from admin (2525)

    public static GenericContainer<?> container;
    public static MbClient mb;
    public static WidgetApiClient client;

    public static void start() {
        container = new GenericContainer<>(DockerImageName.parse("bbyars/mountebank:2.9.1"))
                .withExposedPorts(2525, IMPOSTER_PORT)          // expose BOTH admin and imposter ports
                .withCommand("mb", "start", "--allowInjection"); // --allowInjection only if you use `inject`
        container.start();

        String adminUrl = "http://" + container.getHost() + ":" + container.getMappedPort(2525);
        mb = new MbClient(adminUrl);

        // The SUT's typed client is constructor-injected with the imposter's mapped base URL — never static.
        String imposterBaseUrl = "http://" + container.getHost() + ":" + container.getMappedPort(IMPOSTER_PORT);
        client = new WidgetApiClient(imposterBaseUrl);
    }

    public static void resetImposters() throws Exception {
        mb.deleteAllImposters();   // wipe imposters (and journals) so tests stay independent
    }

    public static void stop() {
        if (container != null) container.stop();
    }
}
```

> **Two ports, one container.** The **admin port** (`2525`) is where you POST imposters; each **imposter**
> binds its own port (`4545`) that the SUT talks to. Expose and map both. Re-creating the imposter in each
> test (after `@AfterMethod` deletes it) keeps tests independent.

### Building imposter JSON — a builder (4+ fields → builder, per the global rules)

```java
// src/test/java/support/ImposterBuilder.java — builds the imposter Jackson tree fluently.
package support;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

public final class ImposterBuilder {
    private static final ObjectMapper M = new ObjectMapper();
    private final ObjectNode imposter = M.createObjectNode();
    private final ArrayNode stubs = M.createArrayNode();

    public ImposterBuilder(int port, String protocol) {
        imposter.put("port", port).put("protocol", protocol).put("recordRequests", true);
    }

    /** A stub = predicates (match) → responses (return), both pre-built JSON nodes. */
    public ImposterBuilder stub(ArrayNode predicates, ArrayNode responses) {
        ObjectNode stub = M.createObjectNode();
        stub.set("predicates", predicates);
        stub.set("responses", responses);
        stubs.add(stub);
        return this;
    }

    public ObjectNode build() {
        imposter.set("stubs", stubs);
        return imposter;
    }
}
```

## Core pattern — create the imposter, point the client, exercise, verify

The SUT is a typed client constructor-injected with the imposter's base URL (cross-link
`qa-api-client-writer-java`). The test creates an imposter, drives the client, asserts the **response** (one
logical assertion), and verifies the **request** via the recorded-request journal.

```java
package api.mocking;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import org.testng.annotations.*;
import support.*;

import static org.assertj.core.api.Assertions.assertThat;
import static support.MountebankFixture.*;

public class WidgetLookupTest {
    private static final ObjectMapper M = new ObjectMapper();

    @BeforeClass public void startMb() { MountebankFixture.start(); }
    @AfterMethod public void reset() throws Exception { MountebankFixture.resetImposters(); }
    @AfterClass public void stopMb() { MountebankFixture.stop(); }

    @Test
    public void Should_return_the_widget_When_the_imposter_responds_200() throws Exception {
        // 1. Create the imposter: a stub = predicates (match) → responses (return).
        ArrayNode predicates = M.createArrayNode();
        predicates.addObject().putObject("equals").put("method", "GET").put("path", "/api/widgets/42");

        ArrayNode responses = M.createArrayNode();
        responses.addObject().putObject("is")
                .put("statusCode", 200)
                .put("body", "{\"id\":42,\"name\":\"Sprocket\",\"priceMinor\":1999}")
                .putObject("headers").put("Content-Type", "application/json");

        mb.createImposter(new ImposterBuilder(IMPOSTER_PORT, "http").stub(predicates, responses).build());

        // 2. Exercise the SUT (already pointed at the imposter's base URL).
        Widget widget = client.getWidget(42);

        // 3. Assert the response (one logical assertion).
        assertThat(widget).isEqualTo(new Widget(42, "Sprocket", 1999));

        // 4. Verify the request the SUT actually sent (the recorded-request journal).
        assertThat(mb.recordedRequests(IMPOSTER_PORT)).hasSize(1);
    }
}
```

The imposter must be created **before** the action that triggers the request. An HTTP `is` response's `body`
is a **string** (serialize JSON yourself) and set `Content-Type`.

## Predicates — which requests this stub answers

A stub's `predicates` are **ANDed**; the **first stub** whose predicates all match wins. Predicates match
over `method`, `path`, `query`, `headers`, `body`:

```java
ArrayNode predicates = M.createArrayNode();
predicates.addObject().putObject("equals").put("method", "POST").put("path", "/api/orders");
predicates.addObject().putObject("contains").putObject("headers").put("Content-Type", "application/json");
predicates.addObject().putObject("matches").put("body", "\"sku\"\\s*:\\s*\"SPR-1\"");   // regex over raw body
```

Predicate cheatsheet (the analogue of WireMock matchers):

| Match on | Predicate |
|----------|-----------|
| Exact equality (case-insensitive by default) | `{ "equals": { "path": "/a/b" } }` |
| Deep/exact object equality | `{ "deepEquals": { "query": { "k": "v" } } }` |
| Substring | `{ "contains": { "body": "needle" } }` |
| Regex | `{ "matches": { "path": "/api/widgets/[0-9]+" } }` |
| Field present | `{ "exists": { "headers": { "Authorization": true } } }` |
| Prefix / suffix | `{ "startsWith": {...} }` / `{ "endsWith": {...} }` |
| JSON-body selector | add `"jsonpath": { "selector": "$..sku" }` to a predicate |
| XML-body selector | add `"xpath": { "selector": "//sku" }` to a predicate |
| Case-sensitive match | add `"caseSensitive": true` to the predicate |
| Boolean combination | `{ "and": [...] }` / `{ "or": [...] }` / `{ "not": {...} }` |

**Ordering is the catch-all.** Mountebank serves the **first matching stub**, so put specific stubs first and
a **predicate-less stub last** as a deterministic fallback (a stub with no `predicates` matches everything):

```java
// specific stub first…
builder.stub(specificPredicates, ok200);
// …predicate-less catch-all LAST.
ArrayNode fallback = M.createArrayNode();
fallback.addObject().putObject("is").put("statusCode", 404).put("body", "no stub matched");
builder.stub(M.createArrayNode(), fallback);   // empty predicates = matches everything
```

## Responses — `is` canned, the multiple-responses cycle, `proxy`, `inject`

A stub's `responses` is an **array**. On repeated matching requests Mountebank **cycles through the array**,
repeating the last entry once exhausted — Mountebank's **stateful / staged analogue** of WireMock Scenarios,
**no state machine needed**:

```java
// 503 on the first call, 201 on every call after — a transient-failure-then-recovery flow.
ArrayNode responses = M.createArrayNode();
responses.addObject().putObject("is").put("statusCode", 503);                    // 1st call
responses.addObject().putObject("is").put("statusCode", 201)
        .put("body", "{\"orderId\":\"ord-7\"}");                                 // 2nd call onward
```

Response types:

| Type | What it does | Analogue |
|------|--------------|----------|
| `is` | A canned response (`statusCode`/`headers`/`body`) | WireMock response definition |
| `proxy` | Record-and-replay against a **real upstream** (`{ to, mode }`) | WireMock recording |
| `inject` | A **JS function** computing the response — requires `--allowInjection` | WireMock Handlebars templating |

`inject` is a **sharp edge**: it needs `mb start --allowInjection`, runs arbitrary JS server-side, and is
harder to review. Prefer `is` + the response cycle; reach for `inject` only when the response must be computed
from the request.

## Fault & latency — `_behaviors`

`_behaviors` decorate a response before it is sent. The headline for resilience tests is **`wait`** — it
makes the imposter respond slowly so you can exercise the SUT's timeout/retry paths. **`wait` SIMULATES
latency — it is never a test sleep:**

```java
// Latency: the imposter itself is slow — SIMULATE slowness here, never Thread.sleep in the test.
ArrayNode responses = M.createArrayNode();
ObjectNode r = responses.addObject();
r.putObject("is").put("statusCode", 200).put("body", "{}");
r.putObject("_behaviors").put("wait", 2000);   // 2s server-side delay
```

Other `_behaviors`: `repeat` (serve the same response N times before advancing the cycle), `decorate` (a JS
post-processor, also needs `--allowInjection`), `copy`/`lookup` (inject request data into the response). For
**hard faults** (dropped/garbled connection) use the `tcp` protocol and close the socket.

Cross-link the fault-injection framing of `qa-network-monitoring-proxy-java` — the proxy injects faults onto a
*real* service's traffic; Mountebank injects them **as** the (fake) service, like WireMock. Assert on the
SUT's **visible outcome** (a thrown exception, a fallback, a retry count) — and when you wait for an async
result, **wait on the condition** with **Awaitility**, never `Thread.sleep`:

```java
import static org.awaitility.Awaitility.await;
import java.time.Duration;

await().atMost(Duration.ofSeconds(10)).pollInterval(Duration.ofMillis(200))
       .until(() -> client.getOrderStatus(7).state().equals("DONE"));
```

## Multi-protocol — the headline (a `tcp` imposter)

Mountebank's reason to exist alongside WireMock is that an imposter can speak more than HTTP. Stand up a
**`tcp`** imposter to fake a non-HTTP dependency — exactly what WireMock cannot do. A `tcp` imposter's `is`
response uses a `data` field (the bytes to send back) instead of HTTP `statusCode`/`body`:

```java
// A second imposter on protocol 'tcp' — fake a raw socket service with a canned response.
ArrayNode tcpPredicates = M.createArrayNode();
tcpPredicates.addObject().putObject("contains").put("data", "PING");
ArrayNode tcpResponses = M.createArrayNode();
tcpResponses.addObject().putObject("is").put("data", "PONG\n");
mb.createImposter(new ImposterBuilder(5555, "tcp").stub(tcpPredicates, tcpResponses).build());
// expose+map port 5555 on the container too.
```

The *same* REST control API, predicate/response/journal model serve `http`, `tcp`, and `smtp`; only the `is`
payload shape changes (`statusCode`/`body` for HTTP, `data` for TCP).

## Verification — the recorded-request journal

Mountebank **keeps a request journal per imposter** when created with `recordRequests: true` — `GET
/imposters/:port` returns a `requests` array. The server-side "was X called, with what" assertion, decoupled
from the stub. **Make the contrast explicit: Mountebank *keeps* a journal (like WireMock); MSW (#23) does
*not*.**

```java
// Called exactly once, with the right body and header.
List<JsonNode> calls = mb.recordedRequests(IMPOSTER_PORT);
List<JsonNode> posts = calls.stream()
        .filter(r -> r.path("method").asText().equals("POST") && r.path("path").asText().equals("/api/orders"))
        .toList();
assertThat(posts).hasSize(1);
assertThat(posts.get(0).path("body").asText()).contains("\"sku\":\"SPR-1\"");
assertThat(posts.get(0).path("headers").has("Idempotency-Key")).isTrue();

// Never called (negative assertion).
assertThat(calls.stream().anyMatch(r -> r.path("path").asText().equals("/api/legacy-pricing"))).isFalse();
```

Verification reads the journal **separately** from the stub — return a generic `201` and still assert the
exact body the SUT POSTed. `recordRequests: true` is required for the journal to populate.

## Run modes — container / standalone CLI

| Mode | How | When |
|------|-----|------|
| **Testcontainers container** (default) | `GenericContainer("bbyars/mountebank")` exposing `2525` + imposter ports | The default — CI-parity, reachable on the Docker network; identical run mode across all three stacks |
| **Standalone `mb` CLI** | `mb start --configfile imposters.json` | A shared mock across processes; manual exploration; declarative config |

There is **no in-process mode** in any stack (contrast WireMock, which runs in-process on the JVM) — that is
exactly why this Java port is a thin REST client nearly identical to the TS canonical.

## Anti-patterns

- **`Thread.sleep` to wait for an async / staged flow.** Races the server and is slow. *Fix:* the **response
  cycle** for staged responses + **Awaitility** on the client's visible state. `_behaviors.wait` only to
  *simulate* latency.
- **Forgetting `recordRequests: true`.** The `requests` array stays empty and verification silently passes.
  *Fix:* set it on every imposter you verify against.
- **Not deleting imposters between tests.** Imposters and journals leak; ports collide. *Fix:* `DELETE
  /imposters` in `@AfterMethod`, re-create per test.
- **Starting a container per test.** Far too slow. *Fix:* one container per class (`@BeforeClass`), delete
  imposters between tests.
- **Hard-coding the SUT's base URL instead of injecting the mapped imposter port.** The port is dynamic.
  *Fix:* construct the typed client with the mapped imposter URL.
- **Putting the catch-all stub first.** Mountebank serves the *first* matching stub, so a leading
  predicate-less stub shadows everything. *Fix:* specific stubs first, predicate-less fallback last.
- **Reaching for `inject` for everything.** Arbitrary server-side JS, needs `--allowInjection`. *Fix:* `is` +
  the response cycle covers most cases.
- **Asserting only the response, never the request.** A passing response can hide a wrong payload. *Fix:* read
  the recorded `requests` and assert body/headers/count.
- **Reaching for Mountebank to mock the app's own outbound HTTP.** That's in-runtime interception. *Fix:* MSW
  (`qa-api-mocking-msw-java`, a Node sidecar port); Mountebank is a separate server.

## Examples

**End-to-end: a retry-then-succeed flow via the response cycle, with a verify on the recorded POSTs.**

```java
package api.mocking;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import org.testng.annotations.*;
import support.*;

import static org.assertj.core.api.Assertions.assertThat;
import static support.MountebankFixture.*;

public class OrderSubmissionTest {
    private static final ObjectMapper M = new ObjectMapper();

    @BeforeClass public void startMb() { MountebankFixture.start(); }
    @AfterMethod public void reset() throws Exception { MountebankFixture.resetImposters(); }
    @AfterClass public void stopMb() { MountebankFixture.stop(); }

    @Test
    public void Should_retry_then_succeed_When_orders_API_is_briefly_unavailable() throws Exception {
        ArrayNode predicates = M.createArrayNode();
        predicates.addObject().putObject("equals").put("method", "POST").put("path", "/api/orders");

        // The response array cycles: 503 first, then 201 — the staged analogue of a WireMock scenario.
        ArrayNode responses = M.createArrayNode();
        responses.addObject().putObject("is").put("statusCode", 503);                         // 1st attempt
        responses.addObject().putObject("is").put("statusCode", 201)
                .put("body", "{\"orderId\":\"ord-7\"}");                                       // retry onward

        mb.createImposter(new ImposterBuilder(IMPOSTER_PORT, "http").stub(predicates, responses).build());

        // SUT has a retry policy; it should transparently recover.
        Order order = client.submitOrder(OrderRequestMother.standard());

        assertThat(order.orderId()).isEqualTo("ord-7");           // one logical assertion: outcome
        long attempts = mb.recordedRequests(IMPOSTER_PORT).stream()
                .filter(r -> r.path("method").asText().equals("POST")).count();
        assertThat(attempts).isEqualTo(2);                        // retried once
    }
}
```

Lifecycle for this test:
1. `@BeforeClass` starts the `mb` container; the typed client is injected with the mapped imposter base URL.
2. One stub stages a 503 → 201 cycle on the same endpoint (no state machine — the response array cycles).
3. The SUT's retry policy turns the transient 503 into success — the test asserts the **outcome** and verifies
   the dependency was hit exactly twice via the recorded-request journal.
4. `@AfterMethod` deletes all imposters; the next test re-creates a clean one.

**Test-data builder for stub payloads (4+ fields → builder).**

```java
public final class OrderRequestMother {
    public static OrderRequest standard() {
        return new OrderRequestBuilder()
                .sku("SPR-1").qty(3).currency("EUR").idempotencyKey("idem-123").build();
    }
}
```

## Rules (hard constraints)

- Mountebank is a **standalone, protocol-agnostic server you point a client at** — inject the imposter's
  mapped base URL into the typed client (`qa-api-client-writer-java`); never hard-code the dynamic port.
- Create the imposter **before** the action that triggers the request; the **first matching stub** wins, so
  order stubs specific-first, predicate-less catch-all last.
- One container per class (`@BeforeClass`) + `DELETE /imposters` in `@AfterMethod`, re-create per test — keep
  tests independent. Never a container per test.
- Set `recordRequests: true` on any imposter you verify against; assert both the **response** (one logical
  assertion) **and** the **request** (recorded `requests`).
- **No `Thread.sleep`.** Use the **response cycle** for staged responses, `_behaviors.wait` to *simulate*
  latency, and **Awaitility** to *assert* on a condition.
- Prefer `is` + the response cycle; reserve `proxy` for record-replay and `inject` (needs `--allowInjection`)
  for genuinely computed responses.
- Builders/ObjectMother for imposter/stub/predicate/response payloads with 4+ fields.
- Test names `Should_X_When_Y`; constructor injection; structured logging; no secrets in imposter specs.
- Prefer **WireMock** for the richest HTTP-only server or in-process JVM; **MSW** (sidecar) for the app's own
  in-runtime HTTP; the MITM proxy for real-service traffic — use Mountebank for multi-protocol or one tool
  across many stacks.

## Cross-references

- `qa-api-mocking-mountebank-typescript` — the **canonical** stack, Node/Vitest (`fetch` REST client +
  `bbyars/mountebank` container). Structure ported from there; this Java port makes the same REST calls.
- `qa-api-mocking-mountebank-dotnet` — same skill, .NET/NUnit (`HttpClient`, async-all-the-way). Same REST
  choreography.
- `qa-api-mocking-wiremock-java` (#22) — the **standalone-server peer** and the JVM-native one. Both replace
  the dependency and keep a journal; **Mountebank adds multiple protocols and is stack-agnostic**, **WireMock
  is richer on HTTP and runs in-process on the JVM** (Mountebank never does).
- `qa-api-mocking-msw-java` (#23) — the **in-runtime vs standalone-server** contrast (MSW is a Node sidecar in
  Java; keeps **no** journal; Mountebank is a separate server that *does*).
- Prism (#25, next) — the **OpenAPI-spec-driven** member; same stack-agnostic CLI/container + thin-client port
  story as Mountebank.
- `qa-network-monitoring-proxy-java` (#10) — out-of-browser MITM proxy on a *real* service's traffic;
  Mountebank *replaces* the service. Mirror its fault-injection framing.
- `qa-api-client-writer-java` + `qa-api-test-author-generator-java` — the typed client / API tests pointed at
  the imposter base URL (constructor injection).
- `qa-test-environments-java` + `qa-db-testing-testcontainers-java` — the container run mode + the
  per-class-vs-per-test lifecycle trade-off mirrored here.
- `qa-ci-pipelines-github-actions-java` — runs these tests; the container run mode needs Docker available.
