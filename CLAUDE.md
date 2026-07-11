# Global rules

These rules apply to every skill in this library unless a specific skill explicitly overrides them.

> **Scope:** The `qa/` folder, `frontend/blazor/` (with the `design/` and `auth/auth0-blazor` skills it depends on), the `data/` folder (8 per-engine skills + 4 cross-engine `_shared` skills + the `data-architect` agent), and the 10 in-scope `engineering-practices/` developer-workflow skills (the `ep-*` set — the 8 core skills plus `ep-subagent-driven-development` and `ep-dispatching-parallel-agents`) are ready for use and the remote. The 2 excluded `engineering-practices/` skills (`requesting-code-review`, `receiving-code-review`) and all other top-level folders are under construction — ignore them, and do not upload them to the remote yet.

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

## Code quality rules

- Constructor injection only. No service locator, no property injection.
- No static mutable state. Constants are fine.
- Async all the way down. Never `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()` in production code.
- Structured logging only. Use message templates, never string interpolation in log calls.
- No secrets in code, `appsettings.json`, or `application.yml`. Use env vars + secret store.
- Every public API has a contract test before integration tests are added.
- Nullable reference types enabled in .NET. `strict: true` in TypeScript.
- Prefer immutability. Records in C#, `readonly` in TS, `final` in Java where it fits.

## Pattern application

- Composition over inheritance, always.
- Repository pattern only when there is a real abstraction need. Do not wrap EF Core or Spring Data just to have a repository.
- CQRS only above a real complexity threshold. State the reason explicitly when applying it.
- One pattern per problem. Flag pattern stacking as a smell in reviews.
- Builder pattern for test data objects with 4+ fields.

## Test code rules

- Test names describe behavior, not implementation. `Should_X_When_Y` or `Given_Y_When_X_Then_Z`.
- One logical assertion per test. Multiple `Assert` calls are fine if they verify one behavior.
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

## QA skills catalog

The `qa/` folder is the most built-out section. When a request matches one of these, prefer the matching skill over improvising. The folder is organized **stack-first** so a new project copies one stack folder plus the agnostic ones, and **domain-encapsulated**: each top-level folder owns a domain, and *its skills are loaded only by its own agents*. Stack agents author + verify; test design (`qa/manual/`), reporting (`qa/reporting/`), CI/CD (`qa/cicd/`), and security (`qa/_shared/agents/qa-security`) are **peer agents** the orchestrator (you, or the human) invokes alongside the stack agent — a stack agent never reaches into another folder's skills.

