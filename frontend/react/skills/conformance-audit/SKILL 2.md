---
name: fe-react-conformance-audit
description: Use to audit a whole React/Next.js codebase against the fe-react plugin's own conventions, producing a saved, re-runnable findings report in `docs/audits/`. Read-only — it never fixes. Triggers "audit our codebase against the plugin conventions", "does this app follow the fe-react rules", "re-audit — what did we fix since last round". Not for one diff (`fe-react-reviewer`), code vs a product spec (`ep-spec-compliance-audit`), or fixing anything (the `fe-react` agent).
---

# fe-react Conformance Audit

Audit an existing React / Next.js codebase against **the conventions this plugin defines** — the FE React code rules in `CLAUDE.md` plus the hard rules each `frontend/react/skills/*` skill owns — and produce **one saved report** someone can act on without re-doing the work: every finding evidenced at `file:line`, severity-tabled, mapped to the skill that owns the fix.

The rule set is fixed and known in advance (unlike a spec audit) and the scope is the whole app (unlike a feature audit). That is what makes it a **one-call** job: no spec to consolidate, no feature to scope — point it at the repo and it sweeps.

This is **read-only analysis on product code**. The audit points; the `fe-react` agent fixes. The only files it writes are its own reports.

**Announce at start:** "I'm using the `fe-react-conformance-audit` skill in Mode A (baseline) / Mode B (re-audit) on `<repo/path>`."

## Read before sweeping

1. [`references/conformance-checklist.md`](references/conformance-checklist.md) — the 19 lettered sections, every check, how to find violations, and the severity each carries. **Read it end-to-end** before Phase 2; it is the audit's spine.
2. [`references/report-template.md`](references/report-template.md) — the Round-1 and Round-N report skeletons. Read it before Phase 3.

Load the **owning skill's `SKILL.md`** (named per section in the checklist) whenever a check is ambiguous, version-keyed, or you are about to write a fix direction for it. The checklist carries the invariant; the skill carries the reasoning and the correct form. When the checklist and the owning skill disagree, **the skill wins** — and that disagreement is itself worth reporting.

## The fence — what this is not

| Job | Owner | Why not this skill |
|---|---|---|
| Review one diff / a few files, inline severity table | [`fe-react-reviewer`](../reviewer/SKILL.md) | No saved artifact, no round tracking, no whole-repo sweep. This skill **reuses** its checklists at repo scale |
| Code vs a written spec / stories / ACs | `ep-spec-compliance-audit` (or the `code-auditor` agent) | Their spine is a requirement register built from *the user's* sources; this skill's spine is *the plugin's* rules |
| "How does feature X actually work / where is it defective" | `ep-feature-audit` | Behaviour tracing of one area, no fixed rule set |
| Multi-lane audit engagement, stakeholder report, other stacks | `code-auditor` agent | Stack-agnostic and lane-driven. Hand off when the ask grows past "does the React code follow our conventions" |
| Attacking authz / injection / DAST | `qa-security` peer | This inventories gates; it does not attack them |
| Running axe / Lighthouse / E2E to *prove* a11y or perf | `qa-ui-typescript` / `qa-security` peers | Static conformance only — see the evidence policy |
| Applying any fix found here | `fe-react` agent (Mode FIX / EXTEND) | Read-only is the contract that makes the report trustworthy |

## Two modes

| | **Mode A — BASELINE** | **Mode B — RE-AUDIT** |
|---|---|---|
| Trigger | No prior conformance report for this repo | A prior `…-fe-react-conformance-r<N>.md` exists |
| Spine | The 19 lettered sections; findings numbered within them (`B3`, `M1`…) | Reload the prior round; **reuse its section letters and finding IDs verbatim** |
| Work | Applicability matrix → full sweep → findings | Re-trace each finding **fresh** → sweep its defect family → new findings get the next free ID |
| Output | `…-fe-react-conformance-r1.md` | `…-fe-react-conformance-r<N>.md`, every finding prefixed **Resolved** / **Resolved (differently)** / **Still open** / **Still open (regressed)** / **New** |

