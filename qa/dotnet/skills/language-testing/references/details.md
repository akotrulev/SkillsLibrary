# Deep-dive details — `qa-language-testing-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs. Every browser fixture here
derives from `BaseTest` (`qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs`) and takes its culture
as a fixture parameter, exactly as SKILL.md §1 shows; the `ContextOptions()` override is the same four lines in
each.

## 0. Page objects

One type per file in a project; they share a block here only to keep the reference short. Each owns its URL,
builds its locators once and asserts nothing.

```csharp
using System.Text.RegularExpressions;
using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public enum ScreenSide
{
    Left,
    Right,
}

public sealed class LandingPage(IPage page)
{
    public ILocator Heading { get; } = page.GetByRole(AriaRole.Heading, new() { Level = 1 }).Describe("Landing heading");

    public ILocator Greeting { get; } = page.GetByTestId("Home.Greeting").Describe("Home greeting");

    public async Task OpenAsync() => await page.GotoAsync("/");
}

public sealed class CartPage(IPage page)
{
    public ILocator Total { get; } = page.GetByTestId("Cart.Total").Describe("Cart total");

    public async Task OpenAsync() => await page.GotoAsync("/cart");
}

public sealed class OrderPage(IPage page)
{
    public ILocator PlacedOn { get; } = page.GetByTestId("Order.PlacedOn").Describe("Order placed-on date");

    public async Task OpenAsync(string orderId) => await page.GotoAsync($"/orders/{orderId}");
}

public sealed class AppShellPage(IPage page)
{
    public ILocator Document { get; } = page.Locator("html").Describe("Document root");

    public ILocator Navigation { get; } = page.GetByRole(AriaRole.Navigation).Describe("Main navigation");

    public async Task OpenAsync() => await page.GotoAsync("/");

    public async Task<ScreenSide> NavigationSideAsync()
    {
        await Navigation.WaitForAsync();
        var box = await Navigation.BoundingBoxAsync()
            ?? throw new InvalidOperationException("The main navigation has no bounding box");
        var viewportWidth = page.ViewportSize?.Width
            ?? throw new InvalidOperationException("The context has no fixed viewport");
        return box.X + box.Width / 2 > viewportWidth / 2f ? ScreenSide.Right : ScreenSide.Left;
    }
}

public sealed class CheckoutPage(IPage page)
{
    private readonly ILocator _anyText = page.GetByText(new Regex(@"\S"));
    private readonly ILocator _pay = page.GetByTestId("Checkout.Pay").Describe("Pay button");

    public ILocator Confirmation { get; } = page.GetByTestId("Checkout.Confirmation").Describe("Order confirmation");

    public async Task OpenAsync()
    {
        await page.GotoAsync("/checkout");
        await _pay.WaitForAsync();
    }

    public async Task PayAsync() => await _pay.ClickAsync();

    public Task<IReadOnlyList<string>> VisibleTextsAsync() => _anyText.AllInnerTextsAsync();

    public Task<bool> PayLabelOverflowsAsync() => _pay.EvaluateAsync<bool>("el => el.scrollWidth > el.clientWidth + 1");
}
```

- `Document` is the one CSS locator: the `<html>` element has no role, label or test id.
- `NavigationSideAsync()` measures **after** a wait for the navigation, and reads the context's viewport
  (`BaseTest` contexts have the runsettings default; a fixture that sets `ViewportSize` changes it).
- `VisibleTextsAsync()` and `PayLabelOverflowsAsync()` are reads, called after `OpenAsync()` has waited for the
  page; the pseudo-loc tests below decide what the result means.

## 3. Pseudo-localization — surface hardcoded strings and truncation (idea #3)

Transform every source value: accent the letters, expand ~40%, wrap in sentinel brackets. Load it as a real
culture (`en-XA`). Then **every visible string must be wrapped** — an unwrapped string is hardcoded and bypassed
i18n.

