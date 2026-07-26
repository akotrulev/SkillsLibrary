---
name: qa-production-uptime-checks-typescript
description: Use when authoring synthetic monitoring as code in Node 24 (22 supported) / TypeScript — scheduled API and Playwright-based browser checks against live staging/prod via Checkly (`@checkly/cli`). The "is it up right now" layer, distinct from CI pre-merge tests. Triggers: "add a prod uptime check", "synthetic monitor for the login flow", "monitoring as code".
---

# Synthetic Monitoring as Code (Checkly · Node 20 / TypeScript) — **canonical stack**

This is the **canonical** stack of the `qa/typescript/skills/production-uptime-checks/` family. It leads in TypeScript because
synthetic monitoring is largely a JS/TS world and **Checkly `@checkly/cli`** is the strongest
monitoring-as-code fit with the library's stack defaults: browser checks are plain `@playwright/test` specs
(so they reuse the page objects from `qa-ui-test-writer-playwright-typescript` verbatim), and the whole
monitoring setup lives in versioned TypeScript. The `dotnet` (Azure Application Insights availability tests)
and `java` (Grafana Cloud Synthetic Monitoring) siblings are **honest ports of the discipline, not the
code** — Checkly has **no official .NET or Java SDK** (TS/JS-only; browser checks are Playwright-JS), so each
sibling re-expresses the same four ideas in its stack's most authentic tool. The *concepts* are identical;
the tool changes.

## What synthetic monitoring is (and what it is not)

**Synthetic monitoring** = scripted checks that run **on a schedule against a deployed, live target**
(staging/prod), continuously, alerting a human when the target is down or degraded. A synthetic check is a
**continuously-running assertion**: you don't watch the result, you alert on its *failure*.

It is **not**:

