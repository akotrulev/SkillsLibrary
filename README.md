# SkillsLibrary

A shared library of Claude skills and rules for backend, frontend, DevOps, observability, and QA work. Designed to be consumed by Claude Code, Claude Desktop, and CI agents across multiple repos.

## How to use

### Install as a Claude Code plugin (recommended)

The repo is a Claude Code plugin marketplace. Add it once, then install the one plugin for your tech stack — Claude Code handles fetching and updates, no cloning or syncing required:

```shell
/plugin marketplace add akotrulev/SkillsLibrary
/plugin install qa-java@skills-library             # complete Java 21 QA toolkit
/plugin install qa-dotnet@skills-library           # complete .NET 8 / C# QA toolkit
/plugin install qa-typescript@skills-library       # complete TypeScript QA toolkit
/plugin install fe-blazor@skills-library           # complete Blazor (.NET 8/9/10) frontend toolkit
/plugin install fe-react@skills-library            # complete React 19/18 (Next.js App Router / Vite) frontend toolkit
/plugin install be-dotnet@skills-library           # .NET 10 backend design-pattern + EF Core + Auth0/Cognito toolkit
/plugin install be-java@skills-library             # Java 21 / Spring Boot backend design-pattern + JPA + Auth0/Cognito toolkit
/plugin install be-node@skills-library             # Node 24 / TypeScript backend design-pattern + Prisma toolkit
/plugin install data@skills-library                # complete database-engineering toolkit (8 engines)
/plugin install business-analysis@skills-library   # cross-feature business-flow analysis toolkit
```

**One self-contained plugin per language** — `qa-java`, `qa-dotnet`, `qa-typescript`. Each is a complete QA toolkit for its stack: it bundles every discipline (API / UI / mobile / performance / LLM authoring and review, BDD living documentation, deep verification, contracts, chaos, feature flags) **plus** the shared, cross-cutting capabilities that used to be separate peer plugins:

- **Manual QA** — the language-agnostic `qa/manual` process skills and the `qa-manual-test-designer` agent (test-basis analysis, ISTQB design techniques, test-case / bug-report / charter writing).
- **Security** — the cross-stack, OWASP-mapped `qa/_shared` scanner gates (ZAP, SAST, secrets, container/IaC, API fuzzing, Nuclei, TLS), the stack-native security skills (BOLA/IDOR/BFLA access-control matrix, ZAP baseline, SCA), and the `qa-security` orchestrator agent.
- **CI/CD** — the stack's `ci-pipelines` skill (GitHub Actions / Azure Pipelines / GitLab CI), the language-agnostic `ci-conventions`, and the `qa-cicd-<stack>` agent.
- **Reporting** — Allure results wiring + flaky-test detection/quarantine and the `qa-reporting-<stack>` agent.

So installing a single plugin gives you the stack's authoring/verification skills, its api/ui/mobile/performance/llm/bdd agents, and the manual / security / cicd / reporting skills and agents — no peer plugins to add. (.NET additionally ships `*-project-scaffold` skills that stand up a complete runnable .NET 8 test solution from zero.)

**The other plugins:**

