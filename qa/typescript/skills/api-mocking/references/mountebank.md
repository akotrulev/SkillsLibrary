# API Mocking — Mountebank (Node 20 / TypeScript / Vitest)

**This is the canonical stack for Mountebank** — `mb` is itself a Node tool, so TypeScript is its closest
home and the raw-`fetch` REST client is cleanest here. But unlike WireMock (`wiremock`, JVM-native) and MSW (`msw`,
TS-native in-runtime), Mountebank is **stack-agnostic**: there is **no native in-process Mountebank in any
runtime**. Every stack — TS, Java, .NET — does the identical thing: it is a **thin HTTP client to a running
`mb` server** that is driven entirely over an **HTTP REST control API**. So the Java/.NET siblings port
almost 1:1 from this file — they make the same `POST /imposters` → exercise → `GET /imposters/:port` →
`DELETE /imposters` REST calls; only the HTTP-client idioms change.

Mountebank is a **standalone, protocol-agnostic service-virtualization server**: you stand up `mb` (here, a
container), then `POST` an **imposter** to it — a fake service bound to a port that speaks a chosen protocol.
Your tests point the SUT's typed client at the imposter's port, exercise the flow, then read the imposter's
recorded `requests` to verify the SUT called the dependency the way you expected, and `DELETE` imposters
between tests.

> **The boundary that defines this skill.** Mountebank is a **standalone server you point a client at** — it
> *replaces* the dependency, the same end of the wire as WireMock. That is the sharp line against the
> `network-monitoring` family: `qa-network-monitoring-typescript` intercepts requests
> *inside a Playwright `page`* (no separate server, browser-only), and `qa-network-monitoring-typescript`
> is an *out-of-browser MITM proxy* (`mockttp`) on a *real* client's live traffic. Mountebank, like
> WireMock, **is** the dependency, fully under the test's control — but it adds **multiple protocols** and is
> driven purely over a REST API.

## Stack

