# Checkov — deep dive

**Checkov** (Bridgecrew → Palo Alto Networks, Python, `checkov==3.2.529` at time of writing) is the primary
IaC scanner in this skill: 1,000+ built-in policies, **graph-based** checks that reason across resources, and
custom policies in **YAML or Python**. Read this when the SKILL.md decision matrix routed you here — deep
Terraform, plan scanning, Bicep/ARM, CI-config scanning, or a custom policy.

## Frameworks

`--framework` / `--skip-framework` take any of: `terraform`, `terraform_plan`, `cloudformation`, `bicep`,
`arm`, `kubernetes`, `helm`, `kustomize`, `dockerfile`, `serverless`, `ansible`, `openapi`, `github_actions`,
`gitlab_ci`, `circleci_pipelines`, `azure_pipelines`, `secrets`, `sca_package`, `sca_image`.

**Always scope it.** An unscoped `checkov -d .` on a normal repo mixes Dockerfile, workflow, and secrets
findings into what the team thinks is "the Terraform gate," and the exit code stops meaning anything.

Two frameworks deserve a note:

- **`secrets`** overlaps `qa-security-secrets-scan` (Gitleaks + TruffleHog) totally. **Skip it here** — that
  skill owns secrets, with its own allow-list and triage. `--skip-framework secrets`.
- **`sca_package` / `sca_image`** overlap `qa-security-testing-dependency-scan-*` and
  `qa-security-image-infra-scan`. Same rule: **skip them**, those skills own their layers.

## Check IDs and the severity asymmetry

Check IDs are stable and readable: `CKV_AWS_18` (S3 access logging), `CKV_K8S_20` (containers must not run as
root), `CKV_AZURE_33` (Storage queue logging), `CKV2_AWS_6` (graph check — bucket has a public-access block).
The **`CKV2_`** prefix marks a **graph check**: one that needs the relationship between resources, not a single
block's attributes. Those are the checks Trivy's per-file model structurally cannot express, and they are the
main reason this skill exists.

Severity filtering is **asymmetric, and it trips people**:

| Flag | Meaning with a severity |
|---|---|
| `--check HIGH` | run checks of **HIGH and above** |
| `--skip-check LOW` | skip checks of **LOW and below** |

A skipped check **does not run at all** and does not appear in output — it is not a "pass". Both flags also
take explicit IDs and wildcards (`--check CKV_AWS_*`), and IDs and severities can be mixed.

> **Severities require a platform connection for some checks.** Community Checkov ships severities for its
> built-ins, but a policy without one is unfiltered by severity flags — if a check you expect to gate on is
> silently absent from the gating pass, check whether it carries a severity, and pin it by **ID** instead.

## Exit-code control — the ratchet

Checkov's default is the inverse of Trivy's: **any failed check exits `1`**. The controls, weakest to
strongest:

```bash
checkov -d ./infra --soft-fail                       # always exit 0 — the informational pass
checkov -d ./infra --soft-fail-on LOW,MEDIUM         # exit 0 for these, non-zero for the rest
checkov -d ./infra --hard-fail-on CKV_AWS_18,HIGH    # exit non-zero only for these
checkov -d ./infra                                   # default: fail on anything
```

The **adoption ratchet** on a legacy repo, in order: `--soft-fail` (see the damage) → `--create-baseline` →
`--hard-fail-on CRITICAL` → clear the backlog → `--skip-check LOW` with the baseline → eventually retire the
baseline entries as they are fixed.

## Terraform depth

```bash
# Variables the plan would supply — source-Terraform and Helm scans only, and requires -d.
checkov -d ./infra/environments/prod --var-file prod.tfvars --var-file secrets.auto.tfvars

# Remote modules: without this, module contents are invisible and graph checks under-report.
# Network egress + third-party code — opt in deliberately.
checkov -d ./infra --download-external-modules true

# Exclude what should never be scanned.
checkov -d . --skip-path '.terraform/' --skip-path 'infra/modules/vendored/' --skip-path 'test/fixtures/'
```

`--skip-path` is **regex**, matched against the path — `.terraform/` also matches `infra/x/.terraform/`.

## Plan scanning (`terraform_plan`)

```bash
terraform -chdir=infra/environments/prod plan -out=tfplan.binary
terraform -chdir=infra/environments/prod show -json tfplan.binary > tfplan.json

checkov -f tfplan.json --framework terraform_plan \
  --deep-analysis --repo-root-for-plan-enrichment infra/environments/prod
```

- The plan is the **resolved** state: variables, locals, `for_each`, module outputs, and data sources are all
  evaluated. `encrypted = var.enable_encryption` becomes `encrypted = false`, and the check fires.
