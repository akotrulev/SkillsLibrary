# Deep-dive details — `qa-java:language-testing`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs. Every browser class extends J1's
`BaseTest` (`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`) and sets its locale in
`contextOptions()` from a `LocaleUnderTest` (SKILL.md § The locale under test), so each test method gets its own
context.

## 1. Locale-pinned UI text — assert the DOM against the catalog (idea #1)

Pin the locale on the context (and, for a SPA that keeps its own language, tell it in `@BeforeMethod`). Then
assert the rendered text equals the bundle entry, by key: the left side is the live DOM, the right side is the
same bundle the app shipped.

```java
package i18n;

public class HomeI18nGermanTest extends BaseTest {
    private final LocaleUnderTest lut = LocaleUnderTest.GERMAN;
    private HomePage homePage;
    private DashboardPage dashboardPage;

    @Override
    protected Browser.NewContextOptions contextOptions() {
        return lut.contextOptions();
    }

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        homePage = new HomePage(page);
        dashboardPage = new DashboardPage(page);
    }

    @Test
    public void Should_RenderHomeHeadingFromCatalog_When_LocaleIsGerman() {
        homePage.open();

        assertThat(homePage.heading()).hasText(Catalog.t("home.title", lut.locale()));
    }

    @Test
    public void Should_InterpolateGreetingWithUserName_When_LocaleIsGerman() {
        dashboardPage.open();

        assertThat(dashboardPage.greeting())
                .hasText(Catalog.t("dashboard.greeting", lut.locale(), Map.of("name", TestUsers.STANDARD.displayName())));
    }
}
```

A reworded string in `common_de.properties` updates the expectation automatically — the test asserts the
**wiring**, not the **words**.

### The locale matrix — one journey across every supported locale

A class that must pass in every supported locale is a TestNG `@Factory` over `Catalog.SUPPORTED`: one instance
per locale, each instance's `contextOptions()` carrying its locale. TestNG runs `@BeforeClass` once per
instance, so each locale gets its own browser on the class's one thread (`parallel="classes"` holds), and each
test its own context.

```java
public class CheckoutI18nTest extends BaseTest {
    private final LocaleUnderTest lut;
    private CheckoutPage checkoutPage;

    @Factory(dataProvider = "supportedLocales")
    public CheckoutI18nTest(LocaleUnderTest lut) {
        this.lut = lut;
    }

    @DataProvider
    public static Object[][] supportedLocales() {
        return Catalog.SUPPORTED.stream()
                .map(locale -> new Object[] {new LocaleUnderTest(locale, "UTC")})
                .toArray(Object[][]::new);
    }

    @Override
    protected Browser.NewContextOptions contextOptions() {
        return lut.contextOptions();
    }

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        checkoutPage = new CheckoutPage(page);
    }

    @Test
    public void Should_ConfirmPayment_When_CheckoutCompletesInTheLocale() {
        checkoutPage.open();

        checkoutPage.pay(Catalog.t("checkout.pay", lut.locale()));

        assertThat(checkoutPage.confirmation()).hasText(Catalog.t("checkout.success", lut.locale()));
    }
}
```

`checkoutPage.pay(label)` clicks `getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions().setName(label))` — the
page object owns the locator; the test supplies the translated name. The `@Factory` data provider is `static` and
sequential (no `parallel = true` with Playwright).

## 3. Pseudo-localization — surface hardcoded strings and truncation (idea #3)

Transform every source value: accent the letters, expand ~40%, wrap in sentinel brackets, leaving ICU
`{placeholders}` untouched. Load it as a real locale (`en-XA`). Then **every visible string must be wrapped** — an
unwrapped string is hardcoded and bypassed i18n.

```java
package i18n;

import java.util.Map;

public final class Pseudo {
    public static final String OPEN = "[!! ";
    public static final String CLOSE = " !!]";
    private static final Map<Character, String> ACCENTS = Map.of(
            'a', "á", 'e', "ḗ", 'i', "í", 'o', "ö", 'u', "ṵ", 'c', "ḉ", 'l', "ḷ", 'm', "ṁ", 'w', "ŵ");

    private Pseudo() {}

    public static String localize(String text) {
        StringBuilder accented = new StringBuilder();
        boolean inPlaceholder = false;
        for (char c : text.toCharArray()) {
            if (c == '{') {
                inPlaceholder = true;
            } else if (c == '}') {
                inPlaceholder = false;
            }
            accented.append(inPlaceholder ? String.valueOf(c)
                    : ACCENTS.getOrDefault(Character.toLowerCase(c), String.valueOf(c)));
        }
        long letters = accented.chars().filter(Character::isLetter).count();
        return OPEN + accented + "~".repeat((int) Math.ceil(letters * 0.4)) + CLOSE;
    }
}
```

```java
public class PseudoI18nTest extends BaseTest {
    private CheckoutPage checkoutPage;
    private Geometry geometry;

    @Override
    protected Browser.NewContextOptions contextOptions() {
        return LocaleUnderTest.PSEUDO.contextOptions();
    }

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        checkoutPage = new CheckoutPage(page);
        geometry = new Geometry(page);
    }

    @Test
    public void Should_WrapEveryVisibleString_When_LocaleIsPseudo() {
        checkoutPage.open();

        assertThat(checkoutPage.visibleTexts())
                .as("hardcoded strings bypassing i18n")
                .allSatisfy(text -> assertThat(text).startsWith(Pseudo.OPEN.strip()).endsWith(Pseudo.CLOSE.strip()));
    }

    @Test
    public void Should_NotClipSubmitLabel_When_LocaleIsPseudo() {
        checkoutPage.open();

        assertThat(geometry.horizontalClip(checkoutPage.submit())).as("submit label overflow px").isZero();
    }
}
```

