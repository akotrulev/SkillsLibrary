---
name: devops-gitlab-ci
description: Use when the user asks to write, review, or modify a GitLab CI/CD pipeline (`.gitlab-ci.yml`) for build/test/deploy of Java, .NET, or TypeScript projects. Triggers: "write a `.gitlab-ci.yml` for X", "add a deploy stage to my GitLab pipeline". Do NOT use for GitHub Actions (`devops/github-actions`), Azure Pipelines (`devops/azure-pipelines`), or IaC (`devops/infrastructure-as-code`). Do NOT use for the test-suite CI lane — `qa-cicd-{java,dotnet,typescript}` owns that.
---

# DevOps — GitLab CI/CD

Authors `.gitlab-ci.yml` pipelines for build, test, and deploy across the project's stacks (Java 21 / .NET 10 primary with 8/9 supported / Node 24 LTS) and target clouds (AWS, Azure). Standardizes on `extends:` templates, `include:` reuse, OIDC for cloud auth (`id_tokens`), and protected-environment gates.

**Version policy:** detect the project's versions (TFM / `engines` / toolchain) and match — never assume. .NET 10 is primary, 8/9 supported (8 LTS ends Nov 2026). Node 20 is EOL (Apr 2026) — 24 is active LTS, 22 maintenance. Java 21 LTS is the default. Never put a job on a newer SDK/runtime than the project targets.

## When to use

- New GitLab project needs CI in `.gitlab-ci.yml`
- Add a deploy stage to an existing pipeline
- Refactor copy-pasted job definitions into `extends:` + `include:`
- Migrate from another CI to GitLab CI/CD

## When NOT to use

- GitHub Actions → `devops/github-actions`
- Azure DevOps Pipelines → `devops/azure-pipelines`
- Bicep / Terraform authoring → `devops/infrastructure-as-code`
- App-level env config → `devops/environment-config`

- Test-suite CI lane (shard matrix, Allure publish, perf gate, flake quarantine) → `qa/cicd/agents/qa-cicd-{java,dotnet,typescript}`
## Inputs needed

1. **Stack(s)**: .NET 10 (8/9 supported) / Java 21 + Gradle / Node 24 (22 maintenance) + which package manager
2. **Target cloud**: AWS (ECS, Lambda, S3+CloudFront, EKS) or Azure (App Service, Container Apps, AKS, Static Web Apps)
3. **Runner model**: GitLab.com SaaS runners, self-hosted runners (which tags?), Kubernetes executor
4. **Environments**: dev / staging / prod, and which are *protected* + need manual approval
5. **Test reporting**: Allure, JUnit XML (GitLab parses these for the MR view), coverage report format
6. **Secret store**: project/group CI/CD variables (masked), GitLab `id_tokens` + cloud OIDC role, or Vault / Key Vault pulled at deploy time

## Standard pipeline shape

Five stages, in order: `build`, `test`, `package`, `deploy-staging`, `deploy-prod`. Manual gate on prod via `when: manual` on a *protected* environment.

```yaml
stages: [build, test, package, deploy-staging, deploy-prod]

default:
  image: alpine:3.20
  interruptible: true   # cancel superseded pipelines on the same ref

workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_TAG

variables:
  CACHE_FALLBACK_KEY: main
```

Set `interruptible: true` on jobs that are safe to cancel (build/test, never deploys). `workflow:` prevents duplicate pipelines (push + MR) that waste minutes.

## Per-stack build/test jobs

### .NET (10 primary; match the project's TFM)

```yaml
.dotnet:
  image: mcr.microsoft.com/dotnet/sdk:10.0   # match the TFM: sdk:8.0 / sdk:9.0 for down-level projects
  cache:
    key:
      files: ['**/*.csproj']
    paths: [.nuget/packages/]
  variables:
    NUGET_PACKAGES: $CI_PROJECT_DIR/.nuget/packages

build:dotnet:
  stage: build
  extends: .dotnet
  script:
    - dotnet restore
    - dotnet build --configuration Release --no-restore
  artifacts:
    paths: [bin/, obj/]
    expire_in: 1 day

test:dotnet:
  stage: test
  extends: .dotnet
  needs: [build:dotnet]
  script:
    # `junit` logger requires the JUnitXml.TestLogger NuGet package in the test project;
    # without it no file is written and the MR test report is silently empty.
    - dotnet test --configuration Release --no-build --logger "junit;LogFilePath=test-results.xml" --collect:"XPlat Code Coverage"
  artifacts:
    when: always
    reports:
      junit: '**/test-results.xml'
      coverage_report:
        coverage_format: cobertura
        path: '**/coverage.cobertura.xml'
```

