# 004 — Plugin surface rework: dependencies, unprefixed names, collision-free commands — plan (2026-10-11)

**Goal:** Every skill and agent is registered in exactly one plugin per category, and the shared layers
(`dev`, `design`) arrive through Claude Code plugin `dependencies` instead of being copied into every
plugin. Skill names drop the domain and stack prefixes the plugin namespace already carries
(`/fe-react:fe-react-forms` → `/fe-react:forms`). Commands follow one scheme, and no name collides with
another name in the same plugin or with a Claude Code built-in.

**Status:** M1 landed 2026-10-11: `.claude-plugin/marketplace.json` lists the 21 plugins at version 3.0.0 with `dependencies`, all 64 command files sit at their §4 paths, and `tools/plugin-surface-check.py` exists. **Built but unverified:** nothing has been run (the plan gates once, in D1) — not `claude plugin validate`, the checker, the token audit or the version check. Prose still cites old names until R1. R1 is next. Baseline (2026-10-11) for D1: `claude plugin validate .` passes, `tools/token-audit.py` exits 1 on 90 pre-existing body-budget violations, and a typical project loads **25,281** always-on description tokens for 219 skill entries covering 182 distinct skills.
---

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| No skill or agent registered in two categories' plugins | 83 of 460 skill folders and 8 of 57 agents are registered in more than one plugin (`.claude-plugin/marketplace.json`). Examples: `engineering-practices/*` in 13 plugins, `code-auditor` in 13, `solution-planner` in 4, `be-documenter` in 5, design skills in 5 | §2 layout: new `dev` and `design` plugins, removal from every other plugin (M1) |
| Shared layers arrive automatically | They are copied: the same paths appear in many `skills` arrays. No plugin declares `dependencies` | `dependencies` on 15 plugins (§2.2, M1) |
| Internal skills stay out of the listing | `ep-agent-orientation-cache` and `ep-code-comments` are registered in all 19 plugins and `ep-standards-audit-engine` in 10, although their descriptions say "never invoke directly". Every registered description is in context every session | Unregister them; agents keep loading them by path (D2, M1) |
| Names without redundant prefixes | 459 of 460 `name:` values repeat what the plugin namespace says (`be-java:be-java-database-code`, `qa-java:qa-api-models-java`) | §5 renames (R1) |
| No duplicate name inside one plugin once the prefixes go | Dropping the prefixes mechanically would collide: in `be-*`, the shared `pattern-guide` and `code-review` clash with the stack's own; in `qa-*`, the shared and per-stack contract-testing skills clash; `mobile-react-native` registers three `basics` skills | Distinct names in §5, RN unregisters the iOS/Android `basics` (D11), and the checker enforces it (§8) |
| No collision with Claude Code built-ins | `training-data` registers `ai-development/claude-api` under `name: claude-api`, which is the name of the built-in skill. Four stack reviewers would become `code-review` once prefixes go | Unregister `claude-api` (D2). Stack reviewers become `conventions-review`. Reserved list enforced by the checker (§3.3, §8) |
| One command scheme | Audits are named `be-dotnet-audit` / `devops-auditor` / `code-auditor` / `dataset-auditor`. The `dev-*` family is split across `business-analysis`, the `be-*` plugins and every stack plugin | §4 map (M1) |
| Prose matches the new names | 161 skill/agent/command files mention `ep-*` / `be-shared-*` / `ba-*` / `td-*` names. 54 old slash forms appear inside skill trees. README, catalog and CLAUDE.md cite both | §6 rewrite (R1); prose sections (D1) |
| The README says how to configure the plugins | No per-project guidance. `claude plugin validate .` advises that README has no install line for `mobile-*` and `devops`. The maintainer's own `~/.claude/settings.json` enables `be-java`, `be-node`, `be-python` and `fe-react` globally | §7 (D1) |
| A gate for the plugin surface | `claude plugin validate .` passes. Nothing checks names, duplicates, reserved words or dependencies | `tools/plugin-surface-check.py` (§8, M1), run in the gate (§9, D1) |

## 2. Target layout

### 2.1 The rule

**Bundle within a category, depend across categories.** The user installs one plugin per category in a
project (O6): one `qa-*`, one `fe-*`, one `mobile-*`, one `be-*`. Sharing *inside* a category
duplicates nothing. `qa/_shared` sits in all three `qa-*` plugins, `observability/*` in three `be-*`
plugins and `mobile/_shared` in all three `mobile-*` plugins, and those all stay bundled. Anything used
by **more than one category** lives in exactly one plugin, and the others depend on it.

Categories: `qa`, `fe`, `be` and `mobile` are each the plugins with that prefix. Every other plugin is
its own category.

### 2.2 Plugins after this plan (21)

| Plugin | Registers | `dependencies` |
|---|---|---|
| **`dev`** *(new)* | **Skills** (17): `engineering-practices/{brainstorming,writing-plans,systematic-debugging,verify-before-done,spec-vs-code-audit,feature-audit}` and `backend/_shared/{solution-blueprint,data-model-plan,experience-plan,api-surface-plan,integration-plan,epic-map,delivery-plan,session-budget,codebase-survey,feature-trace,business-documentation}`. **Agents** (5): `engineering-practices/agents/code-auditor.md`, `backend/_shared/agents/{solution-planner,be-documenter,be-feature-documenter}.md`, `business-analysis/agents/requirements-author.md`. **Commands** (5): see §4 | — |
| **`design`** *(new)* | **Skills** (16): every `design/<x>/SKILL.md`. **Agent**: `design/agents/design-auditor.md`. **Command**: `design/commands/audit.md` | — |
| `qa-java` · `qa-dotnet` · `qa-typescript` | Today's set **minus** every `engineering-practices/*` skill, the `code-auditor` agent and the `dev-design` / `dev-plan-feature` / `code-auditor` commands. Keeps `qa/manual/requirements-breakdown` | `["dev"]` |
| `fe-blazor` · `fe-react` | Today's set **minus** `engineering-practices/*`, `design/*`, `auth/_shared/*`, `qa/manual/requirements-breakdown` and `backend/_shared/session-budget`, the `code-auditor` and `design-auditor` agents, and their commands plus `dev-design` / `dev-plan-feature` | `["dev", "design"]` |
| `mobile-react-native` · `mobile-ios` · `mobile-android` | The same removals as `fe-*`. `mobile-react-native` also stops registering `mobile/ios/skills/basics` and `mobile/android/skills/basics` (D11) | `["dev", "design"]` |
| `be-dotnet` · `be-java` · `be-node` · `be-python` | Today's set **minus** `engineering-practices/*`, every `backend/_shared/*` skill except `pattern-guide` and `code-review`, the four `business-analysis/skills/ba-*` skills, `design/{ui-ux-pro-max,ux-patterns}`, `auth/_shared/*` and `qa/manual/requirements-breakdown`; minus the `code-auditor`, `solution-planner`, `be-documenter` and `be-feature-documenter` agents and their commands. Keeps observability, bundled within the category | `["dev"]` |
| `devops` | Today's set **minus** `engineering-practices/*`, the `code-auditor` agent and the `code-auditor` / `dev-*` commands | `["dev"]` |
| `business-analysis` | The 9 `business-analysis/skills/ba-*` skills and the `business-analyst` agent. `requirements-author`, both documenters, their commands, the `backend/_shared/*` skills and `engineering-practices/*` all leave | `["dev"]` |
| `data` · `tooling` · `training-data` · `penetration-testing` · `security-governance` | Today's set **minus** `engineering-practices/*` and `backend/_shared/session-budget`. `training-data` also drops `ai-development/claude-api` (D2) | — |

**Unregistered and loaded by path only** (D2): `engineering-practices/{agent-orientation-cache,code-comments,standards-audit-engine}`,
`auth/_shared/{auth0-concepts,oidc-concepts}`, `ai-development/claude-api`. They stay on disk, and every
agent that loads them keeps doing so by path.

**Expected counts after M1.** The checker does not assert these; they are for the reviewer:

| Plugin | Skills | Agents | Commands |
|---|---|---|---|
| `qa-java` / `qa-dotnet` / `qa-typescript` | 82 / 86 / 82 | 11 / 11 / 11 | 11 / 12 / 11 |
| `fe-blazor` / `fe-react` | 23 / 26 | 1 / 1 | 1 / 2 |
| `mobile-react-native` / `mobile-ios` / `mobile-android` | 29 / 29 / 30 | 1 / 1 / 1 | 2 / 2 / 2 |
| `be-dotnet` / `be-java` / `be-node` / `be-python` | 16 / 15 / 13 / 8 | 2 / 2 / 2 / 1 | 3 / 2 / 2 / 1 |
| `devops` · `business-analysis` · `data` · `tooling` | 16 · 9 · 12 · 3 | 3 · 1 · 1 · 1 | 3 · 1 · 1 · 1 |
| `training-data` · `penetration-testing` · `security-governance` | 8 · 9 · 5 | 2 · 3 · 1 | 2 · 3 · 2 |
| `dev` · `design` | 17 · 16 | 5 · 1 | 5 · 1 |

### 2.3 Why path loads keep working

Every plugin entry has `"source": "./"` and `"strict": false`, so each installed plugin's cache holds
**the whole repo**. This was verified on 2026-10-11: `~/.claude/plugins/cache/skills-library/be-java/0ad710b5e102/`
contains every top-level folder, `design/` and `engineering-practices/` included. Agents load skills by
path (`${CLAUDE_PLUGIN_ROOT}/backend/java/skills/...`, with `engineering-practices/code-comments` cited
by path in 28 files). Registration only controls what is **listed and slash-invocable**. Removing a
skill from a plugin's `skills` array never breaks an agent that loads it by path.

## 3. Naming rules

### 3.1 Skills

- **`name:` is the topic only.** The plugin namespace already carries the domain and the stack, so a
  name never starts with the plugin's name, a domain prefix (`be-`, `fe-`, `qa-`, `mobile-`, `ba-`,
  `ep-`, `td-`, `tool-`, `secgov-`, `pentest-`, `purpleteam-`, `auth-`, `be-shared-`, `mobile-shared-`),
  and never ends in a stack token or `-shared`.
- **Unique within every plugin that registers it**, counting command names too (skills and commands
  share one slash namespace per plugin).
- **Never a reserved name** (§3.3).
- **Folders do not move** (D3). Paths are the load mechanism, and about 140 files cite them. A name may
  differ from its folder, and §5 is the record.
