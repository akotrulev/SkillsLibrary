---
name: qa-network-monitoring-playwright-routes-typescript
description: Use when the user asks to intercept, mock, assert, or shape HTTP traffic in Playwright TypeScript tests — `page.route` / `context.route` handlers (`route.fulfill` / `abort` / `continue` / `fallback` / `fetch`), request assertions (was endpoint X called, with what method/payload/headers) via `page.waitForRequest` / `page.waitForResponse`, stubbing JSON responses and error codes, modify-in-flight, HAR record-then-replay (`recordHar` + `routeFromHAR`), offline mode (`context.setOffline`), and latency/network-condition simulation. Triggers: "mock the /api/orders response in our Playwright test", "assert the checkout endpoint was called with this payload", "stub a 500 from the payments API", "record a HAR and replay it offline", "intercept network requests in Playwright TS", "force the app offline mid-test". Do NOT use for Playwright .NET network interception (use `qa/dotnet/skills/network-monitoring/playwright-routes`), Playwright Java (use `qa/java/skills/network-monitoring/playwright-routes`), raw CDP scripting (use `qa/typescript/skills/network-monitoring/cdp`), writing the page objects / specs themselves (use `qa/typescript/skills/ui-test-author/playwright`), or API-only contract tests with no browser (use `qa/typescript/skills/api-test-author/generator`).
---

# QA — Playwright Network Monitoring & Interception (TypeScript)

Intercepts, mocks, asserts, and shapes HTTP traffic in Playwright `@playwright/test` tests using TypeScript. Built on the **fixture-driven** model from `qa/typescript/skills/ui-test-author/playwright`: route handlers and request-assertion helpers are exposed as Playwright **fixtures** with intent-revealing names — never raw `page.route(...)` scattered across spec bodies. Every wait is conditional on a request/response predicate; there is **no `waitForTimeout`** anywhere in this skill.

## Stack

- Node 20 + TypeScript (strict mode)
- `@playwright/test` (Playwright ≥ 1.48 — `routeWebSocket`, the post-1.43 glob semantics, `routeFromHAR` update modes)
- Network helpers under `tests/fixtures/network/`, HAR archives under `tests/fixtures/har/`
- Page objects under `tests/pages/`, specs under `tests/specs/` (see the UI sibling)
- These tests run sharded in CI under `qa/typescript/skills/ci-pipelines/github-actions` (`--shard`, `blob` reporter, traces on failure)

## When to use

- Mocking a backend or third-party response so a UI test is deterministic (stub JSON, force a `500`/`403`)
- **Asserting** an endpoint was (or was not) called, with the expected method / payload / headers
- Modifying a real response in flight (inject a flag, corrupt one field) to exercise an edge case
- Recording a HAR of a flaky third-party dependency, then replaying it offline for determinism
- Simulating offline / slow-network conditions to test loading and error states
- Blocking noisy resources (analytics, fonts, images) to speed up or stabilize a suite

## When NOT to use

- Playwright .NET / Java interception → `qa/{dotnet,java}/skills/network-monitoring/playwright-routes`
- Low-level CDP (`Network.*`, real bandwidth throttling, protocol tracing) → `qa/typescript/skills/network-monitoring/cdp`
- An HTTP proxy in front of the browser (mitmproxy, system-level capture) → `qa/typescript/skills/network-monitoring/proxy`
- Writing the page objects / specs themselves → `qa/typescript/skills/ui-test-author/playwright`
- Pure API contract/integration tests with no browser → `qa/typescript/skills/api-test-author/generator`

## Inputs needed

Ask at most 3 questions; infer the rest from `playwright.config.ts` and existing specs.

1. **What traffic** — exact endpoint(s) or URL glob/regex (`**/api/orders/**`), and is it first-party or a third-party dependency?
2. **Intent** — mock a response, assert a call happened, modify in flight, replay a HAR, or simulate offline/latency?
3. **Scope** — one page (`page.route`) or every page in the context including popups (`context.route`)?

## Decision matrix

