---
name: qa-test-case-writer
description: Use when the user asks to write, derive, or generate formal test cases from requirements, user stories, acceptance criteria, or feature specs. Triggers: "write test cases for X", "derive test scenarios from these ACs", "create a test plan for feature Y".
---

# QA Test Case Writer

Generates formal, implementation-agnostic test cases from requirements. Output is structured Markdown suitable for use as manual test scripts, as input to test management tools, or as guides for later automation.

This skill **assembles and formats** the suite: it factors shared preconditions into a single **Setup**, writes lean per-case steps, and always closes with a **Cleanup** so the environment is left as it was found. The *derivation* of which cases to write — partitions, boundaries, decision-table rules, state transitions — is the job of `qa/manual/test-design-techniques`; load that to decide the cases, then format them here. The full doc→suite flow is orchestrated by the `qa/manual/agents/qa-test-case-designer` agent.

## When to use

- The user provides a requirement, user story, or acceptance criteria and wants test cases derived
- The user wants positive, negative, and edge cases enumerated for a feature
- The user wants a test plan or coverage matrix for a feature
- An exploratory session report (from `qa/manual/exploratory-charter-writer`) lists **test-case candidates** to formalize — each candidate becomes a case traced to the session/finding instead of an AC, tagged `#observed`

## When NOT to use

- The user wants an exploratory session charter → `qa/manual/exploratory-charter-writer`
- The user wants automation code (Playwright, Appium, RestSharp) → `qa/<stack>/skills/ui-test-author` or `qa/<stack>/skills/api-test-author`
- The user wants to report a defect they found → `qa/manual/bug-report-writer`

## Inputs needed

Confirm before generating. Ask only what's missing:

1. **Requirement or story** — full text, including acceptance criteria if available (or an exploratory session report whose test-case candidates are the source)
2. **Test type** — functional, API, UI, integration, regression (default: functional)
3. **Coverage depth** — happy path only, or include negative + boundary + edge (default: full)
4. **Output format** — Markdown table (default), Gherkin, or test management tool format

## Procedure

1. Parse the requirement and identify:
   - Actors (who performs the action)
   - Preconditions (state required before the test) — **note which are shared across cases**; those become the Setup
   - Triggers (the action under test)
   - Expected outcomes (and postconditions — these drive the Cleanup)
   - Data variations
2. Apply test design techniques to derive the cases. Load `qa/manual/test-design-techniques` and walk the default recipe: **equivalence partitioning → boundary value analysis → decision table (rule combos) → state transition (workflows) → use-case (end-to-end flows) → error-guessing sweep** (pairwise only if a config matrix appears). Record the technique + coverage level behind each case or group.
3. Generate test cases covering:
   - **Happy path** — at least one per primary acceptance criterion
   - **Negative** — one per invalid equivalence class (one invalid input per case)
   - **Boundary** — one per boundary, at the boundary and its nearest neighbour (3-value for high-risk numeric logic)
   - **Edge** — empty, max-length, special characters, concurrent actions, timing
4. **Factor shared preconditions into a single Setup** block — environment, seeded data, auth, feature flags that every (or most) cases need. Per-case `Preconditions` then list only the *delta* from Setup.
5. **Write a Cleanup block** that restores the starting state — delete created records, reset flags/counters (e.g. failed-login counter), revoke tokens, log out. Every suite ends with Cleanup, even if it's "no residual state — nothing to clean" (state that explicitly).
6. Assign a unique ID per test case using the pattern `TC-<FEATURE>-<NNN>`.
7. Tag each case with priority (P1/P2/P3), type (functional/negative/boundary/edge), and the technique it came from.
8. Emit the output in the requested format.

## Output format

### Default — Markdown table

A suite is **Setup → Cases → Cleanup**. The Setup runs once before the cases (or per-case where noted); the Cleanup always runs last.

```markdown
## Test Cases: <Feature name>

**Source**: <requirement ID or story link>
**Coverage**: <happy / full / regression>
**Techniques applied**: <EP, BVA (3-value on threshold), decision table, state transition (0-switch)>
**Generated**: <date>

### Setup (shared preconditions — run once before the suite)
- **Environment**: staging, build `<sha>`, feature flags `<flag=value>`
- **Data seeded**: user `valid@test.com` / `Valid123!` (role: Customer, not locked); 3× `Paid` orders
- **Auth**: obtain a session for the seeded user where the case starts logged-in
- **Reset**: failed-login counter = 0

### Cases

| ID | Title | Priority | Type | Technique | Preconditions (delta from Setup) | Steps | Expected Result | Test Data |
|----|-------|----------|------|-----------|----------------------------------|-------|-----------------|-----------|
| TC-LOGIN-001 | Successful login with valid credentials | P1 | functional | use-case (basic flow) | — | 1. Navigate to `/login`<br>2. Enter email<br>3. Enter password<br>4. Click "Sign in" | Redirected to `/dashboard`. Session cookie set. | `valid@test.com` / `Valid123!` |

### Cleanup (always runs — restore starting state)
- Delete any records created during the run (orders, sign-ups)
- Reset failed-login counter to 0; unlock the test account if a case locked it
- Revoke issued sessions / tokens; log out
- Restore feature flags to their pre-run values
- _If a case leaves no residual state, say so explicitly: "No residual state — nothing to clean."_
```

