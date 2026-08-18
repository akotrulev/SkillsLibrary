---
name: devops-azure-pipelines
description: Use when the user asks to write, review, or modify Azure DevOps YAML pipelines (`azure-pipelines.yml`) for build/test/deploy of Java, .NET, or TypeScript projects. Triggers: "write an Azure Pipelines YAML for X", "add a stage to my pipeline", "set up Azure DevOps CI". Do NOT use for GitHub Actions (`devops/github-actions`), GitLab CI (`devops/gitlab-ci`), or IaC (`devops/infrastructure-as-code`). Do NOT use for the test-suite CI lane — `qa-cicd-{java,dotnet,typescript}` owns that.
---

# DevOps — Azure Pipelines

Authors Azure DevOps YAML pipelines for build, test, and deploy across the project's stacks (Java 21 / .NET 10 primary with 8/9 supported / Node 24 LTS) and target clouds (AWS, Azure). Standardizes on multi-stage pipelines, template reuse, environment approvals, and Azure Service Connections (Workload Identity Federation — OIDC, not service principal secrets).

**Version policy:** detect the project's versions (TFM / `engines` / toolchain) and match — never assume. .NET 10 is primary, 8/9 supported (8 LTS ends Nov 2026). Node 20 is EOL (Apr 2026) — 24 is active LTS, 22 maintenance. Java 21 LTS is the default. Never put a job on a newer SDK/runtime than the project targets.

## When to use

- New Azure DevOps project needs `azure-pipelines.yml`
- Add a deploy stage to an existing pipeline
- Migrate a classic UI build to YAML
- Extract repeated job logic into pipeline templates
- Add Environment-gated approvals or checks

## When NOT to use

- GitHub Actions → `devops/github-actions`
- GitLab CI/CD → `devops/gitlab-ci`
- Bicep / Terraform authoring → `devops/infrastructure-as-code`
- App-level env config → `devops/environment-config`

- Test-suite CI lane (shard matrix, Allure publish, perf gate, flake quarantine) → `qa/cicd/agents/qa-cicd-{java,dotnet,typescript}`
## Inputs needed

1. **Stack(s)**: .NET 10 (8/9 supported) / Java 21 + Gradle / Node 24 (22 maintenance) + which package manager
2. **Target cloud**: Azure (App Service, Container Apps, AKS, Static Web Apps, Functions) or AWS (ECS, Lambda, S3+CloudFront, EKS)
3. **Agent pool**: Microsoft-hosted (`ubuntu-latest`, `windows-latest`) or self-hosted (which pool/demands?)
4. **Trigger model**: branch CI (`main`, `release/*`), PR validation, tag, scheduled, manual
5. **Environments**: dev / test / prod and which need approvals or branch-control checks
6. **Service connections** available: Azure RM (Workload Identity / WIF preferred), AWS, Docker registry
7. **Variable groups / Key Vault**: where secrets live

## Standard pipeline shape

Multi-stage pipeline: `Build` → `Test` → `Deploy_Dev` → `Deploy_Prod`. Each stage runs only when its predecessors succeed; deploys target an Environment that owns the approval.

```yaml
trigger:
  branches: { include: [main, 'release/*'] }
pr:
  branches: { include: [main] }

# Avoid redundant runs from a PR + the push that opens it
pool:
  vmImage: ubuntu-latest

variables:
  - group: shared-config           # non-secret group
  - group: shared-secrets-kv       # variable group linked to Key Vault
  - name: buildConfiguration
    value: Release

stages:
- stage: Build
  jobs: [...]

- stage: Test
  dependsOn: Build
  jobs: [...]

- stage: Deploy_Dev
  dependsOn: Test
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  jobs:
  - deployment: deploy
    environment: dev
    strategy:
      runOnce:
        deploy:
          steps: [...]

- stage: Deploy_Prod
  dependsOn: Deploy_Dev
  condition: and(succeeded(), startsWith(variables['Build.SourceBranch'], 'refs/heads/release/'))
  jobs:
  - deployment: deploy
    environment: prod   # approval lives on this Environment
    strategy:
      runOnce:
        deploy:
          steps: [...]
```

Approval gates live on the **Environment** (Pipelines → Environments → Approvals & checks). The YAML stays clean; the approval policy stays auditable in one place.

## Per-stack build/test jobs

### .NET (10 primary; match the project's TFM)

```yaml
- stage: Build
  jobs:
  - job: build
    steps:
    - task: UseDotNet@2
      inputs: { packageType: sdk, version: '10.0.x' }   # match the TFM: '8.0.x' / '9.0.x' down-level

    - task: Cache@2
      inputs:
        key: 'nuget | "$(Agent.OS)" | **/packages.lock.json,**/*.csproj'
        path: $(NUGET_PACKAGES)
      displayName: Cache NuGet

    - script: dotnet restore --locked-mode
      displayName: Restore

    - script: dotnet build --configuration $(buildConfiguration) --no-restore
      displayName: Build

    - script: dotnet test --configuration $(buildConfiguration) --no-build --logger "trx" --collect:"XPlat Code Coverage" --results-directory $(Agent.TempDirectory)/TestResults
      displayName: Test

    - task: PublishTestResults@2
      condition: succeededOrFailed()
      inputs:
        testResultsFormat: VSTest
        testResultsFiles: '**/*.trx'
        searchFolder: $(Agent.TempDirectory)/TestResults
        mergeTestResults: true

    - task: PublishCodeCoverageResults@2
      condition: succeededOrFailed()
      inputs:
        summaryFileLocation: $(Agent.TempDirectory)/TestResults/**/coverage.cobertura.xml
```

