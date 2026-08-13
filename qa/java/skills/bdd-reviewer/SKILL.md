---
name: qa-bdd-reviewer-java
description: Use when reviewing or auditing existing Gherkin .feature files and Cucumber-JVM step definitions in Java for living-documentation quality, step reusability, and correct binding/DI/lifecycle. Triggers: "review these feature files", "audit our Cucumber step definitions", "are these Gherkin scenarios good", "check our BDD layer". Do NOT use to generate features (use `qa/_shared/bdd/feature-file-writer`) or step definitions (use `qa/java/skills/gherkin-step-code`). For end-to-end suite work prefer the phased agent `qa-bdd-java` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# Cucumber-JVM / Gherkin Reviewer (Java 21)

Audits a BDD layer across **two surfaces** — the `.feature` files (Gherkin quality / living documentation) and the Cucumber-JVM step definitions + support code (binding correctness, reuse, DI, lifecycle, library rules). Returns findings in the standard table; does not rewrite code.

## When to use

- A `.feature` + `steps/` set exists and needs a critique.
- Steps report undefined/ambiguous matches, or the suite is flaky/duplicative.
- A PR adds BDD coverage and you want a hostile senior review.

## When NOT to use

- "Write feature files" → `qa/_shared/bdd/feature-file-writer`
- "Generate / implement step definitions" → `qa/java/skills/gherkin-step-code`
- Code is pseudocode / incomplete → ask for the real files.

## Procedure

1. Read every `.feature` file and every glue class + the support layer (`TestContext`, `Hooks`, the runner `@Suite`/`junit-platform.properties`). Do not skim.
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

## Cucumber-JVM / step-definition checklist

- [ ] Step definitions split by domain (no mega `Steps.java`); each catalog step bound exactly once.
- [ ] Cucumber Expressions (`{string}`/`{int}`/…) over regex unless regex is genuinely needed.
- [ ] Shared state injected via `TestContext` through the constructor (PicoContainer) — no static mutable state, no `ThreadLocal` in the glue, no `new`-ing page objects, no string-keyed bag for typed state.
- [ ] No step-class inheritance to share state (Cucumber doesn't support it) — `TestContext` injection only.
- [ ] No selectors / `page.locator(...)` / `findElement` / waits in step definitions — mechanics live in page objects.
- [ ] `Then` steps assert (web-first `assertThat`); `Given`/`When` don't assert; page objects don't assert (except `expectLoaded()`).
- [ ] No `Thread.sleep` / `page.waitForTimeout(...)` — auto-wait + web-first assertions (or `WebDriverWait` in the page object) only.
- [ ] Browser/driver lifecycle in `@Before`/`@After` hooks with **teardown** (no leaked browsers/drivers); not in step constructors. Tagged hooks (`@Before("@web")`) where the project spans platforms.
- [ ] Cleanup implemented as an `@After` hook, not as Gherkin steps.
- [ ] Idiomatic JUnit 5 Platform runner (`@Suite` + `cucumber-junit-platform-engine`), not the deprecated JUnit 4 `@RunWith(Cucumber.class)`; glue path + plugins configured.
- [ ] No hardcoded credentials/URLs — env vars / system properties.
- [ ] **No inline comments in step definitions or hooks** — the step text above the binding is already the explanation, and a body long enough to need narration belongs in a page object. Javadoc only where the binding's contract can't be read off the step text and the method name; no commented-out bindings, no stray `TODO`/`FIXME`. Full rule, complex-flow test, and severities: [`ep-code-comments`](../../../../engineering-practices/code-comments/SKILL.md).

## Output format

```
| Severity | Location                       | Issue                                   | Suggested fix                          |
|----------|--------------------------------|-----------------------------------------|----------------------------------------|
| major    | Login.feature:12               | Imperative step "click #submit"         | Raise to "When I sign in…"; move mechanic to LoginPage |
| major    | AuthenticationSteps.java:20    | new LoginPage(page) inside step         | Inject TestContext; reach page via context |
| minor    | CartSteps.java:8               | Two near-duplicate add-item steps       | Parameterize: "I add {int} items"      |
```

After the table, add an **Overall** paragraph (2–3 sentences) and a **Traceability** line (TC-IDs/ACs covered vs. gaps ⚠️).

## Severity guide

- **blocker**: undefined/ambiguous step that fails the run; leaked browser/driver; ships a bug.
- **major**: imperative/UI-coupled Gherkin; selectors or `new`/static state in steps; assertion in a page object; conjunction step that hides a second behavior; deprecated JUnit 4 runner.
- **minor**: duplicate steps that should be parameterized; missing tags; naming.
- **nit**: optional phrasing/style preferences.

## Examples

Input: a `Login.feature` whose every scenario repeats `Given I visit "/login"` / `When I fill "#email"…` and a single `LoginSteps.java` newing up the page object per step.

Findings: imperative steps (major) → factor login into `Background` + declarative step; per-step `new LoginPage` (major) → inject `TestContext`; mechanics in steps (major) → move to `LoginPage`. Overall: the layer works but reads as a script, not documentation, and duplicates mechanics across scenarios.
