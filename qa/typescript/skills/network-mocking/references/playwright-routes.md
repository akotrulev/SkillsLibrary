# QA — Playwright Routing, Mocking and Traffic Assertions (TypeScript / Playwright 1.64)

Intercepts, mocks, asserts and shapes HTTP traffic in `@playwright/test`. Built on the fixture model of
`qa/typescript/skills/ui-test-author/playwright`: interception and traffic checks are **fixtures with intent
names** (`mockApi.stubOrders([...])`, `traffic.requestedUrls(...)`), never `page.route(...)` in a spec. Every
wait is a request/response predicate or a user-visible signal; there is no `waitForTimeout`. The version in
brackets is where an API first shipped.

## When to use

- A backend or third-party response must be deterministic: canned JSON, a forced `500` or `403`.
- A test asserts an endpoint was called — or was **not** — with the expected method and payload.
- A real response is modified in flight to reach an edge case.
- A third-party dependency is replayed from a committed HAR.
- Offline or a slow endpoint, to test loading and error states.
- The app shell's security headers or TLS details are checked.
- Noisy traffic (analytics) is blocked to stabilize a suite.

## When NOT to use

- Real bandwidth throttling, cache disable, CPU throttling, performance metrics → `references/cdp.md`
- A client with no Playwright `page` (Selenium, Appium, native) → `references/proxy.md`
- WebSocket or SSE streams → `qa/typescript/skills/realtime-stream-testing`
- Recording a HAR as evidence → `qa/typescript/skills/evidence-capture` (`references/playwright.md` §5)
- Page objects and specs themselves → `qa/typescript/skills/ui-test-author/playwright`
- Java and .NET → `qa-java:network-mocking`, `qa-dotnet:network-mocking`

## Inputs needed

1. **Which traffic** — the endpoint as a glob, RegExp or URLPattern; first-party or third-party.
2. **Intent** — mock, assert called, assert not called, modify, replay a HAR, offline or latency, headers.
3. **Scope** — one page (`page.route`) or every page in the context, popups included (`context.route`).

## Decision matrix

| Goal | API | Notes |
|---|---|---|
| Canned data, never hit the network | `route.fulfill({ json })` | Sets `content-type` and serializes |
| Force an error status | `route.fulfill({ status: 500, json })` | The error path becomes deterministic |
| Block a resource | `route.abort('blockedbyclient')` | Analytics, fonts, images |
| Pass it through unchanged | `route.continue()` | Goes to the network and **skips** the remaining handlers |
| Let an earlier-registered handler run | `route.fallback()` | Chains instead of going to the network |
| Modify a real response | `await route.fetch()`, then `route.fulfill({ response, json })` | Keeps the original status and headers |
| Change the outgoing request | `route.continue({ headers, postData, url, method })` | The `Cookie` header cannot be overridden [1.52] — use `context.addCookies` |
| Assert a call happened | `page.waitForRequest(url)` / `waitForResponse(url)` started **before** the action | Fails on timeout |
| Assert a call did **not** happen | `page.requests()` [1.56] after a completion signal | A buffer of the page's most recent requests |
| No uncaught errors or console errors | `page.pageErrors()` / `page.consoleMessages()` [1.56] | Same buffers; `filter` option [1.59] |
| Security headers, TLS | `response.allHeaders()`, `response.securityDetails()` | Routing layer, every browser — no CDP needed |
| Deterministic third party | `routeFromHAR(har, { url, notFound: 'abort' })` | Update with `update: true` |
| Offline | `context.setOffline(true)` | Cross-browser |
| A slow endpoint | A delay inside the handler, then `route.continue()` | Real throughput → `references/cdp.md` |

## 1. The fixtures

`network.fixtures.ts` extends the writer's `fixtures.ts`. Mocks live in `MockApi`; traffic reads live in
`Traffic`. Both take the test's `page`.

