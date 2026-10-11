---
name: test-case-writer
description: Use when the user asks to write, derive, or generate formal test cases from requirements, user stories, acceptance criteria, or feature specs. Triggers: "write test cases for X", "derive test scenarios from these ACs", "turn these ACs into runnable case scripts". Do NOT use for a feature test plan (scope/harness/artifacts) — that is test-plan-writer.
---

# QA Test Case Writer

Generates formal, implementation-agnostic test cases from requirements. Output is structured Markdown suitable for use as manual test scripts, as input to test management tools, or as guides for later automation.

This skill **assembles and formats** the suite: it factors shared preconditions into a single **Setup**, writes lean per-case steps, and always closes with a **Cleanup** so the environment is left as it was found. Its input is a **coverage-item list** (condition → technique → coverage items) derived by `qa/manual/test-design-techniques` from a `qa/manual/requirements-breakdown` document. It does not re-derive cases — when it is run standalone with only a raw story, it runs those two skills first (see *Standalone fallback*). The full doc→suite flow is orchestrated by the `qa/manual/agents/qa-test-case-designer` agent.

## When to use

- The user provides a requirement, user story, or acceptance criteria and wants test cases derived
- The user wants positive, negative, and edge cases enumerated for a feature
- The user wants a coverage matrix alongside the cases
- An exploratory session report (from `qa/manual/exploratory-charter-writer`) lists **test-case candidates** to formalize — it goes through `requirements-breakdown` first like any other basis; the resulting cases carry `#observed <session/finding id>` in their `Source` column instead of an AC

## When NOT to use

- The user wants a feature **test plan** — scope in/out, harness, artifacts, a scenario-level case inventory → `qa/manual/test-plan-writer` / the `qa-test-planner` agent
- The user wants an exploratory session charter → `qa/manual/exploratory-charter-writer`
- The user wants automation code (Playwright, Appium, RestSharp) → `qa/<stack>/skills/ui-test-author` or `qa/<stack>/skills/api-test-author`
- The user wants to report a defect they found → `qa/manual/bug-report-writer`

## Inputs needed

Confirm before generating. Ask only what's missing:

1. **The coverage-item list and the test-basis document** it was derived from (`test-design-techniques` + `requirements-breakdown` output). If only a raw story / AC set / session report exists, see *Standalone fallback*.
2. **Coverage depth** — happy path only, or include negative + boundary + edge (default: full)
3. **Where the suite goes** — default `docs/test-cases/<NNN>-<feature-slug>.md`, `NNN` = next free number in that folder, the basis document beside it as `<NNN>-<feature-slug>-basis.md`; ask only when the project already keeps suites elsewhere

The output is always the Markdown suite below. Gherkin is **not** an output of this skill — `qa/_shared/bdd/feature-file-writer` turns the finished suite into `.feature` files, with its own rules. A test-management import is the same table exported as CSV with the same column names, in the same order; no tool-specific shape is produced here.

## Procedure

1. **Map coverage items to cases.** One case per coverage item, or one case per group of *valid* items that can safely share a run (several valid partitions in one case is fine; **never two invalid inputs in one case**). Carry the technique and the condition's source line onto each case.
2. **Factor shared preconditions into a single Setup** block — environment, seeded data, auth, feature flags that every (or most) cases need. Per-case `Preconditions` then list only the *delta* from Setup. A delta that must be *re-established* (a counter reset, a fresh session) is written as the case's first step, not as a precondition — a precondition describes state, it does not act.
3. **Write each case's text** per *Writing the case text well* below: intent-altitude steps, one observable expected result, concrete data.
4. **Write a Cleanup block** that restores the starting state — delete created records, reset flags/counters (e.g. failed-login counter), revoke tokens, log out. Every suite ends with Cleanup, even if it's "no residual state — nothing to clean" (state that explicitly).
5. Assign a unique ID per test case using the pattern `TC-<FEATURE>-<NNN>`. Never renumber an existing suite.
6. Tag each case: **Priority** follows the condition's risk rank from the basis analysis — **P1** = a top-risk condition; P1 cases are the **regression floor** and what downstream agents (`qa-bdd-*`, the stack agents) automate first · **P2** = every other in-scope condition · **P3** = error-guessing and `#assumption` cases awaiting the author's confirmation. **Type** is `positive` (the system accepts the action) or `negative` (it rejects / blocks it). **Technique** names the technique and its coverage level. **Source** is the basis line the case traces to (`AC2`, `BR-1`, `V-3`), the plan row it fulfils (`TP-012`), or a tag: `#observed <evidence>` for a live-page derivation, `#assumption` for a case the basis never stated.
7. Emit the suite, then the coverage summary.

### Standalone fallback — no coverage-item list yet

When the skill is invoked directly with a raw story / AC set / exploratory session report and no basis document exists: load `qa/manual/requirements-breakdown` and write the basis document first, then load `qa/manual/test-design-techniques` and walk its default recipe (EP → BVA → decision table → state transition → use-case → error-guessing sweep) to produce the coverage-item list, then run the procedure above. Do not skip to cases from the story — the anti-example below is what that produces.

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

| ID | Title | Priority | Type | Technique | Source | Preconditions (delta from Setup) | Steps | Expected Result | Test Data |
|----|-------|----------|------|-----------|--------|----------------------------------|-------|-----------------|-----------|
| TC-LOGIN-001 | Successful login with valid credentials | P1 | positive | use-case (basic flow) | AC1 | — | 1. Navigate to `/login`<br>2. Enter email<br>3. Enter password<br>4. Click "Sign in" | Redirected to `/dashboard`. Session cookie set. | `valid@test.com` / `Valid123!` |

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
- [ ] Name the **techniques applied** in the header and the basis document it was derived from
- [ ] Live at `docs/test-cases/<NNN>-<slug>.md` (or the project's stated convention)

Every generated **test case** must:

- [ ] Have an unambiguous title that describes the behavior, not the implementation
- [ ] Cover **one behavior** in ≈3–8 steps (≤15) — split long journeys, don't inline them
- [ ] List only its **delta** preconditions (what differs from Setup) — `—` if none
- [ ] Have numbered, atomic steps written at **intent altitude** (one user action per step; selectors only where the mechanic is under test)
- [ ] Have an **observable, verifiable** expected result — concrete state a reviewer can check, never "works correctly"
- [ ] Specify test data — concrete values, not "valid email"
- [ ] Name the **technique** it was derived from
- [ ] Carry a **Source** — the basis line / plan row it traces to, or `#observed` / `#assumption` — never an empty cell
- [ ] Contain no weasel words (`valid`, `appropriate`, `correctly`, `etc.`) — survive the self-review pass

Negative tests must use realistic invalid inputs, not just "invalid". `password: "''"` is better than `password: "<invalid>"`.

## Test design techniques

Don't improvise the cases — derive them. The full method (definitions, coverage criteria, worked examples, selection matrix, stopping criteria) lives in **`qa/manual/test-design-techniques`**; this skill consumes its coverage-item list. One-line reminder of what each picks, so a reviewer can check the `Technique` column:

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
- Turn the suite into Gherkin `.feature` files → `qa/_shared/bdd/feature-file-writer` (via the `qa-bdd-<stack>` agent)
- Automate the resulting cases → `qa/<stack>/skills/api-test-author/...` / `qa/<stack>/skills/ui-test-author/...`