- Node 20 + TypeScript (strict) + Vitest
- [`testcontainers`](https://www.npmjs.com/package/testcontainers) (`GenericContainer`) running the
  [`bbyars/mountebank`](https://hub.docker.com/r/bbyars/mountebank) image — the default run mode (cross-link
  `qa-test-environments-typescript` / `qa-db-testing-testcontainers-typescript`)
- A thin REST client to the `mb` **admin API** (port `2525`), built on the platform `fetch` — no third-party
  client needed (`POST/GET/DELETE /imposters`). (The `mountebank-helper` npm package exists but a raw client
  ports more directly to Java/.NET.)
- A typed `fetch` client (`qa-api-client-writer-typescript`) is the SUT — **constructor-injected** with the
  imposter's base URL

```bash
npm install --save-dev testcontainers
```

## The Mountebank model — imposters, stubs, lifecycle

Mountebank's whole model is three nested concepts, all expressed as JSON over the REST API:

- An **imposter** = a fake service bound to a `port`, speaking a `protocol` (`http`/`https`/`tcp`/`smtp`),
  holding an ordered list of **stubs**.
- A **stub** = `{ predicates: [...], responses: [...] }`. The **first stub whose predicates all match** the
  request answers it.
- **Predicates** decide *whether* a stub matches; **responses** decide *what* it returns.

The lifecycle of every suite that uses `mb`:

1. **Start** the `mb` server — a `GenericContainer('bbyars/mountebank')` exposing the admin port `2525`.
2. **Connect** the admin client — point a thin `fetch` client at `http://<host>:<adminPort>`.
3. **Create an imposter** — `POST /imposters` with `{ port, protocol, stubs, recordRequests: true }`.
4. **Point the SUT at the imposter's base URL** — injected into the typed client's constructor.
5. **Exercise** the SUT so it calls the dependency.
6. **Verify** via the imposter's recorded `requests` — `GET /imposters/:port`.
7. **Reset** between tests — `DELETE /imposters` (all) or `DELETE /imposters/:port` (one); **stop** the
   container at teardown.

### The admin client + container fixture (per-suite)

Mirror the per-suite lifecycle trade-off from `qa-db-testing-testcontainers-typescript`: **one container per
suite** (`beforeAll`/`afterAll`), delete imposters in `afterEach` so they don't leak. Starting a container
per test is far too slow.

```typescript
// tests/support/mb.client.ts — a thin typed REST client to the mb admin API (port 2525).
export interface Predicate { [op: string]: unknown }
export interface Response { is?: unknown; proxy?: unknown; inject?: string; _behaviors?: unknown }
export interface Stub { predicates?: Predicate[]; responses: Response[] }
export interface ImposterSpec {
  port: number;
  protocol: 'http' | 'https' | 'tcp' | 'smtp';
  stubs: Stub[];
  recordRequests?: boolean;
}
export interface RecordedRequest {
  method: string; path: string; query: Record<string, string>;
  headers: Record<string, string>; body: string;
}

export class MbClient {
  constructor(private readonly adminUrl: string) {}

  async createImposter(spec: ImposterSpec): Promise<void> {
    const res = await fetch(`${this.adminUrl}/imposters`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spec),
    });
    if (!res.ok) throw new Error(`createImposter failed: ${res.status} ${await res.text()}`);
  }

  // The recorded-request journal — needs recordRequests:true on the imposter.
  async recordedRequests(imposterPort: number): Promise<RecordedRequest[]> {
    const res = await fetch(`${this.adminUrl}/imposters/${imposterPort}`);
    const body = (await res.json()) as { requests?: RecordedRequest[] };
    return body.requests ?? [];
  }

  async deleteAllImposters(): Promise<void> {
    await fetch(`${this.adminUrl}/imposters`, { method: 'DELETE' });
  }
}
```

```typescript
// tests/support/mb.fixture.ts
import { GenericContainer, type StartedTestContainer } from 'testcontainers';
import { MbClient } from './mb.client';
import { WidgetApiClient } from '../../src/clients/widget.client';

export let container: StartedTestContainer;
export let mb: MbClient;
export let client: WidgetApiClient;

// The imposter's own port (inside the container) — distinct from the admin port (2525).
export const IMPOSTER_PORT = 4545;

export async function startMountebank(): Promise<void> {
  container = await new GenericContainer('bbyars/mountebank:2.9.1')
    .withExposedPorts(2525, IMPOSTER_PORT)        // expose BOTH the admin port and the imposter port
    .withCommand(['mb', 'start', '--allowInjection'])  // --allowInjection only if you use `inject` (sharp edge)
    .start();

  const adminUrl = `http://${container.getHost()}:${container.getMappedPort(2525)}`;
  mb = new MbClient(adminUrl);

  // The SUT's typed client is constructor-injected with the imposter's mapped base URL — never a static URL.
  const imposterBaseUrl = `http://${container.getHost()}:${container.getMappedPort(IMPOSTER_PORT)}`;
  client = new WidgetApiClient(imposterBaseUrl);
}

export async function resetMountebank(): Promise<void> {
  await mb.deleteAllImposters();   // wipe imposters (and their recorded requests) so tests stay independent
}

export async function stopMountebank(): Promise<void> {
  await container?.stop();
}
```

```typescript
// tests/support/mb.hooks.ts
import { beforeAll, afterEach, afterAll } from 'vitest';
import { startMountebank, resetMountebank, stopMountebank } from './mb.fixture';

beforeAll(startMountebank, 60_000);   // pulling/starting the image can take a moment
afterEach(resetMountebank);           // DELETE /imposters → keep tests independent
afterAll(stopMountebank);
```

> **Two ports, one container.** The **admin port** (`2525`) is where you POST imposters; each **imposter**
> binds its own port (here `4545`) that the SUT talks to. Expose and map both. Re-creating the imposter in
> each test (after `afterEach` deletes it) keeps tests independent.

## Core pattern — create the imposter, point the client, exercise, verify

The SUT is a typed `fetch` client constructor-injected with the imposter's base URL (cross-link
`qa-api-client-writer-typescript`). The test creates an imposter, drives the client, asserts the **response**
(one logical assertion), and verifies the **request** the client sent via the recorded-request journal.

```typescript
import { describe, it, expect } from 'vitest';
import './support/mb.hooks';
import { mb, client, IMPOSTER_PORT } from './support/mb.fixture';

