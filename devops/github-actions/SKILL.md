---
name: devops-github-actions
description: Use when the user asks to write, review, or modify GitHub Actions workflows for build/test/deploy of Java, .NET, or TypeScript projects, with deploys to AWS or Azure. Triggers: "write a GitHub Actions workflow for X", "add a deploy job to .github/workflows/Y.yml", "set up CI for this repo", "add a release workflow". Do NOT use for GitLab CI (use `devops/gitlab-ci`), Azure Pipelines (use `devops/azure-pipelines`), or IaC scripts (use `devops/iac-bicep-terraform`). Do NOT use for the **test-suite CI lane** — shard matrix, Allure publishing, perf gate, flake quarantine — that belongs to `qa-cicd-{java,dotnet,typescript}`; this skill owns the **build/deploy** lane.
---

# DevOps — GitHub Actions

Authors GitHub Actions workflows for build, test, and deploy across the project's stacks (Java 21 / .NET 10 primary with 8/9 supported / Node 24 LTS) and target clouds (AWS, Azure). Standardizes on reusable workflows, OIDC-based cloud auth, matrix builds, and per-environment gates.

**Version policy:** detect the project's versions (TFM / `engines` / toolchain) and match — never assume. .NET 10 is primary, 8/9 supported (8 LTS ends Nov 2026). Node 20 is EOL (Apr 2026) — 24 is active LTS, 22 maintenance.

## When to use

- New repo needs CI in `.github/workflows/`
- Add a deploy stage to an existing CI workflow
- Add a scheduled / release-triggered workflow
- Refactor copy-pasted workflows into reusable workflows + composite actions

## When NOT to use

- GitLab CI/CD → `devops/gitlab-ci`
- Azure DevOps Pipelines → `devops/azure-pipelines`
- Bicep / Terraform authoring → `devops/iac-bicep-terraform`
- App-level env config → `devops/environment-config`

- Test-suite CI lane (shard matrix, Allure publish, perf gate, flake quarantine) → `qa/cicd/agents/qa-cicd-{java,dotnet,typescript}`
## Inputs needed

1. **Stack(s)**: .NET 8/9/10 / Java 21+Gradle / Node 22/24 + which package manager (pnpm/npm/yarn)
2. **Target cloud** for deploy: AWS (which service: ECS, Lambda, S3+CloudFront, EKS) or Azure (App Service, Container Apps, AKS, Static Web Apps)
3. **Trigger model**: push to `main` only, PR + push, manual `workflow_dispatch`, scheduled
4. **Environments**: dev / staging / prod, and which require approval
5. **Test reporting**: Allure, JUnit XML, plain text
6. **Secret store**: GitHub Environment secrets, OIDC + cloud role assumption (preferred), or Key Vault / AWS Secrets Manager pulled at deploy time

## Standard workflow shape

Every workflow follows this skeleton: triggers → concurrency → jobs (build → test → deploy with environment gate).

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

permissions:
  contents: read
  id-token: write    # required for OIDC cloud auth
  checks: write      # required for test reporters

jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      # ... stack-specific steps below

  deploy-staging:
    needs: build-test
    if: github.ref == 'refs/heads/main'
    environment: staging        # gated via GitHub Environments
    runs-on: ubuntu-latest
    steps:
      # ... cloud-specific deploy below
```

`concurrency` cancels in-flight PR runs but never cancels `main`. `id-token: write` is required for OIDC; never use static cloud credentials as repo secrets.

## Per-stack build/test jobs

### .NET (8/9/10 — match the project's TFM)

```yaml
- uses: actions/setup-dotnet@v5
  with: { dotnet-version: '10.0.x' }   # or 8.0.x / 9.0.x — match the TFM

- name: Restore
  run: dotnet restore

- name: Build
  run: dotnet build --configuration Release --no-restore

- name: Test
  run: dotnet test --configuration Release --no-build --logger "trx;LogFileName=test-results.trx" --collect:"XPlat Code Coverage"

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: dotnet-test-results
    path: '**/test-results.trx'
