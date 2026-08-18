---
name: devops-iac-security
description: Use when scanning Infrastructure-as-Code for misconfiguration beyond Trivy's built-in checks — deep Terraform, `terraform plan`, and org-specific policy-as-code (Checkov, OPA/Conftest). Triggers "scan our Terraform for misconfig", "add Checkov to CI", "OPA/Conftest policy for our Helm charts". Not for a live cluster (`devops-k8s-security`), a live cloud account (`devops-cloud-posture`), plugin-rule conformance (`devops-auditor`), or the built-in IaC gate (`qa-security-image-infra-scan`).
---

# DevOps — IaC Security (Checkov & policy-as-code)

Infrastructure-as-Code is the **intended** state of your cloud: an S3 bucket without encryption, a security
group open to `0.0.0.0/0`, a pod spec without `runAsNonRoot`, a Key Vault without purge protection. All of
it is decided in a `.tf` / `.bicep` / `.yaml` file long before it exists, which makes IaC scanning the
cheapest security gate in the library — it reads files, needs no running target, and can run on **every PR
from day one**.

This skill owns the **deep** half of that gate: **Checkov** (1,000+ built-in policies across Terraform,
Terraform *plan*, CloudFormation, Bicep/ARM, Kubernetes, Helm, Kustomize, Dockerfile, Serverless, and CI
configs, with **graph-based** checks that reason across resources), and **OPA/Conftest** — Rego policies over
any structured config, which is how **org-specific** rules that no vendor ships get enforced. It runs in the
**deploy pipeline** (`devops/{github-actions,gitlab-ci,azure-pipelines}`), never the `qa/cicd/*` test lane.

> **⚠️ Authorization: none needed — and say so.** Unlike its Stage-1 siblings (`devops-k8s-security` probes a
> live cluster, `devops-cloud-posture` reads a live account), IaC scanning is **purely static**: it reads
> files in the repo and sends nothing anywhere. There is no live target, no blast radius, and no
> authorization line to record. That is the whole point — this is the **shift-left, safe-on-every-PR** gate
> that runs unattended on forks and untrusted branches. The one caveat is `--download-external-modules`,
> which fetches remote Terraform modules (network egress, third-party code) — treat that as a deliberate
> opt-in, not a default.