```typescript
import type { Page, Request, Response } from '@playwright/test';
import { test as base } from './fixtures';
import { CartPage } from './CartPage';
import { OrdersPage } from './OrdersPage';

export type Order = { readonly id: string; readonly totalMinor: number; readonly currency: string };
export type FeatureFlags = { readonly betaCheckout: boolean; readonly newPricing: boolean };

const updatePaymentsHar = process.env.HAR_UPDATE === '1';

export class MockApi {
  constructor(private readonly page: Page) {}

  async stubOrders(orders: readonly Order[]): Promise<void> {
    await this.page.route('**/api/orders', (route) => route.fulfill({ json: orders }));
  }

  async failOrdersWith(status: number): Promise<void> {
    await this.page.route('**/api/orders', (route) => route.fulfill({ status, json: { error: 'simulated' } }));
  }

  async blockAnalytics(): Promise<void> {
    await this.page.route(/google-analytics\.com|segment\.io/, (route) => route.abort('blockedbyclient'));
  }

  async enableFlag(flag: keyof FeatureFlags): Promise<void> {
    await this.page.route('**/api/feature-flags', async (route) => {
      const response = await route.fetch();
      const flags: FeatureFlags = await response.json();
      await route.fulfill({ response, json: { ...flags, [flag]: true } });
    });
  }

  async tagTenant(tenant: string): Promise<void> {
    await this.page.route('**/api/**', (route) =>
      route.continue({ headers: { ...route.request().headers(), 'x-test-tenant': tenant } }),
    );
  }

  async delay(url: string, ms: number): Promise<void> {
    await this.page.route(url, async (route) => {
      await new Promise((resolve) => setTimeout(resolve, ms));
      await route.continue();
    });
  }

  async stubOrdersInEveryPage(orders: readonly Order[]): Promise<void> {
    await this.page.context().route('**/api/orders', (route) => route.fulfill({ json: orders }));
  }

  async replayPayments(): Promise<void> {
    await this.page.routeFromHAR('tests/fixtures/har/payments.har', {
      url: 'https://api.stripe.com/**',
      notFound: 'abort',
      update: updatePaymentsHar,
      updateContent: 'attach',
      updateMode: 'minimal',
    });
  }

  async goOffline(): Promise<void> {
    await this.page.context().setOffline(true);
  }
}

export class Traffic {
  constructor(private readonly page: Page) {}

  nextRequest(url: string | RegExp): Promise<Request> {
    return this.page.waitForRequest(url);
  }

  nextResponse(url: string | RegExp): Promise<Response> {
    return this.page.waitForResponse(url);
  }

  async requestedUrls(pattern: RegExp): Promise<string[]> {
    const requests = await this.page.requests();
    return requests.map((request) => request.url()).filter((url) => pattern.test(url));
  }

  async consoleErrors(): Promise<string[]> {
    const messages = await this.page.consoleMessages();
    return messages.filter((message) => message.type() === 'error').map((message) => message.text());
  }

  async pageErrors(): Promise<string[]> {
    const errors = await this.page.pageErrors();
    return errors.map((error) => error.message);
  }
}

type NetworkFixtures = {
  mockApi: MockApi;
  traffic: Traffic;
  cartPage: CartPage;
  ordersPage: OrdersPage;
};

export const test = base.extend<NetworkFixtures>({
  mockApi: async ({ page }, use) => {
    await use(new MockApi(page));
  },
  traffic: async ({ page }, use) => {
    await use(new Traffic(page));
  },
  cartPage: async ({ page }, use) => {
    await use(new CartPage(page));
  },
  ordersPage: async ({ page }, use) => {
    await use(new OrdersPage(page));
  },
});

export { expect } from './fixtures';
```

- Every handler returns or awaits its `fulfill` / `abort` / `continue` / `fallback` — a floating
  `route.continue()` is a promise nobody waits for.
- Payload types (`Order`, `FeatureFlags`) come from the project's builders
  (`qa/typescript/skills/test-data-builder`); a large payload is served from a file with
  `route.fulfill({ path })`, never a giant inline literal.
- `delay` holds the one sanctioned `setTimeout` in this skill: a *simulated* slow response, inside a
  handler, never a wait-and-hope.

## 2. Mocking a response

```typescript
import { expect, test } from './network.fixtures';

test('Should_ShowEmptyState_When_ThereAreNoOrders', async ({ mockApi, ordersPage }) => {
  await mockApi.stubOrders([]);

  await ordersPage.open();

  await expect(ordersPage.emptyState).toBeVisible();
});

test('Should_ShowErrorBanner_When_OrdersApiFails', async ({ mockApi, ordersPage }) => {
  await mockApi.failOrdersWith(500);

  await ordersPage.open();

  await expect(ordersPage.errorBanner).toHaveText('We could not load your orders');
});
```

Register the route **before** the navigation or action that fires the request; a route added afterwards
never sees it.

## 3. Asserting a call — method and typed payload

```typescript
type CheckoutRequest = { readonly totalMinor: number; readonly currency: string };

test('Should_PostCartTotal_When_UserPlacesOrder', async ({ cartPage, traffic }) => {
  await cartPage.open();
  const checkout = traffic.nextRequest('**/api/checkout');

  await cartPage.placeOrder();

  const request = await checkout;
  const expected: CheckoutRequest = { totalMinor: 15_000, currency: 'EUR' };
  expect(request.method(), 'checkout method').toBe('POST');
  expect(request.postDataJSON(), 'checkout payload').toEqual(expected);
});
```

Start the wait, act, then await it. Awaiting first hangs; starting it after the action races the request.
Pass the glob, RegExp or URLPattern straight to `waitForRequest` — never a hand-rolled substring match.