- **One meaning per word:** `-setup` creates a project, `-review` reviews, `audit` is a saved read-only
  sweep, and `concepts` explains how a framework works.

### 3.2 Commands

- **Each plugin's front-door agent command is the plugin's name** (`/fe-react`, `/be-java`, `/data`,
  `/devops`), so a bare `/fe-react` keeps working.
- **Every read-only conformance audit is `audit`** (`/be-dotnet:audit`, `/design:audit`, `/dev:audit`).
- **Every other command is a short role or topic** (`/qa-java:api`, `/penetration-testing:pentest`).
- **Agent identifiers do not change** (D4). `code-auditor`, `solution-planner` and the rest are what
  plans' `Agent:` lines and the Agent tool bind on. Only the command file names change.

### 3.3 Reserved names

These are Claude Code built-in commands and skills as of 2026-10-11. No skill name or command stem in
this marketplace may equal one:

```
add-dir agents artifacts bug clear claude-api code-review compact config context cost dataviz doctor
effort exit export fast feedback fewer-permission-prompts focus help hooks ide init install-github-app
keybindings-help login logout loop mcp memory migrate-installer model output-style permissions plan
plugin plugin-authoring pr-comments privacy-settings release-notes resume review rewind run schedule
security-review simplify status statusline terminal-setup todos update-config upgrade usage vim
workflow-authoring
```

## 4. Command map

Every file move is a `git mv`. New paths are relative to the repo root. "Typed as" is what the user
types.

| Old file | New file | Plugin(s) | Typed as |
|---|---|---|---|
| `qa/<stack>/commands/qa-api-<stack>.md` (and `-ui-`, `-mobile-`, `-performance-`, `-llm-`, `-bdd-`) | `qa/<stack>/commands/{api,ui,mobile,performance,llm,bdd}.md` | `qa-<stack>` | `/qa-<stack>:api` … `/qa-<stack>:bdd` |
| `qa/dotnet/commands/qa-dotnet-audit.md` | `qa/dotnet/commands/audit.md` | `qa-dotnet` | `/qa-dotnet:audit` |
| `qa/cicd/commands/qa-cicd-<stack>.md` | `qa/cicd/<stack>/commands/cicd.md` | `qa-<stack>` | `/qa-<stack>:cicd` |
| `qa/reporting/commands/qa-reporting-<stack>.md` | `qa/reporting/<stack>/commands/reporting.md` | `qa-<stack>` | `/qa-<stack>:reporting` |
| `qa/_shared/commands/qa-security.md` | `qa/_shared/commands/security.md` | all `qa-*` | `/qa-<stack>:security` |
| `qa/manual/commands/qa-test-case-designer.md` | `qa/manual/commands/test-cases.md` | all `qa-*` | `/qa-<stack>:test-cases` |
| `qa/manual/commands/qa-test-planner.md` | `qa/manual/commands/test-plan.md` | all `qa-*` | `/qa-<stack>:test-plan` |
| `frontend/react/commands/fe-react.md` · `frontend/blazor/commands/fe-blazor.md` | unchanged | `fe-react` · `fe-blazor` | `/fe-react` · `/fe-blazor` |
| `frontend/react/commands/fe-react-audit.md` | `frontend/react/commands/audit.md` | `fe-react` | `/fe-react:audit` |
| `mobile/<stack>/commands/mobile-<stack>.md` | unchanged | `mobile-<stack>` | `/mobile-<stack>` |
| `mobile/<stack>/commands/mobile-<stack>-audit.md` | `mobile/<stack>/commands/audit.md` | `mobile-<stack>` | `/mobile-<stack>:audit` |
| `backend/<stack>/commands/be-<stack>.md` | unchanged | `be-<stack>` | `/be-<stack>` |
| `backend/dotnet/commands/be-dotnet-audit.md` | `backend/dotnet/commands/audit.md` | `be-dotnet` | `/be-dotnet:audit` |
| `observability/commands/observability-engineer-<stack>.md` (dotnet, java, node) | `observability/commands/<stack>/observability.md` | `be-<stack>` | `/be-<stack>:observability` |
| `devops/commands/devops-engineer.md` | `devops/commands/devops.md` | `devops` | `/devops` |
| `devops/commands/devops-auditor.md` | `devops/commands/audit.md` | `devops` | `/devops:audit` |
| `devops/commands/infra-security-tester.md` | `devops/commands/infra-security.md` | `devops` | `/devops:infra-security` |
| `security/commands/security-test-planner.md` | `security/commands/engagement.md` | `penetration-testing` | `/penetration-testing:engagement` |
| `security/commands/penetration-tester.md` | `security/commands/pentest.md` | `penetration-testing` | `/penetration-testing:pentest` |
| `security/commands/purple-team-engineer.md` | `security/commands/purple-team.md` | `penetration-testing` | `/penetration-testing:purple-team` |
| `security/commands/security-architect.md` | `security/commands/architect.md` | `security-governance` | `/security-governance:architect` |
| `security/commands/security-governance-audit.md` | `security/commands/audit.md` | `security-governance` | `/security-governance:audit` |
| `data/commands/data-architect.md` | `data/commands/data.md` | `data` | `/data` |
| `tooling/commands/tooling-engineer.md` | `tooling/commands/tooling.md` | `tooling` | `/tooling` |
| `training-data/commands/dataset-engineer.md` | `training-data/commands/training-data.md` | `training-data` | `/training-data` |
| `training-data/commands/dataset-auditor.md` | `training-data/commands/audit.md` | `training-data` | `/training-data:audit` |
| `business-analysis/commands/business-analyst.md` | `business-analysis/commands/business-analysis.md` | `business-analysis` | `/business-analysis` |
| `business-analysis/commands/dev-refine.md` | `engineering-practices/commands/refine.md` | `dev` | `/dev:refine` |
| `backend/_shared/commands/dev-plan-solution.md` | `engineering-practices/commands/plan-system.md` | `dev` | `/dev:plan-system` |
| `backend/_shared/commands/dev-document-system.md` | `engineering-practices/commands/document-system.md` | `dev` | `/dev:document-system` |
| `backend/_shared/commands/dev-document.md` | `engineering-practices/commands/document-feature.md` | `dev` | `/dev:document-feature` |
| `engineering-practices/commands/code-auditor.md` | `engineering-practices/commands/audit.md` | `dev` | `/dev:audit` |
| `engineering-practices/commands/dev-design.md` · `dev-plan-feature.md` | **deleted** (D6) | — | `/dev:design` · `/dev:plan-feature` are now the skills |
| `design/commands/design-auditor.md` | `design/commands/audit.md` | `design` | `/design:audit` |

Result: **64 command files** (66 today, minus the two deleted wrappers) and 70 registrations.

**Old slash forms that are planned but not built yet** also map, because live plans cite them:
`/qa-java-audit` → `/qa-java:audit`, `/qa-typescript-audit` → `/qa-typescript:audit`,
`/fe-blazor-audit` → `/fe-blazor:audit`. Old slash forms of removed skill wrappers (for example
`/qa-bug-report-writer`, `/ep-feature-audit`, `/design-tokens`) map to the skill's new typed name from
§5, written `/<plugin>:<new-name>`.

## 5. Skill rename table

This table is the contract R1 applies. Rows with `<stack>` stand for each stack listed in their
**Stacks** column (`all` = `java`, `dotnet`, `typescript` for QA; `dotnet`, `java`, `node` for
observability). The old name carries the same `<stack>` suffix. "unregistered" means the skill keeps
its new `name:` but no plugin lists it (D2).

### 5a. `dev` plugin and unregistered internals

| Folder | Old name | New name | Note |
|---|---|---|---|
| `engineering-practices/agent-orientation-cache` | `ep-agent-orientation-cache` | `orientation-cache` | unregistered |
| `engineering-practices/brainstorming` | `ep-brainstorming` | `design` |  |
| `engineering-practices/code-comments` | `ep-code-comments` | `code-comments` | unregistered |
| `engineering-practices/feature-audit` | `ep-feature-audit` | `audit-feature` |  |
| `engineering-practices/spec-vs-code-audit` | `ep-spec-vs-code-audit` | `audit-spec` |  |
| `engineering-practices/standards-audit-engine` | `ep-standards-audit-engine` | `audit-engine` | unregistered |
| `engineering-practices/systematic-debugging` | `ep-systematic-debugging` | `debugging` |  |
| `engineering-practices/verify-before-done` | `ep-verify-before-done` | `verify` |  |
| `engineering-practices/writing-plans` | `ep-writing-plans` | `plan-feature` |  |

### 5b. `dev` (planning, documentation) and `be-*` (pattern pair)

| Folder | Old name | New name | Note |
|---|---|---|---|
| `backend/_shared/api-surface-plan` | `be-shared-api-surface-plan` | `plan-api-surface` |  |
| `backend/_shared/business-documentation` | `be-shared-business-documentation` | `doc-business-model` |  |
| `backend/_shared/code-review` | `be-shared-code-review` | `architecture-review` |  |
| `backend/_shared/codebase-survey` | `be-shared-codebase-survey` | `doc-codebase-survey` |  |
| `backend/_shared/data-model-plan` | `be-shared-data-model-plan` | `plan-data-model` |  |
| `backend/_shared/delivery-plan` | `be-shared-delivery-plan` | `plan-delivery` |  |
| `backend/_shared/epic-map` | `be-shared-epic-map` | `plan-epic-map` |  |
| `backend/_shared/experience-plan` | `be-shared-experience-plan` | `plan-experience` |  |
| `backend/_shared/feature-trace` | `be-shared-feature-trace` | `doc-feature-trace` |  |
| `backend/_shared/integration-plan` | `be-shared-integration-plan` | `plan-integrations` |  |
| `backend/_shared/pattern-guide` | `be-shared-pattern-guide` | `pattern-catalog` |  |
| `backend/_shared/session-budget` | `be-shared-session-budget` | `plan-session-budget` |  |
| `backend/_shared/solution-blueprint` | `be-shared-solution-blueprint` | `plan-blueprint` |  |

### 5c. `business-analysis`

