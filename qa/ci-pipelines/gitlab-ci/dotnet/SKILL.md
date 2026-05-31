---
name: qa-ci-pipelines-gitlab-ci-dotnet
description: Use when the user asks to author or fix a GitLab CI/CD pipeline (`.gitlab-ci.yml`) for running .NET 8 QA suites — sharded NUnit / Playwright runs via `parallel:` reading `CI_NODE_INDEX`/`CI_NODE_TOTAL` into an NUnit `--filter` slice, Testcontainers integration tests (`docker:dind`), Allure publish to GitLab Pages with history carried in cache, NUnit→JUnit (`--logger junit`) into `artifacts:reports:junit`, secretless cloud auth via `id_tokens:` + cloud OIDC (no long-lived secrets), NuGet `cache:key:files:` on the lockfile, perf gate against k6 thresholds. Triggers: "gitlab-ci.yml for the API tests", "shard our NUnit tests with parallel:", "add Allure to the GitLab pipeline", "wire id_tokens OIDC to AWS for the .NET test pipeline", "publish the test report to GitLab Pages", "fail the build when k6 thresholds break". Do NOT use for GitHub Actions (`qa/ci-pipelines/github-actions/dotnet`), Azure Pipelines (`qa/ci-pipelines/azure-pipelines/dotnet`), deployment-only pipelines (`devops/gitlab-ci`), or non-QA app builds. For Java / TypeScript test suites use the `java` or `typescript` sibling under this skill.
---

# QA — GitLab CI/CD for .NET Test Suites

Authors `.gitlab-ci.yml` that runs NUnit / Playwright / Testcontainers-backed integration tests on GitLab runners using .NET 8, shards for speed via `parallel:`, publishes Allure to GitLab Pages with history, fails on real failures (not flakes), and pulls secrets via `id_tokens:` cloud OIDC rather than long-lived CI/CD variables.

This is a **true port** of `qa/ci-pipelines/github-actions/dotnet` — the *same* pipeline (same stages, same shard strategy, same artifacts, same gates), re-keyed to GitLab's `.gitlab-ci.yml` vocabulary, and the .NET sibling of the canonical `qa/ci-pipelines/gitlab-ci/typescript`. **Translate, don't redesign.** Only the YAML schema and a few primitives differ:

| Capability | GitHub Actions (#11) | GitLab CI (this skill) |
|---|---|---|
| Shard fan-out | `strategy.matrix` (array == `shard-total`) | `parallel: N` → `CI_NODE_INDEX`/`CI_NODE_TOTAL` |
| DAG / ordering | `needs:` between jobs | `needs:` (DAG) + `dependencies:` (artifact scope) |
| Cache | `actions/setup-dotnet` + `actions/cache` | `cache:key:files:[packages.lock.json]` + `policy:` |
| JUnit summary | `dorny/test-reporter` (TRX) | native `artifacts:reports:junit:` (`--logger junit`) |
| Cloud auth | `permissions: id-token: write` + `azure/login` | `id_tokens:` + `aud:` → assume role |
| Cancel superseded | `concurrency: cancel-in-progress` | `interruptible: true` + project auto-cancel |
| Gating | `if: github.event_name == 'schedule'` | `rules: - if: $CI_PIPELINE_SOURCE == "schedule"` |

The canonical TS sibling uses Playwright's native `blob` → `merge-reports` flow; .NET has no blob reporter, so — exactly as in #11 — each NUnit shard emits its own JUnit XML and Allure results, and the `pages` job merges the Allure results into one report. k6 stays the perf tool (matching the #11 dotnet sibling's exit-99 gate).

## When to use

- New QA pipeline for a .NET test project (`ApiTests`, `IntegrationTests`, `UiTests`, perf)
- Adding `parallel:` sharding to an existing serial pipeline
- Wiring Allure publish + history to GitLab Pages (or an artifact)
- Replacing long-lived cloud CI/CD variables with `id_tokens:` OIDC
- Adding a perf gate (k6 / NBomber) that breaks the pipeline on SLO regression