- `checkoutPage.visibleTexts()` returns the trimmed inner texts of the page's visible text nodes after `open()`
  has waited for the form; it is a read for an AssertJ assertion, made once the page has settled.
- `Geometry.horizontalClip(locator)` evaluates `el => Math.max(0, el.scrollWidth - el.clientWidth)` on the
  element; `0` is the one expected value. Pair it with `qa-java:visual-regression` for a pixel record.
- Pseudo-loc needs **zero translators**, so it's the first i18n gate you can run — wire it into CI before any real
  locale exists.

## 4b. Translation-key coverage — a static bundle diff (idea #4)

No browser, no app — just compare the `.properties` bundles. Highest-value, cheapest, most deterministic i18n
test. Gate the build on it.

```java
package i18n;

import org.testng.annotations.*;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.*;

import static org.assertj.core.api.Assertions.assertThat;

public class CoverageI18nTest {
    private static final Pattern PLACEHOLDER = Pattern.compile("\\{\\w+}");

    @DataProvider
    public static Object[][] targets() {
        return new Object[][] {{"de"}, {"ar"}};
    }

    @Test(dataProvider = "targets")
    public void Should_HaveEverySourceKey_When_BundleIsTranslated(String tag) throws Exception {
        Properties target = load(tag);

        assertThat(load("en").stringPropertyNames()).as(tag + " missing keys").allMatch(target::containsKey);
    }

    @Test(dataProvider = "targets")
    public void Should_HaveNoEmptyValues_When_BundleIsTranslated(String tag) throws Exception {
        Properties target = load(tag);

        assertThat(target.stringPropertyNames()).as(tag + " empty entries")
                .noneMatch(key -> target.getProperty(key).isBlank());
    }

    @Test(dataProvider = "targets")
    public void Should_HaveNoOrphanKeys_When_BundleIsTranslated(String tag) throws Exception {
        Set<String> source = load("en").stringPropertyNames();

        assertThat(load(tag).stringPropertyNames()).as(tag + " orphan keys").allMatch(source::contains);
    }

    @Test(dataProvider = "targets")
    public void Should_KeepPlaceholdersIdentical_When_BundleIsTranslated(String tag) throws Exception {
        Properties source = load("en");
        Properties target = load(tag);

        assertThat(source.stringPropertyNames()).as(tag + " placeholder mismatch")
                .filteredOn(target::containsKey)
                .allMatch(key -> placeholders(source.getProperty(key)).equals(placeholders(target.getProperty(key))));
    }

    private static Properties load(String tag) throws Exception {
        Properties properties = new Properties();
        try (InputStream in = CoverageI18nTest.class.getResourceAsStream("/i18n/common_" + tag + ".properties")) {
            properties.load(new InputStreamReader(Objects.requireNonNull(in, "common_" + tag), StandardCharsets.UTF_8));
        }
        return properties;
    }

    private static List<String> placeholders(String value) {
        return PLACEHOLDER.matcher(value).results().map(MatchResult::group).sorted().toList();
    }
}
```

AssertJ's `allMatch` / `noneMatch` failure lists the offending elements, so the report names every missing,
empty, orphan or drifted key. The placeholder check catches the bug a presence check misses: a translator who
renders `Welcome back, {name}` as `Bienvenue` leaves the key present but breaks interpolation.

## ICU plurals — assert the category, per language

English has two plural categories (one/other); Polish four; Arabic six. Exercise the **boundary counts** the
language has, not just 1 and 2. The cases are rows; no loop drives an assertion.

```java
package i18n;

import com.ibm.icu.text.MessageFormat;
import com.ibm.icu.text.PluralRules;
import org.testng.annotations.*;

import java.util.Locale;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

public class PluralI18nTest {
    private final MessageFormat english = new MessageFormat(
            "{count, plural, =0 {no items} one {# item} other {# items}}", Locale.ENGLISH);

    @DataProvider
    public static Object[][] englishCounts() {
        return new Object[][] {{0, "no items"}, {1, "1 item"}, {2, "2 items"}, {5, "5 items"}};
    }

    @Test(dataProvider = "englishCounts")
    public void Should_RenderEnglishPluralCategory_When_CountIs(int count, String expected) {
        assertThat(english.format(Map.of("count", count))).isEqualTo(expected);
    }

    @Test
    public void Should_HaveSixPluralCategories_When_LanguageIsArabic() {
        PluralRules arabic = PluralRules.forLocale(Locale.forLanguageTag("ar"));

        assertThat(arabic.getKeywords()).containsExactlyInAnyOrder("zero", "one", "two", "few", "many", "other");
    }
}
```

The English rows test the app's *message pattern* (its `=0` branch and the `#` placement). The Arabic test pins
the six categories every Arabic plural message must cover; render the message at a count from each category
(0, 1, 2, 3, 11, 100) as rows of the locale-pinned UI test.
