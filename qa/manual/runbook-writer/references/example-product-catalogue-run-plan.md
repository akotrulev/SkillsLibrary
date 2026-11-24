# Worked example — the run plan of the product-catalogue runbook

The filled example for `run-plan.md`: the runbook of `example-product-catalogue.md` in, its first run plan out. **Shape is normative; domain content is illustrative.** Two sections are shown as one line each because a real plan copies them word for word: §3 from `run-plan.md` and the close-out from `plan-format.md` §7. Every task block and every prompt block is written whole, as in a real plan.

**Contents:**
- Input
- Output

## Input

The runbook `docs/runbooks/004-product-catalogue-runbook.md` v2: seven test families (J, P, R, T, D, V, A), no §12 execution order and no Hand step, so the cut is one task per family between the setup task and the cleanup task. The user confirmed staging when the runbook was written.

## Output

`````markdown
# 031 — Run of the Product catalogue runbook on staging — plan (2026-11-24)

**Goal:** Carry out `docs/runbooks/004-product-catalogue-runbook.md` v2 on staging, build `release-stage-0.42` @ `4c1e9a2`, and record a result for every one of its seventeen tests.

**Status:** Nothing run yet. Next: E1. No run data on staging.

**Environment:** staging — not production, confirmed by the catalogue QA lead on 2026-11-24
**Run record:** `docs/runbooks/004-product-catalogue-run-2026-11-24.md` (created by E1)   **Evidence:** `/work/shop/evidence/2026-11-24-product-catalogue-run/` (outside the worktree)
**The queue needs:** allowlist `Bash(psql:*)`, `Bash(uuidgen:*)`, `Bash(date:*)`, `Bash(source:*)`, `mcp__playwright`, `mcp__appium-mcp` · `--add-dir /work/shop/evidence` · variables `QA_ADMIN_USER`, `QA_ADMIN_PASSWORD`, `QA_VIEWER_USER`, `QA_VIEWER_PASSWORD`, `QA_SHOPPER_USER`, `QA_SHOPPER_PASSWORD`, `DB_URL`
**Gate task: none** — a run writes no code and no tests; each task's check is a result row per test.
**Documentation task: none** — a run changes no behaviour. No `TD` tasks: the plan builds no acceptance criteria.

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| Staging checked and set up for a run, with a run record | No run on staging yet (runbook §11) | E1 runs the checks, §5 and §6 and creates the record |
| A result for journey test J01 on staging | Never run there (runbook §11) | E2 runs J01 |
| A result for product-operation tests P01–P08 on staging | Never run there (runbook §11) | E3 runs P01–P08 |
| A result for rule tests R01–R02 on staging | Never run there (runbook §11) | E4 runs R01–R02 |
| A result for time tests T01–T02 on staging | Never run there (runbook §11) | E5 runs T01–T02 |
| A result for history test D01 on staging | Never run there (runbook §11) | E6 runs D01 |
| A result for field-validation tests V01–V02 on staging | Never run there (runbook §11) | E7 runs V01–V02 |
| A result for access test A01 on staging | Never run there (runbook §11) | E8 runs A01 |
| The run's data removed and the baseline reconciled | — | E9 runs §9 and closes the record |

## 2. Progress

| Task | Runbook part | Tests | Result |
|---|---|---|---|
| E1 | §5 Preconditions · §6 Setup | — | — |
| E2 | §8, family J — journeys | J01 | — |
| E3 | §8, family P — product operations | P01–P08 | — |
| E4 | §8, family R — rules | R01–R02 | — |
| E5 | §8, family T — time | T01–T02 | — |
| E6 | §8, family D — data from history | D01 | — |
| E7 | §8, family V — field validation | V01–V02 | — |
| E8 | §8, family A — access | A01 | — |
| E9 | §9 Cleanup · the baseline · the record | — | — |

## 3. How a task runs

*Copied word for word from `run-plan.md`: "What carries a run from one session to the next", "Progress, pausing and resuming" and "What a queued task does differently from a direct run".*

## Decisions

**D1 — The tasks are serial.** They share one environment, one emulator and one run marker. It costs wall-clock time: no two families run at once.

**D2 — The run's products stay on staging until E9.** P02–P04 read what Setup made, and a failed test's records are its evidence. It costs a clean list: the sales demo category is untouched, and *QA Lighting* holds the run's products for as long as the run takes.

## 4. Tasks

### E1 — Staging is checked and set up, and the run has its record

**Stack:** `qa` · **Agent:** `qa-manual-tester`
**Deliverable:** PRE-1 to PRE-5 hold, S-1 to S-8 have each met their Expect, and `docs/runbooks/004-product-catalogue-run-2026-11-24.md` exists with the run marker and every Setup capture in its Run state table.
**Depends on:** —
**Budget:** ~45k — the agent and `execution.md` ~8k, this plan's header, §3 and task ~3k, the runbook's header, §1, §4, §5 and §6 ~9k, 13 steps of tool output ~15k, the record ~3k.
**Gate: none** — a run builds nothing; its check is that every precondition and Setup step has its actual value in the record.

- Read the header's Environment line: it is confirmed, so the run starts without a question.
- Check what the queue needs: each allowlist entry by a harmless call, the evidence folder writable, each variable set (its name only).
- Run the checks before the first step (`execution.md`), then PRE-1 to PRE-5, then S-1 to S-8.
- Create the record with its header and Run state table, and start the journal in the evidence folder.
- **Not in E1:** any recipe, any test, any Cleanup step.

### E2 — Journey test J01 has a result on staging

**Stack:** `qa` · **Agent:** `qa-manual-tester`
**Deliverable:** J01 has a result row in the run record with its kept evidence.
**Depends on:** —
**Budget:** ~40k — the agent and `execution.md` ~8k, this plan's header, §3 and task ~3k, the runbook's header, §1, §4, §5, test J01 in §8 and §10 ~6k, the steps' tool output ~8k, re-entry ~4k.
**Gate: none** — a run builds nothing; its check is that J01 has a result row.

- Re-enter from the journal, or from the record's Run state table where the folder is gone.
- Run J01 by `execution.md`.
- Append the rows to the record and fill the E2 row of §2.
- **Not in E2:** Cleanup (E9), and any test of another family.

### E3 — Product-operation tests P01–P08 each have a result on staging

**Stack:** `qa` · **Agent:** `qa-manual-tester`
**Deliverable:** P01–P08 each have a result row in the run record with its kept evidence.
**Depends on:** —
**Budget:** ~110k — the agent and `execution.md` ~8k, this plan's header, §3 and task ~3k, the runbook's header, §1, §4, §5, tests P01–P08 in §8 and §10 ~22k, the steps' tool output ~55k, re-entry ~4k.
**Gate: none** — a run builds nothing; its check is that P01–P08 each have a result row.

- Re-enter from the journal, or from the record's Run state table where the folder is gone.
- Run P01–P08 in the runbook's order, each by `execution.md`.
- Append the rows to the record and fill the E3 row of §2.
- **Not in E3:** Cleanup (E9), and any test of another family.

### E4 — Rule tests R01 and R02 each have a result on staging

**Stack:** `qa` · **Agent:** `qa-manual-tester`
**Deliverable:** R01–R02 each have a result row in the run record with its kept evidence.
**Depends on:** —
**Budget:** ~50k — the agent and `execution.md` ~8k, this plan's header, §3 and task ~3k, the runbook's header, §1, §4, §5, tests R01 and R02 in §8 and §10 ~9k, the steps' tool output ~18k, re-entry ~4k.
**Gate: none** — a run builds nothing; its check is that R01–R02 each have a result row.

- Re-enter from the journal, or from the record's Run state table where the folder is gone.
- Run R01–R02 in the runbook's order, each by `execution.md`.
- Append the rows to the record and fill the E4 row of §2.
- **Not in E4:** Cleanup (E9), and any test of another family.

### E5 — Time tests T01 and T02 each have a result on staging

**Stack:** `qa` · **Agent:** `qa-manual-tester`
**Deliverable:** T01–T02 each have a result row in the run record with its kept evidence.
**Depends on:** —
**Budget:** ~55k — the agent and `execution.md` ~8k, this plan's header, §3 and task ~3k, the runbook's header, §1, §4, §5, recipes R-1 and R-2 in §7, tests T01 and T02 in §8 and §10 ~11k, the steps' tool output ~20k, re-entry ~4k.
**Gate: none** — a run builds nothing; its check is that T01–T02 each have a result row.

- Re-enter from the journal, or from the record's Run state table where the folder is gone.
- Run T01–T02 in the runbook's order with recipes R-1 and R-2, each by `execution.md`.
- Append the rows to the record and fill the E5 row of §2.
- **Not in E5:** Cleanup (E9), and any test of another family.

### E6 — History test D01 has a result on staging

**Stack:** `qa` · **Agent:** `qa-manual-tester`
**Deliverable:** D01 has a result row in the run record with its kept evidence.
**Depends on:** —
**Budget:** ~45k — the agent and `execution.md` ~8k, this plan's header, §3 and task ~3k, the runbook's header, §1, §4, §5, recipe R-3 in §7, test D01 in §8 and §10 ~8k, the steps' tool output ~12k, re-entry ~4k.
**Gate: none** — a run builds nothing; its check is that D01 has a result row.

- Re-enter from the journal, or from the record's Run state table where the folder is gone.
- Run D01 with recipe R-3 by `execution.md`.
- Append the rows to the record and fill the E6 row of §2.
- **Not in E6:** Cleanup (E9), and any test of another family.

### E7 — Field-validation tests V01 and V02 each have a result on staging

**Stack:** `qa` · **Agent:** `qa-manual-tester`
**Deliverable:** V01–V02 each have a result row in the run record with its kept evidence.
**Depends on:** —
**Budget:** ~55k — the agent and `execution.md` ~8k, this plan's header, §3 and task ~3k, the runbook's header, §1, §4, §5, tests V01 and V02 in §8 and §10 ~10k, the steps' tool output ~22k, re-entry ~4k.
**Gate: none** — a run builds nothing; its check is that V01–V02 each have a result row.

- Re-enter from the journal, or from the record's Run state table where the folder is gone.
- Run V01–V02 in the runbook's order, each by `execution.md`.
- Append the rows to the record and fill the E7 row of §2.
- **Not in E7:** Cleanup (E9), and any test of another family.

### E8 — Access test A01 has a result on staging

**Stack:** `qa` · **Agent:** `qa-manual-tester`
**Deliverable:** A01 has a result row in the run record with its kept evidence.
**Depends on:** —
**Budget:** ~35k — the agent and `execution.md` ~8k, this plan's header, §3 and task ~3k, the runbook's header, §1, §4, §5, test A01 in §8 and §10 ~5k, the steps' tool output ~6k, re-entry ~4k.
**Gate: none** — a run builds nothing; its check is that A01 has a result row.

- Re-enter from the journal, or from the record's Run state table where the folder is gone.
- Run A01 by `execution.md`.
- Append the rows to the record and fill the E8 row of §2.
- **Not in E8:** Cleanup (E9), and any test of another family.

### E9 — The run's data is gone from staging and the record is closed

**Stack:** `qa` · **Agent:** `qa-manual-tester`
**Deliverable:** C-1 to C-7 have run, `BASELINE_PRODUCTS` is reconciled, the record holds its summary, permanent changes and left-behind sections, and the runbook's §10 and §11 show this run.
**Depends on:** —
**Budget:** ~50k — the agent and `execution.md` ~8k, this plan's header, §3 and task ~3k, the runbook's header, §1, §4, §9, §10 and §11 ~8k, the whole record ~8k, 7 steps of tool output ~10k, the edits ~6k.
**Gate: none** — a run builds nothing; its check is that C-4 returns `0` and C-7 returns `BASELINE_PRODUCTS`.

- Re-enter, then run C-1 to C-7 in order, whatever the tests above found.
- Record every test with no result row as *not run*.
- Complete the record: the summary, known issues hit, observations, runbook defects, the baseline, permanent changes, left behind.
- Update the runbook's §10 and §11.
- **Not in E9:** rerunning a failed test, and any change to a test's steps.

## Close-out — every task

*Copied word for word from `product/skills/writing-plans/references/plan-format.md`, §7.*

## Prompts — one per task

Run them in order, one session each; no task runs beside another. Each block is complete on its own. No block may act on any environment but staging.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| E1 | `qa` | `qa-manual-tester` | none | — | ~45k |
| E2 | `qa` | `qa-manual-tester` | E1 | — | ~40k |
| E3 | `qa` | `qa-manual-tester` | E2 | — | ~110k |
| E4 | `qa` | `qa-manual-tester` | E3 | — | ~50k |
| E5 | `qa` | `qa-manual-tester` | E4 | — | ~55k |
| E6 | `qa` | `qa-manual-tester` | E5 | — | ~45k |
| E7 | `qa` | `qa-manual-tester` | E6 | — | ~55k |
| E8 | `qa` | `qa-manual-tester` | E7 | — | ~35k |
| E9 | `qa` | `qa-manual-tester` | E8 | — | ~50k |

All nine prompts are live.

---

### E1 — Checks, preconditions and Setup (qa-manual-tester, qa)

````
Depends on: none
Agent: qa-manual-tester · Stack: qa

You are `qa-manual-tester`, in RUN mode. Task E1 of docs/plans/031-product-catalogue-runbook-run.md: check staging,
set it up for a run of docs/runbooks/004-product-catalogue-runbook.md, and create the run record.

The plan header records that staging is not production. Act on no other environment.

Read, in this order:
1. `qa/manual/agents/qa-manual-tester.md` and `qa/manual/runbook-writer/references/execution.md`
   (under ${CLAUDE_PLUGIN_ROOT}, or the SkillsLibrary root).
2. This plan: the header, §3, task E1, and "Close-out — every task".
3. The runbook: the header, §1, §4, §5, §6 and §10.

Do:
- Check what the header says the queue needs: one harmless call per allowlist entry (`psql --version`,
  a Playwright and an Appium snapshot), a file written to the evidence folder, and each variable set.
  Print a variable's name, never its value. Ask the user for whatever is missing, and wait.
- Run the checks before the first step of `execution.md`, then PRE-1 to PRE-5, then S-1 to S-8.
  A precondition that fails stops the task: end blocked, naming the row.
- Start the journal in the evidence folder: vars.env with every capture, results.md empty.
- Create docs/runbooks/004-product-catalogue-run-2026-11-24.md with its header and its
  Run state table: the run marker and every capture that is not a secret. Fill the E1 row of §2.

Traps:
- S-1 sets `OUT` to the evidence folder the header names, outside this worktree.
- PRE-4 must return `0`: products of an earlier run are that run's to remove, not yours.
- Tokens go in vars.env only. The record and this plan hold no token.
- Run no recipe, no test and no Cleanup step.

Gate: none. Every precondition and Setup step has its actual value in the record.

Commit: `test: product-catalogue runbook, setup on staging (031 E1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### E2 — Journey test J01 (qa-manual-tester, qa)

````
Depends on: E1
Agent: qa-manual-tester · Stack: qa

You are `qa-manual-tester`, in RUN mode. Task E2 of docs/plans/031-product-catalogue-runbook-run.md: run
journey test J01 of docs/runbooks/004-product-catalogue-runbook.md on staging.

The plan header records that staging is not production. Act on no other environment.

Read, in this order:
1. `qa/manual/agents/qa-manual-tester.md` and `qa/manual/runbook-writer/references/execution.md`
   (under ${CLAUDE_PLUGIN_ROOT}, or the SkillsLibrary root).
2. This plan: the header, §3, task E2, and "Close-out — every task".
3. The runbook: the header, §1, §4, §5, test J01 in §8, and §10.
4. The run record: the Run state table and the rows already written.

Do:
- Read the journal in the evidence folder: skip any of these tests that already has a row.
  Re-enter: load vars.env (rebuild it from the record's Run state table if the folder is gone),
  obtain the tokens by Setup steps S-2 and S-3, sign in on the web by S-8, re-check PRE-1 and PRE-2.
- Run J01. Capture evidence at every step; keep the end result
  of a passed test and the whole chain of a failed one.
- Write each test's row to the journal as that test ends. When all are done, copy the rows into the
  run record, add the new captures to its Run state table, and fill the E2 row of §2.

Traps:
- The shopper list is cached for `LIST_BUDGET` (60 s): J01 step 4 polls with pull to refresh until the budget passes, and only then fails.
- J01 step 2 captures `LAMP_ID` from the page's address: write it to vars.env before step 3.
- Run no Cleanup step: the run's data stays for the tasks below.

Gate: none. J01 has a result row with its kept evidence.

Commit: `test: product-catalogue runbook, journeys on staging (031 E2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### E3 — Product-operation tests P01–P08 (qa-manual-tester, qa)

````
Depends on: E2
Agent: qa-manual-tester · Stack: qa

You are `qa-manual-tester`, in RUN mode. Task E3 of docs/plans/031-product-catalogue-runbook-run.md: run
product-operation tests P01–P08 of docs/runbooks/004-product-catalogue-runbook.md on staging.

The plan header records that staging is not production. Act on no other environment.

Read, in this order:
1. `qa/manual/agents/qa-manual-tester.md` and `qa/manual/runbook-writer/references/execution.md`
   (under ${CLAUDE_PLUGIN_ROOT}, or the SkillsLibrary root).
2. This plan: the header, §3, task E3, and "Close-out — every task".
3. The runbook: the header, §1, §4, §5, tests P01–P08 in §8, and §10.
4. The run record: the Run state table and the rows already written.

Do:
- Read the journal in the evidence folder: skip any of these tests that already has a row.
  Re-enter: load vars.env (rebuild it from the record's Run state table if the folder is gone),
  obtain the tokens by Setup steps S-2 and S-3, sign in on the web by S-8, re-check PRE-1 and PRE-2.
- Run P01, P02, P03, P04, P05, P06, P07, P08 in that order. Capture evidence at every step; keep the end result
  of a passed test and the whole chain of a failed one.
- Write each test's row to the journal as that test ends. When all are done, copy the rows into the
  run record, add the new captures to its Run state table, and fill the E3 row of §2.

Traps:
- KI-1 is known: P05 and P06 fail on the price the app shows. Record each as `fail (known KI-1)` and write no bug report.
- P02–P04 read the two products S-6 and S-7 made: take `SHELF_ID` and `STOOL_ID` from the Run state table and create nothing in their place.
- In P07 the `404` of step 4 is the Expect.
- Run no Cleanup step: the run's data stays for the tasks below.

Gate: none. P01–P08 each have a result row with its kept evidence.

Commit: `test: product-catalogue runbook, product operations on staging (031 E3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### E4 — Rule tests R01–R02 (qa-manual-tester, qa)

````
Depends on: E3
Agent: qa-manual-tester · Stack: qa

You are `qa-manual-tester`, in RUN mode. Task E4 of docs/plans/031-product-catalogue-runbook-run.md: run
rule tests R01–R02 of docs/runbooks/004-product-catalogue-runbook.md on staging.

The plan header records that staging is not production. Act on no other environment.

Read, in this order:
1. `qa/manual/agents/qa-manual-tester.md` and `qa/manual/runbook-writer/references/execution.md`
   (under ${CLAUDE_PLUGIN_ROOT}, or the SkillsLibrary root).
2. This plan: the header, §3, task E4, and "Close-out — every task".
3. The runbook: the header, §1, §4, §5, tests R01 and R02 in §8, and §10.
4. The run record: the Run state table and the rows already written.

Do:
- Read the journal in the evidence folder: skip any of these tests that already has a row.
  Re-enter: load vars.env (rebuild it from the record's Run state table if the folder is gone),
  obtain the tokens by Setup steps S-2 and S-3, sign in on the web by S-8, re-check PRE-1 and PRE-2.
- Run R01, R02 in that order. Capture evidence at every step; keep the end result
  of a passed test and the whole chain of a failed one.
- Write each test's row to the journal as that test ends. When all are done, copy the rows into the
  run record, add the new captures to its Run state table, and fill the E4 row of §2.

Traps:
- Both tests are refusals. A row the refused create left behind is a fail: capture its id as `STRAY_ID` into vars.env and the Run state table, so E9 removes it.
- R02 runs on the web: the message under the SKU field is the Expect, in the form's own words.
- Run no Cleanup step: the run's data stays for the tasks below.

Gate: none. R01–R02 each have a result row with its kept evidence.

Commit: `test: product-catalogue runbook, rules on staging (031 E4)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### E5 — Time tests T01–T02 (qa-manual-tester, qa)

````
Depends on: E4
Agent: qa-manual-tester · Stack: qa

You are `qa-manual-tester`, in RUN mode. Task E5 of docs/plans/031-product-catalogue-runbook-run.md: run
time tests T01–T02 of docs/runbooks/004-product-catalogue-runbook.md on staging.

The plan header records that staging is not production. Act on no other environment.

Read, in this order:
1. `qa/manual/agents/qa-manual-tester.md` and `qa/manual/runbook-writer/references/execution.md`
   (under ${CLAUDE_PLUGIN_ROOT}, or the SkillsLibrary root).
2. This plan: the header, §3, task E5, and "Close-out — every task".
3. The runbook: the header, §1, §4, §5, recipes R-1 and R-2 in §7, tests T01 and T02 in §8, and §10.
4. The run record: the Run state table and the rows already written.

Do:
- Read the journal in the evidence folder: skip any of these tests that already has a row.
  Re-enter: load vars.env (rebuild it from the record's Run state table if the folder is gone),
  obtain the tokens by Setup steps S-2 and S-3, sign in on the web by S-8, re-check PRE-1 and PRE-2.
- Run T01, T02 in that order with recipes R-1 and R-2. Capture evidence at every step; keep the end result
  of a passed test and the whole chain of a failed one.
- Write each test's row to the journal as that test ends. When all are done, copy the rows into the
  run record, add the new captures to its Run state table, and fill the E5 row of §2.

Traps:
- R-1's product sits one hour inside the 5-day threshold. Run T01 and T02 within that hour; after a longer pause run R-1 again with a new product and capture its id over the old one.
- A guard that returns another row count stops the recipe: the statement is not sent, and both tests are blocked.
- Run no Cleanup step: the run's data stays for the tasks below.

Gate: none. T01–T02 each have a result row with its kept evidence.

Commit: `test: product-catalogue runbook, time on staging (031 E5)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### E6 — History test D01 (qa-manual-tester, qa)

````
Depends on: E5
Agent: qa-manual-tester · Stack: qa

You are `qa-manual-tester`, in RUN mode. Task E6 of docs/plans/031-product-catalogue-runbook-run.md: run
history test D01 of docs/runbooks/004-product-catalogue-runbook.md on staging.

The plan header records that staging is not production. Act on no other environment.

Read, in this order:
1. `qa/manual/agents/qa-manual-tester.md` and `qa/manual/runbook-writer/references/execution.md`
   (under ${CLAUDE_PLUGIN_ROOT}, or the SkillsLibrary root).
2. This plan: the header, §3, task E6, and "Close-out — every task".
3. The runbook: the header, §1, §4, §5, recipe R-3 in §7, test D01 in §8, and §10.
4. The run record: the Run state table and the rows already written.

Do:
- Read the journal in the evidence folder: skip any of these tests that already has a row.
  Re-enter: load vars.env (rebuild it from the record's Run state table if the folder is gone),
  obtain the tokens by Setup steps S-2 and S-3, sign in on the web by S-8, re-check PRE-1 and PRE-2.
- Run D01 with recipe R-3. Capture evidence at every step; keep the end result
  of a passed test and the whole chain of a failed one.
- Write each test's row to the journal as that test ends. When all are done, copy the rows into the
  run record, add the new captures to its Run state table, and fill the E6 row of §2.

Traps:
- D01 step 3 is an Observe (OQ-2): record what the app shows under Observations. It is neither a pass nor a fail.
- R-3 inserts a row: its guard must return `0` before the insert is sent.
- Run no Cleanup step: the run's data stays for the tasks below.

Gate: none. D01 has a result row with its kept evidence.

Commit: `test: product-catalogue runbook, data from history on staging (031 E6)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### E7 — Field-validation tests V01–V02 (qa-manual-tester, qa)

````
Depends on: E6
Agent: qa-manual-tester · Stack: qa

You are `qa-manual-tester`, in RUN mode. Task E7 of docs/plans/031-product-catalogue-runbook-run.md: run
field-validation tests V01–V02 of docs/runbooks/004-product-catalogue-runbook.md on staging.

The plan header records that staging is not production. Act on no other environment.

Read, in this order:
1. `qa/manual/agents/qa-manual-tester.md` and `qa/manual/runbook-writer/references/execution.md`
   (under ${CLAUDE_PLUGIN_ROOT}, or the SkillsLibrary root).
2. This plan: the header, §3, task E7, and "Close-out — every task".
3. The runbook: the header, §1, §4, §5, tests V01 and V02 in §8, and §10.
4. The run record: the Run state table and the rows already written.

Do:
- Read the journal in the evidence folder: skip any of these tests that already has a row.
  Re-enter: load vars.env (rebuild it from the record's Run state table if the folder is gone),
  obtain the tokens by Setup steps S-2 and S-3, sign in on the web by S-8, re-check PRE-1 and PRE-2.
- Run V01, V02 in that order. Capture evidence at every step; keep the end result
  of a passed test and the whole chain of a failed one.
- Write each test's row to the journal as that test ends. When all are done, copy the rows into the
  run record, add the new captures to its Run state table, and fill the E7 row of §2.

Traps:
- Every row of V01 is its own request and its own evidence file.
- A refused create that left a row is a fail: capture `STRAY_ID` as in E4.
- Run no Cleanup step: the run's data stays for the tasks below.

Gate: none. V01–V02 each have a result row with its kept evidence.

Commit: `test: product-catalogue runbook, field validation on staging (031 E7)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### E8 — Access test A01 (qa-manual-tester, qa)

````
Depends on: E7
Agent: qa-manual-tester · Stack: qa

You are `qa-manual-tester`, in RUN mode. Task E8 of docs/plans/031-product-catalogue-runbook-run.md: run
access test A01 of docs/runbooks/004-product-catalogue-runbook.md on staging.

The plan header records that staging is not production. Act on no other environment.

Read, in this order:
1. `qa/manual/agents/qa-manual-tester.md` and `qa/manual/runbook-writer/references/execution.md`
   (under ${CLAUDE_PLUGIN_ROOT}, or the SkillsLibrary root).
2. This plan: the header, §3, task E8, and "Close-out — every task".
3. The runbook: the header, §1, §4, §5, test A01 in §8, and §10.
4. The run record: the Run state table and the rows already written.

Do:
- Read the journal in the evidence folder: skip any of these tests that already has a row.
  Re-enter: load vars.env (rebuild it from the record's Run state table if the folder is gone),
  obtain the tokens by Setup steps S-2 and S-3, sign in on the web by S-8, re-check PRE-1 and PRE-2.
- Run A01. Capture evidence at every step; keep the end result
  of a passed test and the whole chain of a failed one.
- Write each test's row to the journal as that test ends. When all are done, copy the rows into the
  run record, add the new captures to its Run state table, and fill the E8 row of §2.

Traps:
- A01 sends its request with `TOKEN_VIEWER` (S-3), never the admin token.
- The DB read after the refusal shows no product of the run with A01's SKU.
- Run no Cleanup step: the run's data stays for the tasks below.

Gate: none. A01 has a result row with its kept evidence.

Commit: `test: product-catalogue runbook, access on staging (031 E8)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### E9 — Cleanup, the baseline and the record (qa-manual-tester, qa)

````
Depends on: E8
Agent: qa-manual-tester · Stack: qa

You are `qa-manual-tester`, in RUN mode. Task E9 of docs/plans/031-product-catalogue-runbook-run.md: remove the
run's data from staging by §9 of docs/runbooks/004-product-catalogue-runbook.md, and close the run record.

The plan header records that staging is not production. Act on no other environment.

Read, in this order:
1. `qa/manual/agents/qa-manual-tester.md` and `qa/manual/runbook-writer/references/execution.md`
   (under ${CLAUDE_PLUGIN_ROOT}, or the SkillsLibrary root).
2. This plan: the header, §2, §3, task E9, and "Close-out — every task".
3. The runbook: the header, §1, §4, §9, §10 and §11.
4. The run record, whole.

Do:
- Read the journal and re-enter as every task does: vars.env, the tokens by S-2 and S-3, the web
  sign-in by S-8, PRE-1 and PRE-2.
- Run C-1 to C-7 in order, whatever the tests found. A step that fails goes under Left behind with
  the ids it could not remove, and the next step still runs.
- Give every test of the runbook with no result row the result *not run*.
- Complete the record: the summary, known issues hit, observations, runbook defects, the baseline
  with its difference explained, permanent changes ("None" for this runbook), left behind.
- Update the runbook's §11 with one row per test run and its §10 with each new cause. Edit nothing
  else in the runbook.
- Sign out, close the browser and the device session, and fill the E9 row of §2.

Traps:
- C-1 and the C-2 count name the ids the runbook lists. A `STRAY_ID` in the Run state table is one
  more id for C-1 and one more row for C-2: say so in the record.
- A C-2 guard that returns another count stops C-3: record the rows it found under Left behind.
- The plan's close-out files this plan, since E9 deletes the last prompt block.

Gate: none. C-4 returns `0`, C-7 returns `BASELINE_PRODUCTS`, and the record is complete.

Commit: `test: product-catalogue runbook, cleanup on staging (031 E9)`.
Close out per the plan's "Close-out — every task" before you stop.
````
`````
