---
name: bdd-reviewer
description: Use when reviewing or auditing existing Gherkin `.feature` files and Reqnroll step definitions in C#/.NET for living-documentation quality, step reusability, and correct binding/DI/lifecycle. Triggers "review these feature files", "audit our Reqnroll step definitions", "are these Gherkin scenarios good", "check our BDD layer". Not for generating features (`feature-file-writer`) or step definitions (`gherkin-step-code`).
---

# Reqnroll / Gherkin Reviewer (C# / .NET 10)

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
- [ ] **No `#` comments in the feature file.** A `.feature` is living documentation — if a step needs explaining, the step is wrong; if the *feature* needs explaining, use the `Feature:` description block. Only a linked defect id beside a `@wip`/skip tag is permitted (`minor`).
- [ ] **No commented-out scenarios or steps.** A `#`-prefixed `Scenario` left in place of deletion is dead documentation that still reads as a requirement (`minor`); disable with a tag carrying a ticket instead.

## Reqnroll / step-definition checklist

- [ ] Step definitions split by domain (no mega `Steps.cs`); each catalog step bound exactly once.
- [ ] Cucumber Expressions (`{string}`/`{int}`/…) over regex unless regex is genuinely needed.
- [ ] Shared state injected via `ScenarioState` (scoped DI) through the constructor — no static mutable state, no `new`-ing page objects, no `ScenarioContext` string-bag for typed state.
- [ ] No selectors / `IPage.Locator(...)` / waits in step definitions — mechanics live in page objects.
- [ ] `Then` steps assert (web-first `Expect`); `Given`/`When` don't assert — not even a "page loaded" check; page objects never assert.
- [ ] **Every assertion states one expected condition** — no `Is.AnyOf(...)`, `.Or.`, `||` inside `Assert.That`, `Regex("a|b")` in a text or URL assertion, or an assertion on an `Or()` locator.
- [ ] **No `try`/`catch` (or `finally`) in a step or a hook** — an expected exception is `Assert.ThrowsAsync<T>`; cleanup is an `[AfterScenario]` hook.
- [ ] `async Task` steps for Playwright; every page-object call awaited; no `.Result`/`.Wait()`/`async void`.
- [ ] No `Thread.Sleep` / `Task.Delay` / `WaitForTimeoutAsync` — auto-wait + web-first assertions only.
- [ ] The page objects a step calls use no `WaitUntil = WaitUntilState.NetworkIdle`, no `Force = true`, no `WaitForNavigationAsync` and no page-level selector API (`Page.ClickAsync(selector)`, `Page.InnerTextAsync(selector)`); URL checks use `ToHaveURLAsync(new Regex(...))`, never a glob string.
- [ ] Browser/driver lifecycle in `[BeforeScenario]`/`[AfterScenario]` hooks with **teardown** (no leaked browsers); not in step constructors. The browser comes from the runsettings and the context's `BaseURL` from `BASE_URL` — no hardcoded browser, headless flag or host.
- [ ] **Failure evidence**: the closing `[AfterScenario]` keeps a trace, a full-page screenshot and the video when `ScenarioContext.TestError` is set — in `<WorkDirectory>/playwright-artifacts/<Feature>.<Scenario>.{zip,png,webm}`, attached to NUnit and Allure, in `BaseTest`'s order with no catch (`qa/dotnet/skills/evidence-capture`, `bdd-project-scaffold`).
- [ ] Cleanup implemented as an `[AfterScenario]` hook, not as Gherkin steps.
- [ ] `[ScenarioDependencies]` is static, returns `IServiceCollection`, and does not manually register `[Binding]` classes.
- [ ] No hardcoded credentials/URLs — env vars / config.
- [ ] **No inline comments in step definitions or hooks** — the step text above the binding is already the explanation, and a body long enough to need narration belongs in a page object. XML doc only where the binding's contract can't be read off the step text and the method name; no commented-out bindings, no stray `TODO`/`FIXME`. Full rule, complex-flow test, and severities: [`engineering-practices/code-comments`](../../../../engineering-practices/code-comments/SKILL.md).

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

- **blocker**: undefined/ambiguous step that fails the run; leaked browser/driver; `Thread.Sleep`/`Task.Delay` as a wait; ships a bug.
- **major**: imperative/UI-coupled Gherkin; selectors or `new`/static state in steps; assertion in a page object or a `Given`/`When`; an `OR` in an assertion; `try`/`catch` in a step or hook; `NetworkIdle`, `Force = true` or a deprecated wait; no failure evidence on a failed scenario; conjunction step that hides a second behavior.
- **minor**: duplicate steps that should be parameterized; missing tags; naming.
- **nit**: optional phrasing/style preferences.

## Examples

Input: a `Login.feature` whose every scenario repeats `Given I visit "/login"` / `When I fill "#email"…` and a single `LoginSteps.cs` newing up the page object per step.

Findings: imperative steps (major) → factor login into `Background` + declarative step; per-step `new LoginPage` (major) → inject `ScenarioState`; mechanics in steps (major) → move to `LoginPage`. Overall: the layer works but reads as a script, not documentation, and duplicates mechanics across scenarios.
