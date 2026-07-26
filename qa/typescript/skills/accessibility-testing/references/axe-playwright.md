# Accessibility Testing — axe-core + Playwright (TypeScript)

axe-core is the de-facto accessibility rule engine; `@axe-core/playwright` runs it **inside your
Playwright run**, against the live DOM, and returns structured `violations[]` you assert on. This is an
**assertion layer** on top of the page objects and specs the `qa-ui-test-writer-playwright-typescript`
skill already authored — you inject an axe scan into an already-authored flow. You do **not** write new
page objects here.

Unlike the visual-regression family (free / Percy / Applitools), axe runs **entirely
in-browser**: there is **no SaaS, no agent, and no API key**. The gate is local, deterministic, and free
— `violations` is empty or it isn't.

> **What automation can and can't do.** axe-core catches roughly **30–40%** of WCAG issues — the
> machine-checkable ones (missing `alt`, unlabeled inputs, color contrast, bad ARIA, duplicate IDs). It
> is a **floor, not proof of accessibility**: keyboard traps, focus order, screen-reader comprehension,
> and meaningful alt text still need manual + assistive-tech testing. Cross-link the manual/exploratory
> angle (`qa-exploratory-charter-writer`). Treat a green axe run as "no *automated* regressions," never
> "accessible."

## Setup

```bash
npm install --save-dev @axe-core/playwright axe-core
```

No config file, no service, no token. `AxeBuilder` bundles axe-core and injects it into the page at scan
time; the scan happens in the browser you already launched.

## The AxeBuilder model

`new AxeBuilder({ page }).analyze()` injects axe-core, runs it against the current DOM, and resolves to
an `AxeResults` object with four arrays:

- **`violations[]`** — failed rules. **This is the gate.** Each violation has `id` (rule id, e.g.
  `color-contrast`), `impact` (`minor` | `moderate` | `serious` | `critical`), `help`, `helpUrl`, and
  `nodes[]` — each node carries the failing `target` selector(s) and a `failureSummary` telling you how
  to fix it.
- **`passes[]`** — rules that passed (evidence, not usually asserted on).
- **`incomplete[]`** — rules axe **could not decide** automatically (e.g. a contrast check over a
  background image). **Not a pass** — these need manual review. Don't silently ignore them.
- **`inapplicable[]`** — rules with no matching elements on the page.

The assertion is one logical assertion per the global rules:

```typescript
expect(results.violations).toEqual([]);
```

## Core pattern — scan injected into a page-object-driven flow

The page object exposes intent and drives the app to the state under test; the test stabilizes on a
condition, then scans. No selectors in the test, no fixed waits — axe analyzes the **live DOM at call
time**, so the page must be in its final state before `analyze()`.

```typescript
// pages/checkout.page.ts
import { type Page, type Locator } from '@playwright/test';

export class CheckoutPage {
  readonly page: Page;
  readonly form: Locator;

  constructor(page: Page) {
    this.page = page;
    this.form = page.getByTestId('checkout-form');
  }

  async goto(): Promise<void> {
    await this.page.goto('/checkout');
  }

  /** Resolves once the form is interactive — a condition, never a fixed wait. */
  async waitUntilReady(): Promise<void> {
    await this.form.getByRole('button', { name: 'Pay now' }).waitFor({ state: 'visible' });
  }
}
```

```typescript
// tests/checkout.a11y.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { CheckoutPage } from '../pages/checkout.page';

test('Should_have_no_a11y_violations_When_checkout_form_loaded', async ({ page }) => {
  const checkout = new CheckoutPage(page);
  await checkout.goto();
  await checkout.waitUntilReady();                 // stabilize on a condition first…

  const results = await new AxeBuilder({ page })   // …then scan the live DOM
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  expect(results.violations).toEqual([]);          // one logical assertion = the gate
});
```

## Scoping + rule selection

Scope the scan and pick which rules count — the analogue of `Target.region` / match levels in the
visual family, but here it's *which rules*, not *how lenient*:

