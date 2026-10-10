# QA — Azure Pipelines for Java Test Suites

Authors `azure-pipelines.yml` for Gradle + TestNG suites (per CLAUDE.md defaults) on Microsoft-hosted Linux agents — RestAssured API tests, Testcontainers integration tests and Playwright-for-Java (or Selenium) UI tests, sharded by TestNG groups, Allure-published with history, OIDC-authenticated, with hard perf gates.

**The UI lifecycle is not written here.** `qa/java/skills/ui-test-author/playwright/assets/BaseTest.java` owns it: it reads `BASE_URL` (required), runs headless unless `HEADED=1`, and on a failed test keeps a full-page screenshot, the trace and the video in `build/playwright-artifacts/<Class>.<method>.{png,zip,webm}`. The pipeline runs that as is and publishes exactly that folder. `build/playwright-videos/` holds raw recordings `BaseTest` deletes after every test; it is never published. What the evidence is and how to read it is `qa/java/skills/evidence-capture`.

## When to use

- New QA pipeline for a Java test module (`api-tests`, `e2e`, `integration-tests`)
- Adding TestNG group sharding
- A Playwright-for-Java UI job with failure evidence
- Allure publish + history
- OIDC federated credentials replacing PATs
- Gatling perf gate that breaks the build on SLO regression

## When NOT to use

- GitHub Actions → `references/github-actions.md` in this skill
- GitLab CI → `references/gitlab-ci.md` in this skill
- App build / deploy → `devops/azure-pipelines`
- .NET / TS stacks — see siblings

## Inputs needed

