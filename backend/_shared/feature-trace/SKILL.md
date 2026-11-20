---
name: doc-feature-trace
description: Use when one area of an existing backend must be traced in depth into file:line-evidenced inventories. Triggers "trace how this area works". Not for writing the docs (doc-business-model).
disable-model-invocation: true
---

# Feature Trace — recovering behavior from code

One area at a time, in depth. The output is **structured evidence**, not prose: ten inventories, every item with its `file:line`, for `dev:doc-business-model` to turn into a user guide and for the KB models. The guide needs tasks and actors, rules (each with the task a person meets it in), formulas, the client's words and refusal texts; the models need the rest. A **profile** says how much of the rest is recorded (*Two profiles*).

The discipline: **separate what the code does from what you think it means.** Every extracted item is `#observed` with a `file:line` read this session. Intent is a separate, marked layer; where unrecoverable, the output is the behavior plus a question.

**Prerequisite:** a confirmed area from `dev:doc-codebase-survey` or `be-feature-documenter`'s confirmed Step 1 scope table.

## Output

Per-area evidence for the documenter's write step (`be-documenter` Steps 3–4), never a KB artifact or content of `docs/business-model/`; it stays in the session (or scratchpad) unless it must survive it.

**Multi-session runs persist the trace** (`full` profile only; `be-feature-documenter` runs one session). A run that will not reach Write in the same session persists each completed area's inventory to **`docs/business-model/.trace/<area>.md`** — working files, never in `INDEX.md`, each opening:

```markdown
**Working trace by `be-documenter` @ <commit> on <date> — not a KB artifact**
```

On resume a persisted trace is a **lead, not evidence**: spot-check three citations at the current commit; if code moved or a check fails, re-trace. Step 5 (Consolidate) deletes `.trace/` once every write-up cites its evidence; a leftover one means a run ended before consolidation.

---

## Tasks first

Before walking entry points, list what people do. Sources in order — the first that exists leads, the others fill gaps:

1. **The UI in the repository** — routes, navigation, screens, forms, web and mobile (`references/trace-recipes.md` Part 3a).
2. **Journey tests and `docs/test-cases/` suites**, where the repository has them (Part 5).
3. **The experience plan** — `docs/plans/<NNN>-<initiative>/experience-plan.md`, its screen ↔ endpoint matrix.

Each **Tasks** row is one goal in the person's words, with its actor, the screen and control that start it, and every entry point it calls.

- A task calls one or more entry points; one entry point can serve several tasks. **The guide's tasks come from this inventory, never one per endpoint.**
- Every entry point lands in exactly one place: a task's *Entry points it calls*; **automatic work** (a schedule, timeout, consumer or event nobody triggers by hand — its Edges row says what people notice); a **no-screen task** (an API, CLI or webhook a person or partner calls — *Screen › control* is `none — searched …`); or **parked** with a reason.
- A task found only in a test or plan, whose entry point does not exist, is a finding (planned, not built), not a task.

## The trace path

For **every** entry point, walk this path in order, in both profiles — each stop answers a different business question; skipping one loses a category of rule:

| Stop | The business question it answers | What to extract |
|---|---|---|
| 1. **Entry point** | What can someone ask the system to do? | The capability, in a verb phrase; who can invoke it; the task that reaches it, or automatic work |
| 2. **Authorization** | Who is allowed to do it? | Roles, permissions, scopes; ownership and tenancy checks ("any user" vs "the owner") |
| 3. **Input validation** | What counts as a valid request? | Required fields, formats, ranges, allowed values, cross-field rules |
| 4. **Preconditions & lookups** | What must already be true? | Referenced things that must exist, be visible, be in a permitted state |
| 5. **Orchestration** | What happens, in what order? | The steps; what is transactional, best-effort, fire-and-forget |
| 6. **Domain rules** | What does the business logic decide? | Every branch, threshold, calculation, eligibility condition — **the highest-value stop** |
| 7. **Persistence** | What is remembered, and what does it constrain? | `Entity.field` reads and writes, DB constraints (constraints *are* rules), audit trails, soft deletes |
| 8. **External calls** | What crosses an organisational boundary? | Which system, when, what is sent, what happens if it fails |
| 9. **Events emitted — and who reacts** | What else reacts? | Events, messages, outbox rows, notifications — the seams to other areas — each with its consumers, one hop out (Edges) |
| 10. **Failure paths** | What does the user experience when it goes wrong? | Every error branch, in business terms |

