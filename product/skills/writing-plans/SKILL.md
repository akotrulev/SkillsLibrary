---
name: plan-feature
description: Use when an approved spec needs an implementation plan (ordered tasks, one paste-ready prompt each) before code. Triggers "write the implementation plan". Not for the design itself (feature).
---

# Writing Plans

Write the plan for an engineer who is skilled but has zero context for this codebase. Document what
they need: what exists today and what is missing, the decisions already made and what they cost,
which files each task touches, the real values the code will use, and the traps that specific task
will hit. A decision bound to a framework or version cites its official doc: see `source-grounding`.

## When to use

An approved spec, design or set of requirements that must become an ordered list of tasks, each with a paste-ready prompt, before any code.

## When NOT to use

- The design itself, with the *how* still open: `feature` (brainstorming) writes the spec this skill plans from.
- A whole initiative's task list from stories: `/product:plan-system` (`solution-planner`).

## The format is a contract

**The plan document format is a contract — read it before writing anything.** It is
[`./references/plan-format.md`](./references/plan-format.md): the header, the numbered sections, the
task block's fields, the gate rule, the `## Prompts — one per task` section and the close-out. This
skill is the procedure; that file is the shape. Do not improvise either. The standards a plan must
meet are the product rule file `plans.md` (the project's copy in `.claude/rules/product/`, or the plugin's in
`product/skills/rules/` before `/product:rules` has installed it); where the project's `CLAUDE.md`
states its own plan rules, those win, and where this skill and the rule file disagree, the rule file wins.

**Three properties of that format drive everything below:**

1. **One self-contained file.** The plan is queued whole — by the Plan Queue VS Code plugin, by a
   session, by a person. Everything a cold reader needs is in it, including the paste-ready prompt for
   each task. There is no companion file.
2. **The narrative comes first; the tasks come last.** A task block is only readable against the
   context above it, so `## 1. What already exists, and what is missing` and the sections that decide
   the work are written *before* any task is.
3. **Every task gates its own work and the work landed above it** (plan-format §5).

**The unit of work is a task.** A plan is one flat, ordered list of them, ids prefixed by the family of
work (`B1`, `B2`, `B3`, then `P1`) — never a "slice", never a "phase", never a "stage", and never
grouped into any of those. A task's *internal* actions are its **steps**; that is the only thing the
word "step" names. Use the word **task** in the plan, in the task reports, and when talking to the
user, so the same thing has the same name everywhere.

**Context:** Write the plan on whatever branch you are already on — do not create or check out a branch
or worktree to author it.

**Save plans to** `docs/plans/NNN-<feature-name>.md` under the **current project's** root, never this
skills-library checkout and never a global config directory unless the user asks for a global copy
(a user preference for plan location overrides this default). `NNN` takes the high-water mark across
`docs/plans/` and `docs/plans/implemented/` plus one (plan-format §1).

**Commands:** Every build, test, lint, format and migration command written into the plan is the
**project's own**, read from the repo (`package.json` scripts and `packageManager`, the `Makefile`, the
`.csproj`/`gradle` layout, the CI workflow) — never a guessed default.

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

A web route in the plan → read [`./references/web-routes.md`](./references/web-routes.md) and decide each route's rendering here.

**Done when** the gap table is written, each `Today` cell carries a `file:line` or `—`, and every choice
is a `D<n>`.

## Step 2 — Map the files

Before defining tasks, map out which files will be created or modified and what each is responsible
for. This is where decomposition decisions get locked in, and it is what the task cut and the budget
are both derived from.

- Design units with clear boundaries and well-defined interfaces. One clear responsibility per file.
- Files that change together live together. Split by responsibility, not by technical layer.
- **Note, per task, which files it writes and which build tree it sits in** (one .NET solution, one
  Gradle build, one pnpm package graph). Step 3 turns every overlap into a `Depends on` edge: two
  tasks that touch the same file or build the same tree cannot run beside each other.

**Done when** every file a task writes is listed once, with its build tree.

## Step 3 — Put the tasks in workable order

