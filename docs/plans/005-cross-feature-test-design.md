# 005 — Cross-feature test design: the dependency map and the tests it drives — plan (2026-10-11)

**Goal:** Given a spec, a story, or just a feature in the code, the QA lane finds every connection the
feature has: the API calls, schedules, timeouts, webhooks and internal events that start it or that it
sets off, the data it shares with other features, and the invariants those writes can break. It then
designs test cases for those connections, not only for field constraints. The connections are recorded
once in the project's business-model knowledge base (`docs/business-model/`) as a **dependency map**.
The map is built from specs by `business-analyst` or from code by `be-documenter`, and any later
session looks the connections up there instead of re-deriving them. The three `qa-api-<stack>` agents
then automate the new case kinds. They run scheduled jobs on demand, control the clock at a time
boundary, fire concurrent requests, and deliver a message or webhook twice.

**Status:** K1, D1, Q1, Q2 and A1 landed 2026-10-11. K1: `business-analysis:dependency-map`, its golden example, the KB contract and feature slice, the three reasoning-lane edits and the `business-analyst` edits. D1: `dev:doc-feature-trace` has the seventh inventory (Edges) and the seam recipes, area and feature documents have *How it connects*, and `be-documenter` writes the dependency map. Q1: `requirements-breakdown` writes §8 Connections (schema constraints moved to the data dictionary), `qa-*:cross-feature-test-design` exists with its golden example, registered in all three `qa-*` plugins (D14 records four departures from §9.3). Built but unverified: nothing has been run (the gate is A3), and description lengths and file sizes are counted by hand or `wc` only. Q2: `test-case-writer` writes parameterized field cases and the chain, async, temporal and concurrency forms; `qa-test-case-designer` runs five steps with Code mode and the depth gate; `qa-test-planner` plans from the slice. A1: `qa-typescript:time-and-concurrency-testing` (jobs on demand, controlled clock, barrier races, duplicate delivery), the `qa-api-typescript` Step 3 / Mode B wiring and three review checks, registered in `qa-typescript` only; nothing was run, samples uncompiled. Next: A2. O1 is answered: the automation is in this
plan, as tasks A1–A3. The plan changes skills and agents only, so the gate (§11) proves structure, not
quality. The new stack skills' code samples are never compiled. Whether the suites actually get deeper,
and whether the automation patterns run, is unverified until H1 runs the lane on a real project.

---

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| A persisted model of what sets off what across features | The KB holds flows, one state × event grid per entity with the owning feature on each transition, merged decision tables and the interaction map (`business-analysis/skills/ba-project-memory/SKILL.md:30-39`). The grids' event columns are free text (`ba-entity-state-grid/SKILL.md:33`). `process-flow` asks "who else reacts to this?" but keeps the answer only in one flow's timeline (`ba-process-flow-diagram/SKILL.md:47`) | `events.md`: every trigger (command, schedule, timeout, external, event) and every reaction, with what it emits, its mode and its failure behaviour (§4.1, K1) |
| Which features share which data | Nothing. `conflict-check` classifies "resource" claims during normalization and does not persist them (`ba-feature-conflict-check/SKILL.md:47`) | `shared-data.md`: a CRUD matrix plus the shared fields (§4.2, K1) |
| Cross-feature invariants | Classified as "invariant" during normalization, then discarded (same line) | `invariants.md`: each invariant, the reactions that threaten it, and whether each one enforces it (§4.3, K1) |
| A lookup for "everything connected to feature X" | `conflict-check` §2 builds a pair list by reasoning, once per run (`ba-feature-conflict-check/SKILL.md:51`) | The feature slice: eight grep-able lookups over stable ids (§5, K1) |
| Connections derived from code | `feature-trace` records the events an area emits but not who reacts to them (`backend/_shared/feature-trace/SKILL.md:52`). Its six inventories have none for edges (`:57`) | A seventh inventory, **Edges**, which follows every emitted event and every shared field one hop outside the area (§8.1, D1) |
| Reverse documentation shows connections | Area and feature documents have one flow per trigger but no section on what crosses into other areas (`backend/_shared/business-documentation/SKILL.md:58`) | An optional **How it connects** section, and `be-documenter` writes the dependency map (§8.3–§8.4, D1) |
| The test basis captures connections | `requirements-breakdown` writes seven single-feature sections (`qa/manual/requirements-breakdown/SKILL.md:83`). Its OpenAPI walk writes one validation row per schema keyword (`:67-69`) | A §8 **Connections** section. Schema constraints move to the data dictionary, and validation rows are kept for business validations (§7.1–§7.2, Q1) |
| Test-design techniques for interactions | The default recipe is EP → BVA → decision table → state transition → use-case → error guessing (`qa/manual/test-design-techniques/SKILL.md:225`). There is no CRUD, scenario-based, round-trip, def-use, temporal or concurrency technique | `cross-feature-test-design` (§6, Q1) |
| Test design from code | The designer's inputs are story, BRD, contract, state diagram, rules table or URL (`qa/manual/agents/qa-test-case-designer.md:43-50`). The planner lists surfaces and deliberately does not trace rules (`qa/manual/agents/qa-test-planner.md:44`) | A Code mode that loads `dev:doc-feature-trace` (§7.3, Q2) |
| Depth is measured | Coverage is AC → TC (`qa-test-case-designer.md:117`). Forty field cases and two happy paths "cover every AC" | A Connection → TC matrix, counts by layer, and a depth gate (§7.4, Q2) |
| Suites stay readable when field validation is large | One case per coverage item (`qa/manual/test-case-writer/SKILL.md:38`) | One parameterized case per field and direction, with cases grouped by layer (§7.5, Q2) |
| What QA learns flows back | Only BA → QA, as "boundary conditions double as BVA seeds" (`ba-feature-conflict-check/SKILL.md:73`) | QA hands **KB candidates** to `business-analyst` (§7.6, K1 + Q2) |
| Automated tests can run a scheduled job and control time | The `qa-api-<stack>` Step 3 lists DB, messages, files, email, realtime, contracts, resilience, flags and production probes (`qa/typescript/agents/qa-api-typescript.md:139`, `qa/java/agents/qa-api-java.md:139`, `qa/dotnet/agents/qa-api-dotnet.md:76`). No skill runs a job on demand or replaces the clock. Async effects are already polled (`vi.waitFor` in `qa/typescript/skills/api-test-author/writer/SKILL.md:180`, Awaitility in `qa/java/skills/failure-injection-testing/SKILL.md:151`) | `time-and-concurrency-testing` per stack, wired into Step 3 (§7.8, A1–A3) |
| Automated tests can race requests and replay deliveries | Broker redelivery is covered only as the consumer's settlement (`qa/typescript/skills/messaging-testing/references/sqs.md:238`). Nothing sends the same message twice to prove the consumer is idempotent, nothing fires concurrent requests, and the API review flags neither | The same skill, plus three review checks (§7.8, A1–A3) |

## 2. Why today's suites are validation-heavy

Five causes, each traced to a line in §1:

1. **The basis is richest where the input is most structured.** The OpenAPI walk turns every
   `required`, `minimum`, `maxLength`, `enum` and `pattern` into its own validation row. Rules and
   states appear only when prose states them. An API-first feature therefore arrives at test design with
   thirty constraint rows and three rules.
2. **The recipe starts at the field and stops at the feature.** EP and BVA run first and produce the
   most coverage items. Decision tables and state transition run only inside one feature. The 2025 ISTQB
   Advanced Test Analyst syllabus (CTAL-TA v4.0, §3.2) added the behaviour-based techniques that look
   past one feature: CRUD testing, round-trip state coverage, and scenario-based testing. None of them
   is in the library.
3. **Coverage counts acceptance criteria.** A suite that tests every field and walks the happy path
   satisfies the AC → TC matrix. Nothing measures whether a reaction chain, a shared field or a schedule
   was tested, so nothing pushes towards them.
4. **The cross-feature knowledge exists, but it reaches QA as boundary values.** The KB's grids,
   decision tables and conflict findings are good test input. `conflict-check` hands its boundary
   conditions over as "BVA seeds", which shrinks an interaction to a threshold. The KB also has no
   connection layer. Nothing lists which consumer reacts to which event, which job later selects the rows
   a feature writes, or which invariant a write threatens.
5. **"Point at the code" has no QA route.** The test designer cannot read code, and the planner only
   lists surfaces. The trace that could do it (`feature-trace`) stops at the area boundary: it records
   what is emitted and not who reacts.

## 3. How it will be used — the two stages

**Stage 1 — build the map once, keep it current.** Pick the entry point that matches what the project has:

| The project has | Run | What lands in `docs/business-model/` |
|---|---|---|
| Code and no requirements | `/dev:document-system` (`be-documenter`) | Areas, flows, grids, decisions, plus `events.md`, `shared-data.md` and `invariants.md`, all `#observed`/`#inferred` with `file:line` |
| One feature in code | `/dev:document-feature` (`be-feature-documenter`) | Nothing in the KB. The feature document gains **How it connects** (one hop out), which is test basis in its own right |
| Specs and stories | `/business-analysis` (`business-analyst`, ANALYZE or EXTEND) | The same artifacts, `#confirmed` where a source states them |

Each new story then goes through `business-analyst` EXTEND, and the map grows with the product.
AUDIT and REFRESH runs reconcile it with the code.

**Stage 2 — design from the map.** Run `/qa-<stack>:test-cases <story | spec | feature name | path>`:

1. Step 1 distils the basis (§1–§7 of the basis document, as today, with leaner validations).
2. Step 2 maps the connections into §8. It slices the KB first (§5). Where the KB is missing or stale
   it traces the code (Code mode), and where there is no code it reads the docs with every edge flagged.
3. Step 3 designs the cases. `test-design-techniques` covers fields, rules and the feature's own
   states. `cross-feature-test-design` covers chains, shared data, foreign events, schedules,
   duplicate and concurrent delivery, and invariants.
4. Steps 4 and 5 assemble the suite and review it. The depth gate fails a suite that ignores the
   connections it was given.
5. `/qa-<stack>:api` automates the suite (Mode B: the cases are the plan). Temporal, concurrency and
   delivery cases go through `time-and-concurrency-testing` (§7.8). A case whose *Environment needs*
   the system cannot meet is deferred, and the missing hook is handed to `be-<stack>`.

**The loop.** Edges that Step 2 found in code or docs but did not find in the KB are listed in §8 as
**KB candidates**. `business-analyst` folds them into the map on its next EXTEND. QA never writes the
KB, and every test-design run leaves the next run a better map.

Without a KB, Stage 2 still works on its own: Code mode traces the seams of that one feature. It is
slower, and nothing is kept.

## 4. The dependency map — three new KB artifacts

The skill `business-analysis:dependency-map` owns all three files. They sit beside the existing ones
and follow every rule in `knowledge-base`: stable ids, sources, the annotation grammar, the
header/provenance lines, read-first and update-after. Where a cell names a feature, it uses the
feature-identity rule (`E<n>` or `AREA-nnn` with a label).

### 4.1 `events.md` — triggers and reactions

```markdown
# Events & reactions
**Created:** … · **Owned by:** `business-analysis:dependency-map`

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
- **On failure** is one of: `rolls back` · `retried <n>× then <dead-letter | alert | drop>` ·
  `compensates: <what>` · `unhandled` · `?`. The last two are findings.
- **Rules:**
  - Every column header of an entity grid is a trigger id.
  - Every `event` trigger has at least one reaction, or *Source* says `terminal by decision`.
    Otherwise it is an *unconsumed event* finding.
  - Every reaction's *When* exists. A reaction nothing fires is an *orphan* finding.
  - A cycle of reactions with no guard that breaks it is a conflict class 6 finding (circular dependency).

### 4.2 `shared-data.md` — the CRUD matrix and the shared fields

```markdown
## CRUD matrix — entities touched by two or more features
| Entity | Create | Read | Update | Delete | Completeness |

