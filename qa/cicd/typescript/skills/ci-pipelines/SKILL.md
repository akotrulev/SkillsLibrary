---
name: ci-pipelines
description: Use when wiring a test suite into CI on GitHub Actions, Azure Pipelines or GitLab; shards, Allure publishing, OIDC. Triggers "add a CI pipeline for the tests". Not for cross-CI rules (ci-conventions).
---

# QA — CI Pipelines (TypeScript)

One registered skill, 3 tools — a project uses exactly one. Identify the project's tool
(dependencies, docker-compose, infra config; ask one question if ambiguous), then **read the matching
`references/<tool>.md` end-to-end before writing any code** — it carries the full model, patterns,
templates, anti-patterns, and hard rules for that tool. This file only routes and holds the rules
shared by every tool in the family.

## Tools in this family

| Read | Use when |
|------|----------|
| `references/github-actions.md` | Repo lives on GitHub — workflows, `strategy.matrix` sharding, OIDC to cloud |
| `references/azure-pipelines.md` | Azure DevOps (house default per global rules) — YAML pipelines, environments, service connections |
| `references/gitlab-ci.md` | Repo lives on GitLab — `.gitlab-ci.yml`, parallel matrix, GitLab Pages for reports |

## Rules

The standards this skill's output must meet are the qa-typescript rule files, not a list here: `ci-tests.md`. Read the project's copy in `.claude/rules/qa-typescript/`, or the plugin's in `qa/typescript/skills/rules/` when the project has not installed them (`/qa-typescript:rules` does). Where they and this skill's recipes disagree, the rule files win.

Cross-stack conventions live in `qa/cicd/ci-conventions`: load it alongside the tool reference.

## Cross-references

Each `references/<tool>.md` carries its own cross-references to sibling skills (DB verification,
test environments, CI, chaos). Route there after picking the tool.
