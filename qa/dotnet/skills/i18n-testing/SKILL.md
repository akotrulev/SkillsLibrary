---
name: qa-i18n-testing-dotnet
description: >-
  Write **internationalization (i18n) / localization tests** in .NET 8 / C# with Playwright .NET + NUnit, the
  app's own `.resx` / `ResourceManager` (or `IStringLocalizer`) catalog, and `CultureInfo` (plus ICU4N for plural
  categories) for formatting. Covers the trait that makes i18n testing its own discipline: **you never assert a
  hardcoded literal string — the literal is exactly what changes per locale**. Instead you (1) **pin a culture**
  (`BrowserNewContextOptions.Locale`) and assert the rendered DOM against the **same catalog the app ships,
  resolved by KEY** (`rm.GetString("home.title", culture)`), not an English copy; (2) assert dates/numbers/currency
  against `CultureInfo` (`value.ToString("C", culture)`) for that culture, with the timezone pinned, never a
  hardcoded `"1.234,56"`; (3) render in a **pseudo-locale** (`[!! Ŵḗḷḉöṁḗ !!]`, ~40% expanded) to surface
  **hardcoded strings** that bypassed i18n and **truncation**; and (4) assert **RTL** layout mirrors
  (`<html dir="rtl">` for `ar`/`he`) and run a **static translation-key-coverage** check (every source key present
  + non-empty in every target resource set, no orphans). Also covers ICU plural/select categories and an NUnit
  `[TestCaseSource]` locale matrix. Triggers: "write an i18n test in C#", "test German/Arabic rendering with
  Playwright .NET", "assert currency/date formatting per culture", "add pseudo-localization", "check for missing
  keys in .resx", "test RTL". Do NOT use for: the TypeScript stack (use qa-i18n-testing-typescript), the Java
  stack (use qa-i18n-testing-java), generic Playwright .NET UI tests with no locale dimension (use
  qa-ui-test-author-playwright-dotnet), pixel-diff visual regression (use
  qa-visual-regression-playwright-snapshots-dotnet), or translating the strings themselves (a content task).
---

# QA — i18n / Localization Testing (.NET 8 / Playwright .NET + NUnit + CultureInfo)

Tests that a web app is correctly **internationalized** (culture switching, formatting, layout, catalog
completeness) and **localized** (the right strings render per culture). It splits by the nature of the assertion:
**Playwright .NET** drives the app in a pinned culture for the UI-rendered checks, and **plain NUnit** unit tests
own the pure-function checks (`CultureInfo` formatting math, the pseudo-loc transform, and the static
catalog-coverage diff that needs no browser). Both halves share the fact that makes i18n testing its own
discipline: **the literal string on screen is the variable, not the constant — so the assertion can never be a
hardcoded literal.**

