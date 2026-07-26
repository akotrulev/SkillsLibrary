# Report templates — conformance audit (all stacks)

Two skeletons: **Round 1** (Mode A, baseline) and **Round N** (Mode B, re-audit). Fill them literally — the section order, the rollups, and the ID grammar are what make rounds comparable.

Saved to `docs/audits/<NNN>-<plugin>-conformance-r<N>.md`, resolved under the project being audited (never this skills-library checkout or a global config directory, unless the user explicitly asks for a global copy). Never overwrite a previous round.

**ID grammar:** `<SectionLetter><CheckNumber>` from the stack's checklist — `B3`, `M1`, `G7`. The number *is* the check number, so an ID names the rule it breaks and stays stable forever. Two distinct findings from one check get suffixes (`B3a`, `B3b`), never a new number.

---

## Round 1 (Mode A — baseline)

````markdown
# <plugin> Conformance Audit — <repo name> — Round 1

**Date:** <YYYY-MM-DD> · **Branch:** <branch> · **Commit:** <short sha>
**Auditor:** `<plugin>-conformance-audit` (read-only — no product code was changed)

## 1. Detected lane

<The stack skill's detection table — language/framework majors, build tooling, the
libraries and lanes that decide which rules apply, strictness settings, test runner.>

Every finding below is judged **against this lane**. Down-level projects are never flagged for
lacking an up-level API.

## 2. Scope & coverage

- **In scope:** <dirs>
- **Excluded:** <dependencies, build output, generated code, vendored code, and any deliberate exclusion — say why>
- **Files in scope:** <n> · **files read:** <n>
- **Evidence mode:** static <| + opted-in commands: `<cmd>` → `<result>`>

## 3. Applicability matrix

| Section | Status | Decided by |
|---|---|---|
| A — <name> | Applicable | always |
| B — <name> | Applicable / **N/A** | <the probe> → <result> |
| … one row per section … | | |

## 4. Conformance summary

| Section | Applicable checks | Conforming | Violated | Unverifiable |
|---|---|---|---|---|
| A — <name> | 8 | 6 | 2 | 0 |
| … | | | | |
| **Total** | **<n>** | **<n>** | **<n>** | **<n>** |

**Findings:** <n> blocker · <n> major · <n> minor · <n> nit
**Overall conformance:** <n>/<n> applicable checks (<x>%)

## 5. Findings by section

### A — <section name>

| ID | Sev | Check | Evidence | Fix direction (owner) |
|---|---|---|---|---|
| A4 | blocker | <the invariant> | `<path>:<line>` — <what the code actually does> `#confirmed` | <one line> — `<owning-skill>` |

**Rollup — A:** <2–4 sentences of judgment: what state this section is in, the *pattern* behind its
failures, and the next action. Never a walk through the rows.>

### B — <section name>

| ID | Sev | Check | Evidence | Fix direction (owner) |
|---|---|---|---|---|
| B1 | major (11 sites) | <the invariant> | `<path>:<line>`, `<path>:<line>`, `<path>:<line>` `#confirmed`; +8 more (`<the search>`) | <one line> — `<owning-skill>` |

**Rollup — B:** <…>

*(…one subsection per applicable section, each closing with its rollup…)*

## 6. Defect families

Findings that share one root cause and one fix. Fixing the family head closes the members.

| Family | Head | Members | Sites | One fix closes |
|---|---|---|---|---|
| <name> | B1 | B2, K7 | 11 | <what the head's fix resolves> |

## 7. Priority — leverage-ordered

Not severity order — **leverage** order: what unblocks or de-duplicates the most.

| # | Item | Sev | Why first | Effort |
|---|---|---|---|---|
| 1 | B1 (family head) | major | <one fix closes 11 sites> | M |
| 2 | A4 | blocker | <live exposure regardless of anything else here> | S |

## 8. Noted deviations (not findings)

Things this codebase does differently from the plugin defaults, **consistently and apparently on
purpose**. Recorded so a later round doesn't re-litigate them — each carries one question for the owner.

