---
name: test-design-techniques
description: Use when deriving test cases by technique (journeys, decision tables, calculations, states, boundaries, partitions). Triggers "what technique applies here". Not for writing cases (test-case-writer).
---

# QA — Test Design Techniques (ISTQB)

How to **derive test cases systematically** instead of by intuition, grounded in the ISTQB Foundation (CTFL v4.0) and Advanced Test Analyst syllabi. It answers *which technique, and how many cases*. It does not format cases (`qa/manual/test-case-writer`) and does not size a release (`qa/manual/test-strategy`).

**The order is business first.** A feature is tested from what a person comes to get done, through what the business decides and calculates, down to what each field accepts. The techniques below are numbered in that order, and the default recipe walks them in it: field techniques run last and get the smallest share, because that is where the least value is lost when they are thin.

## The derivation chain

```
Test basis  →  Test conditions  →  Coverage items  →  Test cases  →  Test data
(the spec)     (what to test)      (what to cover)     (the script)   (the values)
```

A **coverage item** is the atomic thing a technique says must be exercised: one flow, one decision-table rule, one formula branch, one transition, one boundary value, one partition. **Coverage** = exercised items ÷ total items, and it is the stopping criterion. A technique enumerates coverage items, so cases can be generated *and* counted.

## The default recipe

| # | Ask of the basis | Technique | Layer |
|---|---|---|---|
| 1 | What does a person come here to get done? | Use-case and end-to-end journey testing (§1) | journey |
| 2 | What does the business decide? | Decision table (§2) | rule |
| 3 | What does it calculate? | Calculation testing (§3) | rule |
| 4 | What states can the thing be in, and who may act on it? | State transition, role × action table (§4) | state |
| 5 | Where do the rules' thresholds sit? | BVA on each **rule** boundary (§6) | rule |
| 6 | What does each input accept? | EP, then BVA on each field (§5, §6) | field |
| 7 | Are there many independent options? | Pairwise (§7), only when a matrix appears | — |
| 8 | What did the basis forget? | Error guessing (§8) | the layer it probes |
| 9 | What does the feature set off elsewhere? | `cross-feature-test-design`, when the basis has §8 entries | data · interaction · temporal · concurrency |

The `qa-test-case-designer` agent runs exactly this order. Record, per condition: technique, coverage items, target. The number of cases is an output of the targets, never a guess up front.

---

## 1. Use-case and end-to-end journey testing

**Idea.** Derive cases from what an actor wants to achieve, walking the whole path the way a user strings the steps together: across screens, features and other actors, to the last consequence the business cares about. It exercises the *integration* of steps that every other technique tests apart.

