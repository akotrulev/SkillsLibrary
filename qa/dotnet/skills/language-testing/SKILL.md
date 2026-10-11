---
name: qa-language-testing-dotnet
description: Use when writing i18n/localization tests in .NET 10 (8-9) — Playwright .NET + NUnit pinned to a locale, asserting via the app's own `.resx`/`IStringLocalizer` catalog by key (never hardcoded literals), `CultureInfo` for number/date/currency formats, pseudo-localization and RTL checks. Triggers "write an i18n test in C#", "test German/Arabic rendering", "assert currency formatting per culture". Not for the app's own localization wiring (the `fe-*` stack's `localization`).
---

# QA — i18n / Localization Testing (.NET 10 / Playwright 1.63 + NUnit + CultureInfo)

Tests that a web app is correctly **internationalized** (culture switching, formatting, layout, catalog
completeness) and **localized** (the right strings render per culture). **Playwright .NET** drives the app in a
pinned culture for the UI-rendered checks; **plain NUnit** owns the pure-function checks (`CultureInfo` math,
the pseudo-loc transform, the static catalog diff). Both share the fact that makes i18n testing its own
discipline: **the literal string on screen is the variable, not the constant — so the assertion is never a
hardcoded literal.**

> **The discipline this skill encodes** — four ideas:
>
> 1. **Pin the culture; assert against the catalog by KEY, never a hardcoded literal.** Drive the app with an
>    explicit culture and resolve the expected text from the **same resources the app ships**
>    (`Catalog.T("home.title", culture)`). `ToHaveTextAsync("Willkommen")` breaks the instant a copywriter
>    rewords the German and only tests one language. The left side is the **rendered DOM**; the resources are
>    only ever the expected side — comparing them to themselves is a tautology.
> 2. **Format is culture-derived — assert via `CultureInfo`, never a hardcoded format.** `1,234.56` (en) vs
>    `1.234,56` (de) vs `1 234,56` (fr). Assert the rendered value equals `value.ToString("C", culture)`, and pin
>    the **timezone** (`TimezoneId` on the context, `TimeZoneInfo` on the expected side) — and the **clock**
>    when the text is relative ("vor 3 Tagen").
> 3. **Pseudo-localize to surface hardcoded and truncated strings — before any translation exists.** An
>    accented, bracketed, ~40%-longer pseudo-locale (`Welcome` → `[!! Ŵḗḷḉöṁḗ~~~ !!]`) shows every string that
>    bypassed i18n (no brackets), every label too tight for real translations (clipped), and every broken
>    concatenation.
> 4. **RTL is a layout assertion; coverage is a static one.** RTL (`ar`/`he`) mirrors the whole UI — assert
>    `<html dir="rtl">` and that the layout actually flipped, with a **real RTL culture**. Translation-key
>    coverage is a **static** resource diff (no browser): every key present and non-empty in every target, no
>    orphans, identical placeholders. It gates the build.

## Decision matrix — i18n surface → test shape

| Surface | What you're proving | Runner | Test shape |
|---------|---------------------|--------|------------|
| **Culture-pinned UI text** | The right translation renders for a culture | Playwright .NET | a fixture per culture (`[TestFixture("de-DE", "Europe/Berlin")]`) → `Expect(page.Heading).ToHaveTextAsync(T("home.title"))` |
| **Date / number / currency** | Culture-correct formatting | Playwright .NET | rendered `==` `value.ToString("C"/"D", culture)`; timezone pinned; clock frozen for relative times |
| **Pseudo-localization** | No hardcoded strings; no truncation | Playwright .NET | `en-XA` fixture → every visible text carries the markers; no label overflows |
| **RTL layout** | UI mirrors for RTL scripts | Playwright .NET | `ar-EG` fixture → `dir="rtl"` + the navigation on the right |
| **Translation-key coverage** | Every resource set complete; no orphans | NUnit (static) | source keys vs each target: present, non-empty, no extras, same `{0}` set |
| **ICU plural / select** | Plurals resolve per language | NUnit | ICU4N at the language's boundary counts |
| **Locale matrix** | All supported cultures pass one journey | Playwright .NET | `[TestFixtureSource]` over `SupportedLocales.All` |

## Stack

- .NET 10 (8/9 supported — match the TFM), NUnit 4, nullable on.
- **Microsoft.Playwright.NUnit** at the pins in the **Versions** table of
  `qa/dotnet/skills/ui-test-author/playwright/SKILL.md` (this skill pins nothing). Every browser fixture
  **derives from that skill's `BaseTest`** — no `[OneTimeSetUp]` browser, no `Playwright.CreateAsync()`, no page
  shared by a fixture's tests. Tests reach the page through page objects.
- **The culture is a fixture parameter.** `[TestFixture("de-DE", "Europe/Berlin")]` passes it to the
  constructor; `ContextOptions()` amends `base.ContextOptions()` with `Locale` and `TimezoneId`.
  `ContextTest` already defaults `Locale` to `en-US`, so the override sets it rather than building new
  options. Several `[TestFixture]` rows on one class run as separate, parallel fixtures (`ParallelScope.Self`).
- The app's **own catalog** — `.resx` resources via `ResourceManager` (`Common.resx`, `Common.de.resx`,
  `Common.ar.resx`); **`CultureInfo`** for formatting; **ICU4N** for plural categories the BCL doesn't model.
