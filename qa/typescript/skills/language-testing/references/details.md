# Deep-dive details — `qa-typescript:language-testing`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## 1. The i18n fixtures, the locale projects and locale-pinned UI text (idea #1)

Pin the locale at the Playwright level **and** tell the app which language to load (a `?lng=` query, a cookie,
or a `localStorage` seed — match your app). `lng` is an **option fixture** — the catalog and app language a
project sets — beside Playwright's own `locale` (the BCP-47 tag) and `timezoneId`. The fixture also freezes
"now" before the page loads, and exposes the page objects and the measuring helper the specs use.

```typescript
import type { Locator, Page } from '@playwright/test';
import { type AppLanguage, t as translate } from '../i18n/catalog';
import { test as base } from '../fixtures';

export const FROZEN_NOW = new Date('2026-03-14T09:00:00Z');

export type I18nOptions = { lng: AppLanguage };

export class HomePage {
  readonly document: Locator;
  readonly heading: Locator;
  readonly navigation: Locator;

  constructor(private readonly page: Page) {
    this.document = page.locator('html');
    this.heading = page.getByRole('heading', { level: 1 });
    this.navigation = page.getByRole('navigation');
  }

  async goto(): Promise<void> {
    await this.page.goto('/');
  }

  action(name: string): Locator {
    return this.page.getByRole('button', { name });
  }
}

export class CartPage {
  readonly total: Locator;

  constructor(private readonly page: Page) {
    this.total = page.getByTestId('Cart.Total');
  }

  async goto(): Promise<void> {
    await this.page.goto('/cart');
  }
}

export class OrderPage {
  readonly placedOn: Locator;
  readonly age: Locator;

  constructor(private readonly page: Page) {
    this.placedOn = page.getByTestId('Order.PlacedOn');
    this.age = page.getByTestId('Order.Age');
  }

  async goto(): Promise<void> {
    await this.page.goto('/orders/1');
  }
}

export class CheckoutPage {
  readonly submit: Locator;
  readonly confirmation: Locator;

  constructor(private readonly page: Page) {
    this.submit = page.getByTestId('Checkout.Submit');
    this.confirmation = page.getByTestId('Checkout.Confirmation');
  }

  async goto(): Promise<void> {
    await this.page.goto('/checkout');
  }

  async pay(): Promise<void> {
    await this.submit.click();
  }
}

export class TextAudit {
  constructor(private readonly page: Page) {}

  async visibleTexts(): Promise<string[]> {
    const texts = await this.page.getByText(/\S/).allInnerTexts();
    return texts.map((text) => text.trim());
  }

  async overflowPx(locator: Locator): Promise<number> {
    return locator.evaluate((element) => element.scrollWidth - element.clientWidth);
  }

  async leftEdgeRatio(locator: Locator): Promise<number> {
    const box = await locator.boundingBox();
    const viewport = this.page.viewportSize();
    if (box === null || viewport === null) {
      throw new Error(`${locator} is not rendered, or the page has no fixed viewport`);
    }
    return box.x / viewport.width;
  }
}

function required(value: string | undefined, option: string): string {
  if (value === undefined) throw new Error(`use.${option} is not set for this project`);
  return value;
}

type I18nFixtures = {
  t: (key: string, vars?: Record<string, string>) => string;
  tag: string;
  zone: string;
  homePage: HomePage;
  cartPage: CartPage;
  orderPage: OrderPage;
  checkoutPage: CheckoutPage;
  textAudit: TextAudit;
};

export const test = base.extend<I18nFixtures & I18nOptions>({
  lng: ['en', { option: true }],
  t: async ({ lng }, use) => {
    await use((key, vars) => translate(key, { lng, vars }));
  },
  tag: async ({ locale }, use) => {
    await use(required(locale, 'locale'));
  },
  zone: async ({ timezoneId }, use) => {
    await use(required(timezoneId, 'timezoneId'));
  },
  page: async ({ page, lng }, use) => {
    await page.addInitScript((language) => window.localStorage.setItem('i18nextLng', language), lng);
    await page.clock.setFixedTime(FROZEN_NOW);
    await use(page);
  },
  homePage: async ({ page }, use) => {
    await use(new HomePage(page));
  },
  cartPage: async ({ page }, use) => {
    await use(new CartPage(page));
  },
  orderPage: async ({ page }, use) => {
    await use(new OrderPage(page));
  },
  checkoutPage: async ({ page }, use) => {
    await use(new CheckoutPage(page));
  },
  textAudit: async ({ page }, use) => {
    await use(new TextAudit(page));
  },
});

export { expect } from '../fixtures';
```

