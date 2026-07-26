# Report templates — fe-react conformance audit

Two skeletons: **Round 1** (Mode A, baseline) and **Round N** (Mode B, re-audit). Fill them literally — the section order, the rollups, and the ID grammar are what make rounds comparable.

Saved to `docs/audits/<NNN>-fe-react-conformance-r<N>.md`. Never overwrite a previous round.

**ID grammar:** `<SectionLetter><n>` — `B3`, `M1`, `K7`. The number is the **check number** from the checklist, so a finding's ID says exactly which rule it breaks and stays stable forever. If one check produces two genuinely distinct findings, suffix them (`B3a`, `B3b`) rather than inventing a new number.

---

## Round 1 (Mode A — baseline)

````markdown
# fe-react Conformance Audit — <repo name> — Round 1

**Date:** <YYYY-MM-DD> · **Branch:** <branch> · **Commit:** <short sha>
**Auditor:** `fe-react-standards-audit` (read-only — no product code was changed)

## 1. Detected lane

| | |
|---|---|
| React | <18 \| 19> |
| Next.js | <14 \| 15 \| n/a (Vite SPA)> |
| Render target | <App Router \| Pages Router \| Vite SPA> |
| React Compiler | <on \| off> |
| Component library | <MUI \| Mantine \| Chakra \| shadcn \| none> |
| Styling authority | <library style API \| Tailwind \| CSS Modules \| mixed ⚠️> |
| TypeScript | strict <on \| off> |
| Package manager | <pnpm \| npm \| yarn \| bun> |
| Test runner | <Vitest \| Jest \| none> |

Every finding below is judged **against this lane**. Down-level projects are never flagged for
lacking an up-level API.

## 2. Scope & coverage

- **In scope:** <dirs>
- **Excluded:** <node_modules, .next, dist, generated clients, vendored code, and any deliberate exclusion — say why>
- **Files in scope:** <n> · **files read:** <n>
- **Evidence mode:** static <| + opted-in commands: `<cmd>` → `<result>`>

## 3. Applicability matrix

| Section | Status | Decided by |
|---|---|---|
| A — Build health & version lane | Applicable | always |
| B — RSC & `'use client'` boundary | Applicable / **N/A** | `ls app` → <result> |
| … one row per section A–S … | | |

## 4. Conformance summary

| Section | Applicable checks | Conforming | Violated | Unverifiable |
|---|---|---|---|---|
| A — Build health & version lane | 7 | 5 | 2 | 0 |
| … | | | | |
| **Total** | **<n>** | **<n>** | **<n>** | **<n>** |

**Findings:** <n> blocker · <n> major · <n> minor · <n> nit
**Overall conformance:** <n>/<n> applicable checks (<x>%)

## 5. Findings by section

### A — Build health, version lane & migration hygiene

| ID | Sev | Check | Evidence | Fix direction (owner) |
|---|---|---|---|---|
| A3 | major | No stranded half-migration | `pages/orders.tsx:1` + `app/orders/page.tsx:1` — both live, `next/router` still imported at `src/hooks/useNav.ts:4` `#confirmed` | Finish the Pages→App port for `/orders` or delete the dead route — `migration` |

**Rollup —A:** <2–4 sentences of judgment: what state this section is in, the *pattern* behind
its failures, and the next action. Never a walk through the rows.>

### B — RSC & the `'use client'` boundary

| ID | Sev | Check | Evidence | Fix direction (owner) |
|---|---|---|---|---|
| B1 | major (11 sites) | `'use client'` on the smallest leaf | `app/(shop)/cart/page.tsx:1`, `app/orders/page.tsx:1`, `app/account/page.tsx:1` `#confirmed`; +8 more (`rg -l "^'use client'" app \| grep page.tsx`) | Move the directive to the interactive leaf components; keep pages server — `component-writer` |

**Rollup — B:** <…>

*(…one subsection per applicable section, each closing with its rollup…)*

## 6. Defect families

Findings that share one root cause and one fix. Fixing the family head closes the members.

| Family | Head | Members | Sites | One fix closes |
|---|---|---|---|---|
| Blanket client boundary | B1 | B2, K7 | 11 | 11 routes' bundle size + 3 hydration issues |

## 7. Priority — leverage-ordered

Not severity order — **leverage** order: what unblocks or de-duplicates the most.

| # | Item | Sev | Why first | Effort |
|---|---|---|---|---|
| 1 | B1 (family head) | major | One directive move per route closes 11 sites and shrinks the client bundle across the app | M |
| 2 | S6 | blocker | A committed key is a live exposure regardless of anything else here | S |

