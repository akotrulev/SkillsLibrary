# Visual Regression — Applitools Eyes (TypeScript / Playwright Test)

Applitools Eyes is the **visual-AI** member of the family. The SDK uploads each checkpoint to the
**Ultrafast Grid**, which re-renders it across a browser/viewport/device matrix and judges the diff with AI
matching that ignores anti-aliasing noise a person would not flag. **Match levels** (Strict, Layout,
Content, Ignore colors) say *how* a region is compared: "the layout of these figures must match, their
numbers may change". That is the difference from Percy's pixel diff and the built-in `toHaveScreenshot`.

This is an **assertion layer** on page objects and fixtures from
`qa/typescript/skills/ui-test-author/playwright`: a spec adds `eyes.check(...)` to an existing flow.

## 1. Why graduate from Percy

| | Percy | **Applitools Eyes** |
|---|---|---|
| What leaves the test | A DOM snapshot, through the `percy exec` agent | The page, uploaded by the SDK itself — no agent |
| How the diff is judged | Server-side pixel diff | Server-side AI match |
| Tolerance lever | `percyCSS` and `scope` | Match levels and region settings |
| Dynamic content | Hide it | `layoutRegions(...)` — the structure still matches, the content may differ |
| Cross-browser and devices | Widths | The Ultrafast Grid matrix from one run |
| Gate | Status check | The runner's aggregated results fail the run |
| Cost | Paid | Paid, usually the most expensive |

## 2. Setup

```bash
npm install --save-dev @applitools/eyes-playwright
```

`APPLITOOLS_API_KEY` is the **only secret**; the SDK reads it from the environment. There is no agent to
start and no wrapper command.

## 3. The model

- **`VisualGridRunner`** sends checkpoints to the Ultrafast Grid. `ClassicRunner` renders one local
  environment and gives up the grid, which is the reason to choose Applitools.
- **`Eyes`** is one visual test bound to a runner: `open` starts it, `check` adds a checkpoint,
  `close(false)` ends it without throwing.
- **`runner.getAllTestResults(true)`** waits until the grid has rendered and diffed every checkpoint, then
  throws if any test has an unresolved diff or an error. **That is the gate.** Its error names each
  unresolved test with its dashboard link.

## 4. The render matrix

```typescript
import { BatchInfo, BrowserType, Configuration, DeviceName, ScreenOrientation } from '@applitools/eyes-playwright';

export function buildEyesConfiguration(): Configuration {
  const config = new Configuration();
  config.setBatch(new BatchInfo({ name: 'Web — Visual', id: process.env.APPLITOOLS_BATCH_ID }));
  config.addBrowser(1280, 800, BrowserType.CHROME);
  config.addBrowser(1280, 800, BrowserType.FIREFOX);
  config.addBrowser(1280, 800, BrowserType.SAFARI);
  config.addDeviceEmulation(DeviceName.iPhone_11, ScreenOrientation.PORTRAIT);
  config.addDeviceEmulation(DeviceName.Pixel_5, ScreenOrientation.PORTRAIT);
  return config;
}
```

Each `addBrowser` / `addDeviceEmulation` adds an environment, so one `check` produces one checkpoint per
environment. The matrix is code in the repo; only the API key is secret. `APPLITOOLS_BATCH_ID`, set once per
CI run, puts every shard's tests into one dashboard batch.

## 5. The fixtures — the session lives in teardown, not in the test

The runner is **worker-scoped**: one per worker, gated when the worker shuts down. `eyes` is
**test-scoped**: opened before the test, closed in its teardown — which runs whether the test passed or
failed, so the test body needs no `try`/`finally`.

```typescript
import { Eyes, VisualGridRunner } from '@applitools/eyes-playwright';
import { test as base } from './fixtures';
import { buildEyesConfiguration } from './eyes-configuration';
import { AccountPage } from './AccountPage';

export const byTestId = (testId: string): string => `[data-testid="${testId}"]`;

type EyesTestFixtures = {
  eyes: Eyes;
  accountPage: AccountPage;
};

type EyesWorkerFixtures = {
  eyesRunner: VisualGridRunner;
};

export const test = base.extend<EyesTestFixtures, EyesWorkerFixtures>({
  eyesRunner: [
    async ({}, use) => {
      const runner = new VisualGridRunner({ testConcurrency: 5 });
      await use(runner);
      await runner.getAllTestResults(true);
    },
    { scope: 'worker' },
  ],
  eyes: async ({ page, eyesRunner }, use, testInfo) => {
    const eyes = new Eyes(eyesRunner);
    eyes.setConfiguration(buildEyesConfiguration());
    await eyes.open(page, 'Web', testInfo.title, { width: 1280, height: 800 });
    await use(eyes);
    await eyes.close(false);
  },
  accountPage: async ({ page }, use) => {
    await use(new AccountPage(page));
  },
});

export { expect } from './fixtures';
```

- `close(false)` per test, gate once per worker: every test's checkpoints finish rendering, and the run
  fails once with the whole picture. A failure in the worker teardown fails the run and is reported as a
  worker error rather than on one test.
