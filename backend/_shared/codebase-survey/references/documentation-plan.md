# The documentation plan — a confirmed survey as a runnable plan

Load this when the confirmed reading plan holds **more than one session**. A run that fits one session is not planned: it goes straight on to tracing.

The survey session writes the plan and stops. Every later session runs one prompt block of it, through Plan Queue or pasted by hand. Read the plan format first — `engineering-practices/writing-plans/references/plan-format.md` — it is the contract the plan is queued under and it is not restated here. This file says only what a documentation plan puts in each part.

**Path:** `docs/plans/NNN-document-<system>.md` in the documented project, `NNN` the next number across `docs/plans/` and `docs/plans/implemented/`.

## What goes where

| Part of the plan | Holds |
|---|---|
| Header | `**Goal:**` the three-level set for every area in scope and for the system. `**Status:**` the split confirmed, by whom and when; nothing documented yet; `A1` next |
| `## 1. What already exists, and what is missing` | `\| Need \| Today \| Gap \|` — one row per area (Need: its three-level set and its flows, entity grids and decision tables; Today: its entry points with the registering `file:line`, and what the KB already holds for it), one row for the system overview, one for the KB's shared files |
| `## 2. The confirmed area map` | The survey's area map with `AREA-nnn` ids assigned, the foundations, the coverage ledger, the parked list and the survey findings. **This is what every task reads instead of surveying again** |
| `## 3. The reading plan` | The reading-plan table: order, area, depth, primary evidence by path, traced lines, the estimate with its arithmetic, the task id — and why this order |
| `## 4. What every task writes, and what no task runs` | The files an area task writes and the KB bookkeeping it does; the one lint command every task runs, `doc-lint.py --dir docs/business-model`, with its path resolved in this session; and one line each: the plan writes no code, so it has no acceptance tests, no coverage floor and no telemetry smoke; stopped halfway, each landed area lints clean but the system overview does not exist |
| `## Decisions` | `D1` below, then every merge, divide, rename or reorder the human asked for at the gate — an order the human sets replaces the proposed reading order |
| `## Answered questions (YYYY-MM-DD)` | `O1` — the names, the split and the scope, as confirmed |
| `## Open questions` | Parked surfaces that need a person; area names still `#inferred` |
| `## N. Tasks` | `A1…An`, then `K1` |
| `## Close-out — every task` | Copied verbatim from the plan format's §7 |
| `## Prompts — one per task` | One block per task, last of all |

**D1 is the same in every documentation plan:**

> **D1 — One session per task, in the reading order, never beside each other.** Every area task writes the KB's shared files (`INDEX.md`, `glossary.md`, `active-context.md`, the dependency map, the orientation cache), and a later area reuses the actors, terms and ids an earlier one set. Cost: no parallelism.

## Tasks

One `A<n>` task per session of the reading plan, in its order; a session holding two small areas is one task naming both. `K1` is last. Every task is stack `docs`, agent `be-documenter`.

````markdown
### A2 — Ordering — placement (AREA-002)

**Stack:** `docs` · **Agent:** `be-documenter`
**Deliverable:** `docs/business-model/areas/ordering-placement.md`, `.behind-the-scenes.md` and `.technical.md` exist for AREA-002 with its flows, entity grids and decision tables, its `INDEX.md` line and its glossary terms, and the area lint exits 0.
**Depends on:** A1 — the KB it initialised, the actors and terms it set, and the shared KB files both tasks write.
**Budget:** ~128k — 85k fixed (harness, agent, skills, references, rule files, working overhead), 18k source (≈ 1,500 traced lines × 12), 25k the three documents written and re-read.
**Gate: own tests** — `python3 <resolved path>/doc-lint.py --dir docs/business-model`. Do not run the unfiltered suite.

- Entry points to trace, each with its registering `file:line`: `POST /orders` (`Orders/OrderEndpoints.cs:14`), …
- Trace (Step 2), model (Step 3), write the three levels (Step 4), then this area's KB bookkeeping — its `INDEX.md` line, glossary terms, `active-context.md` entry and dependency-map rows — and Step 6 for this area.
- **Not in A2:** the system overview and the cross-area flows (K1); Ordering — fulfilment (A3) and Identity & access (A1), cited by `AREA-nnn`, never re-traced; the parked surfaces of §2.
````

````markdown
### K1 — the system overview, the consolidated KB and the whole-KB lint

**Stack:** `docs` · **Agent:** `be-documenter`
**Deliverable:** `docs/business-model/system-overview.md`, `.behind-the-scenes.md` and `.technical.md` exist, the coverage ledger assigns or parks every surface of §2, and the lint over the whole KB exits 0.
**Depends on:** A1, A2, A3 — every area's set.
**Budget:** ~125k — 85k fixed, 25k the three overview documents, 15k reading three areas (each guide's Overview and How it connects, each technical reference's Quick facts and Events and reactions).
**Gate (this is the last runnable task, so it runs the whole set once more across the plan):** `python3 <resolved path>/doc-lint.py --dir docs/business-model`. Fix what it finds, in any area's files.

- Step 5: the system overview at all three levels, the cross-area end-to-end flows, the glossary, `INDEX.md` and `active-context.md` made consistent, the dependency map's findings filed, `.trace/` deleted.
- Step 6 across the plan: the coverage ratio against §2, five evidence-index rows and five cross-level facts checked.
- **Not in K1:** re-tracing an area. A statement the gate shows to be wrong is re-verified in that area's files only.
````

The lint is each task's runnable check, so an area task's gate takes the `own tests` form, never `Gate: none`; before `K1` it sees only the area sets written so far. `A1` also initialises the KB when none exists and documents the cross-cutting foundations it meets. `K1` reads sections, never whole area files; when its estimate passes 135k, split it into the overview (`K1`) and the whole-KB lint with its fixes (`K2`).

## Prompts

Each block follows the plan format's §6 exactly: the heading `### A2 — <title> (be-documenter, docs)`, the first line `Depends on: <ids>`, the second `Agent: be-documenter · Stack: docs`, a four-backtick fence, and the close-out line last. The preamble says: run them in order, one session each, never beside each other (D1); no prompt changes source code. A documentation prompt carries:

- **The reading order** — the project's `CLAUDE.md`; the plan's §2 row for the area, §4, the Decisions, the task block and "Close-out — every task"; `docs/business-model/INDEX.md` and `glossary.md` as the previous task left them (`A1` has none: it initialises the KB); then the area's primary evidence, by path.
- **The line that stops a second survey** — "Step 1 is done: §2 is the confirmed area map. Do not re-survey and do not rename an area; a surface §2 does not list is a finding in your report."
- **The traps**, two to four, from what the survey saw: where this stack hides its rules, the boundary with each neighbouring area and the task that owns it, the parked surfaces, a vocabulary clash between two areas.
- **The gate** copied from the task block, the **commit** (`docs: document <area> (NNN A2)`), and the close-out line.

## Before the survey session stops

1. Write the orientation cache with the area map, the surface counts and the parked list, so every task's orientation gate reads TRUST.
2. Report the plan's path, its tasks with their estimates, and that `A1` is next — and that the plan and the cache must be committed before the plan is queued (commit them yourself only when asked). Trace nothing, and write nothing into `docs/business-model/`: the area map lives in the plan's §2 until `K1` writes it into the system overview.

A REFRESH whose stale areas need more than one session writes the same plan: one `A` task per session of stale areas, and `K1` reconciles the system overview.
