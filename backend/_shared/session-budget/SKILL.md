---
name: be-shared-session-budget
description: Use when plan tasks need sizing to one working session each, and when each task must be handed to an agent as a ready-to-paste prompt. Estimates a task's context cost, grows or splits it toward the session target, and writes the plan's own `## Prompts — one per task` section — one block per task, deleted as each task lands. Triggers "how big should this task be", "is this one session", "what do I paste next". Do NOT use to sequence tasks (`be-shared-delivery-plan`), to group them into epics (`be-shared-epic-map`), or to execute one (Plan Queue, as the task's named agent).
---

# Session Budget — one task, one session, one prompt

Two jobs, both about the boundary between a plan and the sessions that run it.

- **Sizing.** A task is executed in one session, so its context cost is a property of the task. This skill estimates that cost before the task is ever run, so tasks are authored at the size the work actually is instead of being discovered too large halfway through a session.
- **Handoff.** Every task is written as a **prompt** — the agent, the skills, the exact pack sections to read, the deliverable, the files, the bullets, the traps and the gate — into the plan's own `## Prompts — one per task` section. The operator pastes it; nobody re-derives it. The plan document is self-contained and queueable on purpose: there is no `NEXT-PROMPTS.md`. When a task lands, the agent that ran it **deletes its own block** and rewrites the ones below it wherever what it landed differs from what they assume.

**The estimate is a target, never a gate.** It says what to aim for. It does not decide what a task is — coherence does, and coherence wins every time the two disagree. Never split a task that is one thing to get under a number, and never merge unrelated work to fill one up.

**Announce at start:** "I'm using the `be-shared-session-budget` skill to size the tasks and write the prompts."

**Prerequisites:** a task list from `be-shared-delivery-plan` with `Files` filled in, and `epic-map.md` for the lane structure. Sizing a task whose files are vague produces a number with nothing behind it.

## When to use

- Step 8 of a `solution-planner` run — sizing the authored tasks and writing the prompt blocks
- Whenever a task is added, split, or re-scoped and its estimate needs re-deriving
- After a task completes — deleting its block and repairing the ones below it
- From `ep-writing-plans`, for the same sizing question on a non-`solution-planner` plan

## When NOT to use

- Deciding the order tasks run in → `be-shared-delivery-plan`
- Deciding which epics run at the same time → `be-shared-epic-map`
- Actually running a task → the named stack agent, one prompt block per session through Plan Queue

## Output

Two things, both **inside the plan document** — `docs/plans/<NNN>-<initiative>/delivery-plan.md`, or the single-file plan an `ep-writing-plans` run produced:

1. A **`**Budget:**`** line on every task block, with its drivers itemized, and a matching `Budget` cell in the task table.
2. The **`## Prompts — one per task`** section — one paste-ready block per task that has not landed. See `references/prompts-section-template.md`.

The plan document format both of these live in is specified in `engineering-practices/writing-plans/references/plan-format.md`; read it before writing either.

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
| The output the task reads back — its own commit and diff, on an ungated task | 6k |
| The **last runnable task only**: the whole gate, its output, and the fix loop it triggers across the plan | 12k, plus 4k per earlier task whose failures it may have to fix |
| Conversation, tool churn, re-reads after edits | **× 1.2** on the sum of everything above |

So: `Budget = (floor + skills + pack sections + orientation + files + read-back) × 1.2`.

**The gate is budgeted once, on the task that runs it.** The plan gates in its last runnable task, so every earlier task pays 6k for its own diff rather than 12k for a verify loop it is told not to run — and the gate task pays for the whole plan's fallout, which is why it is usually the largest task in the plan and why it must not also carry a big build.

**Worked example** — a `be-dotnet` task creating an Orders resource: floor 25k + 3 skills 24k + task block 1k + 3 pack sections 6k + 5 files created (4 source at 2k, 1 test at 2k) 10k + 1 file modified 1.5k + read-back 6k = 73.5k, × 1.2 = **~90k**. Comfortably one session, with room to absorb the next coherent piece.

### Step 2 — Compare against the target and act

| Estimate | What it means | What to do |
|---|---|---|
| **under ~80k** | The session is underfilled | Look at the next task in the same story, same stack, same agent. If merging them still yields **one** deliverable, merge. The goal is the **fewest sessions**, not the smallest tasks — an agent switch costs a whole context reload. If it does not merge cleanly, leave it alone — a small task is not a defect |
| **~80k – ~150k** | The size to aim for | Nothing. This is the target |
| **over ~150k** | The session will be long, and may need a compaction | Annotate, do not force. Record the estimate on the task and name the natural split point if one exists (`splits cleanly after the endpoints land`). Split **only along a seam inside the same stack**, and only if that point yields two tasks that each state one deliverable |

**The three rules that outrank the number:**

- **One deliverable.** Two deliverables is two tasks at any estimate; no statable deliverable is a fragment at any estimate.
- **One stack, one agent.** A merge that spans `fe` and `be` is not a merge, whatever it costs.
- **The work is whole at the boundary.** A split that leaves a service with no caller, or an endpoint nobody registered, was a bad seam — the pieces are one task, and the estimate does not get a vote. A split that leaves the *build* red is fine: the plan gates once, and that failure is the gate task's to fix.

A task that overshoots the target with all three rules satisfied is a **large task**, correctly authored. Say so on it rather than filing it as a defect.

### Step 3 — Record the budget

On the task block, under `Depends on`:

```markdown
**Budget:** ~90k — CLAUDE.md 25k, `api-surface.md` §5 and two `data-model.md` entity blocks 6k,
3 skills 24k, `src/Billing/*` as the module pattern ~12k, 5 files created and 1 modified 11.5k,
commit and diff read-back 6k, churn ×1.2
```

**Itemize the drivers, don't summarize them.** A bare `~90k` is unfalsifiable; the list is what makes
it checkable and re-derivable, and it lets a reader tell a 90k of many small files from a 90k of one
huge one. In the task table it is one `Budget` cell, carrying the figure only.

Re-derive it whenever the task's `Files`, `Skills`, or cited sections change. A stale budget is worse
than none — it is a number someone will trust.

### Step 4 — Write `## Prompts — one per task`

**One block per task that has not landed, inside the plan document**, in task order. The plan is
queued and handed over whole, so the prompts live in it — see
`engineering-practices/writing-plans/references/plan-format.md` §6 for the section's shape, and
`references/prompts-section-template.md` for the filled template.

The section opens with a preamble — run them in order, one session each, each block complete on its
own; where the gates run; and anything **no** prompt may do — then the task table, then the line saying
which blocks have been deleted, then the blocks themselves.

Each block is a **prompt, not a summary**. It is pasted verbatim into a fresh session, so it carries
everything that session needs and names nothing it does not:

- The agent to adopt and the skills to load.
- **The exact pack sections to read** — `api-surface.md` §5.3, not `api-surface.md`. This is the single
  biggest lever on the budget holding: a session told to read the whole pack reads the whole pack.
- The deliverable, the files, the work bullets, and what is out of scope — copied from the task block,
  never paraphrased.
- **The traps**: the two to four things specific to that task. The convention that is easy to miss, the
  file that looks like the pattern but is not, the migration that must run before the test, the
  down-level API that does not exist here. This is the part the prompt adds, and it is what earns it.
- **The gate line.** `Gate: none — this plan gates once, in <the last runnable task>. Do not run <the
  commands>.` on every block but the last; the last block carries the project's own commands in run
  order, and the instruction to **fix what they find rather than hand it back**.
- The closing duty: write the `As built` note and the header `Status:` line, delete this block, and
  repair the blocks below it.

**A block you cannot write yet is not guessed.** Where it genuinely depends on what an earlier task
lands — the shape of a file it has not created, an id it will assign, a decision it will make — write
`**Blocked on <id>** — <id> writes this prompt when it lands, from <what it will then know>.` and put
writing it in **that** task's bullets and in its own prompt's closing duty. A guessed block is the one
kind of stale that reads as current.

### Step 5 — Maintain the section as each task lands

**This is the executing agent's duty, not the planner's**, and it is part of finishing the task rather
than a write-up afterwards. When a task is done:

1. Write the dated `**As built:**` note onto its task block, with the `file:line` or command output
   that proves the deliverable exists, and rewrite the header `**Status:**` line — what is built, what
   is next, what is built but unverified.
2. **Delete its own prompt block**, and update the line above the blocks
   (*"B1 and B2 have landed, and their prompts are deleted"*). A prompt for a finished task is a thing
   someone runs by mistake, and the live prompt set is the plan's progress indicator.
3. **Rewrite the blocks below it** wherever what landed differs from what they assume — a renamed file,
   a changed signature, a gate that moved. In place, no changelog appended.
4. **Write any block that was `Blocked on` this task**, from what it now knows.
5. If the task was the plan's last runnable one, it ran the gate and fixed what it found; its `As built`
   note says what the gate caught and which task it belonged to.
6. If the task ended partial, blocked or diverged, **the block stays** and gains a
   `**Picking up from:**` line naming what remains — the unfinished bullets are that list. A blocked
   task keeps its block and names what it waits on and who owns it; deleting it loses the lane.
7. **If step 2 left no blocks at all, the plan is finished — file it.** Rewrite the `Status:` line
   one last time (what the plan delivered, what is still **unverified**), then `git mv` the plan — or
   the whole initiative folder — into `docs/plans/implemented/`, keeping its name and its number, in
   this task's commit. A plan still holding a blocked task's block stays in `docs/plans/`: that folder
   answers "what is in flight" by being listed, and moving a waiting plan hides the wait.

The prompts section is rewritten, never appended; the durable history is the `As built` notes and
`## Decisions`, which are append-only. Where the two disagree, the `As built` notes are right.

---

## Rules

- **Estimate before authoring is finished, not after.** The number is an input to how the task is written. Producing a task list and then measuring it turns the estimate into trivia.
- **Never cite a whole artifact in a prompt.** Sections, always. `data-model.md` is 40k of context; the two entity blocks the task needs are 4k.
- **The floor is not negotiable and not divisible.** Two tasks in one session do not pay one floor — they are one task, or they are two sessions.
- **An unknown file size is 3k, and it is written as an assumption.** Do not silently guess a number that reads like a measurement.
- **A task that cannot be run gets a line, not silence.** "Blocked on H1 (Stripe sandbox credentials — owner: Ana)" is the answer to "what do I paste next" for it, and it stays in the section.
- **A prompt that cannot be written yet is written by the task that unblocks it**, never guessed at plan time — and that duty is on the blocking task, not in a note nobody owns.
- **The last block carries the filing duty.** Deleting it is what finishes the plan, so it says to
  rewrite `Status:` and move the plan into `docs/plans/implemented/`. A block that ends without it
  leaves finished plans sitting in the live folder, which is the one thing that folder is for.
- **The gate is budgeted and written once**, on the last runnable task. A block that tells an intermediate task to run the build is the rule's most common violation and the most expensive: it pays 12k for a verify loop whose failures belong to tasks that have not been written yet.
- **The prompt names one task.** A block that hands over two tasks is a block that will get half-done and then re-derived from scratch.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Splitting a coherent task to land under the target | Produces two tasks neither of which can be verified alone, and a half-written seam between them |
| Padding a task with unrelated work to reach the target | A bucket with one number on it; the second deliverable gets dropped when the session runs long |
| `Budget: ~95k` with nothing behind it | Unfalsifiable. The itemized drivers are what make it checkable and re-derivable |
| A prompt that says "read the plan pack" | The session spends its budget reading and its output suffers for it |
| Leaving the prompts section for the end of the session | It is the one part of the plan whose whole value is being current. Maintain it as the task closes |
| Deleting a blocked task's block | The task looks finished. A blocked task keeps its block and states its blocker and owner |
| Keeping a landed task's block "for the record" | Someone runs it again. The record is the `As built` note; the live prompt set is what is left to do |

## Self-check

1. Every task carries a `**Budget:**` line with its drivers itemized, and the task table's `Budget` cell agrees with it.
2. Every estimate over ~150k either names its natural split point — inside its own stack — or states why the task is one thing anyway.
3. No task was split or merged in a way that breaks one deliverable, one stack, one agent, or whole work at the boundary.
4. `## Prompts — one per task` has one block per task that has not landed — no more (a landed task's block is deleted), no fewer (a task with no block is a session nobody knows they can start), and each `Blocked on <id>` placeholder is matched by a bullet on that task.
5. Every block names one task, an exact agent, exact skills, and **sections** rather than artifacts, and carries its traps.
6. Exactly one block carries the gate — the last runnable task's — with the project's own commands in run order and the instruction to fix what they find. Every other block says `Gate: none` and names what not to run.
7. Every block ends with the closing duty: the `As built` note, the `Status:` line, deleting its own block, and repairing the ones below it — and the block that will delete the **last** one also carries the move into `docs/plans/implemented/`.
8. Blocked tasks appear with their blocker and its owner.

## Handoffs

- **← `ep-writing-plans`** — owns the plan document format these prompts live in (`engineering-practices/writing-plans/references/plan-format.md` §6). Where the two disagree on the shape, that reference wins.
- **← `be-shared-delivery-plan`** — supplies the tasks, their files, their streams and their order. Sizing feeds straight back into how those tasks are written.
- **← `be-shared-epic-map`** — supplies the lanes and the current wave, which is what decides who gets a prompt block.
- **→ `be-dotnet` / `be-java` / `be-node` / `be-python` / `fe-react` / `fe-blazor`** — consume the prompt blocks and own Step 5 when their task lands: the `As built` note, the `Status:` line, deleting their own block and repairing the ones below it.
- **→ plan format §7** — the `## Close-out — every task` section every plan carries; it is what tells each queued session to run Step 5.
- **→ `ep-writing-plans`** — uses Step 1 and Step 2 for the same sizing question on plans that never went through `solution-planner`.

## Version policy

The cost model is calibrated for a ~200k-token working window with the target set at one comfortable session inside it. It is stack-agnostic — a file is a file. The one stack-sensitive line is the gate task's verify cost: a project whose test suite prints thousands of lines pays more than 12k, and the orientation pass is where that is discovered. Adjust the constant for the project and say that you did; do not carry a number that the first session disproved.