describe('widget lookup against Mountebank', () => {
  it('Should_return_the_widget_When_the_imposter_responds_200', async () => {
    // 1. Create the imposter: a stub = predicates (match) → responses (return).
    await mb.createImposter({
      port: IMPOSTER_PORT,
      protocol: 'http',
      recordRequests: true,                 // keep the request journal for verification
      stubs: [
        {
          predicates: [{ equals: { method: 'GET', path: '/api/widgets/42' } }],
          responses: [
            {
              is: {
                statusCode: 200,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: 42, name: 'Sprocket', priceMinor: 1999 }),
              },
            },
          ],
        },
      ],
    });

    // 2. Exercise the SUT (already pointed at the imposter's base URL).
    const widget = await client.getWidget(42);

    // 3. Assert the response (one logical assertion).
    expect(widget).toEqual({ id: 42, name: 'Sprocket', priceMinor: 1999 });

    // 4. Verify the request the SUT actually sent (the recorded-request journal).
    const calls = await mb.recordedRequests(IMPOSTER_PORT);
    expect(calls).toHaveLength(1);
  });
});
```

The imposter must be created **before** the action that triggers the request — a stub added after the client
has already called won't match. An HTTP `is` response's `body` is a **string**: serialize JSON yourself
(`JSON.stringify`) and set `Content-Type`. The whole call chain is `async`/`await`.

## Predicates — which requests this stub answers

A stub's `predicates` are **ANDed** together; the **first stub** whose predicates all match wins. Predicates
match over `method`, `path`, `query`, `headers`, and `body`:

```typescript
stubs: [
  {
    predicates: [
      { equals: { method: 'POST', path: '/api/orders' } },
      { contains: { headers: { 'Content-Type': 'application/json' } } },
      { deepEquals: { query: { dryRun: 'false' } } },
      { matches: { body: '"sku"\\s*:\\s*"SPR-1"' } },          // regex over the raw body
    ],
    responses: [{ is: { statusCode: 201 } }],
  },
],
```

Predicate cheatsheet (the analogue of WireMock matchers / MSW resolvers):

| Match on | Predicate |
|----------|-----------|
| Exact equality (case-insensitive by default) | `{ equals: { path: '/a/b' } }` |
| Deep/exact object equality | `{ deepEquals: { query: { k: 'v' } } }` |
| Substring | `{ contains: { body: 'needle' } }` |
| Regex | `{ matches: { path: '/api/widgets/[0-9]+' } }` |
| Field present | `{ exists: { headers: { Authorization: true } } }` |
| Prefix / suffix | `{ startsWith: {...} }` / `{ endsWith: {...} }` |
| JSON-body selector | add `"jsonpath": { "selector": "$..sku" }` to a predicate |
| XML-body selector | add `"xpath": { "selector": "//sku" }` to a predicate |
| Case-sensitive match | add `"caseSensitive": true` to the predicate |
| Boolean combination | `{ and: [...] }` / `{ or: [...] }` / `{ not: {...} }` |

```typescript
// jsonpath selector + boolean OR.
predicates: [
  { or: [
    { equals: { path: '/api/widgets/42' } },
    { matches: { path: '/api/widgets/[0-9]+' }, jsonpath: { selector: '$..id' } },
  ] },
],
```

**Ordering is the catch-all.** Mountebank picks the **first matching stub**, so put specific stubs first and
a predicate-less stub **last** as a deterministic fallback (a stub with no `predicates` matches everything),
so the SUT sees a controlled response instead of Mountebank's default:

```typescript
stubs: [
  { predicates: [{ equals: { path: '/api/widgets/42' } }], responses: [{ is: { statusCode: 200, body: '{}' } }] },
  { responses: [{ is: { statusCode: 404, body: 'no stub matched' } }] },   // last = catch-all
],
```

## Responses — `is` canned, the multiple-responses cycle, `proxy`, `inject`

A stub's `responses` is an **array**. On repeated matching requests Mountebank **cycles through the array**,
repeating the last entry once exhausted. That cycling is Mountebank's **stateful / staged analogue** of
WireMock Scenarios and MSW `{once:true}`/closure-state — **no state machine needed**:

```typescript
// 503 on the first call, 201 on every call after — a transient-failure-then-recovery flow.
stubs: [
  {
    predicates: [{ equals: { method: 'POST', path: '/api/orders' } }],
    responses: [
      { is: { statusCode: 503 } },                                          // 1st call
      { is: { statusCode: 201, body: JSON.stringify({ orderId: 'ord-7' }) } }, // 2nd call onward
    ],
  },
],
```

Response types:

| Type | What it does | Analogue |
|------|--------------|----------|
| `is` | A canned response (`statusCode`/`headers`/`body`) | WireMock response definition / MSW `HttpResponse.json` |
| `proxy` | Record-and-replay against a **real upstream** (`{ to, mode }`) | WireMock recording |
| `inject` | A **JS function** computing the response from the request — requires `--allowInjection` | WireMock Handlebars templating / MSW dynamic resolver |

```typescript
// proxy: record-replay against the real service to bootstrap stubs (prefer hand-written for maintained tests).
responses: [{ proxy: { to: 'https://real-upstream.example.com', mode: 'proxyOnce' } }],
```

`inject` is powerful but a **sharp edge**: it requires starting `mb` with `--allowInjection`, runs arbitrary
JS server-side, and is harder to review. Prefer `is` + the response cycle; reach for `inject` only when the
response genuinely must be computed from the request.

## Fault & latency — `_behaviors`

`_behaviors` decorate a response before it's sent. The headline for resilience tests is **`wait`** — it makes
the imposter respond slowly so you can exercise the SUT's timeout/retry paths. **`wait` SIMULATES latency —
it is never a test sleep:**

```typescript
// Latency: the imposter itself is slow — SIMULATE slowness here, never setTimeout/waitForTimeout in the test.
stubs: [
  {
    predicates: [{ equals: { path: '/api/slow' } }],
    responses: [{ is: { statusCode: 200, body: '{}' }, _behaviors: { wait: 2000 } }],   // 2s server-side delay
  },
],
```

Other `_behaviors`: `repeat` (serve the same response N times before advancing the cycle), `decorate` (a JS
post-processor, also needs `--allowInjection`), `copy`/`lookup` (inject request data into the response). For
**hard faults** (dropped/garbled connection) use the `tcp` protocol and close the socket.

Cross-link the fault-injection framing of `qa-network-monitoring-typescript` — the proxy injects faults
onto a *real* service's traffic; Mountebank injects them **as** the (fake) service, exactly like WireMock.
Assert on the SUT's **visible outcome** (a thrown error, a fallback, a retry count) — and when you wait for
an async result, **wait on the condition**, never on a clock: use Vitest's `expect.poll` (a condition-poll
with a deadline), never `setTimeout`/`waitForTimeout`:

```typescript
await expect
  .poll(async () => (await client.getOrderStatus(7)).state, { timeout: 10_000, interval: 200 })
  .toBe('DONE');
