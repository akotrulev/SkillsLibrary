---
name: language-testing
description: Use when writing i18n/localization tests in Node / TypeScript — Playwright pinned to a locale, asserting via the app's i18next/FormatJS catalog by key (never hardcoded literals), native `Intl` for number/date/currency formats, pseudo-localization and RTL checks. Triggers: "write an i18n test", "test German/Arabic rendering", "assert currency formatting per locale". Not for the app's own localization wiring (`fe-react:i18n`) or breakpoint layout (`qa-typescript:responsive-testing`).
---

# QA — i18n / Localization Testing (TypeScript / Playwright 1.64 + Vitest + Intl)

Tests that a web app is correctly **internationalized** (the machinery — locale switching, formatting, layout,
catalog completeness) and **localized** (the right strings render per locale). It splits across two runners by
nature of the assertion: **Playwright** drives the app in a pinned locale for the UI-rendered checks, and
**Vitest** owns the pure-function checks (formatting math, pseudo-loc transforms, and the static catalog-coverage
diff that needs no browser). Both halves share one fact that makes i18n testing its own discipline: **the literal
string on screen is the variable, not the constant — so the assertion can never be a hardcoded literal.**

> **The discipline this skill encodes** — four ideas that separate a correct i18n test from a UI-test reflex:
>
> 1. **Pin the locale; assert against the catalog by KEY, never a hardcoded literal.** Drive the app with an
>    explicit locale and resolve the expected text from the **same catalog the app ships** (`t('home.title')`),
>    not a copied-in literal. `toHaveText('Willkommen')` breaks the instant a copywriter rewords the German, and
>    only ever tests *one* language; `toHaveText(t('home.title'))` survives rewording and runs for **every**
>    locale from one test body. (Asserting `t(key)` against `t(key)` is a tautology; don't.)
> 2. **Format is locale-derived — assert via `Intl`, never a hardcoded format.** `1,234.56` (en) vs `1.234,56`
>    (de) vs `1 234,56` (fr); `3/14/2026` vs `14.03.2026`. **Derive** the expectation from `Intl` for the locale
>    under test; a hardcoded string bakes in one locale and rots when CLDR data updates. Pin the **timezone**
>    (`Intl.DateTimeFormat` is TZ-sensitive) and **freeze "now"** with `page.clock`, so "today", "3 days ago"
>    and every default date render the same on every run.
> 3. **Pseudo-localize to surface hardcoded + truncated strings — before any real translation exists.** A
>    pseudo-locale transforms source text into an accented, bracketed, ~40%-longer fake language. Any
>    **un-bracketed** text on screen is a **hardcoded string**; **clipped** text is a layout-too-tight bug the
>    expansion forces out; broken **concatenation** shows up garbled. It's the cheap first gate on every build.
> 4. **RTL is a layout assertion; coverage is a static one.** **RTL** (`ar`/`he`) mirrors the *whole* UI —
>    assert `<html dir="rtl">` and that the layout flipped, using a **real RTL locale**. **Translation-key
>    coverage** is a **static** check (no browser): every source key is present and **non-empty** in every
>    target catalog, and there are **no orphan** keys. It gates the build.

## Decision matrix — i18n surface → test shape

| Surface | What you're proving | Runner | Test shape |
|---------|---------------------|--------|------------|
| **Locale-pinned UI text** | The right translation renders for a locale | Playwright | project `use: { lng, locale }` → `toHaveText(t(key))` |
| **Date / number / currency** | Locale-correct formatting | Playwright or Vitest | rendered === `Intl.NumberFormat`/`DateTimeFormat(tag, opts).format(v)`, **timezone pinned** |
| **"Now"-relative text** | "Today", "3 days ago", default dates | Playwright | `page.clock.setFixedTime(FROZEN_NOW)` in the fixture → `Intl.RelativeTimeFormat` / `DateTimeFormat` |
| **Pseudo-localization** | No hardcoded strings; no truncation | Playwright | `pseudo` project → no visible text without the markers; overflow measured per label |
| **RTL layout** | UI mirrors for RTL scripts | Playwright | `ar` project → `<html dir="rtl">` + a mirrored-layout measurement |
| **Translation-key coverage** | Every catalog complete; no orphans | Vitest (static) | source keys ⊆ each target, no empty values, no extra keys, same placeholders |
| **ICU plural / select** | Plurals resolve per language | Vitest | format at the language's boundary counts |
| **Locale matrix** | All supported locales pass one journey | Playwright | one project per locale |

## Stack

- Node 24 (22 maintenance) + TypeScript (strict mode)
- **Playwright** — the locale-pinned UI half. This skill pins nothing: the version is the **Versions** table of
  `qa/typescript/skills/ui-test-author/playwright/SKILL.md`; locale, time zone and the full `page.clock` API are
  its `references/emulation-and-mobile-web.md` §5–§6
- **Vitest** — the pure-function half: `Intl` formatting math, the pseudo-loc transform, the static catalog diff
- The app's **own catalog source** — i18next (`locales/{lng}/{ns}.json`) or FormatJS/react-intl, imported by the
  tests, so a reworded string updates the test for free
- Native **`Intl`** (`NumberFormat`, `DateTimeFormat`, `RelativeTimeFormat`, `PluralRules`) for expectations
- Per locale project: `lng` (the catalog and app language), `locale` (the BCP-47 tag the browser and `Intl` use)
  and `timezoneId` — **never** set per test. One canonical pseudo-locale id (`en-XA`)
- Specs reach the app through page objects and the i18n fixtures (`references/details.md` §1), never raw
  `page.` calls

## The catalog + a test-side resolver

The test imports the app's catalogs and exposes a tiny `t(key, { lng })` that mirrors i18next's lookup (dot-path
+ interpolation) — a read-only view of the same files, not a second translation system. The pseudo-locale has
no catalog, so `t` throws for it: pseudo specs assert markers, never keys.

```typescript
import ar from '../../src/locales/ar/common.json';
import de from '../../src/locales/de/common.json';
import en from '../../src/locales/en/common.json';

export const SUPPORTED_LOCALES = ['en', 'de', 'ar'] as const;
export const PSEUDO_LOCALE = 'en-XA';
export type Locale = (typeof SUPPORTED_LOCALES)[number];
export type AppLanguage = Locale | typeof PSEUDO_LOCALE;

const catalogs: Partial<Record<AppLanguage, Record<string, unknown>>> = { en, de, ar };

export function t(key: string, opts: { lng: AppLanguage; vars?: Record<string, string> }): string {
  const raw = key
    .split('.')
    .reduce<unknown>((node, segment) => (node as Record<string, unknown> | undefined)?.[segment], catalogs[opts.lng]);
  if (typeof raw !== 'string') throw new Error(`Missing key "${key}" for "${opts.lng}"`);
  return raw.replace(/\{\{(\w+)\}\}/g, (match, name: string) => opts.vars?.[name] ?? match);
}
```

`tests/i18n/catalog.ts`.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **1. The i18n
fixtures, the locale projects and locale-pinned UI text (idea #1)**; **3. Pseudo-localization (idea #3)**;
**4b. Translation-key coverage (idea #4)**; **5. ICU plurals**; **6. Locale matrix**.

## 2. Date / number / currency — `Intl`, timezone pinned, "now" frozen (idea #2)

The fixtures give every test `tag` (the project's `locale`) and `zone` (its `timezoneId`); the expected side
uses both, exactly as the browser does.

```typescript
import { expect, test } from '../fixtures/i18n';

test('Should_FormatTotalAsLocaleCurrency_When_CartHoldsSeededItems', async ({ cartPage, tag }) => {
  await cartPage.goto();

  const expected = new Intl.NumberFormat(tag, { style: 'currency', currency: 'EUR' }).format(1234.5);
  await expect(cartPage.total).toHaveText(expected);
});

test('Should_FormatPlacedOnDate_When_OrderHasSeededInstant', async ({ orderPage, tag, zone }) => {
  await orderPage.goto();

  const placedAt = new Date('2026-03-11T09:00:00Z');
  const expected = new Intl.DateTimeFormat(tag, { dateStyle: 'long', timeZone: zone }).format(placedAt);
  await expect(orderPage.placedOn).toHaveText(expected);
});

test('Should_ShowAgeInDays_When_OrderIsThreeDaysOld', async ({ orderPage, tag }) => {
  await orderPage.goto();

  const expected = new Intl.RelativeTimeFormat(tag, { numeric: 'auto' }).format(-3, 'day');
  await expect(orderPage.age).toHaveText(expected);
});
```

`tests/specs/formatting.i18n.spec.ts`. The seeded order was placed three days before `FROZEN_NOW`
(2026-03-14T09:00Z).

- **Frozen time.** The i18n fixture calls `page.clock.setFixedTime(FROZEN_NOW)` before the page loads, so
  `Date.now()` and `new Date()` in the app return that instant while its timers keep running. Relative times,
  "today" and a date picker's default month are then identical on every run and machine. A test that must also
  advance timers uses `page.clock.install({ time })` and `runFor` instead — one clock call per test, before
  the page loads.
- **Pure functions in Vitest** — a formatter utility is asserted without a browser, one row per locale:

```typescript
import { expect, it } from 'vitest';
import { formatPrice } from '../../src/i18n/format';

it.for(['en-US', 'de-DE', 'fr-FR'])('Should_FormatEurLikeIntl_When_LocaleIs %s', (tag) => {
  const expected = new Intl.NumberFormat(tag, { style: 'currency', currency: 'EUR' }).format(1234.5);
  expect(formatPrice(1234.5, tag, 'EUR')).toBe(expected);
});
```

> Locales use **non-breaking** (U+00A0) and **narrow no-break** (U+202F) spaces inside formatted numbers — a
> copy-pasted literal uses a normal space and fails. Asserting against `Intl` also means an ICU upgrade that
> changes a format updates *both* sides together.

## 4a. RTL — assert the layout mirrors (idea #4)

Use a **real RTL locale** (`ar`), not a `direction: rtl` CSS hack — only a real locale exercises the app's own
direction logic, bidi handling, and mirrored icons. RTL specs carry the `@rtl` tag and the left-to-right projects
exclude it with `grepInvert: /@rtl/`, so no test body checks which locale it runs in.

```typescript
import { expect, test } from '../fixtures/i18n';

test('Should_DeclareRtlDocument_When_LocaleIsArabic', { tag: '@rtl' }, async ({ homePage }) => {
  await homePage.goto();

  await expect(homePage.document).toHaveAttribute('dir', 'rtl');
});

test('Should_PlaceNavigationOnTheRight_When_LocaleIsArabic', { tag: '@rtl' }, async ({ homePage, textAudit }) => {
  await homePage.goto();

  await expect.poll(() => textAudit.leftEdgeRatio(homePage.navigation)).toBeGreaterThan(0.5);
});
```

`tests/specs/rtl.i18n.spec.ts`. `leftEdgeRatio` is the element's left edge as a fraction of the viewport width:
past the midpoint means the navigation sits on the right.

## Anti-patterns

- **Asserting a hardcoded literal** (`toHaveText('Welcome')`). *Fix:* `toHaveText(t('home.title'))`.
- **Comparing the catalog to itself.** *Fix:* the left side is always the **live DOM / formatted output**.
- **Hardcoding a formatted number/date/currency** (`'1.234,56 €'`). *Fix:* `Intl` for the locale under test.
- **Letting the CI timezone float, or "now" run free.** "3 days ago" changes at midnight. *Fix:* `timezoneId`
  in the project, the same zone in the formatter, `page.clock.setFixedTime` in the fixture.
- **One locale value standing in for both catalog and browser.** `de` is a catalog key; `de-DE` is what `Intl`
  and `navigator.language` need. *Fix:* `lng` and `locale` per project.
- **`test.use({ locale })` inside a test, or `test.skip` on the locale.** `test.use` is not allowed in a test
  body, and a skip on the locale is a branch. *Fix:* locale projects, tags with `grep`/`grepInvert`.
- **Faking RTL with a `direction: rtl` CSS toggle.** *Fix:* a real RTL locale.
- **Only checking that translation keys *exist*.** *Fix:* presence, non-empty, no orphans, same
  `{{placeholders}}`.
- **Testing plurals at only count 1 and 2.** *Fix:* the boundary counts the language has (`Intl.PluralRules`).
- **Hardcoding the supported-locale list in each spec.** *Fix:* import the one config.

## Rules (hard constraints)

- **Never assert a hardcoded literal string.** The expected value comes from the **app's own catalog** by key or
  from `Intl` — never copied in; the asserted side is the live DOM / formatted output.
- **Formatting is asserted via `Intl`** for the locale under test, the **timezone pinned** in formatter and
  project, and **"now" frozen** with `page.clock` whenever the text depends on the current date.
- **Pseudo-localization is a required CI gate:** every visible string carries the markers, and no label
  overflows its box under +40% expansion.
- **RTL uses a real RTL locale** and asserts `<html dir="rtl">` plus a mirrored-layout measurement.
- **Translation-key coverage is a static, build-gating test.**
- **The supported-locale list comes from one config.** `lng`, `locale` and `timezoneId` are set per project;
  which specs a project runs is decided by tags, never by a branch in a test.
- Test names `Should_X_When_Y`; one logical assertion per test; no `waitForTimeout`/sleeps; no inline comments;
  page objects and fixtures, never raw `page.` calls; `strict: true`.

## Cross-references

- `qa-java:language-testing` · `qa-dotnet:language-testing` — the sibling stacks (ICU4J / `ResourceBundle` ·
  `CultureInfo` / `.resx`); same four ideas.
- `qa-typescript:ui-tests-playwright` — the fixtures this extends; `references/emulation-and-mobile-web.md`
  for locale, time zone and `page.clock`.
- `qa-typescript:visual-regression` — the pixel record of a pseudo-loc overflow; this skill asserts it didn't.
- `qa-typescript:data-driven-testing` — the locale matrix is its row-binding pattern applied to locales.
- `qa-typescript:accessibility-testing` — `html[lang]` / `dir` a11y rules; run them on the locale-pinned page.
- `qa-typescript:test-reports` — each locale project is its own result group, so a failure says *which*
  language broke.
