# QA — Chrome DevTools Protocol Hooks (TypeScript / Playwright 1.64)

Drives the raw **Chrome DevTools Protocol** from a Playwright test through
`page.context().newCDPSession(page)`, for the hooks that live **below the routing layer**: real bandwidth
and latency throttling, HTTP-cache disable, CPU throttling and `Performance` metrics. The session and every
command and event are wrapped in one `cdp` fixture with intent names (`throttle`, `disableCache`,
`cpuThrottle`, `metrics`, `responsesFor`) — never `client.send('Domain.method', …)` in a spec. There is no
`waitForTimeout` in this file.

> **Chromium only.** `newCDPSession` throws on Firefox and WebKit. That is the price of dropping below
> routing; pin the spec to Chromium. Anything that must run cross-browser stays in
> `references/playwright-routes.md` — including security headers and TLS details, which `response.allHeaders()`
> and `response.securityDetails()` cover there.

## When to use

- A **real** slow connection (Slow or Fast 3G throughput and latency) to test loading, skeleton and timeout
  states — not the per-request delay routing can fake.
- Every request must **miss the HTTP cache** (`Network.setCacheDisabled`) so the cold-cache path is
  deterministic.
- **CPU throttling** (4×, 6×) to surface jank and long tasks on low-end devices.
- **Performance metrics** (`Performance.getMetrics` — `JSHeapUsedSize`, `LayoutCount`, `TaskDuration`) with
  a budget.

## When NOT to use

- Mock, abort, modify, assert, HAR replay, offline, security headers, TLS → `references/playwright-routes.md`
- A non-Playwright client, or cross-browser capture → `references/proxy.md`
- Java and .NET CDP → `qa-java:network-mocking`, `qa-dotnet:network-mocking`

## Inputs needed

1. **Which hook** — a throttle preset, cache disable, a CPU rate, or metrics.
2. **Chromium-only is acceptable** for this spec.
3. **The signal** — the loading or ready state to assert.

## Decision matrix — the CDP calls

| Goal | Call | Notes |
|---|---|---|
| Network events on | `client.send('Network.enable')` | Before `responseReceived` fires or a throttle applies |
| Real bandwidth and latency | `client.send('Network.emulateNetworkConditions', { offline, downloadThroughput, uploadThroughput, latency })` | Throughput in **bytes per second**, latency in **ms** |
| No HTTP cache | `client.send('Network.setCacheDisabled', { cacheDisabled: true })` | Every request goes to the network |
| CPU slowdown | `client.send('Emulation.setCPUThrottlingRate', { rate })` | `1` = none, `4` / `6` = low-end device |
| Response metadata | `client.on('Network.responseReceived', …)` | `response.url`, `.status`, `.fromDiskCache` |
| Metrics | `Performance.enable`, then `Performance.getMetrics` | `{ metrics: [{ name, value }] }` |
| End the session | `client.detach()` | In fixture teardown |

DevTools' own profiles, encoded in `NetworkPresets` below:

| Preset | Download | Upload | Latency |
|---|---|---|---|
| Slow 3G | ~50 KB/s (500 kbit/s × 0.8 ÷ 8) | ~50 KB/s | 2000 ms (400 × 5) |
| Fast 3G | ~180 KB/s (1.6 Mbit/s × 0.9 ÷ 8) | ~84 KB/s (750 kbit/s × 0.9 ÷ 8) | ~562 ms (150 × 3.75) |

## 1. The fixture — `cdp.fixtures.ts`

The fixture opens the session, enables `Network`, records every response it sees, exposes intent methods,
and detaches in teardown. CDP's event payloads are typed by the event name, so no protocol type is
imported.