```

## Multi-protocol — the headline (a `tcp` imposter)

Mountebank's reason to exist alongside WireMock is that an imposter can speak more than HTTP. Stand up a
**`tcp`** imposter to fake a non-HTTP dependency — exactly what WireMock cannot do. A `tcp` imposter's `is`
response uses a `data` field (the bytes to send back) instead of HTTP `statusCode`/`body`:

```typescript
// A second imposter on protocol 'tcp' — fake a raw socket service with a canned response.
await mb.createImposter({
  port: 5555,                        // expose+map this port on the container too
  protocol: 'tcp',
  recordRequests: true,
  stubs: [
    {
      predicates: [{ contains: { data: 'PING' } }],
      responses: [{ is: { data: 'PONG\n' } }],
    },
  ],
});
```

Keep the multi-protocol example short but real — the point is that the *same REST control API* and the *same*
predicate/response/journal model serve `http`, `tcp`, and `smtp`; only the `is` payload shape changes
(`statusCode`/`body` for HTTP, `data` for TCP).

## Verification — the recorded-request journal

Mountebank **keeps a request journal per imposter** when created with `recordRequests: true` — `GET
/imposters/:port` returns a `requests` array. This is the server-side "was X called, with what" assertion —
the same intent as the request-assertion framing in `qa-network-monitoring-typescript`,
recorded server-side and decoupled from the stub. **Make the contrast explicit: Mountebank *keeps* a journal
(like WireMock); MSW does *not*.**

```typescript
// Called exactly once, with the right body and header.
const calls = await mb.recordedRequests(IMPOSTER_PORT);
const posts = calls.filter((r) => r.method === 'POST' && r.path === '/api/orders');
expect(posts).toHaveLength(1);
expect(JSON.parse(posts[0].body)).toMatchObject({ sku: 'SPR-1', qty: 3 });   // exact payload
expect(posts[0].headers['Idempotency-Key']).toBeDefined();