## Shared fields
| Field | Written by | Read by | Note |
```

- Cells list `RX-` ids. A human reader is named plainly (`screen: my balance`, `report: monthly
  revenue`). A schedule's selection counts as a read.
- Only entities that two or more features touch get a matrix row. Only fields with two or more writers,
  or a writer in one feature and a reader in another, get a shared-field row. Anything else is a schema
  dump.
- **Completeness** is the static half of CRUD testing (ISTQB CTAL-TA v4.0 §3.2.1). A missing operation
  is either `by decision (<source>)` or a finding.

### 4.3 `invariants.md` — what must always hold

```markdown
| ID | Invariant | Fields | Threatened by | Enforced | Source |
```

- An invariant is an always/never statement or a resource limit, such as capacity, quota or budget.
  `conflict-check` already finds them while normalizing (§1 of that skill). From now on they are kept here.
- *Threatened by* lists every reaction that writes any of the invariant's fields, taken from
  `shared-data.md`.
- *Enforced* is stated per threatening reaction: `yes (<how>)`, or `no` / `?`, both of which are findings.

### 4.4 The procedure `dependency-map` teaches

1. Read the KB first: `INDEX.md`, the three files if they exist, and the grids and decision tables the
   feature touches.
2. List the triggers, all five kinds. The events of every entity grid must appear here.
3. List the reactions: when, guard, owner, effects, emits, mode, on failure.
4. Follow the chains. Check for unconsumed events, orphan reactions and cycles.
5. Build the shared data. Fields read by a schedule's selection count as reads. Run the completeness check.
6. Record the invariants and resource limits, with who threatens each one and whether it is enforced.
7. Hand every finding to `conflict-check` with a boundary condition, then update the KB:
   the three files, `INDEX.md` and `active-context.md`.

### 4.5 Descriptions (each ≤ 500 characters; the task verifies the count)

- `dependency-map`: *Use when a project's business model needs its connections: every trigger (API
  call, schedule, timeout, webhook, internal event) with the reactions it sets off across features, the
  data features share (CRUD matrix), and the invariants those writes threaten — persisted to
  docs/business-model/. Triggers: "what else happens when X", "who else uses this data", "map the events
  and jobs". Do NOT use for one entity's lifecycle (`state-grid`), rule tables (`decision-table`), or
  test cases (qa).*

## 5. The feature slice — the lookup

The slice is the set of connections that matter for one feature. The input is an owner id (`E<n>`,
`AREA-nnn`) or a trigger id (`EVT-nnn`). The slice is eight lookups. Each is a grep, because every row
carries ids under the KB's feature-identity rule.

| # | Lookup | Where | What it yields |
|---|---|---|---|
| 1 | Own triggers and reactions | `events.md`, rows with *Owner* = id | What can start this feature, and what it does |
| 2 | Downstream | follow *Emits* → reactions whose *When* is that event, repeated | What it sets off in other features |
| 3 | Upstream | other owners' reactions whose *Emits* reach this feature's reactions | Who else can start it |
| 4 | States depended on | for each `ENT` transition this feature makes, the target state's row in the grid | Other owners' triggers that are legal in that state, plus every `—` and `?` in the row |
| 5 | Decisions | `decisions/` files this feature contributes rows to | The other contributors' rows |
| 6 | Shared data | `shared-data.md` rows naming this feature's reactions | The other writers and readers |
| 7 | Invariants | `invariants.md` rows whose *Threatened by* includes this feature's reactions | What it can break, and whether it guards against it |
| 8 | Known interactions | `interaction-map.md` entries with this feature in *Pair* | Resolved and open conflicts, each with its boundary condition |

**Depth (D12):** two hops past the feature's own reactions. Go further where an effect moves money or
cannot be undone. `knowledge-base` defines the slice, and `conflict-check` uses it as its pair list
when the map exists. QA reads it through `requirements-breakdown/references/connections.md`, which
restates the eight lookups as a reading guide over files QA treats as data (D1, D5).

## 6. Cross-feature test design — techniques and coverage

The new skill `qa/manual/cross-feature-test-design` (registered as `cross-feature-test-design` in all
three `qa-*` plugins) runs after `test-design-techniques`, from the basis's §8. It produces the same
coverage-item list shape (condition → technique → coverage items → target), and every item carries the
slice id it came from.

### 6.1 Which technique, from which part of the slice

| Slice element | Technique | Coverage item | Stopping criterion |
|---|---|---|---|
| A trigger's reaction chain (lookups 1–2) | **Scenario-based testing**: the chain is the scenario model, with fan-out as forks and main, extension and exception scenarios (CTAL-TA v4.0 §3.2.3) | Each path through the chain, including each reaction's *On failure* exit | Every path to the slice depth. Every `unhandled`/`?` failure gets a P1 case whose expected result is the open question |
| Another owner's trigger legal in a state the feature relies on (lookup 4) | **State transition across owners**: 0-switch on foreign cells, 1-switch (own transition → foreign trigger), round-trip coverage on lifecycle loops (CTAL-TA v4.0 §3.2.2) | Each (state, foreign trigger) cell, and each `—` and `?` cell in the rows the feature reaches, including schedule columns | All foreign-legal cells and all `—`/`?` cells in those rows. 1-switch for money and irreversible paths |
| An entity two features touch (lookup 6) | **CRUD testing, consistency half** (CTAL-TA v4.0 §3.2.1): functions combined over the entity's whole lifecycle, plus negatives such as reading before create or updating after delete | Each C/R/U/D cell in the entity's row | Every operation in the row. For P1 entities, the rigorous form: after each U, every R |
| A field with two or more writers, or a reader in another feature (lookup 6) | **Def-use across features** (Rapps & Weyuker, IEEE TSE 1985) | Each (writer, reader) pair, and each ordered (writer, writer) pair | All-uses on P1 fields, all-defs elsewhere |
| A decision table with rows from two or more features (lookup 5) | Decision table on the cross-feature overlap rows, plus BVA on thresholds the features share | Each overlap row and each shared threshold | All overlap rows, with 3-value BVA on shared thresholds |
| A `schedule` or `timeout` trigger in the slice | **Temporal** (experience-based checklist) | The job's column across every state. Boundary instants: cut-off minus one step, at, plus one step, the schedule's timezone, DST change, month end. A run executed twice. A late or missed run. A run during a user action on the same entity | Every state in the column, every boundary instant, and one idempotency case per job |
| A reaction in `after commit` mode, or a field with two or more writers | **Concurrency and delivery** (experience-based checklist) | Duplicate delivery, out-of-order delivery, a concurrent pair of writers, a retry after partial failure | One duplicate case per `at-least-once` reaction. One concurrent-pair case per pair of writers on a P1 field |
| An invariant (lookup 7) | **Invariant attack** | Each (invariant, threatening reaction) pair | Every pair. Pairs with `Enforced` = `no` or `?` are P1 |
| A conflict entry (lookup 8) | **Conflict boundary case** | Each boundary condition | All of them. A resolved conflict asserts its resolution. An open one gets a case whose expected result is the question |
| A cross-area journey in `system-overview.md` | Scenario-based, end to end, with simple loop coverage | Main, extension and exception scenarios | Every scenario on a journey the feature sits on |

### 6.2 Priority

- **P1:** money, data integrity, an irreversible effect, `Enforced` = `no`/`?`, an `unhandled`/`?`
  failure, an open conflict.
- **P2:** every other slice item.
- **P3:** experience-based extras beyond the checklist rows above.

### 6.3 Pruning

Pairs come from the slice and never from a cross product. A case asserts the effects of one reaction,
the behaviour of one owner. A scenario case chains reactions and attaches checks to the steps where
the next step depends on an effect.

### 6.4 Description (≤ 500 characters; the task verifies the count)

*Use when test cases must cover how a feature affects others — reaction chains, foreign events in
shared states, shared data (CRUD, def-use), schedules and time boundaries, duplicate or concurrent
delivery, invariants — from a basis with Connections. Triggers: "what else should we test
when X changes", "test the side effects of Y", "cross-feature test cases". Do NOT use for field-level
EP/BVA or single-feature rules (`test-design-techniques`) or formatting the suite (`test-case-writer`).*

## 7. The QA pipeline after this plan

### 7.1 The basis document's §8 — Connections

```markdown
## 8. Connections
**Built from:** KB slice @ <date> | code trace @ <sha> | docs only (thin) — <what was missing>

### Triggers and chains
| Trigger | Reaction (owner) | Effects | Emits → next | Mode | On failure | Source |
### States this feature relies on
| Entity · state | Other owners' triggers legal here | `—` / `?` cells | Source |
### Shared data
| Field / entity | Other writers | Other readers | Source |
### Invariants
| INV | Statement | Threatened here by | Enforced? | Source |
### Known interactions
| CONF | Pair | Boundary condition | Status |
### KB candidates
<edges found in code or docs that the KB lacks — handed to `business-analyst`>
```

- Every row cites a source: a KB id, `file:line #observed`, or a document line.
- An edge nobody can confirm is an open question.
- When `requirements-breakdown` runs standalone, it writes `Not built — single-feature basis`.
- The quality bar becomes "one to two pages, plus §8".

### 7.2 Validations, rebalanced (D8)

- §4 *Validations & restrictions* holds **business** validations only: cross-field, state-dependent,
  authorization and rule-based.
- Schema constraints from `required`, `minimum`/`maximum`, `minLength`/`maxLength`, `enum`, `pattern`
  and `format` go into the §6 data dictionary.
- The data dictionary gains an `On violation` column, and each `4xx` response fills it.
- `security` scopes still produce one validation row per operation-scope pair, because authorization
  is a rule.

Nothing is lost. EP and BVA still read every constraint from the dictionary.

### 7.3 `qa-test-case-designer`, five steps

| # | Step | Skills | Exit gate |
|---|---|---|---|
| 1 | Analyze the test basis | `requirements-breakdown` (§1–§7) | As today |
| 2 | **Map the connections** | `requirements-breakdown` (§8 + `references/connections.md`). Code mode adds `dev:doc-feature-trace` | Every trigger of the feature has its chain to the slice depth. Every state the feature relies on lists the foreign triggers legal there. Every shared field lists its other writers and readers. Every invariant on touched data is listed. Unknowns are open questions. KB candidates are listed. §8 conditions are ranked P1/P2/P3 |
| 3 | Design | `test-design-techniques`, then `cross-feature-test-design` when §8 has entries | The coverage-item list, with each cross-feature item carrying its slice id |
| 4 | Assemble the suite | `test-case-writer` | As today, plus layer grouping |
| 5 | Review & coverage | `test-case-writer`, `quality-metrics` | AC → TC **and** Connection → TC matrices, counts by layer, and the depth gate (§7.4) with no unresolved blocker or major |

**New input shapes:**

| Input | What happens |
|---|---|
| A feature in the code (name, path, endpoint, job) | **Code mode**: `dev:doc-feature-trace` over the feature's entry points of every kind, plus the Edges inventory one hop out (§8.1). Everything is `#observed` with `file:line`. Intent becomes `#assumption` plus a question. Defects go to `bug-report-writer`. Where code and docs disagree, it is a finding |
| A feature the KB models (`E<n>`, `AREA-nnn`, `EVT-nnn`) | The slice comes first. Code mode runs only for what the KB lacks, or where the KB's provenance commit is behind the code it cites |

### 7.4 The depth gate (Step 5)

| Condition | Severity |
|---|---|
| §8 has entries, and no case uses a technique from `cross-feature-test-design` | blocker |
| Field-layer cases outnumber all other layers combined | major |
| A slice item has neither a case nor a stated reason (out of scope, deferred) | major |
| An `unhandled`/`?` failure, a `?` cell, or an `Enforced` = `no`/`?` became neither a P1 case nor an open question | major |

Layers are counted from each case's technique:

| Layer | Techniques |
|---|---|
| field | EP or BVA on the data dictionary |
| rule | decision table, or BVA on a rule threshold |
| state | state transition within the feature's own lifecycle |
| data | CRUD consistency, def-use |
| interaction | chain, foreign-state, cross-feature overlap, conflict boundary |
| temporal | temporal |
| concurrency | concurrency and delivery |
| scenario | scenario-based or use-case journeys |
| experience | error guessing |

### 7.5 `test-case-writer`

