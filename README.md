# SkillsLibrary

A shared library of Claude skills and rules for backend, frontend, DevOps, observability, and QA work. Designed to be consumed by Claude Code, Claude Desktop, and CI agents across multiple repos.

## How to use

### Install as a Claude Code plugin (recommended)

The repo is a Claude Code plugin marketplace. Add it once, then install the one plugin for your tech stack — Claude Code handles fetching and updates, no cloning or syncing required:

```shell
/plugin marketplace add akotrulev/SkillsLibrary
/plugin install qa-java@skills-library         # complete Java 21 QA toolkit
/plugin install qa-dotnet@skills-library        # complete .NET 8 / C# QA toolkit
/plugin install qa-typescript@skills-library    # complete TypeScript QA toolkit
```

**One self-contained plugin per language** — `qa-java`, `qa-dotnet`, `qa-typescript`. Each is a complete QA toolkit for its stack: it bundles every discipline (API / UI / mobile / performance / LLM authoring and review, BDD living documentation, deep verification, contracts, chaos, feature flags) **plus** the shared, cross-cutting capabilities that used to be separate peer plugins:

- **Manual QA** — the language-agnostic `qa/manual` process skills and the `qa-manual-test-designer` agent (test-basis analysis, ISTQB design techniques, test-case / bug-report / charter writing).
- **Security** — the cross-stack, OWASP-mapped `qa/_shared` scanner gates (ZAP, SAST, secrets, container/IaC, API fuzzing, Nuclei, TLS), the stack-native security skills (BOLA/IDOR/BFLA access-control matrix, ZAP baseline, SCA), and the `qa-security` orchestrator agent.
- **CI/CD** — the stack's `ci-pipelines` skill (GitHub Actions / Azure Pipelines / GitLab CI), the language-agnostic `ci-conventions`, and the `qa-cicd-<stack>` agent.
- **Reporting** — Allure results wiring + flaky-test detection/quarantine and the `qa-reporting-<stack>` agent.

So installing a single plugin gives you the stack's authoring/verification skills, its api/ui/mobile/performance/llm/bdd agents, and the manual / security / cicd / reporting skills and agents — no peer plugins to add. (.NET additionally ships `*-project-scaffold` skills that stand up a complete runnable .NET 8 test solution from zero.) Pull updates later with `/plugin marketplace update skills-library`.

### Use the repo directly

1. Clone or submodule this repo into your project.
2. Reference skills from your project's `CLAUDE.md` or `.claude/settings.json`, or symlink the folders you need into your project's `.claude/skills/`.
3. The global rules in [`CLAUDE.md`](CLAUDE.md) apply to every skill in the library.

## Layout

```
design-patterns/        # Per-stack pattern reference, generators, reviewers
data/                   # Per-database skills (Postgres, SQL Server, MySQL, Mongo, Redis, DynamoDB, Cosmos) + shared (migrations, caching, query opt, schema design)
auth/                   # Auth0 setup per stack
devops/                 # Pipelines (GH Actions / GitLab CI / Azure Pipelines), deployment, env config, IaC
observability/          # Grafana, OpenTelemetry, structured logging
qa/                     # Test authoring (API/UI/perf), DB/email/network verification, CI pipelines, reporting (see QA skills below)
engineering-practices/  # TDD, debugging, code review, git worktrees, planning (from obra/superpowers)
meta/                   # Authoring skills themselves (writing-skills, skill-creator)
documents/              # Office document generation (docx, pdf, pptx, xlsx) — from anthropics/skills
design/                 # Visual/UX: frontend-design, design-tokens, dataviz, brand-intake, iconography, ux-heuristics, theme-factory, ux-writing, web-design-guidelines
communication/          # BA, user stories, stakeholder updates, internal comms
ai-development/         # claude-api, mcp-builder
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
| design-patterns       | scaffolding (react/reference imported from Vercel) |
| data                  | 3 authored (postgresql, mongodb, redis) + 4 db stubs + 4 shared stubs |
| auth                  | scaffolding |
| devops                | scaffolding (gh-actions / gitlab-ci / azure-pipelines authored; vercel-deployment imported) |
| observability         | scaffolding |
| qa                    | authored — 30 code-producing nodes (mostly ×3 stacks) + 7 process skills; Phase 1 complete, Phase 2 in progress (see qa/GAP-ANALYSIS.md) |
| engineering-practices | imported from obra/superpowers |
| meta                  | imported (writing-skills, skill-creator) |
| documents             | imported from anthropics/skills |
| design                | imported (Anthropic + Vercel) |
| communication         | imported + 3 authored (business-analysis, user-story-writer, stakeholder-updates) |
| ai-development        | imported from anthropics/skills |
