---
name: plan-feature
description: Use when you have an approved spec or clear requirements and need an implementation plan before touching code — one self-contained document: context, decisions, an ordered task list and one paste-ready prompt per task, run through Plan Queue. Triggers: after `dev:design` approves a design, "write the implementation plan", "break this spec into tasks". Do NOT use to design the idea itself (`dev:design`), to execute a written plan, or for a single trivial edit.
---

# Writing Plans

## Overview

Write the plan for an engineer who is skilled but has zero context for this codebase — who knows
almost nothing about our toolset or our problem domain, and whose taste you should not rely on.
Document what they need: what exists today and what is missing, the decisions already made and what
they cost, which files each task touches, the real values the code will use, and the traps that
specific task will hit. DRY. YAGNI. Frequent commits.

**The plan document format is a contract — read it before writing anything.** It is at
[`./references/plan-format.md`](./references/plan-format.md): the header, the numbered sections, the
task block's fields, the gate-once rule, and the `## Prompts — one per task` section. This skill is
the procedure; that file is the shape. Do not improvise either.

**Three properties of that format drive everything below:**

1. **One self-contained file.** The plan is queued whole — by the Plan Queue VS Code plugin, by a
   session, by a person. Everything a cold reader needs is in it, including the paste-ready prompt for
   each task. There is no companion file.
2. **The narrative comes first; the tasks come last.** A task block is only readable against the
   context above it, so `## 1. What already exists, and what is missing` and the sections that decide
   the work are written *before* any task is.
3. **The plan gates once, in its last runnable task.** Every task before it writes code and tests,
   commits, and stops.

**The unit of work is a task.** A plan is one flat, ordered list of them, ids prefixed by the family of
work (`B1`, `B2`, `B3`, then `P1`) — never a "slice", never a "phase", never a "stage", and never
grouped into any of those. A task's *internal* actions are its **steps**; that is the only thing the
word "step" names. Use the word **task** in the plan, in the checkpoint reports, and when talking to
the user, so the same thing has the same name everywhere.

**Context:** Write the plan on whatever branch you are already on — do not create or check out a branch
or worktree to author it. Plan Queue gives each plan its own worktree when it runs, so plans can run in
parallel; nothing in the plan creates branches or worktrees.

**Save plans to:** `docs/plans/NNN-<feature-name>.md` — the live folder. A plan moves to
`docs/plans/implemented/` once every task in it has landed (format reference §8), and that is done by
the task that deletes the last prompt block, not by you.
- `NNN` is zero-padded and sequential, and **its high-water mark spans both folders**: list
  `docs/plans/` *and* `docs/plans/implemented/`, take the highest existing `NNN` prefix (files and
  folders both count), use `highest + 1` — `001` if neither folder exists. Never reuse or renumber an
  existing number; a moved plan's number stays spent, because it is cited by commit messages, prompt
  blocks and `Depends on` lines that outlive the plan being live.
- Resolve the path under the **current project's** root — the repo the session is working in — never
  this skills-library checkout and never a global config directory, unless the user explicitly asks
  for a global copy. (A user preference for plan location overrides this default.)

**Commands:** Every build, test, lint, format and migration command written into the plan is the
**project's own**, read from the repo (`package.json` scripts and `packageManager`, the `Makefile`, the
`.csproj`/`gradle` layout, the CI workflow) — never a guessed default. The snippets in the format
reference are shapes, not the required runner.

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs
during brainstorming. If it wasn't, suggest one plan per subsystem. Each plan should produce working,
testable software on its own.

## Step 1 — Ground the plan before you decompose it

**Write `## 1. What already exists, and what is missing` first**, as a `| Need | Today | Gap |` table —
one row per thing the plan must deliver, what the codebase does about it today with a `file:line` or a
function name, and what is missing. Read the code to fill the `Today` column; do not infer it.

On a greenfield plan the `Today` column is `—` and the table is still written. It is the plan's
grounding: **every task below must trace to a row**, and a row with no task is a gap the plan forgot.

Then write the sections that actually decide the work — the data shape, the matrix, the script, the
flow, what is measured, how it runs, what it reports. Real values, exact paths, exact commands. Any
choice you make while writing them becomes a `**D<n>**` entry in `## Decisions` with what it costs, and
any question you could not answer becomes an `## Open questions` row naming what it blocks.

## Step 2 — Map the files

Before defining tasks, map out which files will be created or modified and what each is responsible
for. This is where decomposition decisions get locked in, and it is what the task cut and the budget
are both derived from.

- Design units with clear boundaries and well-defined interfaces. One clear responsibility per file.
- You reason best about code you can hold in context at once, and your edits are more reliable when
  files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't
  unilaterally restructure — but if a file you're modifying has grown unwieldy, planning a split is
  reasonable.

## Step 3 — Put the tasks in workable order

**Tasks are listed in the order they are done, and the list is flat.** No grouping layer sits above
them — the sequence itself carries the ordering, and the third task is "the third thing you do".

- **Everything a task needs already exists when its turn comes.** Whatever it imports, calls, migrates
  against, registers with, or configures was produced by an earlier task. A task that cannot be started
  at its position is in the wrong position — move it, don't annotate it.