> **The discipline this skill encodes** — four ideas that separate a correct i18n test from a UI-test reflex:
>
> 1. **Pin the culture; assert against the catalog by KEY, never a hardcoded literal.** Drive the app with an
>    explicit culture and resolve the expected text from the **same resources the app ships**
>    (`rm.GetString("home.title", culture)`), not a copied-in literal. `Expect(h).ToHaveTextAsync("Willkommen")`
>    breaks the instant a copywriter rewords the German and only ever tests *one* language. Resolving via the
>    `ResourceManager` survives rewording and runs for **every** culture from one test body. (You assert the
>    *rendered DOM* against the resources — proving the app wired the key to the screen. Asserting
>    `rm.GetString(k)` against itself is a tautology; don't.)
> 2. **Format is culture-derived — assert via `CultureInfo`, never a hardcoded format.** `1,234.56` (en) vs
>    `1.234,56` (de) vs `1 234,56` (fr); `$1,234.56` vs `1.234,56 €`; `3/14/2026` vs `14.03.2026`. Assert the
>    rendered value equals `n.ToString("C", culture)` — **derive** the expectation from the same CLDR/ICU data
>    .NET uses; don't hardcode a formatted string (which bakes in one culture and rots on a globalization-data
>    update). Pin the **timezone** (convert the instant via `TimeZoneInfo`) — date formatting is TZ-sensitive and
>    a floating CI TZ makes it flaky.
> 3. **Pseudo-localize to surface hardcoded + truncated strings — before any real translation exists.** A
>    pseudo-locale transforms source text into an accented, bracketed, ~40%-longer fake language
>    (`Welcome` → `[!! Ŵḗḷḉöṁḗ !!]`). It makes three bug classes visible *at test time, with no translators*: (a)
>    any **un-accented / un-bracketed** text on screen is a **hardcoded string** that bypassed i18n; (b) **clipped
>    or overflowing** text is a layout-too-tight bug the +40% expansion forces out; (c) broken **concatenation**
>    (`"Welcome " + name`) shows up garbled. It's the cheap first gate that runs every CI build.
> 4. **RTL is a layout assertion; coverage is a static one — and they're separate from the text checks.** **RTL**
>    (`ar`/`he`) mirrors the *whole* UI — assert `<html dir="rtl">` and that logical-property layout actually
>    flipped, using a **real RTL culture**, not a CSS `direction` toggle. **Translation-key coverage** is a
>    **static** check (no browser): every key in the source resource set is present and **non-empty** in every
>    target set (missing key → silent invariant/parent fallback in prod) and there are **no orphan** keys. The
>    resource diff is the cheapest, most deterministic i18n test there is — it gates the build.

## Decision matrix — i18n surface → test shape

| Surface | What you're proving | Runner | Test shape |
|---------|---------------------|--------|------------|
| **Culture-pinned UI text** | The right translation renders for a culture | Playwright .NET | `Locale` context + app `lng` → `Expect(el).ToHaveTextAsync(rm.GetString(key, culture))` |
| **Date / number / currency** | Culture-correct formatting | Playwright .NET or NUnit | assert rendered `==` `v.ToString("C"/"D", culture)`, **timezone pinned** |
| **Pseudo-localization** | No hardcoded strings; no truncation | Playwright .NET | render in pseudo-locale → assert visible text wrapped in markers; screenshot for overflow |
| **RTL layout** | UI mirrors for RTL scripts | Playwright .NET | `ar`/`he` culture → `Expect(html).ToHaveAttributeAsync("dir", "rtl")` + mirrored-layout assertion |
| **Translation-key coverage** | Every resource set complete; no orphans | NUnit (static) | diff source keys vs each target: source ⊆ target, no empty values, no extra keys |
| **ICU plural / select** | Plurals & gender resolve per language | NUnit | format the message at count 0/1/2/5 → assert the right plural category (ICU4N) |
| **Locale matrix** | All supported cultures pass one journey | Playwright .NET | `[TestCaseSource]` over the supported-culture list → `qa-data-driven-testing-dotnet` |

## Stack

- .NET 8 + C# (nullable reference types enabled)
- **Playwright .NET** (`Microsoft.Playwright`) — the culture-pinned UI half (`Locale` + `TimezoneId`)
- **NUnit** — both the Playwright specs and the pure-function unit tests (`CultureInfo` math, pseudo-loc, the
  static diff)
- The app's **own catalog source** — `.resx` resources via `ResourceManager` (or `IStringLocalizer`):
  `Common.resx` (invariant/en), `Common.de.resx`, `Common.ar.resx`. Tests resolve from the **same** resources the
  app ships.
- **`System.Globalization.CultureInfo`** for number/date/currency formatting expectations; **ICU4N**
  (`ICU4N.Text.PluralRules` / `MessageFormat`, the .NET port of ICU4J) for plural categories the BCL doesn't model
- The **supported-culture list** comes from one constant (`SupportedCultures.All`), reused by every matrix test
- Culture + timezone set on the `IBrowserContext`, **never** hardcoded per test; one canonical pseudo-locale id
  (`en-XA`)