```typescript
import type { CDPSession, Page } from '@playwright/test';
import { test as base } from './fixtures';
import { DashboardPage } from './DashboardPage';
import { OrdersPage } from './OrdersPage';
import { ProfilePage } from './ProfilePage';

export const NetworkPresets = {
  Slow3G: { offline: false, downloadThroughput: (500 * 1000 * 0.8) / 8, uploadThroughput: (500 * 1000 * 0.8) / 8, latency: 400 * 5 },
  Fast3G: { offline: false, downloadThroughput: (1.6 * 1000 * 1000 * 0.9) / 8, uploadThroughput: (750 * 1000 * 0.9) / 8, latency: 150 * 3.75 },
} as const;

export type NetworkPreset = (typeof NetworkPresets)[keyof typeof NetworkPresets];

export type CapturedResponse = {
  readonly url: string;
  readonly status: number;
  readonly fromDiskCache: boolean;
};

export class CdpControls {
  private readonly captured: CapturedResponse[] = [];

  private constructor(private readonly client: CDPSession) {
    client.on('Network.responseReceived', (event) => {
      this.captured.push({
        url: event.response.url,
        status: event.response.status,
        fromDiskCache: event.response.fromDiskCache ?? false,
      });
    });
  }

  static async attach(page: Page): Promise<CdpControls> {
    const client = await page.context().newCDPSession(page);
    await client.send('Network.enable');
    return new CdpControls(client);
  }

  async throttle(preset: NetworkPreset): Promise<void> {
    await this.client.send('Network.emulateNetworkConditions', preset);
  }

  async disableCache(): Promise<void> {
    await this.client.send('Network.setCacheDisabled', { cacheDisabled: true });
  }

  async cpuThrottle(rate: number): Promise<void> {
    await this.client.send('Emulation.setCPUThrottlingRate', { rate });
  }

  async metrics(): Promise<Map<string, number>> {
    await this.client.send('Performance.enable');
    const { metrics } = await this.client.send('Performance.getMetrics');
    return new Map(metrics.map((metric) => [metric.name, metric.value]));
  }

  responsesFor(matches: (url: string) => boolean): readonly CapturedResponse[] {
    return this.captured.filter((response) => matches(response.url));
  }

  lastResponseFor(matches: (url: string) => boolean): CapturedResponse | undefined {
    return this.responsesFor(matches).at(-1);
  }

  async detach(): Promise<void> {
    await this.client.detach();
  }
}

type CdpFixtures = {
  cdp: CdpControls;
  dashboardPage: DashboardPage;
  ordersPage: OrdersPage;
  profilePage: ProfilePage;
};

export const test = base.extend<CdpFixtures>({
  cdp: async ({ page }, use) => {
    const controls = await CdpControls.attach(page);
    await use(controls);
    await controls.detach();
  },
  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },
  ordersPage: async ({ page }, use) => {
    await use(new OrdersPage(page));
  },
  profilePage: async ({ page }, use) => {
    await use(new ProfilePage(page));
  },
});

export { expect } from './fixtures';
```

- The listener is registered right after `Network.enable`, before the spec navigates, so no response is
  missed.
- `responsesFor` returns every match and `lastResponseFor` the **latest** one. A check after a reload reads
  the last match; the first match is the response from before the reload and would make the test
  impossible to fail.
- Offline is `context.setOffline(true)` at the routing layer, so there is no offline preset here.

Each CDP spec declares the dependency at its top:

```typescript
test.skip(({ browserName }) => browserName !== 'chromium', 'CDP is Chromium-only');
```

## 2. Real throttling — Slow 3G

```typescript
import { NetworkPresets, expect, test } from './cdp.fixtures';

test('Should_ShowSkeletonUntilOrdersArrive_When_NetworkIsSlow3G', async ({ cdp, ordersPage }) => {
  await cdp.throttle(NetworkPresets.Slow3G);

  await ordersPage.goto();

  await expect(ordersPage.skeleton, 'orders skeleton').toBeVisible();
  await expect(ordersPage.list, 'orders list over Slow 3G').toBeVisible({ timeout: 30_000 });
});
```

Apply the profile **before** the navigation that should feel it. `ordersPage.goto()` only navigates, so the
loading state is still observable. The longer `timeout` is a deadline for a web-first assertion, not a sleep.

## 3. Cache disabled — the reload goes to the network

