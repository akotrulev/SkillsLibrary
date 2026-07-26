---
name: qa-responsive-testing-java
description: Use when testing responsive layout/breakpoint behavior in Java 21 with Playwright-Java + TestNG — drive the viewport across the app's real CSS breakpoints (read from its token/theme source, never guessed), assert the layout variant at breakpoint−1 and breakpoint (BVA), verify structural geometry via bounding boxes. Triggers: "test the responsive design", "assert the nav collapses to a hamburger", "test around the breakpoints". Do NOT use for pixel-diff screenshots (qa-visual-regression-java). For end-to-end suite work prefer the phased agent `qa-ui-java` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Responsive / Breakpoint Testing (Java / Playwright + TestNG)

Tests that a web app's layout **adapts correctly across viewport widths**: the right layout variant renders on
each side of every CSS breakpoint, related elements stay aligned with each other when the breakpoint flips, and
nothing overflows. The assertions are **structural** (visibility swaps, bounding-box geometry, overflow math) —
pixel-level diffing is `visual-regression`'s job and pairs with this skill, it doesn't replace it.

> **The discipline this skill encodes** — four ideas that separate a correct responsive test from resizing and
> eyeballing:
>
> 1. **Breakpoints come from the app's source — never guessed, never duplicated per test.** The breakpoint list
>    is test data, read from the one place the app defines it: the Tailwind config / `@theme` block, the MUI
>    theme, Bootstrap's `$grid-breakpoints`, or the CSS custom-property token file. Mirror it once as a
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
>    via `boundingBox()` comparisons with a small tolerance — never absolute coordinates; **overflow** (no
>    horizontal scroll: `scrollWidth <= clientWidth` on the document, no element's right edge past the viewport).
> 4. **Fresh-load and live-resize are different code paths — test both where both happen.** CSS media queries
>    respond to `page.setViewportSize()` live, but JS breakpoint logic (`matchMedia` listeners, resize handlers,
>    JS-chosen component variants) may only run on load — or break only on live resize. Default to **navigating
>    at the target viewport** (viewport set in `Browser.NewContextOptions`); add explicit **live-resize** tests
>    for surfaces users actually resize (desktop window drag, orientation flip), asserting with
>    `assertThat(...)` web-first assertions after the resize — never `Thread.sleep`/`waitForTimeout`.

## Decision matrix — responsive surface → test shape

| Surface | What you're proving | Test shape |
|---------|---------------------|------------|
| **Layout variant per breakpoint** | The right structure renders on each side of the boundary | Navigate at bp−1 and bp → assert the variant marker (`isVisible()`/`isHidden()` on nav/hamburger/drawer) |
| **Element alignment** | Related elements stay aligned when the breakpoint flips | `boundingBox()` — equal left edges / tops within tolerance, at each boundary width |
| **Grid/column reflow** | Cards go 3-col → 2-col → 1-col at the right widths | Group card boxes by `y` → assert row lengths per width |
| **No overflow / no clipping** | Nothing forces a horizontal scrollbar or escapes its container | `scrollWidth <= clientWidth`; child box within parent box |
| **Live resize / rotation** | JS breakpoint logic reacts to a real resize | Load wide → `setViewportSize` narrow → web-first assert the swap (and back) |
| **Whole-page look per viewport** | Everything the structural checks can't name | Hand off: `qa-visual-regression-java`, one baseline per viewport |
| **Real mobile UX (touch, DPR, UA)** | Device behavior, not CSS breakpoints | Device emulation options in `ui-test-author/playwright` — out of scope here |

## Stack

- Java 21, **Playwright-Java** (`com.microsoft.playwright`), **TestNG**, `PlaywrightAssertions.assertThat`
- **The app's own breakpoint source** — mirrored into one `Breakpoints` class (the analogue of language-testing's
  supported-locale list). Where the app defines them:

| App uses | Breakpoints live in | Defaults (px) |
|---|---|---|
| Tailwind | `tailwind.config` `screens` / v4 `@theme` | sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1536 |
| Material UI (MUI) | `theme.breakpoints.values` | sm 600 · md 900 · lg 1200 · xl 1536 |
| Bootstrap 5 | `$grid-breakpoints` | sm 576 · md 768 · lg 992 · xl 1200 · xxl 1400 |
| Bespoke CSS | the tokens file / one `breakpoints.css` | whatever it says — read it |

