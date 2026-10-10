---
name: qa-flaky-test-quarantine-typescript
description: Use when flaky tests in a Node 24 (22 supported) + TypeScript suite (Playwright e2e, Vitest unit) must be detected, **quarantined** and reported. Triggers: "this Playwright test is flaky, stop it blocking CI", "quarantine our flaky e2e tests but keep running them", "find which Playwright tests are flaky". Not for Allure wiring (`qa-test-reports-typescript`), the pipeline lanes (`qa-ci-pipelines-typescript`), or fixing test logic (the owning qa-*-typescript agent).
---

# Flaky-Test Quarantine (Node 24 + TypeScript / Playwright + Vitest)

This is the **TypeScript sibling** of the single-node `qa/reporting/typescript/skills/flaky-test-quarantine/` family, **ported** from
the canonical **Java/TestNG** file (`qa-flaky-test-quarantine-java`). The **four-move loop** is identical;
only the runner API and the quarantine filter change.

**Retries are not this skill's to set.** `qa/cicd/ci-conventions` owns the retry policy: `retries: 0`, except a
documented network-flake hotspot. The canonical config,
`qa/typescript/skills/ui-test-author/playwright/assets/playwright.config.ts`, carries `retries: 0`. With no
in-run retry, Playwright never reports a test as "flaky", so **detection comes from Allure history and a
nightly `--repeat-each` run**, never from a retry turning red into green.

## What "flaky" means (and what it does not)

A **flaky test** passes and fails **non-deterministically against the same code** — a race, a timing
assumption, an order dependency, a real-but-rare backend hiccup. It is *not*:

- a test that **always** fails on a change → that's a **caught regression**, fix the code;
- a test that **always** fails regardless of the change → that's a **broken test**, fix the test.

> **The discipline this skill encodes.** A retry hides real bugs (a 1-in-3 race is a real bug) and lets new
> flakiness slip in unnoticed. So the policy is a **four-move loop**, not "add retries":
>
> 1. **Detect** — Allure history across launches, plus a nightly `--repeat-each` that runs every test N times.
> 2. **Hotspot** — a *documented* network-flake hotspot may opt into one retry for its own `describe`, dated and
>    linked to an issue. Nothing else retries.
> 3. **Quarantine** — move a *known* flaky test out of the **merge gate** into a **non-gating lane** that
>    still runs and reports it, tagged with a **ticket**. The gate stays trustworthy; the flake stays visible.
> 4. **Report & fix-or-delete** — track flaky-rate over time; every quarantined test has an owner and a
>    ticket; quarantine **shrinks**, never grows. A test that can't be de-flaked gets deleted, not left to rot.

## Decision matrix — which move for which situation

| Situation | Move | Mechanism |
|-----------|------|-----------|
| Need to *know* which tests are flaky | **Detect** | Allure history marks (Flaky, Regressed, Fixed) + the nightly `--repeat-each` lane |
| A third-party sandbox or infra warm-up fails a clean run now and then, and the issue is filed | **Hotspot** | `test.describe.configure({ retries: 1 })` on that `describe`, with an `issue` annotation and a date |
| A *known* flaky test, ticketed, not yet fixed | **Quarantine** | `{ tag: '@flaky' }` + `allure.issue(...)`; the gate runs `--grep-invert @flaky`, a non-gating lane runs `--grep @flaky` |
| A test that fails the same way every run | **Fix the code/test** | Not flakiness — a real bug; no retry, no quarantine |
| A flaky test no one will own/fix | **Delete it** | A test you don't trust and won't fix is worse than no test |

**Rule of thumb:** *seen flaky in history or the repeat lane* → `@flaky` tag + ticket + non-gating lane.
*Deterministic failure* → it's a bug, fix it. **Never** add retries to mask a race.

## Stack

- Node 24 (22 supported), TypeScript (strict), Playwright Test (e2e — where flakiness mostly lives) + Vitest (unit)
- **No `await page.waitForTimeout(...)` / `setTimeout` as a wait** — sleeps *cause* flakiness; use Playwright
  **auto-waiting** locators + web-first assertions + `expect.poll` (cross-link
  `qa-ui-test-writer-playwright-typescript`)
- `allure-playwright` + `allure-js-commons` — history-based flaky detection, `allure.tag` / `allure.issue`
  (cross-link `qa-test-reports-typescript` for the full Allure wiring)

```
e2e/
├── playwright.config.ts        ← the canonical config: retries 0, setup + chromium projects
├── tests/checkout.spec.ts      ← tests, some tagged { tag: '@flaky' }
└── categories.json             ← an Allure "Known flaky (quarantined)" triage bucket
```

## Move 1 — Detect

**(a) The nightly repeat lane.** A scheduled job runs every gating test several times in one launch:

```bash
npx playwright test --grep-invert @flaky --repeat-each=5
```