**Why a single Setup + a single Cleanup:** shared preconditions written once stay consistent and don't rot across 30 rows; per-case `Preconditions` carry only what differs. The Cleanup guarantees independence (CLAUDE.md: *tests are independent, any test can run alone, in any order*) — a suite that locks an account or seeds an order and never cleans up poisons the next run.

### Coverage summary

At the end, include a coverage table:

```markdown
## Coverage Summary

| Acceptance Criterion | Test Cases | Covered? |
|---------------------|------------|----------|
| AC1: User can log in with valid credentials | TC-LOGIN-001 | ✅ |
| AC2: User sees error for invalid password | TC-LOGIN-002, TC-LOGIN-003 | ✅ |
| AC3: Account locks after 5 failed attempts | TC-LOGIN-004, TC-LOGIN-005, TC-LOGIN-006 | ✅ |
```

## Writing the case text well

Deriving the *right* cases is `test-design-techniques`' job; writing each one so a **different tester executes it identically** is this skill's. Four rules govern the prose — they're what separates a case that's run once by its author from one that survives in a regression suite.

**Step altitude — intent, not selectors.** Write steps at the level of *user intent*, not UI mechanics, so a case survives a button relabel or a layout change. "Open the login page" — not "Click the hamburger → Account → the blue Sign-in button top-right". Pin an exact selector, path, or shortcut *only* where that mechanic is the thing under test (a masked-field reveal toggle, a deep link, a keyboard accelerator). This is the manual mirror of CLAUDE.md's page-object rule — *expose intent, not selectors* — and it leaves room for exploratory discretion instead of scripting the tester's hands.

**One behavior per case; keep it short.** A case verifies **one** behavior and reads in ≈3–8 steps (hard ceiling ~15). The 30-step "log in → browse → add to cart → checkout → pay → email → refund" script is the *long-sequence anti-pattern*: unmaintainable, and when step 4 breaks you can't tell which behavior failed. Split end-to-end journeys into per-flow use-case cases that **chain via preconditions** ("starts where `TC-…-003` left off") or lean on the shared Setup — don't inline the whole world into one row.

**Expected results are observable and specific.** "System works correctly" / "login succeeds" is *not* an expected result — it can't be falsified. State the **observable** outcome: visible text, URL, HTTP status, a persisted record, an element state. "Redirected to `/dashboard`; header shows 'Hello, Jordan'; session cookie set" — every clause is something a tester can see and a reviewer can check. When a flow asserts at several points, **attach the check to the step** (`3. Submit → 400, body {error:"email_taken"}`) rather than collapsing everything into one final cell.

**Consistency.** One verb per action, one name per field, one ID scheme — and use the product's **real UI labels**, not paraphrases. A suite that says "Sign in" / "Log in" / "Authenticate" for the same button reads as written by three people and slows every execution. If the team has a test-case style guide, follow it; if not, the first suite sets the house style.

**Self-review pass before emitting.** Reread each case as a tester seeing the feature for the first time: can you execute it without guessing? Strip the weasel words that hide missing detail — *valid, appropriate, correctly, as expected, etc., and so on*. Each one is either a concrete value you haven't written down yet or an assertion you haven't made observable.

## Quality bar

The **suite** must:

- [ ] Open with a **Setup** block holding every shared precondition (no precondition repeated across 10 rows)
- [ ] Close with a **Cleanup** block that restores the starting state (or states "nothing to clean")
- [ ] Name the **techniques applied** in the header

Every generated **test case** must:

- [ ] Have an unambiguous title that describes the behavior, not the implementation
- [ ] Cover **one behavior** in ≈3–8 steps (≤15) — split long journeys, don't inline them
- [ ] List only its **delta** preconditions (what differs from Setup) — `—` if none
- [ ] Have numbered, atomic steps written at **intent altitude** (one user action per step; selectors only where the mechanic is under test)
- [ ] Have an **observable, verifiable** expected result — concrete state a reviewer can check, never "works correctly"
- [ ] Specify test data — concrete values, not "valid email"
- [ ] Name the **technique** it was derived from
- [ ] Be traceable back to at least one acceptance criterion
- [ ] Contain no weasel words (`valid`, `appropriate`, `correctly`, `etc.`) — survive the self-review pass

