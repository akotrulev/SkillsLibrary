# QA — Azure Pipelines for TypeScript Test Suites

Authors `azure-pipelines.yml` for Vitest / Jest / Playwright / k6 suites on Microsoft-hosted Linux agents — sharded, Allure-published, OIDC-authenticated, with proper artifact retention and a hard perf gate.

**The Playwright config is not written here.** `qa/typescript/skills/ui-test-author/playwright/assets/playwright.config.ts` owns it: on CI it writes `blob` (to `blob-report/`), `junit` (to `test-results/junit.xml`) and `allure-playwright` (to `allure-results/`), with `retries: 0`, trace and video `retain-on-failure`, and `updateSnapshots: 'none'`. Azure Pipelines does not set `CI` on its own, so every Playwright step sets `CI: 'true'`. What the evidence is and how to read it is `qa/typescript/skills/evidence-capture`.

## When to use

- New QA pipeline for a TS test project (`api-tests`, `e2e`, `integration`)
- Adding Playwright `--shard=i/N` parallelism
- Wiring Allure publish + history
- Replacing PATs with OIDC federated credentials
- Adding a k6 perf gate that breaks the build on SLO regression

## When NOT to use

- GitHub Actions → `references/github-actions.md` in this skill
- GitLab CI → `references/gitlab-ci.md` in this skill
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
| Node version | 24 (22 maintenance) via `UseNode@1`, pinned by `.nvmrc` | Newer LTS once it's been GA for 3 months |
| Browsers | `npx playwright install --with-deps chromium` | A container job on `mcr.microsoft.com/playwright:v1.64.0-noble` when visual baselines are compared (the tag equals the `@playwright/test` version) |
| Reporter | Vitest: JUnit (`vitest --reporter=junit`) + Allure adapter. Playwright: the config's `blob` + `junit` + `allure-playwright` | Always both; never a `--reporter` override for Playwright |
| Sharding | Playwright `--shard=i/N`; Vitest `vitest --shard` (since 1.4) | Pre-computed bin file when fixtures are uneven |
| Auth | Workload Identity Federation (OIDC) | Never PATs |
| Retry | **Off at pipeline level**; `retries: 0` in the Playwright config (`ci-conventions`) | A documented hotspot `describe` per `flaky-test-quarantine` |
| Artifacts | 14 d failure evidence and merged HTML report, 30 d JUnit, 90 d Allure | Stated reason to bump |
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
    value: '24.x'
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

### Playwright shard + merge — `pipelines/templates/playwright.yml`

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
      - task: UseNode@1
        inputs: { version: $(nodeVersion) }

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
            echo "##vso[task.setvariable variable=E2E_USER;issecret=false]$(az keyvault secret show --vault-name kv-qa --name e2e-user --query value -o tsv)"
            echo "##vso[task.setvariable variable=E2E_PASSWORD;issecret=true]$(az keyvault secret show --vault-name kv-qa --name e2e-password --query value -o tsv)"

      - script: npx playwright test --grep-invert @flaky --shard=$(System.JobPositionInPhase)/$(System.TotalJobsInPhase)
        displayName: Run Playwright tests
        env:
          CI: 'true'
          BASE_URL: $(BASE_URL)
          E2E_USER: $(E2E_USER)
          E2E_PASSWORD: $(E2E_PASSWORD)

      - task: PublishTestResults@2
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: JUnit
          testResultsFiles: 'test-results/junit.xml'
          testRunTitle: Playwright shard $(System.JobPositionInPhase)
          failTaskOnFailedTests: true

      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs:
          targetPath: blob-report
          artifact: blob-report-$(System.JobPositionInPhase)

      - task: PublishPipelineArtifact@1
        condition: failed()
        inputs:
          targetPath: test-results
          artifact: test-results-$(System.JobPositionInPhase)

      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs:
          targetPath: allure-results
          artifact: allure-results-e2e-$(System.JobPositionInPhase)

  - job: MergeReports
    dependsOn: E2E
    condition: succeededOrFailed()
    pool: { vmImage: ubuntu-latest }
    steps:
      - checkout: self
      - task: UseNode@1
        inputs: { version: $(nodeVersion) }
      - script: npm ci
        displayName: Install deps

      - download: current
        patterns: 'blob-report-*/**'

      - script: |
          mkdir -p all-blob-reports
          cp $(Pipeline.Workspace)/blob-report-*/*.zip all-blob-reports/
          npx playwright merge-reports --reporter html ./all-blob-reports
        displayName: Merge shard blobs into one HTML report

      - task: PublishPipelineArtifact@1
        inputs:
          targetPath: playwright-report
          artifact: playwright-report
```

- `PublishTestResults@2` reads `test-results/junit.xml`, the file the config writes on CI; the step never passes `--reporter`, which would replace the config's reporters and drop the blob and Allure output. `failTaskOnFailedTests: true` reds the job on real failures.
- `test-results/` is published **on failure only**: under `retain-on-failure` it holds the trace, video, screenshot and `error-context.md` of each failed test. The merged `playwright-report/` carries the same evidence for every shard, and `MergeReports` runs on red (`succeededOrFailed()`).
- Blob names already carry the shard number, so copying every shard's zip into one folder does not clash.
- `--grep-invert @flaky` keeps quarantined tests off the gate. They run in a separate, non-gating job (`npx playwright test --grep @flaky` with `continueOnError: true`), per `qa/reporting/typescript/skills/flaky-test-quarantine` — a separate job, because each run cleans `test-results/` at its start.
- **Running in the pinned image** instead of installing browsers: add `container: mcr.microsoft.com/playwright:v1.64.0-noble` to the `E2E` job and drop the install step. The tag must equal the `@playwright/test` version, and visual baselines are only compared inside it (`qa/typescript/skills/visual-regression`).

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
      - task: UseNode@1
        inputs: { version: $(nodeVersion) }
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

The report is generated with the one Allure CLI pin, `allure-commandline@2.46.1` (`qa/cicd/ci-conventions`). It needs a Java runtime; the Microsoft-hosted Ubuntu image ships one, a self-hosted agent must provide it.

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
            mkdir -p allure-results/history allure-history
            cp -r $(Pipeline.Workspace)/allure-results-*/. allure-results/
            az storage blob download-batch \
              --account-name $(STORAGE_ACCOUNT) \
              --source allure-history \
              --destination allure-history \
              --auth-mode login || echo "no prior history"
            cp -r allure-history/. allure-results/history/ 2>/dev/null || true

      - script: |
          npm i -g allure-commandline@2.46.1
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
- `trigger: none` + explicit `pr:` branches. Nightly `schedules` for the full suite. The schedule-gated visual step runs `npx playwright test --project=visual` (the `visual` project has `default: false`, so a plain `npx playwright test` skips it) in `mcr.microsoft.com/playwright:v1.64.0-noble`.

