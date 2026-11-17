---
paths:
  - "**/*.feature"
  - "**/{steps,step-definitions}/**/*.ts"
  - "**/features/support/**/*.ts"
---

<!-- qa-typescript rules v2 (2026-11-17): BDD. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its features and steps. -->

# BDD standards (Gherkin, playwright-bdd, CucumberJS + WebdriverIO)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

## Feature files

- Steps are declarative: no clicks, CSS or URLs unless the mechanic is under test. One `When` per scenario, no conjunction steps. *major*
- `Background` holds only preconditions all scenarios need. Variants are a `Scenario Outline`, valid and invalid `Examples` split. *major*
- One phrasing per concept; one binding per field, filter or column, calling its control (`I select {string} for Deal Type filter`), never a step taking the field name. *major*
- Tags carry priority, tier, type and `@AC-<n>` traceability; every source case maps to a scenario. *minor*
- No `#` comments or commented-out scenarios. One ahead of its automation carries the excluded tag (`@not-automated` if none) and a ticket. *minor*

## Step definitions

- Every step resolves to exactly one binding; an undefined or ambiguous match fails the run. An empty binding body passes silently. *blocker*
- One binding file per domain; each step bound once; Cucumber Expressions over regex; captures typed. *major*
- A step is one or two page-object calls: no selectors, `page.locator`, `browser.$`, waits or branches. `Given`/`When` act, `Then` asserts. *major*
- The step is the intent layer: a page object may expose named elements and controls to act on (`filterPage.dealType.selectOption(option)`); page methods only for sequences. *major*
- Web (playwright-bdd): `createBdd(test)` from the fixture-extended test, arrow steps destructuring page-object fixtures, no World or `new Page(...)`; `testDir` is the generated dir, never `features/`. *major*
- Mobile (CucumberJS): a typed custom World, `function` steps, no module-level state; the appium service owns the session. *major*
- Cleanup is fixture teardown (web) or an `After` hook (mobile), never Gherkin steps; a `Given … does not exist` pre-clean via a seeder is a precondition. *major; blocker when it leaks a context or session*
- Page objects come from the existing UI project, never redeclared; a missing one is built first. *major*
- `@cucumber/cucumber` stays in `@wdio/cucumber-framework`'s peer range. *major*
