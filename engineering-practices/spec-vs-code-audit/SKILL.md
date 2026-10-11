---
name: audit-spec
description: Use when a written spec — or a pile of user stories / ACs / tickets — must become one deduped requirement register, each verdicted against the code (Met/Partial/Missing/Divergent/Unverifiable) with `file:line` evidence. Triggers "check the implementation against this spec", "which acceptance criteria are not built yet", "build a requirement register from these tickets". Multi-spec, saved to `docs/audits/` → the `code-auditor` agent (SPEC lane). Not for spec-less features (`dev:audit-feature`).
---

# Spec-Compliance Audit

Verify a written specification — or a set of user stories that collectively *are* the specification — against the code that claims to implement it. The output is a **per-requirement verdict with cited evidence**, not an opinion: every requirement gets exactly one verdict, every verdict gets a `file:line` trail, and every gap becomes a severity-tabled finding — classed **data issue / code issue / logical conflict** — that someone can act on.

This is **read-only analysis** on product code. It never fixes anything — it points to the fix and names who applies it (the stack's `be-*`/`fe-*` agent, or the spec's owner when the spec is what's wrong). The only files it writes are its own artifacts: the requirement register and the audit reports.

## The two modes

Every run is one of them. Pick it before reading any code, and state it in the report header.

| | **Mode A — BASELINE** | **Mode B — RE-AUDIT** |
|---|---|---|
| Trigger | First audit of this spec/story set | A register + a prior report already exist |
| Step 1 | **Consolidate** the sources into one requirement register, and **save it** | **Reload** the saved register + the latest report |
| Step 2 | Verdict every requirement against the code | Re-verify each item; mark **Resolved** / **Still open** |
| Output | Register file + Round-1 report | Round-N delta report with a **rollup summary under every section** |
| Register | Created | Reused verbatim — IDs are never renumbered |

Mode B is only possible because Mode A persisted the register. **Never skip the save** — an audit whose requirement set lives only in a chat transcript cannot be re-audited, only redone.

State the mode — Mode A (baseline) or Mode B (re-audit) — in the first line of output, so the reader knows whether the report is a baseline or a delta.

## Relationship to the `code-auditor` agent

This skill is the **SPEC lane** of the `code-auditor` agent, and carries both modes so the agent can load it for either. Run it standalone for one spec/story set in one pass. **Hand off to `code-auditor`** — say so and stop — when the job is bigger than this lane:

- the sources span **several specs or the whole product**, or the register would cross many features (the agent owns cross-lane scoping and the orientation pass)
- the user also wants "how it really works" for spec-less areas, which needs the FEATURE lane folded in
- a register + prior rounds already exist in `docs/audits/` — Mode B must reuse their IDs verbatim, and the agent owns round bookkeeping
- the user wants a **report to hand to someone**, or asks what changed since a prior round

## When to use

- A spec/design doc exists and someone asks whether the code actually does what it says
- **Several stories / ACs / tickets** describe one feature and nobody has a single list of what it must do
- Pre-release or handover: "prove requirement coverage" with evidence, not confidence
- A feature was implemented from a spec months ago and drift is suspected
- **A previous audit's findings were worked on** and someone needs to know what actually closed (Mode B)
- An inherited codebase ships with documentation of unknown accuracy

## When NOT to use

- No spec — the ask is "tell me what this feature does" → `dev:audit-feature`
- The spec itself needs distilling into testable rules for QA → `qa/manual/requirements-breakdown` (run it *first* when the spec is raw prose; this skill consumes its output)
- Requirements conflict with *other requirements*, not with code → `business-analysis:conflict-check`
- The user wants the gaps fixed → hand findings to the owning stack agent; this skill never edits product code

## Evidence policy — static-first, execute opt-in

The default evidence source is **reading code**. Running anything (build, tests, a live app probe) is an explicit **per-audit opt-in** from the user, never assumed:

- Without opt-in, a behavior you cannot settle by reading is `Unverifiable` — and the report names exactly what execution would settle ("running the checkout integration test would confirm the rounding path").
- With opt-in, execution **corroborates** a code trace; it never replaces it. A passing test upgrades `#inferred` to `#confirmed` only when you have also read the code path the test exercises — a green test against unread code proves the test passes, not that the requirement is met as specified.

## Evidence rules (non-negotiable)

1. **Every verdict cites `file:line` you actually read.** A grep hit is a lead, not evidence — open the file and trace the path before citing it.
2. **Tag the confidence:** `#confirmed` = the behavior is traced through the code path end-to-end; `#inferred` = naming, config, or convention suggests it but the path wasn't fully traced. An `#inferred` chain of more than one link is a guess — downgrade the verdict.
3. **Negative claims name the search.** A `Missing` verdict states *where you looked* (paths, symbols, grep patterns) — "not implemented" without a documented search is unfalsifiable.
4. **Never assert from naming alone.** `ValidateOrder()` existing does not mean orders are validated per the spec — read the body.
5. **The spec is not evidence about the code, and the code is not evidence about the spec.** Comments and docstrings claiming compliance count as `#inferred` at best.

## Inputs needed

Ask only what's missing, at most 2–3 questions:

1. **The sources** — path(s) or pasted: one spec, or the whole set of stories/ACs/tickets; if they reference other docs, follow and read them
2. **The implementation scope** — repo/service/folder believed to implement it (default: search the whole repo, excluding build output)
3. **Evidence mode** — static (default) or execute-opt-in (which commands are fair game)

Mode B needs only the **register path** (and, if it isn't the newest file beside it, the prior report). If a register already exists for the named feature, say so and default to Mode B rather than silently re-consolidating.

## Artifacts

Both live beside the project's other process docs, on the current branch:

| File | Written by | Rewritten? |
|---|---|---|
| `docs/audits/<NNN>-<slug>-requirements.md` | Mode A, step 1 | **Never** — amended in place only (§1.4) |
| `docs/audits/<NNN>-<slug>-audit-r<N>.md` | Mode A (`r1`) and every Mode B run (`r2`, `r3`…) | Never — each round is a new file |

**Naming — `<NNN>-<slug>`, the library-wide artifact convention.** `<NNN>` is a zero-padded sequential number scoped to `docs/audits/`: list the folder, take the highest existing `NNN` prefix, and use `highest + 1` (start at `001` if the folder is empty or absent). It is minted **once per audit subject**, at whichever file is written first for it — here the `requirements.md` — and **every later round reuses that same `NNN`**; never renumbered, never reused for a different subject. `<slug>` is a short kebab-case title naming the subject (`checkout-rewrite`, `billing-stories`). Create `docs/audits/` if absent; if the repo already uses a different audits convention, follow it and say so.

Rounds are additive so the trend is diffable: "12 open at r1 → 4 at r2 → 4 at r3" is the sentence a stakeholder actually wants, and it only exists if old rounds survive.

## Procedure — Mode A (baseline)

### 1. Consolidate the sources into a saved requirement register

This is the step that makes everything downstream repeatable. It runs even when there is exactly one clean spec — the register is the audit's stable spine, not a convenience.

**1.1 Distill.** If a source is raw prose, load `qa/manual/requirements-breakdown` (when resolvable in the installed plugin) and apply its distill-don't-invent contract; structured sources (numbered requirements, ACs, a test-basis document, a KB artifact) are consumed as-is.

**1.2 Atomize.** Each entry is:

- **One checkable statement** — a single observable behavior or constraint. Split conjunctions; a requirement you can only verdict "half yes" is two requirements
- **Source citation** — every source that states it (`STORY-14 §AC-2`, `spec.md:88`). Multiple citations on one entry is normal and is exactly the point
- **Stable ID** — see 1.3

**1.3 Section and ID.** Group requirements into **lettered sections** (A, B, C…) by theme — the same lettering `dev:audit-feature` uses for surfaces, so the two audits' reports cross-read. Sections are the unit Mode B summarizes, so pick them by what a reader would want a verdict on as a whole ("A. Authentication", "B. Order placement"), not by which document the requirement came from.

IDs are `<letter><n>` (`A1`, `A2`, `B1`) assigned in section order. Where a source has its own ID, carry it in a `Source` column — never as the primary ID, because two stories can both call something "AC-2". **IDs are permanent**: once written to the register they are never renumbered, reused, or reordered, in any round, forever.

**1.4 Merge, and never silently reconcile.** Consolidating N stories means resolving overlap:

| Situation | What to do |
|---|---|
| Two sources state the same requirement | **One** entry, both citations |
| One source refines another (narrower case, extra constraint) | One entry with the narrowest checkable form; note the broader source |
| Two sources **contradict** | **Do not pick a winner.** One entry per version, both marked `⚠️ CONFLICT` and cross-referenced; verdict them normally against the code, and raise a `major` finding against the *spec set* naming the owner who must decide |
| A source is superseded by a later one | Keep the entry, mark `superseded by <ID>`, exclude from the verdict count |

Later amendments (a new story arrives, a requirement is descoped) **append** to the register with the next free ID and a `Added r<N>` / `Descoped r<N>` note — the file is amended, never regenerated.

**1.5 Exclude explicitly** (report, don't silently drop):
- **Non-buildable outcomes** (business KPIs, "reduce support tickets 50%") — listed under *Out of audit scope*, not verdicted
- **Unfalsifiable wording** ("fast", "user-friendly" with no number) — kept in the register, verdicted `Unverifiable`, with the measurable rewrite the spec needs

**1.6 Save it, then confirm.** Write the register file before reading a line of product code, and show the user the section list + requirement count. A wrong register wastes the whole audit; it is cheap to correct now and expensive after 40 verdicts.

```markdown
# Requirement Register — <feature>
**Sources:** <each doc/story + version/date>  **Created:** <YYYY-MM-DD>  **Rounds:** r1 <date>, r2 <date>
**Written by:** `dev:audit-spec` (via `code-auditor`)
**Requirements:** <n> verdicted · <n> out of scope · <n> conflicts open

## A. Orders
| ID | Requirement (one checkable statement) | Source | Notes |
|----|---------------------------------------|--------|-------|
| A1 | Order total rounds half-even | spec.md:88; STORY-14 AC-2 | |
| A2 | Rejected orders notify the user | STORY-14 AC-5 | |
| A3 | Admin can export orders as CSV | STORY-31 AC-1 | |

## B. Sessions
| ID | Requirement (one checkable statement) | Source | Notes |
|----|---------------------------------------|--------|-------|
| B1 | Sessions expire after 30 min fixed | STORY-9 AC-1 | ⚠️ CONFLICT with B2 |
| B2 | Sessions expire after 60 min sliding | STORY-22 AC-4 | ⚠️ CONFLICT with B1 — owner must decide |

## Out of audit scope
| Source item | Why not verdictable |
```

### 2. Orient in the codebase

Detect the stack and map the territory before verdicting anything: entry points, the module(s) plausibly owning each requirement, how the project is built/tested (even in static mode — the test suite is readable evidence). Read 2–3 representative files to calibrate the project's conventions so you recognize what "implemented normally here" looks like.

### 3. Verdict each requirement

Work through the register **section by section**. For each requirement: locate the implementation candidates → read them → trace the specific behavior → record the verdict, the evidence trail, and the confidence tag.

| Verdict | Meaning | Requires |
|---|---|---|
| **Met** | The code does what the requirement says, in every branch that matters | `#confirmed` trace; cite the path |
| **Partial** | Some of the behavior exists; a case/branch/constraint is absent | Cite what exists *and* what's missing |
| **Missing** | No implementation found | The documented search (rule 3) |
| **Divergent** | The code deliberately does something *else* — different rule, different flow | Cite both behaviors side by side; **escalate, don't judge** — this is candidate spec-drift, and whether the spec or the code is right is the owner's call |
| **Unverifiable** | Static reading can't settle it (runtime config, external service, timing, unfalsifiable wording) | Name exactly what would settle it — the execute-opt-in hook, or the spec rewrite |

Also record **checked-but-adjacent observations** sparingly: behavior the code has that the spec never mentions (undocumented validations, extra states) when it materially affects the spec's intent — as `minor`/`nit` findings, not verdicts.

Keep signal high: cap detailed findings at ~30; aggregate the remainder in one overflow line per family.

**Class every finding.** Class is orthogonal to severity: severity says how much it hurts, class says *what kind of wrong it is* and therefore *who can act*. Exactly one class per finding, and the report's Findings section is split into the three, in this order:

| Class | The defect lives in… | Typical here | Unblocked by |
|---|---|---|---|
| **Data issue** | the data the code runs on, not the logic — the code would be right on correct data | a reference/lookup row or config value that disagrees with the spec (`VatRates.json` holds 19%, spec says 20%, the lookup code is fine); migration residue; stored state violating an invariant the spec assumes; an enum/column out of step with the schema | a data correction, migration, or config change — the data/platform owner |
| **Code issue** | the logic itself — absent, incomplete, or wrong | `Missing` and `Partial` requirements; a missing validation/gate; an unhandled branch; a wrong computation; a trust assumption at a boundary | a code change — the owning `be-*`/`fe-*` agent |
| **Logical conflict** | two things that cannot both hold, and which one wins is not the auditor's call | a `⚠️ CONFLICT` source pair; a `Divergent` verdict (code deliberately does something else); two code paths enforcing contradictory rules; the team's stated model vs what the code does | a **decision** by the spec/product owner first, then code or data — the Suggested-fix cell names the decision and its owner, never a side |

When a bad row is *caused by* a bug that writes it, the finding is a **code issue** (root cause) with the data consequence noted in its row; if the already-written data needs correcting regardless of the code fix, that is a second, cross-referenced **data issue**. `Unverifiable` items are open questions, not findings, until something settles them.

### 4. Report (round 1)

Organized **by register section**, each closed with a rollup — the same shape Mode B reuses, so a round-1 and a round-3 report read alike.

```markdown
# Spec-Compliance Audit — <feature> — Round 1

**Register:** `docs/audits/<...>-requirements.md`  **Scope:** <repo/service audited>  **Date:** <YYYY-MM-DD>
**Written by:** `dev:audit-spec` (via `code-auditor`)
**Evidence mode:** static | static + <commands run>
**Requirements:** <n> verdicted · <n> out of audit scope

## Metrics
Met <n> · Partial <n> · Missing <n> · Divergent <n> · Unverifiable <n> — coverage <Met+Partial %>

## A. Orders
| ID | Requirement (one line) | Verdict | Evidence | Confidence |
|----|------------------------|---------|----------|------------|
| A1 | Order total rounds half-even | Met | `PriceCalc.cs:88-104` | #confirmed |
| A2 | Rejected orders notify the user | Partial | handler `OrderSaga.cs:41`; no notification on timeout path `OrderSaga.cs:77` | #confirmed |
| A3 | Admin can export CSV | Missing | searched `Export*`, `Csv*`, `Controllers/`, routes table | — |

**Section summary —** 1 Met, 1 Partial, 1 Missing. <2–4 sentences: the state of this
section as a whole, the pattern behind its gaps (not a restatement of the rows), and
whether the section is safe to ship. Name the one thing to fix here first.>

## B. Sessions
…
**Section summary —** …

## Findings
<Every finding under exactly one class. All three headings always present — `None.` when
a class is empty — so rounds compare class by class. Severity-ordered within each.>

### Data issues
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| major | A5 `VatRates.json:3` | Rate stored as 19%, spec says 20% — lookup code `PriceCalc.cs:61` is correct | Correct the rate entry; data owner |

### Code issues
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| blocker | A3 | Export requirement has no implementation | Implement or descope; owner decides |
| major | A2 `OrderSaga.cs:77` | Timeout path skips notification | Add notify call on timeout branch |

### Logical conflicts
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| major | B1/B2 conflict | Sources disagree: 30 min fixed vs 60 min sliding (code does `AuthConfig.cs:23` sliding 60) | Spec owner decides — do not pick a side |

## Out of audit scope
<non-buildable outcomes, with why>

## Open questions
<what execution would settle · spec ambiguities needing the owner>

## Recommended next step
<one sentence: who fixes what first — leverage-ordered>
```

Severity mapping uses the library's standard table: **blocker** = a core requirement is Missing/Divergent in a way that ships wrong behavior; **major** = Partial on a requirement that will hurt soon, or spec-drift needing an owner decision; **minor** = adjacent observations, doc drift; **nit** = wording.

## Procedure — Mode B (re-audit)

Same evidence rules, same register, new round. The question is no longer "what does the code do" but **"what moved since round N−1"** — and the answer must be earned, not accepted.

### 1. Reload, don't rebuild

Read the register and the latest round's report. Inventory: every ID, its last verdict, its evidence trail. If new sources arrived since the last round, amend the register per §1.4 (**append** with the next free ID, marked `Added r<N>`) — never regenerate it, never renumber. Report the amendment explicitly; a register that grew between rounds makes the metrics non-comparable unless the growth is stated.

### 2. Re-verify every item — fresh

**Re-trace each requirement's code path from scratch.** A claim that something was fixed, a linked commit, a green test, a changelog entry: all are leads, none are evidence (`dev:verify` discipline). Re-read the code as if round N−1 never happened; then compare.

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

`Divergent` and `Unverifiable` are **Still open** — a divergence nobody has decided is not resolved, and an unverifiable requirement stays unverifiable until the spec gets a number or execution is opted into. Never mark an item Resolved on `#inferred` evidence alone. A **logical conflict** finding is Resolved only when the owner's decision is recorded *and* the code or data now matches it — a decision alone, or a unilateral code change, is Still open. A finding keeps its class across rounds; if a re-trace shows it was misclassed, move it and say so in its row (`reclassed from data`).

### 4. Report (round N)

Same section structure, plus per-section rollups and a delta header.

```markdown
# Spec-Compliance Audit — <feature> — Round <N>

**Register:** `<path>`  **Previous round:** `<path>` (<date>)  **Date:** <YYYY-MM-DD>
**Written by:** `dev:audit-spec` (via `code-auditor`)
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

**Section summary —** 2 of 4 resolved; A2 unmoved and A4 regressed. <2–4 sentences on
the section as a whole: is it converging or churning, what the remaining opens have in
common, whether the regression suggests the fix pattern here is unsafe, and the single
next action for this section. Never a row-by-row restatement.>

## B. Sessions
…
**Section summary —** …

## Findings (open + new only)
<Carry forward each still-open finding with its original ID, under its class; new findings
continue the sequence. All three headings always present — `None.` when empty.>

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

### Section summaries — what makes them worth reading

The rollup under each section is the deliverable stakeholders actually read. Rules:

- **One per section, never per item.** Items already have their own row; a summary that walks the rows adds nothing.
- **2–4 sentences.** Longer means the section should have been split.
- Say the **state**, the **pattern**, and the **next action** — "converging: everything left is the same missing timeout branch, fix it once in the saga and three items close" beats "3 resolved, 2 open".
- Where a section didn't move, **say why if you know and say you don't if you don't** — "unmoved; no commits touched these paths since r2" is useful, silence is not.
- The report's top-level *Movement* block is arithmetic; the section summaries are judgment. Don't swap them.

## Rules

- **Strictly read-only** on product code and the spec. The register and reports are the only files this skill writes. Offer a remediation plan; never apply it here.
- The register is **append-only and never renumbered.** IDs are the contract that makes rounds comparable; breaking them silently invalidates every trend the reports claim.
- Verdicts are per requirement; never a blended "mostly compliant" for the batch. Section summaries characterize, they don't verdict.
- **Findings are listed under exactly one of three classes — Data issues / Code issues / Logical conflicts** — and all three headings appear in every round (`None.` when empty) so rounds compare class by class. Class is orthogonal to severity.
- `Divergent` is never resolved by the auditor — deciding whether spec or code is right is a business call; the audit's job is to make the divergence undeniable. Same for a `⚠️ CONFLICT` pair from consolidation: both entries are verdicted, neither is dropped.
- **Resolved is a claim you make only after re-reading the code this round.** No commit message, ticket status, or passing test earns it on its own.
- A red build/test state discovered on arrival is a finding to report, not yours to fix.
- If the sources are too vague to consolidate at all, stop and say so — route to `qa/manual/requirements-breakdown` or the spec owner rather than auditing a guess.
