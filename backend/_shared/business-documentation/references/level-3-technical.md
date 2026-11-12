# Level 3 — technical reference

Load this when writing or refreshing a Level 3 file (`<name>.technical.md`) — never for Levels 1 or 2. Golden example: [example-technical.md](example-technical.md).

For developers and AI agents who must change the code. Everything is exact: names are the code's names, paths are repo-relative, every fact has its evidence on the same row. It is **looked things up in, not read through** — tables over prose, one fact per row, stable local ids (`EP1`, `R4`, `DB2`, `EV1`, `INT1`, `CFG1`, `F1`) so Levels 1 and 2 and other agents can cite a row, and headings that never change between documents.

```markdown
# <Area name> — Technical reference
<header block: Created · Owned by · Derived from · Audience: internal · Levels>
**Commit:** <sha> · **Stack:** <detected + versions> · **Depth:** full | shallow · **Traced:** <date>

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
## Errors                    ← | Condition | Status / problem type | Body | User-visible text | Evidence |
## Telemetry                 ← spans, logs, metrics the area emits — or the negative search
## Tests                     ← | Test (path:line) | Covers | Gaps |
## Business ↔ code vocabulary
## Changing this safely      ← invariants to keep, coupled files, traps
## Findings                  ← defects, unreachable code, contradictions — routed
## Technical open questions  ← T1, T2 …
## Evidence index            ← every statement in Levels 1 and 2
```

- **Code map** — per concern (routing, handlers, services, domain, persistence, jobs, consumers, clients, config), the path that holds it.
- **Entry points** — one row per route, job and consumer, with its authorisation (policy / permission string) and contract in one line each, or a link to the OpenAPI / schema file. Never copy a schema the repo already holds.
- **Data** — per entity: columns read and written, constraints and indexes (*constraints are rules*), the creating migration, soft-delete and audit behaviour. Each state machine is a **Mermaid `stateDiagram-v2`** plus a line listing the **refused** transitions. *Written by* and *Also written by* columns name every writer.
- **Control flow** — per flow, a **Mermaid `sequenceDiagram`** when more than two participants are involved, plus bullets for: transaction boundary and what runs after commit, ordering assumptions, the idempotency key or its absence, locks and concurrency control, what is retried. A guarantee the code does not show is written `?`.
- **Events and reactions** — the full Edges table (`Kind`, `Reads`, `Writes`, `Also written by`, `Emits`, `Reacted to by`, `Mode`, `On failure`, `Evidence`), with the dependency map's `EVT-` / `RX-` / `INV-` ids.
- **Errors** — the user-visible failure contract: condition → status or problem type, the body, and the **exact user-facing text** quoted from the trace's inventory 3. Level 1's *What stops it* quotes the same text.
- **Telemetry** — what the code emits; "none found — searched …" is a legitimate row and usually a finding.
- **Tests** — existing tests by path and line, and what no test covers. Tests are evidence of intent, never of behaviour.
- **Business ↔ code vocabulary** — every Level 2 part name and every client term Level 1 uses (from the trace's `Client vocabulary` table) mapped to its code name.
- **Changing this safely** — invariants the code relies on without stating them, files that must change together, traps. Every item has evidence.
- **Findings** — defects, unreachable code, contradictions, stale comments. Each has its **boundary condition** and the agent it routes to. **Findings live only here.** This is the only place in the set where behaviour is judged.

## Evidence index

The closing table that backs Levels 1 and 2:

| Level | Section | Statement | Evidence | Tier |
|---|---|---|---|---|
| Guide | Setup | Exposure fee % is defined per group | `ExposureGroup.cs:14` | `#observed` |
| Guide | Daily accrual · step 3 | Base & account interest formula | see **R2** | `#observed` |
| Behind the scenes | Pricing a fill · steps 2–4 | A redelivered notification is priced a second time | see **F1** | `#observed` |
| Guide | Overview | The fee exists to cover losses on margin loans | comment at `ExposureFeeCalculator.cs:9`; Q1 | `#inferred` |

Rules:

- **Every statement in Levels 1 and 2** that states a parameter, formula, threshold, step, branch, connection, timing or failure behaviour has a row. One row per statement, short.
- **Section cites where the statement lives.** A statement inside a flow cites the flow's `###` heading exactly and the step: `Booking a seat · step 3`, or a range `Booking a seat · steps 1–5`. Any other statement cites its section name (`Overview`, `Setup`, `Timing and ordering`). Every `###` flow of Level 1's *How it works* and Level 2's *What happens behind the scenes* has at least one row, and a cited step number exists in that flow.
- **Evidence.** An `#observed` row carries `file:line` read this session, or `see **X**` where `X` is a local row id in this document (`R4`, `EV1`, `F1`). Bold is reserved for local row ids; a section is cited by name in plain text ("see Integrations"). An `#inferred` row names its open question. A negative claim names its search.
- A Level 2 failure or timing statement that is also a finding cites the finding id.

**Length.** Up to about 4,000 words; past that it splits into `<name>.technical.md` (quick facts, code map, evidence index) plus `<name>.technical.<topic>.md` per topic, linked from the top.

**Language.** Everything the other levels ban is welcome here, and nothing the other levels explain is re-explained: `R4 · refund window · order closed > 30 days · reject · RefundService.cs:88`.