1. Suites in scope? (API / integration / UI / perf)
2. Sharding fan-out? (default 4 for UI, 2 for API/integration, 1 for Gatling)
3. Allure history storage? (cache short-term; Azure Blob cross-pipeline)

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Agent pool | `ubuntu-latest` (passwordless `sudo`, JDK 21 preinstalled) | Self-hosted only for proprietary hardware |
| JDK | Temurin 21, pinned via Gradle `toolchain`; `JavaToolInstaller@0` selects the preinstalled 21 | Newer LTS after 3 mo GA |
| Build tool | **Gradle Kotlin DSL** (CLAUDE.md default) | Maven only for legacy modules |
| Playwright browsers | `./gradlew :e2e:installPlaywrightBrowsers` (J1's `JavaExec` task: `install --with-deps chromium`) | The pinned image `mcr.microsoft.com/playwright/java:v1.63.0-noble` for visual baselines (see the UI job) |
| Reporter | TestNG XML → JUnit via Gradle + Allure-TestNG adapter | Always both |
| Sharding | TestNG groups pre-assigned per class, selected with `-PshardIndex/-PshardTotal` | A committed shard map for uneven suites |
| Auth | Workload Identity Federation (OIDC) | Never PATs |
| Retry | **Off at pipeline level** | `@Test(retryAnalyzer = RetryOnce.class)` only on a documented network-flake hotspot |
| Artifacts | `build/playwright-artifacts/` on failure only, test results and Allure results always | Stated reason to bump retention |
| Perf gate | Gatling assertions → non-zero exit → job fails | Soft only while baselining |

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
  - name: javaVersion
    value: '21'
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

  - stage: UiTests
    dependsOn: Build
    jobs:
      - template: pipelines/templates/playwright-ui.yml
        parameters: { shardCount: 4 }

  - stage: Perf
    dependsOn: ApiTests
    condition: and(succeeded(), eq(variables['Build.Reason'], 'Schedule'))
    jobs:
      - template: pipelines/templates/gatling-perf.yml

  - stage: PublishReports
    dependsOn: [ApiTests, IntegrationTests, UiTests]
    condition: always()
    jobs:
      - template: pipelines/templates/allure-publish.yml
```

### Sharded TestNG API job — `pipelines/templates/api-tests.yml`

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
    timeoutInMinutes: 30
    steps:
      - checkout: self

      - task: JavaToolInstaller@0
        inputs:
          versionSpec: $(javaVersion)
          jdkArchitectureOption: x64
          jdkSourceOption: PreInstalled

      - task: Gradle@3
        displayName: Gradle build (skip tests)
        inputs:
          gradleWrapperFile: gradlew
          tasks: 'build -x test'
          options: '--no-daemon'

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
          ./gradlew :api-tests:test \
            -PshardIndex=$(System.JobPositionInPhase) \
            -PshardTotal=$(System.TotalJobsInPhase) \
            --no-daemon
        displayName: Run API tests (shard $(System.JobPositionInPhase))
        env:
          API_BASE_URL: $(API_BASE_URL)
          AUTH0_M2M_SECRET: $(AUTH0_M2M_SECRET)

      - task: PublishTestResults@2
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: JUnit
          testResultsFiles: 'api-tests/build/test-results/test/TEST-*.xml'
          failTaskOnFailedTests: true

      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs:
          targetPath: api-tests/build/allure-results
          artifact: allure-results-api-$(System.JobPositionInPhase)
```

Wire the shard params in the module's `build.gradle.kts`:

```kotlin
tasks.test {
    val total = (project.findProperty("shardTotal") as String?)?.toInt() ?: 1
    val index = (project.findProperty("shardIndex") as String?)?.toInt() ?: 1
    useTestNG {
        suites("testng.xml")
        excludeGroups("flaky")
        if (total > 1) {
            includeGroups("shard-$index-of-$total")
        }
    }
}
```

`System.JobPositionInPhase` is 1-based, like the groups (`shard-1-of-4` … `shard-4-of-4`), pre-assigned per test class. For uneven suites, pre-compute a shard map and commit it under `api-tests/shards/`. `excludeGroups("flaky")` keeps quarantined tests off the gate (`qa/reporting/java/skills/flaky-test-quarantine`).

### Integration with Testcontainers

```yaml
jobs:
  - job: IntegrationTests
    pool: { vmImage: ubuntu-latest }
    timeoutInMinutes: 25
    steps:
      - checkout: self
      - task: JavaToolInstaller@0
        inputs: { versionSpec: $(javaVersion), jdkArchitectureOption: x64, jdkSourceOption: PreInstalled }
      - script: docker info
        displayName: Verify Docker (Testcontainers prereq)
      - script: ./gradlew :integration-tests:test --no-daemon
      - task: PublishTestResults@2
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: JUnit
          testResultsFiles: 'integration-tests/build/test-results/test/TEST-*.xml'
          failTaskOnFailedTests: true
```

### Playwright-for-Java UI shard — `pipelines/templates/playwright-ui.yml`

```yaml
parameters:
  - name: shardCount
    type: number
    default: 4

jobs:
  - job: PlaywrightUi
    pool: { vmImage: ubuntu-latest }
    strategy:
      parallel: ${{ parameters.shardCount }}
    timeoutInMinutes: 45
    steps:
      - checkout: self

      - task: JavaToolInstaller@0
        inputs: { versionSpec: $(javaVersion), jdkArchitectureOption: x64, jdkSourceOption: PreInstalled }

      - script: ./gradlew :e2e:installPlaywrightBrowsers --no-daemon
        displayName: Install Playwright browsers + OS deps

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
          ./gradlew :e2e:test \
            -PshardIndex=$(System.JobPositionInPhase) \
            -PshardTotal=$(System.TotalJobsInPhase) \
            --no-daemon
        displayName: Run UI tests (shard $(System.JobPositionInPhase))
        env:
          BASE_URL: $(BASE_URL)
          E2E_USER: $(E2E_USER)
          E2E_PASSWORD: $(E2E_PASSWORD)

      - task: PublishTestResults@2
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: JUnit
          testResultsFiles: 'e2e/build/test-results/test/TEST-*.xml'
          failTaskOnFailedTests: true

      - task: PublishPipelineArtifact@1
        displayName: Publish failure evidence
        condition: failed()
        inputs:
          targetPath: e2e/build/playwright-artifacts
          artifact: playwright-artifacts-$(System.JobPositionInPhase)

      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs:
          targetPath: e2e/build/allure-results
          artifact: allure-results-ui-$(System.JobPositionInPhase)
```

- **No headless flag.** `BaseTest` is headless unless `HEADED=1`, which only a local run sets; `-Pheadless` or `-Dplaywright.headless` is read by nothing.
- `installPlaywrightBrowsers` passes `--with-deps`, which installs OS packages through the agent's passwordless `sudo`. Browsers are pinned per Playwright version, so the 1.63.0 binding installs its own Chromium build.
- `BASE_URL`, `E2E_USER` and `E2E_PASSWORD` come through OIDC (`issecret=true` masks the password and keeps it out of the environment unless mapped in `env:`). `BaseTest` throws without `BASE_URL`, and the sign-in `@BeforeSuite` needs the account.
- `e2e/build/playwright-artifacts` is published **on failure only**: the screenshot, trace and video of each failed test, plus any deliberate recording. Pipeline artifacts follow the project's retention policy; set it to keep failure evidence 14 days (`qa/cicd/ci-conventions`).
- The quarantine lane is a second job with the same steps running `./gradlew :e2e:flakyQuarantine --no-daemon` and `continueOnError: true` — the one non-gating exception (`qa/reporting/java/skills/flaky-test-quarantine`).
- **Selenium** suites use the same job shape without the install step; `ubuntu-latest` ships Chrome and its driver.
- **Running in the pinned image** instead of installing browsers — what visual baselines need (`qa/java/skills/visual-regression`): a container job (`container: mcr.microsoft.com/playwright/java:v1.63.0-noble`) without the install step; the tag must equal the Playwright version. The image ships OpenJDK 25, Maven and the browsers, but no JDK 21, no `sudo` and no Azure CLI, so the build's Java 21 toolchain and the credential fetch both need work the agent route does not; prefer the agent route for everything but the visual job.

### Allure publish — `pipelines/templates/allure-publish.yml`

The report is generated with the one Allure CLI pin, `allure-commandline@2.46.1` (`qa/cicd/ci-conventions`), which reads allure-java 3.0 results; the hosted agent carries both Node and a Java runtime.

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
            cp -r $(Pipeline.Workspace)/allure-results-*/. allure-results/ 2>/dev/null || true
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
              --auth-mode login --overwrite

      - task: PublishPipelineArtifact@1
        inputs: { targetPath: allure-report, artifact: allure-report }
```

### Gatling perf gate

```yaml
jobs:
  - job: GatlingPerf
    pool: { vmImage: ubuntu-latest }
    timeoutInMinutes: 60
    steps:
      - checkout: self
      - task: JavaToolInstaller@0
        inputs: { versionSpec: $(javaVersion), jdkArchitectureOption: x64, jdkSourceOption: PreInstalled }
      - script: ./gradlew :perf:gatlingRun --no-daemon
        displayName: Run Gatling (assertions enforce SLOs; non-zero exit on breach)
        env:
          GATLING_BASE_URL: $(API_BASE_URL)
      - task: PublishPipelineArtifact@1
        condition: succeededOrFailed()
        inputs:
          targetPath: perf/build/reports/gatling
          artifact: gatling-report
```

## Rules

### Triggers
- `trigger: none` + explicit `pr:` branches. Nightly schedule for the full suite.
- Visual regression and perf run on the schedule only (`eq(variables['Build.Reason'], 'Schedule')`).

### Sharding
- TestNG groups pre-assigned per class (`@Test(groups = "shard-1-of-4")`), 1-based to match `System.JobPositionInPhase`, is the most predictable approach.
- For uneven suites, commit a `shards.txt` mapping test → shard index.
- `strategy: parallel: N` over hand-rolled matrices.
- UI classes run in parallel inside a shard through `testng.xml`'s `parallel="classes"` (J1's asset); never `parallel="methods"` with Playwright.

### Secrets
- **OIDC only** via Workload Identity Federation. No PATs.
- Single `AzureCLI@2` step to pull secrets. `issecret=true` for sensitive vars, mapped explicitly in `env:`.
- Never log secrets. Never write to a path the artifact step picks up. Traces and videos record what the page shows, so tests run as a disposable test user.

### Reporters
- JUnit-XML from TestNG (`useTestNG()` Gradle config emits it under `build/test-results/test/`) feeds `PublishTestResults@2`.
- Allure-TestNG adapter writes `build/allure-results/`. Publish per shard.
- `failTaskOnFailedTests: true` on every `PublishTestResults@2`.

### Retry policy
- No pipeline-level retry. `@Test(retryAnalyzer = RetryOnce.class)` only on a documented network-flake hotspot, dated and linked to an issue at the test.
- For chronic flakes, quarantine via `qa/reporting/java/skills/flaky-test-quarantine`.

### Artifacts
- `build/playwright-artifacts/` (screenshots, traces, videos, deliberate recordings): on failure only, 14 days by retention policy. Never `build/playwright-videos/`.
- Test results and Allure results: always; 30 d. Allure report: 90 d. History in Blob indefinitely.

### Perf gate
- Gatling assertions in the simulation. Exit code is non-zero on breach → job fails automatically.
- Pin Gatling version in `build.gradle.kts`. Upgrade in a dedicated PR.

### What NOT to do
- No `windows-latest` for Linux-container tests.
- No PATs.
- No `continueOnError: true` on a gating test task (the quarantine job is the one exception).
- No `--rerun-tasks` on Gradle to "fix" failures.
- No `-Pheadless` / `-Dplaywright.headless` — nothing reads them.
- No `e2e/build/screenshots` path — no skill writes it; the evidence folder is `build/playwright-artifacts/`.
- No printing of `$(MY_SECRET)`.
- No `./gradlew test` without `--no-daemon` in CI (daemon survives between jobs unpredictably).
- No mixing of Maven and Gradle in the same module.

## Generation steps

1. Read existing `settings.gradle.kts` + `build.gradle.kts` + any `azure-pipelines.yml`. Confirm the UI module builds on J1's `build.gradle.kts` (the `installPlaywrightBrowsers` task) and `BaseTest`.
2. Inventory modules: `api-tests`, `integration-tests`, `e2e`, `perf`.
3. Generate:
   - `azure-pipelines.yml` if missing.
   - `pipelines/templates/{build,api-tests,integration-tests,playwright-ui,allure-publish,gatling-perf}.yml`
4. Wire `sc-qa-oidc` workload-identity-federation service connection.
5. Dry-run via `az pipelines run`.

## Cross-references

- **`qa/java/skills/ui-test-author/playwright`** — `BaseTest`, `build.gradle.kts` (`installPlaywrightBrowsers`, `playwright`) and `testng.xml` the UI job runs.
- **`qa/java/skills/evidence-capture`** — what `build/playwright-artifacts/` holds and how to read a failure's trace.
- **`qa/java/skills/db-testing/testcontainers`** — integration-tests stage runs these.
- **`qa/java/skills/email-testing`** — Mailpit as a service container.
- **`qa/reporting/java/skills/test-reports`** — Allure-TestNG adapter wiring inside test modules.
- **`qa/reporting/java/skills/flaky-test-quarantine`** — the `flaky` group the gate excludes and the quarantine task.
- **`qa/java/skills/load-testing`** — perf-stage simulations.
- **`qa/cicd/ci-conventions`** — cross-stack rules (artifact retention, OIDC, the Allure CLI pin) this skill enforces.
- **`devops/azure-pipelines`** — non-QA pipeline patterns.
