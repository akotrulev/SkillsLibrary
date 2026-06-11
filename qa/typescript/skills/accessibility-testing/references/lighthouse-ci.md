# Accessibility Testing — Lighthouse CI (TypeScript)

Lighthouse is Google's headless-Chrome auditing tool; **Lighthouse CI** (`@lhci/cli`) runs it as a
gated pipeline step that produces a **category score** (0–1) for `performance`, `accessibility`,
`best-practices`, `seo`, and `pwa`, and **fails the build when a score drops below a threshold**. This
is the **broad-audit + score-trend** sibling of `references/axe-playwright.md`:
where axe gives you per-component `violations` to assert empty **inside** your functional E2E run,
Lighthouse runs a **separate full-page pass** and gives you one number per category to gate and trend.
Run both — they are complementary, not alternatives.

> **Lighthouse a11y is axe-powered — but reported as a *score*, not as `violations`.** Under the hood
> Lighthouse's accessibility category runs axe-core, yet it surfaces the result as `categories.accessibility.score`
> (a 0–1 number derived from weighted audit pass/fail), **not** as an assertable list of failing nodes.
> That is exactly why you run both: axe-playwright gives you the per-element rule id + selector to
> *fix*; Lighthouse CI gives you the whole-page *trend* and the perf/SEO/PWA context axe doesn't cover.
> A Lighthouse a11y score is still the automated **floor** (~30–40% of WCAG) — pair with manual +
> assistive-tech testing (`qa-exploratory-charter-writer`); a 1.0 a11y score is not "accessible."

> **⚠️ Node-only tool — the defining nuance of this node.** Lighthouse is a **Node** tool. There is **no
> native .NET or Java Lighthouse SDK.** TypeScript is therefore the **first-class, canonical** stack here
> (`@lhci/cli` + `playwright-lighthouse` are real libraries). The `.NET` and `Java` siblings are **thinner
> CLI-driven ports**: they **invoke the Lighthouse/lhci CLI** (`npx lhci autorun` / `npx lighthouse
> <url> --output=json`) and **parse the JSON report** (`categories.*.score`) to gate their own pipeline.
> The structure (collect → assert on score → report) ports; the *invocation* is a subprocess, not an SDK
> call. See the sibling skills for that honest shape.

## Setup

```bash
npm install --save-dev @lhci/cli                  # the CI runner: collect → assert → upload
npm install --save-dev playwright-lighthouse       # in-Playwright-test audits of stateful pages
```

`@lhci/cli` needs no API key for the default `temporary-public-storage` upload target. The only optional
secret is an **LHCI-server token** (`LHCI_TOKEN`) if you run your own dashboard — read it lazily from the
environment, never commit it.

## The Lighthouse model — category scores, not a violations list

A Lighthouse run loads a URL in headless Chrome and produces five **category scores** in `[0, 1]`:

- `categories.performance.score`
- `categories.accessibility.score`
- `categories.best-practices.score`
- `categories.seo.score`
- `categories.pwa.score`

Each category score is a **weighted aggregate of individual `audits`** (e.g. `color-contrast`,
`image-alt`, `first-contentful-paint`). The **gate is a threshold per category** (`minScore`), optionally
plus per-audit assertions — **not** a pass/fail list of DOM violations (that's `axe-playwright`'s axe). You decide the
conformance target once (e.g. a11y ≥ 0.9) and apply it everywhere.

Two ways to run it in a TypeScript shop — cover both:

1. **`lhci autorun` + `lighthouserc`** — audit a **list of URLs** as a CI step. Best for public/unauth
   pages and the score-trend dashboard.
2. **`playwright-lighthouse` `playAudit`** — audit a page a **Playwright test already drove to a state**
   (logged in, modal open, cart filled). Best for authenticated/stateful flows; reuses `axe-playwright`'s page
   objects.

## `lhci autorun` + `lighthouserc` — the URL-list CI gate

`lhci autorun` does three phases in one command: **collect** (run Lighthouse N times per URL, keep the
median), **assert** (apply your score thresholds — this is the build-fail mechanism), **upload** (store
the report). Configure it in `lighthouserc.cjs`:

```js
// lighthouserc.cjs
module.exports = {
  ci: {
    collect: {
      // Audit these URLs. Use startServerCommand to boot the app first if it isn't already up.
      startServerCommand: 'npm run start',
      url: ['http://localhost:3000/', 'http://localhost:3000/checkout'],
      numberOfRuns: 3,                 // ≥3 and take the median — fights Lighthouse perf variance
    },
    assert: {
      assertions: {
        // Deterministic categories → 'error' (fail the build). a11y is axe-powered and stable.
        'categories:accessibility':   ['error', { minScore: 0.9 }],
        'categories:seo':             ['error', { minScore: 0.9 }],
        'categories:best-practices':  ['error', { minScore: 0.9 }],
        // Noisy category → 'warn' (don't hard-fail a flaky perf number; see "Perf variance" below).
        'categories:performance':     ['warn',  { minScore: 0.8 }],
        // Per-audit assertion: gate a specific audit, not just the category aggregate.
        'color-contrast':             ['error', { minScore: 1 }],
      },
    },
    upload: {
      target: 'temporary-public-storage',   // free, no API key — public Google Cloud link, kept a few days
      // target: 'lhci', serverBaseUrl: process.env.LHCI_SERVER_URL, token: process.env.LHCI_TOKEN,
    },
  },
};
```

Run it:

```bash
npx lhci autorun --config=lighthouserc.cjs
```

- **`ci.collect`** — `url` (the pages to audit), `startServerCommand` (boot the app; lhci waits for it),
  `numberOfRuns` (run ≥3 and median — see below). The median report is what gets asserted/uploaded.
- **`ci.assert.assertions`** — `'categories:<name>': [level, { minScore }]` where `level` is `'error'`
  (fail build) or `'warn'` (report only). Per-audit assertions use the audit id as the key. There are
  preset bundles too (`assertMatrix`, `preset: 'lighthouse:recommended'`) — start from explicit
  assertions so the gate is legible.
- **`ci.upload`** — `temporary-public-storage` (free, no key, public link, retained a few days) or an
  **LHCI server** (`target: 'lhci'` + `serverBaseUrl` + `token` from env) for a private, persistent
  trend dashboard.

## `playwright-lighthouse` — auditing a page your test already drove to a state

For authenticated or stateful pages, drive the app with the page objects the
`qa-ui-test-author-playwright-typescript` skill already authored, **then** audit. Lighthouse connects to
the page over a **remote-debugging port**, so launch Chromium with that port and run a **single worker**
(concurrent audits collide on the shared port):

```ts
// playwright.config.ts — pin one worker for the Lighthouse project
// projects: [{ name: 'a11y-lighthouse', use: { ... }, workers: 1 }]
```

```ts
// tests/dashboard.lighthouse.spec.ts
import { test, chromium, type Browser } from '@playwright/test';
import { playAudit } from 'playwright-lighthouse';
import { DashboardPage } from '../pages/dashboard.page';

const PORT = 9222;
let browser: Browser;

test.beforeAll(async () => {
  // The debugging port Lighthouse attaches to; one shared port ⇒ one worker.
  browser = await chromium.launch({ args: [`--remote-debugging-port=${PORT}`] });
});
test.afterAll(async () => { await browser.close(); });

test('Should_meet_a11y_score_When_dashboard_loaded_for_signed_in_user', async () => {
  const page = await browser.newPage();
  const dashboard = new DashboardPage(page);
  await dashboard.gotoAsSignedInUser();          // page-object intent reused from `axe-playwright`'s authoring skill
  await dashboard.waitUntilReady();              // stabilize on a CONDITION, never waitForTimeout

  await playAudit({
    page,
    port: PORT,
    thresholds: {                                // NOTE: playwright-lighthouse thresholds are 0–100…
      accessibility: 90,                         // …whereas lighthouserc minScore is 0–1. Don't mix them up.
      'best-practices': 90,
      seo: 90,
      performance: 80,
    },
    reports: {                                   // emit html+json so a failure carries the report
      formats: { html: true, json: true },
      name: 'dashboard',
      directory: 'lighthouse-reports',
    },
  });
  // playAudit throws when any category is below its threshold — that thrown error IS the gate.
});
```

`playAudit` **throws** when a category score is below its threshold, which fails the test = the gate. It
reuses the exact page objects from `axe-playwright` — this is the bridge that lets Lighthouse audit a stateful page.
The `.NET`/`Java` analogue is "drive the page with Playwright on a debugging port, then shell out to
`npx lighthouse --port=<port>`" — see the sibling skills.

> **Two scales, one trap:** `playwright-lighthouse` `thresholds` are **0–100**; `lighthouserc` `minScore`
> is **0–1**. `accessibility: 90` and `minScore: 0.9` mean the same gate. Keep them straight.