- Viewport set via `Browser.NewContextOptions().setViewportSize(w, h)` in the context factory (one context per
  viewport class) — never `setViewportSize` scattered per test except in explicit live-resize tests
- A fixed height per class (e.g. 720) — width is the variable under test; height only matters for fold checks

```java
// src/test/java/<pkg>/responsive/Breakpoints.java — the ONE place widths live (mirror of the app's source)
public final class Breakpoints {
    public static final int SM = 640;
    public static final int MD = 768;
    public static final int LG = 1024;
    public static final int XL = 1280;

    /** BVA pair for a min-width breakpoint: last width BELOW it, first width AT it. */
    public static int[] around(int bp) { return new int[] { bp - 1, bp }; }

    private Breakpoints() { }
}
```

## Boundary matrix — the core pattern

```java
public class NavResponsiveTest extends BaseUiTest {

    @DataProvider
    public Object[][] aroundMd() {
        return new Object[][] { { Breakpoints.MD - 1 }, { Breakpoints.MD } };
    }

    @Test(dataProvider = "aroundMd")
    public void shouldRenderCorrectNavVariantAtMdBoundary(int width) {
        page.setViewportSize(width, 720);
        page.navigate(baseUrl + "/");                       // fresh load AT the width (idea #4)

        Locator fullNav = page.getByTestId("nav-desktop");
        Locator hamburger = page.getByTestId("nav-hamburger");
        if (width < Breakpoints.MD) {
            assertThat(hamburger).isVisible();
            assertThat(fullNav).isHidden();                 // the swap is exclusive — assert BOTH sides
        } else {
            assertThat(fullNav).isVisible();
            assertThat(hamburger).isHidden();
        }
    }
}
```

## Geometry assertions — alignment, reflow, overlap

```java
// src/test/java/<pkg>/responsive/LayoutAssert.java — reusable structural helpers
public final class LayoutAssert {

    private static final double TOLERANCE = 1.0; // sub-pixel rendering — never assert exact coordinates

    public static void leftAligned(List<Locator> locators) {
        double reference = locators.getFirst().boundingBox().x;
        assertThat(locators)
            .allSatisfy(l -> org.assertj.core.api.Assertions.assertThat(l.boundingBox().x)
                .as("elements must share a left edge")
                .isCloseTo(reference, within(TOLERANCE)));
    }

    /** Cards grouped into visual rows by y → column count of the first row. */
    public static int columnCount(Locator cards) {
        List<BoundingBox> boxes = cards.all().stream().map(Locator::boundingBox).toList();
        double firstRowY = boxes.stream().mapToDouble(b -> b.y).min().orElseThrow();
        return (int) boxes.stream().filter(b -> Math.abs(b.y - firstRowY) <= TOLERANCE).count();
    }

    public static void noHorizontalOverflow(Page page) {
        int overflow = (int) page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth");
        org.assertj.core.api.Assertions.assertThat(overflow)
            .as("page must not scroll horizontally").isLessThanOrEqualTo(0);
    }

    public static void noOverlap(Locator a, Locator b) {
        BoundingBox ba = a.boundingBox(), bb = b.boundingBox();
        boolean separated =
            ba.x + ba.width <= bb.x + TOLERANCE || bb.x + bb.width <= ba.x + TOLERANCE ||
            ba.y + ba.height <= bb.y + TOLERANCE || bb.y + bb.height <= ba.y + TOLERANCE;
        org.assertj.core.api.Assertions.assertThat(separated)
            .as("elements must not overlap").isTrue();
    }

    private LayoutAssert() { }
}
```

```java
// grid reflow across breakpoints, one data-driven body
@DataProvider
public Object[][] gridBoundaries() {
    return new Object[][] {
        { Breakpoints.MD - 1, 1 }, { Breakpoints.MD, 2 },
        { Breakpoints.LG - 1, 2 }, { Breakpoints.LG, 3 },
    };
}

@Test(dataProvider = "gridBoundaries")
public void shouldReflowProductGridAtBoundary(int width, int expectedColumns) {
    page.setViewportSize(width, 720);
    page.navigate(baseUrl + "/products");
    Locator cards = page.getByTestId("product-card");
    assertThat(cards.first()).isVisible();
    org.assertj.core.api.Assertions.assertThat(LayoutAssert.columnCount(cards)).isEqualTo(expectedColumns);
    LayoutAssert.noHorizontalOverflow(page);
}
```

