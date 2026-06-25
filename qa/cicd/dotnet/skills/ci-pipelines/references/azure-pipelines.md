# QA — Azure Pipelines for .NET Test Suites

Authors `azure-pipelines.yml` (or template fragments) that run NUnit / Playwright / Testcontainers-backed integration tests on Microsoft-hosted Linux agents, shard for speed, publish Allure with history, fail on real failures (not flakes), and pull secrets via workload-identity-federation (OIDC) rather than PATs.

## When to use

- New QA pipeline for a .NET test project (`ApiTests`, `UiTests`, `IntegrationTests`)
- Adding sharding / matrix parallelism to an existing serial pipeline
- Wiring Allure publish + history (cache or Azure Storage)
- Replacing PATs / service-principal secrets with OIDC federated credentials
- Adding a perf gate (k6 / NBomber) that breaks the build on SLO regression

## When NOT to use

- GitHub Actions equivalent → `qa/cicd/dotnet/skills/ci-pipelines`
- GitLab CI equivalent → `qa/cicd/dotnet/skills/ci-pipelines`
- App build / deploy pipelines unrelated to tests → `devops/azure-pipelines`
- Non-.NET stacks — use the `java` or `typescript` sibling under this skill

## Inputs needed

Ask at most 3 questions.

1. Which test projects? (`ApiTests`, `IntegrationTests`, `UiTests`, multiple)
2. Sharding fan-out? (default: 4 agents for UI, 2 for API/integration, 1 for perf)
3. Allure history storage? (default: pipeline cache for short-term; Azure Blob for cross-pipeline history)

Infer everything else from `.csproj` files and existing `azure-pipelines.yml` if present.

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Agent pool | `ubuntu-latest` (Microsoft-hosted, Docker pre-installed) | Self-hosted only for proprietary hardware (mobile farm, GPU) |
| Triggers | `pr: [main]` + nightly `schedules` | Push-on-main triggers only when the suite is < 5 min |
| Test framework reporter | `--logger "trx"` + Allure NUnit adapter | Always both — TRX feeds `PublishTestResults@2`, Allure feeds humans |
| Sharding | Job matrix with `nunit --where` filters | Playwright uses `--shard=i/N`; raw category split for NUnit |
| Auth to Azure / Key Vault | Workload Identity Federation (OIDC) | Never PATs, never long-lived service-principal secrets |
| Retry on failure | **Off at the pipeline level** | Per-test `[Retry(2)]` only for documented network-flake hotspots — never blanket retry |
| Artifact retention | 14 days for traces/videos/HAR, 30 days for TRX, 90 days for Allure history | Bump only with a stated reason (compliance, post-mortem window) |
| Perf gate | k6 thresholds → script exit code → job fails | Soft gate (warn-only) only when a baseline is still being established |

## Templates

### Top-level pipeline — `azure-pipelines.yml`

```yaml
trigger: none
pr:
  branches:
    include: [main]

schedules:
  - cron: "0 2 * * *"
    displayName: Nightly full suite
    branches:
      include: [main]
    always: true

variables:
  - name: dotnetVersion
    value: '8.0.x'
  - name: buildConfiguration
    value: Release
  - group: qa-test-secrets   # variable group backed by Key Vault via OIDC

stages:
  - stage: Build
    jobs:
      - template: pipelines/templates/build.yml

  - stage: ApiTests
    dependsOn: Build
    jobs:
      - template: pipelines/templates/api-tests.yml
        parameters:
          shardCount: 2

  - stage: IntegrationTests
    dependsOn: Build
    jobs:
      - template: pipelines/templates/integration-tests.yml

  - stage: UiTests
    dependsOn: Build
    jobs:
      - template: pipelines/templates/ui-tests.yml
        parameters:
          shardCount: 4

  - stage: Perf
    dependsOn: ApiTests
    condition: and(succeeded(), eq(variables['Build.Reason'], 'Schedule'))
    jobs:
      - template: pipelines/templates/k6-perf.yml

  - stage: PublishReports
    dependsOn: [ApiTests, IntegrationTests, UiTests]
    condition: always()
    jobs:
      - template: pipelines/templates/allure-publish.yml
```

### Sharded NUnit job — `pipelines/templates/api-tests.yml`