```

NuGet caching is automatic via `setup-dotnet` when a `global.json` or `*.sln` is present. For larger solutions add `actions/cache@v4` on `~/.nuget/packages` keyed by `Directory.Packages.props` / `packages.lock.json`.

### Java 21 + Gradle

```yaml
- uses: actions/setup-java@v5
  with:
    distribution: temurin
    java-version: '21'
    cache: gradle

- name: Build & test
  run: ./gradlew build --no-daemon

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: java-test-results
    path: '**/build/test-results/**/*.xml'
```

For Maven: `cache: maven` and `./mvnw verify`. The `--no-daemon` flag matters on ephemeral runners — daemons leak between cached state and slow cold starts.

### Node 24 + pnpm (TypeScript)

```yaml
- uses: pnpm/action-setup@v4     # reads the version from package.json "packageManager" — don't double-pin here
- uses: actions/setup-node@v6
  with:
    node-version: '24'           # active LTS; '22' for maintenance-LTS projects — never EOL 20
    cache: pnpm

- name: Install
  run: pnpm install --frozen-lockfile

- name: Type-check
  run: pnpm tsc --noEmit

- name: Lint
  run: pnpm lint

- name: Test
  run: pnpm test --reporter=junit --outputFile=reports/junit.xml
```

`--frozen-lockfile` is mandatory in CI — a CI run that mutates the lockfile is a footgun. For Vitest add `vitest run` (no watch) and configure `reporters: ['junit']` in `vitest.config.ts`.

## Matrix builds

When the same stack must build against multiple versions/OSes:

```yaml
strategy:
  fail-fast: false
  matrix:
    dotnet: ['8.0.x', '10.0.x']
    os: [ubuntu-latest, windows-latest]
runs-on: ${{ matrix.os }}
```

`fail-fast: false` so one failing combination doesn't kill the others — you want every diagnostic in one run.

## Cloud auth (OIDC, never static keys)

### AWS

Pre-create an IAM role with a trust policy for GitHub's OIDC provider, then:

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
    aws-region: eu-west-1
```

The role's trust policy must restrict `sub` to a specific repo + branch / environment — never `repo:org/*`.

### Azure

```yaml
- uses: azure/login@v2
  with:
    client-id: ${{ vars.AZURE_CLIENT_ID }}
    tenant-id: ${{ vars.AZURE_TENANT_ID }}
    subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
```

The federated credential on the Azure AD app registration must scope to `repo:<org>/<repo>:environment:<env>`. Never use `azure/login` with a client secret stored in `secrets.*`.

## Deploy job patterns

### AWS — container to ECS / Lambda

```yaml
deploy-aws:
  needs: build-test
  environment: prod
  runs-on: ubuntu-latest
  env:
    IMAGE_REPO: orders-api                  # ECR repository name
  steps:
    - uses: actions/checkout@v6
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: ${{ vars.AWS_ROLE }}
        aws-region: ${{ vars.AWS_REGION }}
    - uses: aws-actions/amazon-ecr-login@v2
      id: ecr
    - uses: docker/setup-buildx-action@v3
    - name: Build & push image
      uses: docker/build-push-action@v6
      with:
        context: .
        push: true
        tags: ${{ steps.ecr.outputs.registry }}/${{ env.IMAGE_REPO }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        provenance: true
        sbom: true
    - name: Deploy to ECS
      run: aws ecs update-service --cluster ${{ vars.ECS_CLUSTER }} --service ${{ vars.ECS_SERVICE }} --force-new-deployment
```

`docker/build-push-action` + `type=gha` cache reuses BuildKit layers across runs — raw `docker build`/`tag`/`push` rebuilds cold every time and skips provenance/SBOM (see `devops/docker` for the image-side rules).

### Azure — App Service / Container Apps

```yaml
deploy-azure:
  needs: build-test
  environment: prod
  runs-on: ubuntu-latest
  steps:
    - uses: azure/login@v2
      with: { client-id: ${{ vars.AZURE_CLIENT_ID }}, tenant-id: ${{ vars.AZURE_TENANT_ID }}, subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }} }
    - uses: azure/webapps-deploy@v3
      with:
        app-name: ${{ vars.APP_NAME }}
        package: ./publish
```

