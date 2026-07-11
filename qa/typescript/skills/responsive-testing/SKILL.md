---
name: qa-responsive-testing-typescript
description: Use when testing responsive layout/breakpoint behavior in Node 20 / TypeScript with Playwright — drive the viewport across the app's real CSS breakpoints (read from its Tailwind/MUI/token source, never guessed), assert the layout variant at breakpoint−1 and breakpoint (BVA on the media-query boundary), and verify structural geometry via boundingBox (alignment, containment, no overlap, no horizontal overflow). Triggers: "test the responsive design", "shrink the browser and check the layout", "assert the nav collapses to a hamburger", "elements misalign on tablet", "test around the breakpoints". Do NOT use for pixel-diff screenshots (use qa-visual-regression-typescript — pairs with this), real-device mobile web UX (device profiles in ui-test-author/playwright), native apps (qa-mobile-typescript), or RTL/locale layout (qa-i18n-testing-typescript).
---

# QA — Responsive / Breakpoint Testing (TypeScript / Playwright)

Tests that a web app's layout **adapts correctly across viewport widths**: the right layout variant renders on
each side of every CSS breakpoint, related elements stay aligned with each other when the breakpoint flips, and
nothing overflows. The assertions are **structural** (visibility swaps, bounding-box geometry, overflow math) —
pixel-level diffing is `visual-regression`'s job and pairs with this skill, it doesn't replace it.

> **The discipline this skill encodes** — four ideas that separate a correct responsive test from resizing and
> eyeballing:
>
> 1. **Breakpoints come from the app's source — never guessed, never duplicated per spec.** The breakpoint list
>    is test data, read from the one place the app defines it: the Tailwind config / `@theme` block, the MUI or
>    MudBlazor theme, Bootstrap's `$grid-breakpoints`, or the CSS custom-property token file. Export it once as a
>    `BREAKPOINTS` module and drive every matrix from it — a hardcoded `768` in a spec silently rots the day
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
>    at the target viewport** (viewport set in the project/`test.use`, one project per viewport class); add
>    explicit **live-resize** tests for surfaces users actually resize (desktop window drag, orientation flip),
>    asserting with web-first assertions after the resize — never `waitForTimeout`.

## Decision matrix — responsive surface → test shape

| Surface | What you're proving | Test shape |
|---------|---------------------|------------|
| **Layout variant per breakpoint** | The right structure renders on each side of the boundary | Navigate at bp−1 and bp → assert the variant marker (`toBeVisible`/`toBeHidden` on nav/hamburger/drawer) |
| **Element alignment** | Related elements stay aligned when the breakpoint flips | `boundingBox()` — equal left edges / tops within tolerance, at each boundary width |
| **Grid/column reflow** | Cards go 3-col → 2-col → 1-col at the right widths | Group card boxes by `y` → assert row lengths per width |
| **No overflow / no clipping** | Nothing forces a horizontal scrollbar or escapes its container | `scrollWidth <= clientWidth`; child box within parent box |
| **Live resize / rotation** | JS breakpoint logic reacts to a real resize | Load wide → `setViewportSize` narrow → web-first assert the swap (and back) |
| **Whole-page look per viewport** | Everything the structural checks can't name | Hand off: `qa-visual-regression-typescript`, one baseline per viewport project |
| **Real mobile UX (touch, DPR, UA)** | Device behavior, not CSS breakpoints | `devices['iPhone 15']` profiles in `ui-test-author/playwright` — out of scope here |

## Stack

- Node 20 + TypeScript (strict mode), **Playwright Test**
- **The app's own breakpoint source** — imported or mirrored into one `BREAKPOINTS` module (the analogue of
  i18n-testing's supported-locale list). Where the app defines them:

| App uses | Breakpoints live in | Defaults (px) |
|---|---|---|
| Tailwind | `tailwind.config` `screens` / v4 `@theme` | sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1536 |
| Material UI (MUI) | `theme.breakpoints.values` | sm 600 · md 900 · lg 1200 · xl 1536 |
| Bootstrap 5 | `$grid-breakpoints` | sm 576 · md 768 · lg 992 · xl 1200 · xxl 1400 |
| MudBlazor (Blazor SUT) | `MudGlobal`/theme breakpoints | sm 600 · md 960 · lg 1280 · xl 1920 |
| Bespoke CSS | the tokens file / one `breakpoints.css` | whatever it says — read it |