```csharp
using System.Text;

namespace Example.UiTests.Support;

public static class Pseudo
{
    public const string Open = "[!! ";
    public const string Close = " !!]";

    private static readonly Dictionary<char, string> Accents = new()
    {
        ['a'] = "á", ['e'] = "ḗ", ['i'] = "í", ['o'] = "ö", ['u'] = "ṵ",
        ['c'] = "ḉ", ['l'] = "ḷ", ['m'] = "ṁ", ['w'] = "ŵ",
    };

    public static string Localize(string text)
    {
        var accented = new StringBuilder();
        var insidePlaceholder = false;
        foreach (var character in text)
        {
            insidePlaceholder = character == '{' || (insidePlaceholder && character != '}');
            accented.Append(insidePlaceholder ? character.ToString() : Accents.GetValueOrDefault(char.ToLowerInvariant(character), character.ToString()));
        }
        var padding = new string('~', (int)Math.Ceiling(accented.ToString().Count(char.IsLetter) * 0.4));
        return $"{Open}{accented}{padding}{Close}";
    }
}
```

`Localize` is the build-side transform that produces the `en-XA` resources; it leaves `{0}` placeholders
untouched. Its own unit tests are plain NUnit, no browser.

```csharp
using Example.UiTests.Pages;
using Example.UiTests.Support;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[TestFixture("en-XA", "UTC")]
public class PseudoI18nTests(string locale, string timezoneId) : BaseTest
{
    private CheckoutPage _checkout = null!;

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.Locale = locale;
        options.TimezoneId = timezoneId;
        return options;
    }

    [SetUp]
    public void CreatePages() => _checkout = new CheckoutPage(Page);

    [Test]
    public async Task Should_WrapEveryVisibleString_When_RenderedInThePseudoLocale()
    {
        await _checkout.OpenAsync();

        var leaks = (await _checkout.VisibleTextsAsync())
            .Select(text => text.Trim())
            .Where(text => text.Length > 1 && !text.Contains(Pseudo.Open) && !text.Contains(Pseudo.Close))
            .ToList();
        Assert.That(leaks, Is.Empty, $"hardcoded strings bypassing i18n: {string.Join(" | ", leaks)}");
    }

    [Test]
    public async Task Should_FitThePayLabel_When_TheTextExpands()
    {
        await _checkout.OpenAsync();

        Assert.That(await _checkout.PayLabelOverflowsAsync(), Is.False, "the pay button truncates its pseudo-localized label");
    }
}
```

Pseudo-loc needs **zero translators**, so it is the first i18n gate to wire into CI. Pair the overflow check
with `qa-visual-regression-dotnet` for a pixel record.

## 4b. Translation-key coverage — a static resource diff (idea #4)

No browser, no app — compare the resource sets. `GetResourceSet(culture, createIfNotExists: true,
tryParents: false)` returns **only** that culture's keys, so a missing key shows up instead of resolving from the
invariant set. Gate the build on it.

```csharp
using System.Collections;
using System.Globalization;
using System.Resources;
using System.Text.RegularExpressions;
using NUnit.Framework;

namespace Example.UiTests.Tests;

public class CoverageI18nTests
{
    private static readonly ResourceManager Resources = new("MyApp.Resources.Common", typeof(MyApp.Marker).Assembly);
    private static readonly Regex Placeholder = new(@"\{\d+}");

    private static IEnumerable<string> Targets() => ["de", "ar"];

    [TestCaseSource(nameof(Targets))]
    public void Should_HaveNoMissingKeys_When_ComparedToTheSource(string culture)
    {
        var target = Keys(culture);

        var missing = Keys("en").Keys.Where(key => !target.ContainsKey(key)).Order().ToList();

        Assert.That(missing, Is.Empty, $"{culture} is missing: {string.Join(", ", missing)}");
    }

    [TestCaseSource(nameof(Targets))]
    public void Should_HaveNoEmptyValues_When_Translated(string culture)
    {
        var empty = Keys(culture).Where(entry => string.IsNullOrWhiteSpace(entry.Value)).Select(entry => entry.Key).Order().ToList();

        Assert.That(empty, Is.Empty, $"{culture} has empty entries: {string.Join(", ", empty)}");
    }

    [TestCaseSource(nameof(Targets))]
    public void Should_HaveNoOrphanKeys_When_ComparedToTheSource(string culture)
    {
        var source = Keys("en");

        var orphans = Keys(culture).Keys.Where(key => !source.ContainsKey(key)).Order().ToList();

        Assert.That(orphans, Is.Empty, $"{culture} has orphan keys: {string.Join(", ", orphans)}");
    }

    [TestCaseSource(nameof(Targets))]
    public void Should_KeepPlaceholdersIdentical_When_Translated(string culture)
    {
        var source = Keys("en");
        var target = Keys(culture);

        var drifted = source.Keys
            .Where(key => target.ContainsKey(key) && !Placeholders(source[key]).SequenceEqual(Placeholders(target[key])))
            .Order()
            .ToList();

        Assert.That(drifted, Is.Empty, $"{culture} placeholder mismatch: {string.Join(", ", drifted)}");
    }

    private static Dictionary<string, string> Keys(string culture)
    {
        var info = culture == "en" ? CultureInfo.InvariantCulture : CultureInfo.GetCultureInfo(culture);
        var set = Resources.GetResourceSet(info, createIfNotExists: true, tryParents: false)
            ?? throw new InvalidOperationException($"No resource set for '{culture}'");
        return set.Cast<DictionaryEntry>().ToDictionary(entry => (string)entry.Key, entry => (string?)entry.Value ?? string.Empty);
    }

    private static List<string> Placeholders(string text) => Placeholder.Matches(text).Select(match => match.Value).Order().ToList();
}
```

