---
name: qa-ci-pipelines-java
description: Use when wiring a test suite into CI — shard matrix, JUnit + Allure publishing, performance gates, OIDC secrets — on GitHub Actions, Azure Pipelines, or GitLab CI. Triggers: "add a CI pipeline for the tests", "shard the suite in CI", "publish Allure from the pipeline". The repo's CI host picks the tool; read its reference file.
---

# QA — CI Pipelines (Java 21)

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

## Shared rules (every tool in this family)

- The pipeline runs the same commands developers run locally — no CI-only magic.
- Shard with fail-fast off; always publish JUnit XML + Allure results, including on failure.
- Secrets via OIDC / the platform's secret store — never in YAML.
- Cross-stack conventions live in `qa/_shared/ci-conventions` — load it alongside the tool reference.

## Cross-references

Each `references/<tool>.md` carries its own cross-references to sibling skills (DB verification,
test environments, CI, chaos). Route there after picking the tool.
