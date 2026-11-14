---
name: verify
description: Use when about to claim work is done, fixed or passing, or before committing or a PR; run the checks first. Triggers "done", "tests pass". Not for holding the bar mid-work (quality-constraints).
---

# Verification Before Completion

## Overview

**Make no completion claim without fresh verification evidence.** A claim that work is done, fixed or passing is a statement of fact; without output from a command run in this message, it is a guess presented as a fact, and the user acts on it.

If you haven't run the verification command in this message, you cannot claim it passes.

`quality-constraints` is the during-work counterpart to this end-of-work evidence gate.

**Inside a plan task, the prompt block's `Gate:` line decides what you run:** a `Gate: own tests` task runs exactly the commands its block names — its own tests and the acceptance tests it must turn green — reports those results, and leaves them green; it runs no unfiltered suite. A task with nothing runnable, such as a docs-only task, says so on its `Gate: none` line and claims nothing passes.

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

## Target acceptance — a separate verdict for the deployed environment

A local pass proves the code on this machine. It says nothing about the build that was deployed, its
configuration, its data or its neighbours. Whenever work is meant to reach an environment (staging, preview,
production), the report carries **two** verdicts, never merged into one:

```
Local:             PASSED | FAILED                      — <command> → <result>
Target acceptance: VERIFIED | FAILED | NOT PERFORMED    — <environment>, <build/SHA>, <check> → <result>
Next permitted step: <one step>
```

| Target acceptance | Means | Next permitted step |
|---|---|---|
| **VERIFIED** | The acceptance checks ran **against the deployed environment, on the build this work produced**, in this message, and passed | Report done; promote to the next environment, or close the task |
| **FAILED** | They ran there and at least one failed | Report the failure with its evidence; reproduce and fix (`dev:debugging`); no promotion, no "done" |
| **NOT PERFORMED** | They did not run there — not deployed yet, no access, no smoke tests for it, or only run locally | Say so plainly; the next step is the deployment or the check itself, named exactly. Never claim the feature works on the target |

- **A local pass never counts as VERIFIED.** Nor does a green CI run of the unit suite, a successful deploy
  command, a health endpoint answering `200`, or a different build on the target.
- **Check the build identity** before reading the result: the SHA, image tag or version the environment reports
  must be the one this work produced. A pass on the previous build is NOT PERFORMED.
- **NOT PERFORMED is an honest verdict, not a failure.** Leaving it out, or writing "should work on staging", is the
  failure.

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
| Works on the target environment | Acceptance checks run there, on this build: `Target acceptance: VERIFIED` | Local pass, deploy succeeded, health check `200` |

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
