---
name: qa-api-mocking-prism-dotnet
description: >-
  Service-virtualization / API-mocking with Stoplight **Prism** in .NET 8 (NUnit): run Prism as an
  **OpenAPI-spec-driven** standalone mock server (a Testcontainers-for-.NET `stoplight/prism` container, or the
  `@stoplight/prism-cli` CLI) and drive it with `HttpClient` (async-all-the-way) — `prism mock <openapi.yaml>`
  boots a fake of **every** operation in the spec with **no hand-written stubs**, point the system-under-test's
  constructor-injected typed client at the Prism base URL (default port `4010`), exercise the flow, and assert
  the response. Use when you already have an OpenAPI/Swagger contract and want the mock **derived from it** —
  plus Prism's request/response **validation** (a spec-violating request gets a `422` + `application/problem+json`,
  the contract gate "our client sends a spec-valid request") and **`prism proxy <spec> <upstream>`** which
  validates *live* upstream traffic against the contract. Covers `Prefer`-header **response negotiation**
  (`example=<name>`, `code=<status>`, `dynamic=true`), static-vs-`--dynamic` responses, the `mock` vs `proxy`
  modes, and the **stateless / no-request-journal** posture (assert on outcome + validation verdict). Triggers:
  "mock our API from the OpenAPI spec with Prism in .NET", "spin up a Prism mock for this NUnit test", "Prism
  return the 404 example", "validate the request against the spec", "prism proxy the real service". Do NOT use
  for: hand-authored stubs of a standalone HTTP server (use WireMock, qa-api-mocking-wiremock-dotnet; or
  Mountebank for multi-protocol, qa-api-mocking-mountebank-dotnet), mocking the app's **own** outbound HTTP
  in-runtime (use MSW sidecar, qa-api-mocking-msw-dotnet), an out-of-browser MITM proxy on a real client's traffic
  (use qa-network-monitoring-proxy-dotnet), consumer-driven contracts generated *from tests* (use
  qa-contract-testing-pact-dotnet), the TypeScript stack (the canonical — use qa-api-mocking-prism-typescript), or
  the Java stack (use qa-api-mocking-prism-java).
---

# API Mocking — Prism (.NET 8 / NUnit)

The .NET port of the canonical `qa-api-mocking-prism-typescript`. Prism (`@stoplight/prism-cli`) is
**stack-agnostic** — there is **no native in-process Prism in any runtime** (unlike `WireMock.Net`, which the
`qa-api-mocking-wiremock-dotnet` sibling runs in-process). Every stack does the identical thing: it stands up a
`prism mock` server pointed at an OpenAPI spec and is a **thin HTTP client** to it. So this file ports the
canonical almost 1:1 (the same story as Mountebank #24); only the HTTP-client idioms change (here, `HttpClient` +
`System.Text.Json`, async-all-the-way) and the container run mode (Testcontainers for .NET, `stoplight/prism`).

Prism's defining trait is **spec-driven mocking**. Where `WireMock.Net` makes you hand-write stub *mappings* and
Mountebank hand-write *imposters*, Prism **derives the mock from your OpenAPI contract**: point it at
`openapi.yaml` and it serves a fake of every operation automatically — example responses, schema-faked dynamic
data, and **request/response validation against the contract**. There are no stubs to author and **no request
journal to verify against**; you assert on the SUT's *outcome* and on Prism's *validation verdict*.

> **The two ideas that define this skill.** (1) **Spec-driven, not stub-driven** — the mock *is* the contract.
> (2) **Validation is a free contract gate** — Prism validates the incoming request against the spec and returns
> a **`422` + `application/problem+json`** when it violates, so a green test proves *"our typed client sends a
> spec-valid request."* The flip side: Prism is **stateless** — no per-test registration, **no recorded-request
> journal** (closer to MSW than to WireMock/Mountebank).

## Decision matrix — Prism vs the rest of the `api-mocking` family (and Pact)

