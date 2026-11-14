# Analytics and consent with Playwright Test (TypeScript / Playwright 1.64)

Built on the fixture model of `qa/typescript/skills/ui-test-author/playwright`. Verified against Playwright 1.63
on Chromium and WebKit: a `navigator.sendBeacon` to `/g/collect` is caught by `context.route` as a `POST` whose
`postData()` holds the beacon body, `waitForRequest` resolves for routed requests, `context.setExtraHTTPHeaders`
delivers `Sec-GPC: 1` to the server, and gtag's `arguments` entries in the `dataLayer` read back by index.

## 1. The fixtures

`analytics.fixtures.ts` extends the writer's `fixtures.ts`. Use `base` from `@playwright/test` merged with your
page-object fixtures if the project's `fixtures.ts` carries the auto `dismissConsent` handler.

```typescript
import type { Page, Request } from '@playwright/test';
import { test as base } from './fixtures';
import { CheckoutPage } from './CheckoutPage';
import { ConsentBanner } from './ConsentBanner';
import { HomePage } from './HomePage';

export type Destination = 'ga4' | 'meta-pixel';
export type Hit = {
  readonly destination: Destination;
  readonly eventName: string;
  readonly params: Readonly<Record<string, string>>;
};
export type ConsentState = Readonly<Record<string, string | number>>;
export type ConsentCommand = { readonly command: 'default' | 'update'; readonly state: ConsentState };
export type DataLayerEvent = { readonly event: string } & Readonly<Record<string, unknown>>;

const GA4_COLLECT = /\/g\/collect(\?|$)/;
const META_PIXEL = /^https:\/\/www\.facebook\.com\/tr\/?(\?|$)/;

function paramsOf(encoded: string): Record<string, string> {
  return Object.fromEntries(new URLSearchParams(encoded));
}

function ga4Hits(request: Request): Hit[] {
  const shared = paramsOf(new URL(request.url()).search);
  const lines = (request.postData() ?? '').split('\n').filter((line) => line.length > 0);
  const events = lines.length === 0 ? [shared] : lines.map((line) => ({ ...shared, ...paramsOf(line) }));
  return events.map((params) => ({ destination: 'ga4', eventName: params.en ?? '', params }));
}

function pixelHits(request: Request): Hit[] {
  const params = { ...paramsOf(new URL(request.url()).search), ...paramsOf(request.postData() ?? '') };
  return [{ destination: 'meta-pixel', eventName: params.ev ?? '', params }];
}

function hitsOf(request: Request): Hit[] {
  return GA4_COLLECT.test(request.url()) ? ga4Hits(request) : pixelHits(request);
}

export class Tracker {
  private readonly captured: Hit[] = [];

  constructor(private readonly page: Page) {}

  async capture(): Promise<void> {
    for (const beacon of [GA4_COLLECT, META_PIXEL]) {
      await this.page.context().route(beacon, async (route) => {
        this.captured.push(...hitsOf(route.request()));
        await route.fulfill({ status: 204 });
      });
    }
  }

  hits(): readonly Hit[] {
    return [...this.captured];
  }

  hitsTo(destination: Destination): readonly Hit[] {
    return this.captured.filter((hit) => hit.destination === destination);
  }

  async nextEvent(eventName: string, action: () => Promise<void>): Promise<Hit> {
    const [request] = await Promise.all([
      this.page.waitForRequest((sent) => hitsOf(sent).some((hit) => hit.eventName === eventName)),
      action(),
    ]);
    const hit = hitsOf(request).find((candidate) => candidate.eventName === eventName);
    if (hit === undefined) {
      throw new Error(`No ${eventName} event in ${request.method()} ${request.url()} body ${request.postData()}`);
    }
    return hit;
  }
}

export class DataLayer {
  constructor(private readonly page: Page) {}

  consentCommands(): Promise<ConsentCommand[]> {
    return this.page.evaluate(() =>
      (window.dataLayer ?? [])
        .filter((entry) => entry[0] === 'consent')
        .map((entry) => ({ command: entry[1], state: entry[2] })),
    );
  }

  eventsNamed(event: string): Promise<DataLayerEvent[]> {
    return this.page.evaluate((name) => (window.dataLayer ?? []).filter((entry) => entry.event === name), event);
  }
}

export class PrivacySignals {
  constructor(private readonly page: Page) {}

  async sendGlobalPrivacyControl(): Promise<void> {
    await this.page.context().setExtraHTTPHeaders({ 'Sec-GPC': '1' });
    await this.page.context().addInitScript(() =>
      Object.defineProperty(Navigator.prototype, 'globalPrivacyControl', { get: () => true, configurable: true }),
    );
  }
}

type AnalyticsFixtures = {
  tracker: Tracker;
  dataLayer: DataLayer;
  privacySignals: PrivacySignals;
  consentBanner: ConsentBanner;
  homePage: HomePage;
  checkoutPage: CheckoutPage;
  ga4TestId: string;
};

export const test = base.extend<AnalyticsFixtures>({
  tracker: async ({ page }, use) => {
    const tracker = new Tracker(page);
    await tracker.capture();
    await use(tracker);
  },
  dataLayer: async ({ page }, use) => {
    await use(new DataLayer(page));
  },
  privacySignals: async ({ page }, use) => {
    await use(new PrivacySignals(page));
  },
  consentBanner: async ({ page }, use) => {
    await use(new ConsentBanner(page));
  },
  homePage: async ({ page }, use) => {
    await use(new HomePage(page));
  },
  checkoutPage: async ({ page }, use) => {
    await use(new CheckoutPage(page));
  },
  ga4TestId: async ({}, use) => {
    const id = process.env.GA4_TEST_MEASUREMENT_ID;
    if (id === undefined) {
      throw new Error('Environment variable GA4_TEST_MEASUREMENT_ID is not set');
    }
    await use(id);
  },
});

export { expect } from './fixtures';
```

