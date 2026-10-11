# QA — GitLab CI/CD for .NET Test Suites

Authors `.gitlab-ci.yml` that runs NUnit / Playwright / Testcontainers-backed integration tests on GitLab runners using .NET 10 (8/9 supported), shards for speed via `parallel:` and NUnit class filters, keeps the Playwright failure evidence, publishes Allure to GitLab Pages with history, fails on real failures (not flakes), and pulls secrets via `id_tokens:` cloud OIDC rather than long-lived CI/CD variables.

**The UI lifecycle is not written here.** `qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs` owns it: it reads `BASE_URL` (required), runs headless unless `HEADED=1`, and on a failed test keeps a full-page screenshot, the trace and the video in `UiTests/bin/<cfg>/net10.0/playwright-artifacts/<Class>.<Test>.{png,zip,webm}`. The pipeline runs that as is and keeps exactly that folder. `playwright-videos/` holds raw recordings `BaseTest` deletes after every test; it is never kept. What the evidence is and how to read it is `qa/dotnet/skills/evidence-capture`. The shard filters come from `ci/nunit-shards.sh`, defined once in this skill's `SKILL.md`.

This is a **true port** of this skill's GitHub Actions reference (`references/github-actions.md`) — the *same* pipeline (same stages, same shard strategy, same artifacts, same gates), re-keyed to GitLab's `.gitlab-ci.yml` vocabulary, and the .NET sibling of the canonical `qa/cicd/typescript/skills/ci-pipelines`. **Translate, don't redesign.** Only the YAML schema and a few primitives differ:

| Capability | GitHub Actions | GitLab CI (this skill) |
|---|---|---|
| Shard fan-out | `strategy.matrix` from the `plan` job's output | `parallel: N` → `CI_NODE_INDEX`/`CI_NODE_TOTAL` |
| Shard membership | `plan` job → `*-shards` artifact | `*-shards` job in `install` → artifact read through `needs:` |
| DAG / ordering | `needs:` between jobs | `needs:` (DAG) + `dependencies:` (artifact scope) |
| Cache | `actions/setup-dotnet` + `actions/cache` | `cache:key:files:[packages.lock.json]` + `policy:` |
| JUnit summary | `dorny/test-reporter` (TRX) | native `artifacts:reports:junit:` (`--logger junit`) |
| Cloud auth | `permissions: id-token: write` + `azure/login` | `id_tokens:` + `aud:` → assume role |
| Cancel superseded | `concurrency: cancel-in-progress` | `interruptible: true` + project auto-cancel |
| Gating | `if: github.event_name == 'schedule'` | `rules: - if: $CI_PIPELINE_SOURCE == "schedule"` |

The canonical TS sibling uses Playwright's native `blob` → `merge-reports` flow; .NET has no blob reporter, so — exactly as in `github-actions` — each NUnit shard emits its own JUnit XML and Allure results, and the `pages` job merges the Allure results into one report. k6 stays the perf tool (matching the `github-actions` dotnet sibling's exit-99 gate).

## When to use

- New QA pipeline for a .NET test project (`ApiTests`, `IntegrationTests`, `UiTests`, perf)
- Adding `parallel:` sharding to an existing serial pipeline
- Wiring Allure publish + history to GitLab Pages (or an artifact)
- Replacing long-lived cloud CI/CD variables with `id_tokens:` OIDC
- Adding a perf gate (k6 / NBomber) that breaks the pipeline on SLO regression

## When NOT to use

