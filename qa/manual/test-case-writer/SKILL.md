---
name: test-case-writer
description: Use when writing formal test cases from requirements, stories, ACs or specs; end-to-end journeys and business rules first. Triggers "write test cases for X". Not for a test plan (test-plan-writer).
---

# QA Test Case Writer

A suite exists to show that **the business works**: that a person gets what they came for, from the first screen to the last consequence, and that every rule and every figure on the way is right. Checking that a field rejects a bad email is part of that, and the smallest part. This skill writes suites in that order of importance: **end-to-end journeys, then business rules and calculations, then states and permissions, then the feature's connections, and field validation last.**

The output is implementation-agnostic Markdown: a manual script, a test-management import, and the specification automation is later written from. The skill **assembles and formats**: it takes the **coverage-item list** that `qa/manual/test-design-techniques` (and `cross-feature-test-design`) derived from a `qa/manual/requirements-breakdown` basis, groups it, factors shared preconditions into one **Setup**, writes the cases and closes with a **Cleanup**. Run standalone on a raw story, it runs those skills first (*Standalone fallback*). The whole flow is orchestrated by the `qa-test-case-designer` agent.

## When to use

- A requirement, story, AC set or spec needs test cases
- A feature needs its end-to-end journeys and business rules written down as executable cases
- An exploration report (`qa/manual/app-exploration`, or a human's session report) lists **test-case candidates**: they go through `requirements-breakdown` first, and their cases carry `#observed <finding id>` as `Source`

## When NOT to use

- A feature **test plan** (scope, harness, a scenario-level inventory with no steps) → `qa/manual/test-plan-writer`
- An exploratory charter → `qa/manual/exploratory-charter-writer`; exploring a live app → `qa/manual/app-exploration`
- Automation code → `qa/<stack>/skills/ui-test-author`, `api-test-author`
- A defect to report → `qa/manual/bug-report-writer`

## Inputs needed

Ask only what is missing:

1. **The coverage-item list and its basis document.** With only a raw story, see *Standalone fallback*.
2. **Coverage depth**: full by default. "Happy path only" still means every journey's main path and every rule, never the fields alone.
3. **Where the suite goes**: default `docs/test-cases/<NNN>-<feature-slug>.md` (`NNN` = next free number), the basis beside it as `<NNN>-<feature-slug>-basis.md`. A project's existing location wins.

Gherkin is not an output here (`qa/_shared/bdd/feature-file-writer` owns it). A test-management import is the same table as CSV, same columns, same order.

## What a suite is made of — business first

Cases are grouped under these headings, **written in this order**, each heading present only when it has cases:

| # | Group (layer) | Its cases prove | How much |
|---|---|---|---|
| 1 | **Journeys** (`journey`) | A person reaches a goal end to end: from where they really start to the last thing the business cares about, across every screen, feature and actor on the way | Every actor goal in the basis; the main paths are P1 |
| 2 | **Rules and calculations** (`rule`) | Each business decision gives the intended outcome; each figure is the right figure | One case per rule, and per branch of each formula, with worked numbers |
| 3 | **States and permissions** (`state`) | What may happen to a thing in each state, and who may do it | Each transition, each refused one, each role |
| 4 | **Data · Interactions · Temporal · Concurrency** | What the feature sets off elsewhere and shares with others (the basis's §8) | As `cross-feature-test-design` derived |
| 5 | **Field validation** (`field`) | Each input accepts what is valid and refuses what is not | Written last, parameterized, **at most a third of the suite** |

An error-guessing case sits in the group whose behaviour it probes.

## Procedure

1. **Sort the coverage items into the five groups.** One case per item, or per group of *valid* items that safely share a run; **never two invalid inputs in one case**. Each case keeps its technique, its source line and, for a cross-feature item, its slice id.
2. **Write the journeys** (*Case forms*): one per actor goal, then the alternate and exception paths that end in a different business outcome.
3. **Write the rules and calculations.** Compute every expected figure from the basis's formula and put the working in `### Worked numbers`.
4. **Write states and permissions, then the connection groups.**
5. **Write field validation last**, one parameterized case per field per direction.
6. **Factor shared preconditions into one Setup**: environment, seeded data, accounts, flags, named budgets. A case's `Preconditions` hold only its *delta*. State that must be *re-established* (a counter reset) is the case's first step: a precondition describes state, it does not act.
7. **Write the Cleanup** that restores the starting state, or says "No residual state — nothing to clean".
8. **IDs** `TC-<FEATURE>-<NNN>`, never renumbered.
9. **Tag each case.** **Priority**: **P1** = the main path of every journey, every rule or figure that moves money, an entitlement or irreversible data, and the basis's top-risk conditions; P1 is the regression floor and what gets automated first · **P2** = every other in-scope condition · **P3** = error guessing and `#assumption` cases awaiting confirmation. A field-format case is P1 only when something of value depends on it. **Type**: `positive` (the system accepts) or `negative` (it refuses). **Technique** with its coverage level. **Source**: the basis line (`J-1`, `BR-2`, `C-1`, `V-3`, `AC2`), a plan row (`TP-012`), or `#observed <evidence>` / `#assumption`.
10. **Run the balance check**, fix what it finds, then emit the suite and the coverage summary.

### Standalone fallback — no coverage-item list yet

Load `qa/manual/requirements-breakdown` and write the basis first (its journeys, rules and calculations are what this skill needs most), then `qa/manual/test-design-techniques` and walk its default recipe to the coverage-item list, then the procedure above. Never go from the story straight to cases.

### Case forms

- **Journey.** One actor, **one goal**, from the real starting point (not a deep link into the middle) to the last consequence: often on another screen, for another actor, or later in time (the invoice, the stock count, the staff queue, the month-end charge). Steps read `action → checkpoint`, a checkpoint on every step the next one depends on; the Expected Result is the business outcome in every place it shows. Up to about 15 steps; more means two goals, so split and chain ("starts where `TC-…-003` ends"). A named persona and real numbers. Per goal write: the main path; each alternate path with a *different business outcome*; each exception the business must survive (a declined payment then a retry, a seat taken between viewing and booking); each hand-off between actors; and, where rules accumulate over time, the long journey (a month of activity, then the closing job). The main path repeated with one more invalid field is not a journey: it is a field case.
- **Calculation.** The Expected Result is a number computed from the basis's formula, never "the total is correct". One case per branch of the formula (covered, partly covered, not covered; each cap, floor, tier and override; zero), the boundary of each threshold, and one **accumulation** case where a second operation starts from the first one's result. A formula's branches may share one parameterized case, `inputs → expected`. Assert the figure where the business reads it (the balance, the invoice), not only where it was computed. Rounding or an order of operations the basis does not state is an open question, never a guess.
- **Rule.** One case per decision-table rule, titled in the business's words ("A cancellation with 24 hours' notice returns the credits"). Assert the outcome **and** the absence of the other one.
- **Permission.** A role × action matrix as one parameterized case, `role → allowed / refused`. A refusal is asserted on the surface and by showing that nothing changed.
- **Parameterized field case.** All coverage items for one field in one direction: rows `value → expected`, one invalid value per row. A CSV export writes one line per row.
- **Async effect.** `within <BUDGET>, <observable>`, polled. The budget is one named value declared in Setup (from the NFR, else `#assumption`). Never a fixed wait.
- **Temporal.** Setup or Preconditions name the *Environment needs*: run `<schedule>` on demand, or set the clock to `<instant>` in `<timezone>`. A case the environment cannot support is still written; the need goes in the hand-off notes.
- **Concurrency.** Two actors at the same instant, one expected outcome. Where the spec does not decide it, the expected result is `open question: <the question>` and the case is P1; never "A or B".

## The expected result is the business effect, not the message

"Booking confirmed" is what the screen says. The effect is what is now true, and a suite that asserts only messages passes while the business is broken.

| Weak: the message | Strong: the effect |
|---|---|
| "Booking confirmed" is shown | The booking is under *My bookings* as Confirmed; *My balance* shows credits used 6 → 8 and £6.00 accrued; the session shows 5 of 6 seats taken |
| "Code applied" | The total drops from €80.00 to €68.00 (15 % of €80.00 = €12.00); the confirmation and the invoice both show €68.00 |
| "You cannot do that" | `403`, and the booking is still Confirmed when its owner opens it |

Every clause is **observable** (text, a figure, a status, a record on a screen or in a response), **specific** (one value, never "works correctly") and stated **where the business sees it**. A refusal also asserts that nothing changed. When a flow asserts at several points, attach each check to its step.

## Output format

```markdown
## Test Cases: <Feature name>

**Source**: <story / requirement id> — basis `docs/test-cases/<NNN>-<slug>-basis.md`
**Coverage**: <full / happy path / regression>
**Techniques applied**: <use-case (main + 2 alternate + 1 exception), decision table 3/3, BVA 3-value on the credit threshold, …>
**Balance**: journeys 3 · rules and calculations 5 · states and permissions 3 · connections 1 · field 1 (8 %)
**Generated**: <date>

### Setup (shared preconditions — run once before the suite)
- **Environment**: staging, build `<sha>`, feature flags `<flag=value>`; `ASYNC_BUDGET = 10 s` `#assumption`
- **Data seeded**: plan Basic (8 credits, £6.00 per overage credit); member Ana on Basic, credits used 6; session *Sculpture masterclass* (Masterclass, 3 credits, 4 of 6 seats taken)
- **Environment needs**: run the monthly posting on demand

### Cases

#### Journeys

| ID | Title | Priority | Type | Technique | Source | Preconditions (delta from Setup) | Steps | Expected Result | Test Data |
|----|-------|----------|------|-----------|--------|----------------------------------|-------|-----------------|-----------|
| TC-BOOK-002 | A member who books beyond her credits is charged the overage once, at month end | P1 | positive | use-case (alternate) | J-2, BR-3, C-3 | — | 1. Ana opens the session list and books *Sculpture masterclass* → Confirmed, under *My bookings*<br>2. She opens *My balance* → within `ASYNC_BUDGET`: credits used 8, £6.00 accrued<br>3. Run the monthly posting<br>4. She opens *My balance* and her account | One charge of £6.00 on Ana's account; credits used 0; no accrual left. The session shows 5 of 6 seats taken | Ana; see Worked numbers |

#### Rules and calculations
#### States and permissions
#### Field validation

### Worked numbers
| Case | Inputs | Working | Expected |
|---|---|---|---|
| TC-BOOK-002 | credits 8, used 6, cost 3, rate £6.00 | remaining 8 − 6 = 2; spent 2; overage 3 − 2 = 1; 1 × £6.00 | £6.00 accrued, used 8 |

### Cleanup (always runs — restore starting state)
- Cancel the bookings the run created; remove accrued and posted charges; set credits used back to 6
```

### Coverage summary

```markdown
## Coverage Summary

| Basis line | Test Cases | Covered? |
|---|---|---|
| J-2: a member books beyond her credits and pays at month end | TC-BOOK-002 | ✅ |
| BR-3 / C-3: overage = shortfall × rate | TC-BOOK-002, TC-BOOK-005, TC-BOOK-006 | ✅ |
```

Journeys first, then rules and calculations, then the rest. A line with no case is ⚠️ with the reason.

## The balance check

Run before emitting; fix every row that fails.

| Check | Fails as |
|---|---|
| Every actor goal in the basis has a journey case, or the suite says "single action, no journey" and why | blocker |
| Every rule and every calculation has a case asserting its business effect; a calculation has worked numbers for each branch | major |
| Field validation is at most a third of the cases | major: merge into parameterized cases; if still over, the business groups are thin |
| Every P1 case asserts a business effect, not only a message | major |
| Every figure in an Expected Result appears in Worked numbers, recomputed | major |

## Writing the case text well

- **Intent, not selectors.** "Open the login page", not "click the hamburger, then Account". Pin a selector, path or shortcut only where that mechanic is the thing under test.
- **One goal per case.** A rule, state or field case verifies one behaviour in about 3–8 steps. A journey is longer and still has one goal. The anti-pattern is several goals in one case, or a long case with no checkpoints.
- **Concrete data.** `jordan@test.com`, `€80.00`, `15 Mar 10:00`; never "a valid email" or "some amount".
- **One name per thing**, and the product's real labels: not "Sign in" here and "Log in" there.
- **Self-review.** Reread each case as a tester new to the feature and strip *valid, appropriate, correctly, as expected, etc.*: each hides a value or an assertion not written down.

## Quality bar

- [ ] The **suite**: groups in the business-first order; the **Balance** line in the header and the balance check passed; one Setup, one Cleanup (or "nothing to clean"); the techniques applied and the basis named; saved at `docs/test-cases/<NNN>-<slug>.md` or the project's convention
- [ ] Every **case**: a title stating the behaviour and its outcome in the business's words; one goal; steps at intent altitude, a journey with its checkpoints; an expected result that is the business effect, one value; concrete data and realistic invalid input (`password: "''"`, not `<invalid>`); Technique, Priority, Type and Source filled; only delta preconditions (`—` if none)

## Example

A full worked suite, thirteen cases for "a member books a session" (three journeys, five rule and calculation cases with worked numbers, one field case), is in [`references/example-book-session.md`](references/example-book-session.md).

## Anti-example

Asked for test cases for booking a session, with the story and `POST /bookings`.

Bad: eleven cases. Session id missing, malformed, unknown, negative, very long, SQL in the id, an expired token, a double click, the happy path. Every AC is "covered", and no case shows what a booking costs, what happens at zero credits, or that the member is charged once at month end. The form validates; nobody knows whether the business works.

Good: the example above. If the basis has no journeys, rules or formulas to write from, that is the finding: run `requirements-breakdown`, or ask.

## Handoffs

- The basis (journeys, rules, calculations, data dictionary) → `qa/manual/requirements-breakdown`
- Which cases to write, and how many → `qa/manual/test-design-techniques`; for the feature's connections → `qa/manual/cross-feature-test-design`
- The whole documentation → suite flow → the `qa-test-case-designer` agent; an e2e-only suite from a code trace → `qa-feature-spec-writer`
- A basis from a live app → the `qa-explorer` agent; a defect found on the way → `qa/manual/bug-report-writer`
- Gherkin → `qa/_shared/bdd/feature-file-writer` (the `qa-bdd-<stack>` agent); automation → `qa-api-<stack>` / `qa-ui-<stack>` / `qa-mobile-<stack>`
