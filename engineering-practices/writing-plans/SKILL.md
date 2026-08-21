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

| # | Task | Deliverable | Depends on |
|---|---|---|---|
| 1 | T1 — [name] | [the observable result] | none |
| 2 | T2 — [name] | [the observable result] | T1 |

---
```

The task table is the plan's index: it is how a reader sees the order and what each task produces without opening the task blocks, and it must stay in step with them — same ids, same order, same deliverables.

## Task Structure

````markdown
### T<N> — [Component Name]

**Deliverable:** [the one observable thing that exists when this task is done]
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

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to T<N>" (repeat the code — the engineer may be reading tasks out of order)
- A `**Deliverable:**` that names an activity ("implement the service") instead of a result
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Tasks, numbered `T1…Tn`, in the order they are done — no slices, no phases, no grouping layer
- One stated deliverable per task, plus its `Depends on`
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

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

For a large or high-stakes plan, a dedicated reviewer pass is available — the template at `./plan-document-reviewer-prompt.md` checks completeness, spec alignment, task decomposition, and buildability.

## Execution Handoff

After saving the plan, hand off to execution.

**"Plan complete and saved to `docs/plans/<filename>.md`. Ready to implement it task-by-task with checkpoints for review?"**

- **Inline execution:** use `ep-executing-plans`. Batch execution with checkpoints for review.
- **Subagent execution:** use `ep-delegate-to-subagents`. Self-contained tasks dispatched to implementer agents, each result reviewed before moving on.
