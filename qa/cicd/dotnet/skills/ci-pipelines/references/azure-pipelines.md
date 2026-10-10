# QA — Azure Pipelines for .NET Test Suites

Authors `azure-pipelines.yml` (or template fragments) that run NUnit / Playwright / Testcontainers-backed integration tests on Microsoft-hosted Linux agents, shard for speed with NUnit class filters, upload the Playwright failure evidence, publish Allure with history, fail on real failures (not flakes), and pull secrets via workload-identity-federation (OIDC) rather than PATs.

**The UI lifecycle is not written here.** `qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs` owns it: it reads `BASE_URL` (required), runs headless unless `HEADED=1`, and on a failed test keeps a full-page screenshot, the trace and the video in `UiTests/bin/<cfg>/net10.0/playwright-artifacts/<Class>.<Test>.{png,zip,webm}`. The pipeline runs that as is and publishes exactly that folder. `playwright-videos/` holds raw recordings `BaseTest` deletes after every test; it is never published. What the evidence is and how to read it is `qa/dotnet/skills/evidence-capture`. The shard filters come from `ci/nunit-shards.sh`, defined once in this skill's `SKILL.md`.

## When to use

- New QA pipeline for a .NET test project (`ApiTests`, `UiTests`, `IntegrationTests`)
- Adding sharding / matrix parallelism to an existing serial pipeline
- Wiring Allure publish + history (cache or Azure Storage)
- Replacing PATs / service-principal secrets with OIDC federated credentials
- Adding a perf gate (k6 / NBomber) that breaks the build on SLO regression

## When NOT to use

- GitHub Actions equivalent → `references/github-actions.md` in this skill
- GitLab CI equivalent → `references/gitlab-ci.md` in this skill
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
| Agent pool | `ubuntu-latest` (Microsoft-hosted; Docker, PowerShell 7 and a JDK pre-installed) | Self-hosted only for proprietary hardware (mobile farm, GPU) |
| Triggers | `pr: [main]` + nightly `schedules` | Push-on-main triggers only when the suite is < 5 min |
| Test framework reporter | `--logger "trx"` + Allure NUnit adapter | Always both — TRX feeds `PublishTestResults@2`, Allure feeds humans |
| Sharding | A shards job runs `ci/nunit-shards.sh` once; `strategy: parallel: N` runs one class filter per agent | Shard by namespace when a shard's filter grows past a few thousand characters |
| Playwright browsers | `pwsh UiTests/bin/<cfg>/net10.0/playwright.ps1 install --with-deps chromium` on the agent | The pinned image `mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` for visual baselines (see the UI template) |
| Auth to Azure / Key Vault | Workload Identity Federation (OIDC) | Never PATs, never long-lived service-principal secrets |
| Retry on failure | **Off at the pipeline level** | Per-test `[Retry(2)]` only for documented network-flake hotspots — never blanket retry |
| Artifact retention | 14 days for `playwright-artifacts/` (published on failure only), 30 days for TRX, 90 days for Allure history | Bump only with a stated reason (compliance, post-mortem window) |
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
    value: '10.0.x'
  - name: buildConfiguration
    value: Release
  - group: qa-test-secrets

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

`qa-test-secrets` is a variable group backed by Key Vault through the OIDC service connection.

### Sharded NUnit job — `pipelines/templates/api-tests.yml`

```yaml
parameters:
  - name: shardCount
    type: number
    default: 2

jobs:
  - job: ApiShards
    pool:
      vmImage: ubuntu-latest
    steps:
      - checkout: self
      - task: UseDotNet@2
        inputs:
          version: $(dotnetVersion)

      - script: bash ci/nunit-shards.sh ApiTests/ApiTests.csproj ${{ parameters.shardCount }} $(Build.ArtifactStagingDirectory)/api-shards
        displayName: Split test classes into ${{ parameters.shardCount }} shards

      - publish: $(Build.ArtifactStagingDirectory)/api-shards
        artifact: api-shards

  - job: ApiTests
    dependsOn: ApiShards
    displayName: API Tests (shard $(System.JobPositionInPhase)/${{ parameters.shardCount }})
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

      - download: current
        artifact: api-shards

      - task: AzureCLI@2
        displayName: Fetch test secrets via OIDC
        inputs:
          azureSubscription: sc-qa-oidc
          scriptType: bash
          scriptLocation: inlineScript
          inlineScript: |
            echo "##vso[task.setvariable variable=API_BASE_URL;issecret=false]$(az keyvault secret show --vault-name kv-qa --name api-base-url --query value -o tsv)"
            echo "##vso[task.setvariable variable=AUTH0_M2M_SECRET;issecret=true]$(az keyvault secret show --vault-name kv-qa --name auth0-m2m --query value -o tsv)"

      - script: |
          read -r SHARD_FILTER < "$(Pipeline.Workspace)/api-shards/$(System.JobPositionInPhase).filter"
          dotnet test ApiTests/ApiTests.csproj \
            --configuration $(buildConfiguration) \
            --filter "($SHARD_FILTER)&TestCategory!=Slow&TestCategory!=Perf" \
            --logger "trx;LogFileName=api-shard-$(System.JobPositionInPhase).trx" \
            --logger "console;verbosity=minimal" \
            --results-directory $(Agent.TempDirectory)/TestResults \
            --collect:"XPlat Code Coverage"
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
          targetPath: 'ApiTests/bin/$(buildConfiguration)/net10.0/allure-results'
          artifact: 'allure-results-api-$(System.JobPositionInPhase)'
```

