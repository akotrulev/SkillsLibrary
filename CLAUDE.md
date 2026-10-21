# Global rules

These rules apply to every skill in this library unless a specific skill explicitly overrides them.

> **Full catalog:** the per-domain inventory of every skill, agent, and published plugin — plus the scope list and the 65-command slash surface — lives in [`docs/skills-catalog.md`](docs/skills-catalog.md). Consult it to learn what exists and which agent owns it. This file holds only the behavioral rules every skill follows.

## Role

You are a senior AI engineer and a senior automation QA engineer. You follow best practices in both disciplines: rigorous prompt / skill design, research-first authoring, and the QA-engineering norms encoded in the rest of this file (constructor injection, async-all-the-way, structured logging, real-DB integration tests over mocks, page objects expose intent, no `Thread.Sleep`, etc.).

## Stack defaults

- **Backend**: .NET — 10 primary, 8/9 supported (version-aware: detect the project's TFM and match; never up-level a down-level project)
- **Frontend SPA**: React 19 primary / 18 supported + TypeScript (strict mode), or Blazor when specified
- **JVM backend**: Java 21 + Spring Boot 3.x
- **Node backend**: Node 24 (active LTS; 22 maintenance — Node 20 is EOL since Apr 2026) + TypeScript + NestJS or Express
- **Python worker**: Python 3.13 primary / 3.12 and 3.14 supported — only for the one isolated upload-processing worker (Pillow, rembg, VTracer); uv + ruff + mypy `--strict`, pydantic at the boundary
- **Mobile**: React Native + Expo primary (Expo Router, development builds, EAS) · Swift / SwiftUI (iOS) · Kotlin / Jetpack Compose (Android), with a Kotlin Multiplatform lane — each its own `mobile-*` plugin under `mobile/`
- **Test runners**: NUnit (.NET), TestNG (Java), Vitest or Jest (TS), pytest (Python), Playwright (UI), Appium (mobile); dev-side in mobile apps — Swift Testing (iOS), JUnit 4 + Robolectric (Android), Jest + RNTL (React Native)
- **JVM build tool**: Gradle (Kotlin DSL) for new projects
- **Auth**: Auth0 — Authorization Code + PKCE for SPAs, Client Credentials for service-to-service
- **Cloud**: Azure DevOps for pipelines; AWS or Azure for hosting depending on project
- **Observability**: OpenTelemetry → Grafana stack (Loki for logs, Prometheus for metrics, Tempo for traces)
- **Reporting**: Allure for test results

## Simplicity (KISS)

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

**The plan document format is a contract:** [`engineering-practices/writing-plans/references/plan-format.md`](engineering-practices/writing-plans/references/plan-format.md). It is the shape the Plan Queue VS Code plugin queues, and `dev:plan-feature`, `dev:plan-delivery` and `dev:plan-session-budget` all produce it. Read it before writing a plan; the rules below are the parts that bind everywhere else in this library.

- **One self-contained file.** The plan carries the context, the decisions, the tasks **and** one paste-ready prompt per task in a closing `## Prompts — one per task` section. There is no companion prompt or handoff file — the document is queued and handed over whole.
- **The narrative comes first; the tasks come last.** `## 1. What already exists, and what is missing` is a `| Need | Today | Gap |` table, and every task traces to a row of it. Then the sections that decide the work, then `## Decisions` (`D1…Dn`, each with what it costs) and the answered/open questions, then the tasks.
- **A plan is one flat, ordered list of tasks**, ids carrying a letter prefix for the family of work and a number within it (`C1`, `B1…Bn`, `F1…Fn`, `H1`). No grouping layer sits above them: not phases, not slices, not stages, not milestones — neither as structure nor as vocabulary. An agent's own operating procedure is numbered in **steps**; the actions inside one task are its **steps**; the work items a plan hands out are **tasks**.
- **Workable order.** Each task can be started when its turn comes, because everything it needs was produced by a task above it. Every prerequisite that is not the task immediately above is written on the task as `Depends on:` and points backwards — a forward-pointing dependency is an ordering defect, not a note.
- **One deliverable per task** — the observable thing that exists when the task is done, stated as a result rather than an activity ("`POST /orders` accepts a valid order and returns `201` with the created id", not "implement the orders service"). It is what `Done` means, and a task whose deliverable cannot be stated is not yet one task.
- **One stack and one agent per task**, plus a `**Budget:**` line with its drivers itemized. A task touching the API tree and a web or app tree is two tasks, at any size; a task is split along a seam **inside** its own stack, never by handing part of it to another. Merge consecutive same-stack work until it would exceed the budget target — the goal is the **fewest sessions**, not the smallest tasks.
- **The plan gates once, in its last runnable task.** Every task before it writes its code and its tests, commits, and stops: no build, no test run, no lint, no format check, no typecheck, no eval, no integration or e2e suite. Each carries `**Gate: none**` naming what not to run — or, in a test-first plan, `**Gate: own tests**`: the one filtered command that runs the tests that task writes or must turn green, and nothing else (`plan-format.md` §5). The last runnable task runs the whole set for every task in the plan together — ending with the **coverage floor** (Test code rules) when the plan writes code — **fixes what it finds rather than handing it back** (a failure there may belong to any task above it), and carries the documentation and close-out. **The cost, accepted and stated once in every plan: intermediate commits are ungated, so the tree is not known to build at every task boundary and a plan cannot be stopped halfway and trusted.**
- **Prompts are living text.** A task that lands something different from what the plan predicted rewrites the prompt blocks below it before it stops, in place, with no changelog appended; **a task's own prompt is deleted when it lands** (the live prompt set is the progress indicator); and **a prompt that cannot be written until an earlier task lands is written by that task** — never guessed at plan time.
- **Progress lives in the plan.** The header `**Status:**` line (what is built, what is next, what is built but **unverified**) and a dated `**As built:**` note on each landed task, with the `file:line` or command output that proves it. Append-only; never edited backwards.
- **`docs/plans/` is what is in flight; `docs/plans/implemented/` is what landed.** The task that deletes the **last** prompt block rewrites the `Status:` line one final time and moves the plan there — same filename, same number, in that task's own commit; a `solution-planner` pack moves its whole initiative folder with every artifact in it. A plan still holding a blocked task's block **does not** move, because the live folder answers "what is being built" by being listed. A plan's `NNN` is taken from the high-water mark across **both** folders — a moved plan's number stays spent — and a moved plan is never edited or deleted: it is the record of why the code looks the way it does, and later plans cite its `Decisions`.
- **Capabilities are delivered, not just built.** Where the plan delivers something a person does, that capability's tasks run consecutively and the last of them makes it usable end to end — its deliverable is the behavioural sentence ("a member can book a session and then see it under their bookings"). The one exception is a plan **one operator will execute in back-to-back batches**: there the tasks are batched by executor and file tree (contracts first, then backend module by module, then frontend area by area), a capability's pieces are spread across its batches, and the plan states which batch makes each capability usable. Which shape applies is decided from how the plan will be run — an answer, never an inference.
- **Test-first is the order wherever a plan delivers an API surface or a journey.** Everything both sides bind to comes first — the schema, the contract, the shared types and stubs that answer `501 not-implemented` — then the acceptance tests written against them by `qa-*` agents (the `Q` family, red on the stubs), then the backend, shared-package, frontend and mobile tasks, each turning its named acceptance tests green. **The acceptance tests are read-only to every later task except the gate:** never edit, skip, delete or weaken one; a test believed wrong is a dated `D<n>` and stays red until the gate resolves it with the user (`plan-format.md` §4–§5).
- **In review**, these are **major** findings: a task with no stated deliverable, one that cannot be started at its position, one that names its work a "phase" or a "slice", one that names two stacks or no agent, an intermediate task that runs more than its own tests, a plan with no single gate task, and a prompt block that was guessed instead of left to the task that unblocks it.

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
- **Code an agent writes ships with unit tests covering ≥ 80% of its branches.** The scope is the change, never the repo: a file the change created counts whole; in a file that already existed, the methods it changed. Tests are designed branch by branch — every `if`/`else` arm, `switch` case and default, ternary, `??`/`?.`, short-circuit operand, guard return, `catch`, and loop run zero and many times gets a test that asserts its effect — so the measured 80% is a floor with slack for branches no honest test reaches. **Only an asserting test counts:** one written to move the number is a **major** finding, and mutation score (`test-quality-check`) is what catches it. Files the stack's selection matrix does not test (DTOs, configuration, DI registration, migrations, generated code) are left out of the measurement **by name** — never by lowering the number or by an exclusion marker on code with behavior. A plan's gate measures it per stack (`plan-format.md` §5); where the toolchain reports no branches (Swift), the floor is 80% of lines. Repo-wide coverage is still never a target.

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
- **Design facts come from the vendored corpus.** `design/ui-ux-pro-max` (imported from `nextlevelbuilder/ui-ux-pro-max-skill`, pinned in [`design/ATTRIBUTIONS.md`](design/ATTRIBUTIONS.md)) is the **source of truth** for which style, palette, font pairing, UX guideline, icon, chart type, motion preset, landing pattern or per-stack UI convention applies. Where it and a `design/*` skill — or these global rules — disagree on such a fact, **the corpus wins**; the prose skill supplies only the judgment layered on top. Query it before deciding, and cite the row. It settles facts, not process: the code-quality, comment, planning, and test rules above are unaffected.
- If a user request conflicts with these rules, follow the user but call out the deviation once.
- If you don't have enough information to apply a pattern correctly, ask one clarifying question rather than guess.

## Version policy

Every skill is **version-aware**. The agent's first act on an existing project is version detection (TFM · JDK + Spring Boot BOM · Node major from `package.json` · React/Next major · the live DB's version probe), and every recipe is keyed to what's detected. **Never apply an up-level-only API to a down-level project, and never flag a down-level project for lacking one.**

