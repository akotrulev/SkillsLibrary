---
name: qa-api-mocking-wiremock-typescript
description: >-
  Service-virtualization / API-mocking with WireMock in Node 20 + TypeScript (Vitest): run WireMock as a
  standalone server (a Testcontainers `wiremock/wiremock` container), drive it over its admin API with
  `wiremock-captain`, point the system-under-test's typed `fetch` client at the container's base URL,
  exercise the flow, then verify (via `mock.getRequestsForAPI(...)`) the SUT called the dependency as
  expected. Use when a test must run against a controlled fake of a downstream HTTP dependency (flaky,
  unavailable, rate-limited, or costly) instead of the real service — `new WireMock(baseUrl)`,
  `mock.register({ method, endpoint }, { status, body })`, request matching (URL/method/headers/query
  /body JSON via matching attributes), response definition + delay/fault features, stateful **scenarios**
  (`scenario: { scenarioName, requiredScenarioState, newScenarioState }`), request verification, and run
  modes (container / standalone npx / in-process JVM). Triggers: "mock the payment API with WireMock in
  Node", "fake a downstream service for this Vitest integration test", "WireMock returns 202 then 200",
  "verify our fetch client POSTed the right body", "inject a 500 / delay from a stubbed dependency". Do
  NOT use for: in-browser request interception with a Playwright `page` (use
  qa-network-monitoring-playwright-routes-typescript), an out-of-browser MITM proxy over a real client's
  live traffic (use qa-network-monitoring-proxy-typescript), the Java stack (the canonical — use
  qa-api-mocking-wiremock-java), or the .NET stack (use qa-api-mocking-wiremock-dotnet). For browser/Node
  request interception in the app's *own* runtime prefer MSW (qa-api-mocking-msw-typescript); sibling
  tools: Mountebank, Prism.
---

# API Mocking — WireMock (Node 20 / TypeScript / Vitest)

