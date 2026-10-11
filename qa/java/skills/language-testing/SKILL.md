---
name: qa-language-testing-java
description: Use when writing i18n/localization tests in Java 21 — Playwright-Java + TestNG pinned to a locale, asserting via the app's own `ResourceBundle` catalog by key, plus ICU4J formatting, pseudo-localization, and RTL checks. Triggers "write an i18n test in Java", "test German/Arabic rendering with Playwright-Java", "check RTL layout". Do NOT use for the frontend's own localization wiring (the `fe-*` `localization` skill), or for breakpoint layout (`qa-responsive-testing-java`).
---

# QA — i18n / Localization Testing (Java 21 / Playwright 1.63 + TestNG + ICU4J)

Tests that a web app is correctly **internationalized** (locale switching, formatting, layout, catalog
completeness) and **localized** (the right strings render per locale). It splits by the nature of the assertion:
**Playwright for Java** drives the app in a pinned locale for the UI-rendered checks, and **plain TestNG** unit
tests own the pure-function checks (ICU message formatting, the pseudo-loc transform, and the static
catalog-coverage diff that needs no browser). Both halves share the fact that makes i18n testing its own
discipline: **the literal string on screen is the variable, not the constant — so the assertion can never be a
hardcoded literal.**

> **The discipline this skill encodes** — four ideas that separate a correct i18n test from a UI-test reflex:
>
> 1. **Pin the locale; assert against the catalog by KEY, never a hardcoded literal.** Drive the app with an
>    explicit locale and resolve the expected text from the **same bundle the app ships**
>    (`Catalog.t("home.title", locale)`), not a copied-in literal. `hasText("Willkommen")` breaks the instant a
>    copywriter rewords the German and only ever tests *one* language. The left side is always the **rendered
>    DOM**; the bundle is only ever the expected side — comparing the bundle to itself is a tautology.
> 2. **Format is locale-derived — assert via ICU4J, never a hardcoded format.** `1,234.56` (en) vs `1.234,56`
>    (de) vs `1 234,56` (fr). The expected value is `NumberFormat.getCurrencyInstance(locale).format(n)` /
>    `DateFormat` from **ICU4J** — derived from the same CLDR data, never a typed string (which bakes in one
>    locale, uses the wrong spaces, and rots on an ICU upgrade). Pin the **time zone** on the formatter and the
>    context, and **freeze the page clock** for anything relative to "now".
> 3. **Pseudo-localize to surface hardcoded + truncated strings — before any real translation exists.** A
>    pseudo-locale (`en-XA`) turns `Welcome` into `[!! Ŵḗḷḉöṁḗ~~~ !!]`: (a) any **un-bracketed** text on screen is
>    a **hardcoded string**; (b) **clipped** text is a layout-too-tight bug the +40% expansion forces out; (c)
>    broken **concatenation** shows up garbled. The cheap first gate, every CI build.
> 4. **RTL is a layout assertion; coverage is a static one — and they're separate from the text checks.** **RTL**
>    (`ar`/`he`) mirrors the *whole* UI — assert `<html dir="rtl">` and that the layout actually flipped, with a
>    **real RTL locale**, not a CSS toggle. **Translation-key coverage** is a **static** check (no browser): every
>    source key present and **non-empty** in every target bundle, no **orphans**, identical `{placeholders}`.

## Decision matrix — i18n surface → test shape

| Surface | What you're proving | Runner | Test shape |
|---------|---------------------|--------|------------|
| **Locale-pinned UI text** | The right translation renders for a locale | Playwright | locale class → `assertThat(el).hasText(Catalog.t(key, locale))` |
| **Date / number / currency** | Locale-correct formatting | Playwright | rendered text `hasText` ICU `NumberFormat`/`DateFormat(locale)`, zone pinned, clock frozen |
| **Pseudo-localization** | No hardcoded strings; no truncation | Playwright | `en-XA` class → every visible text bracketed; no label overflows |
| **RTL layout** | UI mirrors for RTL scripts | Playwright | `ar` class → `<html dir="rtl">` + navigation on the right half |
| **Translation-key coverage** | Every bundle complete; no orphans | TestNG (static) | diff source keys vs each target |
| **ICU plural / select** | Plurals resolve per language | TestNG | format at the language's boundary counts |
| **Locale matrix** | All supported locales pass one journey | Playwright | `@Factory` over `Catalog.SUPPORTED` |

