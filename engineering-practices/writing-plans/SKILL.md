---
name: ep-writing-plans
description: Use when you have an approved spec or clear requirements for a multi-step task and need a detailed, bite-sized implementation plan before touching code. Triggers: after `ep-brainstorming` produces an approved design, "write the implementation plan", "break this spec into tasks", "plan out this feature". Chains into `ep-executing-plans`. Do NOT use to design or explore the idea itself (use `ep-brainstorming`), to execute an already-written plan (use `ep-executing-plans`), or for a single trivial edit that needs no plan.
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the `ep-writing-plans` skill to create the implementation plan."

**Context:** If working in an isolated worktree, it should have been created via the `ep-using-git-worktrees` skill at execution time.

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`
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

> **For agentic workers:** REQUIRED SUB-SKILL: Use `ep-executing-plans` (inline, the default) to implement this plan task-by-task. Only if delegation clearly pays for itself and the user asks for it, use `ep-subagent-driven-development` (cost-aware, 2-agent gate). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

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
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it. This is a checklist you run yourself — not a subagent dispatch.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Fix them.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

**Escalation (permission-gated):** the self-review above is the default. For a large or high-stakes plan, and **with the user's OK**, you may dispatch a dedicated reviewer subagent using the template at `./plan-document-reviewer-prompt.md` (it checks completeness, spec alignment, task decomposition, buildability). This is one extra agent — it counts toward the conservative 2-agent gate in `ep-subagent-driven-development`, so ask before spawning it; don't dispatch it by reflex.

## Execution Handoff

After saving the plan, hand off to execution. **Default to inline execution — cost before speed.**

**"Plan complete and saved to `docs/plans/<filename>.md`. Ready to implement it task-by-task with checkpoints for review?"**

- **Default — Inline execution (recommended):** use `ep-executing-plans`. Batch execution with checkpoints for review. Cheaper and simpler; the right choice for almost every plan.
- **Opt-in — Subagent execution:** use `ep-subagent-driven-development` **only** when the user asks for it and delegation clearly pays for itself (self-contained, context-heavy tasks). It is governed by a hard 2-agent gate — spawning more than 2 agents requires the user's permission first.

Do not offer the subagent path as "faster/better" — it is the cost-aware exception, not the default.
