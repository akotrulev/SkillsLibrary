---
name: audit-spec
description: Use when verdicting a spec, stories or ACs against the code as a requirement register with file:line evidence. Triggers "check the code against this spec". Not for spec-less features (audit-feature).
---

# Spec-Compliance Audit

Verify a written specification — or user stories that collectively *are* the specification — against the code that claims to implement it. Every requirement gets exactly one verdict with a `file:line` trail, and every gap becomes a severity-tabled finding classed **data issue / code issue / logical conflict**.

This is **read-only analysis** on product code. It never fixes anything — it points to the fix and names who applies it (the stack's `be-*`/`fe-*` agent, or the spec's owner when the spec is wrong). It writes only its own artifacts: the requirement register and the audit reports.

## The two modes

Every run is one of them. Pick it before reading any code, and state it in the report header.

| | **Mode A — BASELINE** | **Mode B — RE-AUDIT** |
|---|---|---|
| Trigger | First audit of this spec/story set | A register + a prior report already exist |
| Step 1 | **Consolidate** the sources into one requirement register, and **save it** | **Reload** the saved register + the latest report |
| Step 2 | Verdict every requirement against the code | Re-verify each item; mark **Resolved** / **Still open** |
| Output | Register file + Round-1 report | Round-N delta report with a **rollup summary under every section** |
| Register | Created | Reused verbatim — IDs are never renumbered |

Mode B is only possible because Mode A persisted the register. **Never skip the save**: a requirement set that lives only in a transcript cannot be re-audited.

State the mode in the first line of output, so the reader knows whether the report is a baseline or a delta.

**A register and a prior report exist →** this is Mode B: read `references/re-audit.md` (the procedure, status markers and delta report) instead of the Mode A procedure below.

## Relationship to the `code-auditor` agent

This skill is the **SPEC lane** of the `code-auditor` agent and carries both modes. Run it standalone for one spec/story set in one pass. **Hand off to `code-auditor`** — say so and stop — when:

- the sources span several specs or the whole product, or the register would cross many features
- the user also wants "how it really works" for spec-less areas (the FEATURE lane)
- a register and prior rounds already exist in `docs/audits/` (the agent owns round bookkeeping)
- the user wants a report to hand to someone, or asks what changed since a prior round

## When to use

- A spec/design doc exists and someone asks whether the code actually does what it says
- **Several stories / ACs / tickets** describe one feature and nobody has a single list of what it must do
- Pre-release, handover or suspected drift: "prove requirement coverage" with evidence
- A previous audit's findings were worked on and someone needs to know what closed (Mode B)

## When NOT to use

- No spec — the ask is "tell me what this feature does" → `engineering:audit-feature`
- The spec itself needs distilling into testable rules for QA → `qa/manual/requirements-breakdown` (run it first on raw prose)
- Requirements conflict with *other requirements*, not with code → the `business-analyst` agent (it loads `product:conflict-check`)
- The user wants the gaps fixed → hand findings to the owning stack agent

## Evidence policy — static-first, execute opt-in

The default evidence source is **reading code**. Running anything (build, tests, a live app probe) is an explicit **per-audit opt-in** from the user, never assumed:

- Without opt-in, a behavior you cannot settle by reading is `Unverifiable`, and the report names what execution would settle ("running the checkout integration test would confirm the rounding path").
- With opt-in, execution **corroborates** a code trace; it never replaces it. A passing test upgrades `#inferred` to `#confirmed` only when you have also read the code path the test exercises.

## Evidence rules

The evidence, id and round standards every register and report must meet are the engineering rule file `audits.md`, not a list here. Read the project's copy in `.claude/rules/engineering/`, or the plugin's in `engineering/rules/` when the project has not installed them (`/engineering:rules` does). A grep hit is a lead, not evidence: open the file and trace the path before citing it. A `Missing` verdict states where you looked, and the spec is never evidence about the code, nor the code about the spec.

## Inputs needed

Ask only what's missing, at most 2–3 questions:

1. **The sources** — path(s) or pasted: one spec, or the whole set of stories/ACs/tickets; if they reference other docs, follow and read them
2. **The implementation scope** — repo/service/folder believed to implement it (default: search the whole repo, excluding build output)
3. **Evidence mode** — static (default) or execute-opt-in (which commands are fair game)

Mode B needs only the **register path** (and the prior report, when it isn't the newest file beside it). When a register already exists for the named feature, say so and default to Mode B.

## Artifacts

Both live beside the project's other process docs, on the current branch:

| File | Written by | Rewritten? |
|---|---|---|
| `docs/audits/<NNN>-<slug>-requirements.md` | Mode A, step 1 | **Never** — amended in place only (§1.4) |
| `docs/audits/<NNN>-<slug>-audit-r<N>.md` | Mode A (`r1`) and every Mode B run (`r2`, `r3`…) | Never — each round is a new file |

**Naming — `<NNN>-<slug>`.** `<NNN>` is zero-padded and scoped to `docs/audits/`: the highest existing prefix plus one (`001` when the folder is empty or absent), minted once per audit subject at the first file written for it (here the `requirements.md`) and reused by every later round. `<slug>` is a short kebab-case subject (`checkout-rewrite`). Create `docs/audits/` if absent; where the repo keeps audits another way, follow it and say so.

## Procedure — Mode A (baseline)

### 1. Consolidate the sources into a saved requirement register

It runs even for one clean spec: the register is the audit's stable spine.

**1.1 Distill.** If a source is raw prose, load `qa/manual/requirements-breakdown` (when resolvable in the installed plugin) and apply its distill-don't-invent contract; structured sources (numbered requirements, ACs, a test-basis document, a KB artifact) are consumed as-is.

**1.2 Atomize.** Each entry is:

- **One checkable statement** — one observable behavior or constraint. Split conjunctions
- **Source citation** — every source that states it (`STORY-14 §AC-2`, `spec.md:88`).
- **Stable ID** — see 1.3

**1.3 Section and ID.** Group requirements into **lettered sections** (A, B, C…) by theme — the same lettering `engineering:audit-feature` uses for surfaces, so the two audits' reports cross-read. Pick sections by what a reader wants a verdict on as a whole ("A. Authentication"), not by source document.

IDs are `<letter><n>` (`A1`, `A2`, `B1`) assigned in section order and permanent (`audits.md`). A source's own ID goes in the `Source` column, since two stories can both call something "AC-2".

**1.4 Merge, and never silently reconcile.** Consolidating N stories means resolving overlap:

| Situation | What to do |
|---|---|
| Two sources state the same requirement | **One** entry, both citations |
| One source refines another (narrower case, extra constraint) | One entry with the narrowest checkable form; note the broader source |
| Two sources **contradict** | One entry per version, both marked `⚠️ CONFLICT` and cross-referenced (`audits.md`); verdict both against the code, and raise a `major` finding against the *spec set* naming the owner |
| A source is superseded by a later one | Keep the entry, mark `superseded by <ID>`, exclude from the verdict count |

A later amendment follows the register rules in `audits.md`: next free id, marked `Added r<N>` / `Descoped r<N>`.

**1.5 Exclude explicitly** (report, don't silently drop):
- **Non-buildable outcomes** (business KPIs, "reduce support tickets 50%") — listed under *Out of audit scope*, not verdicted
- **Unfalsifiable wording** ("fast", "user-friendly" with no number) — kept in the register, verdicted `Unverifiable`, with the measurable rewrite the spec needs

**1.6 Save it, then confirm.** Write the register file before reading a line of product code, and show the user the section list + requirement count. A wrong register is cheap to correct now and expensive after 40 verdicts.

```markdown
# Requirement Register — <feature>
**Sources:** <each doc/story + version/date>  **Created:** <YYYY-MM-DD>  **Rounds:** r1 <date>, r2 <date>
**Written by:** `engineering:audit-spec` (via `code-auditor`)
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

Detect the stack and map the territory before verdicting anything: entry points, the module(s) plausibly owning each requirement, how the project is built/tested (even in static mode — the test suite is readable evidence). Read 2–3 representative files to calibrate the project's conventions so you recognize what "implemented normally here" looks like. Done when the stack, the entry points and the module owning each register section are named.

### 3. Verdict each requirement

Work through the register **section by section**. For each requirement: locate the implementation candidates → read them → trace the specific behavior → record the verdict, the evidence trail, and the confidence tag. Done when every register id has exactly one verdict, its evidence trail and its confidence tag.

| Verdict | Meaning | Requires |
|---|---|---|
| **Met** | The code does what the requirement says, in every branch that matters | `#confirmed` trace; cite the path |
| **Partial** | Some of the behavior exists; a case/branch/constraint is absent | Cite what exists *and* what's missing |
| **Missing** | No implementation found | The documented search: paths, symbols, grep patterns |
| **Divergent** | The code deliberately does something *else* — different rule, different flow | Cite both behaviors side by side; **escalate, don't judge** — this is candidate spec-drift, and whether the spec or the code is right is the owner's call |
| **Unverifiable** | Static reading can't settle it (runtime config, external service, timing, unfalsifiable wording) | Name exactly what would settle it — the execute-opt-in hook, or the spec rewrite |

Record behavior the code has that the spec never mentions, when it materially affects the spec's intent, as a `minor`/`nit` finding, not a verdict.

Cap detailed findings at ~30; aggregate the rest in one overflow line per family.

**Class every finding.** Class is orthogonal to severity: it says *what kind of wrong it is* and therefore *who can act*. One class per finding, per `audits.md`:

| Class | The defect lives in… | Typical here | Unblocked by |
|---|---|---|---|
| **Data issue** | the data the code runs on, not the logic — the code would be right on correct data | a lookup row or config value that disagrees with the spec (`VatRates.json` holds 19%, spec says 20%, the lookup code is fine); migration residue; stored state violating a spec invariant | a data correction, migration, or config change — the data/platform owner |
| **Code issue** | the logic itself — absent, incomplete, or wrong | `Missing` and `Partial` requirements; a missing validation/gate; an unhandled branch; a wrong computation; a trust assumption at a boundary | a code change — the owning `be-*`/`fe-*` agent |
| **Logical conflict** | two things that cannot both hold, and which one wins is not the auditor's call | a `⚠️ CONFLICT` source pair; a `Divergent` verdict; two code paths enforcing contradictory rules | a **decision** by the spec/product owner first, then code or data |

When a bad row is *caused by* a bug that writes it, the finding is a **code issue** (root cause) with the data consequence noted in its row; if the already-written data needs correcting regardless of the code fix, that is a second, cross-referenced **data issue**. `Unverifiable` items are open questions, not findings.

### 4. Report (round 1)

Organized **by register section**, each closed with a rollup — the same shape Mode B reuses, so a round-1 and a round-3 report read alike. Done when every section has its rollup and all three finding headings are present.

```markdown
# Spec-Compliance Audit — <feature> — Round 1

**Register:** `docs/audits/<...>-requirements.md`  **Scope:** <repo/service audited>  **Date:** <YYYY-MM-DD>
**Written by:** `engineering:audit-spec` (via `code-auditor`)
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

**Section summary —** 1 Met, 1 Partial, 1 Missing. <state, pattern behind the gaps, the one thing to fix first (`audits.md`)>

## B. Sessions
…
**Section summary —** …

## Findings
<Severity-ordered within each class; `None.` when a class is empty.>

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

Severity per `CLAUDE.md` "Review behavior", read here as: **blocker** = a core requirement is Missing/Divergent in a way that ships wrong behavior; **major** = Partial on a requirement that will hurt soon, or spec-drift needing an owner decision; **minor** = adjacent observations, doc drift; **nit** = wording.

## Rules

- Verdicts are per requirement; never a blended "mostly compliant" for the batch. Both entries of a `⚠️ CONFLICT` pair are verdicted; neither is dropped.
- A red build/test state discovered on arrival is a finding to report, not yours to fix.
- If the sources are too vague to consolidate at all, stop and say so — route to `qa/manual/requirements-breakdown` or the spec owner rather than auditing a guess.