`window.dataLayer` needs a type once in the test project:

```typescript
declare global {
  interface Window {
    dataLayer?: Array<Record<string | number, unknown> & { event?: string }>;
  }
}
export {};
```

- **`tracker` is requested by every analytics test**, so capture is registered before the first navigation. A
  test that forgets it lets hits through to the network.
- **A GA4 request can carry several events.** Shared parameters sit in the URL; with a body, each line is one
  event's parameters. `ga4Hits` merges each line over the shared set. That shape is observed from gtag.js, not a
  published contract (SKILL.md, *Rules*).
- **The Meta Pixel** is read from its query string (`id`, `ev`, `cd[...]` custom data, the image-pixel format Meta
  documents) and any form body.
- **`gtag()` pushes an `arguments` object**, so a consent command reads as `entry[0..2]`; a GTM-style
  `dataLayer.push({ event })` reads as `entry.event`. Both shapes are covered.
- **The GPC init script stands in for a browser setting.** Chromium and WebKit expose no switch for it; the header
  plus the property is what a GPC browser sends. Call `sendGlobalPrivacyControl()` **before** the first navigation.

## 2. Consent gating

```typescript
import { expect, test } from './analytics.fixtures';

test.use({ storageState: { cookies: [], origins: [] } });

test('Should_SendNoTrackingRequest_When_VisitorHasNotChosen', async ({ tracker, homePage, consentBanner }) => {
  await homePage.open();
  await expect(consentBanner.root).toBeVisible();

  await homePage.openPricing();

  expect(tracker.hits()).toEqual([]);
});

test('Should_SendPageViewToTestProperty_When_VisitorAcceptsAll', async ({ tracker, homePage, consentBanner, ga4TestId }) => {
  await homePage.open();

  const pageView = await tracker.nextEvent('page_view', () => consentBanner.acceptAll());

  expect(pageView.params).toMatchObject({ en: 'page_view', tid: ga4TestId });
});

test('Should_SendNoTrackingRequest_When_VisitorRejectsAll', async ({ tracker, dataLayer, homePage, consentBanner }) => {
  await homePage.open();

  await consentBanner.rejectAll();
  await expect.poll(() => dataLayer.consentCommands()).toContainEqual(
    expect.objectContaining({ command: 'update', state: expect.objectContaining({ analytics_storage: 'denied' }) }),
  );
  await homePage.openPricing();

  expect(tracker.hits()).toEqual([]);
});

test('Should_DefaultEveryConsentModeV2TypeToDenied_When_PageLoads', async ({ tracker, dataLayer, homePage }) => {
  await homePage.open();

  await expect.poll(() => dataLayer.consentCommands()).toContainEqual({
    command: 'default',
    state: expect.objectContaining({
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied',
      analytics_storage: 'denied',
    }),
  });
});
```

- `test.use({ storageState: ... })` starts every consent test with no stored choice.
- `homePage.openPricing()` navigates and returns once the pricing page's landmark is visible: the second page load
  is the completion signal that gives a late tag time to fire, so the empty list means something.
- In **basic** Consent Mode no Google tag loads before the choice, so the first test's `[]` is the whole
  assertion. In **advanced** mode tags load denied and send cookieless pings: replace the `[]` test with §3.