### Sharding
- Playwright: `--shard=i/N`. Vitest 1.4+: `vitest run --shard=i/N`. Pre-computed bin file for uneven fixtures.
- `strategy: parallel: N` over hand-rolled matrices.

### Secrets
- **OIDC only**. Pull in one `AzureCLI@2` step. Use `issecret=true` for sensitive vars.
- Never echo or log secrets. Never write to a file the artifact step picks up.

### Reporters
- JUnit + Allure on every job. `failTaskOnFailedTests: true` on every `PublishTestResults@2`.
- Playwright: publish the config's `test-results/junit.xml`, and merge the config's blobs with `npx playwright merge-reports`. Never `--reporter` on the command line.

### Retry policy
- No pipeline-level retry. `retries: 0` in the Playwright config (`qa/cicd/ci-conventions`); a documented network-flake hotspot opts in with `test.describe.configure({ retries: 1 })` on its own `describe`, carrying an `issue` annotation with the link and the date.
- For chronic flakes, quarantine via `qa/reporting/typescript/skills/flaky-test-quarantine`.

### Artifacts
- Failure evidence (`test-results/` per shard, on failure only) and the merged `playwright-report/`: 14 d.
- Blob reports: the shortest retention the pipeline allows; they only feed `MergeReports`.
- JUnit: 30 d. Allure report: 90 d. History in Blob indefinitely.

### Perf gate
- k6 thresholds inline in the script. Pipeline does not interpret metrics — k6 exits 99 → job fails automatically.
- Pin tool version. Upgrade in a dedicated PR.

### What NOT to do
- No `windows-latest` for Linux-container tests.
- No PATs — OIDC only.
- No `continueOnError: true` on gating test tasks (the quarantine job is the one non-gating exception).
- No global `retryCountOnTaskFailure`.
- No printing of `$(MY_SECRET)`.
- No `npm install` (use `npm ci` for reproducible installs).
- No `playwright install` without `--with-deps` (missing system libs → silent crashes), and no Playwright image tag that differs from the package version.
- No `--reporter`, `--trace` or `--update-snapshots` on the Playwright command line — the config owns all three.

## Generation steps

1. Read the existing `azure-pipelines.yml` and `package.json` to learn scripts, runners, existing stages.
2. Inventory test projects: Vitest config files, `playwright.config.ts`, `package.json` scripts. The Playwright config comes from `qa/typescript/skills/ui-test-author/playwright/assets/playwright.config.ts`.
3. Generate:
   - `azure-pipelines.yml` if missing
   - `pipelines/templates/{build,api-tests,integration-tests,playwright,allure-publish,k6-perf}.yml`
4. Wire `sc-qa-oidc` workload-identity-federation service connection with read access to the test Key Vault.
5. Dry-run via `az pipelines run`.

## Cross-references

- **`qa/typescript/skills/ui-test-author/playwright`** — owns `assets/playwright.config.ts`, the config this pipeline runs.
- **`qa/typescript/skills/evidence-capture`** — what lands in `test-results/` and `playwright-report/`, and how to read a downloaded trace.
- **`qa/typescript/skills/db-testing/testcontainers`** — integration-tests stage runs these.
- **`qa/typescript/skills/email-testing`** — Mailpit as a service container.
- **`qa/reporting/typescript/skills/test-reports`** — adapter wiring inside the test project.
- **`qa/reporting/typescript/skills/flaky-test-quarantine`** — the `@flaky` tag the gate excludes, and the non-gating quarantine job.
- **`qa/typescript/skills/load-testing`** — perf-stage scripts.
- **`qa/cicd/ci-conventions`** — cross-stack rules (artifact retention, OIDC, the Allure CLI pin) this skill enforces.
- **`devops/azure-pipelines`** — non-QA pipeline patterns.
