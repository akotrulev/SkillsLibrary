---
name: be-shared-session-budget
description: Use when plan tasks need sizing to one working session each, and when the next runnable task must be handed to an agent as a ready-to-paste prompt. Estimates a task's context cost, grows or splits it toward the session target, and writes NEXT-PROMPTS.md — one prompt per lane that can run right now, regenerated as each task lands. Triggers "how big should this task be", "is this one session", "what do I paste next". Do NOT use to sequence tasks (`be-shared-delivery-plan`), to group them into epics (`be-shared-epic-map`), or to execute one (`ep-executing-plans`).
---

# Session Budget — one task, one session, one prompt

Two jobs, both about the boundary between a plan and the sessions that run it.

- **Sizing.** A task is executed in one session, so its context cost is a property of the task. This skill estimates that cost before the task is ever run, so tasks are authored at the size the work actually is instead of being discovered too large halfway through a session.
- **Handoff.** The next runnable task of every lane is written as a **prompt** — the agent, the skills, the exact pack sections to read, the deliverable, the files, the criteria — into `NEXT-PROMPTS.md`. The operator pastes it; nobody re-derives it. When a task lands, the agent that ran it rewrites its lane's block for the next task.

**The estimate is a target, never a gate.** It says what to aim for. It does not decide what a task is — coherence does, and coherence wins every time the two disagree. Never split a task that is one thing to get under a number, and never merge unrelated work to fill one up.

**Announce at start:** "I'm using the `be-shared-session-budget` skill to size the tasks and write the prompts."

**Prerequisites:** a task list from `be-shared-delivery-plan` with `Files` filled in, and `epic-map.md` for the lane structure. Sizing a task whose files are vague produces a number with nothing behind it.

## When to use

- Step 8 of a `solution-planner` run — sizing the authored tasks and writing the first prompts
- Whenever a task is added, split, or re-scoped and its estimate needs re-deriving
- After a task completes — regenerating that lane's prompt block for the next task
- From `ep-writing-plans`, for the same sizing question on a non-`solution-planner` plan

## When NOT to use

- Deciding the order tasks run in → `be-shared-delivery-plan`
- Deciding which epics run at the same time → `be-shared-epic-map`
- Actually running a task → `ep-executing-plans`, or the named stack agent

## Output

Two things, both inside `docs/plans/<NNN>-<initiative>/`:

1. An **`Est. context:`** line on every task block in `delivery-plan.md`, and an `Est.` column in its progress table.
2. **`NEXT-PROMPTS.md`** — one prompt block per lane that is runnable right now. See `references/next-prompts-template.md`.

---

## Procedure

### Step 1 — Estimate the task

Add up the lines that apply, then apply the churn multiplier. Everything is in tokens; report to the nearest 5k.

**The floor — every session pays it, once:**

| Line | Estimate |
|---|---|
| System prompt + tool schemas | 12k |
| `CLAUDE.md` and project instructions | 6k |
| The executing agent's own definition | 7k |
| **Floor** | **25k** |

**Loaded once per session:**

| Line | Estimate |
|---|---|
| Each distinct skill the task loads (`SKILL.md` + the references it opens) | 8k |
| The task block itself | 1k |
| Each design-pack section the task cites (`api-surface.md` §5.3, one `data-model.md` entity block, one `experience-plan.md` screen) | 2k |
| Orientation — repo survey + orientation cache, **brownfield only** | 8k |

**Per file the task touches** — this is where the real weight is:

| Line | Estimate |
|---|---|
| An existing file the task must read | `bytes ÷ 3.5`, rounded up — or **3k** when it cannot be measured |
| A source file the task creates | 2k |
| A UI component or screen the task creates | 3k |
| A test file the task creates | 2k |
| A file modified in place (the read plus the edit) | 1.5k |
| A one-line registration, config key, or migration entry | 0.5k |

**Per task, once:**

| Line | Estimate |
|---|---|
| Build + test run, their output, and the fix loop they trigger | 12k |
| Conversation, tool churn, re-reads after edits | **× 1.2** on the sum of everything above |

So: `Est. = (floor + skills + pack sections + orientation + files + verify) × 1.2`.

**Worked example** — a `be-dotnet` task creating an Orders resource: floor 25k + 3 skills 24k + task block 1k + 3 pack sections 6k + 5 files created (4 source at 2k, 1 test at 2k) 10k + 1 file modified 1.5k + verify 12k = 79.5k, × 1.2 = **95k**. Comfortably one session, with room to absorb the next coherent piece.

### Step 2 — Compare against the target and act

| Estimate | What it means | What to do |
|---|---|---|
| **under ~80k** | The session is underfilled | Look at the next task in the same story, same stack, same agent. If merging them still yields **one** deliverable, merge. If it does not, leave it alone — a small task is not a defect |
| **~80k – ~150k** | The size to aim for | Nothing. This is the target |
| **over ~150k** | The session will be long, and may need a compaction | Annotate, do not force. Record the estimate on the task and name the natural split point if one exists (`splits cleanly after the endpoints land`). Split **only** if that point yields two tasks that each state one deliverable and each leave the tree green |

**The three rules that outrank the number:**

- **One deliverable.** Two deliverables is two tasks at any estimate; no statable deliverable is a fragment at any estimate.
- **One stack, one agent.** A merge that spans `fe` and `be` is not a merge, whatever it costs.
- **The tree is green at the boundary.** A split that leaves the build red between the pieces was a bad seam — the pieces are one task, and the estimate does not get a vote.

A task that overshoots the target with all three rules satisfied is a **large task**, correctly authored. Say so on it rather than filing it as a defect.

### Step 3 — Record the estimate

