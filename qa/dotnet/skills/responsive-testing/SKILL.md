---
name: responsive-testing
description: Use when testing responsive layout/breakpoint behavior in .NET 10 (8-9) with Playwright .NET + NUnit — drive the viewport across the app's real CSS breakpoints (read from its token/theme source, never guessed), assert the layout variant at breakpoint−1 and breakpoint (BVA), verify geometry via bounding boxes. Triggers "test the responsive design", "assert the nav collapses to a hamburger", "test around the breakpoints". Not for pixel diffs (`visual-regression`).
---

# QA — Responsive / Breakpoint Testing (.NET 10 / Playwright 1.63 + NUnit)

Tests that a web app's layout **adapts correctly across viewport widths**: the right layout variant renders on
each side of every CSS breakpoint, related elements stay aligned with each other when the breakpoint flips, and
nothing overflows. The assertions are **structural** (visibility swaps, bounding-box geometry, overflow math) —
pixel-level diffing is `visual-regression`'s job and pairs with this skill, it doesn't replace it.

> **The discipline this skill encodes** — four ideas that separate a correct responsive test from resizing and
> eyeballing:
>
> 1. **Breakpoints come from the app's source — never guessed, never duplicated per test.** The breakpoint list
>    is test data, read from the one place the app defines it: the MudBlazor/Fluent theme, Bootstrap's
>    `$grid-breakpoints`, the Tailwind config, or the CSS custom-property token file. Mirror it once as a
>    `Breakpoints` class and drive every matrix from it — a hardcoded `768` in a test silently rots the day
>    design changes the breakpoint.
> 2. **Test the boundary, not the middle — BVA on the media query.** A `@media (min-width: 768px)` rule is a
>    boundary: at **767 px** the mobile layout must hold, at **768 px** the desktop layout must have taken over.
>    Two-value boundary analysis per breakpoint (bp−1, bp) catches the off-by-one (`min-width` vs `max-width`
>    overlap/gap bugs) that a "test at 375/768/1440" matrix sails past. Representative in-range widths are the
>    *smoke* layer on top, not the substitute.
> 3. **Assert structure, not pixels.** Three assertion families, all robust to content changes: **variant swap**
>    (hamburger visible + full nav hidden), **relative geometry** (column count from bounding-box rows, shared
>    left edges, no overlap — with a small tolerance, never absolute coordinates), and **overflow** (no
>    horizontal scroll: `scrollWidth - clientWidth` is `0`).
> 4. **Fresh-load and live-resize are different code paths — test both where both happen.** CSS media queries
>    respond to a live resize, but JS/interop breakpoint logic (`matchMedia` listeners, MudBlazor's
>    `MudBreakpointProvider`, JS-chosen component variants) may only run on load — or break only on live
>    resize. Default to **loading at the target viewport** (set in the fixture's `ContextOptions()`); add
>    explicit **live-resize** tests for surfaces users actually resize, asserting with web-first `Expect(...)`
>    after the resize — never `Task.Delay`/`WaitForTimeoutAsync`.

## Decision matrix — responsive surface → test shape

| Surface | What you're proving | Test shape |
|---------|---------------------|------------|
| **Layout variant per breakpoint** | The right structure renders on each side of the boundary | One fixture row per width (bp−1, bp) naming the variant shown and the one hidden → `ToBeVisibleAsync` / `ToBeHiddenAsync` |
| **Element alignment** | Related elements stay aligned when the breakpoint flips | `_layout.LeftEdgeSpreadAsync(...)` ≤ tolerance, at each boundary width |
| **Grid/column reflow** | Cards go 3-col → 2-col → 1-col at the right widths | One fixture row per width naming its column count → `_layout.ColumnCountAsync(cards)` |
| **No overflow / no clipping** | Nothing forces a horizontal scrollbar | `_layout.HorizontalOverflowAsync()` is `0` |
| **Live resize / rotation** | JS breakpoint logic reacts to a real resize | Load wide → `_layout.ResizeToAsync(narrow)` → web-first assert the swap (and back) |
| **Whole-page look per viewport** | Everything the structural checks can't name | Hand off: `qa-dotnet:visual-regression`, one baseline per viewport |
| **Real mobile UX (touch, DPR, UA)** | Device behavior, not CSS breakpoints | `Playwright.Devices[...]` per fixture — `ui-test-author/playwright/references/emulation-and-mobile-web.md` |

## Stack

- .NET 10 (8/9 supported — match the project's TFM), NUnit 4, **Microsoft.Playwright.NUnit** at the pins in the
  **Versions** table of `qa/dotnet/skills/ui-test-author/playwright/SKILL.md` (this skill pins nothing).
- Every fixture **derives from N1's `BaseTest`** (`ui-test-author/playwright/assets/BaseTest.cs`): `BASE_URL`,
  failure evidence, `ParallelScope.Self`. No second base class, no `Playwright.CreateAsync()`.
- **Viewport per fixture, in `ContextOptions()`**, amending `base.ContextOptions()`
  (`emulation-and-mobile-web.md` §3). A row matrix is **fixture parameters**: one `[TestFixture(width, …)]` per
  row, the constructor takes the row, and `ContextOptions()` sets that row's width. `SetViewportSizeAsync`
  happens only inside live-resize tests, through `Layout.ResizeToAsync`.
- A fixed height (`Breakpoints.Height`, 720) — width is the variable under test.
- **The app's own breakpoint source**, mirrored into one `Breakpoints` class:

| App uses | Breakpoints live in | Defaults (px) |
|---|---|---|
| MudBlazor (Blazor SUT) | theme / `MudGlobal` breakpoints | sm 600 · md 960 · lg 1280 · xl 1920 |
| Fluent UI Blazor | grid breakpoints | sm 600 · md 960 · lg 1280 · xl 1920 |
| Bootstrap 5 | `$grid-breakpoints` | sm 576 · md 768 · lg 992 · xl 1200 · xxl 1400 |
| Tailwind | `tailwind.config` `screens` / v4 `@theme` | sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1536 |
| Bespoke CSS | the tokens file / one `breakpoints.css` | whatever it says — read it |

## Page objects and the `Layout` helper

`Breakpoints`, the `AppShellPage` and `ProductsPage` page objects and the `Layout` helper are in
[`references/page-objects-and-layout.md`](references/page-objects-and-layout.md). Page objects expose variant
intent (`_appShell.Nav(NavVariant.Hamburger)` → `GetByTestId("Nav.Hamburger")`), never boxes. `Layout`
**measures and returns numbers** — `ColumnCountAsync(cards)`, `HorizontalOverflowAsync()`,
`LeftEdgeSpreadAsync(...)`, `OverlapDepthAsync(a, b)` — plus `ResizeToAsync(width)` for live-resize tests. The
test asserts; a helper never does.

## Boundary rows — the core pattern

Each row states the width **and** what that width must show. The test body has no branch: NUnit builds one
fixture instance per `[TestFixture]` row, `ContextOptions()` gives each instance its viewport, and the row's
expected values are the assertion's operands.

```csharp
using Example.UiTests.Pages;
using Example.UiTests.Support;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[TestFixture(Breakpoints.Md - 1, NavVariant.Hamburger, NavVariant.Desktop)]
[TestFixture(Breakpoints.Md, NavVariant.Desktop, NavVariant.Hamburger)]
public class NavBoundaryTests(int width, NavVariant shown, NavVariant hidden) : BaseTest
{
    private AppShellPage _appShell = null!;

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.ViewportSize = Breakpoints.Viewport(width);
        return options;
    }

    [SetUp]
    public void CreatePages() => _appShell = new AppShellPage(Page);

    [Test]
    public async Task Should_ShowOnlyTheRowsNavVariant_When_LoadedAtTheRowsWidth()
    {
        await _appShell.OpenAsync();

        await Expect(_appShell.Nav(shown), $"{shown} navigation at {width}px").ToBeVisibleAsync();
        await Expect(_appShell.Nav(hidden), $"{hidden} navigation at {width}px").ToBeHiddenAsync();
    }
}
```

- The swap is exclusive, so both sides are asserted: one behaviour, two expectations.
- `Breakpoints.Md - 1` is a constant expression, so it is legal in an attribute; so are the enum values.
- Each row is its own NUnit fixture, so `BaseTest`'s `ParallelScope.Self` runs the rows in parallel, each with
  its own page. Never `ParallelScope.All` with a `[TestCase]` per width that resizes the page.
- `BaseTest` names failure evidence `<Class>.<Test>`, the same for every row: two rows failing in one run write
  the same files in `playwright-artifacts/`. The NUnit result, the TRX and Allure keep the rows apart (the
  fixture name carries its arguments), and the assertion message names the width.

## Geometry rows — reflow, overflow, alignment

```csharp
[TestFixture(Breakpoints.Md - 1, 1)]
[TestFixture(Breakpoints.Md, 2)]
[TestFixture(Breakpoints.Lg - 1, 2)]
[TestFixture(Breakpoints.Lg, 3)]
public class ProductGridBoundaryTests(int width, int columns) : BaseTest
{
    private ProductsPage _productsPage = null!;
    private Layout _layout = null!;

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.ViewportSize = Breakpoints.Viewport(width);
        return options;
    }

    [SetUp]
    public void CreatePages()
    {
        _productsPage = new ProductsPage(Page);
        _layout = new Layout(Page);
    }

    [Test]
    public async Task Should_ShowTheRowsColumnCount_When_LoadedAtTheRowsWidth()
    {
        await _productsPage.OpenAsync();

        Assert.That(await _layout.ColumnCountAsync(_productsPage.Cards), Is.EqualTo(columns), $"columns at {width}px");
    }

    [Test]
    public async Task Should_NotScrollHorizontally_When_LoadedAtTheRowsWidth()
    {
        await _productsPage.OpenAsync();

        Assert.That(await _layout.HorizontalOverflowAsync(), Is.Zero, $"horizontal overflow at {width}px");
    }

    [Test]
    public async Task Should_KeepFiltersBesideResults_When_LoadedAtTheRowsWidth()
    {
        await _productsPage.OpenAsync();

        Assert.That(await _layout.OverlapDepthAsync(_productsPage.Filters, _productsPage.Results),
            Is.LessThanOrEqualTo(Layout.TolerancePx), $"filters overlapping results at {width}px");
    }
}
```

- `_productsPage.OpenAsync()` returns once the first card is visible, and the viewport is fixed for the whole
  test, so the measurement reads a settled layout. The message carries the row into the failure.
- Alignment is the same shape:
  `Assert.That(await _layout.LeftEdgeSpreadAsync(form.Title, form.Email, form.Submit), Is.LessThanOrEqualTo(Layout.TolerancePx))`.

## Live resize — the JS-breakpoint code path (idea #4)

```csharp
public class NavLiveResizeTests : BaseTest
{
    private AppShellPage _appShell = null!;
    private Layout _layout = null!;

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.ViewportSize = Breakpoints.Viewport(Breakpoints.Lg);
        return options;
    }

    [SetUp]
    public void CreatePages()
    {
        _appShell = new AppShellPage(Page);
        _layout = new Layout(Page);
    }

    [Test]
    public async Task Should_ShowHamburgerNav_When_WindowShrinksBelowMd()
    {
        await _appShell.OpenAsync();

        await _layout.ResizeToAsync(Breakpoints.Md - 1);

        await Expect(_appShell.Nav(NavVariant.Hamburger)).ToBeVisibleAsync();
        await Expect(_appShell.Nav(NavVariant.Desktop)).ToBeHiddenAsync();
    }

    [Test]
    public async Task Should_RestoreDesktopNav_When_WindowGrowsBackToLg()
    {
        await _appShell.OpenAsync();
        await _layout.ResizeToAsync(Breakpoints.Md - 1);
        await Expect(_appShell.Nav(NavVariant.Hamburger)).ToBeVisibleAsync();

        await _layout.ResizeToAsync(Breakpoints.Lg);

        await Expect(_appShell.Nav(NavVariant.Desktop)).ToBeVisibleAsync();
        await Expect(_appShell.Nav(NavVariant.Hamburger)).ToBeHiddenAsync();
    }
}
```

The grow test asserts the shrink first only as its arrange step's completion signal — the web-first assertion
waits for the collapsed state before the resize back. After a resize, measure geometry only once a web-first
assertion on the new variant has passed.

**Blazor SUT:** under static SSR, MudBlazor's breakpoint services and `matchMedia` interop don't run (CSS alone
must hold); under interactive render modes, the live-resize test proves the interop re-fires. Test both.

## Anti-patterns

- **Magic widths per test**, or **only representative widths** (375/768/1440). Rots when design moves the
  breakpoint, and misses every off-by-one. *Fix:* one `Breakpoints` class; bp−1 and bp rows per breakpoint.
- **`if (width < Breakpoints.Md)` in the test body.** A branch hides which expectation ran. *Fix:* the row names
  what it must show (`shown` / `hidden`, `columns`).
- **`Page.SetViewportSizeAsync` at the top of every test.** Resizes a page loaded at another width — the
  live-resize path, not a fresh load — and calls `Page` from the test. *Fix:* the viewport per fixture in
  `ContextOptions()`; `ResizeToAsync` only in live-resize tests.
- **Asserting absolute coordinates** (`box.X == 312`), or **only one side of a swap** (both can render). *Fix:*
  relative geometry with `Layout.TolerancePx`; the shown variant visible **and** the other hidden.
- **`Task.Delay`/`WaitForTimeoutAsync` after a resize.** *Fix:* web-first assertions auto-wait; measure after one.
- **Testing breakpoints with device profiles** (`Playwright.Devices["iPhone 13"]`). Profiles pin DPR/UA/touch.
  *Fix:* plain viewport for boundaries; device fixtures for device journeys.
- **Only testing shrink**, or a private `Playwright.CreateAsync()`. *Fix:* resize both directions; derive from
  `BaseTest`.

## Rules (hard constraints)

- **The breakpoint list lives in one `Breakpoints` class that mirrors the app's own definition** — no width
  literals in tests.
- **Every breakpoint gets a bp−1 / bp row pair** (fresh load at each); representative widths are additive.
- **Rows carry the expectation** (`shown`/`hidden`, `columns`); a test body never branches on the width.
- **Assertions are structural**: variant swap (both sides), relative geometry with tolerance, overflow `0`.
  Never absolute coordinates; never pixel diffs (that's `visual-regression`).
- **No horizontal overflow at any tested width** — the cheapest, highest-value responsive assertion.
- **Live-resize tests exist for resize-reachable surfaces**, resize both directions, and use web-first
  assertions — no `Task.Delay`.
- **Viewport per fixture in `ContextOptions()`**, amending `base.ContextOptions()`; rows are `[TestFixture]`
  parameters — except the deliberate resize inside live-resize tests. Tests reach the page only through page
  objects and `Layout`.
- Every fixture derives from `BaseTest`; parallelism stays `ParallelScope.Self`; test names `Should_X_When_Y`;
  test ids PascalCase dot-separated (`Nav.Desktop`, `ProductGrid.Card`).

## Cross-references

- `qa-typescript:responsive-testing` · `qa-java:responsive-testing` — sibling stacks; same four ideas.
- `qa-dotnet:ui-tests-playwright` — `BaseTest`, `ContextOptions()` (`lifecycle.md` §4) and the emulation
  reference (`emulation-and-mobile-web.md`: viewport per fixture, device profiles, media features).
- `qa-dotnet:visual-regression` — the pixel complement: one baseline per viewport, after the structural checks
  pass.
- `qa-dotnet:accessibility-testing` — reflow/zoom (WCAG 1.4.10) and touch targets, at the same widths.
- `qa-dotnet:data-driven-testing` — the row pattern; here rows are fixture parameters (each needs its own
  context options).
- `frontend/blazor/skills/responsive-design` (FE peer) — the dev-side skill that defines the breakpoint contract
  this skill reads. Its variant-suffixed test ids are what make the swap assertable; in this library's
  PascalCase form they are `Nav.Desktop` / `Nav.Hamburger` (CLAUDE.md). `frontend/react/skills/responsive-design`
  is the React peer of the same contract.
