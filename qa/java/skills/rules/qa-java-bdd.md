---
paths:
  - "**/*.feature"
  - "**/src/{test,integrationTest}/java/**/{steps,stepdefs,stepdefinitions,glue,hooks}/**/*.java"
  - "**/src/{test,integrationTest}/java/**/*{Steps,Hooks}.java"
---

<!-- qa-java rules v1 (2026-11-03): BDD. Installed by /qa-java:rules; edit the paths above to where this project keeps its feature files and step definitions. -->

# Gherkin and Cucumber-JVM standards

Severity tags as in the core qa-java rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

## Feature files

- Steps are declarative: no `click`, CSS or URL unless the mechanic is what is tested. One `When` per scenario; no conjunction steps. *major*
- `Background` holds only preconditions every scenario needs, never a `When`, `Then` or data. *major*
- Variants are a `Scenario Outline` with `Examples`, valid and invalid in separate tables (invalid tagged `@negative`). *minor*
- Steps reuse one catalog: no near-duplicate differing by a literal, one verb per concept. *minor*
- Tags carry priority, tier, type and `@AC-<n>`; every source case maps to a scenario. *minor*
- No `#` comments and no commented-out scenarios; explanation goes in the `Feature:` block, a skip is a tag with a ticket. *minor*

## Step definitions and hooks

- One glue class per domain, each catalog step bound once, Cucumber Expressions over regex. *minor*
- State reaches a step through the constructor-injected `TestContext` (PicoContainer): no static state, `ThreadLocal`, string-keyed bag, step-class inheritance or `new LoginPage(page)` in a step. *major*
- A step is one or two page-object calls: no locator, `findElement` or wait. Missing page objects are built first, never inlined. *major*
- Page objects take the `Page` or driver, never `TestContext`, and are the UI suite's own classes. *major*
- `Given` / `When` act; only `Then` asserts. *major*
- Browser and driver lifecycle live in `@Before` / `@After` hooks with teardown, never in a step constructor; cleanup is an `@After` hook, never steps. *major; blocker for a leaked browser or driver*
- The runner is the JUnit Platform `@Suite` engine, not `@RunWith(Cucumber.class)`. *major*
- No inline comments in steps or hooks. *minor*