- **Dependencies are stated, not implied.** Where a task needs an earlier one that is not immediately
  before it, say so: `**Depends on:** B1 (the ledger column)`. Adjacency is not a dependency claim, and
  a dependency on a later task is a defect in the ordering, not an exception to note.
- **Everything both sides bind to comes first** — the API contract, the schema, the shared types — then
  the backend tasks, then the shared-package tasks, then the frontend tasks.
- **Prerequisites a human must do come first**, as their own tasks with `Agent: human` and an
  `**Owner:**` line (an account to provision, an API key to request, a run only they can start), so
  nothing downstream stalls on them silently.
- **Fill the session, then stop.** Merge consecutive same-stack work into one task until it would
  exceed the budget target, then start the next. **The goal is the fewest sessions, not the smallest
  tasks** — an agent switch costs a whole context reload, so a plan of twenty tiny tasks is more
  expensive than one of eight full ones, and it re-reads the same files eight times instead of once.
- **Documentation and close-out ride with the last task**, never a session of their own. That session
  is the only one that knows what actually landed.

**Because the plan gates once, the tree is not guaranteed green at every task boundary.** Say so in the
plan, in those words. It is the deliberate price of one verify-and-fix loop per plan instead of one per
task, and it means the plan cannot be stopped halfway and trusted. Where a stack-cut task cannot be
demonstrated end to end on its own — a backend task whose screen arrives two tasks later — say so in
its `Not in <id>` line rather than pretending the capability landed, and have the contract-first side
return an explicit not-implemented response, never a fake success.

## Step 4 — One stack, one agent, one session per task

**Every task names exactly one stack:** `be` (backend, database, migrations) · `fe` (the web client) ·
`ts` (shared TypeScript packages — CLI, MCP, generated clients) · `data` · `infra` · `qa` · `docs` ·
`human`.

> **A task that touches both the API tree and the web tree is two tasks.** There is no mixed task at
> any size, and no estimate justifies one.

This is what makes a task handable to a single agent without it wandering across a boundary it does not
own, and it is what makes the ordering mechanical rather than a judgement call — same-stack work is
already adjacent. **Split along a seam inside the same stack**, never by handing part of a task to
another stack.

**Every task also names its agent** — an exact catalog name on the same line as the stack
(`be-dotnet`, `be-java`, `be-node`, `be-python`, `fe-react`, `fe-blazor`, `data-architect`,
`devops-engineer`, `tooling-engineer`, `qa-api-<stack>`, …). One stack, one agent, one session: the
agent is who the session is opened as, and it is who each prompt block tells the session to be. A task whose agent you cannot name is a task whose stack you
have not actually decided; an invented agent name is the most damaging defect in the document.

## Step 5 — Budget the session

**One task is executed in one session, so its context cost is a property of the task.** Estimate it
**while you are authoring the task** — not afterwards, which turns the number into trivia rather than
an input to how the task is written.

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
| Each distinct skill the task loads | 8k |
| The task block plus the plan sections it reads | 1k + 2k per section |
| Orientation — repo survey + orientation cache (brownfield only) | 8k |

**Per file the task touches:**

| Line | Estimate |
|---|---|
| An existing file the task must read | `bytes ÷ 3.5`, or **3k** when it cannot be measured |
| A source file created | 2k |
| A UI component or screen created | 3k |
| A test file created | 2k |
| A file modified in place | 1.5k |
| A registration, config key, or migration entry | 0.5k |

**Per task, once:** the output it reads back, **6k** for an ungated task (its own commit and diff) or
**12k** for the last task (the whole gate and the fix loop it triggers); then **× 1.2** on the sum for
conversation and tool churn.

`Budget = (floor + skills + sections + orientation + files + read-back) × 1.2`

**Worked example** — a task creating an Orders resource: 25k floor + 24k (3 skills) + 1k task block +
6k (3 sections) + 10k (4 source files + 1 test) + 1.5k (1 modified) + 6k read-back = 73.5k × 1.2 =
**~90k**.

**Aim for ~80k–150k, centred on ~130k.** Under ~80k, look at the next task in the same stack — merge
only if the result still states **one** deliverable. Over ~150k, name the task's natural split point,
inside its own stack.

Record it on the task **with its drivers itemized**, so a reader can tell a 95k of many small files
from a 95k of one large one:

```markdown
**Budget:** ~95k — CLAUDE.md 25k, plan §2 and §4 4k, `OrderService.cs` + its tests as the pattern ~12k,
3 skills 24k, 5 files created and 1 modified 11.5k, commit and diff read-back 6k, churn ×1.2
```

Re-derive it whenever the task's files, skills or cited sections change. A stale budget is worse than
none — it is a number someone will trust.

> **The budget is a guide, never a gate.** Three rules outrank it, always: one deliverable; one stack
> and one agent; the plan's single gate lands in its last runnable task. A task that overshoots with
> all three satisfied is a large task correctly authored — it is labelled, not filed as a defect. Never
> split something coherent to hit a number, and never pad a task to fill one.

## Step 6 — Write the task blocks and the prompts

