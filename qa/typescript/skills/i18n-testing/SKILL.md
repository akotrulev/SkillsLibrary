---
name: qa-i18n-testing-typescript
description: >-
  Write **internationalization (i18n) / localization tests** in Node 20 / TypeScript with Playwright (the
  locale-pinned UI half), Vitest (the formatting + bundle-coverage static half), the app's own i18next/FormatJS
  catalog, and the native `Intl` API. Covers the trait that makes i18n testing its own discipline: **you never
  assert a hardcoded literal string — the literal is exactly what changes per locale**. Instead you (1) **pin a
  locale** and assert the rendered DOM against the **same translation catalog the app ships, resolved by KEY**
  (`t('home.title', { lng })`), not an English copy; (2) assert dates/numbers/currency against
  `Intl.NumberFormat`/`Intl.DateTimeFormat` for that locale (with the timezone pinned), never a hardcoded
  `'1,234.56'`; (3) render in a **pseudo-locale** (`[!!! Ŵḗḷḉöṁḗ !!!]`, ~40% expanded) to surface **hardcoded
  strings** that bypassed i18n and **truncation/overflow**; and (4) assert **RTL** layout mirrors (`<html dir="rtl">`
  for `ar`/`he`) and run a **static translation-key-coverage** check (every source key present + non-empty in every
  target catalog, no orphans). Also covers ICU plural/select categories and a data-driven locale matrix. Triggers:
  "write an i18n test", "test that the app renders correctly in German/Arabic", "assert currency/date formatting
  per locale", "add pseudo-localization to CI", "check for missing translation keys", "test RTL layout". Do NOT
  use for: the Java stack (use qa-i18n-testing-java), the .NET stack (use qa-i18n-testing-dotnet), generic
  Playwright UI tests with no locale dimension (use qa-ui-test-author-playwright-typescript), pixel-diff visual
  regression in general (use qa-visual-regression-playwright-snapshots-typescript — though pseudo-loc overflow
  pairs with it), or translating the strings themselves (a content task, not a test).
---

# QA — i18n / Localization Testing (TypeScript / Playwright + Vitest + Intl)

Tests that a web app is correctly **internationalized** (the machinery — locale switching, formatting, layout,
catalog completeness) and **localized** (the right strings render per locale). It splits across two runners by
nature of the assertion: **Playwright** drives the app in a pinned locale for the UI-rendered checks, and
**Vitest** owns the pure-function checks (formatting math, pseudo-loc transforms, and the static catalog-coverage
diff that needs no browser). Both halves share one fact that makes i18n testing its own discipline: **the literal
string on screen is the variable, not the constant — so the assertion can never be a hardcoded literal.**

> **The discipline this skill encodes** — four ideas that separate a correct i18n test from a UI-test reflex:
>
> 1. **Pin the locale; assert against the catalog by KEY, never a hardcoded literal.** Drive the app with an
>    explicit locale and resolve the expected text from the **same catalog the app ships**
>    (`t('home.title', { lng: 'de' })`), not a copied-in literal. `expect(h).toHaveText('Willkommen')` breaks the
>    instant a copywriter rewords the German, and it only ever tests *one* language. `expect(h).toHaveText(t('home.title', { lng }))`
>    survives rewording and runs for **every** locale from one test body. (You assert the *rendered DOM* against
>    the catalog — proving the app wired the key to the screen. Asserting `t(key)` against `t(key)` is a
>    tautology; don't.)
> 2. **Format is locale-derived — assert via `Intl`, never a hardcoded format.** `1,234.56` (en) vs `1.234,56`
>    (de) vs `1 234,56` (fr); `$1,234.56` vs `1.234,56 €`; `3/14/2026` vs `14.03.2026`. Assert the rendered value
>    equals `new Intl.NumberFormat(locale, opts).format(n)` — **derive** the expectation from the same locale
>    data the app uses; don't hardcode a formatted string (which bakes in one locale and silently rots when CLDR
>    data updates). Pin the **timezone** too — `Intl.DateTimeFormat` is TZ-sensitive and a floating CI TZ makes
>    date tests flaky.
> 3. **Pseudo-localize to surface hardcoded + truncated strings — before any real translation exists.** A
>    pseudo-locale transforms source text into an accented, bracketed, ~40%-longer fake language
>    (`Welcome` → `[!!! Ŵḗḷḉöṁḗ !!!]`). It makes three bug classes visible *at test time, with no translators*:
>    (a) any **un-accented / un-bracketed** text on screen is a **hardcoded string** that bypassed i18n; (b)
>    **clipped or overflowing** text is a layout-too-tight bug the +40% expansion forces out; (c) broken
>    **concatenation** (`'Welcome ' + name`) shows up garbled. It's the cheap first gate that runs every CI build.
> 4. **RTL is a layout assertion; coverage is a static one — and they're separate from the text checks.** **RTL**
>    (`ar`/`he`) mirrors the *whole* UI — assert `<html dir="rtl">` and that logical-property layout actually
>    flipped, using a **real RTL locale**, not a CSS `direction` toggle. **Translation-key coverage** is a
>    **static** check (no browser): every key in the source catalog is present and **non-empty** in every target
>    catalog (missing key → silent English fallback in prod) and there are **no orphan** keys (dead translations).
>    The catalog diff is the cheapest, most deterministic i18n test there is — it gates the build.