**Defaulting:** check `docs/audits/` first. If a conformance report exists for this repo, enter **Mode B** and say so. Never silently renumber — the whole point of the rounds is that "23 open at r1 → 9 at r2" is a real, comparable claim, and renumbering destroys it. Propose a fresh baseline only when the codebase has changed so broadly that the old spine misleads, and say why.

## Artifacts

Every run writes one file to `docs/audits/` on the current branch:

```
docs/audits/<YY-MM-DD-HHmm>-fe-react-conformance-r<N>.md
```

Rounds are additive — never overwrite or regenerate a previous round. **The report is its own register:** section letters, finding IDs, and defect families are the stable spine every later round reuses. There is no separate requirements file (that belongs to the SPEC lane of `code-auditor`), because the requirements here *are* the plugin's rules.

Create `docs/audits/` if absent. If the repo has a different audits convention already in use, follow it and say so.

## Phases

### Phase 0 — Orient & version gate *(never skip)*

Half of all false findings come from auditing a project against a version lane it isn't on. Detect before you judge:

```bash
cat package.json                                   # react, next, deps, scripts
ls next.config.* vite.config.* 2>/dev/null         # render target
ls -d app src/app pages src/pages 2>/dev/null      # App Router vs Pages Router vs SPA
cat tsconfig.json                                  # strict, paths
ls pnpm-lock.yaml package-lock.json yarn.lock bun.lockb 2>/dev/null   # package manager
ls .eslintrc* eslint.config.* .prettierrc* 2>/dev/null
git log --oneline -5                               # recency, active lane
```

Record: **React major** (18/19) · **Next major** (14/15/none) · **render target** (App Router / Pages Router / Vite SPA) · **React Compiler** on/off (`experimental.reactCompiler` or `babel-plugin-react-compiler`) · **component library** · **styling authority** · **TS strictness** · **package manager** · **repo size** (file counts).

**The version rule binds every finding.** `forwardRef` is a finding only on React 19. Hand-rolled `useMemo`/`useCallback` are a finding only where the Compiler is on. Missing `useActionState`/`useOptimistic`/`use()` is *never* a finding on React 18. Missing App-Router APIs is never a finding on a Vite SPA. Never flag a down-level project for lacking an up-level API — write the detected lane at the top of the report so every reader can check your work.

Then read **2–3 representative files** (a route/page, a shared component, a data hook or server util) to calibrate what "normal here" looks like. A deliberate project convention that differs from the plugin's default is a **noted deviation**, not automatically a finding — say which it is.

### Phase 1 — Applicability matrix

Not every section applies. Decide, per section, **Applicable / Not applicable / Unknown**, with the probe that decided it, before sweeping — a section marked N/A produces no findings and no false confidence.

| Section | Applies when | Probe |
|---|---|---|
| B (RSC boundary), C (routing), L (SEO) | App Router | `ls app src/app` |
| P (localization) | An i18n lib or locale routing exists | `grep -l "next-intl\|react-i18next\|i18next" package.json` |
| Q (PWA / offline) | A manifest or service worker exists, or the product requires offline | `ls public/manifest* app/manifest.* public/sw.js`, `grep serwist\|vite-plugin-pwa package.json` |
| R (auth wiring) | An auth SDK is installed | `grep "auth0\|next-auth\|amazon-cognito\|msal" package.json` |
| E-realtime | A WS/SSE surface exists | `grep -rl "EventSource\|new WebSocket\|socket.io" src app` |
| O (component tests) | A test runner is configured | `grep "vitest\|jest" package.json` — **absent is itself finding O1** |

Everything else (A, D, F, G, H, I, J, K, M, N, S) applies to every React codebase in every lane.

State the matrix in the report. "Not applicable" must name its probe; "Unknown" must name what would settle it.

### Phase 2 — Sweep, section by section

Work the checklist in letter order. For each check:

1. **Locate** candidates with the checklist's grep/glob recipe (fast, mechanical, repeatable across rounds).
2. **Read the code** at each hit. A grep hit is a *lead*, never a finding — the surrounding code decides.
3. **Verdict** the check: `Conforms` · `Violated` (→ a finding) · `Partial` (conforms in places, violated in others — finding, scoped) · `Unverifiable` (say what would settle it).
4. **Group repeats.** Twenty `key={index}` sites are **one finding** with a count and 3–5 cited examples plus "+15 more (`<the grep that found them>`)" — not twenty findings. The grouped set is the finding's **defect family**, and Mode B sweeps the whole family.

**Coverage policy.** Greps run over the whole source tree; reading is targeted at hits. Declare both in the report: files in scope, files actually read, and any directory deliberately excluded (`node_modules`, `.next`, `dist`, generated clients, vendored code). An audit that quietly skipped `src/legacy/` is misleading; one that says it skipped it is useful.

**Do not start writing the report mid-sweep.** Findings written while tracing anchor on early impressions and mis-rank severity.

### Phase 3 — Report

Fill the Mode A or Mode B skeleton in [`references/report-template.md`](references/report-template.md). Non-negotiable parts:

- **Detected lane + applicability matrix** at the top — every finding is read against it.
- **Every section closes with a rollup summary** — 2–4 sentences of *judgment* (state · pattern · next action), distinct from the arithmetic. One per section, never per finding. "Nine of eleven checks conform; the two failures are both the same missing three-state pattern in the two oldest routes, so the fix is one shared hook, not two patches" is a rollup. Walking the rows is not.
- **Findings capped at ~30** by severity, with per-family overflow noted (`+15 more in this family`). A 200-row report gets ignored; a 25-row report gets fixed.
- **Fix direction only** — one line, naming the owning skill. Never patch code, never paste a rewrite.
- **Priority table + leverage-ordered sequencing** — what to fix first because it unblocks or de-duplicates the most (a shared component fix that closes eight sites outranks a lone blocker in a dead route; say why).
- **Conformance score per section**, so the trend across rounds is measurable: `checks applicable / conforming / violated / unverifiable`.

### Phase 4 — Hostile self-review *(before delivering)*

Attack your own report and cut anything that fails:

- Every finding cites `file:line` **you actually read this round** — not a grep count, not a filename guess.
- Every severity is justified by a concrete failure scenario. No scenario → demote or cut.
- Every negative claim names the search that justifies it ("no `error.tsx` anywhere under `app/` — `find app -name 'error.tsx'` → 0 results").
- Every `#inferred` is honestly tagged; every `Unverifiable` names what would settle it.
- No finding contradicts the detected version lane (the top false-positive source).
- No finding is a **project convention** you mistook for a violation — if the codebase does something consistently and deliberately that differs from the plugin default, it's a noted deviation with a rationale question, not a defect.
- Mode B additionally: nothing is marked Resolved without a fresh re-trace this round; no ID was renumbered; every section rollup says something the counts don't.

## Evidence rules

Identical to the library's other audits — they bind every claim:

- **`file:line` you actually read.** Naming alone never proves behaviour (`SafeUserProvider.tsx` proves nothing about safety).
- **`#confirmed`** — read directly in code. **`#inferred`** — deduced from surrounding structure, a comment, or a doc. Comments and docs are `#inferred` at best.
- **Negative claims name their search.** "No route sets `metadata`" requires the glob/grep that establishes it.
- **Static-first, execute opt-in.** Default evidence is read code. Running `build` / `tsc --noEmit` / `lint` / `test`, or probing a live app, happens only when the user opts in for this audit — and execution **corroborates** a code trace, never replaces it. Bash stays read-only (`ls`, `grep`, `find`, `git log`, `cat`) otherwise.
- **A red build/test state on arrival is a finding to report**, not yours to fix (section A).
- **Never upgrade `#inferred` to `#confirmed`** to make a metrics row look clean.