- GitHub Actions equivalent → `references/github-actions.md` in this skill
- Azure Pipelines equivalent → `references/azure-pipelines.md` in this skill
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
| Runner | `image: mcr.microsoft.com/dotnet/sdk:10.0` on a `docker` runner; the UI job in `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` | Self-hosted/shell runner only for proprietary hardware (mobile farm, GPU) |
| .NET | 10 via the SDK image (match the projects' TFM) | Never up-level a down-level project |
| NuGet cache | `cache:key:files:[packages.lock.json]` (enable lock file) + `policy:` + `--locked-mode` restore | Hash `**/*.csproj` when no lock file exists |
| Triggers | `merge_request_event` + nightly `schedule` (set via `workflow:rules`) | `push` on the default branch only when the suite is < 5 min |
| Test reporter | `--logger "junit;LogFilePath=..."` → `artifacts:reports:junit` + Allure NUnit adapter | Always both — JUnit feeds the MR widget, Allure feeds humans |
| Sharding | A `*-shards` job runs `ci/nunit-shards.sh` once; `parallel: N` runs one class filter per node | Shard by namespace when a shard's filter grows past a few thousand characters |
| Auth to AWS / Azure / Vault | `id_tokens:` + `aud:` → assume role (OIDC) | Never long-lived cloud keys; masked+protected CI/CD variables only for unavoidable tokens |
| Retry on failure | **Off at the pipeline level** (no `retry:` on the test job) | Per-test `[Retry(2)]` only for documented flake hotspots — never blanket `retry:` |
| Cancel superseded | `interruptible: true` + project "auto-cancel redundant pipelines" | Keep nightly un-interruptible |
| Artifact retention | `expire_in: 14 days` on the UI job (failure evidence + Allure results), `30 days` for JUnit; Allure history in cache | Bump only with a stated reason |
| Perf gate | k6 thresholds → exit code 99 → job fails | Soft gate (`allow_failure: true`) only while a baseline is being established |

## Templates

### Top-level pipeline — `.gitlab-ci.yml`

```yaml
stages: [install, test, merge, perf, publish]

default:
  image: mcr.microsoft.com/dotnet/sdk:10.0
  tags: [docker]
  interruptible: true

workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_PIPELINE_SOURCE == "schedule"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

variables:
  BUILD_CONFIGURATION: Release
  DOTNET_NOLOGO: "true"
  DOTNET_CLI_TELEMETRY_OPTOUT: "true"
  NUGET_PACKAGES: "$CI_PROJECT_DIR/.nuget/packages"

.nuget-cache: &nuget-cache
  cache:
    key:
      files: [packages.lock.json]
    paths: [.nuget/packages/]
    policy: pull
```

- `tags: [docker]` picks a runner with the Docker executor; `interruptible: true` is the GitLab analogue of `cancel-in-progress` for superseded MR pipelines.
- `NUGET_PACKAGES` puts the NuGet store in the workspace so it can be cached; the `.nuget-cache` anchor is keyed on the lock file, so a dependency change busts it, and test jobs only pull it.
- The five stages map 1:1 onto the github-actions reusable workflows: `install` primes the NuGet cache and computes the shard filters, `test` fans out the sharded suites, `merge` is unused for .NET (kept for family symmetry; the Allure merge happens in `publish`), `perf` runs the gated k6 job, `publish` builds Allure on GitLab Pages. Enable the NuGet lock file (`<RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>` in `Directory.Build.props`) so `cache:key:files:` has a deterministic key; without it, hash `**/*.csproj`.

### Prime the NuGet cache — `install` stage

```yaml
install:
  stage: install
  cache:
    key:
      files: [packages.lock.json]
    paths: [.nuget/packages/]
    policy: pull-push
  script:
    - dotnet restore --locked-mode
```

One job owns `policy: pull-push`; every test job uses `<<: *nuget-cache` (`policy: pull`) so they never race to write the same key. `--locked-mode` is the .NET analogue of `npm ci` — it refuses to restore if `packages.lock.json` doesn't match the project references.

### Shard membership — `install` stage

```yaml
api-shards:
  stage: install
  <<: *nuget-cache
  script:
    - bash ci/nunit-shards.sh ApiTests/ApiTests.csproj 2 shards/api
  artifacts:
    paths: [shards/api/]
    expire_in: 1 day

ui-shards:
  stage: install
  <<: *nuget-cache
  script:
    - bash ci/nunit-shards.sh UiTests/UiTests.csproj 4 shards/ui
  artifacts:
    paths: [shards/ui/]
    expire_in: 1 day
```

Each job lists its project's tests once and writes `shards/<suite>/<i>.filter`. GitLab does not take a variable in `parallel:`, so the shard count is written twice — here and in the test job — and the test job checks that the two agree before it runs. Fewer test classes than shards fails this job; lower both numbers.

### Sharded NUnit job — `test` stage

```yaml
api-tests:
  stage: test
  <<: *nuget-cache
  parallel: 2
  needs: [api-shards]
  id_tokens:
    AWS_ID_TOKEN:
      aud: https://gitlab.example.com
  script:
    - test "$(ls shards/api/*.filter | wc -l)" -eq "$CI_NODE_TOTAL"
    - read -r SHARD_FILTER < "shards/api/$CI_NODE_INDEX.filter"
    - export AWS_WEB_IDENTITY_TOKEN_FILE="$(mktemp)"
    - echo "$AWS_ID_TOKEN" > "$AWS_WEB_IDENTITY_TOKEN_FILE"
    - export AWS_ROLE_ARN="arn:aws:iam::111122223333:role/qa-ci"
    - export API_BASE_URL="$(aws ssm get-parameter --name /qa/api-base-url --with-decryption --query Parameter.Value --output text)"
    - >
      dotnet test ApiTests/ApiTests.csproj
      --configuration "$BUILD_CONFIGURATION"
      --filter "($SHARD_FILTER)&TestCategory!=Slow&TestCategory!=Perf"
      --logger "junit;LogFilePath=$CI_PROJECT_DIR/reports/junit-api-$CI_NODE_INDEX.xml"
      --logger "console;verbosity=minimal"
  artifacts:
    when: always
    expire_in: 30 days
    paths: [ApiTests/bin/$BUILD_CONFIGURATION/net10.0/allure-results/]
    reports:
      junit: reports/junit-api-*.xml
```

- `parallel: N` injects `CI_NODE_INDEX` (1-based) and `CI_NODE_TOTAL`; the job reads the filter file for its index. The `test … -eq` line fails the job when `parallel:` and the shard job's count drift apart — otherwise some classes would never run.
- `read -r` keeps the filter's escaped `\(` intact.
- The `id_tokens:` OIDC token is exchanged for a role; `aud` must match the role's trust policy.
- The `junit` logger comes from the `JunitXml.TestLogger` NuGet package; add it to each test project so `--logger junit` resolves.
- GitLab's native test widget parses the `artifacts:reports:junit` XML directly — the GitLab equivalent of `dorny/test-reporter` reading TRX. `dotnet test` already exits non-zero on failure, which reds the pipeline. Do not add `allow_failure: true`.
- The SDK image ships no AWS CLI: the jobs that fetch through `aws ssm` assume a runner image that adds it, or install it in `before_script`.

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
    TESTCONTAINERS_HOST_OVERRIDE: "docker"
    TESTCONTAINERS_RYUK_DISABLED: "false"
  script:
    - docker info
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

`docker info` fails fast if dind did not come up. `TESTCONTAINERS_HOST_OVERRIDE: docker` is the critical line: with dind, containers' mapped ports are reachable at the `docker` service alias, not `localhost`. Keep Ryuk **enabled** — it reaps leaked containers between jobs on a warm runner. (On a runner configured with a mounted host Docker socket instead of dind, drop the `services:`/`DOCKER_*` block.)

### Playwright UI shard — `test` stage

```yaml
ui-tests:
  stage: test
  <<: *nuget-cache
  image: mcr.microsoft.com/playwright/dotnet:v1.63.0-noble
  parallel: 4
  needs: [ui-shards]
  id_tokens:
    AWS_ID_TOKEN:
      aud: https://gitlab.example.com
  script:
    - test "$(ls shards/ui/*.filter | wc -l)" -eq "$CI_NODE_TOTAL"
    - read -r SHARD_FILTER < "shards/ui/$CI_NODE_INDEX.filter"
    - export AWS_WEB_IDENTITY_TOKEN_FILE="$(mktemp)"
    - echo "$AWS_ID_TOKEN" > "$AWS_WEB_IDENTITY_TOKEN_FILE"
    - export AWS_ROLE_ARN="arn:aws:iam::111122223333:role/qa-ci"
    - export BASE_URL="$(aws ssm get-parameter --name /qa/base-url --query Parameter.Value --output text)"
    - export E2E_USER="$(aws ssm get-parameter --name /qa/e2e-user --query Parameter.Value --output text)"
    - export E2E_PASSWORD="$(aws ssm get-parameter --name /qa/e2e-password --with-decryption --query Parameter.Value --output text)"
    - dotnet build UiTests/UiTests.csproj -c "$BUILD_CONFIGURATION"
    - >
      dotnet test UiTests/UiTests.csproj --no-build -c "$BUILD_CONFIGURATION"
      --filter "($SHARD_FILTER)&TestCategory!=Flaky&TestCategory!=visual&TestCategory!=lighthouse&TestCategory!=grid"
      --logger "junit;LogFilePath=$CI_PROJECT_DIR/reports/junit-ui-$CI_NODE_INDEX.xml"
  artifacts:
    when: always
    expire_in: 14 days
    paths:
      - UiTests/bin/$BUILD_CONFIGURATION/net10.0/allure-results/
      - UiTests/bin/$BUILD_CONFIGURATION/net10.0/playwright-artifacts/
    reports:
      junit: reports/junit-ui-*.xml
```

- **The pinned image is the default here**: `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` carries the .NET 10 SDK and the 1.63.0 browsers with their OS libraries, so there is no install step and no `pwsh` call. The tag must equal the Playwright package version (a mismatch fails with "Executable doesn't exist"), and there is no `-jammy` .NET image since 1.60. The same image produces visual baselines (`qa/dotnet/skills/visual-regression`).
- **No `Playwright.Shard=$CI_NODE_INDEX/$CI_NODE_TOTAL`.** `Microsoft.Playwright.NUnit` ignores it ("Playwright>Shard is not implemented") and every node would run the whole suite; the class filter is the shard. `BaseTest`'s `[Parallelizable(ParallelScope.Self)]` keeps a class on one worker, so a class is the unit.
- **No headless flag.** `BaseTest` is headless unless `HEADED=1` (the runsettings set `Headless`), which only a local run sets.
- `BASE_URL`, `E2E_USER` and `E2E_PASSWORD` come through OIDC: `BaseTest` throws without `BASE_URL`, and the root-namespace `AuthSetup` signs in once per shard before any fixture runs. The image ships no AWS CLI, as for the other jobs.
- **One `artifacts:` block per job**, so the failure evidence rides with the Allure results under one `expire_in`. `playwright-artifacts/` is empty on a green run — `BaseTest` writes it on failure only — so the 14-day bucket stays small. There is no Playwright "trace config" in .NET to tune; the keep-on-failure behaviour is `BaseTest`'s code.
- The quarantine lane is a second job with the same script minus the shard lines, running `--filter "TestCategory=Flaky"` with `allow_failure: true` and no `parallel:` — the one non-gating exception (`qa/reporting/dotnet/skills/flaky-test-quarantine`).

### Allure publish with history — `publish` stage (GitLab Pages)

GitLab has no `gh-pages` branch. The native deliverable is **GitLab Pages**: a job literally named `pages` that publishes a `public/` directory. Allure trend history (the `history/` folder) is carried across pipelines in a **dedicated cache with a stable key** — the GitLab analogue of the `gh-pages` branch. The `pages` job collects the per-shard `allure-results/` artifacts and generates one report with the one Allure CLI pin, `allure-commandline@2.46.1` (`qa/cicd/ci-conventions`), which needs Node and a JRE.

```yaml
pages:
  stage: publish
  image: node:24-bookworm
  needs:
    - job: api-tests
      artifacts: true
    - job: ui-tests
      artifacts: true
  when: always
  cache:
    key: allure-history
    paths: [allure-history/]
    policy: pull-push
  before_script:
    - apt-get update && apt-get install -y default-jre-headless
  script:
    - npm i -g allure-commandline@2.46.1
    - mkdir -p allure-results && find . -type d -name allure-results -path '*/bin/*' -exec cp -r {}/. allure-results/ \;
    - cp UiTests/categories.json allure-results/
    - mkdir -p allure-results/history && cp -r allure-history/. allure-results/history/ 2>/dev/null || true
    - allure generate allure-results --clean -o public
    - rm -rf allure-history && cp -r public/history allure-history
  artifacts:
    paths: [public/]
    expire_in: 30 days
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

The stable cache key — **not** the lock file — is what lets history persist. `categories.json` is read from the results folder, so it is copied in from the test project first. When GitLab Pages is disabled, drop the `pages` name and the Pages `rules`, keep the same script, and publish `public/` as a plain artifact with `expire_in: 90 days`.

### k6 perf gate — `perf` stage

k6 returns exit code 99 when thresholds break; the job inherits that exit code and fails — no extra glue, matching the sibling's contract from `qa/_shared/performance` (tests **fail the build** when SLOs aren't met). This matches the `github-actions` dotnet sibling's k6 exit-99 gate; swap to NBomber only if the org standardized on it (then assert its own SLO threshold and exit non-zero on breach). Gate it to the nightly schedule so MRs stay fast.

```yaml
k6-perf:
  stage: perf
  image: grafana/k6:0.52.0
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

`grafana/k6:0.52.0` is pinned; upgrade it in a dedicated MR.

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
- Membership is computed **once**, in the `*-shards` job, by `ci/nunit-shards.sh` (this skill's `SKILL.md`): test classes, round-robin, one `FullyQualifiedName~` term per class. Never re-discover tests on a node, never filter by individual test names, never pass `Playwright.Shard`, and never use an `NUnit.Where` modulo predicate — none of them shards.
- The shard count appears in the `*-shards` script and in `parallel:`; the test job's first line fails when they differ.

### Reporters
- Always emit **both** a JUnit-shaped XML (`--logger junit` via `JunitXml.TestLogger`) into **`artifacts:reports:junit`** and Allure NUnit results. JUnit feeds GitLab's native MR widget (the `dorny/test-reporter` equivalent); Allure feeds humans with history.
- `dotnet test` exits non-zero on failure → the pipeline reds automatically. Do not mask it with `allow_failure: true`.
- The Allure report is generated with `allure-commandline@2.46.1` — no downloaded allure2 tarball of another version.

### Secrets
- **`id_tokens:` OIDC only** — declare the block with the cloud's `aud:`, exchange for short-lived creds, then read secrets. No long-lived AWS keys / Azure secrets in CI/CD variables.
- The unavoidable token (third-party SaaS key with no OIDC) → **masked + protected** CI/CD variable scoped to protected branches.
- The `aud:` value **must match** the cloud role's trust-policy condition, or `AssumeRoleWithWebIdentity` is rejected.
- Never `echo` a fetched secret; never write it to an `artifacts:paths:` location.

### Retry policy
- **No pipeline-level retry** of failed tests (no `retry:` on the test job). Retry hides bugs.
- Per-test `[Retry(2)]` (two attempts) only for documented network-flake hotspots — each with a date + issue link at the test.
- `retry:` in GitLab is for **infrastructure** failures only (`when: runner_system_failure`), never assertions. For chronic flakes, quarantine via `qa/reporting/dotnet/skills/flaky-test-quarantine`.

### Artifacts
- JUnit + coverage: `expire_in: 30 days` (on the `api-tests` / `integration-tests` jobs).
- `UiTests/bin/<cfg>/net10.0/playwright-artifacts/` and the UI Allure results: `expire_in: 14 days` on the `ui-tests` job — one `artifacts:` block per job, one `expire_in`. The evidence folder holds only failed tests' files. Never `playwright-videos/`.
- Shard filter files: `expire_in: 1 day`.
- Allure history: carried in a **dedicated cache** keyed on a stable string (`allure-history`), **not** the lock file.
- Don't double-declare the same files under `paths:` and `reports:`.

### Perf gate
- k6 / NBomber thresholds live inline. The pipeline does not interpret metrics.
- k6 returns exit code 99 on breach — the job fails automatically. Do not add guards that swallow it.
- Pin the perf-tool version (`grafana/k6:0.52.0`); upgrade in a dedicated MR.

### What NOT to do
- No Testcontainers without `docker:dind` (+ `TESTCONTAINERS_HOST_OVERRIDE: docker`) or a mounted host socket.
- No long-lived cloud keys in CI/CD variables — use `id_tokens:` OIDC.
- No `allow_failure: true` on a gating test job to "make it green".
- No Playwright image whose tag differs from the package version, and no `-jammy` .NET image.
- No unpinned `dotnet restore` in CI — use `--locked-mode`.
- No `--blame` in production runs (slow); enable only for a targeted hang re-run.
- No mixing NUnit `[Parallelizable]` with `LevelOfParallelism > 1` in a fixture that owns a Testcontainer — instant flake.
- No two jobs writing the same `cache:key` (`policy: pull-push`) — one `install` job writes, the rest pull.
- No `retry:` on test assertions — reserve it for `runner_system_failure`.
- No printing of a fetched secret, even with `|| true`.

## Generation steps

1. Read any existing `.gitlab-ci.yml` to learn runner tags, `image:`, existing `id_tokens:`/variables, and stage conventions.
2. Inventory test projects: `find . -name '*Tests.csproj' -not -path '*/bin/*'`. Group into API / integration / UI / perf. Confirm the NuGet lock file exists (enable it if not).
3. Generate `ci/nunit-shards.sh` from this skill's `SKILL.md`, and `.gitlab-ci.yml` with `stages: [install, test, merge, perf, publish]`, the `.nuget-cache` anchor, one `install` job (`policy: pull-push`), the `api-shards` / `ui-shards` jobs, the sharded `api-tests` / `ui-tests` jobs, the dind `integration-tests` job, the `pages` Allure job, and the gated `k6-perf` job. Add `JunitXml.TestLogger` to each test project.
4. Configure cloud OIDC: register GitLab as an OIDC provider, create the role with a trust policy keyed on the project/ref claims, set `id_tokens:` `aud:` to match, and store `/qa/base-url`, `/qa/e2e-user` and `/qa/e2e-password` for the UI job. Document the subject claim in a header comment.
5. Validate with **CI Lint** (Pipelines → CI Lint) or `glab ci lint`, then open a draft MR and confirm every expected job, one UI job per shard, and the MR test widget appear.

## Cross-references

- **`qa/cicd/typescript/skills/ci-pipelines`** (canonical) + **`qa/cicd/java/skills/ci-pipelines`** — the same-CI siblings; the TS one shows the Playwright `blob`/`merge-reports` flow this stack replaces with a per-shard Allure merge.
- **`references/github-actions.md`** — the structural template this ports from; the `strategy.matrix` / `dorny/test-reporter` (TRX) variant.
- **`references/azure-pipelines.md`** — the Azure sibling; the `strategy: parallel` / service-connection variant.
- **`qa/dotnet/skills/ui-test-author/playwright`** — `BaseTest`, `ui.runsettings` and the `UiTests` project the UI job runs.
- **`qa/dotnet/skills/evidence-capture`** — what `playwright-artifacts/` holds and how to read a failed shard's trace.
- **`qa/dotnet/skills/db-testing/testcontainers`** — the integration-tests job runs these (needs the `docker:dind` service shown above).
- **`qa/dotnet/skills/network-mocking`** — runs an **external MITM proxy** (`Titanium.Web.Proxy`) the job must start/stop, whose **CA the client must trust** (per-run — no stored secret); its in-process route and CDP specs need no extra plumbing.
- **`qa/reporting/dotnet/skills/test-reports`** — adapter wiring that produces `allure-results/`, and `categories.json`.
- **`qa/reporting/dotnet/skills/flaky-test-quarantine`** — the `Flaky` category and the non-gating lane.
- **`qa/dotnet/skills/load-testing`** + **`qa/typescript/skills/load-testing`** — perf-job scripts; SLO contract in `qa/_shared/performance`.
- **`qa/cicd/ci-conventions`** — cross-stack rules (artifact retention, OIDC, the Allure CLI pin) this skill enforces.