Both shapes are specified in [`./references/plan-format.md`](./references/plan-format.md) §4 and §6.
Three rules are easy to get wrong and expensive when you do:

- **Every task but the last carries `**Gate: none**`**, naming the commands it must not run. The last
  runnable task carries the whole gate, in run order, and **fixes what it finds rather than handing it
  back**.
- **A prompt you cannot write yet is not guessed.** Where a block genuinely depends on what an earlier
  task lands — the shape of a file it has not created, an id it will assign, a decision it will make —
  write `**Blocked on <id>** — <id> writes this prompt when it lands, from <what it will then know>.`
  and put "write B4's prompt block" in the blocking task's bullets **and** in its own prompt's closing
  duty. Guessing the block produces the one kind of stale that reads as current.
- **Every plan carries `## Close-out — every task`**, copied verbatim from the format reference §7,
  directly above the prompts, and every block names it last in its reading list and ends with its
  close-out line. A queued session loads nothing else, so this is the only place it learns to write
  its `As built` note, repair the blocks below it, delete its own block and file the plan.
- **The block that will delete the last prompt carries the filing duty.** Deleting the last block is
  what finishes the plan (§8). The close-out's step 6 already tells every task to file the plan when its
  deletion leaves no blocks; where a blocked task will still be holding a block, say so in the last
  runnable block: that plan stays in `docs/plans/` until it clears.

## No Placeholders

The format reference §9 lists what is never in a plan. The two worth repeating while you write:
**"similar to B2" is not content** — the executing session may read the tasks out of order, so repeat
it — and **a `**Status:**` line that says "in progress"** without saying what is built and what is
unverified is worse than no status at all.

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it.

1. **Grounding:** every row of `## 1.`'s gap table traces to a task, and every task traces back to a
   row. List any gap in either direction.
2. **Spec coverage:** skim each section of the spec. Can you point to a task that implements it?
3. **Placeholder scan:** search the plan for the format reference's §9 list. Fix what you find.
4. **Type consistency:** do the types, signatures and property names in later tasks match what earlier
   tasks define? A function called `clearLayers()` in B3 but `clearFullLayers()` in B7 is a bug.
5. **Order check:** read the tasks in order and ask, at each one, "could I actually start this now?"
   Everything it needs must come from a task above it, and every `Depends on` must point backwards.
6. **Deliverable check:** every task has one, and each states a result rather than an activity.
7. **Stack check:** every task names exactly one of the eight — run it as a mechanical check on the
   files each task touches. A task whose files span two trees is two tasks, and the split is an
   ordering, not a redesign.
8. **Agent check:** every task names exactly one agent, it is an exact catalog name, and it matches the
   task's stack (a `be` task run by `fe-react` is a mis-cut).
9. **Budget check:** every task carries a `**Budget:**` with itemized drivers, and the task table in
   the prompts section agrees. Every estimate over ~150k names its natural split point or says why the
   task is one thing anyway; every one under ~80k was checked against the next same-stack task and
   either merged or left alone deliberately.
10. **Gate check:** exactly one task carries the gate, it is the last runnable one, its commands are
    the project's own and in run order, and every other task says `**Gate: none**` with what not to run.
    The ungated-boundary cost is stated in the plan.
11. **Filing check:** where a blocked task will outlive the last runnable one, the last runnable block
    says the plan stays in `docs/plans/` until it clears; the plan's own number was taken from the high-water mark across both
    folders.
12. **Prompt check:** one block per task, in task order, each carrying the deliverable verbatim, an
    exact reading list with **sections** rather than artifacts, its traps, its gate line and its
    close-out line; `## Close-out — every task` is present verbatim. Read each block as if it were the
    only thing you had: if you would need the task above it to start, the block is incomplete. Every
    `Blocked on <id>` placeholder is matched by that task's duty to write it.

Fix what you find inline. No need to re-review — fix and move on. A spec requirement with no task gets
a task.

## Execution Handoff

After saving the plan, hand off to execution.

**"Plan complete and saved to `docs/plans/<filename>.md` — ready to queue in Plan Queue."**

The plan file is the whole handoff. It is self-contained on purpose: Plan Queue runs it in its own
worktree, one prompt block per session, in order, and each session closes out per the plan's
`## Close-out — every task`.

## Remember

- Read `./references/plan-format.md` before writing; it is the document contract
- Ground the plan in `## 1.`'s gap table, then decide the work in the numbered sections, then cut tasks
- Tasks flat and ordered, ids prefixed by family — no slices, no phases, no grouping layer
- One deliverable, one stack, one agent, one budget with drivers, one `Depends on` line per task
- The plan gates once, in its last runnable task, and that task fixes what the gate finds
- One paste-ready prompt per task, rewritten in place by any task that changes what it assumes; a
  prompt that cannot be written yet is written by the task that unblocks it
- A landed task's prompt is deleted; the live prompt set is the progress indicator, and the task that
  deletes the last one rewrites `Status:` and moves the plan into `docs/plans/implemented/`
- `## Close-out — every task` sits above the prompts, verbatim, and every block ends by pointing at it
- `**Status:**` at the top is maintained, and names what is built but unverified
- Exact file paths, exact commands, real values — always
