---
name: qa-ci-pipelines-dotnet
description: Use when wiring a test suite into CI — shard matrix, JUnit + Allure publishing, performance gates, OIDC secrets — on GitHub Actions, Azure Pipelines, or GitLab CI. Triggers: "add a CI pipeline for the tests", "shard the suite in CI", "publish Allure from the pipeline". The repo's CI host picks the tool; read its reference file. Not for the cross-CI rules (`qa-ci-conventions-shared`), Allure adapter wiring or quarantine (the qa-reporting agents), or deploy pipelines (the devops plugin).
---

# QA — CI Pipelines (.NET 10 / C#)

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
- Cross-stack conventions live in `qa/cicd/ci-conventions` — load it alongside the tool reference.
- Inside a `Gate: none` plan task, run none of the generation steps' lint, dry-run or smoke checks, and report the pipeline as "written, not run".

## Sharding NUnit suites: class filters computed once

**Neither `Microsoft.Playwright.NUnit` nor NUnit shards a run.** `-- Playwright.Shard=i/N` is ignored (the
adapter prints "Playwright>Shard is not implemented") and every shard would run the whole suite. So every
reference shards the same way, per `qa/cicd/ci-conventions` ("membership is computed once, upstream"):

1. A **plan job** builds the test project, lists its tests once, splits the **test classes** into N groups
   and publishes one filter file per shard as an artifact (`<dir>/<i>.filter`, 1-based).
2. Each **shard job** reads `<dir>/<index>.filter` and runs `dotnet test --filter "(<filter>)"` — for UI,
   `--filter "(<filter>)&TestCategory!=Flaky&TestCategory!=visual&TestCategory!=lighthouse&TestCategory!=grid"` — the nightly-only visual and Lighthouse categories and the cloud-grid fixtures stay out of the PR gate (`qa/reporting/dotnet/skills/flaky-test-quarantine` for `Flaky`).

`ci/nunit-shards.sh <project> <shards> <dir>`, committed in the repo and run with `bash`:

```bash
#!/usr/bin/env bash
set -euo pipefail

project="$1"
shards="$2"
dir="$3"

mkdir -p "$dir"
dotnet test "$project" --list-tests -- NUnit.DisplayName=FullName \
  | sed -n '/The following Tests are available:/,$p' | sed '1d' \
  | awk '/^[ \t]+[^ \t]/ { sub(/^[ \t]+/, ""); sub(/\([^()]*\)$/, ""); sub(/\.[^.(]+$/, ""); print (sub(/\(.*$/, "") ? $0 "\\(" : $0 ".") }' \
  | LC_ALL=C sort -u \
  | awk -v n="$shards" -v dir="$dir" '
      { i = (NR - 1) % n + 1; filter[i] = filter[i] (filter[i] == "" ? "" : "|") "FullyQualifiedName~" $0 }
      END {
        if (NR < n) { printf "%d test classes for %d shards: lower the shard count\n", NR, n > "/dev/stderr"; exit 1 }
        for (i = 1; i <= n; i++) print filter[i] > (dir "/" i ".filter")
      }'
```

- **`NUnit.DisplayName=FullName`** makes `--list-tests` print `Namespace.Class.Method(args)` instead of the
  bare method name. The first `awk` drops the method and its arguments and keeps the class.
- **One term per class, never per test.** A filter of every test name breaks the command-line length limit
  on some runners (8,191 characters through `cmd.exe`) and needs escaping for every argument list. A class
  term is `FullyQualifiedName~Namespace.Class.` — the trailing `.` keeps `LoginTests` from also matching
  `LoginTestsMobile`. A parameterized fixture (`[TestFixture("de-DE", …)]`) puts its arguments in the full
  name, so its term is `FullyQualifiedName~Namespace.Class\(` (an escaped `(`). If one shard's file still
  grows past a few thousand characters, shard by namespace instead.
- **Classes are dealt round-robin in name order** (`LC_ALL=C`), so the same classes always give the same
  shards. Balance is by class count, not duration. Only lines indented under the "available" header are read.
- **Fewer classes than shards fails the plan job**, naming both numbers — lower the shard count rather than
  run an empty shard.
- `BaseTest` carries `[Parallelizable(ParallelScope.Self)]` and `AuthSetup` signs in once per run, so a
  class never splits across shards and each shard signs in once.
- This is the VSTest runner `UiTests.csproj` uses (`Microsoft.NET.Test.Sdk` + `NUnit3TestAdapter`). A project
  switched to Microsoft.Testing.Platform lists and filters tests differently.
- `BaseTest`'s failure evidence lands in `UiTests/bin/<cfg>/net10.0/playwright-artifacts/`; every UI shard
  uploads that folder on failure (14 days) and `UiTests/bin/<cfg>/net10.0/allure-results/` on every run. What
  the files are and how to read them is `qa/dotnet/skills/evidence-capture`.

## Cross-references

Each `references/<tool>.md` carries its own cross-references to sibling skills (DB verification,
test environments, CI, chaos). Route there after picking the tool.