`reports: junit:` makes test results show up inline in the MR — non-negotiable for code review velocity.

### Java 21 + Gradle

```yaml
.gradle:
  image: eclipse-temurin:21-jdk
  cache:
    key:
      files: [build.gradle, settings.gradle, gradle/libs.versions.toml]
    paths: [.gradle/caches/, .gradle/wrapper/]
  variables:
    GRADLE_USER_HOME: $CI_PROJECT_DIR/.gradle

build:java:
  stage: build
  extends: .gradle
  script:
    - ./gradlew assemble --no-daemon
  artifacts:
    paths: [build/libs/]
    expire_in: 1 day

test:java:
  stage: test
  extends: .gradle
  needs: [build:java]
  script:
    - ./gradlew test --no-daemon
  artifacts:
    when: always
    reports:
      junit: '**/build/test-results/test/TEST-*.xml'
```

`--no-daemon` matters on ephemeral runners — the daemon caches between jobs in ways that surface as flakiness.

### Node 24 + pnpm (TypeScript)

```yaml
.node:
  image: node:24-alpine       # 22-alpine for a maintenance-LTS project; 20 is EOL
  before_script:
    - corepack enable
    - corepack prepare --activate   # version comes from package.json `packageManager` — don't double-pin
  cache:
    key:
      files: [pnpm-lock.yaml]
    paths: [.pnpm-store/]
  variables:
    PNPM_STORE: $CI_PROJECT_DIR/.pnpm-store

install:
  stage: build
  extends: .node
  script:
    - pnpm config set store-dir $PNPM_STORE
    - pnpm install --frozen-lockfile

lint:
  stage: test
  extends: .node
  needs: [install]
  script: [pnpm lint, pnpm tsc --noEmit]

test:
  stage: test
  extends: .node
  needs: [install]
  script:
    - pnpm test --reporter=junit --outputFile=reports/junit.xml
  artifacts:
    when: always
    reports:
      junit: reports/junit.xml
```

## Parallel matrix

```yaml
test:matrix:
  parallel:
    matrix:
      - DOTNET_VERSION: ['8.0']
        OS: [linux, windows]
  image: mcr.microsoft.com/dotnet/sdk:$DOTNET_VERSION
  script: [dotnet test]
```

`parallel: matrix:` is GitLab's native fan-out. Avoids hand-rolling N near-duplicate jobs.

## Cloud auth — `id_tokens` + OIDC (never static keys)

### AWS

```yaml
deploy:aws:
  stage: deploy-staging
  id_tokens:
    AWS_ID_TOKEN:
      aud: https://gitlab.com   # or your self-hosted host
  variables:
    AWS_ROLE_ARN: arn:aws:iam::123456789012:role/gitlab-deploy
    AWS_DEFAULT_REGION: eu-west-1
  before_script:
    - >
      export $(aws sts assume-role-with-web-identity
        --role-arn $AWS_ROLE_ARN
        --role-session-name "gitlab-${CI_JOB_ID}"
        --web-identity-token $AWS_ID_TOKEN
        --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]'
        --output text
        | awk '{print "AWS_ACCESS_KEY_ID="$1"\nAWS_SECRET_ACCESS_KEY="$2"\nAWS_SESSION_TOKEN="$3}')
  script:
    - aws ecs update-service --cluster $CLUSTER --service $SERVICE --force-new-deployment
```

The IAM role's trust policy restricts `sub` to `project_path:<group>/<project>:ref_type:branch:ref:main` (or `environment:prod`) — never `project_path:*`.

### Azure

```yaml
deploy:azure:
  stage: deploy-staging
  id_tokens:
    AZURE_ID_TOKEN:
      aud: api://AzureADTokenExchange
  variables:
    AZURE_CLIENT_ID: $AZURE_CLIENT_ID
    AZURE_TENANT_ID: $AZURE_TENANT_ID
    AZURE_SUBSCRIPTION_ID: $AZURE_SUBSCRIPTION_ID
  before_script:
    - az login --service-principal -u $AZURE_CLIENT_ID -t $AZURE_TENANT_ID --federated-token $AZURE_ID_TOKEN
    - az account set --subscription $AZURE_SUBSCRIPTION_ID
  script:
    - az webapp deployment source config-zip --resource-group $RG --name $APP --src ./publish.zip
```

The federated credential on the Azure AD app registration scopes to `project_path:<group>/<project>:environment:<env>`.

## Environments & gates