- **`--deep-analysis` + `--repo-root-for-plan-enrichment`** merge the plan graph with the HCL graph. Without
  them, a plan finding points at a line in `tfplan.json` — useless to the human who has to fix it. With them,
  it points at the `.tf` file.
- Plan scanning **misses** what the plan never instantiates: a module's insecure default that this
  environment happens to override, code paths behind a `count = 0`. Template scanning catches those. **Run
  both** — they are orthogonal, exactly like `trivy config` vs `trivy image`.
- **`tfplan.json` is sensitive** (resolved secrets, account IDs, connection strings). Consume it in-job,
  never commit it, never publish it as an artifact.

## Custom policies

### YAML (declarative — start here)

```yaml
# infra/policies/checkov/CKV_ORG_2-no-public-ingress.yaml
metadata:
  id: "CKV_ORG_2"
  name: "Security groups must not allow ingress from 0.0.0.0/0 outside the DMZ"
  category: "NETWORKING"
  severity: "HIGH"
definition:
  and:
    - cond_type: attribute
      resource_types: ["aws_security_group_rule"]
      attribute: "type"
      operator: "equals"
      value: "ingress"
    - cond_type: attribute
      resource_types: ["aws_security_group_rule"]
      attribute: "cidr_blocks"
      operator: "not_contains"
      value: "0.0.0.0/0"
```

The top-level object under `definition` is an **attribute block**, a **connection block** (the graph half —
"this resource must be connected to one of that type"), or a logical operator (`and`, `or`, `not`). Operators
include `equals`, `not_equals`, `exists`, `not_exists`, `contains`, `regex_match`, `greater_than`,
`within`, `jsonpath_equals`, and ~36 others as of Checkov 3.x.

### Python (when YAML runs out)

```python
# infra/policies/checkov/CKV_ORG_3_rds_retention.py
from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck


class RdsBackupRetention(BaseResourceCheck):
    def __init__(self) -> None:
        super().__init__(
            name="Production RDS clusters retain backups for at least 30 days",
            id="CKV_ORG_3",
            categories=[CheckCategories.BACKUP_AND_RECOVERY],
            supported_resources=["aws_rds_cluster"],
        )

    def scan_resource_conf(self, conf: dict) -> CheckResult:
        retention = conf.get("backup_retention_period", [0])[0]
        return CheckResult.PASSED if retention >= 30 else CheckResult.FAILED


check = RdsBackupRetention()
```

```bash
checkov -d ./infra --external-checks-dir ./infra/policies/checkov
```

Custom policies land in the **same report, same baseline, same SARIF** as the built-ins — which is the reason
to prefer them over Conftest when the rule is about one resource type's attributes. Reach for Rego when the
rule needs real logic, spans arbitrary config, or must be shared with Gatekeeper.

### Testing custom policies is mandatory

A policy with a typo in the attribute path returns `PASSED` forever and proves nothing. Keep a fixture pair
per policy and assert both verdicts in CI:

```
infra/policies/checkov/
  CKV_ORG_2-no-public-ingress.yaml
  tests/CKV_ORG_2/pass/main.tf      # a compliant resource — must not be flagged
  tests/CKV_ORG_2/fail/main.tf      # a violating resource — must be flagged
```

```bash
checkov -d infra/policies/checkov/tests/CKV_ORG_2/fail \
  --external-checks-dir infra/policies/checkov --check CKV_ORG_2   # expect exit 1
checkov -d infra/policies/checkov/tests/CKV_ORG_2/pass \
  --external-checks-dir infra/policies/checkov --check CKV_ORG_2   # expect exit 0
```

## Suppression

```hcl
resource "aws_s3_bucket" "logs" {
  # checkov:skip=CKV_AWS_18:JIRA-5140 — logging the log bucket recurses; re-review 2026-11-01
  bucket = "${var.prefix}-access-logs"
}
```

The comment must sit **inside the block's scope**. Kubernetes/Helm use an annotation
(`checkov.io/skip1: CKV_K8S_20=JIRA-5142 reason`); Dockerfiles use a `#checkov:skip=` comment above the
instruction. Checkov has **no native expiry** — the re-review date is a review-enforced convention, not a
mechanism, which is the one place this discipline is weaker than `.trivyignore.yaml`'s `expired_at`.

## Output & config

```bash
checkov -d ./infra -o cli -o sarif --output-file-path console,checkov.sarif --compact --quiet
```

`-o` is repeatable (`cli`, `json`, `sarif`, `junitxml`, `csv`, `github_failed_only`); `--output-file-path`
takes a matching comma-separated list where `console` means stdout. `--compact` drops code blocks and
`--quiet` shows failures only — together they are the difference between a readable CI log and 4,000 lines of
green.

Commit a `.checkov.yml` (see SKILL.md) so a developer's local run and CI produce the same verdict. Every flag
above has a config-file key.
