---
paths:
  - "**/*.feature"
  - "**/{steps,step-definitions}/**/*.ts"
  - "**/features/support/**/*.ts"
---

<!-- qa-typescript rules v1 (2026-11-03): BDD. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its feature files and step definitions. -->

# BDD standards (Gherkin, playwright-bdd, CucumberJS + WebdriverIO)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

## Feature files

- Steps are declarative: no clicks, CSS or URLs unless the mechanic is what is tested. One `When` per scenario, no conjunction steps. *major*
- `Background` holds only preconditions every scenario needs. Variants are a `Scenario Outline` with valid and invalid `Examples` split. *major*
- Steps reuse a canonical phrasing; no near-duplicates differing by a literal. *minor*
- Tags carry priority, tier, type and AC traceability (`@AC-<n>`); every source case maps to a scenario. *minor*
- No `#` comments and no commented-out scenarios; disable with a tag and ticket. *minor*

## Step definitions

- Every step resolves to exactly one binding; an undefined or ambiguous match fails the run. *blocker*
- One binding file per domain; each step bound once; Cucumber Expressions over regex; captures typed. *major*
- A step is one or two page-object calls: no selectors, `page.locator`, `browser.$` or waits. `Given`/`When` act, `Then` asserts. *major*
- Web (playwright-bdd): `createBdd(test)` from the fixture-extended test, arrow functions destructuring page-object fixtures, no World, no `new Page(...)` in a step; `testDir` is the generated dir, never `features/`. *major*
- Mobile (CucumberJS): state through a typed custom World, `function` steps (never arrows), no module-level state; the appium service owns the session. *major*
- Cleanup is fixture teardown (web) or an `After` hook (mobile), never Gherkin steps. *major; blocker when a missing teardown leaks a context or session*
- Page objects are imported from the existing UI project, not redeclared. A missing one is built first, never inlined. *major*
- `@cucumber/cucumber` stays in the range `@wdio/cucumber-framework` takes as a peer. *major*