**Tasks are listed in the order they are done, and the list is flat.** No grouping layer sits above
them — the sequence itself carries the ordering, and the third task is "the third thing you do".

- **Everything a task needs already exists when its turn comes.** Whatever it imports, calls, migrates
  against, registers with, or configures was produced by an earlier task. A task that cannot be started
  at its position is in the wrong position — move it, don't annotate it.
- **Dependencies are stated, not implied.** Where a task needs an earlier one that is not immediately
  before it, say so: `**Depends on:** B1 (the ledger column)`. A dependency on a later task is a defect
  in the ordering, not an exception to note.
- **Overlap is a dependency too.** A task also depends on every earlier task whose files overlap its
  own or that builds the same tree, and names it in `**Depends on:**` with the overlap as the reason
  (`B1 (same solution)`). Position orders nothing once each prompt carries its `Depends on:` line
  (Step 6): a task that leaves out an overlapping predecessor runs beside it, in the same working tree.
  Tasks with disjoint files and different trees are the ones that run in parallel.
- **Test-first order, `TD` tasks and the two closing tasks** are in plan-format §4 (order, `TD`) and §5
  (the gate task, `DOC1`), and in `rules/plans.md`: the contract and stubs first, then the `Q`
  acceptance tests, then the implementation tasks.
- **Prerequisites a human must do come first**, as their own tasks with `Agent: human` and an
  `**Owner:**` line (an account to provision, an API key to request, a run only they can start), so
  nothing downstream stalls on them silently.
- **Fill the session, then stop.** Merge consecutive same-stack work into one task until it would
  exceed the budget target, then start the next. **The goal is the fewest sessions, not the smallest
  tasks** — an agent switch costs a whole context reload, so twenty tiny tasks cost more than
  eight full ones.

Where a stack-cut task cannot be demonstrated end to end on its own, its `Not in <id>` line says so
(plan-format §4). The plan states what a halfway stop leaves, in the words of plan-format §5.

**Done when** every task has its position and its `Depends on:`, and every `Depends on:` points backwards.

## Step 4 — One stack, one agent, one session per task

**Every task names exactly one stack, from the list in plan-format §4.**

> **A task that touches both the API tree and the web tree is two tasks.** There is no mixed task at
> any size, and no estimate justifies one.

**Split along a seam inside the same stack**, never by handing part of a task to another stack.

**Every task also names its agent** — an exact catalog name on the same line as the stack
(`be-dotnet`, `be-java`, `be-node`, `be-python`, `be-rust`, `fe-react`, `fe-blazor`, `data-architect`,
`devops-engineer`, `tooling-engineer`, `qa-api-<stack>`, …). One stack, one agent, one session: the
agent is who the session is opened as, and it is who each prompt block tells the session to be. A task
whose agent you cannot name is a task whose stack you have not actually decided; an invented agent name
is the most damaging defect in the document.

**Done when** every task names one stack from plan-format §4 and one exact catalog agent.

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

