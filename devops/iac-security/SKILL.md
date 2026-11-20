---
name: iac-security
description: Use when scanning Terraform or Helm for misconfiguration with Checkov or OPA/Conftest policy-as-code. Triggers "scan our Terraform for misconfig". Not for a live account (cloud-posture).
disable-model-invocation: true
---

# DevOps — IaC Security (Checkov & policy-as-code)

Infrastructure-as-Code is the **intended** state of your cloud: an S3 bucket without encryption, a security group open to `0.0.0.0/0`, a pod spec without `runAsNonRoot`, a Key Vault without purge protection. All of it is decided in a `.tf`, `.bicep` or `.yaml` file long before it exists, so IaC scanning is the cheapest security gate in the library: it reads files, needs no running target, and runs on **every PR from day one**.

This skill owns the **deep** half of that gate: **Checkov** (1,000+ built-in policies across Terraform, Terraform *plan*, CloudFormation, Bicep/ARM, Kubernetes, Helm, Kustomize, Dockerfile, Serverless and CI configs, with **graph-based** checks that reason across resources) and **OPA/Conftest**, Rego policies over any structured config, which is how **org-specific** rules no vendor ships get enforced. It runs in the **deploy pipeline**, never the `qa/cicd/*` test lane.

> **Authorization: none needed.** Unlike its siblings (`devops:kubernetes-security` probes a live cluster, `devops:cloud-posture` reads a live account), IaC scanning is purely static: it reads repo files and sends nothing anywhere, so there is no live target and no authorization line to record, and it runs unattended on forks and untrusted branches. Do not import the live-target gates from the sibling skills, and do not claim coverage of live state you never read. The one exception is `--download-external-modules`, which fetches remote Terraform modules (network egress, third-party code): a deliberate per-repo opt-in, only where the module contents change the verdict.

> **The fence vs `qa-<stack>:image-infra-scan` (Trivy `config`).** Trivy already scans IaC (`trivy config ./infra` runs the absorbed tfsec check library over Terraform, CloudFormation, Kubernetes, Helm and Dockerfiles) and owns it as the A02 gate. This skill adds three things: **(a) graph depth**, where Checkov reasons across resources and modules (a bucket and its separate `aws_s3_bucket_public_access_block`) and a per-file check cannot; **(b) policy-as-code**, where Checkov custom policies and OPA/Conftest express rules no catalogue contains ("every resource carries `cost_center`", "only these three AMI owners"); **(c) plan scanning**, where Checkov evaluates the `terraform plan` JSON, the state resolved after variables, locals and modules. **One scanner gates a given misconfig class.** Trivy `config` stays the default for a repo that needs only one; when this skill's gate goes in, Trivy's `config` scan drops to informational (`--exit-code 0`) or is scoped away, so the same open security group never fails two pipelines with two suppressions and two tickets.

## Two spines per finding — OWASP + CIS, ATT&CK where it maps

| Spine | What it answers | Example |
|---|---|---|
| **OWASP Top 10:2025 A02 Security Misconfiguration** (primary) | The application-security category | An unencrypted bucket, a permissive SG, a container with no resource limit |
| OWASP **A01** Broken Access Control · **A03** Software Supply Chain Failures | The two secondary categories IaC reaches | An IAM policy with `Action: "*"` (A01); an unpinned module source or CI action (A03) |
| **CIS Benchmarks** (AWS / Azure / GCP / Kubernetes / Docker) | The compliance control; Checkov ships the mapping | `CKV_AWS_18` → CIS AWS 3.6 (S3 access logging) |
| **MITRE ATT&CK Cloud / Containers** | The technique the misconfig enables | Public S3 bucket → **T1530** · wildcard IAM role → **T1078.004** · privileged pod spec → **T1611** |

Use the Cloud and Containers matrices, never Enterprise. When a misconfig maps to no technique, say so rather than inventing one.

> **Green ≠ safe.** A clean Checkov run means the templates in this repo passed these checks. It says nothing about what is running (drift: `devops:cloud-posture` and `devops:kubernetes-security` read live state), whether the app is exploitable (the `qa-<stack>` security skills), whether the image is patched (`qa-<stack>:image-infra-scan`), or whether a rule your org cares about exists as a check (write it). Every report names what it covered, which checks were skipped and why, and what it handed off.

## Decision matrix — which tool, and when

