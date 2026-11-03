---
name: bdd-reviewer
description: Use when reviewing Gherkin .feature files and playwright-bdd/CucumberJS steps in TypeScript for reuse and binding. Triggers "review these feature files". Not for generating steps (gherkin-step-code).
---

# BDD / Gherkin Reviewer (TypeScript)

Audits a BDD layer across **two surfaces** — the `.feature` files (Gherkin quality / living documentation) and the TypeScript step definitions + support code (binding correctness, reuse, the **state model**, async, library rules). TypeScript has two frameworks, web (playwright-bdd) and mobile (CucumberJS + WebdriverIO); apply the rules for the one(s) the project uses. Returns findings in the standard table; does not rewrite code.

## When to use

- A `.feature` + `steps/` set exists and needs a critique.
- Steps report undefined/ambiguous matches, or the suite is flaky/duplicative.
- A PR adds BDD coverage and you want a hostile senior review.

## When NOT to use

- "Write feature files" → `qa/_shared/bdd/feature-file-writer`
- "Generate / implement step definitions" → `qa/typescript/skills/gherkin-step-code`
- Code is pseudocode / incomplete → ask for the real files.

## Procedure

1. Identify the framework (web playwright-bdd vs mobile CucumberJS+WDIO — check `package.json`, `playwright.config.ts` vs `wdio.conf.ts`).
2. Read every `.feature` file and every step file + the support layer (`steps/fixtures.ts` for web; `support/world.ts` + `support/hooks.ts` for mobile). Do not skim.
3. Walk the rule files: the feature-file rules, then the step-definition rules for the framework in use, marking each pass / fail / N/A. The severity is the tag on the rule, never a new judgment.
4. Produce findings in the standard table. Point to fixes; do not rewrite.
5. Close with an "Overall" paragraph and a coverage/traceability note (every TC-ID + AC accounted for?).

## The checklist is the rule files

Every check, and the severity it reports, lives in one place: the qa-typescript rule files `bdd.md` (feature files and step definitions) and `qa-typescript.md` (core, for the TypeScript step and support code). Each `bdd.md` rule names which framework it binds: apply the web (playwright-bdd) or mobile (CucumberJS + WebdriverIO) rule the project uses.

1. **The project's copies first**: `.claude/rules/qa-typescript/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `qa/typescript/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/qa-typescript:rules` installs them.

Read both files in full before the first finding; a rule loaded on its own by the session is not enough. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead. The rule files' "the codebase wins" line applies.

## Output format

```
| Severity | Location                       | Issue                                   | Suggested fix                          |
|----------|--------------------------------|-----------------------------------------|----------------------------------------|
| major    | login.feature:12               | Imperative step "tap #submit"           | Raise to "When I sign in…"; move mechanic to LoginScreen |
| major    | authentication.steps.ts:20     | Arrow-function CucumberJS step          | Use `function (this: CustomWorld)`; reach page via this |
| major    | authentication.steps.ts:8      | new LoginPage(page) inside step (web)   | Register a fixture in steps/fixtures.ts; destructure it |
| minor    | cart.steps.ts:8                | Two near-duplicate add-item steps       | Parameterize: "I add {int} items"      |
```

After the table, add an **Overall** paragraph (2–3 sentences) and a **Traceability** line (TC-IDs/ACs covered vs gaps ⚠️).

End with one line: `Rules: project .claude/rules/qa-typescript/ | plugin copy (not installed)`.

## Examples

Input: a `login.feature` whose every scenario repeats `Given I open "/login"` / `When I fill "#email"…` and a single `login.steps.ts` (playwright-bdd) newing up the page object per step with `function`-style bodies.

Findings: imperative steps (major) → factor login into `Background` + declarative step; per-step `new LoginPage` (major) → register a fixture and destructure it; `function`/`this` style in a playwright-bdd project (major) → switch to arrow + fixture destructuring (no World on the web path); mechanics in steps (major) → move to `LoginPage`. Overall: the layer works but reads as a script, not documentation, and uses the wrong state model for the web framework.