> **Why resolve from the app's resources instead of asserting literals?** The `.resx` set is the single source of
> truth the app renders from. Resolving expectations from it makes the test assert the *binding* (key → DOM)
> rather than the *content* (the English words) — a copy change is a non-event, and the same test body runs across
> every culture. The one thing you must not do is compare the resources to themselves; the assertion's left side
> is always the **live DOM / formatted output**, the right side is the `ResourceManager` / `CultureInfo`.

## The catalog + a test-side resolver

The app ships `.resx` resources; the test resolves the same key through a shared `ResourceManager` (and, for
interpolation, `string.Format` with positional `{0}` placeholders). This is **not** a second translation system —
it's a read-only view of the same compiled resources.

```csharp
// Tests/I18n/Catalog.cs
using System.Globalization;
using System.Resources;

namespace Tests.I18n;

public static class Catalog
{
    public static readonly IReadOnlyList<CultureInfo> Supported =
        new[] { "en", "de", "ar" }.Select(CultureInfo.GetCultureInfo).ToArray();

    public static readonly ISet<string> Rtl = new HashSet<string> { "ar", "he" };

    // points at the app's compiled .resx (root name + assembly that owns it)
    private static readonly ResourceManager Rm =
        new("MyApp.Resources.Common", typeof(MyApp.Marker).Assembly);

    /// <summary>Read-only mirror of the app's resource lookup.</summary>
    public static string T(string key, CultureInfo culture) =>
        Rm.GetString(key, culture) ?? throw new KeyNotFoundException($"Missing key '{key}' for '{culture.Name}'");

    /// <summary>Same lookup + positional interpolation: "Welcome back, {0}".</summary>
    public static string T(string key, CultureInfo culture, params object[] args) =>
        string.Format(culture, T(key, culture), args);
}
```

## 1. Culture-pinned UI text — assert the DOM against the catalog (idea #1)

Pin the culture on the `IBrowserContext` **and** tell the app which language to load (a `?lng=` query, a cookie,
or a `localStorage` seed — match your app). Then assert the rendered text equals the resource entry, by key.

```csharp
// Tests/I18n/I18nTestBase.cs — one context per culture, culture + timezone pinned
using System.Globalization;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Tests.I18n;

public abstract class I18nTestBase
{
    protected IPlaywright Playwright = null!;
    protected IBrowser Browser = null!;
    protected IBrowserContext Context = null!;
    protected IPage Page = null!;
    protected readonly CultureInfo Culture;
    private readonly string _timezoneId;

    protected I18nTestBase(string locale, string timezoneId)
    {
        Culture = CultureInfo.GetCultureInfo(locale);
        _timezoneId = timezoneId;
    }

    [OneTimeSetUp]
    public async Task LaunchAsync()
    {
        Playwright = await Microsoft.Playwright.Playwright.CreateAsync();
        Browser = await Playwright.Chromium.LaunchAsync();
        Context = await Browser.NewContextAsync(new BrowserNewContextOptions
        {
            Locale = Culture.Name,           // e.g. "de-DE"
            TimezoneId = _timezoneId,        // e.g. "Europe/Berlin"
        });
        await Context.AddInitScriptAsync($"localStorage.setItem('i18nextLng', '{Culture.Name}')");
        Page = await Context.NewPageAsync();
    }

    [OneTimeTearDown]
    public async Task CloseAsync() { await Context.CloseAsync(); await Browser.CloseAsync(); Playwright.Dispose(); }

    protected string T(string key) => Catalog.T(key, Culture);
}
```

