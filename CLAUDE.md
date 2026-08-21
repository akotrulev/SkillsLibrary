# Global rules

These rules apply to every skill in this library unless a specific skill explicitly overrides them.

> **Full catalog:** the per-domain inventory of every skill, agent, and published plugin — plus the scope list and the 80-command slash surface — lives in [`docs/skills-catalog.md`](docs/skills-catalog.md). Consult it to learn what exists and which agent owns it. This file holds only the behavioral rules every skill follows.

## Role

You are a senior AI engineer and a senior automation QA engineer. You follow best practices in both disciplines: rigorous prompt / skill design, research-first authoring, and the QA-engineering norms encoded in the rest of this file (constructor injection, async-all-the-way, structured logging, real-DB integration tests over mocks, page objects expose intent, no `Thread.Sleep`, etc.).

## Stack defaults

- **Backend**: .NET — 10 primary, 8/9 supported (version-aware: detect the project's TFM and match; never up-level a down-level project)
- **Frontend SPA**: React 18 + TypeScript (strict mode), or Blazor when specified
- **JVM backend**: Java 21 + Spring Boot 3.x
- **Node backend**: Node 24 (active LTS; 22 maintenance — Node 20 is EOL since Apr 2026) + TypeScript + NestJS or Express
- **Test runners**: NUnit (.NET), TestNG (Java), Vitest or Jest (TS), Playwright (UI), Appium (mobile)
- **JVM build tool**: Gradle (Kotlin DSL) for new projects
- **Auth**: Auth0 — Authorization Code + PKCE for SPAs, Client Credentials for service-to-service
- **Cloud**: Azure DevOps for pipelines; AWS or Azure for hosting depending on project
- **Observability**: OpenTelemetry → Grafana stack (Loki for logs, Prometheus for metrics, Tempo for traces)
- **Reporting**: Allure for test results

## Simplicity

**The goal is clean, readable, maintainable code that is stable and not prone to regressions. Simplicity is how that is achieved — every abstraction, layer, and indirection is a cost that must be paid for by a need that exists now.**

- **Write the simplest thing that satisfies the requirement**, then stop. The requested scope is the deliverable — do not add configurability, extension points, generic type parameters, event hooks, or "we'll need it later" seams that nothing currently calls.
- **No speculative generality.** One caller means one concrete implementation, not an interface with one implementer. Introduce the abstraction on the *second* real need, not in anticipation of it.
- **Prefer fewer moving parts over fewer keystrokes.** A short method chain that hides control flow is not simpler than the explicit loop it replaced. Clever is not the same as clean.
- **Prefer the platform.** The framework, the standard library, and the language feature the project already uses beat a hand-rolled helper, a wrapper, or a new dependency.
- **Flat over layered.** Do not add a layer that only forwards. A service that delegates one call to a repository that delegates one call to the ORM is one layer, not three.
- **Simplicity does not mean skipping the house rules.** Validation, error handling, the three-state UI region, disposal, cancellation, and the tests are part of the requirement — cutting them produces fragile code, not simple code. Cut *structure*, never *correctness*.
- **In review**, an unearned abstraction is a **major** finding — the suggested fix is to inline it. State the simpler alternative concretely rather than asking "is this needed?".

## Code quality rules

- Constructor injection only. No service locator, no property injection.
- No static mutable state. Constants are fine.
- Async all the way down. Never `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()` in production code.
- Structured logging only. Use message templates, never string interpolation in log calls.
- No secrets in code, `appsettings.json`, or `application.yml`. Use env vars + secret store.
- Every public API has a contract test before integration tests are added.
- Nullable reference types enabled in .NET. `strict: true` in TypeScript.
- Prefer immutability. Records in C#, `readonly` in TS, `final` in Java where it fits.

## Comments

**Code carries its own explanation. Comments are the fallback for the residue that naming cannot reach — not a narration layer laid over working code.**

- **No inline comments.** Nothing inside a method body: no step markers (`// validate input`, `// now save`), no restatements of the line below, no section banners, no commented-out code, no `TODO`/`FIXME` left behind. A line that needs a comment to be understood needs a better name — extract it into a well-named local, constant, or private method instead.
- **The only permitted comment is a short doc comment on a method, class, or type** — XML doc in C#, Javadoc in Java, TSDoc in TS — **and only when the name genuinely cannot carry the meaning.** One or two sentences, stating *why* or *what contract holds*, never *how*.
- **That exception is for complex flows only**, and complexity means one of: a non-obvious business rule or invariant the code enforces but does not state; an ordering/concurrency/lifetime constraint a caller must respect; a deliberate deviation from the obvious implementation, with its reason; or a public API contract (what it throws, what it returns on the empty case, whether it mutates its input).
- **Never comment the trivial.** Properties, DTOs, records, getters/setters, constructors that only assign, single-expression methods, self-describing calls, obvious overrides — these get nothing. A doc comment that restates the signature (`/// Gets the user id.`) is noise and must be deleted.
- **Generated/scaffolded comments are removed**, including template headers and framework placeholders, unless a tool depends on them (analyzer suppressions, `#pragma`, `eslint-disable`, source-generator markers, serializer/OpenAPI annotations that produce output). Those are directives, not comments, and stay — with the reason for the suppression in the directive's own justification field where the tool supports one.
- **A stale comment is worse than none.** If the code moves and the comment does not, the comment is the defect — delete it rather than update it, unless it still earns its place under the rules above.
- The same rules apply to test code, with one addition: the test name and its Arrange/Act/Assert shape are the explanation. A comment is permitted only to record something the test cannot express — a linked defect id, an explicitly-instructed deviation from the house rules (per the Test code rules), or the source of a magic value the domain fixes.
- **In review**, an inline comment is a **minor** finding; a comment that is wrong, or that exists because the code is unclear, is **major** — the suggested fix is the rename or extraction, not a reworded comment.

## Planning

**When work is planned — a feature, a migration, an assessment, any multi-step build — the unit of work is a task.** Every skill, agent, command, and report in this library uses the same word for it.

- **A plan is one flat, ordered list of numbered tasks** (`T1…Tn`). No grouping layer sits above them: not phases, not slices, not stages, not milestones — neither as structure nor as vocabulary. An agent's own operating procedure is numbered in **steps**; the actions inside one task are its **steps**; the work items a plan hands out are **tasks**.
- **Workable order.** Each task can be started when its turn comes, because everything it needs was produced by a task above it. The project builds and its tests pass at every task boundary, so the plan can stop after any task. Every prerequisite that is not the task immediately above is written on the task as `Depends on:` and points backwards — a forward-pointing dependency is an ordering defect, not a note.
- **One deliverable per task** — the observable thing that exists when the task is done, stated as a result rather than an activity ("`POST /orders` accepts a valid order and returns `201` with the created id", not "implement the orders service"). It goes on the task as its first line, it is what `Done` means, and a task whose deliverable cannot be stated is not yet one task.
- **Capabilities are delivered, not just built.** Where the plan delivers something a person does, that capability's tasks run consecutively and the last of them makes it usable end to end — its deliverable is the behavioural sentence ("a member can book a session and then see it under their bookings").
- **In review**, a plan task with no stated deliverable, one that cannot be started at its position, or one that names its work a "phase" or a "slice", is a **major** finding.

## Pattern application

- Composition over inheritance, always.
- Repository pattern only when there is a real abstraction need. Do not wrap EF Core or Spring Data just to have a repository.
- CQRS only above a real complexity threshold. State the reason explicitly when applying it.
- One pattern per problem. Flag pattern stacking as a smell in reviews.
- Builder pattern for test data objects with 4+ fields.

## Test code rules

- Test names describe behavior, not implementation. `Should_X_When_Y` or `Given_Y_When_X_Then_Z`.
- One logical assertion per test. Multiple `Assert` calls are fine if they verify one behavior.
- **Every assertion states one expected condition — never an `OR`.** Assert `200`, never `200 or 204`; assert `400`, never `400 or 409`. The rule is not status-code-specific: field values, counts, error codes, and response-time budgets are asserted against the single value the test expects. An `OR` means the expectation was never pinned down — split it into one test per expected outcome, parameterize it, or find out which value is correct. The only exception is an explicit instruction to accept more than one value, and that instruction is recorded in the test.
- **Never swallow an error.** An unexpected exception fails the test loudly with a message naming what failed and carrying the evidence — the response body, the element, the value, the id. No empty `catch`, no catch-and-continue, no `catch` that ends without an assertion or a rethrow.
- **A test body contains no `try`/`catch` at all.** Every exception inside a test is either expected — and then it is asserted with the runner's throws-assertion (`Assert.ThrowsAsync<T>` / `assertThrows` / `await expect(...).rejects`), which is an assertion, not a catch — or unexpected, and then it must reach the runner untouched. Cleanup of resources the test created is **registered and run in the teardown hook**, never in an inline `try/finally`. `try/catch` belongs only in **helpers performing I/O** — the teardown deleting a record, a driver quit, a probe converting one named exception into a boolean — and even there it logs what it caught and never blanket-catches.
- **A failed deserialization says what actually broke.** The message names the offending field/path and the payload that caused it — a Zod `issues[].path`+`code`, a Jackson `MismatchedInputException` path, a `JsonException` property — and the raw body is attached to the report. A bare framework stack trace ("unexpected character at position 0") sends the reader to the debugger to learn what the test already knew.
- No conditional logic in tests (no `if`, no `for` driving assertions). If you need it, use parameterized tests.
- Page objects expose intent, not selectors. Method names describe user actions.
- Test data via builders or ObjectMother, not inline literals duplicated across tests.
- No `Thread.Sleep` / `await page.waitForTimeout`. Use explicit waits on conditions.
- Tests are independent. Any test can run alone, in any order.

## Review behavior

When reviewing code, return findings in this format:

```
| Severity | Location          | Issue                          | Suggested fix                |
|----------|-------------------|--------------------------------|------------------------------|
| major    | UserService.cs:42 | Service locator anti-pattern   | Inject IUserRepository       |
```

Severities:
- **blocker**: ships a bug, breaks the build, or violates a hard security rule
- **major**: design or correctness issue that will hurt the codebase soon
- **minor**: style, naming, or small inconsistency
- **nit**: optional preference

Do not rewrite code during review. Point to the fix and let the human apply it.

## When uncertain

- If a skill's instructions conflict with these global rules, the skill wins for its domain. Note the conflict in the response.
- If a user request conflicts with these rules, follow the user but call out the deviation once.
- If you don't have enough information to apply a pattern correctly, ask one clarifying question rather than guess.

## Version policy

Every skill is **version-aware**. The agent's first act on an existing project is version detection (TFM · JDK + Spring Boot BOM · Node major from `package.json` · React/Next major · the live DB's version probe), and every recipe is keyed to what's detected. **Never apply an up-level-only API to a down-level project, and never flag a down-level project for lacking one.**

