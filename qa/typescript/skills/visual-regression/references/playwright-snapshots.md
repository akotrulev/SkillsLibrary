# Visual Regression — Playwright Snapshots (TypeScript / Playwright 1.64)

`toHaveScreenshot` compares a fresh capture against a baseline image committed to the repo. Playwright does
the capture and the diff; you own the baselines and the environment they are rendered in. It is a **Node
test-runner feature only** — Java, .NET and Python have no screenshot assertion. The version in brackets is
where an API first shipped.

Visual regression is an **assertion layer** on flows that `qa/typescript/skills/ui-test-author/playwright`
already models: you add a page-object fixture and one capture, never new navigation code in a spec.

## 1. Which assertion

| Need | Use | Why |
|---|---|---|
| A component's look | `await expect(locator).toHaveScreenshot('name.png')` | Scoped capture, least noise. The default |
| A whole page | `await expect(page).toHaveScreenshot(...)` through a page-object method | More surface, more masks |
| Deterministic text or bytes you generated (CSV, SVG, JSON) | `expect(value).toMatchSnapshot('orders.csv')` | No retry and no stabilization — the value must already be stable |
| Roles, names and states, no pixels | `toMatchAriaSnapshot` | `qa/typescript/skills/ui-test-author/playwright/references/assertions.md` §2 |

`toHaveScreenshot` captures until two consecutive screenshots match, then compares with the baseline, and
retries until the `expect` timeout. It disables animations, hides the caret, uses CSS-pixel scale and
waits for web fonts by default, so none of those is set again.

## 2. Config — what this skill adds to the canonical config

The canonical config (`qa/typescript/skills/ui-test-author/playwright/assets/playwright.config.ts`) already
sets the evidence defaults (`trace: 'retain-on-failure'`, video, screenshot) and
`updateSnapshots: isCI ? 'none' : 'missing'`. A visual suite adds a tolerance, a baseline location and a
`visual` project that only the nightly lane runs. Merge these keys into that config:

```typescript
expect: {
  toHaveScreenshot: {
    maxDiffPixelRatio: 0.01,
    pathTemplate: '{testDir}/__screenshots__/{testFilePath}/{arg}{-projectName}-{platform}{ext}',
  },
},
projects: [
  { name: 'setup', testMatch: /.*\.setup\.ts/ },
  {
    name: 'chromium',
    testIgnore: /.*\.visual\.spec\.ts/,
    use: { ...devices['Desktop Chrome'], storageState: authFile },
    dependencies: ['setup'],
  },
  {
    name: 'visual',
    testMatch: /.*\.visual\.spec\.ts/,
    use: { ...devices['Desktop Chrome'], storageState: authFile },
    dependencies: ['setup'],
    default: false,
  },
],
```

- `default: false` [1.64] keeps `visual` out of a plain `npx playwright test`, so the PR lane never runs it.
  `--project=visual` runs it, with its `setup` dependency.
- `expect.toHaveScreenshot.pathTemplate` [1.50] moves screenshot baselines without moving aria snapshots;
  `snapshotPathTemplate` [1.28] moves both.
- Do not set `animations: 'disabled'`, `caret: 'hide'` or `scale: 'css'`: they are already the
  `toHaveScreenshot` defaults.
- Upgrading to 1.64: device descriptors now forward `screen`, so pages that read `window.screen` or screen
  media queries may render differently. Re-baseline once in the image, or set `screen: undefined` in the
  project.

## 3. Where baselines live

The runner default is
`{snapshotDir}/{testFileDir}/{testFileName}-snapshots/{arg}{-projectName}{-snapshotSuffix}{ext}`, with the
platform as the suffix: `dashboard.visual.spec.ts-snapshots/revenue-card-visual-linux.png`. Tokens:
`{arg} {ext} {platform} {projectName} {snapshotDir} {testDir} {testFileDir} {testFileBaseName}` [1.60]
`{testFileName} {testFilePath} {testName}`; a one-character prefix such as `{-projectName}` is written only
when the token is not empty.

Keep `{platform}` in any template. Browser rendering depends on the host OS, fonts and hardware, so the only
baselines that count are the `-linux` ones written in the pinned image. A `-darwin` file from a dev box is
never used by CI and never committed: add `__screenshots__/**/*-darwin.*` and `__screenshots__/**/*-win32.*`
to `.gitignore`. Commit the `-linux` baselines — they are versioned test data, not secrets.

## 4. Fixtures and the page object

Time is frozen for every visual test by an auto fixture, before any navigation. `setFixedTime` makes
`Date.now()` return one instant while timers keep running, which is what "today is …" rendering needs. A
page whose animation is driven by timers needs `page.clock.install()` and `pauseAt()` instead.

