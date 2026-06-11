# Visual Regression — Applitools Eyes (TypeScript)

Applitools Eyes is the **visual-AI** layer of the visual-regression trio. It uploads the rendered page
to the **Ultrafast Grid**, re-renders it server-side across a configured browser/viewport/device
matrix, and diffs with **AI-based matching** that ignores the anti-aliasing and sub-pixel noise a human
wouldn't flag — plus **match levels** (Strict / Layout / Content / Ignore-colors) that let you say
"this region's *layout* must match but its *text* may change." That match-level control is the real
differentiator versus Percy's server-side **pixel** diff and the built-in **byte/pixel** diff
(`playwright-snapshots`).

This is an **assertion layer** on top of the page objects and specs the
`qa-ui-test-author-playwright-typescript` skill already authored. You do not write new page objects
here — you add `eyes.open` / `eyes.check` / `eyes.close` around an existing flow.

## Why graduate from Percy (pixel) to Applitools (visual-AI)

Percy already solved the cross-platform rendering problem by rendering server-side. Applitools
goes further on **how the diff is judged** and **how many environments render at once**:

| | Percy | **Applitools Eyes (this skill)** |
|---|---|---|
| What leaves the test | A DOM snapshot, uploaded by the `percy exec` agent | The rendered page, uploaded by the **SDK directly** (no agent) |
| How the diff is judged | Server-side **pixel** diff | Server-side **AI** match — ignores anti-aliasing / sub-pixel noise |
| Tolerance lever | `percyCSS` hide + `scope` (no pixel knob) | **Match levels** (Strict / Layout / Content / Ignore-colors) + region ignores |
| Dynamic content | Hide it with `percyCSS` | **`Target.layout(region)`** — structure matches, text may differ |
| Cross-browser/device | Re-renders at configured widths | **Ultrafast Grid** — a real browser/viewport/device **matrix** from one run |
| Process model | Local `percy exec` agent wraps the run | **None** — SDK calls the cloud; just `APPLITOOLS_API_KEY` in env |
| Baselines | Percy cloud, keyed by git branch, review UI | **Applitools dashboard**, keyed by app/test/branch, review UI |
| Gate | GitHub/GitLab status check | Runner's **aggregated results** fail the build; dashboard link |
| Cost | Paid | Paid (typically the most expensive of the three) |

State the contrast plainly: **Applitools is AI match (not pixel), match levels (not just hide-or-fail),
and a real cross-browser grid (not just widths)** — and there's **no agent process** to wrap the run.

## Setup

```bash
npm install --save-dev @applitools/eyes-playwright
```

`APPLITOOLS_API_KEY` is the **only secret**. The SDK reads it from the environment automatically — there
is **no agent to launch**, no `percy exec`-style wrapper; the SDK talks to the Applitools cloud directly.
In CI it comes from the secret store (see the ci-pipelines cross-link), never committed. Locally:

```bash
export APPLITOOLS_API_KEY=<your-api-key>   # never hardcode, never log
```

## The Eyes model + the Ultrafast Grid

Three objects, one lifecycle:

- **`VisualGridRunner`** — the runner that ships checkpoints to the **Ultrafast Grid**, which renders
  them server-side across your configured browser/viewport/device matrix. Construct it with a
  concurrency cap: `new VisualGridRunner({ testConcurrency: 5 })`. (Its sibling `ClassicRunner` renders
  locally with one environment — use `VisualGridRunner` to get the grid, which is the whole point of
  Applitools over `playwright-snapshots`/`percy`.)
- **`Eyes`** — one visual test session, bound to a runner: `new Eyes(runner)`. `eyes.open(page, app,
  test, viewport)` starts it; `eyes.check(...)` adds a checkpoint; `eyes.close(false)` ends it
  **without throwing inline**.
- **`runner.getAllTestResults(true)`** — called **once at suite end**, it blocks until every checkpoint
  across every `Eyes` has rendered + diffed on the grid, aggregates the results, and (with `true`)
  throws if any test had a mismatch or error. **This is the gate** — not `eyes.close`.

A `Configuration` with `addBrowser(width, height, BrowserType)` / `addDeviceEmulation(...)` is what
makes **one local run fan out to a cross-browser/device render matrix** server-side — the thing neither
`playwright-snapshots` nor `percy` does natively.

## Configuration — the render matrix