Core stack versions:

- **.NET 10 primary / 8–9 supported** (EF Core major matches the TFM major; .NET 8 LTS ends Nov 2026).
- **Java 21 LTS + Spring Boot 3.x.**
- **Node 24 active LTS / 22 maintenance** — Node 20 is EOL since Apr 2026: flag it, don't target it.
- **Python 3.13 primary / 3.12, 3.14 supported** — the ML worker stays on 3.13 until `uv lock` resolves every wheel (onnxruntime, rembg, vtracer) for 3.14; Pillow 12 primary / 11 supported. Never up-level `requires-python`.
- **Playwright: Node 1.64 / Java, .NET and Python 1.63** (Java and .NET stay on 1.63 until their 1.64 packages publish; `tools/qa-version-check.py` enforces the pins). A 1.64-only API (`locator.within()`, `page.webmcp`, `getByRef`) is taught on the TypeScript lane only and is never taught on a 1.63 lane; the Java and .NET skills teach the 1.63 form plus a "from 1.64" line.
- **Appium 3 primary / 2 supported** — Appium 3.8.0 with `java-client` 11 / `Appium.WebDriver` 9 / WebdriverIO 10 (Node ≥ 22.19); a device cloud still on Appium 2 stays on `java-client` 10.x, `Appium.WebDriver` 8.x or WebdriverIO 9.x. Maestro is a TypeScript-lane alternative to Appium.
- **React 19 primary / 18 tagged fallback** (an 18 pattern is correct for 18, not obsolete); **Next.js 15 primary / 14 fallback** (App Router primary; Pages Router legacy; Vite SPA + React Router 7 is the non-RSC lane).
- **React Native / Expo: SDK 57 primary** (RN 0.86, React 19.2, Node ≥ 22.13) **/ SDK 55–56 supported / SDK 54 the floor** (last SDK where the legacy architecture can be on — the migration bridge only; below 54 is a finding plus a migration run, never authored for). SDK 58 (beta) becomes primary the day it ships stable. New-Architecture only since RN 0.82.
- **iOS / Swift: Xcode 27 + Swift 6.4 + iOS 27 SDK primary / Xcode 26.x + Swift 6.2–6.3 supported; deployment target iOS 17 primary / iOS 16 supported** (below 16 is the UIKit lane only, flagged). Swift 6 language mode for new modules; Swift 5-mode modules migrate one module at a time. Never raise a deployment target as a side effect.
- **Android / Kotlin: Kotlin 2.4 + AGP 9.4 + Gradle 9.6 primary / Kotlin 2.0–2.3 and AGP 8.x supported in brownfield; compileSdk 37, targetSdk 36, minSdk 24; Compose BOM 2026.09; JDK 21 toolchain (17 minimum).** Play requires new apps and updates to target API 36.
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
- **bUnit for logic-bearing components, plain NUnit/xUnit for non-rendering logic** (dev-side — the split is mechanical: does it need a renderer?), to the ≥ 80% branch floor in Test code rules; E2E / user journeys belong to the `qa-ui-dotnet` peer.

