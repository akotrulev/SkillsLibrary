---
name: test-first
description: Use when a plan's `Q` task writes the acceptance tests before the implementation exists — against the contract's stubs, which answer `501 not-implemented`, or a screen's placeholder. Cross-stack. Triggers "write the acceptance tests before the implementation", "a Q task", "red on not-implemented". Do NOT use for tests of built code (the agent's own modes) or unit tests (the be, fe and mobile testing skills).
---

# QA — Test-First Acceptance Tests (Shared)

Cross-stack. In a test-first plan the contract tasks commit the schema, the DTOs and **stubs**, and the `Q` task — yours — writes the acceptance tests against them before a line of the implementation exists. The tests specify the **agreement**, not the code; the implementation tasks then turn them green and may not touch them.

The `qa-api-{stack}`, `qa-ui-{stack}` and `qa-mobile-{stack}` agents load this skill when the invoking prompt is a `Q` task. The stack skills do the authoring (`api-models`, `api-client-writer`, `api-test-author/*`, `ui-test-author/*`, the screen-object skills); this skill owns **what the tests are bound to, how they are traced, and what red means**.

## When

A plan's `Q` task writes acceptance tests before the implementation exists. **Not** for tests of built code — the agents' own modes (greenfield, brownfield fix, brownfield extend) cover that — and **not** for unit tests, which the `be`, `fe` and `mobile` agents write with the stack's testing skills.

## Inputs

- **API:** the OpenAPI asset the contract task generated from the stubs, taken in through `qa/_shared/api-spec-assets` (INGEST on first pass); the endpoint blocks in `api-surface.md` and the validation catalog; the ACs in `stories.md` that the `Acceptance:` lines cite.
- **Journeys:** the journeys with their `Acceptance:` lines and each screen's `Test ids:` line in `experience-plan.md`.
- Read the plan's `Q` task for its deliverable: which endpoints or journeys, which ACs, which folder.

## Where the tests live

In the repo the plan runs in, beside the code they specify — the service's `tests/` folder, or `e2e/` for a journey that needs several deployables. Never in a separate QA repo: the coverage floor and the read-only rule both depend on one worktree.

## Trace

Every test carries the AC id it proves, in the stack's tag form:

| Stack | Tag |
|---|---|
| NUnit | `[Category("US7-AC2")]` |
| JUnit / TestNG | `@Tag("US7-AC2")` / `groups = "US7-AC2"` |
| Playwright | `{ tag: '@US7-AC2' }` |
| Anything else | the `describe` / class title |

Every AC with an outcome on this surface has a test. The report lists any AC without one, and why.

## Bind to the contract

- Use the **generated client and DTOs**, the **agreed test ids** and the **documented error slugs** (`validation-catalog.md`). Never the service's code, which does not exist yet.
- Expected values come from the contract and the ACs — never from what the stub returns.
- Assert the **behaviour the contract promises** (`201` and the created id; `400` with `validation-failed` and the field path), so that the same test passes unchanged when the implementation lands.

## Red for the right reason

A test is red on the stub's `501` `application/problem+json` `not-implemented` — in Arrange or in Act, since a setup call that reaches a stub is also the right reason — or, for a journey, on the screen's placeholder. A test that **passes** against a stub asserts nothing: fix it. A test red on a `404`, a compile error or a wrong URL has a wiring defect: fix it before stopping.

Run the new tests once under the task's `Gate: own tests` — the filtered command naming only these tests — and record each test's red reason in the report.

## Data

Set up through the public API or an existing test hook, never the database. A setup call that reaches a stub is red for the right reason, and the report says so.

## Hand-over

The report lists, per implementation task, its **own-tests filter** — the test classes or files per resource group or journey. The `Q` task writes each filter into the prompt block of the implementation task below it, so that task's `Gate: own tests` runs exactly those tests (the plan's close-out step 3).

## Never

- **Assert `501`** or the `not-implemented` slug. It is the red reason, not the expectation; a test that expects it goes green on the stub and red on the implementation.
- **Weaken an assertion** so it passes early.
- **Skip or ignore a test** until its endpoint lands.
- Edit a test an earlier `Q` task wrote; a test believed wrong is a dated `D<n>` in the plan, and it stays red until the gate resolves it with the user.
- Reach into the service's source, its database or its internals.

The house test rules still hold: one expected value per assertion, no `OR`, no `try`/`catch` in a test body, failures that name the field and carry the body.