```yaml
parameters:
  - name: shardCount
    type: number
    default: 2

jobs:
  - job: ApiTests
    displayName: API Tests (shard $(shardIndex)/${{ parameters.shardCount }})
    pool:
      vmImage: ubuntu-latest
    strategy:
      parallel: ${{ parameters.shardCount }}
    timeoutInMinutes: 30
    steps:
      - checkout: self
        fetchDepth: 1

      - task: UseDotNet@2
        inputs:
          version: $(dotnetVersion)
          performMultiLevelLookup: true

      - task: AzureCLI@2
        displayName: Fetch test secrets via OIDC
        inputs:
          azureSubscription: sc-qa-oidc            # workload-identity-federation service connection
          scriptType: bash
          scriptLocation: inlineScript
          inlineScript: |
            echo "##vso[task.setvariable variable=API_BASE_URL;issecret=false]$(az keyvault secret show --vault-name kv-qa --name api-base-url --query value -o tsv)"
            echo "##vso[task.setvariable variable=AUTH0_M2M_SECRET;issecret=true]$(az keyvault secret show --vault-name kv-qa --name auth0-m2m --query value -o tsv)"

      - script: |
          dotnet test ApiTests/ApiTests.csproj \
            --configuration $(buildConfiguration) \
            --logger "trx;LogFileName=api-shard-$(System.JobPositionInPhase).trx" \
            --logger "console;verbosity=minimal" \
            --results-directory $(Agent.TempDirectory)/TestResults \
            --collect:"XPlat Code Coverage" \
            -- NUnit.NumberOfTestWorkers=1 \
               NUnit.Where="cat != Slow and cat != Perf and (test % $(System.TotalJobsInPhase) == $(System.JobPositionInPhase))"
        displayName: Run API tests (shard $(System.JobPositionInPhase))
        env:
          API_BASE_URL: $(API_BASE_URL)
          AUTH0_M2M_SECRET: $(AUTH0_M2M_SECRET)

      - task: PublishTestResults@2
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: VSTest
          testResultsFiles: '$(Agent.TempDirectory)/TestResults/*.trx'
          testRunTitle: 'API shard $(System.JobPositionInPhase)'
          mergeTestResults: false
          failTaskOnFailedTests: true

      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs:
          targetPath: '$(Agent.TempDirectory)/TestResults'
          artifact: 'api-trx-$(System.JobPositionInPhase)'
          publishLocation: pipeline

      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs:
          targetPath: 'ApiTests/allure-results'
          artifact: 'allure-results-api-$(System.JobPositionInPhase)'
```

`NUnit.Where="test % N == i"` is a stand-in — replace with your real shard predicate (category split, fixture-name hash, or pre-computed bin file). For Playwright/.NET use `--` arguments forwarded to the runner with `--shard=i/N`.

### Integration tests with Testcontainers — `pipelines/templates/integration-tests.yml`

Microsoft-hosted Linux agents have Docker pre-installed; no DinD setup needed. Self-hosted agents must mount `/var/run/docker.sock` and have the user in the `docker` group.

```yaml
jobs:
  - job: IntegrationTests
    pool:
      vmImage: ubuntu-latest
    timeoutInMinutes: 25
    steps:
      - checkout: self
      - task: UseDotNet@2
        inputs:
          version: $(dotnetVersion)

      - script: docker info
        displayName: Verify Docker daemon (Testcontainers prereq)

      - script: |
          dotnet test IntegrationTests/IntegrationTests.csproj \
            --configuration $(buildConfiguration) \
            --logger "trx;LogFileName=integration.trx" \
            --results-directory $(Agent.TempDirectory)/TestResults
        displayName: Run integration tests (Testcontainers)
        env:
          TESTCONTAINERS_RYUK_DISABLED: "false"

      - task: PublishTestResults@2
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: VSTest
          testResultsFiles: '$(Agent.TempDirectory)/TestResults/*.trx'
          failTaskOnFailedTests: true
```

### Playwright UI shard — `pipelines/templates/ui-tests.yml`

