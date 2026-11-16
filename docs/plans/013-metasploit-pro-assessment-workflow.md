# 013 — Metasploit Pro assessment workflow (paid lane) — plan (2026-11-16)

**Goal:** Build the paid **Metasploit Pro** counterpart to the free Framework repo-assessment workflow: a multi-agent workflow that reads a repo, derives its deploy profile, and produces a **Pro-shaped** engagement package — REST/RPC-driven setup, auto-exploitation, the Vulnerability Validation Wizard, MetaModules, task chains and templated reporting — with ready-to-paste operator calls and a pre-filled scope-file skeleton. Static planning only; it executes nothing and stops at the authorization gate, exactly like the free lane.

**Status:** Not started. The free/Framework lane has landed (`security/workflows/metasploit-framework-assessment.mjs`, `/penetration-testing:assess-repo`) and is the priority; this Pro lane is secondary and deferred to this plan. Prerequisite for a real end-to-end dry-run (P1's optional step): a licensed Metasploit Pro install (and, for the Vulnerability Validation path, an InsightVM/Nexpose scan) the user controls — see Open questions.

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| A Pro-lane assessment workflow | The free Framework workflow `security/workflows/metasploit-framework-assessment.mjs` (profile → plan → review); Pro is covered only as prose in `security/metasploit-setup/references/metasploit-pro.md` | No workflow that emits a **Pro-shaped** package (REST/RPC, auto-exploit, Vuln-Validation Wizard, MetaModules, task chains, templated reports) |
| A command entry point for the Pro lane | `/penetration-testing:assess-repo` runs the **free** lane only | No `/penetration-testing:assess-repo-pro` |
| Operator-handoff + gate in the Pro output | The protocol is defined once in `security/metasploit-setup/SKILL.md`; the free workflow emits a per-test `operatorCommand` | The Pro output must emit **REST/RPC operator calls** and the **operator-run wizard steps** under the same handoff, and a Pro-specific scope-file skeleton (licensed host, API-token-as-secret, scheduled-chain windows) |
| Pro-specific profiling signals | The free profiler reads ports/deps/app | Nothing detects the signals that make Pro worthwhile — an existing InsightVM/Nexpose scan (→ Vuln-Validation), many hosts (→ auto-exploit + task chain), credential reuse at scale (→ MetaModules) |

## 2. What the Pro workflow produces (the shape)

It mirrors the free workflow's structure — three parallel readers → one synthesis → one critic — so it is a **variation, not a reinvention** (D1). The differences are all in the synthesis and in one added profiler input:

- **Profile (3 parallel, ≤3 concurrent, Sonnet/medium):** the same infra / dependency-CVE / app-auth readers as the free lane, **plus** each notes the Pro-relevant signal it sees — scanner artifacts or InsightVM/Nexpose config (→ Vulnerability Validation Wizard), host/subnet breadth (→ auto-exploitation + a task chain), and credential-reuse surface (→ the credential MetaModules).
- **Plan (barrier → 1 agent):** a **Pro-shaped** package —
  - **Setup:** the licensed Pro host and its web service (`:3790`), the REST API token (generated in the UI, non-expiring, secret-handled) or the RPC permanent token (`service.key`), the project/workspace, and a note that the Framework MCP server still covers read-only enumeration.
  - **Test plan:** per surface, the Pro mechanism — **auto-exploitation** (ranked, bounded) for breadth, the **Vulnerability Validation Wizard** where a scanner report exists, the matching **MetaModule** (Single Password Testing · Known Credentials · SSH Key Testing · Pass the Hash · Firewall Egress Testing · Passive Network Discovery · AD CS Workflows) for credential/segment work, and a **task chain** for a repeatable discover→exploit→evidence→report→cleanup sequence inside the window — each with the single proven outcome, the ATT&CK id, the availability-risk flag, and the **operator call** (the REST endpoint + `token:` header, or the UI wizard step the operator clicks).
  - **Scope-file skeleton:** the free lane's, plus the Pro host, API-token handling, and any **scheduled task-chain window** bounded by the authorization window.
  - **outOfReach / overreach:** unchanged in intent.
- **Review (1 agent):** the completeness + gate-safety critic, extended to catch a scheduled chain that would outlive the window and auto-exploitation aimed at an availability-risking target.

**Divergence carried from the reference (D4):** the agent drives Pro **only via the REST/RPC API**, and only the **read** endpoints autonomously; **auto-exploitation, the Validation Wizard, campaigns and session writes are operator-run** (the web UI's irreversible buttons), handed over under the operator-handoff protocol. The workflow itself, like the free one, **executes nothing** — it plans.

## 3. The gate for a workflow script

A `.mjs` Workflow orchestration script has **no unit-test lane in this repo** — it is not part of the Vitest/Jest project and only executes inside the Workflow engine against a live repo with real subagents. So the honest gate (D3) is:

1. **Parse-check in the engine's async-body context** — wrap the body in an async function (top-level `return`/`await` are legal there, illegal to a bare `node --check`) and `node --check` the wrapper, as the free lane was validated.
2. **Structural review** — `meta` is a pure literal with `name`/`description`/`phases`; every `agent()` call passes `{ model: 'sonnet', effort: 'medium' }`; `parallel()` width ≤ 3; no `isolation: 'worktree'`, no forks; the script returns a package and triggers no live act.
3. **A sample dry-run the user starts** — because a real run spawns subagents (token cost) and a true end-to-end Pro run needs a licensed Pro install, the one real execution is the user's, against a sample repo; its result is recorded in `As built`. The coverage floor and the telemetry smoke (§5 of plan-format) **do not apply** — there is no branch-measurable unit under test and the workflow stands up no service — and this is the deliberate, recorded deviation, not an omission.

## Decisions

**D1 — The Pro workflow is a variation of the free one, not a new design.** Same phase shape, same ≤3-parallel/Sonnet-medium/no-fork constraints, same gate-safe "plans only" stance; only the synthesis prompt/schema and one profiler signal change. *Cost:* some duplication between the two scripts, accepted so each lane is self-contained and runnable without the other.

**D2 — Executor mapped to `tooling-engineer` / stack `ts`.** Authoring a Workflow orchestration script is library-authoring; the closest catalog agent is `tooling-engineer` (agent-drivable automation surfaces), and the script is JS/TS-family, so stack `ts`. *Cost:* a mild stretch of `tooling-engineer`'s usual MCP/CLI remit; named here so no one reads it as an invented agent.

**D3 — The gate is parse + structural review + a user-run sample dry-run; no coverage floor or telemetry smoke.** A `.mjs` workflow has no unit-test lane here and stands up no service. *Cost:* the automated gate proves the script is well-formed and constraint-abiding, not that its agents produce a good plan — that is what the user's sample dry-run checks.

**D4 — The agent drives Pro only through the REST/RPC API, read endpoints autonomously; every irreversible Pro action is operator-run under the handoff.** Mirrors `references/metasploit-pro.md`. *Cost:* the workflow cannot fully "run" Pro; by design, it plans and hands the licensed, irreversible steps to the authorized human.

| Option | Verdict | Why |
|---|---|---|
| One workflow with a free/Pro flag | Rejected | Two licensing models, two output shapes, two command surfaces — a flag would fork the synthesis in-script and make each lane harder to read and run alone (D1) |
| Pro drives the web UI via browser automation | Rejected | The UI's irreversible buttons are exactly the per-act, authorization-bound steps the nine controls keep with the human; automating them defeats the gate |
| Full REST/RPC auto-execution by the agent | Rejected | Same reason — auto-exploitation and the Validation Wizard are availability-risking and authorization-bound; read endpoints only, the rest operator-run (D4) |

## Answered questions (2026-11-16)

**O1 — Build the free lane first, Pro as a plan? Yes.** The user set the free/open-source Framework workflow as the priority (landed) and this Pro lane as secondary, to be implemented later from this plan.

**O2 — Must a blocked/declined step hand off to the operator? Yes.** Where a live step is gated or the assistant's own safety layer declines the tool call, the assistant states the exact next command, the authorized user runs it and pastes the result, and the run continues (the operator-handoff protocol in `metasploit-setup`). The Pro output bakes this in as the per-test operator call.

## Open questions

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| Q1 | Is there a licensed Metasploit Pro install (and an InsightVM/Nexpose scan for the Validation path) to dry-run against? | yes → P1's sample dry-run is real end-to-end · no → P1 dry-runs the planning half only, Pro execution unverified | P1's `As built` evidence, nothing else | the user |

## 4. Tasks

### P1 — security/workflows: the Metasploit Pro assessment workflow + its command

**Stack:** `ts` · **Agent:** `tooling-engineer`
**Deliverable:** `security/workflows/metasploit-pro-assessment.mjs` exists and parses in the engine's async-body context; its synthesis agent emits the §2 Pro-shaped package (REST/RPC setup, auto-exploit / Vulnerability-Validation / MetaModule / task-chain tests each with a proven outcome, ATT&CK id, availability-risk flag and an **operator call**, plus the Pro-specific scope-file skeleton); `security/commands/assess-repo-pro.md` launches it; both are registered in `.claude-plugin/marketplace.json` under `penetration-testing`. The workflow executes nothing live.
**Depends on:** none. (Shares the `penetration-testing` plugin tree with the free lane but overlaps no file it must not also edit — it adds its own script + command and appends to the same `marketplace.json` arrays.)
**Budget:** ~90k — CLAUDE.md 25k, this plan §2/§3/D1–D4 ~8k, the free workflow `security/workflows/metasploit-framework-assessment.mjs` as the pattern ~6k, `security/metasploit-setup/references/metasploit-pro.md` §REST/RPC/MetaModules/task-chains ~6k, the `assess-repo.md` command as the command pattern ~2k, writes (script + command + manifest edit) ~25k, the wrapped parse-check + structural-review output ~10k.
**Gate (this is the last runnable task, so it runs the whole set): own checks** — `node --check` on the async-wrapped script (per §3 step 1, the free lane's method), the §3 step 2 structural review, and the §3 step 3 sample dry-run **only if** the user says to start it (it spawns subagents). Do not run the project's other suites; the coverage floor and telemetry smoke do not apply (D3).

- Copy `metasploit-framework-assessment.mjs` as the skeleton; keep `meta` a pure literal, the three-reader `parallel()` (width 3), and the `SONNET`/`SAFETY` constants.
- Extend the three profiler prompts to note the Pro signal each sees (scanner/InsightVM config, host breadth, credential-reuse surface).
- Replace the synthesis prompt/schema with the §2 Pro package: REST/RPC setup, the Pro mechanism per surface, the per-test `operatorCall`, and the Pro-specific scope-file skeleton; keep `provenOutcome` single-valued (no OR) and `availabilityRisk` flagged.
- Extend the critic to catch a scheduled chain outliving the window and auto-exploitation at an availability-risking target.
- Write `assess-repo-pro.md` from the `assess-repo.md` pattern — same "planning only / operator-handoff / stops at the gate" framing, pointing at the Pro script, and naming the licensed Pro install as a prerequisite for live execution.
- Register the script is not listed in `marketplace.json` (workflows are not a manifest array); register **only** the command under `commands`.
- **Not in P1:** the catalog/doc updates and the plan filing (DOC1); any real Pro execution beyond the user's optional sample dry-run.

### DOC1 — docs: catalog, cross-links and filing the plan

**Stack:** `docs` · **Agent:** `be-documenter`
**Deliverable:** `docs/skills-catalog.md` reflects the Pro workflow and `/penetration-testing:assess-repo-pro` (command counts recomputed, the `penetration-testing` slash-surface row and the Metasploit-workflow paragraph updated); `security/metasploit-setup/references/metasploit-pro.md` cross-links the workflow; the plan is moved to `docs/plans/implemented/`.
**Depends on:** P1 (documents what P1 landed, from the code).
**Budget:** ~45k — CLAUDE.md 25k, this plan ~5k, `docs/skills-catalog.md` the two command-count lines + the pentest row + the Metasploit-workflow paragraph ~8k, the reference cross-link ~2k, writes ~5k.
**Gate: none** — doc-only; the documenter's own doc lint over the files it touched is the check.

- Recompute the command counts in `docs/skills-catalog.md` (files + registrations) from the manifest, add `:assess-repo-pro` to the `penetration-testing` row, and extend the Metasploit-workflow paragraph to name both lanes.
- Cross-link the workflow from `references/metasploit-pro.md` (the "agent-drivable surface" section).
- File the plan per the close-out: rewrite `Status:`, `git mv` to `docs/plans/implemented/`, add the README row where one exists.

## Close-out — every task

Before you stop, in this order, in this file. Another task may be running in this working tree:
re-read this file immediately before these edits, and touch only your own task block, your own prompt
block and the line that says which have landed.

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified. When a task is running beside you, leave it: the next task that waits for you rewrites it.
5. **Commit the work** — the code, its tests and these plan edits together, on the current branch (under
   Plan Queue, the plan's branch in its worktree; never check out the default branch), adding only your
   own files, by path — never `git add -A`. Your prompt block is still in the plan.
6. **Merge, gate task only** — if you are the task that ran the whole set and this plan runs on its own
   branch, merge the default branch into it now, resolve every conflict by keeping both sides' rows,
   re-run the failing suites if code conflicted, and commit the merge, so the plan merges back cleanly
   and the documentation task after you documents the merged code.
7. **Your own block** — only now delete it, and update the line above the blocks that says which have
   landed, in a follow-up commit of its own: `docs: delete <id>'s prompt (<plan>)`. Do not stop between
   the two commits. Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming
   the blocker and its owner. When the queue says other tasks of this plan are running beside you, do
   not commit, stash, reset or check out at all: make this deletion your last edit, and the queue
   commits the work and the deletion together.
8. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified), `git mv` this plan into `docs/plans/implemented/`, same name and
   number, and add its row to that folder's README where there is one, in the same follow-up commit.

## Prompts — one per task

Run them in order, one session each; each block is complete on its own. P1 builds and self-gates (it is the only runnable task, so its gate is the whole set — the async-wrapped parse-check and the structural review; the sample dry-run runs **only if the user says to**, since it spawns subagents). DOC1 documents what P1 landed and files the plan. **No prompt starts a real Metasploit run or a live Pro execution** — the workflow plans; live acts are the user's under the operator-handoff protocol. Both prompts are live.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| P1 | `ts` | `tooling-engineer` | none | — | ~90k |
| DOC1 | `docs` | `be-documenter` | P1 | — | ~45k |

---

### P1 — the Metasploit Pro assessment workflow + its command (tooling-engineer, ts)

````
Depends on: none
Agent: tooling-engineer · Stack: ts

You are `tooling-engineer`. Task P1 of docs/plans/013-metasploit-pro-assessment-workflow.md: build the
paid Metasploit Pro counterpart to the free Framework assessment workflow. It PLANS — it executes no
live act.

Read, in this order:
1. CLAUDE.md (the global rules; note: subagents Sonnet/medium, ≤3 parallel, no forks).
2. This plan: §2 (the Pro package shape), §3 (the gate for a .mjs workflow), D1–D4, task P1, and
   "Close-out — every task".
3. The free lane as the pattern: `security/workflows/metasploit-framework-assessment.mjs` (whole) and
   `security/commands/assess-repo.md` (whole).
4. `security/metasploit-setup/references/metasploit-pro.md` — the REST/RPC APIs, MetaModules, task
   chains and the Validation Wizard (the Pro mechanisms the synthesis maps to), and the operator-handoff
   section of `security/metasploit-setup/SKILL.md`.

Build:
- `security/workflows/metasploit-pro-assessment.mjs` — copy the free skeleton (pure-literal `meta`,
  the three-reader `parallel()` at width 3, the `SONNET`/`SAFETY` constants), extend the profilers with
  the Pro signal each sees, and replace the synthesis prompt/schema with §2's Pro package (REST/RPC
  setup; per-surface Pro mechanism — auto-exploit / Validation Wizard / MetaModule / task chain; each
  test's single provenOutcome, ATT&CK id, availabilityRisk flag and `operatorCall`; the Pro-specific
  scope-file skeleton). Extend the critic per §2.
- `security/commands/assess-repo-pro.md` — from the `assess-repo.md` pattern, pointing at the Pro
  script, naming the licensed Pro install as the prerequisite for live execution, same planning-only /
  operator-handoff / stops-at-the-gate framing.
- Register ONLY the command in `.claude-plugin/marketplace.json` under `penetration-testing.commands`
  (workflows are not a manifest array).

Traps:
- Every `agent()` call passes `{ model: 'sonnet', effort: 'medium' }`; `parallel()` width is 3; no
  `isolation: 'worktree'`, no forks — CLAUDE.md's subagent rule.
- `meta` must be a pure literal (no variables/among its fields). `Date.now()`/`Math.random()`/argless
  `new Date()` throw in a workflow — don't use them.
- `provenOutcome` is single-valued (no OR); flag `availabilityRisk` on auto-exploitation and
  memory-corruption modules — they are operator-run and never production.
- The script RETURNS a package; it triggers no live act. Pro's irreversible actions are operator-run
  (D4) — the output gives the operator the REST call or the wizard step, it does not run them.

Gate (this is the last runnable task, so it runs the whole set):
  # §3 step 1 — parse-check in the engine's async-body context (top-level return/await are legal there):
  SRC=security/workflows/metasploit-pro-assessment.mjs
  OUT="$TMPDIR/wfcheck-pro.mjs"
  { echo 'async function __wf(agent,parallel,pipeline,log,phase,args,budget,workflow){'; \
    sed 's/^export const meta/const meta/' "$SRC"; echo '}'; echo 'void __wf;'; } > "$OUT"
  node --check "$OUT"
  python3 -c "import json; json.load(open('.claude-plugin/marketplace.json')); print('manifest valid')"
  # §3 step 2 — structural review: meta pure literal; every agent() is Sonnet/medium; parallel width ≤3;
  #   no worktree/fork; returns a package, no live act. §3 step 3 sample dry-run ONLY if the user says so.
Fix what the checks find before you stop.

Commit: `feat(penetration-testing): Metasploit Pro assessment workflow + command (pro P1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### DOC1 — catalog, cross-links and filing the plan (be-documenter, docs)

````
Depends on: P1
Agent: be-documenter · Stack: docs

You are `be-documenter`. Task DOC1 of docs/plans/013-metasploit-pro-assessment-workflow.md: document
what P1 landed, from the code, and file the plan. Doc-only.

Read, in this order:
1. CLAUDE.md.
2. This plan: task DOC1, §2, and "Close-out — every task".
3. What P1 landed: `security/workflows/metasploit-pro-assessment.mjs` and
   `security/commands/assess-repo-pro.md` (and its `marketplace.json` entry) — the code is the evidence,
   P1's "As built" note is the lead.
4. `docs/skills-catalog.md` — the two command-count lines (in "Slash-command surface"), the
   `penetration-testing` row, and the Metasploit repo-assessment-workflow paragraph.

Do:
- Recompute the command counts (files + registrations) in `docs/skills-catalog.md` from the manifest,
  add `:assess-repo-pro` to the `penetration-testing` slash-surface row, and extend the
  Metasploit-workflow paragraph to name both lanes (free Framework + paid Pro).
- Cross-link the workflow from the "agent-drivable surface" section of
  `security/metasploit-setup/references/metasploit-pro.md`.
- File the plan: rewrite `Status:`, `git mv docs/plans/013-metasploit-pro-assessment-workflow.md
  docs/plans/implemented/`, add the README row where `docs/plans/implemented/README.md` exists.

Gate: none — doc-only; run your own doc lint over the files you touched.

Commit: `docs: Metasploit Pro workflow in the catalog; file plan 013 (pro DOC1)`.
Close out per the plan's "Close-out — every task" before you stop.
````