```csharp
// Tests/I18n/HomeI18nDeTests.cs  (one fixture per culture; or drive via [TestFixture("de-DE", ...)])
using Microsoft.Playwright;
using NUnit.Framework;
using static Microsoft.Playwright.Assertions;

namespace Tests.I18n;

[TestFixture]
public class HomeI18nDeTests() : I18nTestBase("de-DE", "Europe/Berlin")
{
    [Test]
    public async Task Should_RenderHomeHeading_When_LocaleIsActive()
    {
        await Page.GotoAsync("/");
        // left side = live DOM; right side = the SAME resources the app shipped — resolved by KEY
        await Expect(Page.GetByRole(AriaRole.Heading)).ToHaveTextAsync(T("home.title"));
        await Expect(Page.GetByRole(AriaRole.Button, new() { Name = T("home.cta") })).ToBeVisibleAsync();
    }

    [Test]
    public async Task Should_InterpolateGreeting_When_UserNameProvided()
    {
        await Page.GotoAsync("/dashboard");
        // de: "Willkommen zurück, {0}" — assert the interpolated resource string
        await Expect(Page.GetByTestId("greeting"))
            .ToHaveTextAsync(Catalog.T("dashboard.greeting", Culture, "Trinity"));
    }
}
```

> This base, used for `en`/`de`/`ar`, covers three languages with no per-culture literals. A reworded string in
> `Common.de.resx` updates the expectation automatically — the test asserts the **wiring**, not the **words**.

## 2. Date / number / currency — assert via `CultureInfo`, timezone pinned (idea #2)

Never hardcode `"1.234,56 €"`. Build the expectation from `CultureInfo` for the culture under test — the same
primitive the app should use — so the test tracks globalization-data updates and proves the app passed the right
format.

```csharp
// Tests/I18n/FormattingI18nTests.cs
using System.Globalization;
using Microsoft.Playwright;
using NUnit.Framework;
using static Microsoft.Playwright.Assertions;

namespace Tests.I18n;

[TestFixture]
public class FormattingI18nTests() : I18nTestBase("de-DE", "Europe/Berlin")
{
    [Test]
    public async Task Should_FormatCartTotal_When_AsLocaleCurrency()
    {
        await Page.GotoAsync("/cart");                       // seeded total: 1234.5 EUR
        // EUR symbol position + separators come from the culture
        var expected = (1234.5m).ToString("C", Culture);     // de-DE → "1.234,50 €"
        await Expect(Page.GetByTestId("cart-total")).ToHaveTextAsync(expected);
    }

    [Test]
    public async Task Should_FormatOrderDate_When_ForLocaleAndPinnedTimezone()
    {
        await Page.GotoAsync("/orders/1");                   // order at a fixed instant
        var utc = new DateTimeOffset(2026, 3, 14, 9, 0, 0, TimeSpan.Zero);
        var berlin = TimeZoneInfo.FindSystemTimeZoneById("Europe/Berlin");
        var local = TimeZoneInfo.ConvertTime(utc, berlin);   // pin TZ — date formatting is TZ-sensitive
        var expected = local.DateTime.ToString("D", Culture);
        await Expect(Page.GetByTestId("order-date")).ToHaveTextAsync(expected);
    }

    [TestCase("en-US", "€1,234.50")]
    [TestCase("de-DE", "1.234,50 €")]   // note the non-breaking space de uses before the symbol
    [TestCase("fr-FR", "1 234,50 €")]
    public void Should_FormatEur_When_ForCulture(string name, string expected)   // pure-function: no browser
    {
        var culture = CultureInfo.GetCultureInfo(name);
        Assert.That((1234.5m).ToString("C", new NumberFormatInfo
        {
            CurrencySymbol = "€",
            CurrencyDecimalSeparator = culture.NumberFormat.CurrencyDecimalSeparator,
            CurrencyGroupSeparator = culture.NumberFormat.CurrencyGroupSeparator,
            CurrencyPositivePattern = culture.NumberFormat.CurrencyPositivePattern,
        }), Is.EqualTo(expected));
    }
}
```

> Two gotchas the `CultureInfo` approach catches and a hardcoded literal hides: many cultures use **non-breaking**
> / **narrow-no-break** spaces inside formatted numbers — a copy-pasted "looks right" literal uses a normal space
> and fails. And asserting against `CultureInfo` means a globalization-data update that changes a format updates
> *both* sides together, instead of a literal silently drifting. (On Linux/macOS .NET uses ICU; ensure CI uses
> ICU-mode globalization, not invariant.)

