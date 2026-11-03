---
paths:
  - "**/*.feature"
  - "**/{StepDefinitions,Steps,Hooks}/**/*.cs"
  - "**/*{BddTests,Bdd.Tests}/**/*.cs"
---

<!-- qa-dotnet rules v1 (2026-11-03): BDD. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its feature files and Reqnroll bindings. -->

# Gherkin and Reqnroll standards

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

## Feature files

- Steps are declarative: no clicks, CSS or URLs unless the mechanic is the subject. *major*
- One `When` per scenario; no conjunction step hiding a second behaviour. *major*
- `Background` holds only preconditions every scenario needs: no `When`, `Then` or data. *minor*
- Variants are a `Scenario Outline` with `Examples`, one behaviour per outline; invalid rows get their own `Examples` tagged `@negative`. *minor*
- Reuse the step catalogue: one verb per concept, no near-duplicates that differ by a literal. *minor*
- Tags carry priority, tier, type and `@AC-<n>`; every source TC-ID or AC maps to a scenario. *minor*
- No `#` comments or commented-out scenarios; explain in the `Feature:` block, disable with a tag and a ticket. *minor*

## Step definitions and hooks

- Each catalogue step is bound exactly once; an undefined or ambiguous step fails the run. *blocker*
- Bindings split by domain, no mega `Steps.cs`; Cucumber Expressions over regex. *minor*
- State is the scoped `ScenarioState`, constructor-injected: no static state, no `new` page objects, no `ScenarioContext` string bag. *major*
- No locators or waits in a step: mechanics live in the UI project's page objects, referenced, not redeclared. *major*
- `Then` asserts; `Given` and `When` never do, not even a "page loaded" check. *major*
- Browser lifecycle and cleanup are `[BeforeScenario]` / `[AfterScenario]` hooks, never steps; the closing hook keeps trace, screenshot and video when `TestError` is set. *blocker for a leaked browser*
- `[ScenarioDependencies]` is static, returns `IServiceCollection`, registers no `[Binding]` class. *minor*