- **`fe-blazor`** — the Blazor (.NET 8/9/10) frontend **development** stack: 22 `fe-blazor-*` skills (scaffold, state, styling, forms, data access, realtime, quality layers, bUnit tests, hostile reviewer), the phased `fe-blazor` orchestrator agent, plus the bundled `design/*` craft skills and `auth/auth0-blazor`.
- **`fe-react`** — the React 19/18 + TypeScript frontend **development** stack (Next.js 15 App Router / RSC primary, Vite SPA fallback, MUI default): 24 `fe-react-*` skills, the phased `fe-react` orchestrator agent, plus the bundled `design/*` craft skills, `auth/auth0-react`, and the vendored Vercel performance/composition/view-transitions seeds. Includes `/fe-react-audit` — a one-call, read-only conformance sweep of an existing codebase against every convention the plugin defines, saved as a re-runnable findings report in `docs/audits/`.
- **`be-dotnet`** — the .NET (10 primary / 8-9 supported) backend **design-pattern + persistence** stack: `reference`/`generator`/`reviewer`/`persistence` (EF Core) + `auth0`/`cognito` (JWT bearer validation, RBAC, Client Credentials M2M), the phased `be-dotnet` orchestrator agent, plus the bundled `backend/_shared` pattern cards and `auth/_shared/{auth0-concepts,oidc-concepts}`.
- **`be-java`** — the Java 21 + Spring Boot 3.x backend **design-pattern + persistence** stack: the same five skills, Spring-idiomatic (JPA/Hibernate + Spring Data, Spring Security OAuth2 Resource Server for `auth0`/`cognito`), the phased `be-java` orchestrator agent, plus `backend/_shared` and `auth/_shared/{auth0-concepts,oidc-concepts}`.
- **`be-node`** — the Node (24 primary / 22 maintenance) + TypeScript strict backend **design-pattern + persistence** stack: `reference`/`generator`/`reviewer`/`persistence` (Prisma default / Drizzle / TypeORM), the phased `be-node` orchestrator agent, plus `backend/_shared` (no `auth0`/`cognito` skill yet — a known gap).
- **`data`** — the database-engineering stack: 8 version-aware per-engine skills (PostgreSQL, SQL Server / Azure SQL, MySQL, MongoDB, Redis / Valkey, DynamoDB, Cosmos DB, Elasticsearch / OpenSearch), 4 cross-engine `_shared` skills (schema-design, migrations, caching-patterns, query-optimization), and the phased `data-architect` agent.
- **`business-analysis`** — the upstream requirements domain in two lanes: 9 `ba-*` skills and 2 agents. The **authoring** lane (`ba-initiative-scoping`, `ba-epic-writer`, `ba-story-writer`, `ba-backlog-auditor` + the `requirements-author` agent) turns a vague stakeholder ask into refinement-ready artifacts; the **reasoning** lane (`ba-project-knowledge`, `ba-flow-mapper`, `ba-state-modeler`, `ba-decision-modeler`, the 11-class `ba-feature-conflict-sweep` + the `business-analyst` agent) keeps a persistent per-project business model and detects conflicts between features.

Every stack plugin (`qa-*`, `fe-*`, `be-*`) also bundles the 14 `ep-*` engineering-practices skills (brainstorm → plan → execute → verify → finish, TDD, systematic debugging, worktrees, agent dispatch, code-review pair, and the spec-compliance/feature audit pair) plus the read-only `code-auditor` agent. A 15th, `ep-conformance-audit`, is the shared engine behind the per-stack conformance audits — it ships only in the plugins whose stack audit exists so far (`qa-dotnet`, `be-dotnet`; `fe-react` carries its own copy pending the extraction), and rolls out with each remaining stack per `CONFORMANCE-AUDIT-PLAN.md`. Pull updates later with `/plugin marketplace update skills-library`.

### Slash commands

**Every agent ships a matching slash command.** Agents are normally picked up by description match, which is probabilistic; the command is the deterministic entry point for when you would rather *name* the workflow than hope for it. Each command loads its agent definition and runs that agent's phased workflow **inline in the current session** — no subagent is spawned unless you ask for one. Called bare with no argument, it runs the agent's orientation pass against the current repo and asks what you need.

**`qa-java` · `qa-dotnet` · `qa-typescript`** — 11 commands each (`qa-dotnet` has 12 — see `/qa-dotnet-audit` below); substitute your stack for `<stack>`:

| Command | Argument | Runs |
|---|---|---|
| `/qa-api-<stack>` | endpoints or suite to cover | scaffold, author, and review API test coverage |
| `/qa-ui-<stack>` | flow, URL, or suite | scaffold, author, and review web UI coverage (or build a POM from a URL) |
| `/qa-mobile-<stack>` | app flow or suite | scaffold, author, and review native/hybrid mobile coverage |
| `/qa-performance-<stack>` | service or workload | design, author, review, and CI-gate a load-test suite |
| `/qa-llm-<stack>` | LLM feature | build an eval dataset, assert properties/rubrics/grounding, red-team |
| `/qa-bdd-<stack>` | test-case suite or features | test cases → feature files → step definitions bound to page objects |
| `/qa-cicd-<stack>` | pipeline to build or harden | shard matrix, gates, OIDC secrets, result publishing |
| `/qa-reporting-<stack>` | what to wire, tag, or quarantine | wire Allure, tag tests by finding, detect and quarantine flakes |
| `/qa-manual-test-designer` | doc, story, contract, or URL | documentation (or a live page) → a systematically-derived test-case suite |
| `/qa-security` | app, API, or layer | OWASP-mapped SAST, secrets, SCA, access-control, DAST, fuzzing, container/IaC, TLS gates |
| `/qa-dotnet-audit` *(qa-dotnet only so far)* | *(none — or a path/section limiter)* | read-only sweep of the **test suite** against the `qa-dotnet` conventions → findings report in `docs/audits/` |
| `/code-auditor` | spec, stories, feature, or area | read-only audit engagement, saved to `docs/audits/` |