`--locked-mode` requires `packages.lock.json` to be committed — that's a feature, not friction. `condition: succeededOrFailed()` so test results publish even on a build failure.

### Java 21 + Gradle

```yaml
- stage: Build
  jobs:
  - job: build
    steps:
    - task: JavaToolInstaller@0
      inputs: { versionSpec: '21', jdkArchitectureOption: x64, jdkSourceOption: PreInstalled }

    - task: Cache@2
      inputs:
        key: 'gradle | "$(Agent.OS)" | **/build.gradle*,**/gradle-wrapper.properties'
        path: $(HOME)/.gradle/caches
      displayName: Cache Gradle

    - task: Gradle@3
      inputs:
        gradleWrapperFile: gradlew
        tasks: 'build --no-daemon'
        publishJUnitResults: true
        testResultsFiles: '**/build/test-results/test/TEST-*.xml'
        codeCoverageToolOption: JaCoCo
        codeCoverageClassFilesDirectories: 'build/classes/java/main'
```

The `Gradle@3` task auto-publishes JUnit + JaCoCo — don't reinvent that with manual `PublishTestResults@2` unless you need it.

### Node 24 + pnpm (TypeScript)

```yaml
- stage: Build
  jobs:
  - job: build
    steps:
    - task: NodeTool@0
      inputs: { versionSpec: '24.x' }   # 22.x for maintenance LTS; 20 is EOL

    - script: |
        corepack enable
        corepack prepare --activate   # version from package.json `packageManager` — don't double-pin
      displayName: Enable pnpm

    - task: Cache@2
      inputs:
        key: 'pnpm | "$(Agent.OS)" | pnpm-lock.yaml'
        path: $(Pipeline.Workspace)/.pnpm-store
      displayName: Cache pnpm store

    - script: |
        pnpm config set store-dir $(Pipeline.Workspace)/.pnpm-store
        pnpm install --frozen-lockfile
      displayName: Install

    - script: pnpm tsc --noEmit
      displayName: Type-check

    - script: pnpm test --reporter=junit --outputFile=$(Agent.TempDirectory)/junit.xml
      displayName: Test

    - task: PublishTestResults@2
      condition: succeededOrFailed()
      inputs:
        testResultsFormat: JUnit
        testResultsFiles: $(Agent.TempDirectory)/junit.xml
```

## Matrix builds

```yaml
- job: test
  strategy:
    matrix:
      linux:
        imageName: ubuntu-latest
      windows:
        imageName: windows-latest
    maxParallel: 2
  pool:
    vmImage: $(imageName)
  steps: [...]
```

`maxParallel` keeps the concurrent agent count under what the org licenses.

## Cloud auth — Workload Identity (OIDC), not secrets

### Azure (Workload Identity Federation)

Create the Service Connection as **Azure Resource Manager → Workload Identity federation (automatic)** in Project Settings → Service connections. The connection issues short-lived tokens via OIDC.

```yaml
- task: AzureCLI@2
  inputs:
    azureSubscription: 'azure-sc-prod'   # WIF service connection name
    scriptType: bash
    scriptLocation: inlineScript
    inlineScript: |
      az webapp deploy --resource-group $(RG) --name $(APP) --src-path ./publish.zip --type zip
```

Never create a service principal + secret manually and stash it in a variable group. WIF removes the secret entirely.

### AWS (OIDC via AssumeRoleWithWebIdentity)

Use the **AWS Toolkit for Azure DevOps** extension; configure the AWS service connection as OIDC.

```yaml
- task: AWSShellScript@1
  inputs:
    awsCredentials: 'aws-sc-prod'      # OIDC service connection name
    regionName: eu-west-1
    scriptType: inline
    inlineScript: |
      aws ecs update-service --cluster $(CLUSTER) --service $(SERVICE) --force-new-deployment
```

The IAM role's trust policy scopes `sub` to `<org>/<project>:environment:<env>` — never `*`.

## Deployment jobs vs regular jobs

For anything that touches an Environment, use a **`deployment:` job**, not `job:`. Only `deployment:` jobs trigger Environment approvals, deployment history, and per-environment checks.

```yaml
- stage: Deploy_Prod
  jobs:
  - deployment: deploy
    environment: prod        # this is what the approval is attached to
    strategy:
      runOnce:
        deploy:
          steps: [...]
```

Strategies:
- `runOnce` — simplest, what most stages need
- `rolling` — for VM scale sets / multi-instance rollouts
- `canary` — for percentage-based releases (rare unless infra supports it)

## Templates (reuse)

### Local template

