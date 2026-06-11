---
name: qa-allure-reporting-typescript
description: Use when the user asks to set up Allure reporting for a TypeScript test suite (Vitest + native fetch, Playwright TS, WebdriverIO TS). Triggers: "set up Allure for our Vitest project", "wire Allure in Playwright config", "publish Allure report from our Node CI".
---

# QA — Allure Reporting (TypeScript / Vitest, Playwright, WebdriverIO)

Wires Allure into a Node 20 + TypeScript test project — `allure-vitest`, `allure-playwright` (`@playwright/test` reporter), or `@wdio/allure-reporter`. Standardizes failure-path attachments, behavior-first hierarchy (`label('feature')` / `label('story')` / `severity`), CI publish, history, and triage categories.

## When to use

- A new TS test project needs a reporting story
- An existing Vitest / Playwright / WebdriverIO suite emits JUnit XML and the team wants richer reports with attachments + history
- CI does not publish reports; PRs have no test artifacts

## When NOT to use

- .NET reporting → `qa/dotnet/skills/allure-reporting`
- Java reporting → `qa/java/skills/allure-reporting`
- Writing tests → `qa/typescript/skills/api-test-author/generator` / `qa/typescript/skills/ui-test-author/<stack>/typescript`
- Test strategy → `qa/manual/test-strategy`
- Quality metrics dashboards → `qa/manual/quality-metrics`

## Stack adapters

| Runner | Allure dependency | Results dir |
|---|---|---|
| Vitest | `allure-vitest` | `allure-results` |
| Playwright (`@playwright/test`) | `allure-playwright` | `allure-results` |
| WebdriverIO | `@wdio/allure-reporter` | `allure-results` |

Each writes `allure-results/` under the project's working directory. Convert to HTML via `allure generate allure-results -o allure-report --clean` (provided by `allure-commandline` or the `pactfoundation/allure` container).

## Install

### Vitest

```bash
pnpm add -D allure-vitest allure-commandline
```

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    setupFiles: ['allure-vitest/setup'],
    reporters: ['default', ['allure-vitest/reporter', { resultsDir: 'allure-results' }]],
  },
});
```

### Playwright (`@playwright/test`)

```bash
pnpm add -D allure-playwright allure-commandline
```

```ts
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  reporter: [
    ['list'],
    ['allure-playwright', { detail: true, outputFolder: 'allure-results', suiteTitle: false }],
  ],
  use: {
    trace:      'retain-on-failure',
    screenshot: 'only-on-failure',
    video:      'retain-on-failure',
  },
});
```

`trace: 'retain-on-failure'` is the highest-leverage line — every failure ships with a deterministic replay.

### WebdriverIO

```ts
// wdio.conf.ts
import type { Options } from '@wdio/types';

export const config: Options.Testrunner = {
  reporters: [
    'spec',
    ['allure', {
      outputDir: 'allure-results',
      disableWebdriverStepsReporting: false,
      disableWebdriverScreenshotsReporting: false,
    }],
  ],
  // ...
};
```

## Hierarchy: Feature → Story → Test

Behavior view: **Epic → Feature → Story**. Suite view: file → describe → test.

In `allure-js-commons` v2 (used by all three adapters), use the runtime API rather than decorators (which don't exist for Vitest / Playwright Test):

```ts
import { allure } from 'allure-vitest';
// or: import { allure } from 'allure-playwright';

it('issues a partial refund', async () => {
  await allure.epic('Orders');
  await allure.feature('Refunds');
  await allure.story('Issue partial refund');
  await allure.severity('critical');           // 'blocker' | 'critical' | 'normal' | 'minor' | 'trivial'
  await allure.description('Partial refund applies to a single line item only.');
  await allure.issue('ORDERS-512', 'https://yourco.atlassian.net/browse/ORDERS-512');
  await allure.tag('regression');

  // arrange / act / assert
});
```

Severity = **test** severity. `'blocker'` = "ship is blocked if this fails"; `'normal'` = "regression on a non-critical flow".

For Playwright Test specifically, you can also use `test.info().annotations.push({ type: 'feature', description: 'Refunds' });` for static tagging.

## Attachments (mandatory on failure path)

| Attachment | When |
|---|---|
| Request + response body | Every API test |
| Screenshot | UI tests, on failure (Playwright auto-attaches with `screenshot: 'only-on-failure'`) |
| Playwright `trace.zip` | UI tests, on failure (Playwright auto-attaches with `trace: 'retain-on-failure'`) |
| Server logs around the test window | Optional, from Loki LogQL |

### API tests (Vitest) — attach response body

```ts
async function attachResponse(response: ApiResponse) {
  await allure.attachment('response.json', response.bodyText, 'application/json');
}