// Never called (negative assertion).
const legacy = calls.filter((r) => r.path === '/api/legacy-pricing');
expect(legacy).toHaveLength(0);
```

Verification reads the journal **separately** from the stub — you can return a generic `201` and still assert
the exact body the SUT POSTed. `recordRequests: true` is required for the journal to be populated.

## Run modes — container / standalone CLI

| Mode | How | When |
|------|-----|------|
| **Testcontainers container** (default) | `GenericContainer('bbyars/mountebank')` exposing `2525` + imposter ports | The Node default — CI-parity with the standalone image, reachable on the Docker network; identical to the Java/.NET ports' run mode |
| **Standalone `mb` CLI** | `npx mountebank` / `mb start --configfile imposters.json` | A shared mock across processes; manual exploration; declarative imposter config |

There is **no in-process mode** in any stack — Mountebank is always a separate `mb` process. That is exactly
why all three siblings are thin REST clients and the port is nearly 1:1 (contrast WireMock, which runs
in-process on JVM/.NET).

## Anti-patterns

- **`setTimeout`/`page.waitForTimeout` to wait for an async / staged flow.** Races the server and is slow.
  *Fix:* use the **response cycle** (`[{is:503},{is:201}]`) for staged responses and `expect.poll(...)` on
  the client's visible state. Use `_behaviors.wait` only to *simulate* latency.
- **Forgetting `recordRequests: true`.** The `requests` array stays empty and verification silently passes.
  *Fix:* set `recordRequests: true` on every imposter you verify against.
- **Not deleting imposters between tests.** Imposters and their journals leak; ports collide; order matters.
  *Fix:* `DELETE /imposters` in `afterEach` and re-create the imposter per test.
- **Starting a container per test.** Far too slow. *Fix:* one container per suite (`beforeAll`), delete
  imposters between tests.
- **Hard-coding the SUT's base URL instead of injecting the mapped imposter port.** The port is dynamic.
  *Fix:* construct the typed client with `http://${host}:${mappedImposterPort}`.
- **Putting the catch-all stub first.** Mountebank serves the *first* matching stub, so a leading
  predicate-less stub shadows everything. *Fix:* specific stubs first, the predicate-less fallback last.
- **Reaching for `inject` for everything.** Arbitrary server-side JS, needs `--allowInjection`, hard to
  review. *Fix:* `is` + the response cycle covers most cases; reserve `inject` for genuinely computed responses.
- **Asserting only the response, never the request.** A passing response can hide a wrong payload/header.
  *Fix:* read the recorded `requests` and assert body/headers/count.
- **Reaching for Mountebank to mock the app's own `fetch`.** That's in-runtime interception. *Fix:* use
  **MSW** (`references/msw.md`); Mountebank is a separate server the SUT talks to over the wire.

## Examples

**End-to-end: a retry-then-succeed flow via the response cycle, with a verify on the recorded POSTs.**

```typescript
import { describe, it, expect } from 'vitest';
import './support/mb.hooks';
import { mb, client, IMPOSTER_PORT } from './support/mb.fixture';
import { orderRequestMother } from './support/order.mother';

describe('order submission against Mountebank', () => {
  it('Should_retry_then_succeed_When_orders_API_is_briefly_unavailable', async () => {
    // The response array cycles: 503 first, then 201 — the staged analogue of a WireMock scenario.
    await mb.createImposter({
      port: IMPOSTER_PORT,
      protocol: 'http',
      recordRequests: true,
      stubs: [
        {
          predicates: [{ equals: { method: 'POST', path: '/api/orders' } }],
          responses: [
            { is: { statusCode: 503 } },                                              // 1st attempt
            {
              is: {
                statusCode: 201,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ orderId: 'ord-7' }),
              },
            },                                                                         // retry onward
          ],
        },
      ],
    });

    // SUT has a retry policy; it should transparently recover.
    const order = await client.submitOrder(orderRequestMother.standard());

    expect(order.orderId).toBe('ord-7');                          // one logical assertion: outcome
    const attempts = (await mb.recordedRequests(IMPOSTER_PORT))
      .filter((r) => r.method === 'POST' && r.path === '/api/orders');
    expect(attempts).toHaveLength(2);                             // retried once
  });
});
```