## When NOT to use

- GitHub Actions equivalent → `qa/ci-pipelines/github-actions/dotnet`
- Azure Pipelines equivalent → `qa/ci-pipelines/azure-pipelines/dotnet`
- App build / deploy pipelines unrelated to tests → `devops/gitlab-ci`
- Non-.NET stacks — use the `java` or `typescript` sibling under this skill

## Inputs needed

Ask at most 3 questions.

1. Which test projects? (`ApiTests`, `IntegrationTests`, `UiTests`, multiple)
2. Sharding fan-out? (default: `parallel: 4` for UI, `parallel: 2` for API/integration, 1 for perf)
3. Allure history destination? (default: GitLab Pages with history in cache; artifact-only when Pages is disabled)

Infer everything else from `.csproj` files, `packages.lock.json` if present, and any existing `.gitlab-ci.yml`.

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Runner | `image: mcr.microsoft.com/dotnet/sdk:8.0` on a `docker` runner | Self-hosted/shell runner only for proprietary hardware (mobile farm, GPU) |
| .NET | 8.0 LTS via the SDK image | Newer LTS only after 3 mo GA |
| NuGet cache | `cache:key:files:[packages.lock.json]` (enable lock file) + `policy:` + `--locked-mode` restore | Hash `**/*.csproj` when no lock file exists |
| Triggers | `merge_request_event` + nightly `schedule` (set via `workflow:rules`) | `push` on the default branch only when the suite is < 5 min |
| Test reporter | `--logger "junit;LogFilePath=..."` → `artifacts:reports:junit` + Allure NUnit adapter | Always both — JUnit feeds the MR widget, Allure feeds humans |
| Sharding | `parallel: N`; runner reads `CI_NODE_INDEX`/`CI_NODE_TOTAL` into an NUnit `--filter` slice | Playwright `Playwright.Shard=$CI_NODE_INDEX/$CI_NODE_TOTAL`; category split via `NUnit.Where` |
| Auth to AWS / Azure / Vault | `id_tokens:` + `aud:` → assume role (OIDC) | Never long-lived cloud keys; masked+protected CI/CD variables only for unavoidable tokens |
| Retry on failure | **Off at the pipeline level** (no `retry:` on the test job) | Per-test `[Retry(2)]` only for documented flake hotspots — never blanket `retry:` |
| Cancel superseded | `interruptible: true` + project "auto-cancel redundant pipelines" | Keep nightly un-interruptible |
| Artifact retention | `expire_in: 14 days` for traces/videos/HAR, `30 days` for JUnit; Allure history in cache | Bump only with a stated reason |
| Perf gate | k6 thresholds → exit code 99 → job fails | Soft gate (`allow_failure: true`) only while a baseline is being established |

## Templates

### Top-level pipeline — `.gitlab-ci.yml`

```yaml
# Same pipeline as the github-actions sibling — GitLab vocabulary.
stages: [install, test, merge, perf, publish]

default:
  image: mcr.microsoft.com/dotnet/sdk:8.0
  tags: [docker]              # a runner with the Docker executor
  interruptible: true         # GitLab analogue of cancel-in-progress for superseded MR pipelines

workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_PIPELINE_SOURCE == "schedule"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

variables:
  BUILD_CONFIGURATION: Release
  DOTNET_NOLOGO: "true"
  DOTNET_CLI_TELEMETRY_OPTOUT: "true"
  NUGET_PACKAGES: "$CI_PROJECT_DIR/.nuget/packages"   # cacheable NuGet store in the workspace

# Reusable NuGet cache anchor — keyed on the lock file so a dependency change busts it.
.nuget-cache: &nuget-cache
  cache:
    key:
      files: [packages.lock.json]
    paths: [.nuget/packages/]
    policy: pull               # test jobs read; the install job writes (below)
```

