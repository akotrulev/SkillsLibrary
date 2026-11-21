---
name: untested-code
description: Use when changing or refactoring code that has no tests (pin today's behaviour first). Triggers "refactor this legacy class", "this has no tests". Not for red gates (quality-constraints).
---

# Changing Untested Code

Code with no tests cannot be changed safely, because nothing says what "unchanged" means. This skill pins today's behaviour first, then changes the code under that pin. Six steps, each with a "done when" that is checked before the next starts.

## When to use

- A change or refactor lands in a class, module or function that has no tests
- "Refactor this legacy class", "this has no tests", "add a feature to this old code"
- A change point whose existing tests cover almost none of its branches

## When NOT to use

- Code that already has tests over the change point → write the next test first, as the stack's `unit-testing` skill says
- A red gate, or a test you are tempted to loosen → `engineering:quality-constraints`
- Finding why something fails → `engineering:debugging`
- New code with no legacy behind it → the stack agent's own test-first flow

## Procedure

1. **Name the change point and what must stay the same.** The change point is the method or type the change edits. Write down the behaviour around it that must not move: inputs, outputs, side effects, messages sent. *Done when both are written down in the report, not only in your head.*

2. **Find the test point.** It is the narrowest public entry that reaches the change point, per `CLAUDE.md` "Test code rules": the test goes in through the unit's public entry and asserts what comes out. Never widen visibility, reach into private state or use reflection to get closer. *Done when the entry is named and a call through it reaches the change point.*

3. **Get it under test.** Where a dependency blocks the call (a constructor that opens a connection, a static clock, a type the project does not own), make the smallest mechanical edit that opens a seam:
   - pass the dependency in through the constructor
   - put a port over code the project does not own

   These edits change no behaviour, and they are the only edits made before tests exist. The stack's `unit-testing` skill says which double fits each seam. *Done when the test point can be called from a test and the diff so far holds seam edits only.*

4. **Write characterization tests.** Each test calls the entry with a chosen input and asserts what the code returns today, wrong behaviour included. Run the test, read what it returns, then pin that. *Done when the branches of the methods about to change are covered to the floor in `CLAUDE.md` "Test code rules", measured and written in the report.*

5. **Record what looks wrong, and do not fix it.** A behaviour that looks like a defect is pinned as it is and listed as a finding with its `file:line`. The fix is a separate change, after this one. *Done when every behaviour you called wrong has two things: a characterization test whose name says it pins current behaviour, and a row in the report's findings; and the production diff since step 4 holds no edit that fixes one of them.*

6. **Make the change test-first.** Write the new expectation as a failing test, or edit the one characterization test the change must alter, then change the code until it passes. A characterization test the change alters is named in the report with its old and new expectation; any other characterization test that turns red means the change moved behaviour it should not have. *Done when the suite is green and each altered test is listed with old and new expectation.*

## Evidence at the end

The report carries two items:

- the coverage of the changed methods **before** the change, from step 4
- the list of characterization tests the change altered, each with old and new expectation, or `none`

## Pointers

- The stack's `unit-testing` skill owns doubles, seams and how to measure coverage.
- `engineering:quality-constraints` owns the rule against weakening a test to reach green.
- `engineering:verify` owns the completion claim; run it before saying the work is done.