## Perf variance discipline — median the noise, gate the deterministic categories

Lighthouse **performance** scores are **noisy** (CPU contention, network jitter, cold caches). The a11y,
SEO, and best-practices categories are **deterministic** (a11y is axe-powered rule checks). So:

- **`numberOfRuns: 3` or more, take the median.** `lhci autorun` does this for you; for `playAudit`,
  audit a stable page and don't gate a single cold run's perf number hard.
- **`'error'` on a11y / SEO / best-practices** (deterministic — a regression is real).
- **`'warn'` on performance** (noisy — a hard-fail on a flaky number trains the team to ignore the gate).
  Trend perf over time on the dashboard instead of hard-gating a single PR.
- Stabilize the page on a **condition** before auditing (interactivity/visibility), never a fixed sleep —
  a half-loaded page tanks the score for the wrong reason.

## Reporting the gate — Lighthouse report into Allure + CI artifact

`lhci autorun` writes reports under `.lighthouseci/` (HTML + JSON + a `manifest.json` naming the median
run) and, with `temporary-public-storage`, prints a public report URL. `playAudit` writes to its
`reports.directory`. Surface the gate in three places (cross-link `qa-allure-reporting-typescript`):

```ts
// support/lighthouse-report.ts
import { allure } from 'allure-playwright';
import { readFileSync } from 'node:fs';

/** Attach the Lighthouse HTML + JSON to Allure so a failure carries the audit without re-running. */
export function attachLighthouseReport(htmlPath: string, jsonPath: string): void {
  allure.attachment('lighthouse-report.html', readFileSync(htmlPath), 'text/html');
  allure.attachment('lighthouse-report.json', readFileSync(jsonPath), 'application/json');
}
```

- **Allure** — attach the HTML + JSON report (above), so a failing gate names the dropped category and
  the failing audits in the report without anyone re-running locally.
- **CI artifact** — upload `.lighthouseci/` (or `lighthouse-reports/`) as a build artifact
  (cross-link `qa-ci-pipelines-typescript`).
- **Status check** — the LHCI GitHub App posts a status check linking the report; with
  `temporary-public-storage` the report URL is in the job log.

**No API key required** for `temporary-public-storage` — same "no secret" theme as `axe-playwright` (axe). The only
secret is an optional `LHCI_TOKEN` for a private LHCI server, read lazily from the environment, never
logged or committed.

## Anti-patterns

- **Hard-`error` gating the performance score.** Perf is noisy; a flaky hard-fail trains the team to
  ignore the gate. *Fix:* `'warn'` on performance, `'error'` on the deterministic categories (a11y / SEO
  / best-practices); trend perf on the dashboard.
- **`numberOfRuns: 1`.** A single run rides the variance. *Fix:* `numberOfRuns: 3`+ and median.
- **`await page.waitForTimeout(...)` before `playAudit`.** A half-loaded page scores low for the wrong
  reason and is flaky. *Fix:* stabilize on a condition (interactivity/visibility) first.
- **Running `playAudit` with multiple workers on one debugging port.** Concurrent audits collide on the
  shared port. *Fix:* one worker for the Lighthouse project.
- **Mixing the 0–100 (`playAudit`) and 0–1 (`lighthouserc`) scales.** *Fix:* `accessibility: 90` for
  `playAudit`, `minScore: 0.9` for `lighthouserc`.
- **Treating a 1.0 a11y score as "accessible."** Lighthouse a11y is axe-powered → ~30–40% automated
  floor. *Fix:* pair with manual + assistive-tech testing; trend the score, don't trust it as proof.
- **Using Lighthouse where you wanted per-node fixes.** The score won't tell a dev *which* element fails.
  *Fix:* run axe-playwright for the assertable rule id + selector; Lighthouse for the trend.
- **Committing an `LHCI_TOKEN`.** *Fix:* env var, read lazily; `temporary-public-storage` needs no key
  at all.

## Examples

**End-to-end: `lhci autorun` gating a11y/SEO hard and perf soft, plus a stateful `playAudit` for an
authenticated page.**

