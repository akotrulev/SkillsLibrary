# CI wiring — the deploy pipeline, not the test lane

Infra gates belong in the deploy pipeline (`devops/{github-actions,gitlab-ci,azure-pipelines}`) beside `fmt`, `validate` and `plan`, not in `qa/cicd/*`, which owns the test-suite lane (shard matrix, Allure, perf gate). Versions match `../SKILL.md` Setup.

```yaml
name: IaC Security
on: [pull_request]

permissions:
  contents: read
  security-events: write
  id-token: write

jobs:
  iac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: bridgecrewio/checkov-action@v12.1347.0
        with:
          directory: infra
          framework: terraform
          soft_fail: true
          output_format: cli,sarif
          output_file_path: console,checkov-all.sarif
      - uses: bridgecrewio/checkov-action@v12.1347.0
        with:
          directory: infra
          framework: terraform
          baseline: infra/.checkov.baseline
          skip_check: LOW
          external_checks_dirs: infra/policies/checkov
          soft_fail: false
      - if: always()
        uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: checkov-all.sarif }

  plan-policy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.PLAN_READONLY_ROLE_ARN }}
          aws-region: eu-west-1
      - uses: hashicorp/setup-terraform@v3
        with: { terraform_version: 1.13.3 }
      - run: |
          terraform -chdir=infra/environments/prod init
          terraform -chdir=infra/environments/prod plan -out=tfplan.binary
          terraform -chdir=infra/environments/prod show -json tfplan.binary > tfplan.json
      - run: |
          docker run --rm -v "$PWD:/w" -w /w openpolicyagent/conftest:v0.62.0 \
            test tfplan.json --policy infra/policies/opa --output github
```

- The first Checkov step is the informational pass and the second is the gating pass; both are in `../SKILL.md`.
- `id-token: write` is OIDC to the cloud for `terraform plan` with a read-only role: no static keys.
- The plan JSON is sensitive: consumed in the job, never uploaded as an artifact.
- Pin every action by tag or SHA (`@v12.1347.0`, never `@master`). KICS's own GitHub Action was compromised in March 2026 (`other-scanners.md`).
- SARIF goes to code-scanning so each finding lands inline on the PR diff, de-duped run over run, the consolidation `qa-<stack>:security-foundations` prescribes.
- GitLab CI and Azure Pipelines run the same two passes through the `bridgecrew/checkov` and `openpolicyagent/conftest` images (`devops/{gitlab-ci,azure-pipelines}`).