For Container Apps, push to ACR (`docker/login-action` + ACR) then `az containerapp update --image ...`.

## Reusable workflows and composite actions

Once you have the same build/test for 3+ repos, extract:

```yaml
# .github/workflows/reusable-dotnet-build.yml
on:
  workflow_call:
    inputs:
      dotnet-version: { type: string, default: '8.0.x' }
    secrets:
      NUGET_API_KEY: { required: false }
```

Caller:

```yaml
jobs:
  build:
    uses: org/.github/.github/workflows/reusable-dotnet-build.yml@v1
    with: { dotnet-version: '8.0.x' }
    secrets: inherit
```

Pin reusable workflows by tag (`@v1`) or SHA, never `@main` — a change in a shared workflow should be a deliberate consumer update.

## Allure reporting

Upload the raw results as an artifact here; the **report generation/publishing pipeline belongs to the QA domain** — `qa/cicd/<stack>/skills/ci-pipelines` (Allure-publish step) and `qa/reporting/<stack>` own it. Don't wire a third-party gh-pages Allure action into an app-deploy workflow.

```yaml
- name: Upload Allure results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: allure-results
    path: allure-results
    retention-days: 14
```

## Rules

- `permissions:` block at the top, restricting to the minimum each job needs. Default `read-all` is sloppy.
- Pin actions to a major version (e.g. `checkout@v6`) at minimum; pin to a SHA when the action runs with elevated permissions. Old action majors also run on deprecated runner Node versions — keep majors current
- Use `secrets.*` for true secrets; use `vars.*` for non-secret config (region, app name, role ARN)
- Use **Environments** (Settings → Environments) for any deploy job; gate prod with required reviewers
- `if: always()` on test-result upload steps so failures still publish artifacts
- One workflow per purpose (`ci.yml`, `release.yml`, `deploy-prod.yml`) — don't bolt release logic onto the CI workflow with cascading `if:` conditions
- Pin Node / Java / .NET versions explicitly — never use a `latest` tag
- `--frozen-lockfile` / `--locked` / equivalent for every package manager
- Step `name:` is mandatory — anonymous steps are unreadable in failure logs

## What NOT to do

- No `${{ secrets.AWS_ACCESS_KEY_ID }}` / `secrets.AZURE_CLIENT_SECRET` long-lived credentials — OIDC only
- No `actions/checkout@master` or `@main` — pin to a tag
- No `continue-on-error: true` on a step you want to actually pass — it silently lies
- No `working-directory: ${{ github.workspace }}/...` everywhere — set it once at the job level
- No deploy job that runs on PRs — guard with `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`
- No installing dependencies with `npm install` (mutates lockfile) — `ci` / `--frozen-lockfile`
- No `cron:` schedules at minute 0 — every popular scheduler fires there; offset by a few minutes to avoid runner queueing
- No `runs-on: self-hosted` without naming a specific labeled runner group — `self-hosted` alone picks any
- No secrets in `env:` at the workflow level — they leak into every step; scope to the job/step that needs them

## Generation steps

1. Confirm stack(s), trigger model, target cloud, and environments with the user.
2. Generate `.github/workflows/ci.yml` with the standard skeleton (triggers + concurrency + permissions + jobs).
3. Insert the per-stack build/test job from the templates above.
4. Insert the cloud deploy job for the target. Gate via `environment:`. Use OIDC.
5. If multiple repos need the same pipeline, extract a reusable workflow and call it from `ci.yml`.
6. Validate locally with `actionlint` (`brew install actionlint`) before committing.

## Handoffs

- GitLab equivalent → `devops/gitlab-ci`
- Azure DevOps equivalent → `devops/azure-pipelines`
- IaC for the underlying cloud resources → `devops/iac-bicep-terraform`
- Per-env secrets/config → `devops/environment-config`
- AWS-specific deploy details → `devops/aws-deployment`
- Azure-specific deploy details → `devops/azure-deployment`

- Test-suite CI lane — shard matrix, Allure publish, perf gate, quarantine → `qa-cicd-{java,dotnet,typescript}`
