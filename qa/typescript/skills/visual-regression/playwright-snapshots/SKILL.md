---
name: qa-visual-regression-playwright-snapshots-typescript
description: >-
  Pixel/snapshot visual regression in Playwright UI tests with TypeScript using the built-in
  screenshot assertions `toHaveScreenshot()` and `toMatchSnapshot()` — the no-extra-SaaS option.
  Use when a Playwright TypeScript test must catch unintended visual changes to a page or component,
  manage `*-snapshots/` baselines in-repo, tame rendering flakiness (`maxDiffPixels`,
  `maxDiffPixelRatio`, `threshold`, `animations`, `mask`, `stylePath`), or generate baselines inside
  the CI container so dev-Mac vs Linux-CI font rendering does not cause false diffs. Covers
  `--update-snapshots`, diff/actual/expected PNG artifacts, and the free-vs-paid decision.
  Do NOT use for: hosted baseline management + review UI (see qa-visual-regression-percy-typescript),
  visual-AI cross-browser diffing (see qa-visual-regression-applitools-typescript), the page
  objects/specs these assertions live inside (see qa-ui-test-author-playwright-typescript), .NET
  (see qa-visual-regression-playwright-snapshots-dotnet), or Java
  (see qa-visual-regression-playwright-snapshots-java).
---

# Visual Regression — Playwright Snapshots (TypeScript)

## When to use this skill

