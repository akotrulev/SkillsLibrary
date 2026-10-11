---
name: test-design-techniques
description: Use when deriving test cases systematically from a specification using formal black-box test design techniques. Triggers: "what technique applies here", "derive partitions and boundaries", "build a decision table for these rules". Not for formatting the suite (test-case-writer) or choosing what to test by risk (test-strategy).
---

# QA — Test Design Techniques (ISTQB)

A reference for **deriving test cases systematically** instead of by intuition. Grounded in the ISTQB Certified Tester Foundation Level (CTFL v4.0) and Advanced Level syllabi. Use it to pick the right technique for the shape of a requirement, apply it correctly, and measure when you've covered enough.

This skill answers *which technique and how many cases*. It does **not** format the final cases — that's `qa/manual/test-case-writer`. It does **not** size a release — that's `qa/manual/test-strategy`.

## The derivation chain (ISTQB vocabulary)

Every technique walks the same chain. Keep the words straight — they map onto coverage:

```
Test basis  →  Test conditions  →  Coverage items  →  Test cases  →  Test data
(the spec)     (what to test)      (what to cover)     (the script)   (the values)
```

- **Test basis** — the documentation you test against: requirements, user stories + ACs, API contracts, state diagrams, business rules, regulations.
- **Test condition** — a testable aspect of the basis ("discount applies over €100", "account locks after 5 failures").
- **Coverage item** — the atomic thing a technique says must be exercised (one equivalence partition, one boundary value, one decision-table rule, one state transition).
- **Test case** — preconditions + steps + input + expected result that exercises one or more coverage items.
- **Coverage** = `exercised coverage items / total coverage items × 100%`. This is your stopping criterion, not a feeling.

A technique is just a disciplined way to enumerate coverage items so you can both *generate* cases and *measure* when to stop.

## Three families

| Family | Based on | Techniques here | Use when |
|---|---|---|---|
| **Black-box** (specification-based) | The spec / external behavior | EP, BVA, decision tables, state transition, use-case, pairwise, classification tree | Default for manual test design from documentation |
| **White-box** (structure-based) | The code structure | statement / branch / path coverage | You can see the code; usually automated/unit level |
| **Experience-based** | Tester knowledge & intuition | error guessing, checklists, exploratory | Gaps the formal techniques miss; complements them |

Manual test-case design from documentation is overwhelmingly **black-box + experience-based**. This skill goes deep on those.

---

## 1. Equivalence Partitioning (EP)

**Idea.** Divide each input (and output) domain into partitions where every member is processed the same way. If one value in a partition reveals a defect, the others would too — so **one value per partition is sufficient**.

**Always partition into valid and invalid classes.**

- **Valid partitions** — accepted values (each exercised; several valid partitions may be combined in one case).
- **Invalid partitions** — rejected values. **Exercise one invalid partition per test case** so the failure is unambiguous (combining two invalid inputs can mask which one was caught).

**Coverage** = partitions exercised / total partitions. 100% EP coverage = at least one value from every valid *and* invalid partition.

**Worked example — age field, accepts 18–65 inclusive:**

| Partition | Class | Representative |
|---|---|---|
| age < 18 | invalid | `17` |
| 18 ≤ age ≤ 65 | valid | `34` |
| age > 65 | invalid | `70` |
| non-numeric | invalid | `"abc"` |
| empty | invalid | `""` |

→ 5 partitions → 5 cases (1 happy, 4 negative, each isolating one invalid class).

**Pitfalls.** Don't forget *output* partitions (e.g. "discount = 0% / 5% / 10%" are output classes worth a case each). Don't combine two invalid inputs in one negative case. Partition the *whole* domain — invalid classes are where most requirements are silent.

---

## 2. Boundary Value Analysis (BVA)

**Idea.** Defects cluster at the edges of partitions. BVA tests the boundaries of **ordered** equivalence partitions. Always layer BVA *on top of* EP — it refines the ordered partitions; EP still covers the unordered ones (e.g. "non-numeric").

A **boundary value** is the minimum or maximum of a partition. There are two strengths:

### 2-value BVA (ISTQB Foundation default)
For each boundary: the **boundary value** and its **nearest neighbour in the adjacent partition** (two coverage items per boundary).

