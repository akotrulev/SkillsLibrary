# API Mocking — Prism (Node 20 / TypeScript / Vitest)

**This is the canonical stack for Prism** — Prism (`@stoplight/prism-cli`) is itself a Node tool, so TypeScript
is its closest home and the raw-`fetch` client is cleanest here. Like Mountebank and unlike WireMock (`wiremock`,
JVM-native) and MSW (`msw`, TS in-runtime), Prism is **stack-agnostic**: there is **no native in-process Prism in
any runtime**. Every stack — TS, Java, .NET — does the identical thing: it stands up a `prism mock` server
pointed at an OpenAPI spec and is a **thin HTTP client** to it. So the Java/.NET siblings port almost 1:1 from
this file (the same port story as `mountebank`); only the HTTP-client and container idioms change.

Prism's defining trait is **spec-driven mocking**. Where WireMock makes you hand-write stub *mappings*, MSW
hand-write *handlers*, and Mountebank hand-write *imposters*, Prism **derives the mock from your OpenAPI
contract**: point it at `openapi.yaml` and it serves a fake of every operation automatically — example
responses, schema-faked dynamic data, and **request/response validation against the contract**. There are no
stubs to author and **no request journal to verify against**; you assert on the SUT's *outcome* and on Prism's
*validation verdict*.

> **The two ideas that define this skill.** (1) **Spec-driven, not stub-driven** — the mock *is* the contract.
> (2) **Validation is a free contract gate** — Prism validates the incoming request against the spec and returns
> a **`422` + `application/problem+json`** when it violates, so a green test proves *"our typed client sends a
> spec-valid request."* That is what no other member of the family gives you. The flip side: Prism is
> **stateless** — no per-test stub registration, **no recorded-request journal** (closer to MSW than to
> WireMock/Mountebank).

## Stack