## Live resize — the JS-breakpoint code path (idea #4)

```java
@Test
public void shouldSwapNavOnLiveShrinkAndRestoreOnGrow() {
    page.setViewportSize(Breakpoints.LG, 720);
    page.navigate(baseUrl + "/");
    assertThat(page.getByTestId("nav-desktop")).isVisible();

    page.setViewportSize(Breakpoints.MD - 1, 720);                 // shrink across the boundary
    assertThat(page.getByTestId("nav-hamburger")).isVisible();     // web-first assertion waits — no sleep
    assertThat(page.getByTestId("nav-desktop")).isHidden();

    page.setViewportSize(Breakpoints.LG, 720);                     // and back — resize listeners leak state
    assertThat(page.getByTestId("nav-desktop")).isVisible();
}
```

## Anti-patterns

- **Hardcoding magic widths per test** (`setViewportSize(768, …)` scattered everywhere). Rots when design moves
  the breakpoint. *Fix:* one `Breakpoints` class mirroring the app's source; tests reference it.
- **Testing only representative widths** (375/768/1440) and skipping the boundaries. Misses every off-by-one in
  the media queries — the exact bug class responsive testing exists for. *Fix:* bp−1 and bp per breakpoint.
- **Asserting absolute coordinates** (`assertThat(box.x).isEqualTo(312)`). Breaks on any content, font, or
  scrollbar change. *Fix:* relative geometry — equal edges, containment, non-overlap, with a 1px tolerance.
- **Asserting only one side of a variant swap.** The hamburger being visible doesn't prove the desktop nav is
  gone — both can render (duplicate DOM bugs). *Fix:* assert visible **and** the counterpart hidden.
- **`Thread.sleep`/`waitForTimeout` after a resize.** Flaky and slow. *Fix:* `assertThat(...)` web-first
  assertions auto-wait; for raw geometry, poll the measurement with Awaitility.
- **Screenshot-only responsive coverage.** A pixel diff says *something* changed, not *what rule* broke, and it
  drowns in noise per viewport. *Fix:* structural assertions here; `visual-regression` per viewport as the
  complement.
- **Testing breakpoints with device emulation.** Device options pin DPR/UA/touch — great for mobile UX, wrong
  for isolating a CSS boundary (the width isn't at your breakpoint). *Fix:* plain viewport for boundaries;
  device emulation for device journeys.
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
  assertions — no `Thread.sleep`.
- **Viewport is configured** (context options / `@DataProvider` widths), not improvised — except the deliberate
  resize inside live-resize tests.
- One logical assertion per test; data-driven iteration over breakpoints (`@DataProvider`, per
  `qa-data-driven-testing-java`), never copy-pasted tests; `final` where it fits.

## Cross-references

- `qa-responsive-testing-typescript` · `qa-responsive-testing-dotnet` — sibling stacks (Playwright Test ·
  Playwright .NET + NUnit); same four ideas, different APIs.
- `qa-ui-test-writer-playwright-java` — base fixture/POM conventions; responsive adds the width dimension.
  Page objects expose variant intent (`navigation().isCollapsed()`), not boxes — geometry helpers live beside
  the tests.
- `qa-visual-regression-java` — the pixel complement: one baseline per viewport, after the structural checks
  pass.
- `qa-accessibility-testing-java` — reflow/zoom (WCAG 1.4.10) and touch-target sizes at mobile widths overlap
  with a11y scans; run them at the same widths.
- `qa-data-driven-testing-java` — the breakpoint matrix is its row-binding pattern applied to widths.
- `frontend/blazor/skills/responsive-design` (FE peer) — the dev-side skill that defines the breakpoint contract
  this skill reads; its testid rules (variant-suffixed `nav-desktop`/`nav-hamburger`) are what make the variant
  swap assertable.