The five stages map 1:1 onto the github-actions reusable workflows: `install` primes the NuGet cache, `test` fans out the sharded suites, `merge` is unused for .NET (kept for family symmetry; the Allure merge happens in `publish`), `perf` runs the gated k6 job, `publish` builds Allure on GitLab Pages. Enable the NuGet lock file (`<RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>` in `Directory.Build.props`) so `cache:key:files:` has a deterministic key; without it, hash `**/*.csproj`.

### Prime the NuGet cache — `install` stage

```yaml
install:
  stage: install
  cache:
    key:
      files: [packages.lock.json]
    paths: [.nuget/packages/]
    policy: pull-push           # THIS job populates the cache; downstream jobs pull
  script:
    - dotnet restore --locked-mode   # frozen, reproducible restore — fails if the lock file is stale
```

One job owns `policy: pull-push`; every test job uses `<<: *nuget-cache` (`policy: pull`) so they never race to write the same key. `--locked-mode` is the .NET analogue of `npm ci` — it refuses to restore if `packages.lock.json` doesn't match the project references.

### Sharded NUnit job — `test` stage

```yaml
api-tests:
  stage: test
  <<: *nuget-cache
  parallel: 2                   # GitLab sets CI_NODE_INDEX (1-based) and CI_NODE_TOTAL
  # OIDC token for the cloud — no stored secret. `aud` must match the role's trust policy.
  id_tokens:
    AWS_ID_TOKEN:
      aud: https://gitlab.example.com
  script:
    - export AWS_WEB_IDENTITY_TOKEN_FILE="$(mktemp)"
    - echo "$AWS_ID_TOKEN" > "$AWS_WEB_IDENTITY_TOKEN_FILE"
    - export AWS_ROLE_ARN="arn:aws:iam::111122223333:role/qa-ci"
    - export API_BASE_URL="$(aws ssm get-parameter --name /qa/api-base-url --with-decryption --query Parameter.Value --output text)"
    # NUnit slices the suite across CI_NODE_TOTAL runners via a modulo filter predicate.
    - >
      dotnet test ApiTests/ApiTests.csproj
      --configuration "$BUILD_CONFIGURATION"
      --logger "junit;LogFilePath=$CI_PROJECT_DIR/reports/junit-api-$CI_NODE_INDEX.xml"
      --logger "console;verbosity=minimal"
      --
      NUnit.NumberOfTestWorkers=1
      NUnit.Where="cat != Slow and cat != Perf and (test % $CI_NODE_TOTAL == $CI_NODE_INDEX - 1)"
  artifacts:
    when: always                # collect reports even when tests fail
    expire_in: 30 days
    paths: [ApiTests/bin/$BUILD_CONFIGURATION/net8.0/allure-results/]
    reports:
      junit: reports/junit-api-*.xml   # native MR test widget — no third-party action
```

`parallel: N` injects `CI_NODE_INDEX` (1-based) / `CI_NODE_TOTAL`, which feed an NUnit `--where` modulo predicate — the GitLab analogue of the github-actions `NUnit.Where="test % N == i"` matrix slice, minus the array you'd otherwise keep in sync with the count. `NUnit.Where="test % N == i"` is a stand-in — replace with your real shard predicate (category split, fixture-name hash, or a committed bin map). The `junit` logger comes from the `JunitXml.TestLogger` (a.k.a. `JUnitTestLogger`) NuGet package; add it to each test project so `--logger junit` resolves.

> GitLab's native test widget parses the `artifacts:reports:junit` XML directly — it is the GitLab equivalent of `dorny/test-reporter` reading TRX. `dotnet test` already exits non-zero on failure, which reds the pipeline; the widget just surfaces *which* tests failed. Do not add `allow_failure: true`.

### Integration tests with Testcontainers — `test` stage