## 3. Pseudo-localization — surface hardcoded strings and truncation (idea #3)

Transform every source value: accent the letters, expand ~40%, wrap in sentinel brackets. Load it as a real
culture (`en-XA`). Then **every visible string must be wrapped** — an unwrapped string is hardcoded and bypassed
i18n.

```csharp
// Tests/I18n/Pseudo.cs — deterministic source→pseudo transform
using System.Text;

namespace Tests.I18n;

public static class Pseudo
{
    public const string Open = "[!! ", Close = " !!]";
    private static readonly Dictionary<char, string> Map = new()
    {
        ['a'] = "á", ['e'] = "ḗ", ['i'] = "í", ['o'] = "ö", ['u'] = "ṵ",
        ['c'] = "ḉ", ['l'] = "ḷ", ['m'] = "ṁ", ['w'] = "ŵ",
    };

    /// <summary>Accent + ~40% pad + bracket-wrap, leaving {0} placeholders untouched.</summary>
    public static string Localize(string text)
    {
        var sb = new StringBuilder();
        var inBrace = false;
        foreach (var c in text)
        {
            if (c == '{') inBrace = true; else if (c == '}') inBrace = false;
            sb.Append(inBrace ? c.ToString() : Map.GetValueOrDefault(char.ToLowerInvariant(c), c.ToString()));
        }
        var letters = sb.ToString().Count(char.IsLetter);
        var pad = new string('~', (int)Math.Ceiling(letters * 0.4));
        return $"{Open}{sb}{pad}{Close}";
    }
}
```

```csharp
// Tests/I18n/PseudoI18nTests.cs — runs against the en-XA build
using NUnit.Framework;

namespace Tests.I18n;

[TestFixture]
public class PseudoI18nTests() : I18nTestBase("en-XA", "UTC")
{
    [Test]
    public async Task Should_RouteEveryVisibleString_Through_I18n()
    {
        await Page.GotoAsync("/checkout");
        var texts = await Page.GetByText(new System.Text.RegularExpressions.Regex(@"\S")).AllInnerTextsAsync();
        var leaks = texts.Select(s => s.Trim())
            .Where(s => s.Length > 1 && !(s.Contains(Pseudo.Open) || s.Contains(Pseudo.Close)))
            .ToList();
        Assert.That(leaks, Is.Empty, $"hardcoded strings bypassing i18n: {string.Join(", ", leaks)}");
    }

    [Test]
    public async Task Should_NotClipAnyLabel_When_TextExpands()
    {
        await Page.GotoAsync("/checkout");
        var clipped = await Page.GetByTestId("submit")
            .EvaluateAsync<bool>("el => el.scrollWidth > el.clientWidth + 1");   // overflow == truncation bug
        Assert.That(clipped, Is.False, "submit button truncates its label");
    }
}
```

> Pseudo-loc needs **zero translators**, so it's the first i18n gate you can run — wire it into CI before any real
> culture exists. Pair the overflow check with `qa-visual-regression-playwright-snapshots-dotnet` for a pixel
> record.

## 4a. RTL — assert the layout mirrors (idea #4)

Use a **real RTL culture** (`ar`), not a `direction: rtl` CSS hack.

```csharp
// Tests/I18n/RtlI18nTests.cs — runs under the ar culture
using Microsoft.Playwright;
using NUnit.Framework;
using static Microsoft.Playwright.Assertions;

namespace Tests.I18n;

[TestFixture]
public class RtlI18nTests() : I18nTestBase("ar-EG", "Africa/Cairo")
{
    [Test]
    public async Task Should_MirrorLayout_When_RtlCulture()
    {
        await Page.GotoAsync("/");
        await Expect(Page.Locator("html")).ToHaveAttributeAsync("dir", "rtl");   // the document declares RTL
        var nav = await Page.GetByRole(AriaRole.Navigation).BoundingBoxAsync();
        var viewportWidth = await Page.EvaluateAsync<int>("() => window.innerWidth");
        Assert.That(nav!.X, Is.GreaterThan(viewportWidth / 2.0), "nav should sit on the right in RTL");
        await Expect(Page.GetByRole(AriaRole.Navigation))
            .ToHaveCSSAsync("margin-inline-start", new System.Text.RegularExpressions.Regex(".+"));
    }
}
```

