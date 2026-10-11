---
name: responsive-testing
description: Use when testing responsive layout/breakpoint behavior in Java 21 with Playwright-Java + TestNG — drive the viewport across the app's real CSS breakpoints (read from its token/theme source, never guessed), assert the layout variant at breakpoint−1 and breakpoint (BVA), verify structural geometry via bounding boxes. Triggers: "test the responsive design", "assert the nav collapses to a hamburger", "test around the breakpoints". Do NOT use for pixel-diff screenshots (qa-java:visual-regression).
---

# QA — Responsive / Breakpoint Testing (Java / Playwright 1.63 + TestNG)

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
>    `Breakpoints` class and drive every row from it — a hardcoded `768` in a test silently rots the day
>    design changes the breakpoint.
> 2. **Test the boundary, not the middle — BVA on the media query.** A `@media (min-width: 768px)` rule is a
>    boundary: at **767 px** the mobile layout must hold, at **768 px** the desktop layout must have taken over.
>    Two-value boundary analysis per breakpoint (bp−1, bp) catches the off-by-one (`min-width` vs `max-width`
>    overlap/gap bugs) that a "test at 375/768/1440" matrix sails past. Representative in-range widths are the
>    *smoke* layer on top, not the substitute.
> 3. **Assert structure, not pixels.** Three assertion families, all robust to content changes: **variant swap**
>    (hamburger visible + full nav hidden); **relative geometry** (column count from card rows, shared left
>    edges, no overlap) with a small tolerance — never absolute coordinates; **overflow** (no horizontal scroll:
>    `scrollWidth - clientWidth` is `0`).
> 4. **Fresh-load and live-resize are different code paths — test both where both happen.** CSS media queries
>    respond to a live resize, but JS breakpoint logic (`matchMedia` listeners, resize handlers, JS-chosen
>    component variants) may only run on load — or break only on live resize. Default to **loading at the target
>    viewport** (the viewport set per class in `contextOptions()`); add explicit **live-resize** tests for surfaces
>    users actually resize (desktop window drag, orientation flip), asserting with web-first `assertThat(...)`
>    after the resize — never `Thread.sleep`/`waitForTimeout`.

## Decision matrix — responsive surface → test shape

| Surface | What you're proving | Test shape |
|---------|---------------------|------------|
| **Layout variant per breakpoint** | The right structure renders on each side of the boundary | One row per width (bp−1, bp) naming the variant shown and the one hidden → `isVisible()` / `isHidden()` |
| **Element alignment** | Related elements stay aligned when the breakpoint flips | `layout.leftEdgeSpread(...)` ≤ tolerance, at each boundary width |
| **Grid/column reflow** | Cards go 3-col → 2-col → 1-col at the right widths | One row per width naming its column count → `layout.columnCount(cards)` |
| **No overflow / no clipping** | Nothing forces a horizontal scrollbar | `layout.horizontalOverflow()` is `0` |
| **Live resize / rotation** | JS breakpoint logic reacts to a real resize | Load wide → `layout.resizeTo(narrow)` → web-first assert the swap (and back) |
| **Whole-page look per viewport** | Everything the structural checks can't name | Hand off: `qa-java:visual-regression`, one baseline per viewport |
| **Real mobile UX (touch, DPR, UA)** | Device behavior, not CSS breakpoints | Device options per class — `ui-test-author/playwright/references/emulation-and-mobile-web.md` |

## Stack

- Java 21, **Playwright for Java** and **TestNG** at the pins in the **Versions** table of
  `qa/java/skills/ui-test-author/playwright/SKILL.md` (this skill pins nothing); `PlaywrightAssertions.assertThat`
  for locators, AssertJ for measured numbers.
- Every class **extends J1's `BaseTest`** (`ui-test-author/playwright/assets/BaseTest.java`): a browser per class,
  a context and page per test, failure evidence, `BASE_URL`, `parallel="classes"`. No second base class.
- **Viewport per class, in `contextOptions()`** (`emulation-and-mobile-web.md` §3). Each test then loads at its
  width. A row matrix is a TestNG `@Factory`: one instance per row, each instance's `contextOptions()` setting
  that row's width. `page.setViewportSize` happens only inside live-resize tests, through `Layout.resizeTo`.
- A fixed height (`Breakpoints.HEIGHT`, 720) — width is the variable under test.
- **The app's own breakpoint source**, mirrored into one `Breakpoints` class:

| App uses | Breakpoints live in | Defaults (px) |
|---|---|---|
| Tailwind | `tailwind.config` `screens` / v4 `@theme` | sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1536 |
| Material UI (MUI) | `theme.breakpoints.values` | sm 600 · md 900 · lg 1200 · xl 1536 |
| Bootstrap 5 | `$grid-breakpoints` | sm 576 · md 768 · lg 992 · xl 1200 · xxl 1400 |
| Bespoke CSS | the tokens file / one `breakpoints.css` | whatever it says — read it |

## Page objects and the `Layout` helper