```typescript
import type { Locator, Page } from '@playwright/test';

export class DashboardPage {
  readonly revenueCard: Locator;
  readonly lastSeen: Locator;
  private readonly revenueSpinner: Locator;

  constructor(private readonly page: Page) {
    this.revenueCard = page.getByTestId('Dashboard.RevenueCard');
    this.lastSeen = page.getByTestId('Dashboard.LastSeen');
    this.revenueSpinner = this.revenueCard.getByRole('progressbar');
  }

  async open(): Promise<void> {
    await this.page.goto('/dashboard');
    await this.revenueSpinner.waitFor({ state: 'hidden' });
  }
}
```

```typescript
import { test as base } from './fixtures';
import { DashboardPage } from './DashboardPage';

export const visualNow = new Date('2026-01-15T09:00:00Z');

type VisualFixtures = {
  frozenClock: void;
  dashboardPage: DashboardPage;
};

export const test = base.extend<VisualFixtures>({
  frozenClock: [
    async ({ page }, use) => {
      await page.clock.setFixedTime(visualNow);
      await use();
    },
    { auto: true },
  ],
  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },
});

export { expect } from './fixtures';
```

`./fixtures` is the writer's `assets/fixtures.ts`; `visual.fixtures.ts` extends it, and visual specs import
`test` and `expect` from it.

## 5. The spec

```typescript
import { expect, test } from './visual.fixtures';

test.describe('Dashboard', { tag: '@visual' }, () => {
  test('Should_MatchRevenueCardBaseline_When_DashboardLoads', async ({ dashboardPage }) => {
    await dashboardPage.open();

    await expect(dashboardPage.revenueCard).toHaveScreenshot('revenue-card.png', {
      mask: [dashboardPage.lastSeen],
    });
  });
});
```

The page object waits for the application state (the spinner gone); `toHaveScreenshot` waits for the
rendering to settle. Playwright cannot know when your data has arrived, so the first wait is yours.

## 6. Taming false diffs

| Source of noise | Fix |
|---|---|
| Data that changes per run (timestamps, avatars, ads) | `mask: [locator]` paints a box over it (`maskColor` [1.35], default `#FF00FF`); masks cover invisible matches too |
| A widget you never want to diff (chat launcher, cookie banner) | `stylePath: './visual.css'` [1.41] in `expect.toHaveScreenshot`, applied to every capture. There is no inline `style` option on `toHaveScreenshot` |
| Today's date | The `frozenClock` fixture (§4) |
| Anti-aliasing and sub-pixel noise | `maxDiffPixelRatio` (0–1, scales with image size) over `maxDiffPixels`; keep it ≤ 0.02 and mask instead of loosening |
| Colour sensitivity per pixel | `threshold` (YIQ distance, 0 strict … 1 lax, default 0.2) — rarely changed |
| A hover state left behind by the last action | A page-object method that moves the pointer off the element before the capture |
| A whole page | `fullPage: true` on `expect(page)` — flakier, mask aggressively |

```css
[data-testid="Chat.Launcher"],
[data-testid="Cookie.Banner"] {
  visibility: hidden !important;
}
```

## 7. Documents and generated files

- **Never byte-compare a PDF.** `page.pdf()` embeds a creation date and a document id, so its bytes differ
  on every run; it is also Chromium-only. Compare the **print rendering** instead — a page-object method
  calls `page.emulateMedia({ media: 'print' })` and opens the document, and the spec asserts
  `toHaveScreenshot` on the document locator. To check the PDF file itself, extract its text with the
  project's PDF library and assert on the text.
- `toMatchSnapshot` is for a value you produced that is deterministic: a CSV export, a generated SVG, a
  serialized JSON. It does not retry or stabilize.

## 8. PNG or WebP

`toHaveScreenshot('name.webp')` [1.62] stores a lossless WebP baseline; `expect.toHaveScreenshot.type:
'webp'` [1.64] does it for unnamed captures. WebP baselines are smaller, but `allure-playwright` builds its
image-diff widget only from `-expected/-actual/-diff.png` triples, so a WebP failure reaches Allure as three
separate images (`qa/reporting/typescript/skills/test-reports`). Use PNG while Allure is where diffs are
reviewed.

## 9. Updating baselines — the modes

`updateSnapshots` in the config, or `--update-snapshots[=mode]` / `-u` on the command line:

| Mode | Missing baseline | Mismatched baseline | Where it is used |
|---|---|---|---|
| `none` | not written | not written | CI — the canonical config sets it; no pipeline passes `-u` |
| `default` (no flag) | written, and the test **fails** | not written | The 1.64 name for the old implicit behaviour |
| `missing` | written, and the test **passes** [1.64] | not written | The canonical config locally. Before 1.64 it failed |
| `changed` (bare `-u`) | written | rewritten | An intended UI change, in the pinned image |
| `all` | rewritten | rewritten | A full re-baseline after a Playwright or browser upgrade |

A script that relied on "`missing` fails" must switch to `default`. Locally, `missing` lets a new visual
test pass on a dev box while writing a `-darwin` baseline; that file is ignored (§3) and the image run
writes the real one.

## 10. Writing baselines in the pinned image

```bash
docker run --rm --ipc=host \
  -v "$PWD":/work -v /work/node_modules -w /work \
  -e BASE_URL -e E2E_USER -e E2E_PASSWORD \
  mcr.microsoft.com/playwright:v1.64.0-noble \
  /bin/bash -c "npm ci && npx playwright test --project=visual --update-snapshots=changed"
```

- The tag equals the installed `@playwright/test`; on a project pinned elsewhere, use that version.
- `--ipc=host` gives Chromium the shared memory it needs; without it the browser can crash on large pages.
- `npm ci` runs **inside** the container, so the Linux browser binaries and native modules are installed for
  the image. `-v /work/node_modules` keeps that install out of the host's `node_modules`.
- From macOS, an app on the host is `BASE_URL=http://host.docker.internal:<port>`.
- Review the changed images in the PR diff and commit them with the UI change that caused them.

## 11. CI — the nightly lane

The scheduled job runs `npx playwright test --project=visual` in the same image (`qa/cicd/ci-conventions`:
visual regression is gated to the schedule or an explicit label). CI never writes a baseline. On a
mismatch the test folder under `test-results/` holds `<name>-expected.png`, `<name>-actual.png` and
`<name>-diff.png`, plus the trace the config keeps; `allure-playwright` turns the PNG triple into one
diff attachment. The job uploads `test-results/` on failure like every UI job
(`qa/cicd/typescript/skills/ci-pipelines`). Nothing re-attaches the diffs in an `afterEach`. Reading the
failure is `qa/typescript/skills/evidence-capture`.

## Anti-patterns

- **Baselines from a dev box.** `-darwin` files never match Linux CI. *Fix:* §10, and ignore them (§3).
- **A sleep or a `document.fonts.ready` step before the capture.** Fonts are already awaited and a sleep
  races the page. *Fix:* the page object waits on the data condition.
- **Re-setting the defaults** (`animations`, `caret`, `scale`). Noise. *Fix:* delete them.
- **Loosening `maxDiffPixelRatio` to 0.2 to make a test pass.** It blinds the test. *Fix:* mask the region.
- **`--update-snapshots` in a pipeline**, or `updateSnapshots` other than `'none'` on CI. Every run
  overwrites the baseline. *Fix:* the canonical config; update in the image by hand.
- **A PDF byte comparison.** *Fix:* §7.
- **An `afterEach` that re-attaches diff images.** `allure-playwright` already attaches them. *Fix:* delete it.
- **`new DashboardPage(page)` in a spec.** *Fix:* a fixture.
- **Visual specs in the PR lane.** *Fix:* the `visual` project with `default: false`.

## Rules

- Stabilize on a condition in the page object; freeze time in an auto fixture; never `waitForTimeout`.
- Element captures over full pages; `mask` every dynamic region; keep `maxDiffPixelRatio` ≤ 0.02.
- Baselines are written in the pinned image only and committed; CI runs with `updateSnapshots: 'none'`.
- Visual specs live in the `visual` project and run in the nightly lane.
- `toHaveScreenshot` for anything the browser renders; `toMatchSnapshot` only for deterministic values you
  produced; never a PDF's bytes.
- Specs reach pages through fixtures; page objects expose locators and intent, never assertions.
- Failure evidence and its Allure mapping come from the canonical config; nothing is re-attached.

## Cross-references

- `qa-visual-regression-dotnet`, `qa-visual-regression-java` — the same skill without a screenshot
  assertion: `screenshot()` plus a comparator.
- `qa/typescript/skills/ui-test-author/playwright` — the canonical config, `fixtures.ts`, page objects.
- `references/percy.md`, `references/applitools.md` — hosted baselines and review.
- `qa/typescript/skills/evidence-capture` — failure evidence, traces, reading a failure.
- `qa/reporting/typescript/skills/test-reports` — the diff widget and the WebP caveat.
- `qa/cicd/typescript/skills/ci-pipelines`, `qa/cicd/ci-conventions` — the nightly job, the image and the
  upload.
