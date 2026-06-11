# QA — Azure Pipelines for Java Test Suites

Authors `azure-pipelines.yml` for Gradle + TestNG suites (per CLAUDE.md defaults) on Microsoft-hosted Linux agents — sharded by TestNG groups or split-test files, Allure-published with history, OIDC-authenticated, with hard perf gates.

## When to use

- New QA pipeline for a Java test module (`api-tests`, `e2e`, `integration-tests`)
- Adding TestNG group sharding or parallel `<test>` blocks
- Allure publish + history
- OIDC federated credentials replacing PATs
- Gatling perf gate that breaks the build on SLO regression

## When NOT to use

- GitHub Actions → `qa/java/skills/ci-pipelines`
- GitLab CI → `qa/java/skills/ci-pipelines`
- App build / deploy → `devops/azure-pipelines`
- .NET / TS stacks — see siblings

## Inputs needed

1. Suites in scope? (API / integration / UI / perf)
2. Sharding fan-out? (default 4 for Selenium UI, 2 for API/integration, 1 for Gatling)
3. Allure history storage? (cache short-term; Azure Blob cross-pipeline)

## Decision matrix

| Concern | Default | Override when |
|---|---|---|
| Agent pool | `ubuntu-latest` | Self-hosted only for proprietary hardware |
| JDK | Temurin 21, pinned via Gradle `toolchain` | Newer LTS after 3 mo GA |
| Build tool | **Gradle Kotlin DSL** (CLAUDE.md default) | Maven only for legacy modules |
| Reporter | TestNG XML → JUnit conversion via Gradle + Allure-TestNG adapter | Always both |
| Sharding | TestNG groups split across jobs OR `--tests` file pre-computed | `splitBy=testClasses` for evenly-balanced suites |
| Auth | Workload Identity Federation (OIDC) | Never PATs |
| Retry | **Off at pipeline level** | TestNG `@Test(retryAnalyzer=...)` only for documented network flakes |
| Artifacts | 14 d screenshots/HAR, 30 d test-results, 90 d Allure | Stated reason to bump |
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
      - template: pipelines/templates/selenium.yml
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

Wire the shard params in `build.gradle.kts`:

```kotlin
tasks.named<Test>("test") {
    useTestNG {
        val total = (project.findProperty("shardTotal") as String?)?.toIntOrNull() ?: 1
        val index = (project.findProperty("shardIndex") as String?)?.toIntOrNull() ?: 0
        if (total > 1) {
            // Pre-computed group list, or simple modulo on test names
            includeGroups = setOf("shard-$index-of-$total")
        }
    }
}
```

For uneven suites, pre-compute a shard map and commit it under `api-tests/shards/`.

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

### Selenium UI shard

```yaml
parameters:
  - name: shardCount
    type: number
    default: 4

jobs:
  - job: UiTests
    pool: { vmImage: ubuntu-latest }
    strategy:
      parallel: ${{ parameters.shardCount }}
    timeoutInMinutes: 45
    steps:
      - checkout: self
      - task: JavaToolInstaller@0
        inputs: { versionSpec: $(javaVersion), jdkArchitectureOption: x64, jdkSourceOption: PreInstalled }
      - script: |
          ./gradlew :e2e:test \
            -PshardIndex=$(System.JobPositionInPhase) \
            -PshardTotal=$(System.TotalJobsInPhase) \
            -Pheadless=true \
            --no-daemon
      - task: PublishPipelineArtifact@1
        condition: failed()
        inputs:
          targetPath: e2e/build/screenshots
          artifact: ui-screenshots-shard-$(System.JobPositionInPhase)
      - task: PublishTestResults@2
        condition: succeededOrFailed()
        inputs:
          testResultsFormat: JUnit
          testResultsFiles: 'e2e/build/test-results/test/TEST-*.xml'
          failTaskOnFailedTests: true
```

### Allure publish — same pattern as `dotnet` sibling

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

### Sharding
- TestNG groups pre-assigned in code (`@Test(groups = "shard-0-of-4")`) is the most predictable approach.
- For uneven suites, commit a `shards.txt` mapping test → shard index.
- `strategy: parallel: N` over hand-rolled matrices.

### Secrets
- **OIDC only** via Workload Identity Federation. No PATs.
- Single `AzureCLI@2` step to pull secrets. `issecret=true` for sensitive vars.
- Never log secrets. Never write to a path the artifact step picks up.

### Reporters
- JUnit-XML from TestNG (`useTestNG()` Gradle config emits it under `build/test-results/test/`) feeds `PublishTestResults@2`.
- Allure-TestNG adapter writes `allure-results/`. Publish per shard.
- `failTaskOnFailedTests: true` on every `PublishTestResults@2`.

### Retry policy
- No pipeline-level retry. TestNG `IRetryAnalyzer` per-test only with a JIRA link in the annotation.
- For chronic flakes, quarantine via `qa/java/skills/flaky-test-quarantine`.

### Artifacts
- Screenshots / HAR: 14 d, on failure only.
- Test results: 30 d. Allure report: 90 d. History in Blob indefinitely.

### Perf gate
- Gatling assertions in the simulation. Exit code is non-zero on breach → job fails automatically.
- Pin Gatling version in `build.gradle.kts`. Upgrade in a dedicated PR.

### What NOT to do
- No `windows-latest` for Linux-container tests.
- No PATs.
- No `continueOnError: true` on test tasks.
- No `--rerun-tasks` on Gradle to "fix" failures.
- No printing of `$(MY_SECRET)`.
- No `./gradlew test` without `--no-daemon` in CI (daemon survives between jobs unpredictably).
- No mixing of Maven and Gradle in the same module.

## Generation steps

1. Read existing `settings.gradle.kts` + `build.gradle.kts` + any `azure-pipelines.yml`.
2. Inventory modules: `api-tests`, `integration-tests`, `e2e`, `perf`.
3. Generate:
   - `azure-pipelines.yml` if missing.
   - `pipelines/templates/{build,api-tests,integration-tests,selenium,allure-publish,gatling-perf}.yml`
4. Wire `sc-qa-oidc` workload-identity-federation service connection.
5. Dry-run via `az pipelines run`.

## Cross-references

- **`qa/java/skills/db-testing/testcontainers`** — integration-tests stage runs these.
- **`qa/java/skills/email-testing`** — Mailpit as a service container.
- **`qa/java/skills/allure-reporting`** — Allure-TestNG adapter wiring inside test modules.
- **`qa/java/skills/performance/gatling`** — perf-stage simulations.
- **`devops/azure-pipelines`** — non-QA pipeline patterns.
