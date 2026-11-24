---
name: runbook-writer
description: Use when turning a feature's test cases into an executable runbook across API, UI and DB. Triggers "write a runbook for X", "run this runbook". Not for the cases themselves (test-case-writer).
disable-model-invocation: true
---

# QA Runbook Writer

A test-case suite says **what** to check and what the business effect must be. A runbook says **how to carry each case out on a real environment**: the exact request, screen action or database statement, by a named **actor**, and the one value each must give. A tester, or the `qa-manual-tester` agent in its RUN mode, follows it and records a result per test.

A runbook is a set of **tests**. One test carries out one case through one **driving actor**, and checks the outcome on every other actor that shows it. The cases and their expected results come from the suite (`qa/manual/test-case-writer`); this skill adds the actors, the commands and the data, and changes no expected result.

**It owns** the actor binding, the test and step forms, the data, the runbook document and the run record. The run itself is in `references/execution.md`.

## Inputs needed

Ask only what is missing, at most three questions:

1. **The cases**: a suite in `docs/test-cases/`, or the spec or explanation it is derived from first (the agent's step 1).
2. **The environment and how each actor is reached**: its name, the build under test, the API base URL and how a token is obtained, the web URL, the device and app build, the database engine and connection, the user and account. Secrets are named by their environment variable, never written.
3. **The codebase**, when there is one: the paths of the API project and of each UI project. With none, say so: the lookup then runs on the contract and the running system.

## Actors

A step names one actor. An actor is used only where the feature has it.

| Actor | What it is | Drives (Act) | Arranges | Asserts |
|---|---|---|---|---|
| **API** | The public API, as the user | Every operation it offers | First choice for all test data | The response, and a read-back |
| **Admin** | The back-office or admin API | What operations staff do | State no user call reaches: a halt, an approval, a switch | The state staff see |
| **UI-web** · **UI-app** | The screens, through the Playwright or Appium MCP | Every operation a screen offers | Never | What a person sees |
| **DB** | Direct SQL | Never | Only what no API, Admin, Sim or Job step can produce | The rows the action should have changed, after every action |
| **Sim** | A simulator or test double for a third party | The third party's answer: fill, reject, expire | The third party's state | What the third party received |
| **Job** | A scheduled job run on demand | Never | Time-driven work that would otherwise wait for its schedule | — |
| **Device** | Device or browser state, through the same MCP | Background, force-stop, offline, a double tap, the notification shade | — | — |
| **Doc** | A generated document: a PDF, an export | Never | — | Its rows and figures |
| **Notify** | A push, an email, an in-app message | Never | — | That it arrived, what it says, where it leads |
| **Hand** | A step only a person can do | What no actor above reaches | — | What the person reports |

A test has three parts. **Arrange** produces its data. **Act** is the one operation under test, on the driving actor. **Assert** checks the outcome on the driving actor, on each other actor that shows the same fact, and in the database.

### Which actor drives a case

| Case layer (from the suite) | Tests written | Asserted on |
|---|---|---|
| **Journey** | One, driven through the UI the actor really uses; the API only arranges | That UI at every checkpoint, an API read-back of the final state, the DB rows |
| **Rule, calculation, state, permission** | One driven by the API carrying every row of the case; one driven by the UI for the rule's main row | API: the status, the body and a read-back. UI: the outcome where the person reads it. DB: the state after |
| **Field validation** | One driven by the API carrying every row; one UI test per form, with one invalid row per field and every rule the code enforces only in the browser | A refusal also shows that nothing was created or changed |
| **Temporal, or data only time or history produces** | The test its layer calls for, arranged by a data recipe or a Job step | As its layer |
| **Data, interaction, concurrency** | One driven by the API; Sim, Job and Device steps where the case needs a third party's answer, a schedule or a device state | A read-back, the other feature's API or screen within the named budget, the DB rows, a Doc or Notify step where the case names one |

The layer is the suite's group heading; in a suite without groups it is read from the case's technique.

### Every operation, on every actor that offers it

Whatever the layers give, each **create, read, update and delete** of the feature's resource ends up with one test driven by the API and one driven by each UI that offers the operation, each asserted on another actor. The **operation grid** in §3 shows it.

- A test the layers already produced fills its cell: a journey that creates on the web is the UI-web-driven create.
- An empty cell gets an **operation test**. It adds no expected result of its own: it carries out, through the missing actor, a case whose expected result covers that operation (`Carries out: TC-…-002, API-driven`).
- An operation no case covers is a gap in the suite: a §14 row for its owner, never an invented expected result.
- A UI that does not offer the operation gets `not offered: <why>` in its cell.

## Procedure

1. **List the cases.** Take every case of the suite with its id, layer, priority and expected result, and list the create, read, update and delete operations the feature offers. Done when each case is one row of the working list and none is left out without a reason.
2. **Look up the surfaces** with `references/surface-lookup.md`: for each operation, its endpoint, its screen on each UI, its table, and any admin call, simulator or job the cases need. Done when §1 and §2 have a stamped row for every operation and every actor in scope.
3. **Bind each case to tests** with the two rules above, and give each test its id. Done when the coverage matrix has a row per test, every case appears in at least one, and every cell of the operation grid holds a test id or `not offered` with its reason.
4. **Settle the data** (*Data*, below): fixtures, the leave-alone list, the recipes, the permanent changes. Done when every precondition of every test names the fixture, Setup step or recipe that produces it.
5. **Write the preconditions, Setup, the tests and Cleanup** in the forms of `references/step-forms.md`. Done when every step has an actor, one action and one expected value or a marked observation, and Cleanup removes or reverses everything it can.
6. **Fill the register and the closing sections**: known issues, results so far, the execution order when time matters, what is not covered, the open questions. Done when every known issue is on the tests that hit it.
7. **Check it** against *The runbook check*. Done when no row fails.

## Tests

- **Ids are by family**: a letter for an area of the feature, a number within it (`J01`, `P03`, `T02`), the letters listed in a legend that opens §8. A variant of one test is `P03-A`, `P03-B`. Ids are never renumbered.
- A test's header gives its title as an outcome, its priority and layer, then `Carries out` (the case), `Uses` (preconditions, fixtures, Setup steps, recipes) and `Known` (the issues it will hit).
- A test on a risky path opens with a one-line **Why**: what breaks for the customer if it fails.

## Step rules

- **One step, one actor, one action, one expected value.** `201`, never "201 or 200". The value comes from the suite's expected result, with its worked numbers.
- **Every step holds its whole command.** No step says "as above" or cites a shared check: the tester copies what is in front of them.
- **Behaviour nobody has decided is an observe step.** It carries `Observe:` in place of `Expect:`, says what to record, and cites its open question (`OQ-3`). It never counts as a pass.
- **After every action that changes state, a DB step reads the rows it should have changed**: the status, the amounts, the history row. Its Expect is the suite's outcome as the row holds it.
- **Every value a later step needs is captured where it is produced**, under a name (`PRODUCT_ID`).
- **A step that changes what every user of the environment shares** (a switch, a halt, a schedule, a job run) is tagged `shared` and has its reversing step in Cleanup.
- **API steps are written in the project's own tool** when it has one (a `.http` file, a Postman or Bruno collection), else as `curl`.
- **UI steps are at intent altitude, in the product's own labels**, naming the screen and its route. A test id from the code follows the label in brackets: `Save [ProductForm.Save]`.
- **An outcome that arrives later is polled** against a named budget declared in Setup. A look at a fixed moment (`+3 s`) is written only in a step whose purpose is to measure the lag, and it records the time.
- **A value the suite leaves open is taken from the contract, else from the code**, stamped, and listed in §14 for the owner. Wording nobody has stated is an observe step.
- **A time boundary is written relative to now**, on both sides of the threshold, with the suite's own values where it gives them.
- **A figure is computed, with its working**, in the test that asserts it.

## Data

- **Per-run data is the default.** Every record a run creates carries the run marker `RUN` (`rb-<yyyymmdd>-<n>`, `n` the day's run number, set by the first Setup step) in a field a person can search. A name the suite gives gains the marker (`Buy stamps <RUN>`). A field whose exact value is the test carries none: that record is found by its captured id.
- **A fixture is long-lived data the runbook reuses**: an account, a funded record, reference data. §4 names each with the state every run needs it in and the Cleanup step that restores it.
- **The leave-alone list** names data on the environment that looks like the runbook's and is not: no step touches it.
- **A permanent change** is one no step can reverse (an applied corporate action, a sent document). It is listed in §4 with why the test needs it and what isolated data it is done on, and a run reports it at the end.
- **A baseline** (a balance, a count) is noted by a precondition and reconciled by the last Cleanup step, every difference explained.

### DB writes

Direct writes are the last resort, under the one confirmation that the environment is not production: API first, with a `Why not the API` line; a guard, the change and a verify; updates on rows the runbook created or declared; inserts and deletes only for what no actor can produce or remove. The seven rules are in `references/step-forms.md`, "DB steps".

## Output format

Saved to `docs/runbooks/<NNN>-<slug>-runbook.md` (`NNN` = the suite's number where it has one, else the next free). A project's own location wins. A tool file and helper scripts sit beside it under the same stem.

```markdown
# Runbook — <Feature> (<NNN>)

**Covers:** <suite path, and the spec it was derived from>   **Version:** <n> · <date>
**Environment:** <name> · <URL> · build <release> @ <commit>
**Device and browser:** <device, app build, browser>   **User and account:** <by name and role>
**Driven by:** <the actors this runbook uses>   **API calls as:** <curl | tool file> (<detected `path` | none found>)
**Codebase read:** <API `path` @ <sha, or the date read> · UI `path` @ <…> | none>
**Known issues:** §10, checked before anything is logged

## 0. What changed since version <n−1>
<Only in a runbook rewritten for another environment or build.>
| Area | Was | Now |
**Not on this build, so not tested and not logged:** <feature — why>

## 1. Access and tools
| Actor | Where | How to get in | Source |
| Variable | Meaning | Set by |
| Tool | Use |
## 2. Surface map
| Operation | API | UI-web | UI-app | DB | Other actors | Source |
## 3. Coverage matrix
| Test | Carries out | Layer | Priority | Arrange | Act | Assert |
### Operation grid
| Operation | Driven by API | Driven by UI-web | Driven by UI-app | Asserted on |
## 4. Data
| Fixture | What it is | State every run needs | Restored by |
**Leave alone:** <data, and whose it is>
| Permanent change | Why the test needs it | Done on |
## 5. Preconditions — before every session
| # | Check | How | Required state |
## 6. Setup — once per run
## 7. Data recipes
### R-1 — <the data, in the business's words>
## 8. Tests
<Legend: J journeys · P product operations · …>
### P02 — <what is done, and what must then be true> (P1 · <layer>)
**Carries out:** TC-<FEATURE>-002   **Uses:** PRE-3, S-2, R-1   **Known:** KI-2
**Why:** <risky tests only>
1. **API** — <action>
   <the whole request>
   **Expect:** <one value>   **Capture:** `PRODUCT_ID` = `id`
2. **DB** — <the rows the action changed>
   **Expect:** <one value>
3. **UI-web** — <action, screen and route>
   **Observe:** <what to record> (OQ-2)
## 9. Cleanup — always runs
## 10. Known issues — check before logging
| ID | Issue | Tests | Report | Tracker |
## 11. Results so far
| Test | Environment and platform | Last run | Result | Record |
**Never run:** <test ids>
## 12. Execution order
<Only when a test depends on a time window, a calendar day or a shared switch.>
| Order | When | Tests | Needs from the user |
## 13. Not covered
| Case | Why | What it needs |
## 14. Assumptions and open questions
```

In the matrix, Arrange holds the fixtures, Setup steps and recipes a test uses, `API` when its own first steps create its data, `—` for none. A grid cell holds a test id or `not offered: <why>`.

A full runbook is in [`references/example-product-catalogue.md`](references/example-product-catalogue.md).

## The runbook check

| Check | Fails as |
|---|---|
| Every case of the suite is carried out by a test, or sits in §13 with its reason | blocker |
| Every cell of the operation grid holds a test or `not offered` with its reason, and each of those tests asserts on another actor | blocker |
| A secret written into the runbook, a tool file or a helper script | blocker |
| A step with two acceptable values, or with "works", "correct" or "as expected" in its Expect | major |
| A step with neither `Expect` nor `Observe`, or an observe step citing no open question | major |
| A state-changing action with no DB read after it, where the DB is in scope | major |
| A DB write without its `Why not the API` line, its guard or its verify | major |
| A record or shared change that Cleanup neither removes nor reverses, and §4 does not list as permanent | major |
| An endpoint, route, label, test id or column with no stamp, or stamped `assumed` and missing from §14 | major |
| A step that says "as above", or needs a value no earlier step captures | major |
| An expected result that differs from the suite's | major |
| A known issue in §10 that no test names, or a test that hits one without naming it | minor |

## Changing a runbook

A changed case, endpoint, screen or column changes the tests that use it and bumps **Version**. A runbook rewritten for another environment or build gains §0, and the earlier version is kept beside it as `<NNN>-<slug>-runbook-v<n>.md`. A run edits §10 and §11 only; a defect in the runbook found during a run is listed in the run record and corrected after it.

## Anti-example

Asked for a runbook for product ingestion.

Bad: twelve `curl` calls for create, read, update and delete with their status codes. Every endpoint answers, and nobody has looked at a screen or a row: the product created through the API never appears in the shopper app because the list is cached, and the delete that answers `204` leaves the row live.

Good: the example above. Each operation is driven once through the API and once through each screen that offers it, each checked on the other side and in the database, and the product that must be five days old is made through the API and aged by one guarded `UPDATE`.
