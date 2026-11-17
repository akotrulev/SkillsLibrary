---
paths:
  - "**/*.feature"
  - "**/{StepDefinitions,Steps,Hooks}/**/*.cs"
  - "**/*{BddTests,Bdd.Tests}/**/*.cs"
---

<!-- qa-dotnet rules v2 (2026-11-17): BDD. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its feature files and Reqnroll bindings. -->

# Gherkin and Reqnroll standards

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

## Feature files

- Steps are declarative: no clicks, CSS or URLs unless the mechanic is the subject. *major*
- One `When` per scenario; no conjunction step hiding a second behaviour. *major*
- `Background` holds only preconditions every scenario needs: no `When`, `Then` or data. *minor*
- Variants are a `Scenario Outline` with `Examples`, one behaviour per outline; invalid rows get their own `Examples` tagged `@negative`. *minor*
- One phrasing per concept; one step per field, filter or column, named after it (`I select {string} for Deal Type filter`), never a generic step taking the field name. *major*
- Tags carry priority, tier, type and `@AC-<n>`; every source TC-ID or AC maps to a scenario. *minor*
- No `#` comments or commented-out scenarios; explain in the `Feature:` block, disable with a tag and a ticket. *minor*

## Step definitions and hooks

- Each catalogue step is bound exactly once; an undefined or ambiguous step fails the run. *blocker*
- Bindings split by domain, no mega `Steps.cs`; Cucumber Expressions over regex. *minor*
- State is the scoped `ScenarioState`, constructor-injected: no static state, no `new` page objects, no `ScenarioContext` string bag. *major*
- The step is the intent layer: a step may act on a control or element the page exposes (`filterPage.DealType.SelectAsync(option)`); a page method only wraps a sequence. One interaction or assertion per step; no branch, locator or wait; page objects come from the UI project, not redeclared. *major*
- A binding with an empty body passes doing nothing; a feature ahead of its automation carries the suite's skip tag (`@not-automated` if none) and a ticket. *blocker*
- `Then` asserts; `Given` and `When` never do, not even a "page loaded" check. *major*
- Browser lifecycle and cleanup are `[BeforeScenario]` / `[AfterScenario]` hooks, never steps; the closing hook keeps trace, screenshot and video when `TestError` is set. *blocker for a leaked browser*
- `[ScenarioDependencies]` is static, returns `IServiceCollection`, registers no `[Binding]` class. *minor*
