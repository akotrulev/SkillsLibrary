---
name: test-reports
description: Use when setting up Allure reporting for a TypeScript test suite (Vitest + native fetch, Playwright TS, WebdriverIO TS). Triggers: "set up Allure for our Vitest project", "wire Allure in Playwright config", "publish Allure report from our Node CI". Not for flaky-test quarantine (`qa-typescript:flaky-test-quarantine`) or pipeline YAML (`qa-typescript:ci-pipelines`).
---

# QA — Allure Reporting (TypeScript / Vitest, Playwright, WebdriverIO)

Wires Allure into a Node 24 + TypeScript test project — `allure-vitest`, `allure-playwright` (`@playwright/test` reporter), or `@wdio/allure-reporter`. Standardizes the runtime API (`allure-js-commons`), behavior-first hierarchy (`feature` / `story` / `severity`), CI publish, history, and triage categories.

**Native Playwright evidence is not configured here.** Trace, video and screenshot modes and reading a trace belong to `qa/typescript/skills/evidence-capture`; the config that carries them is `qa/typescript/skills/ui-test-author/playwright/assets/playwright.config.ts`. This skill only maps that evidence into Allure.

## When to use

- A new TS test project needs a reporting story
- An existing Vitest / Playwright / WebdriverIO suite emits JUnit XML and the team wants richer reports with attachments + history
- CI does not publish reports; PRs have no test artifacts

## When NOT to use

- .NET reporting → `qa/reporting/dotnet/skills/test-reports`
- Java reporting → `qa/reporting/java/skills/test-reports`
- Writing tests → `qa/typescript/skills/api-test-author/writer` / `qa/typescript/skills/ui-test-author/<tool>`
- Trace / video / screenshot modes, screencasts, HAR → `qa/typescript/skills/evidence-capture`
- Test strategy → `qa/manual/test-strategy`
- Quality metrics dashboards → `qa/manual/quality-metrics`

## Versions

| Artifact | Version | Note |
|---|---|---|
| `allure-playwright`, `allure-js-commons`, `allure-vitest` | 3.13.0 | One allure-js release. `allure-playwright` ≥ 3.12 needs `@playwright/test` ≥ 1.62; a project on 1.53–1.61 pins `allure-playwright` ≤ 3.11.1 |
| `@wdio/allure-reporter` | 10.0.1 | The WebdriverIO 10 lane |
| Allure report CLI | **`allure-commandline` 2.46.1** (Allure Report 2) | The npm wrapper of allure2 2.46.1, checked 2026-10-10; needs a Java runtime. The same pin is in `qa/cicd/ci-conventions`, and every snippet below uses it |

Allure Report 3 (npm `allure`, `npx allure generate`) reads the same results; it is not this library's pin.

## Stack adapters

| Runner | Allure dependency | Results dir |
|---|---|---|
| Vitest | `allure-vitest` | `allure-results` |
| Playwright (`@playwright/test`) | `allure-playwright` | `allure-results` |
| WebdriverIO | `@wdio/allure-reporter` | `allure-results` |

Each writes `allure-results/` under the project's working directory. Convert to HTML with `allure generate allure-results -o allure-report --clean` from the pinned CLI.

## Install

### Vitest

```bash
pnpm add -D -E allure-vitest@3.13.0 allure-js-commons@3.13.0 allure-commandline@2.46.1
```

In `vitest.config.ts` (the reporter registers its setup module itself):

```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    reporters: ['default', ['allure-vitest/reporter', { resultsDir: 'allure-results' }]],
  },
});
```

### Playwright (`@playwright/test`)

```bash
pnpm add -D -E allure-playwright@3.13.0 allure-js-commons@3.13.0 allure-commandline@2.46.1
```

The reporter entry is already in the canonical config, `qa/typescript/skills/ui-test-author/playwright/assets/playwright.config.ts`, on CI: `['allure-playwright', { resultsDir: 'allure-results' }]`. Add it there, never in a second config. The allure-playwright 3 options are `resultsDir`, `detail` and `suiteTitle`; `outputFolder` is not an option and is silently ignored.