| Folder | Old name | New name | Note |
|---|---|---|---|
| `business-analysis/skills/ba-decision-table` | `ba-decision-table` | `decision-table` |  |
| `business-analysis/skills/ba-entity-state-grid` | `ba-entity-state-grid` | `state-grid` |  |
| `business-analysis/skills/ba-epic-writer` | `ba-epic-writer` | `epics` |  |
| `business-analysis/skills/ba-feature-conflict-check` | `ba-feature-conflict-check` | `conflict-check` |  |
| `business-analysis/skills/ba-process-flow-diagram` | `ba-process-flow-diagram` | `process-flow` |  |
| `business-analysis/skills/ba-project-memory` | `ba-project-memory` | `knowledge-base` |  |
| `business-analysis/skills/ba-scoping-writeup` | `ba-scoping-writeup` | `scoping` |  |
| `business-analysis/skills/ba-story-quality-review` | `ba-story-quality-review` | `story-review` |  |
| `business-analysis/skills/ba-story-writer` | `ba-story-writer` | `stories` |  |

### 5d. `design`

| Folder | Old name | New name | Note |
|---|---|---|---|
| `design/accessible-by-design` | `design-accessible-by-design` | `accessibility` |  |
| `design/ai-experience` | `design-ai-experience` | `ai-experience` |  |
| `design/brand-import` | `design-brand-import` | `brand-import` |  |
| `design/charts` | `design-charts` | `charts` |  |
| `design/design-tokens` | `design-tokens` | `tokens` |  |
| `design/ethical-patterns` | `design-ethical-patterns` | `dark-patterns` |  |
| `design/iconography` | `design-iconography` | `iconography` |  |
| `design/landing-patterns` | `design-landing-patterns` | `landing-patterns` |  |
| `design/motion` | `design-motion` | `motion` |  |
| `design/theme-presets` | `design-theme-presets` | `theme-presets` |  |
| `design/ui-code-audit` | `design-ui-code-audit` | `ui-code-audit` |  |
| `design/ui-ux-pro-max` | `design-ui-ux-pro-max` | `corpus` |  |
| `design/ux-patterns` | `design-ux-patterns` | `app-structure` |  |
| `design/ux-review` | `design-ux-review` | `ux-review` |  |
| `design/ux-writing` | `design-ux-writing` | `ux-writing` |  |
| `design/visual-identity` | `design-visual-identity` | `visual-identity` |  |

### 5e. `be-<stack>`

| Folder | Old name | New name | Note |
|---|---|---|---|
| `backend/dotnet/skills/auth0` | `be-dotnet-auth0` | `auth0` |  |
| `backend/dotnet/skills/code-review` | `be-dotnet-code-review` | `conventions-review` |  |
| `backend/dotnet/skills/cognito` | `be-dotnet-cognito` | `cognito` |  |
| `backend/dotnet/skills/database-code` | `be-dotnet-database-code` | `persistence` |  |
| `backend/dotnet/skills/pattern-guide` | `be-dotnet-pattern-guide` | `patterns` |  |
| `backend/dotnet/skills/pattern-writer` | `be-dotnet-pattern-writer` | `patterns-apply` |  |
| `backend/dotnet/skills/standards-audit` | `be-dotnet-standards-audit` | `standards-audit` |  |
| `backend/dotnet/skills/unit-testing` | `be-dotnet-unit-testing` | `unit-testing` |  |
| `backend/java/skills/auth0` | `be-java-auth0` | `auth0` |  |
| `backend/java/skills/code-review` | `be-java-code-review` | `conventions-review` |  |
| `backend/java/skills/cognito` | `be-java-cognito` | `cognito` |  |
| `backend/java/skills/database-code` | `be-java-database-code` | `persistence` |  |
| `backend/java/skills/pattern-guide` | `be-java-pattern-guide` | `patterns` |  |
| `backend/java/skills/pattern-writer` | `be-java-pattern-writer` | `patterns-apply` |  |
| `backend/java/skills/unit-testing` | `be-java-unit-testing` | `unit-testing` |  |
| `backend/node/skills/code-review` | `be-node-code-review` | `conventions-review` |  |
| `backend/node/skills/database-code` | `be-node-database-code` | `persistence` |  |
| `backend/node/skills/pattern-guide` | `be-node-pattern-guide` | `patterns` |  |
| `backend/node/skills/pattern-writer` | `be-node-pattern-writer` | `patterns-apply` |  |
| `backend/node/skills/unit-testing` | `be-node-unit-testing` | `unit-testing` |  |
| `backend/python/skills/code-review` | `be-python-code-review` | `conventions-review` |  |
| `backend/python/skills/media-processing` | `be-python-media-processing` | `media-processing` |  |
| `backend/python/skills/pattern-guide` | `be-python-pattern-guide` | `patterns` |  |
| `backend/python/skills/pattern-writer` | `be-python-pattern-writer` | `patterns-apply` |  |
| `backend/python/skills/sandboxed-worker` | `be-python-sandboxed-worker` | `sandboxed-worker` |  |
| `backend/python/skills/unit-testing` | `be-python-unit-testing` | `unit-testing` |  |

### 5f. `be-dotnet` · `be-java` · `be-node` (bundled within the category)

| Folder | Old name | New name | Stacks |
|---|---|---|---|
| `observability/dashboards` | `observability-dashboards` | `dashboards` |  |
| `observability/logs-traces-setup` | `observability-logs-traces-setup` | `logs-traces` |  |
| `observability/metrics-setup` | `observability-metrics-setup` | `metrics` |  |
| `observability/opentelemetry-<stack>` | `observability-opentelemetry-<stack>` | `opentelemetry` | all |
| `observability/queries` | `observability-queries` | `queries` |  |
| `observability/structured-logging-<stack>` | `observability-structured-logging-<stack>` | `structured-logging` | all |

### 5g. `fe-<stack>`

| Folder | Old name | New name | Note |
|---|---|---|---|
| `frontend/blazor/skills/accessibility` | `fe-blazor-accessibility` | `accessibility` |  |
| `frontend/blazor/skills/animation` | `fe-blazor-animation` | `animation` |  |
| `frontend/blazor/skills/basics` | `fe-blazor-basics` | `concepts` |  |
| `frontend/blazor/skills/code-review` | `fe-blazor-code-review` | `conventions-review` |  |
| `frontend/blazor/skills/component-library` | `fe-blazor-component-library` | `component-library` |  |
| `frontend/blazor/skills/component-testing` | `fe-blazor-component-testing` | `component-testing` |  |
| `frontend/blazor/skills/component-writer` | `fe-blazor-component-writer` | `component-writer` |  |
| `frontend/blazor/skills/data-fetching` | `fe-blazor-data-fetching` | `data-fetching` |  |
| `frontend/blazor/skills/error-handling` | `fe-blazor-error-handling` | `error-handling` |  |
| `frontend/blazor/skills/forms` | `fe-blazor-forms` | `forms` |  |
| `frontend/blazor/skills/installable-offline-app` | `fe-blazor-installable-offline-app` | `pwa` |  |
| `frontend/blazor/skills/javascript-calls` | `fe-blazor-javascript-calls` | `js-interop` |  |
| `frontend/blazor/skills/languages` | `fe-blazor-languages` | `i18n` |  |
| `frontend/blazor/skills/performance` | `fe-blazor-performance` | `performance` |  |
| `frontend/blazor/skills/project-setup` | `fe-blazor-project-setup` | `project-setup` |  |
| `frontend/blazor/skills/realtime` | `fe-blazor-realtime` | `realtime` |  |
| `frontend/blazor/skills/responsive-design` | `fe-blazor-responsive-design` | `responsive-design` |  |
| `frontend/blazor/skills/seo` | `fe-blazor-seo` | `seo` |  |
| `frontend/blazor/skills/state-management` | `fe-blazor-state-management` | `state-management` |  |
| `frontend/blazor/skills/styling` | `fe-blazor-styling` | `styling` |  |
| `frontend/blazor/skills/test-ids` | `fe-blazor-test-ids` | `test-ids` |  |
| `frontend/blazor/skills/ui-rules` | `fe-blazor-ui-rules` | `ui-rules` |  |
| `frontend/react/skills/accessibility` | `fe-react-accessibility` | `accessibility` |  |
| `frontend/react/skills/animation` | `fe-react-animation` | `animation` |  |
| `frontend/react/skills/basics` | `fe-react-basics` | `concepts` |  |
| `frontend/react/skills/code-review` | `fe-react-code-review` | `conventions-review` |  |
| `frontend/react/skills/component-library` | `fe-react-component-library` | `component-library` |  |
| `frontend/react/skills/component-testing` | `fe-react-component-testing` | `component-testing` |  |
| `frontend/react/skills/component-writer` | `fe-react-component-writer` | `component-writer` |  |
| `frontend/react/skills/data-fetching` | `fe-react-data-fetching` | `data-fetching` |  |
| `frontend/react/skills/data-grid` | `fe-react-data-grid` | `data-grid` |  |
| `frontend/react/skills/error-handling` | `fe-react-error-handling` | `error-handling` |  |
| `frontend/react/skills/forms` | `fe-react-forms` | `forms` |  |
| `frontend/react/skills/installable-offline-app` | `fe-react-installable-offline-app` | `pwa` |  |
| `frontend/react/skills/languages` | `fe-react-languages` | `i18n` |  |
| `frontend/react/skills/migration` | `fe-react-migration` | `migration` |  |
| `frontend/react/skills/performance` | `fe-react-performance` | `performance` |  |
| `frontend/react/skills/project-setup` | `fe-react-project-setup` | `project-setup` |  |
| `frontend/react/skills/realtime` | `fe-react-realtime` | `realtime` |  |
| `frontend/react/skills/responsive-design` | `fe-react-responsive-design` | `responsive-design` |  |
| `frontend/react/skills/routing` | `fe-react-routing` | `routing` |  |
| `frontend/react/skills/seo` | `fe-react-seo` | `seo` |  |
| `frontend/react/skills/standards-audit` | `fe-react-standards-audit` | `standards-audit` |  |
| `frontend/react/skills/state-management` | `fe-react-state-management` | `state-management` |  |
| `frontend/react/skills/styling` | `fe-react-styling` | `styling` |  |
| `frontend/react/skills/test-ids` | `fe-react-test-ids` | `test-ids` |  |
| `frontend/react/skills/ui-rules` | `fe-react-ui-rules` | `ui-rules` |  |

### 5h. `mobile-<stack>`

