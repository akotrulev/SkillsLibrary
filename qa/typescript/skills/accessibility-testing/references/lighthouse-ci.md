# Accessibility Testing — Lighthouse CI (TypeScript / Playwright Test)

Lighthouse is Google's headless-Chrome auditor. **Lighthouse CI** (`@lhci/cli`) runs it as a pipeline step
that produces a **category score** (0–1) for `accessibility`, `best-practices`, `seo` and `performance`, and
fails the build when a score drops below its threshold. It is the **broad-audit and trend** sibling of
`references/axe-playwright.md`: axe asserts per-component `violations` inside the functional run; Lighthouse
runs a separate full-page pass and gives one number per category. Run both.

> **Lighthouse accessibility is axe-powered, but reported as a score.** The category runs axe-core and
> surfaces a weighted pass/fail aggregate, not a list of failing nodes. axe tells a developer *what* to fix;
> Lighthouse shows the whole-page *trend* plus the performance and SEO context axe does not cover. A score
> of 1.0 is still only the automated floor.

> **Node-only tool.** There is no .NET or Java Lighthouse SDK. TypeScript is the first-class stack; the
> .NET and Java siblings shell out to the CLI and parse its JSON (`categories.*.score`).

Lighthouse 12 removed the PWA category; a config that asserts `categories:pwa` is stale.

## 1. Setup

```bash
npm install --save-dev @lhci/cli playwright-lighthouse lighthouse
```

`@lhci/cli` needs no key for the `temporary-public-storage` upload target. The only optional secret is an
LHCI server token (`LHCI_TOKEN`) for a private dashboard — environment only, never committed.

## 2. Two ways to run it

1. **`lhci autorun` with `lighthouserc.cjs`** — audits a list of URLs as a CI step. For public pages and
   the trend dashboard.
2. **`playwright-lighthouse`'s `playAudit`** — audits a page a Playwright test has driven to a state
   (signed in, dialog open, cart filled), reusing the writer's page objects.

## 3. `lhci autorun` — the URL-list gate

`autorun` **collects** (N runs per URL, keeps the median), **asserts** (the thresholds — the build-fail
mechanism) and **uploads** the report.

```js
module.exports = {
  ci: {
    collect: {
      startServerCommand: 'npm run start',
      url: ['http://localhost:3000/', 'http://localhost:3000/pricing'],
      numberOfRuns: 3,
    },
    assert: {
      assertions: {
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:seo': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['error', { minScore: 0.9 }],
        'categories:performance': ['warn', { minScore: 0.8 }],
        'color-contrast': ['error', { minScore: 1 }],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};
```

```bash
npx lhci autorun --config=lighthouserc.cjs
```

- `collect.url` lists the pages; `startServerCommand` boots the app and lhci waits for it; `numberOfRuns` ≥ 3
  so the median absorbs variance.
- `assert.assertions`: `'categories:<name>': [level, { minScore }]`, where `'error'` fails the build and
  `'warn'` reports. A per-audit assertion uses the audit id as its key (`color-contrast`). Presets exist
  (`preset: 'lighthouse:recommended'`); explicit assertions keep the gate legible.
- `upload.target`: `temporary-public-storage` (no key, a public link kept a few days), or
  `target: 'lhci'` with `serverBaseUrl` and `token` from the environment for a private, persistent
  dashboard.

## 4. `playAudit` — auditing a page a test drove to a state

Lighthouse attaches to the browser over a **remote-debugging port**. That browser is owned by a
**worker-scoped fixture** — it overrides Playwright's built-in `browser` for the Lighthouse project, so the
page objects, `page`, the trace and the failure screenshot all keep working, and the browser closes when the
worker ends. One port means one worker, so the project sets `workers: 1`.

```typescript
{
  name: 'lighthouse',
  testMatch: /.*\.lighthouse\.spec\.ts/,
  use: { storageState: authFile },
  dependencies: ['setup'],
  workers: 1,
  default: false,
},
```

Add that entry to the canonical config's `projects`, and `testIgnore: /.*\.lighthouse\.spec\.ts/` to the
`chromium` project. `TestProject.workers` [1.52] and `default: false` [1.64] keep the audits single-threaded
and out of the PR lane.