- Viewport set via **Playwright projects** (one per viewport class) or `test.use({ viewport })` — never
  `setViewportSize` scattered per test except in explicit live-resize specs
- A fixed height per class (e.g. 720) — width is the variable under test; height only matters for fold checks

```typescript
// tests/responsive/breakpoints.ts — the ONE place widths live (mirror of the app's source)
export const BREAKPOINTS = { sm: 640, md: 768, lg: 1024, xl: 1280 } as const;
export type BreakpointName = keyof typeof BREAKPOINTS;

/** BVA pair for a min-width breakpoint: last width BELOW it, first width AT it. */
export const around = (bp: BreakpointName) =>
  [ { name: `${bp}-1`, width: BREAKPOINTS[bp] - 1 }, { name: bp, width: BREAKPOINTS[bp] } ] as const;
```

## Boundary matrix — the core pattern

```typescript
// tests/specs/nav.responsive.spec.ts
import { test, expect } from '@playwright/test';
import { BREAKPOINTS, around } from '../responsive/breakpoints';

for (const { name, width } of around('md')) {
  test(`nav renders the ${width < BREAKPOINTS.md ? 'hamburger' : 'full'} variant at ${name} (${width}px)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 720 });
    await page.goto('/');                                   // fresh load AT the width (idea #4)

    const fullNav = page.getByTestId('nav-desktop');
    const hamburger = page.getByTestId('nav-hamburger');
    if (width < BREAKPOINTS.md) {
      await expect(hamburger).toBeVisible();
      await expect(fullNav).toBeHidden();                   // the swap is exclusive — assert BOTH sides
    } else {
      await expect(fullNav).toBeVisible();
      await expect(hamburger).toBeHidden();
    }
  });
}
```

## Geometry assertions — alignment, reflow, overlap

```typescript
// tests/responsive/layout.ts — reusable structural helpers
import { expect, type Locator, type Page } from '@playwright/test';

const TOLERANCE = 1; // sub-pixel rendering — never assert exact coordinates

export async function expectLeftAligned(locators: Locator[]) {
  const xs = await Promise.all(locators.map(async (l) => (await l.boundingBox())!.x));
  for (const x of xs) expect(Math.abs(x - xs[0])).toBeLessThanOrEqual(TOLERANCE);
}

/** Cards grouped into visual rows by their y coordinate → column count per row. */
export async function columnCount(cards: Locator): Promise<number> {
  const boxes = await Promise.all((await cards.all()).map(async (c) => (await c.boundingBox())!));
  const firstRowY = Math.min(...boxes.map((b) => b.y));
  return boxes.filter((b) => Math.abs(b.y - firstRowY) <= TOLERANCE).length;
}

export async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, 'page must not scroll horizontally').toBeLessThanOrEqual(0);
}