## Frontend code rules (React)

- Components are **RSC by default; `'use client'` is opt-in per island** — never blanket a route client just because one leaf needs it (the App-Router analog of Blazor's "static SSR default, interactivity opt-in").
- Server Components fetch; Client Components interact — data crosses the boundary as serializable props; a Client Component composes server output via `children`, never by importing a Server Component.
- **Semantic HTML before ARIA.** Reach for ARIA only when no semantic element fits.
- Forms use **React Hook Form + Zod** (Server Actions + `useActionState` on App Router); field-level `aria-invalid` + error text; server errors mapped back with `setError`.
- **One styling authority.** The default lane is **shadcn/ui, where the authority is Tailwind** (utilities + the CSS-variable token layer); CSS Modules only for the rare escape hatch. On a project already built on a CSS-in-JS library (MUI/Mantine/Chakra) that library's theme/`sx` **is** the authority and stays so — **never bolt Tailwind on top**. The reference file says which lane applies.
- Every **interactive element and list/grid container ships a `data-testid`** — PascalCase dot-separated, static row locators, never array index / id / GUID / state value.
- **In-app navigation is a real `<Link href>`**, never an `onClick` `router.push` on a `<div>`.
- Every **data region has explicit loading / loaded / failed states** (Suspense + error boundary, or a three-state hook); a failure never collapses to blank, and never leaks `error.message`. **The failure is scoped to the response-dependent subtree** — search, filters, toolbars and headers keep rendering (only the rows/canvas/pane swaps to the failed body), and **every surfaced failure also raises a persistent top-right notification** that never auto-dismisses and closes only on its close button. A drifted/unparseable response is a *failed* state, never an empty one.
- **No server data in client stores** — RSC fetch / TanStack Query owns server state; Zustand/Context own client state.
- Keys are **stable domain ids**, never array index; **no `useEffect` to derive state** (compute in render); effects have exhaustive deps; subscriptions/timers/listeners are cleaned up; no browser reads (`window`/`localStorage`/`Date.now()`) during render (hydration mismatch).
- Strict TypeScript (`strict: true`), no `any`; async all the way; structured logging on the server; HTTP through a typed client / server util.
- **Vitest + RTL for logic-bearing components, plain Vitest for non-rendering logic** (dev-side — RTL if it renders, a `*.test.ts` on the function if it doesn't; query by role/label first; assert schema errors on `issues[].path`/`code`, never the message), to the ≥ 80% branch floor in Test code rules; E2E / user journeys and async-RSC rendering belong to the `qa-ui-typescript` peer.

## Mobile code rules

All three stacks:

- **Platform conventions first.** Native navigation, native controls, system text styles. An app never
  imitates the other platform or the web. Design facts come from `design/ui-ux-pro-max`
  (`--stack react-native | swiftui | jetpack-compose`).
- **The UI thread never blocks** — no disk, network, database or heavy compute on the main thread (or
  the RN JS thread). A frame budget is a correctness rule.
- **Lifecycle is part of the requirement.** Work a screen starts is cancelled when the screen goes;
  returning to the foreground revalidates instead of showing stale data; Android process death restores
  state; nothing assumes the app stays foregrounded mid-write.
- **Every data region has loading / loaded / failed states, plus stale and offline** — failure scoped to
  the response-dependent subtree, one persistent user-dismissed error banner inside the safe area,
  offline told apart from a server error, every request inside a timeout budget.
- **Secrets never ship in the binary or bundle** — `EXPO_PUBLIC_*`, `Info.plist`, `BuildConfig` and
  resources are public. Tokens live only in Keychain / Keystore-backed storage; nothing sensitive in
  logs, `UserDefaults`, `SharedPreferences` or `AsyncStorage`.
- **TLS only.** An ATS or cleartext exception carries a recorded reason. Deep links, push payloads and
  intents are untrusted input, validated before they route.
- **Permissions are asked in context, at the moment of use, after a pre-prompt; the denied path is a
  working screen.**
- **Accessible by default** — every interactive element labelled, touch targets ≥ 44 pt / 48 dp, text
  scales with the system setting and is never locked, Reduce Motion honoured, no state by colour alone.
- **Every interactive element and list container carries the stack's test id** — `testID` (RN),
  `accessibilityIdentifier` (iOS), `Modifier.testTag` with `testTagsAsResourceId` or `android:id`
  (Android) — PascalCase dot-separated and static, **never the accessibility label**.
- **Store rules are code rules** — privacy manifest and Required Reason APIs, in-app account deletion,
  permission declarations, target API level. `mobile/_shared/store-compliance` owns them.
- Constructor / initializer injection only; no service locator; no static mutable state; async all the
  way — never block on a result.
- **Dev-side tests** for the logic the agent writes (Swift Testing · JUnit + fakes · Jest + RNTL), to
  the ≥ 80% floor in Test code rules — branches, or lines on Swift, where Xcode reports no branches;
  device journeys and E2E belong to the `qa-mobile-<stack>` peer.
- Never up-level a project's toolchain, SDK or deployment target as a side effect of other work.

Per stack:

- **React Native:** Expo is the framework — Expo Router, development builds, CNG; native changes go in
  config plugins, never hand edits to generated `ios/` / `android/`. New Architecture only. Text only
  inside `<Text>`. Unbounded lists are virtualized (FlashList / Legend List). Animation runs on the UI
  thread (Reanimated), transform/opacity only. Server state lives in TanStack Query, never in a client
  store.
- **iOS (Swift):** Swift 6 mode with Approachable Concurrency for new modules — `@MainActor` default in
  app/UI modules, `nonisolated` in packages, `@concurrent` for CPU work; no `@unchecked Sendable` or
  `nonisolated(unsafe)` without a written justification; no force unwrap outside tests. SwiftUI first,
  UIKit where the codebase is UIKit. `@Observable` over `ObservableObject` on iOS 17+. `os.Logger` only.
- **Android (Kotlin):** Compose first. One `uiState: StateFlow` per screen ViewModel, collected with
  `collectAsStateWithLifecycle`; no ViewModel-to-UI events. Structured concurrency — no `GlobalScope`,
  dispatchers injected. No `!!` outside tests. KSP, never kapt. Room / DataStore over raw SQLite /
  `SharedPreferences`. R8 full mode and a Baseline Profile in release builds.

## Backend code rules

- One pattern per problem — flag stacking (e.g. Repository + Unit-of-Work + Specification + Mediator + Decorator on one CRUD slice) as a smell in reviews, per the global Pattern-application rule.
- Constructor injection (or closures, in idiomatic TS) — never a service locator; no static/module-level mutable state; async all the way (never block on a `Task`/`Promise`, never `.Result`/`.Wait()`/`.then().catch()` chains for new code).
- Read 2–3 existing representative files before writing any new one; match the project's conventions (DI container, folder layout, naming) over a skill's defaults.
- **Instrument as you build, on a telemetry base that lands first.** A plan's foundation wires the OpenTelemetry SDK, structured logging and a local Grafana stack (`deploy/local/`); every task that adds an entry point, an outbound call, a background job or a business event adds its own logs at the decision points, a span around the operation and a metric per business event, and names them in its `As built` note — the gate's telemetry smoke proves they arrive.
- Every public API gets a contract test before integration tests — coordinate with the matching `qa-api-<stack>` peer for **that** layer; a `be-*` agent produces the implementation only.
- **A `be-*` agent owns the unit tests for the logic it writes** (Step 3, the stack's `unit-testing` skill), to the ≥ 80% branch floor in Test code rules: in-process, no HTTP, no container, no real DB. The fence is the process boundary — a `WebApplicationFactory` / `@SpringBootTest` / supertest / Testcontainer moves the test into the `qa-api-<stack>` peer's lane. A unit test **never** stands in for a real-DB integration test, and an in-memory provider (EF `UseInMemoryDatabase`, H2, SQLite-for-Postgres, `mockDeep<PrismaClient>()`) is a false-negative machine, not a substitute.

## Repository map

Each top-level folder owns a domain, is **stack-first and domain-encapsulated** (a folder's skills are loaded only by its own agents), and ships as one or more marketplace plugins (21 in all). **Bundle within a category, depend across categories:** sharing inside `qa-*`, `fe-*`, `mobile-*` or `be-*` is bundled, and anything several categories use lives in one plugin they declare in `dependencies` (`dev`, `design`). Full per-skill detail is in [`docs/skills-catalog.md`](docs/skills-catalog.md).

| Folder | Domain | Plugin(s) |
|---|---|---|
| `qa/` | Test automation + manual test design, reporting, CI/CD, security scanning | `qa-java` · `qa-dotnet` · `qa-typescript` |
| `frontend/blazor/`, `frontend/react/` | Frontend dev stacks (+ `design/`, `auth/auth0-*`) | `fe-blazor` · `fe-react` |
| `mobile/` | Mobile dev stacks — React Native (Expo), iOS (Swift), Android (Kotlin + KMP) + the shared store-compliance / security / release / observability / in-app-purchases layer (+ `design/`, `auth/auth0-{react-native,ios,android}`) | `mobile-react-native` · `mobile-ios` · `mobile-android` |
| `design/` | Stack-agnostic aesthetic-craft layer | `design` (a dependency of `fe-*` and `mobile-*`) |
| `backend/` | Design-pattern + persistence dev stacks; the sandboxed Python upload worker (`backend/python/`); planning (`solution-planner`) + reverse-docs (`be-documenter`) | `be-dotnet` · `be-java` · `be-node` · `be-python` |
| `observability/` | OpenTelemetry → Grafana telemetry | bundled within the category into `be-dotnet` · `be-java` · `be-node` |
| `data/` | Database engineering (8 engines) | `data` |
| `devops/` | Platform/delivery + infra-security | `devops` |
| `security/` | Offensive (pentest + purple-team) and defensive/governance lanes | `penetration-testing` · `security-governance` |
| `business-analysis/` | Upstream requirements authoring + cross-feature reasoning | `business-analysis` |
| `training-data/` | LLM/VLM training-data engineering | `training-data` |
| `tooling/` | Agent-drivable surfaces over a project — capability contract → MCP server / CLI | `tooling` |
| `engineering-practices/` | Language-agnostic developer-workflow spine + audit lanes; also `backend/_shared` planning and documentation | `dev` (a dependency of `qa-*`, `fe-*`, `mobile-*`, `be-*`, `devops`, `business-analysis`) |

**Under construction — ignore, do not upload to the remote:** `auth/cognito-{blazor,react}`, `communication/`.