Lifecycle for this test:
1. `beforeAll` starts the `mb` container; the typed client is injected with the mapped imposter base URL.
2. One stub stages a 503 → 201 cycle on the same endpoint (no state machine — the response array cycles).
3. The SUT's retry policy turns the transient 503 into success — the test asserts the **outcome** and
   verifies the dependency was hit exactly twice via the recorded-request journal.
4. `afterEach` deletes all imposters; the next test re-creates a clean one.

**Test-data builder for stub payloads (4+ fields → builder, per the global rules).**

```typescript
export const orderRequestMother = {
  standard: () =>
    new OrderRequestBuilder()
      .withSku('SPR-1').withQty(3).withCurrency('EUR').withIdempotencyKey('idem-123').build(),
};
```

## Rules (hard constraints)

- Mountebank is a **standalone, protocol-agnostic server you point a client at** — inject the imposter's
  mapped base URL into the typed client (`qa-api-client-writer-typescript`); never hard-code the dynamic port.
- Create the imposter **before** the action that triggers the request; the **first matching stub** wins, so
  order stubs specific-first, predicate-less catch-all last.
- One container per suite (`beforeAll`) + `DELETE /imposters` in `afterEach`, re-create per test — keep tests
  independent. Never a container per test.
- Set `recordRequests: true` on any imposter you verify against; assert both the **response** (one logical
  assertion) **and** the **request** (recorded `requests` — body/headers/count).
- **No `setTimeout`/`waitForTimeout`.** Use the **response cycle** for staged responses, `_behaviors.wait` to
  *simulate* latency, and `expect.poll(...)` to *assert* on a condition.
- Prefer `is` + the response cycle; reserve `proxy` for record-replay bootstrapping and `inject` (needs
  `--allowInjection`) for genuinely computed responses.
- Builders/ObjectMother for stub/predicate/response payloads with 4+ fields.
- Test names `Should_X_When_Y`; `strict: true`; no secrets in imposter specs.
- Prefer **WireMock** for the richest HTTP-only server or in-process JVM/.NET; **MSW** for the app's own
  in-runtime `fetch`; the Playwright route/MITM proxy for browser/real-service traffic — use Mountebank when
  you need a standalone fake that is multi-protocol or one tool across many stacks.

## Cross-references

- `qa-api-mocking-java` — same skill, Java / TestNG: the **same REST choreography** over
  `java.net.http.HttpClient` against a `bbyars/mountebank` `GenericContainer`. Structure ported from here.
- `qa-api-mocking-dotnet` — same skill, .NET / NUnit: the same REST choreography over `HttpClient`
  (async-all-the-way) against a Testcontainers-for-.NET container. Structure ported from here.
- `references/wiremock.md` — the **standalone-server peer**. Both replace the dependency and
  keep a request journal; **Mountebank adds multiple protocols and is stack-agnostic HTTP-driven**, while
  **WireMock is richer on HTTP and runs in-process on JVM/.NET** (Mountebank never does). Pick WireMock for
  HTTP depth, Mountebank for protocol breadth.
- `references/msw.md` — the **in-runtime vs standalone-server** contrast: MSW intercepts the
  app's own `fetch` in-process and keeps **no** journal; Mountebank is a separate server that *does*.
- Prism — the **OpenAPI-spec-driven** member of the family (a mock derived from a spec, plus a
  validation-proxy mode); same stack-agnostic CLI/container + thin-client port story as Mountebank.
- `qa-network-monitoring-typescript` — in-browser `page.route` interception; no
  separate server. The boundary: route = inside the browser, Mountebank = a server you point at.
- `qa-network-monitoring-typescript` — `mockttp` out-of-browser MITM proxy on a *real* service's
  traffic; Mountebank *replaces* the service. Mirror its fault-injection framing (`_behaviors.wait` / `tcp`).
- `qa-api-client-writer-typescript` + `qa-api-test-author-generator-typescript` — the typed client / API tests
  pointed at the imposter base URL (constructor injection).
- `qa-test-environments-typescript` + `qa-db-testing-testcontainers-typescript` — the `bbyars/mountebank`
  container run mode + the per-suite-vs-per-test lifecycle trade-off mirrored here.
- `qa-ci-pipelines-typescript` — runs these tests; the container run mode needs Docker
  available in the job.
