# 003 — Mission Control: task streams and explicit ordering

**Status:** planned 2026-08-09
**Scope:** `tools/mission-control` (+ a contract change in `backend/_shared/delivery-plan`)
**Goal:** replace the phase-level all-or-nothing parallelism with **streams** — named lanes whose tasks run strictly in sequence, while lanes run concurrently — and give every task an explicit **order**, so the board can always answer "what is running, and what is next" without inferring it from array position.

---

## Why

### Parallelism is currently a per-phase boolean

`startRun()` picks its batch with `phase.parallelSafe ? selectParallelBatch(dispatchable, maxParallel) : [dispatchable[0]]` (`src/lib/orchestrator.ts:183`). A phase is either fully sequential or a free-for-all bounded by `maxParallel`. There is no way to express the shape real work actually has: *these four tasks touch the ordering module and must go one after another, while those three touch billing and can proceed alongside them.*

The planner is forced into a lossy call — mark the phase parallel and rely on `conflictsWithRunning` to catch collisions at runtime, or mark it sequential and serialise work that had no reason to be serial.

### The batch barrier wastes the parallelism it does allow

`await Promise.all(batch.map(...))` (`orchestrator.ts:185`) means the loop does not re-enter until **every** task in the batch settles. A two-minute task sitting in a batch with a forty-minute one contributes two minutes of work and thirty-eight minutes of idling, even when its successor was dispatchable the whole time. With `maxParallel: 3` this routinely leaves two slots empty for most of a phase.

### "What's next" is currently array position

The sequential branch dispatches `dispatchable[0]` — the first match in `run.tasks` array order. That ordering is whatever the planner happened to emit, is not surfaced anywhere, and silently changes meaning if tasks are ever reordered, inserted, or filtered. Nothing in the model or the UI states the intended sequence, so the board cannot show an up-next queue and a human cannot correct one.

### `files[]` does nothing until it is too late

`conflictsWithRunning()` (`orchestrator.ts:57`) checks declared file overlap at **dispatch** time and merely defers the loser to a later batch. That is a runtime patch over a planning defect: two tasks that write the same file were never safe to place in parallel lanes, and the plan should have said so before the run started.

---

## Design decisions

### D1 — A stream is a run-level named lane; tasks execute in `order` within it

```ts
interface Stream {
  id: string;          // "backend", "billing", "infra"
  name: string;        // display label
  description?: string;// what this lane owns — shown on hover
}

interface Task {
  // …existing fields
  streamId: string;    // which lane it executes in
  order: number;       // position in the run's overall intended sequence
}
```

`order` is **unique across the run**, not per stream. One number then serves both purposes: within a stream it fixes execution sequence, and across the run it gives a single canonical "intended order" the board sorts by. Per-stream numbering would need a second key to answer "what is next overall" and would renumber on every cross-stream edit.

Stream identity is **stable across phases**, so `Backend` is one continuous lane down the whole board rather than a fresh anonymous group per phase. That is what makes swimlane rendering and "what is this lane doing" meaningful.

Rejected: *stream as a per-phase grouping* — loses lane identity, and the UI ends up re-deriving it by name anyway. Rejected: *streams replacing `dependsOn`* — streams express "same lane, therefore sequential"; `dependsOn` expresses cross-lane edges. Both are needed, and a task waits on both.

### D2 — Phases stay hard barriers

A stream may not start its phase-N+1 task until **all** of phase N is finished. Streams partition work *within* the active phase.

This is a deliberate conservatism. `be-planner`'s phases encode prerequisites that are frequently not written out as explicit `dependsOn` edges — P2 schema before P4 feature slices is treated as structural, not enumerated per task. Dropping the barrier in favour of pure dependency scheduling would race migrations against the code that reads them, on plans that are already written and correct under the current semantics.

The cost is honest and should be stated in the UI: a stream that finishes its phase work early **idles at the barrier**. Relaxing this later — letting a stream run ahead when its dependencies are individually satisfied — is a follow-on once plans reliably carry complete edges.

### D3 — `parallelSafe` becomes derived, not authored

A phase is sequential exactly when all its tasks share one stream. Keep the field for back-compat and for the planner's rationale text, but stop scheduling from it.

**Back-fill for existing runs and for planner output that predates streams:**

| Source | Derived streams |
|---|---|
| `parallelSafe: false` | one stream for the whole phase → identical behaviour to today |
| `parallelSafe: true` | one stream per task → maximum fan-out, same as today, then bounded by `maxParallel` |
| no `order` | array index, preserving the current implicit sequence |

Every existing run therefore schedules exactly as it does now, which is the property that makes this safe to land. Implemented at the same load seam as the schema versioning in plan 002 Phase 5.

### D4 — `maxParallel` becomes a ceiling on concurrent *streams*

Same field, same default, adjacent meaning: at most N lanes dispatch at once. When more streams are eligible than slots, they are admitted in ascending order of their next task's `order`, so the lane holding the earliest intended work goes first.

### D5 — File overlap becomes a plan-time constraint

Two tasks whose `files[]` intersect **must** share a stream. This is checked in `validatePlan` and reported as a plan defect with both task ids and the overlapping paths — before a single agent is dispatched.

`conflictsWithRunning()` stays as a runtime net, since `files[]` is a planner estimate and an agent may touch more than it declared. But it stops being the primary mechanism, and a trip on it becomes a signal that the plan was wrong rather than routine scheduling.

### D6 — Continuous scheduling replaces the batch barrier

The loop becomes: compute the eligible set → dispatch into free slots → **await the first settlement, not all of them** → re-evaluate. A finished stream immediately pulls its next task while its neighbours keep running.

