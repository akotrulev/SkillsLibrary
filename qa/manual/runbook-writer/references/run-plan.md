# The run plan — a runbook cut into queue tasks

A run plan is the file that puts one run of a runbook on the Plan Queue: one prompt block per part of the runbook, a progress table that shows how far the run is, and a pause point between every two tasks. It is a plan in the library's plan format (`product/skills/writing-plans/references/plan-format.md`), so Plan Queue lists it, runs one session per block and shows what is left by which blocks are still there.

**When it is written.** With every runbook, as the runbook's first run; and on request for each later run or rerun of an existing runbook (the agent's QUEUE mode). One run plan is one run: when its last block goes it is filed under `docs/plans/implemented/`, and the next run gets a new one.

**Path:** `docs/plans/<PPP>-<slug>-runbook-run.md`. `PPP` is the next free plan number across `docs/plans/` and `docs/plans/implemented/`; it is not the runbook's number.

**What it is not.** It writes no code and no tests, so it has no test-design tasks, no gate task and no documentation task. The plan format allows each (§4 and §5 of `plan-format.md`), and the header says so in the format's words. It holds no test steps: every block points at the runbook's sections, and the runbook stays the one place a step is written.

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

## What the queue needs before the first task

Plan Queue (checked against its 0.7.0 source) runs each task as a Claude Code background session in the plan's own worktree, under `<repo>/.claude/worktrees/`. File edits are accepted; a command outside its allowlist stops the task until the user allows it in the task's session, so a run nobody watches needs the allowlist complete. It commits a passed task with `git add -A`, stashes what a stopped or failed task left, and removes the worktree when the plan finishes. The plan's header lists what a run takes, and `E1` checks each before the first step, asking the user for whatever is missing:

- **Allowlist entries** (`planQueue.allowedTools`) for what the runbook's steps call beyond the queue's defaults: the engine's client (`Bash(psql:*)`), the project's API tool (`Bash(ijhttp:*)`, `Bash(newman:*)`, `Bash(bru:*)`), `Bash(uuidgen:*)`, `Bash(date:*)`, `Bash(source:*)`, any helper script's interpreter, and the MCP servers that drive the screens (`mcp__playwright`, `mcp__appium-mcp`).
- **The MCP servers** registered for the user or the project, since a queued session takes its servers from the Claude Code configuration.
- **The secrets** as environment variables of the VS Code window that runs the queue. The header lists their names.
- **An evidence folder outside the worktree.** Inside it, evidence would be committed with the task when it is not git-ignored, and deleted with the worktree when it is. The header names an absolute folder in the main checkout (`<repo>/evidence/<YYYY-MM-DD>-<slug>-run/`), the queue is given it with `--add-dir <repo>/evidence` in `planQueue.extraArgs`, and `evidence/` is in the project's `.gitignore` (the line is added with the run plan when it is missing).
- **The runbook and the run plan committed**: the worktree holds only what is committed.

## What carries a run from one session to the next

Each task is a new session, so nothing lives in the shell.

