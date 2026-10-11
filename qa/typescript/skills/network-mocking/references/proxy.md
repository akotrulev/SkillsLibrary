# QA — Out-of-Browser MITM Proxy (TypeScript / `mockttp`)

Stands up an **out-of-process MITM HTTP(S) proxy** with [`mockttp`](https://github.com/httptoolkit/mockttp)
for clients that have **no Playwright `page`**: a Selenium WebDriver browser, an Appium driver, a native
HTTP client, a multi-process system. Point the client at `proxy.url`, then **watch** what it sent, **assert**
on it, and **inject faults** (an error status, a dropped connection, a hang). It works for any client that
honours proxy settings; the cost is **TLS interception** — the client must trust the proxy's generated CA.

The proxy and every rule are wrapped in one `ProxyControls` class, and the proxy, the driver and the page
objects are **Vitest fixtures** with teardown — never `server.forGet(...)` in a spec, never `try`/`finally` in
a test body, never a module-level `let proxy`. Every wait is a client-visible signal; there is no sleep.

> **Why this layer exists.** `references/playwright-routes.md` and `references/cdp.md` both need a
> Playwright `page`. With Selenium, Appium or a bare HTTP client there is no `page` to route, so the
> interception moves outside the client.

## Stack

- Node 24 + TypeScript (strict), Vitest as the runner.
- `mockttp` — `getLocal`, `generateCACertificate`, `forGet` / `forPost` / `forUnmatchedRequest`,
  `thenPassThrough` / `thenJson` / `thenCloseConnection` / `thenTimeout`, `MockedEndpoint.getSeenRequests()`.
- `selenium-webdriver`, WebdriverIO (Appium) or a plain HTTP client as the client under test.
- Helpers under `tests/support/proxy/`.

## When to use

- Capturing or asserting the HTTP(S) calls a Selenium, Appium or native-client test makes.
- Fault injection from outside the client: an error status, a dropped socket, a read timeout.
- A log of a multi-process flow's traffic for debugging.
- The same capture and faults across Chrome, Firefox, Safari or a mobile app — one proxy, every client.

## When NOT to use

- Any test with a Playwright `page` → `references/playwright-routes.md` (reach for it first)
- Throttling, cache disable, CPU, metrics → `references/cdp.md`
- Java and .NET proxies → `qa-java:network-mocking`, `qa-dotnet:network-mocking`
- Writing the Selenium page objects themselves → `qa/typescript/skills/ui-test-author/selenium`

## Inputs needed

1. **Which client** — Selenium (which browser), Appium, or a native HTTP client.
2. **Intent** — watch and assert, or inject a fault; is the target **HTTPS** (then the CA step applies)?
3. **The signal** — which client-visible state proves the flow finished, so the assertion reads after it.

## Decision matrix — the `mockttp` moves

| Goal | Call | Notes |
|---|---|---|
| Start with HTTPS interception | `getLocal({ https: { cert, key } })` from `generateCACertificate()` | A fresh CA per run; the client must trust `cert` |
| Forward everything else | `forUnmatchedRequest().thenPassThrough()` | The lowest-priority rule; specific rules win |
| Watch one endpoint | `forPost(path).thenPassThrough()` → `MockedEndpoint` | Forwards it and records what was sent |
| Canned or failing response | `forGet(path).thenJson(status, body)` | Forces the client's error path |
| Dropped connection | `forGet(path).thenCloseConnection()` | A refused or reset socket |
| Hang | `forGet(path).thenTimeout()` | Never answers — the client's read timeout |
| What was sent | `await endpoint.getSeenRequests()` | Each has `method`, `url`, `headers`, `await body.getJson()` |
| Stop | `await server.stop()` | In fixture teardown |

## 1. `ProxyControls` — `tests/support/proxy/ProxyControls.ts`

```typescript
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import * as mockttp from 'mockttp';
import type { MockedEndpoint, Mockttp } from 'mockttp';

const secretHeaders = new Set(['authorization', 'cookie', 'proxy-authorization']);

export class ProxyControls {
  private constructor(
    private readonly server: Mockttp,
    private readonly passedThrough: MockedEndpoint,
    readonly caCert: string,
  ) {}

  static async start(): Promise<ProxyControls> {
    const ca = await mockttp.generateCACertificate();
    const server = mockttp.getLocal({ https: { cert: ca.cert, key: ca.key } });
    await server.start();
    const passedThrough = await server.forUnmatchedRequest().thenPassThrough();
    return new ProxyControls(server, passedThrough, ca.cert);
  }

  get url(): string {
    return this.server.url;
  }

  watchGet(path: string): Promise<MockedEndpoint> {
    return this.server.forGet(path).thenPassThrough();
  }

  watchPost(path: string): Promise<MockedEndpoint> {
    return this.server.forPost(path).thenPassThrough();
  }

  failGetWith(path: string, status: number): Promise<MockedEndpoint> {
    return this.server.forGet(path).thenJson(status, { error: 'simulated' });
  }

  dropConnection(path: string): Promise<MockedEndpoint> {
    return this.server.forGet(path).thenCloseConnection();
  }

  hang(path: string): Promise<MockedEndpoint> {
    return this.server.forGet(path).thenTimeout();
  }

  async writeTrafficLog(path: string): Promise<void> {
    const requests = await this.passedThrough.getSeenRequests();
    const entries = requests.map((request) => ({
      method: request.method,
      url: request.url,
      headers: Object.fromEntries(Object.entries(request.headers).filter(([name]) => !secretHeaders.has(name))),
    }));
    await mkdir(dirname(path), { recursive: true });
    await writeFile(path, JSON.stringify(entries, null, 2));
  }

  async stop(): Promise<void> {
    await this.server.stop();
  }
}
```

- Every rule method returns the `mockttp` promise, so a caller awaits it and the rule exists **before** the
  client acts.
- `writeTrafficLog` keeps a debugging record of everything that passed through, with credentials removed.
  Call it from the fixture's teardown, before `stop()`, when a suite needs that record as evidence; write it
  under `test-results/`, which is never committed.

## 2. Pointing the client at the proxy — the fixtures

```typescript
import { Builder, type WebDriver } from 'selenium-webdriver';
import * as chrome from 'selenium-webdriver/chrome';
import { test as base } from 'vitest';
import { ProxyControls } from './ProxyControls';
import { ShopPages } from './ShopPages';

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (value === undefined) {
    throw new Error(`Environment variable ${name} is not set`);
  }
  return value;
}

type ProxyFixtures = {
  proxy: ProxyControls;
  driver: WebDriver;
  shop: ShopPages;
};

export const test = base.extend<ProxyFixtures>({
  proxy: async ({}, use) => {
    const proxy = await ProxyControls.start();
    await use(proxy);
    await proxy.stop();
  },
  driver: async ({ proxy }, use) => {
    const options = new chrome.Options().addArguments(
      `--proxy-server=${proxy.url}`,
      '--proxy-bypass-list=<-loopback>',
      '--ignore-certificate-errors',
    );
    const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
    await use(driver);
    await driver.quit();
  },
  shop: async ({ driver }, use) => {
    await use(new ShopPages(driver, requiredEnv('BASE_URL')));
  },
});

export { expect } from 'vitest';
```

- Each test gets its own proxy, so no rule leaks into the next test, and teardown stops it whether the test
  passed or failed.
- Chrome sends loopback traffic **around** a proxy by default; `--proxy-bypass-list=<-loopback>` routes a
  `localhost` app through it.
- `--ignore-certificate-errors` is the test-only shortcut for a throwaway browser profile. In CI, prefer
  installing `proxy.caCert` into the OS or NSS trust store. Never trust-all in a real profile.

`ShopPages` is a Selenium page object: its methods drive the browser and wait on a client-visible element,
built from PascalCase test ids:

```typescript
import { By, until, type WebDriver } from 'selenium-webdriver';

const byTestId = (testId: string): By => By.css(`[data-testid="${testId}"]`);

export class ShopPages {
  constructor(
    private readonly driver: WebDriver,
    private readonly baseUrl: string,
  ) {}

  async openCart(): Promise<void> {
    await this.driver.get(`${this.baseUrl}/cart`);
    await this.driver.wait(until.elementLocated(byTestId('Cart.Total')), 10_000);
  }

  async placeOrder(): Promise<void> {
    await this.driver.findElement(byTestId('Cart.PlaceOrder')).click();
    await this.driver.wait(until.elementLocated(byTestId('Order.Confirmation')), 10_000);
  }

  async recalculate(): Promise<void> {
    await this.driver.findElement(byTestId('Cart.Recalculate')).click();
    await this.driver.wait(until.elementLocated(byTestId('Cart.TotalUpdated')), 10_000);
  }

  async openOrders(): Promise<void> {
    await this.driver.get(`${this.baseUrl}/orders`);
  }

  async ordersErrorText(): Promise<string> {
    const banner = await this.driver.wait(until.elementLocated(byTestId('Orders.ErrorBanner')), 10_000);
    return banner.getText();
  }
}
```

A native client through the proxy, with the CA trusted properly instead of switched off:

```typescript
import got from 'got';
import { HttpsProxyAgent } from 'https-proxy-agent';
import type { ProxyControls } from './ProxyControls';

export const clientThroughProxy = (proxy: ProxyControls) =>
  got.extend({
    agent: { https: new HttpsProxyAgent(proxy.url) },
    https: { certificateAuthority: proxy.caCert },
  });
```

For **Appium**, set the proxy in the driver capabilities (WebdriverIO
`proxy: { proxyType: 'manual', httpProxy: 'host:port', sslProxy: 'host:port' }`) and install `proxy.caCert` in
the device's trust store; the same rules then apply unchanged.

## 3. Asserting a request was sent — method and payload

```typescript
import { describe } from 'vitest';
import { expect, test } from './proxy.fixtures';

type CheckoutRequest = { readonly totalMinor: number; readonly currency: string };

describe('Checkout through the proxy', () => {
  test('Should_PostCartTotal_When_UserPlacesOrder', async ({ proxy, shop }) => {
    const checkout = await proxy.watchPost('/api/checkout');

    await shop.openCart();
    await shop.placeOrder();

    const requests = await checkout.getSeenRequests();
    const expected: CheckoutRequest = { totalMinor: 15_000, currency: 'EUR' };
    expect(requests, 'checkout requests').toHaveLength(1);
    expect(await requests[0]?.body.getJson(), 'checkout payload').toEqual(expected);
  });
});
```

The rule is registered before the client acts; the requests are read after `placeOrder()` has seen the
confirmation. No event race, no deadline timer.

## 4. Asserting a request was NOT sent

```typescript
test('Should_NotCallLegacyPricing_When_CartIsRecalculated', async ({ proxy, shop }) => {
  const legacyPricing = await proxy.watchGet('/api/legacy-pricing');

  await shop.openCart();
  await shop.recalculate();

  expect(await legacyPricing.getSeenRequests(), 'legacy pricing calls').toEqual([]);
});
```

Read the list **after** the client-visible completion signal, never after a sleep.

## 5. Injecting a fault — and asserting on it

```typescript
test('Should_ShowErrorBanner_When_OrdersApiReturns500', async ({ proxy, shop }) => {
  await proxy.failGetWith('/api/orders', 500);

  await shop.openOrders();

  expect(await shop.ordersErrorText(), 'orders error banner').toBe('We could not load your orders');
});
```

A fault test asserts the client's visible reaction; a test that injects a fault and checks nothing proves
nothing. `dropConnection(path)` and `hang(path)` exercise the dropped-socket and read-timeout paths the same
way: register the rule, drive the client, assert on its error state.

## Rules

### Lifecycle

- One proxy per test, owned by a Vitest fixture: `start()`, `use`, `stop()` in teardown. No module-level
  proxy, no `beforeAll` / `afterAll` pair holding it.
- Rules are registered — and awaited — before the client action.
- A fresh CA per run from `generateCACertificate()`; never a committed or reused CA key.

### TLS interception

- HTTPS interception needs the client to trust the proxy's CA: the OS or NSS trust store (CI), the HTTP
  client's `certificateAuthority`, or `--ignore-certificate-errors` for a throwaway test browser only.
- A plain-HTTP target needs no CA step; say which scheme each test uses.

### Pointing the client

- The proxy intercepts nothing until the client routes through it: Selenium `--proxy-server`, the native
  client's agent, or Appium capabilities. Loopback targets also need `--proxy-bypass-list=<-loopback>`.
- Use the narrowest matcher (`forPost('/api/checkout')`) so the rest passes through.

### Assertions and waits

- No sleeps. Page objects wait on client-visible elements; assertions read `getSeenRequests()` after them.
- Read payloads with `await request.body.getJson()` into a typed value.
- Every fault test asserts the client's error state.
- No `try`/`finally` in a test body — the fixtures quit the driver and stop the proxy.

### Hygiene

- All `mockttp` calls live in `ProxyControls`; specs call intent methods.
- Credentials never reach a written traffic log.
- With a Playwright `page`, use `references/playwright-routes.md` instead: no CA, no extra process.

## What NOT to do

- A proxy with no client pointed at it.
- HTTPS interception without trusting the CA.
- A sleep to "wait for the request".
- `mockttp` calls in a spec body, or reaching into the server through a private field.
- `try { … } finally { await driver.quit() }` in a test.
- A fault-injection test with no assertion.
- `data-test="place-order"`-style kebab ids in new page objects — test ids are PascalCase dot-separated.
- A static or committed CA key; `rejectUnauthorized: false` in a real client profile.
- Auth headers or cookies in a written log.

## Generation steps

1. Confirm the client, the intent and the scheme.
2. Extend `ProxyControls` with one intent method per rule.
3. Add the fixtures: the proxy, the client pointed at it (trusting the CA), and the page objects.
4. Register rules before the action; read `getSeenRequests()` after the client-visible signal; assert the
   client's state for every fault.
5. Run the suite and `tsc --noEmit`; in CI, trust the per-run CA before the client starts. Inside a plan task
   marked `Gate: none`, run none of this and report the files as written, not run.

## Cross-references

- `references/playwright-routes.md` — in-Playwright routing; first choice whenever there is a `page`.
- `references/cdp.md` — Chromium protocol hooks below routing.
- `qa-java:network-mocking`, `qa-dotnet:network-mocking` — the sibling proxy stacks.
- `qa/typescript/skills/ui-test-author/selenium` — Selenium page objects.
- `qa/cicd/typescript/skills/ci-pipelines` — the job that trusts the per-run CA before the client launches.
