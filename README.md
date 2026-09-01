# SkillsLibrary

A shared library of Claude skills and rules for backend, frontend, DevOps, observability, QA, security, data, and agent-tooling work. Designed to be consumed by Claude Code, Claude Desktop, and CI agents across multiple repos.

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
/plugin install penetration-testing@skills-library # offensive kill-chain + purple-team detection validation
/plugin install security-governance@skills-library # defensive/blue-team + CISO-altitude posture toolkit
/plugin install training-data@skills-library       # LLM/VLM training-data engineering toolkit
/plugin install tooling@skills-library             # turn a project into an agent-drivable MCP server / CLI
```

**One self-contained plugin per language** — `qa-java`, `qa-dotnet`, `qa-typescript`. Each is a complete QA toolkit for its stack: it bundles every discipline (API / UI / mobile / performance / LLM authoring and review, BDD living documentation, deep verification, contracts, chaos, feature flags) **plus** the shared, cross-cutting capabilities that used to be separate peer plugins:

- **Manual QA** — the language-agnostic `qa/manual` process skills and the `qa-test-case-designer` + `qa-test-planner` agents (test-basis analysis, ISTQB design techniques, test-case / test-plan / bug-report / charter writing).
- **Security** — the cross-stack, OWASP-mapped `qa/_shared` scanner gates (ZAP, SAST, secrets, container/IaC, API fuzzing, Nuclei, TLS), the stack-native security skills (BOLA/IDOR/BFLA access-control matrix, ZAP baseline, SCA), and the `qa-security` orchestrator agent.
- **CI/CD** — the stack's `ci-pipelines` skill (GitHub Actions / Azure Pipelines / GitLab CI), the language-agnostic `ci-conventions`, and the `qa-cicd-<stack>` agent.
- **Reporting** — Allure results wiring + flaky-test detection/quarantine and the `qa-reporting-<stack>` agent.

So installing a single plugin gives you the stack's authoring/verification skills, its api/ui/mobile/performance/llm/bdd agents, and the manual / security / cicd / reporting skills and agents — no peer plugins to add. (.NET additionally ships `*-project-setup` skills that stand up a complete runnable .NET 8 test solution from zero.)

**The other plugins:**

- **`fe-blazor`** — the Blazor (.NET 8/9/10) frontend **development** stack: 22 `fe-blazor-*` skills (scaffold, state, styling, forms, data access, realtime, quality layers, bUnit + pure-logic tests, hostile reviewer), the step-by-step `fe-blazor` orchestrator agent, plus the bundled `design/*` craft skills — including the vendored **`ui-ux-pro-max` design-intelligence corpus**, the source of truth for every design fact — and `auth/auth0-blazor`. Also ships **`/design-auditor`** — see below.
- **`fe-react`** — the React 19/18 + TypeScript frontend **development** stack (Next.js 15 App Router / RSC primary, Vite SPA fallback, shadcn/ui + Tailwind default): 24 `fe-react-*` skills, the step-by-step `fe-react` orchestrator agent, plus the bundled `design/*` craft skills — including the vendored **`ui-ux-pro-max` design-intelligence corpus**, the source of truth for every design fact — `auth/auth0-react`, and the vendored Vercel performance/composition/view-transitions seeds. Includes `/fe-react-audit` — a one-call, read-only conformance sweep of an existing codebase against every convention the plugin defines, saved as a re-runnable findings report in `docs/audits/`. Both `fe-*` plugins also ship the **`design-auditor`** agent (`/design-auditor`) — the one-call, read-only sweep of the whole UI across every design altitude at once (visual identity, tokens, IA, Nielsen heuristics, flow friction, responsiveness, UI-code guidelines, copy voice, charts, icons, brand fidelity, **design-time accessibility**, **ethical patterns**, **AI-feature UX**, **motion**, **landing structure**), every section judged against the vendored `ui-ux-pro-max` corpus, with its own screenshot capture per user task (Playwright MCP by default, Claude in Chrome as the backup), cross-altitude deduplication, and re-runnable rounds in `docs/audits/`.
- **`be-dotnet`** — the .NET (10 primary / 8-9 supported) backend **design-pattern + persistence + unit-test** stack: `pattern-guide`/`pattern-writer`/`code-review`/`database-code` (EF Core)/`unit-testing` (NUnit 4 + NSubstitute + `FakeTimeProvider`) + `auth0`/`cognito` (JWT bearer validation, RBAC, Client Credentials M2M), the step-by-step `be-dotnet` orchestrator agent, plus the bundled `backend/_shared` pattern cards and `auth/_shared/{auth0-concepts,oidc-concepts}`. Also ships **`/dev-plan-solution`** and **`/dev-document-system`** — see below.
- **`be-java`** — the Java 21 + Spring Boot 3.x backend **design-pattern + persistence + unit-test** stack: the same six skills, Spring-idiomatic (JPA/Hibernate + Spring Data, Spring Security OAuth2 Resource Server for `auth0`/`cognito`, `unit-testing` on JUnit 5 + Mockito + AssertJ with **no Spring context**), the step-by-step `be-java` orchestrator agent, plus `backend/_shared` and `auth/_shared/{auth0-concepts,oidc-concepts}`. Also ships **`/dev-plan-solution`** and **`/dev-document-system`** — see below.
- **`be-node`** — the Node (24 primary / 22 maintenance) + TypeScript strict backend **design-pattern + persistence + unit-test** stack: `pattern-guide`/`pattern-writer`/`code-review`/`database-code` (Prisma default / Drizzle / TypeORM)/`unit-testing` (Vitest, DI over `vi.mock`, both `Result` branches), the step-by-step `be-node` orchestrator agent, plus `backend/_shared` (no `auth0`/`cognito` skill yet — a known gap). Also ships **`/dev-plan-solution`** and **`/dev-document-system`** — see below.
- **`devops`** — the platform / delivery lane, the path from a built service to a running one: 9 cloud/CI-keyed skills (docker, kubernetes, infrastructure-as-code, aws-deployment, azure-deployment, github-actions, gitlab-ci, azure-pipelines, environment-config) and two stack-agnostic agents — **`devops-engineer`** builds, **`devops-auditor`** audits read-only. Unlike the stack-first plugins these skills are keyed to *tools* rather than languages, so picking which to load **is** the design decision: both agents inspect the repo, derive what the workload requires, and **confirm the tool stack (or the audit scope) with you before loading a single skill**. `/devops-auditor` is the read-only conformance sweep of an existing setup — image, IaC, k8s, deploy target, pipeline, identity, secrets — saved as a re-runnable findings report in `docs/audits/`. OIDC / Workload Identity Federation throughout; no static cloud credentials anywhere.
- **`penetration-testing`** — the **offensive** half of the `security/` domain, language-agnostic throughout (every tool is a Docker/CLI binary). Seven `pentest-*` kill-chain skills — recon-enumeration, initial-access, privilege-escalation, lateral-movement, credential-attacks, post-exploitation, pentest-reporting — plus the two `purpleteam-*` skills (`atomic-simulation` detonates known ATT&CK techniques, `detection-validation` then asserts the SIEM/alert actually fired). Three agents: **`penetration-tester`** runs the full chain to prove an attacker could chain findings into impact, **`security-test-planner`** sequences an assessment across every lane before it starts, and **`purple-team-engineer`** re-runs technique sets on a cadence to catch detection drift. **The safety model is load-bearing and non-optional:** every run refuses to start without a committed engagement scope file (`docs/security/engagement-<NNN>.md` — in-scope hosts, hard exclusions, blast-radius cap, window, named authorizer), re-reads it before every step, treats authorization as expiring rather than cached, requires per-act opt-in for anything irreversible, **never** does DoS, redacts all recovered loot out of the report, logs every action, verifies cleanup, and halts mid-run rather than quietly narrowing scope. Spines are MITRE ATT&CK Enterprise + CVSS. It finds and retests; it never remediates.
- **`security-governance`** — the **defensive / blue-team** half, at CISO altitude. Four `secgov-*` skills: `detection-engineering` (vendor-neutral Sigma rules as code, unit-tested against a true-AND-benign log sample before deploy, each mapped to a pinned ATT&CK technique), `security-hardening` (nonce + `strict-dynamic` CSP, the OWASP Secure Headers baseline, OWASP CRS on Coraza/ModSecurity rolled out detection-only → tuned → blocking), `secrets-hardening` (rotate-first-purge-second, the two-slot rotation runbook, Vault/ESO/SOPS wiring, dynamic over static-and-rotated), and `compliance-evidence-mapping` (the library's own controls and tests mapped to SOC 2 / PCI DSS 4.0.1 / ISO 27001:2022 / GDPR — it **maps, never certifies**). The **`security-architect`** agent is the roll-up: it consumes findings from *every* lane, normalizes offensive CVSS against the library severity table onto one risk band, and produces one posture picture — risk register, ATT&CK coverage map, evidence register with gaps, leverage-ordered roadmap. `/security-governance-audit` is its read-only conformance sweep (14 sections, 127 checks). It authors governance artifacts and prescribes; it never runs a scan and never edits application code.
- **`data`** — the database-engineering stack: 8 version-aware per-engine skills (PostgreSQL, SQL Server / Azure SQL, MySQL, MongoDB, Redis / Valkey, DynamoDB, Cosmos DB, Elasticsearch / OpenSearch), 4 cross-engine `_shared` skills (schema-design, migrations, caching-patterns, slow-query-fixes), and the step-by-step `data-architect` agent.
- **`training-data`** — the **LLM/VLM training-data engineering** domain: building the datasets a *small* model trains on, as distinct from `ai-development/` (apps built *on top of* a hosted model) and from QA's `ai-feature-testing` (which *tests* a model). Eight `td-*` skills cover all four training stages (pretraining corpus, instruction/SFT, preference/DPO, evaluation sets) across both modalities (text and image-text), by curation and/or teacher-model synthesis as equal-weight lanes, over three shared foundations: the on-disk contract (`td-dataset-formats`), the quality gate (`td-data-quality`), and the synthesis engine (`td-synthetic-generation`). Two agents — the phased **`dataset-engineer`** builder and the read-only **`dataset-auditor`**. Two invariants hold everywhere: **decontamination runs last and always** (no eval number is trustworthy until the train split has been checked against its eval targets — the teacher model is itself a prime contamination source), and **synthetic data is a flagged draft, never verified truth**. Out of scope: training the model and the training harness itself.
- **`tooling`** — the agent-drivable-surface lane: turn a project, or a chosen set of its functionalities, into something an agent (or a script, or a CI step) can drive **correctly on the first call**. Its one rule is *contract first, code second* — `tool-capability-contract` reads the codebase's entry points and writes one reviewable contract document (capability table with a `file:line` source per row, typed inputs carrying their examples, an error table whose last column is *what the caller does next*, the multi-step flows, and the dependency + trust boundary), and `tool-mcp-builder` / `tool-cli-builder` then render **that** document mechanically into an MCP server and/or a subcommand CLI sharing one response envelope, one closed error vocabulary, clamped paging, and a gate on every destructive capability. MCP defaults to the TypeScript SDK (in-process for Node projects, a sidecar for anything reachable over HTTP, stack-native .NET / Spring AI only when the capabilities are in-process and unreachable otherwise); the CLI matches the project's stack (commander · System.CommandLine · picocli). One agent, `tooling-engineer`. Distinct from the vendored `ai-development/mcp-builder`, which wraps a **third-party API with no local codebase**.
- **`business-analysis`** — the upstream requirements domain in two lanes: 9 `ba-*` skills and 2 agents. The **authoring** lane (`ba-scoping-writeup`, `ba-epic-writer`, `ba-story-writer`, `ba-story-quality-review` + the `requirements-author` agent) is the front door to the planning ladder: a loose description → one batch of questions → `requirements.md` + `epics.md` + `stories.md` in an initiative folder, handed to `/dev-plan-solution`; the **reasoning** lane (`ba-project-memory`, `ba-process-flow-diagram`, `ba-entity-state-grid`, `ba-decision-table`, the 11-class `ba-feature-conflict-check` + the `business-analyst` agent) keeps a persistent per-project business model and detects conflicts between features.

Every stack plugin (`qa-*`, `fe-*`, `be-*`) also bundles the 14 `ep-*` engineering-practices skills (brainstorm → plan → execute → verify → finish, TDD, systematic debugging, worktrees, agent dispatch, code-review pair, and the spec-compliance/feature audit pair) plus the read-only `code-auditor` agent. A 15th, `ep-standards-audit-engine`, is the shared engine behind the per-stack conformance audits — it ships in **all ten** `qa-*` / `fe-*` / `be-*` / `devops` / `security-governance` plugins. Where a stack's own conformance audit is not authored yet it simply sits inert — the engine carries no rules and its description forbids routing a request to it directly — so nothing needs rewiring when that audit lands. Authored so far: `/qa-dotnet-audit`, `/be-dotnet-audit`, `/fe-react-audit`, `/security-governance-audit`, and `/devops-auditor` (whose agent supplies its own rule sections, since devops is outside `CONFORMANCE-AUDIT-PLAN.md`'s scope; `security-governance` is also outside that scope but took the skill shape); `fe-react` carries its own copy of the procedure pending the extraction. The rest roll out per `CONFORMANCE-AUDIT-PLAN.md`.

A 16th, **`ep-agent-orientation-cache`**, ships in **all fifteen** plugins (including `data`, `business-analysis`, `penetration-testing`, `security-governance`, `training-data`, and `tooling`, which bundle no other `ep-*`): it is the protocol every agent uses to persist its orientation pass to `docs/agent-context/<agent-name>.md` in your project and reuse it next run, re-deriving only what a git delta proves changed. It makes repeat invocations cheap without letting a stale map be mistaken for evidence. Like the audit engine it is loaded by agents, never invoked directly.

A 17th, **`ep-code-comments`**, also ships in **all fifteen** plugins: it is the comment discipline every code-writing and code-reviewing skill applies — **no inline comments**, a short doc comment only where the name genuinely cannot carry the meaning *and* the flow is complex (pinned to four qualifying cases), nothing at all on trivia, and a stale comment deleted rather than updated. Test code adds one rule: the test name and the Arrange-Act-Assert shape *are* the explanation, so `// Arrange` banners are a finding, and exactly three comments are permitted. The six `code-review` reviewers, the nine QA test reviewers, the three conformance checklists, and 31 code-writing agents load it and supply only their own language's doc-comment and suppression syntax. Loaded, never invoked directly. Pull updates later with `/plugin marketplace update skills-library`.

### Slash commands

**Every agent ships a matching slash command, and so does every skill that produces a standalone artifact with nothing to orient on.** Agents are normally picked up by description match, which is probabilistic; the command is the deterministic entry point for when you would rather *name* the workflow than hope for it. Each command loads its agent definition and runs that agent's step-by-step workflow. Called bare with no argument, it runs the agent's orientation pass against the current repo and asks what you need.

**Code-touching skills deliberately have no command** — no `/qa-api-client-writer-<stack>`, no `/be-<stack>-generator`, no `/fe-<stack>-project-setup`, no `/devops-docker`. Reach them through their agent instead. The reason is orientation: an agent's first act is version detection (TFM / React major / engine version / Node major) plus reading existing files for conventions, and a skill invoked directly skips all of it — the exact way a .NET 8 repo ends up with a .NET 10 recipe. Agents are step-scoped and brownfield-capable, so "write me one API client" is a one-step agent run, not a six-step build. What keeps a command is the set with nothing to detect: prose artifacts (manual-QA writing, BA authoring), stack-agnostic design craft, the `ep-*` process entry points, and the read-only audits.

**`qa-java` · `qa-dotnet` · `qa-typescript`** — 23 commands each (`qa-dotnet` has 24 — see `/qa-dotnet-audit` below); substitute your stack for `<stack>`:

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
| `/qa-test-case-designer` | doc, story, contract, or URL | documentation (or a live page) → a systematically-derived test-case suite |
| `/qa-test-planner` | feature, doc, URL, or repo area | feature (documented or not) → a saved test plan: scope, harness looked up from the repo, artifacts, gap-analyzed case inventory |
| `/qa-security` | app, API, or layer | OWASP-mapped SAST, secrets, SCA, access-control, DAST, fuzzing, container/IaC, TLS gates |
| `/qa-dotnet-audit` *(qa-dotnet only so far)* | *(none — or a path/section limiter)* | read-only sweep of the **test suite** against the `qa-dotnet` conventions → findings report in `docs/audits/` |
| `/code-auditor` | spec, stories, feature, or area | read-only audit engagement, saved to `docs/audits/` |

…plus the 6 manual-QA writing commands and the 5 `ep-*` process commands listed under **Shared across plugins** below.

**`fe-blazor`** — 17 commands · **`fe-react`** — 18:

| Command | Argument | Runs |
|---|---|---|
| `/fe-blazor` | what to build, fix, or extend | the step-by-step Blazor Web App UI workflow |
| `/fe-react` | what to build, fix, or extend | the step-by-step React / Next.js UI workflow |
| `/fe-react-audit` *(fe-react only)* | *(none — or a path/section limiter)* | read-only sweep of the repo against the `fe-react` conventions → findings report in `docs/audits/` |
| `/code-auditor` | spec, stories, feature, or area | read-only audit engagement, saved to `docs/audits/` |
| `/design-ui-ux-pro-max` | a brief, or any design question | the vendored design-intelligence corpus — **the source of truth for design facts**: generate a full design system from a brief, or search 88 styles / 192 palettes / 74 font pairings / 119 UX guidelines / 105 icons / 34 landing patterns / 17 motion presets / 25 chart types / 22 stacks, offline |
| `/design-visual-identity` | brief or product | invent a per-brief token system + visual identity (the primary theme authority) |
| `/design-brand-import` | brand book or assets | normalize an existing brand into a token system |
| `/design-theme-presets` | look or mood | pick and apply one of 10 preset palette + font themes |
| `/design-tokens` | token system to build or fix | the primitive → semantic tier discipline |
| `/design-charts` | chart, dashboard, or data | product chart / data-viz design system |
| `/design-iconography` | icon set or social image | one icon family + OG / social imagery |
| `/design-motion` | a surface or product that needs motion | the product-wide intensity tier + the preset, duration, easing and teardown per trigger |
| `/design-landing-patterns` | a marketing page + what the visitor must decide | pick from 34 landing patterns — section order, CTA placement, color strategy, conversion rules |
| `/design-ux-writing` | screen, flow, or copy slots | microcopy voice for the slots the stack's UI skills define |
| `/design-ux-review` | screen, flow, or app | experience-level review — Nielsen heuristics, flow friction, IA |
| `/design-ui-code-audit` | UI source files | code-level audit against the vendored Web Interface Guidelines |
| `/design-accessible-by-design` | screen, flow, or design | the WCAG 2.2 decisions a scan can't make — target size, drag alternatives, accessible auth, cognitive load, layout-for-translation |
| `/design-ethical-patterns` | signup, checkout, cancel, consent, or permission flow | symmetry + the dark-pattern taxonomy prohibited under DSA Art. 25 / FTC §5 |
| `/design-ai-experience` | AI or agent feature | how it behaves on screen — streaming, stop, approval-with-context, uncertainty, correction, labelling |
| `/design-auditor` | *(none — or how to reach the app)* | the **whole** design audit in one run — visual identity, tokens, IA, heuristics, flow, responsiveness, UI code, copy, charts, icons, brand, motion, landing structure — read-only, saved to `docs/audits/` |

…plus `/qa-requirements-breakdown` and the 5 `ep-*` process commands listed under **Shared across plugins** below.

**`be-dotnet` · `be-java` · `be-node`** — 11 commands each (`be-dotnet` has 12 — see `/be-dotnet-audit` below; note the backend stacks are `dotnet` / `java` / **`node`**, not the QA triplet):

| Command | Argument | Runs |
|---|---|---|
| `/be-dotnet` · `/be-java` · `/be-node` | what to build, fix, or extend | apply a design pattern, the persistence layer, or service-side auth |
| `/dev-plan-solution` | the initiative folder from `/dev-refine`, the requirements, or `resume` | plan a whole application: an approved high-level blueprint, then the detail pack — DB structure, experience plan, service→resource→endpoint surface with request/response bodies, shared validation catalog, external dependencies — then the epic map (which lanes can run at once) and a task list where **every task is one epic, one story, one stack, one agent and one session**, closing with `NEXT-PROMPTS.md`: one ready-to-paste prompt per lane that can start right now. Writes plans, never code |
| `/dev-document-system` | the system or area, or `refresh` | the reverse: read an existing backend, split it into functional areas (you confirm the split), trace each one, and write what it does from the **end user's** perspective into `docs/business-model/` — one simple document per area: overview, setup parameters, how it works (triggers → steps → formulas), a full worked example with real numbers, open questions, with flowcharts, decision tables and state grids linked by ID. Every claim `file:line`-evidenced and tiered `#observed` / `#inferred` in a closing table; never invents intent. Read-only on code |
| `/dev-document` | the feature, in your own words (e.g. "the refund flow") | document **one** feature of an existing codebase: locate the implementation, trace it end to end, and write a single standalone `docs/features/<NNN>-<slug>.md` in the same simple shape — overview, scope, setup parameters, how it works (triggers → steps → formulas), a full worked example, open questions & findings, closing `file:line` evidence table. No KB writes; read-only on code |
| `/observability-engineer-dotnet` · `-java` · `-node` | what to instrument, query, or dashboard | OTel, structured logging, Grafana backends, dashboards |
| `/be-dotnet-audit` *(be-dotnet only so far)* | *(none — or a project/section limiter)* | read-only sweep of the service against the `be-dotnet` conventions (incl. the observability invariants) → findings report in `docs/audits/` |
| `/code-auditor` | spec, stories, feature, or area | read-only audit engagement, saved to `docs/audits/` |

…plus `/qa-requirements-breakdown` and the 5 `ep-*` process commands listed under **Shared across plugins** below.

**`devops`** — 8 commands:

| Command | Argument | Runs |
|---|---|---|
| `/devops-engineer` | what to containerize, provision, deploy, or wire | discover → **confirm the tool stack with you** → containerize → provision → deploy → pipeline → review |
| `/devops-auditor` | *(none — or a service/path/section limiter)* | discover → **confirm the audit scope with you** → read-only sweep of the existing image, IaC, k8s, deploy target, pipeline, identity and secrets against the `devops` conventions → findings report in `docs/audits/` |
| `/code-auditor` | spec, stories, feature, or area | read-only audit engagement, saved to `docs/audits/` |

…plus the 5 `ep-*` process commands listed under **Shared across plugins** below. The 9 `devops-*` skills (docker, IaC, kubernetes, the three CI hosts, the two cloud deployments, environment-config) are reached through the two agents — and because devops skills are keyed to *tools* rather than stacks, both agents inspect the repo and **confirm the tool stack with you before loading a single skill**, then load only what that answer selects.

**`penetration-testing`** — 3 commands:

| Command | Argument | Runs |
|---|---|---|
| `/security-test-planner` | repo, running system, cloud account, or a loose description | discover the attack surface, block for scope + authorization, emit an ordered task list binding each step to its lane agent |
| `/penetration-tester` | engagement id / scope-file path, or the owned-lab target | scope gate → recon → exploitation → priv-esc → lateral movement → post-exploitation (capped at proof) → report + cleanup verification |
| `/purple-team-engineer` | engagement id, target, or the ATT&CK technique set | detonate each technique and assert the alert fired — scored detected/not-detected, with the drift delta against the last round |

**`security-governance`** — 2 commands:

| Command | Argument | Runs |
|---|---|---|
| `/security-architect` | the system to build a posture picture for, or a round to consolidate | roll every lane's findings into one risk register, ATT&CK coverage map, evidence register, and remediation roadmap |
| `/security-governance-audit` | *(none — or a path/section limiter)* | read-only sweep of the repo's defensive-security artifacts against the `security-governance` conventions → findings report in `docs/audits/` |

**`data`** — 1 command:

| Command | Argument | Runs |
|---|---|---|
| `/data-architect` | what to model, secure, migrate, or tune | model, secure, implement, and tune a schema across 8 engines |

**`tooling`** — 1 command:

| Command | Argument | Runs |
|---|---|---|
| `/tooling-engineer` | what to expose, and whether you want MCP, CLI, or both | derive and confirm the capability contract, then build and smoke-test the MCP server and/or CLI over it |

**`training-data`** — 2 commands:

| Command | Argument | Runs |
|---|---|---|
| `/dataset-engineer` | what dataset to build — stage, modality, target model | spec → source/curate → synthesize → quality gate (decontamination last) → format & split → dataset card |
| `/dataset-auditor` | dataset path or name, and its eval targets | read-only audit across 8 sections — format, contamination, duplication, PII, license, composition, splits, card |

**`business-analysis`** — 9 commands:

| Command | Argument | Runs |
|---|---|---|
| `/dev-refine` | a loose description of what you want built | the front door: batched questions, then `requirements.md` + `epics.md` (`E1..En`) + `stories.md` (`US1..USn`) in a new initiative folder, ready for `/dev-plan-solution`. Also extends or audits an existing backlog |
| `/business-analyst` | feature or change to analyze | model flows, states and decisions, sweep for cross-feature conflicts, persist the KB |
| `/ba-scoping-writeup` | vague ask or stakeholder brief | structured single-initiative scoping writeup |
| `/ba-epic-writer` | scoped writeup | epics with a measurable outcome **and a plain-English section** (as-a/I-want/so-that, what gets built, how it fits — no technology), slicing strategy, child stories, epic DoD |
| `/ba-story-writer` | requirement or epic | INVEST user stories with Gherkin acceptance criteria |
| `/ba-process-flow-diagram` | requirements or feature | BPMN-disciplined Mermaid flow with swimlanes and labeled exits |
| `/ba-entity-state-grid` | business entity | one state × event grid, all features overlaid |
| `/ba-decision-table` | shared decision point | one merged decision table with a declared DMN hit policy |
| `/ba-feature-conflict-check` | new feature vs the KB | pairwise sweep with the 11-class conflict taxonomy |

**Shared across plugins.** Two families ship inside other plugins rather than standing alone:

| Command | In | Runs |
|---|---|---|
| `/dev-design` | all eight stack plugins + `devops` | one clear feature → approved technical design/spec in `docs/specs/` (loose or multi-capability ask → `/dev-refine`) |
| `/dev-plan-feature` | ″ | approved spec → bite-sized implementation plan in `docs/plans/` |
| `/dev-build` | ″ | execute a written plan task-by-task with checkpoints |
| `/ep-spec-vs-code-audit` | ″ | code vs a spec / stories → requirement register + verdicts |
| `/ep-feature-audit` | ″ | spec-less feature trace → surfaces, inventories, defect families |
| `/qa-test-case-writer` | `qa-*` | requirements → a Setup / Cases / Cleanup manual test-case suite |
| `/qa-test-plan-writer` | `qa-*` | inputs in hand → the assembled feature test-plan document |
| `/qa-requirements-breakdown` | `qa-*`, `fe-*`, `be-*` | a story / BRD / contract → a sourced test-basis document |
| `/qa-bug-report-writer` | `qa-*` | a defect description → a formal, reproducible bug report |
| `/qa-exploratory-charter-writer` | `qa-*` | a feature or area → a bounded session-based exploratory charter |
| `/qa-test-strategy` | `qa-*` | a release or project → a test strategy document |

`/code-auditor` ships in all eight stack plugins (`qa-*`, `fe-*`, `be-*`) and in `devops`, alongside the `ep-*` skills. If two installed plugins expose the same command name, disambiguate with `/plugin-name:command`.

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
devops/                 # Platform lane: docker, kubernetes, IaC (Bicep/Terraform), AWS/Azure deploy, CI pipelines, env config + devops-engineer & devops-auditor agents
observability/          # Grafana, OpenTelemetry, structured logging
security/               # Security domain in two lanes: pentest-* kill chain + purpleteam-* validation (penetration-testing) and secgov-* defensive/governance (security-governance) + 4 agents
training-data/          # LLM/VLM training-data engineering: td-* skills across 4 stages and 2 modalities + dataset-engineer & dataset-auditor agents
qa/                     # Test authoring (API/UI/perf), DB/email/network verification, CI pipelines, reporting (see QA skills below)
engineering-practices/  # TDD, debugging, code review, git worktrees, planning (from obra/superpowers)
meta/                   # Authoring skills themselves (writing-skills, skill-creator)
design/                 # Visual/UX: visual-identity, design-tokens, charts, brand-import, iconography, ux-review, theme-presets, ux-writing, ui-code-audit,
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
| `ui-test-author/playwright` | java · dotnet · typescript | Author Playwright UI tests |
| `ui-test-author/selenium` | java · dotnet · typescript | Author Selenium UI tests |
| `ui-test-author/appium` | java · dotnet · typescript | Author Appium mobile tests |
| `ui-test-author/reviewer` | java · dotnet · typescript | Review UI tests |
| `page-object-design` | java · dotnet · typescript | Page-object architecture (intent-revealing) |
| `api-contract-testing` | java · dotnet · typescript · _shared | Consumer/provider contract tests with Pact |
| `performance/k6` | typescript | Load tests with k6 (JS-native) |
| `performance/nbomber` | dotnet | Load tests with NBomber (.NET-only) |
| `performance/gatling` | java | Load tests with Gatling (JVM-only) |
| `performance/_shared` | — | Workload modelling, SLOs, perf gates |

### Verification inside tests

| Skill | Stacks | What it does |
|-------|--------|--------------|
| `db-testing/client` | java · dotnet · typescript | Connect, seed, query-assert, clean up |
| `db-testing/testcontainers` | java · dotnet · typescript | Postgres/SQL Server/Mongo/Redis lifecycle |
| `db-testing/verification-queries` | java · dotnet · typescript | Safe, parameterized assertion SQL |
| `email-testing` | java · dotnet · typescript | Capture/assert email — tool picked inside via `references/` (mailpit · mailosaur · gmail-imap · sendgrid-sandbox) |
| `messaging-testing` | java · dotnet · typescript | Produce/consume/assert against brokers — broker picked inside via `references/` (kafka · sqs · rabbitmq · service-bus) |
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
| `qa-python-web-testing` | UI automation with Python — Playwright web-app testing toolkit (Anthropic-provided import) |

## Adding a new skill

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and the templates in [`.skill-template/`](.skill-template/).

## Status

| Section               | State |
|-----------------------|-------|
| backend               | authored + shipped — `backend/_shared/` (2 pattern-card skills + the 8 `solution-planner` planning skills + the 3 `be-documenter` reverse-documentation skills + both stack-agnostic agents, bundled into all three plugins; `be-documenter` also into `business-analysis`) + `backend/{dotnet,java,node}/` (4 skills each: reference/generator/reviewer/persistence) + a step-by-step `be-*` agent per stack; `be-dotnet` additionally ships the `standards-audit` self-audit skill + `/be-dotnet-audit`; `be-dotnet` / `be-java` / `be-node` plugins |
| data                  | authored + shipped — 8 version-aware per-engine skills (postgresql, sqlserver, mysql, mongodb, redis, dynamodb, cosmosdb, elasticsearch) + 4 cross-engine `_shared` skills + the `data-architect` agent; `data` plugin |
| frontend              | authored + shipped — `frontend/blazor/` (22 skills + `fe-blazor` agent; `fe-blazor` plugin) and `frontend/react/` (24 skills incl. the `standards-audit` self-audit + `fe-react` agent + vendored Vercel seeds; `fe-react` plugin); `frontend/react-native/` parked, under construction |
| business-analysis     | authored + shipped — 9 `ba-*` skills (authoring + reasoning lanes) + the `requirements-author` and `business-analyst` agents; `business-analysis` plugin |
| auth                  | scaffolding |
| devops                | authored + shipped — 9 cloud/CI-keyed skills (docker, kubernetes, infrastructure-as-code, aws-deployment, azure-deployment, github-actions, gitlab-ci, azure-pipelines, environment-config) + the `devops-engineer` (build) and `devops-auditor` (read-only conformance audit, `/devops-auditor`) agents, both gated on a tool-stack confirmation before any skill loads; `devops` plugin |
| observability         | authored + shipped — 6 skills (per-stack `opentelemetry-*` / `structured-logging-*` + stack-agnostic loki-tempo, prometheus-mimir, queries, dashboards) + `observability-engineer-{dotnet,java,node}` agents; bundled into the `be-*` plugins |
| qa                    | authored — 30 code-producing nodes (mostly ×3 stacks) + 7 process skills. `qa-dotnet` additionally ships the `standards-audit` self-audit skill + `/qa-dotnet-audit` |
| engineering-practices | imported from obra/superpowers |
| meta                  | imported (writing-skills, skill-creator) |
| documents             | imported from anthropics/skills |
| design                | imported (Anthropic + Vercel) |
| communication         | imported + 3 authored (business-analysis, user-story-writer, stakeholder-updates) |
| security              | authored + shipped — 13 language-agnostic skills in two lanes: 7 `pentest-*` + 2 `purpleteam-*` (`penetration-testing` plugin) and 4 `secgov-*` + the `secgov-standards-audit` self-audit (`security-governance` plugin) + the `penetration-tester`, `security-test-planner`, `purple-team-engineer`, and `security-architect` agents |
| training-data         | authored + shipped — 8 `td-*` skills (3 `_shared` foundations + 5 stage lanes) + the `dataset-engineer` and `dataset-auditor` agents; `training-data` plugin |
| ai-development        | imported from anthropics/skills |
| tooling               | authored + shipped — 3 `tool-*` skills (`capability-contract` + the `mcp-builder` / `cli-builder` renderers) + the `tooling-engineer` agent; `tooling` plugin |