**`fe-blazor`** — 2 commands · **`fe-react`** — 3:

| Command | Argument | Runs |
|---|---|---|
| `/fe-blazor` | what to build, fix, or extend | the phased Blazor Web App UI workflow |
| `/fe-react` | what to build, fix, or extend | the phased React / Next.js UI workflow |
| `/fe-react-audit` | *(none — or a path/section limiter)* | read-only sweep of the repo against the `fe-react` conventions → findings report in `docs/audits/` |
| `/code-auditor` | spec, stories, feature, or area | read-only audit engagement, saved to `docs/audits/` |

**`be-dotnet` · `be-java` · `be-node`** — 3 commands each (`be-dotnet` has 4 — see `/be-dotnet-audit` below; note the backend stacks are `dotnet` / `java` / **`node`**, not the QA triplet):

| Command | Argument | Runs |
|---|---|---|
| `/be-dotnet` · `/be-java` · `/be-node` | what to build, fix, or extend | apply a design pattern, the persistence layer, or service-side auth |
| `/observability-engineer-dotnet` · `-java` · `-node` | what to instrument, query, or dashboard | OTel, structured logging, Grafana backends, dashboards |
| `/be-dotnet-audit` *(be-dotnet only so far)* | *(none — or a project/section limiter)* | read-only sweep of the service against the `be-dotnet` conventions (incl. the observability invariants) → findings report in `docs/audits/` |
| `/code-auditor` | spec, stories, feature, or area | read-only audit engagement, saved to `docs/audits/` |

**`data`** — 1 command:

| Command | Argument | Runs |
|---|---|---|
| `/data-architect` | what to model, secure, migrate, or tune | model, secure, implement, and tune a schema across 8 engines |

**`business-analysis`** — 2 commands:

| Command | Argument | Runs |
|---|---|---|
| `/requirements-author` | ask, brief, epics, or stories | scope an initiative, shape epics, write INVEST stories, audit a backlog |
| `/business-analyst` | feature or change to analyze | model flows, states and decisions, sweep for cross-feature conflicts, persist the KB |

`/code-auditor` ships in all eight stack plugins (`qa-*`, `fe-*`, `be-*`) alongside the `ep-*` skills. If two installed plugins expose the same command name, disambiguate with `/plugin-name:command`.

### Use the repo directly

1. Clone or submodule this repo into your project.
2. Reference skills from your project's `CLAUDE.md` or `.claude/settings.json`, or symlink the folders you need into your project's `.claude/skills/`.
3. The global rules in [`CLAUDE.md`](CLAUDE.md) apply to every skill in the library.

## Layout

```
backend/                # Backend dev stacks: dotnet/java/node pattern reference, generators, reviewers, persistence + be-* agents; _shared cross-stack pattern cards
data/                   # Per-engine skills (Postgres, SQL Server, MySQL, Mongo, Redis, DynamoDB, Cosmos, Elasticsearch) + shared (migrations, caching, query opt, schema design) + data-architect agent
frontend/               # Frontend dev stacks: blazor/ (fe-blazor skills + agent), react/ (fe-react skills + agent + vendored Vercel seeds), react-native/ (parked seed)
business-analysis/      # Cross-feature business-flow reasoning: ba-* skills + business-analyst agent
auth/                   # Auth0 setup per stack
devops/                 # Platform lane: docker, kubernetes, IaC (Bicep/Terraform), AWS/Azure deploy, CI pipelines, env config + devops-engineer agent
observability/          # Grafana, OpenTelemetry, structured logging
qa/                     # Test authoring (API/UI/perf), DB/email/network verification, CI pipelines, reporting (see QA skills below)
engineering-practices/  # TDD, debugging, code review, git worktrees, planning (from obra/superpowers)
meta/                   # Authoring skills themselves (writing-skills, skill-creator)
design/                 # Visual/UX: frontend-design, design-tokens, dataviz, brand-intake, iconography, ux-heuristics, theme-factory, ux-writing, web-design-guidelines
communication/          # BA, user stories, stakeholder updates, internal comms
ai-development/         # claude-api, mcp-builder
extras/                 # Off-mission, kept available: algorithmic-art, Office document generation (docx, pdf, pptx, xlsx)
```


