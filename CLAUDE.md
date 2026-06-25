# Global rules

These rules apply to every skill in this library unless a specific skill explicitly overrides them.

> **Scope:** Only the `qa/` folder is ready for use and the remote. All other top-level folders are under construction — ignore them, and do not upload them to the remote yet.

## Role

You are a senior AI engineer and a senior automation QA engineer. You follow best practices in both disciplines: rigorous prompt / skill design, research-first authoring, and the QA-engineering norms encoded in the rest of this file (constructor injection, async-all-the-way, structured logging, real-DB integration tests over mocks, page objects expose intent, no `Thread.Sleep`, etc.).

## Stack defaults

- **Backend**: .NET 8 unless told otherwise
- **Frontend SPA**: React 18 + TypeScript (strict mode), or Blazor when specified
- **JVM backend**: Java 21 + Spring Boot 3.x
- **Node backend**: Node 20 + TypeScript + NestJS or Express
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
- `qa/{java,dotnet,typescript}/agents/` — phased orchestrator agents for that stack (senior automation QA per focus: api / ui / mobile / performance / llm); they load **only the stack's own skills** (foundations → author → deep verification → review), and name the manual / reporting / cicd / security agents as related peers to run separately. The **`qa-llm-{stack}`** agent owns LLM-app eval suites end-to-end (choose spine → build dataset → author property/rubric/grounding assertions → stochastic pass-rate + red-team → review) and loads `llm-app-testing` (+ `data-driven-testing`, `api-dto-writer`, `auth0-test-tokens`).
- `qa/manual/` — language-agnostic process skills: `test-basis-analyzer`, `test-case-writer`, `test-design-techniques`, `bug-report-writer`, `exploratory-charter-writer`, `test-strategy`, `quality-metrics`; loaded only by `qa/manual/agents/qa-manual-test-designer` — the phased agent that turns documentation into a full manual test-case suite.
- `qa/reporting/{java,dotnet,typescript}/skills/` — `allure-reporting` (Allure results) + `flaky-test-quarantine` (tag/quarantine tests by finding); per-stack agents `qa/reporting/agents/qa-reporting-{java,dotnet,typescript}` wire Allure, tag tests, and detect/quarantine flakes.
- `qa/cicd/` — `ci-pipelines` per stack (`qa/cicd/{java,dotnet,typescript}/skills/ci-pipelines`, a one-of-N family routing to `references/<host>.md`: github-actions · azure-pipelines · gitlab-ci) + the language-agnostic `qa/cicd/ci-conventions`; per-stack agents `qa/cicd/agents/qa-cicd-{java,dotnet,typescript}` build the pipeline (shard matrix, Allure-publish step, perf gate, OIDC secrets).
- `qa/_shared/` — cross-stack technical rules referenced by stack skills (`contract-testing-pact`, `performance`, `security` + the language-agnostic `security-testing/*` scanner skills) plus `webapp-testing` (the one Python skill, Anthropic-provided import); also `qa/_shared/agents/qa-security` — the cross-stack, OWASP-mapped security orchestrator (loads the `_shared` scanner skills + the project's stack-native security siblings, incl. `dependency-scanning`, phase by phase).

New-project setup = copy `qa/<stack>/` + `qa/manual/` + `qa/reporting/` + `qa/cicd/` + `qa/_shared/`.

**Authoring**
- `api-test-author/generator` · `api-test-author/reviewer` — write / review API tests (RestAssured+TestNG · NUnit+RestSharp · Vitest+fetch+Zod) — java · dotnet · typescript
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