```typescript
import { playAudit } from 'playwright-lighthouse';
import { test as base } from './fixtures';
import { AccountPage } from './AccountPage';

export const lighthousePort = 9222;

export const lighthouseGate = {
  type: 'no-assertion',
  description: 'playAudit fails the test when a category is below its threshold; the thresholds are the assertion',
};

export type Thresholds = {
  accessibility: number;
  'best-practices': number;
  seo: number;
  performance: number;
};

type Lighthouse = { audit: (name: string, thresholds: Thresholds) => Promise<void> };

export const test = base.extend<{ lighthouse: Lighthouse; accountPage: AccountPage }>({
  browser: [
    async ({ playwright }, use) => {
      const browser = await playwright.chromium.launch({ args: [`--remote-debugging-port=${lighthousePort}`] });
      await use(browser);
      await browser.close();
    },
    { scope: 'worker' },
  ],
  lighthouse: async ({ page }, use, testInfo) => {
    const audited: string[] = [];
    await use({
      audit: async (name, thresholds) => {
        audited.push(name);
        await playAudit({
          page,
          port: lighthousePort,
          thresholds,
          reports: { formats: { html: true, json: true }, name, directory: testInfo.outputPath('lighthouse') },
        });
      },
    });
    for (const name of audited) {
      await testInfo.attach(`${name}.html`, {
        path: testInfo.outputPath('lighthouse', `${name}.html`),
        contentType: 'text/html',
      });
    }
  },
  accountPage: async ({ page }, use) => {
    await use(new AccountPage(page));
  },
});

export { expect } from './fixtures';
```

- The reports land in the test's own output folder, so they travel with its evidence and with the CI
  upload of `test-results/`. The teardown attaches each HTML report — after a threshold failure too, because
  fixture teardown runs either way.
- `playAudit` **throws** when a category is below its threshold. That throw is the test's assertion, so the
  spec carries the `lighthouseGate` annotation, as a Percy test does.
- **Check what was audited.** Lighthouse opens its own tab over the debugging port. Before trusting a
  signed-in audit, open its HTML report once and confirm the audited URL and screenshot are the signed-in
  page, not the sign-in screen.

```typescript
import { lighthouseGate, test } from './lighthouse.fixtures';

test(
  'Should_MeetAccessibilityAndSeoBudgets_When_AccountPageLoads',
  { tag: '@lighthouse', annotation: lighthouseGate },
  async ({ accountPage, lighthouse }) => {
    await accountPage.open();

    await lighthouse.audit('account', { accessibility: 90, 'best-practices': 90, seo: 90, performance: 80 });
  },
);
```

> **Two scales, one trap:** `playAudit` thresholds are **0–100**; `lighthouserc` `minScore` is **0–1**.
> `accessibility: 90` and `minScore: 0.9` are the same gate.

## 5. Performance variance

- `numberOfRuns` ≥ 3 and the median; for `playAudit`, audit a stable page and never hard-gate one cold run's
  performance number.
- `'error'` on accessibility, SEO and best-practices — deterministic rule checks, so a drop is real.
- `'warn'` on performance — noisy; a flaky hard failure trains the team to ignore the gate. Trend it on the
  dashboard instead.
- The page object waits on a condition before the audit; a half-loaded page scores low for the wrong reason.

## 6. Reporting

- `lhci autorun` writes `.lighthouseci/` (HTML, JSON and a `manifest.json` naming the median run) and prints
  the public report URL with `temporary-public-storage`. CI uploads the folder as an artifact
  (`qa/cicd/typescript/skills/ci-pipelines`).
- `playAudit` reports are attached by the fixture (§4) and reach Allure through `allure-playwright`.
- The LHCI GitHub App can post a status check linking the report.

## Anti-patterns

- **`'error'` on the performance score.** *Fix:* `'warn'`; trend it.
- **`numberOfRuns: 1`.** *Fix:* 3 or more, median.
- **A sleep before `playAudit`.** *Fix:* the page object's condition.
- **A module-level `let browser` launched in `beforeAll`.** Static mutable state, no trace, no screenshot, a
  page never closed. *Fix:* the worker fixture that overrides `browser`.
- **Several workers on one debugging port.** *Fix:* `workers: 1` on the Lighthouse project.
- **Mixing the 0–100 and 0–1 scales.**
- **A `categories:pwa` assertion.** The category is gone.
- **An un-awaited `allure.attachment` in a sync helper.** *Fix:* the fixture's awaited `testInfo.attach`.
- **A 1.0 accessibility score reported as "accessible".**
- **A committed `LHCI_TOKEN`.**

## Rules

- The gate is a score threshold per category; test names are `Should_X_When_Y`.
- `'error'` on accessibility, SEO and best-practices; `'warn'` on performance.
- `numberOfRuns` ≥ 3; the median is what is asserted.
- `playAudit` runs in a single-worker project whose debugging-port browser is a worker fixture; specs reach
  pages through fixtures and carry the `lighthouseGate` annotation.
- Reports are written to `testInfo.outputPath` and attached with an awaited `testInfo.attach`.
- No key for `temporary-public-storage`; an optional `LHCI_TOKEN` comes from the environment only.

## Cross-references

- `references/axe-playwright.md` — the per-component gate inside the functional run.
- `qa-accessibility-testing-dotnet`, `qa-accessibility-testing-java` — the CLI-port siblings.
- `qa/typescript/skills/ui-test-author/playwright` — the page objects, the canonical config and its
  `projects`.
- `qa/typescript/skills/evidence-capture` — where the reports and failure evidence land.
- `qa/cicd/typescript/skills/ci-pipelines` — the `lhci autorun` job and artifact upload.
- `qa-exploratory-charter-writer` — the manual and assistive-technology testing no score covers.