- **Parameterized field cases.** Coverage items for one field in one direction (valid or invalid)
  become one case. Its data rows read `value → expected`, with one invalid value per row. A CSV export
  writes one line per row.
- **Layer groups.** Suites group cases under layer headings: Field validation · Rules · States · Data ·
  Interactions · Temporal · Concurrency · Scenarios. IDs do not change.
- **Async effects.** The expected result reads `within <budget>, <observable>`, and the observable is
  polled. The budget is one value, taken from the reaction's mode or from the NFR. A fixed wait is never
  used.
- **Temporal cases.** Setup names the *Environment needs*: a way to run `<schedule>` on demand, or to
  set the clock to `<instant>` in `<timezone>`. If the environment lacks that hook, the case is still
  written, and the need goes into the hand-off notes.
- **Concurrency cases.** Two actors act at the same instant, and the case has one expected outcome. If
  the spec does not decide the outcome, the expected result is the open question and the case is P1,
  which matches the no-`OR` rule.

### 7.6 KB candidates

QA never writes `docs/business-model/` (D10). Step 2 lists KB candidates in §8, and the output contract
names them for `business-analyst`. That agent's EXTEND mode accepts them as input and checks each one
against its source before folding it in.

### 7.7 `qa-test-planner`

- Step 1 reads the slice through the same reading guide.
- Its scenario-level inventory gets a row per slice item, tagged with its layer.
- Its "code repo only" scan also lists the jobs, consumers and other writers that touch the feature's
  entities. It still does not trace rules.

### 7.8 Automating the new case kinds — `time-and-concurrency-testing` (A1–A3)

There is one new skill per stack: `qa/<stack>/skills/time-and-concurrency-testing/SKILL.md`, registered
as `time-and-concurrency-testing` in that stack's plugin only. It automates the case forms from §7.5.
The patterns are the same in every stack; the APIs differ:

| Case kind | Pattern | Never |
|---|---|---|
| Async effect: `within <budget>, <observable>` | The stack's existing poller with the case's budget as its timeout. This skill only points to it | A fixed sleep |
| Scheduled job or timeout trigger | Run the job on demand through the first seam that exists. **(1) In-process host** (the same one `feature-flag-testing` uses to pin flags): call the job's handler, or the scheduler's own trigger API. **(2) Deployed environment**: a trigger the environment exposes for tests, such as an admin endpoint enabled only in test environments, the scheduler's admin API, or `kubectl create job --from=cronjob/<name>`. **(3) Neither exists**: the case is reported as deferred with the missing hook named, the hook request goes to `be-<stack>` as a product change, and no skipped or commented-out test is committed | Waiting for the real schedule, or changing the production schedule |
| Clock boundary: cut-off ±1 step, the schedule's timezone, DST change, month end | **In-process**: replace the clock the application injects, and seed data relative to the controlled "now". **Deployed**: a test clock endpoint if the environment has one. Otherwise, seed data relative to the server's real "now" and make the boundary step larger than clock skew plus request latency, saying so in the test name. If the application reads the system clock directly, the clock cannot be controlled: defer the case and hand the clock seam to `be-<stack>` | The runner's fake timers against a separately running server, because they do not move another process's clock and they break the client's own timeouts. Reading the machine clock inside the assertion |
| Concurrent requests | Release N requests together behind a start barrier, then assert the **invariant** after all of them settle: exactly one success, the rest a single named refusal, and the INV holding (a DB verification query). Repeat with the runner's own repeat feature | Asserting which request wins. An `OR`. A `for` loop driving assertions |
| Duplicate or out-of-order delivery, and idempotency | Publish the same business message twice through the project's `messaging-testing` reference. Replay a webhook with the same delivery id. Resend a request with the same idempotency key. Assert the effect happened once (DB verification). For out-of-order delivery, publish two events in reverse order and assert the declared outcome | Letting broker-level deduplication hide the duplicate. SQS FIFO deduplication, Service Bus duplicate detection and Kafka's idempotent producer all do this, so use a new broker message id with the same business id, ensuring the consumer's idempotency is what gets tested |
| Invariant check after a sequence | A `db-testing` verification query asserting the INV's statement | — |

**Agent wiring (`qa-api-<stack>`):**

- Step 3's deep-verification list gains "schedules, clock, concurrency, duplicate delivery →
  `time-and-concurrency-testing`". It applies when a case's technique is temporal or concurrency, or
  when its Setup names *Environment needs*.
- Mode B maps each case's *Environment needs* to a seam, or to a deferral with the missing hook named.

**Review (`api-test-author/review`) gains three checks:**

| Check | Severity |
|---|---|
| A job test waits for the real schedule | blocker |
| A boundary test runs without a controlled clock or a stated skew margin | major |
| A race test has no barrier or no repeat; a duplicate test is defeated by broker deduplication | major |

**Description template (each stack fills its own runtime words; ≤ 500 characters, counted):**

*Use when a `<Node 24 / TypeScript | Java 21 / TestNG | .NET 10 (8–9) / NUnit>` API suite must run a
scheduled job on demand, control the clock at a time boundary, fire concurrent requests, or deliver a
message or webhook twice — the temporal, concurrency and idempotency cases of a cross-feature suite.
Triggers: "run the nightly job in a test", "freeze the clock at the cut-off", "two requests at once",
"message delivered twice". Do NOT use for broker plumbing (`messaging-testing`) or fault injection
(`failure-injection-testing`).*

**Version-aware:** each task confirms every API it teaches against current documentation before
writing it, for the project's detected major and the down-level versions the stack supports. Each API
is taught only for the versions where it exists, with the down-level form beside it. Examples are the
stack's clock abstraction (where the platform has one), its scheduler trigger APIs, its repeat
annotation or option, and its barrier primitive.

## 8. The code route — trace edges and the documenters

### 8.1 `feature-trace`, seventh inventory: Edges

```markdown
### Edges
| # | Entry point | Kind | Reads | Writes | Emits | Reacted to by (one hop out) | Mode | On failure | Evidence |
```

- Stop 7 (persistence) records reads and writes as `Entity.field`.
- Stop 9 becomes "Events emitted — and who reacts". For every emitted event, message, outbox row or
  notification, search for its consumers and record each one with `file:line` and its owning area.
- For every written field that another area may read, search for the readers, including the queries of
  scheduled jobs.
- A negative claim names its search. A mode or guarantee the code does not show is `?`.
- The self-check gains three lines, one each for reactors, readers and mode.
- "six inventories" becomes "seven" everywhere it is cited: the skill and its description,
  `be-documenter.md:121`, `be-feature-documenter.md:33` and `:57`, and the catalog.

### 8.2 `trace-recipes.md` — following a seam

A section per stack (.NET, Java, Node) covers three things:

- How to find the consumers of an event type: in-process notification handlers, broker consumers,
  framework event listeners, queue processors.
- How to find the readers of a field, including job queries.
- How to tell the reaction's mode from the code: a handler inside the request, an after-commit
  listener, a broker consumer or an outbox. The recipe also gives the delivery guarantee each one
  implies. The recipes reuse the stack idioms the file already lists for scheduled work and consumers.

### 8.3 "How it connects" in area and feature documents

This is an optional section after *How it works*, written in business words like the rest of the body.
It has three short lists:

- **Starts from:** which other areas' actions or schedules start this one.
- **Sets off:** what this area causes elsewhere.
- **Shares:** which data other areas also change or read.

Evidence rows in the closing table cite the `EVT-` and `RX-` ids. The section is dropped when nothing
crosses the area boundary, and the negative search becomes an evidence row. `be-feature-documenter`
writes it from the one-hop Edges, because its document is the only place that feature's connections land.

### 8.4 `be-documenter` writes the dependency map

- Step 2 extracts seven inventories.
- Step 3 path-loads `business-analysis/skills/ba-dependency-map` and writes `events.md`,
  `shared-data.md` and `invariants.md` from the Edges inventories. Every row is `#observed` or
  `#inferred`, with the provenance stamp. It never writes `#confirmed`.
- Step 5 (Consolidate) runs the map's checks: unconsumed events, orphans, CRUD completeness and
  unenforced invariants. Each result becomes an open question or a finding.
- This runs on every FULL run. The edges are already read at stops 8–9, so writing them down costs
  little.

## 9. Worked example — "a member cancels a booking", before and after

The toy is the inherited **workshop-booking** codebase from
`backend/_shared/business-documentation/references/example-area.md`. That file is AREA-004 *Session
credits & charges*: the Basic plan is 8 credits and £6.00 per overage credit; tiers are Standard 1,
Workshop 2, Masterclass 3; the cut-off is 24 h; staff cancellations always return credits; posting runs
on the 1st at 00:00. The other areas are AREA-002 Scheduling and AREA-003 Bookings.

**K1 writes this map into its golden example, and Q1 writes the QA example against it. Both use exactly
these ids, because the gate cross-checks them.**

### 9.1 The map

**Triggers**

| ID | Trigger | Kind | Fired by | Owner |
|---|---|---|---|---|
| EVT-001 | Member books a seat | command | Member | AREA-003 Bookings |
| EVT-002 | Member cancels a booking | command | Member | AREA-003 Bookings |
| EVT-003 | Staff cancels a booking | command | Staff | AREA-003 Bookings |
| EVT-004 | Staff cancels a session | command | Staff | AREA-002 Scheduling |
| EVT-005 | Booking confirmed | event | RX-001 | AREA-003 Bookings |
| EVT-006 | Booking cancelled (by member/staff, hours of notice) | event | RX-002, RX-003, RX-005 | AREA-003 Bookings |
| EVT-007 | Monthly posting | schedule | 1st of the month 00:00, timezone `?` | AREA-004 Credits & charges |

**Reactions**

