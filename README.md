# SkillsLibrary

A shared library of Claude skills and rules for backend, frontend, DevOps, observability, and QA work. Designed to be consumed by Claude Code, Claude Desktop, and CI agents across multiple repos.

## How to use

### Install as a Claude Code plugin (recommended)

The repo is a Claude Code plugin marketplace. Add it once, then install the plugin for your tech stack — Claude Code handles fetching and updates, no cloning or syncing required:

```shell
/plugin marketplace add akotrulev/SkillsLibrary
/plugin install qa-dotnet@skills-library      # or qa-java / qa-typescript
/plugin install qa-manual@skills-library      # language-agnostic manual-QA process skills
```

Each stack plugin bundles that stack's skills, its phased orchestrator agents (api / ui / mobile / performance), the language-agnostic `qa/manual` process skills with the `qa-manual-test-designer` agent, the cross-stack `qa/_shared` rules, and the OWASP-mapped `qa-security` agent. `qa-manual` is the standalone option for manual-QA-only users — the same process skills and agent without the automation stack; skip it if you already installed a stack plugin (you'd register everything twice). Pull updates later with `/plugin marketplace update skills-library`.

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
design/                 # Visual/UX: brand, canvas, frontend-design, theme-factory, algorithmic-art
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
| `email-testing/mailpit` | java · dotnet · typescript | Capture/assert email via local SMTP sink |
| `email-testing/mailosaur` | java · dotnet · typescript | Hosted per-test inbox + SMS OTP |
| `email-testing/gmail-imap` | java · dotnet · typescript | Real Gmail mailbox over IMAP |
| `email-testing/sendgrid-sandbox` | java · dotnet · typescript | Validate-send-only via SendGrid sandbox |
| `network-monitoring/playwright-routes` | java · dotnet · typescript | `page.route`, mocking, HAR |
| `network-monitoring/cdp` | java · dotnet · typescript | Raw CDP throttling/cache/security audit (Chromium) |
| `network-monitoring/proxy` | java · dotnet · typescript | Out-of-browser MITM for non-Playwright stacks |

### Pipelines & environments

| Skill | Stacks | What it does |
|-------|--------|--------------|
| `ci-pipelines/github-actions` | java · dotnet · typescript | Shard matrix, Allure publish, perf gate, OIDC |
| `ci-pipelines/azure-pipelines` | java · dotnet · typescript | Same patterns, Azure idioms |
| `ci-pipelines/gitlab-ci` | java · dotnet · typescript | Same patterns, GitLab idioms |
| `test-environments` | java · dotnet · typescript | Testcontainers + docker-compose multi-service spin-up |
| `cloud-grid-config` | java · dotnet · typescript | BrowserStack / Sauce / LambdaTest / Device Farm wiring |
| `auth0-test-tokens` | java · dotnet · typescript | M2M / ROPG / device-code tokens for test users |

### Visual, reporting & test data

| Skill | Stacks | What it does |
|-------|--------|--------------|
| `visual-regression/playwright-snapshots` | java · dotnet · typescript | Built-in Playwright pixel-diff regression |
| `allure-reporting` | java · dotnet · typescript | Allure results integration |
| `test-data-builder` | java · dotnet · typescript | Builders / ObjectMother for test data |

### Process / planning (single-folder)

| Skill | What it does |
|-------|--------------|
| `test-case-writer` | Write structured test cases |
| `bug-report-writer` | Write actionable bug reports |
| `exploratory-charter-writer` | Write exploratory testing charters |
| `accelerator-conventions` | In-house Accelerator framework rules |
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
