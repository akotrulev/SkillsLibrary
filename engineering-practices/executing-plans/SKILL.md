---
name: ep-executing-plans
description: Use when you have a written implementation plan (from `ep-writing-plans`) to execute task-by-task with review checkpoints. Triggers: "execute this plan", "implement the plan", "work through docs/plans/…", after a plan is approved. Chains into `ep-finish-branch` when all tasks are done. Do NOT use to write the plan (use `ep-writing-plans`), to design the feature (use `ep-brainstorming`), or for ad-hoc edits that have no plan.
---

# Executing Plans

## Overview

Load plan, review critically, execute task-by-task, report at each checkpoint, and report when complete.

**Announce at start:** "I'm using the `ep-executing-plans` skill to implement this plan."

**This is the default execution path (inline, cost before speed).** A subagent-based alternative — `ep-delegate-to-subagents` — exists for the rare case where delegation clearly pays for itself and the user asks for it; it is governed by the cost-before-speed policy. Unless both are true, stay here.

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. If concerns: Raise them with the user before starting
4. If no concerns: Create the task list (TaskCreate) and proceed

### Step 2: Execute Tasks with Checkpoints

For each task:
1. Mark as in_progress (TaskUpdate)
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. Mark as completed (TaskUpdate)
5. **Checkpoint — report, then continue:** post a short summary and continue to
   the next task without waiting for a reply. Include:
   - the task just finished (name/number)
   - files created/modified
   - verification output (test/lint/build result — the actual pass/fail line)
   - what's next (the next task's name)

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
- Checkpoint after each task (files touched + verification output), then continue — unless the user asked to run through to the end
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Integration

**Required workflow skills:**
- **`ep-worktrees`** - Ensures isolated workspace (creates one or verifies existing)
- **`ep-writing-plans`** - Creates the plan this skill executes
- **`ep-finish-branch`** - Complete development after all tasks

**Opt-in alternative:**
- **`ep-delegate-to-subagents`** - subagent execution when delegation pays for itself (cost-aware); not the default
