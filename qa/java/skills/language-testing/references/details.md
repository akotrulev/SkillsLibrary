# Deep-dive details — `qa-language-testing-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## 1. Locale-pinned UI text — assert the DOM against the catalog (idea #1)

Pin the locale on the `BrowserContext` **and** tell the app which language to load (a `?lng=` query, a cookie, or
a `localStorage` seed — match your app). Then assert the rendered text equals the bundle entry, by key.

```java
// src/test/java/i18n/I18nBaseTest.java — one context per locale, locale + timezone pinned
package i18n;

import com.microsoft.playwright.*;
import com.microsoft.playwright.options.*;
import org.testng.annotations.*;
import java.util.Locale;

public abstract class I18nBaseTest {
  protected Playwright playwright;
  protected Browser browser;
  protected BrowserContext context;
  protected Page page;
  protected Locale locale;

  protected I18nBaseTest(Locale locale, String timezoneId) {
    this.locale = locale;
    this.timezoneId = timezoneId;
  }
  private final String timezoneId;

  @BeforeClass
  void launch() {
    playwright = Playwright.create();
    browser = playwright.chromium().launch();
    context = browser.newContext(new Browser.NewContextOptions()
        .setLocale(locale.toLanguageTag())            // e.g. "de-DE"
        .setTimezoneId(timezoneId));                  // e.g. "Europe/Berlin"
    context.addInitScript("localStorage.setItem('i18nextLng', '" + locale.toLanguageTag() + "')");
    page = context.newPage();
  }

  @AfterClass
  void close() { context.close(); browser.close(); playwright.close(); }

  protected String t(String key) { return Catalog.t(key, locale); }
}
```

```java
// src/test/java/i18n/HomeI18nDeTest.java  (one subclass per locale; or drive via @Factory + @DataProvider)
package i18n;

import org.testng.annotations.Test;
import java.util.Locale;
import java.util.Map;
import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

public class HomeI18nDeTest extends I18nBaseTest {
  public HomeI18nDeTest() { super(Locale.forLanguageTag("de"), "Europe/Berlin"); }

  @Test
  public void rendersHomeHeadingInActiveLocale() {
    page.navigate("/");
    // left side = live DOM; right side = the SAME bundle the app shipped — resolved by KEY
    assertThat(page.getByRole(AriaRole.HEADING)).hasText(t("home.title"));
    assertThat(page.getByRole(AriaRole.BUTTON,
        new Page.GetByRoleOptions().setName(t("home.cta")))).isVisible();
  }

  @Test
  public void interpolatesGreetingWithUserName() {
    page.navigate("/dashboard");
    // de: "Willkommen zurück, {name}" — assert the interpolated bundle string
    assertThat(page.getByTestId("greeting"))
        .hasText(Catalog.t("dashboard.greeting", locale, Map.of("name", "Trinity")));
  }
}
```

> This base, subclassed for `en`/`de`/`ar`, covers three languages with no per-locale literals. A reworded string
> in `common_de.properties` updates the expectation automatically — the test asserts the **wiring**, not the
> **words**.

## 4b. Translation-key coverage — a static bundle diff (idea #4)

No browser, no app — just compare the `.properties` bundles. Highest-value, cheapest, most deterministic i18n
test. Gate the build on it.