- The test name in the dashboard is `testInfo.title`, so it matches the report.
- Applitools also ships its own Playwright fixture (`@applitools/eyes-playwright/fixture`), which manages
  the runner, the session and the batch from `use` options. Prefer it on a greenfield TS suite after checking
  its options against the installed SDK's types; the explicit fixture above is the model that ports to the
  .NET and Java siblings.
- Freeze time with the `frozenClock` auto fixture from `references/playwright-snapshots.md` §4 when the page
  shows dates.

## 6. The spec

```typescript
import { Target } from '@applitools/eyes-playwright';
import { byTestId, test } from './eyes.fixtures';

test.describe('Account', { tag: '@visual' }, () => {
  test(
    'Should_KeepSummaryLayout_When_BalancesChange',
    { annotation: { type: 'no-assertion', description: 'Applitools: the Eyes runner gate is the assertion' } },
    async ({ accountPage, eyes }) => {
      await accountPage.open();

      await eyes.check(
        'Account summary',
        Target.region(byTestId('Account.Summary'))
          .layoutRegions(byTestId('Account.Balances'))
          .ignoreRegions(byTestId('Account.LastLogin')),
      );
    },
  );
});
```

As with Percy, the test has no `expect`: the checkpoint is judged on the grid and the worker's runner gate
fails the run. The annotation records that exception in the test. Eyes captures at the moment of `check`, so
the page object's wait comes first.

## 7. Match levels

| Level | Compares |
|---|---|
| **Strict** (default) | "Would a person call these the same?" — ignores rendering noise, catches real change |
| **Layout** | Structure and position only; text, numbers and images may differ. The tool for live data |
| **Content** | Structure and text, not exact pixels or colours |
| **Ignore colors** | Structure and content, any colour |

- A whole checkpoint: `Target.window().fully().layout()`.
- One region: `.layoutRegions(...)` compares that region at Layout and keeps the rest of the checkpoint at
  its own level.
- `.ignoreRegions(...)` drops a region entirely. Reach for **Layout before Ignore**: ignoring loses
  coverage, Layout keeps the structure asserted.
- There is no pixel-ratio knob. The AI and the match level are the tolerance.

## 8. Batches and the dashboard

`BatchInfo` groups one run's tests under one dashboard entry. The dashboard is the hosted baseline store and
review UI; baselines are keyed by app, test and branch, and accepting a diff updates the baseline on every
environment at once. The repo holds no images.

## 9. CI

```yaml
- name: Visual tests (Applitools)
  env:
    APPLITOOLS_API_KEY: ${{ secrets.APPLITOOLS_API_KEY }}
    APPLITOOLS_BATCH_ID: ${{ github.run_id }}-${{ github.run_attempt }}
  run: npx playwright test --project=visual
```

The step belongs to the nightly job (`qa/cicd/ci-conventions`). The run fails when a worker's
`getAllTestResults(true)` throws because an unresolved diff exists; a reviewer then accepts or rejects it in
the dashboard, and on merge the accepted checkpoints become the branch baseline.

## Anti-patterns

- **`try { … } finally { await eyes.close(false) }` in a test body.** *Fix:* the `eyes` fixture's teardown.
- **`eyes.close(true)` as the gate.** One mismatch throws before the others report. *Fix:* `close(false)`
  per test, `getAllTestResults(true)` once.
- **`ClassicRunner` while expecting a grid.** *Fix:* `VisualGridRunner` and the matrix in §4.
- **A sleep before `check`.** *Fix:* the page object waits on a condition.
- **Ignoring a region Layout would cover.** *Fix:* `layoutRegions(...)`.
- **A new `BatchInfo` id per shard.** One run scatters across batches. *Fix:* one `APPLITOOLS_BATCH_ID`.
- **`new AccountPage(page)` or `new Eyes(...)` in a spec.** *Fix:* the fixtures.
- **A hard-coded or logged `APPLITOOLS_API_KEY`.**

## Rules

- `VisualGridRunner` with the matrix in code; a worker-scoped runner that gates in its teardown.
- `eyes` is a test-scoped fixture: opened before the test, `close(false)` in its teardown — never inline.
- Stabilize on a condition before `check`; never `waitForTimeout`.
- Prefer a match level over ignoring a region.
- Every Eyes test carries the no-assertion annotation; the runner gate is its assertion.
- No in-repo baselines; one batch id per run; nightly lane only.
- `APPLITOOLS_API_KEY` is the only secret: environment only, never logged or committed.

## Cross-references

- `qa-dotnet:visual-regression`, `qa-java:visual-regression` — the same model from .NET and Java.
- `references/percy.md` — hosted pixel diff; the no-assertion annotation pattern.
- `references/playwright-snapshots.md` — the free sibling, and the clock fixture.
- `qa/typescript/skills/ui-test-author/playwright` — fixtures and page objects.
- `qa/cicd/typescript/skills/ci-pipelines` — where `APPLITOOLS_API_KEY` comes from.