**Follow the call, do not skim the file:** a five-line handler often delegates to twenty conditions. Depth `full` follows calls to where decisions are made; `shallow` stops at stop 5 and says so.

## Two profiles

The caller names the profile: `be-documenter` runs `full` (the KB models need every column); `be-feature-documenter` runs `guide` (no models to feed). None named: `full`. **`file:line` stays on every item in both.** A profile is independent of **depth** (`full` / `shallow`, how far calls are followed); the inventory reference says how each inventory reduces under **`guide`**.

| Inventory | `full` | `guide` |
|---|---|---|
| 1. Tasks | kept | kept |
| 2. Capabilities | kept | reduced |
| 3. Business rules | kept | kept |
| 4. Validations & gates | kept | reduced |
| 5. Entity states & transitions | kept | reduced |
| 6. Decision points | kept | kept |
| 7. Integrations | kept | reduced |
| 8. Edges | kept | reduced |
| 9. Configuration & switches | kept | reduced |
| 10. Tests & telemetry | kept | dropped |
| Client vocabulary · Intent notes · Findings | kept | kept |

Under `guide`, tests are still **read** as leads for intent and example values.

## The ten inventories

Load `references/inventories.md` before writing any inventory: it has every column list, worked row, `guide` reduction and rule. In brief:

### 1. Tasks
Built first (*Tasks first*).

| # | Task (the person's words) | Who | Screen › control | Entry points it calls | Source |
|---|---|---|---|---|---|
| 1 | Cancel a booking | Member | Your bookings › Cancel booking | `POST /bookings/{id}/cancel` | `app/bookings/page.tsx:42` |

Every role, administrators included; an unfound control is `none — searched …`, never a guess.

### 2. Capabilities
A verb phrase each, with actor, entry point, contract, authorization (`guide`: capability and actor).

### 3. Business rules
Every condition, threshold, calculation and eligibility test the code enforces; the number, not a rounding. Columns: Rule, Condition, Effect, **Inputs**, **Met in**, Evidence, Tier. *Met in* names the task or automatic work where a person meets the rule; *Inputs* is filled for every calculation, in the client's words, with its rounding, day-count and currency conventions.

### 4. Validations & gates
Authorization, input validation, preconditions, state guards: user-terms failure, technical outcome, refusal text verbatim with source (`guide`: failure and message only).

### 5. Entity states & transitions
States, moves, triggers and the transitions the code refuses (a missing arrow is a rule). Per state, record **whether the product shows it to a person** (label and where, or `not shown — searched …`); the guide diagrams only shown states (`guide`: shown statuses only).

### 6. Decision points
Branches where more than two inputs select an outcome: inputs, combinations, results.

### 7. Integrations
Per external system: trigger, what is sent and returned, failure behavior (unhandled is a finding), what a person notices (`guide`: that only).

### 8. Edges
One hop out: every emitted event, message, outbox row or notification with its consumers; every written field with its readers and other writers (`full`). Each row states how the reaction runs and fails; **What people notice** is filled for every row, above all automatic work (`none` where nobody notices). An unshown mode or guarantee is `?`; a negative claim names its search. **Reads, Writes, Also written by and Mode are recorded in the `full` profile only.**

### 9. Configuration & switches
Every key, option class, environment variable name, flag and behaviour-changing constant: default, effect, variation, who can change it. Names only, never a secret's value (`guide`: value and who can change it).

### 10. Tests & telemetry
Tests covering the area and telemetry emitted, with gaps (`guide`: not recorded).

## Harvest the client's words

Record the client's own words so the guide speaks them: UI copy, resource files, templates, validation text, enum display names, domain terms in docs and tests. Each goes in `Client vocabulary` with where seen, where in the product and its code name; a code name with no client term gets the search. Statuses a person sees are recorded here as shown. Where the UI is in the repository, record `screen › control` (`Your orders › Cancel order`) from routes and navigation; else the search, so the guide takes its no-screen form instead of inventing a button. `references/trace-recipes.md` has the per-stack searches.

## Evidence rules

