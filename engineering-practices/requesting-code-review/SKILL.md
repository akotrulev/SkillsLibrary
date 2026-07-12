---
name: ep-requesting-code-review
description: Use when you want a completed change reviewed before it cascades — after a major feature, before a merge/PR, or when a subagent-driven task warrants deeper independent verification than the controller's inline review. Prefer the harness's native review command (e.g. `/code-review`) when one exists; otherwise this skill dispatches a reviewer subagent with precisely-crafted context. Triggers: "review this before I merge", "get a second pair of eyes on this diff", "code-review this feature". Governed by the conservative 2-agent gate — a reviewer subagent is a permission-gated escalation, not a reflex. Do NOT use as a mandatory per-task step in `ep-subagent-driven-development` (its default is the controller's inline review), to receive/act on review feedback (use `ep-receiving-code-review`), or when a native review command is available and sufficient.
---

# Requesting Code Review

Get a completed change reviewed before issues cascade into more work. Two paths, in preference order:

1. **Native review command (preferred).** If the harness provides a review command (e.g. `/code-review`, `/review`), use it — same "never fight the harness" stance as `ep-using-git-worktrees`. It's cheaper than a subagent and integrates with the platform.
2. **Reviewer subagent (permission-gated fallback).** When no native command fits — or you need independent verification with curated context — dispatch a reviewer subagent. The reviewer gets precisely-crafted context, never your session's history, which keeps it focused on the work product and preserves your own context.

**Core principle:** Review before it compounds — but weigh the cost. A reviewer subagent is an extra invocation.

## Cost gate (read before dispatching a subagent)

This skill is governed by the library's conservative agent-spawning policy (see `ep-dispatching-parallel-agents` / `ep-subagent-driven-development`):

- **In `ep-subagent-driven-development`, inline controller review is the default** — the controller reviews the implementer's diff itself (spec compliance THEN code quality, per that skill's rubric). A *separate* reviewer subagent is an **escalation that needs the user's permission** because implementer + reviewer trips the hard **2-agent gate**.
- **For ad-hoc work** (no subagents in flight), a single reviewer subagent is one agent — fine to offer, but still weigh it against just reviewing inline yourself. When inline review would do, do it inline.
- **Never** treat review-by-subagent as "mandatory after each task". It is not.

## When to Request Review

**Worth reviewing:**
- After completing a major feature
- Before a merge to main / opening a PR
- After fixing a complex or subtle bug
- When stuck and a fresh perspective would help

**How to review it** (in preference order): native review command → inline self-review (controller rubric) → reviewer subagent (permission-gated when it pushes you past the 2-agent gate).

## How to Request (reviewer-subagent path)

**1. Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2. Dispatch the reviewer subagent** using the template at `./code-reviewer.md`.

**Placeholders:**
- `{DESCRIPTION}` — brief summary of what you built
- `{PLAN_OR_REQUIREMENTS}` — what it should do (plan file path, task text, or requirements)
- `{BASE_SHA}` — starting commit
- `{HEAD_SHA}` — ending commit

**3. Act on feedback** (hand off to `ep-receiving-code-review`):
- Fix **blocker** issues immediately
- Fix **major** issues before proceeding
- Note **minor** / **nit** issues for later
- Push back with technical reasoning if the reviewer is wrong

## Example

```
[Just completed a major feature: verifyIndex() + repairIndex()]

You: This is a good point to review before merging.
[Prefer native: if /code-review exists, run it here instead of a subagent.]

BASE_SHA=$(git rev-parse origin/main)
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch reviewer subagent via ./code-reviewer.md]
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types
  PLAN_OR_REQUIREMENTS: Task 2 from docs/plans/2026-07-12-deployment.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661

[Subagent returns findings in the CLAUDE.md severity table]
  | Severity | Location            | Issue                         | Suggested fix              |
  | major    | indexer.ts:130      | No progress reporting         | Emit "X of Y" every 100    |
  | minor    | indexer.ts:130      | Magic number 100              | Extract PROGRESS_INTERVAL  |

You: [Hand findings to ep-receiving-code-review; fix major, note minor, continue.]
```

## Integration with Workflows

**`ep-subagent-driven-development`:** the controller reviews **inline** by default. Reach for this skill only as the permission-gated escalation to a dedicated reviewer subagent (implementer + reviewer = past the 2-agent gate → ask first).

**`ep-executing-plans`:** at a natural checkpoint or before finishing, review the accumulated diff — native command first, inline second, subagent only if it earns its cost.

**`ep-finishing-a-development-branch`:** before Option 1 (merge) or Option 2 (PR), a review pass is worthwhile — again, native command → inline → subagent.

**Receiving the feedback:** always route the reviewer's output through `ep-receiving-code-review` (verify before implementing, push back with reasoning, no performative agreement).

## Red Flags

**Never:**
- Skip review because "it's simple" on a genuinely major change
- Ignore **blocker** issues
- Proceed with unfixed **major** issues
- Argue with valid technical feedback (evaluate it via `ep-receiving-code-review`)
- Spawn a reviewer subagent that pushes you past the 2-agent gate **without asking the user first**
- Reach for a subagent when a native review command or your own inline review would do

**If the reviewer is wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

See the reviewer prompt template at `./code-reviewer.md`.