## Skill layers

Each domain follows a three-layer model where it makes sense:

| Layer     | What it does                          | Example trigger                              |
|-----------|---------------------------------------|----------------------------------------------|
| reference | Explain a concept, show canonical code | "what is the strategy pattern in C#"        |
| generator | Scaffold code into the active repo    | "scaffold a strategy pattern for X"          |
| reviewer  | Critique existing code                | "review this for pattern misuse"             |

DevOps and Auth0 skills are mostly procedural, so they typically have one combined skill rather than three layers.

## QA skills

The `qa/` section is the most fully built-out part of the library. Most code-producing skills ship **three sibling stacks** — `java/`, `dotnet/`, and `typescript/` — each as its own `SKILL.md`. Shared cross-stack rules live in a `_shared/SKILL.md`. Process/non-code skills stay single-folder. Tool-bound skills ship only the stack(s) the tool supports.

### Authoring

| Skill | Stacks | What it does |
|-------|--------|--------------|
| `api-test-author/generator` | java · dotnet · typescript | Scaffold API tests (RestAssured+TestNG / NUnit+RestSharp / Vitest+fetch+Zod) |
| `api-test-author/reviewer` | java · dotnet · typescript | Review API tests for design/correctness |
| `api-client-writer` | java · dotnet · typescript | Scaffold typed API clients |
| `api-dto-writer` | java · dotnet · typescript | Generate request/response DTOs |
| `ui-test-author/playwright` | java · dotnet · typescript | Author Playwright UI tests |
| `ui-test-author/selenium` | java · dotnet · typescript | Author Selenium UI tests |
| `ui-test-author/appium` | java · dotnet · typescript | Author Appium mobile tests |
| `ui-test-author/reviewer` | java · dotnet · typescript | Review UI tests |
| `page-object-architect` | java · dotnet · typescript | Page-object architecture (intent-revealing) |
| `contract-testing-pact` | java · dotnet · typescript · _shared | Consumer/provider contract tests with Pact |
| `performance/k6` | typescript | Load tests with k6 (JS-native) |
| `performance/nbomber` | dotnet | Load tests with NBomber (.NET-only) |
| `performance/gatling` | java | Load tests with Gatling (JVM-only) |
| `performance/_shared` | — | Workload modelling, SLOs, perf gates |

### Verification inside tests

| Skill | Stacks | What it does |
|-------|--------|--------------|
| `db-testing/client` | java · dotnet · typescript | Connect, seed, query-assert, clean up |
| `db-testing/testcontainers` | java · dotnet · typescript | Postgres/SQL Server/Mongo/Redis lifecycle |
| `db-testing/query-author` | java · dotnet · typescript | Safe, parameterized assertion SQL |
| `email-testing` | java · dotnet · typescript | Capture/assert email — tool picked inside via `references/` (mailpit · mailosaur · gmail-imap · sendgrid-sandbox) |
| `messaging-testing` | java · dotnet · typescript | Produce/consume/assert against brokers — broker picked inside via `references/` (kafka · sqs · rabbitmq · service-bus) |
| `file-storage-testing` | java · dotnet · typescript | Object-storage assertions — store picked inside via `references/` (s3/LocalStack · azure-blob/Azurite) |
| `network-monitoring` | java · dotnet · typescript | Intercept/mock/throttle browser traffic — layer picked inside via `references/` (playwright-routes · cdp · proxy) |
| `websocket-sse-testing` | java · dotnet · typescript | Real-time WebSocket + SSE assertions |

### Grids & access

| Skill | Stacks | What it does |
|-------|--------|--------------|
| `cloud-grid-config` | java · dotnet · typescript | BrowserStack / Sauce / LambdaTest / Device Farm wiring |
| `auth0-test-tokens` | java · dotnet · typescript | M2M / ROPG / device-code tokens for test users |

### Reporting & CI/CD (`qa/reporting/`, `qa/cicd/` — own folders, own agents)

