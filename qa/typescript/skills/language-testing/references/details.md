# Deep-dive details — `qa-language-testing-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## 1. Locale-pinned UI text — assert the DOM against the catalog (idea #1)

Pin the locale at the Playwright level **and** tell the app which language to load (a `?lng=` query, a cookie, or
a `localStorage` seed — match your app). Then assert the rendered text equals the catalog entry, by key.

```typescript
// tests/fixtures/i18n.ts — a fixture that pins the locale and exposes the catalog resolver
import { test as base, expect } from '@playwright/test';
import { t as translate, Locale, RTL_LOCALES } from '../i18n/catalog';

type I18nFixtures = {
  locale: Locale;                                   // overridden per project (see playwright.config)
  t: (key: string, vars?: Record<string, string>) => string;
};

export const test = base.extend<I18nFixtures>({
  locale: ['en', { option: true }],                 // set per Playwright project
  t: async ({ locale }, use) => {
    await use((key, vars) => translate(key, { lng: locale, vars }));
  },
  page: async ({ page, locale }, use) => {
    await page.addInitScript((lng) => localStorage.setItem('i18nextLng', lng), locale);  // app reads this on boot
    await use(page);
  },
});

export { expect, RTL_LOCALES };
```

```typescript
// playwright.config.ts (excerpt) — one project per locale, locale + timezone pinned
export default defineConfig({
  projects: [
    { name: 'en', use: { locale: 'en-US', timezoneId: 'America/New_York' } },
    { name: 'de', use: { locale: 'de-DE', timezoneId: 'Europe/Berlin' } },
    { name: 'ar', use: { locale: 'ar-EG', timezoneId: 'Africa/Cairo' } },
    { name: 'pseudo', use: { locale: 'en-XA', timezoneId: 'UTC' } },
  ],
});
```

```typescript
// tests/specs/home.i18n.spec.ts
import { test, expect } from '../fixtures/i18n';

test('renders the home heading in the active locale', async ({ page, t }) => {
  await page.goto('/');
  // left side = live DOM; right side = the SAME catalog the app shipped — resolved by KEY, per locale
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(t('home.title'));
  await expect(page.getByRole('button', { name: t('home.cta') })).toBeVisible();
});

test('interpolates the greeting with the user name, per locale', async ({ page, t }) => {
  await page.goto('/dashboard');
  // de: "Willkommen zurück, {{name}}" / en: "Welcome back, {{name}}" — assert the interpolated catalog string
  await expect(page.getByTestId('greeting')).toHaveText(t('dashboard.greeting', { name: 'Trinity' }));
});
```

> This one spec, run under the `en`/`de`/`ar` projects, covers three languages with no per-locale literals. A
> reworded string in `de/common.json` updates the expectation automatically — the test asserts the **wiring**,
> not the **words**.

## 3. Pseudo-localization — surface hardcoded strings and truncation (idea #3)

Generate a pseudo-locale catalog by transforming every source value: accent the letters, expand ~40%, and wrap
in sentinel brackets. Load it as a real locale (`en-XA`). Then **every visible string must be wrapped** — an
unwrapped string is hardcoded and bypassed i18n.

```typescript
// tests/i18n/pseudo.ts — deterministic source→pseudo transform (run as a build step or in a fixture)
const MAP: Record<string, string> = { a: ' á', e: 'ḗ', i: ' í', o: 'ö', u: 'ṵ', c: 'ḉ', l: 'ḷ', m: 'ṁ', w: 'ŵ' };
export const PSEUDO_OPEN = '[!! ';
export const PSEUDO_CLOSE = ' !!]';

/** Accent + ~40% pad + bracket-wrap, leaving {{vars}} and ICU {…} placeholders untouched. */
export function pseudoLocalize(text: string): string {
  const accented = text.replace(/\{\{.*?\}\}|\{.*?\}|[a-z]/gi, (m) =>
    m.startsWith('{') ? m : (MAP[m.toLowerCase()] ?? m));
  const pad = '~'.repeat(Math.ceil(accented.replace(/\s/g, '').length * 0.4));
  return `${PSEUDO_OPEN}${accented}${pad}${PSEUDO_CLOSE}`;
}
```

