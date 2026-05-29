---
name: qa-test-case-writer
description: Use when the user asks to write, derive, or generate formal test cases from requirements, user stories, acceptance criteria, or feature specs. Triggers: "write test cases for X", "derive test scenarios from these ACs", "create a test plan for feature Y", "generate negative test cases". Do NOT use for exploratory test charters (use qa/exploratory-charter-writer), for filing bug reports (use qa/bug-report-writer), or for writing automation code (use qa/api-test-author or qa/ui-test-author).
---

# QA Test Case Writer

Generates formal, implementation-agnostic test cases from requirements. Output is structured Markdown suitable for use as manual test scripts, as input to test management tools, or as guides for later automation.

## When to use

- The user provides a requirement, user story, or acceptance criteria and wants test cases derived
- The user wants positive, negative, and edge cases enumerated for a feature
- The user wants a test plan or coverage matrix for a feature

## When NOT to use

- The user wants an exploratory session charter → `qa/exploratory-charter-writer`
- The user wants automation code (Playwright, Appium, RestSharp) → `qa/ui-test-author` or `qa/api-test-author`
- The user wants to report a defect they found → `qa/bug-report-writer`

## Inputs needed

Confirm before generating. Ask only what's missing:

1. **Requirement or story** — full text, including acceptance criteria if available
2. **Test type** — functional, API, UI, integration, regression (default: functional)
3. **Coverage depth** — happy path only, or include negative + boundary + edge (default: full)
4. **Output format** — Markdown table (default), Gherkin, or test management tool format

## Procedure

1. Parse the requirement and identify:
   - Actors (who performs the action)
   - Preconditions (state required before the test)
   - Triggers (the action under test)
   - Expected outcomes
   - Data variations
2. Apply test design techniques in this order:
   - **Equivalence partitioning** — group inputs into valid/invalid classes
   - **Boundary value analysis** — pick values at and around each boundary
   - **Decision tables** — when multiple conditions combine
   - **State transition** — when the feature has explicit states
3. Generate test cases covering:
   - **Happy path** — at least one per primary acceptance criterion
   - **Negative** — one per invalid equivalence class
   - **Boundary** — one per boundary, at the boundary and just outside
   - **Edge** — empty, max-length, special characters, concurrent actions, timing
4. Assign a unique ID per test case using the pattern `TC-<FEATURE>-<NNN>`.
5. Tag each case with priority (P1/P2/P3) and type (functional/negative/boundary/edge).
6. Emit the output in the requested format.

## Output format

### Default — Markdown table

```markdown
## Test Cases: <Feature name>

**Source**: <requirement ID or story link>
**Coverage**: <happy / full / regression>
**Generated**: <date>

| ID | Title | Priority | Type | Preconditions | Steps | Expected Result | Test Data |
|----|-------|----------|------|--------------|-------|-----------------|-----------|
| TC-LOGIN-001 | Successful login with valid credentials | P1 | functional | User exists with email `valid@test.com` and password `Valid123!` | 1. Navigate to `/login`<br>2. Enter email<br>3. Enter password<br>4. Click "Sign in" | User is redirected to `/dashboard`. Session cookie is set. | `valid@test.com` / `Valid123!` |
```

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

## Quality bar

Every generated test case must:

- [ ] Have an unambiguous title that describes the behavior, not the implementation
- [ ] List preconditions explicitly (don't assume "user is logged in" unless stated)
- [ ] Have numbered, atomic steps — one user action per step
- [ ] Have a single, verifiable expected result
- [ ] Specify test data — concrete values, not "valid email"
- [ ] Be traceable back to at least one acceptance criterion

Negative tests must use realistic invalid inputs, not just "invalid". `password: "''"` is better than `password: "<invalid>"`.

## Test design techniques — quick reference

| Technique | Use when | Example |
|-----------|----------|---------|
| Equivalence partitioning | Inputs fall into groups treated the same | Ages 0–17, 18–64, 65+ |
| Boundary value analysis | Behavior changes at a boundary | Discount kicks in at 100€ → test 99, 100, 101 |
| Decision table | Multiple conditions combine | Loan approval based on age × income × credit |
| State transition | Object has states with transition rules | Order: draft → submitted → approved → shipped |
| Pairwise | Many parameters, can't test all combinations | 5 browsers × 3 OS × 4 languages |

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
**Generated**: 2026-05-27

| ID | Title | Priority | Type | Preconditions | Steps | Expected Result | Test Data |
|----|-------|----------|------|--------------|-------|-----------------|-----------|
| TC-LOGIN-001 | Successful login with valid credentials | P1 | functional | User exists, account not locked | 1. Navigate to `/login`<br>2. Enter email<br>3. Enter password<br>4. Click "Sign in" | Redirected to `/dashboard`. Session cookie set. | `user@test.com` / `Valid123!` |
| TC-LOGIN-002 | Login rejected with invalid password | P1 | negative | User exists | 1. Navigate to `/login`<br>2. Enter valid email<br>3. Enter wrong password<br>4. Click "Sign in" | Stays on `/login`. Error: "Invalid credentials". | `user@test.com` / `WrongPass1!` |
| TC-LOGIN-003 | Login rejected with non-existent email | P1 | negative | None | 1. Navigate to `/login`<br>2. Enter email that does not exist<br>3. Enter any password<br>4. Click "Sign in" | Stays on `/login`. Error: "Invalid credentials" (same message as TC-LOGIN-002, not "user not found"). | `nobody@test.com` / `Valid123!` |
| TC-LOGIN-004 | Account locks after 5 failed attempts | P1 | functional | User exists, 0 failed attempts | 1. Repeat TC-LOGIN-002 five times | After 5th attempt: error message changes to "Account locked. Try again in 15 minutes." | `user@test.com` / `WrongPass1!` × 5 |
| TC-LOGIN-005 | Locked account rejects valid password | P1 | functional | User exists, account just locked | 1. Navigate to `/login`<br>2. Enter valid email<br>3. Enter correct password<br>4. Click "Sign in" | Error: "Account locked. Try again in 15 minutes." Not redirected. | `user@test.com` / `Valid123!` |
| TC-LOGIN-006 | Account unlocks after 15 minutes | P2 | functional | User account locked at time T | 1. Wait 15 minutes from T<br>2. Navigate to `/login`<br>3. Enter valid credentials<br>4. Click "Sign in" | Redirected to `/dashboard`. | `user@test.com` / `Valid123!` |
| TC-LOGIN-007 | Password field masked by default | P2 | functional | None | 1. Navigate to `/login`<br>2. Type into password field | Characters render as `•` or `*`. | `Valid123!` |
| TC-LOGIN-008 | Password reveal toggle shows plain text | P2 | functional | On `/login` with text in password field | 1. Click the eye/reveal icon next to password | Characters render as plain text. | `Valid123!` |
| TC-LOGIN-009 | Email field trims whitespace | P3 | edge | None | 1. Navigate to `/login`<br>2. Enter `" user@test.com "` with leading/trailing space<br>3. Enter valid password<br>4. Sign in | Logs in successfully (whitespace trimmed). | `" user@test.com "` / `Valid123!` |
| TC-LOGIN-010 | SQL injection attempt rejected safely | P1 | negative | None | 1. Navigate to `/login`<br>2. Enter email: `' OR '1'='1`<br>3. Enter any password<br>4. Sign in | Error: "Invalid credentials". No SQL error leaks. No login granted. | `' OR '1'='1` / `anything` |

## Coverage Summary

| Acceptance Criterion | Test Cases | Covered? |
|---------------------|------------|----------|
| AC1: Valid login redirects to dashboard | TC-LOGIN-001 | ✅ |
| AC2: Invalid credentials show generic error | TC-LOGIN-002, TC-LOGIN-003 | ✅ |
| AC3: Account locks after 5 failures, 15 min | TC-LOGIN-004, TC-LOGIN-005, TC-LOGIN-006 | ✅ |
| AC4: Password masked with reveal toggle | TC-LOGIN-007, TC-LOGIN-008 | ✅ |

## Notes

- TC-LOGIN-009 (whitespace trimming) is not in the ACs — flag with the PO before adding to regression.
- TC-LOGIN-010 (SQL injection) is implicit in security baseline; include in P1 regardless.
```

## Anti-example

User says: "write a test case for the login button"

Bad response: a single test case "click login button → user logs in" — too coarse, no preconditions, no negative coverage.

Good response: ask "do you have the acceptance criteria for login? If not, I'll generate cases for the obvious happy path and common negatives, and flag what I assumed."

## Changelog

- 2026-05-27: Initial seed
