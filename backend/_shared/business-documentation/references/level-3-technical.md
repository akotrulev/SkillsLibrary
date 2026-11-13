# Level 3 — technical reference

Load this when writing or refreshing a Level 3 file (`<name>.technical.md`) — never for Levels 1 or 2. Golden example: [example-technical.md](example-technical.md).

For developers and AI agents who must change the code. Everything is exact: names are the code's names, paths are repo-relative, every fact has its evidence on the same row. It is **looked things up in, not read through** — tables over prose, one fact per row, stable local ids so Levels 1 and 2 and other agents can cite a row, and headings that never change between documents.

```markdown
# <Area name> — Technical reference
<header block: Created · Owned by · Derived from · Audience: internal · Levels>
**Stack:** <detected + versions> · **Depth:** full | shallow · **Traced:** <date>

## How to read this          ← tier legend, path convention, id scheme — five lines
## Quick facts               ← | Area id | Modules | Entry points | Entities | Events in/out | Integrations | Flags |
## Code map                  ← | Concern | Path | Notes |
## Entry points              ← | Id | Trigger | Handler (path:line) | Auth | Contract | Evidence |
## Rules, validations and decisions   ← | Id | Rule | Condition | Effect | Evidence | Tier |
## Data                      ← entities, columns, constraints, migrations, state machines, readers and writers
## Control flow              ← per flow: sequence, transaction boundary, ordering, idempotency, concurrency
## Events and reactions      ← the Edges inventory, in full
## Integrations              ← | Id | Client | Trigger | Sends | Timeout / retry / fallback | Evidence |
## Configuration             ← | Id | Key | Defined at | Default | Effect | (names only — never a secret's value)
## Errors                    ← | Id | Condition | Status / problem type | Body | User-visible text | Evidence |
## Telemetry                 ← spans, logs, metrics the area emits — or the negative search
## Tests                     ← | Test (path:line) | Covers | Gaps |
## Business ↔ code vocabulary
## Changing this safely      ← invariants to keep, coupled files, traps
## Findings                  ← defects, unreachable code, contradictions — routed
## Technical open questions  ← T1, T2 …
## Evidence index            ← every statement in Levels 1 and 2
```

**Ids.** The id-carrying tables are Entry points (`EP`), Rules (`R`), Data (`DB`), Events (`EV`), Integrations (`INT`), Configuration (`CFG`), Errors (`ERR`) and Findings (`F`), plus `T` for technical open questions. Code map, Tests, Vocabulary and Changing-this-safely rows carry no id.

**Write order.** This file's body first, then Level 1, then Level 2, then this file's evidence index last — it cites the step numbers of the other two.

- **Code map** — per concern (routing, handlers, services, domain, persistence, jobs, consumers, clients, config), the path that holds it.
- **Entry points** — one row per route, job and consumer, with its authorisation (policy / permission string) and contract in one line each, or a link to the OpenAPI / schema file. Never copy a schema the repo already holds.
- **Data** — per entity: columns read and written, constraints and indexes (*constraints are rules*), the creating migration, soft-delete and audit behaviour. Each state machine is a **Mermaid `stateDiagram-v2`** plus a line listing the **refused** transitions. *Written by* and *Also written by* columns name every writer.
- **Control flow** — per flow, a **Mermaid `sequenceDiagram`** when more than two participants are involved, plus bullets for: transaction boundary and what runs after commit, ordering assumptions, the idempotency key or its absence, locks and concurrency control, what is retried. A guarantee the code does not show is written `?`.
- **Events and reactions** — the full Edges table (`Kind`, `Reads`, `Writes`, `Also written by`, `Emits`, `Reacted to by`, `Mode`, `On failure`, `Evidence`), with the dependency map's `EVT-` / `RX-` / `INV-` ids.
- **Errors** — one `ERR` row per condition, so Level 1's *What stops it* rows have a row to cite; the user-visible failure contract: condition → status or problem type, the body, and the **exact user-facing text** quoted from the trace's inventory 3. Level 1's *What stops it* quotes the same text.
- **Telemetry** — what the code emits; "none found — searched …" is a legitimate row and usually a finding.
- **Tests** — existing tests by path and line, and what no test covers. Tests are evidence of intent, never of behaviour.
- **Business ↔ code vocabulary** — every Level 2 part name and every client term Level 1 uses (from the trace's `Client vocabulary` table) mapped to its code name. A client's own technical-sounding word ("API keys", "consumer") stays in Levels 1–2 only when it is listed in this table's first column — that is what the lint accepts.
- **Changing this safely** — invariants the code relies on without stating them, files that must change together, traps. Every item has evidence.
- **Findings** — defects, unreachable code, contradictions, stale comments. Each has its **boundary condition** and the agent it routes to. **Findings live only here.** This is the only place in the set where behaviour is judged.

## Evidence index

The closing table that backs Levels 1 and 2:

| Level | Section | Statement | Evidence | Tier |
|---|---|---|---|---|
| Guide | Rules and limits | Exposure fee % is defined per group | `ExposureGroup.cs:14` | `#observed` |
| Guide | Daily accrual · step 3 | Base & account interest formula | see **R2** | `#observed` |
| Guide | Place an order · outcome 2 | The order is charged the exposure fee | see **R3** | `#observed` |
| Behind the scenes | Pricing a fill · steps 2–4 | A redelivered notification is priced a second time | see **F1** | `#observed` |
| Guide | Open questions | The fee exists to cover losses on margin loans | comment at `ExposureFeeCalculator.cs:9`; Q1 | `#inferred` |

Rules:

- **Every statement in Levels 1 and 2** that states a parameter, formula, threshold, step, branch, connection, timing or failure behaviour has a row. One row per statement, short.
- **Level** is exactly `Guide` or `Behind the scenes`.
- **Section cites where the statement lives.** A statement inside a flow cites the flow's `###` heading exactly, then ` · step N` or ` · steps N–M` for a numbered step (`Booking a seat · step 3`). In a Level 1 task, a statement in a bullet under **What happens next** cites ` · outcome N` or ` · outcomes N–M`, counted from the top of that list; so a task cites `<Task> · step N` or `<Task> · outcome N`. An unnumbered statement in a flow (its example, its callout, its screen search) cites the heading alone. Any other statement cites its section name (`Who uses it`, `Rules and limits`, `Open questions`, `Timing and ordering`); a guide's opening callout is cited `Important`; an absent optional section is cited by its name with the search that proved it. Every `###` flow under Level 1's `## For …` sections and *What happens automatically*, and under Level 2's *What happens behind the scenes*, has at least one row, and a cited step or outcome number exists in that flow.
- **A task with no screen found** has a row citing the task's heading alone, whose evidence is the negative search (the routes, pages and label files searched), so the guide's plain steps are shown to be honest.
- **Evidence.** Every `#observed` row has evidence: `file:line` read this session, or `see **X**` where `X` resolves to a Level 3 row id (`R4`, `EV1`, `ERR1`, `F1`). Bold is reserved for row ids; a section is cited by name in plain text ("see Integrations"). Every `#inferred` row names a `Q<n>` or `T<n>`. A negative claim names its search.
- A Level 2 failure or timing statement that is also a finding cites the finding id.

**Length.** Up to about 4,000 words, not counting the evidence index; past that it splits into `<name>.technical.md` (How to read this, Quick facts, Code map, Evidence index) plus `<name>.technical.<topic>.md` per topic, linked from the top — the lint reads the topic files together with the main file.

**Language.** Everything the other levels ban is welcome here, and nothing the other levels explain is re-explained: `R4 · refund window · order closed > 30 days · reject · RefundService.cs:88`.