| Folder | Old name | New name | Note |
|---|---|---|---|
| `mobile/_shared/in-app-purchases` | `mobile-shared-in-app-purchases` | `in-app-purchases` |  |
| `mobile/_shared/observability` | `mobile-shared-observability` | `observability` |  |
| `mobile/_shared/release` | `mobile-shared-release` | `release` |  |
| `mobile/_shared/security` | `mobile-shared-security` | `security` |  |
| `mobile/_shared/store-compliance` | `mobile-shared-store-compliance` | `store-compliance` |  |
| `mobile/android/skills/accessibility` | `mobile-android-accessibility` | `accessibility` |  |
| `mobile/android/skills/animation` | `mobile-android-animation` | `animation` |  |
| `mobile/android/skills/architecture` | `mobile-android-architecture` | `architecture` |  |
| `mobile/android/skills/basics` | `mobile-android-basics` | `concepts` |  |
| `mobile/android/skills/code-review` | `mobile-android-code-review` | `conventions-review` |  |
| `mobile/android/skills/device-features` | `mobile-android-device-features` | `device-features` |  |
| `mobile/android/skills/error-handling` | `mobile-android-error-handling` | `error-handling` |  |
| `mobile/android/skills/forms` | `mobile-android-forms` | `forms` |  |
| `mobile/android/skills/kotlin-multiplatform` | `mobile-android-kotlin-multiplatform` | `kotlin-multiplatform` |  |
| `mobile/android/skills/languages` | `mobile-android-languages` | `i18n` |  |
| `mobile/android/skills/migration` | `mobile-android-migration` | `migration` |  |
| `mobile/android/skills/navigation` | `mobile-android-navigation` | `navigation` |  |
| `mobile/android/skills/networking` | `mobile-android-networking` | `networking` |  |
| `mobile/android/skills/notifications-and-links` | `mobile-android-notifications-and-links` | `push-and-deep-links` |  |
| `mobile/android/skills/offline-and-storage` | `mobile-android-offline-and-storage` | `offline-and-storage` |  |
| `mobile/android/skills/performance` | `mobile-android-performance` | `performance` |  |
| `mobile/android/skills/project-setup` | `mobile-android-project-setup` | `project-setup` |  |
| `mobile/android/skills/standards-audit` | `mobile-android-standards-audit` | `standards-audit` |  |
| `mobile/android/skills/styling` | `mobile-android-styling` | `styling` |  |
| `mobile/android/skills/system-integration` | `mobile-android-system-integration` | `system-integration` |  |
| `mobile/android/skills/test-ids` | `mobile-android-test-ids` | `test-ids` |  |
| `mobile/android/skills/ui-components` | `mobile-android-ui-components` | `ui-components` |  |
| `mobile/android/skills/unit-testing` | `mobile-android-unit-testing` | `unit-testing` |  |
| `mobile/android/skills/views-interop` | `mobile-android-views-interop` | `views-interop` |  |
| `mobile/ios/skills/accessibility` | `mobile-ios-accessibility` | `accessibility` |  |
| `mobile/ios/skills/animation` | `mobile-ios-animation` | `animation` |  |
| `mobile/ios/skills/architecture` | `mobile-ios-architecture` | `architecture` |  |
| `mobile/ios/skills/basics` | `mobile-ios-basics` | `concepts` |  |
| `mobile/ios/skills/code-review` | `mobile-ios-code-review` | `conventions-review` |  |
| `mobile/ios/skills/device-features` | `mobile-ios-device-features` | `device-features` |  |
| `mobile/ios/skills/error-handling` | `mobile-ios-error-handling` | `error-handling` |  |
| `mobile/ios/skills/forms` | `mobile-ios-forms` | `forms` |  |
| `mobile/ios/skills/languages` | `mobile-ios-languages` | `i18n` |  |
| `mobile/ios/skills/migration` | `mobile-ios-migration` | `migration` |  |
| `mobile/ios/skills/navigation` | `mobile-ios-navigation` | `navigation` |  |
| `mobile/ios/skills/networking` | `mobile-ios-networking` | `networking` |  |
| `mobile/ios/skills/notifications-and-links` | `mobile-ios-notifications-and-links` | `push-and-deep-links` |  |
| `mobile/ios/skills/offline-and-storage` | `mobile-ios-offline-and-storage` | `offline-and-storage` |  |
| `mobile/ios/skills/performance` | `mobile-ios-performance` | `performance` |  |
| `mobile/ios/skills/project-setup` | `mobile-ios-project-setup` | `project-setup` |  |
| `mobile/ios/skills/standards-audit` | `mobile-ios-standards-audit` | `standards-audit` |  |
| `mobile/ios/skills/styling` | `mobile-ios-styling` | `styling` |  |
| `mobile/ios/skills/system-integration` | `mobile-ios-system-integration` | `system-integration` |  |
| `mobile/ios/skills/test-ids` | `mobile-ios-test-ids` | `test-ids` |  |
| `mobile/ios/skills/ui-components` | `mobile-ios-ui-components` | `ui-components` |  |
| `mobile/ios/skills/uikit` | `mobile-ios-uikit` | `uikit` |  |
| `mobile/ios/skills/unit-testing` | `mobile-ios-unit-testing` | `unit-testing` |  |
| `mobile/react-native/skills/accessibility` | `mobile-react-native-accessibility` | `accessibility` |  |
| `mobile/react-native/skills/animation` | `mobile-react-native-animation` | `animation` |  |
| `mobile/react-native/skills/architecture` | `mobile-react-native-architecture` | `architecture` |  |
| `mobile/react-native/skills/basics` | `mobile-react-native-basics` | `concepts` |  |
| `mobile/react-native/skills/code-review` | `mobile-react-native-code-review` | `conventions-review` |  |
| `mobile/react-native/skills/component-library` | `mobile-react-native-component-library` | `component-library` |  |
| `mobile/react-native/skills/component-testing` | `mobile-react-native-component-testing` | `component-testing` |  |
| `mobile/react-native/skills/device-features` | `mobile-react-native-device-features` | `device-features` |  |
| `mobile/react-native/skills/error-handling` | `mobile-react-native-error-handling` | `error-handling` |  |
| `mobile/react-native/skills/forms` | `mobile-react-native-forms` | `forms` |  |
| `mobile/react-native/skills/languages` | `mobile-react-native-languages` | `i18n` |  |
| `mobile/react-native/skills/migration` | `mobile-react-native-migration` | `migration` |  |
| `mobile/react-native/skills/native-modules` | `mobile-react-native-native-modules` | `native-modules` |  |
| `mobile/react-native/skills/navigation` | `mobile-react-native-navigation` | `navigation` |  |
| `mobile/react-native/skills/networking` | `mobile-react-native-networking` | `networking` |  |
| `mobile/react-native/skills/notifications-and-links` | `mobile-react-native-notifications-and-links` | `push-and-deep-links` |  |
| `mobile/react-native/skills/offline-and-storage` | `mobile-react-native-offline-and-storage` | `offline-and-storage` |  |
| `mobile/react-native/skills/performance` | `mobile-react-native-performance` | `performance` |  |
| `mobile/react-native/skills/project-setup` | `mobile-react-native-project-setup` | `project-setup` |  |
| `mobile/react-native/skills/standards-audit` | `mobile-react-native-standards-audit` | `standards-audit` |  |
| `mobile/react-native/skills/styling` | `mobile-react-native-styling` | `styling` |  |
| `mobile/react-native/skills/test-ids` | `mobile-react-native-test-ids` | `test-ids` |  |
| `mobile/react-native/skills/ui-components` | `mobile-react-native-ui-components` | `ui-components` |  |

### 5i. `fe-*` · `mobile-*` (auth0) and unregistered concepts

| Folder | Old name | New name | Note |
|---|---|---|---|
| `auth/_shared/auth0-concepts` | `auth-auth0-concepts` | `auth0-concepts` | unregistered |
| `auth/_shared/oidc-concepts` | `auth-oidc-concepts` | `oidc-concepts` | unregistered |
| `auth/auth0-android` | `auth-auth0-android` | `auth0` |  |
| `auth/auth0-blazor` | `auth-auth0-blazor` | `auth0` |  |
| `auth/auth0-ios` | `auth-auth0-ios` | `auth0` |  |
| `auth/auth0-react` | `auth-auth0-react` | `auth0` |  |
| `auth/auth0-react-native` | `auth-auth0-react-native` | `auth0` |  |

### 5j. `qa-<stack>` — per-stack skills

