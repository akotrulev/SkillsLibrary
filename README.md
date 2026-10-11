# SkillsLibrary

A shared library of Claude skills and rules for backend, frontend, DevOps, observability, QA, security, data, and agent-tooling work. Designed to be consumed by Claude Code, Claude Desktop, and CI agents across multiple repos.

## How to use

### Install as a Claude Code plugin (recommended)

The repo is a Claude Code plugin marketplace of **21 plugins**. Add it once, then install **one plugin per category** for your project — `qa-*`, `fe-*`, `mobile-*`, `be-*` are the categories with several stacks; every other plugin is its own category. Claude Code handles fetching and updates, no cloning or syncing required.

**Shared layers install themselves.** Anything used by more than one category lives in exactly one plugin, and the others declare it as a `dependency`:

| Plugin | Pulls in |
|---|---|
| `qa-*` · `be-*` · `devops` · `business-analysis` | `dev` |
| `fe-*` · `mobile-*` | `dev` + `design` |
| `data` · `tooling` · `training-data` · `penetration-testing` · `security-governance` | nothing |

`dev` is the delivery lane (design, planning, documentation, audits, debugging); `design` is the visual/UX craft layer with the vendored `ui-ux-pro-max` corpus. Installing a plugin installs its dependencies too; enabling them per project is covered below.

```shell
/plugin marketplace add akotrulev/SkillsLibrary
/plugin install dev@skills-library                 # delivery lane: refine, design, plan, document, audit, debugging, verification
/plugin install design@skills-library              # visual/UX craft layer + ui-ux-pro-max corpus + design audit
/plugin install qa-java@skills-library             # complete Java 21 QA toolkit
/plugin install qa-dotnet@skills-library           # complete .NET 10 / C# QA toolkit (8/9 supported)
/plugin install qa-typescript@skills-library       # complete TypeScript QA toolkit
/plugin install fe-blazor@skills-library           # complete Blazor (.NET 8/9/10) frontend toolkit
/plugin install fe-react@skills-library            # complete React 19/18 (Next.js App Router / Vite) frontend toolkit
/plugin install mobile-react-native@skills-library # React Native + Expo (SDK 57) mobile toolkit
/plugin install mobile-ios@skills-library          # Swift / SwiftUI iOS toolkit
/plugin install mobile-android@skills-library      # Kotlin / Jetpack Compose Android toolkit (+ Kotlin Multiplatform)
/plugin install be-dotnet@skills-library           # .NET 10 backend design-pattern + EF Core + Auth0/Cognito toolkit
/plugin install be-java@skills-library             # Java 21 / Spring Boot backend design-pattern + JPA + Auth0/Cognito toolkit
/plugin install be-node@skills-library             # Node 24 / TypeScript backend design-pattern + Prisma toolkit
/plugin install be-python@skills-library           # Python 3.13 sandboxed upload-processing worker (Pillow / rembg / VTracer, no-network container, pytest)
/plugin install devops@skills-library              # platform / delivery lane: docker, kubernetes, IaC, cloud deploy, CI hosts + infra security
/plugin install data@skills-library                # complete database-engineering toolkit (8 engines)
/plugin install business-analysis@skills-library   # cross-feature business-flow analysis toolkit
/plugin install penetration-testing@skills-library # offensive kill-chain + purple-team detection validation
/plugin install security-governance@skills-library # defensive/blue-team + CISO-altitude posture toolkit
/plugin install training-data@skills-library       # LLM/VLM training-data engineering toolkit
/plugin install tooling@skills-library             # turn a project into an agent-drivable MCP server / CLI
```

### Configure per project, not globally

Install at user scope, keep every `skills-library` plugin `false` in `~/.claude/settings.json`, and enable the project's set in the project's `.claude/settings.json` — the higher scope wins per plugin:

```json
{ "enabledPlugins": { "be-java@skills-library": true, "fe-react@skills-library": true, "qa-typescript@skills-library": true,
                      "dev@skills-library": true, "design@skills-library": true } }
```

**List `dev` (and `design` for `fe-*` / `mobile-*`) explicitly.** A dependency is installed with its dependent, but an explicit `false` at user scope still wins: with the global `false` above, `claude plugin list` run inside the project shows `dev` and `design` disabled unless the project enables them itself (verified 2026-10-11). Check a project with `claude plugin list --json` from its root.

### Typing names

Skills and commands are `/<plugin>:<name>`. A bare `/<name>` works while only one enabled plugin has that name; when two do (for example `forms` in `fe-react` and `mobile-react-native`), type the plugin-qualified form. A plugin's front-door command is the plugin's own name (`/fe-react`, `/be-java`, `/data`, `/devops`), so a bare `/fe-react` keeps working. Skill names are the topic only — the plugin namespace already carries the domain and the stack.

**One self-contained plugin per language** — `qa-java`, `qa-dotnet`, `qa-typescript`. Each is a complete QA toolkit for its stack: it bundles every discipline (API / UI / mobile / performance / LLM authoring and review, BDD living documentation, deep verification, contracts, chaos, feature flags) **plus** the shared, cross-cutting capabilities that used to be separate peer plugins:

- **Manual QA** — the language-agnostic `qa/manual` process skills and the `qa-test-case-designer` + `qa-test-planner` agents (test-basis analysis, ISTQB design techniques, cross-feature test design, test-case / test-plan / bug-report / charter writing).
- **Security** — the cross-stack, OWASP-mapped `qa/_shared` scanner gates (ZAP, SAST, secrets, container/IaC, API fuzzing, Nuclei, TLS), the stack-native security skills (BOLA/IDOR/BFLA access-control matrix, ZAP baseline, SCA), and the `qa-security` orchestrator agent.
- **CI/CD** — the stack's `ci-pipelines` skill (GitHub Actions / Azure Pipelines / GitLab CI), the language-agnostic `ci-conventions`, and the `qa-cicd-<stack>` agent.
- **Reporting** — Allure results wiring + flaky-test detection/quarantine and the `qa-reporting-<stack>` agent.

So installing a single plugin gives you the stack's authoring/verification skills, its api/ui/mobile/performance/llm/bdd agents, and the manual / security / cicd / reporting skills and agents — no peer plugins to add. (Each stack ships `mobile-project-setup`, which stands up a runnable Appium 3 test project from zero; .NET additionally ships `*-project-setup` skills for a complete runnable .NET 10 test solution (8/9 supported).)

**The other plugins:**