```typescript
const results = await new AxeBuilder({ page })
  .include('#checkout-form')          // scan only this component (or pass a chain/array)
  .exclude('.third-party-widget')     // skip an embed you don't own
  .withTags(['wcag2aa', 'wcag21aa'])  // the WCAG level that IS your gate
  .analyze();
```

- **`.include(selector)` / `.exclude(selector)`** — scan a component, not the whole page. Cleaner
  failures, and lets you gate a new component to zero while the legacy page still has debt. `.exclude`
  third-party iframes/widgets you can't fix.
- **`.withTags([...])`** — pick the ruleset = pick which WCAG level is your gate. Common tags:
  `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`, plus `best-practice` (axe's own
  recommendations beyond WCAG). **Decide your conformance target once** and apply the same tags
  everywhere — `wcag2a wcag2aa wcag21a wcag21aa` is the common "AA" gate.
- **`.withRules([...])` / `.disableRules([...])`** — surgical control of individual rule ids; overrides
  tags for those rules.
- **`.options({...})`** — raw axe-core run options (overrides `withRules`/`withTags`); reach for it last.

### A shared AxeBuilder via a fixture (DRY the config)

Configure tags/excludes once so every spec stays clean and consistent — the recommended pattern:

```typescript
// support/axe.fixture.ts
import { test as base } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

type AxeFixture = { makeAxeBuilder: () => AxeBuilder };

export const test = base.extend<AxeFixture>({
  makeAxeBuilder: async ({ page }, use) => {
    await use(() =>
      new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .exclude('#third-party-chat'));   // org-wide excludes live here, once
  },
});
export { expect } from '@playwright/test';
```

```typescript
import { test, expect } from '../support/axe.fixture';

test('Should_have_no_a11y_violations_When_dashboard_loaded', async ({ page, makeAxeBuilder }) => {
  await page.goto('/dashboard');
  const results = await makeAxeBuilder().analyze();
  expect(results.violations).toEqual([]);
});
```

## The triage reality — a real app has pre-existing violations

A green-field `expect(violations).toEqual([])` only works on a clean page. Real apps have debt. The
disciplined patterns, in order of preference:

**1. Gate *new* violations only — baseline the known set.** Snapshot the current violation rule-ids and
fail only on additions. This stops the bleeding without a big-bang fix, and every new feature ships
clean:

```typescript
test('Should_introduce_no_new_a11y_violations_When_profile_loaded', async ({ page }) => {
  await page.goto('/profile');
  const results = await new AxeBuilder({ page }).withTags(['wcag2aa']).analyze();

  // Known debt, each with a tracking ticket — shrink this list, never grow it.
  const KNOWN = new Set(['color-contrast' /* JIRA-1234 */, 'landmark-one-main' /* JIRA-1235 */]);
  const newViolations = results.violations.filter((v) => !KNOWN.has(v.id));

  expect(newViolations).toEqual([]);   // gate additions; legacy debt tracked separately
});
```

(`toHaveScreenshot`-style snapshotting of the full violation set also works via
`expect(results.violations).toMatchSnapshot()`, but an explicit *ticketed* allow-list is more honest —
each entry points at the bug that will remove it.)

**2. Disable a *documented* false-positive — never blanket-disable.** If a rule genuinely
misfires on your markup, `.disableRules(['rule-id'])` with a ticket reference in a comment. Disabling to
make a real failure go away is hiding a bug:

```typescript
const results = await new AxeBuilder({ page })
  .disableRules(['scrollable-region-focusable'])   // axe false-positive on virtualized list — JIRA-2001
  .analyze();
```

**3. Don't silently pass `incomplete[]`.** axe couldn't decide — surface it for manual review rather
than treating it as green:

```typescript
if (results.incomplete.length > 0) {
  console.warn(`axe needs manual review for: ${results.incomplete.map((i) => i.id).join(', ')}`);
}
```

**4. Phase the rollout by impact.** When even the baseline is huge, gate on the worst first and ratchet
down over time:

```typescript
const blocking = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
expect(blocking).toEqual([]);   // gate critical+serious now; widen to moderate/minor later
```

