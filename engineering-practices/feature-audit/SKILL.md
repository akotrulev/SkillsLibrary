---
name: ep-feature-audit
description: Use when ONE feature or area of an existing codebase must be traced with no spec in hand — what it does, which validations and gates it enforces, and where it is defective. Triggers "how does feature X actually work", "what validations does the checkout flow have", "map this module's integrations", "find the defects in this area". Multi-feature and saved to `docs/audits/` → the `code-auditor` agent (its FEATURE lane). Not for verifying a written spec (`ep-spec-compliance-audit`).
---

# Feature Audit

Audit a named feature or area of an existing codebase and produce **one report that makes the feature legible**: what it actually does (not what it's named), every validation and gate it enforces, how it integrates with the rest of the system — and where it's wrong, fragile, or relying on an assumption, as prioritized findings with evidence.

This is **read-only analysis** on product code. The audit points; owners fix. The only files it writes are its own reports.

## The two modes

| | **Mode A — BASELINE** | **Mode B — RE-AUDIT** |
|---|---|---|
| Trigger | First audit of this feature | A prior report exists |
| Spine | Decompose into **lettered surfaces**; findings numbered within them (A1, A2, B1…) | Reload the prior report; **reuse its surface letters and finding IDs verbatim** |
| Work | The three inventories → findings | Re-trace each finding + sweep its defect family |
| Output | `…-audit-r1.md` | `…-audit-r<N>.md` — every finding prefixed **Resolved** / **Still open**, every surface closed with a rollup |

Where `ep-spec-compliance-audit` persists a requirement register, this skill's **report is its own register**: the surface letters, finding IDs, and defect families are the stable spine every later round reuses. That is why the report is saved to a file, not just narrated.

**Announce at start:** "I'm using the `ep-feature-audit` skill in Mode A (baseline) / Mode B (re-audit) on <feature>."

## Relationship to the `code-auditor` agent

This skill is the **FEATURE lane** of the `code-auditor` agent, and carries both modes so the agent can load it for either. Run it standalone for a single feature in one pass. **Hand off to `code-auditor`** — say so and stop — when the job is bigger than this lane:

- the subject spans **several features or the whole codebase** (the agent owns cross-surface scoping and the orientation pass)
- a spec/story set turns up mid-audit, so the run needs the SPEC lane too (the agent runs one report, not two audits)
- artifacts already exist in `docs/audits/` for this subject — Mode B must reuse their IDs verbatim, and the agent owns round bookkeeping
- the user wants a **report to hand to someone**, or asks what changed since a prior round

## When to use

- "How does X actually work?" on an inherited or long-lived codebase
- A cross-cutting concern needs sweeping through one area (timezone handling, tenancy, idempotency, error paths)
- Before extending or rewriting a feature nobody fully understands anymore
- An incident exposed that the team's mental model of X and the code disagree

## When NOT to use

- A spec exists and the ask is "does the code meet it" → `ep-spec-compliance-audit`
- The ask is really "find security vulnerabilities" → `qa-security` agent (this audit *inventories* authz gates; it doesn't attack them)
- The ask is whole-codebase health, not one feature → decompose first; audit one area at a time
- The user wants the findings fixed → the owning `be-*`/`fe-*` agent; never edit product code here

## Evidence policy — static-first, execute opt-in

Same policy as `ep-spec-compliance-audit`: evidence is **read code** by default; running builds/tests or probing a live app is an explicit per-audit opt-in that corroborates a code trace but never replaces it.

## Evidence rules (non-negotiable)

Identical to `ep-spec-compliance-audit` — keep the two skills' discipline aligned:

1. Every claim cites `file:line` you actually read; a grep hit is a lead, not evidence.
2. Tag `#confirmed` (path traced end-to-end) vs `#inferred` (naming/config/convention); an inference chain of more than one link is a guess — say so.
3. Negative claims ("X is never validated") name the search performed.
4. Never assert from naming alone — read the body.
5. Comments and docs claiming behavior are `#inferred` at best.

## Inputs needed

Ask only what's missing, at most 2–3 questions:

1. **The feature/area** — by name, plus any entry point the user already knows
2. **The driving question** — what prompted the audit ("where is the timezone not considered?", "can two users hit this concurrently?", "what would break if we changed X?"). If the user has none, the default is: *"what does it do, what does it enforce, what does it touch — and where does that diverge from what the team believes?"* Write the driving question at the top of the report; every finding should be an answer to it or explicitly marked adjacent.
3. **Evidence mode** — static (default) or execute-opt-in

Mode B needs only the **prior report's path** (plus any new driving question). If a report already exists for the named feature, say so and default to Mode B rather than starting a fresh decomposition — a re-decomposition renumbers everything and destroys comparability.

## Artifacts

`docs/audits/<NNN>-<slug>-audit-r<N>.md`, on the current branch. Round 1 from Mode A; `r2`, `r3`… from each Mode B run. **Rounds are never overwritten** — the trend ("9 open at r1 → 3 at r2") only exists if the old rounds survive.

## Procedure — Mode A (baseline)

### 1. Scope

Turn "audit X" into an explicit boundary: which services/modules are in, which are out (named, so the reader knows what the audit does *not* claim). An audit without a declared scope and driving question is a wander — do not start reading until both are written down.

### 2. Decompose into surfaces

Map the feature's territory: entry points (endpoints, handlers, jobs, consumers, UI actions) → the code paths behind them → the data they own → the boundaries they cross (API/queue/DB/external calls). Group these into **lettered surfaces** (A, B, C…) — coherent sub-areas like "scheduling", "order placement", "notifications" — that structure the whole report. Findings are numbered within their surface (A1, A2, B1…) so the priority table and prose cross-reference cleanly.

### 3. Build the three inventories (per surface)

Read the code — 2–3 representative files first to calibrate the project's conventions, then the surface's actual paths. Collect:

- **Functionality narrative** — what the surface actually does, traced, in a few sentences per path. Where the code and its naming/docs disagree, the code wins and the disagreement is a finding.
- **Validations & gates** — every check the surface enforces: input validation, guards/preconditions, authn/authz checks, feature flags, idempotency keys, concurrency/locking, rate limits, error paths and what each failure does. Also record the *absences* the driving question makes relevant (rule 3: name the search).
- **Integration map** — who calls it, what it calls, events published/consumed, shared tables/contracts, config it reads. Note the *trust assumptions* at each boundary (what inbound data is assumed already-validated/normalized — the classic audit payload).

### 4. Findings

Each finding is one row of the priority table plus a short section containing, in order:

1. **Mechanism** — *why* the code behaves this way, cited (`file:line`), not just that it does
2. **Concrete failure scenario / impact band** — inputs or state → wrong outcome; when the defect only bites in a window, say which ("impact band ≈ 00:00–05:00 UTC")
3. **Severity** — the library's standard table (blocker / major / minor / nit); qualifiers like "(UX)", "(conditional)", "(spec check)", "(design)" are welcome after the severity
4. **Suggested fix direction** — one line pointing where; never the applied fix

Also record what's **correct-but-dependent**: a surface that is internally consistent but inherits another finding's defect is itself a (low-severity) finding — it tells the fixer the blast radius. And group findings into **defect families** in the summary (e.g. "UTC conflated with a local concept" vs "inbound data trusted without normalization") — families reveal the systemic cause individual findings hide.

Keep signal high: cap detailed findings at ~30; aggregate the rest in one overflow line per family.

### 5. Report (round 1)

```markdown
# AUDIT — <feature>: <sub-areas covered> — Round 1

**Date:** <YYYY-MM-DD>  **Scope:** <in / out, named>  **Evidence mode:** static | static + <commands run>
**Written by:** `ep-feature-audit` (via `code-auditor`)
**Question driving the audit:** <the driving question, verbatim>

## Summary
<The defect families (numbered), 2–4 sentences each. Then the single highest-leverage
fix and what it closes/de-risks — leverage, not severity, leads.>

## A. <Surface name>
<Functionality narrative for the surface — what it does, traced.>

### A1 — <finding title> — **<severity>**
<Mechanism with file:line · concrete failure scenario / impact band · fix direction.>

### A2 — …

**Surface summary —** <2–4 sentences on the surface as a whole: how healthy it is, the
family its findings belong to, and the one thing to fix here first. Not a walk through
A1/A2 — those are above.>

## B. <Surface name>
…
**Surface summary —** …

## Validations & gates inventory
| Surface | Check | Where | Notes |
|---------|-------|-------|-------|

## Integration map
<who calls it / what it calls / events / shared data — with the trust assumption at each boundary>

## Priority table
| # | Finding | Severity | File |
|---|---------|----------|------|

## Open questions
<what the audit could not settle statically · what needs the owner/PO · what execute-opt-in would confirm>

## Recommended sequencing
<numbered, LEVERAGE-ordered (a medium fix that closes three findings outranks an
isolated high): 1. <finding> — why first. Items needing a product decision before
code changes say so explicitly.>
```

Scale to the ask: a narrow driving question over one surface can drop the inventory tables into prose; a multi-surface audit keeps all sections. Never drop the Summary, surface summaries, Priority table, or Recommended sequencing.

## Procedure — Mode B (re-audit)

The question is no longer "what does this feature do" but **"what moved since round N−1"**.

### 1. Reload, don't re-decompose

Read the prior report. Inventory its surface letters, finding IDs, severities, defect families, and evidence trails. **Surface letters and finding IDs are permanent** — new surfaces continue the letters (…D, E), new findings continue their surface's numbering (A5, A6). Nothing is ever renumbered or reused.

### 2. Re-verify — fresh, then sweep the family

**Re-trace each finding's code path from scratch.** A "we fixed that" claim, a linked commit, a green test: leads, not evidence (`ep-verification-before-completion` discipline). Read the code as if round N−1 never happened; then compare.

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

Never mark Resolved on `#inferred` evidence, and never on a **correct-but-dependent** finding whose parent is still open — the blast radius hasn't shrunk just because the dependent site looks fine.

### 4. Report (round N)

Same surface structure and section order as round 1, plus status prefixes and a delta header.

```markdown
# AUDIT — <feature> — Round <N>

**Date:** <YYYY-MM-DD>  **Previous round:** `<path>` (<date>)  **Evidence mode:** static | static + <commands run>
**Written by:** `ep-feature-audit` (via `code-auditor`)
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

**Surface summary —** 1 of 3 resolved, 1 new sibling. <2–4 sentences: is this surface
converging or churning, what the remaining opens have in common, whether a regression
suggests the fix pattern here is unsafe, and the one next action. Never a walk through
the findings above.>

## B. <Surface name>
…
**Surface summary —** …

## Validations & gates inventory
<Deltas only — gates added, removed, or changed since round N−1; "unchanged" is a valid row.>

## Integration map
<Deltas only — new boundaries, changed trust assumptions.>

## Priority table (open + new only)
| # | Finding | Severity | File | Status |

## Closed this round
<one line per resolved finding — ID, what closed it, cited. The credit half of the
report; not optional.>

## Open questions
<still unanswered · new · what execute-opt-in would settle>

## Recommended sequencing
<numbered, leverage-ordered, over what remains open.>
```

### Surface summaries — what makes them worth reading

The rollup under each surface is the deliverable stakeholders actually read. Rules:

- **One per surface, never per finding.** Findings have their own sections; a summary that walks them adds nothing.
- **2–4 sentences.** Longer means the surface should have been split.
- Say the **state**, the **pattern**, and the **next action** — "converging: everything left here is the same untrusted-inbound-payload family, one normalization at the boundary closes three" beats "2 resolved, 1 open".
- Where a surface didn't move, **say why if you know and admit it if you don't** — "unmoved; no commits touched these paths since r2" is useful, silence is not.
- The *Movement* block is arithmetic; the surface summaries are judgment. Don't swap them.

## Rules

- **Strictly read-only** on product code. The audit reports are the only files this skill writes. Offer remediation direction; never apply it here.
- **Surface letters and finding IDs are permanent across rounds** — continue the sequence, never renumber or reuse. They are the contract that makes the trend claims real.
- **Resolved is a claim you make only after re-reading the code this round.** No commit message, ticket status, or passing test earns it on its own.
- Every finding answers the driving question or is explicitly marked adjacent.
- Unknowns are legitimate: what you couldn't settle goes in *Open questions*, never silently guessed (an audit that admits its limits is trusted; one that doesn't is checked).
- A red build/test state on arrival is a finding, not yours to fix.
- Sequencing is by leverage, not severity — say why each item is where it is.
- The report is a first-class test-basis input: write findings so `qa/manual/test-basis-analyzer` can consume them (observable behavior, boundaries, states — boundary conditions in findings are BVA seeds).