- **`fe-blazor`** — the Blazor (.NET 8/9/10) frontend **development** stack: 23 `fe-blazor` skills (scaffold, state, styling, forms, data access, realtime, quality layers, bUnit + pure-logic tests, hostile reviewer), the step-by-step `fe-blazor` orchestrator agent, plus `auth/auth0-blazor`. The `design` craft skills — including the vendored **`ui-ux-pro-max` design-intelligence corpus**, the source of truth for every design fact — arrive through the `design` dependency, with **`/design:audit`** (see below).
- **`fe-react`** — the React 19/18 + TypeScript frontend **development** stack (Next.js 15 App Router / RSC primary, Vite SPA fallback, shadcn/ui + Tailwind default): 26 `fe-react` skills, the step-by-step `fe-react` orchestrator agent, plus `auth/auth0-react` and the vendored Vercel performance/composition/view-transitions seeds. The `design` craft skills arrive through the `design` dependency. Includes `/fe-react:audit` — a one-call, read-only conformance sweep of an existing codebase against every convention the plugin defines, saved as a re-runnable findings report in `docs/audits/`. Both `fe-*` plugins get the **`design-auditor`** agent (`/design:audit`) through `design` — the one-call, read-only sweep of the whole UI across every design altitude at once (visual identity, tokens, IA, Nielsen heuristics, flow friction, responsiveness, UI-code guidelines, copy voice, charts, icons, brand fidelity, **design-time accessibility**, **ethical patterns**, **AI-feature UX**, **motion**, **landing structure**), every section judged against the vendored `ui-ux-pro-max` corpus, with its own screenshot capture per user task (Playwright MCP by default, Claude in Chrome as the backup), cross-altitude deduplication, and re-runnable rounds in `docs/audits/`.
- **`be-dotnet`** — the .NET (10 primary / 8-9 supported) backend **design-pattern + persistence + unit-test** stack: `pattern-guide`/`pattern-writer`/`code-review`/`database-code` (EF Core)/`unit-testing` (NUnit 4 + NSubstitute + `FakeTimeProvider`) + `auth0`/`cognito` (JWT bearer validation, RBAC, Client Credentials M2M), the step-by-step `be-dotnet` orchestrator agent, plus the stack-agnostic `architecture-review` and `patterns` skills. Planning and reverse-documentation (`/dev:plan-system`, `/dev:document-system`) come from `dev`.
- **`be-java`** — the Java 21 + Spring Boot 3.x backend **design-pattern + persistence + unit-test** stack: the same six skills, Spring-idiomatic (JPA/Hibernate + Spring Data, Spring Security OAuth2 Resource Server for `auth0`/`cognito`, `unit-testing` on JUnit 5 + Mockito + AssertJ with **no Spring context**), the step-by-step `be-java` orchestrator agent, plus the stack-agnostic `architecture-review` and `patterns` skills. Planning and reverse-documentation (`/dev:plan-system`, `/dev:document-system`) come from `dev`.
- **`be-node`** — the Node (24 primary / 22 maintenance) + TypeScript strict backend **design-pattern + persistence + unit-test** stack: `pattern-guide`/`pattern-writer`/`code-review`/`database-code` (Prisma default / Drizzle / TypeORM)/`unit-testing` (Vitest, DI over `vi.mock`, both `Result` branches), the step-by-step `be-node` orchestrator agent, plus the stack-agnostic `architecture-review` and `patterns` skills (no `auth0`/`cognito` skill yet — a known gap). Planning and reverse-documentation come from `dev`.
- **`be-python`** — the Python 3.13 (3.12 / 3.14 supported) **sandboxed upload-processing worker** stack, the one isolated Python process an otherwise-TypeScript repo needs: `pattern-guide`/`pattern-writer` (uv + ruff + `mypy --strict`, tagged-union `Result`, `Protocol` injection, `pydantic-settings`, JSON logging) / **`media-processing`** (content-sniffed validation, allowlist SVG sanitising that rejects rather than strips, total EXIF/GPS/XMP strip, rembg, VTracer, DPI verdict, dominant colours, resize ladders) / **`sandboxed-worker`** (baked checksum-verified weights, no outbound network, non-root read-only container, per-job spawned child with rlimits and a wall-clock kill) / **`unit-testing`** (pytest with self-proving hostile fixture builders and a `model` lane) / `conventions-review` (an untrusted-input checklist) and the step-by-step `be-python` orchestrator agent. Planning and reverse-documentation come from `dev`.
- **`devops`** — the platform / delivery lane, the path from a built service to a running one: 9 cloud/CI-keyed skills (docker, kubernetes, infrastructure-as-code, aws-deployment, azure-deployment, github-actions, gitlab-ci, azure-pipelines, environment-config) and two stack-agnostic agents — **`devops-engineer`** builds, **`devops-auditor`** audits read-only. Unlike the stack-first plugins these skills are keyed to *tools* rather than languages, so picking which to load **is** the design decision: both agents inspect the repo, derive what the workload requires, and **confirm the tool stack (or the audit scope) with you before loading a single skill**. `/devops:audit` is the read-only conformance sweep of an existing setup — image, IaC, k8s, deploy target, pipeline, identity, secrets — saved as a re-runnable findings report in `docs/audits/`. OIDC / Workload Identity Federation throughout; no static cloud credentials anywhere.
- **`penetration-testing`** — the **offensive** half of the `security/` domain, language-agnostic throughout (every tool is a Docker/CLI binary). Seven kill-chain skills — recon-enumeration, initial-access, privilege-escalation, lateral-movement, credential-attacks, post-exploitation, penetration-testing:reporting — plus the two purple-team skills (`atomic-simulation` detonates known ATT&CK techniques, `detection-validation` then asserts the SIEM/alert actually fired). Three agents: **`penetration-tester`** runs the full chain to prove an attacker could chain findings into impact, **`security-test-planner`** sequences an assessment across every lane before it starts, and **`purple-team-engineer`** re-runs technique sets on a cadence to catch detection drift. **The safety model is load-bearing and non-optional:** every run refuses to start without a committed engagement scope file (`docs/security/engagement-<NNN>.md` — in-scope hosts, hard exclusions, blast-radius cap, window, named authorizer), re-reads it before every step, treats authorization as expiring rather than cached, requires per-act opt-in for anything irreversible, **never** does DoS, redacts all recovered loot out of the report, logs every action, verifies cleanup, and halts mid-run rather than quietly narrowing scope. Spines are MITRE ATT&CK Enterprise + CVSS. It finds and retests; it never remediates.
- **`security-governance`** — the **defensive / blue-team** half, at CISO altitude. Four governance skills: `detection-engineering` (vendor-neutral Sigma rules as code, unit-tested against a true-AND-benign log sample before deploy, each mapped to a pinned ATT&CK technique), `security-hardening` (nonce + `strict-dynamic` CSP, the OWASP Secure Headers baseline, OWASP CRS on Coraza/ModSecurity rolled out detection-only → tuned → blocking), `secrets-hardening` (rotate-first-purge-second, the two-slot rotation runbook, Vault/ESO/SOPS wiring, dynamic over static-and-rotated), and `compliance-evidence-mapping` (the library's own controls and tests mapped to SOC 2 / PCI DSS 4.0.1 / ISO 27001:2022 / GDPR — it **maps, never certifies**). The **`security-architect`** agent is the roll-up: it consumes findings from *every* lane, normalizes offensive CVSS against the library severity table onto one risk band, and produces one posture picture — risk register, ATT&CK coverage map, evidence register with gaps, leverage-ordered roadmap. `/security-governance:audit` is its read-only conformance sweep (14 sections, 127 checks). It authors governance artifacts and prescribes; it never runs a scan and never edits application code.
- **`data`** — the database-engineering stack: 8 version-aware per-engine skills (PostgreSQL, SQL Server / Azure SQL, MySQL, MongoDB, Redis / Valkey, DynamoDB, Cosmos DB, Elasticsearch / OpenSearch), 4 cross-engine `_shared` skills (schema-design, migrations, caching-patterns, slow-query-fixes), and the step-by-step `data-architect` agent.
- **`training-data`** — the **LLM/VLM training-data engineering** domain: building the datasets a *small* model trains on, as distinct from `ai-development/` (apps built *on top of* a hosted model) and from QA's `ai-feature-testing` (which *tests* a model). Eight skills cover all four training stages (pretraining corpus, instruction/SFT, preference/DPO, evaluation sets) across both modalities (text and image-text), by curation and/or teacher-model synthesis as equal-weight lanes, over three shared foundations: the on-disk contract (`training-data:dataset-formats`), the quality gate (`training-data:data-quality`), and the synthesis engine (`training-data:synthetic-generation`). Two agents — the step-by-step **`dataset-engineer`** builder and the read-only **`dataset-auditor`**. Two invariants hold everywhere: **decontamination runs last and always** (no eval number is trustworthy until the train split has been checked against its eval targets — the teacher model is itself a prime contamination source), and **synthetic data is a flagged draft, never verified truth**. Out of scope: training the model and the training harness itself.
- **`tooling`** — the agent-drivable-surface lane: turn a project, or a chosen set of its functionalities, into something an agent (or a script, or a CI step) can drive **correctly on the first call**. Its one rule is *contract first, code second* — `tooling:capability-contract` reads the codebase's entry points and writes one reviewable contract document (capability table with a `file:line` source per row, typed inputs carrying their examples, an error table whose last column is *what the caller does next*, the multi-step flows, and the dependency + trust boundary), and `tooling:mcp-builder` / `tooling:cli-builder` then render **that** document mechanically into an MCP server and/or a subcommand CLI sharing one response envelope, one closed error vocabulary, clamped paging, and a gate on every destructive capability. MCP defaults to the TypeScript SDK (in-process for Node projects, a sidecar for anything reachable over HTTP, stack-native .NET / Spring AI only when the capabilities are in-process and unreachable otherwise); the CLI matches the project's stack (commander · System.CommandLine · picocli). One agent, `tooling-engineer`. Distinct from the vendored `ai-development/mcp-builder`, which wraps a **third-party API with no local codebase**.
- **`business-analysis`** — the upstream requirements domain in two lanes: 10 skills and 2 agents. The **authoring** lane (`business-analysis:scoping`, `business-analysis:epics`, `business-analysis:stories`, `business-analysis:story-review` + the `requirements-author` agent) is the front door to the planning ladder: a loose description → one batch of questions → `requirements.md` + `epics.md` + `stories.md` in an initiative folder, handed to `/dev:plan-system`; the **reasoning** lane (`business-analysis:knowledge-base`, `business-analysis:process-flow`, `business-analysis:state-grid`, `business-analysis:decision-table`, `business-analysis:dependency-map`, the 11-class `business-analysis:conflict-check` + the `business-analyst` agent) keeps a persistent per-project business model and detects conflicts between features.

### The `dev` plugin and the always-on internals

`dev` registers 17 skills, 5 agents and 5 commands: the design-then-plan pair (`/dev:design`, `/dev:plan-feature`), `debugging`, `verify`, the spec-compliance / feature audit pair (`audit-spec`, `audit-feature`), the eleven `backend/_shared` planning and documentation skills (`plan-delivery`, `plan-data-model`, `doc-feature-trace`, …) and the agents `code-auditor`, `solution-planner`, `be-documenter`, `be-feature-documenter` and `requirements-author`.

Three skills are **unregistered and loaded by path only** — they never appear in `/`, and every agent that needs one loads it from the installed repo checkout:

- **`engineering-practices/standards-audit-engine`** — the shared engine behind the per-stack conformance audits. Where a stack's own audit is not authored yet it simply sits inert. Authored so far: `/qa-dotnet:audit`, `/be-dotnet:audit`, `/fe-react:audit`, `/mobile-<stack>:audit`, `/security-governance:audit` and `/devops:audit` (whose agent supplies its own rule sections, since devops is outside [`docs/plans/CONFORMANCE-AUDIT-PLAN.md`](docs/plans/CONFORMANCE-AUDIT-PLAN.md)'s scope); the rest roll out per that plan.
- **`engineering-practices/agent-orientation-cache`** — the protocol every agent uses to persist its orientation pass to `docs/agent-context/<agent-name>.md` in your project and reuse it next run, re-deriving only what a git delta proves changed. It makes repeat invocations cheap without letting a stale map be mistaken for evidence.
- **`engineering-practices/code-comments`** — the comment discipline every code-writing and code-reviewing skill applies: **no inline comments**, a short doc comment only where the name genuinely cannot carry the meaning *and* the flow is complex, nothing at all on trivia, and a stale comment deleted rather than updated. Test code adds one rule: the test name and the Arrange-Act-Assert shape *are* the explanation.

