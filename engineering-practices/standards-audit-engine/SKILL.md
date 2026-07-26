---
name: ep-standards-audit-engine
description: The shared procedure behind every stack's conformance audit — Mode A/B rounds, the artifact contract, evidence rules, severity semantics, grouping policy, and the report templates. Loaded by a stack's `<plugin>-conformance-audit` skill, which supplies the rule set. Do NOT invoke directly or route a user request here — it carries no rules of its own, so an audit run from this file alone would have nothing to check against. Always enter through the stack skill or its `/<plugin>-audit` command.
---

# Conformance Audit — the engine

The stack-agnostic half of a conformance audit: **how** the audit runs, what it writes, and what counts as evidence. The **what** — the rule set being audited — is supplied by the stack skill that loads this file.

This engine is the **CONVENTION lane**, the third of the library's three read-only audit lanes:

| Lane | Spine | Owner |
|---|---|---|
| **SPEC** | A requirement register consolidated from *the user's* spec / stories / ACs | `ep-spec-vs-code-audit` (via the `code-auditor` agent) |
| **FEATURE** | A lettered surface decomposition of one feature, no spec in hand | `ep-feature-audit` |
| **CONVENTION** | *The plugin's own* fixed rule set, swept across the whole codebase | **this engine** + a stack checklist |

## Division of labour

| This engine owns | The stack skill owns |
|---|---|
| Mode A / Mode B, round bookkeeping, ID permanence | The lettered sections and every check in them |
| The artifact path + naming contract | The version-lane probes for its stack |
| Evidence rules, severity semantics, grouping/coverage policy | The applicability probes (which sections are N/A here) |
| The report templates ([`references/report-template.md`](references/report-template.md)) | The fence against its own sibling reviewer skill |
| The 5 phases and the hostile self-review | Handoffs to the agent that applies fixes |

A stack skill **must** name, per section, the skill that owns the rule — so a fix direction always has an owner and a disagreement between checklist and skill is resolvable (**the owning skill wins**; that disagreement is itself worth reporting).

## Two modes

| | **Mode A — BASELINE** | **Mode B — RE-AUDIT** |
|---|---|---|
| Trigger | No prior conformance report for this repo | A prior `…-conformance-r<N>.md` exists |
| Spine | The stack's lettered sections; findings numbered within them | Reload the prior round; **reuse its section letters and finding IDs verbatim** |
| Work | Applicability matrix → full sweep → findings | Re-trace each finding **fresh** → sweep its defect family → new findings take the next free ID |
| Output | `…-conformance-r1.md` | `…-conformance-r<N>.md`, every finding prefixed **Resolved** / **Resolved (differently)** / **Still open** / **Still open (regressed)** / **New** |

**Defaulting:** check `docs/audits/` first. If a conformance report exists for this repo, enter **Mode B** and say so. Never silently renumber — the point of the rounds is that "23 open at r1 → 9 at r2" is a real, comparable claim, and renumbering destroys it. Propose a fresh baseline only when the codebase changed so broadly that the old spine misleads, and say why.

## Artifacts

Every run writes one file to `docs/audits/` on the current branch:

```
docs/audits/<NNN>-<plugin>-conformance-r<N>.md
```

`<plugin>` is the stack plugin's name (`fe-react`, `be-dotnet`, `qa-dotnet`, …). Rounds are additive — never overwrite or regenerate a previous round. **The report is its own register:** section letters, finding IDs, and defect families are the stable spine every later round reuses. There is no separate requirements file — the requirements here *are* the plugin's rules.

