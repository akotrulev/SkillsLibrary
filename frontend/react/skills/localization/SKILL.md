---
name: fe-react-localization
description: Use when a React app (Next.js App Router primary / Vite SPA fallback; React 19 / 18) must support multiple languages/cultures — globalization + localization mechanics. Covers next-intl (App Router — `routing` config, the middleware that negotiates the `[locale]` segment, `useTranslations` in Client vs `getTranslations` in Server/RSC, `setRequestLocale` for static rendering) vs react-i18next (Vite SPA), message catalogs as source of truth (keys not English), the locale-switch that rewrites URL/cookie, culture-correct number/date/money via `Intl` (never hand-rolled separators), and RTL (`dir` from locale). Triggers: "add multi-language support", "translate the UI", "let users switch language", "dates in the wrong locale", "set up message files", "locale routing". Do NOT use for canonical display-format policy (use `frontend/react/skills/ui-conventions`), RTL/logical-CSS beyond `dir` (use `styling`), or i18n test assertions (the qa `i18n-testing` peer).
---

# React — Localization & Globalization

Owns the **mechanics** of running a React UI in multiple languages and cultures: message catalogs and the translation function, how the *current locale* is established (which differs by meta-framework and render environment), letting a user switch language, and culture-correct formatting of numbers/dates/money. It does **not** decide the app's canonical display formats — that policy (one date/money/percent format app-wide, timezone labeled, through shared helpers) is [`ui-conventions`](../ui-conventions/SKILL.md)'; this skill makes those helpers *locale-aware*.

**Two words that are not the same:** **globalization** = formatting values for a locale (the `Intl` API — always relevant, even in a single-language app); **localization** = swapping *text* per locale (translation function + message catalog). You can need one without the other.