`auth/_shared/{auth0-concepts,oidc-concepts}` are reached the same way, through the stack `auth0` skills that load them. Pull updates later with `/plugin marketplace update skills-library`.

### Slash commands

**Commands are kept to the entry points that matter: every front-door agent, the `dev` delivery workflow, and the read-only audits.** Agents are normally picked up by description match, which is probabilistic; the command is the deterministic entry point for when you would rather *name* the workflow than hope for it. Each command loads its agent definition and runs that agent's step-by-step workflow. Called bare with no argument, it runs the agent's orientation pass against the current repo and asks what you need.

**Every skill is already slash-invocable as `/<plugin>:<name>`** — `/design:tokens`, `/business-analysis:stories`, `/qa-<stack>:bug-report-writer`, `/dev:audit-feature` — and the commands below are the agent entry points. Prefer the agent for anything that touches code: an agent's first act is version detection (TFM / React major / engine version / Node major) plus reading existing files for conventions, and a skill invoked directly skips all of it — the exact way a .NET 8 repo ends up with a .NET 10 recipe.

**Naming scheme.** A plugin's front-door command is the plugin's name; every read-only conformance audit is `:audit`; every other command is a short role or topic. 64 command files, 70 registrations.

**`qa-java` · `qa-dotnet` · `qa-typescript`** — 11 commands each (`qa-dotnet` has 12 — see `:audit`); substitute your stack for `<stack>`:

| Command | Argument | Runs |
|---|---|---|
| `/qa-<stack>:api` | endpoints or suite to cover | scaffold, author, and review API test coverage |
| `/qa-<stack>:ui` | flow, URL, or suite | scaffold, author, and review web UI coverage (or build a POM from a URL) |
| `/qa-<stack>:mobile` | app flow or suite | scaffold, author, and review native/hybrid mobile coverage |
| `/qa-<stack>:performance` | service or workload | design, author, review, and CI-gate a load-test suite |
| `/qa-<stack>:llm` | LLM feature | build an eval dataset, assert properties/rubrics/grounding, red-team |
| `/qa-<stack>:bdd` | test-case suite or features | test cases → feature files → step definitions bound to page objects |
| `/qa-<stack>:cicd` | pipeline to build or harden | shard matrix, gates, OIDC secrets, result publishing |
| `/qa-<stack>:reporting` | what to wire, tag, or quarantine | wire Allure, tag tests by finding, detect and quarantine flakes |
| `/qa-<stack>:test-cases` | doc, story, contract, or URL | documentation (or a live page) → a systematically-derived test-case suite |
| `/qa-<stack>:test-plan` | feature, doc, URL, or repo area | feature (documented or not) → a saved test plan: scope, harness looked up from the repo, artifacts, gap-analyzed case inventory |
| `/qa-<stack>:security` | app, API, or layer | OWASP-mapped SAST, secrets, SCA, access-control, DAST, fuzzing, container/IaC, TLS gates |
| `/qa-dotnet:audit` *(qa-dotnet only so far)* | *(none — or a path/section limiter)* | read-only sweep of the **test suite** against the `qa-dotnet` conventions → findings report in `docs/audits/` |

