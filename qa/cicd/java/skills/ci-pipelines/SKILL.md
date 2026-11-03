---
name: ci-pipelines
description: Use when wiring a test suite into CI on GitHub Actions, Azure Pipelines or GitLab; shards, Allure publishing, OIDC. Triggers "add a CI pipeline for the tests". Not for cross-CI rules (ci-conventions).
---

# QA — CI Pipelines (Java 21)

One registered skill, 3 tools — a project uses exactly one. Identify the project's tool
(dependencies, docker-compose, infra config; ask one question if ambiguous), then **read the matching
`references/<tool>.md` end-to-end before writing any code** — it carries the full model, patterns,
templates, anti-patterns, and hard rules for that tool. This file only routes and points to the rule
file shared by every tool in the family.

## Tools in this family

| Read | Use when |
|------|----------|
| `references/github-actions.md` | Repo lives on GitHub — workflows, `strategy.matrix` sharding, OIDC to cloud |
| `references/azure-pipelines.md` | Azure DevOps (house default per global rules) — YAML pipelines, environments, service connections |
| `references/gitlab-ci.md` | Repo lives on GitLab — `.gitlab-ci.yml`, parallel matrix, GitLab Pages for reports |

## Rules

The standards every tool shares are the qa-java rule file `qa-java-ci.md`, not a list here. Read the project's copy in `.claude/rules/qa-java/`, or the plugin's in `qa/java/skills/rules/` when the project has not installed them (`/qa-java:rules` does). Where it and a tool reference disagree, the rule file wins for anything both cover; each reference adds the rules specific to its tool. Cross-stack conventions live in `qa/cicd/ci-conventions`: load it alongside the tool reference.

## Cross-references

Each `references/<tool>.md` carries its own cross-references to sibling skills (DB verification,
test environments, CI, chaos). Route there after picking the tool.