| Folder | Old name | New name | Stacks |
|---|---|---|---|
| `qa/<stack>/skills/accessibility-testing` | `qa-accessibility-testing-<stack>` | `accessibility-testing` | all |
| `qa/<stack>/skills/ai-answer-quality-testing` | `qa-ai-answer-quality-testing-<stack>` | `ai-answer-quality-testing` | all |
| `qa/<stack>/skills/ai-feature-testing` | `qa-ai-feature-testing-<stack>` | `ai-feature-testing` | all |
| `qa/<stack>/skills/api-client-writer` | `qa-api-client-writer-<stack>` | `api-client-writer` | all |
| `qa/<stack>/skills/api-contract-testing` | `qa-api-contract-testing-<stack>` | `api-contract-testing` | all |
| `qa/<stack>/skills/api-models` | `qa-api-models-<stack>` | `api-models` | all |
| `qa/<stack>/skills/api-project-setup` | `qa-api-project-setup-<stack>` | `api-project-setup` | dotnet |
| `qa/<stack>/skills/api-test-author/graphql` | `qa-api-test-graphql-<stack>` | `api-tests-graphql` | all |
| `qa/<stack>/skills/api-test-author/grpc` | `qa-api-test-grpc-<stack>` | `api-tests-grpc` | all |
| `qa/<stack>/skills/api-test-author/playwright` | `qa-api-test-playwright-<stack>` | `api-tests-playwright` | all |
| `qa/<stack>/skills/api-test-author/review` | `qa-api-test-review-<stack>` | `api-tests-review` | all |
| `qa/<stack>/skills/api-test-author/writer` | `qa-api-test-writer-<stack>` | `api-tests` | all |
| `qa/<stack>/skills/bdd-project-scaffold` | `qa-bdd-project-setup-<stack>` | `bdd-project-setup` | all |
| `qa/<stack>/skills/bdd-reviewer` | `qa-bdd-reviewer-<stack>` | `bdd-reviewer` | all |
| `qa/<stack>/skills/browser-cloud-setup` | `qa-browser-cloud-setup-<stack>` | `browser-cloud-setup` | all |
| `qa/<stack>/skills/data-driven-testing` | `qa-data-driven-testing-<stack>` | `data-driven-testing` | all |
| `qa/<stack>/skills/db-testing/connection` | `qa-db-connection-<stack>` | `db-connection` | all |
| `qa/<stack>/skills/db-testing/testcontainers` | `qa-db-testing-testcontainers-<stack>` | `db-testcontainers` | all |
| `qa/<stack>/skills/db-testing/verification-queries` | `qa-db-verification-queries-<stack>` | `db-verification-queries` | all |
| `qa/<stack>/skills/device-cloud` | `qa-device-cloud-<stack>` | `device-cloud` | all |
| `qa/<stack>/skills/email-testing` | `qa-email-testing-<stack>` | `email-testing` | all |
| `qa/<stack>/skills/evidence-capture` | `qa-evidence-capture-<stack>` | `evidence-capture` | all |
| `qa/<stack>/skills/failure-injection-testing` | `qa-failure-injection-testing-<stack>` | `failure-injection-testing` | all |
| `qa/<stack>/skills/feature-flag-testing` | `qa-feature-flag-testing-<stack>` | `feature-flag-testing` | all |
| `qa/<stack>/skills/file-storage-testing` | `qa-file-storage-testing-<stack>` | `file-storage-testing` | all |
| `qa/<stack>/skills/gherkin-step-code` | `qa-gherkin-step-code-<stack>` | `gherkin-step-code` | all |
| `qa/<stack>/skills/inhouse-framework-conventions` | `qa-inhouse-framework-conventions-<stack>` | `inhouse-framework-conventions` | all |
| `qa/<stack>/skills/language-testing` | `qa-language-testing-<stack>` | `language-testing` | all |
| `qa/<stack>/skills/load-testing` | `qa-load-testing-<stack>` | `load-testing` | all |
| `qa/<stack>/skills/messaging-testing` | `qa-messaging-testing-<stack>` | `messaging-testing` | all |
| `qa/<stack>/skills/mobile-app-crawler` | `qa-mobile-app-crawler-<stack>` | `mobile-app-crawler` | all |
| `qa/<stack>/skills/mobile-native-features` | `qa-mobile-native-features-<stack>` | `mobile-native-features` | all |
| `qa/<stack>/skills/mobile-project-setup` | `qa-mobile-project-setup-<stack>` | `mobile-project-setup` | all |
| `qa/<stack>/skills/mobile-screen-explorer` | `qa-mobile-screen-explorer-<stack>` | `mobile-screen-explorer` | all |
| `qa/<stack>/skills/mobile-screen-objects` | `qa-mobile-screen-objects-<stack>` | `mobile-screen-objects` | all |
| `qa/<stack>/skills/network-mocking` | `qa-network-mocking-<stack>` | `network-mocking` | all |
| `qa/<stack>/skills/page-object-design` | `qa-page-object-design-<stack>` | `page-object-design` | all |
| `qa/<stack>/skills/page-objects-from-url` | `qa-page-objects-from-url-<stack>` | `page-objects-from-url` | all |
| `qa/<stack>/skills/performance-project-setup` | `qa-performance-project-setup-<stack>` | `performance-project-setup` | dotnet |
| `qa/<stack>/skills/production-uptime-checks` | `qa-production-uptime-checks-<stack>` | `production-uptime-checks` | all |
| `qa/<stack>/skills/realtime-stream-testing` | `qa-realtime-stream-testing-<stack>` | `realtime-stream-testing` | all |
| `qa/<stack>/skills/responsive-testing` | `qa-responsive-testing-<stack>` | `responsive-testing` | all |
| `qa/<stack>/skills/security-testing/dependency-scan` | `qa-security-dependency-scan-<stack>` | `dependency-scan` | all |
| `qa/<stack>/skills/security-testing/passive-scan` | `qa-security-passive-scan-<stack>` | `passive-scan` | all |
| `qa/<stack>/skills/security-testing/permission-testing` | `qa-permission-testing-<stack>` | `permission-testing` | all |
| `qa/<stack>/skills/standards-audit` | `qa-dotnet-standards-audit` | `standards-audit` | dotnet |
| `qa/<stack>/skills/test-data-builder` | `qa-test-data-builder-<stack>` | `test-data-builder` | all |
| `qa/<stack>/skills/test-login-tokens` | `qa-test-login-tokens-<stack>` | `test-login-tokens` | all |
| `qa/<stack>/skills/test-quality-check` | `qa-test-quality-check-<stack>` | `test-quality-check` | java, dotnet |
| `qa/<stack>/skills/ui-project-setup` | `qa-ui-project-setup-<stack>` | `ui-project-setup` | dotnet |
| `qa/<stack>/skills/ui-test-author/appium` | `qa-ui-test-writer-appium-<stack>` | `ui-tests-appium` | all |
| `qa/<stack>/skills/ui-test-author/playwright` | `qa-ui-test-writer-playwright-<stack>` | `ui-tests-playwright` | all |
| `qa/<stack>/skills/ui-test-author/review` | `qa-ui-test-review-<stack>` | `ui-tests-review` | all |
| `qa/<stack>/skills/ui-test-author/selenium` | `qa-ui-test-writer-selenium-<stack>` | `ui-tests-selenium` | all |
| `qa/<stack>/skills/visual-regression` | `qa-visual-regression-<stack>` | `visual-regression` | all |
| `qa/<stack>/skills/ui-test-author/maestro` | `qa-ui-test-writer-maestro-<stack>` | `ui-tests-maestro` | typescript |

### 5k. `qa-*` — shared, manual, CI and reporting skills

| Folder | Old name | New name | Stacks |
|---|---|---|---|
| `qa/_shared/api-spec-assets` | `qa-api-spec-assets-shared` | `api-spec-assets` |  |
| `qa/_shared/bdd/feature-file-writer` | `qa-feature-file-writer` | `feature-files` |  |
| `qa/_shared/contract-testing-pact` | `qa-api-contract-testing-shared` | `contract-pact` |  |
| `qa/_shared/performance` | `qa-performance-shared` | `performance-foundations` |  |
| `qa/_shared/python-web-testing` | `qa-python-web-testing` | `python-web-testing` |  |
| `qa/_shared/security` | `qa-security-shared` | `security-foundations` |  |
| `qa/_shared/security-testing/active-scan` | `qa-security-active-scan` | `active-scan` |  |
| `qa/_shared/security-testing/api-fuzzing` | `qa-security-testing-api-fuzzing` | `api-fuzzing` |  |
| `qa/_shared/security-testing/certificate-scan` | `qa-security-certificate-scan` | `certificate-scan` |  |
| `qa/_shared/security-testing/client-side-security` | `qa-security-client-side-security` | `client-side-security` |  |
| `qa/_shared/security-testing/code-scan` | `qa-security-code-scan` | `code-scan` |  |
| `qa/_shared/security-testing/exploit-validation` | `qa-security-exploit-validation` | `exploit-validation` |  |
| `qa/_shared/security-testing/image-infra-scan` | `qa-security-image-infra-scan` | `image-infra-scan` |  |
| `qa/_shared/security-testing/known-vuln-scan` | `qa-security-known-vuln-scan` | `known-vuln-scan` |  |
| `qa/_shared/security-testing/mobile-app-scan` | `qa-security-mobile-app-scan` | `mobile-app-scan` |  |
| `qa/_shared/security-testing/mobile-runtime-testing` | `qa-security-mobile-runtime-testing` | `mobile-runtime-testing` |  |
| `qa/_shared/security-testing/secrets-scan` | `qa-security-secrets-scan` | `secrets-scan` |  |
| `qa/_shared/security-testing/vuln-reachability` | `qa-security-vuln-reachability` | `vuln-reachability` |  |
| `qa/_shared/webmcp-testing` | `qa-webmcp-testing-shared` | `webmcp-testing` |  |
| `qa/cicd/ci-conventions` | `qa-ci-conventions-shared` | `ci-conventions` |  |
| `qa/cicd/<stack>/skills/ci-pipelines` | `qa-ci-pipelines-<stack>` | `ci-pipelines` | all |
| `qa/manual/bug-report-writer` | `qa-bug-report-writer` | `bug-report-writer` |  |
| `qa/manual/exploratory-charter-writer` | `qa-exploratory-charter-writer` | `exploratory-charter-writer` |  |
| `qa/manual/quality-metrics` | `qa-quality-metrics` | `quality-metrics` |  |
| `qa/manual/requirements-breakdown` | `qa-requirements-breakdown` | `requirements-breakdown` |  |
| `qa/manual/test-case-writer` | `qa-test-case-writer` | `test-case-writer` |  |
| `qa/manual/test-design-techniques` | `qa-test-design-techniques` | `test-design-techniques` |  |
| `qa/manual/test-plan-writer` | `qa-test-plan-writer` | `test-plan-writer` |  |
| `qa/manual/test-strategy` | `qa-test-strategy` | `test-strategy` |  |
| `qa/reporting/<stack>/skills/flaky-test-quarantine` | `qa-flaky-test-quarantine-<stack>` | `flaky-test-quarantine` | all |
| `qa/reporting/<stack>/skills/test-reports` | `qa-test-reports-<stack>` | `test-reports` | all |

### 5l. `data`

| Folder | Old name | New name | Note |
|---|---|---|---|
| `data/_shared/caching-patterns` | `data-caching-patterns` | `caching` |  |
| `data/_shared/migrations` | `data-migrations` | `migrations` |  |
| `data/_shared/schema-design` | `data-schema-design` | `schema-design` |  |
| `data/_shared/slow-query-fixes` | `data-slow-query-fixes` | `query-tuning` |  |
| `data/cosmosdb` | `data-cosmosdb` | `cosmosdb` |  |
| `data/dynamodb` | `data-dynamodb` | `dynamodb` |  |
| `data/elasticsearch` | `data-elasticsearch` | `elasticsearch` |  |
| `data/mongodb` | `data-mongodb` | `mongodb` |  |
| `data/mysql` | `data-mysql` | `mysql` |  |
| `data/postgresql` | `data-postgresql` | `postgresql` |  |
| `data/redis` | `data-redis` | `redis` |  |
| `data/sqlserver` | `data-sqlserver` | `sqlserver` |  |

### 5m. `devops`

