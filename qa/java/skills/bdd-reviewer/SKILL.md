---
name: bdd-reviewer
description: Use when reviewing Gherkin .feature files and Cucumber-JVM steps in Java for reuse and binding. Triggers "review these feature files". Not for generating steps (gherkin-step-code).
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

## The checklist is the rule file

Every check, and the severity it reports, lives in one place: the qa-java rule files `qa-java-bdd.md` (feature files, glue, hooks) and `qa-java.md` (core), plus `qa-java-ui.md` when page objects are in scope.

1. **The project's copies first**: `.claude/rules/qa-java/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `qa/java/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/qa-java:rules` installs them.

Read each file whose `paths:` match a file under review, in full, before the first finding. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

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
| minor    | CartSteps.java:8               | Two near-duplicate add-item steps       | Parameterize: "I add {int} items"      |
```

After the table, add an **Overall** paragraph (2–3 sentences) and a **Traceability** line (TC-IDs/ACs covered vs. gaps ⚠️).

## Severity

The severity is the tag on the rule, never a new judgment. An undefined or ambiguous step that fails the run is a **blocker**: the build is broken. End with one line: `Rules: project .claude/rules/qa-java/ | plugin copy (not installed)`.

## Examples

Input: a `Login.feature` whose every scenario repeats `Given I visit "/login"` / `When I fill "#email"…` and a single `LoginSteps.java` newing up the page object per step.

Findings: imperative steps (major) → factor login into `Background` + declarative step; per-step `new LoginPage` (major) → inject `TestContext`; mechanics in steps (major) → move to `LoginPage`. Overall: the layer works but reads as a script, not documentation, and duplicates mechanics across scenarios.