## Decision matrix — i18n surface → test shape

| Surface | What you're proving | Runner | Test shape |
|---------|---------------------|--------|------------|
| **Locale-pinned UI text** | The right translation renders for a locale | Playwright | `use: { locale }` + app `lng` → `expect(el).toHaveText(t(key, { lng }))` |
| **Date / number / currency** | Locale-correct formatting | Playwright or Vitest | assert rendered === `Intl.NumberFormat`/`DateTimeFormat(locale, opts).format(v)`, **timezone pinned** |
| **Pseudo-localization** | No hardcoded strings; no truncation | Playwright | render in pseudo-locale → assert visible text wrapped in markers; screenshot for overflow |
| **RTL layout** | UI mirrors for RTL scripts | Playwright | `ar`/`he` locale → `expect(html).toHaveAttribute('dir', 'rtl')` + a mirrored-layout assertion |
| **Translation-key coverage** | Every catalog complete; no orphans | Vitest (static) | diff source keys vs each target: source ⊆ target, no empty values, no extra keys |
| **ICU plural / select** | Plurals & gender resolve per language | Vitest | format the message at count 0/1/2/5 → assert the right plural category renders |
| **Locale matrix** | All supported locales pass one journey | Playwright | data-driven over the supported-locale list → `qa-data-driven-testing-typescript` |

## Stack

- Node 20 + TypeScript (strict mode)
- **Playwright** (`@playwright/test`) — the locale-pinned UI half (`use: { locale, timezoneId }`)
- **Vitest** — the pure-function half: `Intl` formatting math, the pseudo-loc transform, the static catalog diff
- The app's **own catalog source** — i18next (`locales/{lng}/{ns}.json`) or FormatJS/react-intl. Tests import the
  **same** catalog the app ships, so a reworded string updates the test for free.
- Native **`Intl`** (`NumberFormat`, `DateTimeFormat`, `PluralRules`) for formatting expectations
- The **supported-locale list** comes from one config (`src/i18n/locales.ts`), reused by every locale-matrix test
- Locale + timezone set via Playwright project config / `use` — **never** hardcoded per test; one canonical
  pseudo-locale id (`en-XA`)

> **Why import the app's catalog instead of asserting literals?** The catalog is the single source of truth the
> app renders from. Importing it makes the test assert the *binding* (key → DOM) rather than the *content* (the
> English words) — so a copy change is a non-event, and the same test body runs across every locale. The one
> thing you must not do is compare the catalog to itself; the assertion's left side is always the **live DOM /
> formatted output**, the right side is the catalog/`Intl`.

## The catalog + a test-side resolver