- `expect.poll` re-reads the `dataLayer` until the expectation holds or the timeout fails the test — a wait on a
  condition, not a sleep. The `tracker` fixture is listed on the last test so capture is active even though it
  asserts no hit.

## 3. Advanced Consent Mode — the `gcs` value

Google documents `gcs` as carrying the `ad_storage` and `analytics_storage` choice, and `gcd` as the detailed
choice across all types. Their encodings are not published; record them from your own tag in each state and pin
those values as named constants.

```typescript
const GCS_ALL_DENIED = 'G100';
const GCS_ALL_GRANTED = 'G111';

test('Should_SendCookielessPing_When_ConsentIsDenied', async ({ tracker, homePage }) => {
  const pageView = await tracker.nextEvent('page_view', () => homePage.open());

  expect(pageView.params.gcs).toBe(GCS_ALL_DENIED);
});

test('Should_SendGrantedPing_When_VisitorAcceptsAll', async ({ tracker, homePage, consentBanner }) => {
  await homePage.open();

  const event = await tracker.nextEvent('user_engagement', () => consentBanner.acceptAll());

  expect(event.params.gcs).toBe(GCS_ALL_GRANTED);
});
```

The constants' values are the ones a gtag.js build was observed to send (`G1<ad_storage><analytics_storage>`,
1 = granted); confirm them against a hit you recorded before relying on them. Use the event your tag really sends
after an update — `user_engagement` here is an example.

## 4. An event and its parameters

```typescript
import { aPurchaseEvent } from './builders/PurchaseEventBuilder';

test('Should_SendPurchaseWithOrderTotal_When_OrderIsPlaced', async ({ tracker, checkoutPage, consentBanner }) => {
  await checkoutPage.open();
  await consentBanner.acceptAll();

  const purchase = await tracker.nextEvent('purchase', () => checkoutPage.placeOrder());

  expect(purchase.params).toMatchObject({ en: 'purchase', cu: 'EUR', 'epn.value': '68', 'ep.transaction_id': 'ORD-1001' });
});

test('Should_PushPurchaseToDataLayer_When_OrderIsPlaced', async ({ tracker, dataLayer, checkoutPage, consentBanner }) => {
  await checkoutPage.open();
  await consentBanner.acceptAll();

  await checkoutPage.placeOrder();

  await expect.poll(() => dataLayer.eventsNamed('purchase')).toEqual([aPurchaseEvent().withTotal(68, 'EUR').build()]);
});
```

- The beacon test pins the wire keys **you recorded** from your own tag — `cu`, `epn.value` and
  `ep.transaction_id` stand in for them here; replace them with what your hit shows. The `dataLayer` test pins the
  payload against the tracking plan's builder.
- `toEqual([...])` on the `dataLayer` also catches a **double push** — two purchases for one order fail the test.
- `aPurchaseEvent()` is a builder from `test-data-builder`; the purchase has more than four fields.

## 5. Global Privacy Control

```typescript
test('Should_SendNoAdPixel_When_GlobalPrivacyControlIsOn', async ({ tracker, privacySignals, homePage, consentBanner }) => {
  await privacySignals.sendGlobalPrivacyControl();
  await homePage.open();

  await consentBanner.acceptAll();
  await homePage.openPricing();

  expect(tracker.hitsTo('meta-pixel')).toEqual([]);
});

test('Should_KeepAdConsentDenied_When_GlobalPrivacyControlIsOn', async ({ tracker, privacySignals, dataLayer, homePage, consentBanner }) => {
  await privacySignals.sendGlobalPrivacyControl();
  await homePage.open();

  await consentBanner.acceptAll();

  await expect.poll(() => dataLayer.consentCommands()).toContainEqual({
    command: 'update',
    state: expect.objectContaining({ ad_user_data: 'denied', ad_personalization: 'denied' }),
  });
});
```

What GPC must switch off is a legal and product decision (an opt-out of sale or sharing under the applicable
law): take the expected outcome from the privacy requirements, never from the current behaviour.

## Anti-patterns

- `route.continue()` on a collect request — the hit reaches the real property. Fulfil it.
- `route.abort()` on a beacon you assert on — some tags retry or fall back, and the test reads the retry.
- Asserting only that `gtag.js` or `fbevents.js` loaded — that proves nothing was sent correctly.
- `page.waitForTimeout(2000)` before reading `tracker.hits()` — wait on a page signal, then read.
- Reading the hit list straight after the click that should *not* send anything — the request may not have
  started yet; load the next page first.
- A consent test that inherits a stored consent cookie or the auto-dismiss fixture.
