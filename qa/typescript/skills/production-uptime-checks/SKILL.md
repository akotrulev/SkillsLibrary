---
name: qa-production-uptime-checks-typescript
description: Use when authoring synthetic monitoring as code in Node 24 (22 supported) / TypeScript — scheduled API and Playwright-based browser checks against live staging/prod via Checkly (`@checkly/cli`). The "is it up right now" layer, distinct from CI pre-merge tests. Triggers: "add a prod uptime check", "synthetic monitor for the login flow", "monitoring as code". Not for pre-merge CI gates (`qa-ci-pipelines-typescript`) or load testing (`qa-load-testing-typescript`).
---

# Synthetic Monitoring as Code (Checkly · Node 24 / TypeScript) — **canonical stack**

This is the **canonical** stack of the `production-uptime-checks` family. It leads in TypeScript because
synthetic monitoring is largely a JS/TS world and **Checkly** is the strongest monitoring-as-code fit with the
library's stack defaults: browser checks are plain `@playwright/test` specs (so they reuse the fixtures and page
objects from `qa-ui-test-writer-playwright-typescript` verbatim), and the whole monitoring setup lives in
versioned TypeScript. The `dotnet` (Azure Application Insights availability tests) and `java` (Grafana Cloud
Synthetic Monitoring) siblings are **honest ports of the discipline, not the code** — Checkly has no .NET or
Java SDK, so each sibling re-expresses the same four ideas in its stack's most authentic tool.

`qa-api-typescript` loads this skill in its Step 3 when a suite is promoted to production probes; `qa-ui-typescript`
hands its critical journeys to that agent for the same purpose.

## What synthetic monitoring is (and what it is not)

**Synthetic monitoring** = scripted checks that run **on a schedule against a deployed, live target**
(staging/prod), continuously, alerting a human when the target is down or degraded. A synthetic check is a
**continuously-running assertion**: you don't watch the result, you alert on its *failure*.

It is **not** a CI test (once, pre-merge, against an ephemeral env — `qa-ci-pipelines-*`; § The boundary), not a
load test (`qa-load-testing-typescript`), and not a journey author: it reuses the suite's page objects and adds
the **assertion + scheduling + alerting + evidence layer**.

> **The discipline this skill encodes.** A synthetic check is only worth running if its **failure reaches a
> human fast, means something, and explains itself**. So:
>
> 1. **Two check types, both as code** — cheap **API/uptime checks** (status + latency + body shape) for "is the
>    endpoint up", and **browser checks** (a real user journey) for "can a user actually do the thing". Both
>    live in the repo, reviewed and deployed via a CLI — never hand-clicked in a SaaS UI.
> 2. **Assert an SLA, not just pass/fail** — a 200 that takes 8 seconds is a regression. Gate on a **latency
>    budget** (`degradedResponseTime`/`maxResponseTime`) and body shape, not just the status code.
> 3. **Alert on the failure, with its evidence** — a check no one is paged on does nothing, and a page that
>    says only "failed" sends on-call to re-run it by hand. Wire an alert channel and a bounded retry, and keep
>    the trace, video and screenshot of every failed browser run.
> 4. **Wait on a condition, never a sleep** — Playwright auto-waits; never `waitForTimeout`/`setTimeout`.

## Decision matrix — which check for which job

| You want to know… | Check type | Construct | Gate on |
|---|---|---|---|
| Is the API/health endpoint up and fast? | **API / uptime check** | `ApiCheck` + `AssertionBuilder` | status + `responseTime` + `jsonBody` shape + `maxResponseTime` |
| Can a user log in / search / check out? | **Browser check** | `BrowserCheck` (a `@playwright/test` spec) | the journey completes + the page objects' intent assertions |
| Does a multi-call API flow work end-to-end? | **Multi-step check** | `MultiStepCheck` (Playwright `request` spec) | each step's status + chained assertions |
| Is a raw TCP port / service reachable? | **TCP check** | `TcpCheck` | `responseTime` + `responseData` |
| Should several checks share schedule/locations/alerts? | **group** | `CheckGroup` | (shared config, not itself a check) |

