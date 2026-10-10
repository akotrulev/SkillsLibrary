# Accessibility Testing — axe-core + Playwright (TypeScript / Playwright 1.64)

`@axe-core/playwright` runs the axe-core rule engine **inside your Playwright run**, against the live DOM,
and returns structured `violations[]` to assert on. This is an **assertion layer** on page objects and
fixtures from `qa/typescript/skills/ui-test-author/playwright`: a spec reaches a state through a page
object and asks the `a11y` fixture to scan it.

axe runs **entirely in the browser**: no SaaS, no agent, no API key. The gate is local and deterministic.

> **What automation can and cannot do.** axe catches the machine-checkable share of WCAG (roughly a third):
> missing `alt`, unlabeled inputs, contrast, invalid ARIA, duplicate ids. Keyboard traps, focus order,
> screen-reader comprehension and meaningful alt text still need manual and assistive-technology testing
> (`qa-exploratory-charter-writer`). A green scan means "no *automated* regressions", never "accessible".

## 1. Setup

```bash
npm install --save-dev @axe-core/playwright
```

The version is in the writer's **Versions** table. `AxeBuilder` bundles axe-core and injects it at scan
time; there is no config file and no service.

## 2. The result model

`analyze()` resolves to `AxeResults` with four arrays:

- **`violations[]`** — failed rules. **The gate.** Each has `id` (`color-contrast`), `impact` (`minor` |
  `moderate` | `serious` | `critical`), `help`, `helpUrl` and `nodes[]`, each node with its `target`
  selector and a `failureSummary`.
- **`incomplete[]`** — rules axe could not decide (contrast over a background image). **Not a pass**: they
  are the manual-review list, so they are attached on every scan.
- `passes[]`, `inapplicable[]` — evidence; not asserted on.

`expect(results.violations, '<subject>').toEqual([])` is the assertion: on failure the diff prints every
rule and node. Never `violations.length === 0`, which throws that information away.

## 3. Native assertions alongside the scan

axe finds rule violations; it does not know what a control *should* be called. Assert the intended
contract with the web-first set — `toHaveAccessibleName`, `toHaveAccessibleDescription`,
`toHaveAccessibleErrorMessage`, `toHaveRole`, `toMatchAriaSnapshot` — from
`qa/typescript/skills/ui-test-author/playwright/references/assertions.md` §1–§2. A form gets both: an axe
scan per state, and a native assertion for the error message the story specifies (§6).

## 4. The shared fixture — tags, excludes and attachments in one place

The conformance target is **WCAG 2.2 AA**, set once. Every scan attaches its violations and its
incompletes **before** the test asserts, so a failure carries the evidence and incompletes are visible on
every run.

```typescript
import AxeBuilder from '@axe-core/playwright';
import type { AxeResults, Result } from 'axe-core';
import { test as base } from './fixtures';
import { SignupPage } from './SignupPage';

export const wcag22aa = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

export const falsePositives: ReadonlyMap<string, string> = new Map([
  ['scrollable-region-focusable', 'A11Y-2001: misfires on the virtualized order list'],
]);

export const knownViolations: ReadonlyMap<string, string> = new Map([
  ['color-contrast', 'A11Y-1234'],
  ['landmark-one-main', 'A11Y-1235'],
]);

export const newViolations = (violations: Result[]): Result[] =>
  violations.filter((violation) => !knownViolations.has(violation.id));

export const blockingViolations = (violations: Result[]): Result[] =>
  violations.filter((violation) => violation.impact === 'critical' || violation.impact === 'serious');

type A11y = {
  scanPage: () => Promise<AxeResults>;
  scanWithin: (testId: string) => Promise<AxeResults>;
};

export const test = base.extend<{ a11y: A11y; signupPage: SignupPage }>({
  a11y: async ({ page }, use, testInfo) => {
    const builder = (): AxeBuilder =>
      new AxeBuilder({ page })
        .withTags(wcag22aa)
        .exclude('[data-testid="Chat.Widget"]')
        .disableRules([...falsePositives.keys()]);
    const analyze = async (scan: AxeBuilder): Promise<AxeResults> => {
      const results = await scan.analyze();
      await testInfo.attach('axe-violations.json', {
        body: JSON.stringify(results.violations, null, 2),
        contentType: 'application/json',
      });
      await testInfo.attach('axe-incomplete.json', {
        body: JSON.stringify(results.incomplete, null, 2),
        contentType: 'application/json',
      });
      return results;
    };
    await use({
      scanPage: () => analyze(builder()),
      scanWithin: (testId) => analyze(builder().include(`[data-testid="${testId}"]`)),
    });
  },
  signupPage: async ({ page }, use) => {
    await use(new SignupPage(page));
  },
});

export { expect } from './fixtures';
```

- `withTags` picks the ruleset, which is picking the WCAG level. `best-practice` adds axe's own
  recommendations beyond WCAG; add it deliberately, never per spec.
- `include` / `exclude` take CSS selectors; the fixture builds them from test ids, so specs pass
  `'Signup.Form'`, never a selector. `exclude` is for embeds you do not own.
