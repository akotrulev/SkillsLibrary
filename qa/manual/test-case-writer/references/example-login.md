# Worked example — user login

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

**Source**: STORY-1247 — basis `docs/test-cases/007-user-login-basis.md`
**Coverage**: full
**Techniques applied**: equivalence partitioning, BVA (3-value on the 5-attempt lockout threshold), error guessing (whitespace, SQLi)
**Generated**: 2026-05-27

### Setup (run once before the suite)
- **Environment**: staging, build `<sha>`; lockout window = 15 min, threshold = 5 attempts
- **Data seeded**: user `user@test.com` / `Valid123!` exists, account **not locked**, failed-attempt counter = 0 (TC-LOGIN-004/005 re-run this reset as their first step because TC-LOGIN-002/003 consume attempts)
- **State**: tester starts logged out, on a clean browser session

### Cases

| ID | Title | Priority | Type | Technique | Source | Preconditions (delta) | Steps | Expected Result | Test Data |
|----|-------|----------|------|-----------|--------|-----------------------|-------|-----------------|-----------|
| TC-LOGIN-001 | Successful login with valid credentials | P1 | positive | EP (valid) | AC1 | — | 1. Navigate to `/login`<br>2. Enter email<br>3. Enter password<br>4. Click "Sign in" | Redirected to `/dashboard`. Session cookie set. | `user@test.com` / `Valid123!` |
| TC-LOGIN-002 | Login rejected with invalid password | P1 | negative | EP (invalid) | AC2 | — | 1. Navigate to `/login`<br>2. Enter valid email<br>3. Enter wrong password<br>4. Click "Sign in" | Stays on `/login`. Error: "Invalid credentials". | `user@test.com` / `WrongPass1!` |
| TC-LOGIN-003 | Login rejected with non-existent email | P1 | negative | EP (invalid) | AC2 | — | 1. Navigate to `/login`<br>2. Enter email that does not exist<br>3. Enter any password<br>4. Click "Sign in" | Stays on `/login`. Error: "Invalid credentials" (same message as TC-LOGIN-002, not "user not found"). | `nobody@test.com` / `Valid123!` |
| TC-LOGIN-004 | 4 failed attempts do not lock (boundary − 1) | P1 | negative | BVA (3-value) | AC3 | — | 1. Reset the failed-attempt counter to 0 and confirm the account is unlocked<br>2. Repeat TC-LOGIN-002 four times | After 4th attempt: still "Invalid credentials", account **not** locked. | `user@test.com` / `WrongPass1!` × 4 |
| TC-LOGIN-005 | Account locks on the 5th failed attempt (boundary) | P1 | negative | BVA (3-value) | AC3 | — | 1. Reset the failed-attempt counter to 0 and confirm the account is unlocked<br>2. Repeat TC-LOGIN-002 five times | After 5th attempt: "Account locked. Try again in 15 minutes." | `user@test.com` / `WrongPass1!` × 5 |
| TC-LOGIN-006 | Locked account rejects valid password | P1 | negative | state transition | AC3 | starts where TC-LOGIN-005 left off (account locked) | 1. Navigate to `/login`<br>2. Enter valid email<br>3. Enter correct password<br>4. Click "Sign in" | Error: "Account locked. Try again in 15 minutes." Not redirected. | `user@test.com` / `Valid123!` |
| TC-LOGIN-007 | Account unlocks after 15 minutes | P2 | positive | BVA (time) | AC3 | account locked at time T (TC-LOGIN-005) | 1. Wait 15 minutes from T<br>2. Navigate to `/login`<br>3. Enter valid credentials<br>4. Click "Sign in" | Redirected to `/dashboard`. | `user@test.com` / `Valid123!` |
| TC-LOGIN-008 | Password field masked by default | P2 | positive | EP | AC4 | — | 1. Navigate to `/login`<br>2. Type into password field | Characters render as `•` or `*`. | `Valid123!` |
| TC-LOGIN-009 | Email field trims whitespace | P3 | positive | error guessing | `#assumption` | — | 1. Navigate to `/login`<br>2. Enter `" user@test.com "` with leading/trailing space<br>3. Enter valid password<br>4. Sign in | Logs in successfully (whitespace trimmed). | `" user@test.com "` / `Valid123!` |
| TC-LOGIN-010 | SQL injection attempt rejected safely | P1 | negative | error guessing | `#assumption` (security baseline) | — | 1. Navigate to `/login`<br>2. Enter email: `' OR '1'='1`<br>3. Enter any password<br>4. Sign in | Error: "Invalid credentials". No SQL error leaks. No login granted. | `' OR '1'='1` / `anything` |

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
- TC-LOGIN-009 (whitespace trimming) is not in the ACs — `#assumption`, P3 until the PO confirms; it joins the regression floor only if promoted to P1/P2.
- TC-LOGIN-010 (SQL injection) is implicit in the security baseline; `#assumption` but P1 regardless, so it is in the regression floor from day one.
```