Every endpoint gets a cheap API check; every business-critical journey a browser check.

## Stack

- Node 24 (22 maintenance) + TypeScript (strict mode) — **no `waitForTimeout` / `setTimeout`-as-wait** anywhere
- `checkly` (npm) — constructs import from `checkly/constructs`; the `checkly` CLI is the deploy tool
- `@playwright/test` — browser-check bodies are plain Playwright specs on the writer's fixtures
  (`qa/typescript/skills/ui-test-author/playwright/assets/fixtures.ts`). This skill pins nothing; the suite's
  version is the writer's **Versions** table
- **The Checkly runtime decides which Playwright runs the check.** Pin `runtimeId` in `checkly.config.ts` to the
  newest id `npx checkly runtimes` lists, and read the Playwright version that runtime ships from the same
  output. It can lag the suite's own version: a browser-check spec, and every page object it imports, uses only
  APIs that runtime has (a 1.64-only API such as `locator.within()` fails there — use `parent.locator(child)`)
- Checkly cloud — runs the deployed checks on a schedule from global `locations`; alerting + results live there
- Secrets via env, read lazily, never logged (`CHECKLY_API_KEY`, `CHECKLY_ACCOUNT_ID`, target creds)

```
monitoring/
├── checkly.config.ts       project identity (logicalId) + shared check defaults + runtime + CLI config
├── src/
│   ├── alert-channels.ts   EmailAlertChannel / SlackAlertChannel / PagerdutyAlertChannel (shared)
│   ├── api.check.ts        ApiCheck — the uptime/health + SLA layer
│   ├── login.check.ts      BrowserCheck pointing at login.spec.ts
│   └── __checks__/
│       └── login.spec.ts   a @playwright/test spec on tests/fixtures.ts
└── package.json            "checkly" devDependency; npm scripts wrapping the CLI
```

## Monitoring-as-code — the project, the constructs, the lifecycle

**`checkly.config.ts`** — project identity plus shared defaults inherited by every check. `logicalId` is the
resource-graph key: renaming it deletes and recreates everything. Checks run from several `locations` to catch
regional outages; browser checks run a little less often than API checks; `testMatch` auto-discovers the specs.

```typescript
import { defineConfig } from 'checkly';
import { Frequency } from 'checkly/constructs';

export default defineConfig({
  projectName: 'Acme Storefront Monitoring',
  logicalId: 'acme-storefront-monitoring',
  checks: {
    frequency: Frequency.EVERY_5M,
    locations: ['us-east-1', 'eu-west-1'],
    tags: ['storefront', 'production'],
    browserChecks: {
      frequency: Frequency.EVERY_10M,
      testMatch: '**/__checks__/**/*.spec.ts',
    },
  },
  cli: { runLocation: 'eu-west-1', reporters: ['list'] },
});
```

Add `runtimeId` under `checks`, set to the newest id `npx checkly runtimes` prints — a pinned runtime keeps the
checks from drifting when Checkly changes its default.

**The lifecycle** — this *is* the synthetic-vs-CI boundary (§ The boundary):

| Command | Does |
|---|---|
| `npx checkly login` | one-time; in CI, `CHECKLY_API_KEY` + `CHECKLY_ACCOUNT_ID` instead |
| `npx checkly test --record` | a **dry-run** on Checkly's cloud — nothing persisted; gates a PR, and records the run's results |
| `npx checkly deploy --force` | **persists** the checks — they now run on schedule and alert |
| `npx checkly trigger` | runs the deployed checks on demand (a post-deploy smoke) |
| `npx checkly runtimes` | lists the runtimes and the Playwright version each ships |

Every construct's **first constructor arg is a stable `logicalId`** — Checkly diffs the resource graph by it.

## Check type 1 — API / uptime checks (status + latency + body shape)

`ApiCheck` is the cheap layer: hit an endpoint on a schedule, assert status, **latency budget**, and body shape.
Above `degradedResponseTime` the run is DEGRADED (an alert if the channel sends degraded); above
`maxResponseTime` it FAILS. The URL interpolates `{{BASE_URL}}` from the environment.

