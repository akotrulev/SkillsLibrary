---
name: qa-ci-conventions-shared
description: Cross-stack, cross-CI reference for QA pipelines — the rules every `qa/<stack>/skills/ci-pipelines/{azure-pipelines,github-actions,gitlab-ci}` skill enforces regardless of platform or language. Covers pipeline shape (PR lane vs nightly), shard defaults, OIDC-only secrets, dual reporters (native + Allure), the no-retry policy, artifact retention, the perf-gate contract, and runner/container rules. Load alongside a per-CI sibling when generating or reviewing pipeline YAML. Do NOT load standalone to write pipeline YAML — the per-CI sibling carries the platform syntax, templates, and generation steps. Do NOT use for non-QA pipelines (deploy, infra — see `devops/`).
---

# QA — CI Conventions (Shared)

Cross-stack rules shared by all nine `qa/<stack>/skills/ci-pipelines/<ci>` skills. The per-CI siblings carry platform YAML, templates, and generation steps; this skill carries the conventions that must hold identically on Azure Pipelines, GitHub Actions, and GitLab CI, in Java, .NET, and TypeScript. When a per-CI skill and this file disagree, the per-CI skill is wrong — fix it.

## Platform primitive map

The same convention, three spellings. Use this table to translate, not to choose — the project's existing CI decides the platform.

| Convention | Azure Pipelines | GitHub Actions | GitLab CI |
|---|---|---|---|
| Shard fan-out | `strategy: parallel: N` | `strategy.matrix` (+ `fail-fast: false`) | `parallel: N` (+ `CI_NODE_INDEX`/`CI_NODE_TOTAL`) |
| Native test report | `PublishTestResults@2` (TRX) | `dorny/test-reporter` (TRX) | `artifacts:reports:junit` (JUnit XML) |
| Cancel superseded PR runs | branch policy / build queue | `concurrency` + `cancel-in-progress: true` | `interruptible: true` + auto-cancel redundant |
| OIDC mechanism | Workload Identity Federation service connection | `permissions: id-token: write` + `azure/login` / `configure-aws-credentials` | `id_tokens:` with cloud `aud:` |
| Allure history home | Blob storage | `gh-pages` branch | dedicated cache (stable key) |
| Gate expensive stages | `condition:` on `Build.Reason == 'Schedule'` | `if: github.event_name == 'schedule'` | `rules:` matching `$CI_PIPELINE_SOURCE == "schedule"` |

## Pipeline shape

- **Two lanes.** PR lane: build + unit + API + UI smoke, **under 15 minutes**. Nightly scheduled lane: the full suite — all shards, integration, perf, visual regression.
- Perf and visual-regression stages are **gated to the schedule** (or an explicit label/dispatch), never on every PR.
- Triggers are explicit in YAML — the YAML is the source of truth, not implicit branch defaults.
- Cancel superseded PR runs; never cancel a running nightly.

## Sharding

- Defaults: **4 shards UI, 2 API, 1 integration** (Testcontainers cost dominates integration — sharding it multiplies container spin-up, not throughput). Tune from the slowest job over the previous 10 runs.
- Shard membership is computed **once, upstream** (platform fan-out primitive, committed shard map, or a setup job emitting the matrix) — never re-discovered per shard at runtime.
- One shard failing must **not** cancel the others — you lose their reports.

## Secrets

- **OIDC only.** No PATs, no long-lived cloud keys, no static service-principal secrets stored in CI variables.
- Identifiers (`client-id`, `tenant-id`, `subscription-id`, role ARNs) are **not** secrets — store them as plain variables; storing them as secrets hides them from diagnostics for no security gain.
- The unavoidable exception (third-party SaaS key with no OIDC story) → masked + protected variable, scoped to protected branches.
- Never `echo` a fetched secret (even with `|| true`); never write one to a path an artifact step collects; mask runtime-fetched values before exporting them to the job environment.

## Reporters

- Always emit **both**: the platform-native format (TRX / JUnit XML — feeds the PR/MR test widget) **and** Allure results (feeds humans, carries history and trends).
- The pipeline must go red on real failures even when a runner exit code is masked — turn on the report task's fail-on-failed-tests option; never `continue-on-error` / `allow_failure` on a test step.
- Allure **history must persist across runs** (see primitive map for where) — a trendless Allure report is just a prettier TRX.
- Container logs (Testcontainers) attach to Allure via the test runner, not as separate pipeline artifacts.

## Retry policy

- **No pipeline-level retry of failed tests.** Retry hides bugs.
- Per-test retry (`[Retry(2)]` / TestNG `retryAnalyzer` / Playwright `retries`) only for **documented** network-flake hotspots — each one annotated with a date and an issue link at the test.
- Chronic flakes are quarantined via `qa/<stack>/skills/flaky-test-quarantine`, not auto-retried.
- Platform retry features are for **infrastructure** failures only (e.g. GitLab `retry: when: runner_system_failure`) — never assertions.

## Artifact retention

| Artifact | Retention | Condition |
|---|---|---|
| Test results (TRX/JUnit) + coverage | 30 days | always |
| Playwright traces / videos / HAR | 14 days | **on failure only** |
| Allure published report | 90 days | always |
| Allure history | indefinitely | always (Blob / `gh-pages` / cache) |
| Perf tool reports (k6 / NBomber / Gatling) | 30 days | always |

## Perf gate

- Thresholds live **inline in the perf script** (`thresholds:` / `.WithThresholds` / Gatling assertions). The pipeline never interprets metrics — it only honors the runner's exit code (k6 exits 99 on breach).
- No YAML guards softening the exit code. A breached threshold is a red build.
- Pin the perf-tool version; upgrade it in a dedicated PR/MR, never as a drive-by.
- SLO/threshold semantics live in `qa/_shared/performance` — this file only owns the wiring contract.

## Runners & containers

- **Linux runners** for any Testcontainers work — Docker on Windows runners defaults to Windows containers and Linux modules fail.
- Pin tool and image versions (`k6 v0.52.0`, `allure-commandline@2.30.0`, `postgres:17.2`) — never floating tags in CI.
- Never mix runner-level test parallelism with a fixture that owns a container (NUnit `[Parallelizable]` + `LevelOfParallelism > 1`, TestNG parallel suites) — instant flake.
- No `--blame`-style diagnostics in production runs (slow); enable only for a targeted hang re-run.

## What NOT to do (all platforms, all stacks)

- No green-washing: `continueOnError` / `continue-on-error` / `allow_failure` on a test step.
- No PATs or long-lived keys where OIDC exists.
- No printing or artifact-collecting a secret, ever.
- No re-discovering tests per shard at runtime.
- No unpinned tool/image versions.
- No pipeline-level retry of assertions.
- No perf metrics interpreted in YAML — exit codes only.

## Handoffs

- Platform YAML, templates, generation steps → `qa/<stack>/skills/ci-pipelines/{azure-pipelines,github-actions,gitlab-ci}` for the project's stack and CI
- Flake quarantine policy the retry rules defer to → `qa/<stack>/skills/flaky-test-quarantine`
- Allure adapter wiring inside the test project → `qa/<stack>/skills/allure-reporting`
- Workload models and threshold semantics behind the perf gate → `qa/_shared/performance`
- Container lifecycle the integration stage runs → `qa/<stack>/skills/db-testing/testcontainers`, `qa/<stack>/skills/test-environments`
- Non-QA pipelines (deploy, infra) → `devops/`
