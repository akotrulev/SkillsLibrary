---
name: cross-feature-test-design
description: Use when test cases must cover how a feature affects others — reaction chains, foreign events in shared states, shared data (CRUD, def-use), schedules and time boundaries, duplicate or concurrent delivery, invariants — from a basis with Connections. Triggers: "what else should we test when X changes", "test the side effects of Y", "cross-feature test cases". Do NOT use for field-level EP/BVA or single-feature rules (`test-design-techniques`) or formatting the suite (`test-case-writer`).
---

# QA — Cross-Feature Test Design

Turns the basis's **§8 Connections** into coverage items. `test-design-techniques` covers what one feature does with its own fields, rules and states. This skill covers what the feature sets off elsewhere, what else can happen to the state it relies on, what it shares with other features, and what must always hold. It runs **after** `test-design-techniques` and produces the same coverage-item list (condition → technique → coverage items → target), where every item carries the **slice id** it came from.

The analysis half lives in `qa/manual/requirements-breakdown` (§8 and `references/connections.md`). This skill is the design half: §8 says what is connected; this skill says how many cases that deserves and of which kind.

## When to use

- The basis has §8 entries and the suite must go beyond field validation
- A story changes data another feature reads, or a state another feature's trigger acts on
- A schedule, timeout, webhook, retry or at-least-once consumer sits next to the feature
- The question is "what else should we test when X changes" or "which side effects are untested"

## When NOT to use

- Field constraints, thresholds, rule combinations or the feature's own lifecycle → `qa/manual/test-design-techniques`
- The basis itself (building §8) → `qa/manual/requirements-breakdown`
- Formatting, IDs, Setup and Cleanup → `qa/manual/test-case-writer`
- Automating a temporal, concurrency or delivery case → `qa/<stack>/skills/time-and-concurrency-testing`
- §8 reads `Not built — single-feature basis` → nothing to design here; say so and stop

## Inputs needed

1. **The basis with §8** (the connections, each row sourced) and the coverage-item list `test-design-techniques` produced from §1–§7
2. **Slice ids** — the KB ids in §8 (`EVT-`, `RX-`, `ENT-`, `DEC-`, `INV-`), or the document lines of a docs-only §8, which then give `#assumption` items
3. **Priorities** from the basis's risk ranking, where it has one

## Procedure

1. **Read §8 table by table** and tag each row with its slice lookup (`L1`…`L8`, numbered as in `references/connections.md`). A slice id is the lookup plus the KB ids, such as `L2 RX-002 → EVT-006 → RX-006`.
2. **Pick the technique** for each row from the first table below.
3. **Enumerate the coverage items** the technique defines. Pairs come from the slice, never from a cross product.
4. **Prioritize** (below).
5. **Prune**: a case asserts the effects of one reaction, the behaviour of one owner. A scenario case chains reactions and attaches a check to each step the next step depends on.
6. **Emit the coverage-item list**, one row per condition: slice id → technique → coverage items → target from the stopping table. An item that gets no case carries a stated reason (out of scope, deferred, blocked by an open question). A `?` or `unhandled` item becomes an **open-question case** or a stated deferral that names the question.

## Which technique, from which part of the slice