- `ApiShards` lists the tests once and publishes `api-shards/<i>.filter`; each agent of `strategy: parallel` reads the file for its 1-based `System.JobPositionInPhase`. Both jobs take `shardCount` from the same parameter, so they cannot drift. Fewer test classes than shards fails `ApiShards` — lower `shardCount`.
- `read -r` keeps the filter's escaped `\(` intact, and keeps the shell's `$(...)` out of a line Azure's `$(var)` macro syntax also reads.
- Secret variables are not mapped into a script's environment by themselves — the `env:` block maps them.
- Allure.NUnit writes `allure-results/` into the test host's working directory, the build output folder.

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
  - job: UiShards
    pool:
      vmImage: ubuntu-latest
    steps:
      - checkout: self
      - task: UseDotNet@2
        inputs:
          version: $(dotnetVersion)

      - script: bash ci/nunit-shards.sh UiTests/UiTests.csproj ${{ parameters.shardCount }} $(Build.ArtifactStagingDirectory)/ui-shards
        displayName: Split test classes into ${{ parameters.shardCount }} shards

      - publish: $(Build.ArtifactStagingDirectory)/ui-shards
        artifact: ui-shards

  - job: UiTests
    dependsOn: UiShards
    displayName: UI Tests (shard $(System.JobPositionInPhase)/${{ parameters.shardCount }})
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

      - download: current
        artifact: ui-shards

      - script: |
          dotnet build UiTests/UiTests.csproj -c $(buildConfiguration)
          pwsh UiTests/bin/$(buildConfiguration)/net10.0/playwright.ps1 install --with-deps chromium
        displayName: Build + install Playwright browsers

      - task: AzureCLI@2
        displayName: Fetch test credentials via OIDC
        inputs:
          azureSubscription: sc-qa-oidc
          scriptType: bash
          scriptLocation: inlineScript
          inlineScript: |
            echo "##vso[task.setvariable variable=BASE_URL;issecret=false]$(az keyvault secret show --vault-name kv-qa --name base-url --query value -o tsv)"
            echo "##vso[task.setvariable variable=E2E_USER;issecret=false]$(az keyvault secret show --vault-name kv-qa --name e2e-user --query value -o tsv)"
            echo "##vso[task.setvariable variable=E2E_PASSWORD;issecret=true]$(az keyvault secret show --vault-name kv-qa --name e2e-password --query value -o tsv)"

      - script: |
          read -r SHARD_FILTER < "$(Pipeline.Workspace)/ui-shards/$(System.JobPositionInPhase).filter"
          dotnet test UiTests/UiTests.csproj \
            --no-build -c $(buildConfiguration) \
            --filter "($SHARD_FILTER)&TestCategory!=Flaky" \
            --logger "trx;LogFileName=ui-shard-$(System.JobPositionInPhase).trx" \
            --results-directory $(Agent.TempDirectory)/TestResults
        displayName: Run UI tests (shard $(System.JobPositionInPhase)/$(System.TotalJobsInPhase))
        env:
          BASE_URL: $(BASE_URL)
          E2E_USER: $(E2E_USER)
          E2E_PASSWORD: $(E2E_PASSWORD)

      - task: PublishTestResults@2
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: VSTest
          testResultsFiles: '$(Agent.TempDirectory)/TestResults/*.trx'
          testRunTitle: 'UI shard $(System.JobPositionInPhase)'
          failTaskOnFailedTests: true

      - task: PublishPipelineArtifact@1
        condition: failed()
        inputs:
          targetPath: 'UiTests/bin/$(buildConfiguration)/net10.0/playwright-artifacts'
          artifact: 'playwright-artifacts-$(System.JobPositionInPhase)'
          publishLocation: pipeline

      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs:
          targetPath: 'UiTests/bin/$(buildConfiguration)/net10.0/allure-results'
          artifact: 'allure-results-ui-$(System.JobPositionInPhase)'