| Folder | Old name | New name | Note |
|---|---|---|---|
| `devops/aws-deployment` | `devops-aws-deployment` | `aws-deployment` |  |
| `devops/azure-deployment` | `devops-azure-deployment` | `azure-deployment` |  |
| `devops/azure-pipelines` | `devops-azure-pipelines` | `azure-pipelines` |  |
| `devops/cloud-posture` | `devops-cloud-posture` | `cloud-posture` |  |
| `devops/container-runtime-security` | `devops-container-runtime-security` | `container-runtime-security` |  |
| `devops/docker` | `devops-docker` | `docker` |  |
| `devops/environment-config` | `devops-environment-config` | `environment-config` |  |
| `devops/github-actions` | `devops-github-actions` | `github-actions` |  |
| `devops/gitlab-ci` | `devops-gitlab-ci` | `gitlab-ci` |  |
| `devops/iac-security` | `devops-iac-security` | `iac-security` |  |
| `devops/infra-controls-validation` | `devops-infra-controls-validation` | `controls-validation` |  |
| `devops/infrastructure-as-code` | `devops-infrastructure-as-code` | `iac` |  |
| `devops/k8s-security` | `devops-k8s-security` | `kubernetes-security` |  |
| `devops/kubernetes` | `devops-kubernetes` | `kubernetes` |  |
| `devops/supply-chain-security` | `devops-supply-chain-security` | `supply-chain-security` |  |
| `devops/threat-modeling` | `devops-threat-modeling` | `threat-modeling` |  |

### 5n. `penetration-testing` · `security-governance`

| Folder | Old name | New name | Note |
|---|---|---|---|
| `security/atomic-simulation` | `purpleteam-atomic-simulation` | `atomic-simulation` |  |
| `security/compliance-evidence-mapping` | `secgov-compliance-evidence-mapping` | `compliance-evidence-mapping` |  |
| `security/credential-attacks` | `pentest-credential-attacks` | `credential-attacks` |  |
| `security/detection-engineering` | `secgov-detection-engineering` | `detection-engineering` |  |
| `security/detection-validation` | `purpleteam-detection-validation` | `detection-validation` |  |
| `security/initial-access` | `pentest-initial-access` | `initial-access` |  |
| `security/lateral-movement` | `pentest-lateral-movement` | `lateral-movement` |  |
| `security/pentest-reporting` | `pentest-reporting` | `reporting` |  |
| `security/post-exploitation` | `pentest-post-exploitation` | `post-exploitation` |  |
| `security/privilege-escalation` | `pentest-privilege-escalation` | `privilege-escalation` |  |
| `security/recon-enumeration` | `pentest-recon-enumeration` | `recon-enumeration` |  |
| `security/secrets-hardening` | `secgov-secrets-hardening` | `secrets-hardening` |  |
| `security/security-hardening` | `secgov-security-hardening` | `hardening` |  |
| `security/standards-audit` | `secgov-standards-audit` | `standards-audit` |  |

### 5o. `tooling`

| Folder | Old name | New name | Note |
|---|---|---|---|
| `tooling/_shared/capability-contract` | `tool-capability-contract` | `capability-contract` |  |
| `tooling/skills/cli-builder` | `tool-cli-builder` | `cli-builder` |  |
| `tooling/skills/mcp-builder` | `tool-mcp-builder` | `mcp-builder` |  |

### 5p. `training-data`

| Folder | Old name | New name | Note |
|---|---|---|---|
| `training-data/_shared/td-data-quality` | `td-data-quality` | `data-quality` |  |
| `training-data/_shared/td-dataset-formats` | `td-dataset-formats` | `dataset-formats` |  |
| `training-data/_shared/td-synthetic-generation` | `td-synthetic-generation` | `synthetic-generation` |  |
| `training-data/skills/td-eval-sets` | `td-eval-sets` | `eval-sets` |  |
| `training-data/skills/td-instruction-sft` | `td-instruction-sft` | `instruction-sft` |  |
| `training-data/skills/td-preference-data` | `td-preference-data` | `preference-data` |  |
| `training-data/skills/td-pretraining-corpus` | `td-pretraining-corpus` | `pretraining-corpus` |  |
| `training-data/skills/td-vision-language-data` | `td-vision-language-data` | `vision-language-data` |  |

### 5q. `training-data` (unregistered)

| Folder | Old name | New name | Note |
|---|---|---|---|
| `ai-development/claude-api` | `claude-api` | `claude-api` | unregistered |

## 6. How R1 rewrites references

**Scope.** Every tracked `*.md` and `*.json` file **except** `docs/plans/implemented/**`,
`docs/audits/**`, `docs/research/**` and this plan file. Those are records and are never edited (D10).
The vendored `design/ui-ux-pro-max/**` is in scope only for its `SKILL.md` frontmatter `name:` line and
for exact matches of the old name `design-ui-ux-pro-max`. The product name `ui-ux-pro-max` on its own is
never touched.

1. **Frontmatter.** In each `SKILL.md`, the `name:` line becomes the bare new name from §5.
2. **Skill mentions in prose.** Each exact old name (expanded per stack) becomes:
   - `<plugin>:<new>` when exactly one plugin registers the folder after M1 (`fe-react-forms` →
     `fe-react:forms`, `qa-api-models-java` → `qa-java:api-models`, `ep-brainstorming` → `dev:design`);
   - `<category>-<stack>:<new>` written literally when every plugin of one category registers it
     (`qa-performance-shared` → `qa-<stack>:performance-foundations`, `be-shared-code-review` →
     `be-<stack>:architecture-review`, `observability-dashboards` → `be-<stack>:dashboards`,
     `mobile-shared-release` → `mobile-<stack>:release`);
   - the folder path when no plugin registers it (`ep-code-comments` → `engineering-practices/code-comments`).
   - Match with `(?<![\w/.-])OLD(?![\w-]|/)`. That never matches inside a path, so
     `design/design-tokens/SKILL.md` and `business-analysis/skills/ba-story-writer/` survive. Replace
     longest names first.
3. **Collapse repeats.** After step 2, `` `X` (`X`) `` becomes `` `X` ``. Agents wrote
   `` `engineering-practices/code-comments` (`ep-code-comments`) ``, which would otherwise read as the
   same path twice.
4. **Slash mentions.** Each old typed form in §4 becomes its new typed form. Match with
   `(?<![\w/.-])/OLD(?![\w-]|\.md)`, so `engineering-practices/commands/code-auditor.md` is a path and
   is left alone. Agent names without a leading slash (`code-auditor`, `solution-planner`) are agent
   identifiers and are **not** rewritten.
5. **Family wildcards are edited by hand** because the right replacement depends on the sentence. On
   2026-10-11 there were 76: `` `ep-*` `` ×49, `` `qa-ci-pipelines-*` `` ×8, `` `secgov-*` `` ×7,
   `` `qa-test-reports-*` `` ×4, `` `pentest-*` `` ×3, `` `ba-*` `` ×3, `` `be-shared-*` `` ×1,
   `` `auth-auth0-*` `` ×1. Typical outcomes: "the `dev` skills", "`qa-<stack>:ci-pipelines`",
   "`security-governance:*`", "the always-on internals (`engineering-practices/{agent-orientation-cache,code-comments}`)".
6. **Counts in prose** that this plan changes (for example "ships in all sixteen plugins" for the
   orientation cache) are fixed where R1 meets them inside skill and agent files. README, catalog and
   CLAUDE.md prose sections belong to D1.

## 7. What the README must say (D1)

- **Install one plugin per category in a project.** A shared layer installs itself: `qa-*`, `fe-*`,
  `mobile-*`, `be-*`, `devops` and `business-analysis` pull in `dev`; `fe-*` and `mobile-*` also pull
  in `design`. Give one `/plugin install <name>@skills-library` line **for every plugin**, which clears
  the validator's advice about missing lines for `mobile-*` and `devops`, plus `dev` and `design` for
  completeness.
- **Configure per project, not globally.** Install at user scope, keep every skills-library plugin
  `false` in `~/.claude/settings.json`, and enable the project's set in the project's
  `.claude/settings.json` (higher scope wins per plugin, O2):

  ```json
  { "enabledPlugins": { "be-java@skills-library": true, "fe-react@skills-library": true, "qa-typescript@skills-library": true } }
  ```

  Dependencies (`dev`, `design`) are enabled with them and cannot be disabled while a dependent is on.
- **Typing names.** Skills and commands are `/<plugin>:<name>`. A bare `/<name>` works while only one
  enabled plugin has that name. When two do (for example `forms` in `fe-react` and
  `mobile-react-native`), type the plugin-qualified form.
- **Using the repo directly** (symlinking into `.claude/skills`) supports **one stack per project**,
  because unprefixed names from two stacks collide outside a plugin namespace.
- The command tables are rewritten to §4's typed forms: one table per plugin, plus `dev` and `design`.

## 8. `tools/plugin-surface-check.py` (M1 writes it, D1 runs it)

A standalone Python 3 script in the shape of `tools/token-audit.py` (stdlib only, `ROOT` from the
script path). It prints `OK` and exits 0, or prints one line per failure and exits 1. Checks, over
`.claude-plugin/marketplace.json`:

1. **Paths exist.** Every `skills` entry is a folder holding `SKILL.md`, and every `agents` and
   `commands` entry is a file.
2. **Unique per plugin.** Within each plugin, the set of skill `name:` values plus command file stems
   has no duplicate. The message names the plugin, the name and both sources.
3. **Not reserved.** No skill name or command stem is in §3.3's list, kept in the script as a
   `RESERVED` constant.
4. **No prefixes.** No skill name starts with its plugin's name + `-`, or with `be-shared-`,
   `mobile-shared-`, `ep-`, `ba-`, `td-`, `tool-`, `secgov-`, `pentest-`, `purpleteam-`, `auth-`, and
   none ends in `-java`, `-dotnet`, `-typescript`, `-node`, `-python` or `-shared`.
5. **Registered once per category.** No skill folder or agent file is registered by plugins of two
   different categories (§2.1).
6. **Dependencies resolve.** Every `dependencies` entry names a plugin in this marketplace, and the
   dependency graph has no cycle.

## 9. The gate (D1 only)

Run from the repo root, in this order. Fix what fails, because a failure may belong to M1 or R1.

1. `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` exits 0.
2. `claude plugin validate .` ends with `✔ Validation passed`. Then run
   `claude plugin validate . --strict` and record its result in D1's As built. Strict is informative,
   not blocking, unless it names a `dependencies` problem, and that one is fixed.