| Slice element | Technique | Coverage item |
|---|---|---|
| A trigger's reaction chain (L1–L3) | **Scenario-based**: the chain is the model, fan-out is a fork; main, extension and exception scenarios | Each path through the chain, including each reaction's *On failure* exit |
| Another owner's trigger legal in a state the feature relies on (L4) | **State transition across owners**: 0-switch on foreign cells, 1-switch (own transition → foreign trigger), round-trip on lifecycle loops | Each (state, foreign trigger) cell, and each `—` and `?` cell in the rows the feature reaches, schedule columns included |
| An entity two features touch (L6) | **CRUD testing, consistency half**: functions combined over the entity's lifecycle, plus negatives such as reading before create or updating after delete | Each C/R/U/D cell in the entity's row |
| A field with two or more writers, or a reader in another feature (L6) | **Def-use across features** | Each (writer, reader) pair, and each ordered (writer, writer) pair |
| A decision table with rows from two or more features (L5) | Decision table on the overlap rows, plus BVA on thresholds the features share | Each overlap row and each shared threshold |
| A `schedule` or `timeout` trigger | **Temporal** | The job's column across every state. Boundary instants: cut-off minus one step, at, plus one step; the schedule's timezone; DST change; month end. A run executed twice; a late or missed run; a run during a user action on the same entity |
| A reaction in `after commit` mode, or a field with two or more writers | **Concurrency and delivery** | Duplicate delivery, out-of-order delivery, a concurrent pair of writers, a retry after partial failure |
| An invariant (L7) | **Invariant attack** | Each (invariant, threatening reaction) pair |
| A conflict entry (L8) | **Conflict boundary case** | Each boundary condition. A resolved conflict asserts its resolution; an open one expects the question |
| A cross-area journey in `system-overview.md` | Scenario-based, end to end, with simple loop coverage | Main, extension and exception scenarios |

## Stopping criteria

| Technique | Done when |
|---|---|
| Scenario-based | Every path to the slice depth is covered. Every `unhandled`/`?` failure has a P1 open-question case, or a stated deferral naming the question and the missing hook |
| State transition across owners | Every foreign-legal cell and every `—`/`?` cell in those rows. 1-switch for money and irreversible paths |
| CRUD consistency | Every operation in the row. For P1 entities, the rigorous form: after each U, every R |
| Def-use | All-uses on P1 fields, all-defs elsewhere |
| Decision table + BVA | All overlap rows, with 3-value BVA on shared thresholds |
| Temporal | Every state in the column, every boundary instant, one idempotency case per job |
| Concurrency and delivery | One duplicate case per `at-least-once` reaction; one concurrent-pair case per pair of writers on a P1 field |
| Invariant attack | Every pair. Pairs with `Enforced` = `no` or `?` are P1 |
| Conflict boundary | All boundary conditions |

## Priority

- **P1:** money, data integrity, an irreversible effect, `Enforced` = `no`/`?`, an `unhandled`/`?` failure, an open conflict.
- **P2:** every other slice item.
- **P3:** experience-based extras beyond the checklist rows above.

## An open question is an expected result

Where the business never decided the outcome, the case's expected result is `open question: <the question>`, written once, and the case is P1. It is never "credits returned or forfeited". The case is still designed (setup, steps, the exact instant), so the moment the answer arrives only the expected result changes.

## Sources

- **CRUD testing, state transition (N-switch, round-trip), scenario-based testing:** ISTQB Certified Tester Advanced Level Test Analyst, CTAL-TA v4.0 (2025-05-02), §3.2.1–§3.2.3.
- **Def-use:** Rapps and Weyuker, "Selecting Software Test Data Using Data Flow Information", IEEE Transactions on Software Engineering, 1985 (all-defs, all-uses).
- **Temporal and concurrency and delivery:** experience-based checklists keyed to the *Mode* column of `events.md`, not formal techniques. State the coverage as "checklist", never as a percentage.

## Anti-example

The input is `DELETE /bookings/{id}` plus the story. Bad response: seven cases — id missing, id malformed, id unknown, another member's booking, already cancelled, the happy path, maybe one late cancellation. Every AC is "covered", and no case looks at the credits, the freed seat, a staff cancellation of the whole session, or the monthly posting job.

Also bad: a cross product of every feature with every other, or a case that asserts a returned credit and a freed seat and a notification in one go. Take pairs from the slice, one reaction per case.

A filled example, slice to cases, is in `references/example-cancel-booking.md`.

## Handoffs

- Format the cases (layer groups, parameterized fields, async and temporal forms) → `qa/manual/test-case-writer`
- Field, rule and own-state coverage → `qa/manual/test-design-techniques`
- Orchestrate basis → connections → design → suite → `qa/manual/agents/qa-test-case-designer`
- Automate temporal, concurrency and delivery cases → `qa/<stack>/skills/time-and-concurrency-testing`
- Edges the KB lacks (KB candidates) → `business-analysis/agents/business-analyst`
- A defect noticed while designing → `qa/manual/bug-report-writer`