```
while (phase has unfinished work) {
  admit ready streams into free slots        // ascending next-task order
  if (nothing in flight) → diagnose and stop // question, cycle, or review gate
  await Promise.race(in-flight)
}
```

The existing terminal diagnoses — all-blocked-on-questions, unmet-dependency-or-cycle, waiting-on-`review` — must all survive this rewrite; they are the loop's error handling and each corresponds to a real state seen in practice.

### D7 — "What's next" is derived, never stored

A second stored pointer would drift from the task statuses that actually decide dispatch. Derive on read:

- **per stream** — the running task, and the next one in `order`;
- **run level** — an *Up next* queue: for each idle stream its next task, then the remaining backlog sorted by `(phase.index, order)`;
- **per waiting task** — a machine-generated reason, one of: `stream busy — after T-14` · `waiting on T-07` · `blocked by question Q-2` · `phase P3 has not started` · `awaiting review`.

The reason line matters more than the queue. A board that shows twelve tasks not running and explains none of it is what makes people stop trusting the tool.

---

## Phases

### Phase 1 — Model and back-fill

- [ ] `types.ts`: add `Stream`, `Run.streams: Stream[]`, `Task.streamId`, `Task.order`
- [ ] Derivation on load per D3, at the plan-002 Phase-5 schema seam; stamp on next write
- [ ] Planner schema + prompt (`planner.ts`, `prompts.ts`): emit `streams[]`, `streamId`, `order`; instruct that tasks sharing a file must share a stream, and that a stream is a lane of genuinely sequential work rather than an arbitrary partition
- [ ] Derivation unit tests covering both `parallelSafe` branches and the missing-`order` case

**Acceptance:** every run in `.data/runs/` loads with streams and orders assigned, and replays its existing scheduling decisions unchanged.

### Phase 2 — Validation

- [ ] Extend `ValidatablePlan` with `streamId`, `order`, `files`
- [ ] New checks: every `streamId` resolves to a declared stream · `order` unique across the run · **overlapping `files[]` ⇒ same stream** (report both ids and the shared paths) · a `dependsOn` pointing at a *higher* `order` is an ordering contradiction · cycle detection across streams
- [ ] Surface failures on the plan-acceptance screen, before Start becomes available
- [ ] Tests for each new check

**Acceptance:** a plan placing two tasks that both write `src/db/schema.ts` into different streams is rejected with both ids named.

### Phase 3 — Continuous scheduler

- [ ] Rewrite the `startRun` inner loop per D6: `Promise.race` over in-flight tasks, top up free slots on each settlement
- [ ] `isDispatchable()` gains the stream rule: the task must be the lowest-`order` unfinished task of its stream within the active phase
- [ ] `selectParallelBatch` → `admitStreams(eligible, maxParallel)`, admitting by ascending next-task `order`
- [ ] Preserve all three terminal diagnoses and the execution-switch check on every iteration
- [ ] Concurrency tests with fake dispatch: a fast stream advances while a slow one runs; a stream never runs two tasks at once; `maxParallel` is respected; a cycle still fails loudly instead of spinning

**Acceptance:** on a phase with a 1-task fast stream and a 3-task slow stream, the fast stream's task starts and finishes without waiting for the slow stream's first task.

### Phase 4 — Board

- [ ] Swimlane rendering: streams as lanes, phase boundaries as barriers across them (`PhaseLane.tsx` becomes `StreamLane` within a phase band)
- [ ] Per-lane header: stream name, running task, next task, remaining count
- [ ] Run-level **Up next** panel per D7
- [ ] Waiting reason on every non-running card
- [ ] Visible idle-at-barrier state, so a stalled lane reads as "waiting for phase 2 to finish" rather than as a bug
- [ ] Manual **reorder within a stream** and **move task to another stream** before Start, re-running Phase 2 validation on the edit

**Acceptance:** with a run paused mid-phase, the board names the next task for every lane and gives a reason for every task that is not running.

### Phase 5 — Library contract

The `delivery-plan.md` ↔ Mission Control mapping documented in `CLAUDE.md` is currently `id · phaseId · title · intent · acceptanceCriteria[] · agent · skills[] · files[] · dependsOn[]` plus per-phase `parallelSafe`/`parallelRationale`. Streams change what a planner should emit.

- [ ] `backend/_shared/delivery-plan/SKILL.md`: add `streamId` + `order` to the task vocabulary and a streams table to the artifact; reframe the parallel-safety call as *"which lanes exist and why is each internally sequential"*, which is a more answerable question than a per-phase boolean and produces a better `parallelRationale`
- [ ] `CLAUDE.md`: update the Mission Control contract paragraph
- [ ] Keep the derivation in D3 as the compatibility path, so existing packs without streams still import correctly

**Acceptance:** a `be-planner` pack authored after this change imports with its streams intact and needs no derivation.

---

## Interaction with the 002 and 004 work

- **Worktrees (002 Phase 3)** — one worktree per *run*, not per stream. Concurrent streams share it, which is exactly why D5's same-file rule is enforced at plan time: parallel lanes writing one working tree is safe only if their file sets are disjoint. Should per-stream worktrees ever be wanted, the merge cost lands here first.
- **Verify-after-task (004)** — a verification pass belongs *inside* the stream, blocking that lane's next task while other lanes continue. That is a strictly better failure containment than the current batch barrier gives.
- **The existing `review` status** — already a real state the scheduler handles (`orchestrator.ts:139`). With streams it becomes far more useful: a lane can hold for human review without freezing the whole phase.

## Effort

Phase 1–2 about a day and a half, mostly mechanical plus tests. Phase 3 is the delicate one — two days, because the terminal diagnoses are subtle and deserve real concurrency tests. Phase 4 a day and a half. Phase 5 a few hours. **Call it five days.**