3. `python3 tools/plugin-surface-check.py` prints `OK`.
4. `python3 tools/token-audit.py --violations-only` reports **0** skill-description violations and
   **≤ 90** body violations (the 2026-10-11 baseline; the script exits 1 on those pre-existing body
   violations, which is expected). Then `python3 tools/token-audit.py` gives the always-on `desc(tok)`
   for `be-java` + `fe-react` + `qa-typescript` + `data` + `business-analysis` + `dev` + `design`.
   Record it in `Status` against the **25,281** baseline.
5. `python3 tools/qa-version-check.py` prints `OK`.
6. **Old-name sweep.** Every old name in §5's "Old name" column that differs from its new name
   (expanded per stack) and every old typed form in §4 that changed has **zero** matches in §6's scope. Use §6's regexes. A match left on purpose is a
   bug.

## 10. Decisions

**D1 — Bundle within a category, depend across categories.** One plugin per category is installed per
project (O6), so sharing inside a category costs nothing, and sharing across categories is what
duplicates.

| Option | Verdict | Why |
|---|---|---|
| Keep bundling everything (today) | rejected | The typical project lists 37 duplicate skill entries. The listing budget is about 1% of context, and when it is exceeded descriptions are dropped starting with the least-used skills, so duplicates push real skills out |
| A plugin per shared folder (`observability`, `auth`, `qa-shared`, …) with dependencies everywhere | rejected | More plugins to maintain, and no gain: within-category sharing duplicates nothing |
| Shared-across-categories layers become plugins (`dev`, `design`); everything else stays bundled | **chosen** | Removes every cross-category duplicate with two new plugins |

Cost: two more plugins in the marketplace, and dependency behaviour on update has to be verified by a
person (H1).

**D2 — Path-loaded internals are unregistered, not moved into a `core` plugin.** §2.3 shows path loads
work without registration. Cost: `orientation-cache`, `code-comments` and `audit-engine` no longer
appear in `/` (their descriptions already said never to invoke them). `auth0-concepts` and
`oidc-concepts` lose description auto-triggering and are reached through the stack `auth0` skills
that load them. `claude-api` leaves `training-data`, and the built-in Claude Code `claude-api` skill
serves that name. If a plugin's `source` ever stops being `./`, these path loads break, and the
checker does not detect that.

**D3 — Skill names are the topic only, and folders stay.** Cost: a bare `/forms` is ambiguous when two
enabled plugins register `forms`, and repo-direct use supports one stack per project (§7). Renaming
folders too would rewrite about 140 files of load paths for no runtime gain.

**D4 — The front-door command takes the plugin's name, audits are `audit`, and agent identifiers are
unchanged.** Cost: command file names no longer match agent names (`devops.md` runs `devops-engineer`).
Changing the agent identifiers would break every plan's `Agent:` line.

**D5 — The whole delivery lane lives in `dev`** (refine, design, plan-feature, plan-system,
document-system, document-feature, audit), and `business-analysis` depends on `dev`. The `dev-*`
family the user built becomes the `/dev:` namespace. Cost: `requirements-author` is registered by
`dev` while its file stays in `business-analysis/agents/`, and the ba-* skills it loads by path are
registered only in `business-analysis`.

**D6 — The `dev-design` and `dev-plan-feature` wrapper commands are deleted.** The skills renamed
`design` and `plan-feature` take the typed names `/dev:design` and `/dev:plan-feature`, the same thing
done to the 33 skill wrappers on 2026-10-11 (commit `45e7b71`).

**D7 — A reserved-name list is enforced.** The docs do not say whether a plugin skill named like a
built-in shadows it or loses to it, so the library never finds out. Cost: the list is hand-kept and
dated 2026-10-11.

**D8 — Dependencies are declared by bare name, with no version range.** Every plugin ships from one
repo commit, so a range would only add drift to maintain. Cost: no protection against mixing
marketplace revisions.

**D9 — Marketplace version 3.0.0.** Every typed slash name changes, so it is a breaking release.

**D10 — Records keep the old names.** `docs/plans/implemented/`, `docs/audits/` and `docs/research/`
are never edited, so the old-name sweep (§9.6) excludes them.

**D11 — `mobile-react-native` stops registering the iOS and Android `basics` skills.** The RN agent
loads them by path. Otherwise the plugin would hold three skills named `concepts`.

## Answered questions (2026-10-11)

**O1 — Can a plugin declare dependencies?** Yes, with `dependencies` in `plugin.json` or the marketplace
entry. Installing a plugin installs and enables its dependencies at the same scope, and a dependency
cannot be disabled while an enabled plugin needs it (code.claude.com/docs/en/plugins/dependencies.md).

**O2 — Can a user-scope plugin be switched off per project?** Yes. `"<plugin>@<marketplace>": false`
in `.claude/settings.json` or `.claude/settings.local.json` wins per key over user settings
(plugins/loading.md).

**O3 — Does `user-invocable: false` cut the context cost?** No. Only `disable-model-invocation: true`
removes a description from context (skills.md). This plan unregisters instead (D2).

**O4 — May two skills in one plugin share a `name:`?** It is not documented, so it is treated as
forbidden and the checker enforces it.

**O5 — Is engineering-practices shipped standalone today?** No. It is bundled into 13 plugins, and two
of its skills into all 19. `dev` is the standalone plugin it never had.

**O6 — Is one plugin per category installed per project?** Yes; the user stated it on 2026-10-11.

## Open questions

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| Q1 | Does an already-installed plugin pull in a newly declared dependency on `/plugin marketplace update`, or only on install? | Not documented. Either way, H1 installs `dev` / `design` explicitly if they are missing | Nothing in M1–D1; H1 records the answer | the user |

## 11. Tasks

**The cost, accepted and stated once:** intermediate commits are ungated, so the tree is **not** known
to validate at every task boundary, and the plan cannot be stopped halfway and trusted. Between M1 and
R1 the marketplace points at renamed commands while prose still cites old names.

### M1 — marketplace restructure, command moves, and the surface checker

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `.claude-plugin/marketplace.json` lists the 21 plugins of §2.2 with their
`dependencies`, version `3.0.0`, and every command at its §4 path; `tools/plugin-surface-check.py`
implements §8.
**Depends on:** —
**Budget:** ~92k — floor 25k (system prompt, CLAUDE.md, agent), plan §2, §3, §4, §8 and D1–D9 ~12k,
task block 1k, the edit script ~4k, reading the 8 plugin descriptions that mention moved pieces
(`be-*`, `business-analysis`, `fe-*`) ~10k, rewriting them ~6k, 55 `git mv`, 2 `git rm` and the 2 new entries ~8k,
the checker ~5k, commit and diff read-back 6k, churn ×1.2.
**Gate: none** — this plan gates once, in D1. Do not run `claude plugin validate`, the checker,
`tools/token-audit.py` or `tools/qa-version-check.py`.

- Edit `marketplace.json` with a Python script, never by hand-retyping the file, and never round-trip
  it through `json.dumps`, which rewrites the `—` escapes in two descriptions. Edit the `skills`,
  `agents` and `commands` arrays line by line, fix any trailing comma, and confirm the result parses
  with `json.loads` inside the script.
- Add the `dev` and `design` entries with §2.2's skills, agents and commands, `"source": "./"`,
  `"strict": false`, author, license, keywords and category in the existing entries' shape, and a
  description each.
- Apply §2.2's removals and add each plugin's `"dependencies"` array exactly as §2.2 lists it.
- `git mv` every command file per §4 (creating `qa/cicd/<stack>/commands/`,
  `qa/reporting/<stack>/commands/` and `observability/commands/<stack>/`), `git rm` the two wrappers,
  and point every `commands` entry at its new path.
- Rewrite the plugin descriptions that describe moved pieces: the `be-*` entries drop the
  solution-planner / documenter / ep paragraphs, `business-analysis` drops requirements-author and the
  documenters, and `fe-*` / `mobile-*` say design arrives through the `design` dependency. Update
  `metadata.description` to name `dev` and `design`, and set `metadata.version` to `3.0.0`.
- Write `tools/plugin-surface-check.py` per §8.
- **Not in M1:** any `SKILL.md` `name:` change or prose rewrite (R1); README, catalog, CLAUDE.md and
  CONTRIBUTING (D1). Command bodies keep their old prose; R1 rewrites their slash mentions.
- **As built (2026-10-11):** no divergence from the plan. Per-plugin skills/agents/commands counts match §2.2's expected-counts table for all 21 plugins (`dev` 17/5/5, `design` 16/1/1, `qa-dotnet` 86/11/12, `mobile-android` 30/1/2). `marketplace.json` was edited line by line (`dev` and `design` inserted first in `plugins`; `dependencies` sits after `category`), parses with `json.loads`, and has 64 unique command paths that all exist. 55 command files were `git mv`d and `engineering-practices/commands/{dev-design,dev-plan-feature}.md` were `git rm`d. Per-stack commands moved to `qa/cicd/<stack>/commands/cicd.md`, `qa/reporting/<stack>/commands/reporting.md` and `observability/commands/<stack>/observability.md`. Descriptions were rewritten for the `fe-*`, `mobile-*`, `be-*`, `business-analysis`, `devops`, `data`, `tooling`, `penetration-testing`, `security-governance` entries and `metadata`; `qa-dotnet`'s only changed to `/qa-dotnet:audit`. Command file bodies still hold old prose (R1). `RESERVED` in the checker is §3.3's list. Proof: `python3 -m json.tool .claude-plugin/marketplace.json` exits 0; `tools/plugin-surface-check.py` is the checker, **not run**.

