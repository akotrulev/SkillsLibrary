---
name: qa-feature-file-writer
description: Use when turning a manual test-case suite (or raw acceptance criteria) into clean, reusable Gherkin feature files for living documentation — framework-agnostic. Triggers: "convert these test cases to Gherkin", "write feature files for this suite", "structure these scenarios with a Background", "make these steps declarative". Do NOT use to generate step-definition code (the stack's `gherkin-step-code`), scaffold the BDD project (`bdd-project-setup`), or design test cases (`test-case-writer`).
---

# Gherkin Authoring — Test Cases → Living-Documentation Feature Files

Framework-agnostic engine that transforms a **manual test-case suite** (the `qa/manual/test-case-writer` artifact: Setup → Cases table → Cleanup → Coverage Summary) into **clean, deduplicated, declarative `.feature` files** whose steps form a small reusable catalog. The output is the shared input for every stack's `gherkin-step-code` skill (Reqnroll / Cucumber-JVM / playwright-bdd / CucumberJS) and doubles as living documentation.

This skill owns the **Gherkin**, not the code. It decides scenario shape, Background factoring, Scenario Outline vs separate scenarios, tags, and the canonical phrasing of every step. It never writes `[Binding]`/glue.

## When to use

- A `qa-test-case-designer` suite (TC-IDs, steps, expected results, test data) needs to become `.feature` files.
- Acceptance criteria / a story needs feature files and no test-case suite exists yet (derive scenarios directly, but prefer running `qa/manual/test-case-writer` first).
- Existing `.feature` files have inconsistent, imperative, or duplicated steps and need canonicalizing.

## When NOT to use

- Generating step definitions / glue code → the stack's `gherkin-step-code` (Reqnroll / Cucumber-JVM / playwright-bdd|CucumberJS).
- Wiring the BDD framework into a project → the stack's `bdd-project-setup`.
- Designing test cases / applying ISTQB techniques → `qa/manual/test-case-writer` + `qa/manual/test-design-techniques`.
- Deciding which page objects exist → `qa/{stack}/skills/page-object-design`.

## Inputs needed

Confirm at most 2–3; infer the rest from the suite.

1. **The test-case suite** (path or pasted) — the Setup/Cases/Cleanup/Coverage artifact. If only ACs exist, say so and derive scenarios from them.
2. **Feature grouping** — one `.feature` per feature/page (default: group by the `TC-<FEATURE>-` prefix).
3. **Target features directory** — default `Features/` for .NET, `src/test/resources/features/` for Java, `features/` for TS (the scaffold skill owns the exact path).
4. **Platform note** — web, mobile, or both (only affects tags like `@web`/`@mobile`, never step wording).

## Core decisions

### 1. Test case → scenario mapping (the contract)

| Test-case artifact element | Becomes in Gherkin |
|---|---|
| One Cases-table row (one TC-ID) | One `Scenario` (or one `Examples` row of a `Scenario Outline`) |
| Title | `Scenario:` name (behavioral, no UI verbs) |
| **Setup** block (shared preconditions, e.g. login) | **`Background:`** — only the steps *every* scenario in the feature needs |
| Per-case **Preconditions (delta from Setup)** | Leading `Given` steps in that scenario |
| Steps (numbered, atomic) | `When` (the action under test) + supporting `Given`s |
| Expected Result | `Then` (+ `And` for additional observable outcomes) |
| Test Data | Inline step parameters, or an `Examples:` table when ≥2 rows share one behavior |
| Priority (P1/P2/P3) | Tag `@p1` / `@p2` / `@p3`; every `@p1` also gets `@regression` — P1 is the suite's regression floor |
| Type (positive/negative) | Tag `@negative` (positive needs none); add `@boundary` when the Technique column says BVA, `@edge` when it says error guessing |
| Technique (EP/BVA/…) | Drives Outline-vs-scenarios choice (see #4) and the `@boundary`/`@edge` tags above; not a tag itself |
| Source (`AC2` / `BR-1` / `TP-012` / `#observed` / `#assumption`) | Tag `@AC-<n>` / `@BR-<n>` / `@TP-<n>` on each scenario so traceability survives into living docs; `#assumption` cases get `@assumption` and stay out of `@regression` until confirmed |
| Cleanup block | **Not** Gherkin — handed to `gherkin-step-code` as `@AfterScenario`/`After` hook notes (record it in the handoff, not the `.feature`) |

### 2. Declarative over imperative (the central rule)

Every step describes **behavior**, not mechanics. Litmus test: *"Would this step's wording have to change if only the UI changed?"* If yes, raise the altitude.

- ❌ `When I enter "bob@test.com" in the "#email" field` / `And I click the "Sign in" button`
- ✅ `When I sign in as a registered customer` (mechanics live in the step definition + page object)

Keep one user-visible intent per step. The manual suite's steps are often at intent altitude already — collapse multi-line mechanical sequences ("enter email / enter password / click submit") into a single declarative step.

### 3. Background — factor shared preconditions

Put a step in `Background:` **only when every scenario in the feature genuinely needs it** (the classic case: log in as a user). If only some scenarios share it, leave it as a `Given` in those scenarios — a Background that doesn't apply to all hides context and misleads the living docs. Never put the action-under-test or assertions in a Background.

### 4. Scenario Outline vs separate scenarios

- **Same behavior, many data rows** (EP valid/invalid partitions, BVA boundaries, pricing tiers) → one `Scenario Outline` + `Examples:` table. This is where the test-case **Test Data** column and boundary/EP technique rows collapse cleanly.
- **Different behaviors** (login success vs lockout-after-5-attempts) → **separate, named** scenarios even if inputs look similar. Don't force distinct outcomes into one Outline.
- One `Examples` table per equivalence intent; split valid vs invalid into two `Examples` blocks (tag the invalid one `@negative`) rather than a mixed table.

### 5. Reusable step catalog (dedupe)

Maintain one **step catalog** across the whole suite. Before writing a new step, check the catalog for an existing step that differs only in a literal — if so, **parameterize the existing step** instead of adding a near-duplicate. Phrasing rules:

- Pick **one** canonical verb per concept (`sign in`, not a mix of "log in"/"authenticate"/"sign on").
- Parameters as quoted strings or numbers so they map to Cucumber-Expression `{string}`/`{int}` downstream: `Given I am signed in as "{role}"`, `When I add {int} items to the cart`.
- Use ubiquitous domain language from the test basis, not the implementation's identifiers.
- Avoid conjunction steps (`When I do X and Y`) — split into two steps, or use the `*` bullet keyword for list-like consecutive steps.

### 6. Tags

`@p1/@p2/@p3` (priority) · `@smoke`/`@regression` (tier — `@regression` = every P1) · `@negative`/`@boundary`/`@edge` (type) · `@AC-<n>`/`@BR-<n>`/`@TP-<n>`/`@assumption` (traceability, from the Source column) · `@web`/`@mobile` (platform, only if the suite spans both). Feature-level tags are inherited — put `@regression` at the top and only override per scenario.

## Output format

1. One `.feature` file per feature, written to the features directory:

```gherkin
@regression @AC-1 @AC-2
Feature: Login
  As a registered customer
  I want to sign in
  So that I can access my dashboard

  Background:
    Given I am on the login page

  @p1 @smoke @AC-1
  Scenario: Sign in with valid credentials
    When I sign in as a registered customer
    Then I land on the dashboard

  @p2 @negative @AC-2
  Scenario Outline: Sign in is rejected for invalid credentials
    When I sign in with email "<email>" and password "<password>"
    Then I see the error "<message>"

    Examples:
      | email           | password | message              |
      | bob@test.com    | wrong    | Invalid credentials  |
      | not-an-email    | Valid1!  | Enter a valid email  |
```

2. A **Step Catalog** table (the dedup ledger) — every distinct step, its keyword, and the TC-IDs it covers. This is the handoff to `gherkin-step-code`:

```
| Step text (canonical)                                 | Keyword | Params        | Covers TC-IDs        |
|-------------------------------------------------------|---------|---------------|----------------------|
| I am on the login page                                | Given   | —             | Background           |
| I sign in as a registered customer                    | When    | —             | TC-LOGIN-001         |
| I sign in with email {string} and password {string}   | When    | email, pwd    | TC-LOGIN-002/003     |
| I see the error {string}                              | Then    | message       | TC-LOGIN-002/003     |
```

3. A **Cleanup handoff** note: the suite's Cleanup block verbatim, flagged for the binding skill to implement as an `After`/`@AfterScenario` hook (never as Gherkin steps).

4. A **Traceability** line: every TC-ID and AC accounted for, gaps marked ⚠️.

## Procedure

1. Read the test-case suite. Map the Coverage Summary so every AC and TC-ID has a home.
2. Group cases into features (by `TC-<FEATURE>-` prefix unless told otherwise).
3. For each feature, identify the shared precondition(s) → `Background`.
4. For each case: choose Scenario vs Scenario-Outline (decision #4), write declarative steps (#2), and reuse/parameterize against the running Step Catalog (#5).
5. Apply tags (#6) from Priority/Type/AC.
6. Emit `.feature` files, the Step Catalog, the Cleanup handoff, and the Traceability line.
7. Validate the Gherkin parses (the scaffold/binding skill runs the real parser; here, check structure: one `Feature`, valid keyword order, every `Scenario Outline` has matching `<placeholders>` and `Examples` columns).

## Anti-patterns to flag

- Imperative UI steps (`click`, `type`, CSS selectors) in `.feature` files — push into step definitions/page objects.
- A `Background` step that doesn't apply to every scenario in the feature.
- Near-duplicate steps differing only by a literal — parameterize instead.
- A `Scenario Outline` whose rows assert *different* behaviors — split into named scenarios.
- Conjunction steps (`When I X and Y`).
- Mixed valid/invalid rows in one `Examples` table.
- Assertions or test data in a `Background`.
- Cleanup expressed as Gherkin steps — it belongs in an `After` hook.
- Lost traceability — a scenario with no `@AC-<n>` when the suite mapped one.

## Handoffs

- Step definitions / glue + POM wiring → `qa/{stack}/skills/gherkin-step-code`.
- Project wiring (packages, runner, features dir) → `qa/{stack}/skills/bdd-project-setup`.
- Reviewing existing `.feature` files → `qa/{stack}/skills/bdd-reviewer`.
- Deep Gherkin style reference → `references/gherkin-style-guide.md`.
- Source test cases → `qa/manual/test-case-writer` (run `qa-test-case-designer` first if none exist).
