---
name: i18n
description: Use when an Android app must support more than one language or region — string resources, plurals, per-app language (LocaleConfig, AppCompatDelegate / LocaleManager), RTL layout, locale-aware number, date and money formatting. Triggers "add a language", "plural is wrong", "RTL layout broken", "let the user pick a language". Do NOT use for wording and tone (`design:ux-writing`), text scaling (`mobile-android:accessibility`), or Play listing text (`mobile-<stack>:release`).
---

# Android — Localization and Globalization

Two jobs: **localization** (swap the text via resources) and **globalization** (format numbers, dates, money and plurals for the locale — relevant even with one language). On Android the **resource system picks the strings**: the configuration's locale list selects `values-<qualifier>/` at runtime, and Compose's `stringResource` re-resolves when it changes.

## Version lane

| Concern | Detail | Lane |
|---|---|---|
| Strings | `res/values*/strings.xml`; `stringResource` / `pluralStringResource` in Compose | Same |
| Per-app language | **API 33+**: system Settings → App → Language; app declares its locales; `LocaleManager.applicationLocales` | `[API32-]` `AppCompatDelegate.setApplicationLocales` (AppCompat 1.6+) backport, with `autoStoreLocales` |
| Declaring locales | **`androidResources { generateLocaleConfig = true }`** + `res/resources.properties` `unqualifiedResLocale=en-US` (AGP 8.1+, compileSdk 33+) — recommended | Manual `res/xml/locale_config.xml` + `android:localeConfig`; the build **fails** if both exist |
| Limiting packaged locales | `androidResources.localeFilters` is the AGP 8.1+ DSL; the Android page still shows `resourceConfigurations` | **Not verified:** read the AGP 9 DSL reference before choosing; never filter a language you ship |
| Compose | A locale change is a configuration change; `AppCompatDelegate` needs an `AppCompatActivity` host | Same |
| `[API37]` | The per-app-language page lists no Android 17 change | — |

Source read 2026-10-10: developer.android.com/guide/topics/resources/app-languages. Facts on plurals, RTL and formatting below are long-standing platform behaviour not re-fetched this session; confirm a class or flag against the installed SDK before relying on an edge case.

## When to use

- Adding a language, or setting up localization from nothing
- Plurals, quantities, positional arguments; strings that must not be translated
- Dates, money, numbers and measurements that look wrong in another locale
- An RTL language (Arabic, Hebrew, Persian, Urdu)
- An in-app language picker, or appearing in the system per-app language list
- The app name, shortcut labels, channel names and widget text per language

## When NOT to use

- Wording, tone, microcopy → [`design:ux-writing`](../../../../design/ux-writing/SKILL.md)
- Font scale, TalkBack language → [`accessibility`](../accessibility/SKILL.md)
- Layout mechanics, insets, window sizes → [`styling`](../styling/SKILL.md)
- Play listing text per locale → [`mobile-<stack>:release`](../../../_shared/release/SKILL.md)
- The web app's locale routing → [`fe-react:i18n`](../../../../frontend/react/skills/languages/SKILL.md)
- Another stack → `mobile-ios:i18n`, `mobile-react-native:i18n`

## String resources

```xml
<resources>
    <string name="orders_title">Orders</string>
    <string name="order_total">Total: %1$s</string>
    <string name="order_shipped_to">%1$s shipped to %2$s</string>
    <plurals name="orders_count">
        <item quantity="one">%d order</item>
        <item quantity="other">%d orders</item>
    </plurals>
    <string name="app_scheme" translatable="false">myapp</string>
</resources>
```

```kotlin
Text(stringResource(R.string.order_shipped_to, orderRef, city))
Text(pluralStringResource(R.plurals.orders_count, count, count))
```