**Find the journeys.** For each actor in the basis, list their **goals** (the basis's journeys table; if it is empty, derive them: one per reason a person opens the program). A journey starts where the person really starts and ends where the **business outcome** is visible: often on another screen, for another actor, or later in time (the invoice, the stock count, the staff queue, the month-end charge).

**Coverage items, per goal:**

| Item | What it is |
|---|---|
| Main flow | The path most people take, to the outcome |
| Each alternate flow | A valid variation that ends in a **different business outcome** (pays with credits against pays an overage). A variation with the same outcome is a data row, not a flow |
| Each exception flow | A failure the business must survive, with its recovery (a declined payment then a retry; a seat taken between viewing and booking) |
| Each hand-off | A point where another actor continues (the customer books, staff confirm, the customer is notified) |
| The long journey | Where rules accumulate over time: a period of activity, then the job that closes it |

**Coverage** = flows covered ÷ flows listed, with every goal having at least its main flow. Each flow's **postcondition** is the expected result and drives cleanup.

**Pitfalls.** Stopping at the confirmation message instead of the outcome. One journey that tries every variation (no failure can be located). Journeys chosen from the screens instead of the goals. Field variations dressed up as journeys.

---

## 2. Decision table testing

**Idea.** When the outcome depends on a **combination of conditions**, a decision table enumerates every combination so none is missed: the technique for "if A and B but not C, then…".

**Structure.** Rows are conditions and actions; columns are **rules**. N boolean conditions give 2^N columns before simplification. **Coverage** = rules exercised ÷ rules; the minimum is one case per rule.

**Worked example — loan approval.** Conditions: credit score ≥ 700, income verified, existing customer.

| Condition / Rule | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 |
|---|---|---|---|---|---|---|---|---|
| Credit ≥ 700 | T | T | T | T | F | F | F | F |
| Income verified | T | T | F | F | T | T | F | F |
| Existing customer | T | F | T | F | T | F | T | F |
| **Approve** | Y | Y | N | N | Y | N | N | N |
| **Rate** | 4% | 5% | – | – | 6% | – | – | – |

**Collapse with "don't care" (—)** only where the action is truly independent of a condition, and say why: here unverified income rejects whatever the other two say, so R3, R4, R7 and R8 merge into one rule (—, F, — → reject), 8 rules to 5. Flag impossible combinations instead of writing unreachable cases.

**Pitfalls.** A table captures *whether* a rule fires, never *where* its threshold sits: pair every numeric condition with BVA (credit 699 / 700). Assert each rule's action **and** the absence of the others. Independent multi-valued parameters want pairwise, not a table.

---

## 3. Calculation testing

**Idea.** Wherever the system produces a figure (a price, a fee, a balance, a quota, a date, a score), the figure is the behaviour. Derive cases from the **formula**, and state every expected value as a number computed from the basis, never as "calculated correctly".

**Coverage items, per formula:**

| Item | Example, for `overage = (cost − credits remaining) × rate` |
|---|---|
| Each **branch** | Credits cover the cost · cover part of it · cover none of it |
| Each **input class that changes the result** | Each tier's cost; the personal rate against the plan's rate |
| Each **cap, floor and default** | A maximum fee, a minimum charge, a missing rate falling back to the plan's |
| **Zero and identity** | Cost 0, rate 0, nothing to charge: the result is `0.00`, not blank and not an error |
| **Rounding and precision** | A value that lands on half a unit; a sum of rounded lines against the rounded sum |
| **Order of operations** | Discount before tax, or tax before discount: one case that tells them apart |
| **Accumulation** | A second operation that starts from the first one's result; a period total |
| **Reversal** | The operation undone (a refund, a cancellation) returns exactly what was taken |

Add BVA on every threshold inside the formula (§6). **Coverage** = items exercised ÷ items listed, per formula.

**The worked example is the oracle.** Compute each expected value from the basis's formula, write the working beside it, and recompute before handing over: a wrong expected value is worse than a missing case. Assert the figure where the business reads it (the balance, the invoice, the report), and on every screen that shows it.

**Pitfalls.** One happy-path number per formula. Inputs so round that a wrong formula gives the right answer (quantity 1, rate 10 %, price 100): choose values that tell the candidates apart. Guessing a rounding rule the basis does not state: that is an open question, and the case's expected result says so.

---

## 4. State transition testing

**Idea.** When behaviour depends on **history** (the same action does different things in different states), model the states and cover the transitions, including the **invalid** ones that must be refused.

**Model with a state table**, not only a diagram: rows are states, columns are events, a cell is the resulting state or `—` for invalid. The table forces every event in every state, which is how the invalid ones surface.

| State \ Event | submit | pay | ship | cancel |
|---|---|---|---|---|
| Draft | Submitted | — | — | — |
| Submitted | — | Paid | — | Cancelled |
| Paid | — | — | Shipped | — |
| Shipped | — | — | — | — |
| Cancelled | — | — | — | — |

| Coverage level | Covers | Use |
|---|---|---|
| All states | Every state visited | Too weak alone |
| **0-switch** | Every valid transition once | The default |
| **Invalid transitions** | Every `—` cell refused, with nothing changed | The default, alongside 0-switch |
| **1-switch** | Every valid pair of consecutive transitions | Money, approvals, anything irreversible |
| Round trip | Every lifecycle loop | Where states cycle |

Here: 4 valid transitions (0-switch) and the `—` cells that matter (pay a Draft, ship an unpaid order, cancel a Shipped one).

**Who may act.** Where the action depends on the actor, extend the model to a **role × action table** per state (owner, another user, staff, signed out): each cell is allowed or refused, and each refusal is a case that also shows nothing changed.

**Pitfalls.** Only the happy-path arrows. The `—` cells are where skipped payments and double shipments live. Guards on a transition ("pay only if amount > 0") need BVA.

---

## 5. Equivalence partitioning (EP)

**Idea.** Split each input (and output) domain into partitions whose members are processed the same way; one value per partition is enough. Always partition into **valid and invalid** classes: several valid partitions may share a case, but **one invalid partition per case**, so the failure is unambiguous.

**Example — age, accepted 18–65:** `17` (below) · `34` (valid) · `70` (above) · `"abc"` (not a number) · empty. Five partitions; the four invalid ones are one parameterized case with four rows. **Coverage** = partitions exercised ÷ partitions.

**Pitfalls.** Forgetting **output** partitions (discount 0 % / 5 % / 10 % are classes worth a case each: this is where EP meets the business rules). Partitioning only the valid range: the basis is usually silent about the invalid classes.

---

## 6. Boundary value analysis (BVA)

**Idea.** Defects cluster at the edges of **ordered** partitions (numbers, dates, lengths, counts). BVA refines EP; unordered partitions ("valid or invalid email") have no boundary.

- **2-value**: the boundary and its nearest neighbour in the adjacent partition.
- **3-value**: the boundary and both neighbours. If `x <= 10` is miscoded as `x == 10`, the 2-value set `{10, 11}` passes; `9` catches it. Use 3-value on every business threshold.

**Example — "free delivery for orders ≥ €100", range €0–€1000:** rule boundary `99.99 · 100.00 · 100.01`; field boundaries `-0.01 · 0` and `1000 · 1000.01`. The step is the smallest representable one: `1` for integers, `0.01` for money, one second or one day for time.

**Pitfalls.** The boundary of the **rule** (`100`) matters more than the boundary of the **field** (`0`, `1000`), and is the one that gets skipped. `≥ 100` and `> 100` move the boundary by one step: when the basis does not say which, that is a question.

---

## 7. Pairwise and classification trees

**Pairwise.** When several **independent** parameters each take several values (5 browsers × 4 systems × 3 locales × 2 roles = 120), cover every *pair* of values at least once: usually 15–20 cases. Generate the array with a tool (PICT, ACTS, `allpairspy`), say it is pairwise, not exhaustive, and force any high-risk combination in as its own row. Strength: each-choice < pairwise < t-wise < exhaustive. Parameters that interact want a decision table instead.

**Classification tree.** EP made visible: classifications (aspects that vary), each with classes (its partitions), combined by a stated rule (one per class, pairwise, or all). Use it when many dimensions need a reviewable picture.

---

## 8. Error guessing and experience-based

Formal techniques cover what the basis *says*; these cover what it does not.

- **Error guessing**: empty, zero, negative, max + 1, very long, duplicate submit, double click, back button, concurrent edit, special characters, emoji, leading and trailing whitespace, timezone and DST, leap day, month end, rounding, off-by-one.
- **Checklists and fault attacks**: a reusable taxonomy (money, time, authorization, input) applied as a sweep.
- **Exploratory**: `qa/manual/exploratory-charter-writer`, or the `qa-explorer` agent on a live program.

Additive and tagged, never a substitute for the systematic set.

---

## Technique selection matrix

| The requirement looks like… | Primary technique | Combine with |
|---|---|---|
| A goal a person achieves across steps | **Use-case / journey** | Calculation on its figures; state on its hand-offs |
| "If A and B but not C then X" | **Decision table** | BVA on each numeric condition |
| A figure the system produces | **Calculation** | BVA on thresholds in the formula; decision table for its branches |
| A thing with states; history matters | **State transition** | Role × action table; BVA on guards |
| A numeric, date or length threshold | **BVA** | EP for the unordered classes |
| A field with a range or set of values | **EP** | BVA on the ordered partitions |
| Many independent parameters | **Pairwise** | Forced high-risk rows; a classification tree to show it |
| "What did we miss" | **Error guessing** | Always on top of the systematic set |
| An entity two features touch · a chain across features · another owner's trigger · a schedule or timeout | → `cross-feature-test-design` | |

A real feature needs the techniques **layered**: a checkout has journeys (guest, returning), rules (delivery × membership × coupon), figures (discount, tax, total), a lifecycle (basket → paid → shipped) and fields. Each layer contributes cases, and the business layers contribute most of them.

## Stopping criteria

| Technique | Done when |
|---|---|
| Use-case / journey | Every goal has its main flow; every alternate, exception and hand-off listed is covered |
| Decision table | Every reachable rule after collapsing |
| Calculation | Every branch, cap, floor and default; zero; rounding; one accumulation and one reversal per formula that has them |
| State transition | All valid transitions (0-switch) and all invalid ones refused; 1-switch on money and irreversible paths |
| BVA | Every boundary: 3-value on business thresholds, 2-value elsewhere |
| EP | Every valid and every invalid partition |
| Pairwise | Every pair of parameter values |

State the achieved coverage in the deliverable ("use-case: 3 goals, main + 2 alternate + 1 exception; decision table 5/5; BVA 3-value on the delivery threshold"). Coverage that cannot be named was not measured.

## Rules

- Walk the chain: basis → conditions → coverage items → cases. Never jump to cases.
- Business first: journeys, decisions and figures before fields. A design whose field items outnumber the rest has skipped steps 1–4.
- Every expected figure is computed from the basis and its working is kept.
- One invalid partition per negative case. No BVA on unordered partitions.
- State tables, not only diagrams. Decision tables collapsed only with the reason stated.
- Never skip the boundary of the rule because the boundary of the field was tested.
- Name the technique and its coverage level on every case or group.

## Handoffs

- The basis these techniques run against → `qa/manual/requirements-breakdown`
- The feature's connections (chains, shared data, schedules, concurrency) → `qa/manual/cross-feature-test-design`
- Formatting the cases into a suite → `qa/manual/test-case-writer`; the whole flow → the `qa-test-case-designer` agent
- Sizing the investment by risk → `qa/manual/test-strategy`
- Automating the cases → `qa/<stack>/skills/api-test-author/...` / `qa/<stack>/skills/ui-test-author/...`