A test that fails in some repeats and passes in others is flaky by definition, with no retry involved. Each
repeat is its own result in the junit file and the HTML report. Scope a PR-time check to the changed specs
with `npx playwright test --only-changed=origin/main --repeat-each=10`.

**(b) Allure's history-based detection** — identical across every stack (a *report* feature, not a
language one). With Allure **history enabled** (the `history/` folder carried across runs — see
`qa-test-reports-typescript`), Allure adds the **Flaky** mark when, across the latest **5 launches**, a test:

1. got **Failed** at some point within those 5 launches, **and**
2. got **Passed** at least once since that failure, **and**
3. is **Failed or Broken** in the **latest** launch.

It tracks **5 stability marks** off history: **Flaky**, **Retried**, **Fixed** (new pass after a fail),
**Regressed** (new fail after a pass), **Malfunctioned** (new broken). Treat **Flaky** and **Regressed** on an
unchanged area as the quarantine *candidate* list, and **Fixed** as the signal to lift a test *out* of
quarantine.

Playwright's own "flaky" status and `failOnFlakyTests` need in-run retries, so they are not used.

## Move 2 — The documented hotspot

`ci-conventions` allows a per-test retry only for a documented network-flake hotspot. Scope it to the
`describe` that talks to the flaky dependency, never the config:

```ts
import { expect, test } from './fixtures';

test.describe('Payment sandbox', () => {
  test.describe.configure({ retries: 1 });

  test(
    'Should_AuthorizePayment_When_CardIsValid',
    { annotation: { type: 'issue', description: 'https://jira/PAY-1188 (2026-10-10, sandbox cold starts)' } },
    async ({ checkoutPage, validCard }) => {
      await checkoutPage.payWith(validCard);

      await expect(checkoutPage.confirmation).toHaveText('Approved');
    },
  );
});
```

A hotspot retry is still a smell: its issue is reviewed every sprint, and the retry is removed when the
dependency is stubbed (`qa/typescript/skills/network-mocking`) or fixed.

## Move 3 — Quarantine (a tag and a non-gating lane)

Quarantine = **take a known-flaky test out of the merge gate, but keep running it and reporting it.** The
lever is a Playwright **tag** (`{ tag: '@flaky' }`, the details object since 1.42), filtered on the command line.
The canonical config's projects (`setup`, `chromium`) stay as they are; no second config, no extra project.

```ts
import * as allure from 'allure-js-commons';
import { expect, test } from './fixtures';

test('Should_MarkSettled_When_WebhookArrivesWithinSla', { tag: '@flaky' }, async ({ checkoutPage, ledger, validCard }) => {
  await allure.issue('https://jira/PAY-1204', 'PAY-1204');
  await allure.tag('flaky');

  const orderId = await checkoutPage.payWith(validCard);

  await expect.poll(() => ledger.settlementState(orderId), { timeout: 10_000 }).toBe('SETTLED');
});
```

CI runs the two lanes as **separate jobs** — each run cleans `test-results/` at its start, so two runs in one
job would wipe the first lane's evidence (cross-link `qa-ci-pipelines-typescript`):

```yaml
ui-gate:
  steps:
    - run: npx playwright test --grep-invert @flaky

ui-quarantine:
  continue-on-error: true
  steps:
    - run: npx playwright test --grep @flaky
```

The quarantine lane is the **one** non-gating exception `ci-conventions` allows: it runs only `@flaky` tests,
still reports them to Allure, and never blocks the merge.

> **Why a *running* quarantine lane, not `test.skip` / `test.fixme`.** A skipped test rots — the feature
> drifts, the test silently lies, no one notices when it could be re-enabled. A quarantined test **still
> runs** (off the gate), so you keep its signal, you see when it stabilises (Allure history flips it to
> **Fixed**; the repeat lane stops catching it), and the ticket stays honest. Quarantine is a **waiting
> room**, not a graveyard.

For **Vitest**, which has no first-class tags, quarantine via a naming convention + `testNamePattern`: tag
flaky unit tests `'[flaky] ...'`, gate with a negative lookahead (`-t '^(?!.*\\[flaky\\])'`) and run the lane
with `-t '\\[flaky\\]'`. Vitest keeps `retry: 0`; a flaky unit test is usually a real concurrency bug.

## Move 4 — Report the flaky flag in Allure

> **Marking flaky explicitly.** allure-playwright has **no first-class `@Flaky` decorator** (unlike Java's
> `io.qameta.allure.Flaky`). Use `allure.tag('flaky')` + `allure.issue(url, name)` (shown in Move 3) so the
> flag and the **ticket** travel with the test in the report — and lean on Allure history and the repeat
> lane, which catch flakiness you haven't tagged yet.

