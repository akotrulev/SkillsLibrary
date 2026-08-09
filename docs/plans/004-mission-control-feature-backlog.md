# 004 — Mission Control: feature backlog

**Status:** backlog 2026-08-09 — candidates, not committed work
**Scope:** `tools/mission-control`

Ideas evaluated against the current code, ordered by value. Each is independent; none is designed yet. Plans 002 (local deployment) and 003 (streams and ordering) are the committed work — anything promoted from here gets its own numbered plan.

---

## Tier 1 — closes a real gap

### B1 — Import `delivery-plan.md` directly, skip the planner

`Task` (`src/lib/types.ts:83`) is already **exactly** the `be-planner` contract: `id · phaseId · title · intent · acceptanceCriteria · agent · skills · files · dependsOn`. CLAUDE.md states the pack "pastes in and maps ~1:1". Yet the only ingestion path is free-form prose through a multi-minute Opus pass that re-derives a structure already sitting on disk.

Add a *Load plan from file* input taking `docs/plans/<NNN>-<initiative>/delivery-plan.md`, parsing phases, tasks, streams (per 003), `parallelRationale` and `openQuestions[]` straight into a run. Add the reverse — **export** a board to `delivery-plan.md` — so a run started from prose becomes a committed artifact.

### B2 — Validate agent and skill names against the catalog at plan time

CLAUDE.md: *"An invented agent or skill name is the single most damaging defect in the pack, because MC binds on that string."* Today nothing checks it until `dispatchTask` fails at `dispatcher.ts:76` — after earlier phases have already written code. `ValidatablePlan` (`plan-validation.ts:16`) does not even carry `agent`/`skills`.

The catalog is indexed and in memory, so the check is nearly free. Add fuzzy matching: `be-dotnet-persistance` → *did you mean `be-dotnet-persistence`?* Turns a mid-run failure into a pre-run correction. Natural companion to 003 Phase 2, which is already extending the same validator.

### B3 — Verify acceptance criteria instead of trusting the summary

Every task carries `acceptanceCriteria[]` and nothing ever checks them; a task is `done` because the agent said so in its `## Summary`. This is what `ep-verify-before-done` exists to prevent.

Two levels: a per-project **verify command** (`dotnet test`, `npm test`) run after each task, failing it on non-zero exit; and a **verifier pass** — a second small-model call given the diff and the criteria, asked which are actually met. Per 003, verification runs inside the stream, blocking only that lane.

---

## Tier 2 — worth building next

### B4 — Budget ceiling with a hard stop
`costUsd` is recorded per task (`orchestrator.ts:215`) and enforced nowhere. Opus × 200 turns × parallel lanes is real money, and a stuck retry loop is the expensive failure. Per-run cap, running total on the board, pause on breach.

### B5 — Retry *with feedback*
`retryTask` (`orchestrator.ts:247`) re-dispatches the same prompt at the same task, which usually fails the same way. Let a human append a note that gets folded into the implementer prompt.

### B6 — Auto-append a review task per phase
The pieces exist — `code-auditor`, the per-stack `standards-audit`, `ep-requesting-code-review`, and a `review` task status the scheduler already handles. Opt-in insertion of a reviewer-bound task at each phase boundary surfaces defects there rather than six phases later.

### B7 — Skills *loaded* vs skills *assigned*
Unique to this library's thesis. The task log already records every tool call (`dispatcher.ts:describeToolUse`), so the `SKILL.md` files an agent actually read can be diffed against `task.skills[]`. If agents routinely ignore assigned skills, that is the most important signal available about whether the library does anything — and nothing else measures it.

---

## Tier 3 — cheap wins

- **`canUseTool` gate on destructive Bash.** `IMPLEMENTER_TOOLS` grants unrestricted Bash under `permissionMode: "acceptEdits"`. A denylist prompt for `rm -rf`, `git push --force`, `npm publish` is an afternoon's insurance.
- **Desktop notification** on run finish or open-question block — trivial via `osascript` once native (002), and runs are long enough that nobody watches them.
- **Per-task agent override before Start** — the catalog is already served at `/api/catalog`; let a human swap the planner's pick.
- **Emit `HANDOFF.md`** at end of run in `be-planner`'s format: where we are, next task id, blockers, deviations. Closes the loop back into the library's own workflow.
- **Recurring audit runs** — the `standards-audit` skills are re-runnable Mode A/B by design, so "sweep every project weekly" fits them exactly.
