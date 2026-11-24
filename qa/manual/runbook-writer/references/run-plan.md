# The run plan — a runbook cut into queue tasks

A run plan is the file that puts one run of a runbook on the Plan Queue: one prompt block per part of the runbook, a progress table that shows how far the run is, and a pause point between every two tasks. It is a plan in the library's plan format (`product/skills/writing-plans/references/plan-format.md`), so Plan Queue lists it, runs one session per block and shows what is left by which blocks are still there.

**When it is written.** With every runbook, as the runbook's first run; and on request for each later run or rerun of an existing runbook (the agent's QUEUE mode). One run plan is one run: when its last block goes it is filed under `docs/plans/implemented/`, and the next run gets a new one.

**Path:** `docs/plans/<PPP>-<slug>-runbook-run.md`. `PPP` is the next free plan number across `docs/plans/` and `docs/plans/implemented/`; it is not the runbook's number.

**What it is not.** It writes no code and no tests, so it has no test-design tasks, no gate task and no documentation task, and its header says so. It holds no test steps: every block points at the runbook's sections, and the runbook stays the one place a step is written.

## How the runbook is cut

| Task | Runs | Depends on |
|---|---|---|
| `E1` | The checks before the first step (`execution.md`), §5 Preconditions, §6 Setup; creates the run record | none |
| `E2`… | One task per test family, in the order of the legend that opens §8, with the recipes its tests use. Where the runbook has a §12 execution order, one task per row of it instead | the task above |
| the last `E` | §9 Cleanup, the baselines, the final run record, the runbook's §10 and §11 | the task above |

- **Tasks are serial.** Each depends on the one above and none runs beside another: they share one environment, one device and one run marker.
- **A family too large for one session** (more than about sixty steps) is cut in two at a test boundary, as two consecutive tasks.
- **A rerun** holds only the families with a test to rerun, and each block names its tests.
- **A test with a Hand step** is named in its task's row of the task table, with what the user must do, so the user sees it before the queue reaches it.

## What carries a run from one session to the next

Each task is a new session, so nothing lives in the shell.

- **The run record** is created by `E1` and committed by every task. Beside the sections of `execution.md` it holds a **Run state** table: the run marker, and every captured value that is not a secret (ids, names, baselines), each with the step that captured it.
- **Re-entry.** Every task after `E1` starts by rebuilding `vars.env` in the evidence folder from the Run state table, obtaining the tokens again by Setup's token steps, signing in on each UI again, and re-checking the preconditions that drift between sessions: the right app or site in front, the right user, each shared switch.
- **The evidence folder** is fixed in the plan header and git-ignored. Under Plan Queue it lives in the plan's worktree.
- **The secrets** are environment variables of the shell the queue starts sessions in. The header lists their names.
- **The runbook and the run plan are committed before the first task is queued**: the queue works from a worktree of the branch.

## Progress, pausing and resuming

- **`## 2. Progress`** has one row per task: the runbook part, its tests and its result. Each task fills its own row when it lands (`3 pass`, `5 pass · 1 fail new (KI-4) · 1 blocked`). With the live prompt blocks and the header's `Status:` line, it is the picture of the run.
- **To pause**, stop the queue between two tasks. The task that just landed has written `Status:`: which tasks are done, which is next, and what data the run has on the environment.
- **To resume**, queue the next block. Its re-entry puts the session back where the last one ended.
- **To end a paused run early**, delete the blocks of the families that will not be run and queue the last task: it records their tests as *not run* and cleans up.
- **A task stopped in the middle** keeps its block, with a `Picking up from: <test id>` line, and its finished tests are already in the record.
- **Run data stays on the environment until the last task.** Nothing is cleaned between tasks, so a later task may use what an earlier one made.

## What a queued task does differently from a direct run

- **It cannot ask.** The environment's confirmation is read from the plan header. While that line says `not confirmed`, `E1` stops and keeps its block, blocked on the user.
- **At a Hand step it stops**, marks the test `blocked`, keeps its block with `Blocked: Hand step <test.step> — <what the user must do>`, and goes on with the tests that do not depend on it.
- **A failed test does not stop the task.** The task runs every test of its family, and the result goes in its Progress row.
- **Its commit is the run record, the runbook's §10 and §11, any bug report and the plan edits.** Evidence is never committed.

## Output format