## A11y-specific stabilization — scan per state, not per page

axe analyzes the **live DOM at call time**. So scan **after** the page reaches the state under test, and
scan **once per meaningful state** — an open menu, an expanded accordion, a validation-error form are
different DOMs with different a11y surfaces. Drive the state via page-object intent, wait on a condition,
then scan:

```typescript
test('Should_have_no_a11y_violations_When_nav_menu_open', async ({ page }) => {
  const nav = new NavBar(page);
  await page.goto('/');
  await nav.openAccountMenu();                            // page-object intent
  await nav.accountMenu.waitFor({ state: 'visible' });    // condition, not waitForTimeout

  const results = await new AxeBuilder({ page }).include('[role="menu"]').analyze();
  expect(results.violations).toEqual([]);
});
```

Never `await page.waitForTimeout(...)` before a scan — a sleep races the DOM and makes the gate flaky.

## Reporting the gate — violations into Allure, fail CI on non-empty

axe gives you everything to make a failure actionable: rule id, impact, helpUrl, and the failing
selector + fix summary. Attach the JSON and a readable summary to Allure so the report names the rule
without anyone re-running locally (cross-link `qa-test-reports-typescript`):

```typescript
// support/a11y-report.ts
import { type Result } from 'axe-core';
import { allure } from 'allure-playwright';

export function attachViolations(violations: Result[]): void {
  if (violations.length === 0) return;
  // Machine-readable: the full violation objects.
  allure.attachment('axe-violations.json', JSON.stringify(violations, null, 2), 'application/json');
  // Human-readable: one line per failing node.
  const summary = violations
    .map((v) => `[${v.impact}] ${v.id}: ${v.help}\n  ${v.helpUrl}\n  ` +
      v.nodes.map((n) => n.target.join(' ')).join('\n  '))
    .join('\n\n');
  allure.attachment('axe-summary.txt', summary, 'text/plain');
}
```

```typescript
test('Should_have_no_a11y_violations_When_settings_loaded', async ({ page }) => {
  await page.goto('/settings');
  const results = await new AxeBuilder({ page }).withTags(['wcag2aa']).analyze();
  attachViolations(results.violations);     // attach BEFORE asserting, so a failure carries the report
  expect(results.violations).toEqual([]);
});
```

The CI job fails because the assertion fails — no extra wiring beyond uploading the Allure results and
the attached JSON (cross-link `qa-ci-pipelines-typescript`). There is **no API key to
inject** here — call that out as the contrast with the visual-regression family (`percy` `PERCY_TOKEN` /
`applitools` `APPLITOOLS_API_KEY`): axe runs in-browser, so the only thing CI needs is the artifact upload.

## Anti-patterns

- **`await page.waitForTimeout(500)` before `analyze()`.** axe scans the DOM at call time; a sleep
  races it and is slow. *Fix:* wait on a condition (`locator.waitFor`, spinner hidden,
  `document.fonts.ready` is irrelevant here — wait on *interactivity*), then scan.
- **One scan per page, ignoring interactive states.** Menus/modals/error states have their own a11y
  surface. *Fix:* scan per meaningful state after driving the app there.
- **Blanket `.disableRules` / cranking tags down to make it pass.** That hides real failures. *Fix:*
  `.disableRules` only a *documented* false-positive with a ticket; otherwise fix the markup.
- **Treating `incomplete[]` as a pass.** axe abstained; the issue may be real. *Fix:* surface
  incompletes for manual review.
- **Asserting on `violations.length === 0` instead of `toEqual([])`.** The length check throws away the
  diff. *Fix:* `expect(results.violations).toEqual([])` — the failure message names every rule + node.
- **Scanning the whole page when the feature under test is one component.** Legacy debt drowns the new
  regression. *Fix:* `.include(selector)` the component; gate it to zero.
- **Calling a green axe run "accessible."** It covers ~30–40% of WCAG. *Fix:* pair with manual +
  assistive-tech testing; treat axe as the automated floor.
- **Duplicating tag/exclude config across every spec.** Drifts over time. *Fix:* a shared `AxeBuilder`
  fixture.