- `qa/{java,dotnet,typescript}/skills/{node}/SKILL.md` — the per-stack skill implementations (C# → `dotnet/`); pick the stack from the Stack defaults above or the user's project. Tool-bound skills exist only under the stack(s) the tool supports (e.g. `performance/nbomber` only in `dotnet/`). One-of-N tool families (messaging, email, network-monitoring, visual-regression, accessibility, file-storage) are **one registered skill per family**: SKILL.md routes via a decision matrix, the per-tool deep dive lives in `references/<tool>.md`. Oversized skills keep their deep sections in `references/details.md`.
- `qa/{java,dotnet,typescript}/agents/` — phased orchestrator agents for that stack (senior automation QA per focus: api / ui / mobile / performance / llm / bdd); they load **only the stack's own skills** (foundations → author → deep verification → review), and name the manual / reporting / cicd / security agents as related peers to run separately. The **`qa-llm-{stack}`** agent owns LLM-app eval suites end-to-end (choose spine → build dataset → author property/rubric/grounding assertions → stochastic pass-rate + red-team → review) and loads `llm-app-testing` (+ `data-driven-testing`, `api-dto-writer`, `auth0-test-tokens`).
- The **`qa-bdd-{stack}`** agent owns Gherkin/BDD **living-documentation** UI suites (web + mobile) end-to-end: **consume** a `qa-manual-test-designer` test-case suite → canonicalize steps into reusable declarative `.feature` files (Background, Scenario Outline, tags) → generate step definitions split by domain → implement each step against **existing page objects** → review. It loads the cross-stack `qa/_shared/bdd/gherkin-authoring` plus its stack's `bdd-project-scaffold` / `bdd-step-bindings` / `bdd-reviewer` and the stack's page-object/ui skills; the BDD framework is per stack — **Reqnroll** (dotnet) · **Cucumber-JVM** (java) · **playwright-bdd** web + **CucumberJS+WebdriverIO** mobile (typescript). Names `qa-manual-test-designer` (test cases), `qa-ui-{stack}` / `qa-mobile-{stack}` (page objects), `qa-reporting-{stack}`, `qa-cicd-{stack}` as peers.
- `qa/manual/` — language-agnostic process skills: `test-basis-analyzer`, `test-case-writer`, `test-design-techniques`, `bug-report-writer`, `exploratory-charter-writer`, `test-strategy`, `quality-metrics`; loaded only by `qa/manual/agents/qa-manual-test-designer` — the phased agent that turns documentation into a full manual test-case suite.
- `qa/reporting/{java,dotnet,typescript}/skills/` — `allure-reporting` (Allure results) + `flaky-test-quarantine` (tag/quarantine tests by finding); per-stack agents `qa/reporting/agents/qa-reporting-{java,dotnet,typescript}` wire Allure, tag tests, and detect/quarantine flakes.
- `qa/cicd/` — `ci-pipelines` per stack (`qa/cicd/{java,dotnet,typescript}/skills/ci-pipelines`, a one-of-N family routing to `references/<host>.md`: github-actions · azure-pipelines · gitlab-ci) + the language-agnostic `qa/cicd/ci-conventions`; per-stack agents `qa/cicd/agents/qa-cicd-{java,dotnet,typescript}` build the pipeline (shard matrix, Allure-publish step, perf gate, OIDC secrets).
- `qa/_shared/` — cross-stack technical rules referenced by stack skills (`contract-testing-pact`, `performance`, `security` + the language-agnostic `security-testing/*` scanner skills, and `bdd/gherkin-authoring` — the framework-agnostic Gherkin engine loaded by every `qa-bdd-{stack}` agent) plus `webapp-testing` (the one Python skill, Anthropic-provided import); also `qa/_shared/agents/qa-security` — the cross-stack, OWASP-mapped security orchestrator (loads the `_shared` scanner skills + the project's stack-native security siblings, incl. `dependency-scanning`, phase by phase).

New-project setup = copy `qa/<stack>/` + `qa/manual/` + `qa/reporting/` + `qa/cicd/` + `qa/_shared/`.

**Authoring**
- `api-test-author/generator` · `api-test-author/reviewer` — write / review API tests (RestAssured+TestNG · NUnit+RestSharp · Vitest+fetch+Zod) — java · dotnet · typescript
- `api-test-author/playwright` — API tests through Playwright's `APIRequestContext` **instead of** the generator's HTTP stack, when the project already runs Playwright for UI (one dependency/runner/report; context-per-identity auth, same DTO+Client+Test layering) — java · dotnet · typescript
- `api-client-writer` — typed API clients — java · dotnet · typescript
- `api-dto-writer` — request/response DTOs — java · dotnet · typescript
- `ui-test-author/playwright` · `ui-test-author/selenium` · `ui-test-author/appium` · `ui-test-author/reviewer` — write / review UI + mobile tests — java · dotnet · typescript
- `page-object-architect` — page-object architecture (intent, not selectors) — java · dotnet · typescript
- `pom-builder` — extract/update a POM from a live URL or HTML via Playwright MCP (`data-testid`-first locators, `missing-testids.md` dev-team report) — java · dotnet · typescript
- `appium-explore` — drive the live app on a device/emulator via the Appium MCP (`appium-mcp`); enumerate elements, accessibility-id-first locators, `missing-testids.md` report (the mobile counterpart of `pom-builder`) — java · dotnet · typescript
- `appium-page-object` — emit/update a `BaseAppiumPage`/`BasePage` screen object from an `appium-explore` inventory; defers conventions to `ui-test-author/appium` — java · dotnet · typescript
- `api-test-author/graphql` · `api-test-author/grpc` — protocol-specific API tests (assert the `{data,errors}` envelope · the gRPC status) — java · dotnet · typescript
- `contract-testing-pact` — Pact consumer/provider contracts — java · dotnet · typescript · shared rules at `qa/_shared/contract-testing-pact`
- `performance/k6` (typescript) · `performance/nbomber` (dotnet) · `performance/gatling` (java) — load testing (tool-bound stacks); shared rules at `qa/_shared/performance`

**BDD / living documentation** (owned by the `qa-bdd-{stack}` agents; UI web + mobile)
- `qa/_shared/bdd/gherkin-authoring` — the framework-agnostic engine that turns a `test-case-writer` suite into reusable, **declarative** `.feature` files: case→Scenario, shared Setup→**Background**, Test Data→**Scenario Outline + Examples**, Priority/Type/AC→**tags**, dedupe to a reusable **Step Catalog**, Cleanup→hook handoff (`references/gherkin-style-guide.md` = canonical Cucumber style). Cross-stack; loaded by every `qa-bdd-{stack}` agent
- `bdd-project-scaffold` — wire the BDD framework onto an existing UI/mobile project (packages, runner, features dir, **per-scenario state + lifecycle hooks with teardown**): Reqnroll.NUnit + MS-DI `[ScenarioDependencies]` (dotnet) · Cucumber-JVM + JUnit 5 Platform `@Suite` + PicoContainer (java) · playwright-bdd `defineBddConfig`/`bddgen` web + CucumberJS + `@wdio/appium-service` mobile (typescript) — java · dotnet · typescript
- `bdd-step-bindings` — `.feature` → step definitions **split by domain**, Cucumber Expressions, shared state by constructor injection (Reqnroll `ScenarioState`) / PicoContainer `TestContext` / Playwright **fixtures** (web) or CucumberJS **World** (mobile), then **implement each step against existing page objects** (mechanics + waits live in the POM, assertions in `Then`); typescript is one-of-N (`references/playwright-bdd.md` web · `references/cucumberjs-appium.md` mobile) — java · dotnet · typescript
- `bdd-reviewer` — audit both surfaces: Gherkin smells (imperative/UI-coupled steps, missing Background, conjunction steps, duplicated steps, lost AC traceability) + binding correctness (DI vs static state, no selectors/waits in steps, lifecycle teardown, Cleanup-as-hook) — java · dotnet · typescript

**Verification inside tests**
- `db-testing/client` · `db-testing/testcontainers` · `db-testing/query-author` — connect/seed/assert/clean, container lifecycle, safe assertion SQL — java · dotnet · typescript
- `email-testing` — capture/assert email; one skill, tool picked inside via `references/` (mailpit local sink · mailosaur hosted inbox · gmail-imap real IMAP · sendgrid-sandbox) — java · dotnet · typescript
- `network-monitoring` — request mocking/assertion; one skill, layer picked inside via `references/` (playwright-routes · cdp throttling · out-of-browser proxy) — java · dotnet · typescript
- `messaging-testing` — produce/consume/assert against brokers; one skill, broker picked inside via `references/` (kafka · sqs · rabbitmq · service-bus) — java · dotnet · typescript
- `file-storage-testing` — object-storage assertions; one skill, store picked inside via `references/` (s3/LocalStack · azure-blob/Azurite) — java · dotnet · typescript
- `websocket-sse-testing` — real-time WS + SSE assertions — java · dotnet · typescript

**Grids & access**
- `cloud-grid-config` — BrowserStack / Sauce / LambdaTest / Device Farm wiring — java · dotnet · typescript
- `auth0-test-tokens` — M2M / ROPG / device-code tokens for test users — java · dotnet · typescript

**Visual, quality gates & test data**
- `visual-regression` — pixel-diff / hosted visual review; one skill, tool picked inside via `references/` (playwright-snapshots · percy · applitools) — java · dotnet · typescript
- `accessibility-testing` — a11y scans + budgets; one skill, tool picked inside via `references/` (axe-playwright · lighthouse-ci) — java · dotnet · typescript
- `responsive-testing` — breakpoint/viewport layout testing via Playwright: breakpoints read from the app's own token/theme source (never guessed), BVA at bp−1/bp per breakpoint, structural `boundingBox` assertions (variant swap both sides, alignment, column reflow, no overlap, no horizontal overflow), live-resize both directions; pairs with `visual-regression`, loaded by `qa-ui-{stack}` Phase 3 — java · dotnet · typescript
- **`security-testing`** (OWASP-mapped family; backbone at `qa/_shared/security`, orchestrated by the `qa-security` agent at `qa/_shared/agents/`):
  - **Language-agnostic scanner gates** (single skills at `qa/_shared/security-testing/` — most security tools are Docker/CLI binaries, so they are NOT triplicated): `zap-automation-framework` (active/AF DAST + API scan), `sast` (Opengrep/Semgrep), `secrets-scanning` (Gitleaks + TruffleHog), `container-iac-scanning` (Trivy + SBOM, A03 supply chain), `api-fuzzing` (Schemathesis), `nuclei` (template/CVE), `tls-scanning` (sslyze + testssl.sh)
  - **Stack-native skills** — `security-testing/access-control-testing` (functional **BOLA/IDOR/BFLA** authz matrix — the OWASP scanner blind spot; A01:2025 / API1·3·5:2023), `security-testing/zap-baseline` (passive DAST), `security-testing/dependency-scanning` (SCA) — java · dotnet · typescript
- `i18n-testing` — locale-pinned assertions by key, pseudo-localization, RTL — java · dotnet · typescript
- `data-driven-testing` — parameterized test matrices — java · dotnet · typescript
- `synthetic-monitoring` — production probes from test code — java · dotnet · typescript
- `chaos-testing` — Toxiproxy fault injection, assert graceful degradation — java · dotnet · typescript
- `feature-flag-testing` — pin flag state in-process (OpenFeature `InMemoryProvider` / LaunchDarkly `TestData`), test BOTH sides of every flag, targeting via the evaluation context — java · dotnet · typescript
- `llm-app-testing` — property/rubric/grounding assertions for LLM features (chatbot/RAG/summarizer/extraction/agent); a one-of-N spine family: SKILL.md routes **promptfoo** (default, declarative YAML, deterministic-first) vs **DeepEval** (`references/deepeval.md` — pytest-native, research-backed RAG/agent/conversational metrics, G-Eval) vs the in-code SDK path (`references/details.md`); its **adversarial half** is `references/red-teaming.md` — **OWASP LLM Top 10:2025** red-teaming (promptfoo `redteam` `owasp:llm` preset / DeepTeam), assert an attack-success **rate** per item; the model-behavior attack surface `qa-security`'s scanners can't reach (the LLM-Top-10 complement to its web/API-Top-10 map). Owned by the dedicated `qa-llm-{java,dotnet,typescript}` agents — java · dotnet · typescript
- `rag-testing` — RAG (retrieval-augmented generation) eval; the RAG **specialization** of `llm-app-testing` (inherits its four ideas + judge-pinning). Core discipline: **decompose retrieval from generation** so a bad answer is localized, assert the **RAG triad** (context relevance · groundedness/faithfulness · answer relevance) + **deterministic retrieval-ranking metrics** (recall@k/MRR/NDCG) when labels exist, on a **golden set carrying reference contexts**. Spine routes **Ragas** (`references/ragas.md` — RAG-native, the four canonical metrics + corpus→test-set generator, evaluator LLM pinned to Claude) vs DeepEval contextual metrics vs promptfoo `context-*`; owned by the `qa-llm-{stack}` agents — java · dotnet · typescript
- `mobile-device-farm` · `mobile-native-features` — device-cloud runs · OS-surface (permissions, push, deep links) — java · dotnet · typescript
- `test-data-builder` — builders / ObjectMother — java · dotnet · typescript

**Reporting & CI/CD (`qa/reporting/`, `qa/cicd/` — own agents, own skills)**
- `reporting/<stack>/skills/allure-reporting` — Allure results — java · dotnet · typescript
- `reporting/<stack>/skills/flaky-test-quarantine` — detect/quarantine flaky tests, tag tests by finding — java · dotnet · typescript
- `agents/qa-reporting-{java,dotnet,typescript}` — wire Allure → tag tests by finding → detect/quarantine flakes → review
- `cicd/<stack>/skills/ci-pipelines` — shard matrix, Allure-publish step, perf gate, OIDC secrets; one skill, CI host picked inside via `references/` (github-actions · azure-pipelines · gitlab-ci) — java · dotnet · typescript
- `cicd/ci-conventions` — language-agnostic pipeline conventions every `ci-pipelines` implementation references
- `agents/qa-cicd-{java,dotnet,typescript}` — pipeline skeleton → shard/parallelize → gates & secrets (Allure-publish owned by qa-reporting, SCA gate owned by qa-security) → review

**Language-agnostic (`qa/manual/`)**
- `test-basis-analyzer` — distills a story / BRD / API contract / partial feature description into one concise, sourced **test-basis document** (business logic, validations, restrictions, observable implementation notes, data dictionary, states) with every silent/contradictory/untestable item flagged; the source-of-truth artifact that feeds `test-design-techniques` + `test-case-writer` (backs the agent's Phase 1)
- `test-case-writer` · `bug-report-writer` · `exploratory-charter-writer` — manual-QA writing workflows (test-case suites are Setup → Cases → Cleanup)
- `test-design-techniques` — ISTQB black-box technique deep dive (EP, BVA 2/3-value, decision tables, state transition n-switch, use-case, pairwise, classification tree, error guessing) with coverage criteria and a selection matrix; `test-case-writer` defers technique choice here
- `test-strategy` · `quality-metrics` — process / planning
- `agents/qa-manual-test-designer` — phased orchestrator: documentation → systematically-derived manual test-case suite (analyze basis → apply techniques → assemble Setup/Cases/Cleanup → review & coverage); **Exploration mode** builds the test basis from a live web page via the Playwright CLI when docs are thin (charter → explore → file bugs → `#observed` conditions)

**Cross-stack (`qa/_shared/`)**
- `contract-testing-pact` · `performance` — rules every stack implementation references (performance also carries the perf-suite review checklist agents use in their review phase)
- `webapp-testing` — UI automation with Python (Playwright web-app testing toolkit, Anthropic-provided import) — the one Python-based skill; all other skills target Java / C# / TypeScript

## Frontend dev catalog

The `frontend/blazor/` folder is the frontend **development** stack (distinct from `qa/`, which tests it). It is organized like the QA domain — stack-first, domain-encapsulated, one phased orchestrator agent per stack — and shares the aesthetic-craft layer in `design/` and the auth skills in `auth/`. The **`fe-blazor`** agent (`frontend/blazor/agents/fe-blazor.md`) owns a Blazor Web App build end-to-end across six phases: scaffold → architecture foundations (with a **design-critique loop**) → feature build → quality layers → bUnit component tests → hostile self-review (with a **visual self-critique pass**). It loads **only** `frontend/blazor/skills/*` plus the named `design/*` and `auth/auth0-blazor` skills; QA (`qa-ui-dotnet`, `qa-manual-test-designer`, `qa-security`, `qa-cicd-dotnet`) are **peers** it invokes separately, connected by the `data-testid` / `missing-testids.md` handshake.

**Skills** (`frontend/blazor/skills/`, `fe-blazor-*`):
- **Foundations** — `reference` (concept lookup, atomic-design taxonomy) · `project-scaffold` (Blazor Web App from zero, render-mode decision matrix, TFM detection) · `state-management` (scoped state containers, `Changed` events) · `component-library` (one-of-N: MudBlazor · Fluent UI · Radzen · enterprise · none) · `styling` (CSS isolation + `::deep`, design tokens, type scale, dark mode) · `responsive-design` (breakpoint contract + C# mirror, intrinsic-first, container queries; QA handshake to `responsive-testing`)
- **Feature build** — `generator` (pages/components/forms per the patterns) · `forms` (`EditForm` + FluentValidation) · `data-access` (request/response transport lane — WASM/HTTP vs interactive-SSR service injection, `[PersistentState]`, streaming) · `realtime` (server→client push — circuit-as-WebSocket, SignalR client, raw WS/SSE) · `js-interop` (JS↔.NET mechanics — collocated `.razor.js` modules as `IJSObjectReference`, `[JSInvokable]`/`DotNetObjectReference` callbacks, disposal + `JSDisconnectedException`, prerender/render-mode edges; last resort per the no-interop-where-C#-suffices rule) · `testability` (`data-testid` authoring + audit; consumes `missing-testids.md`) · `ui-conventions` (cross-cutting UI-correctness: display/table/CRUD/confirmation/IA rules) · `motion` (CSS-first mechanics, `prefers-reduced-motion` hard floor, view transitions)
- **Quality layers** — `accessibility` (semantic-first, focus under enhanced nav, ARIA in custom components) · `performance` (render perf, WASM startup, Server scale, budgets) · `error-resilience` (`ErrorBoundary`, reconnection UX, three-state regions, Polly) · `seo-discoverability` (static SSR for public pages, meta/OG, real 404, sitemap) · `localization` (`IStringLocalizer`/`.resx`, per-render-mode culture pipeline — Server `RequestLocalization`+cookie vs WASM satellite assemblies/ICU, `@bind:culture`, RTL; QA handshake to `i18n-testing`) · `pwa-offline` (WASM-only installable + offline: manifest, two-service-worker model, cache-first + update lifecycle, offline data strategy; Server can only be *installable*)
- **Test + review** — `component-testing` (bUnit v2, logic-bearing components only; E2E is the `qa-ui-dotnet` peer) · `reviewer` (hostile senior review, standard severity table)

**Loaded (not owned) by the agent** — `auth/auth0-blazor` (+ `auth/_shared/auth0-concepts`) for Phase 1/2 auth; and the stack-agnostic design-craft layer: `design/frontend-design` (**primary theme authority** — per-brief token system feeding `styling`, + the three-AI-look critique) · `design/design-tokens` (the semantic-tier token discipline `frontend-design`/`styling` build on) · `design/brand-intake` (brownfield path — an existing brand book → normalized token system) · `design/dataviz` (chart/data-viz design system) · `design/iconography` (icon family + OG/social-image craft) · `design/theme-factory` (optional quick-start) · `design/ux-writing` (microcopy voice filling the slots `ui-conventions`/`error-resilience`/`generator` define) · `design/web-design-guidelines` (Phase 5 **code-level** audit) · `design/ux-heuristics` (Phase 5 **experience-level** review — Nielsen heuristics, flow-friction, IA; also seeds `qa-manual-test-designer`'s exploration mode).

New-project setup = copy `frontend/blazor/` + the `design/` skills + `auth/auth0-blazor` (+ `auth/_shared/auth0-concepts`).

### Frontend code rules

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
- **bUnit for logic-bearing components** (dev-side); E2E / user journeys belong to the `qa-ui-dotnet` peer.

### Version policy (`frontend/blazor/`)

.NET **8, 9, and 10 are all supported; .NET 10 is primary.** Every skill is version-aware — the agent's first act on an existing project is to detect the `TargetFramework` and apply the guidance keyed to it: net10 primary recipes (`[PersistentState]`, `NotFoundPage` / `NavigationManager.NotFound()`, `AddValidation()`, `ReconnectModal`) with net8/net9 fallbacks (manual `PersistentComponentState`, `UseStatusCodePagesWithReExecute`, DataAnnotations). Never apply a net10-only API to a down-level project, and never flag a down-level project for lacking one.

## Data catalog

The `data/` folder is the **database-engineering** stack (distinct from `qa/`, which tests the data this designs, and from the backends that consume it). It is organized like the QA and Frontend domains — **engine-first, domain-encapsulated, one phased orchestrator agent, one marketplace plugin** — and shipped as the self-contained `data` plugin. The **`data-architect`** agent (`data/agents/data-architect.md`) owns a data design end-to-end across six phases: discover (engine + version detection, workload shape) → model → secure → implement (DDL + migration) → tune (indexing/query) → hostile review. It loads **only** `data/*` skills; QA (`qa-api-{stack}` db-testing, `qa-security` for the cross-tenant leak test, `qa-performance-{stack}`) and `auth/*` (tenant claims → session context) are **peers** it names, not loads.

**Skill shapes.** Two, like the rest of the library:
- **Router + topic references** (`postgresql`, `sqlserver`, `mysql`, `mongodb`, `redis`) — the `SKILL.md` routes and holds the shared rules (version policy, connections/pooling, hard rules); depth lives in `references/<topic>.md` split by **topic** (`data-modeling` · `security` · `indexing` · `performance` · `caching`; Redis: `data-structures` · `patterns` · `security` · `operations`). Unlike qa's one-of-N families, a task may need **two** references at once (a new multi-tenant schema = `data-modeling.md` + `security.md`). **Read the router first, then the matching reference end-to-end before writing code.**
- **Single-file** (`dynamodb`, `cosmosdb`, `elasticsearch`) — their models don't decompose the same way, so each is one file with topic sections.

**Engines** (`data/<engine>/`, skill name `data-<engine>`): `postgresql` · `sqlserver` (Azure SQL) · `mysql` (MariaDB / Aurora) · `mongodb` · `redis` (Valkey) · `dynamodb` · `cosmosdb` · `elasticsearch` (OpenSearch). Fork-divergence is called out where it matters — MariaDB↔MySQL · Valkey↔Redis · OpenSearch↔Elasticsearch.

**Cross-engine `_shared/`** (`data/_shared/<skill>/`): `schema-design` (id strategy / money / soft-delete / multi-tenant pattern choice / embed-vs-reference) · `migrations` (expand-contract universal pattern + tool-selection table) · `caching-patterns` (cache-aside / stampede / TTL & key policy) · `query-optimization` (universal triage / ESR / keyset / N+1).

**The scope-fence contract** (checked every design): `_shared` owns the cross-engine **decision/pattern**, the engine skill owns the **mechanics**. Modeling — `_shared/schema-design` decides id strategy (UUIDv7 default), tenancy pattern, embed-vs-reference; the engine `data-modeling` executes the DDL / native generator / modeling mechanics. Migrations — `_shared/migrations` owns expand-contract + the tool table; the engine owns online-safe DDL (`CONCURRENTLY`, `NOT VALID`, pt-osc/gh-ost). Caching — `_shared/caching-patterns` owns the strategy; the engine `caching` (and Redis command mechanics) own the invalidation/change-channel seam. Query tuning — `_shared/query-optimization` owns universal triage; the engine `performance`/`indexing` own plan-reading and index types.

**Peer handshakes** (named, not loaded): `qa-api-{java,dotnet,typescript}` `db-testing/{client,testcontainers,query-author}` seed/assert/clean against the schema; **`qa-security` owns the cross-tenant leak test** (BOLA/IDOR/BFLA) that proves Phase-3 isolation holds — MySQL/Mongo app-enforced tenancy makes this leak test *mandatory*, since there is no RLS to fall back on; `qa-performance-{stack}` validates Phase-5 tuning under load; `auth/auth0-{stack}` + `auth/_shared/auth0-concepts` supply the tenant/user claims feeding the RLS / app-enforced session context.

### Version policy (`data/`)

Every engine skill is **version-aware** (Blazor-style): the agent's first act on a live database is the version probe, then it keys every recipe to the detected version and never up-levels a down-level server. Supported versions: **PostgreSQL 18 primary / 15–17** · **SQL Server 2025 primary / 2022 / 2019 / Azure SQL evergreen** · **MySQL 8.4 LTS primary / 9.x / 8.0** · **MongoDB 8.0 LTS primary / 7.0** · **Redis 8.x primary / 7.2–7.4 + Valkey fork** · **Elasticsearch 9.x / 8.x + OpenSearch 3.x fork**; cloud stores (DynamoDB, Cosmos DB) track SDK majors + creation-time-immutable constraints. Backend samples match the Stack defaults — **.NET 10 / Java 21 / Node 24** — version-aware where the driver surface differs.

New-project setup = copy `data/` (the engine you need + the four `_shared` skills).

## Engineering-practices catalog

The `engineering-practices/` folder is the **developer-workflow spine** — the language-agnostic idea → spec → plan → execute → verify → finish loop that sits *beside* the `qa/` and `frontend/` domains rather than inside them. The 10 in-scope skills (adapted from obra/superpowers, self-contained: they reference only each other) are **bundled into every stack plugin** (`qa-java`, `qa-dotnet`, `qa-typescript`, `fe-blazor`) — no standalone plugin. All use the `ep-*` name prefix.

**The chain** (each skill announces itself and hands to the next):
- `ep-brainstorming` — turn an ad-hoc idea into an approved design/spec (`docs/specs/YYYY-MM-DD-<topic>-design.md`); HARD-GATE before any code. **Scoped:** a phased agent with its own design gate (`fe-blazor`, the `qa-*` orchestrators) already satisfies the gate — do not run this on top of them. Its browser **visual companion** is opt-in on explicit request only. → `ep-writing-plans`
- `ep-writing-plans` — approved spec → detailed bite-sized implementation plan (`docs/plans/YYYY-MM-DD-<feature>.md`), one action per step, complete code in every step. → `ep-executing-plans`
- `ep-executing-plans` — execute a written plan task-by-task with review checkpoints (task list via TaskCreate/TaskUpdate); stops when blocked. The **only** execution path until the excluded subagent skills are adapted. → `ep-finishing-a-development-branch`
- `ep-finishing-a-development-branch` — tests-pass gate → structured merge/PR/keep/discard options → provenance-based worktree cleanup.

**Cross-cutting** (entered anytime, not part of the linear chain):
- `ep-test-driven-development` — the dev-side red-green-refactor **inner loop**. Complements `qa/` (which owns suite architecture, page objects, builders); this owns only the loop. Reconciles with the CLAUDE.md test rules — no conflict (per "skill wins for its domain", both agree).
- `ep-systematic-debugging` — root-cause-first, four-phase debugging; writes the failing test via `ep-test-driven-development`, confirms via `ep-verification-before-completion`.
- `ep-verification-before-completion` — evidence-before-claims gate before any "done/fixed/passing" statement or commit/PR. Reinforces the global "report outcomes faithfully" rule.
- `ep-using-git-worktrees` — isolated-workspace setup; prefers the harness's native worktree tool (`EnterWorktree`) over the git fallback.

**Agent-dispatch (opt-in, cost-aware — governed by the Conservative agent-spawning policy):**
- `ep-subagent-driven-development` — execute a plan by delegating self-contained tasks to subagents. The **opt-in exception** to inline `ep-executing-plans`, not a replacement — use only when delegation clearly pays for itself. Default flow is 1 implementer subagent per task + **inline** controller review (spec then quality, CLAUDE.md severity-table format); dedicated reviewer subagents are a permission-gated escalation.
- `ep-dispatching-parallel-agents` — fan genuinely independent problems out to concurrent agents. The cost-aware exception to sequential/inline work.
- **The policy (both skills):** *cost before speed* — inline/sequential is the default; spawn only when it pays for itself; and a **hard gate — more than 2 agents (concurrent, or as the plan for one step) requires the user's permission first.** This deliberately inverts the upstream speed-first defaults ("fresh subagent per task", "3+ failures → one agent each"). It aligns with the harness's own guidance to spawn agents conservatively.

**Reconciliation with global rules:** where a process skill and a global rule touch — `ep-test-driven-development` vs the Test code rules, the `ep-brainstorming` HARD-GATE vs the phased-agent design phases, `ep-verification-before-completion` vs "report outcomes faithfully" — the existing "skill wins for its domain" rule already governs; the skills are written to agree with the global rules, so no override is triggered in practice.