## Severity

The library's standard table (`CLAUDE.md`), applied to conformance:

| Severity | Means here | Examples |
|---|---|---|
| **blocker** | Ships a bug, breaks a hard rule, or leaks something | Server secret imported into a `'use client'` module · hook inside a conditional · `await` in a client component body · mutable module-level state holding user data |
| **major** | Design/correctness issue that will hurt soon | Blanket `'use client'` on a route · `useEffect` deriving state · server data in a client store · no three-state data region · `<div onClick>` navigation · index keys on reorderable lists · two styling authorities |
| **minor** | Style, naming, or small inconsistency | Missing `data-testid` on an interactive element · unmemoized non-hot context · missing page title |
| **nit** | Optional preference | kebab-case testid segments · import ordering |

Impact qualifiers after the severity are welcome (`major (8 sites, all in the orders feature)`).

## Read-only contract

`Write`/`Edit` exist **solely** for the report under `docs/audits/`. Never fix, refactor, reformat, add a missing `data-testid`, or "quickly correct" anything found, however trivial — even when the fix is one character. Note it as a finding like any other and hand it to the `fe-react` agent. An auditor that edits product code cannot be trusted about what it found.

## Output contract

Report back in chat (the file holds the detail):

```
Mode A — BASELINE · fe-react conformance — <repo/path>
Detected: React <18|19> · Next <14|15|n/a> · <App Router|Pages Router|Vite SPA> · Compiler <on|off> · <library> · <styling authority> · TS strict <on|off>
Evidence mode: static | static + <opted-in commands>
Applicability: <n> sections applicable · <n> N/A (<letters>) · <n> unknown
Coverage: <n> files in scope · <n> read · excluded: <dirs>
Report: docs/audits/<file>.md
Findings: <n> blocker · <n> major · <n> minor · <n> nit   (conformance <n>/<n> checks)
Highest-leverage item: <one line>
Open questions: <count + the one that most needs an owner>
```

```
Mode B — RE-AUDIT · fe-react conformance — round <N>
Prior round: docs/audits/<file>.md (<date>)
Re-verify scope: <tiers actually covered>
Movement: Resolved <n> · Still open <n> · Regressed <n> · New <n>   (conformance <x%> → <y%>)
Report: docs/audits/<file>.md
Highest-leverage remaining: <one line>
```

## Handoffs

- **Apply the fixes** → the `fe-react` agent, Mode FIX (a defect) or EXTEND (a slice). The priority table is the handoff artifact.
- **One file / one diff instead** → [`fe-react-reviewer`](../reviewer/SKILL.md).
- **Code vs a spec or story set** → `ep-spec-compliance-audit` / the `code-auditor` agent (SPEC lane).
- **"What does this feature actually do"** → `ep-feature-audit`.
- **Prove the a11y / perf / security findings dynamically** → peers `qa-ui-typescript` (axe, E2E), `qa-security` (DAST/SCA/access control), `qa-cicd-typescript` (gate the conformance run in CI).
- **Design-craft altitude** (is it *good*, not just conforming) → `design/web-design-guidelines` (code-level) and `design/ux-heuristics` (experience-level), run by the `fe-react` agent's Phase 5.
- **Section M findings** double as the `missing-testids.md` handshake input for `qa-ui-typescript` / [`testability`](../testability/SKILL.md).

## When uncertain

- A check is ambiguous → read the owning skill's `SKILL.md` before verdicting. Don't guess a rule you can look up.
- The codebase consistently does something different on purpose → note it as a **deviation** with one question for the owner, not a finding. Consistency plus intent is a convention; inconsistency is a finding.
- A verdict you can't settle statically → `Unverifiable` + what would settle it (a run, a screenshot, an owner's answer). Never guess to complete a row.
- Scope ambiguity that changes what gets audited (monorepo with three apps, a legacy directory) → ask **one** question; smaller ambiguities become a stated assumption in the report.
- Tempted to fix while auditing → don't. Read-only is the contract.