## 4b. Translation-key coverage — a static resource diff (idea #4)

No browser, no app — just compare the resource sets. Highest-value, cheapest, most deterministic i18n test.
`GetResourceSet(culture, createIfNotExists: true, tryParents: false)` returns **only** that culture's keys (no
parent fallback) — so a missing key shows up instead of silently resolving from the invariant set. Gate the build
on it.

```csharp
// Tests/I18n/CoverageI18nTests.cs
using System.Collections;
using System.Globalization;
using System.Resources;
using System.Text.RegularExpressions;
using NUnit.Framework;

namespace Tests.I18n;

[TestFixture]
public class CoverageI18nTests
{
    private static readonly ResourceManager Rm = new("MyApp.Resources.Common", typeof(MyApp.Marker).Assembly);

    private static Dictionary<string, string> Keys(string name)
    {
        var culture = name == "en" ? CultureInfo.InvariantCulture : CultureInfo.GetCultureInfo(name);
        var set = Rm.GetResourceSet(culture, createIfNotExists: true, tryParents: false)!;
        return set.Cast<DictionaryEntry>().ToDictionary(e => (string)e.Key, e => (string)e.Value!);
    }

    private static IEnumerable<string> Targets() { yield return "de"; yield return "ar"; }

    [TestCaseSource(nameof(Targets))]
    public void Should_HaveNoMissingKeys_When_ComparedToSource(string tag)
    {
        var source = Keys("en"); var target = Keys(tag);
        var missing = source.Keys.Where(k => !target.ContainsKey(k)).OrderBy(k => k).ToList();
        Assert.That(missing, Is.Empty, $"{tag} is missing: {string.Join(", ", missing)}");   // → fallback in prod
    }

    [TestCaseSource(nameof(Targets))]
    public void Should_HaveNoEmptyValues_When_Translated(string tag)
    {
        var empty = Keys(tag).Where(kv => string.IsNullOrWhiteSpace(kv.Value)).Select(kv => kv.Key)
            .OrderBy(k => k).ToList();
        Assert.That(empty, Is.Empty, $"{tag} has empty entries: {string.Join(", ", empty)}");
    }

    [TestCaseSource(nameof(Targets))]
    public void Should_HaveNoOrphanKeys_When_NotInSource(string tag)
    {
        var source = Keys("en");
        var orphans = Keys(tag).Keys.Where(k => !source.ContainsKey(k)).OrderBy(k => k).ToList();
        Assert.That(orphans, Is.Empty, $"{tag} has orphan keys: {string.Join(", ", orphans)}");
    }

    [TestCaseSource(nameof(Targets))]
    public void Should_KeepPlaceholdersIdentical_When_Translated(string tag)
    {
        var source = Keys("en"); var target = Keys(tag);
        var ph = new Regex(@"\{\d+}");
        List<string> Of(string s) => ph.Matches(s).Select(m => m.Value).OrderBy(x => x).ToList();
        var drifted = source.Keys.Where(k => target.ContainsKey(k))
            .Where(k => !Of(source[k]).SequenceEqual(Of(target[k]))).OrderBy(k => k).ToList();
        Assert.That(drifted, Is.Empty, $"{tag} placeholder mismatch: {string.Join(", ", drifted)}");
    }
}
```

> The placeholder check catches the bug a presence check misses: a translator who renders `Welcome back, {0}` as
> `Bienvenue` (dropping `{0}`) leaves the key present but breaks interpolation. Assert the placeholder set is
> identical.