- a **CI test** — CI tests run **once, pre-merge, against an ephemeral env** to gate a change
  (`qa-ci-pipelines-*`). A synthetic runs **forever, post-deploy, against the real thing**. Same Playwright
  muscle, opposite execution model. (Checkly's selling point: the *same* spec serves both — see § The boundary.)
- a **load test** — `qa-performance-k6` drives throughput to find the breaking point. A synthetic fires one
  scripted journey every N minutes to answer "is it working *right now*". (Note the overlap: k6 *can* run as a
  synthetic via Grafana Synthetic Monitoring — the Java sibling.)
- a **journey author** — this skill *reuses* the page objects authored by
  `qa-ui-test-writer-playwright-typescript`; it is the **assertion + scheduling + alerting layer**, not a new author.

> **The discipline this skill encodes.** A synthetic check is only worth running if its **failure reaches a
> human fast and means something**. So:
>
> 1. **Two check types, both as code** — cheap **API/uptime checks** (status + latency + body shape) for the
>    "is the endpoint up" layer, and **browser checks** (a real user journey) for the "can a user actually do
>    the thing" layer. Both live in the repo, reviewed and deployed via a CLI — never hand-clicked in a SaaS UI.
> 2. **Assert an SLA, not just pass/fail** — a 200 that takes 8 seconds is a regression. Gate on a **latency
>    budget** (`degradedResponseTime`/`maxResponseTime`) and body shape, not just the status code.
> 3. **Alert on the failure** — a check no one is paged on is a check that does nothing. Wire an alert
>    channel and a retry strategy so a single transient blip doesn't page someone at 3am, but a real outage does.
> 4. **Wait on a condition, never a sleep** — the same discipline as the rest of the library. Poll on a
>    condition; never `waitForTimeout`/`setTimeout` to "let it settle".

## Decision matrix — which check for which job

| You want to know… | Check type | Construct | Gate on |
|---|---|---|---|
| Is the API/health endpoint up and fast? | **API / uptime check** | `ApiCheck` + `AssertionBuilder` | status + `responseTime` + `jsonBody` shape + `maxResponseTime` |
| Can a user log in / search / check out? | **Browser check** | `BrowserCheck` (a `@playwright/test` spec) | the journey completes + the page objects' intent assertions |
| Does a multi-call API flow work end-to-end? | **Multi-step check** | `MultiStepCheck` (Playwright `request` spec) | each step's status + chained assertions |
| Is a raw TCP port / service reachable? | **TCP check** | `TcpCheck` | `responseTime` + `responseData` |
| Should several checks share schedule/locations/alerts? | **group** | `CheckGroup` | (shared config, not itself a check) |

**Rule of thumb:** *every endpoint* gets a cheap API check (seconds to run, run them often). *Every
business-critical journey* (login, checkout, search) gets a browser check (run less often, costs more). Don't
browser-check what an API check can prove.

## Stack

- Node 20 + TypeScript (strict mode) — **no `waitForTimeout` / `setTimeout`-as-wait** anywhere
- `checkly` (npm) — constructs import from `checkly/constructs`; the `checkly` CLI is the deploy tool
- `@playwright/test` — browser-check bodies are plain Playwright specs; **reuse** the page objects from
  `qa-ui-test-writer-playwright-typescript` (cross-link — this skill does not author them)
- Checkly cloud — runs the deployed checks on a schedule from global `locations`; alerting + dashboards live there
- Secrets via env, read lazily, never logged (`CHECKLY_API_KEY`, `CHECKLY_ACCOUNT_ID`, target creds)

```
monitoring/
├── checkly.config.ts              ← project identity (logicalId) + shared check defaults + CLI config
├── src/
│   ├── alert-channels.ts          ← EmailAlertChannel / SlackAlertChannel / PagerdutyAlertChannel (shared)
│   ├── api.check.ts               ← ApiCheck — the uptime/health + SLA layer
│   ├── home.check.ts              ← BrowserCheck pointing at home.spec.ts
│   └── __checks__/
│       └── home.spec.ts           ← a @playwright/test spec — REUSES tests/pages/* page objects
└── package.json                   ← "checkly" devDependency; npm scripts wrapping the CLI
```

## Monitoring-as-code — the project, the constructs, the lifecycle

The whole monitoring setup is **versioned TypeScript** deployed to Checkly's cloud, which then runs the
checks continuously from global locations. Nothing is hand-clicked in the UI.

**`checkly.config.ts`** — project identity (`logicalId`, a *stable* identifier — changing it deletes and
recreates everything) plus shared defaults inherited by every check:

```typescript
import { defineConfig } from 'checkly';
import { Frequency } from 'checkly/constructs';

export default defineConfig({
  projectName: 'Acme Storefront Monitoring',
  logicalId: 'acme-storefront-monitoring',          // STABLE — the resource-graph key; do not rename casually
  checks: {
    frequency: Frequency.EVERY_5M,                  // default cadence; per-check overrides allowed
    locations: ['us-east-1', 'eu-west-1'],          // run from multiple regions to catch regional outages
    tags: ['storefront', 'production'],
    runtimeId: '2024.02',                           // pin the runtime so checks don't drift on upgrades
    browserChecks: {
      frequency: Frequency.EVERY_10M,               // browser checks cost more — run them a little less often
      testMatch: '**/__checks__/**/*.spec.ts',      // auto-discover Playwright specs as browser checks
    },
  },
  cli: { runLocation: 'eu-west-1', reporters: ['list'] },
});
```

**The lifecycle is two verbs** — this *is* the synthetic-vs-CI boundary (see § The boundary):

```bash
npx checkly login                        # one-time, or CHECKLY_API_KEY + CHECKLY_ACCOUNT_ID in CI
npx checkly test --record                # DRY-RUN on Checkly's cloud — nothing persisted; gate a PR on this
npx checkly deploy --force               # PERSIST the checks → they now run on schedule + alert, forever
npx checkly trigger                      # run the already-deployed checks on demand (e.g. post-deploy smoke)
```

Every construct's **first constructor arg is a stable `logicalId`** — Checkly diffs the resource graph by it
to know what to create/update/delete on `deploy`.

## Check type 1 — API / uptime checks (status + latency + body shape)

`ApiCheck` is the cheap layer: hit an endpoint on a schedule, assert status, **latency budget**, and body
shape. **Assert the SLA, not just the status** — that's what makes it a monitor and not a ping.

```typescript
import { ApiCheck, AssertionBuilder } from 'checkly/constructs';
import { emailChannel, slackChannel } from './alert-channels';

new ApiCheck('storefront-health-check', {
  name: 'Storefront API — health + SLA',
  alertChannels: [emailChannel, slackChannel],
  degradedResponseTime: 2000,            // > 2s → DEGRADED (alerts if the channel sends degraded) — the SLA warn
  maxResponseTime: 5000,                 // > 5s → FAILED — the hard latency budget; a slow 200 is a regression
  request: {
    method: 'GET',
    url: '{{BASE_URL}}/api/health',      // {{ENV_VAR}} interpolation — base URL from the environment, not hard-coded
    followRedirects: true,
    skipSSL: false,
    assertions: [
      AssertionBuilder.statusCode().equals(200),
      AssertionBuilder.responseTime().lessThan(2000),          // latency assertion = the SLA, asserted every run
      AssertionBuilder.jsonBody('$.status').equals('healthy'),  // body SHAPE, not just 2xx
      AssertionBuilder.jsonBody('$.dependencies.database').equals('up'),
    ],
  },
  retryStrategy: RetryStrategyBuilder.fixedStrategy({ maxRetries: 2, baseBackoffSeconds: 30 }),
});
```

A check that needs auth uses a **setup script** to mint a token (cross-link `qa-test-login-tokens-typescript`
for M2M tokens against the live target) and stashes it on the request — never a hard-coded credential.

## Check type 2 — browser checks (a real user journey, reusing your page objects)

A `BrowserCheck` body is a **plain `@playwright/test` spec**. It **reuses the page objects** authored by
`qa-ui-test-writer-playwright-typescript` — same intent-not-selectors discipline, same `getByRole`/`getByLabel`
locators. This skill does **not** author the journey; it schedules it against the live target and alerts on it.

```typescript
// monitoring/src/home.check.ts — wraps the spec as a scheduled, alerting browser check
import { BrowserCheck, Frequency } from 'checkly/constructs';
import * as path from 'path';
import { emailChannel, pagerdutyChannel } from './alert-channels';

new BrowserCheck('storefront-login-journey', {
  name: 'Storefront — login + add-to-cart journey',
  frequency: Frequency.EVERY_10M,
  alertChannels: [emailChannel, pagerdutyChannel],   // a broken checkout journey pages on-call
  code: { entrypoint: path.join(__dirname, '__checks__/login.spec.ts') },
});
```

```typescript
// monitoring/src/__checks__/login.spec.ts — a NORMAL Playwright spec; reuses tests/pages/* verbatim
import { test, expect } from '@playwright/test';
import { LoginPage } from '../../../tests/pages/login.page';   // ← the SAME page object the CI suite uses
import { CartPage } from '../../../tests/pages/cart.page';

test('user can log in and add an item to the cart', async ({ page }) => {
  const login = new LoginPage(page);
  await login.goto();
  // creds from env, read lazily, NEVER logged or committed — set as Checkly secret env vars
  await login.signInAs(process.env.SYNTHETIC_USER!, process.env.SYNTHETIC_PASSWORD!);

  const cart = new CartPage(page);
  await cart.addFirstFeaturedItem();

  // Playwright auto-waits on the condition — NO waitForTimeout to "let the cart update"
  await expect(cart.itemCount).toHaveText('1');
});
```

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Alerting + SLA thresholds — the part that makes it a monitor**.

## Secrets from env, never logged

Target URLs, API keys, and test-user creds come from the environment — read lazily, never committed, never
logged. Checkly's own env vars carry a **`secret: true`** flag that makes them write-only (masked in output,
traces, and the UI):