| ID | When | Guard | Owner | Effects | Emits | Mode | On failure |
|---|---|---|---|---|---|---|---|
| RX-001 | EVT-001 | seats taken < capacity | AREA-003 | ENT-002 — → Confirmed; Session.seats_taken +1 | EVT-005 | in request | rolls back ("session full") |
| RX-002 | EVT-002 | session not started | AREA-003 | ENT-002 Confirmed → Cancelled; Session.seats_taken −1 | EVT-006 | in request | rolls back |
| RX-003 | EVT-003 | — | AREA-003 | ENT-002 Confirmed → Cancelled (by staff); Session.seats_taken −1 | EVT-006 | in request | rolls back |
| RX-004 | EVT-005 | — | AREA-004 | DEC-002; Member.credits_used +spent; creates Accrued charge (ENT-003 — → Accrued) when short | — | after commit, at-least-once | retried 3× then dead-letter — the booking stays confirmed and unpriced |
| RX-005 | EVT-004 | — | AREA-002 | ENT-001 Scheduled → Cancelled; each Confirmed booking ENT-002 Confirmed → Cancelled (by staff) | EVT-006 per booking | in request | rolls back |
| RX-006 | EVT-006 | — | AREA-004 | DEC-003; Member.credits_used −returned; ENT-003 Accrued → Removed | — | after commit, at-least-once | ? |
| RX-007 | EVT-007 | every member | AREA-004 | ENT-003 Accrued → Posted; creates Charge; Member.credits_used := 0 | — | scheduled | ? (a re-run's behaviour is unknown) |

**DEC-003 — credit return on cancellation** (hit policy U):

| Rule | Cancelled by | Notice | Credits returned and the booking's accrual removed |
|---|---|---|---|
| R1 | member | ≥ 24 h | yes |
| R2 | member | < 24 h | no |
| R3 | staff | − | yes |

**ENT-003 — accrued charge** (grid columns are trigger ids):

| State \ Trigger | EVT-005 (via RX-004) | EVT-006 | EVT-007 |
|---|---|---|---|
| (none) | Accrued (AREA-004), when short | — | — |
| Accrued | — | Removed (AREA-004), when DEC-003 returns | Posted (AREA-004) |
| Posted | — | **?** | — |
| Removed | — | — | — |

**Shared data**

| Entity / field | Create | Read | Update / written by | Delete |
|---|---|---|---|---|
| Booking (ENT-002) | RX-001 | RX-001 (capacity), RX-004, RX-005, RX-006 | RX-002, RX-003, RX-005 | none — by decision: cancelled is a state |
| Accrued charge (ENT-003) | RX-004 | RX-007, screen: my balance | RX-006 (removed), RX-007 (posted) | none |
| Member.credits_used | — | DEC-002 in RX-004, screen: my balance | RX-004 (+), RX-006 (−), RX-007 (:= 0) | — |
| Session.seats_taken | — | RX-001 guard | RX-001 (+1), RX-002 / RX-003 (−1) | — |

**Invariants**

| ID | Invariant | Threatened by | Enforced |
|---|---|---|---|
| INV-001 | Seats taken never exceed capacity | RX-001 | RX-001: yes (conditional update) |
| INV-002 | Credits used is never negative | RX-006, RX-007 | RX-006: **no** — a booking priced last month and cancelled after RX-007's reset drives it below 0 |
| INV-003 | An accrual is charged at most once, and never after its booking was refunded | RX-006, RX-007 | RX-006: **?** (Posted × EVT-006) · RX-007: **?** (re-run) |
| INV-004 | A booking's credits are spent exactly once and returned at most once | RX-004, RX-006 | **?** — both are at-least-once, and no idempotency key was found |

### 9.2 Before — what today's pipeline produces

The input is `DELETE /bookings/{id}` plus the story. Today's pipeline produces seven cases:

1. Id missing.
2. Id malformed.
3. Id unknown.
4. Another member's booking.
5. Already cancelled.
6. Happy path.
7. Possibly one late cancellation.

None of them looks at credits, at the freed seat, at a staff session cancellation, or at the monthly
job. Every AC is "covered".

### 9.3 After — what the slice for EVT-002 produces

| # | Case | Technique (layer) | From the slice |
|---|---|---|---|
| 1 | Ana cancels *Glazing workshop* on 15 Mar 09:00, 25 h ahead: 2 credits come back, credits used 8 → 6, and the £6.00 accrued on 11 Mar stays | scenario (interaction) + DEC-003 R1 | RX-002 → EVT-006 → RX-006 |
| 2–4 | Cut-off for a session starting 16 Mar 10:00. Cancelling at 15 Mar 10:00:00 (24 h 00 m 00 s) returns the credits. Cancelling at 15 Mar 10:00:01 (23 h 59 m 59 s) forfeits them. Cancelling at 15 Mar 09:59:59 returns them. The 1 s step is `#assumption` | BVA 3-value (temporal) | DEC-003 threshold |
| 5 | Staff cancel a booking 10 h ahead: the credits come back | decision table R3 (rule) | DEC-003 |
| 6 | A full session (6/6): Ana cancels, then Ben books the freed seat and is confirmed | def-use (data) | Session.seats_taken, RX-002 → RX-001 |
| 7 | Staff cancel *Wheel basics II* (Standard) 10 h ahead, with Ana, Ben and Cara booked: each gets 1 credit back | scenario fan-out (interaction) | RX-005 → EVT-006 ×3 → RX-006 |
| 8 | Ana, at credits used 7, books *Raku masterclass II* (3 credits, 3 Apr 14:00) on 30 Mar: 1 credit is spent and 2 × £6.00 = £12.00 is accrued. Posting on 1 Apr charges £6.00 + £12.00 = £18.00 and resets credits used to 0. Ana cancels on 1 Apr 10:00, 52 h ahead. **Expected: open question.** Credits used would become −1, and the £12.00 has already been charged | foreign state + invariant attack (interaction), P1 | ENT-003 Posted × EVT-006 = `?`; INV-002, INV-003 |
| 9 | EVT-006 for case 1 is delivered twice: credits used ends at 6, not 4 | concurrency, P1 | RX-006 at-least-once; INV-004 |
| 10 | EVT-005 is delivered twice: the booking is priced once | concurrency, P1 | RX-004 at-least-once; INV-004 |
| 11 | A cancellation lands at 1 Apr 00:00:00 while posting runs. **Expected: open question.** Is the accrual removed or charged? | concurrency (race with a schedule), P1 | RX-006 × RX-007 on Member.credits_used |
| 12 | Ana late-cancels *Raku masterclass* on 20 Mar 20:00, 18 h ahead, and forfeits 3 credits. Staff cancel the session on 21 Mar 09:00. **Expected: open question.** She forfeited credits for a session that never ran | foreign state (interaction) | Booking Cancelled × EVT-004; RX-005 guard |
| 13 | Posting runs twice on 1 Apr: no second charge | temporal (idempotency), P1 | RX-007 on failure `?`; INV-003 |
| 14–16 | Unknown booking → not found. Another member's booking → refused. Already cancelled → refused (Cancelled × EVT-002 = `—`). Session already started → refused (RX-002 guard) | rule / state | V rows and grid |

The three open questions (cases 8, 11 and 12) are the most valuable output. They are business decisions
nobody made, and no field-level technique reaches them. This list is the yardstick for the golden
examples and for H1.

## 10. Size rules

`tools/token-audit.py` budgets: a skill description ≤ 500 characters, an agent description ≤ 650, a
SKILL.md body ≤ 16,000, an agent file ≤ 14,000. The 2026-10-11 baseline has 89 SKILL.md body
violations and 53 agent-file violations.

- A new SKILL.md stays under 16,000 characters. Worked examples go to `references/`.
- A file under budget today stays under budget. `requirements-breakdown` is close to the limit, so it
  moves its Example to `references/example-promo-codes.md` to make room for §8.
- A file already over budget may grow only by the net amount its task bullet allows. Where the bullet
  says so, the growth is paid for by moving the file's Example to `references/`. Those files are
  `test-case-writer`, `test-design-techniques`, `qa-test-case-designer`, `qa-test-planner`,
  `business-analyst`, `business-documentation`, `be-documenter`, `be-feature-documenter`, and the three
  `qa-api-<stack>` agents, which may each grow by ≤ 800 characters net.
- Each `time-and-concurrency-testing` SKILL.md stays under 16,000 characters. Per-broker or
  per-scheduler detail that would push it over goes to the skill's `references/`.

## 11. The gate (A3 only)

Run from the repo root, in this order. Fix whatever fails, because a failure may belong to any task above A3.

1. `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` exits 0.
2. `claude plugin validate .` ends with `✔ Validation passed`.
3. `python3 tools/plugin-surface-check.py` prints `OK`.
4. `python3 tools/token-audit.py --violations-only` reports 0 skill-description and 0
   agent-description violations, **≤ 89** SKILL.md body violations and **≤ 53** agent-file violations.
   None of the five new SKILL.md files (`dependency-map`, `cross-feature-test-design`, and the three
   `time-and-concurrency-testing`) may appear in its list.
5. `python3 tools/qa-version-check.py` prints `OK`.
6. **Id cross-check.** A scratchpad script, not committed, checks that every `EVT-`, `RX-`, `INV-`,
   `ENT-` and `DEC-` id in `qa/manual/cross-feature-test-design/references/*.md` and
   `qa/manual/requirements-breakdown/references/*.md` exists in
   `business-analysis/skills/ba-dependency-map/references/example-dependency-map.md` or in
   `backend/_shared/business-documentation/references/example-area.md`. Zero missing.
7. **Arithmetic.** Recompute every number in the QA golden example against §9 and Ana's month in
   `example-area.md`, and record the result in A3's As built.
8. **Format sweep.** Outside `docs/plans/implemented/`:
   - `grep -rn "six inventories"` has zero matches.
   - `events.md`, `shared-data.md`, `invariants.md`, `EVT-`, `RX-` and `INV-` each appear in both
     `business-analysis/skills/ba-project-memory/SKILL.md` and
     `qa/manual/requirements-breakdown/references/connections.md`.
   - Every `Step <n>` inside `qa/manual/agents/qa-test-case-designer.md`, and in other files that cite
     it, matches the five-step table.
   - `time-and-concurrency-testing` appears in Step 3 of all three `qa-api-<stack>` agents and in all
     three `api-test-author/review` skills.
   - Each `time-and-concurrency-testing` folder is registered in its own stack's plugin and in no other.

The new stack skills' code samples are not compiled by this gate. Each task checks them against
current documentation. Whether they run is part of H1, and the Status line says so until H1 lands.

## 12. Decisions

**D1 — The connection layer extends the BA knowledge base. QA never gets a parallel model.**

| Option | Verdict | Why |
|---|---|---|
| A QA-owned `docs/test-model/` | rejected | It would duplicate the grids and decision tables, and two truths drift |
| Connections only inside each test basis | rejected | They would be re-derived on every run, and nothing could be looked up |
| Extend `docs/business-model/` | **chosen** | The grids, decisions, conflicts and feature ids are already there. The map joins them, and `be-documenter` and `business-analyst` already write the KB |

Cost: QA reads a format that a plugin from another category owns. The coupling is visible on both
sides. `dependency-map`'s handoffs name `requirements-breakdown/references/connections.md` as a
consumer, a format change updates both in one commit, and the gate's sweep (step 8) checks that the two
agree.

**D2 — Three artifacts, one owning skill.**

| Option | Verdict | Why |
|---|---|---|
| Grow `interaction-map.md` | rejected | That file records conflicts and their resolutions. Normal, working dependencies are not conflicts, and most of them never become one |
| One `dependency-map.md` | rejected | Large systems pass the KB's 2,000-word split rule quickly. The three tables also answer three different questions: what happens next, who else touches this, what must hold |
| Three files with one skill | **chosen** | One procedure produces them together from the same reading |
| Three skills | rejected | Three skills would carry one procedure split across them |

Cost: three more files to keep current, and `INDEX.md` gains a Dependencies section.

**D3 — One trigger catalog, and the state grids' columns are its ids.** This joins the transition tables
to the connection graph. Cost: existing grids keep free-text headers until the map is first built or
refreshed. Nothing is migrated in bulk.

**D4 — The lookup is a grep procedure over ids, not generated views or a tool.** Per-feature view files
drift from their source. A query script is unearned while ids are greppable. Revisit when a real KB
passes about 200 reactions.

**D5 — Analysis owns the connection map, and design owns the cases.** `requirements-breakdown` builds §8
(ISTQB test analysis: what to test), and `cross-feature-test-design` turns it into coverage items (test
design: how). This keeps the analysis/design split the library already uses. Cost: §8's shape and its
reading guide live in one skill while the techniques that consume it live in another.

**D6 — The cross-feature techniques are a new skill.** It is grounded in ISTQB CTAL-TA v4.0 §3.2
(2025-05-02):

- **CRUD testing**: static completeness, then dynamic consistency. Coverage is operations executed
  divided by operations in the matrix, and the rigorous form is "after each U, every R".
- **State transition**: N-switch and round-trip coverage.
- **Scenario-based testing**: activity diagrams with forks and swimlanes; main, extension and exception
  scenarios; simple loop coverage.

The def-use row follows Rapps & Weyuker (IEEE TSE 1985, all-defs and all-uses). The temporal and
concurrency rows are experience-based checklists keyed to the catalog's *Mode* column, and the skill
says so. It is not grown into `test-design-techniques`, which is already over its budget at 18,135
characters.

**D7 — QA gets a code route by loading `dev:doc-feature-trace`.** The alternative was to send the user
to `/dev:document-feature` first. `dev` is already a dependency of every `qa-*` plugin, and the trace is
the library's one procedure for reading code. Cost: a code-derived basis is `#observed`, which shows
what *is* rather than what *should be*. A disagreement with the docs is a finding, and unrecoverable
intent is a question. Exploration mode already accepts the same trade.

**D8 — Field validations are compressed, not cut.** Schema constraints go to the data dictionary, and
validation rows hold business validations only. Each field gets one parameterized case per direction.
Cost: this breaks the basis and suite format. Existing documents stay valid, and an EXTEND run upgrades
only the parts it touches. Q1's and Q2's commit messages say `BREAKING (format)`.

**D9 — Depth is gated (§7.4).** A count is not a quality measure, but a suite with zero interaction
cases against a non-empty §8 is wrong by construction, and the gate makes that impossible to hand over.

**D10 — The fence holds both ways.** `business-analyst` records edges and never test cases. QA never
writes the KB, and it hands KB candidates to `business-analyst` instead.

**D11 — The new case kinds are automated in this plan, with one `time-and-concurrency-testing` skill per
stack** (O1, answered 2026-10-11).

| Option | Verdict | Why |
|---|---|---|
| A follow-up plan 006 | rejected by the user | Designed cases with no way to automate them would sit unrun |
| Spread the patterns over `messaging-testing`, `api-test-author` and `db-testing` | rejected | Four files per stack would each carry a fragment, and the scheduler and clock seams have no home among them |
| Two skills per stack (time, concurrency) | rejected | They are written for the same suite and share the in-process/deployed seam split. Six skills would carry one procedure split across them |
| One skill per stack, registered only in that stack's plugin | **chosen** | One place per stack, bundled within the `qa` category |

Cost: three more skills to keep version-current, and the plan's gate moves from Q2 to A3.

**D12 — The slice goes two hops past the feature by default, and deeper where money or an irreversible
effect is involved.** Deeper defaults widen every suite. Shallower ones miss a fan-out, as in case 7.

**D13 — Seams are tried in a fixed order, and a missing hook is a product change, never a workaround.**
The order is an in-process host, then a hook the deployed environment exposes, then deferral. QA agents
do not change product code. A job that cannot be triggered, or a clock that cannot be controlled,
becomes a named request to `be-<stack>`. A skipped test, a long sleep or a test that waits for the real
schedule would look like coverage and give none.

**D14 — Q1's golden example departs from §9.3 in four places (2026-10-11).**

| # | §9.3 reading | As built | Why |
|---|---|---|---|
| 1 | Cases 2–4 are "BVA 3-value (temporal)" | Layer is **rule**: BVA on DEC-003's threshold | §7.4 counts BVA on a rule threshold as the rule layer; the temporal technique is for a `schedule`/`timeout` trigger, and the cut-off is neither |
| 2 | Case 5 is "staff cancel 10 h ahead: the credits come back" | Staff cancel Ana's overage-priced *Sculpture masterclass* booking: 2 credits back (7 → 5) **and** the £6.00 accrual removed | The ENT-003 cell Accrued × EVT-006 → Removed (R1/R3's "accrual removed") had no case in the sixteen |
| 3 | Cases 14–16 list four refusals | Case 14 unknown id, 15 another member's booking, 16 a parameterized pair (already cancelled; session started), one expectation per row | Keeps sixteen cases and one expected condition per row; status codes are `#assumption` |
| 4 | §6.1: an `unhandled`/`?` failure always gets a P1 case | The example defers RX-006's failure (needs a fault-injection seam) and the other timezone-dependent boundary instants, each with a stated reason and an open question (OQ-1, OQ-2); the skill allows "a stated deferral naming the question and the missing hook" | The sixteen cases of §9.3 have none for either, and §7.4's gate accepts an open question |