- The **supported-culture list** is one constant, `SupportedLocales.All`, reused by every matrix.

## The catalog + a test-side resolver

The test resolves the same key through a `ResourceManager` over the app's compiled resources — a read-only view,
not a second translation system.

```csharp
using System.Globalization;
using System.Resources;
using NUnit.Framework;

namespace Example.UiTests.Support;

public static class Catalog
{
    private static readonly ResourceManager Resources = new("MyApp.Resources.Common", typeof(MyApp.Marker).Assembly);

    public static string T(string key, CultureInfo culture) =>
        Resources.GetString(key, culture) ?? throw new KeyNotFoundException($"Missing key '{key}' for '{culture.Name}'");

    public static string T(string key, CultureInfo culture, params object[] args) =>
        string.Format(culture, T(key, culture), args);
}

public static class SupportedLocales
{
    public static IEnumerable<TestFixtureData> All()
    {
        yield return new TestFixtureData("en-US", "America/New_York");
        yield return new TestFixtureData("de-DE", "Europe/Berlin");
        yield return new TestFixtureData("ar-EG", "Africa/Cairo");
    }
}
```

## 1. Culture-pinned UI text — the locale fixture (idea #1)

```csharp
using System.Globalization;
using Example.UiTests.Pages;
using Example.UiTests.Support;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[TestFixture("de-DE", "Europe/Berlin")]
[TestFixture("ar-EG", "Africa/Cairo")]
public class LandingI18nTests(string locale, string timezoneId) : BaseTest
{
    private readonly CultureInfo _culture = CultureInfo.GetCultureInfo(locale);
    private LandingPage _landing = null!;

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.Locale = locale;
        options.TimezoneId = timezoneId;
        return options;
    }

    [SetUp]
    public void CreatePages() => _landing = new LandingPage(Page);

    [Test]
    public async Task Should_RenderTheTranslatedHeading_When_TheCultureIsActive()
    {
        await _landing.OpenAsync();

        await Expect(_landing.Heading).ToHaveTextAsync(Catalog.T("home.title", _culture));
    }

    [Test]
    public async Task Should_InterpolateTheGreeting_When_TheUserIsKnown()
    {
        await _landing.OpenAsync();

        await Expect(_landing.Greeting).ToHaveTextAsync(Catalog.T("home.greeting", _culture, "Trinity"));
    }
}
```

- **How the app learns the culture:** `Locale` sets `navigator.language` and the `Accept-Language` header,
  which ASP.NET Core's request localization reads by default. An app that reads a cookie instead gets it in the
  fixture's `[SetUp]` with `Context.AddCookiesAsync(...)`, before the page object navigates.
- **A matrix over every supported culture** is the same class with
  `[TestFixtureSource(typeof(SupportedLocales), nameof(SupportedLocales.All))]` instead of the two attributes.
- **Failure evidence:** `BaseTest` names files `<Class>.<Test>`, the same for every culture row, so two rows
  failing in one run share the files in `playwright-artifacts/`; the NUnit result, the TRX and Allure keep
  each row apart (the fixture name carries its arguments).
- The page objects (`LandingPage`, `CartPage`, `OrderPage`, `AppShellPage`, `CheckoutPage`) are in
  [`references/details.md`](references/details.md) §0.

## 2. Date / number / currency — via `CultureInfo`, timezone pinned (idea #2)

```csharp
[TestFixture("de-DE", "Europe/Berlin")]
public class FormattingI18nTests(string locale, string timezoneId) : BaseTest
{
    private static readonly DateTimeOffset Now = new(2026, 3, 14, 9, 0, 0, TimeSpan.Zero);
    private readonly CultureInfo _culture = CultureInfo.GetCultureInfo(locale);
    private CartPage _cart = null!;
    private OrderPage _order = null!;

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.Locale = locale;
        options.TimezoneId = timezoneId;
        return options;
    }

    [SetUp]
    public async Task FreezeTimeAndCreatePages()
    {
        await Page.Clock.SetFixedTimeAsync(Now.UtcDateTime);
        _cart = new CartPage(Page);
        _order = new OrderPage(Page);
    }

    [Test]
    public async Task Should_FormatTheCartTotal_When_ShownInTheLocaleCurrency()
    {
        await _cart.OpenAsync();

        await Expect(_cart.Total).ToHaveTextAsync(1234.5m.ToString("C", _culture));
    }

    [Test]
    public async Task Should_FormatThePlacedOnDate_When_ShownInTheLocaleTimezone()
    {
        await _order.OpenAsync("ord-1");

        var placedOn = TimeZoneInfo.ConvertTime(Now, TimeZoneInfo.FindSystemTimeZoneById(timezoneId));
        await Expect(_order.PlacedOn).ToHaveTextAsync(placedOn.DateTime.ToString("D", _culture));
    }
}
```