```yaml
deploy:staging:
  stage: deploy-staging
  environment:
    name: staging
    url: https://staging.example.com
  rules:
    - if: $CI_COMMIT_BRANCH == "main"

deploy:prod:
  stage: deploy-prod
  environment:
    name: production
    url: https://example.com
    deployment_tier: production
  rules:
    - if: $CI_COMMIT_TAG
      when: manual
  needs: [deploy:staging]
```

Mark `production` as a **protected environment** in the GitLab UI and restrict deploys to a maintainer group. `when: manual` plus protected env gives you two-person sign-off.

## Reuse — `extends:` and `include:`

Local reuse:

```yaml
.deploy-base:
  image: amazon/aws-cli
  before_script: [aws sts get-caller-identity]

deploy:staging:
  extends: .deploy-base
  script: [./scripts/deploy.sh staging]
```

Cross-repo reuse — keep templates in a `ci-templates` project:

```yaml
include:
  - project: 'platform/ci-templates'
    ref: v1.4.0
    file:
      - '/dotnet.gitlab-ci.yml'
      - '/aws-deploy.gitlab-ci.yml'
```

Pin `ref:` to a tag, never `main` — a template change should be a deliberate consumer update.

## Allure reporting

Upload the raw results as an artifact here; the **report generation/publishing pipeline belongs to the QA domain** — `qa/cicd/<stack>/skills/ci-pipelines` (Allure-publish step) and `qa/reporting/<stack>` own it. Don't wire a third-party Allure publishing job into an app-deploy pipeline.

```yaml
test:
  artifacts:
    when: always
    paths: [allure-results/]
    expire_in: 14 days
    reports:
      junit: test-results.xml   # GitLab parses this for the MR test view
```

## Rules

- One responsibility per job — don't fold `build && test && deploy` into a single `script:`. `needs:` makes them parallelize anyway.
- Pipeline DAG via `needs:` — declare actual dependencies, don't rely on stage order alone (it under-parallelizes)
- Pin all base images by tag (`node:24-alpine`, `eclipse-temurin:21-jdk`) — never `:latest`
- Pin language versions to what the project targets (`dotnet-version: '10.0.x'`); take the pnpm version from `package.json` `packageManager` via `corepack prepare --activate` — never double-pin it in CI
- Mask & protect secrets in **CI/CD variables** (group-level when shared); protected = only runs from protected branches
- Use `reports:` (`junit`, `coverage_report`, `dotenv`, `sast`) — they make the MR view useful
- `artifacts: when: always` for test results so failed builds still publish them
- `rules:` (modern) over `only:`/`except:` (legacy) — be consistent
- Restrict job runners with `tags:` when self-hosted; never let `deploy:prod` run on a shared runner
- Every job has a clear `stage:` and the stage list is declared once at the top

## What NOT to do

- No static cloud credentials in CI/CD variables — `id_tokens` + OIDC
- No `image: <something>:latest` — pin
- No `script:` without an `extends:` when 3+ jobs share the same setup
- No `before_script:` redefining the same env vars repeatedly — push into a `.template` and `extends:`
- No deploy job that runs on every MR commit — gate via `rules:` on branch/tag and `environment:`
- No `allow_failure: true` to silence flaky jobs — fix the flake or quarantine the test
- No `when: always` on every job — pipeline costs explode and broken MRs auto-fan-out
- No `cache:` without a `key:` based on lockfile content — sticky caches mask broken installs
- No long-lived runner with mutable state (Docker socket, host volume) for production deploys — use isolated runners
- No `Bash`-heavy `script:` blocks — extract to `./scripts/*.sh` and run them; that script can be invoked locally too

## Generation steps

1. Confirm stack(s), runner setup, target cloud, environments, and approval model with the user.
2. Generate `.gitlab-ci.yml` with `stages:`, `workflow:`, `default:`, and the per-stack jobs.
3. Add `id_tokens:` + OIDC `before_script:` blocks for the cloud being deployed to.
4. Add `environment:` to every deploy job; mark prod environment as protected in the UI.
5. If multiple repos share patterns, extract templates into a `ci-templates` project and `include:` them with a pinned `ref:`.
6. Validate locally with the CI Lint endpoint (`Pipelines → CI lint`) or `glab ci lint`. Inside a `Gate: none` plan task, run none of these checks and report them as "written, not run".

## Handoffs

- GitHub equivalent → `devops/github-actions`
- Azure DevOps equivalent → `devops/azure-pipelines`
- IaC for the underlying resources → `devops/infrastructure-as-code`
- Per-env secrets/config → `devops/environment-config`
- Cloud deploy specifics → `devops/aws-deployment` / `devops/azure-deployment`

- Test-suite CI lane — shard matrix, Allure publish, perf gate, quarantine → `qa-cicd-{java,dotnet,typescript}`