```typescript
// support/eyes-config.ts
import { Configuration, BrowserType, DeviceName, ScreenOrientation, BatchInfo } from '@applitools/eyes-playwright';

export function buildConfiguration(): Configuration {
  const config = new Configuration();
  // One batch groups every test in this run in the dashboard (see "Batching" below).
  config.setBatch(new BatchInfo({ name: 'FlexInvest Web — Visual' }));

  // Each addBrowser/addDeviceEmulation adds an environment the Ultrafast Grid renders + diffs.
  // One eyes.check() therefore produces N checkpoints — the cross-browser/device matrix.
  config.addBrowser(1280, 800, BrowserType.CHROME);
  config.addBrowser(1280, 800, BrowserType.FIREFOX);
  config.addBrowser(1280, 800, BrowserType.SAFARI);
  config.addBrowser(375, 812, BrowserType.EDGE_CHROMIUM);
  config.addDeviceEmulation(DeviceName.iPhone_11, ScreenOrientation.PORTRAIT);
  config.addDeviceEmulation(DeviceName.Pixel_5, ScreenOrientation.PORTRAIT);
  return config;
}
```

`eyes.setConfiguration(buildConfiguration())` before `eyes.open` applies it. The matrix lives in code,
in the repo — it's not a secret; only the API key is.

## Core pattern — `open` / `check` / `close` + `getAllTestResults`

The page object exposes intent; the test stabilizes **application** state on a condition, then checks.
No selectors in the test, no fixed waits. `eyes.close(false)` per test; the runner gates at suite end.

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
import { test } from '@playwright/test';
import { Eyes, VisualGridRunner, Target } from '@applitools/eyes-playwright';
import { buildConfiguration } from '../support/eyes-config';
import { DashboardPage } from '../pages/dashboard.page';

// One runner for the whole file (cap concurrency on the grid).
const runner = new VisualGridRunner({ testConcurrency: 5 });

test('Should_match_dashboard_When_loaded', async ({ page }) => {
  const eyes = new Eyes(runner);
  eyes.setConfiguration(buildConfiguration());     // API key read from env automatically
  await eyes.open(page, 'FlexInvest Web', 'Dashboard — revenue card', { width: 1280, height: 800 });

  try {
    const dashboard = new DashboardPage(page);
    await dashboard.goto();
    await dashboard.waitUntilLoaded();             // stabilize on a condition first…

    await eyes.check('Dashboard', Target.window().fully());  // …then capture the checkpoint
  } finally {
    await eyes.close(false);                        // end session WITHOUT throwing inline
  }
});

test.afterAll(async () => {
  // Blocks until the grid finishes; `true` throws if any test mismatched — THE GATE.
  await runner.getAllTestResults(true);
});
```

Why `eyes.close(false)` then `getAllTestResults(true)`: `close(true)` would throw the *first* time any
single test mismatches, aborting the rest before they render on the grid. Passing `false` lets every
test finish; the runner then aggregates **all** results and fails the build once, at suite end, with a
complete picture. Eyes captures **at `check` time**, like Percy — so stabilize before each `check`.

## Match levels — the real differentiator

A match level tells the AI *how* to compare a checkpoint against its baseline. Set it per-check via the
`Target` fluent API; this is the analogue of Percy's `percyCSS`-hide, but richer — prefer a **region
match level** over hiding the region entirely:

```typescript
await eyes.check('Account summary', Target.window().fully()
  // Whole-page level: Strict is the default ("looks the same to a human").
  .layout('[data-testid="balance-figures"]')   // structure must match; the NUMBERS may change
  .ignoreRegions('[data-testid="last-login"]') // ignore entirely (timestamp)
  .floating('[data-testid="toast"]', 5, 5, 5, 5)); // may shift up to 5px in any direction