| Need | Use | Notes |
|---|---|---|
| A **first, cheap** gate on a repo with no scanner | **Trivy `config`** (`qa-<stack>:image-infra-scan`) | One binary you already run for images; escalate when you outgrow it |
| **Deep Terraform**: modules, variables, graph checks | **Checkov** `-d .` | The headline. `references/checkov.md` |
| Gate the **evaluated plan** | **Checkov** `--framework terraform_plan` | Sees resolved vars, locals, module outputs |
| **Org-specific** rule no built-in expresses | **OPA/Conftest**, or a Checkov custom policy | `references/opa-conftest.md` |
| **Bicep / ARM** | **Checkov** `--framework bicep,arm` | Trivy does not cover Bicep |
| **Helm / Kustomize** | **Checkov** `--framework helm,kustomize`, or `helm template` → **Conftest** | Checkov renders internally; Conftest wants rendered YAML |
| **Dockerfile** | Trivy `config` **or** Checkov `--framework dockerfile` | One owner; the overlap is total |
| **CI/CD pipeline config** | **Checkov** `--framework github_actions,gitlab_ci` | Unpinned actions, `pull_request_target`, secret exposure (A03) |
| Exotic IaC formats | **KICS** | Breadth over depth; `references/other-scanners.md` (incl. its 2026 action compromise) |
| **tfsec** / **Terrascan** | **Do not adopt** | tfsec merged into Trivy (EOL May 2025); Terrascan archived Nov 2025. Trivy carries the tfsec check library, Checkov the depth |
| A **live** cluster or cloud account | `devops:kubernetes-security` / `devops:cloud-posture` | Running state, not intended state |
| Conformance against **this plugin's own rules** | `devops-auditor` | A read-only sweep into `docs/audits/`; this skill runs scanners and gates a build. A conformance observation (no `cost_center` tag) becomes this skill's gate once you encode it as a policy |

**Checkov is the gate**, **Conftest is the org rulebook**, **plan scanning is the high-signal pass on the branch about to apply**.

## Setup — pin the version

```bash
pipx install checkov==3.2.529
docker run --rm -v "$PWD:/tf" bridgecrew/checkov:3.2.529 -d /tf

brew install conftest
docker run --rm -v "$PWD:/project" openpolicyagent/conftest:v0.62.0 test .
```

Pin Checkov, Conftest and `bridgecrewio/checkov-action@v12.1347.0` in CI, never `latest` or `@master`. Checkov ships checks weekly; an unpinned scanner turning a green build red overnight is what gets the gate switched off. Bump on purpose, in a PR that triages the new findings.

## The scan commands

```bash
checkov -d ./infra --framework terraform,terraform_plan

terraform -chdir=infra/environments/prod plan -out=tfplan.binary
terraform -chdir=infra/environments/prod show -json tfplan.binary > tfplan.json
checkov -f tfplan.json --framework terraform_plan
conftest test tfplan.json --policy ./policy

helm template ./charts/api | conftest test - --policy ./policy/k8s
```

**Always scope `--framework`.** An unscoped run mixes Dockerfile, CI and secrets findings into the Terraform gate and makes the exit code unreadable. The flag table, the severity asymmetry (`--check HIGH` runs HIGH and above, `--skip-check LOW` skips LOW and below) and the output flags are in `references/checkov.md`.

**Bare `checkov -d .` exits `1` on the first failed check**, the inverse of Trivy. It gates by default and `--soft-fail` makes it report-only. Get this backwards and your adoption PR fails on 400 legacy findings.

## The two-pass gate and the baseline

```bash
checkov -d ./infra --framework terraform --soft-fail --compact -o cli -o sarif \
  --output-file-path console,checkov-all.sarif

checkov -d ./infra --framework terraform \
  --baseline .checkov.baseline \
  --skip-check LOW \
  --compact
```

- **Pass 1 is informational**: every severity, never fails, the complete picture in the logs and the SARIF artifact.
- **Pass 2 is the gate**: `--baseline` drops the known backlog, `--skip-check LOW` drops the noise floor, and the default exit 1 does the failing.
- **Baseline once, gate NEW hard.** A scanner introduced to a real repo finds hundreds of pre-existing failures, and blocking on all of them gets the gate disabled by Friday. Run `checkov -d ./infra --create-baseline` once at adoption and commit `infra/.checkov.baseline`; every later run reports only failures absent from it. New resources have no entry, so new infrastructure is born compliant.
- **The baseline is a debt register, not a mute button**: committed, reviewed in PRs, and it only shrinks. A PR that grows it adds a misconfig. Regenerating it to turn a red build green is how this gate dies; regeneration is a reviewed act, for example after a bulk remediation.
- **Ratchet the severity floor**: adopt at `--check CRITICAL` (or `--soft-fail-on` everything below), clear the backlog, then tighten to `HIGH,CRITICAL`. Never start at HIGH on a legacy repo.