it('returns 422 on invalid email', async () => {
  await allure.feature('Sign-up');
  const response = await usersClient.signUp({ email: 'not-an-email' });
  await attachResponse(response);                  // attach BEFORE assertion
  expect(response.status).toBe(422);
});
```

Attach **before** assertions on the failure path so the body is visible inline when the test fails.

### Playwright TS — manual attachment when you need more

Playwright's reporter auto-attaches screenshot/video/trace per the config. Manual attachments:

```ts
import { test, expect } from '@playwright/test';
import { allure } from 'allure-playwright';

test('checkout completes', async ({ page }) => {
  await allure.feature('Checkout');
  await page.goto('/cart');
  // ...
  await allure.attachment('cart.json', JSON.stringify(cartState), 'application/json');
});
```

### WebdriverIO — failure hook

```ts
// in wdio.conf.ts
afterTest: async function (test, _, { error }) {
  if (!error) return;
  const png = await browser.takeScreenshot();
  await browser.takeScreenshot();
  // @wdio/allure-reporter
  const { addAttachment } = await import('@wdio/allure-reporter');
  addAttachment('screenshot', Buffer.from(png, 'base64'), 'image/png');
},
```

## Steps — `step('…')`

Wrap non-trivial workflows so the report shows a step tree:

```ts
import { allure } from 'allure-playwright';

await allure.step('Sign in', async () => {
  await loginPage.signIn(user);
});
```

For Playwright Test, `test.step('Sign in', async () => { ... })` is captured by `allure-playwright` automatically — prefer it over `allure.step` when both are available.

## CI integration

Pattern is identical regardless of CI:

1. Run tests → `allure-results/` written.
2. Upload `allure-results/` as an artifact, **always** (even on failure).
3. Concatenate with previous run's `history/`.
4. `allure generate allure-results -o allure-report --clean`.
5. Publish to GitHub Pages / GitLab Pages / Azure static page.

### GitHub Actions

```yaml
- uses: actions/setup-node@v4
  with: { node-version: '20' }

- name: Run tests
  run: pnpm test
  continue-on-error: true

- name: Upload Allure results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: allure-results
    path: allure-results

- name: Publish Allure report
  if: github.ref == 'refs/heads/main'
  uses: simple-elf/allure-report-action@v1.9
  with:
    gh_pages: gh-pages
    allure_results: allure-results
    allure_history: allure-history
    keep_reports: 30
```

### Azure Pipelines

```yaml
- task: NodeTool@0
  inputs: { versionSpec: '20.x' }

- script: pnpm install && pnpm test
  displayName: Run tests
  continueOnError: true

- task: PublishBuildArtifacts@1
  condition: always()
  inputs:
    PathtoPublish: $(System.DefaultWorkingDirectory)/allure-results
    ArtifactName: allure-results

- script: |
    curl -L https://github.com/allure-framework/allure2/releases/download/2.27.0/allure-2.27.0.tgz | tar -xz
    ./allure-2.27.0/bin/allure generate allure-results -o $(Build.ArtifactStagingDirectory)/allure-report --clean
  displayName: Generate Allure report
  condition: succeededOrFailed()

- task: PublishHtmlReport@1
  inputs:
    reportDir: $(Build.ArtifactStagingDirectory)/allure-report
    tabName: Allure
```

### GitLab CI

```yaml
test:
  image: node:20
  script:
    - corepack enable
    - pnpm install
    - pnpm test || true
  artifacts:
    when: always
    paths: [allure-results/]
    expire_in: 30 days
    reports:
      junit: junit.xml

publish:allure:
  stage: package
  image: node:20
  needs: [test]
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  before_script:
    - apt-get update && apt-get install -y default-jre-headless
    - curl -L https://github.com/allure-framework/allure2/releases/download/2.27.0/allure-2.27.0.tgz | tar -xz
  script:
    - mkdir -p allure-results/history
    - cp -r public/history allure-results/history || true
    - ./allure-2.27.0/bin/allure generate allure-results --clean -o public
  artifacts:
    paths: [public/]