```yaml
parameters:
  - name: shardCount
    type: number
    default: 4

jobs:
  - job: UiTests
    pool:
      vmImage: ubuntu-latest
    strategy:
      parallel: ${{ parameters.shardCount }}
    timeoutInMinutes: 45
    steps:
      - checkout: self
      - task: UseDotNet@2
        inputs:
          version: $(dotnetVersion)

      - script: |
          dotnet build UiTests/UiTests.csproj -c $(buildConfiguration)
          pwsh UiTests/bin/$(buildConfiguration)/net8.0/playwright.ps1 install --with-deps chromium
        displayName: Build + install Playwright browsers

      - script: |
          dotnet test UiTests/UiTests.csproj \
            --no-build -c $(buildConfiguration) \
            --logger "trx;LogFileName=ui-shard-$(System.JobPositionInPhase).trx" \
            --results-directory $(Agent.TempDirectory)/TestResults \
            -- Playwright.Shard=$(System.JobPositionInPhase)/$(System.TotalJobsInPhase)
        displayName: Run UI tests (shard $(System.JobPositionInPhase)/$(System.TotalJobsInPhase))

      - task: PublishPipelineArtifact@1
        condition: failed()
        inputs:
          targetPath: 'UiTests/bin/$(buildConfiguration)/net8.0/playwright-traces'
          artifact: 'playwright-traces-shard-$(System.JobPositionInPhase)'
          publishLocation: pipeline

      - task: PublishTestResults@2
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: VSTest
          testResultsFiles: '$(Agent.TempDirectory)/TestResults/*.trx'
          failTaskOnFailedTests: true
```

### Allure publish with history — `pipelines/templates/allure-publish.yml`

Persist `history/` across runs via Azure Blob (preferred) or pipeline cache (short-term).

```yaml
jobs:
  - job: AllurePublish
    pool:
      vmImage: ubuntu-latest
    steps:
      - checkout: none

      - download: current
        patterns: 'allure-results-*/**'

      - task: AzureCLI@2
        displayName: Download Allure history from Blob
        inputs:
          azureSubscription: sc-qa-oidc
          scriptType: bash
          scriptLocation: inlineScript
          inlineScript: |
            mkdir -p allure-results allure-history
            cp -r $(Pipeline.Workspace)/allure-results-*/* allure-results/ || true
            az storage blob download-batch \
              --account-name $(STORAGE_ACCOUNT) \
              --source allure-history \
              --destination allure-history \
              --auth-mode login || echo "no prior history"
            cp -r allure-history/* allure-results/history/ 2>/dev/null || true

      - script: |
          npm install -g allure-commandline@2.30.0
          allure generate allure-results --clean -o allure-report

      - task: AzureCLI@2
        displayName: Upload new history
        inputs:
          azureSubscription: sc-qa-oidc
          scriptType: bash
          scriptLocation: inlineScript
          inlineScript: |
            az storage blob upload-batch \
              --account-name $(STORAGE_ACCOUNT) \
              --destination allure-history \
              --source allure-report/history \
              --auth-mode login \
              --overwrite

      - task: PublishPipelineArtifact@1
        inputs:
          targetPath: allure-report
          artifact: allure-report
          publishLocation: pipeline
```

### k6 perf gate — `pipelines/templates/k6-perf.yml`

k6 returns exit code 99 when thresholds break. The job inherits that exit code and fails — no extra glue needed.

```yaml
jobs:
  - job: K6Perf
    pool:
      vmImage: ubuntu-latest
    timeoutInMinutes: 60
    steps:
      - checkout: self
      - script: |
          curl -fsSL https://github.com/grafana/k6/releases/download/v0.52.0/k6-v0.52.0-linux-amd64.tar.gz \
            | tar -xz --strip-components=1 -C /tmp/
          sudo mv /tmp/k6 /usr/local/bin/
        displayName: Install k6 0.52.0 (pinned)

      - script: k6 run --out json=k6-summary.json perf/scenarios/checkout.js
        displayName: Run k6 (thresholds enforce SLOs; exit 99 on breach)
        env:
          K6_BASE_URL: $(API_BASE_URL)

      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs:
          targetPath: k6-summary.json
          artifact: k6-summary
```

## Rules

### Triggers
- `trigger: none` + explicit `pr:` branches. Avoid implicit branch triggers — the YAML should be the source of truth.
- Nightly `schedules` for the full suite. PR runs stay under 15 min by skipping perf and visual-regression unless labelled.
- Use `condition: and(succeeded(), eq(variables['Build.Reason'], 'Schedule'))` to gate expensive stages.