`````markdown
# <PPP> — Run of the <Feature> runbook on <environment> — plan (<YYYY-MM-DD>)

**Goal:** Carry out `docs/runbooks/<NNN>-<slug>-runbook.md` v<n> on <environment>, build <release> @ <commit>, and record a result for every test.

**Status:** Nothing run yet. Next: E1.

**Environment:** <name> — not production, confirmed by <who> on <date> | **not confirmed**
**Run record:** `docs/runbooks/<NNN>-<slug>-run-<YYYY-MM-DD>.md` (created by E1)   **Evidence:** `evidence/<YYYY-MM-DD>-<slug>-run/`
**Variables the queue's shell must hold:** `QA_ADMIN_USER`, `QA_ADMIN_PASSWORD`, `DB_URL`
**Test-design tasks: none** and **Documentation task: none** — a run carries out a suite that exists and changes no behaviour.

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| A result for the journey tests on <environment> | Never run there (runbook §11) | E2 runs J01–J03 |

## 2. Progress

| Task | Runbook part | Tests | Result |
|---|---|---|---|
| E1 | §5 Preconditions · §6 Setup | — | — |
| E2 | §8, family J — journeys | J01–J03 | — |
| E3 | §8, family P — product operations | P01–P08 | — |
| E4 | §9 Cleanup · baselines · the record | — | — |

## 3. How a task runs

<The four lists above this template, copied: what carries the run between sessions, re-entry, what a queued task does differently, and how to pause, resume and end early.>

## Decisions

**D1 — The tasks are serial.** They share one environment, one device and one run marker. It costs wall-clock time: no two families run at once.

## 4. Tasks

### E2 — Journey tests J01–J03 have a result on <environment>

**Stack:** `qa` · **Agent:** `qa-manual-tester`
**Deliverable:** J01, J02 and J03 each have a result row in the run record with its kept evidence.
**Depends on:** —
**Budget:** ~<n>k — the agent and `execution.md` ~8k, this plan's header, §3 and task ~3k, the runbook's header, §1, §4, §5, the three tests and their recipes ~<n>k, <n> steps of tool output ~<n>k.
**Gate: none** — a run builds nothing; its check is that every test of this task has a result row.

- Re-enter from the run record's Run state table.
- Run J01, J02 and J03 in order, each by `execution.md`.
- Append their rows to the record and fill the E2 row of §2.
- **Not in E2:** Cleanup (the last task), and any test of another family.

## Close-out — every task

<Copied verbatim from `product/skills/writing-plans/references/plan-format.md`, §7.>

## Prompts — one per task

Run them in order, one session each; no task runs beside another. Each block is complete on its own. No block may act on any environment but <environment>.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| E1 | `qa` | `qa-manual-tester` | none | — | ~<n>k |
| E2 | `qa` | `qa-manual-tester` | E1 | — | ~<n>k |
| — | P06 step 3: switch the flag in the console | **the user** | E2 | — | — |
| E3 | `qa` | `qa-manual-tester` | E2 | — | ~<n>k |
| E4 | `qa` | `qa-manual-tester` | E3 | — | ~<n>k |

All four prompts are live.

---

### E2 — Journey tests J01–J03 (qa-manual-tester, qa)

````
Depends on: E1
Agent: qa-manual-tester · Stack: qa

You are `qa-manual-tester`, in RUN mode. Task E2 of docs/plans/<PPP>-<slug>-runbook-run.md: run the
journey tests J01, J02 and J03 of docs/runbooks/<NNN>-<slug>-runbook.md on <environment>.

The plan header records that <environment> is not production. Act on no other environment, and ask
nothing: where you would ask, stop as §3 of the plan says.

Read, in this order:
1. `qa/manual/agents/qa-manual-tester.md` and `qa/manual/runbook-writer/references/execution.md`
   (under ${CLAUDE_PLUGIN_ROOT}, or the SkillsLibrary root).
2. This plan: the header, §3, task E2, and "Close-out — every task".
3. The runbook: the header, §1, §4, §5, tests J01–J03 in §8 with recipes R-1 and R-2, and §10.
4. The run record: the Run state table and the rows already written.

Do:
- Re-enter: rebuild vars.env from the Run state table, obtain the tokens by Setup steps S-2 and S-3,
  sign in on each UI, re-check PRE-1 and PRE-2.
- Run J01, J02, J03 in order. Capture evidence at every step; keep the end result of a passed test
  and the whole chain of a failed one.
- Append each test's row to the run record, add new captures to its Run state table, and fill the
  E2 row of §2 in this plan.

Traps:
- <the two to four things specific to these tests: the cache budget, the known issue a test will hit>
- Run no Cleanup step: the run's data stays for the tasks below.

Gate: none. Every test of this task has a result row with its kept evidence.

Commit: `test: <slug> runbook, journeys on <environment> (<PPP> E2)`.
Close out per the plan's "Close-out — every task" before you stop.
````
`````

The first and the last block follow the same shape. `E1`'s block reads the environment line first, runs the checks, the preconditions and Setup, and creates the record with its Run state table. The last block runs every Cleanup step, reconciles the baselines, completes the record's summary, permanent changes and left-behind sections, updates the runbook's §10 and §11, and files the plan.

## The run-plan check

| Check | Fails as |
|---|---|
| Every test of the runbook (or of the rerun's filter) is named in exactly one task | blocker |
| A block that holds a test step instead of pointing at the runbook | major |
| A block whose first two lines are not `Depends on:` and `Agent: qa-manual-tester · Stack: qa`, or a heading that is not `### <id> — <title> (qa-manual-tester, qa)` | blocker |
| A task that does not depend on the one above | major |
| A block with no re-entry, or the last block without Cleanup and the baselines | major |
| A secret's value anywhere in the plan | blocker |
| The environment line missing, or a Hand step missing from the task table | major |
