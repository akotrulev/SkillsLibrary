---
name: mobile-react-native-languages
description: Use when an Expo SDK 57 app must support more than one language or region — expo-localization, i18next or Lingui catalogs, ICU plurals, hoisted Intl formatters, RTL via I18nManager, per-app language on iOS and Android, localized purpose strings. Triggers "add Spanish", "translate the app", "Arabic layout flips", "date shows wrong format". Do NOT use for web i18n routing (`fe-react-languages`), copy voice (`design-ux-writing`), or text scale (`-accessibility`).
---

# React Native — Localization and Globalization

Two jobs: **localization** (swap the text via catalogs) and **globalization** (format numbers, dates, money and plurals for the locale — always relevant, even with one language). Web analog: [`fe-react-languages`](../../../../frontend/react/skills/languages/SKILL.md) — keys as stable ids, ICU in the catalog, never concatenated sentences. What does not carry over: routing by locale prefix, `next-intl`, server components, hreflang. On a phone the **device** owns the locale, and the OS can change it while the app runs.

## Version lane

| Concern | Primary (SDK 57) | Notes |
|---|---|---|
| Device locale | `expo-localization`: `getLocales()` (ordered by preference, never empty), `getCalendars()`; `useLocales()` hook | |
| Library | **i18next 26 + react-i18next** (default) · **Lingui 6** (compile-time macros, smaller bundles) | One library per app; match the one installed |
| Formatting | `Intl.NumberFormat`, `DateTimeFormat`, `PluralRules`, `RelativeTimeFormat`, `ListFormat` on Hermes | Confirm each on the project's RN version before relying on it; polyfill only what is missing |
| RTL | `I18nManager` (`allowRTL`, `forceRTL`, `isRTL`); config-plugin `supportsRTL` / `forcesRTL` | `[SDK58]` RTL support is **on by default** with the device language in `supportedLocales`; on 57 set it explicitly |
| Per-app language | `expo-localization` plugin `supportedLocales` (`ios`, `android`) | Both OSes let the user pick a language per app only if the app declares its locales |
| Floor SDK 54 | Same API | Same recipes |

Detect the installed i18n library first; never add a second.

## When to use

- Adding a language, or setting up localization from nothing
- Dates, money, numbers and plurals that look wrong in another locale
- An RTL language (Arabic, Hebrew, Persian, Urdu)
- A language switcher, or following the device / per-app language
- Purpose strings, app name and store listing text per language

## When NOT to use

- Wording, tone, microcopy → [`design-ux-writing`](../../../../design/ux-writing/SKILL.md)
- Font scaling, dynamic type, screen-reader language → [`accessibility`](../accessibility/SKILL.md)
- Layout mirroring mechanics, logical styles → [`styling`](../styling/SKILL.md)
- The web app's locale routing → [`fe-react-languages`](../../../../frontend/react/skills/languages/SKILL.md)

## The shared half: catalogs and the translate function

- **Catalogs are the source of truth**: `locales/<lng>/<namespace>.json` (i18next) or `.po` / compiled catalogs (Lingui). Keys are **stable ids** (`orders.empty.title`), never the English sentence in i18next; Lingui's message-id-from-source is acceptable because the macro compiles it — pick one and keep it.
- **Plurals and interpolation live in the catalog** in ICU or i18next plural suffixes — never `count + ' items'`, never a sentence built by concatenation. Word order and plural categories differ per language (Arabic has six).
- **No hard-coded UI string** once localization is on — including `accessibilityLabel`, `placeholder`, alert text, tab titles in `app/_layout.tsx`, and notification copy built on the device.
- Initialise **once**, before the first render, from `getLocales()[0]` (language tag + region), a persisted user choice winning over the device:

```ts
import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import { getLocales } from 'expo-localization';

export const supportedLanguages = ['en', 'es', 'ar'] as const;

function initialLanguage(saved: string | null): string {
  const device = getLocales()[0]?.languageCode ?? 'en';
  const choice = saved ?? device;
  return supportedLanguages.find((language) => language === choice) ?? 'en';
}

export function initI18n(saved: string | null) {
  return i18next.use(initReactI18next).init({
    lng: initialLanguage(saved),
    fallbackLng: 'en',
    resources,
    interpolation: { escapeValue: false },
  });
}
```

- `escapeValue: false` is correct on RN (no HTML); `fallbackLng` makes a missing key degrade to English, not a crash. In development, log missing keys; in release, do not show the raw key.
- Components call `useTranslation()`; non-component code (a notification handler, a validator) imports the `i18n` instance — a plain function, no service locator.
- **Bundle only what ships.** Load a non-default language lazily (dynamic `import()` of its catalog) for large catalogs; the default is in the bundle so the first frame is never untranslated.
- A **language switch** calls `i18n.changeLanguage(code)`, persists the code (MMKV, not a secret — [`offline-and-storage`](../offline-and-storage/SKILL.md)), and every mounted component re-renders. If RTL flips, a reload is needed (below).

## Following the device and the OS

- The OS can change the locale **while the app is running**: on Android the app is not recreated; listen for `AppState` → `active` and call `getLocales()` again (and re-evaluate the saved choice). On iOS the same refresh on foreground is the safe default.
- **Per-app language** (iOS Settings → App → Language; Android 13+ per-app language): declare the languages in the `expo-localization` plugin so the OS offers them. A language the app has no catalog for must not appear in `supportedLocales`.

```json
{
  "expo": {
    "plugins": [
      ["expo-localization", { "supportedLocales": { "ios": ["en", "es", "ar"], "android": ["en", "es", "ar"] } }]
    ]
  }
}
```

- **Purpose strings, `CFBundleDisplayName` and the app name** are native resources, localized through the plugin / `locales` config, not through i18next: `NSCameraUsageDescription` in English only is a gap in a Spanish app ([`device-features`](../device-features/SKILL.md), [`mobile-shared-store-compliance`](../../../_shared/store-compliance/SKILL.md)). Store listing text is per-locale in the store consoles — a release concern ([`mobile-shared-release`](../../../_shared/release/SKILL.md)).
- A mixed-locale iOS app needs `ios.infoPlist.CFBundleAllowMixedLocalizations: true`.

## Culture-aware formatting — hoist the formatter

`Intl` is free once the locale is known, and **constructing an `Intl.*` object is expensive on Hermes** — never `new Intl.NumberFormat(...)` or `toLocaleString()` inside a render path or a list row (`rules/js-hoist-intl.md`). A static format is hoisted to module scope; a locale-dependent one is built once per locale in a hook and shared by every row:

```tsx
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

export function useMoneyFormatter(currency: string) {
  const { i18n } = useTranslation();
  return useMemo(
    () => new Intl.NumberFormat(i18n.language, { style: 'currency', currency }),
    [i18n.language, currency],
  );
}
```

The list calls the hook **once** in the screen and passes `formatter.format` down; a row never builds its own. (A module-level `Map` cache is static mutable state — avoid it.)

- **The currency comes from the data, the locale from the user.** Never infer a currency from the locale; never format money with a fixed separator.
- **Dates**: store and transmit ISO 8601 UTC; format at the edge with `Intl.DateTimeFormat(locale, { dateStyle, timeStyle, timeZone })` — an explicit `timeZone` from the user's setting or `getCalendars()[0].timeZone`. Let `Intl` pick the hour cycle from the locale unless the product overrides it.
- Sorting user-visible text uses `Intl.Collator(locale)`; `localeCompare` without a locale is wrong in several languages.
- Measurement system and first weekday come from `getLocales()` / `getCalendars()`, not from a constant.

## RTL