`Breakpoints`, the `AppShell` and `ProductsPage` page objects and the `Layout` helper are in
[`references/page-objects-and-layout.md`](references/page-objects-and-layout.md). Page objects expose variant
intent (`appShell.nav(NavVariant.HAMBURGER)` → `getByTestId("Nav.Hamburger")`), never boxes. `Layout` **measures
and returns numbers** — `columnCount(cards)`, `horizontalOverflow()`, `leftEdgeSpread(...)`,
`overlapDepth(a, b)` — plus `resizeTo(width)` for live-resize tests. The test asserts; a helper never does.

## Boundary rows — the core pattern

Each row states the width **and** what that width must show. The test body has no branch: the `@Factory` builds
one instance per row, `contextOptions()` gives each instance its viewport, and the row's expected values are the
assertion's operands.

```java
public class NavBoundaryTest extends BaseTest {
    private final NavRow row;
    private AppShell appShell;

    @Factory(dataProvider = "navRows")
    public NavBoundaryTest(NavRow row) {
        this.row = row;
    }

    @DataProvider
    public static Object[][] navRows() {
        return new Object[][] {
                {new NavRow("BelowMd", Breakpoints.MD - 1, NavVariant.HAMBURGER, NavVariant.DESKTOP)},
                {new NavRow("AtMd", Breakpoints.MD, NavVariant.DESKTOP, NavVariant.HAMBURGER)},
        };
    }

    @Override
    protected Browser.NewContextOptions contextOptions() {
        return new Browser.NewContextOptions().setViewportSize(row.width(), Breakpoints.HEIGHT);
    }

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        appShell = new AppShell(page);
    }

    @Test
    public void Should_ShowOnlyTheRowsNavVariant_When_LoadedAtTheRowsWidth() {
        appShell.open();

        assertThat(appShell.nav(row.shown())).isVisible();
        assertThat(appShell.nav(row.hidden())).isHidden();
    }

    public record NavRow(String name, int width, NavVariant shown, NavVariant hidden) {
    }
}
```

- The swap is exclusive, so both sides are asserted: one behaviour, two expectations.
- The factory's data provider is `static` (no instance exists yet) and sequential. TestNG runs `@BeforeClass`
  once per instance, so each row gets its own browser on the class's one thread — `parallel="classes"` holds
  (`ui-test-author/playwright/references/lifecycle.md` §1).
- Every row reports the same method name, and the failure evidence shares `<Class>.<method>` (the data-provider
  caveat in `qa/java/skills/evidence-capture`). The failing assertion names the locator through `describe(...)`,
  and the trace records the viewport.

## Geometry rows — reflow, overflow, alignment

```java
public class ProductGridBoundaryTest extends BaseTest {
    private final GridRow row;
    private ProductsPage productsPage;
    private Layout layout;

    @Factory(dataProvider = "gridRows")
    public ProductGridBoundaryTest(GridRow row) {
        this.row = row;
    }

    @DataProvider
    public static Object[][] gridRows() {
        return new Object[][] {
                {new GridRow("BelowMd", Breakpoints.MD - 1, 1)},
                {new GridRow("AtMd", Breakpoints.MD, 2)},
                {new GridRow("BelowLg", Breakpoints.LG - 1, 2)},
                {new GridRow("AtLg", Breakpoints.LG, 3)},
        };
    }

    @Override
    protected Browser.NewContextOptions contextOptions() {
        return new Browser.NewContextOptions().setViewportSize(row.width(), Breakpoints.HEIGHT);
    }

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        productsPage = new ProductsPage(page);
        layout = new Layout(page);
    }

    @Test
    public void Should_ShowTheRowsColumnCount_When_LoadedAtTheRowsWidth() {
        productsPage.open();

        assertThat(layout.columnCount(productsPage.cards())).as("columns at " + row).isEqualTo(row.columns());
    }

    @Test
    public void Should_NotScrollHorizontally_When_LoadedAtTheRowsWidth() {
        productsPage.open();

        assertThat(layout.horizontalOverflow()).as("overflow at " + row).isZero();
    }

    @Test
    public void Should_KeepFiltersBesideResults_When_LoadedAtTheRowsWidth() {
        productsPage.open();

        assertThat(layout.overlapDepth(productsPage.filters(), productsPage.results()))
                .as("overlap at " + row).isLessThanOrEqualTo(Layout.TOLERANCE_PX);
    }

    public record GridRow(String name, int width, int columns) {
    }
}
```

- `productsPage.open()` returns once the first card is visible, and the viewport is fixed for the whole test, so
  the measurement reads a settled layout; `.as(...)` carries the row into the failure.
- Alignment is the same shape:
  `assertThat(layout.leftEdgeSpread(List.of(form.title(), form.email(), form.submit()))).isLessThanOrEqualTo(Layout.TOLERANCE_PX)`.

## Live resize — the JS-breakpoint code path (idea #4)