Negative tests must use realistic invalid inputs, not just "invalid". `password: "''"` is better than `password: "<invalid>"`.

## Test design techniques

Don't improvise the cases — derive them. The full method (definitions, coverage criteria, worked examples, selection matrix, stopping criteria) lives in **`qa/manual/test-design-techniques`**. Load it and apply the default recipe. One-line reminder of what each picks:

| Technique | Use when | Picks |
|-----------|----------|-------|
| Equivalence partitioning | Inputs fall into groups treated the same | one value per valid + invalid partition |
| Boundary value analysis | Behavior changes at an ordered boundary | the boundary + neighbour (3-value for high risk) |
| Decision table | Multiple conditions combine into an outcome | one case per rule (collapse "don't care") |
| State transition | Object has states; history matters | all valid transitions + reject invalid ones |
| Use-case | A user journey with alternate/exception flows | one case per flow |
| Pairwise | Many independent parameters, can't test all | every pair of values |
| Error guessing | Known-fragile spots the spec is silent on | empty/null/max+1/whitespace/concurrency/timezone |

## Example

### Input

> **Story**: As a user, I want to log in with my email and password so I can access my account.
>
> **AC1**: Given a valid email and password, when I click sign in, I am redirected to /dashboard.
> **AC2**: Given an invalid email or password, I see "Invalid credentials" without leaking which was wrong.
> **AC3**: After 5 consecutive failed attempts, the account is locked for 15 minutes.
> **AC4**: Password field is masked by default with a toggle to reveal.

### Output

```markdown
## Test Cases: User Login

**Source**: STORY-1247
**Coverage**: full
**Techniques applied**: equivalence partitioning, BVA (3-value on the 5-attempt lockout threshold), error guessing (whitespace, SQLi)
**Generated**: 2026-05-27

### Setup (run once before the suite)
- **Environment**: staging, build `<sha>`; lockout window = 15 min, threshold = 5 attempts
- **Data seeded**: user `user@test.com` / `Valid123!` exists, account **not locked**, failed-attempt counter = 0
- **State**: tester starts logged out, on a clean browser session

### Cases

| ID | Title | Priority | Type | Technique | Preconditions (delta) | Steps | Expected Result | Test Data |
|----|-------|----------|------|-----------|-----------------------|-------|-----------------|-----------|
| TC-LOGIN-001 | Successful login with valid credentials | P1 | functional | EP (valid) | — | 1. Navigate to `/login`<br>2. Enter email<br>3. Enter password<br>4. Click "Sign in" | Redirected to `/dashboard`. Session cookie set. | `user@test.com` / `Valid123!` |
| TC-LOGIN-002 | Login rejected with invalid password | P1 | negative | EP (invalid) | — | 1. Navigate to `/login`<br>2. Enter valid email<br>3. Enter wrong password<br>4. Click "Sign in" | Stays on `/login`. Error: "Invalid credentials". | `user@test.com` / `WrongPass1!` |
| TC-LOGIN-003 | Login rejected with non-existent email | P1 | negative | EP (invalid) | — | 1. Navigate to `/login`<br>2. Enter email that does not exist<br>3. Enter any password<br>4. Click "Sign in" | Stays on `/login`. Error: "Invalid credentials" (same message as TC-LOGIN-002, not "user not found"). | `nobody@test.com` / `Valid123!` |
| TC-LOGIN-004 | 4 failed attempts do not lock (boundary − 1) | P1 | boundary | BVA (3-value) | counter = 0 | 1. Repeat TC-LOGIN-002 four times | After 4th attempt: still "Invalid credentials", account **not** locked. | `user@test.com` / `WrongPass1!` × 4 |
| TC-LOGIN-005 | Account locks on the 5th failed attempt (boundary) | P1 | boundary | BVA (3-value) | counter = 0 | 1. Repeat TC-LOGIN-002 five times | After 5th attempt: "Account locked. Try again in 15 minutes." | `user@test.com` / `WrongPass1!` × 5 |
| TC-LOGIN-006 | Locked account rejects valid password | P1 | functional | state transition | account just locked | 1. Navigate to `/login`<br>2. Enter valid email<br>3. Enter correct password<br>4. Click "Sign in" | Error: "Account locked. Try again in 15 minutes." Not redirected. | `user@test.com` / `Valid123!` |
| TC-LOGIN-007 | Account unlocks after 15 minutes | P2 | boundary | BVA (time) | account locked at time T | 1. Wait 15 minutes from T<br>2. Navigate to `/login`<br>3. Enter valid credentials<br>4. Click "Sign in" | Redirected to `/dashboard`. | `user@test.com` / `Valid123!` |
| TC-LOGIN-008 | Password field masked by default | P2 | functional | EP | — | 1. Navigate to `/login`<br>2. Type into password field | Characters render as `•` or `*`. | `Valid123!` |
| TC-LOGIN-009 | Email field trims whitespace | P3 | edge | error guessing | — | 1. Navigate to `/login`<br>2. Enter `" user@test.com "` with leading/trailing space<br>3. Enter valid password<br>4. Sign in | Logs in successfully (whitespace trimmed). | `" user@test.com "` / `Valid123!` |
| TC-LOGIN-010 | SQL injection attempt rejected safely | P1 | negative | error guessing | — | 1. Navigate to `/login`<br>2. Enter email: `' OR '1'='1`<br>3. Enter any password<br>4. Sign in | Error: "Invalid credentials". No SQL error leaks. No login granted. | `' OR '1'='1` / `anything` |

### Cleanup (always runs)
- Reset the failed-attempt counter to 0 and **unlock** `user@test.com` (TC-LOGIN-005/006 lock it)
- Revoke any session/cookie issued by TC-LOGIN-001
- Log out; clear the browser session
- No records created → none to delete

## Coverage Summary

| Acceptance Criterion | Test Cases | Covered? |
|---------------------|------------|----------|
| AC1: Valid login redirects to dashboard | TC-LOGIN-001 | ✅ |
| AC2: Invalid credentials show generic error | TC-LOGIN-002, TC-LOGIN-003 | ✅ |
| AC3: Account locks after 5 failures, 15 min | TC-LOGIN-004 (boundary − 1), TC-LOGIN-005 (boundary), TC-LOGIN-006, TC-LOGIN-007 | ✅ |
| AC4: Password masked by default | TC-LOGIN-008 | ⚠️ reveal-toggle half of AC4 not yet covered — add a case |

## Notes

- TC-LOGIN-004/005 split the 5-attempt lockout into boundary − 1 (4 → not locked) and boundary (5 → locked) — 3-value BVA on the threshold, per `qa/manual/test-design-techniques`.
- AC4's reveal-toggle half has no case yet — the ⚠️ in the coverage summary is the honest signal; add `TC-LOGIN-011` for it.
- TC-LOGIN-009 (whitespace trimming) is not in the ACs — flag with the PO before adding to regression.
- TC-LOGIN-010 (SQL injection) is implicit in security baseline; include in P1 regardless.
```