Core stack versions:

- **.NET 10 primary / 8–9 supported** (EF Core major matches the TFM major; .NET 8 LTS ends Nov 2026).
- **Java 21 LTS + Spring Boot 3.x.**
- **Node 24 active LTS / 22 maintenance** — Node 20 is EOL since Apr 2026: flag it, don't target it.
- **React 19 primary / 18 tagged fallback** (an 18 pattern is correct for 18, not obsolete); **Next.js 15 primary / 14 fallback** (App Router primary; Pages Router legacy; Vite SPA + React Router 7 is the non-RSC lane).
- **Data engines** (probe the live server, never up-level it): PostgreSQL 18 / 15–17 · SQL Server 2025 / 2022 / 2019 / Azure SQL evergreen · MySQL 8.4 LTS / 9.x / 8.0 · MongoDB 8.0 LTS / 7.0 · Redis 8.x / 7.2–7.4 + Valkey fork · Elasticsearch 9.x / 8.x + OpenSearch 3.x fork; DynamoDB / Cosmos DB track SDK majors + creation-time-immutable constraints.

Domain specifics: **observability** stack-agnostic tooling tracks current releases — Grafana Alloy (not Promtail), Prometheus 3.x (native histograms stable), Mimir for scale. **DevOps** — managed runtimes lag the language, so pin to the newest runtime the platform actually offers for the project's major and never silently up-level the app to reach one; `infrastructure-as-code` and `kubernetes` are tool-/API-version bound, not stack-bound.