> **⚠️ THE FENCE — vs `qa-security-image-infra-scan` (Trivy `config`). Read this before adding a second
> gate.** Trivy **already scans IaC**: `trivy config ./infra` runs the misconfig scanner (the absorbed tfsec
> check library) over Terraform, CloudFormation, Kubernetes, Helm, and Dockerfiles, and that skill already
> owns it as the A02 gate. **Do not duplicate it.** This skill's distinct value is exactly three things:
> **(a) multi-scanner depth** — Checkov's graph checks reason across resources and modules (bucket → its
> separate `aws_s3_bucket_public_access_block`, role → its attached policy) where a per-file check cannot;
> **(b) policy-as-code** — Checkov custom policies and OPA/Conftest express **org-specific** rules
> ("every resource carries `cost_center`", "only these three AMI owners", "no public ingress outside the
> DMZ account") that no vendor's built-in catalogue contains; **(c) plan scanning** — Checkov evaluates the
> **`terraform plan` JSON**, i.e. the *resolved* state after variables, locals, and modules are computed,
> catching what a static template read cannot. **The rule: one scanner owns the gate for a given
> misconfig class.** Trivy `config` is the lightweight built-in default and stays the default for a repo
> that only needs one; when this skill's gate goes in, Trivy's `config` scan drops to **informational**
> (`--exit-code 0`) or is scoped away, so the same open security group never fails two pipelines, needs two
> suppressions, and produces two conflicting tickets.

## Two spines per finding — OWASP + CIS, ATT&CK where it maps

| Spine | What it answers | Example |
|---|---|---|
| **OWASP Top 10:2025 — A02 Security Misconfiguration** (primary) | Which application-security category the misconfig belongs to | An unencrypted bucket, a permissive SG, a container with no resource limit |
| OWASP **A01** Broken Access Control · **A03** Software Supply Chain Failures | The two secondary categories IaC reaches | An IAM policy with `Action: "*"` (A01); an unpinned module source or CI action (A03) |
| **CIS Benchmarks** (AWS / Azure / GCP / Kubernetes / Docker) | The compliance control — Checkov ships the mapping | `CKV_AWS_18` → CIS AWS 3.6 (S3 access logging) |
| **MITRE ATT&CK Cloud / Containers** | The *technique* the misconfig enables — the offensive-lane language | Public S3 bucket → **T1530** Data from Cloud Storage · wildcard IAM role → **T1078.004** Valid Accounts: Cloud · privileged pod spec → **T1611** Escape to Host |

Use the **Cloud** and **Containers** matrices, not Enterprise — the matrix is keyed to the surface. Not every
misconfig maps to a technique; when it doesn't, say so rather than inventing one.

> **Green ≠ safe.** A clean Checkov run means **the templates in this repo** passed **these** checks. It says
> nothing about: what is *actually running* (drift — someone changed it in the portal; `devops-cloud-posture`
> and `devops-k8s-security` read the live state), whether the app on top is exploitable
> (`qa-security-*`), whether the image is patched (`qa-security-image-infra-scan`), or whether a rule your
> org cares about even exists as a check (that is the policy-as-code half — write it). Every report names
> what it covered and what it handed off.

## Decision matrix — which tool, and when

| Need | Use | Reads | Notes |
|---|---|---|---|
| A **first, cheap** IaC gate on a repo with no scanner at all | **Trivy `config`** (`qa-security-image-infra-scan`) | IaC templates | One binary you already run for images. Start here; escalate when you outgrow it |
| **Deep Terraform** — modules, variables, cross-resource **graph** checks | **Checkov** `-d .` | `.tf` + resolved module graph | The headline. `references/checkov.md` |
| Gate the **evaluated plan**, not the template | **Checkov** `--framework terraform_plan` | `terraform plan` JSON | Sees resolved vars/locals/module outputs. `references/checkov.md` |
| **Org-specific** rule no built-in check expresses | **OPA/Conftest** (or a Checkov custom policy) | any structured config | The policy-as-code half. `references/opa-conftest.md` |
| **Bicep / ARM** templates | **Checkov** `--framework bicep,arm` | `.bicep` / ARM JSON | Trivy does not cover Bicep; Checkov does |
| **Helm / Kustomize** rendered manifests | **Checkov** `--framework helm,kustomize` or render → **Conftest** | rendered YAML | Checkov renders internally; Conftest wants `helm template` output |
| **Dockerfile** misconfig | Trivy `config` **or** Checkov `--framework dockerfile` | the Dockerfile | Pick one owner — overlap is total |
| **CI/CD pipeline** config hardening | **Checkov** `--framework github_actions,gitlab_ci` | workflow YAML | Unpinned actions, `pull_request_target`, secret exposure (A03) |
| Broad multi-format coverage on an exotic IaC format | **KICS** | 20+ IaC formats | Breadth over depth; see `references/other-scanners.md` (incl. its 2026 action compromise) |
| **tfsec** / **Terrascan** | **Do not adopt** | — | tfsec merged into Trivy (EOL May 2025); Terrascan archived Nov 2025. `references/other-scanners.md` |
| A **live** cluster / cloud account | `devops-k8s-security` / `devops-cloud-posture` | the K8s API / cloud APIs | Different lane — running state, not intended state |
| Conformance against **this plugin's own rules** | `devops-auditor` | the repo | Different question — see the fence below |

**Rule of thumb:** **Checkov is the gate**, **Conftest is the org rulebook**, **plan scanning is the
high-signal pass on the branch that is about to apply**. Trivy `config` stays the lightweight default for
repos that need one scanner and nothing more.

> **⚠️ Fence vs `devops-auditor`.** The auditor is a **read-only conformance sweep against the `devops`
> plugin's own twelve-section rule set**, written by a human-facing reviewer, producing a saved
> `docs/audits/<NNN>-devops-conformance-r<N>.md`. **This skill runs the scanners and policy engines** —
> tooling that emits check IDs, exit codes, and SARIF. Overlap is real (both look at Terraform); the split
> is *who decides the rule*: the auditor checks the plugin's conventions, this skill checks a scanner's
> published catalogue plus **your** policies, and gates a build on the result. A pure "we don't tag
> `cost_center`" conformance observation belongs to the auditor **unless you encode it as a policy**, at
> which point it becomes this skill's gate.

## Setup — pin the version, cache nothing that matters

```bash
# Checkov — Python; pin the version in CI so a new check is a deliberate, reviewable bump.
pipx install checkov==3.2.529
# or, no install:
docker run --rm -v "$PWD:/tf" bridgecrew/checkov:3.2.529 -d /tf

# Conftest — single Go binary.
brew install conftest            # or: https://github.com/open-policy-agent/conftest/releases
docker run --rm -v "$PWD:/project" openpolicyagent/conftest:v0.62.0 test .

checkov --version && conftest --version
```

> **Pin the version** (`checkov==3.2.529`, `openpolicyagent/conftest:v0.62.0`, `bridgecrew/checkov:3.2.529`) —
> never `latest`. Checkov ships checks weekly; an unpinned scanner turning a green build red overnight is
> exactly the surprise that gets the gate switched off. Bump on purpose, in a PR, with the new findings
> triaged in that PR.
>
> **Checkov needs no vulnerability DB** (unlike Trivy) — the checks ship in the package, so cold runs are
> fast and offline. The one network dependency is `--download-external-modules`; keep it off unless the repo
> genuinely consumes registry modules whose contents matter to the result.

## The scan commands + gating flags

```bash
# Whole repo, every framework Checkov auto-detects.
checkov -d .

# Scope to what you mean — faster, and it stops Dockerfile/CI findings leaking into the Terraform gate.
checkov -d ./infra --framework terraform,terraform_plan

# One file.
checkov -f ./infra/environments/prod/main.tf

# The evaluated plan — resolved vars, locals, module outputs (see "Plan scanning" below).
terraform -chdir=infra/environments/prod plan -out=tfplan.binary
terraform -chdir=infra/environments/prod show -json tfplan.binary > tfplan.json
checkov -f tfplan.json --framework terraform_plan

# Org policy-as-code over the same plan JSON.
conftest test tfplan.json --policy ./policy

# Rendered Helm → policy.
helm template ./charts/api | conftest test - --policy ./policy/k8s
```

| Flag | Effect |
|---|---|
| `-d` / `-f` | Directory or single file (mutually exclusive) |
| `--framework` / `--skip-framework` | Restrict to `terraform`, `terraform_plan`, `cloudformation`, `bicep`, `arm`, `kubernetes`, `helm`, `kustomize`, `dockerfile`, `github_actions`, `gitlab_ci`, `secrets`, … **Always scope it** |
| `-c` / `--check` | Run **only** these check IDs or severities (`CKV_AWS_18`, `HIGH`) — a severity here means *that severity and above* |
| `--skip-check` | Skip these IDs/severities — a severity here means *that severity and below*. The check does not run at all |
| `--soft-fail` | Always exit `0` — **this is the informational pass**. Default behaviour is exit `1` on any failed check |
| `--soft-fail-on` / `--hard-fail-on` | Per-check/severity exit control — the fine-grained ratchet between report-only and gating |
| `--baseline .checkov.baseline` | Report only failures **not** in the baseline — the gate-NEW mechanism |
| `--create-baseline` | Write the baseline from the current results (run once, at adoption) |
| `--skip-path` | Regex path exclusion (`.terraform/`, vendored modules, fixtures) |
| `--external-checks-dir` | Load custom Python/YAML policies |
| `--var-file` | Extra `.tfvars` (source-Terraform and Helm scans only; requires `-d`) |
| `--download-external-modules` | Fetch remote modules for a complete graph — **network egress, opt-in** |
| `--deep-analysis` + `--repo-root-for-plan-enrichment` | Merge the plan graph with the HCL graph so plan findings carry real `file:line` |
| `-o` / `--output` | `cli`, `json`, `sarif`, `junitxml`, `csv`, `github_failed_only` (repeatable) |
| `--compact` / `--quiet` | Drop code blocks / show failures only — the two flags that make CI logs readable |
| `--config-file .checkov.yml` | All of the above, committed, so local and CI agree |

The defining trait, and the **inverse of Trivy's**: **bare `checkov -d .` exits `1` on the first failed
check.** It gates by default; `--soft-fail` is what makes it report-only. Get this backwards and your
adoption PR fails on 400 legacy findings.

## The two-pass gate — informational + gating

Same shape as the Trivy gate, so the two read identically in a pipeline:

```bash
# Pass 1 — INFORMATIONAL. Everything, every severity, never fails (--soft-fail).
#          Its job is the complete picture in the logs and the SARIF artifact.
checkov -d ./infra --framework terraform --soft-fail --compact -o cli -o sarif \
  --output-file-path console,checkov-all.sarif

# Pass 2 — GATING. Only new, only actionable, fails the build.
checkov -d ./infra --framework terraform \
  --baseline .checkov.baseline \
  --skip-check LOW \
  --compact
```

- **Pass 1** is observability: the Low/Medium backlog is visible without blocking merge.
- **Pass 2** is the gate: `--baseline` drops the known backlog, `--skip-check LOW` drops the noise floor, and
  the default exit-1 does the failing.
- **Ratchet, don't big-bang.** Adopt at `--check CRITICAL` (or `--soft-fail-on` everything below), clear the
  backlog, then tighten to `HIGH,CRITICAL`. Same ratchet as `failBuildOnCVSS` 9.0 → 7.0 in SCA.

## Baseline & gate-NEW discipline

A scanner introduced to a real repo finds hundreds of pre-existing failures. Blocking on all of them means
the gate is disabled by Friday. **Baseline once, then gate NEW hard.**

```bash
# ONE TIME, at adoption. Commit the file; it is the record of accepted debt.
checkov -d ./infra --create-baseline
git add infra/.checkov.baseline

# Every run after: only failures absent from the baseline fail the build.
checkov -d ./infra --baseline .checkov.baseline
```

- The baseline is **a debt register, not a mute button** — it is committed, reviewed in PRs, and **only ever
  shrinks**. A PR that grows the baseline is a PR adding a misconfig; treat it as one.
- **Never regenerate the baseline to make a red build green.** That is the single most common way this gate
  dies. Regeneration is a deliberate, reviewed act (e.g. after a bulk remediation).
- **Newly-added resources have no baseline entry**, so they are gated at full strength from their first line
  — which is the entire point: new infrastructure is born compliant.

## Suppression discipline — ticketed, scoped, expiring

Checkov's inline mechanism is a comment **inside the resource block**, `checkov:skip=<CHECK_ID>:<reason>`.
The discipline is the `.trivyignore` discipline, restated: **specific ID + ticket + reason + a re-review
date.**

```hcl
resource "aws_s3_bucket" "logs" {
  # checkov:skip=CKV_AWS_18:JIRA-5140 — access logging on the log bucket itself would recurse; re-review 2026-11-01
  bucket = "${var.prefix}-access-logs"
}
```

```yaml
# .checkov.yml — committed config so local runs and CI agree. Repo-wide skips live here, ticketed.
directory:
  - infra
framework:
  - terraform
skip-path:
  - .terraform/
  - infra/modules/vendored/
skip-check:
  # JIRA-5141 — CKV_AWS_144 (cross-region replication) is out of scope until the DR programme lands; re-review 2026-12.
  - CKV_AWS_144
baseline: infra/.checkov.baseline
compact: true
```

- Scope every suppression to **one check ID on one resource**. A repo-wide `--skip-check` for a check that
  fails in one place buries every future occurrence, including the real one.
- **The comment carries the ticket and the re-review date** — Checkov has no native expiry (unlike
  `.trivyignore.yaml`'s `expired_at`), so the date is a review-enforced convention. A suppression with no
  ticket is a finding.
- **Prefer the fix.** Encrypting the bucket is one line; the suppression is forever. And a suppression for a
  check you *disagree with* is the wrong tool — disable it once in `.checkov.yml` with the reason, then ask
  whether the *right* rule is a custom policy.

## Policy-as-code — the half no vendor ships

Built-in catalogues encode what the **industry** agrees on. They cannot encode what **your org** decided:
mandatory tags, an allow-list of instance types or regions, "no public ingress outside the DMZ account",
naming conventions, "every RDS instance in prod has `deletion_protection`". That is policy-as-code, and it is
this skill's headline alongside plan scanning.

Two routes, and the choice is mostly about who writes the policy:

| Route | Write it when | Language | Depth |
|---|---|---|---|
| **Checkov custom policy** | The rule is about **one resource type's attributes**, or a **graph connection** between two resources, and you want it in the same run/report/baseline as the built-ins | YAML (declarative) or Python | `references/checkov.md` |
| **OPA / Conftest** | The rule spans **arbitrary structured config**, needs real logic, needs to be **shared across tools** (the same Rego runs in Conftest, Gatekeeper, and Terraform Cloud), or must run over the **plan JSON** | Rego | `references/opa-conftest.md` |

```rego
# infra/policies/opa/tags.rego — an org rule no vendor catalogue ships, over the plan JSON.
package main

import rego.v1

required_tags := {"env", "service", "owner", "cost_center"}

deny contains msg if {
	change := input.resource_changes[_]
	not change.change.actions[0] == "delete"
	missing := required_tags - {t | change.change.after.tags[t]}
	count(missing) > 0
	msg := sprintf("%s is missing mandatory tags: %v", [change.address, missing])
}
```

```bash
conftest test tfplan.json --policy ./infra/policies/opa      # Rego route
checkov -d ./infra --external-checks-dir ./infra/policies/checkov   # Checkov custom-policy route
```

**Test your policies.** A policy that never fires is worse than no policy — it reports green forever and
manufactures confidence. Conftest has `conftest verify` for `*_test.rego` unit tests; Checkov custom policies
get a fixture pair (one compliant resource, one violating) asserted in CI. Both references carry the shapes.

## Plan scanning — the *evaluated* state

Static template scanning reads `encrypted = var.enable_encryption` and cannot know what `var` resolves to.
**Plan scanning reads the resolved value** — after variables, locals, `for_each`, module outputs, and data
sources — which is why it catches a class of findings a template read structurally cannot.

```bash
terraform -chdir=infra/environments/prod plan -out=tfplan.binary
terraform -chdir=infra/environments/prod show -json tfplan.binary > tfplan.json

# --deep-analysis + --repo-root-for-plan-enrichment merges the plan graph with the HCL graph,
# so a plan finding still points at the .tf line a human has to edit.
checkov -f tfplan.json --framework terraform_plan \
  --deep-analysis --repo-root-for-plan-enrichment infra/environments/prod
conftest test tfplan.json --policy ./infra/policies/opa
```

- **The plan JSON is sensitive** — resolved secret values, connection strings, account identifiers. Never
  commit it, never publish it as an artifact, scrub it from logs. Treat it like the state file.
- `plan` needs cloud **read** credentials. In CI that is OIDC / Workload Identity Federation with a read-only
  role — **never** a long-lived key (the `devops` plugin's no-static-credentials invariant).
- **Run both passes.** Templates catch what plan cannot (a module default this env overrides, code behind
  `count = 0`); plan catches what templates cannot (the resolved value). Orthogonal, same as `trivy config`
  vs `trivy image`.

## CI wiring — the DEPLOY pipeline, not the test lane

Infra gates belong in the **deploy** pipeline
(`devops/{github-actions,gitlab-ci,azure-pipelines}`) alongside `fmt`/`validate`/`plan` — **not** in
`qa/cicd/*`, which owns the test-suite lane (shard matrix, Allure, perf gate). Same fence the library already
draws for Trivy's image build.

```yaml
# .github/workflows/infra-security.yml — cross-link devops/github-actions
name: IaC Security
on: [pull_request]

permissions:
  contents: read
  security-events: write        # SARIF upload
  id-token: write               # OIDC to the cloud for `terraform plan` — no static keys

jobs:
  iac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      # Pass 1 — INFORMATIONAL. Full picture, never fails the build.
      - uses: bridgecrewio/checkov-action@v12.1347.0
        with:
          directory: infra
          framework: terraform
          soft_fail: true
          output_format: cli,sarif
          output_file_path: console,checkov-all.sarif

      # Pass 2 — GATING. Baseline-scoped, fails on anything NEW.
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
          role-to-assume: ${{ vars.PLAN_READONLY_ROLE_ARN }}   # OIDC, read-only — no static key
          aws-region: eu-west-1
      - uses: hashicorp/setup-terraform@v3
        with: { terraform_version: 1.13.3 }
      - run: |
          terraform -chdir=infra/environments/prod init
          terraform -chdir=infra/environments/prod plan -out=tfplan.binary
          terraform -chdir=infra/environments/prod show -json tfplan.binary > tfplan.json
      # The plan JSON is sensitive — consumed in-job, never uploaded as an artifact.
      - run: |
          docker run --rm -v "$PWD:/w" -w /w openpolicyagent/conftest:v0.62.0 \
            test tfplan.json --policy infra/policies/opa --output github
```

- **Pin every action by tag or SHA** (`@v12.1347.0`, not `@master`) — the `devops` plugin's pinning
  invariant, and not theoretical: KICS's own GitHub Action was compromised in March 2026
  (`references/other-scanners.md`).
- **SARIF → code-scanning** so each finding lands inline on the PR diff, de-duped run-over-run — the same
  consolidation `qa-security-shared` prescribes.
- **GitLab CI / Azure Pipelines** run the identical two-pass via the `bridgecrew/checkov` and
  `openpolicyagent/conftest` Docker images; cross-link `devops/{gitlab-ci,azure-pipelines}`.

## Anti-patterns

- **Double-gating the same misconfig in Trivy `config` and Checkov.** One open security group, two red
  builds, two suppression files, two tickets — and the team mutes whichever is louder. *Fix:* one scanner
  owns the gate; the other drops to informational (`--exit-code 0` / `--soft-fail`) or is scoped away by
  framework.
- **Adopting Checkov with no baseline.** The first PR fails on 400 pre-existing findings, the gate is
  `--soft-fail`'d "temporarily", and it never comes back. *Fix:* `--create-baseline` once, commit it, gate
  NEW.
- **Regenerating the baseline to turn a build green.** The mechanism designed to make the gate adoptable
  becomes the mechanism that makes it meaningless. *Fix:* the baseline only shrinks; regeneration is a
  reviewed, deliberate act.
- **Blanket `--skip-check` in `.checkov.yml` with no ticket.** Buries every future instance of a check,
  including the one that matters. *Fix:* inline `checkov:skip=<ID>:<ticket + reason>` on the specific
  resource; repo-wide skips carry a ticket and a re-review date.
- **Scanning templates only, never the plan.** `encrypted = var.enable_encryption` reads fine and resolves to
  `false` in prod. *Fix:* add the `terraform_plan` pass on the branch that is about to apply.
- **Committing or publicly archiving `tfplan.json`.** It carries resolved secrets and account identifiers.
  *Fix:* consume it in-job, never upload it, treat it like state.
- **Running the gate with an unpinned scanner.** A weekly check release silently turns a green pipeline red
  and the fix ships as "disable the gate." *Fix:* pin `checkov==X.Y.Z` and the action version; bump in a PR
  that triages the new findings.
- **Writing policies nobody tests.** A Rego rule with a typo in the resource path is green forever and
  proves nothing. *Fix:* `conftest verify` on `*_test.rego`, and a pass/fail fixture per Checkov custom
  policy, both in CI.
- **`--download-external-modules` on by default.** Silent network egress and third-party code execution on
  every PR, including from forks. *Fix:* opt in per repo, only where the module contents change the verdict.
- **Adopting tfsec or Terrascan in 2026.** Both are dead — tfsec merged into Trivy (last release May 2025),
  Terrascan archived by Tenable (Nov 2025). *Fix:* Trivy for the tfsec check library, Checkov for depth.
  `references/other-scanners.md`.
- **Treating a clean IaC scan as "the infrastructure is secure."** It says the *templates* passed *these*
  checks. It knows nothing about drift, runtime, or the rules you never encoded. *Fix:* state the coverage
  and the handoffs (`devops-cloud-posture` for live state, `devops-k8s-security` for the cluster,
  `devops-infra-controls-validation` for whether the controls actually work).

## Rules (hard constraints)

- **Own the boundary with Trivy.** `qa-security-image-infra-scan`'s `trivy config` is the lightweight
  built-in IaC gate; this skill owns **deep Terraform + graph checks, plan scanning, and policy-as-code**.
  **One scanner gates a given misconfig class** — the other runs informational or is scoped away. Never
  double-gate.
- **Pin the scanner and every action** (`checkov==3.2.529`, `openpolicyagent/conftest:v0.62.0`,
  `bridgecrewio/checkov-action@v12.1347.0`). No `latest`, no `@master`.
- **Baseline once, gate NEW hard.** `--create-baseline` at adoption, commit it, and let it **only shrink**.
  Regenerating it to clear a red build is forbidden.
- **Two passes:** informational (`--soft-fail`, everything, SARIF artifact) + gating (`--baseline`,
  severity-scoped, exits non-zero). Ratchet the severity floor up over time; never start at HIGH on a legacy
  repo.
- **Every suppression is `checkov:skip=<CHECK_ID>:<ticket + reason>` on the specific resource**, with a
  re-review date. Checkov has no native expiry — the date is enforced in review. Prefer the fix.
- **Scope `--framework` explicitly.** An unscoped run mixes Dockerfile, CI, and secrets findings into the
  Terraform gate and makes the exit code unreadable.
- **Encode org rules as policy-as-code** (Checkov custom policy or Rego) rather than as review comments — and
  **test every policy** (`conftest verify`, pass/fail fixtures). An untested policy is green forever.
- **`terraform plan` JSON is sensitive** — never committed, never a public artifact, scrubbed from logs. The
  credentials that produce it are **OIDC / Workload Identity, read-only** — never a static key.
- **`--download-external-modules` is opt-in**, per repo, with the network egress acknowledged.
- **Gate in the deploy pipeline** (`devops/{github-actions,gitlab-ci,azure-pipelines}`), never `qa/cicd/*`.
  Emit **SARIF** → code-scanning for inline PR findings.
- **Stamp both spines per finding** — OWASP (A02 primary; A01/A03 where they apply) + the CIS control, and
  the ATT&CK Cloud/Containers technique **where one genuinely maps**. Don't invent a technique ID.
- **No authorization line is needed** — this lane is static and reads files only. Do not import the
  live-target gates from the sibling skills; do not claim coverage of live state you never read.
- A clean run ≠ secure. **State coverage and handoffs** in every report: what was scanned, which checks ran,
  which were skipped and why, and which layer was left to a sibling lane.

## Cross-references

- **`qa-security-image-infra-scan`** — **the most important fence.** Trivy's `config` scanner already covers
  IaC misconfig with the absorbed tfsec check library, and stays the lightweight default. This skill owns
  depth (graph checks), plan scanning, and policy-as-code. **One scanner gates a given class; run the other
  informational.** That skill also owns the image/OS/SBOM layers this one never touches.
- `devops-k8s-security` — the **live cluster** sibling (kube-bench CIS scoring, Kubescape, kube-hunter,
  RBAC/network-policy validation). This skill checks the manifest; that one checks the cluster it produced.
- `devops-cloud-posture` — the **live cloud account** sibling (Prowler / ScoutSuite CSPM). This skill checks
  intended state; that one finds the drift and the resources IaC never created.
- `devops-supply-chain-security` — artifact signing, SLSA provenance, dependency confusion (**A03**). Adjacent
  on the CI/CD surface: this skill scans the pipeline **config**, that one secures the **artifacts** it
  produces.
- `devops-threat-modeling` — STRIDE / attack trees. Upstream: the threat model says which misconfig classes
  matter for **this** system, which is what a custom policy should encode.
- `devops-infra-controls-validation` — proves encryption / secrets management / monitoring controls are not
  just declared but **effective**. This skill proves the setting is in the template; that one proves it works.
- `infra-security-tester` (agent) — the phased orchestrator that runs this skill as its **IaC & image
  posture** phase, before the live-cluster and cloud-posture phases.
- **`devops-auditor`** — the **static conformance** sibling. It sweeps the repo against the `devops` plugin's
  own twelve-section rule set into `docs/audits/`; this skill runs scanners and policy engines and gates a
  build. Fence: who owns the rule — the plugin's conventions vs a scanner catalogue plus your policies.
- **`devops-infrastructure-as-code`** — the **authoring** sibling. It writes the Bicep/Terraform this skill
  scans, and its Rules (tags mandatory, identity-based auth, `prevent_destroy`, remote+locked state) are
  exactly the rules worth encoding as custom policies so they are enforced rather than remembered.
- **`devops-engineer`** — the peer that **applies every fix**. This skill finds and re-scans; it does not edit
  infrastructure (the library's auditor↔engineer handshake).
- `devops/{github-actions,gitlab-ci,azure-pipelines}` — where the gate is wired (**deploy** pipeline, not
  `qa/cicd/*`), including OIDC for the plan credentials and the SARIF upload.
- `references/checkov.md` · `references/opa-conftest.md` · `references/other-scanners.md` — the deep dives.