What `allure-playwright` maps from the runner, with no code:

- Every `testInfo.attachments` entry — the failure screenshot, video and trace the config keeps, and anything a fixture attached — becomes an Allure attachment.
- `trace.zip` is re-typed `application/vnd.allure.playwright-trace`. Allure 2 embeds the Trace Viewer inline; Allure 3 opens it in a tab. The trace is not uploaded, but the viewer page needs internet access.
- `*-expected.png` / `*-actual.png` / `*-diff.png` from a failed `toHaveScreenshot` become one image-diff attachment. WebP baselines (1.62+) do not match that pattern and get no diff widget.
- `test.step` becomes an Allure step.

### WebdriverIO

In `wdio.conf.ts`:

```ts

export const config: WebdriverIO.Config = {
  reporters: [
    'spec',
    ['allure', {
      outputDir: 'allure-results',
      disableWebdriverStepsReporting: false,
      disableWebdriverScreenshotsReporting: false,
    }],
  ],
};
```

WebdriverIO and Appium failure evidence is the base test's `afterTest` hook (`qa/typescript/skills/evidence-capture`, Appium reference). This skill adds no second hook.

## Hierarchy: Feature → Story → Test

Behavior view: **Epic → Feature → Story**. Suite view: file → describe → test.

Vitest and Playwright use one runtime API, `allure-js-commons` — never the deprecated `allure` export of `allure-playwright` or `allure-vitest`. Every call returns a promise and is awaited:

```ts
import * as allure from 'allure-js-commons';
import { expect, it } from 'vitest';

it('Should_RefundOneLine_When_PartialRefundIsIssued', async () => {
  await allure.epic('Orders');
  await allure.feature('Refunds');
  await allure.story('Issue partial refund');
  await allure.severity('critical');
  await allure.description('Partial refund applies to a single line item only.');
  await allure.issue('https://yourco.atlassian.net/browse/ORDERS-512', 'ORDERS-512');
  await allure.tag('regression');

  const refund = await ordersClient.refundLine(orderId, lineId);

  expect(refund.status).toBe(201);
});
```

- `issue(url, name)` and `tms(url, name)` take the **URL first**.
- Severity is **test** severity: `'blocker'`, `'critical'`, `'normal'`, `'minor'` or `'trivial'`. `'blocker'` = "ship is blocked if this fails"; `'normal'` = "regression on a non-critical flow".
- `allure-js-commons/sync` exists for synchronous code; its `step()` must not return a promise. Tests here are async, so use the default import.

## Attachments (mandatory on failure path)

| Attachment | When | How |
|---|---|---|
| Request + response body | Every API test | `allure.attachment`, before the assertion |
| Screenshot, video, trace | Playwright UI tests, on failure | The config's evidence defaults (`evidence-capture`); `allure-playwright` attaches them |
| Recordings, HAR, chosen screenshots | When a test captures them on purpose | A fixture calls `testInfo.attach` (`evidence-capture`); `allure-playwright` copies it |
| Server logs around the test window | Optional | From Loki LogQL |

### API tests (Vitest) — attach the response body

```ts
import * as allure from 'allure-js-commons';
import { expect, it } from 'vitest';

async function attachResponse(response: ApiResponse): Promise<void> {
  await allure.attachment('response.json', response.bodyText, { contentType: 'application/json' });
}

it('Should_Return422_When_EmailIsInvalid', async () => {
  await allure.feature('Sign-up');
  const response = await usersClient.signUp({ email: 'not-an-email' });
  await attachResponse(response);

  expect(response.status).toBe(422);
});
```

Attach **before** the assertion so the body is in the report when the test fails.

### Playwright TS — attachments

Prefer `testInfo.attach` (`evidence-capture` §6): it lands in the Playwright HTML report and in Allure. Use `allure.attachment` only for Allure-only data:

```ts
import * as allure from 'allure-js-commons';
import { expect, test } from './fixtures';

test('Should_ShowOrderTotal_When_CartHasTwoItems', { tag: '@checkout' }, async ({ cartPage, seededCart }) => {
  await allure.feature('Checkout');
  await allure.story('Cart total');
  await allure.attachment('cart.json', JSON.stringify(seededCart), { contentType: 'application/json' });

  await cartPage.open();

  await expect(cartPage.total).toHaveText(seededCart.expectedTotal);
});
```

## Steps

`test.step('Sign in', async () => { … })` is captured by `allure-playwright` automatically and also shows in the Playwright trace — prefer it in Playwright Test. In Vitest, wrap a non-trivial workflow with `allure.step`:

```ts
await allure.step('Create the order', async () => {
  await ordersClient.create(order);
});
```

## Report CLI

One pin: `allure-commandline@2.46.1`. In CI it is installed with `npm i -g allure-commandline@2.46.1` on a runner with a Java runtime, then:

```bash
allure generate allure-results -o allure-report --clean
```

A shard matrix copies every shard's `allure-results/` into one folder before `generate`; new files are added to the existing ones.

## CI integration

Pattern is identical regardless of CI:

1. Run tests → `allure-results/` written.
2. Upload `allure-results/` as an artifact, **always** (even on failure).
3. Copy the previous report's `history/` into `allure-results/history/`.
4. `allure generate allure-results -o allure-report --clean`.
5. Publish to GitHub Pages / GitLab Pages / Azure static page.

The full platform YAML, sharding and evidence uploads live in `qa/cicd/typescript/skills/ci-pipelines`; the snippets below are the publish step only.

### GitHub Actions

```yaml
- uses: actions/setup-java@v5
  with: { distribution: temurin, java-version: '21' }

- name: Restore prior history from gh-pages
  uses: actions/checkout@v6
  with: { ref: gh-pages, path: gh-pages-prior }
  continue-on-error: true

- name: Generate Allure report with history
  if: always()
  run: |
    npm i -g allure-commandline@2.46.1
    mkdir -p allure-results/history
    cp -r gh-pages-prior/history/. allure-results/history/ 2>/dev/null || true
    allure generate allure-results -o allure-report --clean

- name: Publish Allure report
  if: always() && github.ref == 'refs/heads/main'
  uses: peaceiris/actions-gh-pages@v4
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_branch: gh-pages
    publish_dir: allure-report
```

### Azure Pipelines

```yaml
- task: PublishPipelineArtifact@1
  condition: always()
  inputs:
    targetPath: $(System.DefaultWorkingDirectory)/allure-results
    artifact: allure-results

- script: |
    npm i -g allure-commandline@2.46.1
    allure generate allure-results -o $(Build.ArtifactStagingDirectory)/allure-report --clean
  displayName: Generate Allure report
  condition: succeededOrFailed()

- task: PublishHtmlReport@1
  condition: succeededOrFailed()
  inputs:
    reportDir: $(Build.ArtifactStagingDirectory)/allure-report
    tabName: Allure
```

### GitLab CI

```yaml
publish:allure:
  stage: publish
  image: node:24
  needs: [test]
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
      when: always
  before_script:
    - apt-get update && apt-get install -y default-jre-headless
    - npm i -g allure-commandline@2.46.1
  script:
    - mkdir -p allure-results/history
    - cp -r public/history/. allure-results/history/ 2>/dev/null || true
    - allure generate allure-results --clean -o public
  artifacts:
    paths: [public/]
```

## History & trends

Trend graphs require a `history/` folder inside `allure-results/` populated from the previous run. The smoke test is "does the trend chart in the published report show > 1 bar".

Keep last 20–30 runs.

## Categories for triage — `categories.json`

Place at the project root and copy it into `allure-results/` before `allure generate` runs:

```json
[
  { "name": "Backend 5xx",       "matchedStatuses": ["broken", "failed"], "messageRegex": ".*status.*5\\d\\d.*" },
  { "name": "Auth issues",       "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*Unauthorized.*|.*Forbidden.*" },
  { "name": "Flaky timeouts",    "matchedStatuses": ["broken"],           "traceRegex":   ".*TimeoutError.*|.*timeout exceeded.*" },
  { "name": "Element not found", "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*locator.*not found.*|.*Element not found.*" },
  { "name": "Zod schema drift",  "matchedStatuses": ["broken", "failed"], "traceRegex":   ".*ZodError.*" }
]
```

