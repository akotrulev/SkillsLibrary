---
name: qa-bdd-reviewer-dotnet
description: Use when reviewing or auditing existing Gherkin `.feature` files and Reqnroll step definitions in C#/.NET for living-documentation quality, step reusability, and correct binding/DI/lifecycle. Triggers "review these feature files", "audit our Reqnroll step definitions", "are these Gherkin scenarios good", "check our BDD layer". Not for generating features (`feature-file-writer`) or step definitions (`gherkin-step-code`).
---

# Reqnroll / Gherkin Reviewer (C# / .NET 8)

Audits a BDD layer across **two surfaces** — the `.feature` files (Gherkin quality / living documentation) and the Reqnroll step definitions + support code (binding correctness, reuse, DI, async, library rules). Returns findings in the standard table; does not rewrite code.

## When to use

- A `.feature` + `StepDefinitions/` set exists and needs a critique.
- Steps report undefined/ambiguous matches, or the suite is flaky/duplicative.
- A PR adds BDD coverage and you want a hostile senior review.

## When NOT to use

- "Write feature files" → `qa/_shared/bdd/feature-file-writer`
- "Generate / implement step definitions" → `qa/dotnet/skills/gherkin-step-code`
- Code is pseudocode / incomplete → ask for the real files.

## Procedure

1. Read every `.feature` file and every `[Binding]` class + the support layer (`ScenarioState`, hooks, `[ScenarioDependencies]`). Do not skim.
2. Walk both checklists, marking each item pass / fail / N/A.
3. Produce findings in the standard table. Point to fixes; do not rewrite.
4. Close with an "Overall" paragraph and a coverage/traceability note (every TC-ID + AC accounted for?).

## Gherkin checklist (`.feature` files)

- [ ] Steps are declarative — no `click`/`type`/CSS/URLs unless the mechanic is the subject under test.
- [ ] One event under test per scenario (one `When`); no conjunction steps.
- [ ] `Background` holds only preconditions every scenario needs; no `When`/`Then`/data in it.
- [ ] Data-driven variants use `Scenario Outline` + `Examples`, one behavior per outline; valid/invalid split into separate `Examples` (invalid tagged `@negative`).
- [ ] Steps reuse a canonical catalog — no near-duplicate steps differing only by a literal; one verb per concept.
- [ ] Tags carry priority (`@p1..`), tier (`@smoke`/`@regression`), type (`@negative`/`@boundary`/`@edge`), and AC traceability (`@AC-<n>`).
- [ ] Each scenario reads as documentation without the code; names state behavior, not data.
- [ ] Every TC-ID / AC from the source suite maps to a scenario (no silent gaps).

## Reqnroll / step-definition checklist

- [ ] Step definitions split by domain (no mega `Steps.cs`); each catalog step bound exactly once.
- [ ] Cucumber Expressions (`{string}`/`{int}`/…) over regex unless regex is genuinely needed.
- [ ] Shared state injected via `ScenarioState` (scoped DI) through the constructor — no static mutable state, no `new`-ing page objects, no `ScenarioContext` string-bag for typed state.
- [ ] No selectors / `IPage.Locator(...)` / waits in step definitions — mechanics live in page objects.
- [ ] `Then` steps assert (web-first `Expect`); `Given`/`When` don't assert; page objects don't assert (except `ExpectLoadedAsync()`).
- [ ] `async Task` steps for Playwright; every page-object call awaited; no `.Result`/`.Wait()`/`async void`.
- [ ] No `Thread.Sleep` / `WaitForTimeoutAsync` — auto-wait + web-first assertions only.
- [ ] Browser/driver lifecycle in `[BeforeScenario]`/`[AfterScenario]` hooks with **teardown** (no leaked browsers); not in step constructors.
- [ ] Cleanup implemented as an `[AfterScenario]` hook, not as Gherkin steps.
- [ ] `[ScenarioDependencies]` is static, returns `IServiceCollection`, and does not manually register `[Binding]` classes.
- [ ] No hardcoded credentials/URLs — env vars / config.

## Output format

```
| Severity | Location                       | Issue                                   | Suggested fix                          |
|----------|--------------------------------|-----------------------------------------|----------------------------------------|
| major    | Login.feature:12               | Imperative step "click #submit"         | Raise to "When I sign in…"; move mechanic to LoginPage |
| major    | AuthenticationSteps.cs:20      | new LoginPage(page) inside step         | Inject ScenarioState; reach page via _state |
| minor    | CartSteps.cs:8                 | Two near-duplicate add-item steps       | Parameterize: "I add {int} items"      |
```

After the table, add an **Overall** paragraph (2–3 sentences) and a **Traceability** line (TC-IDs/ACs covered vs. gaps ⚠️).

## Severity guide

- **blocker**: undefined/ambiguous step that fails the run; leaked browser/driver; ships a bug.
- **major**: imperative/UI-coupled Gherkin; selectors or `new`/static state in steps; assertion in a page object; conjunction step that hides a second behavior.
- **minor**: duplicate steps that should be parameterized; missing tags; naming.
- **nit**: optional phrasing/style preferences.

## Examples

Input: a `Login.feature` whose every scenario repeats `Given I visit "/login"` / `When I fill "#email"…` and a single `LoginSteps.cs` newing up the page object per step.

Findings: imperative steps (major) → factor login into `Background` + declarative step; per-step `new LoginPage` (major) → inject `ScenarioState`; mechanics in steps (major) → move to `LoginPage`. Overall: the layer works but reads as a script, not documentation, and duplicates mechanics across scenarios.