## ICU plurals & gender — assert the category, per language

The BCL has no CLDR plural rules; use **ICU4N** (the .NET port of ICU4J). English has two plural categories
(one/other); Polish four; Arabic six. Exercise the **boundary counts** the language has, not just 1 and 2.

```csharp
// Tests/I18n/PluralI18nTests.cs
using ICU4N.Globalization;
using ICU4N.Text;
using NUnit.Framework;

namespace Tests.I18n;

[TestFixture]
public class PluralI18nTests
{
    private readonly MessageFormat _en = new(
        "{count, plural, =0 {no items} one {# item} other {# items}}", new UCultureInfo("en"));

    [TestCase(0, "no items")]
    [TestCase(1, "1 item")]
    [TestCase(2, "2 items")]
    [TestCase(5, "5 items")]
    public void Should_RenderPluralCategory_When_EnglishCount(int count, string expected)
    {
        Assert.That(_en.Format(new Dictionary<string, object> { ["count"] = count }), Is.EqualTo(expected));
    }

    [Test]
    public void Should_NeedMoreThanOneAndOther_When_Arabic()
    {
        var ar = PluralRules.ForLocale(new UCultureInfo("ar"));
        var cats = new[] { 0, 1, 2, 3, 11, 100 }.Select(n => ar.Select(n)).ToHashSet();
        Assert.That(cats.Count, Is.GreaterThan(2), "Arabic needs more than one/other plural categories");
    }
}
```

## Locale matrix — one journey across every supported culture

Bind the supported-culture list as data via `[TestCaseSource]` rather than copy-pasting the spec — this is
`qa-data-driven-testing-dotnet` applied to cultures.

```csharp
private static IEnumerable<string> SupportedCultureNames() => Catalog.Supported.Select(c => c.Name);

[TestCaseSource(nameof(SupportedCultureNames))]
public async Task Should_CompleteCheckout_When_AnyCulture(string name)
{
    var culture = CultureInfo.GetCultureInfo(name);
    await using var ctx = await Browser.NewContextAsync(new BrowserNewContextOptions { Locale = name });
    var page = await ctx.NewPageAsync();
    await page.GotoAsync("/checkout");
    await page.GetByRole(AriaRole.Button, new() { Name = Catalog.T("checkout.pay", culture) }).ClickAsync();
    await Expect(page.GetByTestId("confirmation")).ToHaveTextAsync(Catalog.T("checkout.success", culture));
}
```

## Anti-patterns

- **Asserting a hardcoded literal** (`ToHaveTextAsync("Willkommen")`). Breaks on any reword; only tests one
  language. *Fix:* `ToHaveTextAsync(T("home.title"))` — resolve from the shipped resources, by key.
- **Comparing the resources to themselves** (`Assert.That(T("k"), Is.EqualTo(T("k")))`). A tautology. *Fix:* the
  left side is always the **live DOM / formatted output**; the resources are only ever the expected side.
- **Hardcoding a formatted number/date/currency** (`"1.234,56 €"`). Bakes in one culture, uses the wrong spaces,
  rots on a globalization-data update. *Fix:* assert against `value.ToString("C"/"D", culture)`.
- **Letting the CI timezone float for date assertions.** Date formatting is TZ-sensitive → flaky. *Fix:* convert
  the instant via `TimeZoneInfo` **and** set `TimezoneId` on the context. (Also: ensure CI runs ICU-mode
  globalization, not `InvariantGlobalization`.)
- **Faking RTL with a CSS toggle.** Doesn't exercise the app's direction logic, bidi, or mirrored assets. *Fix:*
  drive a real RTL culture (`ar`/`he`); assert `<html dir="rtl">` + a mirrored-layout property.
- **Only checking that keys *exist*.** Misses empty values, orphans, and dropped placeholders. *Fix:* the static
  diff asserts presence **and** non-empty **and** no-orphans **and** identical `{0}` placeholders — and uses
  `tryParents: false` so fallback doesn't hide a missing key.