- The seeded cart total (1234.5 EUR) and the order's placement instant (`Now`) come from the test's data seed;
  the clock is frozen in `[SetUp]`, before the page object navigates, so "today" and relative times
  ("vor 2 Stunden") are stable (`ui-test-author/playwright/references/emulation-and-mobile-web.md` §6).
- Many cultures put a **non-breaking** or narrow no-break space inside formatted numbers — a copy-pasted literal
  uses a normal space and fails. Deriving both sides from `CultureInfo` moves them together on a
  globalization-data update. CI must run ICU globalization, not `InvariantGlobalization`.

## 4a. RTL — assert the layout mirrors (idea #4)

```csharp
[TestFixture("ar-EG", "Africa/Cairo")]
public class RtlI18nTests(string locale, string timezoneId) : BaseTest
{
    private AppShellPage _shell = null!;

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.Locale = locale;
        options.TimezoneId = timezoneId;
        return options;
    }

    [SetUp]
    public void CreatePages() => _shell = new AppShellPage(Page);

    [Test]
    public async Task Should_DeclareRightToLeft_When_TheCultureIsArabic()
    {
        await _shell.OpenAsync();

        await Expect(_shell.Document).ToHaveAttributeAsync("dir", "rtl");
    }

    [Test]
    public async Task Should_PlaceTheNavigationOnTheRight_When_TheCultureIsArabic()
    {
        await _shell.OpenAsync();

        Assert.That(await _shell.NavigationSideAsync(), Is.EqualTo(ScreenSide.Right));
    }
}
```

A real RTL culture exercises the app's direction logic, bidi and mirrored assets; a CSS `direction` toggle does
not. `NavigationSideAsync()` waits for the navigation, then measures its centre against the viewport.

## Deep-dive reference

[`references/details.md`](references/details.md): **0. Page objects** · **3. Pseudo-localization** (the
transform and the `en-XA` fixture) · **4b. Translation-key coverage** (the static diff) · **ICU plurals** ·
**Locale matrix** · **Examples**.

## Anti-patterns

- **Asserting a hardcoded literal** (`ToHaveTextAsync("Willkommen")`), or **comparing the resources to
  themselves**. *Fix:* the DOM on the left, `Catalog.T(key, culture)` on the right.
- **A hardcoded formatted value** (`"1.234,56 €"`). *Fix:* `value.ToString("C"/"D", culture)`.
- **A floating CI timezone or clock.** *Fix:* `TimezoneId` on the context, `TimeZoneInfo` on the expected side,
  `Page.Clock.SetFixedTimeAsync` before load.
- **A base class that launches its own browser in `[OneTimeSetUp]`** and shares one page across the fixture's
  tests. Order-dependent, ignores the runsettings. *Fix:* derive from `BaseTest`; the culture is a fixture
  parameter applied in `ContextOptions()`.
- **`ContextOptions()` returning `new() { Locale = … }`.** Drops `BaseURL` and the video folder. *Fix:* amend
  `base.ContextOptions()`.
- **Faking RTL with a CSS toggle**, or asserting a vacuous style (`ToHaveCSSAsync(prop, ".+")`). *Fix:* a real
  RTL culture; `dir="rtl"` plus a measured position.
- **Only checking that keys exist**, or **plurals at counts 1 and 2 only**. *Fix:* the full static diff; the
  boundary counts the language has.
- **Concatenating translated fragments** (`T("welcome") + name`). *Fix:* one interpolated key.

## Rules (hard constraints)

- **Never assert a hardcoded literal string.** Expected values come from the app's resources by key, or from
  `CultureInfo` — never copied in, never the resources compared to themselves.
- **Formatting is asserted via `CultureInfo`** (or ICU4N `PluralRules`), timezone pinned on both sides, clock
  frozen for relative times.
- **Pseudo-localization is a required CI gate**; **RTL uses a real RTL culture**; **key coverage is a static,
  build-gating test** (`tryParents: false`).
- **Browser fixtures derive from `BaseTest`; the culture is a `[TestFixture]` / `[TestFixtureSource]`
  parameter** applied by amending `base.ContextOptions()`. The supported list is `SupportedLocales.All`.
- Tests reach the page through page objects; one logical assertion per test; `Should_X_When_Y` names; async
  all the way; no `WaitForTimeoutAsync`.

## Cross-references

- `qa-language-testing-typescript` (canonical) · `qa-language-testing-java` — the sibling stacks; same four ideas.
- `qa-ui-test-writer-playwright-dotnet` — `BaseTest`, `ContextOptions()` and the emulation reference (locale,
  time zone, `Page.Clock`).
- `qa-visual-regression-dotnet` — the pixel record that pairs with the pseudo-loc overflow check.
- `qa-data-driven-testing-dotnet` — the row pattern; here the rows are fixture parameters.
- `qa-accessibility-testing-dotnet` — `html[lang]` / `dir` rules; run them on the culture-pinned page.
- `qa-test-reports-dotnet` — each culture as a named result, so a failure says which language broke.