## 8. Noted deviations (not findings)

Things this codebase does differently from the plugin defaults, **consistently and apparently on
purpose**. Recorded so a later round doesn't re-litigate them — each carries one question for the owner.

| # | Deviation | Where | Question for the owner |
|---|---|---|---|
| D-1 | Data fetching via SWR rather than TanStack Query | app-wide `#confirmed` | Intentional standard? If so it should be written down; the plugin's rules apply either way |

## 9. Open questions

| # | Question | Blocks | Needs |
|---|---|---|---|
| Q-1 | Is `src/legacy/` still shipped? | Whether 14 findings there matter | Owner's answer |

## 10. Unverifiable

| ID | Check | Why | What would settle it |
|---|---|---|---|
| K4 | Large lists virtualized | Row counts come from a runtime API | A production data volume figure, or an opt-in run |

## 11. Handoff

- **Fixes:** `fe-react` agent (Mode FIX for defects, EXTEND for missing capability). Work the priority table top-down.
- **Testids (section M):** feed to `qa-ui-typescript` as `missing-testids.md`.
- **Security-flavoured findings (R2–R4, S6):** `qa-security` owns proving exploitability.
- **Next round:** re-run this skill; it enters Mode B and reuses every ID above.
````

---

## Round N (Mode B — re-audit)

````markdown
# fe-react Conformance Audit — <repo name> — Round <N>

**Date:** <YYYY-MM-DD> · **Branch:** <branch> · **Commit:** <short sha>
**Prior round:** `docs/audits/<file>-r<N-1>.md` (<date>, commit <sha>)
**Auditor:** `fe-react-standards-audit` (read-only)

## 1. Movement

| | Count |
|---|---|
| Resolved | <n> |
| Resolved (differently) | <n> |
| Still open | <n> |
| Still open (regressed) | <n> |
| New | <n> |
| **Conformance** | **<x>% → <y>%** (<n>/<n> applicable checks) |

**Lane changes since r<N-1>:** <"none" | "React 18 → 19; Compiler enabled" — this can turn prior
findings stale or create new ones; say which>

**Re-verify scope — tiers actually covered:**
1. Every non-conforming item from r<N-1> — <done / partial>
2. Everything in each such item's section or defect family — <done / partial>
3. Previously-conforming checks whose cited files the diff touched (`git diff --name-only <sha>..HEAD`) — <done / partial>

## 2. Findings by section

Every prior ID reappears with a status prefix. IDs are **never** renumbered or reused.

### B — RSC & the `'use client'` boundary

| ID | Status | Sev | Evidence **this round** | Note |
|---|---|---|---|---|
| B1 | **Resolved** | — | `app/(shop)/cart/page.tsx:1` no longer carries the directive; it now sits on `CartActions.tsx:1` `#confirmed`. Family swept: 11/11 sites re-read | — |
| B6 | **Still open (regressed)** | major | `app/orders/page.tsx:22-31` — three sequential `await`s, was two at r1 `#confirmed` | New code added to the same waterfall |
| B9 | **New** | major | `app/reports/page.tsx:1` — new route ships blanket `'use client'` `#confirmed` | Next free number in section B |

**Rollup — B:** <2–4 sentences: state, pattern, next action. E.g. "The boundary work landed
everywhere it was flagged, but the same mistake reappeared on a route added after r1 — the rule
isn't in the team's review checklist yet, which is the actual fix.">

*(…one subsection per section, each closing with its rollup…)*

## 3. Closed this round

The credit half — not optional. Resolved items with the evidence that closed them.

| ID | Was | Closed by | Verified at |
|---|---|---|---|
| B1 | major, 11 sites | Directive pushed to leaves | `CartActions.tsx:1` + 10 more, re-read this round |

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
- **Resolved is claimed only after re-reading the code this round.** A commit, a ticket, a green test, or a team's word are leads — never evidence.
- **IDs are permanent.** New findings take the next free number in their section; nothing is renumbered, nothing is reused.
- **Findings capped ~30**, largest families collapsed with `+n more (<the grep>)`. Prefer one grouped finding with a count over twenty rows saying the same thing.
- **Fix direction only** — one line, naming the owning skill. Never a patch.
- **Deviations are separate from findings.** Consistent-and-intentional differences from the plugin default belong in the deviations table with a question, not in the findings table with a severity.
- **Negative claims name their search** — inline, in the evidence cell.
