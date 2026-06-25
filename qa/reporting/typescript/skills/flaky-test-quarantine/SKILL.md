---
name: qa-flaky-test-quarantine-typescript
description: Detect, retry, **quarantine**, and report flaky tests in a Node 20 + TypeScript suite (Playwright for e2e, Vitest for unit). Triggers: "this Playwright test is flaky, stop it blocking CI", "quarantine our flaky e2e tests but keep running them", "retry failed tests in Playwright/Vitest".
---

# Flaky-Test Quarantine (Node 20 + TypeScript / Playwright + Vitest)

This is the **TypeScript sibling** of the single-node `qa/reporting/typescript/skills/flaky-test-quarantine/` family, **ported** from
the canonical **Java/TestNG** file (`qa-flaky-test-quarantine-java`). The **four-move loop** is identical;
only the runner API and the quarantine filter change. The TS stack has one genuine advantage worth leading
with: **Playwright detects flakiness natively** — a test that fails then passes on retry is reported with a
distinct **"flaky"** status, no extra tooling. That makes Move 1 (Detect) nearly free here.

## What "flaky" means (and what it does not)

A **flaky test** passes and fails **non-deterministically against the same code** — a race, a timing
assumption, an order dependency, a real-but-rare backend hiccup. It is *not*:

- a test that **always** fails on a change → that's a **caught regression**, fix the code;
- a test that **always** fails regardless of the change → that's a **broken test**, fix the test.

