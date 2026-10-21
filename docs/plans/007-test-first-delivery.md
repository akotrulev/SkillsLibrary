# 007 — The delivery flow: test-first, built to be split, observable from the first task — plan (2026-10-21)

**Goal:** Make test-first the library's default way to deliver a feature. A plan agrees the data model and the API contract, commits stubs that answer `501 not-implemented`, has `qa-*` agents write the acceptance tests against those stubs, and only then has the `be` / `fe` / `mobile` agents implement until the tests pass, with their own unit tests at the 80% branch floor. Implementers may run their own tests; the full gate still runs once. Two rules ride with it: the default architecture is a modular monolith **built to be split later** (§4.5), and every service is **observable from its first task** — logs, traces and metrics reach a local Grafana stack while the feature is being built, not after (§4.6). And every plan flags which of its tasks can run at the same time (§3.7).

**Status:** Planned 2026-10-21; nothing built. Next: T1. The coverage floor this plan's gates keep landed separately in `0d9826a` (committed, not pushed). Before the first test-first plan runs in a project: T5, the push, and H1. Built but unverified: nothing yet.

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| Acceptance tests are written before the implementation | QA authoring is a separate pass at the end: "Live/E2E/integration test runs … belong to a separate QA pass owned by a `qa-*` peer" (`backend/_shared/delivery-plan/SKILL.md:361`), and the agent-batched order puts "the QA pass" in the verification batch (`:177`) | A `Q` task family between the contract tasks and the implementation (§2, §3.2) |
| `Q` tasks have something to test against | Contract-wave stubs return "an explicit not-implemented response" (`delivery-plan/SKILL.md:191`), shape unspecified; the OpenAPI asset is generated "after the last endpoint task" (`:110`) | One stub response, defined once; the asset generated from the stubs by the contract task (§4.1, D3, D6) |
| Tests trace to requirements | Stories carry Gherkin ACs (`business-analysis/skills/ba-story-writer/SKILL.md:46`), cited as `US13 AC2` in `ba-story-quality-review`; `api-surface.md` endpoint blocks and `experience-plan.md` journeys do not cite them | An `Acceptance:` line on each endpoint block and each journey (§4.2, §4.3) |
| Journey tests can be written before the screens | Test ids are authored with the components (`frontend/*/skills/test-ids`); `experience-plan.md` screen blocks carry none (`backend/_shared/experience-plan/SKILL.md:68-90`) | A `Test ids:` line per screen: the names the page objects and the screen both bind to (§4.3) |
| Implementers see red turn green | The plan gates once and every earlier task runs nothing (`engineering-practices/writing-plans/references/plan-format.md` §5); 58 agents carry the identical "`Gate: none` … runs no build, test suite" bullet | A `Gate: own tests` form: a filtered run of the task's own tests (§3.1, D1) |
| Implementers cannot pass a test by changing it | No rule; the gate task "fixes what it finds" (`plan-format.md` §5), tests included | Acceptance tests are read-only to implementation tasks (§3.3, D2) |
| The QA agents can write tests against stubs | `qa-api-<stack>` Mode A builds from a spec and assumes a working service (`qa/dotnet/agents/qa-api-dotnet.md:37`); nothing expects red | A shared `qa/_shared/test-first` skill the nine qa-api/ui/mobile agents cite (§6, D5) |
| Behaviour a change must keep is pinned before the change | Only the unit-level re-entry "the logic is right, the tests are missing" (`backend/dotnet/agents/be-dotnet.md:55`) | A pin task ahead of any change to behaviour no test pins (§5.3, D7) |
| A plan's tests and code share one worktree | Plan Queue makes one worktree per plan, of one repo; the coverage floor diffs one repo's history (`plan-format.md` §5); the blueprint says nothing about repo layout (`backend/_shared/solution-blueprint/SKILL.md` §3) | A repository-layout line in the blueprint, and test-first plans that stay inside one repo (§2.1, D8) |
| The default architecture stays cheap to split | The blueprint's default is a modular monolith whose stated cost is "module boundaries need discipline to survive" (`solution-blueprint/SKILL.md:94`), with no rule or test enforcing them; the data model skips the ownership map for a monolith (`data-model-plan/SKILL.md` Step 6); the planner says "under ~4 functional areas" (`solution-planner.md:88`) where the blueprint says "< ~6" | Four boundary rules, an architecture test and the split triggers (§4.5, D9) |
| Services are observable while they are built | The planner schedules telemetry last — "Last \| The OpenAPI asset, telemetry, …" (`delivery-plan/SKILL.md:161`, `:177`, `:206`) — and the blueprint's routing example runs it "after the first capability's tasks land" (`solution-blueprint/SKILL.md:212`); the `be-*` agents never instrument, the `observability-engineer-<stack>` peer does it afterwards | The telemetry base in the foundation, every implementation task instruments what it builds, and the gate proves the signals arrive (§4.6, D10) |
| A plan says which tasks can run at the same time | Plan Queue is gaining parallel tasks: a `Depends on: T1, T2` line in a task's prompt starts it as soon as those are done, and `Depends on: none` starts it at once. No planning skill writes that line. A task block's `**Depends on:**` lists prerequisites only — not the file overlaps that make two concurrent tasks collide — and position stands in for every other ordering; `solution-planner` packs carry streams instead (`delivery-plan/SKILL.md` Step 3) | A `Depends on:` line in every prompt block, naming its prerequisites and every earlier task it shares files or a build with; the preamble says what runs together; a close-out that is safe while another task runs (§3.7, D11) |
| The user's global task rules agree | `~/.claude/CLAUDE.md` rule 5 forbids any test run before the last task; rule 6 orders contract → backend → frontend with no test step | H1 replaces both rules with §9's text |

## 2. The flow this plan builds

| # | Step | Who | Produces | Tests |
|---|---|---|---|---|
| 1 | Define the feature | `requirements-author` (`/dev:refine`) | `stories.md`: Gherkin ACs, cited `US7 AC2` | — |
| 2 | Agree the contracts | `solution-planner` (`/dev:plan-system`) | approved `blueprint.md`; `data-model.md`; `api-surface.md` with `Acceptance:` per endpoint; `experience-plan.md` with `Test ids:` per screen and `Acceptance:` per journey; `delivery-plan.md` in the test-first order | — |
| 3 | Contract tasks `C` | `be-<stack>`, plus `data-architect` for schema depth, `fe-<stack>` for the shell, and `observability-engineer-<stack>` for the telemetry base | schema and migrations, the module folders with a schema each and the architecture test, entities, DTOs, error envelope, auth wiring, **every endpoint routed and answering `501 not-implemented`**, the OpenAPI asset generated from the stubs, the app shell with a placeholder per screen route, and **the telemetry base**: OpenTelemetry, structured logs carrying the trace id, the local Grafana stack | compile; nothing to run |
| 4 | Acceptance tasks `Q` | `qa-api-<stack>`, then `qa-ui-<stack>` / `qa-mobile-<stack>` | API tests from the endpoint blocks, the validation catalog and the ACs; journey tests on the agreed test ids | **red**, each on `not-implemented` |
| 5 | Implementation tasks `B`, `F` | `be-*`, then `fe-*` / `mobile-*` | the logic, with unit tests at the 80% branch floor, **instrumented as it is built** — the spans, decision-point logs and business metrics its task names | the task's acceptance tests turn **green**; they are read-only |
| 6 | The gate | the last runnable task | build, the whole suite (old and new), lint, the coverage floor, **the telemetry smoke**; fixes what it finds | all green, and the named signals found in Grafana's stores |

Two properties make it hold up with LLM implementers:

- **The tests come from a different agent, from the contract, before the code exists**, so they test the agreement and not the implementation.
- **The implementer cannot change them.** Passing a test by editing it is how test-first fails with LLMs; §3.3 closes that.

**Where it applies (D4):** every plan that delivers an API surface or a journey. A plan with no external contract (an internal refactor, a tool) stays test-after; where it changes behaviour that no test pins, a pin task goes first (§5.3).

### 2.1 Where things live — one repo per product (D8)

A plan runs in one Plan Queue worktree, which is one repo, and the coverage floor diffs one repo's history. So a test-first plan keeps its contract, its acceptance tests and its code in **one repo**. The blueprint (`solution-blueprint/SKILL.md` §3) gains a `**Repository layout:**` line that proposes this by default:

```
<product>/
  contracts/                OpenAPI and AsyncAPI documents: what every side binds to
  services/<name>/          one deployable each, in its stack's native workspace:
                            .NET .slnx · Gradle multi-project · pnpm package · uv project
  services/<name>/src/Modules/<Module>/   inside a modular monolith: one folder per module (§4.5)
  services/<name>/tests/    unit tests and the acceptance tests that drive its implementation
  web/  mobile/             the clients, in the TypeScript workspace or their own native projects
  e2e/                      journey suites that need several deployables running together
  deploy/local/             the local Grafana stack, started with one command (§4.6)
  docs/plans/               the plans
```

- **Mixed languages are fine in one repo.** No build tool spans them: each stack keeps its native workspace in its own folder, CI triggers on path filters, and a nested `CLAUDE.md` per folder carries that stack's conventions.
- **Microservices fit the same layout.** A service is a folder with its own build, image and path-triggered pipeline, deployed on its own; cross-service APIs and events are agreed in `contracts/`, and consumer-driven contract tests between services are `Q` tasks. The default proposal stays a modular monolith, now built to be split later (§4.5); a module becomes a service only on one of its split triggers.
- **Multi-repo is supported with one plan per repo.** A plan cites another repo's plan by its `Depends on` line, and the contract travels as the OpenAPI asset through `qa/_shared/api-spec-assets`. Where a team keeps its suites in a separate QA repo, the acceptance tests that drive the implementation still live beside the service; the QA repo keeps the environment-level suites built from the same asset (O4).

## 3. The plan format

Files: `engineering-practices/writing-plans/references/plan-format.md`, `engineering-practices/writing-plans/SKILL.md`, and the Planning section of `CLAUDE.md`.

### 3.1 `Gate: own tests` (D1)