- Node 20 + TypeScript (strict) + Vitest
- [`testcontainers`](https://www.npmjs.com/package/testcontainers) (`GenericContainer`) running the
  [`stoplight/prism`](https://hub.docker.com/r/stoplight/prism) image — the default run mode (cross-link
  `qa-test-environments-typescript` / `qa-db-testing-testcontainers-typescript`). The `@stoplight/prism-cli`
  `npx` CLI is the lighter alternative.
- A committed **OpenAPI spec fixture** (`tests/fixtures/openapi.yaml`) — this *is* the mock definition; it is
  test data, not a secret.
- A typed `fetch` client (`qa-api-client-writer-typescript`) is the SUT — **constructor-injected** with the
  Prism base URL. The spec describes the same DTOs the client deserializes (`qa-api-dto-writer-typescript`).

```bash
npm install --save-dev testcontainers
```

## The Prism model — spec-driven mock, `mock` vs `proxy`, lifecycle

Prism has **no stub/imposter/handler concept** — the OpenAPI document is the whole configuration. Two run modes:

- **`prism mock <spec>`** — boots a fake server. Every operation in the spec is mocked: it returns the
  operation's response **examples** (or schema-faked data with `--dynamic`), and **validates** each incoming
  request against the spec.
- **`prism proxy <spec> <upstreamUrl>`** — forwards to the *real* upstream and **validates** the live traffic
  (request and response) against the spec, surfacing contract drift. The validation counterpart to `mock`.

The lifecycle of every suite that uses Prism `mock`:

1. **Start** the server — a `GenericContainer('stoplight/prism')` running `mock -h 0.0.0.0 /tmp/openapi.yaml`,
   with the spec file copied in, exposing port `4010`.
2. **Point the SUT at the Prism base URL** — `http://<host>:<mappedPort>`, injected into the typed client.
3. **Exercise** the SUT so it calls the (mocked) dependency, optionally steering the response with a `Prefer`
   header.
4. **Assert** the SUT's outcome — and, for the contract gate, assert a valid request gets `2xx` and a
   deliberately-malformed one gets `422`.
5. **Stop** the container at teardown. There is **nothing to reset between tests** — the mock is stateless
   (spec-driven, no per-test registration). That is a real simplification over WireMock/Mountebank.

> **`-h 0.0.0.0` is mandatory in a container.** Prism binds `localhost` (`127.0.0.1`) by default, which is
> unreachable from outside the container. Always run `mock -h 0.0.0.0`. The default port is `4010` (override
> with `-p`).

### The spec fixture + container fixture (per-suite)

Mirror the per-suite lifecycle trade-off from `qa-db-testing-testcontainers-typescript`: **one container per
suite** (`beforeAll`/`afterAll`). Because Prism is stateless there is **no `afterEach` reset** — the only
per-test state is the `Prefer` header the client sends on a given call.

```yaml
# tests/fixtures/openapi.yaml — the mock IS this contract (committed test data, not a secret).
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

```typescript
// tests/support/prism.fixture.ts
import { GenericContainer, type StartedTestContainer } from 'testcontainers';
import { resolve } from 'node:path';
import { WidgetApiClient } from '../../src/clients/widget.client';

export let container: StartedTestContainer;
export let client: WidgetApiClient;

const PRISM_PORT = 4010; // Prism's default

export async function startPrism(): Promise<void> {
  container = await new GenericContainer('stoplight/prism:5.5.1')
    .withCopyFilesToContainer([
      { source: resolve(__dirname, '../fixtures/openapi.yaml'), target: '/tmp/openapi.yaml' },
    ])
    // -h 0.0.0.0 is REQUIRED so the server is reachable from outside the container.
    .withCommand(['mock', '-h', '0.0.0.0', '/tmp/openapi.yaml'])
    .withExposedPorts(PRISM_PORT)
    .start();

  // The SUT's typed client is constructor-injected with the mapped Prism base URL — never a static URL.
  const baseUrl = `http://${container.getHost()}:${container.getMappedPort(PRISM_PORT)}`;
  client = new WidgetApiClient(baseUrl);
}

export async function stopPrism(): Promise<void> {
  await container?.stop();
}
```

```typescript
// tests/support/prism.hooks.ts
import { beforeAll, afterAll } from 'vitest';
import { startPrism, stopPrism } from './prism.fixture';

beforeAll(startPrism, 60_000); // pulling/starting the image can take a moment
afterAll(stopPrism);
// No afterEach — the mock is stateless (spec-driven). Nothing to reset between tests.
```

## Core pattern — point the client at Prism, exercise, assert

The SUT is a typed `fetch` client constructor-injected with the Prism base URL (cross-link
`qa-api-client-writer-typescript`). With no stubs to register, a test is just: drive the client, assert the
outcome (one logical assertion). Prism serves the spec's example for the operation.

```typescript
import { describe, it, expect } from 'vitest';
import './support/prism.hooks';
import { client } from './support/prism.fixture';

describe('widget lookup against Prism', () => {
  it('Should_return_the_widget_When_Prism_serves_the_spec_example', async () => {
    // No stub setup — Prism mocks GET /api/widgets/{id} straight from the spec.
    const widget = await client.getWidget(42);

    // One logical assertion: the SUT deserialized the spec example.
    expect(widget).toEqual({ id: 42, name: 'Sprocket', priceMinor: 1999 });
  });
});
```

By default Prism returns the **first** example (or the schema's `example`) for the matched operation's first
2xx response. To choose *which* example or status, use the `Prefer` header — next.

## Response negotiation — the `Prefer` header

Prism's analogue of WireMock scenarios / Mountebank's response cycle is **request-header-driven**, not server
state: the **`Prefer`** header on the *request* tells Prism which response to synthesize from the spec. The
typed client passes it through (cross-link `qa-api-client-writer-typescript` — a per-call header option).

| Prefer value | Effect | Use |
|--------------|--------|-----|
| `example=<name>` | Return the spec example with that name | Pick `cog` vs `sprocket` from the `examples` map |
| `code=<status>` | Return the response for that status code | Force the `404`/`500` error path |
| `dynamic=true` | Return schema-faked data instead of the static example | Decouple the test from one canned example |

Multiple preferences combine in one header, comma-separated: `Prefer: code=201, dynamic=true`.

```typescript
it('Should_exercise_the_error_path_When_Prefer_forces_404', async () => {
  // Force the spec's 404 response — the analogue of a WireMock scenario state, driven by the request header.
  await expect(client.getWidget(999, { prefer: 'code=404' }))
    .rejects.toMatchObject({ status: 404 });
});

it('Should_return_the_named_example_When_Prefer_selects_it', async () => {
  const widget = await client.getWidget(7, { prefer: 'example=cog' });
  expect(widget).toEqual({ id: 7, name: 'Cog', priceMinor: 499 });
});
```

> **`Prefer` is request-driven, not stateful.** Unlike a WireMock scenario (server-side state machine) or a
> Mountebank response cycle (advances per call), each Prism response depends only on *this* request's header —
> there is no order-dependence and nothing to reset. That is why tests stay trivially independent.

## Request & response validation — the contract gate

The headline. Prism validates the **incoming request** against the spec (required fields, types, `format`,
`minimum`, enums, required headers/query params…). When the request violates the contract and the spec has no
matching error response to serve, Prism returns **`422 Unprocessable Entity`** with an
**`application/problem+json`** body (RFC 7807) listing the violations. This turns "did our client send a
spec-valid request?" into a real assertion you get for free.

```typescript
describe('order submission — the contract gate', () => {
  it('Should_accept_the_order_When_the_request_is_spec_valid', async () => {
    // A well-formed request → Prism validates it, then serves the 201 example.
    const order = await client.submitOrder({ sku: 'SPR-1', qty: 3 });
    expect(order.orderId).toBe('ord-7'); // one logical assertion: the happy path is spec-valid
  });

  it('Should_be_rejected_422_When_the_request_violates_the_spec', async () => {
    // qty:0 violates `minimum: 1` in the spec — Prism returns 422 + application/problem+json.
    const res = await client.submitOrderRaw({ sku: 'SPR-1', qty: 0 });
    expect(res.status).toBe(422); // the contract gate caught a spec-invalid request
    expect(res.headers.get('content-type')).toContain('application/problem+json');
  });
});
```

Two framings of the gate:
- **Positive** — a real client call that returns `2xx` *proves* the request conformed to the contract. You get
  this on every happy-path test at no extra cost.
- **Negative** — deliberately send a malformed payload (`qty: 0`, a missing required field, a wrong type) and
  assert `422` + `problem+json`. This guards against the client drifting out of contract.

> Prism also validates **responses** in `proxy` mode (below). For `mock` mode the responses are spec-derived, so
> they are conformant by construction — the value in `mock` is the **request** gate.

## Static vs dynamic responses

| Mode | How | Trade-off |
|------|-----|-----------|
| **Static** (default) | Returns the spec's `example`/`examples` value | Deterministic — assert exact values; couples the test to the canned example |
| **Dynamic** | `--dynamic`/`-d` flag, or `Prefer: dynamic=true` per request | Schema-faked random data per call — decouples from one example, but you can only assert **shape/type**, not exact values |

Reach for dynamic when you want to prove the SUT handles *any* schema-valid payload (assert types/required
fields), and static when you want to assert exact values. Default to static for deterministic assertions; opt
into dynamic per-call with the `Prefer` header rather than flipping the whole server.

```typescript
it('Should_handle_any_schema_valid_widget_When_Prism_is_dynamic', async () => {
  const widget = await client.getWidget(42, { prefer: 'dynamic=true' });
  // Dynamic data is random — assert SHAPE, never exact values.
  expect(widget).toMatchObject({
    id: expect.any(Number), name: expect.any(String), priceMinor: expect.any(Number),
  });
});
```

## `prism proxy` mode — validate live upstream traffic

`prism proxy <spec> <upstreamUrl>` sits in front of the **real** service: it forwards each request to the
upstream and **validates both the request and the response against the spec**, flagging drift (e.g. the
upstream's response shape no longer matches the contract). It is the validation counterpart to `mock` — you get
the real data *and* a contract verdict.

```typescript
// proxy mode: forward to the real upstream and validate the live traffic against the spec.
container = await new GenericContainer('stoplight/prism:5.5.1')
  .withCopyFilesToContainer([{ source: specPath, target: '/tmp/openapi.yaml' }])
  .withCommand(['proxy', '-h', '0.0.0.0', '/tmp/openapi.yaml', 'https://real-upstream.example.com'])
  .withExposedPorts(4010)
  .start();
```

Cross-link `qa-network-monitoring-typescript`: both sit on the wire to a real service, but they do
opposite jobs — the MITM proxy **records/faults** real traffic, while Prism `proxy` **validates it against the
contract**. Use Prism `proxy` to catch a backend that has drifted from its own OpenAPI spec.

## Run modes — container / CLI

| Mode | How | When |
|------|-----|------|
| **Testcontainers container** (default) | `GenericContainer('stoplight/prism')` running `mock -h 0.0.0.0 /tmp/openapi.yaml`, spec copied in, port `4010` exposed | The Node default — CI-parity, identical to the Java/.NET ports' run mode |
| **`npx @stoplight/prism-cli`** | `npx @stoplight/prism-cli mock -p 4010 tests/fixtures/openapi.yaml` | Lighter local run; manual exploration; a shared mock across processes |

There is **no in-process mode** in any stack — Prism is always a separate process. That is exactly why all three
siblings are thin HTTP clients and the port is nearly 1:1 (the same story as Mountebank `mountebank`; contrast WireMock,
which runs in-process on JVM/.NET).

## Anti-patterns

- **Forgetting `-h 0.0.0.0` in the container.** Prism binds `localhost`, unreachable from the host; the test
  hangs/connection-refuses. *Fix:* always `mock -h 0.0.0.0`.
- **`setTimeout`/`page.waitForTimeout` to "wait for the mock to be ready".** Races startup. *Fix:* Testcontainers
  waits for the port; if you need to wait on an async SUT outcome, use `expect.poll(...)` on a condition.
- **Asserting exact values against `--dynamic`/`Prefer: dynamic=true` responses.** Dynamic data is random and the
  test will flake. *Fix:* dynamic → assert **shape/type**; static → assert exact values.
- **Expecting a request journal like WireMock/Mountebank.** Prism keeps **none**. *Fix:* assert on the SUT's
  **outcome** and on Prism's **validation verdict** (`2xx` vs `422`); if you must verify the exact bytes sent,
  use WireMock/Mountebank (they keep a journal) or MSW's `server.events`.
- **Hand-writing stubs alongside Prism.** That defeats the point — the spec *is* the mock. *Fix:* if you need
  hand-authored stubs, you want WireMock/Mountebank, not Prism.
- **Hard-coding the SUT's base URL instead of injecting the mapped Prism port.** The port is dynamic. *Fix:*
  construct the typed client with `http://${host}:${mappedPort}`.
- **Editing the spec to make a test pass.** The spec is the contract under test, not a test knob. *Fix:* steer
  responses with the `Prefer` header; change the spec only when the contract genuinely changes.
- **Reaching for Prism to mock the app's own `fetch`.** That's in-runtime interception. *Fix:* use **MSW**
  (`references/msw.md`); Prism is a separate server the SUT talks to over the wire.

## Examples

**End-to-end: the contract gate on both sides of an order submission.**

```typescript
import { describe, it, expect } from 'vitest';
import './support/prism.hooks';
import { client } from './support/prism.fixture';
import { orderRequestMother } from './support/order.mother';

describe('order submission against Prism', () => {
  it('Should_create_the_order_When_the_request_conforms_to_the_contract', async () => {
    // Spec-valid request → Prism validates, then serves the 201 example. The 2xx itself proves conformance.
    const order = await client.submitOrder(orderRequestMother.standard());
    expect(order.orderId).toBe('ord-7'); // one logical assertion: outcome
  });

  it('Should_reject_422_When_a_required_field_is_missing', async () => {
    // Omit the required `sku` — Prism's request validation rejects it before any business logic.
    const res = await client.submitOrderRaw({ qty: 3 } as never);
    expect(res.status).toBe(422); // the contract gate
  });
});
```

Lifecycle for this suite:
1. `beforeAll` starts the `stoplight/prism` container running `mock` against the committed `openapi.yaml`; the
   typed client is injected with the mapped Prism base URL.
2. The happy-path test drives a spec-valid request — the `2xx` *is* the proof of conformance (no stub setup).
3. The negative test sends a contract-violating payload and asserts `422` — the request gate.
4. `afterAll` stops the container. No `afterEach` — the mock is stateless.

**Test-data builder for request payloads (4+ fields → builder, per the global rules).**

```typescript
export const orderRequestMother = {
  standard: () =>
    new OrderRequestBuilder()
      .withSku('SPR-1').withQty(3).withCurrency('EUR').withIdempotencyKey('idem-123').build(),
};
```

## Rules (hard constraints)

- Prism is an **OpenAPI-spec-driven standalone server** — the committed `openapi.yaml` *is* the mock; inject the
  mapped Prism base URL into the typed client (`qa-api-client-writer-typescript`), never hard-code the dynamic
  port. **No hand-written stubs** — if you need them, use WireMock/Mountebank.
- Always run `mock -h 0.0.0.0` in a container (Prism binds `localhost` otherwise). Default port `4010`.
- Steer responses with the **`Prefer` header** (`example=`/`code=`/`dynamic=true`), not server state — keeps
  tests independent. The mock is **stateless**: one container per suite (`beforeAll`), **no `afterEach` reset**,
  never a container per test.
- Use the **validation contract gate**: assert a spec-valid call gets `2xx` (proves the request conforms) and a
  deliberately-malformed one gets **`422` + `application/problem+json`**.
- **Dynamic → assert shape/type only; static → assert exact values.** Default to static for determinism.
- Prism keeps **no request journal** — assert on the SUT's **outcome** and Prism's **validation verdict**, not a
  recorded-request log (use WireMock/Mountebank if you must verify exact bytes).
- **No `setTimeout`/`waitForTimeout`.** Testcontainers waits for the port; `expect.poll(...)` waits on a
  condition.
- Builders/ObjectMother for request payloads with 4+ fields. Test names `Should_X_When_Y`; `strict: true`. The
  OpenAPI spec is committed test data, not a secret.
- Prefer **WireMock/Mountebank** for hand-authored or multi-protocol stubs, **MSW** for the app's own in-runtime
  `fetch`, the route/MITM proxy for browser/real-service traffic, and **Pact** for consumer-driven contracts —
  use Prism when you have an OpenAPI spec and want it mocked + validated.

## Cross-references

- `qa-api-mocking-java` — same skill, Java / TestNG: the **same choreography** (start `prism mock` →
  point a thin `java.net.http.HttpClient` at the base URL → assert) against a `stoplight/prism` `GenericContainer`.
  Structure ported from here.
- `qa-api-mocking-dotnet` — same skill, .NET / NUnit: the same choreography over `HttpClient`
  (async-all-the-way) against a Testcontainers-for-.NET container. Structure ported from here.
- `references/mountebank.md` — the **closest precedent**: same stack-agnostic
  thin-HTTP-client-to-a-standalone-Node-server + Testcontainers run mode. The contrast: Mountebank is
  **imposter-driven** and **keeps a request journal**; Prism is **spec-driven** and keeps **none**.
- `references/wiremock.md` — hand-authored stubs, richest HTTP, in-process JVM/.NET; the
  stub-driven counterpoint to Prism's spec-driven model.
- `references/msw.md` — in-runtime interception of the app's own `fetch`; like Prism it keeps
  **no journal**, unlike WireMock/Mountebank.
- `qa-contract-testing-pact-typescript` — the **consumer-driven** contract (generated *from tests*) vs Prism's
  **spec-first** mock/validate (*from an existing OpenAPI doc*); complementary, not the same.
- `qa-network-monitoring-typescript` — `mockttp` MITM proxy that **records/faults** real traffic;
  Prism `proxy` **validates** real traffic against the spec. Opposite jobs on the same wire.
- `qa-api-client-writer-typescript` + `qa-api-dto-writer-typescript` + `qa-api-test-author-generator-typescript`
  — the typed client / DTOs / API tests; the spec describes those same DTOs, and the client is injected with the
  Prism base URL.
- `qa-test-environments-typescript` + `qa-db-testing-testcontainers-typescript` — the `stoplight/prism`
  container run mode + the per-suite lifecycle.
- `qa-ci-pipelines-typescript` — runs these tests; the container run mode needs Docker available.