## 4. Asserting a call did NOT happen, and that the page logged no errors

```typescript
test('Should_NotCallLegacyPricing_When_CartIsRecalculated', async ({ cartPage, traffic }) => {
  await cartPage.open();

  await cartPage.recalculate();

  expect(await traffic.requestedUrls(/\/api\/legacy-pricing/), 'legacy pricing calls').toEqual([]);
});

test('Should_RaiseNoPageErrors_When_CartOpens', async ({ cartPage, traffic }) => {
  await cartPage.open();

  expect(await traffic.pageErrors(), 'uncaught errors on the cart page').toEqual([]);
});
```

- `recalculate()` returns once the new total is visible. The list is read **after** that signal, or the
  check passes only because the request had not fired yet.
- `page.requests()`, `page.consoleMessages()` and `page.pageErrors()` [1.56] return the page's most
  recent buffered items — no listener to register and no array to manage. The buffer is capped, so for a
  long flow that fires hundreds of requests, collect with `page.on('request', …)` in a fixture instead.
  `filter` [1.59] narrows which buffered items are returned, and `clearConsoleMessages()` /
  `clearPageErrors()` [1.59] reset them.
- Each page has its own buffer: a popup's traffic is read from the popup.

## 5. Security headers and TLS — at the routing layer

```typescript
test('Should_SendSecurityHeaders_When_AppShellLoads', async ({ homePage, traffic }) => {
  const shell = traffic.nextResponse('/');

  await homePage.goto();

  const headers = await (await shell).allHeaders();
  expect(Object.keys(headers), 'security headers on the app shell').toEqual(
    expect.arrayContaining(['content-security-policy', 'strict-transport-security', 'x-frame-options']),
  );
});

test('Should_NegotiateTls13_When_AppShellLoads', async ({ homePage, traffic }) => {
  const shell = traffic.nextResponse('/');

  await homePage.goto();

  const details = await (await shell).securityDetails();
  expect(details?.protocol, 'TLS protocol of the app shell').toBe('TLS 1.3');
});
```

- `allHeaders()` returns every response header with **lower-cased** names, including the ones
  `headers()` omits; `headerValue(name)` reads one case-insensitively.
- `securityDetails()` returns `{ protocol, issuer, subjectName, validFrom, validTo }`, or `null` over plain
  HTTP — so the TLS test fails loudly against an HTTP environment.
- `'/'` is resolved against `baseURL`, so it matches the document exactly. Both checks are
  cross-browser; CDP is not needed for either.

## 6. Modifying traffic in flight

- **The response:** `mockApi.enableFlag('betaCheckout')` fetches the real flags and re-serves them with one
  flag forced. Passing `response` keeps the original status and headers.
- **The request:** `mockApi.tagTenant('tenant-42')` adds a header. A `Cookie` header set through
  `route.continue` is ignored since 1.52; add the cookie with `context.addCookies` in a fixture.

## 7. HAR replay and update

Replay a committed HAR on every run, and update it on purpose:

- `mockApi.replayPayments()` serves `https://api.stripe.com/**` from the HAR. `notFound: 'abort'` turns any
  request the HAR does not hold into a failure, so a new dependency cannot slip through to the live service.
- **Updating** is a deliberate, local run against the real dependency:
  `HAR_UPDATE=1 npx playwright test payments.spec.ts`. With `update: true`, the requests reach the network
  and the HAR is written when the context closes. Commit it in a dedicated PR; never update in CI.
- The `routeFromHAR` options are `updateContent: 'embed' | 'attach'` [1.32] (`attach` stores bodies as
  separate files: reviewable diffs) and `updateMode: 'full' | 'minimal'` [1.32] (`minimal` keeps only what
  replay needs). `content` and `mode` are the names of the **recording** options (`recordHar`,
  `tracing.startHar`) — a different API.
- Recording a HAR of a whole test as evidence — `context.tracing.startHar()` [1.60] in a fixture, or
  `use: { contextOptions: { recordHar: { path } } }` — is `qa/typescript/skills/evidence-capture`.
  `recordHar` is a context option, never a `test.use` key.
- Scrub tokens, cookies and personal data from a committed HAR; record against disposable test accounts.

## 8. Offline and latency

```typescript
test('Should_ShowOfflineBanner_When_NetworkDrops', async ({ mockApi, ordersPage }) => {
  await ordersPage.open();

  await mockApi.goOffline();
  await ordersPage.refresh();

  await expect(ordersPage.offlineBanner).toHaveText('You are offline');
});

test('Should_KeepSpinnerVisible_When_OrdersRespondSlowly', async ({ mockApi, ordersPage }) => {
  await mockApi.delay('**/api/orders', 1_500);

  await ordersPage.open();

  await expect(ordersPage.spinner).toBeVisible();
});
```