| Goal | Tool | Notes |
|---|---|---|
| Return canned data, never hit the network | `route.fulfill({ json })` | `json` sets `content-type: application/json` and serializes for you |
| Force an error status | `route.fulfill({ status: 500, json: {...} })` | The app's error path is now deterministic |
| Block a resource (analytics, images) | `route.abort()` | `abort('blockedbyclient')` to be explicit |
| Let it through unchanged | `route.continue()` | Goes straight to network; **skips** remaining handlers |
| Let an **earlier-registered** handler also run | `route.fallback()` | Chains to the next matching handler instead of the network |
| Modify a real response | `await route.fetch()` → mutate → `route.fulfill({ response, body/json })` | Preserves original status/headers unless you override |
| Tweak the outgoing request | `route.continue({ headers, postData, url, method })` | Header tampering, payload rewrite |
| Assert a call happened | `page.waitForRequest(pred)` / `page.waitForResponse(pred)` | Listener **before** the action; fails fast on timeout |
| Deterministic third-party dep | `page.routeFromHAR(har, { url, notFound: 'abort' })` | Record once with `update: true`, commit, replay |
| Whole-context offline | `context.setOffline(true)` | Cross-browser |
| Latency simulation | delay inside the handler, then `route.continue()` | No built-in `route` throttle; real bandwidth = CDP (Chromium-only) → `qa/typescript/skills/network-monitoring/cdp` |
| Mock a WebSocket | `page.routeWebSocket(url, ws => …)` | ≥ 1.48 |

## Patterns

### Route-mocking fixture — `tests/fixtures/network/mockApi.ts`

Expose interception as a fixture with intent-revealing methods. Specs call `mockApi.stubOrders([...])`, not `page.route('**/api/orders', ...)`.

```typescript
import { test as base, Page } from '@playwright/test';

export class MockApi {
  constructor(private readonly page: Page) {}

  /** Serve canned orders; the real backend is never hit. */
  async stubOrders(orders: unknown[]): Promise<void> {
    await this.page.route('**/api/orders', (route) =>
      route.fulfill({ json: orders }),
    );
  }

  /** Force the orders endpoint to fail so the UI's error path runs. */
  async failOrdersWith(status: number): Promise<void> {
    await this.page.route('**/api/orders', (route) =>
      route.fulfill({ status, json: { error: 'simulated failure' } }),
    );
  }

  /** Drop noisy third-party traffic to stabilize and speed up the run. */
  async blockAnalytics(): Promise<void> {
    await this.page.route(/google-analytics\.com|segment\.io/, (route) =>
      route.abort('blockedbyclient'),
    );
  }
}

type NetFixtures = { mockApi: MockApi };

export const test = base.extend<NetFixtures>({
  mockApi: async ({ page }, use) => {
    await use(new MockApi(page));
  },
});

export { expect } from '@playwright/test';
```

```typescript
// tests/specs/orders.spec.ts
import { test, expect } from '../fixtures/network/mockApi';

test('renders an empty state when there are no orders', async ({ page, mockApi }) => {
  await mockApi.stubOrders([]);
  await page.goto('/orders');

  await expect(page.getByTestId('orders-empty')).toBeVisible();
});

test('shows the error banner when the orders API fails', async ({ page, mockApi }) => {
  await mockApi.failOrdersWith(500);
  await page.goto('/orders');

  await expect(page.getByRole('alert')).toContainText(/couldn’t load orders/i);
});
```

Register routes **before** the navigation/action that triggers them — a route registered after the request has fired won't catch it.

### Request-assertion helper — fail fast on a missing/mismatched call

A call assertion uses the **listener-before-action** ordering: start the wait, then perform the action, then await. Awaiting before the action hangs; awaiting after races the request.