- **The journal** is the run's working state, in the evidence folder: `vars.env` with every captured value, and `results.md` with one row per finished test, written the moment that test ends. It survives a stop, a stash and the end of a session.
- **The run record** is created by `E1` and committed with every task. Before a task ends it copies its new journal rows into the record's Results table and its new captures that are not secrets into the record's **Run state** table.
- **Re-entry.** Every task after `E1` starts by reading the journal (rebuilding `vars.env` from the record's Run state table where the folder is gone), obtaining the tokens again by Setup's token steps, signing in on each UI again, and re-checking the preconditions that drift between sessions: the right app or site in front, the right user, each shared switch.

## Progress, pausing and resuming

- **The queue's sidebar** shows each task as pending, working, paused, waiting for a reply or done. **`## 2. Progress`** in the plan adds what the run found: one row per task with the runbook part, its tests and its result (`3 pass`, `5 pass · 1 fail new (KI-4) · 1 blocked`), filled by the task when it lands.
- **Pause** interrupts a task at any point and keeps its session: the queue's own button, a closed window, or the usage limit, which the queue lifts by itself at the reset. On **Resume**, before repeating the step that was cut off, the task reads back what that step did (the response saved, the row): a request sent twice is a second record. A pause can last hours, so the task also re-enters, and a test whose data is set relative to now starts again from its Arrange.
- **Stop**, or a task that ended blocked, leaves the task pending and its uncommitted edits stashed, and it starts again from its block. It reads the journal first, restores its rows in the record from it, and continues with the first of its tests that has no row.
- **On the backlog**, a task waiting for a reply keeps its plan out of the unattended sweeps until the user answers.
- **Between two tasks** the header's `Status:` line says which tasks are done, which is next, and what data the run has on the environment.
- **To end a run early**, delete the blocks of the families that will not be run and queue the last task: it records their tests as *not run* and cleans up.
- **Run data stays on the environment until the last task.** Nothing is cleaned between tasks, so a later task may use what an earlier one made.

## What a queued task does differently from a direct run

- **It asks only where it cannot go on without a person**, and says so in the way the queue's own instructions describe; the queue brings the answer back to the same session. Two cases are always that: an environment the header does not confirm, and a Hand step.
- **The environment is confirmed once per run.** Where the header says `not confirmed`, `E1` asks before anything else and writes the answer into that line; every later task reads it there.
- **A failed test is a result, not a failure of the task.** The task runs every test of its family and ends done. It ends blocked only when the run cannot go on at all: an actor every test needs is down, a credential is missing.
- **A command outside the allowlist** waits for the user in the task's session. The step is never rewritten to avoid the prompt; when the user declines, the step is blocked and the task names the entry that would allow it.
- **The queue commits what the task leaves**: the run record, the runbook's §10 and §11, any bug report and the plan edits. Evidence is never in it.

## Output format

`````markdown
# <PPP> — Run of the <Feature> runbook on <environment> — plan (<YYYY-MM-DD>)

**Goal:** Carry out `docs/runbooks/<NNN>-<slug>-runbook.md` v<n> on <environment>, build <release> @ <commit>, and record a result for every test.

**Status:** Nothing run yet. Next: E1.

**Environment:** <name> — not production, confirmed by <who> on <date> | **not confirmed**
**Run record:** `docs/runbooks/<NNN>-<slug>-run-<YYYY-MM-DD>.md` (created by E1)   **Evidence:** `<repo>/evidence/<YYYY-MM-DD>-<slug>-run/` (outside the worktree)
**The queue needs:** allowlist `Bash(psql:*)`, `Bash(uuidgen:*)`, `Bash(date:*)`, `Bash(source:*)`, `mcp__playwright`, `mcp__appium-mcp` · `--add-dir <repo>/evidence` · variables `QA_ADMIN_USER`, `QA_ADMIN_PASSWORD`, `DB_URL`
**Gate task: none** — a run writes no code and no tests; each task's check is a result row per test.
**Documentation task: none** — a run changes no behaviour. No `TD` tasks: the plan builds no acceptance criteria.

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

<The three lists above this template, copied: what carries the run between sessions, how it pauses and resumes, and what a queued task does differently.>

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

The plan header records that <environment> is not production. Act on no other environment. A
Hand step is a case you cannot go on without a person: ask, and wait for the reply.

Read, in this order:
1. `qa/manual/agents/qa-manual-tester.md` and `qa/manual/runbook-writer/references/execution.md`
   (under ${CLAUDE_PLUGIN_ROOT}, or the SkillsLibrary root).
2. This plan: the header, §3, task E2, and "Close-out — every task".
3. The runbook: the header, §1, §4, §5, tests J01–J03 in §8 with recipes R-1 and R-2, and §10.
4. The run record: the Run state table and the rows already written.

Do:
- Read the journal in the evidence folder: skip any of these tests that already has a row.
  Re-enter: load vars.env (rebuild it from the record's Run state table if the folder is gone), obtain the tokens by Setup steps S-2 and S-3,
  sign in on each UI, re-check PRE-1 and PRE-2.
- Run J01, J02, J03 in order. Capture evidence at every step; keep the end result of a passed test
  and the whole chain of a failed one.
- Write each test's row to the journal as that test ends. When all three are done, copy the rows
  into the run record, add the new captures to its Run state table, and fill the E2 row of §2.

Traps:
- <the two to four things specific to these tests: the cache budget, the known issue a test will hit>
- Run no Cleanup step: the run's data stays for the tasks below.

Gate: none. Every test of this task has a result row with its kept evidence.

Commit: `test: <slug> runbook, journeys on <environment> (<PPP> E2)`.
Close out per the plan's "Close-out — every task" before you stop.
````
`````

A filled run plan, with its first and last blocks written out, is in [`example-product-catalogue-run-plan.md`](example-product-catalogue-run-plan.md): read it before the first run plan in a project.

The first and the last block follow the same shape. `E1`'s block reads the environment line first and asks the user where it is not confirmed, checks what the queue needs, runs the checks of `execution.md`, the preconditions and Setup, and creates the record with its Run state table. The last block runs every Cleanup step, reconciles the baselines, completes the record's summary, permanent changes and left-behind sections, updates the runbook's §10 and §11, and files the plan.

## The run-plan check

| Check | Fails as |
|---|---|
| Every test of the runbook (or of the rerun's filter) is named in exactly one task | blocker |
| A block that holds a test step instead of pointing at the runbook | major |
| A block whose first two lines are not `Depends on:` and `Agent: qa-manual-tester · Stack: qa`, or a heading that is not `### <id> — <title> (qa-manual-tester, qa)` | blocker |
| A task that does not depend on the one above | major |
| A block with no journal read and re-entry, or the last block without Cleanup and the baselines | major |
| A secret's value anywhere in the plan | blocker |
| The environment line, the queue-needs line, `Gate task: none` or `Documentation task: none` missing from the header, an evidence folder inside the worktree, or a Hand step missing from the task table | major |
