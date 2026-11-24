---
name: runbook-writer
description: Use when turning a feature's test cases into an executable runbook across API, UI and DB. Triggers "write a runbook for X", "run this runbook". Not for the cases themselves (test-case-writer).
disable-model-invocation: true
---

# QA Runbook Writer

A test-case suite says **what** to check and what the business effect must be. A runbook says **how to carry each case out on a real environment**: the exact request, the exact screen action, the exact database statement, and the one value each must give. A tester, or the `qa-manual-tester` agent in its RUN mode, follows it top to bottom and records a result per script.

A runbook is a set of **scripts**. One script carries out one case through one **driving channel**, and checks the outcome on every other channel that shows it. The cases and their expected results come from the suite (`qa/manual/test-case-writer`); this skill adds the channels, the commands and the data, and changes no expected result.

**It owns** the channel binding, the script and step forms, the data recipes, the runbook document and the run record. The run itself is in `references/execution.md`.

## Inputs needed

Ask only what is missing, at most three questions:

1. **The cases**: a suite in `docs/test-cases/`, or the spec or explanation it is derived from first (the agent's step 1).
2. **The channels and how to reach them**, per environment: the API base URL and how a token is obtained, the web URL and the app build, the database engine and the connection the tester uses. Secrets are named by their environment variable, never written.
3. **The codebase**, when there is one: the paths of the API project and of each UI project. With none, say so: the lookup then runs on the contract and the running system.

## Channels and what each is for

| Channel | Drives (Act) | Arranges | Asserts |
|---|---|---|---|
| **API** | Every operation the API offers | First choice for all test data | The response, and a read-back `GET` |
| **UI-web** · **UI-app** | Every operation the screen offers | Never: arranging through screens is slow and hides its own failures | What a person sees: the row, the figure, the badge, the message |
| **DB** | Never | Only what the API cannot produce | Only a fact no API response and no screen shows |

A script has three parts. **Arrange** produces its data. **Act** is the one operation under test, on the driving channel. **Assert** checks the outcome on the driving channel and on each other channel that shows the same fact.

### Which channel drives a case

| Case layer (from the suite) | Scripts written | Asserted on |
|---|---|---|
| **Journey** | One, driven through the UI the actor really uses; the API only arranges | That UI at every checkpoint, then an API read-back of the final state |
| **Rule, calculation, state, permission** | One driven by the API carrying every row of the case; one driven by the UI for the rule's main row | API: the status, the body and a read-back showing the state after. UI: the outcome where the person reads it |
| **Field validation** | One driven by the API carrying every row; one UI script per form, with one invalid row per field and every rule the code enforces only in the browser | A refusal also shows that nothing was created or changed |
| **Temporal, or data only time or history produces** | The script its layer calls for, arranged by a data recipe | As its layer |
| **Data, interaction, concurrency** (what the feature stores and sets off elsewhere) | One driven by the API | A read-back, and the other feature's API or screen within the named budget; the DB only for an effect with no surface |

The layer is the suite's group heading; in a suite without groups it is read from the case's technique.

### Every operation, on every channel that offers it

Whatever the layers give, each **create, read, update and delete** of the feature's resource ends up with one script driven by the API and one driven by each UI that offers the operation, each asserted on another channel: API-driven is checked on the web and in the app, UI-driven by an API `GET`. The **operation grid** in §3 shows it.

- A script the layers already produced fills its cell: a journey that creates on the web is the UI-web-driven create.
- An empty cell gets an **operation script**. It adds no expected result of its own: it carries out, through the missing channel, a case whose expected result covers that operation, and says so (`Carries out: TC-…-002, API-driven`).
- An operation no case of the suite covers is a gap in the suite: a §9 row for its owner, never an invented expected result.
- A UI that does not offer the operation gets `not offered: <why>` in its cell.

## Procedure

1. **List the cases.** Take every case of the suite with its id, layer, priority and expected result, and list the create, read, update and delete operations the feature offers. Done when each case is one row of the working list and none is left out without a reason.
2. **Look up the surfaces** with `references/surface-lookup.md`: for each operation the cases use, its endpoint, its screen on each UI, and its table. Record how the project already makes API calls. Done when the Access table and the Surface map have a stamped row for every operation and every channel.
3. **Bind each case to scripts** with the two rules above. Done when the coverage matrix has a row per script, every case appears in at least one, and every cell of the operation grid holds a script id or `not offered` with its reason.
4. **Write the data recipes.** Each precondition the Setup cannot seed through the API becomes a recipe under the DB rules below. Done when every precondition of every script names the Setup step or recipe that produces it.
5. **Write Setup, the scripts and Cleanup** in the forms of `references/step-forms.md`. Done when every step has a channel, one action and one expected value, and Cleanup removes every record the Setup, the recipes and the scripts create, newest first.
6. **Check it** against the table under *The runbook check*. Done when no row fails.

## Step rules

- **One step, one action, one expected value.** `201`, never "201 or 200". The value comes from the suite's expected result, with its worked numbers.
- **Every value a later step needs is captured where it is produced**, under a name (`PRODUCT_ID`), and that step's text says so.
- **Every API and DB step holds its whole command.** No step says "as above": the tester copies what is in front of them.
- **Every record carries the run marker** `RUN` (`rb-<yyyymmdd>-<n>`, `n` the day's run number, set by the first Setup step) in a field a person can search, so a rerun never collides and Cleanup finds what it made. A name the suite gives gains the marker (`Buy stamps <RUN>`), which changes no expected result. A field whose exact value is the test (an empty title, an 80-character one) carries none: that record is found by its captured id.
- **A value the suite leaves open is taken from the contract, else from the code**, stamped, and listed in §9 for the owner: a status code, an error code. Wording nobody has stated is not guessed: the Expect names what is known (a refusal under the *Title* field) and the wording is a §9 row, filled as `observed` at the first run.
- **API steps are written in the project's own tool** when it has one (a `.http` file, a Postman or Bruno collection), else as `curl`. `references/step-forms.md` has the detection and each form.
- **UI steps are at intent altitude, in the product's own labels**, naming the screen and its route. Where the code gave a test id, it follows the label in brackets: `Save [ProductForm.Save]`.
- **An effect that arrives later is polled** against a named budget declared in Setup (`within ASYNC_BUDGET`). A fixed wait is never written.
- **A figure is computed, with its working**, in the script that asserts it.
- **A time boundary is written relative to now** (`now − 5 days`), on both sides of the threshold the rule names, with the suite's own values where it gives them.

## DB rules

Direct database access is the last resort, and it leaves no trace in the application's own logic. So:

1. **Non-production only.** The Access table names the database, and the run confirms that name before the first statement.
2. **API first.** Every DB step, a change or an assert, carries a `Why not the API` line: `created_at is set by the server`.
3. **Update what the runbook created.** The row is created through the API, and the `UPDATE` targets it by the primary key that call returned.
4. **Insert or delete only what the API cannot produce or remove at all**: a row from before a migration, a state no endpoint reaches. The insert supplies every column the application requires, taken from the schema lookup, and carries the run marker.
5. **Guard, change, verify.** A `SELECT` that must return the expected row count, then the statement with the same key, then a `SELECT` showing the new value.
6. **The row stays one the application could have produced.** Fields that time or an operator would have changed together are changed together: `created_at` with `updated_at`, a status with its history row.
7. **Derived copies are brought along.** When the lookup shows the field is also held in a cache, a search index, a read model or a denormalised column, the recipe updates or re-syncs each. With no way to do that, the script is marked `needs-hook` and the hook is named.
8. **Never** a schema change, a `TRUNCATE`, or a statement whose `WHERE` holds no key.
9. **Every row a DB step creates or changes is in Cleanup.**
10. **A DB assert is written only for a fact with no surface**: a soft-delete column, an audit row, an outbox entry.

Engine forms and clients are in `references/step-forms.md`.

## Output format

Saved to `docs/runbooks/<NNN>-<slug>-runbook.md` (`NNN` = the suite's number where it has one, else the next free). A project's own location wins. API requests kept in a tool file sit beside it under the same stem (`<NNN>-<slug>-runbook.http`).

```markdown
# Runbook — <Feature> (<NNN>)

**Covers:** <suite path, and the spec it was derived from>   **Version:** <n> · <date>
**Channels:** API · UI-web · UI-app · DB
**API calls as:** <curl | `<NNN>-<slug>-runbook.http` | Postman `<file>` | Bruno `<folder>`> (<detected `path` | none found>)
**Codebase read:** <API `path` @ <sha, or the date read> · UI `path` @ <…> | none>

## 1. Access
| Channel | Where | How to get in | Source |
| Variable | Meaning | Set by |

## 2. Surface map
| Operation | API | UI-web | UI-app | DB | Source |

## 3. Coverage matrix
| Script | Carries out | Layer | Priority | Arrange | Act | Assert |
<Arrange: the Setup steps and recipes it uses, `API` when its own first steps create its data, `—` for none.>

### Operation grid
| Operation | Driven by API | Driven by UI-web | Driven by UI-app | Asserted on |
<A cell: a script id, or `not offered: <why>`. Asserted on: every channel some script checks the operation's outcome on.>

## 4. Setup — run once
## 5. Data recipes
### R-1 — <the data, in the business's words>
## 6. Scripts
### RB-01 — <what is done, and what must then be true> (P1 · <layer>)
**Carries out:** TC-<FEATURE>-001   **Uses:** S-2, R-1
1. **API** — <action>
   <the request, or its name in the tool file>
   **Expect:** <one value>   **Capture:** `PRODUCT_ID` = `id`
2. **UI-web** — <action, screen and route>
   **Expect:** <what is shown>

## 7. Cleanup — always runs
## 8. Not run through a channel
| Case | Why | What it needs |
## 9. Assumptions and open questions
```

A full runbook, for a product catalogue with a web admin and a shopper app, is in [`references/example-product-catalogue.md`](references/example-product-catalogue.md).

## The runbook check

| Check | Fails as |
|---|---|
| Every case of the suite is carried out by a script, or sits in §8 with its reason | blocker |
| Every cell of the operation grid holds a script or `not offered` with its reason, and each of those scripts asserts on another channel | blocker |
| A step with two acceptable values, or with "works", "correct" or "as expected" in its Expect | major |
| A DB step without its `Why not the API` line, or a DB change without its guard and its verify | major |
| A record created anywhere that Cleanup does not remove | major |
| An endpoint, route, label, test id or column with no stamp, or stamped `assumed` and missing from §9 | major |
| A script that needs a value no earlier step captures | major |
| A secret written into the runbook or a tool file | blocker |
| An expected result that differs from the suite's | major |

## Changing a runbook

A changed case, endpoint, screen or column changes the scripts that use it and bumps **Version**; script ids are never renumbered. A defect in the runbook found during a run (a label that moved, a step out of order) is fixed after the run and listed in the run record, never patched silently in the middle of it.

## Anti-example

Asked for a runbook for product ingestion.

Bad: twelve `curl` calls for create, read, update and delete with their status codes. Every endpoint answers, and nobody has looked at a screen: the product created through the API never appears in the shopper app because the list is cached, and the admin form saves a price the API then rounds differently.

Good: the example above. Each operation is driven once through the API and once through each screen that offers it, each checked on the other side, and the product that must be five days old is made through the API and aged by one guarded `UPDATE`.