Cost: the example and the plan's §9.3 no longer match line for line. §9.3 stays as the yardstick for H1; the example is what the skill teaches.

**D15 — Q2 departs from §7.3/§7.5 in two places (2026-10-11).**

| # | Plan said | Built | Why |
|---|---|---|---|
| 1 | §7.5 lists five forms | A sixth, *Chains*: a case that chains reactions attaches a check to each step the next depends on | §6.3 already requires it, and the writer is where cases are formatted |
| 2 | *Temporal cases*: "Setup names the *Environment needs*" | "the Setup or the case's Preconditions name them" | Q1's golden example puts the duplicate-delivery need in the case's Preconditions column |

Cost: the designer is 30 characters over its +2,000 bullet.

## Answered questions (2026-10-11)

**O1 — Should the stack agents automate the new case kinds (on-demand job runs, clock control,
duplicate delivery, concurrent requests) in this plan or in a follow-up? In this plan.** Tasks A1–A3
add `time-and-concurrency-testing` per stack (§7.8, D11, D13).

No question is open.

## 13. Tasks

**The cost, accepted and stated once:** intermediate commits are ungated, so the tree is **not** known
to pass `claude plugin validate` or the checkers at every task boundary, and the plan cannot be stopped
halfway and trusted. A3 runs §11 once for everything.

### K1 — business-analysis: the dependency map, its golden example, and the KB contract

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** The KB has a connection layer. `business-analysis:dependency-map` defines `events.md`,
`shared-data.md` and `invariants.md` with a golden workshop-booking example. `knowledge-base` carries
their ids and the §5 feature slice. `state-grid`, `process-flow`, `conflict-check` and the
`business-analyst` agent all read and write through the new layer, and the skill is registered in the
`business-analysis` plugin.
**Depends on:** —
**Budget:** ~95k:
- CLAUDE.md, the global rules and the system prompt: ~22k
- this plan's §3–§5, §9, §10 and D1–D4, D10, D12: ~14k
- the five files it edits (`ba-project-memory` 3.3k, `ba-entity-state-grid` 2k,
  `ba-process-flow-diagram` 2.7k, `ba-feature-conflict-check` 2.7k, `business-analyst.md` 5.3k): ~16k
- `ba-decision-table` as the skill pattern: 2.5k
- `example-area.md` for the toy domain: 6k
- the `business-analysis` marketplace entry: 1k
- writes (the skill ~4.5k, the example ~4k, the edits ~8k): ~17k
- reasoning: ~15k

**Gate: none** — this plan gates once, in A3. Do not run `claude plugin validate`,
`tools/plugin-surface-check.py`, `tools/token-audit.py` or any check script.

- **New skill.** `business-analysis/skills/ba-dependency-map/SKILL.md` with `name: dependency-map`
  and the §4.5 description; count it and confirm ≤ 500 characters. Use the CONTRIBUTING outline:
  When to use · When NOT to use · Contract with the KB · Procedure (§4.4) · the three file formats
  (§4.1–§4.3, normative) · the checks (unconsumed event, orphan reaction, cycle, CRUD completeness,
  unenforced invariant), each finding carrying a boundary condition and handed to `conflict-check` ·
  Quality bar · Anti-example · Handoffs. The Handoffs name the QA consumer,
  `qa/manual/requirements-breakdown/references/connections.md`, and state that a format change updates
  it in the same commit. Stay under 16,000 characters.
- **Golden example.** `business-analysis/skills/ba-dependency-map/references/example-dependency-map.md`
  is §9.1 as the three KB files would hold it, with the header and provenance lines, plus the ENT-003
  grid with trigger-id columns and DEC-003. Use exactly §9.1's ids, effects and enforcement values,
  because Q1's QA example cites them and the gate cross-checks them. Domain facts must match
  `example-area.md`. Illustrative citations follow that file's evidence style
  (`BookingCancelledHandler.cs`, `OverageChargeJob.cs`, `CreditPricingService.cs`).
- **`ba-project-memory/SKILL.md` (`knowledge-base`):**
  - The layout gains the three files, each with its owner.
  - The id list gains `EVT-`, `RX-` and `INV-`.
  - The INDEX format gains a `## Dependencies` section.
  - A new section, **Feature slice**, carries §5's table and the depth rule.
  - The handoffs gain `dependency-map`.
  - It stays under 16,000 characters.
- **`ba-entity-state-grid/SKILL.md`:** in procedure step 2, once `events.md` exists, each event is a
  trigger and the column header carries its `EVT-` id. Grids built earlier keep free-text headers until
  the map is built or refreshed (D3). Show the id form in the file-format example. Add the
  `dependency-map` handoff.
- **`ba-process-flow-diagram/SKILL.md`:** in event-timeline step 3, the answers to "who else reacts"
  are recorded as reactions in `events.md` through `dependency-map`. Add the handoff.
- **`ba-feature-conflict-check/SKILL.md`:**
  - §1: invariant and resource claims are persisted to `invariants.md` through `dependency-map`.
  - §2: when the map exists, the pair list is the feature slice, plus anything the slice misses.
  - §4: "Boundary conditions double as BVA seeds for QA" becomes "…double as test seeds for QA —
    BVA, and the cross-feature cases of `qa-<stack>:cross-feature-test-design`". Change the matching
    handoff line too.
- **`business-analyst.md`** (already over budget; net growth ≤ 1,500 characters):
  - The Step 3 selection matrix gains *what else reacts, who else uses this data, what must always
    hold? → dependency map*, and the Step 3 skill list gains it.
  - The orientation inventory's id ranges gain `EVT-`, `RX-` and `INV-`.
  - The AUDIT open surface gains unconsumed events, `unhandled`/`?` failures, `?` modes, unenforced
    invariants and CRUD anomalies.
  - EXTEND accepts **KB candidates** handed over by `qa-test-case-designer` and checks each one against
    its source before folding it in.
  - The Related agents entry for `qa-test-case-designer` says it reads the slice and sends candidates back.
- **Marketplace.** Add `./business-analysis/skills/ba-dependency-map` to the `business-analysis`
  plugin's `skills`, after `ba-decision-table`. Add "a dependency map (triggers, reactions, shared data,
  invariants)" to that plugin's description.
- **Not in K1:** the code route (D1), anything under `qa/` (Q1, Q2, A1–A3), README and the catalog (A3).

**As built (2026-10-11):** as planned, with no divergence and no §9.1 id changed.
- `business-analysis/skills/ba-dependency-map/SKILL.md` (`name: dependency-map`, ~9.8k bytes; description 490 characters, counted by script) and `references/example-dependency-map.md` (EVT-001…007, RX-001…007, INV-001…004, ENT-003 grid with trigger-id columns, DEC-003; header and `Derived from: code by be-documenter @ a3f9c21` lines).
- `ba-project-memory/SKILL.md`: layout, ids, INDEX `## Dependencies`, `## Feature slice` (§5 table and depth rule), handoff; 14,979 bytes.
- `ba-entity-state-grid`, `ba-process-flow-diagram`, `ba-feature-conflict-check`: edits per the bullets; the state-grid file-format example now shows `EVT-` column headers.
- `business-analyst.md`: net +464 characters (19,538 → 20,002), paid partly by two trims.
- `.claude-plugin/marketplace.json`: skill registered after `ba-decision-table`; plugin description names the dependency map.
- Unverified: no checker was run.

### D1 — dev: trace edges, "How it connects", and the documenters write the dependency map

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `dev:doc-feature-trace` produces a seventh inventory, **Edges**, which follows every
emitted event and every shared field one hop outside the area with `file:line` evidence. Area and
feature documents carry an optional **How it connects** section. `be-documenter` writes `events.md`,
`shared-data.md` and `invariants.md` from the edges.
**Depends on:** K1, for the three file formats and the ids.
**Budget:** ~100k:
- CLAUDE.md, the global rules and the system prompt: ~22k
- this plan's §4, §8, §9 and D7: ~12k
- the `dependency-map` skill and example as K1 landed them: ~9k
- `feature-trace` 3.5k and `trace-recipes.md` ~4k
- `business-documentation` 5.6k and `example-area.md` 6k
- `be-documenter.md` 6k and `be-feature-documenter.md` 4k
- the consumers/jobs part of `codebase-survey`: ~1k
- writes: ~16k
- reasoning: ~12k

**Gate: none** — this plan gates once, in A3. Do not run `claude plugin validate`, the checkers,
`tools/token-audit.py` or any script.

- **`backend/_shared/feature-trace/SKILL.md`:**
  - Stop 7 records reads and writes as `Entity.field`.
  - Stop 9 becomes "Events emitted — and who reacts", with §8.1's one-hop rule.
  - "The six inventories" becomes "The seven inventories", with **7. Edges** in §8.1's columns.
  - The trace record shape gains `### Edges`.
  - The self-check gains three items: every emitted event has its reactors or a named negative search;
    every written field another area reads is listed; mode and failure behaviour are stated or `?`.
  - The description says "seven"; keep it ≤ 500 characters.
  - The Handoffs gain `business-analysis:dependency-map`, because Edges become `events.md`,
    `shared-data.md` and `invariants.md`.
- **`backend/_shared/feature-trace/references/trace-recipes.md`:** a "Following a seam" section per
  stack, as §8.2 describes.