**Library rule.** On the **App Router (primary)** use **`next-intl`** — it is built for RSC, handles locale routing + the middleware, and exposes both a server (`getTranslations`) and client (`useTranslations`) API. On the **Vite SPA fallback** use **`react-i18next`** — the mature client-only choice (there's no server to negotiate locale, so the SSR/RSC split below collapses to "set it at startup, like Blazor WASM"). Don't mix them. `next-i18next` is the pre-App-Router package — do not reach for it on the App Router.

**Version rule.** next-intl's App Router APIs are stable across **Next 14/15** and **React 18/19** (the RSC split is a Next.js reality, not a React-version one). Two moving pieces to detect, not assume: next-intl **v4** is current (v3 had a different `getRequestConfig`/plugin shape); and **Next.js 16** renames the `middleware.ts` file to `proxy.ts` (the `createMiddleware`/`createProxy` function is otherwise the same) — on Next 15 it is still `middleware.ts`. Match the project's installed versions.

## When to use

- Standing up multi-language support (message catalogs, translation-function injection, `t("key")`)
- Establishing the current locale correctly (App Router routing/middleware, or SPA startup)
- A language switcher users can operate, persisted across visits
- Culture-correct number/date/currency display and input parsing
- Right-to-left layout enablement

## When NOT to use

- The app's canonical format-per-data-type policy, humanized enums, id→name → [`ui-conventions`](../ui-conventions/SKILL.md) (localization supplies the locale; ui-conventions owns the policy)
- RTL styling mechanics (logical properties, mirrored icons) beyond setting `dir` → [`styling`](../styling/SKILL.md) + [`responsive-design`](../responsive-design/SKILL.md)
- Validation-message wording/voice → [`design/ux-writing`](../../../../design/ux-writing/SKILL.md); the *plumbing* of localized validation messages is here + [`forms`](../forms/SKILL.md)
- Asserting translations/locale behavior in tests → the qa **`i18n-testing`** peer (locale-pinned assertions, pseudo-loc, RTL) — a peer, not loaded here

## The shared half: message catalogs + the translation function

Same idea in every setup. Keys map to translated text, one catalog per locale, resolved through a `t` function. **Keys are stable identifiers, not English sentences** — a literal in JSX is invisible to translation, exactly like a hardcoded string.

```
messages/
  en.json   → { "Home": { "greeting": "Hello", "itemCount": "{count, plural, one {# item} other {# items}}" } }
  fr.json   → { "Home": { "greeting": "Bonjour", "itemCount": "{count, plural, one {# article} other {# articles}}" } }
```

- **ICU message syntax** (`{count, plural, ...}`, `{name}`, `{date, date, long}`) is how you handle pluralization, gender, and interpolation *inside the catalog* — never build a sentence by string-concatenating fragments in code (word order differs per language).
- **Namespace by feature** (`Home`, `Checkout`) so a component loads only the messages it needs — this is also the lazy-loading seam ([`performance`](../performance/SKILL.md)).
- A missing key should **fall back visibly** (to the key or a default), not crash — you want to *see* untranslated strings, then translate them.
- Localize **validation messages** (Zod/RHF) through the same catalog so form errors translate — see [`forms`](../forms/SKILL.md).

## The split half: establishing the current locale

```
Which setup serves this component?
  App Router (Next.js, primary)
    → next-intl: routing config + middleware negotiate the [locale] segment;
      Server/RSC read it via getTranslations(); Client Components via useTranslations()
  Vite SPA (fallback)
    → react-i18next: locale set at startup from storage / navigator.language (no server)
```

### App Router — next-intl

Locale lives in the **URL** (`/en/...`, `/fr/...`), negotiated by middleware, resolved per request on the server.

```ts
// src/i18n/routing.ts
import { defineRouting } from 'next-intl/routing';
export const routing = defineRouting({ locales: ['en', 'fr', 'de', 'ar'], defaultLocale: 'en' });
```
```ts
// middleware.ts  (Next 16: proxy.ts)
import createMiddleware from 'next-intl/middleware';
import { routing } from './src/i18n/routing';
export default createMiddleware(routing);
export const config = { matcher: '/((?!api|_next|.*\\..*).*)' };
```

- Pages/layouts live under `app/[locale]/…`. The middleware detects locale from the path (then cookie, then `Accept-Language`) and redirects `/` to the negotiated locale.
- **Server/RSC** (the default) read translations with the **async `getTranslations()`** from `next-intl/server` — `useTranslations()` is a hook and only works in `'use client'` code. This mirrors the FE React rule: Server Components fetch/read; hooks are client-only.

```tsx
// Server Component (default)
import { getTranslations } from 'next-intl/server';
export default async function Home() {
  const t = await getTranslations('Home');
  return <h1>{t('greeting')}</h1>;
}
```
```tsx
// Client Component
'use client';
import { useTranslations } from 'next-intl';
export function Counter({ count }: { count: number }) {
  const t = useTranslations('Home');
  return <p>{t('itemCount', { count })}</p>;
}
```

- **Static rendering:** call `setRequestLocale(locale)` in the layout/page and `generateStaticParams` from `routing.locales`, so pages render at build time instead of reading the request header (which would force them dynamic — a [`performance`](../performance/SKILL.md)/SEO cost). Without it, every localized page is dynamic.
- Cross-link the locale into [`seo-discoverability`](../seo-discoverability/SKILL.md): each locale needs its own `<html lang>` and `alternates.languages` (hreflang) in `generateMetadata`.

### Vite SPA — react-i18next

No server negotiates locale; it's a **client startup** value (the React analog of Blazor WASM's "set culture before the app boots"). Initialize `i18next` with the catalogs and a language detector, wrap the app in `<I18nextProvider>` (or use the `initReactI18next` plugin), and read text with the `useTranslation()` hook. Lazy-load non-default locale bundles via `i18next-http-backend` so you don't ship every language up front.

## Switching language at runtime

- **App Router:** switching = **navigating to the same route under a new locale prefix** using next-intl's locale-aware `Link`/`useRouter` (from `createNavigation(routing)`), which rewrites `/en/orders` → `/fr/orders`. next-intl persists the choice in a cookie so a bare `/` visit re-resolves to it. No full reload needed — it's a normal client navigation.
- **Vite SPA:** call `i18n.changeLanguage('fr')` and persist to `localStorage`; the tree re-renders in the new language in place (a SPA has no locale in the URL by default, though you can add one via the router).
- Persist the choice so returning users keep their language; default from `Accept-Language`/`navigator.language` on first visit.

## Culture-aware formatting — the `Intl` API, free once locale is set

Once you know the locale, format through the **built-in `Intl` API** — never hand-roll separators or month names.

```ts
new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD' }).format(amountMinor / 100);
new Intl.DateTimeFormat(locale, { dateStyle: 'long' }).format(date);
new Intl.NumberFormat(locale).format(1234.5);          // 1,234.5 (en) · 1 234,5 (fr) · ١٬٢٣٤٫٥ (ar)
```