Unlike GitHub-hosted runners (Docker pre-installed, socket mounted), a GitLab Docker-executor job has **no Docker daemon by default**. Add the `docker:dind` service and point Testcontainers at it. This is the one genuinely GitLab-specific wrinkle in the port.

```yaml
integration-tests:
  stage: test
  <<: *nuget-cache
  services:
    - name: docker:27-dind
      alias: docker
  variables:
    DOCKER_HOST: "tcp://docker:2376"
    DOCKER_TLS_CERTDIR: "/certs"
    DOCKER_TLS_VERIFY: "1"
    DOCKER_CERT_PATH: "/certs/client"
    # Testcontainers must reach published ports at the dind host, not localhost.
    TESTCONTAINERS_HOST_OVERRIDE: "docker"
    TESTCONTAINERS_RYUK_DISABLED: "false"
  script:
    - docker info                       # fail fast if dind didn't come up
    - >
      dotnet test IntegrationTests/IntegrationTests.csproj
      --configuration "$BUILD_CONFIGURATION"
      --logger "junit;LogFilePath=$CI_PROJECT_DIR/reports/junit-integration.xml"
  artifacts:
    when: always
    expire_in: 30 days
    reports:
      junit: reports/junit-integration.xml
```

`TESTCONTAINERS_HOST_OVERRIDE: docker` is the critical line: with dind, containers' mapped ports are reachable at the `docker` service alias, not `localhost`. Keep Ryuk **enabled** — it reaps leaked containers between jobs on a warm runner. (On a runner configured with a mounted host Docker socket instead of dind, drop the `services:`/`DOCKER_*` block.)

### Playwright UI shard — `test` stage

```yaml
ui-tests:
  stage: test
  <<: *nuget-cache
  image: mcr.microsoft.com/playwright/dotnet:v1.47.0-jammy   # browsers + deps preinstalled
  parallel: 4
  script:
    - dotnet build UiTests/UiTests.csproj -c "$BUILD_CONFIGURATION"
    # The Playwright image ships browsers; otherwise: pwsh UiTests/bin/.../playwright.ps1 install --with-deps chromium
    - >
      dotnet test UiTests/UiTests.csproj --no-build -c "$BUILD_CONFIGURATION"
      --logger "junit;LogFilePath=$CI_PROJECT_DIR/reports/junit-ui-$CI_NODE_INDEX.xml"
      --
      Playwright.Shard=$CI_NODE_INDEX/$CI_NODE_TOTAL
  artifacts:
    # One artifacts block per job, one expire_in — traces ride with the results here.
    # Configure Playwright-for-.NET to keep traces on failure only so the 14-day bucket
    # stays small; a separate `needs:`-download job would collect nothing new.
    when: always
    expire_in: 14 days
    paths:
      - UiTests/bin/$BUILD_CONFIGURATION/net8.0/allure-results/
      - UiTests/bin/$BUILD_CONFIGURATION/net8.0/playwright-traces/
    reports:
      junit: reports/junit-ui-*.xml
```

Using the `mcr.microsoft.com/playwright/dotnet` image avoids the `playwright.ps1 install --with-deps` step (browsers + OS libs are baked in). If you stay on the SDK image, run the install script with `--with-deps` so system libs are present.

### Allure publish with history — `publish` stage (GitLab Pages)