> **The discipline this skill encodes.** A retry is a **band-aid**, not a cure. Retrying to green **hides
> real bugs** (a 1-in-3 race is a real bug) and lets new flakiness slip in unnoticed. So the policy is a
> **four-move loop**, not "just add retries":
>
> 1. **Detect** — surface which tests are flaky (Playwright's "flaky" status + Allure history), don't guess.
> 2. **Retry — once, bounded** — absorb *true* transients on the gate so one hiccup doesn't fail a clean PR.
> 3. **Quarantine** — move a *known* flaky test out of the **merge gate** into a **non-gating lane** that
>    still runs and reports it, tagged with a **ticket**. The gate stays trustworthy; the flake stays visible.
> 4. **Report & fix-or-delete** — track flaky-rate over time; every quarantined test has an owner and a
>    ticket; quarantine **shrinks**, never grows. A test that can't be de-flaked gets deleted, not left to rot.

## Decision matrix — which move for which situation

| Situation | Move | Mechanism |
|-----------|------|-----------|
| A clean PR occasionally red on a *transient* (network blip, cold cache) | **Retry once** | `retries: 1` (Playwright) / `retry: 1` (Vitest) on CI |
| A *known* flaky test, ticketed, not yet fixed | **Quarantine** | `{ tag: '@flaky' }` + `allure.issue(...)`; `--grep-invert @flaky` on gate, non-gating lane runs it |
| A test that fails the same way every run | **Fix the code/test** | Not flakiness — a real bug; no retry, no quarantine |
| A flaky test no one will own/fix | **Delete it** | A test you don't trust and won't fix is worse than no test |
| Need to *know* which tests are flaky | **Detect** | Playwright "flaky" status (native) + Allure history-based mark + flaky-rate |

**Rule of thumb:** *transient on otherwise-green* → one retry. *Known-flaky, ticketed* → `@flaky` tag +
non-gating lane. *Deterministic failure* → it's a bug, fix it. **Never** crank retries to mask a real race.

## Stack

- Node 20, TypeScript (strict), Playwright Test (e2e — where flakiness mostly lives) + Vitest (unit)
- **No `await page.waitForTimeout(...)` / `setTimeout` as a wait** — sleeps *cause* flakiness; use Playwright
  **auto-waiting** locators + web-first assertions + `expect.poll` (cross-link
  `qa-ui-test-author-playwright-typescript`)
- `allure-playwright` — the Allure **Retries** view + **history-based** flaky detection + `allure.tag` /
  `allure.issue` (cross-link `qa-allure-reporting-typescript` for the full Allure wiring)

```
e2e/
├── playwright.config.ts        ← retries on CI + a "gate" project (grepInvert @flaky) + a "quarantine" project
├── tests/checkout.spec.ts      ← tests, some tagged { tag: '@flaky' }
└── categories.json             ← an Allure "Known flaky (quarantined)" triage bucket
vitest.config.ts                ← retry on CI for unit tests
```

## Move 2 — Retry, bounded

**Playwright** retries a failed test, then reports the outcome — and crucially, a test that **fails then
passes** is marked **"flaky"** (not "passed"), so the retry never hides the signal. Keep the cap **low — 1**
on the gate.

```ts
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  retries: process.env.CI ? 1 : 0,   // one retry on CI to absorb a true transient; 0 locally (fail fast)
  reporter: [['line'], ['allure-playwright']],
  // ... projects below (Move 3)
});
```

The line/HTML reporter then prints e.g. `12 passed, 1 flaky` — the **flaky count is your detection signal**;
treat any flaky test as a quarantine candidate, not a pass.

**Vitest** (unit) has the same idea via `retry` — though unit tests are rarely flaky; if one is, that's
usually a real concurrency bug to fix, not retry:

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config';
export default defineConfig({ test: { retry: process.env.CI ? 1 : 0 } });

// or per-test, when only one test needs it:
import { it, expect } from 'vitest';
it('should debounce within the window', { retry: 2 }, async () => { /* ... */ });
```

Cap at **1** on the gate. The cap is the whole safety mechanism — a high cap is how flakiness gets hidden.

## Move 3 — Quarantine (Playwright tags + a non-gating project)

Quarantine = **take a known-flaky test out of the merge gate, but keep running it and reporting it.** In
Playwright the lever is a **tag** (`{ tag: '@flaky' }`, Playwright 1.42+), filtered with `--grep` /
`--grep-invert` or split into a **project**.

```ts
import { test, expect } from '@playwright/test';
import * as allure from 'allure-js-commons';

test('should settle payment when gateway is slow', { tag: '@flaky' }, async ({ page }) => {
  await allure.issue('CHECKOUT-871', 'https://jira/CHECKOUT-871'); // the ticket — quarantine is NEVER permanent
  await allure.tag('flaky');                                       // visible flag in Allure (Move 4)
  // ... the intermittently-failing assertion, awaiting a real fix under CHECKOUT-871
});
```

**Two projects in `playwright.config.ts` — a gating one and a non-gating one:**

```ts
export default defineConfig({
  retries: process.env.CI ? 1 : 0,
  reporter: [['line'], ['allure-playwright']],
  projects: [
    { name: 'gate',       grepInvert: /@flaky/ },                 // blocks the merge — quarantined excluded
    { name: 'quarantine', grep: /@flaky/, retries: 3 },           // visibility only — a bit more headroom
  ],
});
```

CI runs them as **two lanes** — the quarantine lane never blocks (cross-link
`qa-ci-pipelines`):

```yaml
- name: Gate suite (blocks merge)
  run: npx playwright test --project=gate            # excludes @flaky

- name: Quarantine lane (visibility only)
  if: always()
  run: npx playwright test --project=quarantine      # still runs + reports
  continue-on-error: true                            # a red quarantine lane does NOT fail the pipeline

- name: Upload Allure results
  if: always()
  uses: actions/upload-artifact@v4
  with: { name: allure-results, path: allure-results/ }
```

> **Why a *running* quarantine lane, not `test.skip` / `test.fixme`.** A skipped test rots — the feature
> drifts, the test silently lies, no one notices when it could be re-enabled. A quarantined test **still
> runs** (off the gate), so you keep its signal, you see when it stabilises (Playwright stops reporting it
> "flaky"; Allure history flips it to **Fixed**), and the ticket stays honest. Quarantine is a **waiting
> room**, not a graveyard.

For **Vitest**, which has no first-class tags, quarantine via a naming convention + `testNamePattern`: tag
flaky unit tests `'[flaky] ...'`, gate with a negative lookahead (`-t '^(?!.*\\[flaky\\])'`) and run the lane
with `-t '\\[flaky\\]'`. In practice almost all quarantine lives in Playwright e2e, not Vitest unit.

## Move 4 — Report the flaky flag in Allure

Two layers of detection, and the TS stack gets one for free:

**(a) Playwright's native "flaky" status** — independent of Allure. A failed-then-passed test is reported
**flaky** in the line summary and the HTML report. This is the strongest *native* detection of the three
stacks — it needs no history and no extra tool. Use it as the live candidate list.

**(b) Allure's history-based auto-detection** — identical across every stack (a *report* feature, not a
language one). With Allure **history enabled** (the `history/` folder carried across runs — see
`qa-allure-reporting-typescript`), Allure auto-adds the **Flaky** mark when, across the latest **5
launches**, a test:

1. got **Failed** at some point within those 5 launches, **and**
2. got **Passed** at least once since that failure, **and**
3. is **Failed or Broken** in the **latest** launch.

It tracks **5 stability marks** off history: **Flaky**, **Retried**, **Fixed** (new pass after a fail),
**Regressed** (new fail after a pass), **Malfunctioned** (new broken). Treat **Retried** + **Flaky** as your
quarantine *candidate* list, and **Fixed** as the signal to lift a test *out* of quarantine.

> **Marking flaky explicitly.** allure-playwright has **no first-class `@Flaky` decorator** (unlike Java's
> `io.qameta.allure.Flaky`). Use `allure.tag('flaky')` + `allure.issue('CHECKOUT-871', url)` (shown in Move
> 3) so the flag and the **ticket** travel with the test in the report — but lean primarily on Playwright's
> native "flaky" status and Allure history, which catch flakiness you haven't tagged yet.

**A triage bucket in `categories.json`** keeps quarantined/flaky failures out of "real" failures (the
reporter picks it up — see `qa-allure-reporting-typescript`):

```json
[
  { "name": "Known flaky (quarantined)", "matchedStatuses": ["failed", "broken"],
    "messageRegex": ".*Timeout.*exceeded.*|.*locator.*not.*visible.*|.*ECONNRESET.*" }
]
```

**Track flaky-rate over time, not per-run green.** A single green run proves nothing about a flaky test. The
metric that matters is *flaky-rate* (flaky marks ÷ total) trending **down** — wire it into the team dashboard
(`qa/manual/quality-metrics`). A growing `@flaky` tag set is a smell: tagging faster than fixing.

## Anti-patterns

- **Cranking `retries` to make CI green.** `retries: 5` doesn't fix a 1-in-3 race — it hides it (though
  Playwright will at least still flag it "flaky"). *Fix:* cap the gate at **1**; quarantine the rest with a ticket.
- **Retrying a *deterministic* failure.** Fails every run → retrying wastes CI minutes before the same red.
  *Fix:* it's a caught regression or broken test — fix it.
- **`test.skip` / `test.fixme` as "quarantine".** A skipped test rots and lies. *Fix:* `{ tag: '@flaky' }` +
  a non-gating project that **still runs** it; keep the signal and the history.
- **Quarantine with no ticket / no owner.** An untracked tag set only grows. *Fix:* every `@flaky` carries
  `allure.issue(...)`; review each sprint; it must **shrink**.
- **Treating a Playwright "flaky" result as a pass.** It needed a retry — by definition it's flaky. *Fix:*
  add it to the candidate list; the green-on-retry is the warning, not the all-clear.
- **Fighting a `waitForTimeout`-induced flake with more retries.** The fixed sleep is the *cause*. *Fix:*
  replace it with auto-waiting locators / web-first assertions / `expect.poll`, then most "flakiness" disappears.
- **Hard-coded `retries` on in dev.** Local retries hide races you'd otherwise catch fast. *Fix:*
  `retries: process.env.CI ? 1 : 0` — fail fast locally, absorb one transient on CI.

## Examples

**End-to-end: a transient on the gate (retried once) vs a known flaky (quarantined + tracked).**

```ts
import { test, expect } from '@playwright/test';
import * as allure from 'allure-js-commons';
import { CheckoutPage } from '../pages/checkout.page';   // page object — intent, not selectors

// GATE test (in the "gate" project, untagged). Normally deterministic; one retry absorbs a cold-start 503.
test('should authorize payment when card is valid', async ({ page }) => {
  const checkout = new CheckoutPage(page);
  await checkout.payWith(validCard({ amount: 1999 }));   // test-data builder
  await expect(checkout.confirmation()).toHaveText('Approved');   // web-first assertion, auto-waits
});

// QUARANTINED test — known to race the async settlement webhook. Tagged @flaky → "quarantine" project only.
test('should mark settled when webhook arrives within sla', { tag: '@flaky' }, async ({ page }) => {
  await allure.issue('PAY-1204', 'https://jira/PAY-1204');
  await allure.tag('flaky');
  const checkout = new CheckoutPage(page);
  await checkout.payWith(validCard());
  // de-flake (PAY-1204): poll the settlement condition, never a fixed window. Until then, quarantined.
  await expect.poll(() => ledger.settlementState(orderId), { timeout: 10_000 })
    .toBe('SETTLED');
});
```

The gate is green if the untagged tests pass (one retry absorbed any transient); the quarantine lane's result
is reported in Allure (flaky-flagged, history-tracked) but **never** fails the pipeline.

## Rules (hard constraints)

- **Retry is bounded and low on the gate** — `retries: process.env.CI ? 1 : 0` (Playwright) / `retry: 1`
  (Vitest). The cap is the safety mechanism; never crank it to hide failures. Playwright's **"flaky" status**
  keeps a green-on-retry visible — treat it as a candidate, not a pass.
- **Quarantine = tag + non-gating lane, never `test.skip`/`test.fixme`.** `{ tag: '@flaky' }`, excluded by
  `grepInvert: /@flaky/` on the gate project, run by a `grep: /@flaky/` project with `continue-on-error: true`.
  The test keeps running.
- **Every quarantined test carries a ticket** (`allure.issue(...)`) and `allure.tag('flaky')`. The tag set
  **shrinks**; review each sprint; un-fixable → **deleted**, not left to rot.
- **Allure flags flakiness via history** — identical 5-launch rule across stacks (history enabled) — *and*
  Playwright flags it natively. Track **flaky-rate trending down**, not per-run green.
- **A deterministic failure is a bug, not a flake** — fix the code/test; do not retry or quarantine it.
- **No `waitForTimeout` / `setTimeout`-as-wait** — use auto-waiting locators, web-first assertions,
  `expect.poll`. Test names describe behavior; one logical assertion per test; no conditional logic in tests;
  builders for 4+-field test data; `strict: true`.

## Cross-references

- `qa-flaky-test-quarantine-java` — the **canonical** stack this is ported from. TestNG `IRetryAnalyzer` +
  `IAnnotationTransformer` gives true **suite-wide** retry and native group-based quarantine + the
  first-class `@Flaky` annotation. Same four moves.
- `qa-flaky-test-quarantine-dotnet` — same four moves, NUnit: `[Retry]` (method-level only) + a custom
  `IRepeatTest` attribute; `[Category("Flaky")]` + `dotnet test --filter` for the gate vs non-gating lane.
- `qa-allure-reporting-typescript` (#?) — the **full** allure-playwright wiring this layers on: the reporter,
  history/trends (required for auto-flaky detection), `categories.json`, CI publish. Base setup lives there.
- `qa-_shared-quality-metrics` — track **flaky-rate over time**; a `@flaky` tag set that grows is the metric
  to watch.
- `qa-ui-test-author-playwright-typescript` — where the quarantined tests are authored; flakiness is best
  fixed at the source: auto-waiting locators, web-first assertions, **no `waitForTimeout`**,
  intent-not-selectors page objects. Fix the wait and the test leaves quarantine.
- `qa-ci-pipelines` (github-actions / azure-pipelines / gitlab-ci references) — the gate-lane vs quarantine-lane job
  wiring (`continue-on-error` on the non-gating lane); sharding the gate project across runners.