### 3-value BVA (stronger)
For each boundary: the **boundary** and **both neighbours** (three coverage items per boundary).

**Why 3-value catches more.** If `if (x <= 10)` is mis-coded as `if (x == 10)`, the 2-value set `{10, 11}` passes both (10 → true correctly, 11 → false correctly) and misses the bug. The extra 3-value point `x = 9` (should be true, mis-code gives false) **catches it**. Use 3-value for high-risk numeric logic; 2-value otherwise.

**Worked example — "free shipping for orders ≥ €100", valid range €0–€1000:**

Boundaries: `0`, `100` (the rule edge), `1000`.

| Boundary | 2-value items | extra 3-value item |
|---|---|---|
| min `0` | `-0.01`, `0` | `0.01` |
| rule `100` | `99.99`, `100` | `100.01` |
| max `1000` | `1000`, `1000.01` | `999.99` |

Pick the increment from the data type/precision: `1` for integers, `0.01` for euro amounts, `1 day` for dates. The neighbour must be the *smallest representable* step, or you're not testing the boundary.

**Pitfalls.** BVA only applies to **ordered** partitions (numbers, dates, ordered enums, string length, collection size). "Valid email vs invalid email" has no boundary — that's EP only. The boundary of the *rule* (`100`) matters as much as the boundary of the *field* (`0`, `1000`). Watch closed vs open intervals: `≥ 100` and `> 100` move the boundary by one increment.

---

## 3. Decision Table Testing

**Idea.** When the output depends on a **combination of conditions** (business rules), a decision table enumerates every combination so none is missed. This is the technique for "if A and B but not C, then…" requirements.

**Structure.** Rows = conditions (inputs) and actions (outputs). Columns = **rules** (one combination). For N independent boolean conditions there are 2^N columns before simplification.

**Coverage** = rules exercised / total rules. Minimum sensible coverage = **one test case per rule (column)**.

**Worked example — loan approval:**

Conditions: `Credit score ≥ 700?`, `Income verified?`, `Existing customer?` → action: `Approve?`, `Rate`.

| Condition / Rule | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 |
|---|---|---|---|---|---|---|---|---|
| Credit ≥ 700 | T | T | T | T | F | F | F | F |
| Income verified | T | T | F | F | T | T | F | F |
| Existing customer | T | F | T | F | T | F | T | F |
| **Approve** | Y | Y | N | N | Y | N | N | N |
| **Rate** | 4% | 5% | – | – | 6% | – | – | – |

→ 8 rules → 8 candidate cases.

**Collapsing with "don't care" (—).** When a condition doesn't affect the action, merge columns and mark it `—`. E.g. if credit < 700 always rejects regardless of the other two, R5–R8 collapse to one rule (`Credit = F, *, * → Reject`), cutting 8 rules to 5. Collapse only when the action is genuinely independent — document why. Pair decision-table cases with **BVA on the numeric conditions** (test credit = 699/700) since the table only captures the boolean, not the boundary.

**Pitfalls.** Watch the column count explode (2^N) — collapse aggressively, or switch to **pairwise** if conditions are independent multi-valued parameters. Flag impossible/contradictory rule combinations rather than writing unreachable cases.

---

## 4. State Transition Testing

**Idea.** When the object has **states** and behavior depends on **history** (the same input does different things in different states), model it as a state machine and cover the transitions. The technique also surfaces **invalid transitions** — inputs that should be rejected in a given state.

**Model.** A state diagram or **state table** (rows = states, columns = events, cells = resulting state / "—" for invalid). The state table is the better tool because it forces you to consider *every event in every state*, exposing the invalid ones.

**Coverage levels (n-switch):**

| Level | Covers | Catches |
|---|---|---|
| **0-switch** (all transitions / "1-switch" in some texts) | every single valid transition once | wrong/ missing single transitions |
| **1-switch** | every valid **pair** of consecutive transitions | bugs needing two steps of history |
| **N-switch** | every sequence of N+1 transitions | deep history bugs (rare, expensive) |
| **All-states** (weakest) | every state visited | dead states; misses transition logic |
| **Invalid transitions** | every illegal event/state cell rejected | "can I skip payment?" security/logic holes |

Default target: **0-switch (all valid transitions) + all invalid transitions rejected.** Go to 1-switch for high-risk workflows (checkout, approvals, payments).