The app ships JSON catalogs; the test imports them and exposes a tiny `t(key, { lng })` that mirrors i18next's
lookup (dot-path + interpolation). It is **not** a second translation system — it's a read-only view of the same
files, so the expected value always equals what the app loaded.

```typescript
// tests/i18n/catalog.ts
import en from '../../src/locales/en/common.json';
import de from '../../src/locales/de/common.json';
import ar from '../../src/locales/ar/common.json';

export const SUPPORTED_LOCALES = ['en', 'de', 'ar'] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

const catalogs: Record<Locale, Record<string, unknown>> = { en, de, ar };

/** Read-only mirror of i18next lookup: dot-path resolution + {{var}} interpolation. */
export function t(key: string, opts: { lng: Locale; vars?: Record<string, string> }): string {
  const raw = key.split('.').reduce<unknown>((node, seg) => (node as Record<string, unknown>)?.[seg], catalogs[opts.lng]);
  if (typeof raw !== 'string') throw new Error(`Missing key "${key}" for "${opts.lng}"`);
  return opts.vars
    ? raw.replace(/\{\{(\w+)\}\}/g, (_, name: string) => opts.vars![name] ?? `{{${name}}}`)
    : raw;
}

export const RTL_LOCALES = new Set<Locale>(['ar']);
```

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

## 2. Date / number / currency — assert via `Intl`, timezone pinned (idea #2)

Never hardcode `'1.234,56 €'`. Build the expectation from `Intl` for the locale under test — the same primitive
the app should be using — so the test tracks CLDR updates and proves the app passed the right options.

```typescript
// tests/specs/formatting.i18n.spec.ts
import { test, expect } from '../fixtures/i18n';

test('formats the cart total as locale currency', async ({ page, locale }) => {
  await page.goto('/cart');                          // seeded total: 1234.5 EUR
  const expected = new Intl.NumberFormat(localeTag(locale), {
    style: 'currency', currency: 'EUR',
  }).format(1234.5);                                 // en → "€1,234.50"; de → "1.234,50 €"
  await expect(page.getByTestId('cart-total')).toHaveText(expected);
});

test('formats the order date for the locale and pinned timezone', async ({ page, locale }) => {
  await page.goto('/orders/1');                       // order placed at a fixed ISO instant
  const expected = new Intl.DateTimeFormat(localeTag(locale), {
    dateStyle: 'long', timeZone: 'Europe/Berlin',     // pin TZ — DateTimeFormat is TZ-sensitive
  }).format(new Date('2026-03-14T09:00:00Z'));
  await expect(page.getByTestId('order-date')).toHaveText(expected);
});
```

```typescript
// pure-function variant (no browser) — assert a formatter utility directly in Vitest
import { describe, it, expect } from 'vitest';
import { formatPrice } from '../../src/i18n/format';

describe('formatPrice', () => {
  it.each([
    ['en-US', '€1,234.50'],
    ['de-DE', '1.234,50 €'],   // note the non-breaking space de uses before the symbol
    ['fr-FR', '1 234,50 €'],
  ])('formats EUR for %s', (tag, expected) => {
    expect(formatPrice(1234.5, tag, 'EUR')).toBe(expected);
  });
});
```

> Two gotchas the `Intl` approach catches and a hardcoded literal hides: locales use **non-breaking** (` `)
> and **narrow-no-break** (` `) spaces inside formatted numbers — copy-pasting a "looks right" literal uses a
> normal space and fails. And asserting against `Intl` means a Node/ICU upgrade that changes a format updates
> *both* sides together, instead of a literal silently drifting out of date.

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
> real locale exists. Pair the overflow check with `qa-visual-regression-playwright-snapshots-typescript` when
> you want a pixel record of the breakage, not just a boolean.

## 4a. RTL — assert the layout mirrors (idea #4)

Use a **real RTL locale** (`ar`), not a `direction: rtl` CSS hack — only a real locale exercises the app's own
direction logic, bidi handling, and mirrored icons.