```

- **No `-- Playwright.Shard=i/N`.** `Microsoft.Playwright.NUnit` ignores it ("Playwright>Shard is not implemented") and every agent would run the whole suite; the class filter is the shard. `BaseTest`'s `[Parallelizable(ParallelScope.Self)]` keeps a class on one worker, so a class is the unit.
- **No headless flag.** `BaseTest` is headless unless `HEADED=1` (the runsettings set `Headless`), which only a local run sets.
- `--with-deps` installs OS packages through `sudo` on the agent; the 1.63.0 binding installs its own Chromium build. Do not cache browsers.
- `BASE_URL`, `E2E_USER` and `E2E_PASSWORD` come through OIDC: `BaseTest` throws without `BASE_URL`, and the root-namespace `AuthSetup` signs in once per shard before any fixture runs.
- `playwright-artifacts-<n>` is published **on failure only** (`condition: failed()`): the screenshot, trace and video of each failed test plus any deliberate recording. A green run leaves the folder empty.
- The quarantine lane is a second, non-gating job in this template — the same steps without `UiShards` and `strategy`, running `--filter "TestCategory=Flaky"` with `continueOnError: true` on its test step, per `qa/reporting/dotnet/skills/flaky-test-quarantine`.
- **Running in the pinned image** instead of installing browsers — what visual baselines need (`qa/dotnet/skills/visual-regression`): give the job `container: mcr.microsoft.com/playwright/dotnet:v1.63.0-noble` and drop the install line; the image carries the .NET 10 SDK and the browsers. The tag must equal the Playwright version, and there is no `-jammy` .NET image since 1.60. `AzureCLI@2` runs inside the container, which has no Azure CLI, so a container job tests only pages that need no fetched credentials.

### Allure publish with history — `pipelines/templates/allure-publish.yml`

Persist `history/` across runs via Azure Blob (preferred) or pipeline cache (short-term). The report is generated with the one Allure CLI pin, `allure-commandline@2.46.1` (`qa/cicd/ci-conventions`); the hosted agent's JDK runs it.

```yaml
jobs:
  - job: AllurePublish
    pool:
      vmImage: ubuntu-latest
    steps:
      - checkout: self

      - download: current
        patterns: 'allure-results-*/**'

      - task: AzureCLI@2
        displayName: Download Allure history from Blob
        inputs:
          azureSubscription: sc-qa-oidc
          scriptType: bash
          scriptLocation: inlineScript
          inlineScript: |
            mkdir -p allure-results/history allure-history
            cp -r $(Pipeline.Workspace)/allure-results-*/. allure-results/
            cp UiTests/categories.json allure-results/
            az storage blob download-batch \
              --account-name $(STORAGE_ACCOUNT) \
              --source allure-history \
              --destination allure-history \
              --auth-mode login || echo "no prior history"
            cp -r allure-history/. allure-results/history/ 2>/dev/null || true

      - script: |
          npm install -g allure-commandline@2.46.1
          allure generate allure-results --clean -o allure-report
        displayName: Generate Allure report

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