### R1 — skill renames and reference rewrite

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** every registered and unregistered `SKILL.md` carries its §5 `name:`, and no file in
§6's scope contains an old skill name from §5 or an old typed command form from §4.
**Depends on:** M1 (the post-M1 registrations decide each mention's `<plugin>:` form).
**Budget:** ~105k — floor 25k, plan §4, §5 and §6 ~15k, task block 1k, the rewrite script ~5k, its
dry-run report (per-name counts) ~8k, hand edits of the 76 wildcard sites with context ~15k,
spot-checking 12 diffs across domains ~12k, commit read-back 6k, churn ×1.2. If it runs over, the split
point is by domain: `qa/` in one session, everything else in the next.
**Gate: none** — this plan gates once, in D1. Do not run `claude plugin validate`, the checker or the
token audit.

- Write a one-off script in the session scratchpad, not in the repo, that parses §5's tables from this
  plan file, expands `<stack>` rows per their Stacks column, reads the post-M1 registrations from
  `marketplace.json`, and applies §6 steps 1–4 to §6's scope. Run it with `--dry-run` first and read
  the per-name counts. A name with zero hits outside its own `SKILL.md` is fine. A name with hits inside
  a path means the regex is wrong; stop and fix it.
- Apply it, then do §6 step 5 (wildcards) and step 6 (counts in skill and agent prose) by hand.
- Spot-check one diff in each of: an agent (`backend/java/agents/be-java.md`), a QA skill, a design
  skill, a command file, `marketplace.json`, and `docs/skills-catalog.md`.
- **Not in R1:** rewriting README, catalog or CLAUDE.md *sections* (D1). R1's mechanical pass does run
  over them, so D1 starts from correct names.

### D1 — documentation, the gate, and close-out

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** §9's gate passes end to end; README, `docs/skills-catalog.md`, CLAUDE.md, CONTRIBUTING
and `.skill-template/*` describe the §2 layout, §3 rules and §4 names.
**Depends on:** M1 (layout, checker), R1 (names).
**Budget:** ~125k — floor 25k, plan §2, §3, §4, §7, §9 and the Decisions ~12k, task block 1k, README
read ~13k, the catalog's scope paragraph and command section ~8k, CONTRIBUTING ~2k, writes (README
~8k, catalog ~4k, CLAUDE.md ~2k, CONTRIBUTING ~2k, templates ~1k), gate output 12k, fix loop ~15k,
churn ×1.2.
**Gate:** §9, in order. This is the plan's only gate. Fix what it finds, whichever task it belongs to.

- **README** (`README.md` §"Slash commands" and the install section): §7 in full; rewrite every
  command table to §4's typed forms, one per plugin, plus `dev` and `design`; delete the paragraph
  about "Code-touching skills deliberately have no command"; restate the `ep-*` / orientation-cache /
  code-comments paragraphs in terms of `dev` and the unregistered internals.
- **`docs/skills-catalog.md`**: the "Scope & published plugins" paragraph (21 plugins, the two
  dependencies, what moved), the "Slash-command surface" section (§4 table, 64 files), and the
  per-domain lines that say where a skill ships.
- **CLAUDE.md**: the catalog pointer's command count ("66-command" → "64-command"); in "Repository
  map", `engineering-practices/` ships as `dev` and `design/` ships as `design`, and remove "bundled
  into" wording that is no longer true.
- **CONTRIBUTING.md**: a "Names and registration" section stating §3.1–§3.3 and §2.1, and that
  `python3 tools/plugin-surface-check.py` must print `OK` before a commit that touches
  `marketplace.json` or a `name:`.
- **`.skill-template/*.SKILL.md`**: next to `name: <skill-name>`, the rule "topic only, no domain or
  stack prefix, unique within its plugin, not a reserved name".
- Run §9. Then write H1's prompt-block checklist from what actually landed, rewrite `Status`, and
  **leave the plan in `docs/plans/`**: H1 still holds a block.
- **Not in D1:** pushing, editing the user's `~/.claude/settings.json`, reinstalling plugins (H1).

### H1 — verify the installed result

**Stack:** `human` · **Agent:** `human` · **Owner:** the user
**Deliverable:** in a real project with the new marketplace revision installed, `dev` (and `design`
under `fe-*` / `mobile-*`) is installed as a dependency, `/dev:` lists `refine`, `design`,
`plan-feature`, `plan-system`, `document-system`, `document-feature` and `audit`, and no skill appears
under two plugins.
**Depends on:** D1, and the plan's commits on `origin/master`.
**Budget:** a few minutes, no subscription cost beyond one short agent run.
**Gate:** the checklist in H1's prompt block.

## Close-out — every task

Before you stop, in this order, in this file:

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Your own block** — delete it, and update the line above the blocks that says which have landed.
   Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming the blocker and
   its owner.
5. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified.
6. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified) and `git mv` this plan into `docs/plans/implemented/`, same
   name and number — a `solution-planner` pack moves its whole initiative folder.
7. **Commit** — the code, its tests and these plan edits together, in one commit.

## Prompts — one per task

Run them in order, one session each, opened from Plan Queue. Each block is complete on its own.

- **Gates:** M1 and R1 are `Gate: none`. D1 runs §9 once for everything.
- **What no block may do:** create a branch or worktree, push, edit `~/.claude/settings.json` or
  anything outside the repo, reinstall plugins, or edit `docs/plans/implemented/`, `docs/audits/` or
  `docs/research/`.
- **H1** is the user's. It runs after the commits are on `origin/master`, and its block keeps the plan
  in `docs/plans/` until the user deletes it.

| # | Stack | Agent | Depends on | Budget |
|---|---|---|---|---|
| M1 | `docs` | `general-purpose` | — | ~92k |
| R1 | `docs` | `general-purpose` | M1 | ~105k |
| D1 | `docs` | `general-purpose` | M1, R1 | ~125k |
| H1 | `human` | **the user** | D1, pushed | minutes |

M1 has landed; its block is deleted. The R1, D1 and H1 blocks are live.

---

### R1 — skill renames and reference rewrite (general-purpose, docs)

````
You are `general-purpose`. Task R1 of docs/plans/004-plugin-surface-rework.md: give every skill its
§5 name and rewrite every reference to old skill names and old command forms.

Deliverable: every registered and unregistered `SKILL.md` carries its §5 `name:`, and no file in §6's
scope contains an old skill name from §5 or an old typed command form from §4.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2.2 (who registers what), §4, §5, §6, D2, D3, D10, task R1, M1's "As built" notes, and
   "Close-out — every task".
3. `.claude-plugin/marketplace.json`, through a script that prints each skill folder with the plugins
   that register it.

Build:
- A one-off rewrite script in the session scratchpad (never committed) that parses §5's tables out of
  the plan, expands `<stack>` rows by their Stacks column, maps each folder to its `<plugin>:` form per
  §6 step 2, and applies §6 steps 1–4 to §6's scope. Run `--dry-run` first, read the per-name counts,
  then apply.
- §6 step 5: hand-edit every family wildcard (`ep-*`, `qa-ci-pipelines-*`, `secgov-*`,
  `qa-test-reports-*`, `pentest-*`, `ba-*`, `be-shared-*`, `auth-auth0-*`), reading each sentence.
- §6 step 6: fix counts in skill and agent prose that the new layout falsifies (for example "ships in
  all sixteen plugins").
- Spot-check diffs: `backend/java/agents/be-java.md`, one `qa/java/skills/*/SKILL.md`, one
  `design/*/SKILL.md`, one command file, `marketplace.json`, `docs/skills-catalog.md`.

Traps:
- Several folders equal their old name (`design/design-tokens`, `business-analysis/skills/ba-*`,
  `training-data/*/td-*`). §6's lookbehind `(?<![\w/.-])` and lookahead `(?![\w-]|/)` are what keep
  those paths intact. A dry-run hit inside a path means the regex is wrong.
- `design-ui-ux-pro-max` is renamed. The product name `ui-ux-pro-max` and the vendored corpus's own
  files are not.
- Agent identifiers without a leading slash (`code-auditor`, `solution-planner`, `qa-security`) are
  not skill names. Leave them.
- Never touch `docs/plans/implemented/`, `docs/audits/`, `docs/research/` or this plan file (D10).

**Gate: none** — this plan gates once, in D1. Do not run `claude plugin validate`, the checker or the
token audit.

Commit: `refactor(skills): topic-only skill names, references rewritten to plugin:name (004 R1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### D1 — documentation, the gate, and close-out (general-purpose, docs)

````
You are `general-purpose`. Task D1 of docs/plans/004-plugin-surface-rework.md: document the new plugin
surface, then run the plan's only gate and fix whatever it finds.

Deliverable: §9's gate passes end to end; README, `docs/skills-catalog.md`, CLAUDE.md, CONTRIBUTING
and `.skill-template/*` describe the §2 layout, §3 rules and §4 names.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §3, §4, §7, §9, the Decisions, task D1, the "As built" notes of M1 and R1, and
   "Close-out — every task".
3. `README.md` — the install section and §"Slash commands".
4. `docs/skills-catalog.md` — only "Scope & published plugins" and "Slash-command surface".
5. `CONTRIBUTING.md` and `.skill-template/*.SKILL.md`.

Build: task D1's bullets — README per §7, the catalog's two sections, CLAUDE.md's count and
Repository-map rows, CONTRIBUTING's "Names and registration" section, and the template note.

Gate (this is the last runnable task, so it carries the plan's only gate, in run order):
  python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
  claude plugin validate .                 # must end "✔ Validation passed"
  claude plugin validate . --strict        # record the result; fix only dependency problems
  python3 tools/plugin-surface-check.py    # must print OK
  python3 tools/token-audit.py --violations-only   # 0 description violations, ≤ 90 body violations
  python3 tools/token-audit.py             # record dev+design+be-java+fe-react+qa-typescript+data+business-analysis desc(tok) vs 25,281
  python3 tools/qa-version-check.py        # must print OK
  the §9.6 old-name sweep                  # zero matches in §6's scope
Fix what it finds, because a failure may belong to M1 or R1. Use the checker's and the sweep's output
as the fix list.

Traps:
- `tools/token-audit.py --violations-only` exits 1 on the 90 pre-existing body violations. That is
  the baseline, not a failure. The number must not rise.
- The validator's advice about missing README install lines is cleared by §7's one-line-per-plugin
  install list. Check its output after writing README.
- After the gate, write H1's prompt-block checklist from what actually landed (plugin names, typed
  forms, the measured token figure). Then **do not** move the plan: H1 still holds a block.

Commit: `docs(plugins): dependency layout, naming rules and command tables; gate passed (004 D1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### H1 — verify the installed result (the user)

**Blocked on D1** — D1 writes this checklist when it lands, from the plugin names, typed forms and
token figure that actually shipped. It covers: commits on `origin/master`; `/plugin marketplace update
skills-library`; switching the skills-library plugins to `false` in `~/.claude/settings.json` and
enabling a project's set in its `.claude/settings.json` (§7); confirming `dev` / `design` installed as
dependencies (installing them explicitly if Q1's answer is "only on install", and recording that
answer); `/dev:` and `/design:` listing what §4 says; `claude plugin details be-java` for the
always-on figure; one short `/dev:audit` run to prove an agent still loads its skills by path. Then
the user deletes this block, rewrites `Status`, and moves the plan to `docs/plans/implemented/`.