**Worked example — order: `Draft → Submitted → Paid → Shipped`; `Submitted → Cancelled`:**

State table (cell = resulting state, `—` = invalid):

| State \ Event | submit | pay | ship | cancel |
|---|---|---|---|---|
| Draft | Submitted | — | — | — |
| Submitted | — | Paid | — | Cancelled |
| Paid | — | — | Shipped | — |
| Shipped | — | — | — | — |
| Cancelled | — | — | — | — |

- 0-switch valid transitions → 5 positive cases (submit, pay, ship, cancel-from-submitted… one per non-`—` cell).
- Invalid transitions → one negative case per `—` cell you care about (e.g. "pay a Draft order → rejected", "ship an unpaid order → rejected", "cancel a Shipped order → rejected").
- 1-switch example pair: `Draft --submit--> Submitted --pay--> Paid` as a single chained case.

**Pitfalls.** The `—` cells are where the real bugs live (skip-payment, double-ship). Don't model only the happy path arrows. Identify the **guard conditions** on transitions (e.g. "pay only if amount > 0") and BVA them.

---

## 5. Use-Case Testing

**Idea.** Derive cases from **use cases / user stories** by walking each flow end-to-end. One case per flow.

- **Basic (main success) flow** → 1 positive case.
- **Alternate flows** → 1 case each (valid variations: "pay with saved card" vs "new card").
- **Exception flows** → 1 case each (error handling: "card declined", "session expired mid-checkout").

Use-case testing exercises the **integration of steps** the way a user strings them together — it complements EP/BVA (which test fields in isolation) and decision tables (which test rule combinations). Map each flow to its preconditions and postconditions; postconditions become your expected results *and* drive cleanup.

**Pitfalls.** Don't stop at the basic flow — the alternate and exception flows are where coverage is usually thin. Each flow's **postcondition** tells you what state to assert and what to tear down.

---

## 6. Pairwise / Combinatorial Testing

**Idea.** When several independent parameters each have several values, testing all combinations explodes (5 browsers × 4 OS × 3 locales × 2 roles = 120). **Pairwise (all-pairs)** testing covers every *pair* of values at least once — empirically catching the large majority of combinatorial defects with a fraction of the cases (often ~15–20 instead of 120).

**When to use.** Configuration matrices, feature-flag combinations, form fields that are independent. **Not** for conditions with real interdependencies — those want a decision table.

**How.** List parameters and their values, then generate a covering array (PICT, ACTS, or `allpairspy`/`pairwise` libraries; by hand for ≤3 parameters). State explicitly that it's pairwise, not exhaustive — and pin any combination that's high-risk as a *forced* row in the array.

**Classification of strength:** each-choice (every value once, weakest) < pairwise (every pair) < t-wise (every t-tuple) < exhaustive. Pairwise is the usual sweet spot.

---

## 7. Classification Tree

**Idea.** A visual structuring of equivalence partitioning. Break the test object into **classifications** (aspects to vary), each with **classes** (the partitions), then compose test cases by picking one class per classification. It's EP + a combination strategy (often pairwise) made explicit and reviewable.

Use it to *organize* a complex EP/pairwise problem so stakeholders can see what's covered — especially when there are many dimensions. The leaves are your partitions; the combination rule (one-per-class, pairwise, or full) decides the case count.

---

## 8. Error Guessing & Experience-Based

**Idea.** Formal techniques cover what the spec *says*. Experience-based techniques cover what it *doesn't* — the gaps, the "developers always get this wrong here" hunches.

- **Error guessing** — enumerate likely mistakes and target them: empty/null, zero, negative, max+1, very long strings, duplicate submit, double-click, back-button, concurrent edit, special characters, unicode/emoji, leading/trailing whitespace, copy-paste with hidden chars, timezone/DST, leap day, end-of-month, rounding, off-by-one.
- **Checklists / fault attacks** — reusable defect taxonomies (e.g. input validation, auth, money, time) applied as a sweep.
- **Exploratory** — unscripted, but charter it via `qa/manual/exploratory-charter-writer`.

Experience-based cases are a **complement**, never a replacement, for the systematic ones. Tag them so reviewers know they're not traceable to a specific AC.

---

## Technique selection matrix

