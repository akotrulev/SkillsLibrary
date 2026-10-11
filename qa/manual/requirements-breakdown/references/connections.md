# Reading guide — building §8 Connections

How `requirements-breakdown` fills the basis's §8 (**Connections**). Four parts, in the order they are tried: the KB slice, the code trace, the docs, then the hand-back.

**This guide reads `docs/business-model/` as data**, in the format `business-analysis:dependency-map` and `knowledge-base` define (`events.md`, `shared-data.md`, `invariants.md`, plus the grids, decision files and `interaction-map.md`). **QA never writes there.** A format change in those skills updates this file in the same commit.

The ids are the KB's: `EVT-` triggers, `RX-` reactions, `INV-` invariants, `ENT-` entities, `DEC-` decisions, `E<n>` / `AREA-nnn` owners. Restate an id in §8; never copy a row.

## 1. The KB slice

Input: an owner id (`E<n>`, `AREA-nnn`) or a trigger id (`EVT-nnn`). Read `INDEX.md` first. Compare each file's `Derived from … @ <sha>` line with the code it cites; where the commit is behind, trace those rows (part 2) instead of trusting them. Run eight lookups, each a grep over ids:

| # | Lookup | File and grep | Lands in §8 |
|---|---|---|---|
| 1 | Own triggers and reactions | `events.md`: rows whose *Owner* is the id (`grep "AREA-003" events.md`) | Triggers and chains |
| 2 | Downstream | `events.md`: take each *Emits* id, grep reactions whose *When* is that id, repeat | Triggers and chains |
| 3 | Upstream | `events.md`: other owners' reactions whose *Emits* reaches this feature's reactions (`grep "EVT-006" events.md`) | Triggers and chains |
| 4 | States depended on | `entities/<entity>.md`: the row of each target state of the feature's `ENT-` transitions | States this feature relies on |
| 5 | Decisions | `decisions/*.md` that name the feature: the other contributors' rows | Triggers and chains (the `DEC-` in Effects) |
| 6 | Shared data | `shared-data.md`: rows naming the feature's `RX-` ids | Shared data |
| 7 | Invariants | `invariants.md`: rows whose *Threatened by* has the feature's `RX-` ids | Invariants |
| 8 | Known interactions | `interaction-map.md`: entries with the feature in *Pair* | Known interactions |

- **Depth:** two hops past the feature's own reactions. Go further where an effect moves money or cannot be undone.
- In lookup 4, copy every `—` and `?` cell of those rows into the third column. A `?` cell is an open question as well.
- `Built from:` reads `KB slice @ <the files' Created or Updated date>`.

## 2. Trace Edges → §8

When the KB lacks the feature, or is stale, the agent's Code mode runs `dev:doc-feature-trace`. Its **Edges** inventory maps column by column:

| Edges column | §8 |
|---|---|
| Entry point, Kind | *Trigger* |
| Reacted to by (one hop out) | *Reaction (owner)*: one row per reactor, owner from its area |
| Writes, Reads | *Shared data*: each `Entity.field` another area also writes or reads; the other writers and readers are the reactors and the jobs' queries found by the trace |
| Emits | *Emits → next* |
| Mode, On failure | *Mode*, *On failure*, copied as the trace states them (`?` stays `?`) |
| Evidence | *Source*, tagged `#observed` |

- The trace's *Entity states & transitions* inventory feeds *States this feature relies on*; its refused transitions are the `—` cells.
- A negative claim keeps its named search ("no consumer of `BookingCancelled`, searched …").
- `Built from:` reads `code trace @ <sha>`.
- Where the code and a document disagree, record both and flag a conflict. Intent the code cannot show is `#assumption` plus a question.

## 3. Docs only — the thin fallback

With no KB and no code, read the ACs, flows and feature documents for sentences that name another feature, a schedule, a time limit, a retry or a shared number ("credits", "capacity", "balance").

- Every such edge is `#assumption` with a row in the open questions: what fires it, when, and what happens on failure.
- *Built from:* `docs only (thin) — <what was missing>`.
- Say once, at the end of §8, that a dependency map would replace these guesses, and offer `business-analysis:business-analyst` to build it from the specs.

## 4. KB candidates

An edge found in the code or the docs that the KB does not have goes under **KB candidates**: the trigger or reaction, its owner, its effects, its source. It is not written to `docs/business-model/`. The suite's hand-off notes give the list to `business-analysis:business-analyst`, whose EXTEND mode checks each one against its source before folding it in.

- A candidate that only restates a KB row is not a candidate.
- A candidate found by code trace is `#observed`; one from the docs is `#assumption`.