The `**Gate:**` line gets a third form, in §4's table and in §5:

| Form | On | Runs |
|---|---|---|
| `**Gate: none** — this plan gates once, in <id>. Do not run …` | contract tasks, docs tasks, journey tasks whose app cannot start in one command | nothing |
| ``**Gate: own tests** — run only `<command>`; this plan gates once, in <id>. Do not run the full suite, another tree's build, lint or typecheck.`` | `Q` tasks and the implementation tasks of a test-first plan | exactly the command |
| `**Gate (this is the last runnable task …):**` | the last runnable task | the whole set in run order, ending with the coverage floor |

- **The planner writes the command, filtered by file or class**, never the unfiltered suite: `dotnet test tests/Orders.AcceptanceTests --filter "FullyQualifiedName~Orders"`, `./gradlew test --tests '*OrdersApiTest'`, `npx vitest run src/orders`, `npx playwright test e2e/booking.spec.ts`.
- **A `Q` task's command runs the tests it writes and expects red. An implementation task's command runs its unit tests and the acceptance tests it must turn green, then the coverage-floor measure over the files it wrote** (§5's table, scoped to those files), so a shortfall is closed in the session that wrote the code.
- **When the acceptance tests need a running service**, the command starts it the project's own way (a Testcontainers fixture, the compose file, Playwright's `webServer`), and the block says so. A journey suite that cannot start its app in one command is `Gate: none`, and its red check moves to the gate.
- **A failure outside the task's own tests is not its to fix**; it is noted in `As built`.
- **Read-back budget** (writing-plans Step 5): **10k** for an own-tests task — its commit and diff, plus the filtered runs.
- **Every test-first plan restates the cost:** the tree is still not known to build at a task boundary; only each task's own tests are known to pass.

### 3.2 The `Q` family and the order

- **`Q` is the acceptance-test family:** ids `Q1…Qn`, stack `qa`, agent `qa-api-<stack>` / `qa-ui-<stack>` / `qa-mobile-<stack>`, skills including `qa-<stack>:test-first`.
- **Order** (writing-plans Step 3): everything both sides bind to — the schema, the contract, the shared types and **the stubs** — then **the acceptance tests written against them**, then the backend tasks, the shared-package tasks, and the frontend and mobile tasks.
- **A `Q` task's deliverable names its tests and their red reason:** "every endpoint in `api-surface.md` §5.2 and every AC of US7–US9 has an acceptance test in `services/orders/tests/Orders.AcceptanceTests/`, and each fails on `501 not-implemented`."
- **An implementation task's deliverable names the acceptance tests it turns green:** "the 14 Orders acceptance tests from Q1 pass, and B3's unit tests cover ≥ 80% of its branches."

### 3.3 Acceptance tests are read-only to implementers (D2)

A rule in §4 and a line in every implementation prompt, verbatim:

> The acceptance tests a `Q` task wrote are the spec, and they are **read-only** to every later task except the gate. Never edit, skip, delete or weaken one: not its assertion, its data or its timeout. A test you believe is wrong is a dated `D<n>` with both readings, and it stays red; the gate task resolves it with the user.

### 3.4 Red for the right reason

A `Q` test is red **on the `not-implemented` stub** — in Arrange or in Act, since a setup call that reaches a stub is also the right reason — or, for a journey, **on the screen's placeholder**. A test that passes against a stub asserts nothing. A test that is red on a `404`, a compile error or a wrong URL has a wiring defect, which the `Q` task fixes before it stops.

### 3.5 Never in a plan (§9 additions)

- An implementation task that edits, skips or deletes an acceptance test
- A `Gate: own tests` line with no command, or with an unfiltered one
- A `Q` task that was allowed to run its tests and did not see them red on the stub

The existing line "an intermediate task that runs the build or the suite" is reworded so that a filtered own-tests run is not a defect.

### 3.6 `CLAUDE.md` Planning

The gate-once bullet names the `own tests` form. One new bullet states the test-first order and the read-only rule, pointing at `plan-format.md` §5. The "In review" line drops "an intermediate task that runs the suite" for "an intermediate task that runs more than its own tests".

### 3.7 Parallel tasks: a `Depends on:` line in every prompt (D11)

Plan Queue starts a task as soon as the tasks named on its prompt's `Depends on: T1, T2` line are done, and starts a task whose line reads `Depends on: none` at once. Writing those lines is how a plan says which of its tasks can run in parallel; tasks that run together share the plan's working tree.

- **Every prompt block carries the line, as its first line, ids only:** `Depends on: T1, T3`, or `Depends on: none`. A plan never relies on what a missing line means.
- **The line names every earlier task this one must not run beside:** its prerequisites, which the task block's `**Depends on:**` already gives, and every earlier task whose `Files` overlap its own or that builds the same tree. Two tasks in one .NET solution, one Gradle build or one pnpm package graph share build output, so one waits for the other. Once the lines exist, position orders nothing: a task that leaves out an overlapping predecessor runs beside it, in the same working tree.
- **The task block and the prompt agree.** The block's `**Depends on:**` gives the reasons and the prompt's line gives the ids; an edge already implied through another task may be left out of both.
- **The gate task waits for every task that nothing else waits for**, so it starts last.
- **The prompts table gains a `Runs beside` column** naming, per task, the tasks it can run in parallel with, and the preamble says it in one line: "After C1, B1 → B2 run beside Q1; F1 waits for both; F2 is the gate."
- **The close-out while another task may be running** (two additions to format §7): commit only your own files, by path, never `git add -A`; and re-read the plan immediately before the close-out edits, touching only your own task block, your own prompt block and the landed line. `Status:` is rewritten by the next task that waits for you.

