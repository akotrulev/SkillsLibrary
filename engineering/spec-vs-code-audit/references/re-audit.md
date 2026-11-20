# Mode B — re-audit

Loaded by `spec-vs-code-audit` when a register and a prior report exist. The evidence policy, the artifacts and the verdict table stay in `SKILL.md`.

Same evidence rules, same register, new round. The question is no longer "what does the code do" but **"what moved since round N−1"** — and the answer must be earned, not accepted.

### 1. Reload, don't rebuild

Read the register and the latest round's report. Inventory: every ID, its last verdict, its evidence trail. If new sources arrived since the last round, amend the register per §1.4 of `SKILL.md` (**append** with the next free ID, marked `Added r<N>`) — never regenerate it, never renumber. State the growth in the report, or the round's metrics are not comparable. Done when every id in the register is listed with its last verdict and trail, and every register amendment is named.

### 2. Re-verify every item — fresh

**Re-trace each requirement's code path from scratch.** A fixed-claim, a linked commit, a green test or a changelog entry is a lead, not evidence (`audits.md`). Re-read the code as if round N−1 never happened; then compare.

Scope of a re-audit, in order:
1. Every previously non-`Met` requirement (that's the point of the round)
2. Every requirement in the **same section as a changed one** — a fix at one site routinely misses its siblings
3. Previously `Met` requirements only when the diff since round N−1 touched their cited files — cheap regression insurance, and it catches the fix that broke a neighbor

Say which of the three you did. A re-audit that skipped 3 is still valid; one that silently skipped 3 while claiming "no regressions" is not.

### 3. Mark each item Resolved or Still open

Every item carries its status **as a prefix**, so the report is scannable without reading a single cell:

| Marker | Meaning |
|---|---|
| **Resolved** | Verdict is now `Met`, re-traced this round — whether it moved to `Met` this round or was already `Met` and still holds (both mean "nothing to do here") |
| **Resolved (differently)** | `Met`, but not the way the report suggested — fine; judge the outcome, not adherence to your advice. Note the actual approach in one line |
| **Still open** | Anything not `Met`: unchanged, or partially moved (say which — "Still open — moved Missing → Partial" is real progress and reads as such) |
| **Still open (regressed)** | Was `Met` at round N−1, is not now. Always a finding, severity at least `major` |
| **New** | Added to the register this round (§1), verdicted for the first time |

`Divergent` and `Unverifiable` are **Still open** — a divergence nobody has decided is not resolved, and an unverifiable requirement stays unverifiable until the spec gets a number or execution is opted into. Resolved needs the fresh re-trace of `audits.md`. A **logical conflict** is Resolved only when the owner's decision is recorded *and* the code or data now matches it. A finding keeps its class across rounds; a re-trace that shows it misclassed moves it, with `reclassed from data` in its row.

### 4. Report (round N)

Same section structure, plus per-section rollups and a delta header. Done when every section has its rollup, the three finding headings are present and **Closed this round** is filled.

```markdown
# Spec-Compliance Audit — <feature> — Round <N>

**Register:** `<path>`  **Previous round:** `<path>` (<date>)  **Date:** <YYYY-MM-DD>
**Written by:** `engineering:audit-spec` (via `code-auditor`)
**Evidence mode:** static | static + <commands run>
**Re-verify scope:** all non-Met · their sections · previously-Met touched by the diff
**Register changes this round:** <"none" | "+3 requirements (D1–D3), 1 descoped">

## Movement
Resolved <n> · Still open <n> · Regressed <n> · New <n>
Coverage <r(N−1) %> → <r(N) %>   Open findings <n> → <n>

## A. Orders
| Status | ID | Requirement | Verdict now | Evidence | Was (r<N−1>) |
|--------|----|-------------|-------------|----------|--------------|
| **Resolved** | A1 | Order total rounds half-even | Met | `PriceCalc.cs:88-104` #confirmed | Met |
| **Resolved (differently)** | A3 | Admin can export CSV | Met | `ExportJob.cs:12-60` #confirmed — async job, not the sync endpoint suggested | Missing |
| **Still open** | A2 | Rejected orders notify the user | Partial | timeout path still bare `OrderSaga.cs:77` #confirmed | Partial |
| **Still open (regressed)** | A4 | Rate limit 100/min | Divergent | limiter removed in `Startup.cs:44` #confirmed | Met |

**Section summary —** 2 of 4 resolved; A2 unmoved and A4 regressed. <converging or churning, what the opens share, the next action>

## B. Sessions
…
**Section summary —** …

## Findings (open + new only)
<Each still-open finding keeps its original id under its class; new ones continue the sequence.>

### Data issues
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|

### Code issues
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|

### Logical conflicts
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|

## Closed this round
<one line per resolved finding — ID, what closed it, cited. This is the credit half of
the report and it is not optional.>

## Open questions
<unchanged questions still unanswered · new ones · conflicts still awaiting an owner decision>

## Recommended next step
<one sentence, leverage-ordered.>
```

### Section summaries

Rules in `audits.md`. Beyond them:

- Say the **state**, the **pattern** and the **next action**: "converging: everything left is the same missing timeout branch, fix it once in the saga and three items close" beats "3 resolved, 2 open".
- Where a section did not move, say why if you know and say you do not if you do not: "unmoved; no commits touched these paths since r2".
- The *Movement* block is arithmetic; the section summaries are judgment.