```java
public class NavLiveResizeTest extends BaseTest {
    private AppShell appShell;
    private Layout layout;

    @Override
    protected Browser.NewContextOptions contextOptions() {
        return new Browser.NewContextOptions().setViewportSize(Breakpoints.LG, Breakpoints.HEIGHT);
    }

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        appShell = new AppShell(page);
        layout = new Layout(page);
    }

    @Test
    public void Should_ShowHamburgerNav_When_WindowShrinksBelowMd() {
        appShell.open();

        layout.resizeTo(Breakpoints.MD - 1);

        assertThat(appShell.nav(NavVariant.HAMBURGER)).isVisible();
        assertThat(appShell.nav(NavVariant.DESKTOP)).isHidden();
    }

    @Test
    public void Should_RestoreDesktopNav_When_WindowGrowsBackToLg() {
        appShell.open();
        layout.resizeTo(Breakpoints.MD - 1);
        assertThat(appShell.nav(NavVariant.HAMBURGER)).isVisible();

        layout.resizeTo(Breakpoints.LG);

        assertThat(appShell.nav(NavVariant.DESKTOP)).isVisible();
        assertThat(appShell.nav(NavVariant.HAMBURGER)).isHidden();
    }
}
```

The grow test asserts the shrink first only as its arrange step's completion signal — the web-first assertion
waits for the collapsed state before the resize back. After a resize, measure geometry only once a web-first
assertion on the new variant has passed.

## Anti-patterns

- **Hardcoding magic widths per test** (`setViewportSize(768, …)` scattered everywhere). Rots when design moves
  the breakpoint. *Fix:* one `Breakpoints` class mirroring the app's source; rows reference it.
- **Testing only representative widths** (375/768/1440) and skipping the boundaries. Misses every off-by-one in
  the media queries. *Fix:* bp−1 and bp per breakpoint.
- **`if (width < MD)` in the test body.** A branch hides which expectation ran. *Fix:* the row names what it
  must show (`shown` / `hidden`, `columns`).
- **`page.setViewportSize` at the top of every test.** Resizes a page loaded at another width — the live-resize
  path, not a fresh load. *Fix:* the viewport per class in `contextOptions()`; `resizeTo` only in live-resize tests.
- **Asserting absolute coordinates** (`box.x == 312`). *Fix:* relative geometry with `Layout.TOLERANCE_PX`.
- **Asserting only one side of a variant swap.** Both can render (duplicate DOM bugs). *Fix:* the shown variant
  visible **and** the other hidden.
- **`Thread.sleep`/`waitForTimeout` after a resize.** *Fix:* web-first assertions auto-wait; measure after one.
- **Screenshot-only coverage.** A pixel diff says *something* changed, not *what rule* broke. *Fix:* structural
  assertions here; `visual-regression` per viewport as the complement.
- **Testing breakpoints with device emulation.** Device options pin DPR/UA/touch. *Fix:* plain viewport for
  boundaries; device classes for device journeys.
- **Only testing shrink**, or a private `Playwright.create()`. *Fix:* resize both directions; extend `BaseTest`.

## Rules (hard constraints)

- **The breakpoint list lives in one `Breakpoints` class that mirrors the app's own definition** — no width
  literals in tests.
- **Every breakpoint gets a bp−1 / bp row pair** (fresh load at each); representative widths are additive.
- **Rows carry the expectation** (`shown`/`hidden`, `columns`); a test body never branches on the width.
- **Assertions are structural**: variant swap (both sides), relative geometry with tolerance, overflow `0`.
  Never absolute coordinates; never pixel diffs (that's `visual-regression`).
- **No horizontal overflow at any tested width** — the cheapest, highest-value responsive assertion.
- **Live-resize tests exist for resize-reachable surfaces**, resize both directions, and use web-first
  assertions — no `Thread.sleep`.
- **Viewport per class in `contextOptions()`**, rows through a `@Factory` — except the deliberate resize inside
  live-resize tests. Tests reach the page only through page objects and `Layout`.
- Every class extends `BaseTest`; no `@DataProvider(parallel = true)`; test names `Should_X_When_Y`; test ids
  PascalCase dot-separated (`Nav.Desktop`, `ProductGrid.Card`).

## Cross-references

- `qa-typescript:responsive-testing` · `qa-dotnet:responsive-testing` — sibling stacks; same four ideas.
- `qa-java:ui-tests-playwright` — `BaseTest`, the hooks (`lifecycle.md` §3) and the emulation reference
  (`emulation-and-mobile-web.md`: viewport per class, device profiles, media features).
- `qa-java:visual-regression` — the pixel complement: one baseline per viewport, after the structural checks pass.
- `qa-java:accessibility-testing` — reflow/zoom (WCAG 1.4.10) and touch targets; run them at the same widths.
- `qa-java:data-driven-testing` — the row pattern; here the rows feed a `@Factory` because each row needs its own
  context options.
- `frontend/react/skills/responsive-design` (FE peer) — the dev-side skill that defines the breakpoint contract
  this skill reads; its variant-suffixed test ids (`Nav.Desktop` / `Nav.Hamburger`) are what make the variant
  swap assertable. `frontend/blazor/skills/responsive-design` is the Blazor peer of the same contract.
