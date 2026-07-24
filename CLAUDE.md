# Global rules

These rules apply to every skill in this library unless a specific skill explicitly overrides them.

> **Scope:** The `qa/` folder, `frontend/blazor/` and `frontend/react/` (each with the `design/` and `auth/auth0-{blazor,react}` skills it depends on, and `frontend/react/` additionally with its vendored `vendor/{reference,composition-patterns,view-transitions}` seeds), the `backend/` folder (`_shared` + `dotnet`/`java`/`node`, each with a phased `be-*` agent; `dotnet`/`java` additionally own their own service-side `auth0`/`cognito` skills, depending on the cross-cutting `auth/_shared/{auth0-concepts,oidc-concepts}`), the `data/` folder (8 per-engine skills + 4 cross-engine `_shared` skills + the `data-architect` agent), the `business-analysis/` folder (9 `ba-*` skills + the `requirements-author` and `business-analyst` agents), the `observability/` folder (6 skills — the per-stack `opentelemetry-{dotnet,java,node}` + `structured-logging-{dotnet,java,node}` and the stack-agnostic `loki-tempo-setup` · `prometheus-mimir-setup` · `logql-promql` · `grafana-dashboards` — plus the per-stack `observability-engineer-{dotnet,java,node}` agents, all **bundled into the `be-*` plugins**, not shipped standalone), the `devops/` folder (9 cloud/CI-keyed skills + the `devops-engineer` agent), and the 14 in-scope `engineering-practices/` skills (the `ep-*` set — the 8 core developer-workflow skills plus `ep-subagent-driven-development`, `ep-dispatching-parallel-agents`, `ep-requesting-code-review`, `ep-receiving-code-review`, and the audit pair `ep-spec-compliance-audit` + `ep-feature-audit` with their `code-auditor` agent) are ready for use and the remote. All other top-level folders (`frontend/react-native/`, `auth/cognito-{blazor,react}` — authored but not yet wired into `fe-blazor`/`fe-react`) are under construction — ignore them, and do not upload them to the remote yet.
>
> **Published plugins** (`.claude-plugin/marketplace.json`, marketplace `skills-library`): **`qa-java`** · **`qa-dotnet`** · **`qa-typescript`** (one self-contained QA toolkit per stack) · **`fe-blazor`** · **`fe-react`** (frontend dev stacks + `design/*` + `auth/auth0-{blazor,react}` + `auth/_shared/auth0-concepts`) · **`be-dotnet`** · **`be-java`** · **`be-node`** (backend design-pattern + persistence dev stacks + `backend/_shared/*`; `be-dotnet`/`be-java` additionally bundle their `auth0`/`cognito` skills + `auth/_shared/{auth0-concepts,oidc-concepts}`; **all three additionally bundle the `observability/*` skills + their `observability-engineer-{stack}` agent**) · **`data`** (8 engines + 4 `_shared` + `data-architect`) · **`business-analysis`** (9 `ba-*` skills + `requirements-author` + `business-analyst`) · **`devops`** (9 skills + `devops-engineer`). The `ep-*` skills (developer-workflow + the audit pair), the `code-auditor` agent, and `qa/manual/test-basis-analyzer` (which the auditor loads) are bundled into the eight stack plugins (`qa-*`, `fe-*`, `be-*`) and into `devops`, not shipped standalone.

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
- `qa/_shared/` — cross-stack technical rules referenced by stack skills (`contract-testing-pact`, `performance`, `security` + the language-agnostic `security-testing/*` scanner skills, and `bdd/gherkin-authoring` — the framework-agnostic Gherkin engine loaded by every `qa-bdd-{stack}` agent) plus `qa-webapp-testing` (the one Python skill, Anthropic-provided import); also `qa/_shared/agents/qa-security` — the cross-stack, OWASP-mapped security orchestrator (loads the `_shared` scanner skills + the project's stack-native security siblings, incl. `dependency-scanning`, phase by phase).

New-project setup = copy `qa/<stack>/` + `qa/manual/` + `qa/reporting/` + `qa/cicd/` + `qa/_shared/`.

**Project scaffolding** (dotnet-only so far; version-aware — .NET 10 primary, 8/9 supported)
- `api-project-scaffold` · `ui-project-scaffold` · `mobile-project-scaffold` · `performance-project-scaffold` — stand up a runnable test solution from zero (flat projects, shared `TestCore`, CPM version table, per-project config); composable into one multi-module solution — dotnet
- `accelerator-conventions` — conventions for working inside the in-house Accelerator test-automation framework (JSON-driven screens) — dotnet (java sibling `accelerator-conventions` lives in `qa/java/`)

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
- `mutation-testing` — measure TEST QUALITY, not coverage: seed faults and prove tests catch them, gate on a mutation-score threshold, treat surviving mutants as missing-assertion findings (tool-bound: **PIT/pitest** java · **Stryker.NET** dotnet · StrykerJS typescript — the TS sibling is not built yet) — java · dotnet
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
- `qa-webapp-testing` — UI automation with Python (Playwright web-app testing toolkit, Anthropic-provided import) — the one Python-based skill; all other skills target Java / C# / TypeScript

## Frontend dev catalog

The `frontend/blazor/` folder is the frontend **development** stack (distinct from `qa/`, which tests it). It is organized like the QA domain — stack-first, domain-encapsulated, one phased orchestrator agent per stack — and shares the aesthetic-craft layer in `design/` and the auth skills in `auth/`. The **`fe-blazor`** agent (`frontend/blazor/agents/fe-blazor.md`) owns a Blazor Web App build end-to-end across six phases: scaffold → architecture foundations (with a **design-critique loop**) → feature build → quality layers → bUnit component tests → hostile self-review (with a **visual self-critique pass**). It loads **only** `frontend/blazor/skills/*` plus the named `design/*` and `auth/auth0-blazor` skills; QA (`qa-ui-dotnet`, `qa-manual-test-designer`, `qa-security`, `qa-cicd-dotnet`) are **peers** it invokes separately, connected by the `data-testid` / `missing-testids.md` handshake.

**Skills** (`frontend/blazor/skills/`, `fe-blazor-*`):
- **Foundations** — `reference` (concept lookup, atomic-design taxonomy) · `project-scaffold` (Blazor Web App from zero, render-mode decision matrix, TFM detection) · `state-management` (scoped state containers, `Changed` events) · `component-library` (one-of-N: MudBlazor · Fluent UI · Radzen · enterprise · none) · `styling` (CSS isolation + `::deep`, design tokens, type scale, dark mode) · `responsive-design` (breakpoint contract + C# mirror, intrinsic-first, container queries; QA handshake to `responsive-testing`)
- **Feature build** — `generator` (pages/components/forms per the patterns) · `forms` (`EditForm` + FluentValidation) · `data-access` (request/response transport lane — WASM/HTTP vs interactive-SSR service injection, `[PersistentState]`, streaming) · `realtime` (server→client push — circuit-as-WebSocket, SignalR client, raw WS/SSE) · `js-interop` (JS↔.NET mechanics — collocated `.razor.js` modules as `IJSObjectReference`, `[JSInvokable]`/`DotNetObjectReference` callbacks, disposal + `JSDisconnectedException`, prerender/render-mode edges; last resort per the no-interop-where-C#-suffices rule) · `testability` (`data-testid` authoring + audit; consumes `missing-testids.md`) · `ui-conventions` (cross-cutting UI-correctness: display/table/CRUD/confirmation/IA rules) · `motion` (CSS-first mechanics, `prefers-reduced-motion` hard floor, view transitions)
- **Quality layers** — `accessibility` (semantic-first, focus under enhanced nav, ARIA in custom components) · `performance` (render perf, WASM startup, Server scale, budgets) · `error-resilience` (`ErrorBoundary`, reconnection UX, three-state regions, Polly) · `seo-discoverability` (static SSR for public pages, meta/OG, real 404, sitemap) · `localization` (`IStringLocalizer`/`.resx`, per-render-mode culture pipeline — Server `RequestLocalization`+cookie vs WASM satellite assemblies/ICU, `@bind:culture`, RTL; QA handshake to `i18n-testing`) · `pwa-offline` (WASM-only installable + offline: manifest, two-service-worker model, cache-first + update lifecycle, offline data strategy; Server can only be *installable*)
- **Migration** — `migration` (React 18→19, Next 14→15 async request APIs + flipped caching defaults, Pages→App Router incremental port; the official codemods and what they miss — the only skill that *changes* the version lane rather than reading it)
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

## Frontend-React dev catalog

The `frontend/react/` folder is the React frontend **development** stack — the port of `frontend/blazor/` to React, organized identically (stack-first, domain-encapsulated, one phased orchestrator agent, one marketplace plugin) and sharing the same `design/` aesthetic-craft layer and the auth skills in `auth/`. **Stack decisions are locked:** Next.js 15 App Router (RSC) primary / Vite SPA + React Router fallback · **MUI default** component library · follow-the-library styling · **React 19 primary / React 18 tagged fallback** (version-aware). The **`fe-react`** agent (`frontend/react/agents/fe-react.md`) owns a React build **and brownfield fix/extend** end-to-end across six phases: scaffold → architecture foundations (with a **design-critique loop**) → feature build → quality layers → Vitest + RTL component tests → hostile self-review (with a **visual self-critique pass**). It loads **only** `frontend/react/skills/*` plus the named `design/*` and `auth/auth0-react` skills (and, for brownfield, the bundled `ep-*` developer-workflow skills); QA (`qa-ui-typescript`, `qa-manual-test-designer`, `qa-security`, `qa-cicd-typescript`) are **peers** it invokes separately, connected by the `data-testid` / `missing-testids.md` handshake.

**Skills** (`frontend/react/skills/`, `fe-react-*` — 24 skills; Blazor's `js-interop` is **dropped** since React has no interop barrier, its browser-API guidance folded into `reference`/`performance`; `routing` and `migration` are **React-only additions** with no Blazor sibling — `@page` collapses routing to one line, and Blazor has no App-Router-scale version jump):
- **Foundations** — `reference` (RSC vs Client Components + the `'use client'` boundary, hooks lifecycle, `use()`/Actions/`useActionState`/`useOptimistic`, `ref`-as-prop, Context vs store, hydration trap, atomic-design taxonomy, React↔Blazor map) · `project-scaffold` (`create-next-app`/Vite from zero, rendering-strategy-per-route matrix, feature folders, strict-TS/ESLint/Prettier/pnpm/env) · `state-management` (server vs client state, Context split read/write, Zustand, TanStack Query, URL-as-state) · `component-library` (one-of-N: MUI default · Mantine · Chakra · shadcn · none; `references/{mui,mantine,chakra,shadcn,none}.md`) · `styling` (follow-the-library authority, CSS Modules for gaps, tokens as CSS vars, `next-themes` dark mode, type scale) · `responsive-design` (breakpoint contract + TS mirror, container queries, SSR `useMediaQuery` caveat) · `routing` (App Router file conventions — `page`/`layout`/`template`/`loading`/`not-found`/`route`, route groups, dynamic + catch-all segments, parallel `@slot` + intercepting `(.)` modal routes, `middleware.ts` gate, the `useRouter`/`usePathname`/`useSearchParams` triad, React Router 7 fallback lane)
- **Feature build** — `generator` (RSC-boundary decision + page/component/hook/context/compound/container-presentation/error-boundary/Suspense recipes) · `forms` (React Hook Form + Zod + React 19 Server-Actions lane) · `data-access` (RSC `fetch`/`cache` vs client TanStack Query, Server Actions, Suspense streaming, ProblemDetails→UI) · `realtime` (SSE/WebSocket hooks, snapshot→live handoff) · `testability` (`data-testid` authoring + audit, per-library matrix, `missing-testids.md` handshake) · `ui-conventions` (display/table/CRUD/confirmation/IA/surface-choice) · `motion` (CSS-first, `prefers-reduced-motion` floor, the React exit-animation gap → `motion`/View Transitions) · `localization` (next-intl on App Router / react-i18next on Vite, per-locale routing, RTL; QA `i18n-testing` handshake)
- **Quality layers** — `accessibility` (semantic-first, client-nav focus gap, Radix/React Aria widgets; axe handoff to QA) · `performance` (four cost centers + the vendored Vercel ruleset entry point) · `error-resilience` (`error.tsx`/`react-error-boundary`, three-state regions, idempotent retry) · `seo-discoverability` (`metadata`/`generateMetadata`, static rendering, `sitemap.ts`/`robots.ts`, JSON-LD, real 404) · `pwa-offline` (Serwist on Next / vite-plugin-pwa on Vite, manifest, update lifecycle, offline-data strategy)
- **Test + review** — `component-testing` (Vitest + React Testing Library, logic-bearing components + custom hooks only, the async-RSC limit — extract the fetch, E2E the rest; E2E is the `qa-ui-typescript` peer) · `reviewer` (hostile senior review, standard severity table; RSC/`'use client'`-placement/hydration/effect-deps/key/cleanup checklist) · `conformance-audit` (**the plugin's self-audit** — the one whole-repo, read-only, re-runnable lane: sweeps an existing codebase against *this plugin's own* rules across 19 lettered sections A–S, one per skill domain, and saves `docs/audits/<ts>-fe-react-conformance-r<N>.md` with `file:line` evidence, section rollups, defect families, and a leverage-ordered priority table; version-gated and applicability-gated first so a React-18 or non-App-Router project is never flagged for lacking an up-level API. **Three-way fence:** `reviewer` = one diff, inline, no artifact · `conformance-audit` = whole repo vs *the plugin's* fixed rule set, saved, Mode A/B rounds · `code-auditor`/`ep-*-audit` = code vs *the user's* spec/stories, or a spec-less feature trace, stack-agnostic. Read-only — the `fe-react` agent applies every fix in a separate FIX/EXTEND run)

**Loaded (not owned) by the agent** — `auth/auth0-react` (+ `auth/_shared/auth0-concepts`) for Phase 1/2 auth — **two lanes**: `@auth0/nextjs-auth0` (App Router: middleware, encrypted-cookie session read server-side in RSC/Actions/handlers) vs `@auth0/auth0-react` (Vite/CRA SPA, PKCE); the stack-agnostic design-craft layer (`design/frontend-design` **primary theme authority** · `design/{design-tokens,brand-intake,dataviz,iconography,theme-factory,ux-writing}` · `design/web-design-guidelines` Phase-5 code-level audit · `design/ux-heuristics` Phase-5 experience-level review); and **referenced** (not absorbed — deliberately **not registered as skills**, so they can't out-trigger the house skills they feed) the vendored rules-format seeds at `frontend/react/vendor/{reference` (Vercel 70-rule perf guide, feeds `performance`)`,composition-patterns,view-transitions` (feeds `motion`)`}` — upstream imports shipped in-bundle with the `fe-react` plugin.

New-project setup = copy `frontend/react/` + the `design/` skills + `auth/auth0-react` (+ `auth/_shared/auth0-concepts`). The plugin ships **two slash commands**: **`/fe-react`** loads the agent definition and runs its phased workflow inline (the deterministic entry point when the agent isn't picked up by name), and **`/fe-react-audit`** runs the `conformance-audit` skill inline against the current repo — one call, read-only, findings saved to `docs/audits/`.

### Frontend-React code rules

- Components are **RSC by default; `'use client'` is opt-in per island** — never blanket a route client just because one leaf needs it (the App-Router analog of Blazor's "static SSR default, interactivity opt-in").
- Server Components fetch; Client Components interact — data crosses the boundary as serializable props; a Client Component composes server output via `children`, never by importing a Server Component.
- **Semantic HTML before ARIA.** Reach for ARIA only when no semantic element fits.
- Forms use **React Hook Form + Zod** (Server Actions + `useActionState` on App Router); field-level `aria-invalid` + error text; server errors mapped back with `setError`.
- **Follow-the-library styling** (MUI theme/`sx`); CSS Modules only for gaps; **never Tailwind atop MUI**. (When the library is shadcn/none the authority flips to Tailwind / CSS Modules — the reference file says which.)
- Every **interactive element and list/grid container ships a `data-testid`** — PascalCase dot-separated, static row locators, never array index / id / GUID / state value.
- **In-app navigation is a real `<Link href>`**, never an `onClick` `router.push` on a `<div>`.
- Every **data region has explicit loading / loaded / failed states** (Suspense + error boundary, or a three-state hook); a failure never collapses to blank, and never leaks `error.message`.
- **No server data in client stores** — RSC fetch / TanStack Query owns server state; Zustand/Context own client state.
- Keys are **stable domain ids**, never array index; **no `useEffect` to derive state** (compute in render); effects have exhaustive deps; subscriptions/timers/listeners are cleaned up; no browser reads (`window`/`localStorage`/`Date.now()`) during render (hydration mismatch).
- Strict TypeScript (`strict: true`), no `any`; async all the way; structured logging on the server; HTTP through a typed client / server util.
- **Vitest + React Testing Library for logic-bearing components** (dev-side, query by role/label first); E2E / user journeys and async-RSC rendering belong to the `qa-ui-typescript` peer.

### Version policy (`frontend/react/`)

**React 19 is primary; React 18 is a tagged fallback** (an 18 pattern is not obsolete — it's correct for that version). Every skill is version-aware — the agent's first act on an existing project is to detect the React (and Next.js) major from `package.json` and apply the guidance keyed to it: React 19 primary recipes (`use()`, Actions, `useActionState`, `useOptimistic`, `ref` as a plain prop / no `forwardRef`, `<title>`/`<meta>` hoisting, React Compiler auto-memoization) with React 18 fallbacks (`forwardRef`, manual data hooks + `isPending`/rollback, `react-helmet`). **Next.js 15 primary / 14 fallback** tracks alongside (App Router primary; the Pages Router is legacy; Vite SPA + React Router 7 is the tagged non-RSC lane). Never apply a React-19-only API to an 18 project, and never flag a down-level project for lacking one.

## Design catalog

The `design/` folder is the **stack-agnostic aesthetic-craft layer** shared by both frontend stacks. Its skills carry the **`design-*` name prefix** (`design-frontend-design`, `design-dataviz`, `design-tokens`, `design-web-guidelines`, …) so they don't collide in the global skill namespace with same-named third-party skills — the folder names are unprefixed, the frontmatter `name:` is what carries the prefix. It is **not a standalone plugin** — it is bundled wholesale into `fe-blazor` and `fe-react`, and its 9 skills are **loaded, not owned** by the `fe-*` agents (Phase 1/2 foundations + Phase 5 review). Borrowed artifacts (the Anthropic brand fixture, the vendored Vercel ruleset, the Anthropic theme import) are recorded in `design/ATTRIBUTIONS.md`.

**The routing triangle** — how a project gets its look: **greenfield identity** → `design/frontend-design` (the **primary theme authority**; invents a per-brief token system) · **existing brand** → `design/brand-intake` (a brand book → normalized token system) · **preset quick-start** → `design/theme-factory` (10 preset palette+font themes). All three feed `design/design-tokens`' primitive → semantic tier discipline (the token tier/naming mechanics every look is expressed in).

**The remaining skills:** `design/dataviz` (product charts/dashboards — operational/RED-USE dashboards stay with `observability/grafana-dashboards`) · `design/iconography` (one icon family + OG/social imagery) · `design/ux-writing` (microcopy voice filling the slots a stack's `ui-conventions`/`error-resilience`/`generator` define).

**The two review altitudes (the fence users trip on):** `design/web-design-guidelines` is the **code-level** audit — reads UI source files against the vendored Vercel Web Interface Guidelines ruleset (offline-first), flagging markup/attribute/handler violations; `design/ux-heuristics` is the **experience-level** review — Nielsen heuristics, flow-friction, and IA on the house severity table (and seeds `qa-manual-test-designer`'s exploration mode). Code-level vs experience-level — one audits the implementation, the other the experience.

New-project setup = copy `design/` alongside the `frontend/<stack>/` you need (already bundled in the `fe-*` plugins).

## Backend catalog

The `backend/` folder is the **design-pattern application + persistence** dev-stack domain — the backend sibling of `frontend/blazor` and `frontend/react` — distinct from `qa/` (which tests this code) and `data/` (which owns schema/DDL/engine tuning; a backend `persistence` skill owns only the ORM-side mechanics on top of it). Organized identically to the rest of the library: **stack-first, domain-encapsulated, one phased orchestrator agent per stack, one marketplace plugin per stack** — `be-dotnet` · `be-java` · `be-node`.

**Cross-stack `backend/_shared/`** (skill prefix `be-shared-*`): `reference` (language-agnostic pattern cards — intent, when to use, when not to, common failure mode) · `reviewer` (architecture-altitude review for cross-stack/pattern-stacking concerns). Every stack's `reference`/`reviewer` loads these for the conceptual case; they hold the "what & when," the stack skill holds the "how" in that language.

**Stacks** (`backend/<stack>/skills/`, prefix `be-<stack>-*`; agent `backend/<stack>/agents/be-<stack>.md`):
- **`dotnet`** (.NET 10 primary / 8-9 supported) — `reference` / `generator` (Strategy, Decorator, Repository, CQRS/MediatR, Factory, Options, Pipeline) / `reviewer` (DI/async/layering violations) / `persistence` (EF Core: `DbContext` design, configurations, migrations, query patterns, optimistic concurrency, bulk operations) / `auth0` + `cognito` (service-side auth: JWT bearer validation via `AddJwtBearer`, RBAC via authorization policies, Client Credentials M2M — the ASP.NET Core sibling of `auth/auth0-blazor` / `auth/cognito-blazor`)
- **`java`** (Java 21 + Spring Boot 3.x) — same five skills, Spring-idiomatic (constructor injection, `@ConfigurationProperties` Options, JPA/Hibernate + Spring Data + Flyway persistence, `@Transactional` boundaries, `@Version` optimistic locking, N+1 prevention; `auth0`/`cognito` via the Spring Security OAuth2 Resource Server + method-level `@PreAuthorize`)
- **`node`** (Node 24 active LTS primary / 22 maintenance supported; TypeScript strict) — the four pattern/persistence skills, TS-idiomatic (discriminated unions + `Result<T,E>` over class hierarchies, branded ids, higher-order-function decorators, Zod at every boundary; Prisma default / Drizzle / TypeORM persistence); no `auth0`/`cognito` skill yet (gap — the Node backend currently has no service-side auth skill; `qa-auth0-test-tokens-typescript` exists but there's nothing for it to complement)

`dotnet`/`java`'s `auth0`/`cognito` skills load the cross-cutting `auth/_shared/{auth0-concepts,oidc-concepts}` for the provider-agnostic concept model, and hand off to `auth/auth0-{blazor,react}` / `auth/cognito-{blazor,react}` for the SPA/Blazor side of the same login flow — the frontend and backend halves of one integration, split by where the code runs.

Each stack agent runs the same three-phase pipeline — **pattern decision** (confirm the pattern is earned, not premature/stacked; detect the stack version) → **generate** (scaffold the pattern, persistence layer, and/or service-side auth wiring) → **review** (hostile senior review: pattern misuse, DI/async/type-safety violations, layering) — and is **brownfield-capable**: it orients on an existing codebase first (build/lint clean, seams to reuse), then only **fixes** a defect or **extends** a slice, re-entering just the touched phase(s), per `.skill-template/agent.md`.

**Peer handshakes** (named, not loaded): `qa-api-{java,dotnet,typescript}` write the contract/integration tests against the API a `be-*` agent implements (`qa-*-{java,dotnet}`'s `auth0-test-tokens` skill mints test tokens against the login flow a `be-*` auth skill validates); `qa-security` owns the DAST/SAST/SCA/access-control gates; `qa-cicd-{java,dotnet,typescript}` wires build+test into CI; `data-architect` owns schema/DDL/index design and cross-engine migration strategy whenever the persistence need goes beyond ORM mechanics — the backend `persistence` skill stays in its lane (EF Core / JPA / Prisma mechanics only).

New-project setup = copy `backend/_shared/` + the `backend/<stack>/` you need.

### Backend code rules

- One pattern per problem — flag stacking (e.g. Repository + Unit-of-Work + Specification + Mediator + Decorator on one CRUD slice) as a smell in reviews, per the global Pattern-application rule.
- Constructor injection (or closures, in idiomatic TS) — never a service locator; no static/module-level mutable state; async all the way (never block on a `Task`/`Promise`, never `.Result`/`.Wait()`/`.then().catch()` chains for new code).
- Read 2–3 existing representative files before writing any new one; match the project's conventions (DI container, folder layout, naming) over a skill's defaults.
- Every public API gets a contract test before integration tests — coordinate with the matching `qa-api-<stack>` peer for the test layer; a `be-*` agent produces the implementation only.

### Version policy (`backend/`)

Every stack skill is **version-aware**, mirroring the rest of the library: the agent's first act on an existing project is version detection (TFM / Java release + Spring Boot BOM / Node major from `package.json`), and every recipe is keyed to what's detected. **.NET 10 primary / 8-9 supported** (EF Core major matches the TFM major) · **Java 21 + Spring Boot 3.x** · **Node 24 primary / 22 maintenance supported** (Node 20 is EOL since April 2026 — flag it, don't target it). Never apply an up-level-only API to a down-level project, and never flag a down-level project for lacking one.

## Observability catalog

The `observability/` folder is the **telemetry** domain — the Grafana-stack sibling of `backend/`, distinct from `qa/` (which tests the service this instruments) and `data/` (which owns the schema). It is **not a standalone plugin**: its skills and agents are **bundled into the three `be-*` plugins** so a backend install carries observability with it. The design standardizes on the library's Observability default (root Stack defaults): **OpenTelemetry → Grafana stack** — Loki (logs), Prometheus/Mimir (metrics), Tempo (traces), all fed through a single **OTel Collector** as the seam, with cross-store navigation (exemplars metrics→traces, Loki derived fields logs→traces) as the payoff.

**Skill shapes.** Two, like the rest of the library:
- **Per-stack** (`opentelemetry-{dotnet,java,node}`, `structured-logging-{dotnet,java,node}`) — the instrumentation + logging skills, one implementation per stack (OTel .NET SDK + Serilog · OTel Java agent + SLF4J/Logback · `@opentelemetry/sdk-node` + pino). Version-aware to the stack's version policy.
- **Stack-agnostic** (`loki-tempo-setup`, `prometheus-mimir-setup`, `logql-promql`, `grafana-dashboards`) — the backend + query + dashboard skills shared by all three stacks. `loki-tempo-setup` stands up the Collector hub + logs/traces backend and log forwarding (**Grafana Alloy** default; Promtail is deprecated/EOL 2026); `prometheus-mimir-setup` owns the metrics backend (Prometheus single-cluster vs Mimir multi-cluster/long-retention), exemplar storage, and rule *deployment*; `logql-promql` owns query + recording/alert-rule *syntax*; `grafana-dashboards` owns panel layout + cross-store nav wiring.

**Agents** — one phased **`observability-engineer-{dotnet,java,node}`** per stack, bundled into the matching `be-*` plugin as a sibling of the `be-<stack>` agent. Six phases: Discover (detect stack version + existing telemetry) → Backend setup (`loki-tempo-setup` + `prometheus-mimir-setup`) → Instrument (the stack's `opentelemetry-*` + `structured-logging-*`) → Query & dashboards (`logql-promql` + `grafana-dashboards`) → Hostile review (cardinality audit, cross-store nav wired, no direct-to-backend exporters). Loads **only** `observability/*` skills (+ the bundled `ep-*` for brownfield); brownfield-capable (orient → FIX/EXTEND, re-entering only touched phases) per `.skill-template/agent.md`.

**Peer handshakes** (named, not loaded): `be-{stack}` (the service being instrumented — sibling in the same plugin), `qa-cicd-{stack}` (CI wiring for the telemetry-emitting build), `qa/manual/quality-metrics` (the SLO/KPI math the recording rules encode), `devops/kubernetes` + `devops/iac-bicep-terraform` (cluster manifests + object-storage buckets/IAM for the backends).

The two invariants every design holds: **bounded metric cardinality** (per-record ids — `order.id`, `user.id`, `trace_id` — are span attributes, never metric labels) and **the Collector as the seam** (apps export OTLP to the Collector, never straight to Tempo/Prometheus, so sampling/routing changes without an app redeploy).

### Version policy (`observability/`)

Every stack-bound skill is **version-aware**, keyed to the same policy as `backend/`: **.NET 10 primary / 8-9 supported** (prefer the portable `RecordException` over the net9+ `Activity.AddException`) · **Java 21 + Spring Boot 3.x** (pin all OTel artifacts to one release train) · **Node 24 primary / 22 maintenance** (Node 20 EOL since April 2026 — flag it). The stack-agnostic skills track current tooling: **Grafana Alloy** (not Promtail), **Prometheus 3.x** (native histograms stable), **Mimir** for scale.

New-project setup = install the `be-<stack>` plugin (observability comes bundled).

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

## DevOps catalog

The `devops/` folder is the **platform / delivery** domain — the path from a built service to a running one. It sits beside `backend/` (which writes the service) and `observability/` (which instruments it), and is shipped as the self-contained **`devops`** plugin. Unlike the stack-first domains, devops is **cloud-keyed, not stack-triplicated**: the skills wrap Dockerfiles, IaC, cloud primitives, and pipeline YAML, none of which split usefully three ways, so there is **one skill per tool/cloud** and **one stack-agnostic agent**. Skill names carry the `devops-*` prefix.

**Skills** (`devops/<skill>/`, name `devops-<skill>`):
- **Image** — `docker` (multi-stage builds, base-image choice per detected version, layer optimization, non-root + healthcheck, image scanning)
- **Infrastructure** — `iac-bicep-terraform` (Bicep for Azure-only stacks, Terraform for AWS/multi-cloud; module structure, remote+locked state, `prevent_destroy`) · `kubernetes` (manifests, Helm, Kustomize overlays, Deployment/Service/Ingress/HPA/PDB, IRSA / Workload Identity, for AKS/EKS/GKE)
- **Deploy** — `aws-deployment` (ECS Fargate default, Lambda, App Runner, S3+CloudFront with OAC, EKS) · `azure-deployment` (Container Apps default, Functions, App Service, Static Web Apps, AKS). Each opens with a primitive-decision matrix keyed to workload shape
- **Pipeline** — `github-actions` · `gitlab-ci` · `azure-pipelines` (kept as three full authoring surfaces rather than a one-of-N router: each is a 300+ line surface, the host is repo-determined so no decision matrix is needed, and ~10 inbound references already point at the three paths)
- **Config** — `environment-config` (typed config classes, secret stores — Key Vault / Secrets Manager / Parameter Store / Vault, layering defaults → per-env → secrets, startup schema validation, hot-reload)

**Agent** — one stack-agnostic **`devops-engineer`** (`devops/agents/devops-engineer.md`), six phases: **Discover** (detect stack version + cloud + CI host + existing infra; pick the deploy primitive from workload shape) → **Containerize** (`docker`) → **Provision** (`iac-bicep-terraform`, + `kubernetes` for k8s targets) → **Deploy** (`{aws,azure}-deployment`) → **Pipeline & config** (the detected CI host + `environment-config`) → **Hostile review** (OIDC-only audit, pinned tags/digests/actions, non-root + probes + resource requests, min-replicas, tags on every resource, remote+locked state, no plaintext secrets). Loads **only** `devops/*` skills (+ the bundled `ep-*` for brownfield); brownfield-capable (orient → FIX/EXTEND, re-entering only touched phases) per `.skill-template/agent.md`. Ships a **`/devops-engineer` slash command** as the deterministic entry point.

**The two invariants every design holds:** **no static cloud credentials** (OIDC / Workload Identity Federation from the pipeline; Managed Identity / IRSA / task role at runtime — a long-lived key is a blocker finding) and **pin everything** (base images by tag, actions/tasks by major or SHA, language versions to what the project targets, the pnpm version sourced from `package.json` `packageManager` and never double-pinned in CI).

**The scope fence users trip on — deploy lane vs test lane.** `devops/{github-actions,gitlab-ci,azure-pipelines}` own the **build/deploy** pipeline; `qa/cicd/<stack>/skills/ci-pipelines` + `qa-cicd-{stack}` own the **test-suite** lane (shard matrix, Allure publishing, perf gate, flake quarantine). All three devops CI skills upload raw test results as artifacts and hand off — they never generate or publish an Allure report.

**Peer handshakes** (named, not loaded): `be-{dotnet,java,node}` (the service being shipped — build command + artifact path), `observability-engineer-{stack}` (devops provisions the buckets/IAM their backends need), `qa-cicd-{stack}` (the test lane in the same pipeline file), `qa-security` (`qa-security-testing-container-iac-scanning` owns the Trivy gate policy; devops wires the image build it scans), `data-architect` (devops provisions the server/network/identity; data-architect owns the schema), `fe-{blazor,react}` (static-hosting target + build output directory).

### Version policy (`devops/`)

Every version-sensitive skill is **version-aware**, keyed to the root Stack defaults: **.NET 10 primary / 8-9 supported** (8 LTS ends Nov 2026) · **Java 21 LTS** · **Node 24 active LTS / 22 maintenance** (Node 20 EOL since Apr 2026 — flag it, don't target it). The agent's first act on an existing project is version + platform detection (TFM, JDK + Boot BOM, Node major, CI host, cloud), and every recipe is keyed to what's detected. **Managed runtimes lag the language** — pin to the newest runtime the platform actually offers for the project's major, and never silently up-level the app to reach one. `iac-bicep-terraform` and `kubernetes` carry no stack-version policy (they are tool- and API-version bound, not stack-bound).

New-project setup = copy `devops/` (all 9 skills + the agent), or install the `devops` plugin.

## Engineering-practices catalog

The `engineering-practices/` folder is the **developer-workflow spine** — the language-agnostic idea → spec → plan → execute → verify → finish loop that sits *beside* the `qa/` and `frontend/` domains rather than inside them. The 14 in-scope skills (the 12 workflow skills adapted from obra/superpowers, self-contained: they reference only each other — plus the 2 audit skills) and the domain's one agent (`code-auditor` — the deliberate exception to "skills-only") are **bundled into every stack plugin** (the eight `qa-*` / `fe-*` / `be-*` plugins) — no standalone plugin. All skills use the `ep-*` name prefix.

**The chain** (each skill announces itself and hands to the next):
- `ep-brainstorming` — turn an ad-hoc idea into an approved design/spec (`docs/specs/YY-MM-DD-HHmm-<topic>-design.md`, written on the current branch); HARD-GATE before any code. **Scoped:** a phased agent with its own design gate (`fe-blazor`, the `qa-*` orchestrators) already satisfies the gate — do not run this on top of them. Its browser **visual companion** is opt-in on explicit request only. → `ep-writing-plans`
- `ep-writing-plans` — approved spec → detailed bite-sized implementation plan (`docs/plans/YY-MM-DD-HHmm-<feature>.md`, written on the current branch), one action per step, complete code in every step. → `ep-executing-plans`
- `ep-executing-plans` — execute a written plan task-by-task, reporting at a checkpoint after each task (task list via TaskCreate/TaskUpdate); stops when blocked. The **default** (inline) execution path; `ep-subagent-driven-development` is the opt-in alternative. → `ep-finishing-a-development-branch`
- `ep-finishing-a-development-branch` — tests-pass gate → structured merge/PR/keep/discard options → provenance-based worktree cleanup.

**Cross-cutting** (entered anytime, not part of the linear chain):
- `ep-test-driven-development` — the dev-side red-green-refactor **inner loop**. Complements `qa/` (which owns suite architecture, page objects, builders); this owns only the loop. Reconciles with the CLAUDE.md test rules — no conflict (per "skill wins for its domain", both agree).
- `ep-systematic-debugging` — root-cause-first, four-phase debugging; writes the failing test via `ep-test-driven-development`, confirms via `ep-verification-before-completion`.
- `ep-verification-before-completion` — evidence-before-claims gate before any "done/fixed/passing" statement or commit/PR. Reinforces the global "report outcomes faithfully" rule.
- `ep-using-git-worktrees` — isolated-workspace setup; prefers the harness's native worktree tool (`EnterWorktree`) over the git fallback.

**Agent-dispatch (opt-in, cost-aware — governed by the Conservative agent-spawning policy):**
- `ep-subagent-driven-development` — execute a plan by delegating self-contained tasks to subagents. The **opt-in exception** to inline `ep-executing-plans`, not a replacement — use only when delegation clearly pays for itself. Default flow is 1 implementer subagent per task + **inline** controller review (spec then quality, CLAUDE.md severity-table format); dedicated reviewer subagents are a cost-weighed escalation.
- `ep-dispatching-parallel-agents` — fan genuinely independent problems out to concurrent agents. The cost-aware exception to sequential/inline work.
- **The policy (both skills):** *cost before speed* — inline/sequential is the default; spawn only when it pays for itself; and **every additional agent is a deliberate spend** — fan out to as many as the independent domains genuinely warrant, and say what you are spawning and why rather than fanning out silently. This deliberately tempers the upstream speed-first defaults ("fresh subagent per task", "3+ failures → one agent each"). It aligns with the harness's own guidance to spawn agents conservatively.

**Code review (the request/receive pair, entered around finishing & subagent-driven work):**
- `ep-requesting-code-review` — get a completed change reviewed before it cascades. Preference order: **native review command** (e.g. `/code-review`) → **inline self-review** (the controller rubric) → **reviewer subagent** (a deliberate extra invocation). Carries the `code-reviewer.md` prompt template; findings in the CLAUDE.md severity table. Named by `ep-finishing-a-development-branch` (before merge/PR) and `ep-subagent-driven-development` (the escalation off its default inline review).
- `ep-receiving-code-review` — the receiving half: verify feedback before implementing, fix by severity (blocker → nit), push back with technical reasoning, no performative agreement.

**Audit (read-only analysis of existing code — the `code-auditor` agent at `engineering-practices/agents/code-auditor.md` owns both, stack-agnostic, static-first with execute-opt-in evidence). Every run is one of two modes × one of two lanes:**
- **Mode A — BASELINE** (first audit: build the stable spine, verdict everything, save Round 1) · **Mode B — RE-AUDIT** (reload the spine, re-trace every item **fresh**, prefix each **Resolved / Resolved (differently) / Still open / Still open (regressed) / New**, save Round N). **EXTEND** (new stories/surfaces) is a Mode A variant that appends with the next free IDs, never renumbering. Artifacts live in `docs/audits/`: `…-requirements.md` (append-only register) + one `…-audit-r<N>.md` per round — rounds are never overwritten, IDs never reused, so the trend ("12 open at r1 → 4 at r2") is real.
- `ep-spec-compliance-audit` (**SPEC lane** — a spec, *or a set of stories/ACs/tickets*) — Mode A's first act is **consolidation**: merge the sources into one deduped, **lettered-section**, ID-stable requirement register and **save it before reading any product code** (same source stated twice → one entry, two citations; sources contradicting → a paired `⚠️ CONFLICT`, both verdicted, owner decides). Then per-requirement verdicts **Met / Partial / Missing / Divergent / Unverifiable** with `file:line` evidence (`#confirmed`/`#inferred`; negative claims name the search) → coverage metrics + severity-tabled findings. Loads `qa/manual/test-basis-analyzer` (loaded-not-owned, bundled into all eight stack plugins) to distill raw-prose sources first. `Divergent` always escalates to the owner — the auditor never picks spec vs code.
- `ep-feature-audit` (**FEATURE lane** — a feature/area by name, no spec) — declared scope + **driving question** → lettered surface decomposition (the report *is* the register here) → three inventories (functionality narrative · **validations & gates** · integration map with per-boundary trust assumptions) → findings, each = mechanism + concrete failure scenario/impact band + severity + fix direction, grouped into **defect families** → priority table + **leverage-ordered** recommended sequencing. Mode B re-traces each finding then **sweeps its defect family** (a fix at one site routinely misses siblings). The report is a first-class test-basis input for `qa/manual/test-basis-analyzer` (finding boundary conditions are BVA seeds).
- **Every section/surface closes with a rollup summary** — one per section, never per item, 2–4 sentences of *judgment* (state · pattern · next action), distinct from the arithmetic Movement/metrics block. **Resolved is only claimed after re-reading the code that round** — commits, ticket status, and green tests are leads, never evidence.
- **Fences:** never fixes (the owning `be-*`/`fe-*` agent applies remediation); security *attacks* belong to `qa-security` (the audit's gates inventory is its starting map); spec-vs-spec conflicts belong to `business-analyst`; pre-implementation story audits belong to `ba-backlog-auditor`.

**Reconciliation with global rules:** where a process skill and a global rule touch — `ep-test-driven-development` vs the Test code rules, the `ep-brainstorming` HARD-GATE vs the phased-agent design phases, `ep-verification-before-completion` vs "report outcomes faithfully" — the existing "skill wins for its domain" rule already governs; the skills are written to agree with the global rules, so no override is triggered in practice.

## Business-analysis catalog

The `business-analysis/` folder is the **upstream requirements domain**, organized in **two lanes** and shipped as the self-contained `business-analysis` plugin. The **authoring lane** turns a vague stakeholder ask into refinement-ready artifacts (scoping writeup → epics → INVEST stories, plus a review-only backlog audit). The **reasoning lane** is the cross-feature business-flow layer — it sits *upstream* of `qa/manual/` (which distills one feature for testing) and owns what nothing else does: detecting conflicts **between features** and keeping a **persistent per-project business model** so later sessions reason with whole-project context. Language-agnostic skills + one phased orchestrator agent per lane. (The pure-communication skills — `stakeholder-updates`, `meeting-notes`, `incident-postmortem` — stayed in `communication/`, which remains under construction.)

**The KB (`docs/business-model/` in the target project)** — versioned, diffable, Cline-Memory-Bank-shaped: `INDEX.md` (read first, every session) · `glossary.md` · `flows/` · `entities/` · `decisions/` · `interaction-map.md` (resolved conflicts + rationale) · `active-context.md` (dynamic tier). Contract: **read-first / update-after**; stable IDs (`FLOW-`/`ENT-`/`DEC-`/`CONF-`) + source traceability; annotation grammar `[TBD - reason]` · `⚠️ Assumption:` · `#confirmed`/`#inferred`/`#observed`.

**Authoring-lane skills** (`business-analysis/skills/`, `ba-*`):
- `ba-initiative-scoping` — vague business problem / stakeholder ask → structured single-initiative scoping writeup (problem statement, goals + measurable success metrics, stakeholder map, in/out/deferred scope, constraints, likelihood×impact risks, assumptions, open questions); includes the elicitation question bank for driving discovery
- `ba-epic-writer` — scoped writeup → one or more epics, each with a one-sentence WHO / DO WHAT / SO THAT MEASURABLE outcome, a named slicing strategy, anticipated child stories, explicit out-of-scope, epic-level DoD; sizing heuristics (story set vs epic vs program)
- `ba-story-writer` — scoped requirement / epic → INVEST user stories with Gherkin AC (one behavior per scenario), functional vs non-functional AC separated, story-level out-of-scope + dependencies
- `ba-backlog-auditor` — review-only readiness audit of stories/epics **authored elsewhere** (client, another team, a PO): INVEST + AC quality + testability + backlog hygiene checks, per-story verdicts, severity-tabled findings; never rewrites — routes fixes to `ba-story-writer` / `ba-epic-writer`

**Reasoning-lane skills** (`business-analysis/skills/`, `ba-*`):
- `ba-project-knowledge` — the KB protocol every reasoning-lane skill loads (layout, contract, authoring rules, init)
- `ba-flow-mapper` — requirements → BPMN-disciplined Mermaid flow (named actors/swimlanes, every decision exit incl. failure labeled, boundary events, precondition→action→postcondition steps, event-timeline pass)
- `ba-state-modeler` — **one state × event grid per business entity**, all features overlaid, transitions annotated with owning feature; conflict surfaces: double-fire, state interference, orphan transitions, silent `—` assumptions
- `ba-decision-modeler` — **one merged decision table per shared decision point** with a declared DMN hit policy (U/A/F/P/C); completeness check = gaps, overlap check = contradictions, missing Collect operator = missing stacking rule; precedence is a *business decision to escalate, never invent*
- `ba-feature-conflict-sweep` — the quality gate: normalize the new feature into trigger/actor/action/data/constraint/state tuples → pairwise sweep against the KB with the **11-class conflict taxonomy** (contradictory rules · trigger overlap · state interference · resource contention · ordering/race · circular dependency · policy stacking · permission/authority · duplication/subsumption · terminology drift · boundary divergence) → **every finding gets a concrete boundary condition** → severity table; resolutions recorded in `interaction-map.md`

**Agents** — one per lane, peers that name each other:
- `business-analysis/agents/requirements-author`: the authoring lane. Five input modes (raw ask / scoped writeup / epics-provided / stories-authored-elsewhere), four phases (Initiative scoping → Epic shaping → Story refinement → Backlog audit 3R on-demand). Loads **only** the four authoring-lane skills; reuses the KB's glossary/IDs when one exists but never edits it. Downstream defaults: `business-analyst` sweep when stories touch shared rules, then `qa/manual/test-basis-analyzer` / `qa-manual-test-designer`.
- `business-analysis/agents/business-analyst`: the reasoning lane. Three modes (analyze / model / audit), six phases (Orient → Normalize → Model per selection matrix → Sweep → Resolve & persist → Report). Loads **only** `business-analysis/*` skills. **Brownfield-capable** like every agent in the library: on a populated KB it orients (KB inventory + staleness signals), then fixes (source-changed vs model-defect vs unresolved-conflict triage — never invents precedence) or extends (folds a new feature into the existing model, reusing stable IDs and glossary) with a `Mode: FIX | EXTEND` KB-delta report; the discipline is inlined since this plugin doesn't bundle `ep-*`.

**Scope fence vs `qa/manual/*`:** `test-basis-analyzer` keeps single-story distillation; `test-design-techniques` keeps decision-/state-table *test-design mechanics* (rule coverage, n-switch); this domain owns requirements authoring + the cross-feature models + the sweep and **never produces test cases**. The three document-ingestion altitudes fence each other explicitly: `ba-initiative-scoping` (one initiative, for scoping) · `ba-feature-conflict-sweep` (cross-feature, against the KB) · `qa/manual/test-basis-analyzer` (one doc, for testing). Handshakes: story sets are the sweep's normalization input; KB artifacts are first-class test-basis inputs; sweep boundary conditions are BVA seeds; `qa-manual-test-designer` names `business-analyst` as the upstream peer.

New-project setup = copy `business-analysis/` (all 9 skills + both agents).