Pick by the **shape of the requirement**, then combine:

| The requirement looks like… | Primary technique | Combine with |
|---|---|---|
| A field with a range / set of accepted values | **Equivalence partitioning** | BVA on the ordered partitions |
| A numeric / date / length threshold | **Boundary value analysis** | EP for the unordered classes |
| "If A and B but not C then X" — rules combining conditions | **Decision table** | BVA on each numeric condition |
| An object with states; same action behaves differently by state | **State transition** | BVA on guard conditions; decision table for complex guards |
| A user journey with main / alternate / error flows | **Use-case testing** | EP+BVA on each step's fields |
| Many independent parameters, can't test all combos | **Pairwise** | Force high-risk rows; classification tree to visualize |
| Many dimensions needing a clear coverage picture | **Classification tree** | Pairwise as the combination rule |
| "What did we miss" / known-fragile areas | **Error guessing** | Always layer on top of the systematic set |

**Default recipe for a feature from documentation:** EP → BVA → decision table for the rule combos → state transition for any workflow → use-case for end-to-end flows → error-guessing sweep → (pairwise only if a config matrix appears). The `qa-test-case-designer` agent runs exactly this order.

## Combining techniques (the part people skip)

Real features need **layered** techniques, not one:

- A checkout form has **fields** (EP+BVA), **business rules** (decision table: free shipping × member × coupon), a **workflow** (state transition: cart → address → pay → confirm), and **journeys** (use-case: guest vs returning). Each layer contributes cases; together they're the suite.
- Decision tables capture *whether* a rule fires; BVA captures *where* its numeric boundary sits. You need both — a table with `amount ≥ 100 = T/F` still needs `99/100/101` from BVA.
- State transition tells you the *legal* paths; error guessing probes the *illegal* ones the `—` cells imply.

## Stopping criteria — how many cases is enough

Stop when the **coverage target per technique** is met, not when you're tired:

| Technique | Minimum coverage to claim "done" |
|---|---|
| Equivalence partitioning | every valid + every invalid partition exercised |
| Boundary value analysis | every boundary (2-value, or 3-value for high-risk) |
| Decision table | every reachable rule (after collapsing) |
| State transition | all valid transitions (0-switch) + all invalid transitions rejected |
| Use-case | basic + every alternate + every exception flow |
| Pairwise | every pair of parameter values |

State the achieved coverage explicitly in the deliverable (e.g. "BVA 3-value on the discount threshold; decision table 5/5 rules after collapsing R5–R8"). Coverage you can't name, you didn't measure.

## Rules

- Walk the chain: test basis → conditions → coverage items → cases. Don't jump straight to cases.
- EP and BVA travel together — partition first, then push every ordered partition to its edges.
- One invalid partition per negative case (isolate the failure).
- Decision tables for combinations; collapse with "don't care" and document why.
- State tables (not just diagrams) — the empty cells are the bug farm.
- Name the technique and the coverage level on every case or group ("TC-07–11: state transition, 0-switch").
- Experience-based cases are additive and tagged, never a substitute for the systematic set.
- The number of cases is an *output* of the coverage targets, not a guess up front.

## What NOT to do

- No "I wrote 20 cases" without saying which techniques and what coverage.
- No combining two invalid inputs in one negative case.
- No BVA on unordered partitions (there's no boundary on "valid vs invalid email").
- No decision table left at 2^N when half the rules collapse — and no collapsing without stating the independence assumption.
- No state model that only draws the happy-path arrows.
- No pairwise where conditions actually interact (use a decision table) and no decision table where parameters are independent (use pairwise).
- No skipping the boundary of the *rule* because you tested the boundary of the *field*.

## Handoffs

- Distill the source docs into the test-basis these techniques run against → `qa/manual/requirements-breakdown`
- Format the derived cases into a suite with shared setup + cleanup → `qa/manual/test-case-writer`
- Orchestrate the whole doc → suite flow → `qa/manual/agents/qa-test-case-designer`
- Size the test investment by risk first → `qa/manual/test-strategy`
- Unscripted probing of the gaps these techniques leave → `qa/manual/exploratory-charter-writer`
- Automate the resulting cases → `qa/<stack>/skills/api-test-author/...` / `qa/<stack>/skills/ui-test-author/...`