- `disableRules` is only for a **documented** false positive, with its ticket and reason in
  `falsePositives`. Disabling a rule to hide a real failure hides a bug.
- `withRules([...])` runs only the named rules; `options({...})` is raw axe run options and overrides both —
  reach for it last.
- `testInfo.attach` lands in the Playwright report and, through `allure-playwright`, in Allure. A direct
  Allure call would be `await allure.attachment(...)` from `allure-js-commons` — never the
  `allure-playwright` export, never un-awaited.

## 5. The core pattern — one scan per state

```typescript
import { expect, test } from './a11y.fixtures';

test.describe('Sign-up accessibility', { tag: '@a11y' }, () => {
  test('Should_HaveNoWcagViolations_When_SignupFormIsEmpty', async ({ signupPage, a11y }) => {
    await signupPage.open();

    const results = await a11y.scanWithin('Signup.Form');

    expect(results.violations, 'axe violations in the empty sign-up form').toEqual([]);
  });

  test('Should_HaveNoWcagViolations_When_ValidationErrorsShow', async ({ signupPage, a11y }) => {
    await signupPage.submitEmpty();

    const results = await a11y.scanWithin('Signup.Form');

    expect(results.violations, 'axe violations in the sign-up form with errors').toEqual([]);
  });
});
```

axe analyzes the DOM **at call time**, so the page object drives the state and waits on a condition first
(`submitEmpty()` returns once the error summary is visible). An open menu, an expanded accordion and a
form showing errors are different DOMs with different accessibility surfaces: scan each one. Never
`waitForTimeout` before a scan.

## 6. The native assertion for the same state

```typescript
test('Should_AnnounceEmailRequired_When_SignupSubmittedEmpty', async ({ signupPage }) => {
  await signupPage.submitEmpty();

  await expect(signupPage.email, 'email field').toHaveAccessibleErrorMessage('Enter an email address');
});
```

The scan proves no rule broke; this test proves the field says what the story requires.

## 7. Triage — a real app has existing violations

In order of preference:

1. **Gate new violations only.** Known debt lives in `knownViolations`, each with its ticket; the list only
   shrinks. `expect(newViolations(results.violations), 'new axe violations').toEqual([])`.
2. **Disable a documented false positive** through `falsePositives` (§4), never in a spec.
3. **Read the incompletes.** `axe-incomplete.json` is attached on every scan; reviewing it is part of
   accepting a new screen.
4. **Ratchet by impact** when even the baseline is large:
   `expect(blockingViolations(results.violations), 'critical and serious violations').toEqual([])`, then
   widen to every impact once the backlog clears.

A snapshot of the whole violation set (`toMatchSnapshot`) also gates additions, but a ticketed allow-list is
more honest: each entry names the bug that removes it.

## 8. CI

The scans run inside the normal UI job; the job fails because the assertion fails. The attachments travel
with the test's evidence (`qa/typescript/skills/evidence-capture`) and into Allure. No secret is needed —
the contrast with Percy's and Applitools' keys.

## Anti-patterns

- **A sleep before `analyze()`.** *Fix:* the page object waits for the state.
- **One scan per page, ignoring interactive states.** *Fix:* one scan per meaningful state.
- **Tags that stop at WCAG 2.1 AA.** *Fix:* `wcag22aa` in the shared tag set.
- **Tags or excludes repeated per spec.** They drift. *Fix:* the fixture.
- **`if (results.incomplete.length) console.warn(...)`.** A condition in a test, and silent in CI. *Fix:* the
  fixture attaches the incompletes on every scan.
- **An un-awaited `allure.attachment` in a sync helper**, or `import { allure } from 'allure-playwright'`.
  *Fix:* awaited `testInfo.attach`.
- **`new AxeBuilder({ page })` or `new SignupPage(page)` in a spec.** *Fix:* the fixtures.
- **A whole-page scan for one new component.** Legacy debt drowns the regression. *Fix:* `scanWithin`.
- **A green scan reported as "accessible".**

## Rules

- WCAG 2.2 AA tags, excludes and false positives live in one fixture.
- One logical assertion per test: `expect(results.violations, '<subject>').toEqual([])`, or a named subset.
- Stabilize through the page object before a scan; scan once per meaningful state.
- Every scan attaches its violations and incompletes with an awaited `testInfo.attach`.
- Known debt is ticketed and only shrinks; false positives are documented.
- Specs reach pages through fixtures; selectors are built from test ids inside the fixture.
- Pair every scan of a story's form with the native assertion for what the story specifies.

## Cross-references

- `qa-accessibility-testing-dotnet`, `qa-accessibility-testing-java` — the same skill on .NET and Java.
- `references/lighthouse-ci.md` — the score-and-trend sibling.
- `qa/typescript/skills/ui-test-author/playwright/references/assertions.md` — the native accessible and aria
  assertions.
- `qa/typescript/skills/evidence-capture` — the attachments and failure evidence.
- `qa/reporting/typescript/skills/test-reports` — how the attachments appear in Allure.
- `qa-exploratory-charter-writer` — the manual and assistive-technology testing axe cannot do.
