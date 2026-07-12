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
- **`fe-react`** — the React 19/18 + TypeScript frontend **development** stack (Next.js 15 App Router / RSC primary, Vite SPA fallback, MUI default): 21 `fe-react-*` skills, the phased `fe-react` orchestrator agent, plus the bundled `design/*` craft skills, `auth/auth0-react`, and the vendored Vercel performance/composition/view-transitions seeds.
- **`be-dotnet`** — the .NET (10 primary / 8-9 supported) backend **design-pattern + persistence** stack: `reference`/`generator`/`reviewer`/`persistence` (EF Core) + `auth0`/`cognito` (JWT bearer validation, RBAC, Client Credentials M2M), the phased `be-dotnet` orchestrator agent, plus the bundled `backend/_shared` pattern cards and `auth/_shared/{auth0-concepts,oidc-concepts}`.
- **`be-java`** — the Java 21 + Spring Boot 3.x backend **design-pattern + persistence** stack: the same five skills, Spring-idiomatic (JPA/Hibernate + Spring Data, Spring Security OAuth2 Resource Server for `auth0`/`cognito`), the phased `be-java` orchestrator agent, plus `backend/_shared` and `auth/_shared/{auth0-concepts,oidc-concepts}`.
- **`be-node`** — the Node (24 primary / 22 maintenance) + TypeScript strict backend **design-pattern + persistence** stack: `reference`/`generator`/`reviewer`/`persistence` (Prisma default / Drizzle / TypeORM), the phased `be-node` orchestrator agent, plus `backend/_shared` (no `auth0`/`cognito` skill yet — a known gap).
- **`data`** — the database-engineering stack: 8 version-aware per-engine skills (PostgreSQL, SQL Server / Azure SQL, MySQL, MongoDB, Redis / Valkey, DynamoDB, Cosmos DB, Elasticsearch / OpenSearch), 4 cross-engine `_shared` skills (schema-design, migrations, caching-patterns, query-optimization), and the phased `data-architect` agent.
- **`business-analysis`** — cross-feature business-flow reasoning: 5 `ba-*` skills (persistent project knowledge base, flow mapping, state modeling, decision modeling, the 11-class feature-conflict sweep) and the `business-analyst` agent (analyze / model / audit modes).

Every stack plugin (`qa-*`, `fe-*`, `be-*`) also bundles the 10 `ep-*` engineering-practices developer-workflow skills (brainstorm → plan → execute → verify → finish, TDD, systematic debugging, worktrees, agent dispatch). Pull updates later with `/plugin marketplace update skills-library`.

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
devops/                 # Pipelines (GH Actions / GitLab CI / Azure Pipelines), deployment, env config, IaC
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

See [`qa/GAP-ANALYSIS.md`](qa/GAP-ANALYSIS.md) for the live build/audit plan and remaining backlog.

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
| `webapp-testing` | UI automation with Python — Playwright web-app testing toolkit (Anthropic-provided import) |

## Adding a new skill

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and the templates in [`.skill-template/`](.skill-template/).

## Status

| Section               | State |
|-----------------------|-------|
| backend               | authored + shipped — `backend/_shared/` (2 pattern-card skills) + `backend/{dotnet,java,node}/` (4 skills each: reference/generator/reviewer/persistence) + a phased `be-*` agent per stack; `be-dotnet` / `be-java` / `be-node` plugins |
| data                  | authored + shipped — 8 version-aware per-engine skills (postgresql, sqlserver, mysql, mongodb, redis, dynamodb, cosmosdb, elasticsearch) + 4 cross-engine `_shared` skills + the `data-architect` agent; `data` plugin |
| frontend              | authored + shipped — `frontend/blazor/` (22 skills + `fe-blazor` agent; `fe-blazor` plugin) and `frontend/react/` (21 skills + `fe-react` agent + vendored Vercel seeds; `fe-react` plugin); `frontend/react-native/` parked, under construction |
| business-analysis     | authored + shipped — 5 `ba-*` skills + the `business-analyst` agent; `business-analysis` plugin |
| auth                  | scaffolding |
| devops                | scaffolding (gh-actions / gitlab-ci / azure-pipelines authored; vercel-deployment moved to extras/) |
| observability         | scaffolding |
| qa                    | authored — 30 code-producing nodes (mostly ×3 stacks) + 7 process skills; Phase 1 complete, Phase 2 in progress (see qa/GAP-ANALYSIS.md) |
| engineering-practices | imported from obra/superpowers |
| meta                  | imported (writing-skills, skill-creator) |
| documents             | imported from anthropics/skills |
| design                | imported (Anthropic + Vercel) |
| communication         | imported + 3 authored (business-analysis, user-story-writer, stakeholder-updates) |
| ai-development        | imported from anthropics/skills |
