# Gherkin Style Guide (canonical Cucumber community guidance)

Deep reference for `feature-file-writer`. Distilled from the Cucumber.io "Writing better Gherkin" / BDD guidance and the Gherkin reference. Use it to settle phrasing and structure disputes.

## The one rule everything derives from

**Describe behavior, not implementation.** A scenario is a specification and a piece of living documentation, read by non-programmers. If a step would have to change when the *implementation* changes (but the *behavior* doesn't), it is at the wrong altitude.

## Declarative vs imperative

| Imperative (avoid) | Declarative (prefer) |
|---|---|
| `Given I visit "/login"` | `Given I am on the login page` |
| `When I fill "#email" with "a@b.com"` | `When I sign in as a registered customer` |
| `And I fill "#pwd" with "x"` | |
| `And I press "#submit"` | |

Imperative scenarios are verbose, brittle, and duplicate UI mechanics across every scenario. Declarative scenarios read as behavior and keep the mechanics in *one* step definition. Exception: when the **mechanic itself is what's under test** (e.g. a validation that fires on blur), a more concrete step is legitimate — but that is the minority.

## Keyword discipline

- `Given` — context / preconditions (past or present state). No actions that are the point of the test.
- `When` — the single event/action under test. Ideally **one** `When` per scenario.
- `Then` — an observable, verifiable outcome. No internal-state checks the user can't see.
- `And` / `But` — continuations of the previous keyword. Keep to a minimum.
- `*` — bullet form for a list of same-kind steps; reads better than stacking `And`.

A scenario that needs several `When`s usually hides multiple behaviors — split it.

## Background

- Use only for `Given`s that **every** scenario in the feature needs.
- Keep it short (a line or two). A long Background means the feature is doing too much — split the feature.
- Never put `When`/`Then` in a Background. Never put data setup that only some scenarios need.
- If readers must scroll up to understand a scenario, the Background is hurting more than helping.

## Scenario Outline + Examples

- Use for the **same behavior** exercised over multiple data sets (equivalence partitions, boundary values, pricing tiers).
- Placeholders `<name>` in steps bind to `Examples:` columns.
- One behavior per Outline. If a row's *expected outcome differs in kind* (success vs blocked-as-fraud), it is a different behavior → a separate named `Scenario`.
- Split valid and invalid data into separate `Examples` blocks; tag the invalid block `@negative`. This keeps each table a single equivalence intent.
- Name the outline for the behavior, not the data: `Scenario Outline: Discount is applied by tier`, not `Scenario Outline: test discounts`.

## Tags

- Tags filter and group scenarios and feed reporting/living docs.
- Feature-level tags are **inherited** by all scenarios, outlines, and examples below them.
- Conventions used by this library: `@p1/@p2/@p3` (priority), `@smoke`/`@regression` (tier), `@negative`/`@boundary`/`@edge` (type), `@AC-<n>` (acceptance-criterion traceability), `@web`/`@mobile` (platform).
- Allure adapters map `@allure.label.<key>:<value>` tags to report labels — the binding/reporting skills own that; keep semantic tags here.

## Reusable, parameterized steps

- One canonical verb per concept. Agree it once and never synonym-drift (`sign in` ≠ "log in" ≠ "authenticate" — pick one).
- Parameterize literals so one step definition serves many concrete steps. Quote strings, leave numbers bare, so they map to Cucumber-Expression `{string}` / `{int}` downstream.
- Prefer domain/ubiquitous language over implementation identifiers (`the premium plan`, not `plan_id=3`).
- Keep steps composable and small; a good step catalog has far fewer steps than scenarios.

## Conjunction steps (anti-pattern)

`When I log in and go to the dashboard` couples two actions. Split:

```
When I sign in as a registered customer
Then I land on the dashboard
```

If you find yourself writing `And` inside a single logical action, it's a conjunction step.

## Scenario hygiene checklist

- [ ] Title states a behavior, readable by a business stakeholder.
- [ ] Exactly one event under test (one `When`).
- [ ] Steps are declarative — no selectors, URLs, or UI verbs unless the mechanic is the subject.
- [ ] No conjunction steps.
- [ ] Shared-by-all preconditions are in `Background`; partial ones are not.
- [ ] Data-driven variants use `Scenario Outline` + `Examples`, one behavior per outline.
- [ ] Steps reuse the catalog; new steps are parameterized, not near-duplicates.
- [ ] Tags carry priority, tier, type, and AC traceability.
- [ ] The feature reads top-to-bottom as documentation without needing the code.

## Sources

- Cucumber.io — Writing better Gherkin: https://cucumber.io/docs/bdd/better-gherkin/
- Cucumber.io — Gherkin reference: https://cucumber.io/docs/gherkin/reference/
- Cucumber.io — BDD / example mapping: https://cucumber.io/docs/bdd/