- **Testing plurals at only count 1 and 2.** Misses zero/few/many categories Polish/Russian/Arabic need. *Fix:*
  exercise the boundary counts the language has (drive from ICU4N `PluralRules`).
- **Concatenating translated fragments** (`T("welcome") + name`). Can't reorder for languages that put the name
  first. *Fix:* one interpolated key (`"Welcome, {0}"`); pseudo-loc surfaces the concatenation.
- **Hardcoding the supported-culture list in each test.** Drifts from the app's real list. *Fix:* use
  `Catalog.Supported`; drive the matrix from it.

## Examples

**A reword that would break a literal-based suite is a non-event here.** Marketing changes the German CTA from
`„Jetzt kaufen"` to `„Sofort bestellen"`. A literal suite turns red across every German test; this suite re-reads
`Common.de.resx` through `T("home.cta")` and stays green — it asserts the button is wired to `home.cta`, which is
still true.

**Pseudo-loc catches the bug three other tests can't.** A developer hardcodes a `"Loading…"` spinner label
directly in a Razor component. The culture-pinned tests pass (the resources are complete), the coverage diff
passes (no key is missing — there's no key at all), but the pseudo-loc test fails: `"Loading…"` appears *without*
brackets, so it's flagged as bypassing i18n. That's the class of bug pseudo-localization exists to find.

## Rules (hard constraints)

- **Never assert a hardcoded literal string.** The expected value is always resolved from the **app's own
  resources** by key (`Catalog.T(key, culture)`) or computed via `CultureInfo` — never copied in. Never compare
  the resources to themselves.
- **Formatting is asserted via `CultureInfo`** (`ToString("C"/"N"/"D", culture)` / ICU4N `PluralRules`) for the
  culture under test, with the **timezone pinned** (via `TimeZoneInfo`) and `TimezoneId` set on the context.
- **Pseudo-localization is a required CI gate:** every visible string must be wrapped in the pseudo markers, and
  no label may overflow its box under +40% expansion.
- **RTL uses a real RTL culture** and asserts `<html dir="rtl">` plus a mirrored-layout property — not a CSS
  toggle.
- **Translation-key coverage is a static, build-gating test:** source keys ⊆ each target, no empty values, no
  orphan keys, identical `{0}` placeholders; `tryParents: false` so fallback can't hide a gap.
- **The supported-culture list comes from one constant** (`Catalog.Supported`), reused by every matrix test.
  Culture + timezone are set on the context, never hardcoded per test.
- **One logical assertion per test; async all the way (no `.Result`/`.Wait()`); no `WaitForTimeoutAsync`;
  nullable enabled.** Locale-matrix expansion uses `[TestCaseSource]` (`qa-data-driven-testing-dotnet`), never
  copy-paste.

## Cross-references

- `qa-i18n-testing-typescript` (canonical) · `qa-i18n-testing-java` — the sibling stacks (Playwright + Vitest +
  i18next + `Intl` · Playwright-Java + TestNG + ICU4J / `ResourceBundle`); same four ideas, different catalog +
  formatting APIs.
- `qa-ui-test-author-playwright-dotnet` — the base Playwright .NET / page-object conventions this builds on; i18n
  adds the culture dimension on top.
- `qa-visual-regression-playwright-snapshots-dotnet` (#17) — pairs with the pseudo-loc **overflow** check: a pixel
  diff records *how* the layout broke; this skill asserts *that* it didn't.
- `qa-data-driven-testing-dotnet` (#39) — the locale matrix is its `[TestCaseSource]` row-binding applied to the
  supported-culture list.
- `qa-accessibility-testing-axe-playwright-dotnet` (#20) — RTL + language correctness overlaps with the
  `html[lang]` / `dir` a11y rules; run them together on the culture-pinned page.
- `qa-allure-reporting-dotnet` — render each culture (and the pseudo-locale) as a named result / Allure parameter
  so a failure says *which* language broke.
