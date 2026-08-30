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
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. **Confirm the task's stated `Deliverable` actually exists** — the endpoint
   answers, the migration applied, the test file runs. The deliverable is what
   "done" means; the steps are only how you got there. **Stay inside the task's
   stack:** every task names exactly one, and a file outside that tree in the
   task's `Files` list means the task was mis-cut — that is a blocker to raise,
   not something to fix by widening your reach
5. Mark as completed (TaskUpdate)
6. **Write the record back into the plan** — status and `file:line` evidence, the
   criteria ticked in place, an append-only execution-log row, and anything you
   built differently from the plan. This is part of the task, not a write-up
   afterwards. **Then, where the plan pack has a `NEXT-PROMPTS.md`** (a
   `solution-planner` pack does), rewrite this lane's block for the lane's next
   task per `be-shared-session-budget` Step 5 — built from that task's own block,
   copied rather than paraphrased. If yours was the lane's last task, replace the
   block with a closed-lane line and check `epic-map.md` — a finished lane usually
   opens a wave, and every lane that just became runnable needs a block. Stopping
   mid-task keeps the block on the **same** task with a `Picking up from:` line;
   a blocked lane keeps its block and names its blocker and owner, because
   deleting it loses the lane.
7. **Checkpoint — report, then continue:** post a short summary and continue to
   the next task without waiting for a reply. Include:
   - the task just finished (id + name, its stack and lane)
   - its deliverable, and the evidence it exists
   - files created/modified
   - verification output (test/lint/build result — the actual pass/fail line)
   - the plan record written, and the prompt block rewritten (or why not)
   - what's next (the next task's id + name)

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
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- The user updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Tasks are the unit of work — never call one a slice or a phase, in the plan or in a report
- Run them in the plan's order; a task that can't start where it sits is a blocker
- Write the record back into the plan before checkpointing, and rewrite the lane's `NEXT-PROMPTS.md` block where the pack has one — the plan is the record, the prompts are only what's next
- Stay inside the task's stack; a file outside its tree is a mis-cut task, which is a blocker, not a licence to widen
- A task's `Est. context` is a plan-time target, not a budget to manage mid-run — if the session is running long, that is a finding for the plan, not a reason to cut the task short
- Checkpoint after each task (deliverable + evidence + files touched + verification output), then continue — unless the user asked to run through to the end
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Integration

**Required workflow skills:**
- **`ep-worktrees`** - Ensures isolated workspace (creates one or verifies existing)
- **`ep-writing-plans`** - Creates the plan this skill executes
- **`ep-finish-branch`** - Complete development after all tasks

**Alternative:**
- **`ep-delegate-to-subagents`** - execute the plan's tasks through subagents instead