```typescript
// tests/fixtures/network/expectRequest.ts
import { Page, Request, expect } from '@playwright/test';

/**
 * Assert an outbound request matching `urlGlob` fires while `action` runs,
 * and (optionally) that its JSON payload matches. Fails fast on timeout.
 */
export async function expectRequest(
  page: Page,
  urlGlob: string | RegExp,
  action: () => Promise<void>,
  opts: { method?: string; bodyMatches?: (json: any) => boolean; timeout?: number } = {},
): Promise<Request> {
  const waitFor = page.waitForRequest(
    (req) =>
      (typeof urlGlob === 'string' ? req.url().includes(urlGlob.replace(/\*/g, '')) : urlGlob.test(req.url())) &&
      (!opts.method || req.method() === opts.method),
    { timeout: opts.timeout ?? 5_000 },
  );

  const [request] = await Promise.all([waitFor, action()]);

  if (opts.bodyMatches) {
    expect(opts.bodyMatches(request.postDataJSON()), 'request payload did not match').toBe(true);
  }
  return request;
}
```

```typescript
test('submits the checkout with the cart total', async ({ page }) => {
  await page.goto('/cart');

  await expectRequest(
    page,
    '**/api/checkout',
    () => page.getByRole('button', { name: 'Place order' }).click(),
    { method: 'POST', bodyMatches: (b) => b.totalMinor === 15_000 && b.currency === 'EUR' },
  );
});
```

Prefer a Playwright glob/regex over hand-rolled string matching where the matcher is the whole assertion — the helper above is for the common case where you also want to assert on the payload. For a plain "was it called", `page.waitForResponse('**/api/checkout')` inside a `Promise.all` is enough.

### Asserting an endpoint was **not** called

There is no negative `waitFor`. Collect matching requests over the window of the action, then assert the count.

```typescript
test('does not call the legacy pricing endpoint', async ({ page }) => {
  const calls: string[] = [];
  page.on('request', (req) => {
    if (req.url().includes('/api/legacy-pricing')) calls.push(req.url());
  });

  await page.goto('/cart');
  await page.getByRole('button', { name: 'Recalculate' }).click();
  await expect(page.getByTestId('cart-total')).toBeVisible(); // a real signal the flow finished

  expect(calls, 'legacy pricing endpoint should be retired').toHaveLength(0);
});
```

Gate the assertion on a **user-visible signal** that the flow completed (`toBeVisible` on the result), never on a fixed sleep — otherwise the negative check passes simply because the request hadn't fired yet.

### Modify a real response in flight

Fetch the live response, mutate the body, re-serve. Passing `response` keeps the original status and headers.

```typescript
await page.route('**/api/feature-flags', async (route) => {
  const response = await route.fetch();
  const flags = await response.json();
  flags.betaCheckout = true;            // force the variant under test
  await route.fulfill({ response, json: flags });
});
```

### Header / payload tampering on the outbound request

```typescript
await page.route('**/api/**', (route) => {
  const headers = { ...route.request().headers(), 'x-test-tenant': 'tenant-42' };
  route.continue({ headers });
});
```

### HAR record-then-replay for deterministic third-party deps

Record once against the live dependency, commit the archive, then replay offline on every run. Use `content: 'attach'` so bodies live as separate files (reviewable diffs, no giant JSON blobs).

```typescript
// One-off recording run — set update: true, then commit tests/fixtures/har/payments.har
await page.routeFromHAR('tests/fixtures/har/payments.har', {
  url: '**/api.stripe.com/**',
  update: true,
  updateMode: 'minimal',
  updateContent: 'attach',
});
```

```typescript
// Every CI run — replay. notFound: 'abort' makes any un-recorded call a hard failure
// (so a new dependency can't silently slip through to the real network).
test.beforeEach(async ({ page }) => {
  await page.routeFromHAR('tests/fixtures/har/payments.har', {
    url: '**/api.stripe.com/**',
    notFound: 'abort',
  });
});
```

`recordHar` as a `test.use({ recordHar: { path, mode: 'minimal', content: 'attach' } })` context option captures the **whole** context's traffic for debugging; `routeFromHAR` is the scoped record/replay you want for a specific dependency.

### Offline and latency simulation