```typescript
import { ApiCheck, AssertionBuilder, RetryStrategyBuilder } from 'checkly/constructs';
import { emailChannel, slackChannel } from './alert-channels';

new ApiCheck('storefront-health-check', {
  name: 'Storefront API — health + SLA',
  alertChannels: [emailChannel, slackChannel],
  degradedResponseTime: 2000,
  maxResponseTime: 5000,
  request: {
    method: 'GET',
    url: '{{BASE_URL}}/api/health',
    followRedirects: true,
    skipSSL: false,
    assertions: [
      AssertionBuilder.statusCode().equals(200),
      AssertionBuilder.responseTime().lessThan(2000),
      AssertionBuilder.jsonBody('$.status').equals('healthy'),
      AssertionBuilder.jsonBody('$.dependencies.database').equals('up'),
    ],
  },
  retryStrategy: RetryStrategyBuilder.linearStrategy({ maxRetries: 2, baseBackoffSeconds: 30, sameRegion: false }),
});
```

An authenticated check mints its token in a **setup script** (`qa-test-login-tokens-typescript`).

## Check type 2 — browser checks (a real user journey, reusing your page objects)

A `BrowserCheck` body is a **plain `@playwright/test` spec** on the same fixtures the CI suite uses — the same
page objects, the same intent-not-selectors discipline. This skill does **not** author the journey; it
schedules it against the live target, alerts on it and keeps its evidence.

```typescript
import { BrowserCheck, Frequency } from 'checkly/constructs';
import * as path from 'path';
import { emailChannel, pagerdutyChannel } from './alert-channels';

new BrowserCheck('storefront-login-journey', {
  name: 'Storefront — login + add-to-cart journey',
  frequency: Frequency.EVERY_10M,
  alertChannels: [emailChannel, pagerdutyChannel],
  code: { entrypoint: path.join(__dirname, '__checks__/login.spec.ts') },
});
```

`monitoring/src/login.check.ts` — a broken checkout journey pages on-call.

```typescript
import { expect, test } from '../../../tests/fixtures';

test.use({
  trace: 'retain-on-failure',
  video: 'retain-on-failure',
  screenshot: { mode: 'only-on-failure', fullPage: true },
});

test('Should_AddFeaturedItemToCart_When_SyntheticUserSignsIn', async ({ loginPage, cartPage, testUser }) => {
  await loginPage.signIn(testUser);

  await cartPage.addFirstFeaturedItem();

  await expect(cartPage.itemCount).toHaveText('1');
});
```

`monitoring/src/__checks__/login.spec.ts`. `testUser` reads `E2E_USER` / `E2E_PASSWORD` lazily — set them as
Checkly **secret** environment variables for the synthetic user. The spec signs in itself: Checkly runs the
spec, not the suite's `playwright.config.ts`, so there is no setup project and no `storageState` file.

## Evidence when a probe fails

A page at 3 a.m. must say *what* broke, not only *that* something did.

- **Browser checks keep the R7 evidence.** Checkly runs the spec, not the canonical config, so the spec states
  the failure-evidence defaults itself with the `test.use` above: trace and video `retain-on-failure`, a
  full-page screenshot `only-on-failure`. A passing run keeps nothing, so every-minute probes stay cheap. Never
  `'on'` — a probe runs thousands of times a week.
- **Read the failed run before re-running it.** The failed run's result page carries what the run kept
  (screenshots, trace, video, logs). A downloaded `trace.zip` is read exactly like a CI failure:
  `npx playwright trace open <zip>`, then `trace errors` and `trace actions` (`qa/typescript/skills/evidence-capture`,
  "Reading a failure"). Check that a failed run's result shows the trace before the first incident relies on it
  — what is kept, and for how long, is the Checkly account's setting.
- **API checks** keep the request, the response and the timing phases of a failed run in the check result —
  assert the body shape (`jsonBody`) so the failure names the field that broke, not only the status.
