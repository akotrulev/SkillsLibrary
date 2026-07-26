# QA — Azure Pipelines for TypeScript Test Suites

Authors `azure-pipelines.yml` for Vitest / Jest / Playwright / k6 suites on Microsoft-hosted Linux agents — sharded, Allure-published, OIDC-authenticated, with proper artifact retention and a hard perf gate.

## When to use

- New QA pipeline for a TS test project (`api-tests`, `e2e`, `integration`)
- Adding Playwright `--shard=i/N` parallelism
- Wiring Allure publish + history
- Replacing PATs with OIDC federated credentials
- Adding a k6 perf gate that breaks the build on SLO regression

## When NOT to use

- GitHub Actions → `qa/cicd/typescript/skills/ci-pipelines`
- GitLab CI → `qa/cicd/typescript/skills/ci-pipelines`
- App build / deploy → `devops/azure-pipelines`
- Non-TS stacks — see siblings

## Inputs needed

1. Test runners in scope? (Vitest, Jest, Playwright, k6)
2. Sharding fan-out? (default 4 for Playwright, 2 for Vitest integration, 1 for k6)
3. Allure history storage? (pipeline cache short-term; Azure Blob cross-pipeline)

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Agent pool | `ubuntu-latest` | Self-hosted only for proprietary hardware |
| Node version | 20 LTS, pinned via `.nvmrc` | Newer LTS once it's been GA for 3 months |
| Reporter | JUnit (`vitest --reporter=junit`) + Allure adapter | Always both |
| Sharding | Playwright `--shard=i/N`; Vitest `vitest --shard` (since 1.4) | Pre-computed bin file when fixtures are uneven |
| Auth | Workload Identity Federation (OIDC) | Never PATs |
| Retry | **Off at pipeline level** | Per-test `test.retry()` only for documented flake hotspots |
| Artifacts | 14 d traces/videos, 30 d JUnit, 90 d Allure | Stated reason to bump |
| Perf gate | k6 thresholds → exit 99 → job fails | Soft gate only while baselining |

## Templates

### Top-level — `azure-pipelines.yml`

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
  - name: nodeVersion
    value: '20.x'
  - group: qa-test-secrets

stages:
  - stage: Build
    jobs:
      - template: pipelines/templates/build.yml

  - stage: ApiTests
    dependsOn: Build
    jobs:
      - template: pipelines/templates/api-tests.yml
        parameters: { shardCount: 2 }

  - stage: IntegrationTests
    dependsOn: Build
    jobs:
      - template: pipelines/templates/integration-tests.yml

  - stage: E2E
    dependsOn: Build
    jobs:
      - template: pipelines/templates/playwright.yml
        parameters: { shardCount: 4 }

  - stage: Perf
    dependsOn: ApiTests
    condition: and(succeeded(), eq(variables['Build.Reason'], 'Schedule'))
    jobs:
      - template: pipelines/templates/k6-perf.yml

  - stage: PublishReports
    dependsOn: [ApiTests, IntegrationTests, E2E]
    condition: always()
    jobs:
      - template: pipelines/templates/allure-publish.yml
```

### Playwright shard — `pipelines/templates/playwright.yml`

```yaml
parameters:
  - name: shardCount
    type: number
    default: 4

jobs:
  - job: E2E
    displayName: Playwright shard $(System.JobPositionInPhase)/${{ parameters.shardCount }}
    pool: { vmImage: ubuntu-latest }
    strategy:
      parallel: ${{ parameters.shardCount }}
    timeoutInMinutes: 45
    steps:
      - checkout: self
      - task: NodeTool@0
        inputs: { versionSpec: $(nodeVersion) }

      - script: npm ci
        displayName: Install deps

      - script: npx playwright install --with-deps chromium
        displayName: Install Chromium

      - task: AzureCLI@2
        displayName: Fetch test secrets via OIDC
        inputs:
          azureSubscription: sc-qa-oidc
          scriptType: bash
          scriptLocation: inlineScript
          inlineScript: |
            echo "##vso[task.setvariable variable=BASE_URL;issecret=false]$(az keyvault secret show --vault-name kv-qa --name base-url --query value -o tsv)"
            echo "##vso[task.setvariable variable=API_KEY;issecret=true]$(az keyvault secret show --vault-name kv-qa --name api-key --query value -o tsv)"

      - script: |
          npx playwright test \
            --shard=$(System.JobPositionInPhase)/$(System.TotalJobsInPhase) \
            --reporter=junit,line,allure-playwright
        displayName: Run Playwright tests
        env:
          BASE_URL: $(BASE_URL)
          API_KEY: $(API_KEY)
          PLAYWRIGHT_JUNIT_OUTPUT_NAME: $(Build.ArtifactStagingDirectory)/playwright-shard-$(System.JobPositionInPhase).xml

      - task: PublishTestResults@2
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: JUnit
          testResultsFiles: '$(Build.ArtifactStagingDirectory)/playwright-shard-*.xml'
          failTaskOnFailedTests: true

      - task: PublishPipelineArtifact@1
        condition: failed()
        inputs:
          targetPath: playwright-report
          artifact: playwright-report-shard-$(System.JobPositionInPhase)

      - task: PublishPipelineArtifact@1
        condition: failed()
        inputs:
          targetPath: test-results
          artifact: playwright-traces-shard-$(System.JobPositionInPhase)

      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs:
          targetPath: allure-results
          artifact: allure-results-e2e-$(System.JobPositionInPhase)