The TypeScript port of the canonical `qa-api-mocking-wiremock-java`. Same model (a standalone HTTP server
that fakes a downstream dependency), same lifecycle, same matcher → response → verify shape — but WireMock
has **no native Node implementation**: it's a JVM server. So in TypeScript you **run WireMock as a server**
(a Testcontainers `wiremock/wiremock` container, or `npx wiremock`) and talk to it over its **admin API**
with [`wiremock-captain`](https://www.npmjs.com/package/wiremock-captain) — a typed client that registers
stubs and reads received requests. The TS stack is therefore a **thin client to a running server**, where
Java/.NET run the server in-process.

> **TS-specific framing.** Because WireMock is a separate process here, the "in-process server" run mode
> the Java/.NET siblings default to does not exist. The Node default is the **Testcontainers container**:
> language-agnostic, CI-parity with the standalone image, and the SUT can reach it on the Docker network.
> If your app's own `fetch`/XHR layer is what you want to mock *inside the app's runtime* (no separate
> server), that's **MSW** (`qa-api-mocking-msw-typescript`, #23), not WireMock.

WireMock is an **HTTP service-virtualization / API-mocking server**: a real HTTP server you stand up so
your tests run against a **controlled fake** of a downstream dependency instead of the real service. You
register **stub mappings** (a request matcher → a response definition), point the SUT's typed client at
the server's base URL, exercise the flow, then **verify** the SUT called the dependency the way you
expected.

> **The boundary that defines this skill.** WireMock is a **standalone HTTP server you point a client at**.
> That is the sharp line against the `network-monitoring` family:
> `qa-network-monitoring-playwright-routes-typescript` intercepts requests *inside a Playwright `page`*
> (no separate server, browser-only), and `qa-network-monitoring-proxy-typescript` is an *out-of-browser
> MITM proxy* (`mockttp`) on a real client's live traffic. WireMock owns the other end of the wire: it
> **is** the dependency, fully under the test's control.

## Decision matrix — WireMock vs the rest of the `api-mocking` family, vs network-monitoring

| Need | Use | Why |
|------|-----|-----|
| A **standalone HTTP server** faking a downstream dependency; rich matching + scenarios + verification; the SUT is a service/native client | **WireMock (this skill)** | A real server you point at; CI-parity image; cross-stack |
| Mock the app's **own** `fetch`/XHR in a browser or Node runtime, no separate server | **MSW** (`qa-api-mocking-msw-typescript`, #23) | Request-interception in-runtime; TS-primary, lighter for app-level tests |
| Intercept **browser** requests inside a Playwright test | `qa-network-monitoring-playwright-routes-typescript` (#8) | `page.route` lives in the browser |
| Observe / rewrite a **real client's** live traffic out-of-browser (MITM) | `qa-network-monitoring-proxy-typescript` (#10) | `mockttp` proxy on the wire to the *real* service; WireMock replaces it |
| **Protocol-agnostic** over-the-wire imposters (TCP/HTTP/SMTP) | Mountebank (#24) | Multi-protocol |
| Mock derived **from an OpenAPI spec** automatically | Prism (#25) | Spec-driven |

**Rule of thumb (TS):** *Faking a downstream service the SUT talks HTTP to, want CI-parity + scenarios?*
→ WireMock (container). *Mocking the front-end/app's own outbound `fetch` in-runtime?* → MSW. *Real
browser/real-service traffic?* → the network-monitoring family.

## Stack

- Node 20 + TypeScript (strict) + Vitest
- [`wiremock-captain`](https://www.npmjs.com/package/wiremock-captain) — the typed admin client
  (`WireMock`, `IWireMockRequest`, `IWireMockResponse`, `Method`, `MatchingAttributes`, `IWireMockFeatures`)
- [`testcontainers`](https://www.npmjs.com/package/testcontainers) (`GenericContainer`) running the
  `wiremock/wiremock` image — the default run mode (cross-link `qa-test-environments-typescript` /
  `qa-db-testing-testcontainers-typescript`)
- A typed `fetch` client (`qa-api-client-writer-typescript`) is the SUT — **constructor-injected** with
  the container's base URL

```bash
npm install --save-dev wiremock-captain testcontainers
```

## The WireMock model — lifecycle

WireMock is a real HTTP server (here, a container). The lifecycle of every suite that uses it:

1. **Start** the WireMock server — a `GenericContainer('wiremock/wiremock')` exposing `8080`.
2. **Connect** the admin client — `const mock = new WireMock(baseUrl)`.
3. **Register stub mappings** — `await mock.register(request, response, features?)`.
4. **Point the SUT at the base URL** — injected into the typed client's constructor.
5. **Exercise** the SUT so it calls the dependency.
6. **Verify** the SUT sent the requests you expected — `await mock.getRequestsForAPI(method, endpoint)`.
7. **Reset** between tests (`resetMappings` + `deleteAllRequests`); **stop** the container at teardown.

### Per-suite vs per-test lifecycle (the same trade-off as Testcontainers)

Mirror the lifecycle trade-off from `qa-db-testing-testcontainers-typescript`:

- **One container per suite** (`beforeAll`/`afterAll`), reset mappings + requests in `afterEach` —
  fastest, but you **must** reset between tests so stubs/recorded requests don't leak. Default; tests
  stay independent because state is reset. (Starting a container per test is far too slow.)

```typescript
// tests/support/wiremock.fixture.ts
import { GenericContainer, type StartedTestContainer } from 'testcontainers';
import { WireMock } from 'wiremock-captain';
import { WidgetApiClient } from '../../src/clients/widget.client';

export let container: StartedTestContainer;
export let mock: WireMock;
export let client: WidgetApiClient;

export async function startWireMock(): Promise<void> {
  container = await new GenericContainer('wiremock/wiremock:3.9.1')
    .withExposedPorts(8080)
    .withCommand(['--global-response-templating'])   // enable Handlebars templating for all stubs
    .start();
  const baseUrl = `http://${container.getHost()}:${container.getMappedPort(8080)}`;
  mock = new WireMock(baseUrl);
  // The SUT's typed client is constructor-injected with the mock's base URL — never a static URL.
  client = new WidgetApiClient(baseUrl);
}

export async function resetWireMock(): Promise<void> {
  await mock.resetMappings();        // wipe stubs
  await mock.deleteAllRequests();    // wipe the recorded request journal so verify counts are clean
}

export async function stopWireMock(): Promise<void> {
  await container?.stop();
}
```

```typescript
// tests/support/wiremock.hooks.ts
import { beforeAll, afterEach, afterAll } from 'vitest';
import { startWireMock, resetWireMock, stopWireMock } from './wiremock.fixture';

beforeAll(startWireMock, 60_000);   // pulling/starting the image can take a moment
afterEach(resetWireMock);           // keep tests independent
afterAll(stopWireMock);
```

## Core pattern — stub, point the client, exercise, verify

The SUT is a typed `fetch` client constructor-injected with the base URL (cross-link
`qa-api-client-writer-typescript`). The test stubs the dependency, drives the client, asserts the
**response** (one logical assertion), and verifies the **request** the client sent.

```typescript
import { describe, it, expect } from 'vitest';
import { Method } from 'wiremock-captain';
import './support/wiremock.hooks';
import { mock, client } from './support/wiremock.fixture';

describe('widget lookup against WireMock', () => {
  it('Should_return_the_widget_When_the_service_responds_200', async () => {
    // 1. Stub: matcher → response definition.
    await mock.register(
      {
        method: Method.GET,
        endpoint: '/api/widgets/42',
        headers: { Accept: 'application/json' },
      },
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: { id: 42, name: 'Sprocket', priceMinor: 1999 },
      },
    );

    // 2. Exercise the SUT (already pointed at the WireMock base URL).
    const widget = await client.getWidget(42);

    // 3. Assert the response (one logical assertion).
    expect(widget).toEqual({ id: 42, name: 'Sprocket', priceMinor: 1999 });

    // 4. Verify the request the SUT actually sent.
    const calls = await mock.getRequestsForAPI(Method.GET, '/api/widgets/42');
    expect(calls).toHaveLength(1);
  });
});
```

`body` as an object is serialized as JSON and `Content-Type` is set for you. Stub mappings must be
registered **before** the action that triggers the request — a stub added after the client has already
called won't match. The whole call chain is `async`/`await`.

## Request matching — which requests this stub answers

Match on URL, method, query, headers, and body. The default for `endpoint` is exact-path equality; for
regex/contains and JSON-body matching, attach `MatchingAttributes`:

```typescript
import { Method, MatchingAttributes } from 'wiremock-captain';

await mock.register(
  {
    method: Method.POST,
    endpoint: '/api/orders',
    queryParameters: { dryRun: { matcher: 'equalTo', value: 'false' } },
    headers: { 'Content-Type': { matcher: 'contains', value: 'application/json' } },
    body: { sku: 'SPR-1', qty: 3 },                       // JSON-equality body match
  },
  { status: 201 },
  { requestBodyFeature: MatchingAttributes.EqualToJson }, // ignore order / extra fields per feature flags
);
```

Matcher cheatsheet (`wiremock-captain` translates these to WireMock's `urlPath`/`equalToJson`/`matchesJsonPath`
admin payloads):

| Match on | How |
|----------|-----|
| Exact path | `endpoint: '/a/b'` |
| Path regex | `endpoint: '/a/[0-9]+'` + `requestEndpointFeature: EndpointFeature.UrlPathPattern` |
| Query param | `queryParameters: { k: { matcher: 'equalTo', value: 'v' } }` |
| Header contains | `headers: { Accept: { matcher: 'contains', value: 'json' } }` |
| Body JSON equality | `body: {...}` + `requestBodyFeature: MatchingAttributes.EqualToJson` |
| Body JSONPath | `body: '$.field'` + `requestBodyFeature: MatchingAttributes.MatchesJsonPath` |

**Priority & catch-all.** When two stubs could match, the lower `stubPriority` wins (1 = highest). A
catch-all default catches unmatched requests so the SUT sees a deterministic response instead of
WireMock's default `404`:

```typescript
await mock.register(
  { method: Method.GET, endpoint: '/.*' },
  { status: 404, body: 'no stub matched' },
  { stubPriority: 10, requestEndpointFeature: EndpointFeature.UrlPathPattern },   // low priority fallback
);
```

## Response definition — status, headers, body, templating, delay/fault

```typescript
await mock.register(
  { method: Method.GET, endpoint: '/api/widgets/42' },
  {
    status: 200,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' },
    body: { id: 42 },
  },
);
```

**Response templating (Handlebars)** derives the response from the request — enabled here by the
`--global-response-templating` container command. Reference `{{request.*}}` in a string body:

```typescript
await mock.register(
  { method: Method.GET, endpoint: '/api/widgets/[0-9]+' },
  {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    // {{request.pathSegments.[2]}} echoes the id from the URL the SUT requested.
    body: '{ "id": {{request.pathSegments.[2]}}, "name": "generated" }',
  },
  { requestEndpointFeature: EndpointFeature.UrlPathPattern },
);
```

### Fault & delay injection — resilience / chaos testing

WireMock simulates latency and broken responses so you can test the SUT's **error paths** (retries,
timeouts). This is WireMock's own feature — **not** a `setTimeout` sleep in the test:

```typescript
import { DelayType, WireMockFault } from 'wiremock-captain';

// Latency: the stub itself is slow — SIMULATE slowness here, never waitForTimeout in the test.
await mock.register(
  { method: Method.GET, endpoint: '/api/slow' },
  { status: 200, body: {} },
  { responseDelay: { type: DelayType.FIXED, constantDelay: 2000 } },
);

// Fault: dropped / malformed response to exercise the client's failure handling.
await mock.register(
  { method: Method.GET, endpoint: '/api/reset' },
  { status: 200 },
  { fault: WireMockFault.CONNECTION_RESET_BY_PEER },
);
```

Cross-link the fault-injection angle of `qa-network-monitoring-proxy-typescript` — the proxy injects
faults onto a *real* service's traffic; WireMock injects them as *the* (fake) service. Assert on the SUT's
**visible outcome** (a thrown error, a fallback value, a retry count) — never sleep-then-check.

## Stateful behavior — scenarios (the state machine)

A **scenario** lets one stub's response depend on the server's current state — to model eventual
consistency, multi-step flows, or "first call pending, then done". Pass a `scenario` feature naming the
state this stub requires and the state it moves to. Scenarios start in `Started`.

```typescript
const scenarioName = 'order-fulfilment';

// First poll: 202 Accepted, then advance to "READY".
await mock.register(
  { method: Method.GET, endpoint: '/api/orders/7/status' },
  { status: 202, body: { state: 'PENDING' } },
  { scenario: { scenarioName, requiredScenarioState: 'Started', newScenarioState: 'READY' } },
);

// Subsequent polls (state == READY): 200 Done.
await mock.register(
  { method: Method.GET, endpoint: '/api/orders/7/status' },
  { status: 200, body: { state: 'DONE' } },
  { scenario: { scenarioName, requiredScenarioState: 'READY' } },
);
```

The SUT polls until it sees `DONE`. **Wait on the condition (the `DONE` payload), not on a clock** — use
Vitest's `expect.poll` (a condition-poll with a deadline), never `setTimeout`/`waitForTimeout`:

```typescript
await expect
  .poll(async () => (await client.getOrderStatus(7)).state, { timeout: 10_000, interval: 200 })
  .toBe('DONE');
```

## Verification — assert the SUT called the dependency

WireMock records every received request in its journal; `wiremock-captain` reads it. This is the
server-side "was X called, with what" assertion — the same intent as the request-assertion framing in
`qa-network-monitoring-playwright-routes-typescript`, but recorded server-side, decoupled from the stub:

```typescript
// Called exactly once.
const orders = await mock.getRequestsForAPI(Method.POST, '/api/orders');
expect(orders).toHaveLength(1);
expect(orders[0].request.body).toMatchObject({ sku: 'SPR-1', qty: 3 });   // exact payload
expect(orders[0].request.headers['Idempotency-Key']).toBeDefined();

// Never called (negative assertion).
const legacy = await mock.getRequestsForAPI(Method.GET, '/api/legacy-pricing');
expect(legacy).toHaveLength(0);
```

Verification reads the journal **separately** from the stub — you can stub a generic 201 and still assert
the exact body the SUT POSTed.

## Record & playback (mention, don't over-invest)

To bootstrap stubs from a real service: start WireMock with a proxy mapping to the real upstream and
recording enabled (`POST /__admin/recordings/start` with the target URL), drive the SUT once, then
`POST /__admin/recordings/stop` to write the mappings for offline replay. Prefer hand-written stubs for
tests you'll maintain.

## Run modes — container / standalone npx / in-process JVM

| Mode | How | When |
|------|-----|------|
| **Testcontainers container** (default) | `GenericContainer('wiremock/wiremock')` exposing `8080` | The Node default — CI-parity with the standalone image, reachable on the Docker network; no JVM in your repo |
| **Standalone `npx`** | `npx wiremock --port 8080`, mappings in `mappings/`, files in `__files/` | A shared mock across processes; manual exploration; record-&-playback |
| **In-process JVM** | n/a in Node — see `qa-api-mocking-wiremock-java` | Only available in the JVM siblings; the TS stack always talks to a separate process |

The container is the default for Node — there is no in-process option (the Java/.NET siblings have one
because WireMock/`WireMock.Net` run in their host runtime; Node always talks to a separate server).

## Anti-patterns

- **`setTimeout`/`page.waitForTimeout` to wait for an async / scenario flow.** Races the server and is
  slow. *Fix:* drive a **scenario** for staged responses and `expect.poll(...)` on the client's visible
  state. Use WireMock's `responseDelay` only to *simulate* latency.
- **Forgetting to reset between tests.** Stubs and the request journal leak, so order matters and verify
  counts are wrong. *Fix:* `mock.resetMappings()` + `mock.deleteAllRequests()` in `afterEach`.
- **Starting a container per test.** Far too slow. *Fix:* one container per suite (`beforeAll`), reset
  state between tests.
- **Hard-coding the SUT's base URL instead of injecting the container's mapped port.** The port is
  dynamic. *Fix:* construct the typed client with `http://${host}:${mappedPort}`.
- **Asserting only the response, never the request.** A passing response can hide a wrong payload/header.
  *Fix:* `getRequestsForAPI(...)` and assert body/headers/count.
- **One giant catch-all stub for everything.** Tests pass even when the SUT calls the wrong endpoint.
  *Fix:* narrow stubs per case; a `404` catch-all only as an explicit low-priority fallback.
- **Reaching for WireMock to mock the app's own `fetch`.** That's in-runtime interception. *Fix:* use
  **MSW** (`qa-api-mocking-msw-typescript`) for app-level `fetch`/XHR mocking; WireMock is a separate
  server the SUT talks to over the network.

## Examples

**End-to-end: a retry-then-succeed flow gated on a scenario, with a verify on the final POST.**

```typescript
import { describe, it, expect } from 'vitest';
import { Method } from 'wiremock-captain';
import './support/wiremock.hooks';
import { mock, client } from './support/wiremock.fixture';
import { orderRequestMother } from './support/order.mother';

describe('order submission against WireMock', () => {
  it('Should_retry_then_succeed_When_orders_API_is_briefly_unavailable', async () => {
    const flow = 'orders-transient-503';

    // First attempt: 503 (transient), then advance to "UP".
    await mock.register(
      { method: Method.POST, endpoint: '/api/orders' },
      { status: 503 },
      { scenario: { scenarioName: flow, requiredScenarioState: 'Started', newScenarioState: 'UP' } },
    );

    // Retry (state == UP): 201 Created with the order id.
    await mock.register(
      { method: Method.POST, endpoint: '/api/orders' },
      { status: 201, headers: { 'Content-Type': 'application/json' }, body: { orderId: 'ord-7' } },
      { scenario: { scenarioName: flow, requiredScenarioState: 'UP' } },
    );

    // SUT has a retry policy; it should transparently recover.
    const order = await client.submitOrder(orderRequestMother.standard());

    expect(order.orderId).toBe('ord-7');                          // one logical assertion: outcome
    const attempts = await mock.getRequestsForAPI(Method.POST, '/api/orders');
    expect(attempts).toHaveLength(2);                             // retried once
  });
});
```

Lifecycle for this test:
1. `beforeAll` starts the WireMock container; the typed client is injected with the mapped base URL.
2. Two scenario stubs stage a 503 → 201 sequence on the same endpoint.
3. The SUT's retry policy turns the transient 503 into success — the test asserts the **outcome** and
   verifies the dependency was hit exactly twice via the request journal.
4. `afterEach` resets mappings + the journal; the next test starts clean.

**Test-data builder for stub payloads (4+ fields → builder, per the global rules).**

```typescript
export const orderRequestMother = {
  standard: () =>
    new OrderRequestBuilder()
      .withSku('SPR-1').withQty(3).withCurrency('EUR').withIdempotencyKey('idem-123').build(),
};
```

## Rules (hard constraints)

- WireMock is a **standalone HTTP server you point a client at** — inject the container's mapped base URL
  into the typed client (`qa-api-client-writer-typescript`); never hard-code the dynamic port.
- Register stub mappings **before** the action that triggers the request.
- One container per suite (`beforeAll`) + reset mappings & journal in `afterEach` — keep tests
  independent and verify counts correct. Never a container per test.
- Assert both sides: the **response** (one logical assertion) **and** the **request**
  (`getRequestsForAPI(...)` — body/headers/count).
- **No `setTimeout`/`waitForTimeout`.** Use WireMock's `responseDelay` to *simulate* latency and
  `expect.poll(...)` to *assert* on a condition. Use **scenarios** for staged/eventual-consistency responses.
- Use the **narrowest** matcher; a catch-all only as an explicit low-priority fallback.
- Builders/ObjectMother for stub & request payloads with 4+ fields.
- Test names `Should_X_When_Y`; `strict: true`; no secrets in stub files.
- Prefer **MSW** for mocking the app's own in-runtime `fetch`; prefer the Playwright route/MITM proxy for
  browser/real-service traffic — use WireMock when the SUT talks HTTP to a separate dependency.

## Cross-references

- `qa-api-mocking-wiremock-java` — the **canonical** stack, Java / TestNG (`org.wiremock:wiremock`,
  in-process `WireMockServer`, `stubFor`/`verify`/Scenarios). Structure ported from there.
- `qa-api-mocking-wiremock-dotnet` — same skill, .NET / NUnit (`WireMock.Net`, in-process
  `WireMockServer.Start()`, `FindLogEntries`). Structure ported.
- `qa-api-mocking-msw-typescript` (#23, next) — the second `api-mocking` sibling and the **TS-primary**
  one: MSW intercepts requests in the app's *own* runtime (Service Worker / Node), no separate server —
  reach for it for app-level `fetch`/XHR mocking. Plus Mountebank (#24) and Prism (#25).
- `qa-network-monitoring-playwright-routes-typescript` (#8) — in-browser `page.route` interception; no
  separate server, Playwright-only. The boundary: route = inside the browser, WireMock = a server you
  point at.
- `qa-network-monitoring-proxy-typescript` (#10) — `mockttp` out-of-browser MITM proxy on a *real*
  service's traffic; WireMock *replaces* the service. Mirror its fault-injection framing.
- `qa-api-client-writer-typescript` + `qa-api-test-author-generator-typescript` — the typed client / API
  tests pointed at the WireMock base URL (constructor injection).
- `qa-test-environments-typescript` + `qa-db-testing-testcontainers-typescript` — the Testcontainers run
  mode + the per-suite-vs-per-test lifecycle trade-off mirrored here.
- `qa-ci-pipelines-github-actions-typescript` — runs these tests; the container run mode needs Docker
  available in the job.
