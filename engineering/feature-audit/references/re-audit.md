# Mode B — re-audit

Loaded by `feature-audit` when a prior report exists. The evidence policy, the artifacts and the class table stay in `SKILL.md`.

The question is no longer "what does this feature do" but **"what moved since round N−1"**.

### 1. Reload, don't re-decompose

Read the prior report. Inventory its surface letters, finding IDs, severities, defect families, and evidence trails. Ids follow `audits.md`: new surfaces continue the letters (…D, E), new findings continue their surface's numbering (A5, A6). Done when every surface letter, finding id, severity, defect family and evidence trail of the prior report is listed.

### 2. Re-verify — fresh, then sweep the family

**Re-trace each finding's code path from scratch.** A "we fixed that" claim, a linked commit or a green test is a lead, not evidence (`audits.md`). Read the code as if round N−1 never happened; then compare.

Then **sweep the defect family** of every finding that moved. A fix applied at one site routinely misses its siblings, and the family grouping in the prior report exists precisely to make that sweep cheap. Family siblings found now are new findings continuing the sequence — not "the old finding, still open".

Findings closed in an *earlier* round aren't re-verified by default — they appear as a single "previously closed (r1–r2): A1, B3" line — unless the diff since then touched their cited files, which promotes them back into the re-trace set.

Default scope is *findings + their families*, not the whole feature. Re-run a full surface only when its narrative changed (the code no longer does what round N−1 said it does) — and when it did, say so loudly: a stale narrative misleads worse than a stale finding.

### 3. Mark each finding Resolved or Still open

Every finding carries its status **as a prefix**, so the report is scannable without reading a paragraph:

| Marker | Meaning |
|---|---|
| **Resolved** | Re-traced this round; the mechanism is gone and the failure scenario no longer reproduces on the code |
| **Resolved (differently)** | Fixed, but not the way the fix direction suggested — fine; judge the outcome, not adherence to your advice. Note the actual approach in one line |
| **Still open** | Unchanged, or partially addressed (say which — "Still open — guard added on the sync path, job path still bare" is progress and reads as such) |
| **Still open (regressed)** | Was resolved in an earlier round, is back. Always at least `major`, and always names what reintroduced it |
| **New** | Found this round — a family sibling, or a defect introduced since round N−1 |

Resolved needs the fresh re-trace of `audits.md`, and a **correct-but-dependent** finding stays open while its parent is open. A **logical conflict** is Resolved only when the owner's decision is recorded *and* the code or data now matches it. A finding keeps its class across rounds; a re-trace that shows it misclassed moves it, with `reclassed from data` in its row.

### 4. Report (round N)

Same surface structure and section order as round 1, plus status prefixes and a delta header. Done when every surface has its summary, the three class headings are present and **Closed this round** is filled.

```markdown
# AUDIT — <feature> — Round <N>

**Date:** <YYYY-MM-DD>  **Previous round:** `<path>` (<date>)  **Evidence mode:** static | static + <commands run>
**Written by:** `engineering:audit-feature` (via `code-auditor`)
**Question driving the audit:** <verbatim — restated, or the new one if it changed>
**Re-verify scope:** <"prior findings + defect families" | "+ surface B re-traced, narrative had changed">

## Movement
Resolved <n> · Still open <n> · Regressed <n> · New <n>
By severity, open now: blocker <n> · major <n> · minor <n> · nit <n>  (was <…>)

## Summary
<Which defect families closed, which persist, which appeared. The single
highest-leverage remaining fix — leverage, not severity, leads.>

## A. <Surface name>
<Narrative: unchanged, or the re-traced replacement if the code moved — say which.>

### A1 — <title> — **Resolved** — <original severity>
<What closed it, cited file:line, re-traced this round. One line on the approach if it
differed from the suggested direction.>

### A2 — <title> — **Still open** — **major**
<What is still true, re-cited at current file:line. What moved, if anything. Fix
direction — restated only if it changed.>

### A5 — <title> — **New** — **minor**
<Family sibling of A2, surfaced by this round's sweep. Mechanism · failure scenario · fix direction.>

**Surface summary —** 1 of 3 resolved, 1 new sibling. <converging or churning, what the opens share, the next action>

## B. <Surface name>
…
**Surface summary —** …

## Validations & gates inventory
<Deltas only — gates added, removed, or changed since round N−1; "unchanged" is a valid row.>

## Integration map
<Deltas only — new boundaries, changed trust assumptions.>

## Priority table (open + new only)
<Same three class headings as round 1, always present — `None.` when empty.>

### Data issues
| # | Finding | Severity | File | Status |

### Code issues
| # | Finding | Severity | File | Status |

### Logical conflicts
| # | Finding | Severity | File | Status |

## Closed this round
<one line per resolved finding — ID, what closed it, cited. The credit half of the
report; not optional.>

## Open questions
<still unanswered · new · what execute-opt-in would settle>

## Recommended sequencing
<numbered, leverage-ordered, over what remains open.>
```

### Surface summaries

Rules in `audits.md`. Beyond them:

- Say the **state**, the **pattern** and the **next action**: "converging: everything left here is the same untrusted-inbound-payload family, one normalization at the boundary closes three" beats "2 resolved, 1 open".
- Where a surface did not move, say why if you know and admit it if you do not: "unmoved; no commits touched these paths since r2".
- The *Movement* block is arithmetic; the surface summaries are judgment.
