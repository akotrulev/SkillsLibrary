---
name: debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes — find root cause first, fix the cause not the symptom. Triggers: "this test is failing", "debug this", "why is X breaking", "the fix didn't work". Pairs with `dev:verify` (confirm the fix). Do NOT use for designing new work (`dev:design`) or known-cause changes needing no investigation.
---

# Systematic Debugging

## Overview

**Find the root cause before proposing a fix.** A fix aimed at a symptom masks the defect, and a guessed fix that happens to work leaves you unable to say why — so the next change breaks it again. Until Step 1 below is complete, do not propose a fix.

## When to Use

Use for any technical issue: test failures, production bugs, unexpected behavior, performance problems, build failures, integration issues.

It matters most when guessing is tempting: under time pressure, when one quick fix looks obvious, when earlier fixes did not work, or when you do not fully understand the issue. A simple-looking bug still has a root cause, and a systematic pass on it is short.

## The Four Steps

Complete each step before starting the next.

### Step 1: Root Cause Investigation

Before attempting any fix:

1. **Read Error Messages Carefully**
   - Don't skip past errors or warnings
   - They often contain the exact solution
   - Read stack traces completely
   - Note line numbers, file paths, error codes

2. **Reproduce Consistently**
   - Can you trigger it reliably?
   - What are the exact steps?
   - Does it happen every time?
   - If not reproducible → gather more data, don't guess

3. **Check Recent Changes**
   - What changed that could cause this?
   - Git diff, recent commits
   - New dependencies, config changes
   - Environmental differences

4. **Gather Evidence in Multi-Component Systems**

   When the system has multiple components (CI → build → signing, API → service → database), add diagnostic instrumentation before proposing fixes:
   ```
   For each component boundary:
     - Log what data enters component
     - Log what data exits component
     - Verify environment/config propagation
     - Check state at each layer

   Run once to gather evidence showing where it breaks
   Then analyze evidence to identify failing component
   Then investigate that specific component
   ```

   **Example (multi-layer system):**
   ```bash
   # Layer 1: Workflow
   echo "=== Secrets available in workflow: ==="
   echo "IDENTITY: ${IDENTITY:+SET}${IDENTITY:-UNSET}"

   # Layer 2: Build script
   echo "=== Env vars in build script: ==="
   env | grep IDENTITY || echo "IDENTITY not in environment"

   # Layer 3: Signing script
   echo "=== Keychain state: ==="
   security list-keychains
   security find-identity -v

   # Layer 4: Actual signing
   codesign --sign "$IDENTITY" --verbose=4 "$APP"
   ```

   **This reveals:** Which layer fails (secrets → workflow ✓, workflow → build ✗)

5. **Trace Data Flow**

   When the error is deep in the call stack, see `root-cause-tracing.md` in this directory for the complete backward tracing technique.

   **Quick version:**
   - Where does bad value originate?
   - What called this with bad value?
   - Keep tracing up until you find the source
   - Fix at source, not at symptom

### Step 2: Pattern Analysis

**Find the pattern before fixing:**

1. **Find Working Examples**
   - Locate similar working code in same codebase
   - What works that's similar to what's broken?

2. **Compare Against References**
   - If implementing a pattern, read the reference implementation completely, not a skim — a partly understood pattern produces the bug you are chasing
   - Understand the pattern fully before applying

3. **Identify Differences**
   - What's different between working and broken?
   - List every difference, however small
   - Don't assume "that can't matter"

4. **Understand Dependencies**
   - What other components does this need?
   - What settings, config, environment?
   - What assumptions does it make?

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
   - Don't pretend to know
   - Ask for help
   - Research more

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
   - No "while I'm here" improvements
   - No bundled refactoring

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

| Step | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence | Understand what and why |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
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
- **`dev:verify`** - Verify fix worked before claiming success