```typescript
// tests/specs/rtl.i18n.spec.ts — runs under the `ar` project
import { test, expect, RTL_LOCALES } from '../fixtures/i18n';

test('mirrors the layout for an RTL locale', async ({ page, locale }) => {
  test.skip(!RTL_LOCALES.has(locale), 'RTL-only assertion');
  await page.goto('/');

  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');     // the document declares RTL
  // the nav sits on the right in RTL: its left edge is past the viewport midpoint
  const nav = page.getByRole('navigation');
  const box = await nav.boundingBox();
  const viewport = page.viewportSize()!;
  expect(box!.x).toBeGreaterThan(viewport.width / 2);
  // logical CSS resolved to a physical right-side margin
  await expect(nav).toHaveCSS('margin-inline-start', /.+/);
});
```

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

## ICU plurals & gender — assert the category, per language

English has two plural categories (one/other); Polish has four; Arabic has six. A correct test exercises the
**boundary counts** for the language, not just 1 and 2.

```typescript
// tests/specs/plurals.i18n.spec.ts
import { describe, it, expect } from 'vitest';
import { IntlMessageFormat } from 'intl-messageformat';

const msg = (lng: string) =>
  new IntlMessageFormat(
    '{count, plural, =0 {no items} one {# item} other {# items}}', lng,
  );

describe('item-count plural', () => {
  it.each([[0, 'no items'], [1, '1 item'], [2, '2 items'], [5, '5 items']])(
    'en renders count=%i as "%s"', (count, expected) => {
      expect(msg('en')(({ count }))).toBe(expected);   // exercises =0, one, other
    });

  it('uses PluralRules to know which categories a language needs', () => {
    // Arabic has 6 categories — a test that only checks 1 and 2 misses zero/few/many
    const cats = new Set([0, 1, 2, 3, 11, 100].map((n) => new Intl.PluralRules('ar').select(n)));
    expect(cats.size).toBeGreaterThan(2);              // proves the language needs more than one/other
  });
});
```

## Locale matrix — one journey across every supported locale

When a whole journey must pass in every locale, bind the supported-locale list as data rather than copy-pasting
the spec — this is `qa-data-driven-testing-typescript` applied to locales.

```typescript
import { SUPPORTED_LOCALES } from '../i18n/catalog';
import { test, expect } from '../fixtures/i18n';

for (const lng of SUPPORTED_LOCALES) {
  test(`checkout completes in ${lng}`, async ({ page, t }) => {
    test.use({ locale: lng });                          // or run via the per-locale Playwright projects
    await page.goto('/checkout');
    await page.getByRole('button', { name: t('checkout.pay') }).click();
    await expect(page.getByTestId('confirmation')).toHaveText(t('checkout.success'));
  });
}
```

## Anti-patterns

- **Asserting a hardcoded literal** (`toHaveText('Welcome')`). Breaks on any reword and only tests one language.
  *Fix:* `toHaveText(t('home.title', { lng }))` — resolve from the shipped catalog, by key.
- **Comparing the catalog to itself** (`expect(t('k')).toBe(t('k'))`). A tautology that tests nothing. *Fix:* the
  left side is always the **live DOM / formatted output**; the catalog is only ever the expected side.
- **Hardcoding a formatted number/date/currency** (`'1.234,56 €'`). Bakes in one locale, uses the wrong
  (non-breaking) spaces, and rots on a CLDR/ICU update. *Fix:* assert against `Intl.NumberFormat`/`DateTimeFormat`
  built for the locale under test.
- **Letting the CI timezone float for date assertions.** `Intl.DateTimeFormat` is TZ-sensitive → flaky across
  machines. *Fix:* pin `timeZone` in the formatter **and** `timezoneId` in the Playwright project.
- **Faking RTL with a `direction: rtl` CSS toggle.** Doesn't exercise the app's own direction logic, bidi, or
  mirrored assets. *Fix:* drive a real RTL locale (`ar`/`he`) and assert `<html dir="rtl">` + a mirrored-layout
  property.
- **Only checking that translation keys *exist*.** Misses empty values, orphan keys, and dropped interpolation
  placeholders. *Fix:* the static diff asserts presence **and** non-empty **and** no-orphans **and** identical
  `{{placeholders}}`.