```yaml
# templates/dotnet-build.yml
parameters:
- name: configuration
  type: string
  default: Release
steps:
- task: UseDotNet@2
  inputs: { packageType: sdk, version: '10.0.x' }   # match the project's TFM
- script: dotnet build --configuration ${{ parameters.configuration }}
```

Caller:

```yaml
steps:
- template: templates/dotnet-build.yml
  parameters:
    configuration: Release
```

### Cross-repo template (recommended for 3+ pipelines)

```yaml
resources:
  repositories:
  - repository: templates
    type: git
    name: platform/ci-templates
    ref: refs/tags/v1.4.0

stages:
- template: dotnet-ci.yml@templates
```

Pin the `ref:` to a tag. A change in the templates repo should be a deliberate consumer update.

## Variables, variable groups, and Key Vault

- **Inline `variables:`** — non-secret, per-pipeline values (e.g., `buildConfiguration`)
- **Variable groups** (Library → Variable groups) — shared, non-secret config; mark sensitive values as secret
- **Key Vault-backed variable groups** — preferred for secrets; values are pulled at runtime, masked in logs, and rotated in one place
- **Pipeline secrets** — only when a value is truly per-pipeline and not appropriate for KV

Never define a secret in `variables:` at the top of the YAML (it leaks into every step's env).

## Allure reporting

Publish the raw results as a pipeline artifact here; the **report generation/publishing pipeline belongs to the QA domain** — `qa/cicd/<stack>/skills/ci-pipelines` (Allure-publish step) and `qa/reporting/<stack>` own it. Don't wire a third-party Allure publishing task into an app-deploy pipeline.

```yaml
- task: PublishPipelineArtifact@1
  condition: always()
  inputs:
    targetPath: allure-results
    artifact: allure-results

- task: PublishTestResults@2      # native Azure DevOps test tab
  condition: always()
  inputs: { testResultsFormat: JUnit, testResultsFiles: '**/test-results.xml' }
```

## Rules

- Multi-stage with explicit `dependsOn:` — don't conflate `Build`, `Test`, and `Deploy`
- One `deployment:` job per target environment; approvals live on the Environment, not in YAML
- Pin all task versions explicitly (`UseDotNet@2`, `Cache@2`, `AzureCLI@2`) — `@*` floats
- Pin language versions to what the project targets (`10.0.x`, `21`, `24.x`); take the pnpm version from `package.json` `packageManager` via `corepack prepare --activate` — never double-pin it in CI
- Use `Cache@2` keyed on lockfile content — sticky caches mask broken installs
- `condition: succeededOrFailed()` on result-publishing tasks so failed builds still upload reports
- Service connections use Workload Identity Federation (Azure) / OIDC (AWS) — no service principal secrets
- Self-hosted agents use `demands:` to ensure the right capabilities; never run prod deploys on a shared default pool
- Every step has a clear `displayName:` — anonymous steps in a 200-line log are unreadable
- Variable groups link to Key Vault for secrets; YAML never references plaintext credentials

## What NOT to do

- No service principal client secret in a variable group when WIF is available — migrate the service connection
- No `vmImage: ubuntu-latest` for prod deploys requiring network reach into a private VNet — use a self-hosted agent
- No `condition: always()` on deploy steps — it bypasses upstream failure
- No `dependsOn:` chains that flatten parallelism (`B dependsOn A, C dependsOn B` when `C` only really needs `A`)
- No `${{ }}` template expressions in places that need runtime values (`$( )` for runtime, `${{ }}` for compile-time)
- No `script:` block longer than ~10 lines — extract to `scripts/*.sh` / `*.ps1` and call them
- No `continueOnError: true` to hide a flaky step — fix or quarantine
- No `displayName:` left as the default task title — name what it does in context
- No mixing of classic build definitions and YAML in the same project — migrate fully, the dual model produces accidents
- No `dotnet restore` without `--locked-mode` if a lockfile exists — defeats the purpose of the lockfile

## Generation steps

1. Confirm stacks, target cloud, environments, approval model, and agent pool with the user.
2. Generate `azure-pipelines.yml` with `trigger:` / `pr:` / `pool:` / `variables:` / `stages:`.
3. Add the per-stack `Build` job from the templates above.
4. Add a `Test` stage (often folded into `Build` for small projects; separate stage when matrix or long).
5. Add `Deploy_<Env>` stages using `deployment:` jobs and Environments. Wire WIF service connections.
6. If multiple pipelines share logic, extract templates and `resources: repositories:` them in.
7. Validate with `az pipelines validate` or the **Validate** button in the YAML editor before merging.

## Handoffs

- GitHub equivalent → `devops/github-actions`
- GitLab equivalent → `devops/gitlab-ci`
- IaC for underlying resources → `devops/infrastructure-as-code`
- Per-env secrets/config → `devops/environment-config`
- Azure-specific deploy details → `devops/azure-deployment`
- AWS-specific deploy details → `devops/aws-deployment`

- Test-suite CI lane — shard matrix, Allure publish, perf gate, quarantine → `qa-cicd-{java,dotnet,typescript}`