Files: `plan-format.md` §4 (what the `Depends on` row must name), §6 (the prompt's first line, the `Runs beside` column, the preamble line) and §7 (the two additions); `writing-plans/SKILL.md` (Step 2's file map gives the overlap edges, Step 3 writes them, Self-Review checks them, the handoff names what runs together); `delivery-plan/SKILL.md` Steps 3 and 6 (each prompt's line names its stream predecessor and its cross-stream edges — the streams stay, because Mission Control reads them); the prompts template (the line in every block); `solution-planner.md` Step 9's parallelism check.

## 4. The design pack and the architecture rules

### 4.1 The stub response — `api-surface-plan/references/validation-catalog.md` (D6)

A new standard-set entry: **`501` `application/problem+json`, `type` slug `not-implemented`, `detail` naming the task that implements the endpoint (`"B3"`).** A contract-task stub answers exactly this and nothing else. It is never listed per endpoint, and it exists only while the stub does. The stub declares the endpoint's real response types, so the OpenAPI asset generated from it is complete (D3).

### 4.2 `Acceptance:` per endpoint — `api-surface-plan/SKILL.md` Step 3

Each endpoint block gains `**Acceptance:** US7 AC1, US7 AC2` under `**Auth:**`: the ACs the endpoint proves. Step 3's rules gain two: every AC in `stories.md` with an outcome visible at the API lands on at least one endpoint, and an endpoint with no AC is either a missing story or an endpoint nobody asked for. `references/example-api-surface.md` shows it.

### 4.3 `Test ids:` per screen, `Acceptance:` per journey — `experience-plan/SKILL.md` Steps 3–4

- Each screen block gains `**Test ids:**`: the PascalCase dot-separated ids of its interactive elements and list containers (`SessionDetail.BookButton`, `SessionDetail.AttendeeList`), named by the stack's `test-ids` rules. The journey tests' page objects and the screen both bind to these names, which is what lets a journey test exist before its screen. "What NOT to put in an experience plan" keeps its ban on component names; a test id is not a component name, and one line says so.
- Each journey gains `**Acceptance:**`: the ACs it proves.
- The template, the Self-check and `references/example-experience-plan.md` (`S3`, `J1`) follow.

### 4.4 `Repository layout:` — `solution-blueprint/SKILL.md` §3 (D8)

The §3 template gains `**Repository layout:**` after `**Patterns in play:**`, with §2.1 as the default proposal: one repo per product, one folder per deployable in its native workspace, the driving acceptance tests beside the code. Multi-repo needs a stated reason (independent teams or release cadences) and means one plan per repo.

### 4.5 Built to be split later (D9)

The default proposal stays a modular monolith, now **built to be split later**: every boundary a service split needs exists from the first task, so splitting a module later is a move, not a redesign.

**The four rules:**

1. **A module owns its data.** Its tables live in its own schema. No other module reads or writes them: no cross-module join, no shared table, and no foreign key into another module's schema — another module holds the id.
2. **Modules talk through a public surface.** Each module exposes one public API — a facade or interface shaped like the HTTP contract it would become, DTOs in and out, never an entity — and the events it publishes. Everything else is internal: `internal` in C#, an internal package under Spring Modulith, not exported from the module's `index.ts`.
3. **An architecture test fails the build on a reach-in.** ArchUnitNET for .NET (NetArchTest.Rules has had no release since 2021); Spring Modulith's `ApplicationModules.verify()`, or ArchUnit, for Java; dependency-cruiser for TypeScript. It runs with the unit tests, so an agent cannot erode a boundary without turning the build red.
4. **One folder per module**, mirrored by one schema, one DI registration and one test folder — one module per functional area in the blueprint.

**The split triggers** are the only reasons a module becomes a service, and each is recorded as a dated decision when it is used:

- it must scale apart from the rest;
- another team will own it, on its own release schedule;
- it needs isolation the process cannot give — untrusted input, or a compliance scope (the sandboxed upload worker is the house example);
- it needs a different runtime.

Size, tidiness and "we might need it later" are not triggers. Splitting a module means moving its folder into `services/<name>/`, giving its schema a database of its own, and replacing the in-process calls to its public API with a client generated from that same contract.

| File | Change |
|---|---|
| `solution-blueprint/SKILL.md` Step 3 | The default row becomes "Modular monolith, built to be split later", with the four rules and the triggers under the table. The "+ extracted service" and "Services per area" rows cite the triggers as what earns them. The area count (`< ~6`) goes: the triggers decide. The §3 template gains `**Modules:**` (module → schema → owning area), and `references/example-blueprint.md` (`:36`) fills it in |
| `data-model-plan/SKILL.md` Steps 3 and 6, template §6 | The owning-area column names the module's schema. Step 6 runs for a modular monolith too, recording each cross-module read and the public API it goes through; a cross-module join or write is a finding, as two services writing one table already is. `references/example-data-model.md` (`:133`) follows |
| `solution-planner.md:88` | "under ~4 functional areas" goes; the rule cites the blueprint's default and its triggers |
| `delivery-plan/SKILL.md` Step 1 | The scaffold row adds the module folders, a schema per module and the architecture test, written by the first contract task so that every later task is checked against it. The example's `C1` names the test |
| `backend/{dotnet,java,node}/skills/pattern-writer/SKILL.md` | A "Module boundaries" section: the public surface, `internal` by default, a schema per module in the ORM mapping, a call or an event between two modules, and the stack's architecture test |
| `backend/{dotnet,java,node}/skills/code-review/SKILL.md` | One row: a module reading another module's table, entity or internal type → **major**; the fix is the owner's public API |

`be-python` is out of scope: the upload worker is a single-purpose service, not a modular monolith.

### 4.6 Observable from the first task (D10)

Today the planner puts telemetry after the features, and only the `observability-engineer-<stack>` peer instruments (§1). After this plan, three things change.

1. **The telemetry base is foundation work.** One task right after the scaffold, run by `observability-engineer-<stack>`, wires the OpenTelemetry SDK (traces and metrics, OTLP export), structured logging with the trace id on every line, the resource attributes (`service.name`, `service.version`, `deployment.environment`), a per-service RED dashboard, and **the local Grafana stack**: a compose file under `deploy/local/` (Collector, Loki, Tempo, Prometheus, Grafana) that every developer and the gate start with one command. From then on, every request that any later task's code serves shows up in Grafana while the feature is still being built.
2. **Every implementation task instruments what it builds.** The `be-{dotnet,java,node}` agents gain a rule, and load their bundled `structured-logging-<stack>` and `opentelemetry-<stack>` skills whenever a task adds an entry point, an outbound call, a background job or a business event:
   - **logs** at the decision points (a rejection, a retry, a state change), written as message templates with the ids as properties and no secrets or personal data; an error is logged once, where it is handled, with its exception;
   - **a span** around each business operation and around each outbound call that auto-instrumentation does not cover, with the ids and the outcome as attributes, and the trace context carried across queues and jobs;
   - **a metric** per business event (`orders.placed{outcome}`), with low-cardinality labels only;
   - the task's bullets name the signals it adds, so the gate can look for them.
3. **The gate proves the signals arrive: the telemetry smoke.** A plan that adds or changes a service's behaviour ends its gate, after the coverage floor, with the local stack up while the acceptance suite runs against the service. It then confirms the named spans in Tempo, a log line in Loki carrying one of those traces' id, and the named metrics in Prometheus, and records the trace id and the queries in `As built`. With no container runtime on the machine, the smoke is recorded as unverified in `Status:`, never skipped silently.

| File | Change |
|---|---|
| `delivery-plan/SKILL.md` | The telemetry base joins the foundation in all three shapes, after the scaffold and before the `Q` tasks. "Telemetry" leaves the `Last` rows (`:161`, `:177`, `:206`), which keep business dashboards and alert rules only. Step 4's rules: an implementation task's bullets name its signals |
| `delivery-plan/references/example-delivery-plan.md` | A telemetry-base task in the contract wave (`observability-engineer-dotnet`), and named signals on `B3` |
| `solution-blueprint/SKILL.md` | The routing example (`:212`) runs telemetry in the foundation; the §3 template's cross-cutting line names the local Grafana stack |
| `solution-planner.md` | The observability peer runs in the foundation; Step 9 gains "every implementation task names its signals" |
| `plan-format.md` §5 | The telemetry smoke, after the coverage floor |
| `be-{dotnet,java,node}` agents | An "Instrument what you build, as you build it" bullet beside the coverage floor, naming the two bundled skills by path, so the skill-loading protocol permits them |
| `be-{dotnet,java,node}` code-review skills | One row: new behaviour with no span, no decision-point log or no business metric → **major**; a secret or personal data in a log line or span attribute → **blocker** |
| `observability/agents/observability-engineer-{dotnet,java,node}.md` | In a plan, its first task is the telemetry base — the SDK wiring, the local stack and the RED dashboard; business dashboards and alerts come in a later task |
| `CLAUDE.md` Backend code rules | One bullet: instrument as you build, on a telemetry base that lands first |

`be-python`'s upload worker has no observability skill in this library; that is O6, not this plan.

## 5. The planner

### 5.1 `backend/_shared/delivery-plan/SKILL.md`

- **Step 1 table, two new rows:** endpoint blocks + the validation catalog + the `Acceptance:` lines → **API acceptance tasks** (`qa-api-<stack>`, one per resource group that fits a session); journeys + `Test ids:` → **journey tasks** (`qa-ui-<stack>` / `qa-mobile-<stack>`). The OpenAPI-asset row (`:110`) changes: in a test-first plan, the contract task generates the asset from the stubs.
- **Step 2, every shape:** the `Q` tasks sit after the contract tasks and before the implementation they specify.
  - Agent-batched: contract wave → API acceptance batches → journey batches → backend module batches → frontend area batches → verification. `:177` drops "the QA pass", which now runs before the implementation.
  - Feature-complete: per capability, its contract task → its `Q` tasks → its backend task → its screens.
  - Platform-first: contract → `Q` → one task per resource.
  - Each shape states its cost (D4).
- **`:191` "Stubs must be unmistakable"** cites §4.1's response.
- **`:361` "Tasks are implementation"** is rewritten: `Q` tasks write the acceptance tests before the implementation; running the whole suite, the journeys and any manual check stays with the gate.
- **Step 4:** a `Q1` example block beside `B3`; `B3`'s deliverable names the Q1 tests it turns green, and its gate becomes `Gate: own tests`.
- **Self-review:** every endpoint and every journey is covered by a `Q` task; every `Q` task precedes the tasks that turn its tests green; every implementation deliverable names its acceptance tests; every own-tests command is filtered.
- **The header-note template (`:543`)** names the `own tests` form.

### 5.2 `delivery-plan/references/example-delivery-plan.md`

The example (agent-batched, .NET API + web client) gains `Q1` (the Bookings API acceptance tests, `qa-api-dotnet`) and `Q2` (journeys J1–J2, `qa-ui-typescript`) after its contract wave. The `B` and `F` tasks name the tests they turn green, and the task table, the `Order` column and §1's rows follow. Abbreviated blocks stay abbreviated.

### 5.3 Pin tasks (D7)

Behaviour the plan must **not** change, that no test pins, gets a **pin task** before the first task that touches it: `qa-api-<stack>` pins what the API shows, and the `be-<stack>` agent pins logic with unit tests (the "logic is right, the tests are missing" re-entry). Deliverable: "the current behaviour of <area> is pinned by N tests, green on today's code." Pin tests are read-only like acceptance tests. Behaviour the plan **does** change gets `Q` tests for the new behaviour instead, never a pin.

### 5.4 `backend/_shared/session-budget/SKILL.md` and `references/prompts-section-template.md`

- The read-back table: **10k** for an own-tests task.
- A `Q` block shape. Its reading list: the endpoint blocks by section, the validation catalog's standard set, the ACs, and the OpenAPI asset's path from the contract task's `As built`. Its traps: §3.4, never assert the stub, bind to the contract and the test ids, never to code. Its gate: `own tests`, expecting red.
- The implementation block: §3.3 verbatim, and `Gate: own tests` expecting green.

### 5.5 `backend/_shared/agents/solution-planner.md`

- Step 1's question batch: test-first is the default where there is an API surface or a journey (D4); ask only whether to opt out, and record the answer beside the execution model. The repository layout is proposed per §4.4.
- The routing map includes the `qa-*` agents for `Q` tasks, with `qa-<stack>:test-first`.
- Steps 7–9 carry §5.1's self-review lines; the Step 9 checklist gains "every AC reaches a `Q` test" and "every own-tests command is filtered".
- The "plan gates once" operating rule names the `own tests` form.

## 6. The QA lane — `qa/_shared/test-first` (D5)

A new shared skill, registered in `qa-java`, `qa-dotnet` and `qa-typescript` beside `./qa/_shared/api-spec-assets` (`.claude-plugin/marketplace.json:130,265,405`):

| Section | Says |
|---|---|
| When | A plan's `Q` task writes acceptance tests before the implementation exists. Not for tests of built code: the agents' own modes cover that |
| Inputs | The OpenAPI asset the contract task generated from the stubs, taken in through `api-spec-assets`; the endpoint blocks and the validation catalog; the ACs. For journeys: the journeys and the `Test ids:` lines |
| Where the tests live | In the repo the plan runs in, beside the code they specify (D8) |
| Trace | Every test carries the AC id it proves: NUnit `[Category("US7-AC2")]`, JUnit `@Tag("US7-AC2")`, Playwright `{ tag: '@US7-AC2' }`, otherwise in the `describe` title. Every AC with an outcome on this surface has a test; the report lists any AC without one, and why |
| Bind to the contract | The generated client and DTOs, the agreed test ids and the documented error slugs, never the service's code, which does not exist yet. Expected values come from the contract and the ACs, never from the stub |
| Red for the right reason | §3.4. Run the new tests once under `Gate: own tests` and record each one's red reason. Fix any red on a `404`, a compile error or a wrong URL before stopping |
| Data | Set up through the public API or an existing test hook. A setup call that reaches a stub is red for the right reason, and the report says so |
| Hand-over | The report lists each implementation task's own-tests filter (the test classes or files per resource group or journey), which the `Q` task writes into the blocks below it (close-out step 3) |
| Never | Assert `501`; weaken an assertion so it passes early; skip a test until its endpoint lands |

Each of the nine agents — `qa-api-{dotnet,java,typescript}`, `qa-ui-{dotnet,java,typescript}`, `qa-mobile-{dotnet,java,typescript}` — gains one line where it decides what to build from (the qa-api agents' `## Input modes`; the qa-ui and qa-mobile agents' equivalent): **Test-first (a `Q` task in a plan):** load `qa/_shared/test-first` and follow it. The service is a stub, and red on `not-implemented` is the expected result.

## 7. The executing agents and the testing skills

### 7.1 The shared gate bullet

Fifty-eight agents carry this bullet verbatim:

> - **Inside a plan task, the prompt block's `Gate:` line decides what you run.** A `Gate: none` task writes its code and tests and runs no build, test suite, lint or typecheck, whatever an exit criterion below says; only the task that carries the plan's gate runs them.

In all 58 it becomes, verbatim:

> - **Inside a plan task, the prompt block's `Gate:` line decides what you run.** A `Gate: none` task writes its code and tests and runs nothing. A `Gate: own tests` task runs exactly the command its block names — its own tests and the acceptance tests it writes or must turn green — and nothing else: no full suite, no other tree's build, no lint or typecheck. Only the task that carries the plan's gate runs the whole set, whatever an exit criterion below says.

The three variants — `qa/manual/agents/qa-test-case-designer.md`, `qa/manual/agents/qa-feature-spec-writer.md:36` and `engineering-practices/verify-before-done/SKILL.md:14` — get the same meaning in their own words.

### 7.2 The read-only rule

The ten implementing agents — `be-{dotnet,java,node,python}`, `fe-{react,blazor}`, `mobile-{react-native,ios,android}` and `tooling-engineer` — gain this bullet after their coverage-floor bullet:

> - **In a test-first plan, the acceptance tests are the spec, and they are read-only to you.** A `qa-*` task above yours wrote them against the contract; your task makes the ones its block names pass. Never edit, skip, delete or weaken one: not its assertion, its data or its timeout. A test you believe is wrong is a dated `D<n>` with both readings, and it stays red; the gate task resolves it with the user.

The eight "Obey your task's `Gate:` line" bullets (`be-*` ×4, `fe-*` ×2, `tooling-engineer`, `data-architect`) name the `own tests` form in one clause.

### 7.3 The testing skills

The nine unit- and component-testing skills say today, in their generation or validation lines, that a `Gate: none` task runs none of their commands. Each line becomes: `Gate: none` runs nothing and reports "written, not run"; `Gate: own tests` runs this task's tests — step 4's red run, then green — and the *Coverage floor* measure over the files it wrote, and nothing else.

## 8. The gate (T5)

From the SkillsLibrary root, in order:

1. `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` exits 0.
2. `claude plugin validate .` ends with `✔ Validation passed`.
3. `python3 tools/plugin-surface-check.py` reports OK.
4. `python3 tools/token-audit.py --violations-only` lists no file this plan created. A file it changed that the audit lists is compared with its size at this plan's first commit (`git show <commit>:<path> | wc -c`); a violation that predates the plan and grew is recorded as a dated `D<n>`.
5. `python3 tools/qa-version-check.py` reports OK.
6. ``grep -rlF 'A `Gate: own tests` task runs exactly the command its block names' --include='*.md' . | grep -v docs/plans | wc -l`` is 58; `grep -rlF "the acceptance tests are the spec, and they are read-only to you" --include='*.md' . | grep -v docs/plans | wc -l` is 10; the old bullet's text appears nowhere outside `docs/plans/`.
7. `qa/_shared/test-first` is registered in exactly the three `qa-*` plugins, and every citation of `qa-<stack>:test-first` or `qa/_shared/test-first` resolves.
8. Built to be split (M1): `grep -c "~4 functional areas" backend/_shared/agents/solution-planner.md` prints 0; the blueprint's default row reads "built to be split later"; `backend/{dotnet,java,node}/skills/pattern-writer/SKILL.md` each have a module-boundaries section naming ArchUnitNET, Spring Modulith (or ArchUnit) and dependency-cruiser respectively, and none recommends NetArchTest.Rules.
9. Observable from the first task (L1): no `Last` row in `delivery-plan/SKILL.md` names telemetry, and all three shapes carry the telemetry base in their foundation rows; `plan-format.md` §5 names the telemetry smoke; `grep -l "Instrument what you build" backend/{dotnet,java,node}/agents/be-*.md` lists three files.
10. Parallel tasks (P1): `plan-format.md` §6 requires a `Depends on:` line in every prompt block, the `Runs beside` column and the preamble's runs-together line; §4 says the line names overlap edges; §7 carries the two close-out additions; the prompts template shows the line in every block; `writing-plans/SKILL.md` Self-Review checks the overlap edges.
11. Format sweep over the changed files: no `TODO` or `FIXME`; every `file:line` this plan cites still points at the text it names.

## Decisions

**D1 — Test-first tasks run their own tests; the full gate still runs once.** Recommended 2026-10-21, and taken with the user's go-ahead on the proposal. Flip it before T1 runs if not.

| Option | Verdict | Why |
|---|---|---|
| `Gate: own tests`: a filtered run of the task's own tests | **chosen** | The implementer sees red turn green on exactly its tests; the gate stays the one place the whole set runs |
| Gate-once unchanged: tests written first, never run before the gate | rejected | Test-first in name only: the gate session inherits every failure, which in a large codebase overruns its budget |
| The full gate per task | rejected | The whole-suite verify loop per task that the 2026-09-20 rule removed |

Cost: about 4k more read-back per own-tests task (10k instead of 6k). The tree is still not known to build at a task boundary. It reverses part of the 2026-09-20 rule and of the 2026-09-26 removal of TDD, which is why H1 rewrites the user's global rules.

**D2 — Acceptance tests are read-only to implementers.** A disputed test becomes a `D<n>` and stays red, and the gate resolves it with the user. Cost: a wrong test stays red until the gate, and the gate session may need the user before it can finish.

**D3 — The contract task generates the OpenAPI asset from its stubs.** Today the asset is generated after the last endpoint task (`delivery-plan/SKILL.md:110`); the `Q` tasks need it first, to generate their typed client and DTOs through `api-spec-assets`. Cost: a stub must declare its real response types or the asset is incomplete, and the asset is regenerated when the bodies land, through `api-spec-assets`' diff lane.

**D4 — Test-first is the default wherever there is an API surface or a journey.** Plans with no external contract stay test-after. Cost: agent-batched plans gain two agent switches (the API batch and the journey batch); feature-complete plans gain two per capability.

**D5 — One shared skill, `qa/_shared/test-first`, cited by nine agents**, not a mode copied into each. Precedent: `qa/_shared/api-spec-assets`. Cost: one more shared skill registered in three plugins; a heading renamed in it breaks nine citations, which gate step 7 checks.

**D6 — The stub answers `501` problem+json `not-implemented`, defined once in the validation catalog.** It makes "red for the right reason" a precise check. Cost: one entry in the standard set.

**D7 — Pin before change.** Behaviour a plan must keep, and that no test pins, gets a pin task first; behaviour it changes gets `Q` tests for the new behaviour. Cost: one task per untested area a plan touches. This is the direct answer to regressions in a large codebase.

**D8 — A test-first plan runs in one repo.** Its contract, its acceptance tests and its code share one worktree, because Plan Queue makes one worktree per plan and the coverage floor diffs one repo's history. The blueprint proposes one repo per product (§2.1); a product spread over several repos runs one plan per repo, and its contract travels as the OpenAPI asset.

| Option | Verdict | Why |
|---|---|---|
| One repo per product, polyglot, one folder per deployable | **default proposal** | A contract change, its tests, the server and the client land in one plan and one history; no version skew between repos |
| One repo per service or per team, with one plan per repo | supported | Fits independent teams and release cadences; every cross-repo seam is a hand-off between plans |
| One plan spanning several repos | rejected | Plan Queue's worktree is one repo, and the per-repo `git diff` cannot measure the floor across repos |

Cost: a team that keeps its suites in a separate QA repo moves the tests that drive implementation next to the service (O4).

**D9 — The default architecture is a modular monolith built to be split later.** The user chose this over microservices as the default (2026-10-21).

| Option | Verdict | Why |
|---|---|---|
| Modular monolith, built to be split later | **chosen** | Boundaries without network hops: a wrong boundary is a refactor, the compiler and the in-process tests guard every cross-module change, and a module becomes a service on a trigger, by a move |
| Microservices as the default | rejected | Independent deploys, scaling and team autonomy pay off for several teams; for one team they add runtime-only contract failures, distributed transactions and heavier end-to-end tests — the regression surface this plan exists to shrink |
| Modular monolith as today, rules unstated | rejected | "Module boundaries need discipline to survive" is a cost the blueprint names and nothing enforces; agents erode an unenforced boundary first |

Cost: no foreign key across modules, so referential integrity between modules is the owning module's job; cross-module reads go through an API call instead of a join. An existing codebase keeps the architecture it has — the default applies to new systems only.

**D10 — Services are observable from their first task, not after the features.** The user asked for this (2026-10-21): Grafana must have data while a feature is being developed. The telemetry base lands in the foundation, each implementation task instruments what it builds, and the gate's telemetry smoke proves the signals arrive. Cost: one more foundation task per plan that starts a service (an `observability-engineer-<stack>` session); about 2k more per implementation task for its spans, logs and metrics; and a gate that needs a container runtime, or records the smoke as unverified.

**D11 — Every prompt carries a `Depends on:` line, and the line includes file overlap.** The user asked for this (2026-10-21), to cut a plan's wall-clock time; Plan Queue runs a task as soon as the tasks on its line are done.

| Option | Verdict | Why |
|---|---|---|
| A `Depends on:` line in every prompt, with prerequisites and overlap edges | **chosen** | It is what Plan Queue reads, and the overlap edges are what make two tasks safe to run in one working tree |
| Prerequisites only on the line | rejected | Two tasks with no logical edge can still edit one file, or build one tree, at the same time |
| `Stream:` lanes on every task | rejected | Plan Queue does not read them: a second notation to keep in step with the first. `solution-planner` packs keep theirs, because Mission Control reads them |

Cost: a missed overlap edge lets two agents edit one file at once, and the Self-Review check is the only guard; the close-out gains two rules; and a plan's history interleaves the commits of tasks that ran together.

## Answered questions (2026-10-21)

**O1 — Do implementers run tests:** their own, filtered (D1).
**O2 — Who writes the acceptance tests:** the `qa-*` agents, before the implementation. The implementing agent writes only its unit tests.
**O3 — Mixed languages and microservices:** both fit one repo — a native workspace per folder, path-filtered CI, services deployed on their own (§2.1).
**O7 — Monolith or microservices by default:** a modular monolith built to be split later (D9).
**O8 — When telemetry is built:** from the foundation on, with each task (D10).
**O9 — How Plan Queue runs parallel tasks:** it starts a task once the tasks on its prompt's `Depends on:` line are done, and `Depends on: none` starts it at once (the user; being built in plan-queue).
**O10 — Should plans say which tasks can run in parallel:** yes, through those lines (D11).

## Open questions

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| O4 | Your work repos keep suites in a separate QA repo. Where do the tests that drive implementation live there? | (a) beside the service, with the QA repo keeping the environment-level suites — recommended; (b) test-first is not used in those repos | H2's choice of project | the user |
| O5 | Between a `Q` task and the task that turns its tests green, acceptance tests sit in the history red. Does Plan Queue merge a plan's commits into the main branch only after its gate? | (a) yes, so red never reaches main — recommended; (b) no, and CI must exclude the not-yet-green tests until the gate | H2 in a project whose CI runs on main | the user |
| O6 | The Python upload worker has no observability skill. How do its signals reach Grafana? | (a) a follow-up plan adds `observability/opentelemetry-python` and `structured-logging-python` — recommended; (b) JSON logs to stdout only, collected from the container | nothing in this plan; a project with the worker | the user |

## 9. The user's global task rules (H1)

H1 replaces rules 5 and 6 of `~/.claude/CLAUDE.md` § "How features are broken down into tasks" with:

```markdown
5. **Each task states one deliverable, and writes the tests that deliverable needs** — and **the
   full gate runs once, with the plan's last task** (2026-09-20; own tests since 2026-10-21). An
   earlier task runs at most its own tests: one whose block says `**Gate: own tests**` runs
   exactly the filtered command it names — the unit tests it wrote, the acceptance tests it writes
   or must turn green, and the coverage measure over its own files — and nothing else. Every other
   earlier task says `**Gate: none**` and runs nothing: no build, no test run, no lint, no format
   check, no typecheck, no eval, no integration suite, no e2e. The last task — the close-out task,
   or the last task of a phase in a phased plan — runs the whole set for every task in the plan
   together, ending with the coverage floor (≥ 80% of the branches the plan wrote) and the
   telemetry smoke (the plan's named spans, logs and metrics found in the local Grafana stack),
   and **fixes what it finds rather than handing it back**, because a failure there may belong
   to any task before it. **The cost, accepted and stated once here: intermediate commits are not fully gated,
   so the tree is not known to build at every task boundary and a plan cannot be stopped halfway
   and trusted.** Where a stack-cut task cannot be demonstrated end to end on its own — a backend
   task whose screen arrives two tasks later — say so in the plan rather than pretending the
   capability landed, and have the contract-first side return an explicit not-implemented
   response (`501`, problem type `not-implemented`), never a fake success.
6. **Order: everything both sides bind to first** (the API contract, the schema, shared types,
   stubs that answer not-implemented, and the telemetry base — OpenTelemetry, structured logs
   and the local Grafana stack), **then the acceptance tests written against them** (`qa-*`
   tasks: API tests from the contract, journey tests from the experience plan — red on the
   stubs, and read-only to every later task except the gate), then the backend tasks, then the
   shared-package tasks, then the frontend and mobile tasks, each turning its acceptance tests
   green and instrumenting what it builds. Behaviour a plan must keep, and that no test pins,
   gets a pin task first. Every prompt carries a `Depends on:` line naming its prerequisites
   and every earlier task it shares files or a build with (`Depends on: none` when it can start
   at once), so independent tasks run in parallel. **The
   documentation and close-out work rides with the last task** rather than taking a session of its
   own — that session is the only one that knows what actually landed and what is built but
   unverified, and a session that only writes markdown is the wasted agent switch this rule exists
   to remove.
```

## 10. Tasks

### T1 — the format and the design pack specify test-first

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `plan-format.md`, `writing-plans/SKILL.md` and `CLAUDE.md` define the `Gate: own tests` form, the `Q` family and its order, the read-only rule and red for the right reason (§3.1–§3.6); the validation catalog, `api-surface-plan/SKILL.md`, `experience-plan/SKILL.md`, `solution-blueprint/SKILL.md` and their examples carry the stub response, the `Acceptance:` lines, the `Test ids:` line and the `Repository layout:` line (§4.1–§4.4).
**Depends on:** —
**Budget:** ~130k — CLAUDE.md 25k, this plan §1–§4 and D1–D8 11k, `plan-format.md` 7k, `writing-plans/SKILL.md` 6k, `api-surface-plan/SKILL.md` + `validation-catalog.md` + example 11k, `experience-plan/SKILL.md` + example 7k, `solution-blueprint/SKILL.md` §3 and template 3k, edits ~28k, commit and diff read-back 6k, churn ×1.2. Natural split if it runs over: §4 into its own task.
**Gate: none** — this plan gates once, in T5. Do not run `claude plugin validate`, the `tools/*.py` checkers or the token audit.

- `plan-format.md`: §3.1's three forms in §4's `Gate:` row and in §5, ahead of the coverage-floor paragraph; §3.2's family, order and deliverable forms as §4 rules; §3.3 verbatim; §3.4; §3.5's three lines in §9, with the existing build-or-suite line reworded.
- `writing-plans/SKILL.md`: Step 3's order, Step 5's read-back (10k for an own-tests task), Step 6's gate rule, Self-Review items 5 and 10, and one new item: every acceptance test precedes the tasks that turn it green.
- `CLAUDE.md` Planning: §3.6.
- §4.1 in the validation catalog's standard set; §4.2 in `api-surface-plan/SKILL.md` Step 3 and its example; §4.3 in `experience-plan/SKILL.md` Steps 3–4, its template, its Self-check and its example; §4.4 in `solution-blueprint/SKILL.md` Step 3 and the §3 template.
- **Not in T1:** the delivery-plan, session-budget and solution-planner changes (T2), the QA skill (T3), the agents and testing skills (T4), the catalog, README and gate (T5).

### T2 — the planner writes test-first plans

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `delivery-plan/SKILL.md`, its example, `session-budget/SKILL.md`, the prompts template and `solution-planner.md` produce test-first plans per §5: `Q` tasks after the contract tasks in every shape, own-tests gates on `Q` and implementation tasks, and pin tasks for untested behaviour.
**Depends on:** T1 (the format sections it cites).
**Budget:** ~130k — CLAUDE.md 25k, this plan §3, §5 and D1–D8 8k, `plan-format.md` §4–§5 as T1 left them 3k, `delivery-plan/SKILL.md` 17k, its example 9k, `session-budget/SKILL.md` 5k, the prompts template 4k, `solution-planner.md` 13k, edits ~19k, read-back 6k, churn ×1.2. Natural split if it runs over: `solution-planner.md` (§5.5) into its own task.
**Gate: none** — this plan gates once, in T5. Do not run the validators.

- §5.1 in `delivery-plan/SKILL.md` at the cited lines, and §5.3 in its Step 1 table (behaviour the plan must keep, with no test → a pin task) and Step 2 (pins first).
- §5.2 in the example.
- §5.4 in `session-budget/SKILL.md` and the template.
- §5.5 in `solution-planner.md`.

### M1 — the modular monolith is built to be split later

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** the blueprint, the data-model plan, the planner and the delivery plan propose a modular monolith built to be split later — the four rules, the split triggers, and the architecture test in the first contract task (§4.5) — and the three `be-*` pattern-writer and code-review skills teach and check its boundaries.
**Depends on:** T1 (the `Repository layout:` line that `Modules:` sits beside), T2 (the delivery-plan and example edits this task extends).
**Budget:** ~125k — CLAUDE.md 25k, this plan §2.1, §4.5 and D9 5k, `solution-blueprint/SKILL.md` Step 3 and template 4k, `example-blueprint.md` 3k, `data-model-plan/SKILL.md` 4.5k and its example 2.5k, `solution-planner.md:88` and `delivery-plan/SKILL.md` Step 1 by grep 3k, the example's `C1` 2k, three pattern-writers 10k, three code-reviews 9k, edits ~28k, read-back 6k, churn ×1.2.
**Gate: none** — this plan gates once, in T5. Do not run the validators.

- §4.5's table, row by row.
- Each pattern-writer's new section carries a short snippet of its stack's architecture test, checked against the tool's current documentation rather than written from memory: ArchUnitNET (`TngTech.ArchUnitNET` with its NUnit package); Spring Modulith's `ApplicationModules.of(Application.class).verify()`, on the Spring Modulith line that matches the project's Spring Boot major; and a dependency-cruiser `forbidden` rule that lets one module import another only through its `index.ts`.
- **Not in M1:** observability (L1) and `be-python` (§4.5's last line).

### L1 — services are observable from their first task

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** plans put the telemetry base in the foundation, every `be-{dotnet,java,node}` implementation task instruments what it builds, and the gate's telemetry smoke is defined (§4.6) — across the delivery plan and its example, the blueprint, the planner, `plan-format.md` §5, the three `be-*` agents and their code-review skills, the three `observability-engineer-*` agents and `CLAUDE.md`.
**Depends on:** T1 (`plan-format.md` §5 as T1 left it), T2 and M1 (the delivery-plan shapes and the example's contract wave, which this task extends).
**Budget:** ~140k — CLAUDE.md 25k, this plan §4.6 and D10 5k, `delivery-plan/SKILL.md` shape tables and Step 4 by grep 4k, the example's contract wave and `B3` 3k, the blueprint's routing example and template 2k, `solution-planner.md` by grep 1k, `plan-format.md` §5 2k, three `be-*` agents' operating rules 4.5k, three code-reviews 9k, three `observability-engineer-*` agents 14k, `structured-logging-dotnet` and `opentelemetry-dotnet` as the naming reference 7k, edits ~29k, read-back 6k, churn ×1.2. Natural split if it runs over: the three `observability-engineer-*` agents and the code-review rows into their own task.
**Gate: none** — this plan gates once, in T5. Do not run the validators.

- §4.6's table, row by row.
- The `be-{dotnet,java,node}` bullet, verbatim apart from `<stack>`:

  > - **Instrument what you build, as you build it.** When your task adds an entry point, an outbound call, a background job or a business event, load `observability/structured-logging-<stack>` and `observability/opentelemetry-<stack>` and add: a log at each decision point (a message template, ids as properties, no secrets or personal data; an error logged once, where it is handled), a span around the business operation and around any outbound call that auto-instrumentation misses, and a metric per business event with low-cardinality labels. Name the signals in your `As built` note; the plan's gate looks for them. The telemetry base — the SDK, the exporters, the local Grafana stack — belongs to the foundation task; never rebuild it.

- The telemetry smoke in `plan-format.md` §5, after the coverage-floor table: start the `deploy/local` stack, run the service with `OTEL_EXPORTER_OTLP_ENDPOINT` pointing at it, run the acceptance suite against it, then find the plan's named spans in Tempo, a log line in Loki that carries one of those traces' id, and the named metrics in Prometheus; record the trace id and the queries; with no container runtime, record the smoke as unverified in `Status:`.
- **Not in L1:** a Python observability skill (O6); frontend real-user monitoring.

### P1 — plans flag the tasks that can run at the same time

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** every plan the library writes puts a `Depends on:` line in each prompt block — its prerequisites and every earlier task it shares files or a build with — says in its preamble and its `Runs beside` column which tasks run in parallel, and closes out safely while another task runs (§3.7); in `plan-format.md`, `writing-plans/SKILL.md`, `delivery-plan/SKILL.md`, the prompts template and `solution-planner.md`.
**Depends on:** T1 (`plan-format.md` §4, §6 and §7 as T1 left them); L1, the last task before it to edit `plan-format.md`, `delivery-plan/SKILL.md` and `solution-planner.md`, which P1 edits too.
**Budget:** ~80k — CLAUDE.md 25k, this plan §3.7 and D11 4k, `plan-format.md` §4, §6 and §7 5k, `writing-plans/SKILL.md` Steps 2–3, Self-Review and the handoff 3k, `delivery-plan/SKILL.md` Steps 3 and 6 3k, the prompts template 2k, `solution-planner.md` Step 9 1k, edits ~16k, read-back 6k, churn ×1.2. Left at the low mark on purpose: merged into L1 it would pass 150k, and T3 runs beside it.
**Gate: none** — this plan gates once, in T5. Do not run the validators.

- §3.7, into each file it names.
- The prompts template's gate heading (`### F3 — <title> (<agent>, <stack>) — the last runnable task, so it carries the gate`) puts text after the agent's parentheses; Plan Queue reads the agent from a heading's trailing parentheses, so the note moves before them.
- The two close-out additions go into `plan-format.md` §7's fenced section, which every later plan copies. This plan's own `## Close-out — every task` stays as it is: a plan never edits its copy.
- **Not in P1:** Plan Queue itself, which is being built in its own repo.

### T3 — the QA lane writes acceptance tests first

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/_shared/test-first/SKILL.md` exists per §6 and is registered in `qa-java`, `qa-dotnet` and `qa-typescript`, and the nine qa-api, qa-ui and qa-mobile agents cite it.
**Depends on:** T1 (the stub response, the `Acceptance:` and `Test ids:` lines, red for the right reason).
**Budget:** ~100k — CLAUDE.md 25k, this plan §2.1, §3.3–§3.4, §4 and §6 6k, `qa/_shared/api-spec-assets/SKILL.md` as the shared-skill pattern 6k, `qa-api-dotnet.md` input modes 5k, the other eight agents' mode sections by grep 6k, the marketplace `qa-*` entries 5k, the skill written ~8k, nine agent edits 14k, three registrations 2k, read-back 6k, churn ×1.2.
**Gate: none** — this plan gates once, in T5. Do not run the validators.

- The skill per §6's table. Frontmatter: `name: test-first`; a description of at most 500 characters with triggers ("write the acceptance tests before the implementation", "a Q task") and fences (tests of built code → the agent's own modes; unit tests → the `be` / `fe` / `mobile` testing skills).
- Register it beside `./qa/_shared/api-spec-assets` in the three `qa-*` plugin entries.
- One line in each of the nine agents, per §6's last paragraph.
- **Not in T3:** the gate bullet in the qa agents — T4 rewrites all 58 at once.

### T4 — the executing agents run their own tests and keep acceptance tests read-only

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** the 58 agents carry §7.1's bullet verbatim, the three variants say the same, the ten implementing agents carry §7.2's bullet, the eight "Obey" bullets name `own tests`, and the nine testing skills carry §7.3.
**Depends on:** T1 (the `Gate: own tests` definition the bullets point at); T3 and P1, the last tasks to touch the files this one edits (the nine qa agents; the `be-*` agents and `solution-planner.md`).
**Budget:** ~135k — CLAUDE.md 25k, this plan §7 4k, grep of the 58 + 3 + 8 sites 6k, the ten implementing agents' operating rules 15k, the nine testing skills' step and validation lines 9k, a scripted replacement for the 58 3k, the variants 4k, ten read-only bullets 15k, eight "Obey" edits 12k, nine skill edits 13k, read-back 6k, churn ×1.2.
**Gate: none** — this plan gates once, in T5. Do not run the validators.

- Replace §7.1's bullet with a script that asserts exactly 58 matches outside `docs/plans/` before it writes; edit the three variants by hand.
- §7.2's bullet after each implementing agent's coverage-floor bullet; the `own tests` clause in the eight "Obey" bullets.
- §7.3 in the nine testing skills.

### T5 — the catalog, the README, the gate and the close-out

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** §8 passes, and `docs/skills-catalog.md` and `README.md` describe the delivery flow (§2, §2.1, §3.7, §4.5, §4.6) and list `qa-<stack>:test-first`.
**Depends on:** T4, which waits for every other task, so this one starts last.
**Budget:** ~100k — CLAUDE.md 25k, this plan §2, §8 and the `As built` notes 10k, catalog sections (planning lane, `qa/_shared` skills, the command tables) 8k, README sections 6k, edits 9k, the gate output and fix loop 12k plus fixes ~10k, churn ×1.2.
**Gate (this is the last runnable task, so it carries the plan's only gate, in run order):** §8, steps 1–11.

- Catalog: `test-first` joins the `qa/_shared` skill list; the planning-lane description says test-first is the default (D4), repos are one per product by default (D8), the default architecture is built to be split later (D9), and the telemetry base comes first (D10); skill counts per plugin are recounted.
- README: a "How a feature is built" section of at most 40 lines — §2's table, its two properties, §2.1's layout, and one line each for §4.5 and §4.6 — plus the new skill in the `qa-*` lists.
- Run §8 and fix what it finds; a failure may belong to any task above.
- Close out. H1 and H2 still hold blocks, so the plan does **not** move.

### H1 — the user's global task rules

**Stack:** `human` · **Agent:** `human` · **Owner:** the user
**Deliverable:** rules 5 and 6 of `~/.claude/CLAUDE.md` read as §9.
**Depends on:** T5.
**Gate:** the user reads the two rules back.

### H2 — one real feature, test-first

**Stack:** `human` · **Agent:** `human` · **Owner:** the user
**Deliverable:** H2's `As built` records whether one real feature went through §2 end to end: the `Q` tests were red on `not-implemented`, each implementation task turned its tests green without touching them, Grafana showed the feature's traces, logs and metrics while it was being built, and the gate passed with the coverage floor and the telemetry smoke.
**Depends on:** H1, the push (Status), and O4 and O5 answered.
**Gate:** the checklist in H2's prompt block.

## Close-out — every task

Before you stop, in this order, in this file:

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Your own block** — delete it, and update the line above the blocks that says which have landed.
   Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming the blocker and
   its owner.
5. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified.
6. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified) and `git mv` this plan into `docs/plans/implemented/`, same
   name and number — a `solution-planner` pack moves its whole initiative folder.
7. **Commit** — the code, its tests and these plan edits together, in one commit.

## Prompts — one per task

Run them one session each, in the SkillsLibrary checkout on `master`; never create a branch. Each block is complete on its own. Only T5 runs the gate (§8). No prompt edits `~/.claude/CLAUDE.md`: that is H1, the user's.

**What runs together:** after T1, T3 runs beside T2 → M1 → L1 → P1 — their files are disjoint. T4 waits for P1 and T3; T5 waits for T4. Each block's first line is the `Depends on:` line Plan Queue schedules on. **While T3 runs beside another task,** each of them commits only its own files, by path (never `git add -A`), re-reads this plan immediately before its close-out, and edits only its own task block, its own prompt block and the landed line; `Status:` is left to T4.

**The cost, accepted and stated once:** T1–T4's commits are ungated, so the library is not known to validate until T5, and the plan cannot be stopped halfway and trusted.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| T1 | `docs` | `general-purpose` | none | — | ~130k |
| T2 | `docs` | `general-purpose` | T1 | T3 | ~130k |
| M1 | `docs` | `general-purpose` | T1, T2 | T3 | ~125k |
| L1 | `docs` | `general-purpose` | T1, T2, M1 | T3 | ~140k |
| P1 | `docs` | `general-purpose` | T1, L1 | T3 | ~80k |
| T3 | `docs` | `general-purpose` | T1 | T2, M1, L1, P1 | ~100k |
| T4 | `docs` | `general-purpose` | T1, T3, P1 | — | ~135k |
| T5 | `docs` | `general-purpose` | T4 | — | ~100k |
| — | `git push origin master` | **the user** | T5 | — | — |
| H1 | `human` | **the user** | T5 | — | five minutes |
| H2 | `human` | **the user** | H1, the push, O4, O5 | — | one feature |

No task has landed; every block below is live.

---

### T1 — the format and the design pack specify test-first (general-purpose, docs)

````
Depends on: none

You are `general-purpose`. Task T1 of docs/plans/007-test-first-delivery.md: write the rules a
test-first plan follows (the `Gate: own tests` form, the `Q` family and its order, read-only
acceptance tests, red for the right reason) and the design-pack lines `Q` tasks are written from.

Read, in this order:
1. CLAUDE.md, the Planning section.
2. The plan: §1, §2, §2.1, §3.1–§3.6, §4.1–§4.4, D1–D8, task T1, and "Close-out — every task".
3. engineering-practices/writing-plans/references/plan-format.md §4 (the task-block table), §5 —
   including the coverage-floor paragraph and table that commit 0d9826a added — and §9.
4. engineering-practices/writing-plans/SKILL.md: Steps 3, 5 and 6, and Self-Review.
5. backend/_shared/api-surface-plan/references/validation-catalog.md (the standard set, §0–§8),
   backend/_shared/api-surface-plan/SKILL.md Step 3, and its references/example-api-surface.md.
6. backend/_shared/experience-plan/SKILL.md Steps 3–4, its template, "What NOT to put in an
   experience plan" and Self-check, and references/example-experience-plan.md.
7. backend/_shared/solution-blueprint/SKILL.md Step 3 and the §3 block of its template.

Build:
- plan-format.md: §3.1's three forms in §4's `Gate:` row and in §5, ahead of the coverage-floor
  paragraph; §3.2's family, order and deliverable forms as §4 rules; §3.3 verbatim; §3.4; §3.5's
  three lines in §9, rewording the existing build-or-suite line so a filtered own-tests run is not
  a defect.
- writing-plans/SKILL.md: Step 3's order; Step 5's read-back (10k for an own-tests task); Step 6's
  gate rule; Self-Review items 5 and 10; one new item: every acceptance test precedes the tasks
  that turn it green.
- CLAUDE.md Planning: §3.6.
- §4.1 in the validation catalog's standard set; §4.2 in api-surface-plan Step 3 and its example;
  §4.3 in experience-plan Steps 3–4, its template, its Self-check and its example; §4.4 in
  solution-blueprint Step 3 and the §3 template.

Traps:
- plan-format.md is cited by section number from three skills and every plan: add text inside the
  existing sections, never renumber them.
- A test id is not a component name. Keep "What NOT to put in an experience plan" as it is and add
  one line saying so.
- The `not-implemented` entry belongs to the standard set, is never listed per endpoint, and exists
  only while a stub does. Do not add it to a single endpoint block in the example.

Gate: none — this plan gates once, in T5. Do not run `claude plugin validate`, the tools/*.py
checkers or the token audit.

Commit: `docs(dev): test-first plans — own-tests gate, Q family, read-only acceptance tests (007 T1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### T2 — the planner writes test-first plans (general-purpose, docs)

````
Depends on: T1

You are `general-purpose`. Task T2 of docs/plans/007-test-first-delivery.md: make the planning
skills produce test-first plans — `Q` tasks after the contract tasks in every sequencing shape,
own-tests gates on `Q` and implementation tasks, and pin tasks for behaviour no test pins.

Read, in this order:
1. CLAUDE.md, the Planning section (T1 changed it).
2. The plan: §3.1–§3.6, §5, D1–D8, T1's As built, task T2, and "Close-out — every task".
3. engineering-practices/writing-plans/references/plan-format.md §4 and §5, as T1 left them.
4. backend/_shared/delivery-plan/SKILL.md: Step 1's table (`:110`), Step 2's three shape tables
   (`:177`, `:191`), Step 4 (the B3 example and its rules, `:361`), the header note (`:543`) and
   Self-review.
5. backend/_shared/delivery-plan/references/example-delivery-plan.md: the task table, §1, the C6
   and B7 blocks.
6. backend/_shared/session-budget/SKILL.md (the read-back table) and
   backend/_shared/session-budget/references/prompts-section-template.md.
7. backend/_shared/agents/solution-planner.md: Operating rules, the Steps table, the Step 9
   checklist.

Build:
- §5.1 in delivery-plan/SKILL.md, and §5.3 in its Step 1 table (behaviour the plan must keep,
  with no test → a pin task) and Step 2 (pins first).
- §5.2 in the example.
- §5.4 in session-budget/SKILL.md and the template.
- §5.5 in solution-planner.md.

Traps:
- Test-first is an ordering rule inside each shape (D4), not a fourth shape. Do not add a row to
  the shape table.
- `:361` keeps its last point: running the whole suite, the journeys and any manual check stays
  with the gate.
- The example's `Order` column and its task table must agree after the Q tasks are inserted;
  renumber `Order`, never task ids.
- Line numbers above are as of commit 0d9826a; T1 did not touch these files, but check before
  editing.

Gate: none — this plan gates once, in T5. Do not run the validators.

Commit: `docs(dev): the planner writes test-first plans (007 T2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### M1 — the modular monolith is built to be split later (general-purpose, docs)

````
Depends on: T1, T2

You are `general-purpose`. Task M1 of docs/plans/007-test-first-delivery.md: make the default
architecture a modular monolith built to be split later — four boundary rules, the split triggers,
and an architecture test that fails the build on a reach-in.

Read, in this order:
1. CLAUDE.md, the Backend code rules.
2. The plan: §2.1, §4.5, D9, the As built notes of T1 and T2, task M1, and "Close-out — every
   task".
3. backend/_shared/solution-blueprint/SKILL.md Step 3 (the style table) and the §3 template, as T1
   left them; references/example-blueprint.md §3.
4. backend/_shared/data-model-plan/SKILL.md Steps 3 and 6 and template §6;
   references/example-data-model.md (the ownership line near :133).
5. backend/_shared/agents/solution-planner.md:88; backend/_shared/delivery-plan/SKILL.md Step 1's
   scaffold row and references/example-delivery-plan.md's C1, as T2 left them.
6. backend/{dotnet,java,node}/skills/pattern-writer/SKILL.md (Rules, Generation outputs) and
   backend/{dotnet,java,node}/skills/code-review/SKILL.md (the severity table).

Build: §4.5's table, row by row, and in each pattern-writer a "Module boundaries" section ending in
its stack's architecture-test snippet.

Traps:
- Check each architecture-test tool against its current documentation before writing its snippet:
  ArchUnitNET (`TngTech.ArchUnitNET` with its NUnit package), Spring Modulith (the line matching
  the project's Spring Boot major — never up-level Boot to reach it), dependency-cruiser.
  NetArchTest.Rules has had no release since 2021; do not recommend it.
- The area count leaves both files — the blueprint's "< ~6" and the planner's "~4". The triggers
  decide, so the example blueprint's "three areas" justification is rewritten around them.
- KISS still holds: one public surface per module, no interface per class, and no message bus
  between modules unless an event is earned.

Gate: none — this plan gates once, in T5. Do not run the validators.

Commit: `docs(dev, be): modular monolith built to be split later (007 M1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### L1 — services are observable from their first task (general-purpose, docs)

````
Depends on: T1, T2, M1

You are `general-purpose`. Task L1 of docs/plans/007-test-first-delivery.md: make services observable
from their first task — the telemetry base in the foundation, every implementation task
instrumenting what it builds, and a telemetry smoke at the gate.

Read, in this order:
1. CLAUDE.md: Stack defaults (Observability) and the Backend code rules.
2. The plan: §4.6, D10, O6, the As built notes of T1, T2 and M1, task L1, and "Close-out — every
   task".
3. backend/_shared/delivery-plan/SKILL.md: the three shape tables (grep "telemetry"; T2 and M1
   moved the lines) and Step 4's rules; references/example-delivery-plan.md's contract wave and B3.
4. backend/_shared/solution-blueprint/SKILL.md: the routing example (grep "Telemetry") and the §3
   template's cross-cutting line; backend/_shared/agents/solution-planner.md: the
   observability-engineer line under Related agents, and the Step 9 checklist.
5. engineering-practices/writing-plans/references/plan-format.md §5, as T1 left it.
6. backend/{dotnet,java,node}/agents/be-*.md Operating rules; backend/{dotnet,java,node}/skills/
   code-review/SKILL.md severity tables.
7. observability/agents/observability-engineer-{dotnet,java,node}.md: the Steps table and the plan
   execution rules; observability/opentelemetry-dotnet/SKILL.md and
   observability/structured-logging-dotnet/SKILL.md as the naming reference.

Build: §4.6's table, row by row; task L1's be-* bullet verbatim apart from `<stack>`; the telemetry
smoke in plan-format.md §5, after the coverage-floor table.

Traps:
- The observability skills' choices win — Serilog on .NET, their sinks, their resource attributes.
  This task changes *when* telemetry is built, not *how*.
- The local stack is a compose file in the target project; the library ships none. Name what it
  runs and what the gate queries. If you name a single all-in-one image, check that it exposes the
  Tempo, Loki and Prometheus query APIs; otherwise query them through Grafana's API.
- A be-* agent may load only the skills it names, so the bullet names both observability skills by
  path.
- be-python stays out (O6).

Gate: none — this plan gates once, in T5. Do not run the validators.

Commit: `docs(dev, be, observability): services observable from their first task (007 L1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### P1 — plans flag the tasks that can run at the same time (general-purpose, docs)

````
Depends on: T1, L1

You are `general-purpose`. Task P1 of docs/plans/007-test-first-delivery.md: make every plan say which
tasks can run in parallel — a `Depends on:` line in every prompt block that names its prerequisites
and every earlier task it shares files or a build with, the `Runs beside` column and the
runs-together line in the preamble, and a close-out that is safe while another task runs.

Read, in this order:
1. CLAUDE.md, the Planning section.
2. The plan: §3.7, D11, task P1, and "Close-out — every task".
3. engineering-practices/writing-plans/references/plan-format.md §4, §6 and §7, as T1 and L1 left
   them.
4. engineering-practices/writing-plans/SKILL.md: Steps 2 and 3, Self-Review, Execution Handoff.
5. backend/_shared/delivery-plan/SKILL.md Steps 3 and 6 (streams, the prompts section); the prompts
   template; solution-planner.md's Step 9 item 11.

Build: §3.7 into each file it names.

Traps:
- The line is read by a program: ids only, comma-separated, or `none` when the task can start at
  once. Prose on that line turns into ids nobody has.
- Once the lines exist, position orders nothing. The overlap edges are the whole safety argument:
  a task that shares a file or a build tree with an earlier one must name it.
- solution-planner packs keep their streams, because Mission Control reads them; their prompts get
  the line too, derived from each task's stream predecessor and its cross-stream edges.
- §7's two additions go inside its fenced close-out section, which every later plan copies
  verbatim. Do not edit this plan's own close-out copy.
- A prompt heading ends with its agent in parentheses — `### F3 — <title> (<agent>, <stack>)` —
  because that is where Plan Queue reads it. Fix the template's gate heading, which has text after
  them.

Gate: none — this plan gates once, in T5. Do not run the validators.

Commit: `docs(dev): every prompt names what it waits for, so independent tasks run in parallel (007 P1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### T3 — the QA lane writes acceptance tests first (general-purpose, docs)

````
Depends on: T1

You are `general-purpose`. Task T3 of docs/plans/007-test-first-delivery.md: write the shared skill
`qa/_shared/test-first`, register it in the three qa plugins, and have the nine qa-api, qa-ui and
qa-mobile agents cite it.

Read, in this order:
1. CLAUDE.md, the Test code rules.
2. The plan: §2.1, §3.3, §3.4, §4, §6, D5, D6, D8, T1's As built, task T3, and "Close-out — every
   task".
3. qa/_shared/api-spec-assets/SKILL.md — the shared-skill pattern, and the asset the Q tests take
   their client from.
4. qa/dotnet/agents/qa-api-dotnet.md `## Input modes`; then, by grep, the input or mode section of
   qa-api-java, qa-api-typescript, qa-ui-{dotnet,java,typescript} and
   qa-mobile-{dotnet,java,typescript}.
5. .claude-plugin/marketplace.json, the three `./qa/_shared/api-spec-assets` lines (130, 265, 405)
   and their plugin entries.

Build:
- qa/_shared/test-first/SKILL.md per §6's table. Frontmatter `name: test-first`; a description of
  at most 500 characters with triggers ("write the acceptance tests before the implementation",
  "a Q task") and fences (tests of built code → the agent's own modes; unit tests → the be, fe and
  mobile testing skills).
- Register it beside ./qa/_shared/api-spec-assets in the qa-java, qa-dotnet and qa-typescript
  entries.
- One line in each of the nine agents where it decides what to build from — §6's last paragraph.

Traps:
- The tests assert the contract's behaviour. `501` is only the red reason, and asserting it is on
  the skill's "Never" list.
- The qa-ui and qa-mobile agents have no `## Input modes`; their Mode A/B are brownfield fix and
  extend. Put the line where the agent reads its basis, not inside those modes.
- Do not touch the shared Gate bullet in any agent; T4 rewrites all 58 with one script.

Gate: none — this plan gates once, in T5. Do not run the validators.

Commit: `feat(qa): test-first — acceptance tests written against stubs, before the implementation (007 T3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### T4 — the executing agents run their own tests and keep acceptance tests read-only (general-purpose, docs)

````
Depends on: T1, T3, P1

You are `general-purpose`. Task T4 of docs/plans/007-test-first-delivery.md: teach every agent the
`Gate: own tests` form, make acceptance tests read-only to the ten implementing agents, and update
the nine testing skills' run rules.

Read, in this order:
1. CLAUDE.md, the Planning section (T1 changed it).
2. The plan: §3.1, §3.3, §7, the As built notes of T1, T3, L1 and P1, task T4, and "Close-out —
   every task". T4 waits for both P1 and T3, so it also rewrites the `Status:` line that tasks
   running together left alone.
3. By grep, not whole files:
   - the 58 sites of §7.1's old bullet:
     grep -rlF "A \`Gate: none\` task writes its code and tests and runs no build" --include='*.md' . | grep -v docs/plans
   - the three variants named in §7.1;
   - the eight "Obey your task's \`Gate:\` line" bullets;
   - each implementing agent's coverage-floor bullet (be-*: appended to "You own the unit tests";
     fe-*: after "Run what you write"; mobile-*: before "No comments"; tooling-engineer: after
     "Run what you write");
   - the nine testing skills' `Gate: none` lines (backend/*/skills/unit-testing,
     frontend/*/skills/component-testing, mobile/*/skills/{unit,component}-testing).

Build:
- A script that replaces §7.1's old bullet with the new one verbatim, asserts exactly 58 matches
  outside docs/plans/ before writing, and writes nothing if the count differs. Then the three
  variants by hand.
- §7.2's bullet after each implementing agent's coverage-floor bullet; the `own tests` clause in
  the eight "Obey" bullets.
- §7.3 in the nine testing skills.

Traps:
- docs/plans/ quotes the old bullet (this plan does, in §7.1). The script must skip it.
- The be-* agents carry two gate rules — the shared bullet and "Obey your task's Gate: line" in
  their plan-execution section. Update both so they say the same thing.
- L1 put an "Instrument what you build" bullet next to the coverage-floor bullet in the three be-*
  agents. Put the read-only bullet in the same place relative to the coverage floor in all ten
  agents.
- The unit-testing skills' step 4 ("watch it fail for the right reason") is what `own tests` now
  allows. Say so in the step rather than adding a new step.

Gate: none — this plan gates once, in T5. Do not run the validators.

Commit: `feat: agents run their own tests under Gate: own tests; acceptance tests are read-only (007 T4)`.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### T5 — the gate: the catalog, the README and the close-out (general-purpose, docs)

````
Depends on: T4

You are `general-purpose`. Task T5 of docs/plans/007-test-first-delivery.md: describe the test-first
flow in the catalog and the README, run the plan's only gate, and close the work out. **You are the
plan's gate and its close-out.**

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §2.1, §4.5, §4.6, §8, D4 and D8–D11, every As built note, task T5, and "Close-out
   — every task".
3. docs/skills-catalog.md by grep, never whole (it is 186 KB): the qa/_shared skill list, the
   planning-lane description, the per-plugin skill counts, the command tables.
4. README.md by grep: the qa-* skill lists and where a "How a feature is built" section fits.

Build:
- Catalog: `test-first` in the qa/_shared skill list; the planning lane says test-first is the
  default (D4), one repo per product is the default proposal (D8), the default architecture is
  built to be split later (D9), the telemetry base comes first (D10), and every prompt names what
  it waits for, so independent tasks run in parallel (D11); skill counts recounted.
- README: "How a feature is built", at most 40 lines — §2's table, its two properties, §2.1's
  layout, and one line each for §4.5, §4.6 and §3.7 — plus the new skill in the qa-* lists.

Gate (this is the last runnable task, so it carries the plan's only gate, in run order):
  §8 steps 1–11, from the SkillsLibrary root.
**Fix what it finds rather than handing it back** — a failure may belong to any task above. Say in your
As built which task each failure belonged to.

Traps:
- §8 step 4: the token audit may list a file this plan changed that was already over budget.
  Compare with its size at this plan's first commit and record a D<n> if it grew, as plan 006 D6
  did; do not trim unrelated text.
- §8 step 6 counts must exclude docs/plans/, which quotes the old bullet.
- H1 and H2 still hold blocks, so the plan does not move. Say so in Status, and name the push,
  H1, O4 and O5 as what is next.

Commit: `docs: test-first delivery in the catalog and README; gate passed (007 T5)`.
Close out per the plan's "Close-out — every task" before you stop.
````

---

### H1 — the user's global task rules (the user)

H1 of docs/plans/007-test-first-delivery.md — your step.

Replace rules 5 and 6 of ~/.claude/CLAUDE.md § "How features are broken down into tasks" with
the text in the plan's §9: paste it yourself, or tell a session "apply plan 007 §9 to my global
CLAUDE.md". Read the two rules back. Then tell a session in SkillsLibrary to record "done" as H1's
As built and close out per the plan's "Close-out — every task".

---

### H2 — one real feature, test-first (the user)

H2 of docs/plans/007-test-first-delivery.md — your checklist.

0. In SkillsLibrary: `git push origin master`, then `claude plugin marketplace update skills-library`.
   Answer O4 and O5 in the plan first; they decide the project and where its acceptance tests live.
1. In the chosen project, take one small feature — one resource and one screen. Run `/dev:refine`,
   then `/dev:plan-system`. Check the delivery plan before queueing it:
   - the contract task stubs every endpoint with `501 not-implemented` and generates the OpenAPI
     asset from the stubs;
   - the contract wave holds the module folders with the architecture test, and the telemetry
     base with the local Grafana stack;
   - Q tasks sit between the contract and the implementation, with `Gate: own tests` expecting red;
   - every implementation block carries the read-only line, a filtered own-tests command and the
     signals it adds;
   - every prompt block opens with a `Depends on:` line that names overlapping tasks as well as
     prerequisites, and the preamble says what runs together;
   - the last task's gate ends with the coverage floor and the telemetry smoke.
2. Queue it in Plan Queue. After each Q task: its As built shows every test red on
   not-implemented, with its red reason.
3. After each implementation task: its own tests are green, `git diff` for that task shows no
   change under the acceptance-test paths, and the local Grafana shows its requests as traces with
   their logs attached.
4. After the gate: the whole suite is green, the coverage floor is met, and the telemetry smoke
   found the named spans, logs and metrics — the figures, the trace id and the queries are in its
   As built.
5. Tell a session in SkillsLibrary to record your verdict as H2's As built (what worked, what an
   agent got wrong, which rule needs changing), then close out per the plan's "Close-out — every
   task". Deleting this block files the plan into docs/plans/implemented/.