- **Every user-visible string is a resource** — `Text`, `contentDescription`, placeholders, snackbars, dialogs, notification and channel text, shortcut labels, widget text, `stateDescription`, error copy. A literal in a composable is a finding; so is a string built from a ViewModel's `Context`. **The ViewModel exposes a typed state or a `@StringRes` / `UiText` value; the composable resolves it** ([`architecture`](../architecture/SKILL.md)) — the ViewModel never holds a `Context` to translate.
- **Keys are semantic and screen-scoped** (`orders_empty_title`), snake_case; reuse a string only when the meaning is the same in every language — "Open" the verb and "Open" the adjective are two keys.
- **Positional arguments always** (`%1$s`, `%2$s`) — word order differs by language; one `%s` is a trap the moment a second argument arrives. **Never concatenate** a sentence from pieces; interpolation lives inside the resource.
- **Plurals through `<plurals>`**, with the **count passed as the quantity and as the argument** (`pluralStringResource(id, count, count)`). Languages need different categories — English has two, Russian and Arabic more, Japanese one; the translator supplies them. The `one` item is not "exactly 1" in every language — never write `if (count == 1)`.
- **`translatable="false"`** for schemes, ids, brand names and anything the translator must not touch; a comment above a non-obvious string (`<!-- Button that opens a delivered order -->`) — the one allowed comment form in resources because the translator reads it.
- **Default resources (`values/`) are the source language** and exist for every key — a missing translation falls back to them, so a missing key in `values/` crashes with `NotFoundException`. Locale folders use BCP 47 qualifiers: `values-fr`, `values-pt-rBR`, `values-b+sr+Latn`.
- Strings stay in resources, not `BuildConfig` or Kotlin constants; a `const val` string shown to a user freezes the build locale.
- `HtmlCompat` / `AnnotatedString` for styled text — never split a sentence around a link or a bold word; use `<annotation>` or `AnnotatedString.fromHtml` so the translator sees the whole sentence.
- A pseudo-locale (`en-XA`, `ar-XB`) via `pseudoLocalesEnabled true` on the debug build type finds hard-coded strings, truncation and RTL breaks without a translator.

## Per-app language

1. **Declare the locales** — `generateLocaleConfig = true` and `unqualifiedResLocale`, so the system Settings → Apps → Language list shows exactly the languages shipped. Without a locale config the user **cannot** pick the app's language separately from the system's.
2. **The picker, if you want one in-app**, is a thin call, not a framework:

```kotlin
fun setAppLanguage(languageTag: String) {
    AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(languageTag))
}
```

   `LocaleManager.applicationLocales` is the platform call on API 33+ and stays in sync with the system screen; `AppCompatDelegate` is the one call that covers every API level. It **must be called on the main thread and recreates the activity** unless the app handles locale configuration changes.
3. **Compose host must extend `AppCompatActivity`** when you use `AppCompatDelegate`, or the change does not apply.
4. **API 32 and below**: the AndroidX service entry (`AppLocalesMetadataHolderService`, `enabled=false`, meta-data `autoStoreLocales=true`) stores the choice for you — at the price of a blocking read on the main thread (StrictMode `diskRead`). With custom storage, restore the locale **before `onCreate`**.
5. **Resetting**: removing `localeConfig` later leaves users stuck on the language they picked — reset with an empty `LocaleList` / `LocaleListCompat.getEmptyLocaleList()`.
6. **Pick-a-language UI**: list each language **in its own name** (`Locale.getDisplayName(locale)`), include a "System default", never use flags as languages, and mark the current one with text, not colour alone.
7. Tell outgoing requests the language (`Accept-Language` from the app locale in the OkHttp client — [`networking`](../networking/SKILL.md)) and Custom Tabs (`Browser.EXTRA_HEADERS`) so server-rendered text matches.

## Globalization — locale-aware formatting

- **Format at the edge, from typed values.** The ViewModel holds `Money(amount, currency)`, an `Instant`, a `Double`; the UI formats with the **current** locale. Never store or send a formatted string.
- **Numbers and money**: `NumberFormat.getCurrencyInstance(locale).apply { currency = Currency.getInstance(code) }`, `NumberFormat.getInstance(locale)`, `NumberFormat.getPercentInstance(locale)` — never `String.format("%.2f")` or `"$" + amount`. Money is **`BigDecimal` / minor units + an ISO currency code**, never `Double`.
- **Dates and times**: `java.time` with `DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM).withLocale(locale)`; a custom pattern string (`"dd/MM/yyyy"`) is a finding; relative text via `DateUtils.getRelativeTimeSpanString`. Store and send `Instant` / ISO-8601 UTC; convert to `ZoneId.systemDefault()` for display. `java.time` is available on API 26+ natively and by desugaring below ([`project-setup`](../project-setup/SKILL.md)).
- **Lists and units**: `ListFormatter` (API 33+) or a resource for the joined list; `MeasureFormat` / `android.icu.util.Measure` (ICU, API 24+) for units — never `"$km km"`.
- **Current locale in Compose**: `LocalConfiguration.current.locales[0]` (recomposes on change), not `Locale.getDefault()` cached in a field. A formatter created once in a `companion object` freezes the locale — build it per use or keyed on the locale in `remember(locale)`.
- **Sorting and case**: `Collator` for user-visible sorts; `uppercase(locale)` / `lowercase(locale)` — `"i".uppercase()` is wrong in Turkish unless the locale is passed.
- **Text input**: `KeyboardType.Number` shows the locale's decimal separator; parse with `NumberFormat.parse`, not `toDouble()` ([`forms`](../forms/SKILL.md)).

