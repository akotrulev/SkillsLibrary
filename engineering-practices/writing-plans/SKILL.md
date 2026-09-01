---
name: ep-writing-plans
description: Use when you have an approved spec or clear requirements and need a detailed, bite-sized implementation plan before touching code — an ordered list of tasks, each with one deliverable. Triggers: after `ep-brainstorming` produces an approved design, "write the implementation plan", "break this spec into tasks". Chains into `ep-executing-plans`. Do NOT use to design the idea itself (`ep-brainstorming`), to execute a written plan (`ep-executing-plans`), or for a single trivial edit.
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**The unit of work is a task.** A plan is an ordered list of numbered tasks — `T1`, `T2`, `T3` — each with one stated deliverable. It is never a "slice", never a "phase", never a "stage", and tasks are never grouped into any of those. (A task's *internal* actions are its **steps** — that is the only thing the word "step" names here.) Use the word **task** in the plan document, in the checkpoint reports, and when talking to the user, so the same thing has the same name everywhere it is referred to.

**Announce at start:** "I'm using the `ep-writing-plans` skill to create the implementation plan."

**Context:** Write the plan on whatever branch you are already on — do not create or check out a branch or worktree to author it. Workspace isolation, if any, is `ep-executing-plans`' call at execution time.

**Save plans to:** `docs/plans/NNN-<feature-name>.md`
- `NNN` is a zero-padded sequential number, scoped to `docs/plans/`: list the folder, take the highest existing `NNN` prefix, use `highest + 1` (start at `001` if the folder is empty or doesn't exist yet). Never reuse or renumber an existing file's number.
- Resolve this path under the current project's root — the repo the session is actually working in — never this skills-library checkout or a global config directory, unless the user explicitly asks for a global copy.
- (User preferences for plan location override this default)

**Test commands:** Where a step runs tests, lint, or build, use the command for the project's stack (see the Stack defaults in CLAUDE.md — `dotnet test`, `./gradlew test`, `npm test`, etc.). The pytest/npm snippets below are generic illustrations of plan *shape*, not the required runner.

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Workable Order

**Tasks are listed in the order they are meant to be done, and the list is flat.** No grouping layer sits above them — the sequence itself carries the ordering, and `T7` means "the seventh thing you do", not "the seventh item in some bucket".

Order the tasks so that:

- **Everything a task needs already exists when its turn comes.** Whatever it imports, calls, migrates against, or configures was produced by an earlier task. A task that cannot be started at its position is in the wrong position.
- **The tree is working at every task boundary.** Each task ends with the project building and its tests green — so the plan can be stopped after any task and what exists still runs. A task that leaves the build red until the next one finishes is not a task boundary; merge the two.
- **Dependencies are stated, not implied.** Where a task needs an earlier one that is not immediately before it, say so on the task: `**Depends on:** T3`. Adjacency is not a dependency claim, and a dependency on a later task is a defect in the ordering — fix the order, don't note the exception.
- **User-facing capability comes together in consecutive tasks.** Where the plan delivers something a person does — place an order, reset a password — the tasks that make it work run back to back, and the last of them is the one that makes it usable end to end. Don't finish one layer across every capability before starting the next; finish one capability, then start the next.
- **Prerequisites a human must do come first**, as their own numbered tasks (an account to provision, an API key to request), so nothing downstream stalls on them silently.

**One exception to the capability rule: a plan one operator will execute in back-to-back batches.** Where the whole plan is run by one person in sequential batches, and nobody needs a capability demonstrable before the last of them, order the tasks by **who executes them and what files they touch** instead — everything both sides bind to first (schema, shared types, the API contracts, the app shell), then one task per backend module, then one per frontend screen area, then the verification pass. It buys one agent switch and one context reload per batch instead of one per capability. Two tasks merge into one batch only when they share an executor and a file tree, nothing gates between them, and their dependencies are already satisfied — and the merged task still states **one** deliverable, with its acceptance criteria as the per-piece breakdown. The costs are stated in the plan, not discovered: no capability works until both of its batches land, and a contract-first stub returns an explicit not-implemented response — never a fake success — naming the task that fills it. Everything else is unchanged: the tree still builds at every task boundary, and unit tests still ship inside the task that writes the code.

## Deliverables

**Every task states one deliverable — the observable thing that exists once it is done, that did not exist before.** It goes on the task as a `**Deliverable:**` line, and it is what the plan is checked against.

A deliverable is concrete and checkable by someone who did not do the work:

| Not a deliverable | A deliverable |
|---|---|
| "Work on the orders API" | "`POST /orders` accepts a valid order and returns `201` with the created id" |
| "Refactoring done" | "`OrderService` no longer reads `HttpContext`; the request id arrives as a parameter" |
| "Tests added" | "`OrderServiceTests` covers all four validation branches; `dotnet test` green" |
| "Migration work" | "`AddOrders` migration applied; `orders` and `order_lines` tables exist with their FKs" |

State it as a fact about the world after the task, not as an activity. If you cannot write the deliverable, the task is not yet one task — it is either too vague to start or two tasks wearing one number.

## One Stack Per Task

**Every task names exactly one stack, and it is one of eight:** `be` (backend, database, migrations) · `fe` (the web client) · `ts` (shared TypeScript packages — CLI, MCP, generated clients) · `data` · `infra` · `qa` · `docs` · `human`.

> **A task that touches both the API tree and the web tree is two tasks.** There is no mixed task at any size, and no estimate justifies one.

This is what makes a task handable to a single agent without it wandering across a boundary it does not own, and it is what makes the ordering mechanical rather than a judgement call — same-stack work is already adjacent.

**Every task also names its agent** — an `**Agent:**` line beside `Stack`, naming the plugin agent or skill that executes it (`be-dotnet`, `be-java`, `be-node`, `fe-react`, `fe-blazor`, `data-architect`, `devops-engineer`, `tooling-engineer`, `qa-api-<stack>` …; `human` tasks name the person or role). One stack, one agent, one session: the agent is who the session is opened as, and it is what `ep-executing-plans` adopts and `ep-delegate-to-subagents` dispatches to. A task whose agent you cannot name is a task whose stack you have not actually decided. Where a stack-cut task cannot be demonstrated end to end on its own (a backend task whose screen arrives two tasks later), say so in its `Out of scope` rather than pretending the capability landed, and have the contract-first side return an explicit not-implemented response — never a fake success or an empty list.

## Sizing a Task to One Session

**One task is executed in one session, so its context cost is a property of the task.** Estimate it while you are authoring the task — not afterwards, which turns the number into trivia rather than an input to how the task is written.

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
| The task block itself | 1k |
| Each design/spec **section** the task cites | 2k |
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

**Per task, once:** build + test run and the fix loop it triggers, **12k**; then **× 1.2** on the whole sum for conversation and tool churn.

`Est. = (floor + skills + sections + orientation + files + verify) × 1.2`

**Worked example** — a task creating an Orders resource: 25k floor + 24k (3 skills) + 1k task block + 6k (3 sections) + 10k (4 source files + 1 test) + 1.5k (1 modified) + 12k verify = 79.5k × 1.2 = **~95k**.

**Aim for ~80k–150k, centred on ~130k.** Under ~80k, look at the next task in the same stack — merge only if the result still states **one** deliverable. Over ~150k, annotate the task with its estimate and name its natural split point.

> **The estimate is a guide, never a gate.** Three rules outrank it, always: one deliverable; one stack and one agent; a green tree at every task boundary. A task that overshoots with all three satisfied is a large task correctly authored — it is labelled, not filed as a defect. Never split something coherent to hit a number, and never pad a task to fill one.

Record it on the task with its drivers, so a reader can tell a 95k of many small files from a 95k of one large one:

```markdown
**Est. context:** ~95k — 5 files created, 1 modified, 3 skills, 3 pack sections
```

Re-derive it whenever the task's files, skills or cited sections change. A stale estimate is worse than none — it is a number someone will trust.

For a plan produced by `solution-planner`, this is `be-shared-session-budget`'s job and it also writes `NEXT-PROMPTS.md`; here the same cost model applies to a plan that never went through that pipeline, and the prompts live inside the plan itself (see **Prompts — one per task** below).

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

**Date:** [YYYY-MM-DD] · **Written by:** `ep-writing-plans`

> **For agentic workers:** REQUIRED SUB-SKILL: Use `ep-executing-plans` to implement this plan task-by-task, or `ep-delegate-to-subagents` to run its tasks through subagents. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**Tasks** — in the order they are done:

| # | Task | Stack | Agent | Deliverable | Est. | Depends on |
|---|---|---|---|---|---|---|
| 1 | T1 — [name] | `be` | `be-dotnet` | [the observable result] | ~95k | none |
| 2 | T2 — [name] | `fe` | `fe-react` | [the observable result] | ~120k | T1 |

---
```

The task table is the plan's index: it is how a reader sees the order and what each task produces without opening the task blocks, and it must stay in step with them — same ids, same order, same deliverables.

## Task Structure

````markdown
### T<N> — [Component Name]

**Deliverable:** [the one observable thing that exists when this task is done]
**Stack:** `be` | `fe` | `ts` | `data` | `infra` | `qa` | `docs` | `human` — exactly one
**Agent:** `<plugin agent or skill that executes this task>` — exactly one
**Est. context:** ~<n>k — [the drivers: files created/modified, skills, sections cited]
**Depends on:** T<n> ([what it provides]) — or `none`

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Prompts — one per task

**One task is one session, so the plan ends with a `## Prompts — one per task` section: one paste-ready block per task, in task order.** The block is the whole of what the next session is told, so it is complete on its own:

````markdown
### Prompt — T<N> — [Component Name]

```
You are `<agent>`. Read, in this order: `docs/plans/<NNN>-<feature>.md` §T<N> · `CLAUDE.md` · [the files this task must read as patterns, exact paths] · [the spec sections it cites].

Deliver: [the task's Deliverable, verbatim].

Traps this task will hit: [the 2–4 things specific to this task — the convention that is easy to miss, the file that looks like the pattern but is not, the migration that must run before the test, the version-lane API that does not exist here].

When done: run [the exact build/test gate command], commit `[what to commit]` as `[commit message]`, write the record back into §T<N> of the plan, and rewrite the prompt blocks below yours if what landed differs from what they assume.
```
````

- **Built from the task's own block, copied rather than paraphrased** — the deliverable, the files and the gate are the task's; the prompt adds only the reading order and the traps.
- **Living text.** A task that lands something different from what the plan predicted rewrites the prompt blocks *below* it before it stops — in place, with no changelog appended. A prompt block that still names a file the previous task renamed is the most expensive kind of stale.
- **No block says "see task".** A session opened from the block must be able to start without scrolling up.

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to T<N>" (repeat the code — the engineer may be reading tasks out of order)
- A `**Deliverable:**` that names an activity ("implement the service") instead of a result
- A task with no `**Agent:**` line, or one naming two agents
- A prompt block that says "see T<N>" or "as above" instead of carrying its own reading list, traps and gate
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Tasks, numbered `T1…Tn`, in the order they are done — no slices, no phases, no grouping layer
- One stated deliverable per task, plus its `Stack`, its `Agent`, its `Est. context` and its `Depends on`
- One stack per task — a task spanning the API tree and the web tree is two tasks, at any size
- One paste-ready prompt block per task under `## Prompts — one per task`, rewritten in place by the task that changes what it assumes
- The estimate is a target, never a gate: one deliverable, one stack, a green tree at the boundary all outrank it
- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Fix them.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in T3 but `clearFullLayers()` in T7 is a bug.

**4. Order check:** Read the tasks in order and ask, at each one, "could I actually start this now?" Anything it needs must have been produced by a task above it, and every `Depends on` must point backwards. A forward-pointing dependency means the order is wrong, not that the dependency needs a note.

**5. Deliverable check:** Every task has a `**Deliverable:**` line, and each one states a result rather than an activity.

**6. Stack check:** Every task names exactly one `Stack` from the eight. Run it as a mechanical check on the `Files` lists — a task whose files span two trees is two tasks, and the split is an ordering, not a redesign.

**7. Sizing check:** Every task carries an `Est. context` with its drivers, and the header table's `Est.` column agrees with it. Every estimate over ~150k either names its natural split point or says why the task is one thing anyway; every one under ~80k was checked against the next same-stack task and either merged or left alone deliberately.

**8. Agent check:** Every task names exactly one `Agent`, it matches the task's `Stack` (a `be` task run by `fe-react` is a mis-cut), and the header table agrees.

**9. Prompt check:** There is one prompt block per task, in task order, each carrying the deliverable verbatim, an exact reading list, its traps, and the gate command. Read each block as if it were the only thing you had: if you would need the task above it to start, the block is incomplete.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

For a large or high-stakes plan, a dedicated reviewer pass is available — the template at `./plan-document-reviewer-prompt.md` checks completeness, spec alignment, task decomposition, and buildability.

## Execution Handoff

After saving the plan, hand off to execution.

**"Plan complete and saved to `docs/plans/<filename>.md`. Ready to implement it task-by-task with checkpoints for review?"**

- **Inline execution:** use `ep-executing-plans`. Batch execution with checkpoints for review.
- **Subagent execution:** use `ep-delegate-to-subagents`. Self-contained tasks dispatched to implementer agents, each result reviewed before moving on.
