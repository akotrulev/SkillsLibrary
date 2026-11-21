---
name: audit-feature
description: Use when tracing one existing feature with no spec (what it does, its validations, its defects). Triggers "how does feature X actually work", "find the defects here". Not for spec checks (audit-spec).
---

# Feature Audit

Audit a named feature or area of an existing codebase and produce **one report that makes the feature legible**: what it actually does (not what it's named), every validation and gate it enforces, how it integrates with the rest of the system — and where it's wrong, fragile, or relying on an assumption, as prioritized findings with evidence, each classed **data issue / code issue / logical conflict**.

This is **read-only analysis** on product code. The audit points; owners fix. The only files it writes are its own reports.

## The two modes

| | **Mode A — BASELINE** | **Mode B — RE-AUDIT** |
|---|---|---|
| Trigger | First audit of this feature | A prior report exists |
| Spine | Decompose into **lettered surfaces**; findings numbered within them (A1, A2, B1…) | Reload the prior report; **reuse its surface letters and finding IDs verbatim** |
| Work | The three inventories → findings | Re-trace each finding + sweep its defect family |
| Output | `…-audit-r1.md` | `…-audit-r<N>.md` — every finding prefixed **Resolved** / **Still open**, every surface closed with a rollup |

Where `engineering:audit-spec` persists a requirement register, this skill's **report is its own register**: the surface letters, finding IDs, and defect families are the stable spine every later round reuses. That is why the report is saved to a file, not just narrated.

State the mode and the feature in the first line of output.

**A prior report exists →** this is Mode B: read `references/re-audit.md` (reload, re-verify, status markers, delta report) instead of the Mode A procedure below.

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

- A spec exists and the ask is "does the code meet it" → `engineering:audit-spec`
- The ask is really "find security vulnerabilities" → `qa-security` agent (this audit *inventories* authz gates; it doesn't attack them)
- The ask is whole-codebase health, not one feature → decompose first; audit one area at a time
- The ask is about structure: shallow modules, duplicated logic, module boundaries, tests tied to internals → `engineering:audit-architecture`
- The user wants the findings fixed → the owning `be-*`/`fe-*` agent; never edit product code here

## Evidence policy — static-first, execute opt-in

Evidence is **read code** by default; running builds/tests or probing a live app is an explicit per-audit opt-in that corroborates a code trace but never replaces it.

## Evidence rules

The evidence, id and round standards every report must meet are the engineering rule file `audits.md`, shared with `engineering:audit-spec`, not a list here. Read the project's copy in `.claude/rules/engineering/`, or the plugin's in `engineering/rules/` when the project has not installed them (`/engineering:rules` does). Where it and this skill disagree, the rule file wins. A grep hit is a lead, not evidence; a negative claim ("X is never validated") names the search performed.

## Inputs needed

Ask only what's missing, at most 2–3 questions:

1. **The feature/area** — by name, plus any entry point the user already knows
2. **The driving question** — what prompted the audit ("where is the timezone not considered?", "can two users hit this concurrently?", "what would break if we changed X?"). If the user has none, the default is: *"what does it do, what does it enforce, what does it touch — and where does that diverge from what the team believes?"* Write the driving question at the top of the report; every finding should be an answer to it or explicitly marked adjacent.
3. **Evidence mode** — static (default) or execute-opt-in

Mode B needs only the **prior report's path** (plus any new driving question). If a report already exists for the named feature, say so and default to Mode B rather than starting a fresh decomposition — a re-decomposition renumbers everything and destroys comparability.

## Artifacts

`docs/audits/<NNN>-<slug>-audit-r<N>.md`, on the current branch. Round 1 from Mode A; `r2`, `r3`… from each Mode B run. **Rounds are never overwritten** — the trend ("9 open at r1 → 3 at r2") only exists if the old rounds survive.

**Naming — `<NNN>-<slug>`.** `<NNN>` is zero-padded and scoped to `docs/audits/`: the highest existing prefix plus one (`001` when the folder is empty or absent), minted once per audit subject at the `r1` report and reused by every later round. `<slug>` is a short kebab-case feature name (`checkout-flow`). Create `docs/audits/` if absent; where the repo keeps audits another way, follow it and say so.

## Procedure — Mode A (baseline)

### 1. Scope

Turn "audit X" into an explicit boundary: which services/modules are in, which are out (named, so the reader knows what the audit does *not* claim). An audit without a declared scope and driving question is a wander — do not start reading until both are written down.

### 2. Decompose into surfaces

Map the feature's territory: entry points (endpoints, handlers, jobs, consumers, UI actions) → the code paths behind them → the data they own → the boundaries they cross (API/queue/DB/external calls). Group these into **lettered surfaces** (A, B, C…) — coherent sub-areas like "scheduling", "order placement", "notifications" — that structure the whole report. Findings are numbered within their surface (A1, A2, B1…). Done when every entry point sits under a lettered surface.

### 3. Build the three inventories (per surface)

Read the code — 2–3 representative files first to calibrate the project's conventions, then the surface's actual paths. Collect:

- **Functionality narrative** — what the surface actually does, traced, in a few sentences per path. Where the code and its naming/docs disagree, the code wins and the disagreement is a finding. Where `docs/business-model/glossary.md` exists, an identifier that uses an `Avoid` term is a finding, a code issue, minor, citing the glossary row.
- **Validations & gates** — every check the surface enforces: input validation, guards/preconditions, authn/authz checks, feature flags, idempotency keys, concurrency/locking, rate limits, error paths and what each failure does. Also record the *absences* the driving question makes relevant, each naming the search.
- **Integration map** — who calls it, what it calls, events published/consumed, shared tables/contracts, config it reads. Note the *trust assumptions* at each boundary (what inbound data is assumed already-validated/normalized — the classic audit payload). Done when every surface has its three inventories.

### 4. Findings

Each finding is one row of the priority table plus a short section containing, in order:

1. **Mechanism** — *why* the code behaves this way, cited (`file:line`), not just that it does
2. **Concrete failure scenario / impact band** — inputs or state → wrong outcome; when the defect only bites in a window, say which ("impact band ≈ 00:00–05:00 UTC")
3. **Severity** — the library's standard table (blocker / major / minor / nit); qualifiers like "(UX)", "(conditional)", "(spec check)", "(design)" are welcome after the severity
4. **Class** — data issue / code issue / logical conflict, one per finding (table below)
5. **Suggested fix direction** — one line pointing where; never the applied fix

**Class every finding**, one class per finding, per `audits.md`. The class definitions and the *Unblocked by* column are `spec-vs-code-audit`'s "Class every finding" table. What each class looks like in a feature audit:

| Class | Typical here |
|---|---|
| **Data issue** | wrong seed/reference/lookup rows; a stale or wrong config value; migration residue; stored state violating an invariant the code assumes; an enum/column out of step with the schema |
| **Code issue** | a missing validation or gate; an unhandled error path; a wrong computation; inbound data trusted without normalization; a concurrency window |
| **Logical conflict** | two code paths enforcing contradictory rules (one normalizes to UTC, another assumes local); a gate that contradicts another gate; naming/docs vs behavior where it is genuinely unclear which was intended |

When a bad row is *caused by* a bug that writes it, the finding is a **code issue** (root cause) with the data consequence noted; if the already-written data needs correcting regardless of the code fix, that is a second, cross-referenced **data issue**. One family can span all three classes — that is normal, and the split is what tells the fixer which part of the family they can close alone.

Also record what's **correct-but-dependent**: a surface that is internally consistent but inherits another finding's defect is itself a (low-severity) finding — it tells the fixer the blast radius. And group findings into **defect families** in the summary (e.g. "UTC conflated with a local concept" vs "inbound data trusted without normalization") — families reveal the systemic cause individual findings hide.

Cap detailed findings at ~30; aggregate the rest in one overflow line per family. Done when every finding has its mechanism, scenario, severity, class and fix direction.

### 5. Report (round 1)

Done when the Summary, every surface summary, the Priority table with its three class headings and Recommended sequencing are all written.

```markdown
# AUDIT — <feature>: <sub-areas covered> — Round 1

**Date:** <YYYY-MM-DD>  **Scope:** <in / out, named>  **Evidence mode:** static | static + <commands run>
**Written by:** `engineering:audit-feature` (via `code-auditor`)
**Question driving the audit:** <the driving question, verbatim>

## Summary
<The defect families (numbered), 2–4 sentences each. Then the single highest-leverage
fix and what it closes/de-risks — leverage, not severity, leads.>

## A. <Surface name>
<Functionality narrative for the surface — what it does, traced.>

### A1 — <finding title> — **<severity>**
<Mechanism with file:line · concrete failure scenario / impact band · fix direction.>

### A2 — …

**Surface summary —** <how healthy, the family its findings belong to, the one thing to fix first (`audits.md`)>

## B. <Surface name>
…
**Surface summary —** …

## Validations & gates inventory
| Surface | Check | Where | Notes |
|---------|-------|-------|-------|

## Integration map
<who calls it / what it calls / events / shared data — with the trust assumption at each boundary>

## Priority table
<Severity-ordered within each class; `None.` when a class is empty.>

### Data issues
| # | Finding | Severity | File |
|---|---------|----------|------|

### Code issues
| # | Finding | Severity | File |
|---|---------|----------|------|

### Logical conflicts
| # | Finding | Severity | File |
|---|---------|----------|------|

## Open questions
<what the audit could not settle statically · what needs the owner/PO · what execute-opt-in would confirm>

## Recommended sequencing
<numbered, LEVERAGE-ordered (a medium fix that closes three findings outranks an
isolated high): 1. <finding> — why first. Items needing a product decision before
code changes say so explicitly.>
```

Scale to the ask: a narrow driving question over one surface can drop the inventory tables into prose; a multi-surface audit keeps all sections. Never drop the Summary, surface summaries, Priority table (with its three class headings), or Recommended sequencing.

## Rules

- Every finding answers the driving question or is explicitly marked adjacent.
- A red build/test state on arrival is a finding, not yours to fix.
- The report is a first-class test-basis input: write findings so `qa/manual/requirements-breakdown` can consume them (observable behavior, boundaries, states — boundary conditions in findings are BVA seeds).