`delay` slows one endpoint. Real bandwidth and latency emulation is CDP's
`Network.emulateNetworkConditions`, Chromium-only, in `references/cdp.md`.

## Rules

### Matching

- A URL matcher is a **glob** (`*` matches any character except `/`; `**` spans `/`; `{a,b}` alternates), a
  **RegExp**, a `(url: URL) => boolean` predicate, or a **URLPattern** — the last is in the Node API docs
  since 1.59 and needs the `URLPattern` global (Node 24) and its type in the project's TypeScript `lib`:
  `page.route(new URLPattern({ pathname: '/api/orders/:id' }), …)`.
- **Glob `?` and `[]` were removed in 1.52.** Use a RegExp for single-character or character-class matches.
- **`baseURL`:** a string that does not start with `*` is resolved against `baseURL`; one starting with `*`
  or `**` is a raw glob. Write `'**/api/orders'`, never `'/api/orders'` expecting a glob.

### Handlers

- A handler calls exactly one of `fulfill` / `abort` / `continue` / `fallback`, and awaits or returns it.
  None hangs the request; two throws.
- **The last registered handler runs first.** `route.fallback()` defers to an earlier one;
  `route.continue()` goes straight to the network and skips the others.
- `route.fulfill({ json })` over `{ body: JSON.stringify(...), contentType }`.
- A handler sees only the **first** URL of a redirect chain; assert on the final response.
- Re-routing the same URL inside one test uses `page.unroute` / `page.unrouteAll({ behavior: 'wait' })`;
  otherwise the route lives for the test's page.

### Scope

- `page.route` covers one page and does **not** see a popup's first request. A flow that opens a popup — a
  payment window, an OAuth sign-in — routes with `context.route` (`mockApi.stubOrdersInEveryPage`).
- Mock at the narrowest scope that works; a context route reaches every page in the context.
- Since 1.57, Chromium reports service-worker requests through context routing. If a service worker still
  answers before your route, set `serviceWorkers: 'block'` for that project.

### Assertions and waits

- Start the wait before the action; read buffers after a user-visible completion signal.
- Read payloads with `request.postDataJSON()` into a typed value, and `await response.json()`; never
  re-parse `postData()` by hand.
- One expected value per assertion: `toBe(200)`, never "2xx".
- No `waitForTimeout`. The only `setTimeout` is inside `MockApi.delay`.

## What NOT to do

- `page.route(...)` in a spec body — wrap it in a fixture method with an intent name.
- `route.continue()` neither awaited nor returned.
- `(json: any)` or a glob turned into a substring with `replace(/\*/g, '')`.
- `route.continue()` where `route.fallback()` was meant.
- `'/api/orders'` expecting glob behaviour; glob `?` / `[abc]`.
- "Not called" checked after a sleep, or before the completion signal.
- `test.use({ recordHar })` — it is not a test option.
- `content: 'attach'` passed to `routeFromHAR` — its option is `updateContent`.
- `update: true` left on, or a HAR re-recorded in CI.
- `notFound: 'fallback'` on a replay meant to be hermetic.
- `page.route` for a popup's traffic.
- `routeWebSocket` here, or `route.fulfill` standing in for an SSE stream — that is
  `qa/typescript/skills/realtime-stream-testing`.
- Secrets or personal data in a mock response or a committed HAR.

## Generation steps

1. Confirm the traffic, the intent and the scope.
2. Add one intent-named method per scenario to `MockApi` or `Traffic` in `network.fixtures.ts`.
3. Write the spec through the page-object fixtures; register mocks before the action; start waits before
   it; read buffers after the completion signal.
4. For a third party, record the HAR once with `HAR_UPDATE=1`, commit it, replay with `notFound: 'abort'`.
5. Run `npx playwright test` and `tsc --noEmit`; the trace's Network tab shows which requests were routed.
   Inside a plan task marked `Gate: none`, run none of this and report the files as written, not run.

## Cross-references

- `qa/typescript/skills/ui-test-author/playwright` — the fixtures and page objects these extend; the
  listener-before-action rule.
- `references/cdp.md` — real throttling, cache, CPU and metrics below the routing layer.
- `references/proxy.md` — clients with no Playwright `page`.
- `qa/typescript/skills/realtime-stream-testing` — WebSocket (`routeWebSocket`) and SSE.
- `qa/typescript/skills/evidence-capture` — HAR recording and failure evidence.
- `qa/typescript/skills/test-data-builder` — the payload shapes.
- `qa/typescript/skills/api-test-author/writer` — when no browser is needed.
- `qa/cicd/typescript/skills/ci-pipelines` — runs these specs and uploads the evidence.
