---
name: test-first
description: Use when a plan's Q task writes acceptance tests before the implementation, red against 501 not-implemented stubs. Triggers "write the acceptance tests first". Not for unit tests (unit-testing).
disable-model-invocation: true
---

# QA — Test-First Acceptance Tests (Shared)

Cross-stack. In a test-first plan the contract tasks commit the schema, the DTOs and **stubs**, and the `Q` task — yours — writes the acceptance tests against them before a line of the implementation exists. The tests specify the **agreement**, not the code; the implementation tasks then turn them green and may not touch them.

The `qa-api-{stack}`, `qa-ui-{stack}` and `qa-mobile-{stack}` agents load this skill when the invoking prompt is a `Q` task. The stack skills do the authoring (`api-models`, `api-client-writer`, `api-test-author/*`, `ui-test-author/*`, the screen-object skills); this skill owns **what the tests are bound to, how they are traced, and what red means**.

## When

A plan's `Q` task writes acceptance tests before the implementation exists. **Not** for tests of built code — the agents' own modes (greenfield, brownfield fix, brownfield extend) cover that — and **not** for unit tests, which the `be`, `fe` and `mobile` agents write with the stack's testing skills.

## Inputs

The feature spec the plan builds (`docs/specs/<NNN>-<feature>-design.md`, named in the plan's header) is the basis; its `## Acceptance criteria` (`AC1…ACn`) are what the tests prove.

- **API:** the OpenAPI asset the contract task generated from the stubs, taken in through `qa/_shared/api-spec-assets` (INGEST on first pass); the endpoint blocks in the spec's `## API surface`, each with the `Acceptance:` line naming the `AC<k>` it proves; the project's validation catalog, `docs/specs/validation-catalog.md`, which that section cites.
- **Journeys:** the journeys in the spec's `## Experience` (`### Journeys`) with their `Acceptance:` lines, each screen's `Test ids:` line under `### Screens`, and the route's entry in `### Rendering plan`.
- **A plan built from a story backlog** instead: the ACs of its stories (`US<n> AC<k>`) take the spec's place, and the endpoint and journey blocks come from wherever that plan names them.
- Read the plan's `Q` task for its deliverable: which endpoints or journeys, which ACs, which folder.

## Where the tests live

In the repo the plan runs in, beside the code they specify — the service's `tests/` folder, or `e2e/` for a journey that needs several deployables. Never in a separate QA repo: the coverage floor and the read-only rule both depend on one worktree.

## Trace

Every test carries the criterion it proves, `<spec> AC<k>`, in the stack's tag form: `SPEC<NNN>-AC<k>`, the spec's number and the criterion (`SPEC006-AC2` for `docs/specs/006-booking-cancellation-design.md` AC2). From a story backlog the tag is `US<n>-AC<k>`.

| Stack | Tag |
|---|---|
| NUnit | `[Category("SPEC006-AC2")]` |
| JUnit / TestNG | `@Tag("SPEC006-AC2")` / `groups = "SPEC006-AC2"` |
| Playwright | `{ tag: '@SPEC006-AC2' }` |
| Anything else | the `describe` / class title |

A test bound to a test-plan scenario carries its `TP-` id beside the criterion, in the same form.

Every AC with an outcome on this surface has a test. The report lists any AC without one, and why.

## Bind to the contract

- Use the **generated client and DTOs**, the **agreed test ids** (the spec's `Test ids:` lines) and the **documented error slugs** (`docs/specs/validation-catalog.md`). Never the service's code, which does not exist yet.
- Expected values come from the contract and the ACs — never from what the stub returns.
- Assert the **behaviour the contract promises** (`201` and the created id; `400` with `validation-failed` and the field path), so that the same test passes unchanged when the implementation lands.

## Red for the right reason

A test is red on the stub's `501` `application/problem+json` `not-implemented` — in Arrange or in Act, since a setup call that reaches a stub is also the right reason — or, for a journey, on the screen's placeholder. A test that **passes** against a stub asserts nothing: fix it. A test red on a `404`, a compile error or a wrong URL has a wiring defect: fix it before stopping.

Run the new tests once under the task's `Gate: own tests` — the filtered command naming these tests, besides the landed tasks' tests above it — and record each test's red reason in the report. If the app cannot start in one command, the gate proves the tests load and list instead (Playwright's `--list`, or the runner's equivalent), the report says so, and the task that serves each journey turns it green.

## Data

Set up through the public API or an existing test hook, never the database. A setup call that reaches a stub is red for the right reason, and the report says so.

## Hand-over

The report lists, per implementation task, its **own-tests filter** — the test classes or files per resource group or journey. The `Q` task writes each filter into the prompt block of the implementation task below it, so that task's `Gate: own tests` runs those tests, with the tests of the landed tasks above it (the plan's close-out step 3).

## Never

- **Assert `501`** or the `not-implemented` slug. It is the red reason, not the expectation; a test that expects it goes green on the stub and red on the implementation.
- **Weaken an assertion** so it passes early.
- **Skip or ignore a test** until its endpoint lands.
- Edit a test an earlier `Q` task wrote; a test believed wrong is a dated `D<n>` in the plan, and it stays red until the gate resolves it with the user.
- Reach into the service's source, its database or its internals.

The house test rules still hold: one expected value per assertion, no `OR`, no `try`/`catch` in a test body, failures that name the field and carry the body.
