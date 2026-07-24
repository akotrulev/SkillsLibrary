---
name: qa-i18n-testing-java
description: Use when writing i18n/localization tests in Java 21 — Playwright-Java + TestNG pinned to a locale, asserting via the app's own `ResourceBundle` (`.properties`) catalog **by key** (never a hardcoded literal string), ICU4J (`com.ibm.icu.text.*`) for number/date/currency formatting, plus pseudo-localization and RTL checks. Triggers "write an i18n test in Java", "test German/Arabic rendering with Playwright-Java", "assert currency/date formatting per locale with ICU4J", "pseudo-localization pass", "check RTL layout". Do NOT use for the frontend's own localization wiring (that is the `fe-*` stack's `localization` skill), for breakpoint/viewport layout (use `qa-responsive-testing-java`), or for non-Java projects (use `qa-i18n-testing-{dotnet,typescript}`). For end-to-end suite work prefer the phased agent `qa-ui-java` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — i18n / Localization Testing (Java 21 / Playwright-Java + TestNG + ICU4J)

Tests that a web app is correctly **internationalized** (locale switching, formatting, layout, catalog
completeness) and **localized** (the right strings render per locale). It splits by the nature of the assertion:
**Playwright-Java** drives the app in a pinned locale for the UI-rendered checks, and **plain TestNG** unit tests
own the pure-function checks (ICU formatting math, the pseudo-loc transform, and the static catalog-coverage diff
that needs no browser). Both halves share the fact that makes i18n testing its own discipline: **the literal
string on screen is the variable, not the constant — so the assertion can never be a hardcoded literal.**

> **The discipline this skill encodes** — four ideas that separate a correct i18n test from a UI-test reflex:
>
> 1. **Pin the locale; assert against the catalog by KEY, never a hardcoded literal.** Drive the app with an
>    explicit locale and resolve the expected text from the **same bundle the app ships**
>    (`bundle.getString("home.title")`), not a copied-in literal. `assertThat(h).hasText("Willkommen")` breaks the
>    instant a copywriter rewords the German and only ever tests *one* language. Resolving via the bundle survives
>    rewording and runs for **every** locale from one test body. (You assert the *rendered DOM* against the
>    bundle — proving the app wired the key to the screen. Asserting `bundle.getString(k)` against itself is a
>    tautology; don't.)
> 2. **Format is locale-derived — assert via ICU4J, never a hardcoded format.** `1,234.56` (en) vs `1.234,56`
>    (de) vs `1 234,56` (fr); `$1,234.56` vs `1.234,56 €`; `Mar 14, 2026` vs `14.03.2026`. Assert the rendered
>    value equals `com.ibm.icu.text.NumberFormat.getCurrencyInstance(locale).format(n)` — **derive** the
>    expectation from the same CLDR data; don't hardcode a formatted string (which bakes in one locale and rots
>    on an ICU upgrade). Pin the **timezone** on the `DateFormat` — date formatting is TZ-sensitive and a
>    floating CI TZ makes it flaky.
> 3. **Pseudo-localize to surface hardcoded + truncated strings — before any real translation exists.** A
>    pseudo-locale transforms source text into an accented, bracketed, ~40%-longer fake language
>    (`Welcome` → `[!! Ŵḗḷḉöṁḗ !!]`). It makes three bug classes visible *at test time, with no translators*: (a)
>    any **un-accented / un-bracketed** text on screen is a **hardcoded string** that bypassed i18n; (b) **clipped
>    or overflowing** text is a layout-too-tight bug the +40% expansion forces out; (c) broken **concatenation**
>    (`"Welcome " + name`) shows up garbled. It's the cheap first gate that runs every CI build.
> 4. **RTL is a layout assertion; coverage is a static one — and they're separate from the text checks.** **RTL**
>    (`ar`/`he`) mirrors the *whole* UI — assert `<html dir="rtl">` and that logical-property layout actually
>    flipped, using a **real RTL locale**, not a CSS `direction` toggle. **Translation-key coverage** is a
>    **static** check (no browser): every key in the source bundle is present and **non-empty** in every target
>    bundle (missing key → silent default-locale fallback in prod) and there are **no orphan** keys. The bundle
>    diff is the cheapest, most deterministic i18n test there is — it gates the build.

## Decision matrix — i18n surface → test shape

| Surface | What you're proving | Runner | Test shape |
|---------|---------------------|--------|------------|
| **Locale-pinned UI text** | The right translation renders for a locale | Playwright-Java | `setLocale` context + app `lng` → `assertThat(el).hasText(bundle.getString(key))` |
| **Date / number / currency** | Locale-correct formatting | Playwright-Java or TestNG | assert rendered `.equals` ICU `NumberFormat`/`DateFormat(locale)`, **timezone pinned** |
| **Pseudo-localization** | No hardcoded strings; no truncation | Playwright-Java | render in pseudo-locale → assert visible text wrapped in markers; screenshot for overflow |
| **RTL layout** | UI mirrors for RTL scripts | Playwright-Java | `ar`/`he` locale → `assertThat(html).hasAttribute("dir", "rtl")` + mirrored-layout assertion |
| **Translation-key coverage** | Every bundle complete; no orphans | TestNG (static) | diff source keys vs each target: source ⊆ target, no empty values, no extra keys |
| **ICU plural / select** | Plurals & gender resolve per language | TestNG | format the message at count 0/1/2/5 → assert the right plural category renders |
| **Locale matrix** | All supported locales pass one journey | Playwright-Java | `@DataProvider` over the supported-locale list → `qa-data-driven-testing-java` |

## Stack

- Java 21 + Gradle (Kotlin DSL)
- **Playwright-Java** (`com.microsoft.playwright`) — the locale-pinned UI half (`setLocale` + `setTimezoneId`)
- **TestNG** — both the Playwright specs and the pure-function unit tests (ICU math, pseudo-loc, the static diff)
- The app's **own catalog source** — `ResourceBundle` `.properties` files
  (`src/main/resources/i18n/common_en.properties`, `…_de.properties`, `…_ar.properties`). Tests load the **same**
  bundle the app ships.
- **ICU4J** (`com.ibm.icu:icu4j`) — `NumberFormat`, `DateFormat`, `MessageFormat`, `PluralRules` for formatting
  expectations (CLDR-backed; richer + more current than `java.text`)
- The **supported-locale list** comes from one constant (`SupportedLocales.ALL`), reused by every matrix test
- Locale + timezone set on the `BrowserContext`, **never** hardcoded per test; one canonical pseudo-locale id
  (`en-XA`)

> **Why import the app's bundle instead of asserting literals?** The bundle is the single source of truth the app
> renders from. Resolving expectations from it makes the test assert the *binding* (key → DOM) rather than the
> *content* (the English words) — a copy change is a non-event, and the same test body runs across every locale.
> The one thing you must not do is compare the bundle to itself; the assertion's left side is always the **live
> DOM / formatted output**, the right side is the bundle / ICU.

## The catalog + a test-side resolver

The app ships `.properties` bundles; the test loads the same bundle and (for interpolation) formats with ICU
`MessageFormat` (named `{name}` arguments). This is **not** a second translation system — it's a read-only view
of the same files.

```java
// src/test/java/i18n/Catalog.java
package i18n;

import com.ibm.icu.text.MessageFormat;
import java.util.*;

public final class Catalog {
  public static final List<Locale> SUPPORTED = List.of(
      Locale.forLanguageTag("en"), Locale.forLanguageTag("de"), Locale.forLanguageTag("ar"));
  public static final Set<Locale> RTL = Set.of(Locale.forLanguageTag("ar"));

  private Catalog() {}

  /** Read-only mirror of the app's bundle lookup. */
  public static String t(String key, Locale lng) {
    ResourceBundle bundle = ResourceBundle.getBundle("i18n.common", lng);
    if (!bundle.containsKey(key)) throw new MissingResourceException(
        "Missing key " + key + " for " + lng, Catalog.class.getName(), key);
    return bundle.getString(key);
  }

  /** Same lookup + ICU named-argument interpolation: "Welcome back, {name}". */
  public static String t(String key, Locale lng, Map<String, Object> vars) {
    return new MessageFormat(t(key, lng), lng).format(vars);
  }
}
```

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **1. Locale-pinned UI text — assert the DOM against the catalog (idea #1)**; **4b. Translation-key coverage — a static bundle diff (idea #4)**; **3. Pseudo-localization — surface hardcoded strings and truncation (idea #3)**.

## 2. Date / number / currency — assert via ICU4J, timezone pinned (idea #2)

Never hardcode `"1.234,56 €"`. Build the expectation from ICU4J for the locale under test — the same primitive
the app should use — so the test tracks CLDR updates and proves the app passed the right pattern.

```java
// src/test/java/i18n/FormattingI18nTest.java
package i18n;

import com.ibm.icu.text.*;
import com.ibm.icu.util.*;
import org.testng.annotations.*;
import java.util.Date;
import java.util.Locale;
import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.testng.Assert.assertEquals;

public class FormattingI18nTest extends I18nBaseTest {
  public FormattingI18nTest() { super(Locale.forLanguageTag("de"), "Europe/Berlin"); }

  @Test
  public void formatsCartTotalAsLocaleCurrency() {
    page.navigate("/cart");                            // seeded total: 1234.5 EUR
    NumberFormat fmt = NumberFormat.getCurrencyInstance(locale);
    fmt.setCurrency(Currency.getInstance("EUR"));
    assertThat(page.getByTestId("cart-total")).hasText(fmt.format(1234.5));   // de → "1.234,50 €"
  }

  @Test
  public void formatsOrderDateForLocaleAndPinnedTimezone() {
    page.navigate("/orders/1");                        // order at a fixed instant
    DateFormat fmt = DateFormat.getDateInstance(DateFormat.LONG, locale);
    fmt.setTimeZone(TimeZone.getTimeZone("Europe/Berlin"));   // pin TZ — date formatting is TZ-sensitive
    String expected = fmt.format(new Date(1773478800000L));   // 2026-03-14T09:00:00Z
    assertThat(page.getByTestId("order-date")).hasText(expected);
  }

  @DataProvider(name = "currency")
  Object[][] currency() {
    return new Object[][] {
        {"en", "€1,234.50"}, {"de", "1.234,50 €"}, {"fr", "1 234,50 €"},   // note non-breaking spaces
    };
  }

  @Test(dataProvider = "currency")
  public void formatsEur(String tag, String expected) {   // pure-function: no browser needed
    NumberFormat fmt = NumberFormat.getCurrencyInstance(Locale.forLanguageTag(tag));
    fmt.setCurrency(Currency.getInstance("EUR"));
    assertEquals(fmt.format(1234.5), expected);
  }
}
```

> Two gotchas ICU4J catches and a hardcoded literal hides: many locales use **non-breaking** / **narrow-no-break**
> spaces inside formatted numbers — a copy-pasted "looks right" literal uses a normal space and fails. And
> asserting against ICU means an icu4j upgrade that changes a format updates *both* sides together, instead of a
> literal silently drifting.

## 4a. RTL — assert the layout mirrors (idea #4)

Use a **real RTL locale** (`ar`), not a `direction: rtl` CSS hack.

```java
// src/test/java/i18n/RtlI18nTest.java — runs under the ar locale
package i18n;

import com.microsoft.playwright.options.BoundingBox;
import org.testng.annotations.Test;
import java.util.Locale;
import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.testng.Assert.assertTrue;

public class RtlI18nTest extends I18nBaseTest {
  public RtlI18nTest() { super(Locale.forLanguageTag("ar"), "Africa/Cairo"); }

  @Test
  public void mirrorsLayoutForRtlLocale() {
    page.navigate("/");
    assertThat(page.locator("html")).hasAttribute("dir", "rtl");      // the document declares RTL
    BoundingBox nav = page.getByRole(AriaRole.NAVIGATION).boundingBox();
    int viewportWidth = (Integer) page.evaluate("() => window.innerWidth");
    assertTrue(nav.x > viewportWidth / 2.0, "nav should sit on the right in RTL");
    assertThat(page.getByRole(AriaRole.NAVIGATION)).hasCSS("margin-inline-start",
        java.util.regex.Pattern.compile(".+"));
  }
}
```

## ICU plurals & gender — assert the category, per language

English has two plural categories (one/other); Polish four; Arabic six. Exercise the **boundary counts** the
language has, not just 1 and 2.

```java
// src/test/java/i18n/PluralI18nTest.java
package i18n;

import com.ibm.icu.text.*;
import org.testng.annotations.*;
import java.util.Locale;
import java.util.Map;
import static org.testng.Assert.*;

public class PluralI18nTest {
  private final MessageFormat en = new MessageFormat(
      "{count, plural, =0 {no items} one {# item} other {# items}}", Locale.ENGLISH);

  @DataProvider(name = "counts")
  Object[][] counts() { return new Object[][] {{0, "no items"}, {1, "1 item"}, {2, "2 items"}, {5, "5 items"}}; }

  @Test(dataProvider = "counts")
  public void enRendersPluralCategory(int count, String expected) {
    assertEquals(en.format(Map.of("count", count)), expected);   // exercises =0, one, other
  }

  @Test
  public void arabicNeedsMoreThanOneAndOther() {
    PluralRules ar = PluralRules.forLocale(Locale.forLanguageTag("ar"));
    var cats = new java.util.HashSet<String>();
    for (int n : new int[] {0, 1, 2, 3, 11, 100}) cats.add(ar.select(n));
    assertTrue(cats.size() > 2, "Arabic needs more than one/other plural categories");
  }
}
```

## Locale matrix — one journey across every supported locale

Bind the supported-locale list as data via `@DataProvider` rather than copy-pasting the spec — this is
`qa-data-driven-testing-java` applied to locales.

```java
@DataProvider(name = "supportedLocales")
Object[][] supportedLocales() {
  return Catalog.SUPPORTED.stream().map(l -> new Object[]{l}).toArray(Object[][]::new);
}

@Test(dataProvider = "supportedLocales")
public void checkoutCompletes(Locale lng) {
  try (BrowserContext ctx = browser.newContext(new Browser.NewContextOptions().setLocale(lng.toLanguageTag()))) {
    Page p = ctx.newPage();
    p.navigate("/checkout");
    p.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName(Catalog.t("checkout.pay", lng))).click();
    assertThat(p.getByTestId("confirmation")).hasText(Catalog.t("checkout.success", lng));
  }
}
```

## Anti-patterns

- **Asserting a hardcoded literal** (`hasText("Willkommen")`). Breaks on any reword; only tests one language.
  *Fix:* `hasText(t("home.title"))` — resolve from the shipped bundle, by key.
- **Comparing the bundle to itself** (`assertEquals(t("k"), t("k"))`). A tautology. *Fix:* the left side is always
  the **live DOM / formatted output**; the bundle is only ever the expected side.
- **Hardcoding a formatted number/date/currency** (`"1.234,56 €"`). Bakes in one locale, uses the wrong spaces,
  rots on an ICU upgrade. *Fix:* assert against ICU4J `NumberFormat`/`DateFormat` for the locale under test.
- **Letting the CI timezone float for date assertions.** ICU `DateFormat` is TZ-sensitive → flaky. *Fix:*
  `setTimeZone` on the formatter **and** `setTimezoneId` on the context.
- **Faking RTL with a CSS toggle.** Doesn't exercise the app's direction logic, bidi, or mirrored assets. *Fix:*
  drive a real RTL locale (`ar`/`he`); assert `<html dir="rtl">` + a mirrored-layout property.
- **Only checking that keys *exist*.** Misses empty values, orphans, and dropped placeholders. *Fix:* the static
  diff asserts presence **and** non-empty **and** no-orphans **and** identical `{placeholders}`.
- **Testing plurals at only count 1 and 2.** Misses zero/few/many categories Polish/Russian/Arabic need. *Fix:*
  exercise the boundary counts the language has (drive from `PluralRules`).
- **Concatenating translated fragments** (`t("welcome") + name`). Can't reorder for languages that put the name
  first. *Fix:* one interpolated key (`"Welcome, {name}"`); pseudo-loc surfaces the concatenation.
- **Hardcoding the supported-locale list in each test.** Drifts from the app's real list. *Fix:* import
  `Catalog.SUPPORTED`; drive the matrix from it.

## Examples

**A reword that would break a literal-based suite is a non-event here.** Marketing changes the German CTA from
`„Jetzt kaufen"` to `„Sofort bestellen"`. A literal suite turns red across every German test; this suite re-reads
`common_de.properties` through `t("home.cta")` and stays green — it asserts the button is wired to `home.cta`,
which is still true.

**Pseudo-loc catches the bug three other tests can't.** A developer hardcodes a `"Loading…"` spinner label
directly in a template. The locale-pinned tests pass (the bundle is complete), the coverage diff passes (no key
is missing — there's no key at all), but the pseudo-loc test fails: `"Loading…"` appears *without* brackets, so
it's flagged as bypassing i18n. That's the class of bug pseudo-localization exists to find.

## Rules (hard constraints)

- **Never assert a hardcoded literal string.** The expected value is always resolved from the **app's own bundle**
  by key (`Catalog.t(key, lng)`) or computed via ICU4J — never copied in. Never compare the bundle to itself.
- **Formatting is asserted via ICU4J** (`NumberFormat`/`DateFormat`/`PluralRules`) for the locale under test, with
  the **timezone pinned** on both the formatter and the `BrowserContext`.
- **Pseudo-localization is a required CI gate:** every visible string must be wrapped in the pseudo markers, and
  no label may overflow its box under +40% expansion.
- **RTL uses a real RTL locale** and asserts `<html dir="rtl">` plus a mirrored-layout property — not a CSS toggle.
- **Translation-key coverage is a static, build-gating test:** source keys ⊆ each target, no empty values, no
  orphan keys, identical `{placeholders}`.
- **The supported-locale list comes from one constant** (`Catalog.SUPPORTED`), reused by every matrix test.
  Locale + timezone are set on the context, never hardcoded per test.
- **One logical assertion per test; no `Thread.sleep`/`page.waitForTimeout`; nullable handled.** Locale-matrix
  expansion uses `@DataProvider` (`qa-data-driven-testing-java`), never copy-paste.

## Cross-references

- `qa-i18n-testing-typescript` (canonical) · `qa-i18n-testing-dotnet` — the sibling stacks (Playwright + Vitest +
  i18next + `Intl` · Playwright .NET + NUnit + `CultureInfo` / `.resx`); same four ideas, different catalog +
  formatting APIs.
- `qa-ui-test-author-playwright-java` — the base Playwright-Java / page-object conventions this builds on; i18n
  adds the locale dimension on top.
- `qa-visual-regression-java` — pairs with the pseudo-loc **overflow** check: a pixel
  diff records *how* the layout broke; this skill asserts *that* it didn't.
- `qa-data-driven-testing-java` — the locale matrix is its `@DataProvider` row-binding applied to the
  supported-locale list.
- `qa-accessibility-testing-java` — RTL + language correctness overlaps with the `html[lang]`
  / `dir` a11y rules; run them together on the locale-pinned page.
- `qa-allure-reporting-java` — render each locale (and the pseudo-locale) as a named result / Allure parameter so
  a failure says *which* language broke.