```

The levels, precisely:

- **Strict** (default) — AI match: "would a human call these the same?" Ignores anti-aliasing /
  rendering noise but catches real visual changes. The right default for stable UI.
- **Layout** — only the **structure/position** of elements must match; their **content** (text,
  numbers, images) may differ. *The killer feature for dynamic data* — baseline a populated page once
  and it stays green as the data changes, while a broken layout still fails.
- **Content** — like Layout but also compares text content (structure + text, not exact pixels/colors).
- **Ignore-colors** — match structure + content but ignore color (theme/branding churn).

Region levels are the surgical version: `Target.window().fully().layout(locator)` keeps the page Strict
but treats one region as Layout. Region ignores — `.ignoreRegions(locator)` (drop entirely),
`.layoutRegions(locator)`, `.floating(locator, ...)` (element may shift within a pixel margin),
`.accessibility(locator, AccessibilityRegionType.LargeText)` (contrast checks) — are the analogue of
masking, but expressed as intent.

**There is no per-call pixel-ratio knob** (no `maxDiffPixelRatio` like `playwright-snapshots`). The AI plus the match
level *is* the tolerance lever. Reach for **Layout** before you reach for ignore.

## Batching + the dashboard

`BatchInfo` groups one run's tests under a single entry in the **Applitools dashboard** (set it on the
`Configuration`, as above). The dashboard is the hosted **baseline store + review UI** — the analogue
of Percy's. Baselines are keyed by **app / test / branch**; you accept or reject diffs there, and an
accept updates the baseline. Same "no in-repo baselines, no `-{platform}` naming" story as Percy: the
repo holds no PNGs.

To group a sharded CI run into one dashboard batch, set a stable `BATCH_ID` across shards:

```typescript
config.setBatch(new BatchInfo({
  name: 'FlexInvest Web — Visual',
  id: process.env.APPLITOOLS_BATCH_ID,   // same value across all shards → one batch
}));
```

## CI integration + the gate

There's **no agent to wrap the command** (the difference from Percy's `percy exec`): the SDK talks to
the cloud directly, so CI just runs the normal Playwright command with `APPLITOOLS_API_KEY` in env. The
build fails when `runner.getAllTestResults(true)` throws because an **unresolved diff** exists in the
dashboard.

```yaml
# inside your test job — see qa-ci-pipelines-typescript for the full pipeline
- name: Visual tests (Applitools)
  env:
    APPLITOOLS_API_KEY: ${{ secrets.APPLITOOLS_API_KEY }}   # from the secret store; never inline
    APPLITOOLS_BATCH_ID: ${{ github.run_id }}-${{ github.run_attempt }}  # one batch across shards
  run: npx playwright test
```

Link the dashboard batch URL into Allure so reviewers jump straight to it (cross-link
`qa-allure-reporting-typescript`):

```typescript
import { test } from '@playwright/test';
import { allure } from 'allure-playwright';

test.afterAll(async () => {
  const summary = await runner.getAllTestResults(false);     // false: don't throw here…
  const url = summary.getAllResults()[0]?.getTestResults()?.getAppUrls()?.getBatch();
  if (url) allure.link(url, 'Applitools dashboard', 'applitools');
  if (summary.getAllResults().some((r) => r.getException() || r.getTestResults()?.getStatus() === 'Unresolved')) {
    throw new Error('Applitools: unresolved visual diffs — review the dashboard batch.');  // …gate explicitly
  }
});
```

The review-UI workflow, concretely:
1. PR runs `playwright test`; the SDK uploads to the Ultrafast Grid, which renders + diffs against the
   branch baseline.
2. `getAllTestResults(true)` fails the build if any environment is **Unresolved** (new diff).
3. A reviewer accepts/rejects in the Applitools dashboard. Accepting updates the baseline.
4. On merge, the accepted checkpoints become the branch baseline for the next PR.

> **Shortcut:** the modern TS SDK (1.32+) also offers a fixture — `import { test } from
> '@applitools/eyes-playwright/fixture'` then `await eyes.check('Home', { fully: true, matchLevel:
> 'Layout' })` — which manages the runner/Eyes/batch for you. Prefer it for greenfield TS specs; the
> explicit `Eyes`/`VisualGridRunner` model shown above is the one that **ports identically to .NET and
> Java**, so it's the canonical structure here.

## Anti-patterns

- **`eyes.close(true)` (or `eyes.close()`) per test as the gate.** It throws on the first mismatch and
  aborts the rest before they render. *Fix:* `eyes.close(false)` per test; gate once at suite end with
  `runner.getAllTestResults(true)`.
- **Using `ClassicRunner` and expecting a cross-browser grid.** ClassicRunner renders one local
  environment. *Fix:* `VisualGridRunner` + `Configuration.addBrowser`/`addDeviceEmulation`.
- **`await page.waitForTimeout(500)` before `eyes.check`.** Eyes captures at call time; a sleep is
  flaky and slow. *Fix:* wait on a condition (`document.fonts.ready`, spinner hidden, `locator.waitFor`).
- **Hiding a dynamic region when Layout would do.** Ignoring drops coverage. *Fix:* `Target.layout(
  region)` — structure stays asserted, only content is allowed to vary.
- **Committing `*-snapshots/` PNGs alongside Applitools.** Baselines live in the dashboard. *Fix:*
  delete them; rely on the dashboard baseline.
- **Hardcoding / logging `APPLITOOLS_API_KEY`.** It's a write credential. *Fix:* env only, from the CI
  secret store, read lazily by the SDK, never echoed.
- **A new `BatchInfo` per shard.** Splits one run across many dashboard batches. *Fix:* one stable
  `BATCH_ID` env var shared across shards.
- **Full-page Strict checks on a page full of live data.** Chatty reviews. *Fix:* `Target.region(
  locator)` for the stable part, `layout`/`ignore` regions for the live bits.

## Examples

**End-to-end: a pricing-table visual gate across a browser/device grid, reviewed in the dashboard.**

```typescript
// tests/pricing.spec.ts
import { test } from '@playwright/test';
import { Eyes, VisualGridRunner, Target } from '@applitools/eyes-playwright';
import { buildConfiguration } from '../support/eyes-config';
import { PricingPage } from '../pages/pricing.page';

