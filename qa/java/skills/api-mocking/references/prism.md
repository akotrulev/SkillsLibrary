# API Mocking — Prism (Java 21 / TestNG)

The Java port of the canonical `qa-api-mocking-typescript`. Prism (`@stoplight/prism-cli`) is
**stack-agnostic** — there is **no native in-process Prism in any runtime** (unlike WireMock, which the
`references/wiremock.md` sibling runs in-process on the JVM). Every stack does the identical thing: it
stands up a `prism mock` server pointed at an OpenAPI spec and is a **thin HTTP client** to it. So this file
ports the canonical almost 1:1 (the same story as Mountebank `mountebank`); only the HTTP-client idioms change (here,
`java.net.http.HttpClient` + Jackson) and the container run mode (a `GenericContainer` for `stoplight/prism`).

Prism's defining trait is **spec-driven mocking**. Where WireMock makes you hand-write stub *mappings* and
Mountebank hand-write *imposters*, Prism **derives the mock from your OpenAPI contract**: point it at
`openapi.yaml` and it serves a fake of every operation automatically — example responses, schema-faked dynamic
data, and **request/response validation against the contract**. There are no stubs to author and **no request
journal to verify against**; you assert on the SUT's *outcome* and on Prism's *validation verdict*.

> **The two ideas that define this skill.** (1) **Spec-driven, not stub-driven** — the mock *is* the contract.
> (2) **Validation is a free contract gate** — Prism validates the incoming request against the spec and returns
> a **`422` + `application/problem+json`** when it violates, so a green test proves *"our typed client sends a
> spec-valid request."* The flip side: Prism is **stateless** — no per-test registration, **no recorded-request
> journal** (closer to MSW than to WireMock/Mountebank).

## Stack