`tests/fixtures/i18n.ts`. The `page` override seeds the app language with an init script (it runs before the
app's own scripts on every navigation) and freezes the clock, both before any `goto`.

```typescript
import { defineConfig } from '@playwright/test';
import type { I18nOptions } from './tests/fixtures/i18n';

export default defineConfig<I18nOptions>({
  testMatch: /.*\.i18n\.spec\.ts/,
  use: { baseURL: process.env.BASE_URL },
  projects: [
    { name: 'en', use: { lng: 'en', locale: 'en-US', timezoneId: 'America/New_York' }, grepInvert: /@rtl|@pseudo/ },
    { name: 'de', use: { lng: 'de', locale: 'de-DE', timezoneId: 'Europe/Berlin' }, grepInvert: /@rtl|@pseudo/ },
    { name: 'ar', use: { lng: 'ar', locale: 'ar-EG', timezoneId: 'Africa/Cairo' }, grepInvert: /@pseudo/ },
    { name: 'pseudo', use: { lng: 'en-XA', locale: 'en-US', timezoneId: 'UTC' }, grep: /@pseudo/ },
  ],
});
```

`playwright.config.ts` for the i18n suite (or its projects, merged into the canonical config). Tags choose
which specs a project runs: RTL specs only under `ar`, pseudo specs only under `pseudo`. The pseudo project keeps a
real browser locale (`en-US`); only the app language is the pseudo one.

```typescript
import { expect, test } from '../fixtures/i18n';

test('Should_RenderHomeHeadingFromCatalog_When_LocaleIsActive', async ({ homePage, t }) => {
  await homePage.goto();

  await expect(homePage.heading).toHaveText(t('home.title'));
});

test('Should_LabelCallToActionFromCatalog_When_LocaleIsActive', async ({ homePage, t }) => {
  await homePage.goto();

  await expect(homePage.action(t('home.cta'))).toBeVisible();
});
```

`tests/specs/home.i18n.spec.ts`. This one spec, run under the `en`/`de`/`ar` projects, covers three languages
with no per-locale literals. A reworded string in `de/common.json` updates the expectation automatically — the
test asserts the **wiring**, not the **words**.

## 3. Pseudo-localization — surface hardcoded strings and truncation (idea #3)

Generate a pseudo-locale catalog by transforming every source value: accent the letters, expand ~40%, and wrap
in sentinel brackets, leaving `{{vars}}` and ICU `{…}` placeholders untouched. Load it as the app language
`en-XA`. Then **every visible string must be wrapped** — an unwrapped string is hardcoded and bypassed i18n.

```typescript
const ACCENTS: Record<string, string> = { a: 'á', e: 'ḗ', i: 'í', o: 'ö', u: 'ṵ', c: 'ḉ', l: 'ḷ', m: 'ṁ', w: 'ŵ' };
export const PSEUDO_OPEN = '[!! ';
export const PSEUDO_CLOSE = ' !!]';

export function pseudoLocalize(text: string): string {
  const accented = text.replace(/\{\{.*?\}\}|\{.*?\}|[a-z]/gi, (match) =>
    match.startsWith('{') ? match : (ACCENTS[match.toLowerCase()] ?? match));
  const pad = '~'.repeat(Math.ceil(accented.replace(/\s/g, '').length * 0.4));
  return `${PSEUDO_OPEN}${accented}${pad}${PSEUDO_CLOSE}`;
}
```

`tests/i18n/pseudo.ts` — a deterministic source→pseudo transform, run as a build step that writes the `en-XA`
catalog.

```typescript
import { expect, test } from '../fixtures/i18n';
import { PSEUDO_CLOSE, PSEUDO_OPEN } from '../i18n/pseudo';

const isWrapped = (text: string) => text.length <= 1 || (text.includes(PSEUDO_OPEN) && text.includes(PSEUDO_CLOSE));

test('Should_ShowNoUnwrappedText_When_CheckoutRendersInPseudoLocale', { tag: '@pseudo' }, async ({ checkoutPage, textAudit }) => {
  await checkoutPage.goto();

  await expect.poll(async () => (await textAudit.visibleTexts()).filter((text) => !isWrapped(text))).toEqual([]);
});

test('Should_NotClipSubmitLabel_When_TextExpandsByFortyPercent', { tag: '@pseudo' }, async ({ checkoutPage, textAudit }) => {
  await checkoutPage.goto();

  await expect.poll(() => textAudit.overflowPx(checkoutPage.submit)).toBeLessThanOrEqual(1);
});
```

`tests/specs/pseudo.i18n.spec.ts`. The first test's failure message lists the leaked strings; the second
reports how many pixels the label overflows (`scrollWidth - clientWidth`), never a bare `false`.

> Pseudo-loc needs **zero translators**, so it's the first i18n gate you can run — wire it into CI before any
> real locale exists. Pair the overflow check with `qa-typescript:visual-regression` when you want a pixel
> record of the breakage.

## 4b. Translation-key coverage — a static catalog diff (idea #4)

No browser, no app — just compare the JSON catalogs. This is the highest-value, cheapest, most deterministic
i18n test. Run it in Vitest and gate the build on it. `flatten` turns the nested catalog into dot-path → value,
so the comparison is order-independent.

```typescript
import { describe, expect, it } from 'vitest';
import ar from '../../src/locales/ar/common.json';
import de from '../../src/locales/de/common.json';
import en from '../../src/locales/en/common.json';

function flatten(catalog: Record<string, unknown>, prefix = ''): Record<string, string> {
  return Object.entries(catalog).reduce<Record<string, string>>((flat, [key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return value !== null && typeof value === 'object'
      ? { ...flat, ...flatten(value as Record<string, unknown>, path) }
      : { ...flat, [path]: String(value) };
  }, {});
}

const placeholders = (text: string) => (text.match(/\{\{.*?\}\}/g) ?? []).sort().join();
const source = flatten(en);
const targets = Object.entries({ de: flatten(de), ar: flatten(ar) });

describe.each(targets)('catalog %s', (lng, target) => {
  it('Should_HaveEverySourceKey_When_ComparedToEnglish', () => {
    expect(Object.keys(source).filter((key) => !(key in target)), `${lng} is missing keys`).toEqual([]);
  });

  it('Should_HaveNoEmptyValues_When_Translated', () => {
    expect(Object.keys(target).filter((key) => target[key].trim() === ''), `${lng} has empty entries`).toEqual([]);
  });

  it('Should_HaveNoOrphanKeys_When_ComparedToEnglish', () => {
    expect(Object.keys(target).filter((key) => !(key in source)), `${lng} has orphan keys`).toEqual([]);
  });

  it('Should_KeepSourcePlaceholders_When_Translated', () => {
    const drifted = Object.keys(source).filter((key) => key in target && placeholders(source[key]) !== placeholders(target[key]));
    expect(drifted, `${lng} placeholder mismatch`).toEqual([]);
  });
});
```

`tests/specs/coverage.i18n.test.ts`. The placeholder check catches the bug a key-presence check misses: a
translator who renders `Welcome back, {{name}}` as `Bienvenue` leaves the key *present* but breaks
interpolation.

## 5. ICU plurals & gender — assert the category, per language

English has two plural categories (one/other); Polish has four; Arabic has six. Exercise the **boundary counts**
for the language, not just 1 and 2.

```typescript
import { IntlMessageFormat } from 'intl-messageformat';
import { expect, it } from 'vitest';

const itemCount = new IntlMessageFormat('{count, plural, =0 {no items} one {# item} other {# items}}', 'en');

it.for([
  { count: 0, expected: 'no items' },
  { count: 1, expected: '1 item' },
  { count: 2, expected: '2 items' },
  { count: 5, expected: '5 items' },
])('Should_Render "$expected"_When_CountIs $count', ({ count, expected }) => {
  expect(itemCount.format({ count })).toBe(expected);
});

it('Should_NeedSixPluralCategories_When_LanguageIsArabic', () => {
  const categories = new Set([0, 1, 2, 3, 11, 100].map((n) => new Intl.PluralRules('ar').select(n)));

  expect(categories.size).toBe(6);
});
```

`tests/specs/plurals.i18n.test.ts`. `Intl.PluralRules(lng).resolvedOptions().pluralCategories` lists what a
language needs — drive each catalog's plural rows from it.

## 6. Locale matrix — one journey across every supported locale

The locale projects are the matrix: a spec with no tag runs once per locale project, so a journey written once
covers every supported language. Bind the list as data, never copy-paste the spec.

```typescript
import { expect, test } from '../fixtures/i18n';

test('Should_ConfirmPaymentInActiveLocale_When_CustomerPays', async ({ checkoutPage, t }) => {
  await checkoutPage.goto();

  await checkoutPage.pay();

  await expect(checkoutPage.confirmation).toHaveText(t('checkout.success'));
});
```

When one spec must cover locales outside the project list, generate a `describe` per locale and set the
options there — `test.use` is allowed in a `describe`, never inside a test:

```typescript
import { SUPPORTED_LOCALES } from '../i18n/catalog';
import { expect, test } from '../fixtures/i18n';

const LOCALE_TAGS = { en: 'en-US', de: 'de-DE', ar: 'ar-EG' } as const;

for (const lng of SUPPORTED_LOCALES) {
  test.describe(lng, () => {
    test.use({ lng, locale: LOCALE_TAGS[lng], timezoneId: 'UTC' });

    test(`Should_ConfirmPayment_When_CustomerPaysIn ${lng}`, async ({ checkoutPage, t }) => {
      await checkoutPage.goto();

      await checkoutPage.pay();

      await expect(checkoutPage.confirmation).toHaveText(t('checkout.success'));
    });
  });
}
```

The `for` generates one independent, individually-named test per locale outside every test body — the
sanctioned parameterization (`qa-typescript:data-driven-testing`).