GitLab has no `gh-pages` branch. The native deliverable is **GitLab Pages**: a job literally named `pages` that publishes a `public/` directory. Allure trend history (the `history/` folder) is carried across pipelines in a **dedicated cache with a stable key** — the GitLab analogue of `keep_files: true` on `gh-pages`. The `pages` job collects the per-shard `allure-results/` artifacts and generates one report (the .NET analogue of #11's gh-pages publish, since there is no Playwright blob to merge).

```yaml
pages:
  stage: publish
  image: node:20-bookworm              # allure-commandline needs Node + a JRE
  needs:
    - job: api-tests
      artifacts: true
    - job: ui-tests
      artifacts: true
  when: always                         # publish even when a test job failed
  cache:
    key: allure-history                # stable key — NOT the lock file — so history persists
    paths: [allure-history/]
    policy: pull-push
  before_script:
    - apt-get update && apt-get install -y default-jre-headless
  script:
    - npm i -g allure-commandline@2.30.0
    # Gather every shard's results.
    - mkdir -p allure-results && find . -type d -name allure-results -not -path './allure-results' -exec cp -r {}/. allure-results/ \;
    # Re-seed history from the prior run before generating.
    - mkdir -p allure-results/history && cp -r allure-history/* allure-results/history/ 2>/dev/null || true
    - allure generate allure-results --clean -o public
    - rm -rf allure-history && cp -r public/history allure-history
  artifacts:
    paths: [public/]
    expire_in: 30 days
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

When GitLab Pages is disabled, drop the `pages` name and the Pages `rules`, keep the same script, and publish `public/` as a plain artifact with `expire_in: 90 days`.

### k6 perf gate — `perf` stage

k6 returns exit code 99 when thresholds break; the job inherits that exit code and fails — no extra glue, matching the sibling's contract from `qa/performance/_shared` (tests **fail the build** when SLOs aren't met). This matches the #11 dotnet sibling's k6 exit-99 gate; swap to NBomber only if the org standardized on it (then assert its own SLO threshold and exit non-zero on breach). Gate it to the nightly schedule so MRs stay fast.

```yaml
k6-perf:
  stage: perf
  image: grafana/k6:0.52.0             # pinned; upgrade in a dedicated MR
  needs: ["api-tests"]
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
  id_tokens:
    AWS_ID_TOKEN:
      aud: https://gitlab.example.com
  script:
    - export AWS_WEB_IDENTITY_TOKEN_FILE="$(mktemp)"; echo "$AWS_ID_TOKEN" > "$AWS_WEB_IDENTITY_TOKEN_FILE"
    - export AWS_ROLE_ARN="arn:aws:iam::111122223333:role/qa-ci"
    - export K6_BASE_URL="$(aws ssm get-parameter --name /qa/api-base-url --query Parameter.Value --output text)"
    - k6 run --out json=k6-summary.json perf/scenarios/checkout.js
  artifacts:
    when: always
    expire_in: 30 days
    paths: [k6-summary.json]
```

## Rules

### Triggers
- `workflow:rules` allowing `merge_request_event` + default branch + `schedule`. Create the nightly run in **CI/CD → Schedules** (it runs on the default branch).
- MR pipelines stay under 15 min by gating perf to `schedule`.
- Avoid duplicate pipelines by not also matching `push` for branches with an open MR.

### Cancel superseded
- `interruptible: true` + project **"Auto-cancel redundant pipelines"** — the GitLab analogue of `concurrency: cancel-in-progress`. Leave nightly un-interruptible.

### NuGet / restore
- Enable the **NuGet lock file** so `cache:key:files:[packages.lock.json]` is deterministic; without it, hash `**/*.csproj`.
- **One `install` job with `policy: pull-push`** populates the cache; every other job uses `<<: *nuget-cache` (`policy: pull`). Two jobs writing the same key race.
- Restore with **`--locked-mode`** (frozen, reproducible). Never an unpinned restore in CI.

### Sharding
- Default: `parallel: 4` for UI, `parallel: 2` for API, 1 for integration (Testcontainers cost dominates). Tune from the slowest job on the previous 10 runs.
- The runner reads **`CI_NODE_INDEX`** (1-based) / **`CI_NODE_TOTAL`** — GitLab injects both from `parallel: N`. Feed them into an NUnit `--where` modulo predicate or a committed shard map; never re-discover tests per shard at runtime.

### Reporters
- Always emit **both** a JUnit-shaped XML (`--logger junit` via `JunitXml.TestLogger`) into **`artifacts:reports:junit`** and Allure NUnit results. JUnit feeds GitLab's native MR widget (the `dorny/test-reporter` equivalent); Allure feeds humans with history.
- `dotnet test` exits non-zero on failure → the pipeline reds automatically. Do not mask it with `allow_failure: true`.

### Secrets
- **`id_tokens:` OIDC only** — declare the block with the cloud's `aud:`, exchange for short-lived creds, then read secrets. No long-lived AWS keys / Azure secrets in CI/CD variables.
- The unavoidable token (third-party SaaS key with no OIDC) → **masked + protected** CI/CD variable scoped to protected branches.
- The `aud:` value **must match** the cloud role's trust-policy condition, or `AssumeRoleWithWebIdentity` is rejected.
- Never `echo` a fetched secret; never write it to an `artifacts:paths:` location.

### Retry policy
- **No pipeline-level retry** of failed tests (no `retry:` on the test job). Retry hides bugs.
- Per-test `[Retry(2)]` only for documented network-flake hotspots — document each with a date + issue link in an XML comment.
- `retry:` in GitLab is for **infrastructure** failures only (`when: runner_system_failure`), never assertions. For chronic flakes, quarantine via `qa/flaky-test-quarantine/dotnet`.

### Artifacts
- JUnit + coverage: `expire_in: 30 days` (on the `api-tests` / `integration-tests` jobs).
- Playwright traces / videos: `expire_in: 14 days` on the `ui-tests` job — one `artifacts:` block per job, one `expire_in`, so traces ride with the results there. Keep them small by retaining traces on failure only (Playwright-for-.NET trace config) rather than a `needs:`-download-then-reupload job.
- Allure history: carried in a **dedicated cache** keyed on a stable string (`allure-history`), **not** the lock file.
- Don't double-declare the same files under `paths:` and `reports:`.

### Perf gate
- k6 / NBomber thresholds live inline. The pipeline does not interpret metrics.
- k6 returns exit code 99 on breach — the job fails automatically. Do not add guards that swallow it.
- Pin the perf-tool version (`grafana/k6:0.52.0`); upgrade in a dedicated MR.

### What NOT to do
- No Testcontainers without `docker:dind` (+ `TESTCONTAINERS_HOST_OVERRIDE: docker`) or a mounted host socket.
- No long-lived cloud keys in CI/CD variables — use `id_tokens:` OIDC.
- No `allow_failure: true` on a test job to "make it green".
- No unpinned `dotnet restore` in CI — use `--locked-mode`.
- No `--blame` in production runs (slow); enable only for a targeted hang re-run.
- No mixing NUnit `[Parallelizable]` with `LevelOfParallelism > 1` in a fixture that owns a Testcontainer — instant flake.
- No two jobs writing the same `cache:key` (`policy: pull-push`) — one `install` job writes, the rest pull.
- No `retry:` on test assertions — reserve it for `runner_system_failure`.
- No printing of a fetched secret, even with `|| true`.

## Generation steps

1. Read any existing `.gitlab-ci.yml` to learn runner tags, `image:`, existing `id_tokens:`/variables, and stage conventions.
2. Inventory test projects: `find . -name '*Tests.csproj' -not -path '*/bin/*'`. Group into API / integration / UI / perf. Confirm the NuGet lock file exists (enable it if not).
3. Generate `.gitlab-ci.yml` with `stages: [install, test, merge, perf, publish]`, the `.nuget-cache` anchor, one `install` job (`policy: pull-push`), the sharded `api-tests` / `ui-tests` jobs, the dind `integration-tests` job, the `pages` Allure job, and the gated `k6-perf` job. Add `JunitXml.TestLogger` to each test project.
4. Configure cloud OIDC: register GitLab as an OIDC provider, create the role with a trust policy keyed on the project/ref claims, set `id_tokens:` `aud:` to match. Document the subject claim in a header comment.
5. Validate with **CI Lint** (Pipelines → CI Lint) or `glab ci lint`, then open a draft MR and confirm every expected job and the MR test widget appear.

## Cross-references

- **`qa/ci-pipelines/gitlab-ci/typescript`** (canonical) + **`qa/ci-pipelines/gitlab-ci/java`** — the same-CI siblings; the TS one shows the Playwright `blob`/`merge-reports` flow this stack replaces with a per-shard Allure merge.
- **`qa/ci-pipelines/github-actions/dotnet`** — the structural template this ports from; the `strategy.matrix` / `dorny/test-reporter` (TRX) variant.
- **`qa/ci-pipelines/azure-pipelines/dotnet`** — the Azure sibling; the `strategy: parallel` / service-connection variant.
- **`qa/db-testing/testcontainers/dotnet`** — the integration-tests job runs these (needs the `docker:dind` service shown above).
- **`qa/network-monitoring/proxy/dotnet`** — runs an **external MITM proxy** (`Titanium.Web.Proxy`) the job must start/stop, whose **CA the client must trust** (per-run — no stored secret); the in-process `playwright-routes`/`cdp` specs need no extra plumbing.
- **`qa/network-monitoring/cdp/dotnet`** — in-process CDP specs the `ui-tests` job runs directly.
- **`qa/allure-reporting/dotnet`** — adapter wiring that produces `allure-results/`.
- **`qa/performance/nbomber/dotnet`** + **`qa/performance/k6/typescript`** — perf-job scripts; SLO contract in `qa/performance/_shared`.
- **`qa/_shared/ci-conventions`** — cross-stack rules (artifact retention, OIDC) this skill enforces.

## Sources synthesized (research-first per CLAUDE.md)

- [GitLab Docs — CI/CD YAML syntax reference](https://docs.gitlab.com/ci/yaml/) — `parallel`, `needs`, `artifacts:reports:junit`, `cache:key:files`, `rules`, `interruptible`, `id_tokens`.
- [GitLab Docs — Caching in GitLab CI/CD](https://docs.gitlab.com/ci/caching/) + [Build a .NET project](https://docs.gitlab.com/ci/examples/dotnet/) — NuGet cache via `NUGET_PACKAGES` + `cache:key:files:`.
- [GitLab Docs — predefined variables](https://docs.gitlab.com/ci/variables/predefined_variables/) — `CI_NODE_INDEX` (1-based) / `CI_NODE_TOTAL` from `parallel: N`.
- [JUnit Test Logger (spekt/junit.testlogger)](https://github.com/spekt/junit.testlogger) — `--logger "junit;LogFilePath=..."` for `dotnet test` → GitLab `artifacts:reports:junit`.
- [GitLab Docs — Connect to cloud services with OpenID Connect / ID tokens](https://docs.gitlab.com/ci/cloud_services/aws/) — `id_tokens:` + `aud:` and `AssumeRoleWithWebIdentity` against AWS.

## Changelog

- 2026-05-31: Authored as the GitLab CI/CD / .NET port of `qa/ci-pipelines/github-actions/dotnet` (structural template) and sibling of the canonical `qa/ci-pipelines/gitlab-ci/typescript` — QA Skills Library Phase 1, `qa/GAP-ANALYSIS.md` row 13; closes the `ci-pipelines` family and Phase 1. True port (translate, not redesign): `parallel: N` + `CI_NODE_INDEX`/`CI_NODE_TOTAL` into an NUnit `--where` modulo slice (Playwright `Playwright.Shard`), `cache:key:files:[packages.lock.json]` + one `pull-push` install job with `--locked-mode`, `id_tokens:` cloud OIDC (no long-lived secrets), `--logger junit` → `artifacts:reports:junit` native widget, Allure on GitLab Pages with history in a stable-key cache, `docker:dind` + `TESTCONTAINERS_HOST_OVERRIDE` for Testcontainers, k6 exit-99 perf gate gated to `schedule`.
