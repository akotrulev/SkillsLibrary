---
name: bdd-reviewer
description: Use when reviewing Gherkin .feature files and Reqnroll steps in .NET for reuse and binding. Triggers "review these feature files". Not for generating steps (gherkin-step-code).
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

## The checklist is the rule file

Every check, and the severity it reports, lives in one place: the qa-dotnet rule files `bdd.md` (feature files, step definitions, hooks), `automation.md` (core: assertions, async, errors, waits, comments) and `web-ui.md` or `mobile-ui.md` for the page objects the steps call.

1. **The project's copies first**: `.claude/rules/qa-dotnet/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `qa/dotnet/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/qa-dotnet:rules` installs them.

Read every file that applies in full before the first finding. A rule loaded on its own by the session is not enough. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead. The rule file's "the codebase wins" line applies.

## Procedure

1. Read the rule files, then every `.feature` file, every `[Binding]` class and the support layer (`ScenarioState`, hooks, `[ScenarioDependencies]`). Do not skim.
2. Walk `bdd.md` over both surfaces, then the core and UI rules over the bindings, marking each pass / fail / N/A.
3. Produce findings in the standard table; the severity is the tag on the rule. Point to fixes; do not rewrite.
4. Close with an "Overall" paragraph and a coverage/traceability note (every TC-ID + AC accounted for?).

## Output format

```
| Severity | Location                       | Issue                                   | Suggested fix                          |
|----------|--------------------------------|-----------------------------------------|----------------------------------------|
| major    | Login.feature:12               | Imperative step "click #submit"         | Raise to "When I sign in…"; move mechanic to LoginPage |
| major    | AuthenticationSteps.cs:20      | new LoginPage(page) inside step         | Inject ScenarioState; reach page via _state |
| minor    | CartSteps.cs:8                 | Two near-duplicate add-item steps       | Parameterize: "I add {int} items"      |
```

After the table, add a `Rules: project .claude/rules/qa-dotnet/ | plugin copy (not installed)` line, then an **Overall** paragraph (2–3 sentences) and a **Traceability** line (TC-IDs/ACs covered vs. gaps ⚠️).

## Examples

Input: a `Login.feature` whose every scenario repeats `Given I visit "/login"` / `When I fill "#email"…` and a single `LoginSteps.cs` newing up the page object per step.

Findings: imperative steps (major) → factor login into `Background` + declarative step; per-step `new LoginPage` (major) → inject `ScenarioState`; mechanics in steps (major) → move to `LoginPage`. Overall: the layer works but reads as a script, not documentation, and duplicates mechanics across scenarios.