**Per task, once:** the output it reads back, **10k** for any code task (its commit and diff, plus its
own gate's output; ~8k more when it needs a production build and e2e), or **12k plus 2k per earlier
task** for the last task (the whole set, the coverage floor included, and the fix loop it triggers);
then **× 1.2** on the sum for conversation and tool churn.

`Budget = (floor + skills + sections + orientation + files + read-back) × 1.2`

**Aim for ~80k–150k, centred on ~130k.** Under ~80k, look at the next task in the same stack — merge
only if the result still states **one** deliverable. Over ~150k, name the task's natural split point,
inside its own stack.

Record it on the task **with its drivers itemized**, so a reader can tell a 95k of many small files
from a 95k of one large one:

```markdown
**Budget:** ~95k — CLAUDE.md 25k, plan §2 and §4 4k, `OrderService.cs` + its tests as the pattern ~12k,
3 skills 24k, 5 files created and 1 modified 11.5k, commit, diff and gate read-back 10k, churn ×1.2
```

Re-derive it whenever the task's files, skills or cited sections change.

> **The budget is a guide, never a gate.** Three rules outrank it, always: one deliverable; one stack
> and one agent; every task gates its own work and the work landed above it. A task that overshoots with
> all three satisfied is a large task correctly authored — it is labelled, not filed as a defect. Never
> split something coherent to hit a number, and never pad a task to fill one.

**Done when** every task carries a `**Budget:**` with itemized drivers, and the prompts table agrees.

## Step 6 — Write the task blocks and the prompts

Both shapes are in [`./references/plan-format.md`](./references/plan-format.md) §4 and §6, the gate
in §5, the close-out in §7, and the standards in `rules/plans.md`. Four things are easy to get wrong:

- **A program reads the prompt's first lines** (plan-format §6): `Depends on: <ids>` is the task
  block's `**Depends on:**` reduced to ids, overlap edges included, no prose. The last runnable task
  waits for every task that nothing else waits for, and the preamble's one line says what runs together.
- **Every task that writes code or tests carries `**Gate: own tests**`** with the commands named,
  filtered by file or class (plan-format §5); each task's bullets name the branches its tests must
  reach, as `OrderServiceTests` does in the format reference's deliverable table.
- **A prompt you cannot write yet is not guessed.** Where a block depends on what an earlier task
  lands, write `**Blocked on <id>**` as plan-format §6 gives it, and put "write B4's prompt block" in
  the blocking task's bullets **and** in its own prompt's closing duty.
- **`## Close-out — every task` is copied verbatim from plan-format §7**, directly above the prompts.
  The documentation task's block carries the filing duty; where a blocked task will still hold a
  block, that block says the plan stays in `docs/plans/` until it clears.

**Done when** every task has its block and its prompt, and the close-out section is in place.

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and test the plan against these
criteria. Fix what you find inline; a spec requirement with no task gets a task.

1. **Grounding.** Every row of `## 1.`'s gap table traces to a task, and every task traces back to a row.
2. **Spec coverage.** Each section of the spec points at the task that implements it.
3. **Placeholders.** The plan holds none of plan-format §9's list.
4. **Type consistency.** Types, signatures and property names in later tasks match what earlier tasks
   define: `clearLayers()` in B3 and `clearFullLayers()` in B7 is a bug.
5. **Order.** At each task, everything it needs comes from a task above it, and every `Depends on` points
   backwards. The contract, the schema and the stubs come before any `Q` task, and every acceptance
   test precedes the tasks that turn it green.
6. **Parallel order.** Every block opens with a `Depends on:` line of ids only, equal to its task
   block's; tasks whose `Files` overlap, or that build one tree, are ordered by an edge; the
   `Runs beside` column lists only pairs with disjoint files and different trees.
7. **Deliverable.** Every task has one, stated as a result rather than an activity.
8. **Stack.** Every task's files sit in one tree and the task names one stack from plan-format §4.
9. **Agent.** Every task names one exact catalog agent that matches its stack.
10. **Budget.** Every estimate over ~150k names its split point or says why the task is one thing; every
    one under ~80k was checked against the next same-stack task.
11. **Gate.** Every code task's gate and the last runnable task meet plan-format §5 and `rules/plans.md`.
12. **Documentation.** The plan ends with `DOC1`, or its header says `Documentation task: none — <why>`
    (plan-format §5).
13. **Filing.** The filing duty is on the documentation task, and the plan's number came from the
    high-water mark across both folders.
14. **Prompt.** One block per task, in task order, each carrying the deliverable verbatim, a reading
    list of **sections**, its traps, its gate line and its close-out line; each block is complete
    without the task above it, and every `Blocked on <id>` is matched by that task's duty to write it.
15. **Web routes.** Where the plan adds or changes a web route, the criterion in
    [`./references/web-routes.md`](./references/web-routes.md) holds.

## Execution Handoff

After saving the plan, hand off to execution.

**"Plan complete and saved to `docs/plans/<filename>.md` — ready to queue in Plan Queue."**

The plan file is the whole handoff. Plan Queue runs it in its own worktree, one prompt block per
session, in order, and each session closes out per the plan's `## Close-out — every task`.
