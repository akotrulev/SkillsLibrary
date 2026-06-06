---
name: qa-api-mocking-msw-typescript
description: >-
  API-mocking with MSW (Mock Service Worker) in Node 20 + TypeScript — intercept the app's **own**
  outbound HTTP **in-runtime** (no separate server): `setupServer(...handlers)` for Node tests
  (Vitest/Jest unit, component, integration) and `setupWorker(...handlers)` for the browser
  (Playwright/component), with `http.get('/api/x', resolver)` / `http.post(...)` / `graphql` handlers
  returning `HttpResponse.json(body, { status })`. Use when a test must fake the dependency the
  application's own `fetch`/XHR talks to, inside the app's process, instead of standing up a separate
  mock server. Covers the `server.listen({ onUnhandledRequest: 'error' })` / `resetHandlers()` /
  `close()` lifecycle, `server.use(...)` per-test overrides, path-param/query/header/body matching,
  dynamic + `{ once: true }` + `passthrough()` + `HttpResponse.error()` responses, closure-state staged
  responses (the Scenarios analogue), and verification via the `server.events.on('request:start' |
  'response:mocked', ...)` listener API (MSW has **no request journal**). Triggers: "mock our app's
  fetch with MSW", "MSW handler returns 500 for this component test", "override a handler for one test",
  "assert MSW intercepted the POST", "onUnhandledRequest error". Do NOT use for: a standalone HTTP
  server the SUT (a service/native client) points at — use WireMock (qa-api-mocking-wiremock-typescript)
  / Mountebank (#24) / Prism (#25); in-browser interception at the Playwright **driver** for E2E (use
  qa-network-monitoring-playwright-routes-typescript); an out-of-browser MITM proxy on real traffic (use
  qa-network-monitoring-proxy-typescript); the Java sidecar port (use qa-api-mocking-msw-java) or the
  .NET sidecar port (use qa-api-mocking-msw-dotnet) — those run MSW as a standalone Node sidecar because
  MSW cannot intercept in-process in the JVM/.NET runtime.
---

# API Mocking — MSW / Mock Service Worker (Node 20 / TypeScript)

**This is the canonical, native-home stack for MSW.** MSW (Mock Service Worker) is fundamentally a
TypeScript/JavaScript tool: it intercepts requests **inside the application's own runtime** — a Service
Worker in the browser (`setupWorker`), or Node request interception by patching `http`/`https`/`fetch`
(`setupServer` from `msw/node`). There is **no separate mock server** in the TS case; the mock lives
*in-process* with the code under test. That makes MSW the right tool for **front-end / app-level tests**
— unit, component, and integration tests where the app's own `fetch`/XHR is exactly what you want to fake.