- **Every item carries `file:line`, read this session** — not from the cache, a prior run or memory; only the read is evidence.
- **Negative claims name their search:** *searched for `RateLimit|Throttle|Bucket` across `src/Ordering/**` — no matches* `#observed`, never a bare "no rate limiting".
- **Tier every item:** `#observed` for behavior, `#inferred` for intent. Never `#confirmed`.
- **Intent has sources of two kinds.** A purpose **stated** by a story of the plan that built the area (`docs/plans/**/stories.md`, `requirements.md`, `epics.md`, also under `implemented/`; cite `US<n>`/`AC<k>` and `file:line`) or by a `#confirmed` KB entry (cite its id) goes in `Intent notes` with that source as basis, and its question cell reads `none — stated`. Comments, tests, naming and commit messages are **leads**: a probable purpose, the question kept. Stories come from the folder the caller names, else a search of `docs/plans/**` for the area's terms; none found is normal. Where a story and the code disagree, the code is the behavior and the gap is a `contradiction` finding with both readings.
- **Comments and tests evidence intent, not behavior.** "30-day window per card scheme rules" is a strong `#inferred` *why*; only code evidences *what*. A stale comment contradicting the code is a finding.
- **Commit history is a source for intent** — `git log -S'<the constant>'` or `git log --follow <file>` often surfaces the ticket. Cite it; still `#inferred` unless the message states the rule.
- **Config and flags change the answer.** A rule inside `if (featureFlags.NewPricing)` is conditional: record both branches and which environments run which, or `[TBD - who knows the flag state]`.

## What to do with things that are not documentation

You trace, not audit. Load `references/trace-record.md` (*Handling what is not documentation*) when you meet a defect, unreachable code, a trigger whose caller is outside the repository, contradicting rules, an unrecoverable purpose, or something that should change. Always: a defect is a finding, never fixed or documented as intended; unreachable code is never a capability; you never change code.

## Trace record shape

Load `references/trace-record.md` before writing the record or a persisted `.trace/<area>.md`: the full template, one section per inventory plus `Client vocabulary`, `Intent notes (#inferred)` and `Findings (not documentation)`.

Header: `**Traced:** YYYY-MM-DD · **Depth:** full | shallow · **Profile:** full | guide · **Commit:** <sha>`.

## Self-check before handing off

1. Tasks are built from the sources in order, each with its actor and entry points — not one per endpoint.
2. Every entry point the ledger assigns to this area is traced and sits in a task, automatic work, a no-screen task, or is listed as not traced / parked with a reason.
3. Every inventory item has `file:line` read this session; every negative claim names its search.
4. Every item is tiered; no `#confirmed`.
5. The rules inventory is not empty, or the area is declared a pass-through — an empty table usually means the trace stopped at stop 5.
6. Every rule says where a person meets it; every calculation lists its inputs in the client's words and its conventions.
7. Refused state transitions are recorded, not only permitted ones; every status says whether the product shows it to a person.
8. Every integration has a stated failure behavior, including "unhandled" (`guide`: as the person experiences it).
9. Findings sit in the findings list, out of the documentation stream.
10. Every emitted event has its reactors, or a negative search naming what was searched.
11. Every piece of automatic work says what each person notices, or `none`.
12. `full`: every written field has its readers and other writers, jobs' queries included.
13. `full`: every reaction states its mode and failure behavior, or `?` — never a guessed guarantee.
14. Configuration and constants are inventoried (or a negative search recorded); no secret value written.
15. `full`: tests and telemetry are inventoried with their gaps, or a negative search recorded.
16. Client words are in `Client vocabulary`; every user-facing refusal quotes its exact text and source (or the search finding none).
17. A purpose from a story or `#confirmed` entry carries its source and no question; every other purpose is `#inferred` with its question.

## Version policy

Rules hide in **stack- and version-specific** places; `references/trace-recipes.md` has the per-stack searches, keyed to `CLAUDE.md`'s Stack defaults: **.NET 10 / 8-9** · **Java 21 + Spring Boot 3.x** · **Node 24 / 22**; for screens, **React 19 / 18** (Next.js App Router, Vite + React Router) · **Blazor** · **React Native / Expo Router (SDK 57 primary)** · **SwiftUI** · **Jetpack Compose**. Take stack and version from orientation; idioms the version lacks under-report rules.