## Stack

- Java 21 + Gradle (Kotlin DSL); Playwright for Java and TestNG at the pins in the **Versions** table of
  `qa/java/skills/ui-test-author/playwright/SKILL.md` (this skill pins nothing)
- Every browser class **extends J1's `BaseTest`**: a context per **test method**, failure evidence, `BASE_URL`,
  `parallel="classes"`. The locale and time zone go in the class's **`contextOptions()`** override
  (`setLocale` / `setTimezoneId`), so every test gets a fresh context in its locale — never a context opened once
  per class and shared by its tests
- The app's **own catalog source** — `ResourceBundle` `.properties` files
  (`src/main/resources/i18n/common_en.properties`, `…_de.properties`, `…_ar.properties`), loaded by the tests
- **ICU4J** (`com.ibm.icu:icu4j`) — `NumberFormat`, `DateFormat`, `MessageFormat`, `PluralRules`
- The **supported-locale list** comes from one constant (`Catalog.SUPPORTED`); one canonical pseudo-locale (`en-XA`)

## The catalog + a test-side resolver

A read-only view of the files the app ships, with ICU `MessageFormat` for named arguments — not a second
translation system.

```java
package i18n;

import com.ibm.icu.text.MessageFormat;
import java.util.*;

public final class Catalog {
    public static final List<Locale> SUPPORTED = List.of(
            Locale.forLanguageTag("en"), Locale.forLanguageTag("de"), Locale.forLanguageTag("ar"));

    private Catalog() {}

    public static String t(String key, Locale locale) {
        ResourceBundle bundle = ResourceBundle.getBundle("i18n.common", locale);
        if (!bundle.containsKey(key)) {
            throw new MissingResourceException("Missing key " + key + " for " + locale, Catalog.class.getName(), key);
        }
        return bundle.getString(key);
    }

    public static String t(String key, Locale locale, Map<String, Object> arguments) {
        return new MessageFormat(t(key, locale), locale).format(arguments);
    }
}
```

## The locale under test — `contextOptions()`, context per method

`LocaleUnderTest` holds a locale and its time zone and turns them into context options. A class pins one locale
by overriding `contextOptions()`; a class that runs for every supported locale is a `@Factory` with one instance
per locale. `BaseTest` opens a new context from those options for **each test**.

```java
public record LocaleUnderTest(Locale locale, String timezoneId) {
    public static final LocaleUnderTest GERMAN = new LocaleUnderTest(Locale.forLanguageTag("de-DE"), "Europe/Berlin");
    public static final LocaleUnderTest ARABIC = new LocaleUnderTest(Locale.forLanguageTag("ar-EG"), "Africa/Cairo");
    public static final LocaleUnderTest PSEUDO = new LocaleUnderTest(Locale.forLanguageTag("en-XA"), "UTC");

    public Browser.NewContextOptions contextOptions() {
        return new Browser.NewContextOptions().setLocale(locale.toLanguageTag()).setTimezoneId(timezoneId);
    }
}
```

- `setLocale` sets `navigator.language`, `Accept-Language` and the browser's number and date formatting, so a
  server-rendered app picks the language from the request. A SPA that keeps its language in its own store
  (`localStorage`, a `?lng=` query, a cookie) is told in the class's `@BeforeMethod` — e.g.
  `page.addInitScript("localStorage.setItem('lng', '" + tag + "')")` before the page object navigates.
- One `@BeforeMethod` per class builds the page objects; tests never call `page` directly.

