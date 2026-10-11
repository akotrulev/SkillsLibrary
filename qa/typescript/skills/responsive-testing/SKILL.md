---
name: responsive-testing
description: Use when testing responsive layout/breakpoint behavior in TypeScript with Playwright — drive the viewport across the app's real CSS breakpoints (read from its token/theme source, never guessed), assert the layout variant at breakpoint−1 and breakpoint (BVA), verify geometry via bounding boxes. Triggers: "test the responsive design", "assert the nav collapses to a hamburger", "test around the breakpoints". Do NOT use for pixel-diff screenshots (qa-typescript:visual-regression).
---

# QA — Responsive / Breakpoint Testing (TypeScript / Playwright 1.64)

Tests that a web app's layout **adapts correctly across viewport widths**: the right layout variant renders on
each side of every CSS breakpoint, related elements stay aligned with each other when the breakpoint flips, and
nothing overflows. The assertions are **structural** (visibility swaps, bounding-box geometry, overflow math) —
pixel-level diffing is `visual-regression`'s job and pairs with this skill, it doesn't replace it.

This skill pins nothing. The Playwright version is the **Versions** table of
`qa/typescript/skills/ui-test-author/playwright/SKILL.md`. Viewport, device and `screen` mechanics are
`qa/typescript/skills/ui-test-author/playwright/references/emulation-and-mobile-web.md`; this skill owns the
breakpoint coverage that reference hands over.