| Need | Use | Why |
|------|-----|-----|
| A mock **derived from an OpenAPI spec** automatically, + request/response **validation** against the contract | **Prism (this skill)** | Spec-driven; no stubs to write; the `422`/`problem+json` contract gate; `proxy` validates live traffic |
| **Hand-authored stubs**, the **richest HTTP** server + **in-process .NET** run mode; templating, scenarios | **WireMock** (`qa-api-mocking-wiremock-dotnet`, #22) | Deepest HTTP control; runs in-process via `WireMock.Net` (Prism never does) |
| A **multi-protocol** (`http`/`tcp`/`smtp`) standalone server driven over a REST API | **Mountebank** (`qa-api-mocking-mountebank-dotnet`, #24) | Imposters speak more than HTTP; same stack-agnostic thin-client port story as Prism |
| Mock the app's **own** outbound HTTP **in-runtime**, no separate server | **MSW** (`qa-api-mocking-msw-dotnet` — a Node sidecar port, #23) | Interception in the app's process; TS-native, .NET is a sidecar |
| Observe / rewrite a **real client's** live traffic out-of-browser (MITM) | `qa-network-monitoring-proxy-dotnet` (#10) | Proxy on the wire to the *real* service |
| A **consumer-driven** contract **generated from the test**, verified by the provider | `qa-contract-testing-pact-dotnet` | Pact *produces* the contract from interactions; Prism *consumes* an existing OpenAPI spec — complementary |

**Rule of thumb (.NET):** *Already have an OpenAPI spec and want the mock + a "did we call it correctly per the
contract" check for free?* → Prism. *Need hand-crafted stubs, in-process via `WireMock.Net`, or scenarios?* →
WireMock. *Multi-protocol standalone fake?* → Mountebank. *Real-service traffic?* → the network-monitoring
family. *Want a contract authored *by* the consumer test?* → Pact.

> **Prism vs Pact — both "contract", different direction.** Pact (`qa-contract-testing-pact-dotnet`) is
> **consumer-driven**: the consumer test *records* expected interactions into a pact file the provider then
> verifies. Prism is **spec-first**: you already have an OpenAPI document and Prism *mocks and validates against
> it*. They compose — Prism can mock the OpenAPI spec a Pact provider also satisfies.

## Stack

- .NET 8 + NUnit + `HttpClient` (async-all-the-way) + `System.Text.Json`
- [Testcontainers for .NET](https://dotnet.testcontainers.org/) running the
  [`stoplight/prism`](https://hub.docker.com/r/stoplight/prism) image — the default run mode (cross-link
  `qa-test-environments-dotnet` / `qa-db-testing-testcontainers-dotnet`)
- A committed **OpenAPI spec fixture** (`Tests/Fixtures/openapi.yaml`, copied to the output dir) — this *is* the
  mock definition; it is test data, not a secret
- A typed client (`qa-api-client-writer-dotnet`) is the SUT — **constructor-injected** with the Prism base URL;
  the spec describes the same DTOs (`qa-api-dto-writer-dotnet`)

```bash
dotnet add package Testcontainers
dotnet add package NUnit
```

## The Prism model — spec-driven mock, `mock` vs `proxy`, lifecycle

Prism has **no stub/imposter/handler concept** — the OpenAPI document is the whole configuration. Two run modes:

- **`prism mock <spec>`** — boots a fake server. Every operation in the spec is mocked: it returns the
  operation's response **examples** (or schema-faked data with `--dynamic`), and **validates** each incoming
  request against the spec.
- **`prism proxy <spec> <upstreamUrl>`** — forwards to the *real* upstream and **validates** the live traffic
  against the spec, surfacing contract drift. The validation counterpart to `mock`.

The lifecycle of every suite that uses Prism `mock`:

1. **Start** the server — a Testcontainers container running `mock -h 0.0.0.0 /tmp/openapi.yaml`, the spec file
   copied in, exposing port `4010`.
2. **Point the SUT at the Prism base URL** — `http://<host>:<mappedPort>`, injected into the typed client.
3. **Exercise** the SUT, optionally steering the response with a `Prefer` header.
4. **Assert** the SUT's outcome — and, for the contract gate, that a valid request gets `2xx` and a malformed one
   gets `422`.
5. **Stop** the container at teardown. There is **nothing to reset between tests** — the mock is stateless
   (spec-driven). A real simplification over WireMock/Mountebank.

> **`-h 0.0.0.0` is mandatory in a container.** Prism binds `localhost` by default, unreachable from outside the
> container. Always run `mock -h 0.0.0.0`. The default port is `4010` (override with `-p`).

### The spec fixture + container fixture (per-fixture)

Mirror the lifecycle trade-off from `qa-db-testing-testcontainers-dotnet`: **one container per fixture**
(`[OneTimeSetUp]`/`[OneTimeTearDown]`). Because Prism is stateless there is **no `[TearDown]` reset** — the only
per-test state is the `Prefer` header the client sends on a given call.

```yaml
# Tests/Fixtures/openapi.yaml — the mock IS this contract (committed test data; CopyToOutputDirectory=Always).
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

```csharp
// Tests/Support/PrismFixture.cs
using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Containers;

namespace Tests.Support;

public sealed class PrismFixture
{
    private const int PrismPort = 4010;   // Prism's default

    public IContainer Container { get; private set; } = null!;
    public WidgetApiClient Client { get; private set; } = null!;

    public async Task StartAsync()
    {
        var specPath = Path.Combine(AppContext.BaseDirectory, "Fixtures", "openapi.yaml");
        Container = new ContainerBuilder()
            .WithImage("stoplight/prism:5.5.1")
            .WithResourceMapping(specPath, "/tmp/openapi.yaml")
            // -h 0.0.0.0 is REQUIRED so the server is reachable from outside the container.
            .WithCommand("mock", "-h", "0.0.0.0", "/tmp/openapi.yaml")
            .WithPortBinding(PrismPort, true)
            .WithWaitStrategy(Wait.ForUnixContainer().UntilPortIsAvailable(PrismPort))
            .Build();
        await Container.StartAsync();

        // The SUT's typed client is constructor-injected with the mapped Prism base URL — never static.
        var baseUrl = $"http://{Container.Hostname}:{Container.GetMappedPublicPort(PrismPort)}";
        Client = new WidgetApiClient(baseUrl);
    }

    public async Task StopAsync()
    {
        if (Container is not null) await Container.DisposeAsync();
    }
}
```

## Core pattern — point the client at Prism, exercise, assert

The SUT is a typed client constructor-injected with the Prism base URL (cross-link `qa-api-client-writer-dotnet`).
With no stubs to register, a test is just: drive the client, assert the outcome (one logical assertion). Prism
serves the spec's example for the operation. Everything is `async`/`await` — never `.Result`/`.Wait()`.

```csharp
using NUnit.Framework;
using Tests.Support;

[TestFixture]
public class WidgetLookupTests
{
    private readonly PrismFixture _fx = new();

    [OneTimeSetUp] public Task StartPrism() => _fx.StartAsync();
    [OneTimeTearDown] public Task StopPrism() => _fx.StopAsync();
    // No [TearDown] — the mock is stateless (spec-driven). Nothing to reset between tests.

    [Test]
    public async Task Should_return_the_widget_When_Prism_serves_the_spec_example()
    {
        // No stub setup — Prism mocks GET /api/widgets/{id} straight from the spec.
        var widget = await _fx.Client.GetWidgetAsync(42);

        // One logical assertion: the SUT deserialized the spec example.
        Assert.That(widget, Is.EqualTo(new Widget(42, "Sprocket", 1999)));
    }
}
```

By default Prism returns the **first** example for the matched operation's first 2xx response. To choose *which*
example or status, use the `Prefer` header — next.

## Response negotiation — the `Prefer` header

Prism's analogue of WireMock scenarios / Mountebank's response cycle is **request-header-driven**, not server
state: the **`Prefer`** header on the *request* tells Prism which response to synthesize from the spec. The typed
client passes it through (cross-link `qa-api-client-writer-dotnet` — a per-call header option).

| Prefer value | Effect | Use |
|--------------|--------|-----|
| `example=<name>` | Return the spec example with that name | Pick `cog` vs `sprocket` from the `examples` map |
| `code=<status>` | Return the response for that status code | Force the `404`/`500` error path |
| `dynamic=true` | Return schema-faked data instead of the static example | Decouple the test from one canned example |

Multiple preferences combine in one header, comma-separated: `Prefer: code=201, dynamic=true`.

```csharp
[Test]
public async Task Should_exercise_the_error_path_When_Prefer_forces_404()
{
    // Force the spec's 404 response — the analogue of a WireMock scenario state, driven by the request header.
    var res = await _fx.Client.GetWidgetResponseAsync(999, prefer: "code=404");
    Assert.That((int)res.StatusCode, Is.EqualTo(404));
}

[Test]
public async Task Should_return_the_named_example_When_Prefer_selects_it()
{
    var widget = await _fx.Client.GetWidgetAsync(7, prefer: "example=cog");
    Assert.That(widget, Is.EqualTo(new Widget(7, "Cog", 499)));
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

```csharp
[TestFixture]
public class OrderSubmissionTests
{
    private readonly PrismFixture _fx = new();

    [OneTimeSetUp] public Task StartPrism() => _fx.StartAsync();
    [OneTimeTearDown] public Task StopPrism() => _fx.StopAsync();

    [Test]
    public async Task Should_accept_the_order_When_the_request_is_spec_valid()
    {
        // A well-formed request → Prism validates it, then serves the 201 example.
        var order = await _fx.Client.SubmitOrderAsync(OrderRequestMother.Standard());
        Assert.That(order.OrderId, Is.EqualTo("ord-7")); // one logical assertion: the happy path is spec-valid
    }

    [Test]
    public async Task Should_be_rejected_422_When_the_request_violates_the_spec()
    {
        // qty:0 violates `minimum: 1` in the spec — Prism returns 422 + application/problem+json.
        var res = await _fx.Client.SubmitOrderRawAsync("{\"sku\":\"SPR-1\",\"qty\":0}");
        Assert.That((int)res.StatusCode, Is.EqualTo(422)); // the contract gate caught a spec-invalid request
        Assert.That(res.Content.Headers.ContentType?.MediaType, Is.EqualTo("application/problem+json"));
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

```csharp
[Test]
public async Task Should_handle_any_schema_valid_widget_When_Prism_is_dynamic()
{
    var widget = await _fx.Client.GetWidgetAsync(42, prefer: "dynamic=true");
    // Dynamic data is random — assert SHAPE, never exact values.
    Assert.That(widget.Name, Is.Not.Empty);
}
```

## `prism proxy` mode — validate live upstream traffic

`prism proxy <spec> <upstreamUrl>` sits in front of the **real** service: it forwards each request to the
upstream and **validates both the request and the response against the spec**, flagging drift (e.g. the
upstream's response shape no longer matches the contract). The validation counterpart to `mock` — you get the
real data *and* a contract verdict.

```csharp
// proxy mode: forward to the real upstream and validate the live traffic against the spec.
Container = new ContainerBuilder()
    .WithImage("stoplight/prism:5.5.1")
    .WithResourceMapping(specPath, "/tmp/openapi.yaml")
    .WithCommand("proxy", "-h", "0.0.0.0", "/tmp/openapi.yaml", "https://real-upstream.example.com")
    .WithPortBinding(4010, true)
    .Build();
```

Cross-link `qa-network-monitoring-proxy-dotnet` (#10): both sit on the wire to a real service, but they do
opposite jobs — the MITM proxy **records/faults** real traffic, while Prism `proxy` **validates it against the
contract**.

## Run modes — container / CLI

| Mode | How | When |
|------|-----|------|
| **Testcontainers container** (default) | a `ContainerBuilder` for `stoplight/prism` running `mock -h 0.0.0.0 /tmp/openapi.yaml`, spec mapped in, port `4010` | The default — CI-parity, identical run mode across all three stacks |
| **`@stoplight/prism-cli` CLI** | `npx @stoplight/prism-cli mock -p 4010 openapi.yaml` (needs Node) | Lighter local run; manual exploration; a shared mock across processes |

There is **no in-process mode** in any stack (contrast `WireMock.Net`, which runs in-process) — that is exactly
why this .NET port is a thin HTTP client nearly identical to the TS canonical.

## Anti-patterns

- **Forgetting `-h 0.0.0.0` in the container.** Prism binds `localhost`, unreachable from the host; the test
  connection-refuses. *Fix:* always `mock -h 0.0.0.0`.
- **`Task.Delay`-as-wait (or `Thread.Sleep`) to "wait for the mock to be ready".** Races startup. *Fix:*
  Testcontainers waits for the port; for an async SUT outcome use a bounded **condition-poll**.
- **`.Result` / `.Wait()` on the SUT calls.** Blocks and risks deadlock. *Fix:* `await` throughout — async all
  the way.
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
  (`qa-api-mocking-msw-dotnet`, a Node sidecar port); Prism is a separate server.

## Examples

**End-to-end: the contract gate on both sides of an order submission.**

```csharp
using NUnit.Framework;
using Tests.Support;

[TestFixture]
public class OrderContractGateTests
{
    private readonly PrismFixture _fx = new();

    [OneTimeSetUp] public Task StartPrism() => _fx.StartAsync();
    [OneTimeTearDown] public Task StopPrism() => _fx.StopAsync();

    [Test]
    public async Task Should_create_the_order_When_the_request_conforms_to_the_contract()
    {
        // Spec-valid request → Prism validates, then serves the 201 example. The 2xx itself proves conformance.
        var order = await _fx.Client.SubmitOrderAsync(OrderRequestMother.Standard());
        Assert.That(order.OrderId, Is.EqualTo("ord-7")); // one logical assertion: outcome
    }

    [Test]
    public async Task Should_reject_422_When_a_required_field_is_missing()
    {
        // Omit the required `sku` — Prism's request validation rejects it before any business logic.
        var res = await _fx.Client.SubmitOrderRawAsync("{\"qty\":3}");
        Assert.That((int)res.StatusCode, Is.EqualTo(422)); // the contract gate
    }
}
```

Lifecycle for this suite:
1. `[OneTimeSetUp]` starts the `stoplight/prism` container running `mock` against the copied `openapi.yaml`; the
   typed client is injected with the mapped Prism base URL.
2. The happy-path test drives a spec-valid request — the `2xx` *is* the proof of conformance (no stub setup).
3. The negative test sends a contract-violating payload and asserts `422` — the request gate.
4. `[OneTimeTearDown]` stops the container. No `[TearDown]` — the mock is stateless.

**Test-data builder for request payloads (4+ fields → builder).**

```csharp
public static class OrderRequestMother
{
    public static OrderRequest Standard() =>
        new OrderRequestBuilder()
            .WithSku("SPR-1").WithQty(3).WithCurrency("EUR").WithIdempotencyKey("idem-123").Build();
}
```

## Rules (hard constraints)

- Prism is an **OpenAPI-spec-driven standalone server** — the committed `openapi.yaml` *is* the mock; inject the
  mapped Prism base URL into the typed client (`qa-api-client-writer-dotnet`), never hard-code the dynamic port.
  **No hand-written stubs** — if you need them, use WireMock/Mountebank.
- Always run `mock -h 0.0.0.0` in a container (Prism binds `localhost` otherwise). Default port `4010`.
- Steer responses with the **`Prefer` header** (`example=`/`code=`/`dynamic=true`), not server state. The mock is
  **stateless**: one container per fixture (`[OneTimeSetUp]`), **no `[TearDown]` reset**, never a container per
  test.
- Use the **validation contract gate**: assert a spec-valid call gets `2xx` and a deliberately-malformed one gets
  **`422` + `application/problem+json`**.
- **Async all the way** — `await` every SUT call; never `.Result`/`.Wait()`. **No `Task.Delay`/`Thread.Sleep` as
  a wait** — Testcontainers waits for the port; a bounded **condition-poll** waits on an async outcome.
- **Dynamic → assert shape/type only; static → assert exact values.** Default to static for determinism.
- Prism keeps **no request journal** — assert on the SUT's **outcome** and Prism's **validation verdict**, not a
  recorded-request log (use WireMock/Mountebank if you must verify exact bytes).
- Builders/ObjectMother for request payloads with 4+ fields. Test names `Should_X_When_Y`; constructor injection;
  structured logging; the OpenAPI spec is committed test data, not a secret.
- Prefer **WireMock/Mountebank** for hand-authored or multi-protocol stubs, **MSW** (sidecar) for the app's own
  in-runtime HTTP, the MITM proxy for real-service traffic, and **Pact** for consumer-driven contracts — use
  Prism when you have an OpenAPI spec and want it mocked + validated.

## Cross-references

- `qa-api-mocking-prism-typescript` — the **canonical** stack, Node/Vitest (`fetch` client + `stoplight/prism`
  container). Structure ported from there; this .NET port makes the same calls.
- `qa-api-mocking-prism-java` — same skill, Java/TestNG (`java.net.http.HttpClient` + Jackson). Same choreography.
- `qa-api-mocking-mountebank-dotnet` (#24) — the **closest precedent**: same stack-agnostic
  thin-HTTP-client-to-a-standalone-Node-server + Testcontainers run mode. The contrast: Mountebank is
  **imposter-driven** and **keeps a request journal**; Prism is **spec-driven** and keeps **none**.
- `qa-api-mocking-wiremock-dotnet` (#22) — hand-authored stubs (`WireMock.Net`), richest HTTP, in-process; the
  stub-driven counterpoint to Prism's spec-driven model.
- `qa-api-mocking-msw-dotnet` (#23) — in-runtime interception (a Node sidecar in .NET); like Prism it keeps **no
  journal**, unlike WireMock/Mountebank.
- `qa-contract-testing-pact-dotnet` — the **consumer-driven** contract (generated *from tests*) vs Prism's
  **spec-first** mock/validate (*from an existing OpenAPI doc*); complementary.
- `qa-network-monitoring-proxy-dotnet` (#10) — MITM proxy that **records/faults** real traffic; Prism `proxy`
  **validates** real traffic against the spec. Opposite jobs on the same wire.
- `qa-api-client-writer-dotnet` + `qa-api-dto-writer-dotnet` + `qa-api-test-author-generator-dotnet` — the typed
  client / DTOs / API tests; the spec describes those same DTOs, and the client is injected with the Prism base URL.
- `qa-test-environments-dotnet` + `qa-db-testing-testcontainers-dotnet` — the `stoplight/prism` container run mode
  + the per-fixture lifecycle.
- `qa-ci-pipelines-github-actions-dotnet` — runs these tests; the container run mode needs Docker available.
