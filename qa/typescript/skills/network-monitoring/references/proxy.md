# QA — Out-of-Browser MITM Proxy (TypeScript / `mockttp`)

Stands up an **out-of-process MITM HTTP(S) proxy** with [`mockttp`](https://github.com/httptoolkit/mockttp) (Node 20 + TS strict) to capture, assert, and fault-inject traffic when **there is no Playwright in the picture** — the client under test is a Selenium WebDriver, an Appium driver, a native HTTP client, or a multi-process system. The proxy sits between the client and the network; you point the client at `proxy.url`, then **record** what it sent, **assert** a specific request fired, and **inject faults** (abort, timeout, rewrite a response). Cross-browser and cross-client by construction — the cost is **TLS interception**: the client must trust the proxy's generated CA certificate.

Built on the same wrapper discipline as `qa/typescript/skills/network-monitoring` and `cdp/typescript`: the proxy and every match/record/fault rule are wrapped in one intent-revealing `ProxyControls` helper exposed through a fixture — never raw `proxy.forGet(...).thenReply(...)` scattered across spec bodies. Every wait is conditional on a seen-request promise or a real client signal; there is **no `setTimeout`-as-a-wait / `waitForTimeout`** anywhere in this skill.

> **Why this skill exists.** `playwright-routes` and `cdp` both require a Playwright `page`. The moment your stack is Selenium / Appium / a bare HTTP client / multiple processes, neither applies — there is no `page` to route. An external MITM proxy is the answer: it works for **any** client that honors proxy settings, across **any** browser. You pay for that reach with CA-trust setup and an extra process to start/stop.

## Stack

- Node 20 + TypeScript (strict mode)
- [`mockttp`](https://www.npmjs.com/package/mockttp) ≥ 3.x — `getLocal()`, `forGet`/`forPost`/`forAnyRequest`, `thenReply`/`thenJson`/`thenPassThrough`/`thenForwardTo`/`thenCallback`/`thenCloseConnection`/`thenTimeout`, `getSeenRequests`, `on('request'|'response')`, `generateCACertificate`
- `selenium-webdriver` (or `webdriverio` for Appium) as the **client under test**; a plain `fetch`/`got` client also works
- Proxy helpers under `tests/support/proxy/`, recorded HARs under `tests/artifacts/har/`
- Vitest (or any runner) drives the lifecycle — the proxy is runner-agnostic; this skill uses Vitest hooks
- These tests run in CI under `qa/cicd/typescript/skills/ci-pipelines`: the job starts/stops the proxy as an in-process resource and the client must **trust the per-run generated CA** (no long-lived secret — the CA is generated fresh each run)

## When to use

- Capturing or asserting the HTTP(S) calls a **Selenium / Appium / native-client** test makes, where `page.route` is unavailable
- **Asserting** a request fired with the expected method / URL / payload / headers from a non-Playwright client
- **Fault-injecting** from outside the browser: abort the connection, time out, rewrite a `200` to a `500`, or forward to a stand-in service
- **Recording a HAR** (or an assertable seen-requests list) of a multi-process flow for debugging or determinism
- Driving the **same** capture/assert/fault logic across Chrome, Firefox, Edge, Safari, or a mobile app — one proxy, every client

## When NOT to use

- In-Playwright request routing (mock/abort/fulfill/assert, HAR replay, approximate offline) → `qa/typescript/skills/network-monitoring` (reach for it first **if** you have a Playwright `page`)
- Raw CDP hooks (real bandwidth/CPU throttling, cache disable, `securityDetails`, `Performance` metrics) → `qa/typescript/skills/network-monitoring`
- The .NET / Java proxy stacks → `qa/{dotnet,java}/skills/network-monitoring`
- Writing the page objects / specs themselves → the relevant `qa/typescript/skills/ui-test-author/*` sibling

## Inputs needed

Ask at most 3 questions; infer the rest from the existing test project.

1. **Which client** — Selenium WebDriver (which browser?), Appium, or a native HTTP client? This decides how you point it at `proxy.url`.
2. **Intent** — record/assert a request, or inject a fault (abort / timeout / rewrite a status)? And is the target endpoint **HTTPS** (→ CA-trust step) or plain HTTP?
3. **The signal** — which seen-request (method + URL) or client-visible state proves the flow completed, so the assertion can wait on it instead of sleeping?

## Decision matrix — `mockttp` moves used in tests

| Goal | `mockttp` call | Notes |
|---|---|---|
| Start the proxy (HTTP) | `const proxy = getLocal(); await proxy.start()` | Dynamic port; `proxy.url` is the address to point the client at |
| Start with HTTPS interception | `getLocal({ https: { cert, key } })` from `generateCACertificate()` | Required to **decrypt** HTTPS; client must trust `cert` |
| Pass real traffic through | `proxy.forAnyRequest().thenPassThrough()` | The proxy records but forwards untouched — the recording baseline |
| Forward to a stand-in | `proxy.forGet(url).thenForwardTo('http://stub.local')` | Redirect a dependency to a local fake |
| Canned response | `proxy.forGet(url).thenReply(200, body)` / `.thenJson(200, obj)` | `thenJson` sets `content-type` + serializes |
| Rewrite / fail | `proxy.forPost(url).thenReply(500, '...')` or `.thenCallback(req => ({ statusCode, json }))` | Fault: force the client's error path |
| Abort the connection | `proxy.forGet(url).thenCloseConnection()` | Simulate a dropped/refused connection |
| Hang the request | `proxy.forGet(url).thenTimeout()` | Never responds — exercises client read-timeout handling |
| Assert what was sent | `const ep = await proxy.forPost(url).thenPassThrough(); await ep.getSeenRequests()` | Each request exposes `.method`, `.url`, `.headers`, `await req.body.getJson()` |
| Wait for a request (no sleep) | `proxy.on('request', cb)` → resolve a promise when a match arrives | The sanctioned wait — never a fixed delay |
| Stop the proxy | `await proxy.stop()` | In fixture teardown; releases the port |

## Patterns

### The proxy fixture — `tests/support/proxy/proxyControls.ts`

One helper owns the proxy lifecycle, the generated CA, the recorded traffic, and the intent-named match/fault rules. Specs call `proxy.recordAll()`, `proxy.failPostWith(url, 500)`, `proxy.awaitRequest(...)` — never raw `mockttp` calls.

```typescript
import * as mockttp from 'mockttp';
import { CompletedRequest, Mockttp } from 'mockttp';

/** A request captured off the wire, normalized for assertions. */
export interface SeenRequest {
  method: string;
  url: string;
  headers: Record<string, string | string[] | undefined>;
  json(): Promise<unknown>;
}

export class ProxyControls {
  private constructor(
    private readonly server: Mockttp,
    /** PEM of the CA the client must trust to decrypt HTTPS. */
    readonly caCert: string,
  ) {}

  /** Start an HTTPS-intercepting proxy with a freshly generated CA. */
  static async start(): Promise<ProxyControls> {
    const ca = await mockttp.generateCACertificate(); // { cert, key } PEM strings, fresh per run
    const server = mockttp.getLocal({ https: { cert: ca.cert, key: ca.key } });
    await server.start();
    return new ProxyControls(server, ca.cert);
  }

  /** The address to hand to the client's proxy settings, e.g. http://localhost:54321 */
  get url(): string {
    return this.server.url;
  }

  /** Forward everything untouched while recording it — the capture baseline. */
  async recordAll(): Promise<void> {
    await this.server.forUnmatchedRequest().thenPassThrough();
  }

  /** Force the POST to fail so the client's error path runs (fault injection). */
  async failPostWith(url: string, status: number): Promise<void> {
    await this.server.forPost(url).thenReply(status, JSON.stringify({ error: 'simulated' }), {
      'content-type': 'application/json',
    });
  }

  /** Drop the connection — simulate a refused/dropped socket. */
  async abort(url: string): Promise<void> {
    await this.server.forGet(url).thenCloseConnection();
  }

  /** Never respond — exercise the client's read-timeout handling. */
  async hang(url: string): Promise<void> {
    await this.server.forGet(url).thenTimeout();
  }

  /**
   * Resolve when a request matching the predicate is first seen, or reject on deadline.
   * This is the ONLY wait — never a fixed sleep.
   */
  awaitRequest(pred: (r: CompletedRequest) => boolean, timeoutMs = 10_000): Promise<SeenRequest> {
    return new Promise<SeenRequest>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('no matching request within deadline')), timeoutMs);
      this.server.on('request', (req) => {
        if (!pred(req)) return;
        clearTimeout(timer);
        resolve({
          method: req.method,
          url: req.url,
          headers: req.headers,
          json: () => req.body.getJson() as Promise<unknown>,
        });
      });
    });
  }

  async stop(): Promise<void> {
    await this.server.stop();
  }
}
```

```typescript
// tests/support/proxy/fixture.ts — Vitest lifecycle (the proxy is runner-agnostic)
import { beforeAll, afterAll } from 'vitest';
import { ProxyControls } from './proxyControls';

export let proxy: ProxyControls;

beforeAll(async () => {
  proxy = await ProxyControls.start();
});

afterAll(async () => {
  await proxy.stop();
});
```

Register match/fault rules **before** the action that triggers the request — a rule added after the client has already sent won't catch it.

### Point the client at the proxy — Selenium WebDriver

The whole reason this node exists: there is no `page`, so you wire the proxy into the **client's** settings. For a browser via Selenium, set proxy capabilities **and trust the CA** so HTTPS can be decrypted.

```typescript
// tests/support/proxy/seleniumClient.ts
import { Builder, WebDriver } from 'selenium-webdriver';
import * as chrome from 'selenium-webdriver/chrome';
import { ProxyControls } from './proxyControls';

export async function chromeThroughProxy(proxy: ProxyControls): Promise<WebDriver> {
  const options = new chrome.Options();
  // Route ALL of Chrome's traffic through the MITM proxy.
  options.addArguments(`--proxy-server=${proxy.url}`);
  // Trust the proxy's generated CA so intercepted HTTPS doesn't error.
  // Prefer installing proxy.caCert into the OS/NSS trust store in CI; this flag is the
  // test-only shortcut equivalent — never ship it to a real browser profile.
  options.addArguments('--ignore-certificate-errors');
  return new Builder().forBrowser('chrome').setChromeOptions(options).build();
}
```

```typescript
// tests/support/proxy/httpClient.ts — a native client through the proxy (no browser at all)
import { HttpsProxyAgent } from 'https-proxy-agent';
import got from 'got';
import { ProxyControls } from './proxyControls';

export function clientThroughProxy(proxy: ProxyControls) {
  // Trust the generated CA cleanly (preferred over rejectUnauthorized:false).
  return got.extend({
    agent: { https: new HttpsProxyAgent(proxy.url) },
    https: { certificateAuthority: proxy.caCert },
  });
}
```

For **Appium**, set the proxy on the device/driver capabilities (e.g. WebdriverIO `capabilities.proxy = { proxyType: 'manual', httpProxy: host:port, sslProxy: host:port }`) and install `proxy.caCert` into the device's trust store — the identical record/assert/fault helpers then apply unchanged.

### Assert a request fired — method + payload + headers

```typescript
import { describe, it, expect } from 'vitest';
import { proxy } from '../support/proxy/fixture';
import { chromeThroughProxy } from '../support/proxy/seleniumClient';

describe('checkout through the proxy', () => {
  it('Should_post_the_cart_total_When_the_user_places_the_order', async () => {
    await proxy.recordAll();
    const driver = await chromeThroughProxy(proxy);
    try {
      // Listener BEFORE the action — start the wait, then drive the client.
      const seen = proxy.awaitRequest((r) => r.method === 'POST' && r.url.includes('/api/checkout'));

      await driver.get('https://shop.example.com/cart');
      await driver.findElement({ css: '[data-test="place-order"]' }).click();

      const request = await seen; // resolves when the POST is observed; rejects on deadline
      const body = (await request.json()) as { totalMinor: number; currency: string };
      expect(body).toMatchObject({ totalMinor: 15_000, currency: 'EUR' });
      expect(request.headers['x-tenant']).toBe('tenant-42');
    } finally {
      await driver.quit();
    }
  });
});
```

`awaitRequest` resolves on a real wire event and rejects on a deadline — it is **not** a sleep. For "was it called at all", awaiting it is enough; for the payload, read `await request.json()`.

### Asserting a request was **not** sent

There is no negative wait. Drive the flow to a **client-visible completion signal**, then assert the seen-requests list holds none matching.

```typescript
it('Should_not_call_the_legacy_pricing_endpoint_When_recalculating', async () => {
  const endpoint = await proxy['server']?.forGet('https://shop.example.com/api/legacy-pricing').thenPassThrough();
  const driver = await chromeThroughProxy(proxy);
  try {
    await driver.get('https://shop.example.com/cart');
    await driver.findElement({ css: '[data-test="recalculate"]' }).click();
    // A real signal the flow finished — never a fixed sleep.
    await driver.wait(async () => (await driver.findElements({ css: '[data-test="cart-total"]' })).length > 0, 10_000);

    expect(await endpoint!.getSeenRequests()).toHaveLength(0);
  } finally {
    await driver.quit();
  }
});
```

(In real code expose a `proxy.endpointFor(url)` helper rather than reaching into `server` — shown inline here only to keep the example self-contained.)

### Inject a fault — rewrite, abort, timeout

```typescript
it('Should_show_the_error_banner_When_the_orders_API_returns_500', async () => {
  await proxy.failPostWith('https://shop.example.com/api/orders', 500);
  const driver = await chromeThroughProxy(proxy);
  try {
    await driver.get('https://shop.example.com/orders');
    await driver.findElement({ css: '[data-test="refresh"]' }).click();
    await driver.wait(async () => (await driver.findElements({ css: '[role="alert"]' })).length > 0, 10_000);
  } finally {
    await driver.quit();
  }
});
```

`abort(url)` (`thenCloseConnection`) and `hang(url)` (`thenTimeout`) exercise dropped-socket and read-timeout paths the same way — register the rule, drive the client, assert on the client's visible error state.

### Record to a HAR for debugging / determinism

`getSeenRequests()` is the assertable artifact; for a reviewable archive, subscribe to completed request+response pairs and serialize a minimal HAR. Keep it in a helper, and **scrub auth headers** before writing.

```typescript
// tests/support/proxy/harRecorder.ts
import { writeFile } from 'node:fs/promises';
import { Mockttp } from 'mockttp';

export function recordHar(server: Mockttp): { save: (path: string) => Promise<void> } {
  const entries: unknown[] = [];
  server.on('response', (res) => {
    const { authorization, cookie, ...safeHeaders } = res.headers; // never persist auth
    entries.push({
      request: { method: res.request.method, url: res.request.url },
      response: { status: res.statusCode, headers: safeHeaders },
    });
  });
  return {
    save: (path) => writeFile(path, JSON.stringify({ log: { version: '1.2', entries } }, null, 2)),
  };
}
```

## Rules

### Proxy lifecycle
- One proxy per suite/worker owned by the fixture: `getLocal()` → `start()` → `…` → **`stop()` in teardown**. A leaked proxy holds its port and keeps intercepting.
- Register every match/fault rule **before** the client action that fires the request — a rule added afterward misses it.
- Use a generated CA per run (`generateCACertificate()`); never commit or reuse a static CA key — it is a fresh, ephemeral secret.

### TLS interception (the caveat that bites everyone)
- **HTTPS interception requires the client to trust the proxy's CA.** Start the proxy with `getLocal({ https: { cert, key } })`, then trust `proxy.caCert` on the client: install it in the OS/NSS store (CI), pass it as the HTTP client's `certificateAuthority`/`ca`, or — test-only — `--ignore-certificate-errors` for a throwaway browser. Never trust-all in a real profile.
- Plain-HTTP targets need no CA step; call it out per test which scheme the target uses.

### Pointing the client
- The proxy is useless until the **client** routes through it: Selenium `--proxy-server=${proxy.url}`, a native client's proxy agent, or Appium proxy capabilities. This is the whole point of the node — make it explicit.
- Use the **narrowest** matcher that works (`forPost(exactUrl)` over `forAnyRequest`) so unrelated traffic still passes through and recordings stay readable.

### Assertions & waits
- **No `setTimeout`-as-a-wait / `page.waitForTimeout`.** Wait on `awaitRequest(pred)` (resolves on a wire event, rejects on a deadline) or on a real client-visible signal (`driver.wait` on an element). A longer deadline is a *deadline*, not a sleep.
- **Listener before action**: start `awaitRequest` (or capture the endpoint) *before* driving the client; awaiting after races the request.
- Read payloads with `await request.body.getJson()` / `.getText()` and `request.headers` — don't re-parse raw bytes by hand.
- A "not called" assertion checks `getSeenRequests()` **after** a client-visible completion signal — never after a sleep.

### Hygiene
- Wrap all `mockttp` calls in the `ProxyControls` helper with intent names — no raw `proxy.forGet(...).thenReply(...)` in spec bodies.
- Never persist auth headers / tokens / PII into a recorded HAR — scrub before writing.
- Don't reach for the proxy when you actually have a Playwright `page` — `page.route` is simpler and needs no CA. Justify the choice (non-Playwright client / multi-process).

### What NOT to do
- No proxy without pointing a client at `proxy.url` — it intercepts nothing.
- No HTTPS interception without trusting the CA — the client errors on every TLS handshake.
- No `setTimeout`/`waitForTimeout` to "wait for the request" — use `awaitRequest` or a client signal.
- No raw `mockttp` calls scattered through specs — wrap them in `ProxyControls`.
- No static/committed CA key — generate per run.
- No `rejectUnauthorized: false` / trust-all in a real client profile — scope CA trust to the test.
- No auth headers or secrets persisted in a HAR.
- No proxy where a Playwright `page.route` (no CA, in-process) expresses the test just as well.

## Generation steps

1. Confirm **which client** (Selenium / Appium / native), **intent** (record/assert vs fault), and whether the target is **HTTPS** (→ CA-trust step).
2. Add or extend `tests/support/proxy/proxyControls.ts` — `start()` with a generated CA, intent methods (`recordAll`, `failPostWith`, `abort`, `hang`, `awaitRequest`), `stop()` in teardown. Wire the Vitest lifecycle fixture.
3. Point the client at `proxy.url` (`chromeThroughProxy` / native agent / Appium caps) and **trust `proxy.caCert`** for HTTPS.
4. Register match/fault rules before the action; assert via `awaitRequest` (payload from `request.json()`) or `getSeenRequests()`, waiting only on wire events / client signals.
5. For determinism/debugging, record a scrubbed HAR via the `recordHar` helper under `tests/artifacts/har/`.
6. Run the suite; run `tsc --noEmit` for strict-TS green. In CI, ensure the job installs/trusts the per-run CA before the client starts.

## Cross-references

- **`qa/typescript/skills/network-monitoring`** — in-Playwright routing; reach for it first **if** you have a `page`. The proxy is for when you don't.
- **`qa/typescript/skills/network-monitoring`** — raw CDP hooks below routing (Playwright + Chromium only); the proxy covers the cross-client case CDP can't.
- **`qa/dotnet/skills/network-monitoring`** + **`qa/java/skills/network-monitoring`** — the sibling proxy stacks (`Titanium.Web.Proxy`, `BrowserUp Proxy`). Same five moves (start → point client → record → assert → fault → trust CA), different libraries — structure ported, not code.
- **`qa/cicd/typescript/skills/ci-pipelines`** — runs these specs; the job starts/stops the proxy and trusts the per-run generated CA before the client launches (no long-lived secret).
