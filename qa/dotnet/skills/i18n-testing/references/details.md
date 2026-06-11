# Deep-dive details — `qa-i18n-testing-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

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
> culture exists. Pair the overflow check with `qa-visual-regression-dotnet` for a pixel
> record.

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