To wire both passes and the plan job into a pipeline, read `references/ci-wiring.md`.

## Suppression — ticketed, scoped, expiring

Checkov's inline mechanism is a comment inside the resource block: `checkov:skip=<CHECK_ID>:<reason>`. Scope each suppression to **one check ID on one resource**, with a ticket, a reason and a re-review date. Checkov has no native expiry (unlike `.trivyignore.yaml`'s `expired_at`), so the date is enforced in review, and a suppression with no ticket is a finding.

```hcl
resource "aws_s3_bucket" "logs" {
  # checkov:skip=CKV_AWS_18:JIRA-5140 — access logging on the log bucket itself would recurse; re-review 2026-11-01
  bucket = "${var.prefix}-access-logs"
}
```

Prefer the fix: encrypting the bucket is one line, the suppression is forever. A check you disagree with is disabled once in `.checkov.yml` with the reason (the committed config is in `references/checkov.md`), and then ask whether the right rule is a custom policy.

## Policy-as-code — the half no vendor ships

Built-in catalogues encode what the industry agrees on, not what your org decided: mandatory tags, an allow-list of instance types or regions, "no public ingress outside the DMZ account", "every prod RDS instance has `deletion_protection`". Two routes:

| Route | Write it when | Language |
|---|---|---|
| **Checkov custom policy** | The rule is about one resource type's attributes, or a graph connection between two resources, and belongs in the same run, report and baseline as the built-ins | YAML or Python: `references/checkov.md` |
| **OPA / Conftest** | The rule spans arbitrary structured config, needs real logic, must be shared across tools (the same Rego runs in Conftest, Gatekeeper and Terraform Cloud), or runs over the plan JSON | Rego: `references/opa-conftest.md` |

```bash
conftest test tfplan.json --policy ./infra/policies/opa
checkov -d ./infra --external-checks-dir ./infra/policies/checkov
```

**Test every policy.** A policy that never fires reports green forever and manufactures confidence: `conftest verify` over `*_test.rego` for Rego, a compliant-and-violating fixture pair asserted in CI for each Checkov custom policy. Both references carry the shapes.

## Plan scanning — the evaluated state

A template read sees `encrypted = var.enable_encryption` and cannot know what `var` resolves to; plan scanning reads the resolved value after variables, locals, `for_each`, module outputs and data sources.

```bash
checkov -f tfplan.json --framework terraform_plan \
  --deep-analysis --repo-root-for-plan-enrichment infra/environments/prod
```

`--deep-analysis` with `--repo-root-for-plan-enrichment` merges the plan graph with the HCL graph so a plan finding still points at the `.tf` line a human edits.

- **The plan JSON is sensitive** (resolved secret values, connection strings, account identifiers): never commit it, never publish it as an artifact, scrub it from logs. Treat it like the state file.
- `plan` needs cloud **read** credentials: OIDC or Workload Identity Federation with a read-only role, never a long-lived key.
- **Run both passes.** Templates catch what plan cannot (a module default this environment overrides, code behind `count = 0`); plan catches the resolved value.

## Cross-references

- **`qa-<stack>:image-infra-scan`**: the most important fence. Trivy `config` stays the lightweight default and owns the image, OS and SBOM layers; run the other scanner informational.
- `devops:kubernetes-security` (the live cluster) · `devops:cloud-posture` (the live account, the drift and the resources IaC never created) · `devops:supply-chain-security` (artifact signing, SLSA, dependency confusion; this skill scans the pipeline *config*, that one secures the *artifacts*) · `devops:threat-modeling` (which misconfig classes matter for this system, and so what a custom policy encodes) · `devops:controls-validation` (proves a declared control works).
- `infra-security-tester`: the orchestrator that runs this skill as its IaC and image posture step, before the live-cluster and cloud-posture steps.
- **`devops:iac`**: the authoring sibling. Its Rules (mandatory tags, identity-based auth, `prevent_destroy`, remote locked state) are the rules worth encoding as custom policies so they are enforced rather than remembered.
- **`devops-engineer`** applies every fix; this skill finds and re-scans.
- **Cloud application security (M12)**: this skill is the cloud-app-security IaC/config lane (prefer `trivy config`; legacy tfsec rule ids map to Trivy AVD). Image scanning is `qa-{java,dotnet,typescript}:image-infra-scan`; signing, SBOM and SLSA are `devops/supply-chain-security`; SAST → `qa-*:code-scan`, DAST → `qa-*:{active,passive}-scan`, SCA → `qa-*:dependency-scan`.
- `references/checkov.md` · `references/opa-conftest.md` · `references/other-scanners.md` · `references/ci-wiring.md`.