```

### Vitest API/integration — `pipelines/templates/api-tests.yml`

```yaml
parameters:
  - name: shardCount
    type: number
    default: 2

jobs:
  - job: ApiTests
    pool: { vmImage: ubuntu-latest }
    strategy:
      parallel: ${{ parameters.shardCount }}
    timeoutInMinutes: 25
    steps:
      - checkout: self
      - task: NodeTool@0
        inputs: { versionSpec: $(nodeVersion) }
      - script: npm ci

      - script: docker info
        displayName: Verify Docker (Testcontainers prereq)

      - script: |
          npx vitest run \
            --shard=$(System.JobPositionInPhase)/$(System.TotalJobsInPhase) \
            --reporter=default \
            --reporter=junit \
            --outputFile.junit=reports/junit-api-$(System.JobPositionInPhase).xml
        displayName: Run API tests (shard $(System.JobPositionInPhase))

      - task: PublishTestResults@2
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: JUnit
          testResultsFiles: 'reports/junit-api-*.xml'
          failTaskOnFailedTests: true

      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs:
          targetPath: allure-results
          artifact: allure-results-api-$(System.JobPositionInPhase)
```

### Allure publish with Blob-backed history — `pipelines/templates/allure-publish.yml`

```yaml
jobs:
  - job: AllurePublish
    pool: { vmImage: ubuntu-latest }
    steps:
      - checkout: none
      - download: current
        patterns: 'allure-results-*/**'

      - task: AzureCLI@2
        displayName: Hydrate history from Blob
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
              --auth-mode login --overwrite

      - task: PublishPipelineArtifact@1
        inputs:
          targetPath: allure-report
          artifact: allure-report
```

### k6 perf gate — `pipelines/templates/k6-perf.yml`

```yaml
jobs:
  - job: K6Perf
    pool: { vmImage: ubuntu-latest }
    timeoutInMinutes: 60
    steps:
      - checkout: self
      - script: |
          curl -fsSL https://github.com/grafana/k6/releases/download/v0.52.0/k6-v0.52.0-linux-amd64.tar.gz \
            | tar -xz --strip-components=1 -C /tmp/
          sudo mv /tmp/k6 /usr/local/bin/
        displayName: Install k6 0.52.0 (pinned)
      - script: k6 run --out json=k6-summary.json perf/scenarios/checkout.js
        env: { K6_BASE_URL: $(BASE_URL) }
      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs: { targetPath: k6-summary.json, artifact: k6-summary }
```

## Rules

### Triggers
- `trigger: none` + explicit `pr:` branches. Nightly `schedules` for the full suite.

### Sharding
- Playwright: `--shard=i/N`. Vitest 1.4+: `vitest run --shard=i/N`. Pre-computed bin file for uneven fixtures.
- `strategy: parallel: N` over hand-rolled matrices.

### Secrets
- **OIDC only**. Pull in one `AzureCLI@2` step. Use `issecret=true` for sensitive vars.
- Never echo or log secrets. Never write to a file the artifact step picks up.

### Reporters
- JUnit + Allure on every job. `failTaskOnFailedTests: true` on every `PublishTestResults@2`.

### Retry policy
- No pipeline-level retry. `playwright.config.ts → retries: 0` in CI by default; only enable per-project with a JIRA link in the comment.
- For chronic flakes, quarantine via `qa/reporting/typescript/skills/flaky-test-quarantine`.

### Artifacts
- Traces/videos/HAR: 14 d, **on failure only**.
- JUnit: 30 d. Allure report: 90 d. History in Blob indefinitely.

### Perf gate
- k6 thresholds inline in the script. Pipeline does not interpret metrics — k6 exits 99 → job fails automatically.
- Pin tool version. Upgrade in a dedicated PR.

### What NOT to do
- No `windows-latest` for Linux-container tests.
- No PATs — OIDC only.
- No `continueOnError: true` on test tasks.
- No global `retryCountOnTaskFailure`.
- No printing of `$(MY_SECRET)`.
- No `npm install` (use `npm ci` for reproducible installs).
- No `playwright install` without `--with-deps` (missing system libs → silent crashes).

## Generation steps

1. Read the existing `azure-pipelines.yml` and `package.json` to learn scripts, runners, existing stages.
2. Inventory test projects: Vitest config files, `playwright.config.ts`, `package.json` scripts.
3. Generate:
   - `azure-pipelines.yml` if missing
   - `pipelines/templates/{build,api-tests,integration-tests,playwright,allure-publish,k6-perf}.yml`
4. Wire `sc-qa-oidc` workload-identity-federation service connection with read access to the test Key Vault.
5. Dry-run via `az pipelines run`.

## Cross-references

- **`qa/typescript/skills/db-testing/testcontainers`** — integration-tests stage runs these.
- **`qa/typescript/skills/email-testing`** — Mailpit as a service container.
- **`qa/reporting/typescript/skills/test-reports`** — adapter wiring inside the test project.
- **`qa/typescript/skills/load-testing`** — perf-stage scripts.
- **`devops/azure-pipelines`** — non-QA pipeline patterns.