```typescript
const isAvatar = (url: string): boolean => url.includes('/avatars/');

test('Should_RefetchAvatarFromNetwork_When_CacheIsDisabled', async ({ cdp, profilePage }) => {
  await cdp.disableCache();
  await profilePage.open();

  await profilePage.reloadProfile();

  await expect.poll(() => cdp.responsesFor(isAvatar).length, 'avatar responses').toBe(2);
  expect(cdp.lastResponseFor(isAvatar)?.fromDiskCache, 'reloaded avatar served from disk cache').toBe(false);
});
```

`expect.poll` waits until the reload's response has arrived; the assertion then reads the **last** avatar
response, the one the reload produced.

## 4. CPU throttling

```typescript
test('Should_RenderDashboardWithinDeadline_When_CpuIsThrottled4x', async ({ cdp, dashboardPage }) => {
  await cdp.cpuThrottle(4);

  await dashboardPage.goto();

  await expect(dashboardPage.ready, 'dashboard ready under 4x CPU').toBeVisible({ timeout: 15_000 });
});
```

The fixture gives each test a fresh session, so the rate never needs resetting.

## 5. Performance budget

```typescript
test('Should_StayWithinLayoutAndHeapBudget_When_DashboardRenders', async ({ cdp, dashboardPage }) => {
  await dashboardPage.open();

  const metrics = await cdp.metrics();

  expect.soft(metrics.get('LayoutCount') ?? Infinity, 'layout count').toBeLessThan(60);
  expect.soft(metrics.get('JSHeapUsedSize') ?? Infinity, 'JS heap bytes').toBeLessThan(50 * 1024 * 1024);
});
```

`dashboardPage.open()` returns once the dashboard's ready marker is visible; sampling before that passes only
because the page had not finished rendering. The two `expect.soft` calls are one behaviour, "renders within
budget", and both report.

## Rules

### Session lifecycle

- Open with `page.context().newCDPSession(page)`; **`detach()` in fixture teardown**.
- `Network.enable` before relying on `Network.*` events or throttling; `Performance.enable` before
  `getMetrics`.
- One session per page, owned by the fixture.

### Chromium only

- `newCDPSession` throws on Firefox and WebKit. Every CDP spec carries the `test.skip` line, or runs in a
  Chromium-only project.
- A test that must run cross-browser does not belong here.

### Throttling and emulation

- Throughput is **bytes per second**, latency **milliseconds**; use `NetworkPresets`, never raw numbers per
  spec.
- Apply throttle, cache disable and CPU rate **before** the navigation or action that should feel them.

### Assertions and waits

- No `waitForTimeout`. Waits are web-first assertions with a deadline, or `expect.poll` over captured events.
- After a reload or a second request, read the **last** captured match.
- Sample metrics after a user-visible ready signal.

### Hygiene

- Method and event names are strings; a typo fails at runtime. Every `send` and `on` lives in `CdpControls`.
- Justify every drop below routing; routing is typed and cross-browser.

## What NOT to do

- `client.send(...)` or `client.on(...)` in a spec body.
- A CDP spec on Firefox or WebKit.
- A sleep to "wait for the slow load".
- `emulateNetworkConditions` before `Network.enable`; `getMetrics` before `Performance.enable`.
- Raw throughput numbers per spec.
- The **first** captured match after a reload.
- A leaked session.
- CDP for security headers or TLS details — `references/playwright-routes.md` §5 covers them in every
  browser.

## Generation steps

1. Confirm the hook, that Chromium-only is acceptable, and the signal.
2. Extend `cdp.fixtures.ts`: `Network.enable`, the response capture, intent methods, `detach()` in teardown.
3. Pin the spec to Chromium.
4. Apply the hook before the navigation; assert on a loading or ready signal with a deadline.
5. Run `npx playwright test --project=chromium` and `tsc --noEmit`. Inside a plan task marked
   `Gate: none`, run none of this and report the files as written, not run.

## Cross-references

- `references/playwright-routes.md` — the layer above; reach for it first, including for headers and TLS.
- `references/proxy.md` — out-of-browser capture for non-Playwright clients.
- `qa/typescript/skills/ui-test-author/playwright` — the fixtures and page objects these extend.
- `qa-java:network-mocking`, `qa-dotnet:network-mocking` — the same hooks in Java and .NET.
- `qa/cicd/typescript/skills/ci-pipelines` — runs these specs in the Chromium project.