- **Testing plurals at only count 1 and 2.** Misses zero/few/many categories that Polish, Russian, Arabic need.
  *Fix:* exercise the boundary counts the language actually has (drive from `Intl.PluralRules`).
- **String-concatenating translated fragments in the app, then asserting the result.** `t('welcome') + name`
  can't reorder for languages that put the name first. *Fix:* one interpolated key (`'Welcome, {{name}}'`); the
  pseudo-loc test surfaces the concatenation when the static part isn't wrapped.
- **Hardcoding the supported-locale list in each spec.** Drifts from the app's real list. *Fix:* import the one
  config; drive the matrix from it.

## Examples

**A reword that would break a literal-based suite is a non-event here.** Marketing changes the German CTA from
`„Jetzt kaufen"` to `„Sofort bestellen"`. A suite asserting the literal turns red across every German spec; this
suite re-reads `de/common.json` through `t('home.cta', { lng: 'de' })` and stays green — it was asserting that
the button is wired to `home.cta`, which is still true.

**Pseudo-loc catches the bug three other tests can't.** A developer hardcodes a `"Loading…"` spinner label
directly in JSX. The locale-pinned specs pass (the catalog is complete), the coverage diff passes (no key is
missing — there's no key at all), but the pseudo-loc spec fails: `"Loading…"` appears on screen *without*
brackets, so it's flagged as a string that bypassed i18n. That's the class of bug pseudo-localization exists to
find.

## Rules (hard constraints)

- **Never assert a hardcoded literal string.** The expected value is always resolved from the **app's own
  catalog** by key (`t(key, { lng })`) or computed via `Intl` — never copied in. And never compare the catalog to
  itself; the asserted side is the live DOM / formatted output.
- **Formatting is asserted via `Intl`** (`NumberFormat`/`DateTimeFormat`/`PluralRules`) for the locale under
  test, with the **timezone pinned** in both the formatter and the Playwright project.
- **Pseudo-localization is a required CI gate:** every visible string must be wrapped in the pseudo markers (an
  unwrapped string is a hardcoded leak), and no label may overflow its box under +40% expansion.
- **RTL uses a real RTL locale** and asserts `<html dir="rtl">` plus a mirrored-layout property — not a CSS
  toggle.
- **Translation-key coverage is a static, build-gating test:** source keys ⊆ each target, no empty values, no
  orphan keys, identical `{{placeholders}}`.
- **The supported-locale list comes from one config**, reused by every matrix test. Locale + timezone are set in
  Playwright project config, never hardcoded per test.
- **One logical assertion per test; no `waitForTimeout`/sleeps; `strict: true`.** Locale-matrix expansion uses
  data-driven iteration (`qa-data-driven-testing-typescript`), never copy-paste.

## Cross-references

- `qa-i18n-testing-java` · `qa-i18n-testing-dotnet` — the sibling stacks (Playwright-Java + TestNG + ICU4J /
  `ResourceBundle` · Playwright .NET + NUnit + `CultureInfo` / `.resx`); same four ideas, different catalog +
  formatting APIs.
- `qa-ui-test-author-playwright-typescript` — the base Playwright/page-object/fixture conventions this builds on;
  i18n adds the locale dimension on top. Read it for the fixture + locator idioms.
- `qa-visual-regression-playwright-snapshots-typescript` (#17) — pairs with the pseudo-loc **overflow** check: a
  pixel diff records *how* the layout broke when text expanded; this skill asserts *that* it didn't.
- `qa-data-driven-testing-typescript` (#39) — the locale matrix is its row-binding pattern applied to the
  supported-locale list.
- `qa-accessibility-testing-axe-playwright-typescript` (#20) — RTL + language correctness overlaps with the
  `html[lang]` / `dir` a11y rules; run them together on the locale-pinned page.
- `qa-allure-reporting-typescript` — render each locale (and the pseudo-locale) as a named result / Allure
  parameter so a failure says *which* language broke.