```typescript
test('shows the offline banner when the network drops', async ({ page, context }) => {
  await page.goto('/dashboard');
  await expect(page.getByTestId('live-feed')).toBeVisible();

  await context.setOffline(true);
  await page.getByRole('button', { name: 'Refresh' }).click();

  await expect(page.getByRole('alert')).toContainText(/you’re offline/i);
});
```

Latency injection has **no built-in `route` throttle** — add a delay inside the handler. This is the one sanctioned `setTimeout` in this skill (it is a *simulated delay*, not a *wait-and-hope*), and it belongs in a fixture, not a spec:

```typescript
async function withLatency(page: Page, urlGlob: string, ms: number): Promise<void> {
  await page.route(urlGlob, async (route) => {
    await new Promise((r) => setTimeout(r, ms));
    await route.continue();
  });
}
// Test the loading spinner stays up while /api/orders is slow.
await withLatency(page, '**/api/orders', 1_500);
await page.goto('/orders');
await expect(page.getByTestId('orders-spinner')).toBeVisible();
```

For real bandwidth/latency emulation (not just per-request delay) use CDP `Network.emulateNetworkConditions` — Chromium-only — covered in `qa/typescript/skills/network-monitoring/cdp`.

## Rules

### Matching
- URL patterns are a **glob** (`*` = any char except `/`; `**` spans `/`; `{a,b}` alternation), a **RegExp**, or a `(url: URL) => boolean` predicate. Prefer a glob for path shape, a regex for ids/query specifics.
- **Glob `?` and `[]` (character classes) are not supported** since Playwright 1.43 — use a `RegExp` for those.
- **`baseURL` gotcha:** a string pattern that does **not** start with `*` is resolved against `baseURL` via `new URL(pattern, baseURL)`; a pattern starting with `*`/`**` is treated as a raw glob and is **not** joined to `baseURL`. Don't write `'/api/orders'` expecting a glob — write `'**/api/orders'`.

### Handler discipline
- A route handler **must call exactly one** of `fulfill` / `abort` / `continue` / `fallback`. Calling none hangs the request; calling two throws.
- **Handlers run last-registered-first.** The most recent `route(...)` wins; use `route.fallback()` to defer to an earlier handler. `route.continue()` goes straight to the network and **skips** the remaining handlers.
- `route.fulfill({ json })` over manual `{ body: JSON.stringify(...), contentType: 'application/json' }` — the shorthand sets the header and serializes.
- Serve large mock payloads from a file via `route.fulfill({ path: 'tests/fixtures/responses/orders.json' })`, not a giant inline literal.
- Clean up route scope deliberately: a `page.route` lives for the page's lifetime (fresh per test here); use `page.unroute` / `page.unrouteAll({ behavior: 'wait' })` only when you re-route the same URL within one test.

### Scope
- `page.route` for one page (handles its popups); `context.route` for **every** page in the context. Page-level routes take precedence over context-level for the same request.
- Mock at the **narrowest** scope that works — context routes that leak across tests are a common source of cross-test contamination.

### Assertions & waits
- **Listener before action**: `const p = page.waitForResponse(pred); await action(); await p;` (or `Promise.all([waitFor, action])`). Never `await` the wait before firing the action.
- Use **predicates** on `waitForRequest`/`waitForResponse` to assert method/status/url together: `r => r.url().includes('/api/x') && r.status() === 200`.
- Read payloads with `request.postDataJSON()` / `request.headers()` and `await response.json()` / `response.status()` — don't re-parse `postData()` by hand.
- **Negative assertions** ("endpoint not called") collect from `page.on('request', …)` and assert `.toHaveLength(0)` **after** a user-visible completion signal — never after a sleep.
- **No `page.waitForTimeout(ms)` as a wait.** The only `setTimeout` allowed is inside a latency-injection route handler, and only there.

### HAR
- Record with `update: true` once, commit, then replay with no `update`. Re-record in a dedicated PR, never silently in CI.
- Use `content: 'attach'` (bodies as files) for reviewable diffs; `mode: 'minimal'` unless you need timings.
- Set `notFound: 'abort'` on replay so an un-recorded request is a hard failure, not a silent hit to the real third party.