On the task block, under `Stream` / `Order`:

```markdown
**Est. context:** ~95k — 5 files created, 1 modified, 3 skills, 3 pack sections
```

One line, with what drives it, so a reader can tell a 95k of many small files from a 95k of one huge one. In the progress table it is one `Est.` column.

Re-derive it whenever the task's `Files`, `Skills`, or cited sections change. A stale estimate is worse than none — it is a number someone will trust.

### Step 4 — Write `NEXT-PROMPTS.md`

**One block per lane that is runnable right now**, and nothing else. A lane is runnable when its dependencies are `Done` and no gate blocks it; `epic-map.md`'s current wave says which lanes those are. At the start of a run that is the first task of every wave-1 epic — which is exactly the set of sessions the operator can open at the same time.

Each block is a **prompt, not a summary**. It is pasted verbatim into a fresh session, so it carries everything that session needs and names nothing it does not:

- The agent to adopt and the skills to load.
- **The exact pack sections to read** — `api-surface.md` §5.3, not `api-surface.md`. This is the single biggest lever on the estimate holding: a session told to read the whole pack reads the whole pack.
- The deliverable, the files, the acceptance criteria, and what is out of scope.
- The closing duty: update `delivery-plan.md`, then regenerate this block for the next task.

The full template and a filled example are in `references/next-prompts-template.md`.

### Step 5 — Regenerate after each task

**This is the executing agent's duty, not the planner's**, and it is part of finishing the task rather than a write-up afterwards. When a task reaches `Done`:

1. Write the status, evidence and ticked criteria into `delivery-plan.md` (§2, §3, §6) — the durable record.
2. **Replace that lane's block in `NEXT-PROMPTS.md`** with the prompt for the lane's next task, built from its task block by this skill's Step 4.
3. If the finished task was the lane's last, replace the block with a closed-lane line naming what the lane delivered, and check `epic-map.md` — completing an epic usually unblocks a wave, and every lane that just became runnable needs a block.
4. If the task ended `Partial`, `Blocked` or `Diverged`, the block stays on the **same** task and gains a `**Picking up from:**` line naming what remains. A blocked lane keeps its block and states what it waits on — deleting it loses the lane.

`NEXT-PROMPTS.md` is rewritten, never appended. It holds only what to do next; history lives in `delivery-plan.md` §6. The two files disagreeing is always the plan being right.

---

## Rules

- **Estimate before authoring is finished, not after.** The number is an input to how the task is written. Producing a task list and then measuring it turns the estimate into trivia.
- **Never cite a whole artifact in a prompt.** Sections, always. `data-model.md` is 40k of context; the two entity blocks the task needs are 4k.
- **The floor is not negotiable and not divisible.** Two tasks in one session do not pay one floor — they are one task, or they are two sessions.
- **An unknown file size is 3k, and it is written as an assumption.** Do not silently guess a number that reads like a measurement.
- **A lane with no runnable task gets a line, not silence.** "Blocked on U2 (Stripe sandbox credentials — owner: Ana)" is the answer to "what do I paste next" for that lane.
- **The prompt names one task.** A block that hands over two tasks is a block that will get half-done and then re-derived from scratch.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Splitting a coherent task to land under the target | Produces two tasks neither of which can be verified alone, and a red tree between them |
| Padding a task with unrelated work to reach the target | A bucket with one number on it; the second deliverable gets dropped when the session runs long |
| `Est. context: ~95k` with nothing behind it | Unfalsifiable. The drivers are what make it checkable and re-derivable |
| A prompt that says "read the plan pack" | The session spends its budget reading and its output suffers for it |
| Leaving `NEXT-PROMPTS.md` for the end of the session | It is the one artifact whose whole value is being current. Regenerate it as the task closes |
| Deleting a blocked lane's block | The lane looks finished. Blocked lanes state their blocker and their owner |

## Self-check

1. Every task in `delivery-plan.md` carries an `Est. context:` line with its drivers, and the progress table's `Est.` column agrees with it.
2. Every estimate over ~150k either names its natural split point or states why the task is one thing anyway.
3. No task was split or merged in a way that breaks one deliverable, one stack, or a green tree at the boundary.
4. `NEXT-PROMPTS.md` has one block per currently-runnable lane — no more (a lane whose dependencies are unmet has no block), no fewer (a runnable lane with no block is a session nobody knows they can start).
5. Every block names one task, an exact agent, exact skills, and **sections** rather than artifacts.
6. Every block ends with the update-and-regenerate duty, naming `delivery-plan.md` and this file.
7. Blocked lanes appear with their blocker and its owner.

## Handoffs

- **← `be-shared-delivery-plan`** — supplies the tasks, their files, their streams and their order. Sizing feeds straight back into how those tasks are written.
- **← `be-shared-epic-map`** — supplies the lanes and the current wave, which is what decides who gets a prompt block.
- **→ `be-dotnet` / `be-java` / `be-node` / `be-python` / `fe-react` / `fe-blazor`** — consume the prompt blocks and own Step 5's regeneration when their task lands.
- **→ `ep-executing-plans`** — the task-by-task loop; its per-task checkpoint is where Step 5 runs.
- **→ `ep-writing-plans`** — uses Step 1 and Step 2 for the same sizing question on plans that never went through `solution-planner`.

## Version policy

The cost model is calibrated for a ~200k-token working window with the target set at one comfortable session inside it. It is stack-agnostic — a file is a file. The one stack-sensitive line is the verify cost: a project whose test suite prints thousands of lines pays more than 12k, and the orientation pass is where that is discovered. Adjust the constant for the project and say that you did; do not carry a number that the first session disproved.
