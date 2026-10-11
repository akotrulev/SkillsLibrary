---
name: dependency-map
description: Use when a project's business model needs its connections: every trigger (API call, schedule, timeout, webhook, internal event) with the reactions it sets off across features, the data features share (CRUD matrix), and the invariants those writes threaten — persisted to docs/business-model/. Triggers: "what else happens when X", "who else uses this data", "map the events and jobs". Do NOT use for one entity's lifecycle (`state-grid`), rule tables (`decision-table`), or test cases (qa).
---

# BA — Dependency Mapper

Records how features connect: what **starts** each piece of behavior (a trigger), what **happens next** (a reaction), which **data** several features write or read, and what must **always hold** across those writes. The entity grids say what may happen to one entity; the decision tables say which outcome a rule set yields. Neither says that cancelling a booking also returns credits, removes an accrual and frees a seat, in three features, after commit, at-least-once. That is the connection layer, and it lives in three files of the KB.

A reaction that nobody fires, an event that nobody consumes, a field two features write with no rule between them: each is invisible inside one feature's spec and visible the moment the connections sit in one place.

## When to use

- A feature fires, or reacts to, something another feature owns: an API call, a schedule, a timeout, a webhook, an internal event
- Two features write or read the same entity or field
- The user asks "what else happens when X", "who else uses this data", "what must never be violated"
- A conflict sweep needs its pair list, or an entity grid needs trigger ids for its columns
- The KB is being built or refreshed from specs or from code

## When NOT to use

- One entity's lifecycle → `business-analysis:state-grid`
- Rule tables for one decision point → `business-analysis:decision-table`
- Step paths and failure exits of one process → `business-analysis:process-flow`
- Test cases for any of this → `qa/manual/*`. This skill records what the software does and how features interact, never how to test it

## Contract with the KB

Per `business-analysis/skills/ba-project-memory`: **read first** (`INDEX.md`, the three files if they exist, and the entity grids and decision files the feature touches), **update after** (the three files, `INDEX.md`, `active-context.md`). New rows join the existing files; a second events file for one feature is the anti-pattern.

Where a cell names a feature, it uses the feature-identity rule: `E<n>` or `AREA-nnn` with a label. Every row carries a source and a confidence tag, in the KB's annotation grammar.

## Procedure

1. **Read the KB first**: `INDEX.md`, `events.md`, `shared-data.md`, `invariants.md`, and the grids and decisions the feature touches.
2. **List the triggers**, all five kinds. Every event column of every entity grid must appear here.
3. **List the reactions**: when, guard, owner, effects, emits, mode, on failure.
4. **Follow the chains.** Check for unconsumed events, orphan reactions and cycles.
5. **Build the shared data.** Fields read by a schedule's selection count as reads. Run the completeness check.
6. **Record the invariants and resource limits**, with who threatens each and whether each is enforced.
7. **Hand every finding to `conflict-check`** with a boundary condition, then update the KB.

## `events.md` — triggers and reactions

```markdown
# Events & reactions

**Created:** <YYYY-MM-DD>
**Owned by:** `business-analysis:dependency-map`

## Triggers
| ID | Trigger | Kind | Fired by | Owner | Source |

## Reactions
| ID | When | Guard | Owner | Effects | Emits | Mode | On failure | Source |
```

- **Kind** is one of five values:
  - `command`: an actor asks, through an API call, a screen or an admin tool.
  - `schedule`: a clock fires it. *Fired by* carries the schedule and its timezone.
  - `timeout`: a deadline relative to an entity, such as "15 min after a reservation".
  - `external`: an inbound webhook, callback, file drop or partner message.
  - `event`: an internal past-tense fact. *Fired by* lists the `RX-` ids that emit it.
- **Effects** use four forms, separated by `;`:
  - `ENT-nnn From → To`
  - `DEC-nnn` (the decision evaluated)
  - `Entity.field +n | −n | := v`, or `creates <Entity>`
  - `notifies <who>`, which is terminal
- **Mode** is one of four values:
  - `in request`: the same transaction as the trigger.
  - `after commit, <at-least-once | at-most-once | exactly-once | ?>`
  - `scheduled`: runs inside a schedule over the selection named in *Guard*.
  - `best effort`: loss is acceptable, and *Source* names the decision that says so.
