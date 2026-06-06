---
name: qa-visual-regression-percy-typescript
description: >-
  Hosted visual regression for Playwright UI tests in TypeScript using Percy (by BrowserStack):
  `@percy/cli` + `@percy/playwright`, `percySnapshot(page, name, options)` run under
  `percy exec -- <test cmd>`. Use when visual baselines should live in Percy's cloud with a web
  review UI (approve/reject, auto-approve on the base branch, git-branch baseline tracking) and
  diffing happens server-side after a DOM-snapshot upload — so the dev-Mac-vs-Linux-CI rendering
  problem that dominates the built-in snapshots skill disappears. Covers `PERCY_TOKEN` (the only
  secret, env, read lazily), `.percy.yml` (widths/min-height/percy-css/enable-javascript/discovery),
  snapshot options (widths, minHeight, percyCSS, scope, enableJavaScript), hiding dynamic regions via
  percyCSS, the GitHub/GitLab status-check review gate, and the free-vs-Percy-vs-Applitools decision.
  Do NOT use for: free in-repo baselines you diff yourself (see
  qa-visual-regression-playwright-snapshots-typescript), visual-AI cross-browser diffing (see
  qa-visual-regression-applitools-typescript), the page objects/specs `percySnapshot` is called
  inside (see qa-ui-test-author-playwright-typescript), .NET (see qa-visual-regression-percy-dotnet),
  or Java (see qa-visual-regression-percy-java).
---

# Visual Regression — Percy (TypeScript)