| # | Deviation | Where | Question for the owner |
|---|---|---|---|
| D-1 | <what differs> | <where> `#confirmed` | Intentional standard? If so it should be written down |

## 9. Open questions

| # | Question | Blocks | Needs |
|---|---|---|---|
| Q-1 | <question> | <what it blocks> | Owner's answer |

## 10. Unverifiable

| ID | Check | Why | What would settle it |
|---|---|---|---|
| <id> | <check> | <why static reading can't settle it> | <a run, a metric, an owner's answer> |

## 11. Handoff

- **Fixes:** <the owning stack agent> (Mode FIX for defects, EXTEND for missing capability). Work the priority table top-down.
- **Peer-owned findings:** <which findings belong to which peer agent and why>
- **Next round:** re-run this skill; it enters Mode B and reuses every ID above.
````

---

## Round N (Mode B — re-audit)

````markdown
# <plugin> Conformance Audit — <repo name> — Round <N>

**Date:** <YYYY-MM-DD> · **Branch:** <branch> · **Commit:** <short sha>
**Prior round:** `docs/audits/<file>-r<N-1>.md` (<date>, commit <sha>)
**Auditor:** `<plugin>-conformance-audit` (read-only)

## 1. Movement

| | Count |
|---|---|
| Resolved | <n> |
| Resolved (differently) | <n> |
| Still open | <n> |
| Still open (regressed) | <n> |
| New | <n> |
| **Conformance** | **<x>% → <y>%** (<n>/<n> applicable checks) |

**Lane changes since r<N-1>:** <"none" | what moved — a major upgrade can make prior findings stale
or create new ones; say which>

**Re-verify scope — tiers actually covered:**
1. Every non-conforming item from r<N-1> — <done / partial>
2. Everything in each such item's section or defect family — <done / partial>
3. Previously-conforming checks whose cited files the diff touched (`git diff --name-only <sha>..HEAD`) — <done / partial>

## 2. Findings by section

Every prior ID reappears with a status prefix. IDs are **never** renumbered or reused.

### B — <section name>

| ID | Status | Sev | Evidence **this round** | Note |
|---|---|---|---|---|
| B1 | **Resolved** | — | `<path>:<line>` — <what changed> `#confirmed`. Family swept: 11/11 sites re-read | — |
| B6 | **Still open (regressed)** | major | `<path>:<line>` — <worse than r1 how> `#confirmed` | <why> |
| B9 | **New** | major | `<path>:<line>` `#confirmed` | Next free number in section B |

**Rollup — B:** <2–4 sentences: state, pattern, next action. The most useful rollups name the
*process* gap — e.g. the rule isn't in the team's review checklist yet, which is the actual fix.>

*(…one subsection per section, each closing with its rollup…)*

## 3. Closed this round

The credit half — not optional. Resolved items with the evidence that closed them.

| ID | Was | Closed by | Verified at |
|---|---|---|---|
| B1 | major, 11 sites | <what the team did> | `<path>:<line>` + n more, re-read this round |

## 4. Still open — priority (leverage-ordered)

| # | ID | Sev | Rounds open | Why now | Effort |
|---|---|---|---|---|---|

## 5. Open questions

<carry forward unanswered ones with their original numbers; mark newly answered ones **Answered r<N>** with the answer>

## 6. Handoff

<same as Round 1>
````

---

## Rules the templates encode

- **Every section gets a rollup.** One per section, 2–4 sentences of judgment — state, pattern, next action. Not a summary of the rows; something the row counts can't say.
- **Resolved is claimed only after re-reading the code this round.** A commit, a ticket, a green test, or the team's word are leads — never evidence.
- **IDs are permanent.** New findings take the next free number in their section; nothing is renumbered, nothing is reused.
- **Findings capped ~30**, largest families collapsed with `+n more (<the search>)`. One grouped finding with a count beats twenty rows saying the same thing.
- **Fix direction only** — one line, naming the owning skill. Never a patch.
- **Deviations are separate from findings.** Consistent-and-intentional differences from a plugin default belong in the deviations table with a question, not in the findings table with a severity.
- **Negative claims name their search** — inline, in the evidence cell.