const runner = new VisualGridRunner({ testConcurrency: 5 });

test.describe('Pricing page visual regression (Applitools)', () => {
  test('Should_match_pricing_table_When_plans_loaded', async ({ page }) => {
    const eyes = new Eyes(runner);
    eyes.setConfiguration(buildConfiguration());
    await eyes.open(page, 'FlexInvest Web', 'Pricing — plan table', { width: 1280, height: 800 });

    try {
      const pricing = new PricingPage(page);
      await pricing.goto();
      await pricing.waitUntilPlansRendered();              // condition, not sleep
      await page.evaluate(() => document.fonts.ready);       // fonts settled before capture

      await eyes.check('Pricing table', Target.region('[data-testid="pricing-table"]')   // element, not full page
        .layout('[data-testid="promo-price"]')              // price A/B-tests → Layout, not ignore
        .ignoreRegions('[data-testid="promo-banner"]'));    // rotates daily → ignore entirely
    } finally {
      await eyes.close(false);                              // don't throw inline
    }
  });

  test.afterAll(async () => {
    await runner.getAllTestResults(true);                   // grid finishes → gate the build
  });
});
```

Lifecycle for this test:
1. Dev makes an intended CSS change to the pricing table.
2. CI runs `playwright test`; the SDK ships one checkpoint per configured browser/device to the grid,
   which renders + AI-diffs each vs the branch baseline.
3. `getAllTestResults(true)` fails the build; the dev reviews + accepts the diff in the dashboard
   (accepting it on **all** environments at once).
4. On merge, the accepted renders become the branch baseline — the next PR diffs against them.

## Rules (hard constraints)

- Visual regression is an assertion layer on existing page objects/specs — add `eyes.check`, don't
  author new page objects here. Page objects expose intent + locators; no selectors in tests.
- `VisualGridRunner` (not `ClassicRunner`) + `Configuration.addBrowser`/`addDeviceEmulation` — the grid
  is the reason to choose Applitools.
- `eyes.close(false)` per test (never inline-throw); gate **once** at suite end with
  `runner.getAllTestResults(true)`.
- Stabilize **application** state on a condition before `eyes.check`; never `waitForTimeout` — Eyes
  captures at call time.
- Prefer a **match level** (especially `Target.layout(region)`) over hiding dynamic content; there is
  **no per-call pixel-ratio knob** — the AI + match level is the lever.
- `APPLITOOLS_API_KEY` is the **only** secret: env-only, from the CI secret store, read lazily by the
  SDK, never logged or committed. No agent process to launch (unlike Percy's `percy exec`).
- No in-repo `*-snapshots/` baselines — baselines live in the **dashboard**, keyed by app/test/branch,
  managed via the review UI. One stable `BatchInfo` id across shards.
- The gate is the runner's **aggregated results**; link the dashboard batch URL into Allure.

## Cross-references

- `qa-visual-regression-dotnet` — same skill, .NET / NUnit (`Applitools.Playwright`,
  `Eyes.Check(Target.Window().Fully())`, `runner.GetAllTestResults(false)`).
- `qa-visual-regression-java` — same skill, Java / TestNG (`com.applitools:eyes-playwright-java5`,
  `eyes.check(Target.window().fully())`, `runner.getAllTestResults(false)`).
- `references/percy.md` — the **hosted pixel-diff** sibling: DOM-upload agent +
  server-side pixel diff + review UI. Applitools is the "graduate to visual-AI + match levels + grid" step.
- `references/playwright-snapshots.md` — the **free** sibling: in-repo baselines
  you diff yourself, with the CI-container discipline both Percy and Applitools remove.
- `qa-ui-test-author-playwright-typescript` — the page objects/specs `eyes.check` is called inside.
  Author the flow there; add the visual checkpoint here.
- `qa-ci-pipelines-typescript` — where `APPLITOOLS_API_KEY` is sourced (secrets/OIDC); no
  agent wrapper needed.
- `qa-allure-reporting-typescript` — link the Applitools dashboard batch URL into the report.