Percy (by BrowserStack) is the **hosted** visual-regression layer. Instead of capturing a PNG and
diffing it locally against an in-repo baseline (that's the built-in
`qa-visual-regression-playwright-snapshots-typescript` skill, #17), Percy **uploads a DOM snapshot**
of the page, then **renders and diffs it on Percy's own infrastructure**. Baselines live in Percy's
cloud, keyed by git branch, and are reviewed/approved in a **web UI**. The build is gated on that
review, not on a local artifact.

This is an **assertion layer** on top of the page objects and specs the
`qa-ui-test-author-playwright-typescript` skill already authored. You do not write new page objects
here — you add a `percySnapshot(page, name)` call to an existing flow and wrap the test command in
`percy exec`.

## Why graduate from built-in snapshots to Percy

The single biggest pain in the free `playwright-snapshots` skill is the **cross-platform rendering
problem**: a baseline rendered on a dev Mac (`...-darwin.png`) never matches a Linux CI runner, so
you must generate baselines *inside the CI container*. Percy makes that problem **disappear**:

| | Built-in snapshots (#17) | **Percy (this skill)** |
|---|---|---|
| What leaves the test | Nothing — a PNG is diffed locally | A **DOM snapshot** is uploaded |
| Where rendering happens | Your machine / CI container | **Percy's servers**, consistently |
| Where baselines live | Committed `*-snapshots/*.png` in your repo | **Percy cloud**, keyed by git branch |
| `-{platform}` baselines | Yes — the whole headache | **None** — server renders identically every time |
| Baseline-in-CI-container rule | Mandatory | **Not needed** |
| Updating a baseline | `--update-snapshots` / delete-and-rerun | **Approve in the review UI** |
| Diff budget | `maxDiffPixelRatio` etc. per assertion | No per-call pixel knob — **`percyCSS` + region ignores** |
| Gate | Local pass/fail + `-diff.png` artifact | **Status check** linking the visual review |
| Cost | Free | Paid (per snapshot) |

State this contrast plainly when explaining Percy: **no in-repo baselines, no `-{platform}` naming,
no in-CI-container baseline generation, no `--update-snapshots`.** Baselines are managed in Percy and
auto-established from the **base branch**.

## Decision matrix — which visual-regression tool

| Need | Use | Why |
|------|-----|-----|
| Free, baselines in your repo, you own diffing + the CI-container discipline | built-in snapshots (#17) | No SaaS, no per-snapshot cost, full control |
| Hosted baselines + human review UI + server-side cross-browser render | **Percy (this skill)** | Kills the platform-rendering problem; team review workflow |
| Visual-AI diffing (ignore anti-aliasing) + a full cross-browser rendering grid | Applitools (#19) | AI diff tolerance + broad browser/viewport matrix; most expensive |

**Graduation path:** start **free** with built-in snapshots; move to **Percy** when in-repo baselines
and the platform-rendering discipline become a team bottleneck and you want a review workflow; move to
**Applitools** when anti-aliasing noise across many browsers makes even Percy's pixel diff too chatty.

## Setup

Install the Percy CLI (the local agent) plus the Playwright binding:

```bash
npm install --save-dev @percy/cli @percy/playwright
```

`PERCY_TOKEN` is the **only secret**. It's a per-project write token; in CI it comes from the secret
store (see the ci-pipelines cross-link), never committed. Locally:

```bash
export PERCY_TOKEN=<your-project-token>   # never hardcode, never log
```

## How you run the suite — `percy exec`

You do **not** call Percy's API to start a build. You wrap your existing Playwright test command in
`percy exec`. That starts the local Percy agent (a proxy that receives DOM snapshots, renders the
asset discovery, and uploads to Percy), runs your suite, then finalizes the build:

```bash
# package.json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:visual": "percy exec -- playwright test"
  }
}
```

```bash
PERCY_TOKEN=<token> npm run test:visual
```

**Percy no-ops gracefully when the agent isn't running.** If you run `playwright test` *without*
`percy exec` (or `PERCY_TOKEN` is absent), `percySnapshot()` detects Percy is not running, logs a
warning, **skips the snapshot, and the test still passes**. That means a developer without the token
can run the functional suite untouched — the visual assertions simply don't fire. Call this out: it's
why `percySnapshot` is safe to leave in shared specs.

## `.percy.yml` — project-wide snapshot config

Set rendering width(s), min height, global CSS, and discovery options once, in repo:

```yaml
# .percy.yml
version: 2
snapshot:
  # Percy renders each DOM snapshot at every width, server-side. Responsive coverage with no
  # extra test runs.
  widths:
    - 375    # mobile
    - 1280   # desktop
  min-height: 1024
  # Global CSS injected only in Percy's renderer — hide app-wide dynamic chrome (live chat, clocks).
  percy-css: |
    .intercom-launcher, [data-testid="live-clock"] { visibility: hidden !important; }
  enable-javascript: false   # Percy renders the captured DOM statically by default; turn on only if needed
discovery:
  # Asset discovery network controls — allow/disallow hostnames, concurrency, etc.
  allowed-hostnames:
    - cdn.flexinvest.test
  network-idle-timeout: 250
```

`percy exec --config ./.percy.yml -- playwright test` if the file isn't at the default location.

## Core pattern — `percySnapshot` on a page-object-driven flow

The page object exposes intent; the test stabilizes **application** state on a condition, then calls
`percySnapshot`. No selectors in the test, no fixed waits.

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
import percySnapshot from '@percy/playwright';
import { DashboardPage } from '../pages/dashboard.page';

test('Should_capture_dashboard_percy_snapshot_When_loaded', async ({ page }) => {
  const dashboard = new DashboardPage(page);
  await dashboard.goto();
  await dashboard.waitUntilLoaded();              // stabilize on a condition first…

  await percySnapshot(page, 'Dashboard — revenue card');   // …then snapshot (DOM uploaded, rendered server-side)
});
```

Unlike `toHaveScreenshot()`, `percySnapshot` does **not** assert pass/fail in the test — it uploads a
snapshot. The pass/fail decision happens later, in Percy, after rendering and diffing against the
branch baseline. So a Percy "failure" surfaces as an **unreviewed status check**, not a thrown
assertion. Stabilize before snapshotting anyway: Percy captures the DOM *at the moment you call it*,
so a half-loaded page uploads a half-loaded snapshot.

## Snapshot options — `percySnapshot(page, name, options)`

```typescript
await percySnapshot(page, 'Pricing page', {
  widths: [375, 768, 1280],          // override .percy.yml per snapshot
  minHeight: 1024,
  scope: '[data-testid="pricing-table"]',  // snapshot only this element's subtree
  enableJavaScript: false,
  percyCSS: `
    [data-testid="promo-banner"] { visibility: hidden !important; }  /* rotates daily */
    [data-testid="last-seen"]    { visibility: hidden !important; }  /* timestamp */
  `,
});
```

The options, precisely:

- **`widths`** — viewport widths Percy renders the snapshot at (server-side). Overrides `.percy.yml`.
- **`minHeight`** — minimum render height (default 1024).
- **`scope`** — a CSS selector; Percy snapshots only that element's subtree (the analogue of an
  element screenshot — less noise than a full page).
- **`enableJavaScript`** — run JS in Percy's renderer. Off by default (Percy renders the captured DOM
  statically). Turn on only when the page genuinely needs client-side JS to paint correctly.
- **`percyCSS`** — CSS injected **only in Percy's renderer**, applied right before the diff. This is
  your primary stabilization lever — there is **no per-call pixel-ratio knob** in Percy. Hide dynamic
  regions with `visibility: hidden` rather than loosening a (non-existent) diff budget.

### Hiding dynamic regions is `percyCSS`, not a pixel budget

The built-in skill tames flakiness with `maxDiffPixelRatio` / `mask`. **Percy has neither.** The lever
is `percyCSS` (per-snapshot or global in `.percy.yml`) plus region-ignore selectors. Neutralize the
*specific* dynamic region; don't try to loosen the whole diff:

```typescript
// Hide the avatar + timestamp that change every run, keep the rest pixel-strict.
await percySnapshot(page, 'Profile header', {
  percyCSS: `
    img.gravatar              { visibility: hidden !important; }
    [data-testid="last-seen"] { visibility: hidden !important; }
  `,
});
```

## CI integration + the review gate

In CI, `percy exec` wraps the test step exactly as locally; `PERCY_TOKEN` comes from the secret store.
After the build finalizes, Percy posts a **GitHub/GitLab status check** linking the visual review. The
build is **green only once the diffs are approved** in Percy's UI (or auto-approved because there were
no changes / it's the base branch). Baselines auto-establish from the **base branch**, so a PR diffs
against `main`'s last approved snapshots.

```yaml
# inside your test job — see qa-ci-pipelines-github-actions-typescript for the full pipeline
- name: Visual tests (Percy)
  env:
    PERCY_TOKEN: ${{ secrets.PERCY_TOKEN }}   # from the secret store; never inline
  run: npx percy exec -- npx playwright test
```

Contrast with built-in snapshots: there is **no `-diff.png` artifact to upload** — the diff lives in
Percy's UI. Link the Percy build URL into Allure so reviewers jump straight to it (cross-link
`qa-allure-reporting-typescript`):

```typescript
import { test } from '@playwright/test';
import { allure } from 'allure-playwright';

test.afterAll(async () => {
  // percy exec prints the build URL; PERCY_BUILD_URL is exported by the agent in recent CLI versions.
  const url = process.env.PERCY_BUILD_URL;
  if (url) allure.link(url, 'Percy visual review', 'percy');
});
```

The review-UI workflow, concretely:
1. PR runs `percy exec -- playwright test`; Percy renders + diffs against the base-branch baseline.
2. Percy posts a status check: **changes detected** (needs review) or **no changes** (auto-green).
3. A reviewer approves/rejects in Percy's UI. Approving updates the branch baseline.
4. On merge, the approved snapshots become `main`'s baseline for the next PR.

## Anti-patterns

- **Committing `*-snapshots/` PNGs alongside Percy.** Percy keeps baselines in the cloud — in-repo
  PNGs are the built-in-snapshots model and don't apply here. *Fix:* delete them; rely on the Percy
  baseline.
- **`await page.waitForTimeout(500)` before `percySnapshot`.** Percy captures the DOM at call time; a
  sleep is flaky and slow. *Fix:* wait on a condition (`document.fonts.ready`, spinner hidden,
  `locator.waitFor`), then snapshot.
- **Trying to "loosen the diff" to stop flakes.** Percy has no per-call pixel budget. *Fix:* hide the
  specific dynamic region with `percyCSS` (`visibility: hidden`).
- **Running the suite without `percy exec` and expecting visual coverage.** `percySnapshot` silently
  no-ops when the agent isn't running. *Fix:* run via `percy exec -- playwright test` with
  `PERCY_TOKEN` set; reserve the bare `playwright test` for functional-only runs.
- **Hardcoding / logging `PERCY_TOKEN`.** It's a write credential. *Fix:* env only, from the CI secret
  store, read lazily, never echoed.
- **Treating a Percy "diff" as a thrown test failure.** It's an unreviewed **status check**, not an
  in-test assertion. *Fix:* gate the merge on the Percy status check; review in the UI.
- **Full-page snapshots of a dynamic page.** Noisy reviews. *Fix:* `scope` to the element under test;
  `percyCSS` away the rotating bits.

## Examples

**End-to-end: a pricing-table visual gate reviewed in Percy.**

```typescript
// tests/pricing.spec.ts
import { test } from '@playwright/test';
import percySnapshot from '@percy/playwright';
import { PricingPage } from '../pages/pricing.page';

test.describe('Pricing page visual regression (Percy)', () => {
  test('Should_capture_pricing_table_When_plans_loaded', async ({ page }) => {
    const pricing = new PricingPage(page);
    await pricing.goto();
    await pricing.waitUntilPlansRendered();          // condition, not sleep
    await page.evaluate(() => document.fonts.ready);  // fonts settled before DOM capture

    await percySnapshot(page, 'Pricing — plan table', {
      scope: '[data-testid="pricing-table"]',         // element subtree, not full page
      widths: [375, 1280],                            // mobile + desktop, rendered server-side
      percyCSS: `[data-testid="promo-banner"] { visibility: hidden !important; }`, // rotates daily
    });
  });
});
```

Lifecycle for this test:
1. Dev makes an intended CSS change to the pricing table.
2. CI runs `percy exec -- playwright test`; Percy renders at 375px + 1280px and diffs vs `main`.
3. Percy's status check flags the change; the dev reviews + approves the diff in Percy's UI.
4. On merge, the approved render becomes `main`'s baseline — the next PR diffs against it.

## Rules (hard constraints)

- Visual regression is an assertion layer on existing page objects/specs — add `percySnapshot`, don't
  author new page objects here. Page objects expose intent + locators; no selectors in tests.
- Stabilize **application** state on a condition before `percySnapshot`; never `waitForTimeout` — Percy
  captures the DOM at call time.
- Run the suite under `percy exec -- <test cmd>`; `percySnapshot` no-ops gracefully without the agent.
- `PERCY_TOKEN` is the **only** secret: env-only, from the CI secret store, read lazily, never logged
  or committed.
- No in-repo `*-snapshots/` baselines, no `-{platform}` naming, no `--update-snapshots` — baselines
  live in Percy and are managed via the **review UI**, auto-established from the base branch.
- Stabilize/neutralize dynamic regions with **`percyCSS`** (`visibility: hidden`) and `scope`, not a
  diff budget — Percy has no per-call pixel-ratio knob.
- Prefer `scope`d element snapshots over full-page; render responsive widths via `widths` /
  `.percy.yml`, not extra tests.
- The gate is the **Percy status check** (review/approve), not a thrown assertion or a local artifact.

## Cross-references

- `qa-visual-regression-percy-dotnet` — same skill, .NET / NUnit (`PercyIO.Playwright`,
  `Percy.Snapshot(page, name, options)`).
- `qa-visual-regression-percy-java` — same skill, Java / TestNG (`io.percy.playwright.Percy`,
  `new Percy(page).snapshot(name, ...)`).
- `qa-visual-regression-playwright-snapshots-typescript` (#17) — the **free** sibling: in-repo
  baselines you diff yourself, with the CI-container discipline Percy removes. Start here; graduate to
  Percy when it becomes a bottleneck.
- `qa-visual-regression-applitools-typescript` (#19, next) — the visual-AI sibling: AI diff tolerance
  + a cross-browser rendering grid.
- `qa-ui-test-author-playwright-typescript` — the page objects/specs `percySnapshot` is called inside.
  Author the flow there; add the visual snapshot here.
- `qa-ci-pipelines-github-actions-typescript` — where `PERCY_TOKEN` is sourced (secrets/OIDC) and
  `percy exec` wraps the test step.
- `qa-allure-reporting-typescript` — link the Percy build URL into the report.