`<NNN>` is a zero-padded sequential number, scoped to `docs/audits/`: list the folder, take the highest existing `NNN` prefix, use `highest + 1` (start at `001` if the folder is empty or doesn't exist yet). It is minted **once per plugin lineage** at `r1` and every later round for that plugin reuses the same `NNN` — never renumbered, never reused for a different lineage.

Create `docs/audits/` if absent. If the repo already uses a different audits convention, follow it and say so.

**Finding IDs** are `<SectionLetter><CheckNumber>` (`B3`, `M1`, `G7`) — the number is the check number from the stack's checklist, so an ID names exactly which rule is broken and stays stable forever. If one check yields two genuinely distinct findings, suffix them (`B3a`, `B3b`) rather than inventing a number.

## Phases

### Phase 0 — Orient & version gate *(never skip)*

Half of all false findings come from auditing a project against a version lane it isn't on. Run the stack skill's detection probes, record the lane, and read **2–3 representative files** to calibrate what "normal here" looks like.

**The version rule binds every finding:** never flag a down-level project for lacking an up-level API, and never apply an up-level recipe to it. Write the detected lane at the top of the report so every reader can check your work.

A deliberate project convention that differs from the plugin's default is a **noted deviation**, not automatically a finding — say which it is.

### Phase 1 — Applicability matrix

Decide per section: **Applicable / Not applicable / Unknown**, with the probe that decided it, *before* sweeping. A section marked N/A produces no findings and no false confidence. "Not applicable" must name its probe; "Unknown" must name what would settle it. State the matrix in the report.

### Phase 2 — Sweep, section by section

Work the checklist in letter order. For each check:

1. **Locate** candidates with the checklist's recipe (fast, mechanical, repeatable across rounds).
2. **Read the code** at each hit. A grep hit is a *lead*, never a finding — the surrounding code decides.
3. **Verdict**: `Conforms` · `Violated` (→ a finding) · `Partial` (conforms in places, violated in others — finding, scoped) · `Unverifiable` (say what would settle it).
4. **Group repeats.** Twenty sites of one mistake are **one finding** with a count, 3–5 cited examples, and `+15 more (<the search that found them>)` — not twenty findings. The grouped set is the finding's **defect family**, and Mode B sweeps the whole family.

**Coverage policy.** Searches run over the whole source tree; reading is targeted at hits. Declare both in the report: files in scope, files actually read, and any directory deliberately excluded (dependencies, build output, generated code, vendored code). An audit that quietly skipped a legacy folder is misleading; one that says it skipped it is useful.

**Do not start writing the report mid-sweep.** Findings written while tracing anchor on early impressions and mis-rank severity.

### Phase 3 — Report

Fill the Mode A or Mode B skeleton in [`references/report-template.md`](references/report-template.md). Non-negotiable parts:

- **Detected lane + applicability matrix** at the top — every finding is read against it.
- **Every section closes with a rollup summary** — 2–4 sentences of *judgment* (state · pattern · next action), distinct from the arithmetic. One per section, never per finding. Walking the rows is not a rollup.
- **Findings capped at ~30** by severity, with per-family overflow noted. A 200-row report gets ignored; a 25-row report gets fixed.
- **Fix direction only** — one line, naming the owning skill. Never patch code, never paste a rewrite.
- **Priority table + leverage-ordered sequencing** — what to fix first because it unblocks or de-duplicates the most (a shared-component fix that closes eight sites outranks a lone blocker in a dead corner; say why).
- **Conformance score per section** (`applicable / conforming / violated / unverifiable`), so the trend across rounds is measurable.

### Phase 4 — Hostile self-review *(before delivering)*

Attack your own report and cut anything that fails:

- Every finding cites `file:line` **you actually read this round** — not a search count, not a filename guess.
- Every severity is justified by a concrete failure scenario. No scenario → demote or cut.
- Every negative claim names the search that justifies it.
- Every `#inferred` is honestly tagged; every `Unverifiable` names what would settle it.
- No finding contradicts the detected version lane (the top false-positive source).
- No finding is a **project convention** mistaken for a violation — consistent + deliberate is a convention (deviations table); inconsistent is a finding.
- Mode B additionally: nothing marked Resolved without a fresh re-trace this round; no ID renumbered; every section rollup says something the counts don't.

## Evidence rules

Identical to the library's other audit lanes — they bind every claim:

- **`file:line` you actually read.** Naming alone never proves behaviour.
- **`#confirmed`** — read directly in code. **`#inferred`** — deduced from surrounding structure, a comment, or a doc. Comments and docs are `#inferred` at best.
- **Negative claims name their search.** "No fixture disposes the container" requires the search that establishes it.
- **Static-first, execute opt-in.** Default evidence is read code. Running builds / type-checks / tests / linters, or probing a live system, happens only when the user explicitly opts in for this audit — and execution **corroborates** a code trace, never replaces it. Otherwise shell use stays read-only (`ls`, `grep`, `find`, `git log`, `cat`).
- **A red build/test state on arrival is a finding to report**, not yours to fix.
- **Never upgrade `#inferred` to `#confirmed`** to make a metrics row look clean.

## Severity

The library's standard table (`CLAUDE.md`), applied to conformance:

| Severity | Means here |
|---|---|
| **blocker** | Ships a bug, breaks a hard rule, or leaks something (a secret in a public bundle/log, sync-over-async, shared mutable state, a test that asserts nothing) |
| **major** | Design/correctness issue that will hurt soon (wrong pattern, leaky layering, missing failure state, order-dependent tests) |
| **minor** | Style, naming, or small inconsistency |
| **nit** | Optional preference |

Impact qualifiers after the severity are welcome (`major (8 sites, all in the orders module)`).

## Read-only contract

`Write`/`Edit` exist **solely** for the report under `docs/audits/`. Never fix, refactor, reformat, or "quickly correct" anything found, however trivial — even when the fix is one character. Note it as a finding and hand it to the stack agent that owns remediation. An auditor that edits product code cannot be trusted about what it found.

## Output contract

```
Mode A — BASELINE · <plugin> conformance — <repo/path>
Detected: <the stack's version lane, one line>
Evidence mode: static | static + <opted-in commands>
Applicability: <n> sections applicable · <n> N/A (<letters>) · <n> unknown
Coverage: <n> files in scope · <n> read · excluded: <dirs>
Report: docs/audits/<file>.md
Findings: <n> blocker · <n> major · <n> minor · <n> nit   (conformance <n>/<n> checks)
Highest-leverage item: <one line>
Open questions: <count + the one that most needs an owner>
```

```
Mode B — RE-AUDIT · <plugin> conformance — round <N>
Prior round: docs/audits/<file>.md (<date>)
Re-verify scope: <tiers actually covered>
Movement: Resolved <n> · Still open <n> · Regressed <n> · New <n>   (conformance <x%> → <y%>)
Report: docs/audits/<file>.md
Highest-leverage remaining: <one line>
```

## When uncertain

- A check is ambiguous → read the owning skill named in the checklist section before verdicting. Don't guess a rule you can look up.
- The codebase consistently does something different on purpose → **deviations table** + one question for the owner, not a finding.
- A verdict you can't settle statically → `Unverifiable` + what would settle it. Never guess to complete a row.
- Scope ambiguity that changes what gets audited (a monorepo with three apps, a legacy directory) → ask **one** question; smaller ambiguities become a stated assumption in the report.
- Tempted to fix while auditing → don't. Read-only is the contract that makes the report trustworthy.