- next-intl wraps `Intl` (`useFormatter()` / `format.dateTime`, `format.number`) and reads the active locale for you — prefer it on the App Router so formatting and messages share one locale source.
- **Money:** the currency *code* is data, not locale — a French user still sees USD as USD; the locale controls symbol placement/separators, not which currency. Keep amounts as minor units per [`data-access`](../data-access/SKILL.md)/`ui-conventions`.
- **Timezone:** pass an explicit `timeZone` to `Intl.DateTimeFormat` — the server and the user's browser are in different zones; an unqualified date renders inconsistently between SSR and hydration (a hydration-mismatch trap — [`reference`](../reference/SKILL.md)). next-intl takes a global `timeZone` for exactly this.
- Route all display formatting through the **shared helpers** [`ui-conventions`](../ui-conventions/SKILL.md) mandates; this skill just guarantees those helpers see the right locale.

## RTL

- Set `dir="rtl"` on `<html>` for RTL locales (Arabic, Hebrew) — derive it from the locale in the root layout, don't hardcode. next-intl's routing knows the locale; map it to `dir`.
- The layout must already use **logical CSS properties** (`margin-inline-start`, not `margin-left`) so it mirrors automatically — that mechanics work lives in [`styling`](../styling/SKILL.md)/[`responsive-design`](../responsive-design/SKILL.md); this skill owns *deriving* `dir` from locale.
- Mirror directional icons (chevrons, back arrows); leave logos/brand marks unmirrored.

## Rules

- **Distinguish globalization (formatting via `Intl`, always relevant) from localization (text swap via catalogs).**
- **next-intl on the App Router, react-i18next on the Vite SPA** — never `next-i18next` on App Router, never two libraries at once.
- **Keys are stable ids**, catalogs are the source of truth, never hardcode UI strings; pluralization/interpolation via ICU syntax *in the catalog*, never string concatenation in code.
- **Server/RSC → `getTranslations()` (async); Client → `useTranslations()` (hook)** — the hook is client-only, same rule as any React hook.
- **`setRequestLocale` + `generateStaticParams`** to keep localized pages statically renderable; otherwise they go dynamic.
- **Language switch = navigate under the new locale prefix** (App Router) or `changeLanguage` + persist (SPA), remembered for return visits.
- **Format via `Intl`** (or next-intl's `useFormatter`) with an explicit `timeZone` — never hand-roll separators; watch for the SSR/hydration date mismatch.
- **`dir` derives from locale**; logical-property mirroring is `styling`'s job. Emit `lang` + hreflang alternates for SEO.

## What NOT to do

- No hardcoded UI strings once localization is enabled — invisible to translators.
- No string-concatenated sentences for plurals/interpolation — word order and plural rules differ per language; use ICU syntax.
- No `useTranslations()` in a Server Component — it's a hook; use `getTranslations()`.
- No reading the locale from the request header without `setRequestLocale` when you want static rendering — it silently forces every page dynamic.
- No hand-formatted dates/money with fixed separators — breaks in every other locale.
- No unqualified `toLocaleDateString()`/`Intl` without a `timeZone` in SSR — server and client zones differ → hydration mismatch.
- No `next-i18next` on the App Router — it predates RSC.
- No RTL via `left/right` CSS — use logical properties so one stylesheet serves both directions.

## Validation

- Switch language in the UI → text, dates, numbers, and currency all change; the choice survives a reload/return visit; the URL reflects the locale (App Router).
- A Server Component and a Client Component on the same page both render translated text (proves `getTranslations` + `useTranslations` are wired correctly).
- Localized pages render statically where expected (`setRequestLocale` + `generateStaticParams` held) — not forced dynamic.
- A missing message key falls back visibly (key/default), not a crash — then gets translated.
- Form validation messages appear in the active language.
- A date renders identically on the server and after hydration (explicit `timeZone`, no mismatch warning).
- An RTL locale flips layout direction with `<html dir="rtl" lang="ar">` and no broken alignment (logical properties held); hreflang alternates present in the page head.

## Handoffs

- Canonical format-per-type policy, humanized enums, id→name → [`ui-conventions`](../ui-conventions/SKILL.md)
- Localized validation-message plumbing → [`forms`](../forms/SKILL.md); their wording/voice → [`design/ux-writing`](../../../../design/ux-writing/SKILL.md)
- RTL/logical-property styling, mirrored components → [`styling`](../styling/SKILL.md) + [`responsive-design`](../responsive-design/SKILL.md)
- `lang`/hreflang alternates, per-locale canonical URLs → [`seo-discoverability`](../seo-discoverability/SKILL.md)
- Server vs Client boundary (drives `getTranslations` vs `useTranslations`) and the hydration-mismatch trap → [`reference`](../reference/SKILL.md)
- Lazy-loading message bundles, keeping locale data off the critical path → [`performance`](../performance/SKILL.md)
- Locale-pinned test assertions, pseudo-localization, RTL testing → the qa **`i18n-testing`** peer (invoke separately)