```js
// lighthouserc.cjs — the public-pages CI gate
module.exports = {
  ci: {
    collect: { startServerCommand: 'npm run start', url: ['http://localhost:3000/', 'http://localhost:3000/pricing'], numberOfRuns: 3 },
    assert: {
      assertions: {
        'categories:accessibility':  ['error', { minScore: 0.9 }],
        'categories:seo':            ['error', { minScore: 0.9 }],
        'categories:best-practices': ['error', { minScore: 0.9 }],
        'categories:performance':    ['warn',  { minScore: 0.8 }],
      },
    },
    upload: { target: 'temporary-public-storage' },
  },
};
```

```ts
// tests/account.lighthouse.spec.ts — the authenticated-page gate (reuses `axe-playwright`'s page objects)
import { test, chromium, type Browser } from '@playwright/test';
import { playAudit } from 'playwright-lighthouse';
import { AccountPage } from '../pages/account.page';

const PORT = 9222;
let browser: Browser;
test.beforeAll(async () => { browser = await chromium.launch({ args: [`--remote-debugging-port=${PORT}`] }); });
test.afterAll(async () => { await browser.close(); });

test('Should_meet_a11y_and_seo_scores_When_account_page_loaded', async () => {
  const page = await browser.newPage();
  const account = new AccountPage(page);
  await account.gotoAsSignedInUser();                       // intent, not selectors
  await account.waitUntilReady();                           // condition, not sleep

  await playAudit({
    page, port: PORT,
    thresholds: { accessibility: 90, seo: 90, 'best-practices': 90, performance: 80 },
    reports: { formats: { html: true, json: true }, name: 'account', directory: 'lighthouse-reports' },
  });
});
```

Lifecycle for this gate:
1. A dev ships a redesign that drops color contrast on the pricing page and removes a `<main>` landmark.
2. CI runs `lhci autorun`; Lighthouse audits each URL 3× and medians the result.
3. `categories.accessibility.score` falls below `0.9` → the assertion fails → **the build fails**, with
   the dropped category and failing audits in the uploaded report (linked from the status check / job
   log, and attached to Allure).
4. The dev fixes contrast + the landmark; the score climbs back over the threshold; the gate goes green.
   Perf stays a `warn` and is trended on the dashboard rather than hard-failing the PR.

## Rules (hard constraints)

- The gate is a **score threshold per category** (`minScore`), one logical assertion per category under
  test. Test names `Should_X_When_Y`.
- `'error'` (hard-fail) on the **deterministic** categories (accessibility / SEO / best-practices);
  `'warn'` (report only) on the **noisy** performance category — trend perf, don't hard-gate a flaky run.
- `numberOfRuns` ≥ 3 and take the **median** — fights Lighthouse variance.
- `playwright-lighthouse` audits reuse existing page objects (intent, not selectors); stabilize on a
  **condition** before `playAudit`, never `waitForTimeout`; one worker per shared debugging port.
- Don't mix scales: `playAudit` thresholds are **0–100**, `lighthouserc` `minScore` is **0–1**.
- **No API key** for `temporary-public-storage` (contrast `percy` `PERCY_TOKEN` / `applitools` `APPLITOOLS_API_KEY`);
  an optional `LHCI_TOKEN` for a private server is the only secret — env, lazy, never logged.
- A Lighthouse a11y score is axe-powered = the automated **floor** (~30–40% of WCAG), not proof. Pair
  with manual + assistive-tech testing, and run axe-playwright for assertable per-node fixes.

## Cross-references

- `references/axe-playwright.md` — the **per-component assertion** sibling:
  gate on `violations` empty **inside** the E2E run. Run both — axe to *fix* nodes, Lighthouse to *trend*
  whole-page scores + gate perf/SEO/PWA. (Lighthouse a11y is axe-powered but reported as a score.)
- `qa-accessibility-testing-dotnet` — same skill, .NET / NUnit. **No native SDK** → shells
  out to `npx lhci`/`npx lighthouse --output=json` and parses `categories.*.score`.
- `qa-accessibility-testing-java` — same skill, Java / TestNG. Same CLI-port shape.
- `qa-ui-test-author-playwright-typescript` — the page objects the `playwright-lighthouse` audit reuses to
  reach a stateful page. Author the flow there; add the audit here.
- `qa-ci-pipelines-typescript` — the `lhci autorun` job, artifact upload, and LHCI status
  check; how the dotnet/java siblings invoke the Node CLI from their pipelines.
- `qa-allure-reporting-typescript` — attach the Lighthouse HTML + JSON report to the run.
- `qa-exploratory-charter-writer` — the manual/assistive-tech testing that covers the ~60% no automated
  a11y score can.