## Frontend code rules (Blazor)

- Components are **render-mode-agnostic** — `@rendermode` is set by the consumer, never hardcoded inside a reusable component.
- `[PersistentState]` (net10) / `PersistentComponentState` (net8/9) over manual prerender persistence — no double-fetch across prerender → interactive.
- **Semantic HTML before ARIA.** Reach for ARIA only when no semantic element fits.
- **No JS interop where C# suffices.** Interop is a last resort, disposed (`IAsyncDisposable` / `_module.DisposeAsync()`), and never called in `OnInitializedAsync`.
- Forms use `EditForm` + FluentValidation (or DataAnnotations); `OnValidSubmit`, `<ValidationMessage For>` per field.
- **CSS isolation** (`.razor.css` + `::deep`), no global-stylesheet dumping; a component library's theme system owns the library, your CSS layers on top.
- Every **interactive element and list/grid container ships a `data-testid`** — PascalCase dot-separated, static row locators, never numeric ids / GUIDs / array indexes / state values in the locator.
- **In-app navigation is a real anchor** (`href` / `NavLink`), never a click-handler-only `NavigateTo` button.
- Every **data region has explicit loading / loaded / failed states**; a failure never collapses into a blank section.
- **Background→UI updates only via `InvokeAsync`** (circuit / renderer sync context) — a background thread never touches component state directly.
- Constructor injection only; no static mutable state; async all the way; structured logging; HTTP through `IHttpClientFactory` typed clients.
- **bUnit for logic-bearing components, plain NUnit/xUnit for non-rendering logic** (dev-side — the split is mechanical: does it need a renderer?); E2E / user journeys belong to the `qa-ui-dotnet` peer.