## Examples

**End-to-end: a per-component a11y gate that ships new features clean against a legacy page.**

```typescript
// tests/signup.a11y.spec.ts
import { test, expect } from '../support/axe.fixture';   // shared tags + org-wide excludes
import { attachViolations } from '../support/a11y-report';
import { SignupPage } from '../pages/signup.page';

test.describe('Signup accessibility (axe-core)', () => {
  test('Should_have_no_a11y_violations_When_signup_form_empty', async ({ page, makeAxeBuilder }) => {
    const signup = new SignupPage(page);
    await signup.goto();
    await signup.waitUntilReady();                       // condition, not sleep

    const results = await makeAxeBuilder().include('#signup-form').analyze();
    attachViolations(results.violations);
    expect(results.violations).toEqual([]);
  });

  test('Should_have_no_a11y_violations_When_validation_errors_shown', async ({ page, makeAxeBuilder }) => {
    const signup = new SignupPage(page);
    await signup.goto();
    await signup.submitEmpty();                          // page-object intent
    await signup.errorSummary.waitFor({ state: 'visible' });

    const results = await makeAxeBuilder().include('#signup-form').analyze();
    attachViolations(results.violations);
    expect(results.violations).toEqual([]);              // error state has its own a11y surface
  });
});
```

Lifecycle for this gate:
1. A dev adds a new field to the signup form.
2. CI runs the E2E suite; the axe scan runs in the same browser, on the live DOM, per state.
3. If the new field is missing a label, `violations` is non-empty — the build fails with the rule id
   (`label`), the failing selector, and the helpUrl in the Allure attachment.
4. The dev fixes the markup; the gate goes green. Legacy debt on other pages is tracked separately by
   the ticketed allow-list, shrinking over time.

## Rules (hard constraints)

- A11y testing is an **assertion layer** on existing page objects/specs — inject the axe scan, don't
  author new page objects here. Page objects expose intent + locators; no selectors in tests.
- One logical assertion per test: `expect(results.violations).toEqual([])` (or a filtered subset). Test
  names `Should_X_When_Y`.
- Stabilize on a **condition** (interactivity/visibility) before `analyze()`; never `waitForTimeout` —
  axe scans the live DOM at call time.
- Scan **per meaningful state** (menu open, accordion expanded, errors shown), not once per page.
- Pick the WCAG level deliberately via `.withTags` and apply it consistently (a shared fixture).
- Triage with discipline: baseline known debt with **ticketed** allow-lists, `.disableRules` only
  *documented* false-positives, and surface `incomplete[]` for manual review — never silently pass it.
- **No SaaS, no API key** (axe runs in-browser) — the gate is local and deterministic. The only CI need
  is the violations-JSON/Allure artifact upload.
- axe covers ~30–40% of WCAG: it's the automated **floor**, not proof of accessibility. Pair with
  manual + assistive-tech testing.

## Cross-references

- `qa-accessibility-testing-dotnet` — same skill, .NET / NUnit
  (`Deque.AxeCore.Playwright`, `new AxeBuilder(page).AnalyzeAsync()`, `result.Violations`).
- `qa-accessibility-testing-java` — same skill, Java / TestNG
  (`com.deque.html.axe-core:playwright`, `new AxeBuilder(page).analyze()`, `results.getViolations()`).
- `references/lighthouse-ci.md` — the audit/score sibling: full-page
  perf/SEO/PWA + a11y **score** threshold, a separate Lighthouse pass. Run both: axe gates, Lighthouse
  trends.
- `qa-ui-test-writer-playwright-typescript` — the page objects/specs the axe scan is injected into.
  Author the flow there; add the a11y scan here.
- `qa-ci-pipelines-typescript` — where the job fails on the assertion and the violations
  JSON is uploaded as an artifact. Note: **no secret to inject** (contrast `percy`/`applitools`).
- `qa-test-reports-typescript` — attach the violations JSON + readable summary to the report.
- `qa-exploratory-charter-writer` — the manual/assistive-tech testing that covers the ~60% axe can't.