> **The boundary that defines this skill — and the whole reason both #22 and #23 exist.**
> **WireMock (`qa-api-mocking-wiremock-typescript`, #22) is a separate HTTP server you point a client at**
> — it owns the other end of the wire and *replaces* the dependency. **MSW intercepts requests inside the
> app's own runtime** — no separate server; the mock sits in-process with the code under test. Reach for
> **MSW** when the thing making the request is the **application itself** (a React app's `fetch`, a Node
> module's HTTP client) and you're writing app/component-level tests. Reach for **WireMock** when the SUT
> is a service/native client that talks HTTP to a genuinely external dependency and you want a real
> server, CI-parity image, and scenarios. This contrast is the spine of the decision matrix below.

> **⚠️ TS-native — the inverse of #22's caveat.** WireMock (#22) is **JVM-native** with a *thin TS client*
> to a containerised server; MSW is **TS-native** with **sidecar-only Java/.NET ports**. MSW cannot
> intercept in-process in the JVM or .NET runtime at all — for those stacks MSW only makes sense run as a
> **standalone Node sidecar mock server** (`@mswjs/http-middleware`'s `createServer(...handlers)` wraps
> MSW handlers in an Express server you start as a separate process; the JVM/.NET SUT then points its
> client at that base URL). See `qa-api-mocking-msw-java` / `qa-api-mocking-msw-dotnet` for that honest
> shape. Everything below is the first-class, in-runtime TypeScript experience.

## Decision matrix — MSW vs the rest of the `api-mocking` family, vs network-monitoring

| Need | Use | Why |
|------|-----|-----|
| Mock the app's **own** `fetch`/XHR **in-runtime** (no separate server); Node unit/component/integration or browser | **MSW (this skill)** | Intercepts inside the app's process; TS-native; lightest for app-level tests |
| A **standalone HTTP server** faking a downstream dependency; the SUT is a service/native client; rich scenarios + CI-parity image | **WireMock** (`qa-api-mocking-wiremock-typescript`, #22) | A real server you point at; owns the wire; cross-stack |
| Intercept **browser** requests at the Playwright **driver** for E2E | `qa-network-monitoring-playwright-routes-typescript` (#8) | `page.route` lives at the Playwright driver, outside the app's runtime — see the carefully-drawn line below |
| Observe / rewrite a **real client's** live traffic out-of-browser (MITM) | `qa-network-monitoring-proxy-typescript` (#10) | `mockttp` proxy on the wire to the *real* service; MSW replaces it in-runtime |
| **Protocol-agnostic** over-the-wire imposters (TCP/HTTP/SMTP) | Mountebank (#24) | Multi-protocol, standalone `mb` server |
| Mock derived **from an OpenAPI spec** automatically | Prism (#25) | Spec-driven |

**Rule of thumb (TS):** *Faking the dependency the **app itself** calls, in a unit/component/integration
test?* → MSW. *Faking a downstream service a **separate SUT** talks HTTP to, want a real server +
scenarios?* → WireMock. *Real browser-driver/real-service traffic?* → the network-monitoring family.

### MSW Service Worker vs `page.route` — the careful line (both "in-browser", different layers)

Both MSW's `setupWorker` and Playwright's `page.route` (#8) intercept in the browser — but at **different
layers, for different test shapes**:

- **MSW (`setupWorker`)** intercepts at the **Service Worker** registered in the *app's own runtime*. The
  app's `fetch` is mocked exactly as it runs in production, so it's the right fit for **component tests**
  and dev-time mocking where you ship the app's runtime (Storybook, component-test harnesses, Vitest
  browser mode). The **same handlers** you wrote for Node tests (`setupServer`) work in the browser.
- **`page.route`** intercepts at the **Playwright driver**, *outside* the app's runtime, for full **E2E**
  runs against a deployed app. It doesn't need a Service Worker registered and works for any page.

Use MSW-worker when you own and ship the app's runtime in the test (component/dev); use `page.route` for
driver-level interception in an end-to-end Playwright run. They are not interchangeable.

## Stack

- Node 20 + TypeScript (strict) + Vitest (Jest is equivalent — the MSW surface is identical)
- [`msw`](https://www.npmjs.com/package/msw) 2.x — `http` / `graphql` handlers, `HttpResponse`,
  `setupServer` (`msw/node`) for Node tests, `setupWorker` (`msw/browser`) for the browser
- The **system under test is the app's own code** (a typed `fetch` client, `qa-api-client-writer-typescript`,
  or a React component) — MSW patches its runtime; **nothing is constructor-injected** in the Node case
  because there is no separate server URL (contrast WireMock and the Java/.NET sidecar ports)

```bash
npm install --save-dev msw
# Browser worker mode only — generate the Service Worker script into your public dir once:
npx msw init ./public --save
```

## The MSW model — handlers, server, lifecycle

A **handler** maps a request matcher to a **resolver** that returns a response. Handlers are registered
on a `server` (Node) or `worker` (browser). The Node lifecycle for every suite:

1. **Define handlers** — `http.get('/api/widgets/:id', resolver)`, `http.post(...)`.
2. **Create the server** — `const server = setupServer(...handlers)` (from `msw/node`).
3. **`server.listen({ onUnhandledRequest: 'error' })`** in `beforeAll` — start intercepting; fail loudly
   on any un-mocked request (the discipline that makes MSW tests honest — see below).
4. **Exercise** the app's code so it issues the request MSW intercepts.
5. **`server.resetHandlers()`** in `afterEach` — drop any per-test overrides so tests stay independent.
6. **`server.close()`** in `afterAll` — stop intercepting.

```typescript
// tests/support/handlers.ts — the default ("happy-path") handlers shared across the suite.
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/widgets/:id', ({ params }) => {
    return HttpResponse.json({ id: Number(params.id), name: 'Sprocket', priceMinor: 1999 });
  }),
];
```

```typescript
// tests/support/msw.server.ts — one server per process.
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
```

```typescript
// tests/support/msw.setup.ts — referenced from vitest `setupFiles`, or imported per spec.
import { beforeAll, afterEach, afterAll } from 'vitest';
import { server } from './msw.server';

// onUnhandledRequest:'error' → any request without a handler throws, instead of hitting the network.
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());   // wipe per-test server.use(...) overrides → tests independent
afterAll(() => server.close());
```

> **No constructor-injected base URL in Node.** MSW patches the process's HTTP layer, so the app's client
> keeps its real relative/absolute URL and MSW intercepts it. (The sidecar Java/.NET ports *do* inject a
> base URL — there the Node mock is a separate server.)

## `onUnhandledRequest: 'error'` — the discipline that makes MSW honest

Set `onUnhandledRequest: 'error'` on `listen()`. Any request the app makes that **no handler matches**
**throws** instead of silently escaping to the real network. Without it, a typo'd path or a forgotten
handler lets the test hit a real (or dead) endpoint and pass or hang misleadingly. This is MSW's
equivalent of WireMock's explicit catch-all — but stricter and on by default-choice. Make every mocked
dependency explicit; an un-mocked call is a test bug, surfaced immediately.

```typescript
server.listen({
  onUnhandledRequest: 'error',          // throw on any un-mocked request — the honest default
  // 'warn' logs but allows; 'bypass' silently allows — avoid both in CI.
});
```

## Core pattern — render/exercise, assert outcome, (optionally) verify the call

The SUT is the app's own code. The test relies on the shared handlers (or overrides one), drives the
code, and asserts the **outcome** (one logical assertion). Because MSW has no request journal, verifying
*that the call happened* uses the events API (next section) — but most app-level tests assert on the
resulting **state**, which is stronger.

```typescript
import { describe, it, expect } from 'vitest';
import './support/msw.setup';
import { WidgetApiClient } from '../src/clients/widget.client';

describe('widget lookup with MSW', () => {
  it('Should_return_the_widget_When_the_api_responds_200', async () => {
    const client = new WidgetApiClient();          // the app's own client — no injected mock URL
    const widget = await client.getWidget(42);     // MSW intercepts the in-process fetch
    expect(widget).toEqual({ id: 42, name: 'Sprocket', priceMinor: 1999 });
  });
});
```

## Per-test overrides — `server.use(...)`

`server.use(...handlers)` **prepends** handlers for the current test, taking priority over the defaults —
the MSW analogue of a per-test WireMock stub. `afterEach(() => server.resetHandlers())` drops them so the
next test is back to the shared baseline. This is how one test exercises an error path without touching
the others.

```typescript
import { http, HttpResponse } from 'msw';
import { server } from './support/msw.server';

it('Should_surface_a_friendly_error_When_the_api_returns_500', async () => {
  server.use(
    http.get('/api/widgets/:id', () =>
      HttpResponse.json({ message: 'upstream down' }, { status: 500 }),
    ),
  );

  await expect(new WidgetApiClient().getWidget(42)).rejects.toThrow(/upstream/);
});
// afterEach resetHandlers() removes this override automatically.
```

## Request matching — which requests a handler answers

Match on path (with params), query, method, headers, and body. Read the request inside the resolver via
the `{ request, params }` argument; `await request.json()` to branch on the payload.

```typescript
http.post('/api/orders', async ({ request }) => {
  const body = (await request.json()) as { sku: string; qty: number };
  if (body.qty <= 0) return HttpResponse.json({ message: 'qty must be > 0' }, { status: 422 });
  return HttpResponse.json({ orderId: 'ord-7' }, { status: 201 });
});
```

| Match on | How |
|----------|-----|
| Path param | `http.get('/api/widgets/:id', ({ params }) => ...)` — `params.id` |
| Query | `const url = new URL(request.url); url.searchParams.get('dryRun')` |
| Method | the `http.<method>` you choose (`get`/`post`/`put`/`delete`/`patch`) |
| Header | `request.headers.get('authorization')` |
| Body (JSON) | `await request.json()` then branch |
| GraphQL op | `graphql.query('GetWidget', resolver)` / `graphql.mutation('AddWidget', ...)` |

A wildcard handler (`http.get('*/api/widgets/:id', ...)` or `http.all('*', ...)`) catches a family of
URLs — but prefer the narrowest matcher per test and let `onUnhandledRequest:'error'` catch the rest.

## Response — status, headers, dynamic, one-time, passthrough, network error

```typescript
// JSON with status + headers.
HttpResponse.json({ id: 42 }, { status: 200, headers: { 'Cache-Control': 'no-cache' } });
// Plain text / empty.
HttpResponse.text('pong');
new HttpResponse(null, { status: 204 });
```

**Dynamic responses** derive the body from the request — MSW's equivalent of WireMock's Handlebars
templating, but it's just code:

```typescript
http.get('/api/widgets/:id', ({ params }) =>
  HttpResponse.json({ id: Number(params.id), name: 'generated' }),
);
```

**One-time handlers** (`{ once: true }`) match a single request then fall through to the next matching
handler — the building block for staged responses:

```typescript
server.use(
  http.get('/api/health', () => new HttpResponse(null, { status: 503 }), { once: true }), // first call 503
  http.get('/api/health', () => HttpResponse.json({ status: 'UP' })),                       // then UP
);
```

**`passthrough()`** lets a specific request reach the real network (selective, deliberate — not the
escape hatch `onUnhandledRequest:'bypass'`):

```typescript
import { http, passthrough } from 'msw';
http.get('/api/feature-flags', () => passthrough());   // let this one hit the real service
```

**Network-error simulation** — `HttpResponse.error()` rejects the request as a transport failure (DNS /
connection refused), to exercise the client's error path. Cross-link the fault-injection framing of
`qa-network-monitoring-proxy-typescript` (the proxy injects faults on a *real* service; MSW injects them
as the in-runtime mock). Assert on the SUT's **visible outcome** (a thrown error, a fallback, a retry) —
never sleep-then-check.

```typescript
http.get('/api/flaky', () => HttpResponse.error());   // transport-level failure
```

## Stateful behavior — closure state (the Scenarios analogue)

MSW has no built-in state machine like WireMock Scenarios; you model staged responses with **closure /
in-memory state** in the resolver (or `{ once: true }` chains). Reset the state per test so tests stay
independent — typically via `server.resetHandlers()` plus re-registering fresh closure-bearing handlers,
or by resetting the variable in `afterEach`.

```typescript
it('Should_poll_until_the_order_is_DONE', async () => {
  let polls = 0;
  server.use(
    http.get('/api/orders/7/status', () => {
      polls += 1;
      return HttpResponse.json({ state: polls < 2 ? 'PENDING' : 'DONE' });  // PENDING then DONE
    }),
  );

  // Wait on the CONDITION (the DONE payload), never on a clock — no setTimeout/waitForTimeout.
  await expect
    .poll(async () => (await new OrderApiClient().getStatus(7)).state, { timeout: 5_000, interval: 100 })
    .toBe('DONE');
});
```

The MSW *response* is instantaneous; the **wait is a condition-poll** (`expect.poll`) on the client's
visible state, with a deadline — never `setTimeout`/`waitForTimeout`. (MSW also supports artificial delay
via `await delay(ms)` inside a resolver to *simulate* latency — that's a simulation knob, not a test wait,
exactly like WireMock's `responseDelay`.)

## Verification — the events API (MSW has no request journal)

**Unlike WireMock, MSW keeps no request journal you can query after the fact.** To assert *that* a call
happened (and with what), subscribe to the **life-cycle events** and collect them into an array. The key
events: `request:start` / `request:match` / `request:unhandled` / `request:end` receive
`{ request, requestId }`; `response:mocked` / `response:bypass` receive `{ request, requestId, response }`.

```typescript
// tests/support/recorder.ts — collect intercepted requests for assertion.
import type { SetupServerApi } from 'msw/node';

export function recordRequests(server: SetupServerApi) {
  const seen: { method: string; url: string; body?: unknown }[] = [];
  server.events.on('request:match', async ({ request }) => {
    const clone = request.clone();
    const body = request.method !== 'GET' ? await clone.json().catch(() => undefined) : undefined;
    seen.push({ method: request.method, url: request.url, body });
  });
  return seen;
}
```

```typescript
it('Should_POST_the_order_exactly_once_with_the_right_body', async () => {
  const seen = recordRequests(server);

  await new OrderApiClient().submit({ sku: 'SPR-1', qty: 3 });

  const posts = seen.filter((r) => r.method === 'POST' && r.url.endsWith('/api/orders'));
  expect(posts).toHaveLength(1);
  expect(posts[0].body).toMatchObject({ sku: 'SPR-1', qty: 3 });
});
```

Call `server.events.removeAllListeners()` in `afterEach` (alongside `resetHandlers()`) so recorders don't
leak across tests. **Prefer asserting on the app's resulting state** (rendered DOM, store, returned value)
when you can — it's a stronger assertion than "the call was made"; reach for events when the call itself
is the contract (idempotency key, analytics beacon, exact payload).

## Browser mode — `setupWorker`

The **same handlers** drive the browser via a Service Worker. Use this for component tests / dev-time
mocking where you ship the app's runtime (Storybook, Vitest browser mode, a component harness):

```typescript
// src/mocks/browser.ts
import { setupWorker } from 'msw/browser';
import { handlers } from '../../tests/support/handlers';   // the SAME handlers as Node

export const worker = setupWorker(...handlers);
```

```typescript
// start it where your component/dev runtime boots:
await worker.start({ onUnhandledRequest: 'error' });
// override per scenario with worker.use(...); reset with worker.resetHandlers().
```

`npx msw init ./public --save` generates the `mockServiceWorker.js` the browser registers. The worker is
the right tool when your test renders the app's own runtime; for **driver-level** interception in a full
Playwright E2E run, use `page.route` (`qa-network-monitoring-playwright-routes-typescript`, #8) — see the
careful line in the decision matrix.

## Run modes — in-runtime (default) vs the Node sidecar (for Java/.NET)

| Mode | How | When |
|------|-----|------|
| **In-runtime — Node** (default) | `setupServer(...handlers)` patches `http`/`https`/`fetch` in-process | Vitest/Jest unit, component, integration — the app's own client |
| **In-runtime — browser** | `setupWorker(...handlers)` via a Service Worker | Component tests / dev-time mocking shipping the app's runtime |
| **Standalone Node sidecar** | `createServer(...handlers).listen(port)` (`@mswjs/http-middleware`) | When a **non-Node** SUT must hit the mock over HTTP — the basis of the **Java/.NET ports** |

The sidecar exists so the JVM/.NET stacks can reuse MSW handlers: `@mswjs/http-middleware`'s
`createServer(...handlers)` wraps the handlers in an Express server you start as a separate process (or a
Testcontainers Node image), and the .NET/JVM SUT's **constructor-injected** typed client points at its
base URL. See `qa-api-mocking-msw-java` / `qa-api-mocking-msw-dotnet`.

## Anti-patterns

- **`onUnhandledRequest: 'bypass'` (or omitting it).** Un-mocked requests silently hit the real network;
  tests pass against the wrong target or hang. *Fix:* `onUnhandledRequest: 'error'` — un-mocked = bug.
- **`setTimeout`/`waitForTimeout` to wait for a staged/async flow.** Races the resolver. *Fix:* closure
  state or `{ once: true }` chains for staged responses + `expect.poll(...)` on the client's visible
  state. Use `await delay(ms)` in a resolver only to *simulate* latency.
- **Forgetting `resetHandlers()` (and `removeAllListeners()`).** Per-test `server.use(...)` overrides and
  event recorders leak; order starts to matter. *Fix:* both in `afterEach`.
- **Asserting only the rendered outcome when the call itself is the contract.** Misses a wrong
  payload/header on a fire-and-forget POST. *Fix:* record via `server.events.on('request:match', ...)` and
  assert body/headers/count.
- **Reaching for MSW to fake a separate downstream service a non-app SUT talks to.** That's a server's
  job. *Fix:* **WireMock** (`qa-api-mocking-wiremock-typescript`) — a real server you point a client at.
- **Using MSW-worker for a full E2E run against a deployed app.** The Service Worker needs the app's own
  runtime. *Fix:* `page.route` (`qa-network-monitoring-playwright-routes-typescript`) at the driver layer.
- **Expecting a `verify`-style request journal.** MSW has none. *Fix:* the `server.events` listener API.

## Examples

**End-to-end: a component test that overrides a handler to an error, asserting the UI's fallback.**

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import './support/msw.setup';
import { server } from './support/msw.server';
import { WidgetPanel } from '../src/components/WidgetPanel';

describe('WidgetPanel with MSW', () => {
  it('Should_render_the_widget_When_the_api_responds_200', async () => {
    render(<WidgetPanel id={42} />);                                 // uses the shared happy-path handler
    expect(await screen.findByText('Sprocket')).toBeInTheDocument(); // one logical assertion: the outcome
  });

  it('Should_show_a_retry_prompt_When_the_api_is_down', async () => {
    server.use(
      http.get('/api/widgets/:id', () =>
        HttpResponse.json({ message: 'down' }, { status: 503 }),     // per-test override
      ),
    );
    render(<WidgetPanel id={42} />);
    expect(await screen.findByRole('button', { name: /retry/i })).toBeInTheDocument();
  });
});
```

Lifecycle for this test: `beforeAll` starts MSW with `onUnhandledRequest:'error'`; the first test uses the
shared handler; the second overrides it with `server.use(...)`; `afterEach(resetHandlers())` drops the
override so the suite stays independent.

**Test-data builder for handler/response payloads (4+ fields → builder, per the global rules).**

```typescript
export const widgetResponseMother = {
  standard: () =>
    new WidgetResponseBuilder()
      .withId(42).withName('Sprocket').withPriceMinor(1999).withCurrency('EUR').build(),
};

http.get('/api/widgets/:id', () => HttpResponse.json(widgetResponseMother.standard()));
```

## Rules (hard constraints)

- MSW intercepts the app's **own** HTTP **in-runtime** — there's no separate server URL in the Node case;
  don't inject a base URL (that's the sidecar Java/.NET ports). Reach for MSW for app/component-level tests.
- Always `server.listen({ onUnhandledRequest: 'error' })` — an un-mocked request is a test bug.
- One server per process; `resetHandlers()` **and** `removeAllListeners()` in `afterEach` — keep tests
  independent. `close()` in `afterAll`.
- Per-test error/edge paths via `server.use(...)`; staged responses via closure state or `{ once: true }`.
- **No `setTimeout`/`waitForTimeout`.** `expect.poll(...)` on the client's visible state; `delay(ms)` only
  to *simulate* latency.
- Verify via `server.events.on('request:match'|'response:mocked', ...)` (MSW has **no journal**); prefer
  asserting the app's resulting state when you can.
- The **same handlers** drive `setupServer` (Node) and `setupWorker` (browser) — share them.
- Builders/ObjectMother for handler & response payloads with 4+ fields; test names `Should_X_When_Y`;
  `strict: true`; no secrets in handlers.
- Prefer **WireMock** for a standalone server a non-app SUT points at; prefer `page.route` for E2E
  driver-level interception — use MSW for the app's own in-runtime `fetch`/XHR.

## Cross-references

- `qa-api-mocking-msw-java` — the **Java sidecar port**: MSW can't intercept in the JVM, so it runs as a
  standalone Node sidecar (`@mswjs/http-middleware` `createServer`) the JVM SUT points at. Structure
  ported from here; the *interception model* does not survive the port (it becomes a server).
- `qa-api-mocking-msw-dotnet` — the **.NET sidecar port**, same shape (Node sidecar + injected base URL,
  NUnit).
- `qa-api-mocking-wiremock-typescript` (#22) — the **key contrast**: WireMock is a **standalone HTTP
  server you point a client at** (it owns the wire); MSW intercepts **in the app's own runtime**. Reach
  for WireMock when the SUT is a service/native client + you want a real server & scenarios; MSW for
  app-level `fetch`/XHR. Plus Mountebank (#24) and Prism (#25) in the family.
- `qa-network-monitoring-playwright-routes-typescript` (#8) — `page.route` is *also* in-browser
  interception, but at the **Playwright driver** for E2E (outside the app's runtime); MSW-worker is at the
  **Service Worker** in the app's runtime (component/dev). Draw the line by test shape.
- `qa-network-monitoring-proxy-typescript` (#10) — `mockttp` out-of-browser MITM on a *real* service's
  traffic; MSW replaces it in-runtime. Mirror its fault-injection framing (`HttpResponse.error()`).
- `qa-api-client-writer-typescript` + `qa-api-test-author-generator-typescript` — the app's typed `fetch`
  client / API tests whose in-process requests MSW intercepts.
- `qa-test-environments-typescript` + `qa-db-testing-testcontainers-typescript` — the Node-sidecar run
  mode (process or Testcontainers Node image) the Java/.NET ports rely on.
- `qa-ci-pipelines-github-actions-typescript` — runs these tests; Node-only, no Docker needed for the
  in-runtime mode (the sidecar ports do need Node available in the job).
