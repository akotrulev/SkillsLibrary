# Visual Regression — Percy (TypeScript / Playwright Test)

Percy (by BrowserStack) is the **hosted** visual-regression layer. The test uploads a **DOM snapshot**;
Percy renders it on its own infrastructure, diffs it against the branch baseline and gates the build on a
human review. Baselines live in Percy's cloud, keyed by git branch.

This is an **assertion layer** on page objects and fixtures that
`qa/typescript/skills/ui-test-author/playwright` already provides: you add a `percy` fixture call to an
existing flow and wrap the run in `percy exec`.

## 1. Why graduate from built-in snapshots

| | Built-in snapshots | **Percy** |
|---|---|---|
| What leaves the test | Nothing — a PNG is diffed locally | A DOM snapshot is uploaded |
| Where rendering happens | Your pinned image | Percy's renderers, the same every time |
| Baselines | Committed `-linux` images | Percy cloud, from the base branch |
| Pinned-image rule for baselines | Mandatory | Not needed |
| Updating a baseline | `--update-snapshots` in the image | **Approve in the review UI** |
| Tolerance | `maxDiffPixelRatio`, `mask` | No pixel knob — `percyCSS` and `scope` |
| Gate | A failed `expect` | The Percy build's **status check** |
| Cost | Free | Paid, per snapshot |

## 2. Setup

```bash
npm install --save-dev @percy/cli @percy/playwright
```

`PERCY_TOKEN` is the **only secret**: a per-project write token from the CI secret store, never committed,
never logged.

## 3. Running — `percy exec`

Percy is not started from the test. `percy exec` starts the local Percy agent, runs the command it wraps,
then finalizes the build:

```json
{
  "scripts": {
    "test:visual": "percy exec -- playwright test --project=visual"
  }
}
```

**Without the agent, `percySnapshot` logs a warning, skips the snapshot and the test passes.** That is why
it is safe in shared specs — and why the nightly lane must run under `percy exec` with `PERCY_TOKEN` set,
or the visual coverage silently disappears.

## 4. `.percy.yml` — project-wide snapshot settings

```yaml
version: 2
snapshot:
  widths:
    - 375
    - 1280
  min-height: 1024
  percy-css: |
    [data-testid="Chat.Launcher"], [data-testid="Cookie.Banner"] { visibility: hidden !important; }
discovery:
  allowed-hostnames:
    - cdn.example.test
  network-idle-timeout: 250
```

- `widths` — Percy renders each snapshot at every width, server-side: responsive coverage with no extra run.
- `percy-css` — injected only in Percy's renderer; it hides app-wide dynamic chrome.
- `enable-javascript` is off by default (the captured DOM renders statically); turn it on only for a page
  that cannot paint without client JS.
- `percy exec --config ./.percy.yml -- …` when the file is elsewhere.

## 5. The fixtures

Two pieces: a `percy` fixture that forwards to `percySnapshot` with the test's `page`, and an auto fixture
that links the Percy build into Allure. `percy exec` sets `PERCY_BUILD_URL` for the command it wraps; a run
without the agent has no build to link.

```typescript
import percySnapshot from '@percy/playwright';
import * as allure from 'allure-js-commons';
import { test as base } from './fixtures';
import { PricingPage } from './PricingPage';

type PercyOptions = Parameters<typeof percySnapshot>[2];

export const byTestId = (testId: string): string => `[data-testid="${testId}"]`;

export const percyReview = {
  type: 'no-assertion',
  description: 'Percy: the reviewed Percy build is the assertion; this test uploads a snapshot and has no expect',
};

type PercyFixtures = {
  percyBuildLink: void;
  percy: (name: string, options?: PercyOptions) => Promise<void>;
  pricingPage: PricingPage;
};

export const test = base.extend<PercyFixtures>({
  percyBuildLink: [
    async ({}, use) => {
      const buildUrl = process.env.PERCY_BUILD_URL;
      if (buildUrl !== undefined) {
        await allure.link(buildUrl, 'Percy build', 'percy');
      }
      await use();
    },
    { auto: true },
  ],
  percy: async ({ page }, use) => {
    await use((name, options) => percySnapshot(page, name, options));
  },
  pricingPage: async ({ page }, use) => {
    await use(new PricingPage(page));
  },
});

export { expect } from './fixtures';
```

`PricingPage.open()` navigates and waits for the plans to render, the same shape as `DashboardPage` in
`references/playwright-snapshots.md` §4. Freeze time with the same `frozenClock` auto fixture when the page
shows dates.

## 6. The spec — and the no-assertion exception