## Frontend code rules (React)

- Components are **RSC by default; `'use client'` is opt-in per island** — never blanket a route client just because one leaf needs it (the App-Router analog of Blazor's "static SSR default, interactivity opt-in").
- Server Components fetch; Client Components interact — data crosses the boundary as serializable props; a Client Component composes server output via `children`, never by importing a Server Component.
- **Semantic HTML before ARIA.** Reach for ARIA only when no semantic element fits.
- Forms use **React Hook Form + Zod** (Server Actions + `useActionState` on App Router); field-level `aria-invalid` + error text; server errors mapped back with `setError`.
- **Follow-the-library styling** (MUI theme/`sx`); CSS Modules only for gaps; **never Tailwind atop MUI**. (When the library is shadcn/none the authority flips to Tailwind / CSS Modules — the reference file says which.)
- Every **interactive element and list/grid container ships a `data-testid`** — PascalCase dot-separated, static row locators, never array index / id / GUID / state value.
- **In-app navigation is a real `<Link href>`**, never an `onClick` `router.push` on a `<div>`.
- Every **data region has explicit loading / loaded / failed states** (Suspense + error boundary, or a three-state hook); a failure never collapses to blank, and never leaks `error.message`. **The failure is scoped to the response-dependent subtree** — search, filters, toolbars and headers keep rendering (only the rows/canvas/pane swaps to the failed body), and **every surfaced failure also raises a persistent top-right notification** that never auto-dismisses and closes only on its close button. A drifted/unparseable response is a *failed* state, never an empty one.
- **No server data in client stores** — RSC fetch / TanStack Query owns server state; Zustand/Context own client state.
- Keys are **stable domain ids**, never array index; **no `useEffect` to derive state** (compute in render); effects have exhaustive deps; subscriptions/timers/listeners are cleaned up; no browser reads (`window`/`localStorage`/`Date.now()`) during render (hydration mismatch).
- Strict TypeScript (`strict: true`), no `any`; async all the way; structured logging on the server; HTTP through a typed client / server util.
- **Vitest + RTL for logic-bearing components, plain Vitest for non-rendering logic** (dev-side — RTL if it renders, a `*.test.ts` on the function if it doesn't; query by role/label first; assert schema errors on `issues[].path`/`code`, never the message); E2E / user journeys and async-RSC rendering belong to the `qa-ui-typescript` peer.

## Backend code rules

- One pattern per problem — flag stacking (e.g. Repository + Unit-of-Work + Specification + Mediator + Decorator on one CRUD slice) as a smell in reviews, per the global Pattern-application rule.
- Constructor injection (or closures, in idiomatic TS) — never a service locator; no static/module-level mutable state; async all the way (never block on a `Task`/`Promise`, never `.Result`/`.Wait()`/`.then().catch()` chains for new code).
- Read 2–3 existing representative files before writing any new one; match the project's conventions (DI container, folder layout, naming) over a skill's defaults.
- Every public API gets a contract test before integration tests — coordinate with the matching `qa-api-<stack>` peer for **that** layer; a `be-*` agent produces the implementation only.
- **A `be-*` agent owns the unit tests for the logic it writes** (Step 3, the stack's `unit-testing` skill): in-process, no HTTP, no container, no real DB. The fence is the process boundary — a `WebApplicationFactory` / `@SpringBootTest` / supertest / Testcontainer moves the test into the `qa-api-<stack>` peer's lane. A unit test **never** stands in for a real-DB integration test, and an in-memory provider (EF `UseInMemoryDatabase`, H2, SQLite-for-Postgres, `mockDeep<PrismaClient>()`) is a false-negative machine, not a substitute.

## Repository map

Each top-level folder owns a domain, is **stack-first and domain-encapsulated** (a folder's skills are loaded only by its own agents), and ships as one or more marketplace plugins. Full per-skill detail is in [`docs/skills-catalog.md`](docs/skills-catalog.md).

| Folder | Domain | Plugin(s) |
|---|---|---|
| `qa/` | Test automation + manual test design, reporting, CI/CD, security scanning | `qa-java` · `qa-dotnet` · `qa-typescript` |
| `frontend/blazor/`, `frontend/react/` | Frontend dev stacks (+ `design/`, `auth/auth0-*`) | `fe-blazor` · `fe-react` |
| `design/` | Stack-agnostic aesthetic-craft layer | bundled into `fe-*` |
| `backend/` | Design-pattern + persistence dev stacks; planning (`be-planner`) + reverse-docs (`be-documenter`) | `be-dotnet` · `be-java` · `be-node` |
| `observability/` | OpenTelemetry → Grafana telemetry | bundled into `be-*` |
| `data/` | Database engineering (8 engines) | `data` |
| `devops/` | Platform/delivery + infra-security | `devops` |
| `security/` | Offensive (pentest + purple-team) and defensive/governance lanes | `penetration-testing` · `security-governance` |
| `business-analysis/` | Upstream requirements authoring + cross-feature reasoning | `business-analysis` |
| `training-data/` | LLM/VLM training-data engineering | `training-data` |
| `engineering-practices/` | Language-agnostic developer-workflow spine (`ep-*`) + audit lanes | bundled into all stack plugins |

**Under construction — ignore, do not upload to the remote:** `frontend/react-native/`, `auth/cognito-{blazor,react}`, `communication/`.