The manual-QA writers (`qa-<stack>:test-case-writer`, `qa-<stack>:test-plan-writer`, `qa-<stack>:requirements-breakdown`, `qa-<stack>:bug-report-writer`, `qa-<stack>:exploratory-charter-writer`, `qa-<stack>:test-strategy`) are skills, invoked by name.

**`fe-blazor`** — 1 command · **`fe-react`** — 2:

| Command | Argument | Runs |
|---|---|---|
| `/fe-blazor` | what to build, fix, or extend | the step-by-step Blazor Web App UI workflow |
| `/fe-react` | what to build, fix, or extend | the step-by-step React / Next.js UI workflow |
| `/fe-react:audit` *(fe-react only)* | *(none — or a path/section limiter)* | read-only sweep of the repo against the `fe-react` conventions → findings report in `docs/audits/` |

The 16 `design` craft skills (`/design:corpus` — **the source of truth for design facts** — `/design:visual-identity`, `/design:tokens`, `/design:app-structure`, `/design:ux-review`, …) arrive through the `design` dependency and are skills, invoked by name; `/design:audit` runs them all as one audit.

**`mobile-react-native` · `mobile-ios` · `mobile-android`** — 2 commands each:

| Command | Argument | Runs |
|---|---|---|
| `/mobile-<stack>` | what to build, fix, or extend | the step-by-step mobile app workflow for that stack |
| `/mobile-<stack>:audit` | *(none — or a path/section limiter)* | read-only sweep of the app against the plugin's conventions → findings report in `docs/audits/` |

**`be-dotnet` · `be-java` · `be-node` · `be-python`** — `be-dotnet` 3 commands, `be-java` and `be-node` 2, `be-python` 1 (no `:observability`). Note the backend stacks are `dotnet` / `java` / **`node`** / `python`, not the QA triplet:

| Command | Argument | Runs |
|---|---|---|
| `/be-dotnet` · `/be-java` · `/be-node` | what to build, fix, or extend | apply a design pattern, the persistence layer, or service-side auth |
| `/be-python` | what to build, fix, or extend | build, fix, extend or review the sandboxed Python upload worker — validation, SVG sanitising, EXIF strip, rembg, VTracer, DPI, colours, resize, hardened container, pytest |
| `/be-<stack>:observability` *(dotnet · java · node)* | what to instrument, query, or dashboard | OTel, structured logging, Grafana backends, dashboards |
| `/be-dotnet:audit` *(be-dotnet only so far)* | *(none — or a project/section limiter)* | read-only sweep of the service against the `be-dotnet` conventions (incl. the observability invariants) → findings report in `docs/audits/` |

**`devops`** — 3 commands:

| Command | Argument | Runs |
|---|---|---|
| `/devops` | what to containerize, provision, deploy, or wire | discover → **confirm the tool stack with you** → containerize → provision → deploy → pipeline → review |
| `/devops:audit` | *(none — or a service/path/section limiter)* | discover → **confirm the audit scope with you** → read-only sweep of the existing image, IaC, k8s, deploy target, pipeline, identity and secrets against the `devops` conventions → findings report in `docs/audits/` |
| `/devops:infra-security` | *(none — or a cluster, cloud account, path, or area limiter)* | assess existing infrastructure's security posture — IaC/image misconfig, K8s CIS, container runtime, cloud CSPM/IAM, supply chain — authorization-gated for live probes, never fixes, report in `docs/security/` |

The 9 delivery skills (docker, IaC, kubernetes, the three CI hosts, the two cloud deployments, environment-config) are reached through the two agents — and because devops skills are keyed to *tools* rather than stacks, both agents inspect the repo and **confirm the tool stack with you before loading a single skill**, then load only what that answer selects.

**`penetration-testing`** — 3 commands:

| Command | Argument | Runs |
|---|---|---|
| `/penetration-testing:engagement` | repo, running system, cloud account, or a loose description | discover the attack surface, block for scope + authorization, emit an ordered task list binding each step to its lane agent |
| `/penetration-testing:pentest` | engagement id / scope-file path, or the owned-lab target | scope gate → recon → exploitation → priv-esc → lateral movement → post-exploitation (capped at proof) → report + cleanup verification |
| `/penetration-testing:purple-team` | engagement id, target, or the ATT&CK technique set | detonate each technique and assert the alert fired — scored detected/not-detected, with the drift delta against the last round |

**`security-governance`** — 2 commands:

| Command | Argument | Runs |
|---|---|---|
| `/security-governance:architect` | the system to build a posture picture for, or a round to consolidate | roll every lane's findings into one risk register, ATT&CK coverage map, evidence register, and remediation roadmap |
| `/security-governance:audit` | *(none — or a path/section limiter)* | read-only sweep of the repo's defensive-security artifacts against the `security-governance` conventions → findings report in `docs/audits/` |