```typescript
import { byTestId, percyReview, test } from './percy.fixtures';

test.describe('Pricing', { tag: '@visual' }, () => {
  test(
    'Should_UploadPlanTableSnapshot_When_PlansRender',
    { annotation: percyReview },
    async ({ pricingPage, percy }) => {
      await pricingPage.open();

      await percy('Pricing — plan table', {
        scope: byTestId('Pricing.Table'),
        widths: [375, 1280],
        percyCSS: `${byTestId('Pricing.PromoBanner')} { visibility: hidden !important; }`,
      });
    },
  );
});
```

**This test has no `expect`, deliberately.** `percySnapshot` uploads; the pass/fail decision happens later in
Percy, after rendering and diffing, and surfaces as the build's status check. The house rule is that every
test asserts, so the exception is **recorded in the test** with the `percyReview` annotation, which the HTML
report and Allure show. Without it, a reader cannot tell a Percy test from a forgotten assertion. Percy
captures the DOM at the moment of the call, so the page object's wait comes first.

## 7. Snapshot options

| Option | Does |
|---|---|
| `widths` | Widths Percy renders this snapshot at; overrides `.percy.yml` |
| `minHeight` | Minimum render height (default 1024) |
| `scope` | A CSS selector; only that subtree is snapshotted — the element-screenshot analogue. Build it from the test id with `byTestId` |
| `enableJavaScript` | Run JS in Percy's renderer; off by default |
| `percyCSS` | CSS applied only in Percy's renderer, before the diff — **the** stabilization lever |

Percy has **no per-call pixel budget**. Hide the specific dynamic region with `percyCSS`
(`visibility: hidden`) or narrow with `scope`; there is nothing to loosen.

## 8. CI and the review gate

```yaml
- name: Visual tests (Percy)
  env:
    PERCY_TOKEN: ${{ secrets.PERCY_TOKEN }}
  run: npx percy exec -- npx playwright test --project=visual
```

This step belongs to the **nightly** job (`qa/cicd/ci-conventions`), whose full shape is
`qa/cicd/typescript/skills/ci-pipelines`. After the build finalizes, Percy posts a status check that links
the review. The build goes green once the diffs are approved, or at once when nothing changed. There is no
`-diff.png` artifact to upload: the diff lives in Percy.

1. The run uploads snapshots; Percy renders and diffs them against the base branch.
2. The status check reads **changes detected** (needs review) or **no changes**.
3. A reviewer approves or rejects in Percy. Approving updates the branch baseline.
4. On merge, the approved snapshots become the base branch's baseline.

## Anti-patterns

- **Committed `*-snapshots/` images alongside Percy.** *Fix:* delete them; the baseline is in Percy.
- **A sleep before the snapshot.** *Fix:* the page object waits on a condition.
- **Trying to loosen the diff.** *Fix:* `percyCSS` on the specific region.
- **The nightly run without `percy exec`.** Snapshots no-op and every test passes. *Fix:* wrap the command
  and set `PERCY_TOKEN`.
- **A Percy test without the `percyReview` annotation.** It reads as a test with a missing assertion.
- **`percySnapshot(page, …)` or `new PricingPage(page)` in the spec.** *Fix:* the fixtures.
- **`import { allure } from 'allure-playwright'`**, or an un-awaited Allure call. *Fix:* `allure-js-commons`,
  awaited.
- **A hard-coded or logged `PERCY_TOKEN`.**

## Rules

- Add a `percy(...)` call to an existing fixture-driven flow; author no navigation in the spec.
- Stabilize on a condition before the snapshot; never `waitForTimeout`.
- Run under `percy exec -- playwright test --project=visual`, in the nightly lane.
- Every Percy test carries the `percyReview` annotation: the review is its assertion.
- No in-repo baselines and no `--update-snapshots`; baselines are approved in Percy.
- Stabilize with `percyCSS` and `scope`, never a diff budget.
- `PERCY_TOKEN` is the only secret: environment only, never logged or committed.

## Cross-references

- `qa-visual-regression-dotnet`, `qa-visual-regression-java` — the same tool from .NET and Java.
- `references/playwright-snapshots.md` — the free sibling, and the page-object and clock fixtures reused here.
- `references/applitools.md` — the visual-AI sibling.
- `qa/typescript/skills/ui-test-author/playwright` — the fixtures and page objects.
- `qa/cicd/typescript/skills/ci-pipelines` — where `PERCY_TOKEN` comes from and `percy exec` wraps the step.
- `qa/reporting/typescript/skills/test-reports` — the Allure link and annotations in the report.