- RN mirrors layout through `I18nManager.isRTL`. **Use logical style properties** (`marginStart`, `paddingEnd`, `start` / `end`, `flexDirection: 'row'` which already flips) — `marginLeft`, `left`, `textAlign: 'left'` do not mirror ([`styling`](../styling/SKILL.md)).
- Changing `I18nManager.forceRTL(...)` takes effect **after a reload** (`Updates.reloadAsync()`, not available in Expo Go): switching between LTR and RTL languages at runtime restarts the app — tell the user and persist the choice first.
- `[SDK58]` `forcesRTL: true` in the plugin is for testing or RTL-only apps; `supportsRTL: false` opts out. On SDK 57 and earlier confirm RTL is allowed (`I18nManager.allowRTL(true)` / the plugin) — a project that ships Arabic with it off lays out left-to-right.
- **Mirror directional icons** (back chevrons, progress arrows, send); do not mirror logos, clocks, media transport controls, or phone-number text. Use `transform: [{ scaleX: I18nManager.isRTL ? -1 : 1 }]` on the icon only.
- Numbers and mixed-direction strings (an English product name in an Arabic sentence) need the `Intl` / Unicode bidi behaviour of `<Text>`; do not reorder by hand.
- Keep one test id per element regardless of language ([`test-ids`](../test-ids/SKILL.md)) — a locator that is a translated string breaks in every other language.

## Rules

- **Globalization (formatting) is always on; localization (text) is opt-in** — they are separate tasks.
- **One i18n library**; keys are stable ids; ICU plurals and interpolation in the catalog.
- **Initialise before the first render**; persisted choice > device language > `en`.
- **Hoist every `Intl` object**; module scope when static, `useMemo` per locale otherwise.
- **Logical styles for layout**; RTL flip needs a reload and is announced.
- **Native strings (permissions, app name) are localized through config plugins**, not i18next.
- **Never ship a language without a complete catalog** — a half-translated app is worse than the fallback; track coverage per language.

## What NOT to do

- No string concatenation for a sentence, plural or list — `Intl.ListFormat` and ICU.
- No `toLocaleString()` / `new Intl.*` in a render or `renderItem`.
- No locale-derived currency; no fixed-separator money.
- No `left` / `right` / `marginLeft` in a shared component.
- No raw key visible in a release build when a translation is missing.
- No translated string as a `testID` or as the selector in a test.
- No `Platform.OS`-based language guess when `getLocales()` answers.

## Procedure

1. Detect the SDK, the i18n library, existing catalogs, languages already shipped and whether RTL is allowed.
2. Add or extend the catalogs; extract hard-coded strings, labels and alerts into keys.
3. Initialise i18n once; wire the persisted choice and the foreground refresh.
4. Replace ad-hoc formatting with hoisted `Intl` helpers; set explicit time zones.
5. Declare `supportedLocales`; localize purpose strings and the app name.
6. For RTL: logical styles, mirrored icons, reload on direction change.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Change the device language: on return the app shows it; text, dates, numbers and money all change.
- Pick a per-app language in system Settings: the app follows it.
- A missing key falls back to English in a release build; development logs it.
- An RTL language mirrors layout, back arrows and the swipe-back direction; logos do not mirror; no `marginLeft` hits (`rg`, P6).
- A list of 500 priced rows scrolls without constructing a formatter per row.
- Plural forms read correctly for 0, 1, 2, 5 in a language with several categories.

## Handoffs

- Wording and tone of source copy → [`design-ux-writing`](../../../../design/ux-writing/SKILL.md)
- Logical properties, mirrored styles → [`styling`](../styling/SKILL.md)
- Dynamic type, screen-reader language → [`accessibility`](../accessibility/SKILL.md)
- Persisting the choice → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Localized permission strings → [`device-features`](../device-features/SKILL.md)
- Store listings per locale → [`mobile-shared-release`](../../../_shared/release/SKILL.md)
- Catalog and hoisting checks in review → [`code-review`](../code-review/SKILL.md)
