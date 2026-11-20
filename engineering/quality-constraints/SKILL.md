---
name: quality-constraints
description: Use when implementing, to stop the bar dropping to reach green (skipped tests, suppressions, lost coverage). Triggers "don't weaken the tests", "keep the bar". Not for completion evidence (verify).
---

# Quality Constraints

## Overview

`engineering:verify` proves a claim at the end. This skill applies **during the work**: the moments where lowering the bar is the cheapest way to get a gate green. The bar is already written down — in `CLAUDE.md` and in the plan's acceptance tests. This skill adds no new artifact; it lists what the agent must not do and the evidence that shows it didn't.

## When to use

- Any implementation task, from the first edit, whether or not a plan exists
- A gate is red and the next move is to change the test
- Before committing a task, as a pass over your own diff

## When NOT to use

- Claiming the work is done or passing — `engineering:verify` owns that
- Picking thresholds — the coverage floor is in `CLAUDE.md` (Test code rules)
- Reviewing someone else's code — use the review skills and the house findings table

## The constraints

Each row is a thing the agent must not do, and the evidence that proves it didn't. Run the evidence command before the commit, not after.

| Must not | Evidence it did not |
|---|---|
| Edit, skip, delete or weaken an acceptance test | `git diff --stat` over the acceptance-test folder is empty. A test believed wrong is recorded as a dated `D<n>` in the plan's open issues and the final message, and stays red |
| Add an `OR` assertion | Per `CLAUDE.md` "Test code rules" (one expected condition per assertion): `git diff` added lines hold no alternation inside an assertion |
| Swallow an error, or put `try`/`catch` in a test body | Per "Test code rules" (never swallow an error): `git diff` added lines hold no `catch` that ends without an assertion or a rethrow, and none inside a test body |
| Add a lint, analyzer, type or `#pragma` suppression without a reason | Every added suppression carries its justification in the directive's own field, and the diff of the tool's config shows no rule turned down |
| Exclude a file with behaviour from the coverage measure | Per "Test code rules" (coverage exclusions): the coverage config diff adds only files the stack's selection matrix does not test, each by name |
| Lower a threshold, timeout or budget to get green | `git diff` of config and test files shows no number moved in the permissive direction |
| Replace an implementation with a stub that returns success | Per `plans.md` (stubs answer `501 not-implemented`): every stub added answers `501`, and the plan says which task replaces it |
| Mark a task `DONE` with a red test it did not record | Every red test in the last run appears as a dated `D<n>` in the plan's open issues and in the final message |
| Write a test to move the coverage number | Per "Test code rules" (only an asserting test counts): each new test asserts an effect on the branch it covers; a test with no assertion is deleted |

## The evidence, at three moments

1. **Before the first edit** — find the acceptance-test folder and the coverage config. Note both paths so the later diffs have a target.
2. **When a gate goes red** — fix the code. If the test itself looks wrong, stop editing it. Done when the test is unedited and the reason is recorded as a dated `D<n>` in the plan's open issues and the final message. A red test never justifies a change to the test.
3. **Before the commit** — run the evidence column. If a row cannot be answered from the diff, treat it as failed and look again.

## Red flags

- "Just this once" next to a suppression, a skip or an exclusion
- A test edited in the same commit as the code it covers, with the expectation moved
- A threshold or timeout changed in a commit whose message is about something else
- A broad `catch` added to make a flaky run pass
- A summary that says "tests pass" without naming which were skipped