### Determinism & hygiene
- If `page.route` mocks are being bypassed, set `serviceWorkers: 'block'` in the context — a Service Worker can intercept before your route does.
- A route handler is only invoked for the **first** URL of a redirect chain — assert on the final response, not the 30x hop.
- Never put real secrets/tokens in committed mock responses or HAR files — scrub auth headers (`content: 'attach'` + a redaction step, or a `recordHar` `urlFilter`).

### What NOT to do
- No `page.waitForTimeout(ms)` to "wait for the request" — use `waitForRequest`/`waitForResponse` with a predicate.
- No raw `page.route('**/api/...', ...)` scattered through spec bodies — wrap it in a `mockApi`-style fixture with an intent name.
- No handler that calls neither `fulfill`/`abort`/`continue`/`fallback` (hangs) or two of them (throws).
- No `route.continue()` when you meant `route.fallback()` — `continue` skips your other handlers.
- No `'/api/orders'` string pattern expecting glob behavior — it gets `baseURL`-resolved; write `'**/api/orders'`.
- No glob `?`/`[abc]` since 1.43 — switch to a `RegExp`.
- No `{ body: JSON.stringify(x), contentType: 'application/json' }` where `{ json: x }` does the same thing.
- No giant inline JSON literal as a mock — `route.fulfill({ path })` from a fixture file.
- No silent HAR re-record in CI (`update: true` left on) — recordings drift and tests stop testing anything.
- No `notFound: 'fallback'` on a third-party HAR replay you intend to be hermetic — it lets un-recorded calls hit the live service.
- No secrets/PII committed inside a mock response or HAR archive.
- No `context.route` for something one page needs — it leaks the mock into every page in the context.
- No asserting "not called" after a fixed sleep — gate on a user-visible completion signal.

## Generation steps

1. Confirm **traffic** (endpoints + glob/regex), **intent** (mock / assert / modify / HAR / offline), and **scope** (page vs context).
2. Add or extend `tests/fixtures/network/mockApi.ts` with one intent-named method per scenario (`stubOrders`, `failOrdersWith`, `blockAnalytics`). Register the fixture.
3. For call assertions, use `expectRequest` (or a direct `waitForResponse` predicate) with listener-before-action ordering; assert payload via `postDataJSON()`.
4. For third-party determinism, record a HAR with `update: true`, commit it under `tests/fixtures/har/` with `content: 'attach'`, then replay with `notFound: 'abort'`.
5. For offline/latency states, use `context.setOffline(true)` and a latency-injection route helper — never `waitForTimeout`.
6. Run `npx playwright test`; verify under `npx playwright test --ui` (the trace's Network tab shows which requests were routed vs hit the network). Run `tsc --noEmit` for strict-TS green.

## Cross-references

- **`qa/typescript/skills/ui-test-author/playwright`** — the fixture/page-object model these network fixtures layer on; `waitForResponse` ordering and the no-`waitForTimeout` discipline originate there.
- **`qa/dotnet/skills/network-monitoring/playwright-routes`** + **`qa/java/skills/network-monitoring/playwright-routes`** — the sibling stacks porting this canonical TS skill into Playwright-for-.NET / -Java idioms.
- **`qa/typescript/skills/network-monitoring/cdp`** — low-level CDP (`Network.emulateNetworkConditions` for real throttling, protocol-level tracing) when `route` isn't enough.
- **`qa/typescript/skills/network-monitoring/proxy`** — out-of-browser HTTP capture (mitmproxy / system proxy) for multi-process or non-browser traffic.
- **`qa/typescript/skills/ci-pipelines/github-actions`** — runs these specs sharded; HAR archives and traces are uploaded as artifacts there.
- **`qa/typescript/skills/test-data-builder`** — builds the shapes you stub into `route.fulfill({ json })`.
- **`qa/typescript/skills/api-test-author/generator`** — when the test needs no browser, assert against the API directly instead of intercepting.