- **`backend/_shared/business-documentation/SKILL.md`** (already over budget; net ≤ 1,500 characters):
  - The area shape gains the optional `## How it connects`, after *How it works*, as §8.3 describes.
  - The output table gains a row: the three map files are owned by `business-analysis:dependency-map`,
    so they are "not yours" and are produced in Step 3.
  - The self-check gains "How it connects is present, or its negative search is an evidence row".
- **`example-area.md`:** add *How it connects* for AREA-004, from §9.1.
  - **Starts from:** a booking confirmed or cancelled in Bookings (AREA-003), and a staff session
    cancellation in Scheduling (AREA-002), which arrives as one cancellation per booking.
  - **Sets off:** nothing outside the area.
  - **Shares:** it reads bookings owned by Bookings.
  - Add the evidence rows citing `EVT-`/`RX-` ids. Keep the tone and the language discipline of the
    rest of the file.
- **`backend/_shared/agents/be-documenter.md`** (already over budget; net ≤ 1,500 characters):
  - Step 2 says seven inventories (line 121).
  - Step 3 path-loads `business-analysis/skills/ba-dependency-map` and writes the three files: rows
    `#observed`/`#inferred`, the provenance stamp, never `#confirmed`.
  - Step 5 runs the map's checks.
  - The report gains counts of triggers, reactions and invariants, and of map findings.
- **`backend/_shared/agents/be-feature-documenter.md`:** "six" becomes "seven" (lines 33 and 57). The
  document includes *How it connects* from the one-hop Edges. It still writes no KB.
- **Not in D1:** anything under `qa/`; editing `business-analysis/` (read only); the audit lane
  (`dev:audit-feature` could use Edges later, but not here); README and the catalog (A3).

