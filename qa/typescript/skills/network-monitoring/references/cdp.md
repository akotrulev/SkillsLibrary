# QA — Raw CDP Network & Performance Hooks (TypeScript)

Drives the raw **Chrome DevTools Protocol** from a Playwright `@playwright/test` (Node 20 + TS strict) test via `page.context().newCDPSession(page)`, for the hooks that live **below the `page.route` routing layer**: real bandwidth/latency throttling, HTTP-cache disable, CPU throttling, security-header/`securityDetails` auditing, and `Performance` metrics. Built on the **fixture-driven** model from `qa/typescript/skills/network-monitoring`: the CDP session and every command/event are wrapped in a single fixture (`cdp`) with intent-revealing methods (`throttle`, `disableCache`, `cpuThrottle`, `metrics`, `responseFor`) — never raw `client.send('Domain.method', …)` scattered across spec bodies. Every wait is conditional on a Playwright condition or a CDP event; there is **no `waitForTimeout`** anywhere in this skill.

> **Chromium-only.** CDP exists only in Chromium-based browsers. On Firefox/WebKit `newCDPSession` throws. That is the price of dropping below the routing layer — guard the project (or `test.skip`) to the `chromium` project. For anything that must run cross-browser, stay at the `page.route` layer (`playwright-routes`).

## Stack

- Node 20 + TypeScript (strict mode)
- `@playwright/test` (Playwright ≥ 1.49) — `page.context().newCDPSession(page)` → `client.send(method, params)` + `client.on(event, …)`
- CDP helpers under `tests/fixtures/cdp/`
- Page objects under `tests/pages/`, specs under `tests/specs/` (see the UI sibling)
- These tests run **only in the `chromium` project**, sharded in CI under `qa/typescript/skills/ci-pipelines` (`--shard`, `blob` reporter, traces on failure). No new secrets — CDP needs none.

## When to use

- Emulating a **real** slow connection (Slow/Fast 3G with actual throughput + latency numbers) to test loading/timeout/skeleton states — not the per-request `setTimeout` delay `page.route` can fake
- Forcing every request to **miss the HTTP cache** (`Network.setCacheDisabled`) so a test exercises cold-cache behavior deterministically
- **CPU-throttling** the main thread (4×/6×) to surface jank, long tasks, and slow renders on low-end devices
- **Auditing security headers** — assert the document (and its API calls) carry CSP / HSTS / `X-Frame-Options`, or inspect TLS `securityDetails` (protocol, issuer, validity)
- Capturing **performance metrics** (`Performance.getMetrics` — `JSHeapUsedSize`, `LayoutCount`, `TaskDuration`, …) and asserting a budget

## When NOT to use

- High-level request **mock / abort / fulfill / modify-in-flight**, HAR replay, or approximate offline (`context.setOffline`) → `qa/typescript/skills/network-monitoring` (the layer above; reach for it first)
- Playwright .NET / Java CDP → `qa/{dotnet,java}/skills/network-monitoring`
- **Cross-browser** throttling/auditing, or capture for a non-Playwright / multi-process stack (Appium, Selenium, native apps) → `qa/typescript/skills/network-monitoring`
- Writing the page objects / specs themselves → `qa/typescript/skills/ui-test-author/playwright`

## Inputs needed

Ask at most 3 questions; infer the rest from `playwright.config.ts` and existing specs.

1. **Which hook** — network throttle (which preset?), cache disable, CPU throttle (which rate?), security-header audit, or perf metrics?
2. **Confirm Chromium-only is acceptable** — is this suite (or this spec) allowed to run only in the `chromium` project?
3. **The signal** — for throttle/CPU: which loading/jank state to assert? For audit: which headers must be present, on which URL?

## Decision matrix — CDP domains used in tests

| Goal | CDP call | Notes |
|---|---|---|
| Enable network events | `client.send('Network.enable')` | Required **before** `responseReceived`/`emulateNetworkConditions` fire |
| Real bandwidth + latency | `client.send('Network.emulateNetworkConditions', { offline, downloadThroughput, uploadThroughput, latency })` | Throughput in **bytes/s**, latency in **ms**; use the Slow/Fast 3G presets |
| Disable the HTTP cache | `client.send('Network.setCacheDisabled', { cacheDisabled: true })` | Every request misses cache → cold-cache path is deterministic |
| Throttle the CPU | `client.send('Emulation.setCPUThrottlingRate', { rate })` | `rate` = slowdown multiplier; `1` = none, `4`/`6` = low-end device |
| Capture response metadata | `client.on('Network.responseReceived', e => …)` | `e.response.url` / `.status` / `.headers` / `.securityDetails` |
| Perf metrics | `client.send('Performance.enable')` then `client.send('Performance.getMetrics')` | Returns `{ metrics: [{ name, value }] }` |
| Close the session | `client.detach()` | Do it in fixture teardown; a detached session emits no events |

