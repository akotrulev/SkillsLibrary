---
name: ep-requesting-code-review
description: Use when you want a completed change reviewed before it cascades — after a major feature, before a merge/PR. Prefer the harness's native review command (e.g. `/code-review`); otherwise dispatch a reviewer subagent. Triggers: "review this before I merge", "second pair of eyes on this diff". Do NOT use to act on feedback (`ep-receiving-code-review`).
---

# Requesting Code Review

Get a completed change reviewed before issues cascade into more work. Two paths:

1. **Native review command.** If the harness provides a review command (e.g. `/code-review`, `/review`), use it — same "never fight the harness" stance as `ep-worktrees`; it integrates with the platform.
2. **Reviewer subagent.** The reviewer gets precisely-crafted context, never your session's history, which keeps it focused on the work product and preserves your own context.

**Core principle:** Review before it compounds.

## When to Request Review

**Worth reviewing:**
- After completing a major feature
- Before a merge to main / opening a PR
- After fixing a complex or subtle bug
- When stuck and a fresh perspective would help

**How to review it:** a native review command, a self-review against the controller rubric, or a reviewer subagent.

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
  PLAN_OR_REQUIREMENTS: Task 2 from docs/plans/014-deployment.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661

[Subagent returns findings in the CLAUDE.md severity table]
  | Severity | Location            | Issue                         | Suggested fix              |
  | major    | indexer.ts:130      | No progress reporting         | Emit "X of Y" every 100    |
  | minor    | indexer.ts:130      | Magic number 100              | Extract PROGRESS_INTERVAL  |

You: [Hand findings to ep-receiving-code-review; fix major, note minor, continue.]
```

## Integration with Workflows

**`ep-delegate-to-subagents`:** reach for this skill for the per-task review of an implementer's diff.

**`ep-executing-plans`:** at a natural checkpoint or before finishing, review the accumulated diff.

**`ep-finish-branch`:** before Option 1 (merge) or Option 2 (PR), a review pass is worthwhile.

**Receiving the feedback:** always route the reviewer's output through `ep-receiving-code-review` (verify before implementing, push back with reasoning, no performative agreement).

## Red Flags

**Never:**
- Skip review because "it's simple" on a genuinely major change
- Ignore **blocker** issues
- Proceed with unfixed **major** issues
- Argue with valid technical feedback (evaluate it via `ep-receiving-code-review`)

**If the reviewer is wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

See the reviewer prompt template at `./code-reviewer.md`.