**A triage bucket in `categories.json`** keeps quarantined/flaky failures out of "real" failures (the
reporter picks it up — see `qa-test-reports-typescript`):

```json
[
  { "name": "Known flaky (quarantined)", "matchedStatuses": ["failed", "broken"],
    "messageRegex": ".*Timeout.*exceeded.*|.*locator.*not.*visible.*|.*ECONNRESET.*" }
]
```

**Track flaky-rate over time, not per-run green.** A single green run proves nothing about a flaky test. The
metric that matters is *flaky-rate* (flaky marks ÷ total, plus repeat-lane failures ÷ repeats) trending
**down** — wire it into the team dashboard (`qa/manual/quality-metrics`). A growing `@flaky` tag set is a
smell: tagging faster than fixing.

## Anti-patterns

- **Adding `retries` to make CI green.** `retries: 2` doesn't fix a 1-in-3 race — it hides it. *Fix:* keep
  `retries: 0`; quarantine with a ticket.
- **Detecting flakes through retries.** Under `retries: 0` the "flaky" status never appears. *Fix:* the nightly
  `--repeat-each` lane and Allure history.
- **A config-wide retry for one bad dependency.** *Fix:* `test.describe.configure({ retries: 1 })` on that
  `describe`, dated and linked — or stub the dependency.
- **Retrying a *deterministic* failure.** Fails every run → retrying wastes CI minutes before the same red.
  *Fix:* it's a caught regression or broken test — fix it.
- **`test.skip` / `test.fixme` as "quarantine".** A skipped test rots and lies. *Fix:* `{ tag: '@flaky' }` +
  a non-gating lane that **still runs** it; keep the signal and the history.
- **Quarantine with no ticket / no owner.** An untracked tag set only grows. *Fix:* every `@flaky` carries
  `allure.issue(...)`; review each sprint; it must **shrink**.
- **Running the gate and the quarantine lane in one job.** The second run cleans `test-results/` and loses
  the first lane's failure evidence. *Fix:* two jobs.
- **Fighting a `waitForTimeout`-induced flake with retries.** The fixed sleep is the *cause*. *Fix:* replace
  it with auto-waiting locators / web-first assertions / `expect.poll`, then most "flakiness" disappears.

## Rules (hard constraints)

- **Retries follow `qa/cicd/ci-conventions`** — `retries: 0` in the canonical config; one retry only on a
  documented hotspot `describe`, dated and linked. This skill never raises the config's retries.
- **Detection = Allure history + the nightly `--repeat-each` lane.** Playwright's "flaky" status and
  `failOnFlakyTests` are not used.
- **Quarantine = tag + non-gating lane, never `test.skip`/`test.fixme`.** `{ tag: '@flaky' }`, excluded with
  `--grep-invert @flaky` on the gate, run by a separate `--grep @flaky` job with `continue-on-error: true`.
  The test keeps running.
- **Every quarantined test carries a ticket** (`allure.issue(url, name)`) and `allure.tag('flaky')`. The tag set
  **shrinks**; review each sprint; un-fixable → **deleted**, not left to rot.
- **A deterministic failure is a bug, not a flake** — fix the code/test; do not retry or quarantine it.
- **No `waitForTimeout` / `setTimeout`-as-wait** — use auto-waiting locators, web-first assertions,
  `expect.poll`. Test names are `Should_X_When_Y`; one logical assertion per test; no conditional logic in
  tests; builders for 4+-field test data; `strict: true`.

## Cross-references

- `qa-flaky-test-quarantine-java` — the **canonical** stack this is ported from: TestNG groups for quarantine
  and the first-class `@Flaky` annotation. Same four moves.
- `qa-flaky-test-quarantine-dotnet` — same four moves, NUnit: `[Category("Flaky")]` + `dotnet test --filter` for
  the gate vs non-gating lane.
- `qa-test-reports-typescript` — the **full** allure-playwright wiring this layers on: the reporter,
  history/trends (required for auto-flaky detection), `categories.json`, CI publish. Base setup lives there.
- `qa-ci-conventions-shared` — the retry policy this skill defers to.
- `qa-_shared-quality-metrics` — track **flaky-rate over time**; a `@flaky` tag set that grows is the metric
  to watch.
- `qa-ui-test-writer-playwright-typescript` — where the quarantined tests are authored and where the canonical
  config lives; flakiness is best fixed at the source: auto-waiting locators, web-first assertions, **no
  `waitForTimeout`**, intent-not-selectors page objects. Fix the wait and the test leaves quarantine.
- `qa-evidence-capture-typescript` — the trace and video a flaky failure leaves behind, and how to read them.
- `qa-ci-pipelines-typescript` (its GitHub Actions, Azure Pipelines and GitLab CI references) — the gate job,
  the quarantine job (`continue-on-error` on the non-gating lane) and the nightly repeat lane.