- **PII.** A trace and a video carry what the synthetic user typed and saw: it is a dedicated, disposable
  account, never a real customer.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Alerting + SLA
thresholds — the part that makes it a monitor**; **Secrets from env, never logged**; **The CI workflow — gate,
then deploy**.

## The boundary — `checkly test` (CI gate) vs `checkly deploy` (continuous monitor)

| | `checkly test` | `checkly deploy` |
|---|---|---|
| **When** | Pre-merge / pre-promote, ad-hoc | Once; then runs on schedule forever |
| **Against** | The deployed preview/staging | The live prod/staging target |
| **Persisted?** | No (dry-run) | Yes (a continuous monitor) |
| **Alerts?** | No (it's a gate — green/red) | Yes (pages on failure/degradation) |
| **Role** | A **CI test** (`qa-ci-pipelines-*` territory) | A **synthetic monitor** (this skill) |

**One spec, two execution modes:** the pipeline runs `checkly test --record` to gate the merge, then (on main,
after deploy) `checkly deploy --force` — the workflow steps are in `references/details.md`.

## Anti-patterns

- **Asserting only the status code.** A 200 that takes 9 seconds is a user-facing regression. *Fix:* a
  **latency budget** and the body **shape**, not just `statusCode().equals(200)`.
- **A check with no alert channel.** It goes red and no one knows. *Fix:* an `alertChannel` on every check.
- **A failed browser run with no trace.** On-call re-runs it by hand and the transient evidence is gone. *Fix:*
  the spec's `test.use` keeps trace, video and screenshot on failure.
- **`maxRetries: 5` to stop the alerts.** It delays the page while users suffer. *Fix:* 1–2 retries,
  `sameRegion: false`, and **fix the flakiness** (`qa-flaky-test-quarantine-typescript`).
- **Re-authoring the journey inside the check.** *Fix:* import the suite's fixtures.
- **A hard-coded URL or credential in `checkly.config.ts`.** *Fix:* `{{BASE_URL}}`, `secret: true` variables,
  `CHECKLY_API_KEY` from the CI secret store.

## Rules (hard constraints)

- **Synthetics run against a LIVE target, post-deploy, on a schedule — never as the merge gate.** `checkly test`
  (dry-run) may gate a PR; `checkly deploy` is the continuous monitor.
- **Assert an SLA, not just a status code** — a latency budget and the body shape on every API check.
- **Every check has an alert channel.** Page on critical journeys, email/Slack on the rest; `sendDegraded` on
  for SLA breaches.
- **Every browser check keeps its failure evidence** — trace and video `retain-on-failure`, a full-page
  screenshot `only-on-failure` — and a failed run is read (`qa-evidence-capture-typescript`) before it is re-run.
- **Retries are bounded** — 1–2, `sameRegion: false`; never cranked to silence alerts.
- **The runtime is pinned**, and browser-check code uses only the Playwright APIs that runtime ships.
- **Wait on a condition, never a sleep.**
- **Browser checks reuse the suite's fixtures and page objects** — this skill never authors a journey.
- **Secrets from env, never logged.** Test names `Should_X_When_Y`; one logical assertion; no conditional logic;
  no inline comments in the code.

## Cross-references

- `qa-production-uptime-checks-dotnet` (Application Insights availability tests) · `qa-production-uptime-checks-java`
  (Grafana Cloud Synthetic Monitoring) — the discipline ported, not the code.
- `qa-ui-test-writer-playwright-typescript` — the fixtures, page objects and journeys the **browser checks
  reuse**.
- `qa-evidence-capture-typescript` — the evidence modes the browser-check spec sets, and how a failed run's
  trace is read.
- `qa-load-testing-typescript` — throughput, not uptime.
- `qa-ci-pipelines-typescript` — the pre-merge gate against ephemeral envs; where `checkly test --record` and
  `checkly deploy` are wired.
- `qa-test-login-tokens-typescript` — M2M / test-user tokens for checks that hit an **authenticated** endpoint.
- `qa-flaky-test-quarantine-typescript` — a synthetic that needs `maxRetries` cranked to stay green is flaky.