```java
// src/test/java/i18n/CoverageI18nTest.java
package i18n;

import org.testng.annotations.*;
import java.util.*;
import java.util.regex.*;
import static org.testng.Assert.assertTrue;

public class CoverageI18nTest {
  private Properties load(String tag) throws Exception {
    Properties p = new Properties();
    try (var in = getClass().getResourceAsStream("/i18n/common_" + tag + ".properties")) {
      p.load(new java.io.InputStreamReader(in, java.nio.charset.StandardCharsets.UTF_8));
    }
    return p;
  }

  @DataProvider(name = "targets")
  Object[][] targets() { return new Object[][] {{"de"}, {"ar"}}; }

  @Test(dataProvider = "targets")
  public void hasNoMissingKeys(String tag) throws Exception {
    Set<String> source = load("en").stringPropertyNames();
    Set<String> target = load(tag).stringPropertyNames();
    List<String> missing = source.stream().filter(k -> !target.contains(k)).sorted().toList();
    assertTrue(missing.isEmpty(), tag + " is missing: " + missing);       // missing → default-locale fallback
  }

  @Test(dataProvider = "targets")
  public void hasNoEmptyValues(String tag) throws Exception {
    Properties target = load(tag);
    List<String> empty = target.stringPropertyNames().stream()
        .filter(k -> target.getProperty(k).isBlank()).sorted().toList();
    assertTrue(empty.isEmpty(), tag + " has empty entries: " + empty);
  }

  @Test(dataProvider = "targets")
  public void hasNoOrphanKeys(String tag) throws Exception {
    Set<String> source = load("en").stringPropertyNames();
    List<String> orphans = load(tag).stringPropertyNames().stream()
        .filter(k -> !source.contains(k)).sorted().toList();
    assertTrue(orphans.isEmpty(), tag + " has orphan keys: " + orphans);
  }

  @Test(dataProvider = "targets")
  public void keepsPlaceholdersIdentical(String tag) throws Exception {
    Properties source = load("en"), target = load(tag);
    Pattern ph = Pattern.compile("\\{\\w+}");
    List<String> drifted = source.stringPropertyNames().stream()
        .filter(target::containsKey)
        .filter(k -> !placeholders(ph, source.getProperty(k)).equals(placeholders(ph, target.getProperty(k))))
        .sorted().toList();
    assertTrue(drifted.isEmpty(), tag + " placeholder mismatch: " + drifted);
  }

  private List<String> placeholders(Pattern ph, String s) {
    return ph.matcher(s).results().map(MatchResult::group).sorted().toList();
  }
}
```

> The placeholder check catches the bug a presence check misses: a translator who renders `Welcome back, {name}`
> as `Bienvenue` (dropping `{name}`) leaves the key present but breaks interpolation. Assert the placeholder set
> is identical.

## 3. Pseudo-localization — surface hardcoded strings and truncation (idea #3)

Transform every source value: accent the letters, expand ~40%, wrap in sentinel brackets. Load it as a real
locale (`en-XA`). Then **every visible string must be wrapped** — an unwrapped string is hardcoded and bypassed
i18n.

```java
// src/test/java/i18n/Pseudo.java — deterministic source→pseudo transform
package i18n;

import java.util.Map;

public final class Pseudo {
  public static final String OPEN = "[!! ", CLOSE = " !!]";
  private static final Map<Character, String> MAP = Map.of(
      'a', "á", 'e', "ḗ", 'i', "í", 'o', "ö", 'u', "ṵ", 'c', "ḉ", 'l', "ḷ", 'm', "ṁ", 'w', "ŵ");

  private Pseudo() {}

  /** Accent + ~40% pad + bracket-wrap, leaving ICU {placeholders} untouched. */
  public static String localize(String text) {
    StringBuilder accented = new StringBuilder();
    boolean inBrace = false;
    for (char c : text.toCharArray()) {
      if (c == '{') inBrace = true; else if (c == '}') inBrace = false;
      accented.append(inBrace ? c : MAP.getOrDefault(Character.toLowerCase(c), String.valueOf(c)));
    }
    int letters = (int) accented.chars().filter(Character::isLetter).count();
    String pad = "~".repeat((int) Math.ceil(letters * 0.4));
    return OPEN + accented + pad + CLOSE;
  }
}
```

```java
// src/test/java/i18n/PseudoI18nTest.java — runs against the en-XA build
package i18n;

import org.testng.annotations.Test;
import java.util.List;
import java.util.Locale;
import static org.testng.Assert.assertTrue;

public class PseudoI18nTest extends I18nBaseTest {
  public PseudoI18nTest() { super(Locale.forLanguageTag("en-XA"), "UTC"); }

  @Test
  public void everyVisibleStringWentThroughI18n() {
    page.navigate("/checkout");
    List<String> leaks = page.getByText(java.util.regex.Pattern.compile("\\S")).allInnerTexts().stream()
        .map(String::trim)
        .filter(s -> s.length() > 1 && !(s.contains(Pseudo.OPEN) || s.contains(Pseudo.CLOSE)))
        .toList();
    assertTrue(leaks.isEmpty(), "hardcoded strings bypassing i18n: " + leaks);
  }

  @Test
  public void noLabelIsClippedUnderExpansion() {
    page.navigate("/checkout");
    boolean clipped = (Boolean) page.getByTestId("submit")
        .evaluate("el => el.scrollWidth > el.clientWidth + 1");   // overflow == truncation bug
    assertTrue(!clipped, "submit button truncates its label");
  }
}
```

> Pseudo-loc needs **zero translators**, so it's the first i18n gate you can run — wire it into CI before any real
> locale exists. Pair the overflow check with `qa-visual-regression-java` for a pixel record.