- Java 21 + TestNG + AssertJ
- [Testcontainers](https://testcontainers.com/) (`GenericContainer`) running the
  [`stoplight/prism`](https://hub.docker.com/r/stoplight/prism) image — the default run mode (cross-link
  `qa-test-environments-java` / `qa-db-testing-testcontainers-java`)
- `java.net.http.HttpClient` (JDK built-in) for the thin client to the Prism base URL; **Jackson**
  (`ObjectMapper`) for request/response JSON
- [Awaitility](http://www.awaitility.org/) for condition-waits if any async (never `Thread.sleep`)
- A committed **OpenAPI spec fixture** (`src/test/resources/openapi.yaml`) — this *is* the mock definition; it is
  test data, not a secret
- A typed client (`qa-api-client-writer-java`) is the SUT — **constructor-injected** with the Prism base URL; the
  spec describes the same DTOs (`qa-api-dto-writer-java`)

```kotlin
// build.gradle.kts
testImplementation("org.testng:testng:7.10.2")
testImplementation("org.assertj:assertj-core:3.26.3")
testImplementation("org.testcontainers:testcontainers:1.20.4")
testImplementation("org.awaitility:awaitility:4.2.2")
testImplementation("com.fasterxml.jackson.core:jackson-databind:2.18.2")
```

## The Prism model — spec-driven mock, `mock` vs `proxy`, lifecycle

Prism has **no stub/imposter/handler concept** — the OpenAPI document is the whole configuration. Two run modes:

- **`prism mock <spec>`** — boots a fake server. Every operation in the spec is mocked: it returns the
  operation's response **examples** (or schema-faked data with `--dynamic`), and **validates** each incoming
  request against the spec.
- **`prism proxy <spec> <upstreamUrl>`** — forwards to the *real* upstream and **validates** the live traffic
  against the spec, surfacing contract drift. The validation counterpart to `mock`.

The lifecycle of every suite that uses Prism `mock`:

1. **Start** the server — a `GenericContainer("stoplight/prism")` running `mock -h 0.0.0.0 /tmp/openapi.yaml`,
   the spec file copied in, exposing port `4010`.
2. **Point the SUT at the Prism base URL** — `http://<host>:<mappedPort>`, injected into the typed client.
3. **Exercise** the SUT, optionally steering the response with a `Prefer` header.
4. **Assert** the SUT's outcome — and, for the contract gate, that a valid request gets `2xx` and a malformed one
   gets `422`.
5. **Stop** the container at teardown. There is **nothing to reset between tests** — the mock is stateless
   (spec-driven). A real simplification over WireMock/Mountebank.

> **`-h 0.0.0.0` is mandatory in a container.** Prism binds `localhost` by default, unreachable from outside the
> container. Always run `mock -h 0.0.0.0`. The default port is `4010` (override with `-p`).

### The spec fixture + container fixture (per-class)

Mirror the lifecycle trade-off from `qa-db-testing-testcontainers-java`: **one container per class**
(`@BeforeClass`/`@AfterClass`). Because Prism is stateless there is **no `@AfterMethod` reset** — the only
per-test state is the `Prefer` header the client sends on a given call.

```yaml
# src/test/resources/openapi.yaml — the mock IS this contract (committed test data, not a secret).
openapi: 3.0.3
info: { title: Widgets API, version: 1.0.0 }
paths:
  /api/widgets/{id}:
    get:
      operationId: getWidget
      parameters:
        - { name: id, in: path, required: true, schema: { type: integer } }
      responses:
        '200':
          description: A widget
          content:
            application/json:
              schema:
                type: object
                required: [id, name, priceMinor]
                properties:
                  id: { type: integer }
                  name: { type: string }
                  priceMinor: { type: integer }
              examples:
                sprocket: { value: { id: 42, name: Sprocket, priceMinor: 1999 } }
                cog:      { value: { id: 7,  name: Cog,      priceMinor: 499  } }
        '404': { description: Not found }
  /api/orders:
    post:
      operationId: submitOrder
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [sku, qty]
              properties:
                sku: { type: string }
                qty: { type: integer, minimum: 1 }
      responses:
        '201':
          description: Created
          content:
            application/json:
              schema: { type: object, properties: { orderId: { type: string } } }
              examples:
                created: { value: { orderId: ord-7 } }
```

```java
// src/test/java/support/PrismFixture.java
package support;

import org.testcontainers.containers.GenericContainer;
import org.testcontainers.utility.DockerImageName;
import org.testcontainers.utility.MountableFile;

public final class PrismFixture {
    private static final int PRISM_PORT = 4010;   // Prism's default

    public static GenericContainer<?> container;
    public static WidgetApiClient client;

    public static void start() {
        container = new GenericContainer<>(DockerImageName.parse("stoplight/prism:5.5.1"))
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource("openapi.yaml"), "/tmp/openapi.yaml")
                // -h 0.0.0.0 is REQUIRED so the server is reachable from outside the container.
                .withCommand("mock", "-h", "0.0.0.0", "/tmp/openapi.yaml")
                .withExposedPorts(PRISM_PORT);
        container.start();

        // The SUT's typed client is constructor-injected with the mapped Prism base URL — never static.
        String baseUrl = "http://" + container.getHost() + ":" + container.getMappedPort(PRISM_PORT);
        client = new WidgetApiClient(baseUrl);
    }

    public static void stop() {
        if (container != null) container.stop();
    }
}
```

## Core pattern — point the client at Prism, exercise, assert

The SUT is a typed client constructor-injected with the Prism base URL (cross-link `qa-api-client-writer-java`).
With no stubs to register, a test is just: drive the client, assert the outcome (one logical assertion). Prism
serves the spec's example for the operation.

```java
package api.mocking;

import org.testng.annotations.*;
import support.*;

import static org.assertj.core.api.Assertions.assertThat;
import static support.PrismFixture.*;

public class WidgetLookupTest {

    @BeforeClass public void startPrism() { PrismFixture.start(); }
    @AfterClass public void stopPrism() { PrismFixture.stop(); }
    // No @AfterMethod — the mock is stateless (spec-driven). Nothing to reset between tests.

    @Test
    public void Should_return_the_widget_When_Prism_serves_the_spec_example() throws Exception {
        // No stub setup — Prism mocks GET /api/widgets/{id} straight from the spec.
        Widget widget = client.getWidget(42);

        // One logical assertion: the SUT deserialized the spec example.
        assertThat(widget).isEqualTo(new Widget(42, "Sprocket", 1999));
    }
}
```

By default Prism returns the **first** example for the matched operation's first 2xx response. To choose *which*
example or status, use the `Prefer` header — next.

## Response negotiation — the `Prefer` header

Prism's analogue of WireMock scenarios / Mountebank's response cycle is **request-header-driven**, not server
state: the **`Prefer`** header on the *request* tells Prism which response to synthesize from the spec. The typed
client passes it through (cross-link `qa-api-client-writer-java` — a per-call header option).

| Prefer value | Effect | Use |
|--------------|--------|-----|
| `example=<name>` | Return the spec example with that name | Pick `cog` vs `sprocket` from the `examples` map |
| `code=<status>` | Return the response for that status code | Force the `404`/`500` error path |
| `dynamic=true` | Return schema-faked data instead of the static example | Decouple the test from one canned example |

Multiple preferences combine in one header, comma-separated: `Prefer: code=201, dynamic=true`.

```java
@Test
public void Should_exercise_the_error_path_When_Prefer_forces_404() throws Exception {
    // Force the spec's 404 response — the analogue of a WireMock scenario state, driven by the request header.
    assertThat(client.getWidgetResponse(999, "code=404").statusCode()).isEqualTo(404);
}

@Test
public void Should_return_the_named_example_When_Prefer_selects_it() throws Exception {
    Widget widget = client.getWidget(7, "example=cog");
    assertThat(widget).isEqualTo(new Widget(7, "Cog", 499));
}
```

> **`Prefer` is request-driven, not stateful.** Unlike a WireMock scenario (server-side state machine) or a
> Mountebank response cycle (advances per call), each Prism response depends only on *this* request's header — no
> order-dependence, nothing to reset. That is why tests stay trivially independent.

## Request & response validation — the contract gate

The headline. Prism validates the **incoming request** against the spec (required fields, types, `format`,
`minimum`, enums, required headers/query params…). When the request violates the contract and the spec has no
matching error response to serve, Prism returns **`422 Unprocessable Entity`** with an
**`application/problem+json`** body (RFC 7807) listing the violations. This turns "did our client send a
spec-valid request?" into a real assertion you get for free.

```java
public class OrderSubmissionTest {

    @BeforeClass public void startPrism() { PrismFixture.start(); }
    @AfterClass public void stopPrism() { PrismFixture.stop(); }

    @Test
    public void Should_accept_the_order_When_the_request_is_spec_valid() throws Exception {
        // A well-formed request → Prism validates it, then serves the 201 example.
        Order order = client.submitOrder(OrderRequestMother.standard());
        assertThat(order.orderId()).isEqualTo("ord-7"); // one logical assertion: the happy path is spec-valid
    }

    @Test
    public void Should_be_rejected_422_When_the_request_violates_the_spec() throws Exception {
        // qty:0 violates `minimum: 1` in the spec — Prism returns 422 + application/problem+json.
        var res = client.submitOrderRaw("{\"sku\":\"SPR-1\",\"qty\":0}");
        assertThat(res.statusCode()).isEqualTo(422); // the contract gate caught a spec-invalid request
        assertThat(res.headers().firstValue("content-type").orElse(""))
                .contains("application/problem+json");
    }
}
```

Two framings of the gate:
- **Positive** — a real client call that returns `2xx` *proves* the request conformed to the contract. Free on
  every happy-path test.
- **Negative** — deliberately send a malformed payload (`qty: 0`, a missing required field, a wrong type) and
  assert `422` + `problem+json`. Guards against the client drifting out of contract.

> Prism also validates **responses** in `proxy` mode (below). For `mock` mode the responses are spec-derived, so
> they are conformant by construction — the value in `mock` is the **request** gate.

## Static vs dynamic responses

| Mode | How | Trade-off |
|------|-----|-----------|
| **Static** (default) | Returns the spec's `example`/`examples` value | Deterministic — assert exact values; couples the test to the canned example |
| **Dynamic** | `--dynamic`/`-d` flag, or `Prefer: dynamic=true` per request | Schema-faked random data per call — decouples from one example, but you can only assert **shape/type** |

Reach for dynamic when you want to prove the SUT handles *any* schema-valid payload (assert types/required
fields), static when you want exact values. Default to static for deterministic assertions; opt into dynamic
per-call with the `Prefer` header rather than flipping the whole server.

```java
@Test
public void Should_handle_any_schema_valid_widget_When_Prism_is_dynamic() throws Exception {
    Widget widget = client.getWidget(42, "dynamic=true");
    // Dynamic data is random — assert SHAPE, never exact values.
    assertThat(widget.id()).isNotNull();
    assertThat(widget.name()).isNotBlank();
}
```

## `prism proxy` mode — validate live upstream traffic

`prism proxy <spec> <upstreamUrl>` sits in front of the **real** service: it forwards each request to the
upstream and **validates both the request and the response against the spec**, flagging drift (e.g. the
upstream's response shape no longer matches the contract). The validation counterpart to `mock` — you get the
real data *and* a contract verdict.

```java
// proxy mode: forward to the real upstream and validate the live traffic against the spec.
container = new GenericContainer<>(DockerImageName.parse("stoplight/prism:5.5.1"))
        .withCopyFileToContainer(MountableFile.forClasspathResource("openapi.yaml"), "/tmp/openapi.yaml")
        .withCommand("proxy", "-h", "0.0.0.0", "/tmp/openapi.yaml", "https://real-upstream.example.com")
        .withExposedPorts(4010);
```

Cross-link `qa-network-monitoring-java`: both sit on the wire to a real service, but they do opposite
jobs — the MITM proxy **records/faults** real traffic, while Prism `proxy` **validates it against the contract**.

## Run modes — container / CLI

| Mode | How | When |
|------|-----|------|
| **Testcontainers container** (default) | `GenericContainer("stoplight/prism")` running `mock -h 0.0.0.0 /tmp/openapi.yaml`, spec copied in, port `4010` | The default — CI-parity, identical run mode across all three stacks |
| **`@stoplight/prism-cli` CLI** | `npx @stoplight/prism-cli mock -p 4010 openapi.yaml` (needs Node) | Lighter local run; manual exploration; a shared mock across processes |

There is **no in-process mode** in any stack (contrast WireMock, which runs in-process on the JVM) — that is
exactly why this Java port is a thin HTTP client nearly identical to the TS canonical.

## Anti-patterns

- **Forgetting `-h 0.0.0.0` in the container.** Prism binds `localhost`, unreachable from the host; the test
  connection-refuses. *Fix:* always `mock -h 0.0.0.0`.
- **`Thread.sleep` to "wait for the mock to be ready".** Races startup. *Fix:* Testcontainers waits for the port;
  for an async SUT outcome use **Awaitility** on a condition.
- **Asserting exact values against `--dynamic`/`Prefer: dynamic=true` responses.** Dynamic data is random and the
  test flakes. *Fix:* dynamic → assert **shape/type**; static → assert exact values.
- **Expecting a request journal like WireMock/Mountebank.** Prism keeps **none**. *Fix:* assert on the SUT's
  **outcome** and on Prism's **validation verdict** (`2xx` vs `422`); use WireMock/Mountebank if you must verify
  exact bytes.
- **Hand-writing stubs alongside Prism.** Defeats the point — the spec *is* the mock. *Fix:* if you need
  hand-authored stubs, use WireMock/Mountebank.
- **Hard-coding the SUT's base URL instead of injecting the mapped Prism port.** The port is dynamic. *Fix:*
  construct the typed client with the mapped URL.
- **Editing the spec to make a test pass.** The spec is the contract under test, not a test knob. *Fix:* steer
  responses with the `Prefer` header; change the spec only when the contract genuinely changes.
- **Reaching for Prism to mock the app's own outbound HTTP.** That's in-runtime interception. *Fix:* MSW
  (`references/msw.md`, a Node sidecar port); Prism is a separate server.

## Examples

**End-to-end: the contract gate on both sides of an order submission.**

```java
package api.mocking;

import org.testng.annotations.*;
import support.*;

import static org.assertj.core.api.Assertions.assertThat;
import static support.PrismFixture.*;

public class OrderContractGateTest {

    @BeforeClass public void startPrism() { PrismFixture.start(); }
    @AfterClass public void stopPrism() { PrismFixture.stop(); }

    @Test
    public void Should_create_the_order_When_the_request_conforms_to_the_contract() throws Exception {
        // Spec-valid request → Prism validates, then serves the 201 example. The 2xx itself proves conformance.
        Order order = client.submitOrder(OrderRequestMother.standard());
        assertThat(order.orderId()).isEqualTo("ord-7"); // one logical assertion: outcome
    }

    @Test
    public void Should_reject_422_When_a_required_field_is_missing() throws Exception {
        // Omit the required `sku` — Prism's request validation rejects it before any business logic.
        var res = client.submitOrderRaw("{\"qty\":3}");
        assertThat(res.statusCode()).isEqualTo(422); // the contract gate
    }
}
```

Lifecycle for this suite:
1. `@BeforeClass` starts the `stoplight/prism` container running `mock` against the classpath `openapi.yaml`; the
   typed client is injected with the mapped Prism base URL.
2. The happy-path test drives a spec-valid request — the `2xx` *is* the proof of conformance (no stub setup).
3. The negative test sends a contract-violating payload and asserts `422` — the request gate.
4. `@AfterClass` stops the container. No `@AfterMethod` — the mock is stateless.

**Test-data builder for request payloads (4+ fields → builder).**

```java
public final class OrderRequestMother {
    public static OrderRequest standard() {
        return new OrderRequestBuilder()
                .sku("SPR-1").qty(3).currency("EUR").idempotencyKey("idem-123").build();
    }
}
```

## Rules (hard constraints)

- Prism is an **OpenAPI-spec-driven standalone server** — the committed `openapi.yaml` *is* the mock; inject the
  mapped Prism base URL into the typed client (`qa-api-client-writer-java`), never hard-code the dynamic port.
  **No hand-written stubs** — if you need them, use WireMock/Mountebank.
- Always run `mock -h 0.0.0.0` in a container (Prism binds `localhost` otherwise). Default port `4010`.
- Steer responses with the **`Prefer` header** (`example=`/`code=`/`dynamic=true`), not server state. The mock is
  **stateless**: one container per class (`@BeforeClass`), **no `@AfterMethod` reset**, never a container per test.
- Use the **validation contract gate**: assert a spec-valid call gets `2xx` and a deliberately-malformed one gets
  **`422` + `application/problem+json`**.
- **Dynamic → assert shape/type only; static → assert exact values.** Default to static for determinism.
- Prism keeps **no request journal** — assert on the SUT's **outcome** and Prism's **validation verdict**, not a
  recorded-request log (use WireMock/Mountebank if you must verify exact bytes).
- **No `Thread.sleep`.** Testcontainers waits for the port; **Awaitility** waits on a condition.
- Builders/ObjectMother for request payloads with 4+ fields. Test names `Should_X_When_Y`; constructor injection;
  structured logging; the OpenAPI spec is committed test data, not a secret.
- Prefer **WireMock/Mountebank** for hand-authored or multi-protocol stubs, **MSW** (sidecar) for the app's own
  in-runtime HTTP, the MITM proxy for real-service traffic, and **Pact** for consumer-driven contracts — use
  Prism when you have an OpenAPI spec and want it mocked + validated.

## Cross-references

- `qa-api-mocking-typescript` — the **canonical** stack, Node/Vitest (`fetch` client + `stoplight/prism`
  container). Structure ported from there; this Java port makes the same calls.
- `qa-api-mocking-dotnet` — same skill, .NET/NUnit (`HttpClient`, async-all-the-way). Same choreography.
- `references/mountebank.md` — the **closest precedent**: same stack-agnostic
  thin-HTTP-client-to-a-standalone-Node-server + Testcontainers run mode. The contrast: Mountebank is
  **imposter-driven** and **keeps a request journal**; Prism is **spec-driven** and keeps **none**.
- `references/wiremock.md` — hand-authored stubs, richest HTTP, in-process JVM; the stub-driven
  counterpoint to Prism's spec-driven model.
- `references/msw.md` — in-runtime interception (a Node sidecar in Java); like Prism it keeps **no
  journal**, unlike WireMock/Mountebank.
- `qa-contract-testing-pact-java` — the **consumer-driven** contract (generated *from tests*) vs Prism's
  **spec-first** mock/validate (*from an existing OpenAPI doc*); complementary.
- `qa-network-monitoring-java` — MITM proxy that **records/faults** real traffic; Prism `proxy`
  **validates** real traffic against the spec. Opposite jobs on the same wire.
- `qa-api-client-writer-java` + `qa-api-dto-writer-java` + `qa-api-test-author-generator-java` — the typed client
  / DTOs / API tests; the spec describes those same DTOs, and the client is injected with the Prism base URL.
- `qa-test-environments-java` + `qa-db-testing-testcontainers-java` — the `stoplight/prism` container run mode +
  the per-class lifecycle.
- `qa-ci-pipelines-java` — runs these tests; the container run mode needs Docker available.