## RTL

- **`android:supportsRtl="true"`** in the manifest (the template default); **`start` / `end`, never `left` / `right`** — `Modifier.padding(start = …)`, `Arrangement.Start`, `Alignment.Start`, `TextAlign.Start`, `android:layout_marginStart` in Views. `Row` mirrors automatically; a hard-coded `Alignment.CenterStart` is correct, `Alignment.TopLeft` is not.
- **Mirror directional icons** (back arrow, send, progress, list bullets) with `Icons.AutoMirrored.*` / `autoMirrored = true`; **do not mirror** clocks, media transport controls, checkmarks, brand marks or phone numbers.
- **Numbers and Latin fragments inside RTL text** keep their order; mixed-direction strings in a data cell need `BidiFormatter.unicodeWrap` or `TextDirection.Content` on the `Text`.
- **Gestures follow the layout direction** — swipe-to-reveal and carousels reverse; read `LocalLayoutDirection.current`.
- Test with the `ar-XB` pseudo-locale or the "Force RTL layout direction" developer option, and add a screenshot test in an RTL locale for a representative screen ([`unit-testing`](../unit-testing/SKILL.md)).

## Layout that survives translation

German and Finnish run 30–40 % longer; CJK is shorter and taller. No fixed widths on text containers, no `maxLines = 1` on a label that carries meaning without `overflow = Ellipsis` **and** a full-text path (TalkBack still reads it), buttons grow vertically, `Modifier.weight` over fixed sizes. Text scales with the system font setting up to 200 % and is never locked ([`accessibility`](../accessibility/SKILL.md)).

## Procedure

1. Detect: existing `values-*`, `locale_config.xml` or `generateLocaleConfig`, the activity base class, any hand-rolled language switcher, AGP version.
2. Move every user-visible literal into `values/strings.xml` with positional args and plurals; no concatenation.
3. Replace ad-hoc formatting with locale-aware formatters at the edge.
4. Declare locales; add the picker only if the product wants one; mind the `AppCompatActivity` requirement.
5. RTL pass: start / end, auto-mirrored icons, pseudo-locale screenshots.
6. Test ids stay English and untranslated ([`test-ids`](../test-ids/SKILL.md)); Play listing text per locale is the release task.

## Validation (exit gate)

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- [ ] No user-visible string literal in Kotlin or layout files; every ViewModel string is a resource id or typed state
- [ ] Plurals use `<plurals>` with the count passed twice; no `count == 1` branch
- [ ] Per-app language list shows the shipped locales; picking one recreates the screen in that language
- [ ] A pseudo-locale and an RTL run show no truncation, no un-mirrored arrows, no left / right
- [ ] No `String.format` money, no date pattern strings, no cached `NumberFormat`
- [ ] Dev-side tests: formatters with fixed locales (`Locale.GERMANY`, `ar`), a plural-quantity test per language shipped

## Handoffs

- Wording, tone, error copy → [`design:ux-writing`](../../../../design/ux-writing/SKILL.md)
- Font scale and TalkBack → [`accessibility`](../accessibility/SKILL.md)
- Edge insets, RTL layout structure → [`styling`](../styling/SKILL.md)
- Locale in requests → [`networking`](../networking/SKILL.md)
- Number parsing in fields → [`forms`](../forms/SKILL.md)
- Store listing localization → [`mobile-<stack>:release`](../../../_shared/release/SKILL.md)
- Locale and RTL screenshot tests → [`unit-testing`](../unit-testing/SKILL.md)