```typescript
// tests/specs/pseudo.i18n.spec.ts — runs under the `pseudo` project
import { test, expect } from '../fixtures/i18n';
import { PSEUDO_OPEN, PSEUDO_CLOSE } from '../i18n/pseudo';

test('every visible string went through i18n (no hardcoded text)', async ({ page }) => {
  await page.goto('/checkout');
  // collect on-screen text that the user can read
  const texts = await page.getByText(/\S/).allInnerTexts();
  const leaks = texts
    .map((s) => s.trim())
    .filter((s) => s.length > 1 && !(s.includes(PSEUDO_OPEN) || s.includes(PSEUDO_CLOSE)));
  expect(leaks, `hardcoded strings bypassing i18n: ${JSON.stringify(leaks)}`).toEqual([]);
});

test('no label is clipped under +40% text expansion', async ({ page }) => {
  await page.goto('/checkout');
  const submit = page.getByTestId('submit');
  // scrollWidth > clientWidth means the text overflows its box — a real truncation bug
  const clipped = await submit.evaluate((el) => el.scrollWidth > el.clientWidth + 1);
  expect(clipped, 'submit button truncates its label').toBe(false);
});
```

> Pseudo-loc needs **zero translators**, so it's the first i18n gate you can run — wire it into CI before any
> real locale exists. Pair the overflow check with `qa-visual-regression-typescript` when
> you want a pixel record of the breakage, not just a boolean.

## 4b. Translation-key coverage — a static catalog diff (idea #4)

No browser, no app — just compare the JSON catalogs. This is the highest-value, cheapest, most deterministic
i18n test. Run it in Vitest and gate the build on it.

```typescript
// tests/specs/coverage.i18n.spec.ts
import { describe, it, expect } from 'vitest';
import en from '../../src/locales/en/common.json';
import de from '../../src/locales/de/common.json';
import ar from '../../src/locales/ar/common.json';

/** flatten nested catalog to dot-path → value, so comparison is order-independent */
function flatten(obj: Record<string, unknown>, prefix = ''): Record<string, string> {
  return Object.entries(obj).reduce<Record<string, string>>((acc, [k, v]) => {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object') Object.assign(acc, flatten(v as Record<string, unknown>, key));
    else acc[key] = String(v);
    return acc;
  }, {});
}

const source = flatten(en);
const targets = { de: flatten(de), ar: flatten(ar) };

describe.each(Object.entries(targets))('catalog coverage: %s', (lng, target) => {
  it('has no MISSING keys (would fall back to English in prod)', () => {
    const missing = Object.keys(source).filter((k) => !(k in target));
    expect(missing, `${lng} is missing: ${missing.join(', ')}`).toEqual([]);
  });

  it('has no EMPTY values (placeholder, not a translation)', () => {
    const empty = Object.entries(target).filter(([, v]) => v.trim() === '').map(([k]) => k);
    expect(empty, `${lng} has empty entries: ${empty.join(', ')}`).toEqual([]);
  });

  it('has no ORPHAN keys (translated but no longer used)', () => {
    const orphans = Object.keys(target).filter((k) => !(k in source));
    expect(orphans, `${lng} has orphan keys: ${orphans.join(', ')}`).toEqual([]);
  });

  it('keeps interpolation placeholders identical to the source', () => {
    const placeholders = (s: string) => (s.match(/\{\{.*?\}\}/g) ?? []).sort();
    const drifted = Object.keys(source).filter(
      (k) => k in target && placeholders(source[k]).join() !== placeholders(target[k]).join(),
    );
    expect(drifted, `${lng} placeholder mismatch: ${drifted.join(', ')}`).toEqual([]);
  });
});
```

> The placeholder check catches the subtle bug a key-presence check misses: a translator who renders
> `Welcome back, {{name}}` as `Bienvenue` (dropping `{{name}}`) leaves the key *present* but breaks
> interpolation. Assert the placeholder set is identical on both sides.
