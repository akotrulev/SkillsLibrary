---
name: ep-executing-plans
description: Use when you have a written implementation plan (from `ep-writing-plans`) to execute task-by-task with review checkpoints. Triggers: "execute this plan", "implement the plan", "work through docs/plans/…", after a plan is approved. Chains into `ep-finish-branch` when all tasks are done. Do NOT use to write the plan (use `ep-writing-plans`), to design the feature (use `ep-brainstorming`), or for ad-hoc edits that have no plan.
---

# Executing Plans

## Overview

Load plan, review critically, execute task-by-task, report at each checkpoint, and report when complete.

**Announce at start:** "I'm using the `ep-executing-plans` skill to implement this plan."

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. If concerns: Raise them with the user before starting
4. If no concerns: Create the task list (TaskCreate) and proceed

### Step 2: Execute Tasks with Checkpoints

**Work the tasks in the order the plan lists them.** The order is the plan's
dependency graph — a task's inputs are produced by the tasks above it. Don't
reorder, don't run ahead to a task that looks independent, and if a task cannot
be started at its position, that is a blocker to raise, not an ordering to fix
on the fly.

For each task:
1. Mark as in_progress (TaskUpdate)
2. **Run it as the agent the task's `Agent:` line names** — `Read` that agent's definition and follow its skill-loading protocol for the task's steps; a task whose agent you cannot resolve is a blocker, not a licence to improvise the stack's patterns. Where the plan carries a prompt block for the task (`## Prompts — one per task`), its reading list and traps are the first thing you read.
3. Work the task's bullets in order, exactly as written — they are the work and its checks at once, with the exact paths, names and values the plan settled on
4. **Run only the verifications your task's `Gate:` line authorizes.** The plan gates once, in
   its last runnable task: every task before it says `**Gate: none**` and names what not to run.
   Writing the tests is yours; running them is that task's. Do not "just check" with a build —
   it spends context on failures that belong to tasks nobody has written yet, and it reports a
   red tree as your failure. **If you are the last runnable task**, you carry the whole gate in
   run order and you **fix what it finds rather than handing it back**: a failure may belong to
   any task above you, and attributing it in your `As built` note is part of the task
5. **Confirm the task's stated `Deliverable` actually exists** — the endpoint
   answers, the migration applied, the test file exists and reads correctly. The
   deliverable is what "done" means; the bullets are only how you got there. On an
   ungated task, confirm it by reading the code you wrote, not by running the suite. **Stay inside the task's
   stack:** every task names exactly one, and a file outside that tree in the
   task's `Files` list means the task was mis-cut — that is a blocker to raise,
   not something to fix by widening your reach
6. Mark as completed (TaskUpdate)
7. **Write the record back into the plan, then maintain its prompts.** This is part of the
   task, not a write-up afterwards:
   - A dated `**As built:**` note on your task block — what differed from the plan, the ids and
     names you assigned, what is built but unverified, and the `file:line` or command output
     that proves the deliverable exists. Append; never edit one backwards.
   - The plan's header `**Status:**` line, rewritten: what is built, what is next, what is built
     but unverified.
   - `## Decisions`, where you built something differently from the plan — appended as a dated
     `D<n>`, with both readings. A divergence is escalated, never absorbed.
   - **Delete your own prompt block** in `## Prompts — one per task`, and update the line above
     the blocks saying which have landed. A prompt for a finished task is a thing someone runs
     by mistake, and the live prompt set is the plan's progress indicator.
   - **Rewrite the blocks below yours** wherever what you landed differs from what they assume —
     a renamed file, a changed signature, a moved gate. In place, no changelog appended.
   - **Write any block left `Blocked on <your task>`**, from what you now know. That duty is a
     bullet on your task and a line in your own prompt; a guessed block is the one kind of stale
     that reads as current.
   - Stopping mid-task keeps your block in place with a `Picking up from:` line; a blocked task
     keeps its block and names its blocker and owner, because deleting it loses the lane.
   - **If your deletion left no blocks at all, the plan is finished — file it.** Rewrite the
     `Status:` line one last time (what the plan delivered, and what is still **unverified**), then
     `git mv` the plan into `docs/plans/implemented/` keeping its filename and its number — a
     `solution-planner` pack moves its whole initiative folder, artifacts and all — and include the
     move in this task's commit. Say in your checkpoint where the plan went. **A plan still holding
     a blocked task's block does not move:** it stays in `docs/plans/`, which is what makes that
     folder answerable by listing it.

8. **Checkpoint — report, then continue:** post a short summary and continue to
   the next task without waiting for a reply. Include:
   - the task just finished (id + name, its stack and lane)
   - its deliverable, and the evidence it exists
   - files created/modified
   - the gate: `Gate: none — tests written, not run` on an ungated task, or the actual pass/fail lines and what you fixed if you carried the gate
   - what you wrote back: the `As built` note, the `Status:` line, your block deleted, which blocks below you repaired or wrote
   - what's next (the next task's id + name), or, if the plan is finished, where you filed it

   This is a **report, not a permission prompt** — you keep going. It exists so
   the user has a natural interception point to correct course mid-plan; the skill
   already stops on its own for blockers (see "When to Stop"). Don't ask "should I
   continue?" — just checkpoint and proceed.

**Batch rule (default = checkpoint after every task):** report after each task
unless the user says otherwise. The user may say **"run through to the end"** (or
"batch these", "no checkpoints") to collapse checkpoints — then run straight
through and report once at the end. They may also set a batch size ("checkpoint
every 3 tasks"); honor whatever they asked for. When in doubt, checkpoint per task.

### Step 3: Complete Development

After all tasks complete and verified:
- Announce: "I'm using the ep-finish-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use `ep-finish-branch`
- Follow that skill to verify tests, present options, execute choice

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker (missing dependency, instruction unclear, a task that can't start at its position)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- You carry the gate and a failure resists fixing, or you cannot tell which task it belongs to

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- The user updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- Review plan critically first
- Work the task's bullets exactly as written
- Don't skip the gate when it is yours, and don't run it when it is not
- Reference skills when plan says to
- Tasks are the unit of work — never call one a slice or a phase, in the plan or in a report
- Run them in the plan's order; a task that can't start where it sits is a blocker
- Run each task as the agent its `Agent:` line names; an unresolvable agent is a blocker
- **Obey the task's `Gate:` line.** `Gate: none` means write the tests and stop — the plan gates
  once, in its last runnable task, which fixes what the gate finds for the whole plan
- Before checkpointing: the `As built` note, the `Status:` line, `## Decisions` if you diverged,
  your own prompt block deleted, the blocks below yours repaired, and any block that was blocked
  on you written
- **No blocks left means the plan is done: move it to `docs/plans/implemented/`**, same name, same
  number, in your commit — unless a blocked task is still holding one
- Stay inside the task's stack; a file outside its tree is a mis-cut task, which is a blocker, not
  a licence to widen
- A task's `Budget` is a plan-time target, not a budget to manage mid-run — if the session is
  running long, that is a finding for the plan, not a reason to cut the task short
- Checkpoint after each task (deliverable + evidence + files touched + what you wrote back), then
  continue — unless the user asked to run through to the end
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Integration

**Required workflow skills:**
- **`ep-worktrees`** - Ensures isolated workspace (creates one or verifies existing)
- **`ep-writing-plans`** - Creates the plan this skill executes
- **`ep-finish-branch`** - Complete development after all tasks

**Alternative:**
- **`ep-delegate-to-subagents`** - execute the plan's tasks through subagents instead