The placeholder check catches what a presence check misses: a translator who renders `Welcome back, {0}` as
`Bienvenue` (dropping `{0}`) leaves the key present but breaks interpolation.

## ICU plurals & gender — assert the category, per language

The BCL has no CLDR plural rules; use **ICU4N** (the .NET port of ICU4J). English has two categories
(one/other), Polish four, Arabic six. Exercise the **boundary counts** the language has, not just 1 and 2.

```csharp
using ICU4N.Globalization;
using ICU4N.Text;
using NUnit.Framework;

namespace Example.UiTests.Tests;

public class PluralI18nTests
{
    private readonly MessageFormat _english = new("{count, plural, =0 {no items} one {# item} other {# items}}", new UCultureInfo("en"));

    [TestCase(0, "no items")]
    [TestCase(1, "1 item")]
    [TestCase(2, "2 items")]
    [TestCase(5, "5 items")]
    public void Should_RenderThePluralCategory_When_TheCountIsGivenInEnglish(int count, string expected)
    {
        Assert.That(_english.Format(new Dictionary<string, object> { ["count"] = count }), Is.EqualTo(expected));
    }

    [Test]
    public void Should_ReachAllSixCategories_When_ArabicBoundaryCountsAreSelected()
    {
        var arabic = PluralRules.ForLocale(new UCultureInfo("ar"));

        var categories = new[] { 0, 1, 2, 3, 11, 100 }.Select(count => arabic.Select(count)).Distinct().ToList();

        Assert.That(categories, Has.Count.EqualTo(6), string.Join(", ", categories));
    }
}
```

## Locale matrix — one journey across every supported culture

`qa-data-driven-testing-dotnet`'s row binding applied to cultures: the fixture is the row, so each culture gets
its own context with its own `Locale` and `TimezoneId`, and the rows run as parallel fixtures.

```csharp
[TestFixtureSource(typeof(SupportedLocales), nameof(SupportedLocales.All))]
public class CheckoutI18nTests(string locale, string timezoneId) : BaseTest
{
    private readonly CultureInfo _culture = CultureInfo.GetCultureInfo(locale);
    private CheckoutPage _checkout = null!;

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.Locale = locale;
        options.TimezoneId = timezoneId;
        return options;
    }

    [SetUp]
    public void CreatePages() => _checkout = new CheckoutPage(Page);

    [Test]
    public async Task Should_ConfirmTheOrder_When_CheckingOutInTheCulture()
    {
        await _checkout.OpenAsync();

        await _checkout.PayAsync();

        await Expect(_checkout.Confirmation).ToHaveTextAsync(Catalog.T("checkout.success", _culture));
    }
}
```

The old shape — a `[TestCaseSource]` of culture names with `Browser.NewContextAsync(new() { Locale = name })`
inside the test — opened a second context the test had to close, skipped `BaseTest`'s evidence and drove a raw
page. The fixture row replaces all of it.

## Examples

**A reword is a non-event.** Marketing changes the German CTA from „Jetzt kaufen" to „Sofort bestellen". A
literal suite turns red across every German test; this suite re-reads `Common.de.resx` through
`Catalog.T("home.cta", culture)` and stays green — it asserts the button is wired to `home.cta`, which is still
true.

**Pseudo-loc catches what nothing else does.** A developer hardcodes a "Loading…" spinner label in a Razor
component. The culture-pinned tests pass (the resources are complete), the coverage diff passes (there is no key
at all), but `Should_WrapEveryVisibleString_When_RenderedInThePseudoLocale` lists "Loading…" without brackets.
