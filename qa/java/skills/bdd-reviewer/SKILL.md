---
name: bdd-reviewer
description: Use when reviewing Gherkin .feature files and Cucumber-JVM steps in Java for reuse and binding. Triggers "review these feature files". Not for generating steps (gherkin-step-code).
disable-model-invocation: true
---

# Cucumber-JVM / Gherkin Reviewer (Java 21)

Audits a BDD layer across **two surfaces** — the `.feature` files (Gherkin quality / living documentation) and the Cucumber-JVM step definitions + support code (binding correctness, reuse, DI, lifecycle, library rules). Returns findings in the standard table; does not rewrite code.

## The checklist is the rule file

Every check, and the severity it reports, lives in one place: the qa-java rule files `qa-java-bdd.md` (feature files, glue, hooks) and `qa-java.md` (core), plus `qa-java-ui.md` and `qa-java-page-objects.md` when page objects are in scope, and `qa-java-data.md` when steps seed, pre-clean or read reference data.

1. **The project's copies first**: `.claude/rules/qa-java/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `qa/java/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/qa-java:rules` installs them.

Read each of these files that applies, in full, before the first finding. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

**Version policy.** Detect the Cucumber BOM and the JUnit Platform engine first; the rule files' "the codebase wins" line applies.

## Procedure

1. Read every `.feature` file and every glue class + the support layer (`TestContext`, `Hooks`, the runner `@Suite`/`junit-platform.properties`). Do not skim.
2. Walk `qa-java-bdd.md` (feature files, then step definitions and hooks), then the core rules, marking each rule pass / fail / N/A.
3. Produce findings in the standard table. Point to fixes; do not rewrite.
4. Close with an "Overall" paragraph and a coverage/traceability note (every TC-ID + AC accounted for?).

## Output format

```
| Severity | Location                       | Issue                                   | Suggested fix                          |
|----------|--------------------------------|-----------------------------------------|----------------------------------------|
| major    | Login.feature:12               | Imperative step "click #submit"         | Raise to "When I sign in…"; move mechanic to LoginPage |
| major    | AuthenticationSteps.java:20    | new LoginPage(page) inside step         | Inject TestContext; reach page via context |
| major    | FilterSteps.java:14            | "I select {string} for {string} filter" maps a field name to a control | One binding per filter: "I select {string} for Deal Type filter" |
| blocker  | DealSteps.java:31              | Step body is empty: the scenario passes doing nothing | Implement it, or tag the scenario `@not-automated` with a ticket and remove the binding |
```

After the table, add an **Overall** paragraph (2–3 sentences) and a **Traceability** line (TC-IDs/ACs covered vs. gaps ⚠️).

## Severity

The severity is the tag on the rule, never a new judgment. An undefined or ambiguous step that fails the run is a **blocker**: the build is broken, and so is a binding with an empty body, which passes without doing anything. A step that makes one interaction on an element or control its page object exposes (`filterPage.dealType().selectOption(option)`) is the BDD intent layer, not a finding; a locator, wait or branch in the step still is. A `Then` that checks every row asserts the column is not empty first (`qa-java-data.md`). End with one line: `Rules: project .claude/rules/qa-java/ | plugin copy (not installed)`.

## Examples

Input: a `Login.feature` whose every scenario repeats `Given I visit "/login"` / `When I fill "#email"…` and a single `LoginSteps.java` newing up the page object per step.

Findings: imperative steps (major) → factor login into `Background` + declarative step; per-step `new LoginPage` (major) → inject `TestContext`; mechanics in steps (major) → move to `LoginPage`. Overall: the layer works but reads as a script, not documentation, and duplicates mechanics across scenarios.