**`data`** — 1 command:

| Command | Argument | Runs |
|---|---|---|
| `/data` | what to model, secure, migrate, or tune | model, secure, implement, and tune a schema across 8 engines |

**`tooling`** — 1 command:

| Command | Argument | Runs |
|---|---|---|
| `/tooling` | what to expose, and whether you want MCP, CLI, or both | derive and confirm the capability contract, then build and smoke-test the MCP server and/or CLI over it |

**`training-data`** — 2 commands:

| Command | Argument | Runs |
|---|---|---|
| `/training-data` | what dataset to build — stage, modality, target model | spec → source/curate → synthesize → quality gate (decontamination last) → format & split → dataset card |
| `/training-data:audit` | dataset path or name, and its eval targets | read-only audit across 8 sections — format, contamination, duplication, PII, license, composition, splits, card |

**`business-analysis`** — 1 command:

| Command | Argument | Runs |
|---|---|---|
| `/business-analysis` | feature or change to analyze | model flows, states and decisions, sweep for cross-feature conflicts, persist the KB |

The ten skills (`/business-analysis:scoping`, `/business-analysis:epics`, `/business-analysis:stories`, `/business-analysis:story-review`, `/business-analysis:process-flow`, `/business-analysis:state-grid`, `/business-analysis:decision-table`, `/business-analysis:conflict-check`, `/business-analysis:dependency-map`, `/business-analysis:knowledge-base`) are skills, invoked by name; the `business-analyst` agent sequences them. The authoring front door, `/dev:refine`, lives in `dev`.

**`dev`** — 5 commands, shared by every plugin that depends on it:

| Command | Argument | Runs |
|---|---|---|
| `/dev:refine` | a loose description of what you want built | the front door: batched questions, then `requirements.md` + `epics.md` (`E1..En`) + `stories.md` (`US1..USn`) in a new initiative folder, ready for `/dev:plan-system`. Also extends or audits an existing backlog |
| `/dev:plan-system` | the initiative folder from `/dev:refine`, the requirements, or `resume` | plan a whole application: an approved high-level blueprint, then the detail pack — DB structure, experience plan, service→resource→endpoint surface with request/response bodies, shared validation catalog, external dependencies — then the epic map (which lanes can run at once) and a task list where **every task is one epic, one story, one stack, one agent and one session**, closing with the plan's own `## Prompts — one per task` section: one ready-to-paste prompt per task, in one self-contained, queueable document. Writes plans, never code |
| `/dev:document-system` | the system or area, or `refresh` | the reverse: read an existing backend, split it into functional areas (you confirm the split), trace each one, and write what it does from the **end user's** perspective into `docs/business-model/` — one simple document per area: overview, setup parameters, how it works (triggers → steps → formulas), a full worked example with real numbers, open questions, with flowcharts, decision tables and state grids linked by ID. Every claim `file:line`-evidenced and tiered `#observed` / `#inferred` in a closing table; never invents intent. Read-only on code |
| `/dev:document-feature` | the feature, in your own words (e.g. "the refund flow") | document **one** feature of an existing codebase: locate the implementation, trace it end to end, and write a single standalone `docs/features/<NNN>-<slug>.md` in the same simple shape — overview, scope, setup parameters, how it works (triggers → steps → formulas), a full worked example, open questions & findings, closing `file:line` evidence table. No KB writes; read-only on code |
| `/dev:audit` | spec, stories, feature, or area | read-only audit engagement (the `code-auditor` agent), saved to `docs/audits/` — owns both the spec-vs-code and spec-less feature lanes; `dev:audit-spec` / `dev:audit-feature` remain invocable for a one-off |

`/dev:design` (one clear feature → approved technical design/spec in `docs/specs/`; a loose or multi-capability ask → `/dev:refine`) and `/dev:plan-feature` (approved spec → a self-contained plan document in `docs/plans/`: the gap table, the decisions, one flat ordered task list, and one paste-ready prompt per task) are **skills** in `dev`, typed the same way.

**`design`** — 1 command:

| Command | Argument | Runs |
|---|---|---|
| `/design:audit` | *(none — or how to reach the app)* | the **whole** design audit in one run — visual identity, tokens, IA, heuristics, flow, responsiveness, UI code, copy, charts, icons, brand, motion, landing structure — read-only, saved to `docs/audits/` |

### Use the repo directly

1. Clone or submodule this repo into your project.
2. Reference skills from your project's `CLAUDE.md` or `.claude/settings.json`, or symlink the folders you need into your project's `.claude/skills/`.
3. The global rules in [`CLAUDE.md`](CLAUDE.md) apply to every skill in the library.

This supports **one stack per project**: the unprefixed skill names of two stacks collide outside a plugin namespace.

## Layout