Realistic throttling numbers (Chrome DevTools' own Slow/Fast 3G profiles — encoded in the `NetworkPresets` below):

| Preset | download | upload | latency |
|---|---|---|---|
| Slow 3G | ~50 KB/s (`500 kbit/s × 0.8 ÷ 8`) | ~50 KB/s | 2000 ms (`400 × 5`) |
| Fast 3G | ~180 KB/s (`1.6 Mbit/s × 0.9 ÷ 8`) | ~84 KB/s (`750 kbit/s × 0.9 ÷ 8`) | ~562 ms (`150 × 3.75`) |

## Patterns

### The CDP fixture — `tests/fixtures/cdp/cdp.ts`

One fixture owns the session: it opens it, enables `Network`, captures every `responseReceived` for later auditing, exposes intent-named methods, and detaches in teardown. Specs call `cdp.throttle(NetworkPresets.Slow3G)`, never `client.send('Network.emulateNetworkConditions', …)`.

```typescript
import { test as base, expect, CDPSession, Page, Protocol } from '@playwright/test';

/**
 * Chrome DevTools network profiles — throughput in BYTES/SECOND, latency in MS,
 * matching DevTools' own Slow/Fast 3G formulas. `offline` rides in the same params.
 */
export const NetworkPresets = {
  Slow3G: { offline: false, downloadThroughput: (500 * 1000 * 0.8) / 8, uploadThroughput: (500 * 1000 * 0.8) / 8, latency: 400 * 5 },
  Fast3G: { offline: false, downloadThroughput: (1.6 * 1000 * 1000 * 0.9) / 8, uploadThroughput: (750 * 1000 * 0.9) / 8, latency: 150 * 3.75 },
  Offline: { offline: true, downloadThroughput: 0, uploadThroughput: 0, latency: 0 },
} as const;

export type NetworkPreset = (typeof NetworkPresets)[keyof typeof NetworkPresets];

/** A response captured off the wire via Network.responseReceived. */
export interface CapturedResponse {
  url: string;
  status: number;
  headers: Record<string, string>;
  securityDetails: Protocol.Network.SecurityDetails | null;
}

export class CdpControls {
  private readonly captured: CapturedResponse[] = [];

  private constructor(private readonly client: CDPSession) {
    // Registered immediately after Network.enable, before any navigation in the spec —
    // so no document/API response is missed.
    client.on('Network.responseReceived', (e: Protocol.Network.responseReceivedPayload) => {
      this.captured.push({
        url: e.response.url,
        status: e.response.status,
        headers: e.response.headers as Record<string, string>,
        securityDetails: e.response.securityDetails ?? null,
      });
    });
  }

  static async attach(page: Page): Promise<CdpControls> {
    const client = await page.context().newCDPSession(page); // Chromium-only — throws on FF/WebKit
    await client.send('Network.enable');
    return new CdpControls(client);
  }

  /** Apply a real bandwidth + latency profile (e.g. NetworkPresets.Slow3G). */
  async throttle(preset: NetworkPreset): Promise<void> {
    await this.client.send('Network.emulateNetworkConditions', preset);
  }

  /** Force every request to miss the HTTP cache — cold-cache path becomes deterministic. */
  async disableCache(): Promise<void> {
    await this.client.send('Network.setCacheDisabled', { cacheDisabled: true });
  }

  /** Slow the main thread by `rate`× (1 = none, 4/6 = low-end device) to surface jank. */
  async cpuThrottle(rate: number): Promise<void> {
    await this.client.send('Emulation.setCPUThrottlingRate', { rate });
  }

  /** Performance.getMetrics as a name→value map for budget assertions. */
  async metrics(): Promise<Map<string, number>> {
    await this.client.send('Performance.enable');
    const { metrics } = await this.client.send('Performance.getMetrics');
    return new Map(metrics.map((m) => [m.name, m.value]));
  }

  /** The captured response whose URL matches — for the security-header audit. */
  responseFor(pred: (url: string) => boolean): CapturedResponse | undefined {
    return this.captured.find((r) => pred(r.url));
  }

  async detach(): Promise<void> {
    await this.client.detach();
  }
}

type CdpFixtures = { cdp: CdpControls };

export const test = base.extend<CdpFixtures>({
  cdp: async ({ page }, use) => {
    const controls = await CdpControls.attach(page);
    await use(controls);
    await controls.detach();
  },
});

export { expect };
```

Pin the suite to Chromium so a Firefox/WebKit project never opens a CDP session and throws:

```typescript
// at the top of a CDP spec — declare the dependency loudly
test.skip(({ browserName }) => browserName !== 'chromium', 'CDP is Chromium-only');
```

### Real network throttling — Slow 3G

```typescript
import { test, expect, NetworkPresets } from '../fixtures/cdp/cdp';

test('Should_keep_the_skeleton_visible_When_orders_load_over_Slow_3G', async ({ page, cdp }) => {
  await cdp.throttle(NetworkPresets.Slow3G); // apply BEFORE navigating

  await page.goto('/orders');

  // The skeleton is the genuine loading signal — assert on it, never on a fixed sleep.
  await expect(page.getByTestId('orders-skeleton')).toBeVisible();
  await expect(page.getByTestId('orders-list')).toBeVisible({ timeout: 30_000 });
});
```

Apply the profile **before** the navigation that should feel it. `Network.emulateNetworkConditions` is real emulation — Playwright's web-first `expect` retries until the slow load completes, so the longer `timeout` is a deadline, **not** a `waitForTimeout`.

### Disable the HTTP cache

```typescript
test('Should_refetch_the_avatar_When_the_cache_is_disabled', async ({ page, cdp }) => {
  await cdp.disableCache();

  await page.goto('/profile');
  await expect(page.getByTestId('avatar')).toBeVisible();
  await page.getByRole('button', { name: 'Reload profile' }).click();

  // With the cache off, the avatar request is re-issued (200) rather than served from memory (304/from-cache).
  const avatar = cdp.responseFor((u) => u.includes('/avatars/'));
  expect(avatar?.status).toBe(200);
});
```

### CPU throttling — surface jank

```typescript
test('Should_render_the_dashboard_within_budget_When_the_CPU_is_throttled_4x', async ({ page, cdp }) => {
  await cdp.cpuThrottle(4); // 4× slowdown ≈ a mid-tier mobile device

  await page.goto('/dashboard');

  await expect(page.getByTestId('dashboard-ready')).toBeVisible({ timeout: 15_000 });
});
```

Reset the rate to `1` if you keep one session across phases of a test; the fixture's fresh session per test makes that unnecessary here.

### Security-header audit from captured `Network.responseReceived`

Assert the document response carries the expected security headers. CDP header keys are **lowercased** by the protocol, so normalize the lookup. This is **one logical assertion** ("the response is securely configured") expressed as a few `expect.soft` checks so a run reports *every* missing header at once.

```typescript
// tests/fixtures/cdp/security.ts
import { expect } from '@playwright/test';
import { CapturedResponse } from './cdp';

const REQUIRED = ['content-security-policy', 'strict-transport-security', 'x-frame-options'] as const;

export function expectSecurityHeaders(response: CapturedResponse | undefined): void {
  expect(response, 'no response was captured for that URL').toBeDefined();
  const headers = Object.fromEntries(
    Object.entries(response!.headers).map(([k, v]) => [k.toLowerCase(), v]),
  );
  for (const name of REQUIRED) {
    expect.soft(headers[name], `${name} header is missing`).toBeDefined();
  }
}
```

```typescript
import { test, expect } from '../fixtures/cdp/cdp';
import { expectSecurityHeaders } from '../fixtures/cdp/security';

test('Should_send_CSP_HSTS_and_X_Frame_Options_When_the_app_shell_loads', async ({ page, cdp }) => {
  await page.goto('/');
  await expect(page.getByRole('navigation')).toBeVisible(); // shell loaded → its response was captured

  expectSecurityHeaders(cdp.responseFor((u) => u === page.url()));
});

test('Should_negotiate_TLS_1_3_for_the_document_When_loaded_over_HTTPS', async ({ page, cdp }) => {
  await page.goto('/');
  await expect(page.getByRole('navigation')).toBeVisible();

  const doc = cdp.responseFor((u) => u.startsWith('https://'));
  expect(doc?.securityDetails?.protocol).toBe('TLS 1.3'); // securityDetails: protocol, issuer, validFrom/To, sanList
});
```

### Performance budget from `Performance.getMetrics`

```typescript
test('Should_stay_under_the_layout_and_heap_budget_When_the_dashboard_renders', async ({ page, cdp }) => {
  await page.goto('/dashboard');
  await expect(page.getByTestId('dashboard-ready')).toBeVisible(); // a real "done" signal before sampling

  const metrics = await cdp.metrics();

  // One behavior — "the dashboard renders within budget" — verified by related metrics.
  expect.soft(metrics.get('LayoutCount') ?? Infinity, 'too many layouts').toBeLessThan(60);
  expect.soft((metrics.get('JSHeapUsedSize') ?? Infinity), 'JS heap too large').toBeLessThan(50 * 1024 * 1024);
});
```

Sample metrics **after** a user-visible "ready" signal, never after a sleep — otherwise the budget passes simply because the page hadn't finished rendering.

## Rules

### Session lifecycle
- Open with `page.context().newCDPSession(page)` and **`detach()` in fixture teardown** — a leaked session keeps emitting events and can outlive the page.
- Call `Network.enable` **before** registering `Network.responseReceived` or applying `emulateNetworkConditions`; call `Performance.enable` before `getMetrics`. A command on a disabled domain silently does nothing or throws.
- One session per page in the fixture; don't sprinkle extra `newCDPSession` calls through specs.

### Chromium-only
- `newCDPSession` **throws on Firefox/WebKit.** Gate the suite to the `chromium` project (config `projects` or `test.skip(({ browserName }) => browserName !== 'chromium', …)`). State the limitation in the spec, not just in your head.
- If a test must be cross-browser, it does not belong here — use `page.route` (`playwright-routes`) or an external `proxy`.

### Throttling & emulation
- `emulateNetworkConditions` throughput is **bytes/second**, latency is **milliseconds** — use the `NetworkPresets` constants, don't hand-roll raw numbers per spec.
- Apply throttle / cache-disable / CPU-throttle **before** the navigation or action that should feel it.
- `Emulation.setCPUThrottlingRate` `rate` is a **slowdown multiplier** (`1` = none); reset to `1` only if you reuse one session across test phases.

### Assertions & waits
- **No `page.waitForTimeout(ms)`.** Every wait is a Playwright web-first `expect(...).toBeVisible({ timeout })` on a real loading/ready signal, or driven by a captured CDP event. A longer `timeout` under throttling is a deadline, not a sleep.
- CDP response **header keys are lowercased** — normalize before lookup (`content-security-policy`, not `Content-Security-Policy`).
- A security-header / perf-budget check is **one logical assertion**; group its related `expect.soft` calls so the report lists every failure at once, rather than failing on the first.
- Sample `Performance.getMetrics` (and read captured responses) **after** a user-visible completion signal, never after a fixed delay.

### Hygiene
- Protocol method/event names are **strings** — a typo (`'Network.emulateNetworkCondition'`) fails at runtime, not compile time. Keep every `send`/`on` inside the typed `CdpControls` wrapper so the spelling lives in exactly one place.
- Don't reach for CDP when `page.route` would do — it's the more brittle, Chromium-only layer. Justify the drop.

### What NOT to do
- No `client.send('Domain.method', …)` / `client.on(...)` scattered through spec bodies — wrap it in the `cdp` fixture with an intent name.
- No CDP spec running on Firefox/WebKit — it throws; gate to `chromium`.
- No `page.waitForTimeout(ms)` to "wait for the slow load" — assert on the loading/ready element with a `timeout` deadline.
- No `emulateNetworkConditions` before `Network.enable`, no `getMetrics` before `Performance.enable`.
- No raw throughput numbers per spec — use `NetworkPresets`.
- No `Content-Security-Policy` cased lookup against CDP headers — they're lowercased.
- No leaked session — `detach()` in teardown.
- No CDP where `page.route` (cross-browser, typed) expresses the test just as well.

## Generation steps

1. Confirm **which hook** (throttle / cache / CPU / security audit / perf), that **Chromium-only is acceptable**, and **the signal** to assert.
2. Add or extend `tests/fixtures/cdp/cdp.ts` — open the session, `Network.enable`, capture `responseReceived`, expose intent methods (`throttle`, `disableCache`, `cpuThrottle`, `metrics`, `responseFor`), `detach()` in teardown.
3. Gate the spec to `chromium` (`test.skip(({ browserName }) => …)` or a project filter).
4. Apply the hook **before** the navigation/action; assert on a real loading/ready signal with a `timeout` deadline — never `waitForTimeout`.
5. For audits, normalize header case and use `expectSecurityHeaders`; for budgets, sample `metrics()` after a ready signal.
6. Run `npx playwright test --project=chromium`; inspect under `--ui` (the trace's Network tab shows the throttled timings). Run `tsc --noEmit` for strict-TS green.

## Cross-references

- **`qa/typescript/skills/network-monitoring`** — the **layer above**; reach for it first (cross-browser mock/abort/fulfill/assert, HAR, approximate offline). Drop to CDP only when routing can't express the test.
- **`qa/dotnet/skills/network-monitoring`** + **`qa/java/skills/network-monitoring`** — the sibling stacks porting this canonical TS skill into Playwright-for-.NET / -Java idioms.
- **`qa/typescript/skills/network-monitoring`** — out-of-browser MITM capture for cross-browser or non-Playwright (Appium/Selenium/native) stacks.
- **`qa/typescript/skills/ui-test-author/playwright`** — the fixture/page-object model these CDP fixtures layer on; the no-`waitForTimeout` discipline originates there.
- **`qa/typescript/skills/ci-pipelines`** — runs these specs (Chromium project only) sharded; traces on failure show throttled network timings.