```

## History & trends

Trend graphs require an `history/` folder inside `allure-results/` populated from the previous run. The smoke test is "does the trend chart in the published report show > 1 bar".

Keep last 20–30 runs.

## Categories for triage — `categories.json`

Place at the project root (the adapters pick it up automatically when present alongside `allure-results/`, or copy it in during CI):

```json
[
  { "name": "Backend 5xx",       "matchedStatuses": ["broken", "failed"], "messageRegex": ".*status.*5\\d\\d.*" },
  { "name": "Auth issues",       "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*Unauthorized.*|.*Forbidden.*" },
  { "name": "Flaky timeouts",    "matchedStatuses": ["broken"],           "traceRegex":   ".*TimeoutError.*|.*timeout exceeded.*" },
  { "name": "Element not found", "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*locator.*not found.*|.*Element not found.*" },
  { "name": "Zod schema drift",  "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*ZodError.*" }
]
```

Copy it into `allure-results/` before `allure generate` runs.

## Rules

- One Allure adapter per project (`allure-vitest` **or** `allure-playwright` **or** `@wdio/allure-reporter`) — never two writing into the same `allure-results/`.
- Every test calls `allure.feature(…)` + `allure.story(…)` + `allure.severity(…)` (or the equivalent annotation in Playwright Test).
- API tests attach `response.bodyText` **before** assertions on failure paths.
- Playwright config sets `trace: 'retain-on-failure'`, `screenshot: 'only-on-failure'`, `video: 'retain-on-failure'`.
- `allure-results/` uploaded as a CI artifact on **every** run, even on test failure.
- History preserved across runs (last 20–30 retained).
- Report published from `main` to a stable URL; PR builds publish to a PR-scoped URL or skip publish.
- `categories.json` lives at the project root and is copied into `allure-results/` during CI.
- Floating promises forbidden — every `await allure.*` call must be awaited; enable ESLint `no-floating-promises`.

## What NOT to do

- No "always pass" wrappers around `pnpm test` — use `continue-on-error: true` (GHA) / `continueOnError: true` (Azure) instead.
- No committing `allure-results/` to Git — it's an artifact.
- No `allure.feature('misc')` catch-all bucket.
- No `allure.description` that paraphrases the test name — describe behavior or link the spec.
- No attaching secrets / PII / auth tokens — sanitize before `allure.attachment(...)`.
- No `trace: 'on'` in production CI (perf cost) — use `'retain-on-failure'`.
- No `allure.feature(…)` calls outside `it`/`test` bodies — they won't bind to a test in the Vitest adapter.
- No `JSON.stringify(largeObject)` attachments > 1 MB — link to Loki / object storage instead.
- No mixing `allure-playwright` with `allure-vitest` in the same project unless they write to **separate** result directories.

## Generation steps

1. Confirm runner (Vitest / Playwright / WebdriverIO), CI, publishing target, feature/severity taxonomy.
2. Install the matching adapter package and `allure-commandline`.
3. Wire the reporter in `vitest.config.ts` / `playwright.config.ts` / `wdio.conf.ts`.
4. Add `allure.feature/story/severity/issue` calls to existing tests (or Playwright `test.info().annotations`).
5. Attach response body **before** assertions in API tests; rely on Playwright config for UI auto-attachments.
6. Drop `categories.json` at the project root.
7. Wire CI per the snippet for the team's CI platform; configure history retention.
8. Smoke a green build + a deliberate failing test; confirm trend, categories, attachments populate.

## Handoffs

- .NET Allure → `qa/dotnet/skills/allure-reporting`
- Java Allure → `qa/java/skills/allure-reporting`
- API test generation → `qa/typescript/skills/api-test-author/generator`
- UI test generation → `qa/typescript/skills/ui-test-author/playwright` / `qa/typescript/skills/ui-test-author/selenium` / `qa/typescript/skills/ui-test-author/appium`
- Test strategy → `qa/manual/test-strategy`
- Quality metrics dashboards → `qa/manual/quality-metrics`
- CI pipeline syntax → `qa/typescript/skills/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` or `devops/<ci>`