## Anti-example

User says: "write a test case for the login button"

Bad response: a single test case "click login button → user logs in" — too coarse, no preconditions, no negative coverage.

Good response: ask "do you have the acceptance criteria for login? If not, I'll generate cases for the obvious happy path and common negatives, and flag what I assumed."

### Vague vs. observable case text

Same intent — "verify a returning user can log in" — written two ways:

```markdown
<!-- BAD: every cell is unfalsifiable or over-scripted -->
| Steps | Expected Result | Test Data |
| 1. Open app and authenticate correctly | User logs in and everything works as expected | valid credentials |

<!-- GOOD: intent-altitude steps, observable result, concrete data -->
| Steps | Expected Result | Test Data |
| 1. Open the login page<br>2. Sign in with the seeded credentials | Redirected to `/dashboard`; header shows "Hello, Jordan"; session cookie `sid` set. | `jordan@test.com` / `Valid123!` |
```

Why the first row fails every rule in *Writing the case text well*: **"authenticate correctly"** scripts nothing a tester can repeat (no page, no fields) yet hides a weasel word (*correctly*); **"logs in and everything works as expected"** can't be falsified — there's no URL, text, or state to check; **"valid credentials"** isn't data. A different tester runs it three different ways and none of them can fail it.

## Handoffs

- Distill the source docs into a concise, sourced test-basis document first → `qa/manual/requirements-breakdown`
- Decide *which* cases to write (partitions, boundaries, rules, transitions) → `qa/manual/test-design-techniques`
- Orchestrate the full documentation → suite flow → `qa/manual/agents/qa-test-case-designer`
- Size the test investment by risk first → `qa/manual/test-strategy`
- Unscripted probing beyond the scripted cases → `qa/manual/exploratory-charter-writer`
- File defects found while authoring/executing → `qa/manual/bug-report-writer`
- Automate the resulting cases → `qa/<stack>/skills/api-test-author/...` / `qa/<stack>/skills/ui-test-author/...`