### Sharding
- Default: 4 shards for UI, 2 for API, 1 for integration (Testcontainers cost dominates). Tune from the slowest job on the previous 10 runs.
- Use `strategy: parallel: N` rather than hand-rolled matrices for evenly-balanced shards.
- For uneven suites, pre-compute a `shard.txt` of test IDs and pass to the runner — never re-discover at runtime.

### Secrets
- **OIDC only** via Workload Identity Federation service connections. No PATs, no static service-principal secrets.
- Pull secrets in a single `AzureCLI@2` step, hoist as job variables with `##vso[task.setvariable variable=X;issecret=true]`.
- Never write a secret to a file the artifact step might pick up. Never echo a secret into a script (`echo "$MY_TOKEN"`).

### Reporters
- Always emit **both** TRX and Allure. TRX feeds `PublishTestResults@2` (native Azure Pipelines test tab); Allure feeds humans with history.
- `failTaskOnFailedTests: true` on every `PublishTestResults@2`. The pipeline must red on real failures even if the runner exit code is masked.

### Retry policy
- **No pipeline-level retry** of failed tests. Retry hides bugs.
- Per-test `[Retry(2)]` is allowed only for documented network-flake hotspots (third-party sandboxes, infra warm-up). Document each one in the test's XML comment with a date and a JIRA/issue link.
- For genuinely flaky tests, quarantine via `qa/reporting/dotnet/skills/flaky-test-quarantine` — do not auto-retry.

### Artifacts
- TRX + coverage: 30 days.
- Playwright traces / videos / HAR: 14 days, **only on failure** (`condition: failed()`) to keep storage bounded.
- Allure report: 90 days for the published report; history persisted in Blob indefinitely.
- Container logs (Testcontainers): attach to Allure via the test runner, not as a separate pipeline artifact.

### Perf gate
- k6 / NBomber thresholds must be inline in the script (`thresholds: { http_req_duration: ['p(95)<500'] }`). Pipeline does not interpret metrics.
- The runner returns a non-zero exit code on threshold breach (k6: 99) — the job fails automatically. Do not add YAML guards.
- Pin the perf tool version (`k6 v0.52.0`); upgrade in a dedicated PR.

### What NOT to do
- No `vmImage: 'windows-latest'` for Linux-container tests (Docker engine on Windows is Windows-container by default → Testcontainers Linux modules fail).
- No PATs in `$(System.AccessToken)` for cross-org operations — use OIDC.
- No `continueOnError: true` on a test task to "make it green". Fix the test or quarantine it.
- No `--blame` flag in production runs (slow); enable only for the targeted re-run of a hang.
- No mixing of NUnit `[Parallelizable]` with `LevelOfParallelism > 1` in a fixture that owns a Testcontainer — instant flake.
- No printing of `$(MY_SECRET)` in any script step, even with `||true`.
- No global `retryCountOnTaskFailure` on the test task. Fail loud.

## Generation steps

1. Read the existing `azure-pipelines.yml` (if any) to learn variable groups, service connections, and stage layout.
2. Inventory test projects: `find . -name '*Tests.csproj' -not -path '*/bin/*'`. Group them into API / integration / UI / perf.
3. Generate:
   - `azure-pipelines.yml` (top-level) if missing.
   - `pipelines/templates/{build,api-tests,integration-tests,ui-tests,allure-publish,k6-perf}.yml` as needed.
4. Wire one workload-identity-federation service connection (`sc-qa-oidc`) with read access to the test Key Vault. Document the federated subject string in the pipeline header comment.
5. Dry-run with `az pipelines run --branch <PR-branch>` and check that all expected stages appear in the Azure DevOps UI.

## Cross-references

- **`qa/dotnet/skills/db-testing/testcontainers`** — integration-tests stage runs these.
- **`qa/dotnet/skills/email-testing`** — pair Mailpit as a `services` definition or inline Testcontainers run.
- **`qa/reporting/dotnet/skills/allure-reporting`** — adapter wiring inside the test project that produces `allure-results/`.
- **`qa/dotnet/skills/performance/nbomber`** + **`qa/typescript/skills/performance/k6`** — perf-stage scripts.
- **`devops/azure-pipelines`** — non-QA pipeline patterns (deploy, infra) live here.
- **`qa/cicd/ci-conventions`** — cross-stack rules (artifact retention, OIDC) that this skill enforces.