export async function expectNoOverlap(a: Locator, b: Locator) {
  const [ba, bb] = await Promise.all([a.boundingBox(), b.boundingBox()]);
  const separated =
    ba!.x + ba!.width <= bb!.x + TOLERANCE || bb!.x + bb!.width <= ba!.x + TOLERANCE ||
    ba!.y + ba!.height <= bb!.y + TOLERANCE || bb!.y + bb!.height <= ba!.y + TOLERANCE;
  expect(separated, 'elements must not overlap').toBe(true);
}
```

```typescript
// grid reflow across every breakpoint, one data-driven body
for (const [bp, expectedCols] of [['sm', 1], ['md', 2], ['lg', 3]] as const) {
  for (const { name, width } of around(bp)) {
    test(`product grid at ${name} (${width}px)`, async ({ page }) => {
      await page.setViewportSize({ width, height: 720 });
      await page.goto('/products');
      const cards = page.getByTestId('product-card');
      await expect(cards.first()).toBeVisible();
      expect(await columnCount(cards)).toBe(width < BREAKPOINTS[bp] ? Math.max(1, expectedCols - 1) : expectedCols);
      await expectNoHorizontalOverflow(page);
    });
  }
}
```

## Live resize — the JS-breakpoint code path (idea #4)

```typescript
test('nav swaps to hamburger on live shrink and back on grow', async ({ page }) => {
  await page.setViewportSize({ width: BREAKPOINTS.lg, height: 720 });
  await page.goto('/');
  await expect(page.getByTestId('nav-desktop')).toBeVisible();

  await page.setViewportSize({ width: BREAKPOINTS.md - 1, height: 720 });   // shrink across the boundary
  await expect(page.getByTestId('nav-hamburger')).toBeVisible();            // web-first assertion waits — no sleep
  await expect(page.getByTestId('nav-desktop')).toBeHidden();

  await page.setViewportSize({ width: BREAKPOINTS.lg, height: 720 });       // and back — resize listeners leak state
  await expect(page.getByTestId('nav-desktop')).toBeVisible();
});
```

## Anti-patterns

- **Hardcoding magic widths per spec** (`setViewportSize({ width: 768 })` scattered everywhere). Rots when
  design moves the breakpoint. *Fix:* one `BREAKPOINTS` module mirroring the app's source; specs import it.
- **Testing only representative widths** (375/768/1440) and skipping the boundaries. Misses every off-by-one in
  the media queries — the exact bug class responsive testing exists for. *Fix:* bp−1 and bp per breakpoint.
- **Asserting absolute coordinates** (`expect(box.x).toBe(312)`). Breaks on any content, font, or scrollbar
  change. *Fix:* relative geometry — equal edges, containment, non-overlap, with a 1px tolerance.
- **Asserting only one side of a variant swap.** The hamburger being visible doesn't prove the desktop nav is
  gone — both can render (duplicate DOM bugs). *Fix:* assert visible **and** the counterpart hidden.
- **`waitForTimeout` after a resize.** Flaky and slow. *Fix:* web-first assertions (`toBeVisible`/`toBeHidden`
  auto-wait); for raw geometry, `expect.poll` on the measurement.
- **Screenshot-only responsive coverage.** A pixel diff says *something* changed, not *what rule* broke, and it
  drowns in noise per viewport. *Fix:* structural assertions here; `visual-regression` per viewport as the
  complement.
- **Testing breakpoints with device profiles** (`devices['iPhone 15']`). Profiles pin DPR/UA/touch — great for
  mobile UX, wrong for isolating a CSS boundary (the width isn't at your breakpoint). *Fix:* plain viewport for
  boundaries; device profiles for device journeys.
- **Only testing shrink.** Grow paths (mobile → desktop) exercise different listener/state code and un-collapse
  logic. *Fix:* resize both directions in the live-resize spec.

## Rules (hard constraints)

- **The breakpoint list is imported from one module that mirrors the app's own definition** — no width literals
  in specs.
- **Every breakpoint gets a bp−1 / bp boundary pair** (fresh load at each); representative widths are additive.
- **Assertions are structural**: variant swap (both sides), relative bounding-box geometry with tolerance,
  overflow math. Never absolute coordinates; never pixel diffs (that's `visual-regression`).
- **No horizontal overflow at any tested width** — the cheapest, highest-value responsive assertion; run it in
  every responsive spec.
- **Live-resize specs exist for resize-reachable surfaces**, resize both directions, and use web-first
  assertions — no `waitForTimeout`.
- **Viewport is configured** (project / `test.use`), not improvised — except the deliberate resize inside
  live-resize specs.
- One logical assertion per test; data-driven iteration over breakpoints (`qa-data-driven-testing-typescript`
  pattern), never copy-pasted specs; `strict: true`.

## Cross-references

- `qa-responsive-testing-java` · `qa-responsive-testing-dotnet` — sibling stacks (Playwright-Java + TestNG ·
  Playwright .NET + NUnit); same four ideas, different APIs.
- `qa-ui-test-author-playwright-typescript` — base fixture/POM conventions; responsive adds the width dimension.
  Page objects expose variant intent (`navigation().isCollapsed()`), not boxes — geometry helpers live beside
  the specs.
- `qa-visual-regression-typescript` — the pixel complement: one baseline per viewport project, after the
  structural checks pass.
- `qa-accessibility-testing-typescript` — reflow/zoom (WCAG 1.4.10) and touch-target sizes at mobile widths
  overlap with a11y scans; run them at the same widths.
- `qa-data-driven-testing-typescript` — the breakpoint matrix is its row-binding pattern applied to widths.
- `frontend/blazor/skills/responsive-design` (FE peer) — the dev-side skill that defines the breakpoint contract
  this skill reads; its testid rules (variant-suffixed `nav-desktop`/`nav-hamburger`) are what make the variant
  swap assertable.