| Skill | Stacks | What it does |
|-------|--------|--------------|
| `reporting/<stack>/skills/allure-reporting` | java · dotnet · typescript | Allure results integration — loaded by `qa-reporting-<stack>` |
| `reporting/<stack>/skills/flaky-test-quarantine` | java · dotnet · typescript | Detect/quarantine flaky tests, tag tests by finding — loaded by `qa-reporting-<stack>` |
| `cicd/<stack>/skills/ci-pipelines` | java · dotnet · typescript | Shard matrix, Allure-publish step, perf gate, OIDC — CI host picked inside via `references/` (github-actions · azure-pipelines · gitlab-ci) — loaded by `qa-cicd-<stack>` |
| `cicd/ci-conventions` | language-agnostic | Pipeline conventions every `ci-pipelines` implementation references |

### Visual & test data

| Skill | Stacks | What it does |
|-------|--------|--------------|
| `visual-regression` | java · dotnet · typescript | Pixel-diff / visual review — tool picked inside via `references/` (playwright-snapshots · percy · applitools) |
| `accessibility-testing` | java · dotnet · typescript | A11y scans + budgets — tool picked inside via `references/` (axe-playwright · lighthouse-ci) |
| `test-data-builder` | java · dotnet · typescript | Builders / ObjectMother for test data |

### Process / planning (single-folder)

| Skill | What it does |
|-------|--------------|
| `test-case-writer` | Write structured test cases |
| `bug-report-writer` | Write actionable bug reports |
| `exploratory-charter-writer` | Write exploratory testing charters |
| `_shared/test-strategy` | Test strategy guidance |
| `_shared/quality-metrics` | Quality metrics guidance |
| `qa-webapp-testing` | UI automation with Python — Playwright web-app testing toolkit (Anthropic-provided import) |

## Adding a new skill

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and the templates in [`.skill-template/`](.skill-template/).

## Status

| Section               | State |
|-----------------------|-------|
| backend               | authored + shipped — `backend/_shared/` (2 pattern-card skills) + `backend/{dotnet,java,node}/` (4 skills each: reference/generator/reviewer/persistence) + a phased `be-*` agent per stack; `be-dotnet` additionally ships the `conformance-audit` self-audit skill + `/be-dotnet-audit`; `be-dotnet` / `be-java` / `be-node` plugins |
| data                  | authored + shipped — 8 version-aware per-engine skills (postgresql, sqlserver, mysql, mongodb, redis, dynamodb, cosmosdb, elasticsearch) + 4 cross-engine `_shared` skills + the `data-architect` agent; `data` plugin |
| frontend              | authored + shipped — `frontend/blazor/` (22 skills + `fe-blazor` agent; `fe-blazor` plugin) and `frontend/react/` (24 skills incl. the `conformance-audit` self-audit + `fe-react` agent + vendored Vercel seeds; `fe-react` plugin); `frontend/react-native/` parked, under construction |
| business-analysis     | authored + shipped — 9 `ba-*` skills (authoring + reasoning lanes) + the `requirements-author` and `business-analyst` agents; `business-analysis` plugin |
| auth                  | scaffolding |
| devops                | authored + shipped — 9 cloud/CI-keyed skills (docker, kubernetes, iac-bicep-terraform, aws-deployment, azure-deployment, github-actions, gitlab-ci, azure-pipelines, environment-config) + the `devops-engineer` agent; `devops` plugin |
| observability         | authored + shipped — 6 skills (per-stack `opentelemetry-*` / `structured-logging-*` + stack-agnostic loki-tempo, prometheus-mimir, logql-promql, grafana-dashboards) + `observability-engineer-{dotnet,java,node}` agents; bundled into the `be-*` plugins |
| qa                    | authored — 30 code-producing nodes (mostly ×3 stacks) + 7 process skills. `qa-dotnet` additionally ships the `conformance-audit` self-audit skill + `/qa-dotnet-audit` |
| engineering-practices | imported from obra/superpowers |
| meta                  | imported (writing-skills, skill-creator) |
| documents             | imported from anthropics/skills |
| design                | imported (Anthropic + Vercel) |
| communication         | imported + 3 authored (business-analysis, user-story-writer, stakeholder-updates) |
| ai-development        | imported from anthropics/skills |