```typescript
// In a check or group:
environmentVariables: [
  { key: 'BASE_URL', value: 'https://staging.acme.example' },
  { key: 'SYNTHETIC_PASSWORD', value: process.env.SYNTHETIC_PASSWORD!, secret: true },  // write-only, masked
],
```

```bash
# CI auth — never in checkly.config.ts:
export CHECKLY_API_KEY=...        # from the CI secret store
export CHECKLY_ACCOUNT_ID=...
npx checkly test -e BASE_URL=https://staging.acme.example --record   # override per run
```

## The boundary — `checkly test` (CI gate) vs `checkly deploy` (continuous monitor)

This is the synthetic-vs-CI distinction made concrete, and it's the whole reason the family exists:

| | `checkly test` | `checkly deploy` |
|---|---|---|
| **When** | Pre-merge / pre-promote, ad-hoc | Once; then runs on schedule forever |
| **Against** | The deployed preview/staging | The live prod/staging target |
| **Persisted?** | No (dry-run) | Yes (a continuous monitor) |
| **Alerts?** | No (it's a gate — green/red) | Yes (pages on failure/degradation) |
| **Role** | A **CI test** (`qa-ci-pipelines-*` territory) | A **synthetic monitor** (this skill) |

The payoff of monitoring-as-code: **one spec, two execution modes** — you don't maintain a separate CI test
and a separate monitor. The CI pipeline runs `checkly test --record` to gate the merge, then (on merge to
main, after deploy) runs `checkly deploy --force` to promote the monitoring config:

```yaml
# .github/workflows — cross-link qa-ci-pipelines for the full pipeline
- name: Synthetic dry-run (gate the PR)
  run: npx checkly test --record --reporter=github
  env: { CHECKLY_API_KEY: ${{ secrets.CHECKLY_API_KEY }}, CHECKLY_ACCOUNT_ID: ${{ secrets.CHECKLY_ACCOUNT_ID }} }

- name: Deploy the monitors (main only, post-deploy)
  if: github.ref == 'refs/heads/main'
  run: npx checkly deploy --force
  env: { CHECKLY_API_KEY: ${{ secrets.CHECKLY_API_KEY }}, CHECKLY_ACCOUNT_ID: ${{ secrets.CHECKLY_ACCOUNT_ID }} }
```

## Anti-patterns

- **Asserting only the status code.** A 200 that takes 9 seconds is a user-facing regression a status check
  misses. *Fix:* assert a **latency budget** (`maxResponseTime` / `responseTime().lessThan(...)`) and the body
  **shape** (`jsonBody('$.x')`), not just `statusCode().equals(200)`.
- **A check with no alert channel.** It runs, it goes red, no one knows. *Fix:* attach an `alertChannel`
  (page on critical journeys, email/Slack on the rest); a synthetic *is* its alert.
- **`maxRetries: 5` to stop the alerts.** That's the flaky-quarantine masking knob — it just delays the page
  while users suffer. *Fix:* bound retries (1–2), retry `sameRegion: false` to tell a regional blip from a real
  outage, and **fix the underlying flakiness** (cross-link `qa-flaky-test-quarantine-typescript`).
- **`page.waitForTimeout(3000)` to "let it settle".** A fixed sleep is flaky and slow, and it's banned across
  this library. *Fix:* Playwright auto-waits; assert on the condition (`expect(locator).toHaveText(...)`).
- **Hand-clicking checks in the Checkly UI.** Unversioned, unreviewed, undiffable, lost on account churn.
  *Fix:* monitoring-as-code in `checkly.config.ts` + constructs, deployed via the CLI from CI.
- **Running synthetics as the merge gate against an ephemeral env.** That's a CI test, not a monitor — wrong
  tool. *Fix:* `checkly test` gates the PR; `checkly deploy` runs the monitor against the *live* target. Keep
  them distinct (`qa-ci-pipelines-*`).
- **Re-authoring the journey inside the check.** Duplicated selectors that drift from the CI suite. *Fix:*
  the browser-check spec **imports the same page objects** from `qa-ui-test-writer-playwright-typescript`.
- **A hard-coded URL or credential in `checkly.config.ts`.** Committed secrets, no env separation. *Fix:*
  `{{BASE_URL}}` interpolation + `secret: true` env vars + `CHECKLY_API_KEY` from the CI secret store, lazily.

## Examples

**End-to-end: a cheap uptime check + a critical-journey browser check, sharing a group and an alert.**

```typescript
// monitoring/src/storefront.ts
import { ApiCheck, BrowserCheck, AssertionBuilder, Frequency } from 'checkly/constructs';
import * as path from 'path';
import { storefrontGroup } from './alert-channels';   // group carries locations + alerts + retry

// Cheap, frequent: is the API up and within SLA?
new ApiCheck('home-api', {
  name: 'Home API',
  group: storefrontGroup,
  frequency: Frequency.EVERY_1M,                       // run the cheap one often
  maxResponseTime: 3000,
  request: {
    method: 'GET',
    url: '{{BASE_URL}}/api/products?featured=true',
    assertions: [
      AssertionBuilder.statusCode().equals(200),
      AssertionBuilder.responseTime().lessThan(1500),
      AssertionBuilder.jsonBody('$.items.length').greaterThan(0),  // shape: there ARE featured products
    ],
  },
});

// Expensive, less frequent: can a user actually complete the journey?
new BrowserCheck('checkout-journey', {
  name: 'Checkout journey',
  group: storefrontGroup,
  frequency: Frequency.EVERY_15M,
  code: { entrypoint: path.join(__dirname, '__checks__/checkout.spec.ts') },  // reuses tests/pages/*
});
```

The API check fires every minute and pages if the storefront is down or slow; the browser check fires every
15 minutes and pages if a user can't actually check out — both alert through the group's channel, both
deployed with `checkly deploy`, both runnable as a PR gate with `checkly test --record`.

## Rules (hard constraints)

- **Synthetics run against a LIVE target, post-deploy, on a schedule — never as the merge gate.** `checkly
  test` (dry-run) may gate a PR; `checkly deploy` is the continuous monitor. Keep the two modes distinct
  (`qa-ci-pipelines-*` owns the pre-merge gate against ephemeral envs).
- **Assert an SLA, not just a status code.** Every API check gates on a **latency budget**
  (`maxResponseTime` / `responseTime().lessThan`) and body **shape** (`jsonBody`), not only `200`.
- **Every check has an alert channel.** A synthetic *is* its alert; an un-alerted check does nothing. Page on
  critical journeys, email/Slack on the rest; `sendDegraded` on for SLA breaches.
- **Retries are bounded.** 1–2, `sameRegion: false` to distinguish a regional blip from a real outage —
  never cranked to silence alerts (that's the flaky-quarantine masking anti-pattern).
- **Wait on a condition, never a sleep.** Playwright auto-waits; `expect(...).toHaveText/poll`. No
  `waitForTimeout` / `setTimeout`-as-wait anywhere.
- **Monitoring-as-code, in the repo.** Checks live in `checkly.config.ts` + constructs, reviewed and deployed
  via the CLI — never hand-clicked in the SaaS UI.
- **Browser checks REUSE the page objects** from `qa-ui-test-writer-playwright-typescript` — intent, not
  selectors; this skill is the assertion/scheduling/alerting layer, not a journey author.
- **Secrets from env, never logged.** `{{BASE_URL}}` interpolation, `secret: true` env vars, `CHECKLY_API_KEY`
  from the CI secret store, read lazily. Tests: behavioral names, one logical assertion, no conditional logic.

## Cross-references

- `qa-production-uptime-checks-dotnet` — same four ideas, the **.NET-native** tool: **Azure Application Insights
  availability tests** (Standard tests as config-as-code via Bicep/Terraform + custom `TrackAvailability` with
  a Playwright-.NET / `HttpClient` probe pushing results to App Insights). Honest divergence: **no Checkly
  .NET SDK** — App Insights is the way to write the probe in C# end-to-end. Discipline ported, not code.
- `qa-production-uptime-checks-java` — same four ideas, the **JVM/observability-native** tool: **Grafana Cloud
  Synthetic Monitoring** (k6 scripts + HTTP/ping/TCP probe checks, managed via the Grafana Terraform provider)
  — matches the library's Grafana observability default. Honest divergence: **no Checkly Java SDK**. Discipline
  ported, not code.
- `qa-ui-test-writer-playwright-typescript` — authors the page objects + journeys that the **browser checks
  reuse**. This skill schedules and alerts on them; it does not author them. Mirror its intent-not-selectors discipline.
- `qa-performance-k6` — load testing (throughput), NOT uptime. The overlap: k6 *can* run as a synthetic via
  Grafana Synthetic Monitoring (the Java sibling). Synthetics check "is it working"; k6 checks "how much can it take".
- `qa-ci-pipelines` (github-actions / azure-pipelines / gitlab-ci references) — the **pre-merge gate against
  ephemeral envs** boundary; also where `checkly test --record` (gate) + `checkly deploy` (promote) are wired.
- `qa-test-login-tokens-typescript` — M2M / test-user tokens for checks that hit an **authenticated** live
  endpoint (setup script mints the token; creds from env, lazily).
- `qa-flaky-test-quarantine-typescript` — a synthetic that needs `maxRetries` cranked to stay green is
  *flaky*; bound the retries and fix the root cause rather than masking the alert.
- `qa-test-reports-typescript` — surfacing `checkly test --record` run results / traces (the synthetic's
  reporting layer beyond the Checkly dashboard).
