---
name: verify
description: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs — requires running verification commands and confirming output before any success claim; evidence before assertions. Triggers: before saying "done"/"fixed"/"tests pass", before committing/pushing/opening a PR. Do NOT skip it because a check "should" pass — that is exactly when it applies.
---

# Verification Before Completion

## Overview

**Make no completion claim without fresh verification evidence.** A claim that work is done, fixed or passing is a statement of fact; without output from a command run in this message, it is a guess presented as a fact, and the user acts on it.

If you haven't run the verification command in this message, you cannot claim it passes.

**Inside a plan task, the prompt block's `Gate:` line decides what you run:** a `Gate: none` task runs nothing and reports its work as "written, not run", never "passing"; a `Gate: own tests` task runs exactly the command its block names — its own tests and the acceptance tests it must turn green — reports those results, and runs nothing else.

## The Gate Function

```
Before claiming any status or expressing satisfaction:

1. Identify: what command proves this claim?
2. Run: execute the full command (fresh, complete)
3. Read: full output, check exit code, count failures
4. Verify: does output confirm the claim?
   - If no: state actual status with evidence
   - If yes: state claim with evidence
5. Only then: make the claim

A skipped step means the claim is unverified.
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | Tests passing |

Hedged wording ("should", "probably", "seems to"), satisfaction before a run ("Done!"), and a partial check standing in for the full one are the usual signs a claim has run ahead of its evidence. A linter pass does not prove compilation, and an agent's success report does not prove the diff.

## Key Patterns

**Tests:**
```
✅ [Run test command] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**Regression tests (red-green):**
```
✅ Write → Run (pass) → Revert fix → Run (must fail) → Restore → Run (pass)
❌ "I've written a regression test" (without red-green verification)
```

**Build:**
```
✅ [Run build] [See: exit 0] "Build passes"
❌ "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
✅ Re-read plan → Create checklist → Verify each → Report gaps or completion
❌ "Tests pass, step complete"
```

**Agent delegation:**
```
✅ Agent reports success → Check VCS diff → Verify changes → Report actual state
❌ Trust agent report
```

## Why This Matters

Common failure modes when completion is claimed without verification:
- The user says "I don't believe you" — trust broken
- Undefined functions shipped — would crash
- Missing requirements shipped — incomplete features
- Time wasted on false completion → redirect → rework

## When To Apply

Before any success or completion claim, however it is worded — an exact phrase, a paraphrase, or an implication that the work is correct — and before committing, opening a PR, marking a task complete, moving to the next task, or delegating to an agent.