## Rules

- One Allure adapter per project (`allure-vitest` **or** `allure-playwright` **or** `@wdio/allure-reporter`) — never two writing into the same `allure-results/`.
- The runtime API is `import * as allure from 'allure-js-commons'`, every call awaited; enable ESLint `no-floating-promises`.
- Every test calls `allure.feature(…)` + `allure.story(…)` + `allure.severity(…)`.
- API tests attach `response.bodyText` **before** assertions on failure paths.
- The Playwright evidence modes are the config asset's and are explained by `evidence-capture`; this skill never sets `trace`, `video` or `screenshot`.
- One Allure CLI pin, `allure-commandline@2.46.1`, equal to `qa/cicd/ci-conventions`.
- `allure-results/` uploaded as a CI artifact on **every** run, even on test failure.
- History preserved across runs (last 20–30 retained).
- Report published from `main` to a stable URL; PR builds publish to a PR-scoped URL or skip publish.
- `categories.json` lives at the project root and is copied into `allure-results/` during CI.

## What NOT to do

- No "always pass" wrappers around the test step — no `continue-on-error` / `continueOnError` / `|| true`. The test step fails the build; the upload and publish steps run anyway (`if: always()` / `condition: succeededOrFailed()` / `when: always`).
- No `import { allure } from 'allure-playwright'` — deprecated for removal in 3.13.0.
- No un-awaited `allure.*` call, and no `void` helper that calls one.
- No committing `allure-results/` to Git — it's an artifact.
- No `allure.feature('misc')` catch-all bucket.
- No `allure.description` that paraphrases the test name — describe behavior or link the spec.
- No attaching secrets / PII / auth tokens — sanitize before `allure.attachment(...)`.
- No `allure.feature(…)` calls outside `it`/`test` bodies — they won't bind to a test in the Vitest adapter.
- No `JSON.stringify(largeObject)` attachments > 1 MB — link to Loki / object storage instead.
- No unpinned or second Allure CLI (`allure-commandline` without a version, a downloaded allure2 tarball, an action that bundles its own Allure).
- No mixing `allure-playwright` with `allure-vitest` in the same project unless they write to **separate** result directories.

## Generation steps

1. Confirm runner (Vitest / Playwright / WebdriverIO), CI, publishing target, feature/severity taxonomy.
2. Install the matching adapter and `allure-js-commons` at 3.13.0, and `allure-commandline@2.46.1`.
3. Wire the reporter in `vitest.config.ts` / the canonical `playwright.config.ts` / `wdio.conf.ts`.
4. Add `allure.feature/story/severity/issue` calls to existing tests.
5. Attach response body **before** assertions in API tests; rely on the config's evidence defaults for UI attachments.
6. Drop `categories.json` at the project root.
7. Wire CI per the snippet for the team's CI platform; configure history retention.
8. Smoke a green build + a deliberate failing test; confirm trend, categories, attachments populate.

Inside a `Gate: none` plan task, skip the smoke run in the last step and report the wiring as "written, not run".

## Handoffs

- .NET Allure → `qa/reporting/dotnet/skills/test-reports`
- Java Allure → `qa/reporting/java/skills/test-reports`
- Native Playwright evidence → `qa/typescript/skills/evidence-capture`
- API test generation → `qa/typescript/skills/api-test-author/writer`
- UI test generation → `qa/typescript/skills/ui-test-author/playwright` / `qa/typescript/skills/ui-test-author/selenium` / `qa/typescript/skills/ui-test-author/appium`
- Test strategy → `qa/manual/test-strategy`
- Quality metrics dashboards → `qa/manual/quality-metrics`
- CI pipeline syntax → `qa/cicd/typescript/skills/ci-pipelines` (its `references/<ci>.md`) or `devops/<ci>`