**As built (2026-10-11):** as planned, with no divergence; Q1's and Q2's prompts needed no rewrite.
- `backend/_shared/feature-trace/SKILL.md`: stop 7 and stop 9 reworded, `### 7. Edges` (§8.1's columns, one example row, the `?`-unless-visible rule and the named-negative-search rule), `### Edges` in the record shape, self-check items 8–10, handoff to `business-analysis:dependency-map`; description 492 characters (counted by hand).
- `references/trace-recipes.md`: new `## Part 3b — Following a seam`: a mode table (what the code shows → mode → guarantee, `?` unless a retry, ack or key is visible) and per-stack search blocks for .NET, Java and Node.
- `business-documentation/SKILL.md`: `## How it connects` in the shape and as a section, an output-table row for the three map files, self-check item 12; net +782 characters.
- `example-area.md`: `## How it connects` for AREA-004 and six evidence rows citing EVT-004/005/006 and RX-004/005/006/007, INV-004; no existing text or number changed.
- `be-documenter.md`: seven inventories (Step 2), Step 3 writes the three files, Step 5 runs the map's checks, report counts in both shapes; net +582 characters. `be-feature-documenter.md`: seven (lines 33, 57), `## How it connects` in the document contract, still no KB writes.
- Unverified: no checker was run, and the sizes are counted by hand; the Part 3b search patterns were not run against a real codebase (H1).

### Q1 — qa/manual: the Connections basis section and the cross-feature test-design skill

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `requirements-breakdown` writes a §8 **Connections** section from a KB slice, a code
trace or the docs, and keeps schema constraints in the data dictionary.
`qa-<stack>:cross-feature-test-design` exists with §6's techniques and a golden example built on §9,
and it is registered in all three `qa-*` plugins.
**Depends on:** K1 (the KB formats and the slice) and D1 (the Edges inventory shape).
**Budget:** ~105k:
- CLAUDE.md, the global rules and the system prompt: ~22k
- this plan's §2, §5–§7, §9, §10 and D5, D6, D8, D12: ~14k
- the `dependency-map` skill and example: ~9k
- `feature-trace`'s Edges section: ~2k
- `requirements-breakdown` 4.4k and `test-design-techniques` 5k
- `example-area.md` for Ana's month: 6k
- the `qa-*` marketplace entries (grep): ~2k
- writes (the skill ~5k, the example ~5k, `connections.md` ~2k, the moved example ~2k, the edits ~6k): ~20k
- reasoning: ~20k

**Gate: none** — this plan gates once, in A3. Do not run `claude plugin validate`, the checkers,
`tools/token-audit.py` or any script.

- **`qa/manual/requirements-breakdown/SKILL.md`:**
  - The input-shape table: the KB row adds "and the §8 slice"; the feature-document row maps
    *How it connects* to §8; a new row covers code-trace evidence (`dev:doc-feature-trace`, run by the
    agent's Code mode).
  - The OpenAPI walk follows §7.2: no validation row per schema keyword.
  - §4 holds business validations only. §6 gains `On violation`.
  - New §8 Connections in §7.1's shape.
  - The procedure gains the §8 step, pointing at `references/connections.md`.
  - The quality bar reads "one to two pages, plus §8".
  - The intro says the skill backs Steps 1–2 of the agent.
  - Move the Example section to `references/example-promo-codes.md` and link it, so the file stays
    under 16,000 characters.
  - The handoffs gain `cross-feature-test-design`.
- **`qa/manual/requirements-breakdown/references/connections.md`** is the reading guide, in four parts:
  1. The KB slice: §5's eight lookups, each with its file and its grep.
  2. How trace Edges map to §8's tables.
  3. The docs-only fallback: ACs and flows that name other features, every edge `#assumption` with an
     open question, and an offer to build the KB.
  4. The KB-candidate rule.

  It states that it reads `docs/business-model/` as data, in the format `business-analysis:dependency-map`
  and `knowledge-base` define, and that QA never writes there.
- **New skill.** `qa/manual/cross-feature-test-design/SKILL.md` with `name: cross-feature-test-design`
  and the §6.4 description; confirm ≤ 500 characters.
  - Sections: When to use · When NOT to use · Inputs (a basis with §8 entries) · Procedure.
  - The procedure: pick techniques from §8's contents per §6.1; enumerate coverage items; prioritize
    (§6.2); prune (§6.3); emit the coverage-item list in `test-design-techniques`' shape, each item
    carrying its slice id.
  - Then the stopping-criteria table, the Anti-example (§9.2) and the Handoffs.
  - Cite the sources: ISTQB CTAL-TA v4.0 §3.2.1–§3.2.3 (2025-05-02) for the CRUD, state and scenario
    rows, and Rapps & Weyuker (IEEE TSE 1985) for def-use. Label the temporal and concurrency rows as
    experience-based checklists.
  - Stay under 16,000 characters.
- **`qa/manual/cross-feature-test-design/references/example-cancel-booking.md`** is §9 end to end:
  - the slice for EVT-002;
  - the §8 Connections section as `requirements-breakdown` would write it;
  - the coverage-item list;
  - all sixteen cases as headlines with priority and technique, and full `test-case-writer` rows for
    cases 1, 8 and 9.

  Every id must exist in K1's example or in `example-area.md`, and every number is recomputed against
  §9.3 and Ana's month.
- **`qa/manual/test-design-techniques/SKILL.md`** (already over budget; net ≤ 1,000 characters):
  - Selection-matrix rows point to `cross-feature-test-design`: shared entity → CRUD; reaction chain →
    scenario-based; another owner's trigger in a shared state → cross-owner state transition; schedule
    → temporal.
  - The default recipe ends "→ `cross-feature-test-design` when the basis has §8 entries".
  - State transition names round-trip coverage in one line.
- **Marketplace.** Register `./qa/manual/cross-feature-test-design` in `qa-java`, `qa-dotnet` and
  `qa-typescript`, after `./qa/manual/test-design-techniques`.
- **Commit message:** carries `BREAKING (format): basis §4 holds business validations only; schema
  constraints move to the data dictionary; new §8 Connections`.
- **Not in Q1:** `test-case-writer` and the two agents (Q2); the stack automation (A1–A3); README, the catalog and the gate (A3).

**As built (2026-10-11):** as planned, with four small divergences recorded as D14.
- `qa/manual/requirements-breakdown/SKILL.md`: input shapes (KB + slice, *How it connects* → §8, a code-trace row), OpenAPI walk per §7.2, §4 business validations only, §6 `On violation`, `## 8. Connections` in §7.1's shape, procedure step 7, quality bar, intro "Steps 1–2", handoffs; 15,862 bytes (15,669 characters, counted by `wc`), so it stays under 16,000 only because the Example moved verbatim to `references/example-promo-codes.md` (with a header note that it predates the rebalancing).
- `requirements-breakdown/references/connections.md`: the four parts (KB slice with the eight lookups and their greps, Edges → §8 column map, docs-only fallback, KB candidates); states that QA reads `docs/business-model/` as data and never writes it.
- `qa/manual/cross-feature-test-design/SKILL.md` (`name: cross-feature-test-design`, 9,064 bytes; description 491 characters, counted by `wc`): §6.1 technique table, stopping criteria, priority, "an open question is an expected result", sources (CTAL-TA v4.0 §3.2.1–§3.2.3, Rapps & Weyuker 1985), anti-example, handoffs. A slice id is the lookup `L1`…`L8` plus the KB ids.
- `references/example-cancel-booking.md`: the EVT-002 slice, §8 as `requirements-breakdown` writes it, the coverage-item list, all sixteen cases as headlines, full rows for TC-CANCEL-001, 008 and 009, and a recomputed arithmetic table (30 Mar booking: 1 credit, 2 × £6.00 = £12.00; £6.00 + £12.00 = £18.00; 52 h; −1; 8 → 6, not 4).
- `test-design-techniques/SKILL.md`: four selection-matrix rows, the recipe tail and a round-trip line; net +467 characters.
- `.claude-plugin/marketplace.json`: `./qa/manual/cross-feature-test-design` after `./qa/manual/test-design-techniques` in `qa-java` (:206), `qa-dotnet` (:342) and `qa-typescript` (:424).
- Unverified: no checker was run. Sizes are counted with `wc`. The id cross-check (§11 step 6) was done by reading, not by script, and the case-numbering `TC-CANCEL-nnn` is new.

### Q2 — qa/manual: the suite and the two agents

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** The manual QA lane designs to depth, and all three of these hold:
- `qa-test-case-designer` runs five steps, with a Code mode and the depth gate;
- `test-case-writer` writes parameterized field cases and the chain, async, temporal and concurrency forms;
- `qa-test-planner` plans from the slice.

**Depends on:** Q1 (basis §8 and `cross-feature-test-design`), D1 (Edges, for Code mode) and K1.
**Budget:** ~85k:
- CLAUDE.md, the global rules and the system prompt: ~22k
- this plan's §6, §7.1–§7.7, §10 and D7–D10: ~11k
- Q1's outputs (the new SKILL.md, `connections.md`, the example's headings): ~9k
- `test-case-writer` 6k, `qa-test-case-designer.md` 6k, `qa-test-planner.md` 4.4k
- `feature-trace`'s 10-stop table and Edges: ~2k
- writes: ~14k
- reasoning: ~10k

**Gate: none** — this plan gates once, in A3. Do not run `claude plugin validate`, the checkers,
`tools/token-audit.py` or any script.

- **`qa/manual/test-case-writer/SKILL.md`:** add §7.5. Move the Example section to
  `references/example-login.md` and link it, which pays for the additions; net growth ≤ 0.
- **`qa/manual/agents/qa-test-case-designer.md`** (already over budget; net ≤ 2,000 characters):
  - The input table gains §7.3's two rows.
  - A **Code mode** section goes after Exploration mode, in the same shape and ≤ about 1,200
    characters. It loads `backend/_shared/feature-trace/SKILL.md` (`dev:doc-feature-trace`, available
    through the `dev` dependency).
  - The steps table becomes §7.3's five steps, with a Step 2 detail paragraph.
  - Step 3 loads `cross-feature-test-design`. Step 5 carries the Connection → TC matrix, counts by
    layer and §7.4's depth gate.
  - Renumber every internal step reference: the orientation pass, Modes A and B, the Exploration-mode
    paragraph and the output contracts.
  - The output contract adds counts by layer and the KB candidates.
  - Related agents: `business-analyst` receives the KB candidates, and the `qa-api-<stack>` agents
    automate the temporal, concurrency and delivery cases with `time-and-concurrency-testing`.
- **`qa/manual/agents/qa-test-planner.md`:** §7.7; net ≤ 800 characters.
- **Before stopping:** if the case forms in `test-case-writer` landed differently from §7.5 (wording of
  *Environment needs*, the async expected-result form, the concurrency form), rewrite the A1–A3 blocks
  below to match, because those tasks automate exactly these forms.
- **Commit message:** carries `BREAKING (format): suites group cases by layer; field constraints are
  parameterized cases`.
- **Not in Q2:** the stack automation (A1–A3); README, the catalog and the gate (A3).

**As built (2026-10-11):** as planned, with two small additions recorded as D15; the A1–A3 blocks needed no rewrite (the async, temporal and concurrency wording is §7.5's).
- `qa/manual/test-case-writer/SKILL.md`: `### Case forms` (parameterized field cases, layer groups, async, temporal, concurrency, chains), procedure step 1, a layer-heading placeholder in the output template, a quality-bar item and a handoff to `cross-feature-test-design`; the Example moved to `references/example-login.md`; 21,778 → 18,128 characters.
- `qa/manual/agents/qa-test-case-designer.md`: five-step table, Step 2 detail, Code mode, two input rows, the depth gate and layer list in Step 5, every "Step <n>" renumbered, output contract (layers, connections, KB candidates, *Environment needs*), related agents; 22,377 → 24,407 characters (net +2,030, 30 over the bullet, with trims elsewhere in the file).
- `qa/manual/agents/qa-test-planner.md`: slice read through `connections.md`, the code-only scan lists jobs, consumers and other writers, inventory rows tagged with a layer; net +~400 characters.
- Unverified: no checker was run; sizes counted with `len()` and `wc`. `requirements-breakdown`'s intro already said "Steps 1–2", so it needed no edit.

### A1 — qa-typescript: `time-and-concurrency-testing` and the API lane wiring

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa-typescript:time-and-concurrency-testing` teaches §7.8's patterns for Node 24 (22
supported) with Vitest, for both an in-process host and a deployed environment. `qa-api-typescript`
routes temporal, concurrency and delivery cases to it, and `api-test-author/review` carries §7.8's
three checks.
**Depends on:** Q2, for the §7.5 case forms it automates.
**Budget:** ~95k:
- CLAUDE.md, the global rules and the system prompt: ~22k
- this plan's §7.5, §7.8, §9.3 (cases 6, 9–11, 13), §10, D11, D13: ~8k
- `test-case-writer`'s §7.5 additions as Q2 landed them: ~2k
- `qa-api-typescript.md` 6k, `api-test-author/writer` 4k, `api-test-author/review` 4k
- `feature-flag-testing`, whose in-process provider override is the clock-override pattern to mirror: 7k
- `messaging-testing` SKILL.md 1k, plus one reference's producer section ~3k
- `db-testing/verification-queries`' poller section: ~2k
- current-docs lookups (Vitest's repeat option; `@nestjs/schedule`, BullMQ and `node-cron` trigger
  APIs; clock injection): ~10k
- writes: ~10k
- reasoning: ~15k

**Gate: none** — this plan gates once, in A3. Do not run `claude plugin validate`, the checkers,
`tools/token-audit.py`, `npx tsc`, `npx vitest` or any script.

- **New skill.** `qa/typescript/skills/time-and-concurrency-testing/SKILL.md` with
  `name: time-and-concurrency-testing` and §7.8's description template filled with `Node 24 /
  TypeScript`; count it and confirm ≤ 500 characters.
  - Sections: When to use · When NOT to use · Inputs (the case's technique and *Environment needs*,
    plus the host mode — in-process or deployed — detected from the suite) · Procedure.
  - The procedure picks the seam by §7.8's order, then gives one pattern per table row, each with a
    short Vitest example:
    - **Job, in-process:** the cron job's tick through the NestJS scheduler registry, adding the job to
      a BullMQ queue or calling its processor, or calling a plain exported job function.
    - **Job, deployed:** an admin trigger through the typed client, or `kubectl create job --from=cronjob/…`
      inside a helper that performs I/O.
    - **Clock:** an injected clock provider, overridden in the in-process host the way
      `feature-flag-testing` overrides its provider, with data seeded relative to it.
    - **Concurrency:** a start barrier, `Promise.all`, Vitest's repeat option, and the invariant
      checked through `db-testing`.
    - **Duplicate delivery:** through the `messaging-testing` reference's producer, with a new broker
      id and the same business id; a webhook replay; an idempotency-key resend.
  - Then Anti-patterns · Hard rules · Handoffs (`be-node` for missing hooks; `messaging-testing`;
    `db-testing`; `failure-injection-testing` for a retry after a fault).
  - Stay under 16,000 characters.
- **`qa/typescript/agents/qa-api-typescript.md`** (already over budget; net ≤ 800 characters): the
  Step 3 row gains the entry. Mode B maps *Environment needs* to a seam, or to a deferral that names
  the hook and hands it to `be-node`.
- **`qa/typescript/skills/api-test-author/review/SKILL.md`:** §7.8's three checks.
- **Marketplace.** Register `./qa/typescript/skills/time-and-concurrency-testing` in `qa-typescript` only.
- **Not in A1:** Java and .NET (A2, A3); any product code, because a hook a test needs is `be-node`'s
  to build; README and the catalog (A3).

**As built (2026-10-11):** as planned, with no divergence; the A2 and A3 prompts needed no rewrite.
- `qa/typescript/skills/time-and-concurrency-testing/SKILL.md`: 15,744 characters (`wc -c`, under 16,000); description 489 characters. Sections: When to use · When NOT to use · Inputs · Procedure (seam order, then job in-process / job deployed / clock / concurrency / duplicate delivery / invariant) · Anti-patterns · Hard rules · Handoffs · APIs checked. Helpers A2/A3 mirror: `ControlledClock` + host override, `startTogether` barrier, `runCronJobNow` (kubectl, no catch).
- `qa/typescript/agents/qa-api-typescript.md`: Step 3 entry plus Mode B step 6 (seam or named deferral to `be-node`); net +494 characters.
- `qa/typescript/skills/api-test-author/review/SKILL.md`: three checks (blocker / major / major) after the Zod row. `.claude-plugin/marketplace.json`: registered in `qa-typescript` only (`python3 -m json.tool` ran once, exit 0; nothing else was run).
- APIs checked against the published packages' type definitions and docs: Vitest 3.2, 4.0, 5.0 (`repeats` in the test options, `test(name, { repeats }, fn)`; hooks run inside the repeat loop, `run.*.js:3859`) · `cron` 3.5.0 and 4.4.0 (`CronJob.fireOnTick(): Promise<void>`, public; `@nestjs/schedule` 12.0.2 depends on `cron` 4.4.0; `SchedulerRegistry.getCronJob(name)` per docs.nestjs.com) · BullMQ 6.3.12 (duplicate `jobId` ignored per docs.bullmq.io; `Worker` accepts a processor function) · node-cron 4.6.0 (`ScheduledTask.execute()`; 3.0.3 has no public run-now) · Node 22+ for `Promise.withResolvers`. Unchecked: Vitest 2.x, `@nestjs/schedule` 4–6 beyond their `cron` 3.x dependency, BullMQ below 6.
- Unverified: no sample was compiled or run; description and size counted with `wc` only.

### A2 — qa-java: `time-and-concurrency-testing` and the API lane wiring

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa-java:time-and-concurrency-testing` teaches §7.8's patterns for Java 21 with TestNG
and Spring Boot 3.x, for both an in-process host and a deployed environment, in the same shape as A1's
skill. `qa-api-java` routes temporal, concurrency and delivery cases to it, and `api-test-author/review`
carries §7.8's three checks.
**Depends on:** A1 (the sibling skill's shape) and Q2 (the case forms).
**Budget:** ~95k:
- CLAUDE.md, the global rules and the system prompt: ~22k
- this plan's §7.5, §7.8, §9.3 (cases 6, 9–11, 13), §10, D11, D13, and A1's As built: ~9k
- A1's SKILL.md as the shape to mirror: ~4k
- `qa-api-java.md` 6k, `api-test-author/writer` 4k, `api-test-author/review` 4k
- `feature-flag-testing` 7k; `failure-injection-testing`'s Awaitility section ~2k
- `messaging-testing` SKILL.md 1k plus one reference's producer section ~3k; `db-testing`'s poller ~2k
- current-docs lookups (the Spring test-time bean override for the Boot 3.x minor in use; Spring
  `@Scheduled` and Quartz trigger APIs; TestNG `invocationCount`; ShedLock): ~10k
- writes: ~10k
- reasoning: ~11k

**Gate: none** — this plan gates once, in A3. Do not run `claude plugin validate`, the checkers,
`tools/token-audit.py`, `./gradlew` or any script.

- **New skill.** `qa/java/skills/time-and-concurrency-testing/SKILL.md` with
  `name: time-and-concurrency-testing` and the description template filled with `Java 21 / TestNG`;
  confirm ≤ 500 characters. Same sections and order as A1's skill, with Java patterns:
  - **Job, in-process:** call the `@Scheduled` bean's method, or trigger the Quartz job by key, in a
    `@SpringBootTest` context. Trap: ShedLock's lock from a previous run can block an idempotency
    re-run, so the skill says how to handle it.
  - **Job, deployed:** the same seams as A1.
  - **Clock:** a `java.time.Clock` bean replaced by a test clock the test can move. If the code calls
    `Instant.now()` with no clock, defer the case and hand it to `be-java`.
  - **Concurrency:** a `CountDownLatch` start gate, futures, TestNG `invocationCount`, and Awaitility
    for the async settle.
  - **Duplicate delivery:** as A1, through the Java `messaging-testing` references.
- **`qa/java/agents/qa-api-java.md`** (already over budget; net ≤ 800 characters): the same two edits as
  A1, with `be-java` as the hook owner.
- **`qa/java/skills/api-test-author/review/SKILL.md`:** §7.8's three checks.
- **Marketplace.** Register `./qa/java/skills/time-and-concurrency-testing` in `qa-java` only.
- **Not in A2:** TypeScript and .NET; product code; README and the catalog (A3).

### A3 — qa-dotnet: `time-and-concurrency-testing`, docs, the gate, and close-out

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** §11's gate passes for the whole plan, and by then:
- `qa-dotnet:time-and-concurrency-testing` teaches §7.8's patterns for .NET 10 (8–9 supported) with
  NUnit and `WebApplicationFactory`, in A1's shape;
- `qa-api-dotnet` and its review skill are wired to it;
- README and the catalog describe everything this plan added.

**Depends on:** A1 and A2 (the sibling shape), Q2, Q1, D1 and K1.
**Budget:** ~125k:
- CLAUDE.md, the global rules and the system prompt: ~22k
- this plan's §7.8, §10, §11, D11, D13 and every As built note above: ~12k
- A1's SKILL.md as the shape: ~4k
- `qa-api-dotnet.md` 4.5k, `api-test-author/writer` and `review` ~8k
- `feature-flag-testing` 7k; `messaging-testing` and the `db-testing` poller ~4k
- current-docs lookups (`TimeProvider`/`FakeTimeProvider` and their package; Hangfire and Quartz.NET
  trigger APIs; NUnit `[Repeat]`): ~8k
- skill writes: ~10k
- the catalog, grep-scoped (line 7, line 20, the business-analysis catalog, the `qa/manual` bullets,
  the stack-skill list near line 100, line 264): ~8k; README lines 84, 201, 300, 353: ~3k; doc writes ~5k
- gate output: ~6k
- the fix loop: ~15k

**Gate:** §11, in order. This is the plan's only gate. Fix what it finds, whichever task it belongs to.

- **New skill.** `qa/dotnet/skills/time-and-concurrency-testing/SKILL.md` with
  `name: time-and-concurrency-testing` and the description template filled with `.NET 10 (8–9) /
  NUnit`; confirm ≤ 500 characters. Same sections and order as A1's skill, with .NET patterns:
  - **Job, in-process:** a Hangfire recurring job or a Quartz.NET job triggered by id or key inside a
    `WebApplicationFactory` host. A `BackgroundService` whose work cannot be invoked needs a hook, so
    the case is deferred and handed to `be-dotnet`.
  - **Job, deployed:** the same seams as A1.
  - **Clock:** `TimeProvider` swapped for `FakeTimeProvider` in `ConfigureTestServices`. Code that
    reads `DateTime.UtcNow` directly means defer the case and hand it to `be-dotnet`.
  - **Concurrency:** a `TaskCompletionSource` start gate, `Task.WhenAll`, NUnit `[Repeat]`, and the
    suite's existing poller for the async settle.
  - **Duplicate delivery:** as A1, through the .NET `messaging-testing` references.
- **`qa/dotnet/agents/qa-api-dotnet.md`** (already over budget; net ≤ 800 characters): the same two
  edits as A1, with `be-dotnet` as the hook owner.
- **`qa/dotnet/skills/api-test-author/review/SKILL.md`:** §7.8's three checks.
- **Marketplace.** Register `./qa/dotnet/skills/time-and-concurrency-testing` in `qa-dotnet` only.
- **`docs/skills-catalog.md`:**
  - The scope paragraph and the business-analysis row: 10 skills.
  - The business-analysis reasoning lane gains a `dependency-map` bullet and the KB-layout mention.
  - The `qa/manual/` list gains `cross-feature-test-design`, the Code mode and the five steps.
  - The stack-skill list near line 100 gains `time-and-concurrency-testing — java · dotnet · typescript`.
  - The reverse lane, line 264: seven inventories, How it connects, and the dependency map.
- **`README.md`:**
  - The business-analysis bullet becomes 10 skills (line 84).
  - The skills list gains `/business-analysis:dependency-map` (line 201).
  - The stack-skill table near line 300 gains a `time-and-concurrency-testing` row.
  - The status row is updated (line 353), and any `qa/manual` list gains `cross-feature-test-design`.
- **Run §11 and fix what it finds.** Record its output in `Status` and in As built.
- **Before stopping:** rewrite H1's prompt block if what landed changes its checklist. Do **not** file
  the plan, because H1's block remains.

### H1 — try it on a real feature

**Stack:** `human` · **Agent:** `human` · **Owner:** the user
**Deliverable:** H1's As built records a verdict on four things:
- on a real project, the suite for one feature with a schedule or an event consumer contains
  cross-feature cases the user judges valuable;
- at least one temporal case and one concurrency or duplicate-delivery case run as automated tests;
- the three new skill kinds trigger on their phrases;
- what the run missed.

**Depends on:** A3.
**Gate:** the checklist in H1's prompt block.

## Close-out — every task

Before you stop, in this order, in this file:

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Your own block** — delete it, and update the line above the blocks that says which have landed.
   Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming the blocker and
   its owner.
5. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified.
6. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified) and `git mv` this plan into `docs/plans/implemented/`, same
   name and number — a `solution-planner` pack moves its whole initiative folder.
7. **Commit** — the code, its tests and these plan edits together, in one commit.

## Prompts — one per task

Run them in order, one session each. Each block is complete on its own. Only A3 runs the gate (§11);
every task before it must not run `claude plugin validate`, the checkers, the token audit, or any
compiler or test runner. No prompt
may write into a project's `docs/business-model/`; these tasks change the skills, not a project. Work
in the checkout you are given, commit there, and never create a branch.

| # | Stack | Agent | Depends on | Budget |
|---|---|---|---|---|
| K1 | `docs` | `general-purpose` | — | ~95k |
| D1 | `docs` | `general-purpose` | K1 | ~100k |
| Q1 | `docs` | `general-purpose` | K1, D1 | ~105k |
| Q2 | `docs` | `general-purpose` | Q1, D1, K1 | ~85k |
| A1 | `docs` | `general-purpose` | Q2 | ~95k |
| A2 | `docs` | `general-purpose` | A1, Q2 | ~95k |
| A3 | `docs` | `general-purpose` | A1, A2, Q2, Q1, D1, K1 | ~125k |
| H1 | `human` | **the user** | A3 | one real feature |

Three blocks are live. K1, D1, Q1, Q2 and A1 have landed (their blocks are deleted).

---

### A2 — qa-java: `time-and-concurrency-testing` and the API lane wiring (general-purpose, docs)

````
You are a general-purpose agent working in the SkillsLibrary repo. Task A2 of
docs/plans/005-cross-feature-test-design.md: `qa-java:time-and-concurrency-testing` — A1's skill for
Java 21 + TestNG + Spring Boot 3.x — plus the qa-api-java wiring and three review checks.

Read, in this order:
1. CLAUDE.md (Test code rules, Simplicity, Comments, Version policy).
2. The plan: §7.5, §7.8, §9.3 (cases 6, 9, 10, 11, 13), §10, D11, D13, task A2 and the As built notes
   of Q2 and A1, and "Close-out — every task".
3. qa/typescript/skills/time-and-concurrency-testing/SKILL.md — the shape to mirror, section for section.
4. qa/java/agents/qa-api-java.md (Input modes, Step 3 row at line ~139).
5. qa/java/skills/api-test-author/writer/SKILL.md and .../review/SKILL.md.
6. qa/java/skills/feature-flag-testing/SKILL.md (in-process override) and the Awaitility section of
   qa/java/skills/failure-injection-testing/SKILL.md.
7. qa/java/skills/messaging-testing/SKILL.md, the producer section of one reference, and the poller in
   qa/java/skills/db-testing/verification-queries/SKILL.md.

Before writing an API into the skill, confirm it against current documentation for the Spring Boot 3.x
minors the stack supports: the test-time bean override for a `java.time.Clock` bean (which annotation
exists in which minor — teach the up-level form only with its down-level twin), calling a `@Scheduled`
method through the context, Quartz `triggerJob`, TestNG `invocationCount`, ShedLock's behaviour when
the scheduled method is called directly. Record the versions you checked in your As built.

Build (task A2's bullets, in order): the SKILL.md (template description with `Java 21 / TestNG`,
≤ 500 characters, counted) · qa-api-java (Step 3 entry, Mode B mapping, be-java as hook owner; net ≤ 800)
· review checks · marketplace registration in qa-java only.

Traps:
- TestNG, not JUnit, is the Java test runner here (CLAUDE.md Stack defaults) — repeat with
  `invocationCount`, not `@RepeatedTest`.
- A ShedLock lock left by the previous run can make an idempotency re-run silently do nothing — the
  test would pass for the wrong reason.
- Code calling `Instant.now()`/`LocalDateTime.now()` without a `Clock` cannot be time-controlled —
  defer and hand the seam to be-java; never sleep to the boundary.
- Same race, duplicate-delivery and deferral rules as A1 (§7.8, D13).

Gate: none — this plan gates once, in A3. Do not run `claude plugin validate`, the checkers,
tools/token-audit.py, `./gradlew` or any script.

Commit: `feat(qa-java): time-and-concurrency-testing — jobs on demand, clock, races, duplicate delivery (005 A2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### A3 — qa-dotnet: `time-and-concurrency-testing`, docs, the gate, and close-out (general-purpose, docs)

````
You are a general-purpose agent working in the SkillsLibrary repo. Task A3 of
docs/plans/005-cross-feature-test-design.md: `qa-dotnet:time-and-concurrency-testing` — A1's skill for
.NET 10 (8–9 supported) + NUnit + WebApplicationFactory — plus the qa-api-dotnet wiring and three
review checks; then README and the catalog for everything the plan added; then the plan's only gate.

Read, in this order:
1. CLAUDE.md (Test code rules, Simplicity, Comments, Version policy, Planning).
2. The plan: §7.8, §10, §11, D11, D13, task A3 and every As built note above it, and
   "Close-out — every task".
3. qa/typescript/skills/time-and-concurrency-testing/SKILL.md — the shape to mirror (and A2's, to keep
   the three consistent).
4. qa/dotnet/agents/qa-api-dotnet.md (Step 3 row at line ~76, input modes).
5. qa/dotnet/skills/api-test-author/ (writer and review SKILL.md files).
6. qa/dotnet/skills/feature-flag-testing/SKILL.md (in-process override via the factory),
   qa/dotnet/skills/messaging-testing/SKILL.md, and the poller in qa/dotnet/skills/db-testing/.
7. docs/skills-catalog.md grep-scoped (line 7, line 20, the "Business-analysis catalog" section, the
   qa/manual bullets near lines 58 and 136–142, the stack-skill list near line 100, line 264) and
   README.md lines 84, 201, 300, 353.

Before writing an API into the skill, confirm it against current documentation for .NET 8, 9 and 10:
`TimeProvider` and `FakeTimeProvider` (which package, which TFMs), Hangfire's and Quartz.NET's trigger
APIs for the versions in use, NUnit `[Repeat]`. Record the versions you checked in your As built.

Build (task A3's bullets, in order): the SKILL.md (template description with `.NET 10 (8–9) / NUnit`,
≤ 500 characters, counted) · qa-api-dotnet (Step 3 entry, Mode B mapping, be-dotnet as hook owner;
net ≤ 800) · review checks · marketplace registration in qa-dotnet only · catalog · README.

Then the gate — §11, in order:
  python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
  claude plugin validate .
  python3 tools/plugin-surface-check.py
  python3 tools/token-audit.py --violations-only
  python3 tools/qa-version-check.py
plus §11 steps 6–8 (id cross-check script in your scratchpad, arithmetic recompute, format sweep).
Fix what it finds — a failure may belong to any task above you, not only to you.

Traps:
- Code reading `DateTime.UtcNow`/`DateTimeOffset.UtcNow` directly cannot be time-controlled — defer and
  hand the `TimeProvider` seam to be-dotnet; never sleep to the boundary.
- A `BackgroundService` loop is usually not invocable from a test — that is a hook request, not a reason
  to wait for its timer.
- Token audit: SKILL.md body violations ≤ 89, agent-file violations ≤ 53, 0 description violations,
  and none of the five new SKILL.md files listed. Relocate detail to references/ before trimming rules.
- Do not file the plan: H1's block remains. Rewrite H1's checklist if what landed changes it.

Commit: `feat(qa-dotnet): time-and-concurrency-testing; docs; gate passed (005 A3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### H1 — try it on a real feature (the user)

````
H1 of docs/plans/005-cross-feature-test-design.md — your checklist. Run it in a work repo that enables
`qa-<stack>`, `dev` and `business-analysis`.

1. Pick one feature that has a schedule or an event consumer (a job, a webhook, a message handler).
2. Optional, stage 1: `/dev:document-feature <feature>` (or `/dev:document-system` for its area) and
   check that How it connects lists what starts it, what it sets off, and what it shares — and, for the
   system run, that docs/business-model/events.md, shared-data.md and invariants.md exist.
3. `/qa-<stack>:test-cases <feature name, path or story>` and check:
   - the basis has §8 Connections, built from the KB or a code trace;
   - there is at least one case per reaction chain path, schedule and shared field the feature has;
   - field validations are parameterized cases, not the bulk of the suite;
   - Step 5 reports counts by layer and the depth gate's result;
   - the open questions are real business decisions nobody made (as cases 8, 11, 12 in §9.3 are).
4. `/qa-<stack>:api` with that suite (Mode B) and check: one temporal case (a job run on demand or a
   clock boundary) and one concurrency or duplicate-delivery case are automated and green; any case
   the environment cannot support is reported as deferred with the missing hook named — not skipped,
   not slept through.
5. Trigger phrases in a fresh session: "what else happens when <X> is cancelled" → loads
   dependency-map; "test the side effects of <Y>" → loads cross-feature-test-design; "run the nightly
   job in a test" → loads time-and-concurrency-testing; "write field validation cases for this form" →
   loads test-design-techniques, NOT cross-feature-test-design.
6. Tell a session to record your verdict as H1's As built (which cross-feature cases you judged
   valuable, what ran, what it missed, any trigger misfire), then close out per the plan's "Close-out —
   every task" — deleting this block files the plan into docs/plans/implemented/.
````