- **On failure** is one of: `rolls back` · `retried <n>× then <dead-letter | alert | drop>` · `compensates: <what>` · `unhandled` · `?`. The last two are findings.
- **Rules:**
  - Every column header of an entity grid is a trigger id.
  - Every `event` trigger has at least one reaction, or *Source* says `terminal by decision`. Otherwise it is an *unconsumed event* finding.
  - Every reaction's *When* exists. A reaction nothing fires is an *orphan* finding.
  - A cycle of reactions with no guard that breaks it is a conflict class 6 finding (circular dependency).

## `shared-data.md` — the CRUD matrix and the shared fields

```markdown
## CRUD matrix — entities touched by two or more features
| Entity | Create | Read | Update | Delete | Completeness |

## Shared fields
| Field | Written by | Read by | Note |
```

- Cells list `RX-` ids. A human reader is named plainly (`screen: my balance`, `report: monthly revenue`). A schedule's selection counts as a read.
- Only entities that two or more features touch get a matrix row. Only fields with two or more writers, or a writer in one feature and a reader in another, get a shared-field row. Anything else is a schema dump.
- **Completeness** is the static half of CRUD testing (ISTQB CTAL-TA v4.0 §3.2.1). A missing operation is either `by decision (<source>)` or a finding.

## `invariants.md` — what must always hold

```markdown
| ID | Invariant | Fields | Threatened by | Enforced | Source |
```

- An invariant is an always/never statement or a resource limit, such as capacity, quota or budget. `conflict-check` finds them while normalizing (its §1); from then on they are kept here.
- *Threatened by* lists every reaction that writes any of the invariant's fields, taken from `shared-data.md`.
- *Enforced* is stated per threatening reaction: `yes (<how>)`, or `no` / `?`, both of which are findings.

## The checks

| Check | Finding when | Boundary condition names |
|---|---|---|
| Unconsumed event | an `event` trigger has no reaction and no `terminal by decision` | the emitting reaction and what the missing consumer would have done |
| Orphan reaction | a reaction's *When* is fired by nothing | the state in which the reaction would be expected to run |
| Cycle | reactions emit and consume each other with no breaking guard | the first trigger and the entity state that repeats |
| CRUD completeness | a matrix cell is empty without `by decision` | the operation and the entity state in which it is expected |
| Unenforced invariant | a threatening reaction is `no` or `?` | the concrete sequence of reactions that breaks it |
| Unsafe failure or mode | *On failure* is `unhandled` or `?`, or *Mode* is `?` | the failed or repeated delivery and the data left behind |

Every finding goes to `business-analysis/skills/ba-feature-conflict-check` for severity and resolution recording; none is resolved here. An edge a source is silent on is `[TBD - source silent]`, never a guessed `yes` or `in request`.

## Quality bar

- [ ] Every trigger names its kind; every `schedule` names its timezone or `?`
- [ ] Every entity-grid column header is a trigger id
- [ ] Every reaction carries guard, owner, effects, emits, mode and on-failure, with a source
- [ ] Effects use the four forms; no prose in the Effects column
- [ ] Unconsumed events, orphan reactions and cycles checked and filed
- [ ] CRUD matrix limited to entities two or more features touch; every empty cell is `by decision` or a finding
- [ ] Every invariant lists all threatening reactions and states enforcement per reaction
- [ ] Every finding carries a boundary condition
- [ ] No test cases, techniques or coverage anywhere in the files
- [ ] KB updated per the contract (three files + INDEX + active-context)

## Anti-example

Bad: the bookings spec says a cancellation frees a seat; the credits spec says credits come back on cancellation. Each is correct alone and neither lists the other. The map records the cancellation as one trigger with reactions in both features, plus the second event (cancelled by staff, from a session cancellation) that reaches the same credit reaction. The reaction's mode (at-least-once) and the missing idempotency key become visible as an unenforced invariant, instead of a double refund found in production.

Also bad: one row per field of every table. The shared-data file holds only what two features touch.

A filled example is in `references/example-dependency-map.md`.

## Handoffs

- Every finding → `business-analysis/skills/ba-feature-conflict-check`
- Grid columns become trigger ids → `business-analysis/skills/ba-entity-state-grid`
- A reaction hides a multi-input rule → `business-analysis/skills/ba-decision-table`
- A flow's "who else reacts" answers → recorded here from `business-analysis/skills/ba-process-flow-diagram`
- KB mechanics and the feature slice → `business-analysis/skills/ba-project-memory`
- The QA consumer reads these files as data through `qa/manual/requirements-breakdown/references/connections.md`; a format change here updates that file in the same commit
