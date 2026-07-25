---
name: qa-responsive-testing-dotnet
description: Use when testing responsive layout/breakpoint behavior in .NET 10 (8-9) with Playwright .NET + NUnit — drive the viewport across the app's real CSS breakpoints (read from its token/theme source, never guessed), assert the layout variant at breakpoint−1 and breakpoint (BVA), verify geometry via bounding boxes. Triggers "test the responsive design", "assert the nav collapses to a hamburger", "test around the breakpoints". Not for pixel diffs (`visual-regression`).
---

# QA — Responsive / Breakpoint Testing (.NET / Playwright + NUnit)

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
>    (hamburger visible + full nav hidden, grid renders 3 columns vs 1 — derived from bounding-box rows);
>    **relative geometry** (children share a left edge, sibling boxes don't overlap, child stays inside parent)
>    via `BoundingBoxAsync()` comparisons with a small tolerance — never absolute coordinates; **overflow** (no
>    horizontal scroll: `scrollWidth <= clientWidth` on the document, no element's right edge past the viewport).
> 4. **Fresh-load and live-resize are different code paths — test both where both happen.** CSS media queries
>    respond to `Page.SetViewportSizeAsync` live, but JS/interop breakpoint logic (`matchMedia` listeners,
>    Blazor `MudBreakpointProvider` / resize interop, JS-chosen component variants) may only run on load — or
>    break only on live resize. Default to **navigating at the target viewport** (viewport set in
>    `ContextOptions()`); add explicit **live-resize** tests for surfaces users actually resize (desktop window
>    drag, orientation flip), asserting with `Expect(...)` web-first assertions after the resize — never
>    `Task.Delay`/`WaitForTimeoutAsync`.

## Decision matrix — responsive surface → test shape

| Surface | What you're proving | Test shape |
|---------|---------------------|------------|
| **Layout variant per breakpoint** | The right structure renders on each side of the boundary | Navigate at bp−1 and bp → assert the variant marker (`ToBeVisibleAsync`/`ToBeHiddenAsync` on nav/hamburger/drawer) |
| **Element alignment** | Related elements stay aligned when the breakpoint flips | `BoundingBoxAsync()` — equal left edges / tops within tolerance, at each boundary width |
| **Grid/column reflow** | Cards go 3-col → 2-col → 1-col at the right widths | Group card boxes by `Y` → assert row lengths per width |
| **No overflow / no clipping** | Nothing forces a horizontal scrollbar or escapes its container | `scrollWidth <= clientWidth`; child box within parent box |
| **Live resize / rotation** | JS breakpoint logic reacts to a real resize | Load wide → `SetViewportSizeAsync` narrow → web-first assert the swap (and back) |
| **Whole-page look per viewport** | Everything the structural checks can't name | Hand off: `qa-visual-regression-dotnet`, one baseline per viewport |
| **Real mobile UX (touch, DPR, UA)** | Device behavior, not CSS breakpoints | `Playwright.Devices["iPhone 15"]` profiles in `ui-test-author/playwright` — out of scope here |

## Stack

- .NET 8, **Microsoft.Playwright.NUnit** (`PageTest`), NUnit
- **The app's own breakpoint source** — mirrored into one `Breakpoints` class (the analogue of i18n-testing's
  supported-culture list). Where the app defines them:

| App uses | Breakpoints live in | Defaults (px) |
|---|---|---|
| MudBlazor (Blazor SUT) | theme / `MudGlobal` breakpoints | sm 600 · md 960 · lg 1280 · xl 1920 |
| Fluent UI Blazor | grid breakpoints | sm 600 · md 960 · lg 1280 · xl 1920 |
| Bootstrap 5 | `$grid-breakpoints` | sm 576 · md 768 · lg 992 · xl 1200 · xxl 1400 |
| Tailwind | `tailwind.config` `screens` / v4 `@theme` | sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1536 |
| Bespoke CSS | the tokens file / one `breakpoints.css` | whatever it says — read it |

- Viewport set via `ContextOptions()` per fixture (one fixture/parameterization per viewport class) — never
  `SetViewportSizeAsync` scattered per test except in explicit live-resize tests
- A fixed height per class (e.g. 720) — width is the variable under test; height only matters for fold checks

```csharp
// Responsive/Breakpoints.cs — the ONE place widths live (mirror of the app's source)
public static class Breakpoints
{
    public const int Sm = 640;
    public const int Md = 768;
    public const int Lg = 1024;
    public const int Xl = 1280;

    /// <summary>BVA pair for a min-width breakpoint: last width BELOW it, first width AT it.</summary>
    public static IEnumerable<int> Around(int bp) => new[] { bp - 1, bp };
}
```

## Boundary matrix — the core pattern

```csharp
[TestFixture]
public class NavResponsiveTests : PageTest
{
    private static IEnumerable<int> AroundMd => Breakpoints.Around(Breakpoints.Md);

    [TestCaseSource(nameof(AroundMd))]
    public async Task Should_Render_Correct_Nav_Variant_At_Md_Boundary(int width)
    {
        await Page.SetViewportSizeAsync(width, 720);
        await Page.GotoAsync("/");                          // fresh load AT the width (idea #4)

        var fullNav = Page.GetByTestId("nav-desktop");
        var hamburger = Page.GetByTestId("nav-hamburger");
        if (width < Breakpoints.Md)
        {
            await Expect(hamburger).ToBeVisibleAsync();
            await Expect(fullNav).ToBeHiddenAsync();        // the swap is exclusive — assert BOTH sides
        }
        else
        {
            await Expect(fullNav).ToBeVisibleAsync();
            await Expect(hamburger).ToBeHiddenAsync();
        }
    }
}
```

## Geometry assertions — alignment, reflow, overlap

```csharp
// Responsive/LayoutAssert.cs — reusable structural helpers
public static class LayoutAssert
{
    private const float Tolerance = 1f; // sub-pixel rendering — never assert exact coordinates

    public static async Task LeftAlignedAsync(params ILocator[] locators)
    {
        var boxes = await Task.WhenAll(locators.Select(l => l.BoundingBoxAsync()));
        var reference = boxes[0]!.X;
        Assert.That(boxes.Select(b => b!.X), Is.All.EqualTo(reference).Within(Tolerance),
            "elements must share a left edge");
    }

    /// <summary>Cards grouped into visual rows by Y → column count of the first row.</summary>
    public static async Task<int> ColumnCountAsync(ILocator cards)
    {
        var boxes = await Task.WhenAll((await cards.AllAsync()).Select(c => c.BoundingBoxAsync()));
        var firstRowY = boxes.Min(b => b!.Y);
        return boxes.Count(b => Math.Abs(b!.Y - firstRowY) <= Tolerance);
    }

    public static async Task NoHorizontalOverflowAsync(IPage page)
    {
        var overflow = await page.EvaluateAsync<int>(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth");
        Assert.That(overflow, Is.LessThanOrEqualTo(0), "page must not scroll horizontally");
    }

    public static async Task NoOverlapAsync(ILocator a, ILocator b)
    {
        var (ba, bb) = (await a.BoundingBoxAsync(), await b.BoundingBoxAsync());
        var separated =
            ba!.X + ba.Width <= bb!.X + Tolerance || bb.X + bb.Width <= ba.X + Tolerance ||
            ba.Y + ba.Height <= bb.Y + Tolerance || bb.Y + bb.Height <= ba.Y + Tolerance;
        Assert.That(separated, Is.True, "elements must not overlap");
    }
}
```

```csharp
// grid reflow across breakpoints, one data-driven body
[TestCase(Breakpoints.Md - 1, 1)]
[TestCase(Breakpoints.Md, 2)]
[TestCase(Breakpoints.Lg - 1, 2)]
[TestCase(Breakpoints.Lg, 3)]
public async Task Should_Reflow_Product_Grid_At_Boundary(int width, int expectedColumns)
{
    await Page.SetViewportSizeAsync(width, 720);
    await Page.GotoAsync("/products");
    var cards = Page.GetByTestId("product-card");
    await Expect(cards.First).ToBeVisibleAsync();
    Assert.That(await LayoutAssert.ColumnCountAsync(cards), Is.EqualTo(expectedColumns));
    await LayoutAssert.NoHorizontalOverflowAsync(Page);
}
```

## Live resize — the JS-breakpoint code path (idea #4)

```csharp
[Test]
public async Task Should_Swap_Nav_On_Live_Shrink_And_Restore_On_Grow()
{
    await Page.SetViewportSizeAsync(Breakpoints.Lg, 720);
    await Page.GotoAsync("/");
    await Expect(Page.GetByTestId("nav-desktop")).ToBeVisibleAsync();

    await Page.SetViewportSizeAsync(Breakpoints.Md - 1, 720);              // shrink across the boundary
    await Expect(Page.GetByTestId("nav-hamburger")).ToBeVisibleAsync();    // web-first assertion waits — no sleep
    await Expect(Page.GetByTestId("nav-desktop")).ToBeHiddenAsync();

    await Page.SetViewportSizeAsync(Breakpoints.Lg, 720);                  // and back — resize listeners leak state
    await Expect(Page.GetByTestId("nav-desktop")).ToBeVisibleAsync();
}
```

> **Blazor SUT note:** MudBlazor's `MudHidden`/`MudBreakpointProvider` and hand-rolled `matchMedia` interop are
> exactly the JS-path logic idea #4 targets — under **static SSR** the C# breakpoint services don't run at all
> (CSS-only responsiveness must hold), and under interactive render modes the live-resize test proves the interop
> actually re-fires. Test both a fresh load per boundary width *and* a live resize on interactive surfaces.

## Anti-patterns

- **Hardcoding magic widths per test** (`SetViewportSizeAsync(768, …)` scattered everywhere). Rots when design
  moves the breakpoint. *Fix:* one `Breakpoints` class mirroring the app's source; tests reference it.
- **Testing only representative widths** (375/768/1440) and skipping the boundaries. Misses every off-by-one in
  the media queries — the exact bug class responsive testing exists for. *Fix:* bp−1 and bp per breakpoint.
- **Asserting absolute coordinates** (`Assert.That(box.X, Is.EqualTo(312))`). Breaks on any content, font, or
  scrollbar change. *Fix:* relative geometry — equal edges, containment, non-overlap, with a 1px tolerance.
- **Asserting only one side of a variant swap.** The hamburger being visible doesn't prove the desktop nav is
  gone — both can render (duplicate DOM bugs). *Fix:* assert visible **and** the counterpart hidden.
- **`Task.Delay`/`WaitForTimeoutAsync` after a resize.** Flaky and slow. *Fix:* `Expect(...)` web-first
  assertions auto-wait; for raw geometry, poll the measurement (`Assert.ThatAsync` / retry on condition).
- **Screenshot-only responsive coverage.** A pixel diff says *something* changed, not *what rule* broke, and it
  drowns in noise per viewport. *Fix:* structural assertions here; `visual-regression` per viewport as the
  complement.
- **Testing breakpoints with device profiles** (`Devices["iPhone 15"]`). Profiles pin DPR/UA/touch — great for
  mobile UX, wrong for isolating a CSS boundary (the width isn't at your breakpoint). *Fix:* plain viewport for
  boundaries; device profiles for device journeys.
- **Only testing shrink.** Grow paths (mobile → desktop) exercise different listener/state code and un-collapse
  logic. *Fix:* resize both directions in the live-resize test.

## Rules (hard constraints)

- **The breakpoint list lives in one `Breakpoints` class that mirrors the app's own definition** — no width
  literals in tests.
- **Every breakpoint gets a bp−1 / bp boundary pair** (fresh load at each); representative widths are additive.
- **Assertions are structural**: variant swap (both sides), relative bounding-box geometry with tolerance,
  overflow math. Never absolute coordinates; never pixel diffs (that's `visual-regression`).
- **No horizontal overflow at any tested width** — the cheapest, highest-value responsive assertion; run it in
  every responsive test.
- **Live-resize tests exist for resize-reachable surfaces**, resize both directions, and use web-first
  assertions — no `Task.Delay`.
- **Viewport is configured** (fixture `ContextOptions` / `TestCaseSource` widths), not improvised — except the
  deliberate resize inside live-resize tests.
- One logical assertion per test; data-driven iteration over breakpoints (`TestCaseSource`, per
  `qa-data-driven-testing-dotnet`), never copy-pasted tests; nullable reference types enabled; async all the way.

## Cross-references

- `qa-responsive-testing-typescript` · `qa-responsive-testing-java` — sibling stacks (Playwright Test ·
  Playwright-Java + TestNG); same four ideas, different APIs.
- `qa-ui-test-author-playwright-dotnet` — base fixture/POM conventions; responsive adds the width dimension.
  Page objects expose variant intent (`Navigation.IsCollapsedAsync()`), not boxes — geometry helpers live beside
  the tests.
- `qa-visual-regression-dotnet` — the pixel complement: one baseline per viewport, after the structural checks
  pass.
- `qa-accessibility-testing-dotnet` — reflow/zoom (WCAG 1.4.10) and touch-target sizes at mobile widths overlap
  with a11y scans; run them at the same widths.
- `qa-data-driven-testing-dotnet` — the breakpoint matrix is its row-binding pattern applied to widths.
- `frontend/blazor/skills/responsive-design` (FE peer) — the dev-side skill that defines the breakpoint contract
  this skill reads; its testid rules (variant-suffixed `nav-desktop`/`nav-hamburger`) are what make the variant
  swap assertable.