Use when a Playwright **TypeScript** test must detect **unintended visual change** — a CSS
regression, a broken layout, a shifted component — by comparing a fresh screenshot against a
committed baseline image. This is the **built-in, free** layer: Playwright does the capture and the
pixel diff, baselines live in your repo, and you own the flakiness budget. Reach for Percy (#18) or
Applitools (#19) only when you need hosted baseline management, a human review UI, or visual-AI
cross-browser diffing — see the decision matrix.

Visual regression is an **assertion layer** that sits *on top of* your existing page objects and
specs. You do not write new page objects here — you add a screenshot assertion to a flow the
`qa-ui-test-author-playwright-typescript` skill already authored.

## Decision matrix — which assertion, which tool

| Need | Use | Why |
|------|-----|-----|
| Visual diff of a page/element, auto-retried + stabilized | `await expect(page).toHaveScreenshot()` | The modern API: waits for the page to stop changing, retries until match or timeout |
| Visual diff of an element only | `await expect(locator).toHaveScreenshot()` | Scopes the capture; less flaky than full page |
| Compare an arbitrary buffer/string you produced | `expect(buffer).toMatchSnapshot('name.png')` | Raw snapshot of bytes you control (e.g. a generated PDF/SVG, a `screenshot()` you post-processed) |
| Free, baselines in your repo, you own diffing | **this skill** | No SaaS, no per-screenshot cost, full control |
| Hosted baselines + PR review UI + auto-approve flow | Percy (#18) | Offloads baseline mgmt + review; paid |
| Visual-AI diffing + cross-browser rendering grid | Applitools (#19) | Ignores anti-aliasing noise via AI; paid |

**Rule of thumb:** `toHaveScreenshot()` for anything rendered in the browser (it stabilizes and
retries). `toMatchSnapshot()` only for bytes/strings you generated yourself and want to pin. Prefer
**element** screenshots over **full-page** — they are dramatically less flaky.

## Setup

```bash
npm init playwright@latest
```

`playwright.config.ts` — set global screenshot defaults once so individual tests stay clean, and
make failures debuggable:

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  // Fail fast in CI; never write/update baselines implicitly on CI.
  forbidOnly: !!process.env.CI,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  expect: {
    toHaveScreenshot: {
      // Global flakiness budget — override per assertion when a region needs more/less tolerance.
      maxDiffPixelRatio: 0.01, // ≤1% of pixels may differ
      animations: 'disabled',  // freeze CSS animations/transitions for the shot
      scale: 'css',            // size in CSS pixels, stable across DPI
    },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
```

## Where baselines live & how they're named

On the first run, Playwright writes a baseline next to the spec, then compares against it on every
later run:

```
tests/
  dashboard.spec.ts
  dashboard.spec.ts-snapshots/
    revenue-card-chromium-linux.png      ← {name}-{projectName}-{platform}.png
```

The `-{platform}` suffix (`linux` / `darwin` / `win32`) is the crux of the **cross-platform
rendering problem**: a baseline generated on a dev Mac is named `...-darwin.png` and will **not** be
found — or worse, will subtly mismatch on font hinting/anti-aliasing — when CI runs on Linux. The
fix is below in "The CI baseline discipline". Commit the `*-snapshots/` directories to the repo:
**baselines are build artifacts under version control, not secrets.**

## Core pattern 1 — element screenshot on a page-object-driven flow

The page object exposes intent and the locator; the test adds the visual assertion. No selectors in
the test.

```typescript
// pages/dashboard.page.ts
import { type Page, type Locator } from '@playwright/test';

export class DashboardPage {
  readonly page: Page;
  readonly revenueCard: Locator;

  constructor(page: Page) {
    this.page = page;
    this.revenueCard = page.getByTestId('revenue-card');
  }

  async goto(): Promise<void> {
    await this.page.goto('/dashboard');
  }

  /** Resolves once the card's data has rendered — a condition, never a fixed wait. */
  async waitUntilLoaded(): Promise<void> {
    await this.revenueCard.getByRole('status').waitFor({ state: 'hidden' });
  }
}
```

```typescript
// tests/dashboard.spec.ts
import { test, expect } from '@playwright/test';
import { DashboardPage } from '../pages/dashboard.page';

test('Should_match_revenue_card_baseline_When_dashboard_loads', async ({ page }) => {
  const dashboard = new DashboardPage(page);
  await dashboard.goto();
  await dashboard.waitUntilLoaded();      // stabilize on a condition first…

  await expect(dashboard.revenueCard).toHaveScreenshot('revenue-card.png'); // …then assert (auto-retries)
});
```

`toHaveScreenshot()` auto-retries the capture+compare until it matches or the `expect` timeout
elapses, and it waits for fonts/animations to settle. You still stabilize *application* state
(data loaded, spinners gone) yourself — Playwright cannot know your spinner is "done".

## Core pattern 2 — taming flakiness

The four sources of false diffs and the deterministic fix for each:

```typescript
test('Should_match_profile_page_When_dynamic_regions_neutralized', async ({ page }) => {
  await page.goto('/profile');

  // 1) Fonts not yet rendered → wait on the condition, not a timeout.
  await page.evaluate(() => document.fonts.ready);

  // 2) Dynamic content (timestamps, avatars, ads) → mask it out (painted as a solid box).
  await expect(page).toHaveScreenshot('profile.png', {
    mask: [page.getByTestId('last-seen'), page.locator('img.gravatar')],
    maskColor: '#FF00FF',

    // 3) Anti-aliasing / sub-pixel noise → small tolerance. Prefer ratio over absolute.
    maxDiffPixelRatio: 0.02,
    // threshold is per-pixel color sensitivity (0 strict … 1 loose); default 0.2 is usually right.
    threshold: 0.2,

    // 4) Animations / carets → freeze them.
    animations: 'disabled',
    caret: 'hide',
  });
});
```

Knobs, precisely:

- **`maxDiffPixels`** — absolute number of differing pixels allowed. Brittle across viewport sizes.
- **`maxDiffPixelRatio`** — fraction (0–1) of differing pixels allowed. **Prefer this** — it scales
  with image size.
- **`threshold`** — per-pixel YIQ color-distance sensitivity (0 = exact, 1 = anything). Controls
  *whether a pixel counts as different at all* before the ratio/count is applied. Default `0.2`.
- **`mask` / `maskColor`** — overpaint dynamic regions so they can never diff.
- **`animations: 'disabled'`** — sets CSS animations/transitions to their end state.
- **`caret: 'hide'`** — hides the text input caret (a classic 1px flake).
- **`stylePath`** — inject a CSS file to hide/neutralize elements (e.g. `* { caret-color: transparent }`,
  hide live chat widgets) consistently across every screenshot.
- **`fullPage: true`** — capture the whole scrollable page (flakier; mask aggressively).
- **`clip`** — capture a fixed rectangle.

`stylePath` for repo-wide stabilization:

```typescript
// snapshot.css
*, *::before, *::after { transition: none !important; animation: none !important; }
[data-testid="live-clock"], .chat-widget { visibility: hidden !important; }
```

```typescript
expect: {
  toHaveScreenshot: { stylePath: './snapshot.css', animations: 'disabled', maxDiffPixelRatio: 0.01 },
},
```

## Core pattern 3 — `toMatchSnapshot()` for bytes you produced

Use only when you own the buffer/string — not for live page captures (those should use
`toHaveScreenshot()` so they stabilize and retry).

```typescript
test('Should_match_generated_invoice_pdf_baseline', async ({ page }) => {
  const pdf = await page.pdf({ format: 'A4' });
  expect(pdf).toMatchSnapshot('invoice.pdf'); // raw byte comparison; no stabilization
});
```

`toMatchSnapshot()` does **not** auto-retry and does **not** stabilize. For images it accepts the
same `threshold` / `maxDiffPixels` options, but for live pages `toHaveScreenshot()` is strictly
better.

## The CI baseline discipline (the part everyone gets wrong)

Baselines are platform-specific. The only reliable workflow:

1. **Never commit baselines generated on your dev box.** A `...-darwin.png` baseline is useless to a
   Linux runner.
2. **Generate/update baselines inside the same container CI uses.** Either run CI's Docker image
   locally, or run an update step in CI itself:

   ```bash
   # Reproduce CI's exact rendering locally via the official image (tag must match your @playwright/test version):
   docker run --rm --network host -v "$(pwd):/work" -w /work \
     mcr.microsoft.com/playwright:v1.50.0-noble \
     npx playwright test --update-snapshots
   ```

3. **`--update-snapshots` discipline.** Run it deliberately when a change is *intended*, review the
   resulting PNGs in the diff, and commit them in the same PR as the UI change. Never wire
   `--update-snapshots` into the normal test run — that makes every run "pass" by overwriting the
   baseline.

4. **Gate updates behind a manual/labelled CI job**, not a local push. See the github-actions
   cross-link below for the gated `update-baselines` job pattern.

On a normal CI failure Playwright emits three PNGs — `*-actual.png`, `*-expected.png`,
`*-diff.png` — into `test-results/`. Upload them as artifacts and attach to the report:

```yaml
# inside your test job (see qa-ci-pipelines-github-actions-typescript for the full pipeline)
- name: Upload visual diff artifacts
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: playwright-visual-diffs
    path: |
      test-results/**/*-actual.png
      test-results/**/*-expected.png
      test-results/**/*-diff.png
    retention-days: 7
```

Attach the diff into Allure so reviewers see it inline (cross-link `qa-allure-reporting-typescript`):

```typescript
import { test } from '@playwright/test';
import { allure } from 'allure-playwright';
import { readFileSync } from 'node:fs';

test.afterEach(async ({}, testInfo) => {
  if (testInfo.status !== testInfo.expectedStatus) {
    for (const a of testInfo.attachments) {
      if (a.name.includes('diff') && a.path) {
        allure.attachment('visual-diff', readFileSync(a.path), 'image/png');
      }
    }
  }
});
```

## Anti-patterns

- **Committing dev-box baselines.** `...-darwin.png` baselines fail or flake on Linux CI. Generate
  inside the CI container. *Fix:* the Docker/`--update-snapshots` workflow above.
- **`await page.waitForTimeout(500)` before the screenshot.** A fixed sleep is both flaky and slow.
  *Fix:* wait on a condition (`document.fonts.ready`, spinner hidden, `locator.waitFor`), then assert
  — `toHaveScreenshot()` auto-retries the rest.
- **Full-page screenshots of a page full of dynamic data.** Guaranteed flake. *Fix:* screenshot the
  **element** under test; `mask` the dynamic bits; use `stylePath` to neutralize globally.
- **Cranking `maxDiffPixelRatio` to 0.2 to "make it pass".** That blinds the test to real
  regressions. *Fix:* find the *specific* flaky region and `mask` it; keep the ratio tight (≤0.02).
- **Wiring `--update-snapshots` into the default test command.** Every run silently rewrites the
  baseline, so nothing is ever caught. *Fix:* update only via a deliberate, gated step.
- **Using `toMatchSnapshot()` for a live page.** No stabilization, no retry → flaky. *Fix:*
  `toHaveScreenshot()` for anything the browser renders.
- **Treating a baseline as a secret / `.gitignore`-ing `*-snapshots/`.** Then CI has nothing to
  compare against. *Fix:* commit baselines; they are versioned build artifacts.

## Examples

**End-to-end: a component visual gate that survives CI.**

```typescript
// tests/pricing.spec.ts
import { test, expect } from '@playwright/test';
import { PricingPage } from '../pages/pricing.page';

test.describe('Pricing table visual regression', () => {
  test('Should_match_pricing_table_baseline_When_plans_loaded', async ({ page }) => {
    const pricing = new PricingPage(page);
    await pricing.goto();
    await pricing.waitUntilPlansRendered();        // condition, not sleep
    await page.evaluate(() => document.fonts.ready); // fonts settled

    await expect(pricing.table).toHaveScreenshot('pricing-table.png', {
      mask: [pricing.promoBanner],   // rotates daily — never diff it
      maxDiffPixelRatio: 0.01,
      animations: 'disabled',
      caret: 'hide',
    });
  });
});
```

Baseline lifecycle for this test:
1. Dev makes an intended CSS change.
2. Runs `docker run … npx playwright test pricing.spec.ts --update-snapshots` in the CI image.
3. Reviews `pricing-table-chromium-linux.png` in the diff, commits it with the CSS change.
4. CI compares against it on every PR; an *unintended* change now fails with a `-diff.png` artifact.

## Rules (hard constraints)

- Stabilize **application** state on a condition before asserting; never `waitForTimeout`. Let
  `toHaveScreenshot()` auto-retry the rendering settle.
- Prefer **element** screenshots over full-page; `mask` every dynamic region.
- Prefer `maxDiffPixelRatio` (scales with size) over `maxDiffPixels`; keep tolerance tight and mask
  noise rather than loosening the budget.
- **Generate baselines inside the CI container**, never on the dev box. Baselines are committed,
  versioned build artifacts — not secrets, not `.gitignore`-d.
- `--update-snapshots` is a deliberate, reviewed, gated action — never part of the default test run.
- On failure, upload `*-actual/-expected/-diff.png` as artifacts and attach the diff to the report.
- `toHaveScreenshot()` for browser-rendered content; `toMatchSnapshot()` only for bytes you produced.
- Page objects expose intent + locators; the test owns the visual assertion. No selectors in tests.

## Cross-references

- `qa-visual-regression-playwright-snapshots-dotnet` — same skill, .NET / NUnit
  (`Expect(...).ToHaveScreenshotAsync()`).
- `qa-visual-regression-playwright-snapshots-java` — same skill, Java / TestNG
  (`assertThat(page).hasScreenshot()`).
- `qa-ui-test-author-playwright-typescript` — the page objects/specs these assertions layer on top
  of. Author the flow there; add the visual gate here.
- `qa-visual-regression-percy-typescript` (#18, next) — hosted baseline management + PR review UI
  when in-repo baselines become a bottleneck.
- `qa-visual-regression-applitools-typescript` (#19) — visual-AI diffing + cross-browser rendering
  grid.
- `qa-ci-pipelines-github-actions-typescript` — artifact upload, the container-baseline discipline,
  and the gated `update-baselines` job.
- `qa-allure-reporting-typescript` — attach `-diff.png` images to the test report.