`categories.json` is read from the results folder, so it is copied in from the test project first. The first-ever run has no history blob, which the `|| echo` covers — it is not a test step.

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
- Membership is computed **once**, in the shards job, by `ci/nunit-shards.sh` (this skill's `SKILL.md`): test classes, round-robin, one `FullyQualifiedName~` term per class, published as a pipeline artifact. Never re-discover tests on an agent, never filter by individual test names, and never pass `Playwright.Shard`.
- `strategy: parallel: N` and the script take N from the same template parameter; each agent reads the file for its `System.JobPositionInPhase`.

### Secrets
- **OIDC only** via Workload Identity Federation service connections. No PATs, no static service-principal secrets.
- Pull secrets in a single `AzureCLI@2` step, hoist as job variables with `##vso[task.setvariable variable=X;issecret=true]`, and map them into the test step's `env:`.
- Never write a secret to a file the artifact step might pick up. Never echo a secret into a script (`echo "$MY_TOKEN"`).

### Reporters
- Always emit **both** TRX and Allure. TRX feeds `PublishTestResults@2` (native Azure Pipelines test tab); Allure feeds humans with history.
- `failTaskOnFailedTests: true` on every `PublishTestResults@2`. The pipeline must red on real failures even if the runner exit code is masked.
- The Allure report is generated with `allure-commandline@2.46.1` — no downloaded allure2 tarball of another version.

### Retry policy
- **No pipeline-level retry** of failed tests. Retry hides bugs.
- Per-test `[Retry(2)]` (two attempts) is allowed only for documented network-flake hotspots (third-party sandboxes, infra warm-up), each with a date and an issue link at the test.
- For genuinely flaky tests, quarantine via `qa/reporting/dotnet/skills/flaky-test-quarantine` — `TestCategory!=Flaky` on the gate, a non-gating `TestCategory=Flaky` job.

### Artifacts
- TRX + coverage: 30 days.
- `UiTests/bin/<cfg>/net10.0/playwright-artifacts/` (trace, video, screenshot of failed tests): 14 days, **only on failure** (`condition: failed()`). Never `playwright-videos/`.
- Allure report: 90 days for the published report; history persisted in Blob indefinitely.
- Container logs (Testcontainers): attach to Allure via the test runner, not as a separate pipeline artifact.

### Perf gate
- k6 / NBomber thresholds must be inline in the script (`thresholds: { http_req_duration: ['p(95)<500'] }`). Pipeline does not interpret metrics.
- The runner returns a non-zero exit code on threshold breach (k6: 99) — the job fails automatically. Do not add YAML guards.
- Pin the perf tool version (`k6 v0.52.0`); upgrade in a dedicated PR.

### What NOT to do
- No `vmImage: 'windows-latest'` for Linux-container tests (Docker engine on Windows is Windows-container by default → Testcontainers Linux modules fail).
- No PATs in `$(System.AccessToken)` for cross-org operations — use OIDC.
- No `continueOnError: true` on a gating test task to "make it green". Fix the test or quarantine it.
- No `-- Playwright.Shard=i/N` and no `NUnit.Where` modulo predicate — neither shards anything.
- No `--blame` flag in production runs (slow); enable only for the targeted re-run of a hang.
- No mixing of NUnit `[Parallelizable]` with `LevelOfParallelism > 1` in a fixture that owns a Testcontainer — instant flake.
- No printing of `$(MY_SECRET)` in any script step, even with `||true`.
- No global `retryCountOnTaskFailure` on the test task. Fail loud.

## Generation steps

1. Read the existing `azure-pipelines.yml` (if any) to learn variable groups, service connections, and stage layout.
2. Inventory test projects: `find . -name '*Tests.csproj' -not -path '*/bin/*'`. Group them into API / integration / UI / perf.
3. Generate:
   - `ci/nunit-shards.sh` from this skill's `SKILL.md`.
   - `azure-pipelines.yml` (top-level) if missing.
   - `pipelines/templates/{build,api-tests,integration-tests,ui-tests,allure-publish,k6-perf}.yml` as needed.
4. Wire one workload-identity-federation service connection (`sc-qa-oidc`) with read access to the test Key Vault, including the `base-url`, `e2e-user` and `e2e-password` secrets the UI job reads. Document the federated subject string in the pipeline header comment.
5. Dry-run with `az pipelines run --branch <PR-branch>` and check that all expected stages, one UI job per shard, appear in the Azure DevOps UI.

## Cross-references

- **`qa/dotnet/skills/ui-test-author/playwright`** — `BaseTest`, `ui.runsettings` and the `UiTests` project the UI template runs.
- **`qa/dotnet/skills/evidence-capture`** — what `playwright-artifacts/` holds and how to read a failed shard's trace.
- **`qa/dotnet/skills/db-testing/testcontainers`** — integration-tests stage runs these.
- **`qa/dotnet/skills/email-testing`** — pair Mailpit as a `services` definition or inline Testcontainers run.
- **`qa/reporting/dotnet/skills/test-reports`** — adapter wiring inside the test project that produces `allure-results/`, and `categories.json`.
- **`qa/reporting/dotnet/skills/flaky-test-quarantine`** — the `Flaky` category and the non-gating lane.
- **`qa/dotnet/skills/load-testing`** + **`qa/typescript/skills/load-testing`** — perf-stage scripts.
- **`devops/azure-pipelines`** — non-QA pipeline patterns (deploy, infra) live here.
- **`qa/cicd/ci-conventions`** — cross-stack rules (artifact retention, OIDC, the Allure CLI pin) that this skill enforces.