## 2. Date / number / currency — assert via ICU4J, zone pinned, clock frozen (idea #2)

```java
public class FormattingI18nTest extends BaseTest {
    private static final Instant ORDER_PLACED = Instant.parse("2026-03-14T09:00:00Z");
    private final LocaleUnderTest lut = LocaleUnderTest.GERMAN;
    private CartPage cartPage;
    private OrderPage orderPage;

    @Override
    protected Browser.NewContextOptions contextOptions() {
        return lut.contextOptions();
    }

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        page.clock().setFixedTime(ORDER_PLACED.plus(Duration.ofDays(2)).toString());
        cartPage = new CartPage(page);
        orderPage = new OrderPage(page);
    }

    @Test
    public void Should_FormatCartTotalAsLocaleCurrency_When_LocaleIsGerman() {
        cartPage.open();

        NumberFormat currency = NumberFormat.getCurrencyInstance(lut.locale());
        currency.setCurrency(Currency.getInstance("EUR"));
        assertThat(cartPage.total()).hasText(currency.format(CartFixtures.TOTAL_EUR));
    }

    @Test
    public void Should_FormatOrderDateForLocaleAndZone_When_LocaleIsGerman() {
        orderPage.open(OrderFixtures.PLACED_ORDER_ID);

        DateFormat date = DateFormat.getDateInstance(DateFormat.LONG, lut.locale());
        date.setTimeZone(TimeZone.getTimeZone(lut.timezoneId()));
        assertThat(orderPage.placedOn()).hasText(date.format(Date.from(ORDER_PLACED)));
    }
}
```

- `page.clock().setFixedTime(...)` runs **before** the page loads, so "2 days ago", "today" and expiry banners
  render against a known instant (`emulation-and-mobile-web.md` §6). The seeded order and cart come from
  fixtures, never literals in the test.
- Many locales use **non-breaking** / **narrow-no-break** spaces inside formatted numbers — a copy-pasted
  literal uses a normal space and fails. Asserting against ICU means an icu4j upgrade updates both sides
  together. There is no test that compares ICU output to a typed string: that would test ICU, not the app.

## 4a. RTL — assert the layout mirrors (idea #4)

A **real RTL locale** (`ar`), not a `direction: rtl` CSS toggle. Two behaviours, two tests:

```java
public class RtlI18nTest extends BaseTest {
    private AppShell appShell;
    private Geometry geometry;

    @Override
    protected Browser.NewContextOptions contextOptions() {
        return LocaleUnderTest.ARABIC.contextOptions().setViewportSize(1280, 720);
    }

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        appShell = new AppShell(page);
        geometry = new Geometry(page);
    }

    @Test
    public void Should_DeclareRtlDirection_When_LocaleIsArabic() {
        appShell.open();

        assertThat(appShell.document()).hasAttribute("dir", "rtl");
    }

    @Test
    public void Should_PlaceNavigationOnTheRight_When_LocaleIsArabic() {
        appShell.open();
        assertThat(appShell.navigation()).isVisible();

        assertThat(geometry.centerX(appShell.navigation())).as("navigation centre x").isGreaterThan(640.0);
    }
}
```

`Geometry.centerX(locator)` returns `box.x + box.width / 2` from `boundingBox()`; it measures, the test asserts.
The viewport is fixed in `contextOptions()`, so half its width is a known number.

## Deep-dive reference

`references/details.md` — **read it when the task touches them**: **1. Locale-pinned UI text** (a locale class
and a `@Factory` locale matrix); **3. Pseudo-localization**; **4b. Translation-key coverage**; **ICU plurals**.

## Anti-patterns

- **Asserting a hardcoded literal** (`hasText("Willkommen")`). *Fix:* `hasText(Catalog.t("home.title", locale))`.
- **Comparing the bundle to itself.** A tautology. *Fix:* the left side is the live DOM / formatted output.
- **Hardcoding a formatted number/date/currency** (`"1.234,56 €"`), including as a data-provider "expected"
  column. *Fix:* the expected value comes from ICU4J for the locale under test.