> **The discipline this skill encodes** — four ideas that separate a correct responsive test from resizing and
> eyeballing:
>
> 1. **Breakpoints come from the app's source — never guessed, never duplicated per spec.** The breakpoint list
>    is test data, read from the one place the app defines it: the Tailwind config / `@theme` block, the MUI
>    theme, Bootstrap's `$grid-breakpoints`, or the CSS custom-property token file. Export it once as a
>    `BREAKPOINTS` module and drive every row from it — a hardcoded `768` in a spec silently rots the day
>    design changes the breakpoint.
> 2. **Test the boundary, not the middle — BVA on the media query.** A `@media (min-width: 768px)` rule is a
>    boundary: at **767 px** the mobile layout must hold, at **768 px** the desktop layout must have taken over.
>    Two-value boundary analysis per breakpoint (bp−1, bp) catches the off-by-one (`min-width` vs `max-width`
>    overlap/gap bugs) that a "test at 375/768/1440" matrix sails past. Representative in-range widths are the
>    *smoke* layer on top, not the substitute.
> 3. **Assert structure, not pixels.** Three assertion families, all robust to content changes: **variant swap**
>    (hamburger visible + full nav hidden, grid renders 3 columns vs 1 — derived from bounding-box rows);
>    **relative geometry** (children share a left edge, sibling boxes don't overlap) via `boundingBox()`
>    measurements with a small tolerance — never absolute coordinates; **overflow** (no horizontal scroll:
>    `scrollWidth - clientWidth` on the document is `0`).
> 4. **Fresh-load and live-resize are different code paths — test both where both happen.** CSS media queries
>    respond to a live resize, but JS breakpoint logic (`matchMedia` listeners, resize handlers, JS-chosen
>    component variants) may only run on load — or break only on live resize. Default to **loading at the
>    target viewport** (`test.use({ viewport })` per row, or a project per viewport class); add explicit
>    **live-resize** tests for surfaces users actually resize (desktop window drag, orientation flip),
>    asserting with web-first assertions after the resize — never `waitForTimeout`.

## Decision matrix — responsive surface → test shape

| Surface | What you're proving | Test shape |
|---------|---------------------|------------|
| **Layout variant per breakpoint** | The right structure renders on each side of the boundary | One row per width (bp−1, bp) naming the variant shown and the one hidden → `toBeVisible` / `toBeHidden` |
| **Element alignment** | Related elements stay aligned when the breakpoint flips | `Layout.leftEdgeSpread(...)` ≤ tolerance, at each boundary width |
| **Grid/column reflow** | Cards go 3-col → 2-col → 1-col at the right widths | Rows carry `columns`; `expect.poll(() => layout.columnCount(cards))` |
| **No overflow / no clipping** | Nothing forces a horizontal scrollbar | `Layout.horizontalOverflow()` is `0` |
| **Live resize / rotation** | JS breakpoint logic reacts to a real resize | Load wide → `layout.resizeTo(narrow)` → web-first assert the swap (and back) |
| **Whole-page look per viewport** | Everything the structural checks can't name | Hand off: `qa-typescript:visual-regression`, one baseline per viewport project |
| **Real mobile UX (touch, DPR, UA)** | Device behavior, not CSS breakpoints | Device projects in `emulation-and-mobile-web.md` §1–§2; real devices → `qa/typescript/skills/device-cloud` |

## Stack

- Node 24 (22 maintenance) + TypeScript (strict mode), **Playwright Test**, on the writer's fixtures
  (`qa/typescript/skills/ui-test-author/playwright/assets/fixtures.ts`)
- **The app's own breakpoint source** — imported or mirrored into one `BREAKPOINTS` module (the analogue of
  language-testing's supported-locale list). Where the app defines them:

| App uses | Breakpoints live in | Defaults (px) |
|---|---|---|
| Tailwind | `tailwind.config` `screens` / v4 `@theme` | sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1536 |
| Material UI (MUI) | `theme.breakpoints.values` | sm 600 · md 900 · lg 1200 · xl 1536 |
| Bootstrap 5 | `$grid-breakpoints` | sm 576 · md 768 · lg 992 · xl 1200 · xxl 1400 |
| MudBlazor (Blazor SUT) | `MudGlobal`/theme breakpoints | sm 600 · md 960 · lg 1280 · xl 1920 |
| Bespoke CSS | the tokens file / one `breakpoints.css` | whatever it says — read it |

- Viewport set with **`test.use({ viewport })` inside a `describe` per row**, or a project per viewport class —
  never `setViewportSize` per test except in explicit live-resize specs (`emulation-and-mobile-web.md` §3)
- A fixed height per class (720) — width is the variable under test; height only matters for fold checks
- **1.64:** a `devices[...]` project now forwards `screen` too. `test.use({ viewport })` changes only the
  viewport, so an app whose media queries read `device-width` or `window.screen` also needs `screen` set to the
  same size in that `test.use`

```typescript
export const BREAKPOINTS = { sm: 640, md: 768, lg: 1024, xl: 1280 } as const;
export type BreakpointName = keyof typeof BREAKPOINTS;
export const HEIGHT = 720;
```

`breakpoints.ts` is the one place widths live, mirroring the app's source.

## The fixtures — page objects and a measuring helper

`responsive.fixtures.ts` extends the writer's fixtures with two page objects and `Layout` — the full file is
[`references/fixtures.md`](references/fixtures.md). Page objects expose variant intent
(`appShell.nav('Hamburger')` → `getByTestId('Nav.Hamburger')`), never boxes. `Layout` **measures and returns
numbers** — `columnCount(cards)`, `horizontalOverflow()`, `leftEdgeSpread([...])`, `overlapDepth(a, b)` —
plus `resizeTo(width)` for live-resize specs. The test asserts; a helper never does, so the report shows the
measured value. Test ids are the PascalCase ids `fe-react`'s responsive-design skill generates
(`Nav.Desktop` / `Nav.Hamburger`).

## Boundary rows — the core pattern

Each row states the width **and** what that width must show. The test body has no branch: one `describe` per
row sets the viewport, and the row's expected values are the assertion's operands.

```typescript
import { BREAKPOINTS, HEIGHT } from './breakpoints';
import { expect, test } from './responsive.fixtures';

const navRows = [
  { name: 'BelowMd', width: BREAKPOINTS.md - 1, shown: 'Hamburger', hidden: 'Desktop' },
  { name: 'AtMd', width: BREAKPOINTS.md, shown: 'Desktop', hidden: 'Hamburger' },
] as const;

for (const row of navRows) {
  test.describe(`${row.name} (${row.width}px)`, () => {
    test.use({ viewport: { width: row.width, height: HEIGHT } });

    test(`Should_ShowOnly${row.shown}Nav_When_Width${row.name}`, async ({ appShell }) => {
      await appShell.open();

      await expect(appShell.nav(row.shown)).toBeVisible();
      await expect(appShell.nav(row.hidden)).toBeHidden();
    });
  });
}
```

`nav.responsive.spec.ts`. The swap is exclusive, so both sides are asserted: one behaviour, two expectations.
The `for` generates one independent, individually-named test per row — it is outside every test body, which
is the sanctioned parameterization (`qa-typescript:data-driven-testing`).

## Geometry rows — reflow, overflow, alignment

```typescript
import { BREAKPOINTS, HEIGHT } from './breakpoints';
import { expect, TOLERANCE_PX, test } from './responsive.fixtures';

const gridRows = [
  { name: 'BelowMd', width: BREAKPOINTS.md - 1, columns: 1 },
  { name: 'AtMd', width: BREAKPOINTS.md, columns: 2 },
  { name: 'BelowLg', width: BREAKPOINTS.lg - 1, columns: 2 },
  { name: 'AtLg', width: BREAKPOINTS.lg, columns: 3 },
] as const;

for (const row of gridRows) {
  test.describe(`${row.name} (${row.width}px)`, () => {
    test.use({ viewport: { width: row.width, height: HEIGHT } });

    test(`Should_Show${row.columns}Columns_When_Width${row.name}`, async ({ productsPage, layout }) => {
      await productsPage.open();

      await expect.poll(() => layout.columnCount(productsPage.cards)).toBe(row.columns);
    });

    test(`Should_NotScrollHorizontally_When_Width${row.name}`, async ({ productsPage, layout }) => {
      await productsPage.open();

      await expect.poll(() => layout.horizontalOverflow()).toBe(0);
    });

    test(`Should_KeepFiltersBesideResults_When_Width${row.name}`, async ({ productsPage, layout }) => {
      await productsPage.open();

      await expect.poll(() => layout.overlapDepth(productsPage.filters, productsPage.results)).toBeLessThanOrEqual(TOLERANCE_PX);
    });
  });
}
```

- `expect.poll` re-measures until the layout settles — the geometry analogue of a web-first assertion.
- Alignment is the same shape:
  `expect.poll(() => layout.leftEdgeSpread([form.title, form.email, form.submit])).toBeLessThanOrEqual(TOLERANCE_PX)`.
- `scrollWidth` is never below `clientWidth`, so `0` is the one expected overflow.

## Live resize — the JS-breakpoint code path (idea #4)

```typescript
import { BREAKPOINTS, HEIGHT } from './breakpoints';
import { expect, test } from './responsive.fixtures';

test.describe('live resize from AtLg', () => {
  test.use({ viewport: { width: BREAKPOINTS.lg, height: HEIGHT } });

  test('Should_ShowHamburgerNav_When_WindowShrinksBelowMd', async ({ appShell, layout }) => {
    await appShell.open();

    await layout.resizeTo(BREAKPOINTS.md - 1);

    await expect(appShell.nav('Hamburger')).toBeVisible();
    await expect(appShell.nav('Desktop')).toBeHidden();
  });

  test('Should_RestoreDesktopNav_When_WindowGrowsBackToLg', async ({ appShell, layout }) => {
    await appShell.open();
    await layout.resizeTo(BREAKPOINTS.md - 1);
    await expect(appShell.nav('Hamburger')).toBeVisible();

    await layout.resizeTo(BREAKPOINTS.lg);

    await expect(appShell.nav('Desktop')).toBeVisible();
    await expect(appShell.nav('Hamburger')).toBeHidden();
  });
});
```

The grow test asserts the shrink first only as its arrange step's completion signal — the web-first assertion
waits for the collapsed state before the resize back, so the test never grows a page that had not yet shrunk.

## Anti-patterns

- **Hardcoding magic widths per spec** (`setViewportSize({ width: 768 })` scattered everywhere). Rots when
  design moves the breakpoint. *Fix:* one `BREAKPOINTS` module mirroring the app's source; rows import it.
- **Testing only representative widths** (375/768/1440) and skipping the boundaries. Misses every off-by-one in
  the media queries — the exact bug class responsive testing exists for. *Fix:* bp−1 and bp per breakpoint.
- **Choosing the assertion inside the test** (`if (width < md) { … } else { … }`, a ternary computing the
  expected column count). *Fix:* the row carries the expected variant and count; the body has no branch.
- **`setViewportSize` at the top of every test.** It loads at the default size first and hides fresh-load
  bugs. *Fix:* `test.use({ viewport })` per row `describe`; `resizeTo` only in live-resize specs.
- **Asserting absolute coordinates** (`expect(box.x).toBe(312)`). Breaks on any content, font, or scrollbar
  change. *Fix:* relative geometry — edge spread, overlap depth, column count — with a 1px tolerance.
- **Asserting inside a geometry helper** (`for (const x of xs) expect(…)`, `expect(separated).toBe(true)`).
  The failure loses the measurements and runs assertions in a loop. *Fix:* the helper returns a number; the
  test asserts it, so the report shows the measured value.
- **Asserting only one side of a variant swap.** The hamburger being visible doesn't prove the desktop nav is
  gone — both can render (duplicate DOM bugs). *Fix:* assert visible **and** the counterpart hidden.
- **`waitForTimeout` after a resize.** Flaky and slow. *Fix:* web-first assertions (`toBeVisible`/`toBeHidden`
  auto-wait); for raw geometry, `expect.poll` on the measurement.
- **Testing breakpoints with device profiles** (`devices['iPhone 15']`). Profiles pin DPR/UA/touch/screen —
  right for mobile UX, wrong for isolating a CSS boundary (the width isn't at your breakpoint). *Fix:* plain
  viewport rows for boundaries; device projects for device journeys.
- **Only testing shrink.** Grow paths (mobile → desktop) exercise different listener/state code. *Fix:* a
  live-resize test in each direction.

## Rules (hard constraints)

- **The breakpoint list is imported from one module that mirrors the app's own definition** — no width literals
  in specs.
- **Every breakpoint gets a bp−1 / bp boundary row** (fresh load at each); representative widths are additive.
- **Rows carry the expectation** (`shown`/`hidden`, `columns`); a test body never branches on the width.
- **Assertions are structural**: variant swap (both sides), relative geometry with tolerance, overflow `0`.
  Helpers measure, tests assert. Never absolute coordinates; never pixel diffs (that's `visual-regression`).
- **No horizontal overflow at any tested width** — the cheapest, highest-value responsive assertion; one test
  per row.
- **Live-resize specs exist for resize-reachable surfaces**, resize in both directions, and use web-first
  assertions — no `waitForTimeout`.
- **Viewport is configured** (`test.use` per row, or a project) — except the deliberate resize inside
  live-resize specs. Tests reach the page only through page objects and the `Layout` fixture.
- Test names are `Should_X_When_Y`; one logical assertion per test; `strict: true`.

## Cross-references

- `qa-java:responsive-testing` · `qa-dotnet:responsive-testing` — sibling stacks (Playwright-Java + TestNG ·
  Playwright .NET + NUnit); same four ideas, different APIs.
- `qa-typescript:ui-tests-playwright` — the fixtures this extends, and
  `references/emulation-and-mobile-web.md` for viewport, `screen`, device projects and media features.
- `qa-typescript:visual-regression` — the pixel complement: one baseline per viewport project, after the
  structural checks pass.
- `qa-typescript:accessibility-testing` — reflow/zoom (WCAG 1.4.10) and touch-target sizes at mobile widths
  overlap with a11y scans; run them at the same widths.
- `qa-typescript:data-driven-testing` — the breakpoint rows are its row-binding pattern applied to widths.
- `frontend/react/skills/responsive-design` (`fe-react:responsive-design`, the FE peer) — the dev-side skill
  that defines the breakpoint contract this skill reads; its variant-suffixed test ids (`Nav.Desktop` /
  `Nav.Hamburger`) are what make the variant swap assertable.