```
backend/                # Backend dev stacks: dotnet/java/node pattern reference, generators, reviewers, persistence + be-* agents; _shared cross-stack pattern cards
data/                   # Per-engine skills (Postgres, SQL Server, MySQL, Mongo, Redis, DynamoDB, Cosmos, Elasticsearch) + shared (migrations, caching, query opt, schema design) + data-architect agent
frontend/               # Frontend dev stacks: blazor/ (fe-blazor skills + agent), react/ (fe-react skills + agent + vendored Vercel seeds)
mobile/                 # Mobile dev stacks: react-native/ (Expo, 23 skills + vendored Vercel seed), ios/ (Swift, 23), android/ (Kotlin + KMP, 24), _shared/ (store compliance, security, release, observability, in-app purchases) + the mobile-* agents
business-analysis/      # Cross-feature business-flow reasoning: skills + business-analyst agent
auth/                   # Auth0 setup per stack
devops/                 # Platform lane: docker, kubernetes, IaC (Bicep/Terraform), AWS/Azure deploy, CI pipelines, env config + devops-engineer & devops-auditor agents
observability/          # Grafana, OpenTelemetry, structured logging
security/               # Security domain in two lanes: pentest kill chain + purple-team validation (penetration-testing) and defensive/governance (security-governance) + 4 agents
training-data/          # LLM/VLM training-data engineering: skills across 4 stages and 2 modalities + dataset-engineer & dataset-auditor agents
qa/                     # Test authoring (API/UI/perf), DB/email/network verification, CI pipelines, reporting (see QA skills below)
engineering-practices/  # planning, debugging, verification (from obra/superpowers), audits — ships as the `dev` plugin
meta/                   # Authoring skills themselves (writing-skills, skill-creator)
design/                 # Ships as the `design` plugin. Visual/UX: visual-identity, design:tokens, charts, brand-import, iconography, ux-review, theme-presets, ux-writing, ui-code-audit,
                        #   accessible-by-design (WCAG 2.2 design-time), ethical-patterns (dark patterns), ai-experience + design-auditor agent
communication/          # BA, user stories, stakeholder updates, internal comms
ai-development/         # claude-api, mcp-builder (vendored: wraps a third-party API)
tooling/                # Agent-drivable surfaces over your own project: capability-contract -> mcp-builder / cli-builder + tooling-engineer agent
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
| `api-models` | java · dotnet · typescript | Generate request/response DTOs |
| `ui-test-author/playwright` | java · dotnet · typescript | Author Playwright UI tests (1.64 on TypeScript, 1.63 on Java and .NET) — locators, assertions, emulation, one failure-evidence base test |
| `ui-test-author/selenium` | java · dotnet · typescript | Author Selenium UI tests |
| `ui-test-author/appium` | java · dotnet · typescript | Author Appium 3 mobile tests (java-client 11 · Appium.WebDriver 9 · WebdriverIO 10) on compilable assets |
| `ui-test-author/maestro` | typescript | Author Maestro mobile flows (`.maestro/` flows, subflows, `config.yaml`) — the alternative to Appium for Expo / React Native projects |
| `ui-test-author/review` | java · dotnet · typescript | Review UI tests |
| `page-object-design` | java · dotnet · typescript | Page-object architecture (intent-revealing) |
| `evidence-capture` | java · dotnet · typescript | Screenshots, video, screencast, trace and HAR for Playwright, and screenshot / page source / device log / recording for Appium — what a failed test keeps and where CI finds it |
| `mobile-project-setup` | java · dotnet · typescript | Stand up a runnable Appium 3 test project from zero (server, drivers, emulator, capabilities from the environment, a first smoke) |
| `webmcp-testing` | _shared | Test pages that register WebMCP tools — `page.webmcp` on Playwright 1.64, an `evaluate` helper on 1.63 |
| `api-contract-testing` | java · dotnet · typescript | Consumer/provider contract tests with Pact |
| `contract-testing-pact` | _shared | Pact rules every stack's `api-contract-testing` references |
| `load-testing` | java · dotnet · typescript | Load tests — Gatling (java) · NBomber (dotnet) · k6 (typescript) |
| `performance` | _shared | Workload modelling, SLOs, perf gates |

### Verification inside tests

| Skill | Stacks | What it does |
|-------|--------|--------------|
| `db-testing/client` | java · dotnet · typescript | Connect, seed, query-assert, clean up |
| `db-testing/testcontainers` | java · dotnet · typescript | Postgres/SQL Server/Mongo/Redis lifecycle |
| `db-testing/verification-queries` | java · dotnet · typescript | Safe, parameterized assertion SQL |
| `email-testing` | java · dotnet · typescript | Capture/assert email — tool picked inside via `references/` (mailpit · mailosaur · gmail-imap · sendgrid-sandbox) |
| `messaging-testing` | java · dotnet · typescript | Produce/consume/assert against brokers — broker picked inside via `references/` (kafka · sqs · rabbitmq · service-bus) |
| `time-and-concurrency-testing` | java · dotnet · typescript | Run a scheduled job on demand, control the clock at a time boundary, fire concurrent requests, deliver a message or webhook twice |
| `file-storage-testing` | java · dotnet · typescript | Object-storage assertions — store picked inside via `references/` (s3/LocalStack · azure-blob/Azurite) |
| `network-mocking` | java · dotnet · typescript | Intercept/mock/throttle browser traffic — layer picked inside via `references/` (playwright-routes · cdp · proxy) |
| `realtime-stream-testing` | java · dotnet · typescript | Real-time WebSocket + SSE assertions |

### Grids & access

| Skill | Stacks | What it does |
|-------|--------|--------------|
| `browser-cloud-setup` | java · dotnet · typescript | BrowserStack / Sauce / LambdaTest / Device Farm wiring |
| `test-login-tokens` | java · dotnet · typescript | M2M / ROPG / device-code tokens for test users |

### Reporting & CI/CD (`qa/reporting/`, `qa/cicd/` — own folders, own agents)

| Skill | Stacks | What it does |
|-------|--------|--------------|
| `reporting/<stack>/skills/test-reports` | java · dotnet · typescript | Allure results integration — loaded by `qa-reporting-<stack>` |
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
| `test-plan-writer` | Assemble a feature/release test plan (scope, harness, artifacts, case inventory) |
| `bug-report-writer` | Write actionable bug reports |
| `exploratory-charter-writer` | Write exploratory testing charters |
| `_shared/test-strategy` | Test strategy guidance |
| `_shared/quality-metrics` | Quality metrics guidance |
| `qa-<stack>:python-web-testing` | UI automation with Python — Playwright web-app testing toolkit (Anthropic-provided import) |

## Adding a new skill

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and the templates in [`.skill-template/`](.skill-template/).

## Status

| Section               | State |
|-----------------------|-------|
| backend               | authored + shipped — `backend/_shared/` (2 pattern-card skills + the 8 `solution-planner` planning skills + the 3 `be-documenter` reverse-documentation skills + both stack-agnostic agents; the planning and documentation skills and agents are registered in `dev`, the two pattern-card skills in each `be-*` plugin) + `backend/{dotnet,java,node}/` (4 skills each: reference/generator/reviewer/persistence) + `backend/python/` (6 skills: reference/generator/media-processing/sandboxed-worker/unit-testing/reviewer + the `be-python` agent; `be-python` plugin) + a step-by-step `be-*` agent per stack; `be-dotnet` additionally ships the `standards-audit` self-audit skill + `/be-dotnet:audit`; `be-dotnet` / `be-java` / `be-node` plugins |
| data                  | authored + shipped — 8 version-aware per-engine skills (postgresql, sqlserver, mysql, mongodb, redis, dynamodb, cosmosdb, elasticsearch) + 4 cross-engine `_shared` skills + the `data-architect` agent; `data` plugin |
| frontend              | authored + shipped — `frontend/blazor/` (22 skills + `fe-blazor` agent; `fe-blazor` plugin) and `frontend/react/` (24 skills incl. the `standards-audit` self-audit + `fe-react` agent + vendored Vercel seeds; `fe-react` plugin); React Native lives in `mobile/` |
| mobile                | authored + shipped — `mobile/react-native/` (23 skills + `mobile-react-native` agent), `mobile/ios/` (23 + `mobile-ios`), `mobile/android/` (24 incl. Kotlin Multiplatform + `mobile-android`), each with a `standards-audit` self-audit + `/mobile-<stack>:audit`; 5 `mobile/_shared/` skills bundled within the category into all three; `auth/auth0-{react-native,ios,android}`; `mobile-react-native` · `mobile-ios` · `mobile-android` plugins. Unverified: no agent has been run against a real app |
| business-analysis     | authored + shipped — 10 skills (authoring + reasoning lanes) + the `requirements-author` and `business-analyst` agents; `business-analysis` plugin |
| auth                  | scaffolding |
| devops                | authored + shipped — 9 cloud/CI-keyed skills (docker, kubernetes, infrastructure-as-code, aws-deployment, azure-deployment, github-actions, gitlab-ci, azure-pipelines, environment-config) + the `devops-engineer` (build) and `devops-auditor` (read-only conformance audit, `/devops:audit`) agents, both gated on a tool-stack confirmation before any skill loads; `devops` plugin |
| observability         | authored + shipped — 6 skills (per-stack `opentelemetry-*` / `structured-logging-*` + stack-agnostic loki-tempo, prometheus-mimir, queries, dashboards) + `observability-engineer-{dotnet,java,node}` agents; bundled within the category into the `be-*` plugins |
| qa                    | authored — 35 code-producing nodes (mostly ×3 stacks; Playwright 1.64 on TypeScript and 1.63 on Java / .NET / Python, Appium 3, plus a TypeScript-only Maestro lane) + 8 process skills (incl. `cross-feature-test-design`). Unverified: no `time-and-concurrency-testing` sample (any stack) has been compiled or run; no Appium or Maestro flow has run on a device or emulator, and no WebMCP test has run against a site that registers tools. `qa-dotnet` additionally ships the `standards-audit` self-audit skill + `/qa-dotnet:audit` |
| engineering-practices | imported from obra/superpowers — registered in the `dev` plugin (3 internals are loaded by path only) |
| meta                  | imported (writing-skills, skill-creator) |
| documents             | imported from anthropics/skills |
| design                | imported (Anthropic + Vercel) — the `design` plugin, a dependency of `fe-*` and `mobile-*` |
| communication         | imported + 3 authored (business-analysis, user-story-writer, stakeholder-updates) |
| security              | authored + shipped — 13 language-agnostic skills in two lanes: 7 pentest + 2 purple-team (`penetration-testing` plugin) and 4 governance + the `security-governance:standards-audit` self-audit (`security-governance` plugin) + the `penetration-tester`, `security-test-planner`, `purple-team-engineer`, and `security-architect` agents |
| training-data         | authored + shipped — 8 skills (3 `_shared` foundations + 5 stage lanes) + the `dataset-engineer` and `dataset-auditor` agents; `training-data` plugin |
| ai-development        | imported from anthropics/skills — `claude-api` re-vendored 2026-09-26 from `main` `33375500` (2026-09-24), models table "cached: 2026-06-24" |
| tooling               | authored + shipped — 3 skills (`capability-contract` + the `mcp-builder` / `cli-builder` renderers) + the `tooling-engineer` agent; `tooling` plugin |