- **Letting the CI time zone or the wall clock float.** *Fix:* `setTimezoneId` on the context, `setTimeZone` on
  the formatter, `page.clock().setFixedTime(...)` before the page loads.
- **One context per class shared by its tests** (a private `Playwright.create()` in `@BeforeClass`, an
  `I18nBaseTest`). State leaks between tests and the order matters. *Fix:* extend `BaseTest`; locale in
  `contextOptions()`; a context per test.
- **A vacuous layout assertion** (`hasCSS("margin-inline-start", ".+")` matches any value). *Fix:* assert where
  the element is (`Geometry`), or the attribute that drives it (`dir="rtl"`).
- **Faking RTL with a CSS toggle.** *Fix:* a real RTL locale.
- **Only checking that keys *exist*.** *Fix:* presence **and** non-empty **and** no orphans **and** identical
  `{placeholders}`.
- **Testing plurals at only count 1 and 2.** *Fix:* the boundary counts the language has (`PluralRules`).
- **Concatenating translated fragments** (`t("welcome") + name`). *Fix:* one interpolated key.
- **Hardcoding the supported-locale list in each test.** *Fix:* `Catalog.SUPPORTED`.

## Examples

**A reword that would break a literal-based suite is a non-event here.** Marketing changes the German CTA from
`„Jetzt kaufen"` to `„Sofort bestellen"`. A literal suite turns red across every German test; this suite re-reads
`common_de.properties` through `Catalog.t("home.cta", locale)` and stays green — it asserts the button is wired to
`home.cta`, which is still true.

**Pseudo-loc catches the bug three other tests can't.** A developer hardcodes a `"Loading…"` spinner label. The
locale-pinned tests pass, the coverage diff passes (there's no key at all), but the pseudo-loc test fails:
`"Loading…"` appears *without* brackets, so it's flagged as bypassing i18n.

## Rules (hard constraints)

- **Never assert a hardcoded literal string.** The expected value is resolved from the **app's own bundle** by key
  or computed via ICU4J. Never compare the bundle to itself.
- **Formatting is asserted via ICU4J** for the locale under test, with the **time zone pinned** on the formatter
  and the context, and the **page clock frozen** for anything relative to now.
- **Every browser class extends `BaseTest`**; locale and time zone are set in `contextOptions()`, so each test
  method gets its own context. No class-level shared context, no second base class.
- **Pseudo-localization is a required CI gate:** every visible string wrapped in the pseudo markers, no label
  overflowing under +40% expansion.
- **RTL uses a real RTL locale** and asserts `<html dir="rtl">` plus a measured mirrored layout — not a CSS toggle.
- **Translation-key coverage is a static, build-gating test:** source keys ⊆ each target, no empty values, no
  orphan keys, identical `{placeholders}`.
- **The supported-locale list comes from one constant** (`Catalog.SUPPORTED`); the locale matrix is a `@Factory`
  over it. One logical assertion per test; `Should_X_When_Y`; no `Thread.sleep`; tests reach the page only
  through page objects.

## Cross-references

- `qa-language-testing-typescript` · `qa-language-testing-dotnet` — the sibling stacks; same four ideas.
- `qa-ui-test-writer-playwright-java` — `BaseTest`, `contextOptions()` (`lifecycle.md` §3) and the emulation
  reference (`emulation-and-mobile-web.md` §5 locale/time zone, §6 `page.clock()`).
- `qa-visual-regression-java` — pairs with the pseudo-loc **overflow** check: a pixel diff records *how* the
  layout broke; this skill asserts *that* it didn't.
- `qa-data-driven-testing-java` — the row pattern; the locale matrix feeds a `@Factory` because each locale needs
  its own context options.
- `qa-accessibility-testing-java` — `html[lang]` / `dir` a11y rules; run them together on the locale-pinned page.
- `qa-test-reports-java` — name each locale in the report so a failure says *which* language broke.
