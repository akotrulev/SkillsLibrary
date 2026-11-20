---
name: debugging
description: Use when hitting any bug, test failure or unexpected behavior, before proposing fixes; find the root cause. Triggers "this test is failing", "why is X breaking". Not for new work (feature).
---

# Systematic Debugging

## Overview

**Find the root cause before proposing a fix.** A fix aimed at a symptom masks the defect, and a guessed fix that happens to work leaves you unable to say why — so the next change breaks it again. Until Step 1 below is complete, do not propose a fix.

## When to use

Use for any technical issue: test failures, production bugs, unexpected behavior, performance problems, build failures, integration issues.

It matters most when guessing is tempting: under time pressure, when one quick fix looks obvious, when earlier fixes did not work, or when you do not fully understand the issue. A simple-looking bug still has a root cause, and a systematic pass on it is short.

## When NOT to use

New work with no defect to explain: `feature` (brainstorming) designs it. Confirming a fix is finished is `verify`.

## The Four Steps

Complete each step before starting the next.

### Step 1: Root Cause Investigation

Before attempting any fix:

1. **Read Error Messages Carefully**
   - Read every warning and every line of the trace
   - Note line numbers, file paths, error codes

2. **Reproduce Consistently**
   - Can you trigger it reliably?
   - What are the exact steps?
   - Does it happen every time?
   - If not reproducible → gather more data

3. **Check Recent Changes**
   - What changed that could cause this?
   - Git diff, recent commits
   - New dependencies, config changes
   - Environmental differences

4. **Gather Evidence in Multi-Component Systems**

   The bug crosses component boundaries (CI → build → signing, API → service → database) → read `references/multi-component.md` and add the diagnostic instrumentation before proposing a fix.

5. **Trace Data Flow**

   When the error is deep in the call stack, see `root-cause-tracing.md` in this directory for the complete backward tracing technique.

   **Quick version:**
   - Where does bad value originate?
   - What called this with bad value?
   - Keep tracing up until you find the source
   - Fix at source, not at symptom

Done when the bug is reproduced and the failing component is named with its evidence line.

### Step 2: Pattern Analysis

**Find the pattern before fixing:**

1. **Find Working Examples**
   - Locate similar working code in same codebase
   - What works that's similar to what's broken?

2. **Compare Against References**
   - If implementing a pattern, read the reference implementation completely, not a skim — a partly understood pattern produces the bug you are chasing

3. **Identify Differences**
   - What's different between working and broken?
   - List every difference, however small
   - Treat each difference as a candidate cause

4. **Understand Dependencies**
   - What other components does this need?
   - What settings, config, environment?
   - What assumptions does it make?

Done when every difference between working and broken is listed.

### Step 3: Hypothesis and Testing

**Scientific method:**

1. **Form Single Hypothesis**
   - State clearly: "I think X is the root cause because Y"
   - Write it down
   - Be specific, not vague

2. **Test Minimally**
   - Make the smallest possible change to test the hypothesis
   - One variable at a time, so the result says which change mattered

3. **Verify Before Continuing**
   - Did it work? Yes → Step 4
   - Didn't work? Form a new hypothesis rather than adding more fixes on top

4. **When You Don't Know**
   - Say "I don't understand X"
   - Separate what you know from what you assume
   - Ask for help
   - Research more

Done when one hypothesis is confirmed or refuted by a single-variable change.

### Step 4: Implementation

**Fix the root cause, not the symptom:**

1. **Create Failing Test Case**
   - Simplest possible reproduction
   - Automated test if possible
   - One-off test script if no framework
   - Have it before fixing: it is what proves the fix, and a fix without it tends not to stick

2. **Implement Single Fix**
   - Address the root cause identified
   - One change at a time
   - Keep the change to the root cause; refactoring and "while I'm here" improvements go in a separate change

3. **Verify Fix**
   - Test passes now?
   - No other tests broken?
   - Issue actually resolved?

4. **If Fix Doesn't Work**
   - Count how many fixes you have tried
   - Fewer than 3: return to Step 1 and re-analyze with the new information
   - 3 or more: stop fixing and question the architecture (step 5) before a fourth attempt

5. **If 3+ Fixes Failed: Question Architecture**

   **Pattern indicating architectural problem:**
   - Each fix reveals new shared state/coupling/problem in different place
   - Fixes require "massive refactoring" to implement
   - Each fix creates new symptoms elsewhere

   **Question fundamentals:**
   - Is this pattern fundamentally sound?
   - Are we "sticking with it through sheer inertia"?
   - Should we refactor architecture vs. continue fixing symptoms?

   **Discuss with the user before attempting more fixes.** This is a wrong architecture, not a failed hypothesis.

## Signs You Have Left the Process

Return to Step 1 when you notice any of these: a fix proposed before the data flow is traced; several changes made in one go; "try X and see"; skipping the failing test; adapting a pattern you have not read in full; a third fix attempt after two failures; or the user asking "is that not happening?", "stop guessing" or "are we stuck?" — each means an assumption went unverified.

## Quick Reference

| Step | Key Activities | Done when |
|-------|---------------|-----------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence | Bug reproduced, failing component named with its evidence line |
| **2. Pattern** | Find working examples, compare | Every difference between working and broken listed |
| **3. Hypothesis** | Form theory, test minimally | One hypothesis confirmed or refuted by a single-variable change |
| **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass |

## When Process Reveals "No Root Cause"

If systematic investigation reveals issue is truly environmental, timing-dependent, or external:

1. You've completed the process
2. Document what you investigated
3. Implement appropriate handling (retry, timeout, error message)
4. Add monitoring/logging for future investigation

Treat "no root cause" as a conclusion to justify, not a default: most such cases turn out to be an incomplete investigation.

## Supporting Techniques

These techniques are part of systematic debugging and available in this directory:

- **`root-cause-tracing.md`** - Trace bugs backward through call stack to find original trigger
- **`defense-in-depth.md`** - Add validation at multiple layers after finding root cause
- **`condition-based-waiting.md`** - Replace arbitrary timeouts with condition polling

> **Stack note:** `condition-based-waiting-example.ts` (TypeScript) and `find-polluter.sh`
> (a shell/glob loop) are illustrations of the *technique*, not required tooling. Port
> the idea to your stack — the .NET, Java, or Node equivalent — rather than the literal
> code.

**Related skills:**
- **`engineering:verify`** - Verify fix worked before claiming success
